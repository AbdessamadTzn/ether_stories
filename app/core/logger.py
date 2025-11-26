import logging
import sys

# Create a custom logger
logger = logging.getLogger("ether_stories")
logger.setLevel(logging.INFO)

# Create handlers (stdout)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

# Create formatters and add it to handlers
formatter = logging.Formatter(
    '%(asctime)s | %(levelname)s | %(module)s:%(funcName)s | %(message)s',
    datefmt='%H:%M:%S'
)
console_handler.setFormatter(formatter)

# Add handlers to the logger if not already present
if not logger.hasHandlers():
    logger.addHandler(console_handler)

def get_logger(name: str):
    """Returns a child logger (e.g. ether_stories.manager)"""
    return logging.getLogger(f"ether_stories.{name}")