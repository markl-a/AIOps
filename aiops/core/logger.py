"""Logging configuration for AIOps framework."""

import sys
from loguru import logger
from aiops.core.config import get_config


def setup_logger():
    """Setup logger with configuration."""
    config = get_config()

    # Remove default logger
    logger.remove()

    # Add custom logger with configuration
    logger.add(
        sys.stderr,
        level=config.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True,
    )

    # Add file logger
    logger.add(
        "logs/aiops_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="30 days",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    )

    return logger


def get_logger(name: str = __name__):
    """Get logger instance."""
    return logger.bind(name=name)
