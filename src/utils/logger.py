"""
Centralized logging configuration for the YouTube Comments Analysis System.

Provides setup for three log files:
- app.log: General application logs
- openai_calls.log: All OpenAI API call details
- errors.log: Errors and exceptions only
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Optional


def setup_logging(
    log_dir: str = "logs",
    level: str = "INFO",
    log_format: Optional[str] = None
) -> logging.Logger:
    """
    Sets up logging configuration with multiple handlers.

    Args:
        log_dir: Directory for log files
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Custom log format string

    Returns:
        Configured root logger
    """
    # Create log directory if it doesn't exist
    try:
        os.makedirs(log_dir, exist_ok=True)
    except Exception as e:
        print(f"Failed to create log directory {log_dir}: {e}")
        raise

    # Default format
    if log_format is None:
        log_format = '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s'

    # Create formatter
    formatter = logging.Formatter(log_format)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers to avoid duplicates
    root_logger.handlers = []

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, level.upper()))
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # App log file handler (all logs)
    app_log_path = os.path.join(log_dir, 'app.log')
    app_handler = RotatingFileHandler(
        app_log_path,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=7  # Keep 7 days
    )
    app_handler.setLevel(logging.INFO)
    app_handler.setFormatter(formatter)
    root_logger.addHandler(app_handler)

    # OpenAI calls log file handler
    openai_log_path = os.path.join(log_dir, 'openai_calls.log')
    openai_handler = RotatingFileHandler(
        openai_log_path,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=30  # Keep 30 days
    )
    openai_handler.setLevel(logging.INFO)
    openai_handler.setFormatter(formatter)

    # Create OpenAI logger
    openai_logger = logging.getLogger('openai_calls')
    openai_logger.setLevel(logging.INFO)
    openai_logger.addHandler(openai_handler)
    openai_logger.propagate = False  # Don't propagate to root logger

    # Error log file handler (errors only)
    error_log_path = os.path.join(log_dir, 'errors.log')
    error_handler = RotatingFileHandler(
        error_log_path,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=90  # Keep 90 days
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)

    root_logger.info(f"[Logger] Logging initialized - Level: {level}, Log dir: {log_dir}")

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Returns logger for specific module.

    Args:
        name: Module name (usually __name__)

    Returns:
        Logger instance for the module
    """
    return logging.getLogger(name)


def get_openai_logger() -> logging.Logger:
    """
    Returns the dedicated OpenAI API calls logger.

    Returns:
        OpenAI logger instance
    """
    return logging.getLogger('openai_calls')
