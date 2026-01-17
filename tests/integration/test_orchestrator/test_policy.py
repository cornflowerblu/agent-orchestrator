"""Integration tests for Policy service.

These tests verify Policy service integration with PolicyEnforcer.
They are marked as integration tests and require AWS credentials.
"""

import pytest

from src.orchestrator.models import PolicyConfig
from src.orchestrator.policy import PolicyEnforcer
from src.exceptions import PolicyViolationError


@pytest.mark.integration
class TestPolicyServiceIntegration:
    """Integration tests for Policy service."""

    def test_policy_enforcer_initialization(self):
        """Test PolicyEnforcer can be initialized (may fail without AWS creds)."""
        config = PolicyConfig(
            agent_name="test-agent",
            max_iterations=100,
        )

        # This test verifies the PolicyEnforcer can be created
        # Actual AWS calls would require credentials
        enforcer = PolicyEnforcer(config=config, region="us-east-1")

        assert enforcer.config == config
        assert enforcer.region == "us-east-1"

    def test_policy_config_generates_valid_cedar(self):
        """Test PolicyConfig generates valid Cedar syntax."""
        config = PolicyConfig(
            agent_name="test-agent",
            max_iterations=100,
        )

        cedar_statement = config.generate_cedar_statement()

        # Verify Cedar syntax elements
        assert "permit(" in cedar_statement
        assert "action ==" in cedar_statement
        assert "when {" in cedar_statement
        assert "context.current_iteration < context.max_iterations" in cedar_statement

    def test_policy_violation_error_attributes(self):
        """Test PolicyViolationError contains correct attributes."""
        try:
            raise PolicyViolationError(
                agent_name="test-agent",
                current_iteration=100,
                max_iterations=100,
                session_id="session-123",
                policy_arn="arn:aws:policy:test",
            )
        except PolicyViolationError as e:
            assert e.agent_name == "test-agent"
            assert e.current_iteration == 100
            assert e.max_iterations == 100
            assert e.session_id == "session-123"
            assert e.policy_arn == "arn:aws:policy:test"
            assert "iteration limit" in str(e).lower()

    def test_cedar_statement_syntax_variations(self):
        """Test Cedar statement generation with different actions."""
        config = PolicyConfig(
            agent_name="test-agent",
            max_iterations=100,
        )

        # Test default action
        default_cedar = config.generate_cedar_statement()
        assert 'action == Action::"iterate"' in default_cedar

        # Test custom action
        custom_cedar = config.generate_cedar_statement(action="custom_action")
        assert 'action == Action::"custom_action"' in custom_cedar

    @pytest.mark.skip(reason="Requires AWS credentials and Policy service setup")
    def test_create_policy_engine_real(self):
        """Test creating real policy engine (requires AWS credentials)."""
        config = PolicyConfig(
            agent_name="integration-test-agent",
            max_iterations=100,
        )

        enforcer = PolicyEnforcer(config=config, region="us-east-1")

        # This would require AWS credentials
        # engine = enforcer._get_or_create_policy_engine()
        # assert engine["policyEngineId"] is not None

        # Placeholder for real integration test
        assert True

    @pytest.mark.skip(reason="Requires AWS credentials and Policy service setup")
    def test_check_iteration_allowed_real(self):
        """Test real policy evaluation (requires AWS credentials)."""
        config = PolicyConfig(
            agent_name="integration-test-agent",
            max_iterations=100,
        )

        enforcer = PolicyEnforcer(config=config, region="us-east-1")

        # This would require AWS credentials and policy setup
        # allowed = enforcer.check_iteration_allowed(
        #     current_iteration=50,
        #     session_id="test-session"
        # )
        # assert allowed is True

        # Placeholder for real integration test
        assert True
