"""Unit tests for PolicyEnforcer.

Tests for policy enforcement logic including Cedar policy creation,
iteration limit checking, and Policy service integration.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch

from src.orchestrator.policy import PolicyEnforcer
from src.orchestrator.models import PolicyConfig
from src.exceptions import PolicyViolationError


class TestPolicyEnforcer:
    """Tests for PolicyEnforcer class."""

    def test_create_policy_enforcer(self):
        """Test creating PolicyEnforcer instance."""
        config = PolicyConfig(
            agent_name="test-agent",
            max_iterations=100,
        )

        enforcer = PolicyEnforcer(config=config, region="us-east-1")

        assert enforcer.config == config
        assert enforcer.region == "us-east-1"
        # policy_client will be initialized in T079

    def test_create_policy_enforcer_default_region(self):
        """Test PolicyEnforcer with default region."""
        config = PolicyConfig(
            agent_name="test-agent",
            max_iterations=100,
        )

        enforcer = PolicyEnforcer(config=config)

        assert enforcer.region == "us-east-1"
