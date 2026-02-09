import logging
import sys
import os
from app.config import settings

def setup_logging():
    """Configure logging for the application"""
    
    # Set log level based on environment
    log_level = logging.INFO
    if os.getenv("ENVIRONMENT") == "development":
        log_level = logging.DEBUG
        
    # Create logger
    logger = logging.getLogger("pims_enrichment")
    logger.setLevel(log_level)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)
    
    # Add handler to logger
    if not logger.handlers:
        logger.addHandler(console_handler)
        
    # Configure root logger as well
    logging.getLogger().setLevel(log_level)
    
    return logger

logger = setup_logging()
