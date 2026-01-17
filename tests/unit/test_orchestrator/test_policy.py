"""Unit tests for PolicyEnforcer.

Tests for policy enforcement logic including Cedar policy creation,
iteration limit checking, and Policy service integration.
"""

from unittest.mock import patch

import pytest

from src.exceptions import PolicyViolationError
from src.orchestrator.models import PolicyConfig
from src.orchestrator.policy import PolicyEnforcer


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
        """Test that policy client is initialized with correct region (lazy init)."""
        config = PolicyConfig(
            agent_name="test-agent",
            max_iterations=100,
        )

        enforcer = PolicyEnforcer(config=config, region="us-west-2")

        # PolicyClient is lazily initialized - not created yet
        mock_policy_client.assert_not_called()

        # Access the property to trigger initialization
        _ = enforcer.policy_client

        # Now it should be initialized with correct region
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

    @patch("src.orchestrator.policy.PolicyClient")
    def test_create_iteration_policy(self, mock_policy_client):
        """Test creating an iteration limit policy."""
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
        mock_client_instance.create_or_get_policy.return_value = {
            "policyId": "policy-456",
            "policyArn": "arn:aws:policy:policy-456",
        }

        enforcer = PolicyEnforcer(config=config)
        policy_arn = enforcer.create_iteration_policy()

        # Verify policy engine was created
        mock_client_instance.create_or_get_policy_engine.assert_called_once()

        # Verify policy was created with Cedar statement
        mock_client_instance.create_or_get_policy.assert_called_once()
        call_kwargs = mock_client_instance.create_or_get_policy.call_args[1]
        assert call_kwargs["policy_engine_id"] == "engine-123"
        assert "iteration_limit" in call_kwargs["name"]
        assert "cedar" in call_kwargs["definition"]

        # Verify Cedar statement in policy
        cedar_def = call_kwargs["definition"]["cedar"]
        assert "permit(" in cedar_def["statement"]
        assert "AgentCore::Action" in cedar_def["statement"]
        assert "AgentCore::Gateway" in cedar_def["statement"]
        assert "current_iteration" in cedar_def["statement"]

        # Verify result
        assert policy_arn == "arn:aws:policy:policy-456"

    @patch("src.orchestrator.policy.PolicyClient")
    def test_create_iteration_policy_with_session_id(self, mock_policy_client):
        """Test creating policy with session ID in name."""
        config = PolicyConfig(
            agent_name="test-agent",
            max_iterations=100,
            session_id="session-abc",
        )

        # Mock responses
        mock_client_instance = mock_policy_client.return_value
        mock_client_instance.create_or_get_policy_engine.return_value = {
            "policyEngineId": "engine-123",
            "policyEngineArn": "arn:aws:policy:engine-123",
        }
        mock_client_instance.create_or_get_policy.return_value = {
            "policyId": "policy-456",
            "policyArn": "arn:aws:policy:policy-456",
        }

        enforcer = PolicyEnforcer(config=config)
        enforcer.create_iteration_policy()

        # Verify policy name includes session ID (sanitized)
        call_kwargs = mock_client_instance.create_or_get_policy.call_args[1]
        assert "session_abc" in call_kwargs["name"]

    def test_check_iteration_allowed_success(self):
        """Test checking if iteration is allowed (within limit)."""
        config = PolicyConfig(
            agent_name="test-agent",
            max_iterations=100,
        )

        enforcer = PolicyEnforcer(config=config)

        # Check iteration well below limit
        result = enforcer.check_iteration_allowed(current_iteration=50, session_id="session-123")

        # Should return True (allowed)
        assert result is True

        # Check iteration at boundary (iteration 99 is allowed for max=100)
        result = enforcer.check_iteration_allowed(current_iteration=99, session_id="session-123")
        assert result is True

    def test_check_iteration_allowed_violation(self):
        """Test checking iteration when limit exceeded."""
        config = PolicyConfig(
            agent_name="test-agent",
            max_iterations=100,
        )

        enforcer = PolicyEnforcer(config=config)

        # Should raise PolicyViolationError at iteration 100 (0-indexed, so this is the 101st)
        with pytest.raises(PolicyViolationError) as exc_info:
            enforcer.check_iteration_allowed(current_iteration=100, session_id="session-123")

        # Verify error details
        error = exc_info.value
        assert error.agent_name == "test-agent"
        assert error.current_iteration == 100
        assert error.max_iterations == 100
        assert error.session_id == "session-123"

    def test_check_iteration_allowed_at_limit(self):
        """Test checking iteration at exact limit."""
        config = PolicyConfig(
            agent_name="test-agent",
            max_iterations=100,
        )

        enforcer = PolicyEnforcer(config=config)

        # iteration 99 is the last allowed (0-indexed)
        result = enforcer.check_iteration_allowed(current_iteration=99, session_id="session-123")
        assert result is True

        # iteration 100 exceeds limit (would be 101st iteration)
        with pytest.raises(PolicyViolationError):
            enforcer.check_iteration_allowed(current_iteration=100, session_id="session-123")

    @patch("src.orchestrator.policy.PolicyClient")
    def test_update_policy(self, mock_policy_client):
        """Test updating an existing policy."""
        config = PolicyConfig(
            agent_name="test-agent",
            max_iterations=100,
        )

        # Mock policy client
        mock_client_instance = mock_policy_client.return_value
        mock_client_instance.create_or_get_policy_engine.return_value = {
            "policyEngineId": "engine-123",
            "policyEngineArn": "arn:aws:policy:engine-123",
        }
        mock_client_instance.update_policy.return_value = {
            "policyId": "policy-456",
            "policyArn": "arn:aws:policy:policy-456",
        }

        enforcer = PolicyEnforcer(config=config)

        # Update policy with new max iterations
        new_config = PolicyConfig(
            agent_name="test-agent",
            max_iterations=200,
        )
        result = enforcer.update_policy(new_config=new_config, policy_id="policy-456")

        # Verify update was called
        mock_client_instance.update_policy.assert_called_once()
        call_kwargs = mock_client_instance.update_policy.call_args[1]
        assert call_kwargs["policy_id"] == "policy-456"
        assert "cedar" in call_kwargs["definition"]

        # Verify result
        assert result == "arn:aws:policy:policy-456"

    @patch("src.orchestrator.policy.PolicyClient")
    def test_get_policy(self, mock_policy_client):
        """Test retrieving an existing policy."""
        config = PolicyConfig(
            agent_name="test-agent",
            max_iterations=100,
        )

        # Mock policy client
        mock_client_instance = mock_policy_client.return_value
        mock_client_instance.get_policy.return_value = {
            "policyId": "policy-456",
            "policyArn": "arn:aws:policy:policy-456",
            "name": "iteration-limit-test-agent",
            "definition": {"cedar": {"statement": "permit(..."}},
        }

        enforcer = PolicyEnforcer(config=config)
        result = enforcer.get_policy(policy_id="policy-456")

        # Verify get_policy was called
        mock_client_instance.get_policy.assert_called_once_with(policy_id="policy-456")

        # Verify result
        assert result["policyId"] == "policy-456"
        assert result["name"] == "iteration-limit-test-agent"


