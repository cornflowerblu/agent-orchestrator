"""Logging configuration for the agent framework."""

import logging
import sys
from typing import Any

# Configure logging format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: int = logging.INFO, **kwargs: Any) -> None:
    """
    Configure logging for the agent framework.

    Args:
        level: Logging level (default: INFO)
        **kwargs: Additional logging configuration options
    """
    logging.basicConfig(
        level=level,
        format=kwargs.get("format", LOG_FORMAT),
        datefmt=kwargs.get("datefmt", DATE_FORMAT),
        stream=sys.stdout,
        force=True,
    )

    # Set specific logger levels
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
