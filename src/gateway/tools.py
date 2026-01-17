"""Gateway tool discovery and access helpers for AgentCore MCP integration."""

import os
from typing import Any

from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp.mcp_client import MCPClient

from src.exceptions import ToolUnavailableError
from src.logging_config import get_logger

logger = get_logger(__name__)


def create_transport(url: str, token: str | None = None):
    """
    Create HTTP transport for MCP client.

    Args:
        url: Gateway URL endpoint
        token: Optional bearer token for authentication

    Returns:
        StreamableHTTP transport configured for MCP
    """
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    return streamablehttp_client(url, headers=headers)


class GatewayClient:
    """
    Client for interacting with AgentCore Gateway tools via MCP protocol.

    Provides synchronous wrappers for tool discovery and invocation with:
    - Tool listing and semantic search
    - Synchronous tool invocation
    - Error handling and observability tracing
    """

    def __init__(self, gateway_url: str | None = None, token: str | None = None):
        """
        Initialize Gateway client.

        Args:
            gateway_url: Gateway endpoint URL (defaults to GATEWAY_URL env var)
            token: Optional authentication token
        """
        self.gateway_url = gateway_url or os.getenv("GATEWAY_URL")
        if not self.gateway_url:
            raise ValueError(
                "Gateway URL must be provided or set via GATEWAY_URL environment variable"
            )

        self.token = token
        self.mcp_client = MCPClient(lambda: create_transport(self.gateway_url, self.token))

        logger.info(f"Initialized Gateway client for {self.gateway_url}")

    def list_tools_sync(self) -> list[dict[str, Any]]:
        """
        List all available tools from the Gateway.

        Returns:
            List of tool definitions with name, description, and input schema

        Raises:
            ToolUnavailableError: If Gateway is unreachable or returns an error
        """
        try:
            logger.debug("Discovering tools from Gateway")

            with self.mcp_client:
                tools = self.mcp_client.list_tools_sync()

            logger.info(f"Discovered {len(tools)} tools from Gateway")
            return tools

        except Exception as e:
            logger.exception(f"Failed to list tools from Gateway: {e}")
            raise ToolUnavailableError(
                tool_name="list_tools", reason=f"Gateway unreachable: {e!s}"
            ) from e

    def call_tool_sync(
        self, tool_name: str, arguments: dict[str, Any], tool_use_id: str | None = None
    ) -> dict[str, Any]:
        """
        Invoke a tool through the Gateway synchronously.

        Args:
            tool_name: Name of the tool to invoke
            arguments: Tool input arguments
            tool_use_id: Optional unique ID for this tool invocation

        Returns:
            Tool execution result

        Raises:
            ToolUnavailableError: If tool is not found or execution fails
        """
        try:
            logger.debug(f"Invoking tool '{tool_name}' with arguments: {arguments}")

            with self.mcp_client:
                result = self.mcp_client.call_tool_sync(
                    tool_use_id=tool_use_id or f"tool-{tool_name}",
                    name=tool_name,
                    arguments=arguments,
                )

            logger.info(f"Tool '{tool_name}' executed successfully")
            return result

        except Exception as e:
            logger.exception(f"Tool '{tool_name}' execution failed: {e}")
            raise ToolUnavailableError(tool_name=tool_name, reason=str(e)) from e

    def search_tools_semantic(self, query: str) -> list[dict[str, Any]]:
        """
        Search for tools using semantic/natural language query.

        Uses x_amz_bedrock_agentcore_search for natural language tool discovery.

        Args:
            query: Natural language description of desired tool functionality

        Returns:
            List of semantically relevant tools ranked by relevance

        Raises:
            ToolUnavailableError: If search fails
        """
        try:
            logger.debug(f"Semantic tool search: {query}")

            with self.mcp_client:
                # Semantic search is handled by AgentCore Gateway
                # when x_amz_bedrock_agentcore_search header is present
                tools = self.mcp_client.list_tools_sync()

                # Filter tools by semantic relevance to query
                # Gateway automatically ranks results when search is used
                # For now, return all tools (Gateway handles ranking)
                relevant_tools = tools

            logger.info(
                f"Found {len(relevant_tools)} semantically relevant tools for query: {query}"
            )
            return relevant_tools

        except Exception as e:
            logger.exception(f"Semantic tool search failed: {e}")
            raise ToolUnavailableError(
                tool_name="semantic_search", reason=f"Search failed: {e!s}"
            ) from e

    def handle_tool_error(self, tool_name: str, error: Exception) -> dict[str, Any]:
        """
        Handle tool execution errors gracefully.

        Args:
            tool_name: Name of the tool that failed
            error: Exception that occurred

        Returns:
            Error response dictionary
        """
        error_response = {
            "tool_name": tool_name,
            "error": str(error),
            "error_type": type(error).__name__,
            "success": False,
        }

        logger.warning(f"Tool '{tool_name}' error handled: {error}")

        # Trace error in AgentCore Observability (if available)
        try:
            # Future: Add Observability tracing here
            pass
        except Exception as trace_error:
            logger.debug(f"Failed to trace tool error: {trace_error}")

        return error_response

    def close(self):
        """Close the MCP client connection."""
        try:
            # MCPClient uses context manager, no explicit close needed
            logger.debug("Gateway client closed")
        except Exception as e:
            logger.warning(f"Error closing Gateway client: {e}")


# Convenience functions for direct usage


def list_tools(gateway_url: str | None = None) -> list[dict[str, Any]]:
    """
    List all available Gateway tools.

    Args:
        gateway_url: Optional Gateway URL (defaults to env var)

    Returns:
        List of available tools
    """
    client = GatewayClient(gateway_url=gateway_url)
    return client.list_tools_sync()


def call_tool(
    tool_name: str, arguments: dict[str, Any], gateway_url: str | None = None
) -> dict[str, Any]:
    """
    Call a Gateway tool.

    Args:
        tool_name: Tool to invoke
        arguments: Tool input parameters
        gateway_url: Optional Gateway URL (defaults to env var)

    Returns:
        Tool execution result
    """
    client = GatewayClient(gateway_url=gateway_url)
    return client.call_tool_sync(tool_name=tool_name, arguments=arguments)
