import logging
import sys
import os

# Configure logging
def setup_logging():
    # Create a custom logger
    logger = logging.getLogger("findora_ai")
    
    # Set the default log level
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, log_level, logging.INFO))

    # Create formatters
    # [2026-01-10 18:55:00] [INFO] [main.py:123] - Message
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s] [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console Handler (STDOUT)
    # This is critical for Docker containers to capture logs
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File Handler (Optional, logs to a file in the app directory)
    # Using a path that is likely to be mapped in Docker
    log_path = "app.log"
    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

# Initialize the logger
logger = setup_logging()
