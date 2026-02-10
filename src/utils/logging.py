"""
Centralized Logging Configuration

Provides structured logging with rotation and formatting.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional
from config import Config


def setup_logger(
    name: str,
    log_file: Optional[Path] = None,
    level: Optional[str] = None
) -> logging.Logger:
    """
    Setup a logger with consistent formatting and handlers
    
    Args:
        name: Logger name (usually __name__)
        log_file: Path to log file (uses config default if None)
        level: Log level (uses config default if None)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Set level
    log_level = getattr(logging, (level or Config.LOG_LEVEL).upper())
    logger.setLevel(log_level)
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(levelname)s - %(message)s'
    )
    
    # Console handler (INFO and above)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation (DEBUG and above)
    if log_file or Config.LOG_FILE:
        file_path = log_file or Config.LOG_FILE
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            file_path,
            maxBytes=Config.LOG_MAX_BYTES,
            backupCount=Config.LOG_BACKUP_COUNT
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)
    
    return logger


def log_exception(logger: logging.Logger, exc: Exception, context: str = ""):
    """
    Log an exception with context
    
    Args:
        logger: Logger instance
        exc: Exception to log
        context: Additional context string
    """
    if context:
        logger.error(f"{context}: {type(exc).__name__}: {str(exc)}", exc_info=True)
    else:
        logger.error(f"{type(exc).__name__}: {str(exc)}", exc_info=True)


# Create default application logger
app_logger = setup_logger('receipt_checker')
