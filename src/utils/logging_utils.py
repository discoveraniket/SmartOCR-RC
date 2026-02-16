import logging
import sys
import os

def setup_logging(level=logging.INFO):
    """
    Configures the logging system for the entire application.
    Sets up a stream handler for the terminal and ensures all 
    relevant loggers (project and libraries) are at the correct level.
    """
    root_logger = logging.getLogger()
    
    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Base configuration
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', '%H:%M:%S')
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Set levels
    root_logger.setLevel(level)
    logging.getLogger("src").setLevel(level)
    logging.getLogger("ppocr").setLevel(level)
    
    # Suppress some noisy external loggers unless we are in DEBUG
    if level > logging.DEBUG:
        logging.getLogger("PIL").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("matplotlib").setLevel(logging.WARNING)

    logging.info(f"Logging initialized at level: {logging.getLevelName(level)}")
