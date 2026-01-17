"""Integration tests for Gateway tool access."""

import pytest
from src.gateway.tools import GatewayClient


@pytest.mark.integration
@pytest.mark.skip(reason="Requires deployed AgentCore Gateway")
class TestGatewayIntegration:
    """Integration tests for Gateway (requires AWS setup)."""

    def test_discover_tools_from_gateway(self):
        """Should discover tools from deployed Gateway."""
        # Requires actual Gateway deployment
        # Will be enabled once infrastructure is deployed
        pass

    def test_invoke_tool_via_gateway(self):
        """Should invoke a tool through Gateway."""
        # Requires actual Gateway with registered tools
        # Will be enabled once infrastructure is deployed
        pass

    def test_semantic_search_returns_relevant_tools(self):
        """Should return semantically relevant tools for natural language query."""
        # Requires Gateway with semantic search enabled
        # Will be enabled once infrastructure is deployed
        pass

    def test_tool_unavailable_error_handling(self):
        """Should handle unavailable tools gracefully."""
        # Test error handling when tool doesn't exist
        # Will be enabled once infrastructure is deployed
        pass

    def test_observability_tracing(self):
        """Should trace tool invocations in AgentCore Observability."""
        # Test that tool calls appear in Observability traces
        # Will be enabled once Observability is configured
        pass
