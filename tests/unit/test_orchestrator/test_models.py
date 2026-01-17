"""Unit tests for orchestrator models.

Tests for PolicyConfig and related models used in policy enforcement.
"""

import pytest
from pydantic import ValidationError

from src.orchestrator.models import PolicyConfig


class TestPolicyConfig:
    """Tests for PolicyConfig model."""

    def test_create_policy_config_minimal(self):
        """Test creating PolicyConfig with minimal required fields."""
        config = PolicyConfig(
            agent_name="test-agent",
            max_iterations=100,
        )

        assert config.agent_name == "test-agent"
        assert config.max_iterations == 100
        assert config.session_id is None
        assert config.policy_engine_name == "LoopIterationPolicyEngine"
        assert config.policy_name_prefix == "iteration-limit"

    def test_create_policy_config_with_session_id(self):
        """Test creating PolicyConfig with session ID."""
        config = PolicyConfig(
            agent_name="test-agent",
            max_iterations=50,
            session_id="session-123",
        )

        assert config.session_id == "session-123"

    def test_create_policy_config_with_custom_names(self):
        """Test creating PolicyConfig with custom engine and policy names."""
        config = PolicyConfig(
            agent_name="test-agent",
            max_iterations=100,
            policy_engine_name="CustomEngine",
            policy_name_prefix="custom-policy",
        )

        assert config.policy_engine_name == "CustomEngine"
        assert config.policy_name_prefix == "custom-policy"

    def test_max_iterations_validation(self):
        """Test max_iterations validation."""
        # Valid range
        config = PolicyConfig(agent_name="test", max_iterations=1)
        assert config.max_iterations == 1

        config = PolicyConfig(agent_name="test", max_iterations=10000)
        assert config.max_iterations == 10000

        # Invalid: too low
        with pytest.raises(ValidationError) as exc_info:
            PolicyConfig(agent_name="test", max_iterations=0)
        assert "greater than or equal to 1" in str(exc_info.value)

        # Invalid: too high
        with pytest.raises(ValidationError) as exc_info:
            PolicyConfig(agent_name="test", max_iterations=10001)
        assert "less than or equal to 10000" in str(exc_info.value)

    def test_agent_name_validation(self):
        """Test agent_name validation."""
        # Valid names
        PolicyConfig(agent_name="a", max_iterations=100)
        PolicyConfig(agent_name="a" * 64, max_iterations=100)

        # Invalid: empty
        with pytest.raises(ValidationError) as exc_info:
            PolicyConfig(agent_name="", max_iterations=100)
        assert "at least 1 character" in str(exc_info.value)

        # Invalid: too long
        with pytest.raises(ValidationError) as exc_info:
            PolicyConfig(agent_name="a" * 65, max_iterations=100)
        assert "at most 64 characters" in str(exc_info.value)
