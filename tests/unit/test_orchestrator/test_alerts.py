"""Unit tests for AlertManager.

Tests for iteration warning alerts when approaching the iteration limit.
"""

import pytest
from unittest.mock import Mock, patch

from src.orchestrator.alerts import AlertManager


class TestAlertManager:
    """Tests for AlertManager class."""

    def test_create_alert_manager(self):
        """Test creating AlertManager instance."""
        manager = AlertManager(agent_name="test-agent", region="us-east-1")

        assert manager.agent_name == "test-agent"
        assert manager.region == "us-east-1"

    def test_create_alert_manager_default_region(self):
        """Test AlertManager with default region."""
        manager = AlertManager(agent_name="test-agent")

        assert manager.region == "us-east-1"

    def test_send_warning_at_threshold(self):
        """Test sending warning when approaching iteration limit."""
        manager = AlertManager(agent_name="test-agent")

        # Send warning at 80% threshold
        result = manager.send_warning(
            current_iteration=80,
            max_iterations=100,
            threshold=0.8,
            session_id="session-123",
        )

        # Should return True indicating warning was sent
        assert result is True

    def test_send_warning_below_threshold(self):
        """Test that no warning is sent below threshold."""
        manager = AlertManager(agent_name="test-agent")

        # Below 80% threshold
        result = manager.send_warning(
            current_iteration=70,
            max_iterations=100,
            threshold=0.8,
            session_id="session-123",
        )

        # Should return False indicating no warning needed
        assert result is False

    def test_send_warning_above_threshold(self):
        """Test sending warning above threshold."""
        manager = AlertManager(agent_name="test-agent")

        # Above 80% threshold
        result = manager.send_warning(
            current_iteration=90,
            max_iterations=100,
            threshold=0.8,
            session_id="session-123",
        )

        # Should return True
        assert result is True

    def test_send_warning_custom_threshold(self):
        """Test sending warning with custom threshold."""
        manager = AlertManager(agent_name="test-agent")

        # At 90% threshold
        result = manager.send_warning(
            current_iteration=90,
            max_iterations=100,
            threshold=0.9,
            session_id="session-123",
        )

        # Should return True
        assert result is True

        # Below 90% threshold
        result = manager.send_warning(
            current_iteration=85,
            max_iterations=100,
            threshold=0.9,
            session_id="session-123",
        )

        # Should return False
        assert result is False
