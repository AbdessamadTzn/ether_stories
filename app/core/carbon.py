"""
Carbon Emission Tracker for Ether Stories
Uses CodeCarbon to measure CO2 emissions from AI operations
"""

from datetime import datetime
from typing import Optional
from contextlib import contextmanager
from codecarbon import EmissionsTracker
from sqlmodel import Session

from app.db.models import CarbonEmission, OperationType
from app.db.session import engine
from app.core.logger import log_carbon_emission, get_logger

# Carbon-specific logger
carbon_logger = get_logger("carbon")


class CarbonTracker:
    """
    Wrapper around CodeCarbon's EmissionsTracker for easy integration.
    Automatically saves emission data to the database.
    """
    
    def __init__(
        self, 
        user_id: int, 
        operation_type: OperationType,
        story_id: Optional[int] = None,
        operation_details: Optional[str] = None
    ):
        self.user_id = user_id
        self.story_id = story_id
        self.operation_type = operation_type
        self.operation_details = operation_details
        self.tracker = None
        self.start_time = None
        
    def start(self):
        """Start tracking emissions"""
        self.tracker = EmissionsTracker(
            project_name="ether_stories",
            measure_power_secs=10,  # Measure power every 10 seconds
            save_to_file=False,     # Don't save CSV, we'll use DB
            logging_logger=None,    # Suppress logs
            log_level="error"       # Only show errors
        )
        self.start_time = datetime.utcnow()
        self.tracker.start()
        return self
    
    def stop(self) -> Optional[CarbonEmission]:
        """
        Stop tracking and save to database.
        Returns the CarbonEmission record.
        """
        if not self.tracker:
            return None
            
        # Stop tracking and get emissions
        emissions_kg = self.tracker.stop()
        
        if emissions_kg is None:
            emissions_kg = 0.0
        
        # Calculate duration
        duration = (datetime.utcnow() - self.start_time).total_seconds() if self.start_time else 0.0
        
        # Get additional data from tracker (with safe type conversion)
        energy_kwh = getattr(self.tracker, '_total_energy', None)
        cpu_power = getattr(self.tracker, '_cpu_power', None)
        gpu_power = getattr(self.tracker, '_gpu_power', None)
        country_code = getattr(self.tracker, '_country_iso_code', None)
        
        # Safe float conversion helper
        def safe_float(val):
            if val is None:
                return None
            try:
                return float(val)
            except (TypeError, ValueError):
                return None
        
        # Create emission record
        emission = CarbonEmission(
            user_id=self.user_id,
            story_id=self.story_id,
            operation_type=self.operation_type,
            operation_details=self.operation_details,
            emissions_kg=float(emissions_kg) if emissions_kg else 0.0,
            energy_kwh=safe_float(energy_kwh) or 0.0,
            duration_seconds=float(duration),
            cpu_power=safe_float(cpu_power),
            gpu_power=safe_float(gpu_power),
            country_iso_code=str(country_code) if country_code else None
        )
        
        # Save to database
        try:
            with Session(engine) as session:
                session.add(emission)
                session.commit()
                session.refresh(emission)
                # Log to file
                log_carbon_emission(
                    user_id=self.user_id,
                    operation=self.operation_type.value,
                    emissions_kg=float(emissions_kg) if emissions_kg else 0.0,
                    story_id=self.story_id
                )
                carbon_logger.info(f"🌱 Carbon tracked: {float(emissions_kg)*1000:.4f}g CO2 for {self.operation_type.value}")
                return emission
        except Exception as e:
            carbon_logger.error(f"Failed to save carbon emission: {e}")
            return emission
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False  # Don't suppress exceptions


