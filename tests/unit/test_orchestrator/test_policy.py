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

    @patch("src.orchestrator.policy.PolicyClient")
    def test_policy_client_initialization(self, mock_policy_client):
        """Test that policy client is initialized with correct region."""
        config = PolicyConfig(
            agent_name="test-agent",
            max_iterations=100,
        )

        enforcer = PolicyEnforcer(config=config, region="us-west-2")

        # Verify PolicyClient was initialized with correct region
        mock_policy_client.assert_called_once_with(region_name="us-west-2")
        assert enforcer.policy_client is not None

    @patch("src.orchestrator.policy.PolicyClient")
    def test_get_or_create_policy_engine(self, mock_policy_client):
        """Test getting or creating a policy engine."""
        config = PolicyConfig(
            agent_name="test-agent",
            max_iterations=100,
        )

        # Mock the policy client responses
        mock_client_instance = mock_policy_client.return_value
        mock_client_instance.create_or_get_policy_engine.return_value = {
            "policyEngineId": "engine-123",
            "policyEngineArn": "arn:aws:policy:engine-123",
        }

        enforcer = PolicyEnforcer(config=config)
        result = enforcer._get_or_create_policy_engine()

        # Verify the method was called with correct parameters
        mock_client_instance.create_or_get_policy_engine.assert_called_once()
        call_kwargs = mock_client_instance.create_or_get_policy_engine.call_args[1]
        assert call_kwargs["name"] == "LoopIterationPolicyEngine"

        # Verify result
        assert result["policyEngineId"] == "engine-123"
        assert result["policyEngineArn"] == "arn:aws:policy:engine-123"
