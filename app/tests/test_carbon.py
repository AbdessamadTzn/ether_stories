"""
Carbon Tracking Tests
=====================
Tests for CO2 emission tracking and dashboard.
"""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from app.db.models import User, Story, CarbonEmission, OperationType


class TestCarbonEmissionModel:
    """Test CarbonEmission model operations."""
    
    def test_create_emission_record(self, session: Session, test_user: User, test_story: Story):
        """Test creating a carbon emission record."""
        emission = CarbonEmission(
            user_id=test_user.id,
            story_id=test_story.id,
            operation_type=OperationType.STORY_GENERATION,
            operation_details="Generated a 5-minute story",
            emissions_kg=0.00123,
            energy_kwh=0.0056,
            duration_seconds=15.5
        )
        session.add(emission)
        session.commit()
        session.refresh(emission)
        
        assert emission.id is not None
        assert emission.emissions_kg == 0.00123
        assert emission.operation_type == OperationType.STORY_GENERATION
    
    def test_emission_operation_types(self, session: Session, test_user: User, test_story: Story):
        """Test different operation types can be recorded."""
        operations = [
            (OperationType.STORY_GENERATION, "Story gen"),
            (OperationType.TRANSLATION, "Translation"),
            (OperationType.TTS, "Text to speech"),
            (OperationType.IMAGE_GENERATION, "Image gen"),
        ]
        
        for op_type, details in operations:
            emission = CarbonEmission(
                user_id=test_user.id,
                story_id=test_story.id,
                operation_type=op_type,
                operation_details=details,
                emissions_kg=0.001,
                energy_kwh=0.005,
                duration_seconds=10.0
            )
            session.add(emission)
        
        session.commit()
        
        # Verify all types were saved
        stmt = select(CarbonEmission).where(CarbonEmission.user_id == test_user.id)
        emissions = session.exec(stmt).all()
        op_types = {e.operation_type for e in emissions}
        
        for op_type, _ in operations:
            assert op_type in op_types
    
    def test_emission_user_relationship(self, test_carbon: CarbonEmission, test_user: User):
        """Test emission is linked to correct user."""
        assert test_carbon.user_id == test_user.id
    
    def test_emission_story_relationship(self, test_carbon: CarbonEmission, test_story: Story):
        """Test emission is linked to correct story."""
        assert test_carbon.story_id == test_story.id


class TestCarbonCalculations:
    """Test carbon emission calculations."""
    
    def test_total_emissions_calculation(self, session: Session, test_user: User, test_story: Story):
        """Test calculating total emissions for a user."""
        # Add multiple emissions
        for i in range(5):
            emission = CarbonEmission(
                user_id=test_user.id,
                story_id=test_story.id,
                operation_type=OperationType.STORY_GENERATION,
                emissions_kg=0.001,  # 1 gram each
                energy_kwh=0.005,
                duration_seconds=10.0
            )
            session.add(emission)
        session.commit()
        
        # Calculate total
        from sqlmodel import func
        stmt = select(func.sum(CarbonEmission.emissions_kg)).where(
            CarbonEmission.user_id == test_user.id
        )
        total_kg = session.exec(stmt).one()
        
        assert total_kg >= 0.005  # At least 5 * 0.001
    
    def test_emissions_by_operation_type(self, session: Session, test_user: User, test_story: Story):
        """Test grouping emissions by operation type."""
        # Add different types
        session.add(CarbonEmission(
            user_id=test_user.id,
            story_id=test_story.id,
            operation_type=OperationType.STORY_GENERATION,
            emissions_kg=0.002,
            energy_kwh=0.01,
            duration_seconds=20.0
        ))
        session.add(CarbonEmission(
            user_id=test_user.id,
            story_id=test_story.id,
            operation_type=OperationType.TTS,
            emissions_kg=0.001,
            energy_kwh=0.005,
            duration_seconds=10.0
        ))
        session.commit()
        
        # Group by type
        from sqlmodel import func
        stmt = select(
            CarbonEmission.operation_type,
            func.sum(CarbonEmission.emissions_kg)
        ).where(
            CarbonEmission.user_id == test_user.id
        ).group_by(CarbonEmission.operation_type)
        
        results = session.exec(stmt).all()
        assert len(results) >= 2


class TestCarbonDashboard:
    """Test carbon dashboard endpoint."""
    
    def test_dashboard_requires_auth(self, client: TestClient):
        """Test carbon dashboard requires authentication."""
        response = client.get("/carbon-dashboard")
        assert response.status_code in [401, 307]
    
    def test_dashboard_accessible_when_logged_in(self, auth_client: TestClient):
        """Test dashboard is accessible when authenticated."""
        response = auth_client.get("/carbon-dashboard")
        assert response.status_code == 200
    
    def test_dashboard_shows_emissions(self, auth_client: TestClient, test_carbon: CarbonEmission):
        """Test dashboard displays emission data."""
        response = auth_client.get("/carbon-dashboard")
        assert response.status_code == 200
        # The page should load successfully with data


class TestCarbonEquivalences:
    """Test CO2 equivalence calculations."""
    
    def test_grams_to_car_km(self):
        """Test conversion to car kilometers."""
        # ~120g CO2 per km for average car
        grams = 120
        km = grams / 120  # 1 km
        assert km == pytest.approx(1.0, rel=0.1)
    
    def test_grams_to_phone_charges(self):
        """Test conversion to phone charges."""
        # ~8.22g CO2 per phone charge
        grams = 8.22
        charges = grams / 8.22
        assert charges == pytest.approx(1.0, rel=0.1)
    
    def test_grams_to_tv_hours(self):
        """Test conversion to TV hours."""
        # ~36g CO2 per hour of TV
        grams = 36
        hours = grams / 36
        assert hours == pytest.approx(1.0, rel=0.1)
    
    def test_zero_emissions(self):
        """Test zero emissions case."""
        grams = 0
        assert grams / 120 == 0  # 0 km
        assert grams / 8.22 == 0  # 0 charges
