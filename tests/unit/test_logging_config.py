"""Unit tests for logging configuration."""

import logging

from src.logging_config import get_logger, setup_logging


class TestLoggingConfig:
    """Test logging configuration functions."""

    def test_setup_logging_default(self):
        """Should configure logging with default settings."""
        setup_logging()

        # Verify root logger is configured
        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO

    def test_setup_logging_custom_level(self):
        """Should configure logging with custom level."""
        setup_logging(level=logging.DEBUG)

        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    def test_setup_logging_suppresses_noisy_loggers(self):
        """Should suppress boto3/botocore/urllib3 loggers."""
        setup_logging()

        assert logging.getLogger("boto3").level == logging.WARNING
        assert logging.getLogger("botocore").level == logging.WARNING
        assert logging.getLogger("urllib3").level == logging.WARNING

    def test_get_logger_returns_logger(self):
        """Should return a logger instance."""
        logger = get_logger("test.module")

        assert isinstance(logger, logging.Logger)
        assert logger.name == "test.module"
