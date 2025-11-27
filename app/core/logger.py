"""
Ether Stories - Logging System
Provides structured logging with file rotation and multiple log levels.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

# Create logs directory
LOGS_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Log format
DETAILED_FORMAT = '%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s'
SIMPLE_FORMAT = '%(asctime)s | %(levelname)-8s | %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# =========================
# MAIN APPLICATION LOGGER
# =========================

def setup_logger():
    """Setup the main application logger with console and file handlers."""
    
    logger = logging.getLogger("ether_stories")
    logger.setLevel(logging.DEBUG)  # Capture all levels
    
    # Prevent duplicate handlers
    if logger.hasHandlers():
        logger.handlers.clear()
    
    # --- Console Handler (INFO and above) ---
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(SIMPLE_FORMAT, datefmt='%H:%M:%S')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # --- Main App Log File (rotating, max 5MB, keep 5 backups) ---
    app_log_file = LOGS_DIR / "app.log"
    app_handler = RotatingFileHandler(
        app_log_file,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=5,
        encoding='utf-8'
    )
    app_handler.setLevel(logging.DEBUG)
    app_formatter = logging.Formatter(DETAILED_FORMAT, datefmt=DATE_FORMAT)
    app_handler.setFormatter(app_formatter)
    logger.addHandler(app_handler)
    
    # --- Error Log File (errors only) ---
    error_log_file = LOGS_DIR / "error.log"
    error_handler = RotatingFileHandler(
        error_log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(DETAILED_FORMAT, datefmt=DATE_FORMAT))
    logger.addHandler(error_handler)
    
    return logger


# Initialize main logger
logger = setup_logger()


# =========================
# SPECIALIZED LOGGERS
# =========================

def get_logger(name: str) -> logging.Logger:
    """
    Returns a child logger (e.g. ether_stories.manager).
    Inherits handlers from parent logger.
    """
    return logging.getLogger(f"ether_stories.{name}")


def get_carbon_logger() -> logging.Logger:
    """
    Specialized logger for carbon emissions tracking.
    Writes to a separate carbon.log file.
    """
    carbon_logger = logging.getLogger("ether_stories.carbon")
    
    if not any(isinstance(h, RotatingFileHandler) and 'carbon' in str(h.baseFilename) for h in carbon_logger.handlers):
        carbon_log_file = LOGS_DIR / "carbon.log"
        carbon_handler = RotatingFileHandler(
            carbon_log_file,
            maxBytes=2 * 1024 * 1024,  # 2 MB
            backupCount=10,  # Keep more history for carbon tracking
            encoding='utf-8'
        )
        carbon_handler.setLevel(logging.INFO)
        carbon_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | user_id=%(user_id)s | %(message)s',
            datefmt=DATE_FORMAT
        )
        carbon_handler.setFormatter(carbon_formatter)
        carbon_logger.addHandler(carbon_handler)
    
    return carbon_logger


def get_security_logger() -> logging.Logger:
    """
    Specialized logger for security events (auth, access).
    Writes to a separate security.log file.
    """
    security_logger = logging.getLogger("ether_stories.security")
    
    if not any(isinstance(h, RotatingFileHandler) and 'security' in str(h.baseFilename) for h in security_logger.handlers):
        security_log_file = LOGS_DIR / "security.log"
        security_handler = RotatingFileHandler(
            security_log_file,
            maxBytes=2 * 1024 * 1024,
            backupCount=10,
            encoding='utf-8'
        )
        security_handler.setLevel(logging.INFO)
        security_handler.setFormatter(logging.Formatter(DETAILED_FORMAT, datefmt=DATE_FORMAT))
        security_logger.addHandler(security_handler)
    
    return security_logger


# =========================
# CONVENIENCE FUNCTIONS
# =========================

def log_story_event(user_id: int, story_id: int, event: str, details: str = ""):
    """Log story-related events."""
    story_logger = get_logger("story")
    story_logger.info(f"[User:{user_id}] [Story:{story_id}] {event} | {details}")


def log_carbon_emission(user_id: int, operation: str, emissions_kg: float, story_id: int = None):
    """Log carbon emission events."""
    carbon_logger = get_carbon_logger()
    story_info = f"story_id={story_id}" if story_id else "no_story"
    # Use LogRecord adapter for extra fields
    carbon_logger.info(
        f"{operation} | emissions={emissions_kg*1000:.4f}g | {story_info}",
        extra={"user_id": user_id}
    )


def log_security_event(event_type: str, user_email: str = None, ip_address: str = None, success: bool = True, details: str = ""):
    """Log security-related events (login, signup, access)."""
    security_logger = get_security_logger()
    status = "SUCCESS" if success else "FAILED"
    user_info = f"user={user_email}" if user_email else "anonymous"
    ip_info = f"ip={ip_address}" if ip_address else ""
    security_logger.info(f"[{event_type}] [{status}] {user_info} | {ip_info} | {details}")


def log_api_request(method: str, path: str, status_code: int, duration_ms: float, user_id: int = None):
    """Log API request metrics."""
    api_logger = get_logger("api")
    user_info = f"user={user_id}" if user_id else "anonymous"
    api_logger.info(f"{method} {path} | {status_code} | {duration_ms:.2f}ms | {user_info}")


def log_agent_action(agent_name: str, action: str, details: str = "", success: bool = True):
    """Log agent actions (manager, writer, moderator, etc.)."""
    agent_logger = get_logger(f"agent.{agent_name}")
    status = "✓" if success else "✗"
    agent_logger.info(f"[{status}] {action} | {details}")


def log_error(message: str, error: Exception = None, context: dict = None):
    """Log error with optional exception and context."""
    error_logger = get_logger("error")
    context_str = ""
    if context:
        context_str = " | " + " | ".join(f"{k}={v}" for k, v in context.items())
    if error:
        error_logger.error(f"{message}: {str(error)}{context_str}", exc_info=True)
    else:
        error_logger.error(f"{message}{context_str}")