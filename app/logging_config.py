"""
Central logging configuration for the application.

This module sets up logging to output both to the console (stdout) and to a file.
The log file is stored in the portable data directory.
"""
import logging
import sys
from pathlib import Path
from app.portable_data import get_data_manager

def setup_logging():
    """Configure logging to file and console."""
    
    # Get log file path from portable data manager
    try:
        log_file = get_data_manager().get_log_file_path()
        # Ensure directory exists
        log_file.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"Failed to determine log file path: {e}")
        return

    # Create root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG) # Catch everything

    # Clear existing handlers to avoid duplicates on reload
    if logger.hasHandlers():
        logger.handlers.clear()

    # Formatter for logs
    # Format: [TIME] [LEVEL] [MODULE] - MESSAGE
    file_formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console formatter can be simpler
    console_formatter = logging.Formatter(
        '[%(levelname)s] %(message)s'
    )

    # 1. File Handler (Overwrites each run 'w')
    try:
        file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Failed to setup file logging: {e}")

    # 2. Console Handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO) # Console sees INFO and up (less noise)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    logging.info(f"Logging initialized. Log file: {log_file}")
