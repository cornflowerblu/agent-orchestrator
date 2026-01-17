"""Unit tests for Gateway tool discovery and access."""

from unittest.mock import MagicMock, patch

import pytest

from src.exceptions import ToolUnavailableError
from src.gateway.tools import GatewayClient, call_tool, create_transport, list_tools


@pytest.fixture
def gateway_url():
    """Sample Gateway URL for testing."""
    return "https://test-gateway.us-east-1.amazonaws.com/mcp"


@pytest.fixture
def mock_mcp_client():
    """Create a mock MCP client."""
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    return mock


class TestCreateTransport:
    """Test transport creation."""

    @patch("src.gateway.tools.streamablehttp_client")
    def test_create_transport_without_token(self, mock_streamable):
        """Should create transport without auth header."""
        create_transport("https://example.com/mcp")

        mock_streamable.assert_called_once_with("https://example.com/mcp", headers={})

    @patch("src.gateway.tools.streamablehttp_client")
    def test_create_transport_with_token(self, mock_streamable):
        """Should create transport with auth header when token provided."""
        create_transport("https://example.com/mcp", token="my-token")

        mock_streamable.assert_called_once_with(
            "https://example.com/mcp", headers={"Authorization": "Bearer my-token"}
        )


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

    @patch("src.gateway.tools.MCPClient")
    def test_list_tools_sync_success(self, mock_mcp_class, gateway_url):
        """Should list tools from Gateway."""
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.list_tools_sync.return_value = [
            {"name": "tool1", "description": "Test tool"},
            {"name": "tool2", "description": "Another tool"},
        ]
        mock_mcp_class.return_value = mock_client

        client = GatewayClient(gateway_url=gateway_url)
        tools = client.list_tools_sync()

        assert len(tools) == 2
        assert tools[0]["name"] == "tool1"
        mock_client.list_tools_sync.assert_called_once()

    @patch("src.gateway.tools.MCPClient")
    def test_list_tools_sync_error(self, mock_mcp_class, gateway_url):
        """Should raise ToolUnavailableError on failure."""
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.list_tools_sync.side_effect = Exception("Connection failed")
        mock_mcp_class.return_value = mock_client

        client = GatewayClient(gateway_url=gateway_url)

        with pytest.raises(ToolUnavailableError) as exc_info:
            client.list_tools_sync()

        assert "Gateway unreachable" in str(exc_info.value)

    @patch("src.gateway.tools.MCPClient")
    def test_call_tool_sync_success(self, mock_mcp_class, gateway_url):
        """Should invoke tools through Gateway."""
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.call_tool_sync.return_value = {"result": "success"}
        mock_mcp_class.return_value = mock_client

        client = GatewayClient(gateway_url=gateway_url)
        result = client.call_tool_sync("my-tool", {"arg": "value"})

        assert result["result"] == "success"
        mock_client.call_tool_sync.assert_called_once()

    @patch("src.gateway.tools.MCPClient")
    def test_call_tool_sync_with_tool_use_id(self, mock_mcp_class, gateway_url):
        """Should pass tool_use_id to MCP client."""
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.call_tool_sync.return_value = {"result": "success"}
        mock_mcp_class.return_value = mock_client

        client = GatewayClient(gateway_url=gateway_url)
        client.call_tool_sync("my-tool", {"arg": "value"}, tool_use_id="custom-id")

        mock_client.call_tool_sync.assert_called_once_with(
            tool_use_id="custom-id", name="my-tool", arguments={"arg": "value"}
        )

    @patch("src.gateway.tools.MCPClient")
    def test_call_tool_sync_error(self, mock_mcp_class, gateway_url):
        """Should raise ToolUnavailableError on tool failure."""
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.call_tool_sync.side_effect = Exception("Tool failed")
        mock_mcp_class.return_value = mock_client

        client = GatewayClient(gateway_url=gateway_url)

        with pytest.raises(ToolUnavailableError) as exc_info:
            client.call_tool_sync("failing-tool", {})

        assert exc_info.value.tool_name == "failing-tool"

    @patch("src.gateway.tools.MCPClient")
    def test_search_tools_semantic_success(self, mock_mcp_class, gateway_url):
        """Should search tools using semantic query."""
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.list_tools_sync.return_value = [
            {"name": "calculator", "description": "Math operations"},
        ]
        mock_mcp_class.return_value = mock_client

        client = GatewayClient(gateway_url=gateway_url)
        tools = client.search_tools_semantic("math calculation")

        assert len(tools) == 1
        assert tools[0]["name"] == "calculator"

    @patch("src.gateway.tools.MCPClient")
    def test_search_tools_semantic_error(self, mock_mcp_class, gateway_url):
        """Should raise ToolUnavailableError on search failure."""
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.list_tools_sync.side_effect = Exception("Search failed")
        mock_mcp_class.return_value = mock_client

        client = GatewayClient(gateway_url=gateway_url)

        with pytest.raises(ToolUnavailableError) as exc_info:
            client.search_tools_semantic("find tools")

        assert "Search failed" in str(exc_info.value)

    def test_handle_tool_error(self, gateway_url):
        """Should handle tool errors gracefully."""
        client = GatewayClient(gateway_url=gateway_url)

        error = Exception("Test error")
        result = client.handle_tool_error("test-tool", error)

        assert result["success"] is False
        assert result["tool_name"] == "test-tool"
        assert "Test error" in result["error"]
        assert result["error_type"] == "Exception"

    def test_close(self, gateway_url):
        """Should close client without error."""
        client = GatewayClient(gateway_url=gateway_url)
        client.close()  # Should not raise


class TestConvenienceFunctions:
    """Test module-level convenience functions."""

    @patch("src.gateway.tools.GatewayClient")
    def test_list_tools(self, mock_client_class):
        """Should create client and list tools."""
        mock_instance = MagicMock()
        mock_instance.list_tools_sync.return_value = [{"name": "tool1"}]
        mock_client_class.return_value = mock_instance

        result = list_tools(gateway_url="https://example.com")

        assert result == [{"name": "tool1"}]
        mock_client_class.assert_called_once_with(gateway_url="https://example.com")

    @patch("src.gateway.tools.GatewayClient")
    def test_call_tool(self, mock_client_class):
        """Should create client and call tool."""
        mock_instance = MagicMock()
        mock_instance.call_tool_sync.return_value = {"result": "done"}
        mock_client_class.return_value = mock_instance

        result = call_tool("my-tool", {"arg": "val"}, gateway_url="https://example.com")

        assert result == {"result": "done"}
        mock_instance.call_tool_sync.assert_called_once_with(
            tool_name="my-tool", arguments={"arg": "val"}
        )