@contextmanager
def track_carbon(
    user_id: int,
    operation_type: OperationType,
    story_id: Optional[int] = None,
    operation_details: Optional[str] = None
):
    """
    Context manager for tracking carbon emissions.
    
    Usage:
        with track_carbon(user_id=1, operation_type=OperationType.STORY_GENERATION):
            # Your AI operation here
            generate_story()
    """
    tracker = CarbonTracker(
        user_id=user_id,
        operation_type=operation_type,
        story_id=story_id,
        operation_details=operation_details
    )
    try:
        tracker.start()
        yield tracker
    finally:
        tracker.stop()


def get_user_carbon_stats(user_id: int) -> dict:
    """
    Get aggregated carbon statistics for a user.
    Returns total emissions, story count, and breakdown by operation type.
    """
    from sqlmodel import select, func
    
    with Session(engine) as session:
        # Total emissions
        total_query = select(
            func.sum(CarbonEmission.emissions_kg).label("total_emissions"),
            func.sum(CarbonEmission.energy_kwh).label("total_energy"),
            func.count(CarbonEmission.id).label("total_operations")
        ).where(CarbonEmission.user_id == user_id)
        
        result = session.exec(total_query).first()
        
        # Breakdown by operation type
        breakdown_query = select(
            CarbonEmission.operation_type,
            func.sum(CarbonEmission.emissions_kg).label("emissions"),
            func.count(CarbonEmission.id).label("count")
        ).where(
            CarbonEmission.user_id == user_id
        ).group_by(CarbonEmission.operation_type)
        
        breakdown_results = session.exec(breakdown_query).all()
        
        breakdown = {}
        for row in breakdown_results:
            breakdown[row.operation_type.value] = {
                "emissions_kg": float(row.emissions or 0),
                "count": row.count
            }
        
        # Recent emissions (last 10)
        recent_query = select(CarbonEmission).where(
            CarbonEmission.user_id == user_id
        ).order_by(CarbonEmission.created_at.desc()).limit(10)
        
        recent = session.exec(recent_query).all()
        
        return {
            "total_emissions_kg": float(result.total_emissions or 0),
            "total_energy_kwh": float(result.total_energy or 0),
            "total_operations": result.total_operations or 0,
            "breakdown": breakdown,
            "recent": [
                {
                    "id": e.id,
                    "operation_type": e.operation_type.value,
                    "emissions_kg": e.emissions_kg,
                    "created_at": e.created_at.isoformat()
                }
                for e in recent
            ],
            # Fun equivalences
            "equivalences": calculate_equivalences(float(result.total_emissions or 0))
        }


def calculate_equivalences(emissions_kg: float) -> dict:
    """
    Convert CO2 emissions to relatable equivalences.
    Based on EPA and other standard conversion factors.
    """
    return {
        "km_by_car": round(emissions_kg / 0.12, 2),          # ~120g CO2/km average car
        "smartphone_charges": round(emissions_kg / 0.008, 1), # ~8g CO2 per charge
        "hours_of_tv": round(emissions_kg / 0.097, 1),       # ~97g CO2/hour
        "cups_of_coffee": round(emissions_kg / 0.021, 1),    # ~21g CO2 per cup
        "google_searches": round(emissions_kg / 0.0007, 0),  # ~0.7g CO2 per search
        "trees_absorbed_daily": round(emissions_kg / 0.022, 3)  # Tree absorbs ~22g/day
    }


def get_story_carbon(story_id: int) -> dict:
    """Get carbon emissions for a specific story."""
    from sqlmodel import select, func
    
    with Session(engine) as session:
        query = select(
            func.sum(CarbonEmission.emissions_kg).label("total_emissions"),
            func.sum(CarbonEmission.energy_kwh).label("total_energy"),
            func.sum(CarbonEmission.duration_seconds).label("total_duration")
        ).where(CarbonEmission.story_id == story_id)
        
        result = session.exec(query).first()
        
        return {
            "story_id": story_id,
            "total_emissions_kg": float(result.total_emissions or 0),
            "total_energy_kwh": float(result.total_energy or 0),
            "total_duration_seconds": float(result.total_duration or 0),
            "equivalences": calculate_equivalences(float(result.total_emissions or 0))
        }
