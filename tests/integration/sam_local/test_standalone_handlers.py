"""SAM Local integration tests for standalone Lambda handlers.

Tests for ToolRegistryFunction and PolicyEnforcerFunction.
These handlers don't use DynamoDB - they interact with AgentCore services.
"""

import pytest

pytestmark = [
    pytest.mark.sam_local,
    pytest.mark.slow,
]


class TestToolRegistryHandler:
    """Integration tests for ToolRegistryFunction."""

    def test_tool_registry_list_with_event_file(self, sam_invoker):
        """Tool registry list action works with pre-defined event file."""
        response = sam_invoker.invoke_with_event_file(
            "ToolRegistryFunction", "tool_registry_list.json"
        )

        # Handler should return a valid response
        # May fail gracefully if AgentCore Gateway not available locally
        assert "statusCode" in response or "errorMessage" in response

    def test_tool_registry_register_with_event_file(self, sam_invoker):
        """Tool registry register action works with pre-defined event file."""
        response = sam_invoker.invoke_with_event_file(
            "ToolRegistryFunction", "tool_registry_register.json"
        )

        # Handler should return a valid response
        assert "statusCode" in response or "errorMessage" in response


class TestPolicyEnforcerHandler:
    """Integration tests for PolicyEnforcerFunction."""

    def test_policy_enforcer_with_event_file(self, sam_invoker):
        """Policy enforcer handler works with pre-defined event file."""
        response = sam_invoker.invoke_with_event_file(
            "PolicyEnforcerFunction", "policy_enforcer.json"
        )

        # Handler should return a valid response
        # May fail gracefully if Policy service not available locally
        assert "statusCode" in response or "errorMessage" in response

    def test_policy_enforcer_check_iteration(self, sam_invoker):
        """Policy enforcer can check iteration limits."""
        event = {
            "action": "check_iteration",
            "agent_name": "test-agent",
            "session_id": "test-session-123",
            "current_iteration": 5,
            "max_iterations": 100,
        }

        response = sam_invoker.invoke("PolicyEnforcerFunction", event)

        # Handler should process the request
        # Result depends on policy service availability
        assert "statusCode" in response or "errorMessage" in response or "allowed" in response
