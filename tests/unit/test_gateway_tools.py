"""Unit tests for Gateway tool discovery and access."""

import pytest
from src.gateway.tools import GatewayClient
from src.exceptions import ToolUnavailableError


@pytest.fixture
def gateway_url():
    """Sample Gateway URL for testing."""
    return "https://test-gateway.us-east-1.amazonaws.com/mcp"


class TestGatewayClient:
    """Test GatewayClient functionality."""

    def test_gateway_client_initialization(self, gateway_url):
        """Should initialize Gateway client with URL."""
        client = GatewayClient(gateway_url=gateway_url)

        assert client.gateway_url == gateway_url
        assert client.mcp_client is not None

    def test_gateway_client_requires_url(self):
        """Should raise error if no Gateway URL provided."""
        with pytest.raises(ValueError, match="Gateway URL must be provided"):
            GatewayClient(gateway_url=None)

    def test_list_tools_sync(self, gateway_url):
        """Should list tools from Gateway."""
        # This will be tested with mocking once Gateway is available
        pass

    def test_call_tool_sync(self, gateway_url):
        """Should invoke tools through Gateway."""
        # This will be tested with mocking once Gateway is available
        pass

    def test_search_tools_semantic(self, gateway_url):
        """Should search tools using semantic query."""
        # This will be tested with mocking once Gateway is available
        pass

    def test_handle_tool_error(self, gateway_url):
        """Should handle tool errors gracefully."""
        client = GatewayClient(gateway_url=gateway_url)

        error = Exception("Test error")
        result = client.handle_tool_error("test-tool", error)

        assert result["success"] is False
        assert result["tool_name"] == "test-tool"
        assert "Test error" in result["error"]