class TestPolicyEnforcerNoneClient:
    """Tests for PolicyEnforcer when policy_client is None."""

    @patch("src.orchestrator.policy.PolicyClient", None)
    def test_get_or_create_policy_engine_raises_when_client_none(self):
        """Test that _get_or_create_policy_engine raises when policy_client is None."""
        config = PolicyConfig(
            agent_name="test-agent",
            max_iterations=100,
        )

        enforcer = PolicyEnforcer(config=config)

        with pytest.raises(PolicyViolationError):
            enforcer._get_or_create_policy_engine()

    @patch("src.orchestrator.policy.PolicyClient", None)
    def test_update_policy_raises_when_client_none(self):
        """Test that update_policy raises when policy_client is None."""
        config = PolicyConfig(
            agent_name="test-agent",
            max_iterations=100,
        )

        enforcer = PolicyEnforcer(config=config)
        new_config = PolicyConfig(agent_name="test-agent", max_iterations=200)

        with pytest.raises(PolicyViolationError):
            enforcer.update_policy(new_config=new_config, policy_id="policy-456")

    @patch("src.orchestrator.policy.PolicyClient", None)
    def test_get_policy_raises_when_client_none(self):
        """Test that get_policy raises when policy_client is None."""
        config = PolicyConfig(
            agent_name="test-agent",
            max_iterations=100,
        )

        enforcer = PolicyEnforcer(config=config)

        with pytest.raises(PolicyViolationError):
            enforcer.get_policy(policy_id="policy-456")
