"""A2A Agent Card discovery module.

Task T065: Implement A2A Agent Card discovery
Task T066: Implement fetch_agent_card from /.well-known/agent-card.json
Task T067: Implement discover_all_agents via A2A protocol
"""

import asyncio
from typing import Any, cast

import httpx
from pydantic import BaseModel, Field

from src.agents.models import AgentCard
from src.logging_config import get_logger

logger = get_logger(__name__)


class DiscoveryError(Exception):
    """Error during agent discovery."""

    def __init__(self, message: str, endpoint: str | None = None):
        self.endpoint = endpoint
        super().__init__(message)


class DiscoveryResult(BaseModel):
    """Result of discovering an agent."""

    endpoint: str = Field(..., description="The agent endpoint URL")
    agent_card: AgentCard | None = Field(default=None, description="The discovered agent card")
    success: bool = Field(..., description="Whether discovery succeeded")
    error: str | None = Field(default=None, description="Error message if failed")


class AgentDiscovery:
    """Discovery service for A2A agent cards.

    Implements agent discovery via the A2A protocol, fetching agent cards
    from the well-known endpoint.

    Task T065: Implement A2A Agent Card discovery
    """

    def __init__(
        self,
        timeout: float = 30.0,
        well_known_path: str = "/.well-known/agent-card.json",
    ):
        """Initialize agent discovery.

        Args:
            timeout: HTTP request timeout in seconds
            well_known_path: Path to the agent card endpoint
        """
        self.timeout = timeout
        self.well_known_path = well_known_path
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def _http_get(self, url: str) -> dict[str, Any]:
        """Perform HTTP GET request and return JSON.

        Args:
            url: URL to fetch

        Returns:
            Parsed JSON response

        Raises:
            httpx.ConnectError: On connection failure
            httpx.TimeoutException: On timeout
            ValueError: On invalid JSON
        """
        client = await self._get_client()
        response = await client.get(url)
        response.raise_for_status()
        return cast(dict[str, Any], response.json())

    async def fetch_agent_card(self, endpoint: str) -> AgentCard:
        """Fetch an agent card from the well-known endpoint.

        Task T066: Implement fetch_agent_card from /.well-known/agent-card.json

        Args:
            endpoint: The base URL of the agent (e.g., https://agent.example.com)

        Returns:
            The agent's AgentCard

        Raises:
            DiscoveryError: If the agent card cannot be fetched
        """
        # Normalize endpoint URL
        endpoint = endpoint.rstrip("/")
        url = f"{endpoint}{self.well_known_path}"

        logger.debug(f"Fetching agent card from {url}")

        try:
            data = await self._http_get(url)
        except httpx.ConnectError as e:
            logger.warning(f"Connection error fetching agent card from {endpoint}: {e}")
            raise DiscoveryError(f"Connection refused: {e}", endpoint=endpoint) from e

        except httpx.TimeoutException as e:
            logger.warning(f"Timeout fetching agent card from {endpoint}: {e}")
            raise DiscoveryError(f"Request timed out: {e}", endpoint=endpoint) from e

        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP error fetching agent card from {endpoint}: {e}")
            raise DiscoveryError(f"HTTP error: {e.response.status_code}", endpoint=endpoint) from e

        except ValueError as e:
            logger.warning(f"Invalid JSON from {endpoint}: {e}")
            raise DiscoveryError(f"Invalid JSON response: {e}", endpoint=endpoint) from e

        # Parse and validate the agent card
        try:
            card = AgentCard(**data)
        except Exception as e:
            # Pydantic validation or other parsing errors
            logger.exception(f"Agent card validation failed for {endpoint}")
            raise DiscoveryError(f"Invalid agent card format: {e}", endpoint=endpoint) from e

        logger.info(f"Discovered agent '{card.name}' at {endpoint}")
        return card

    async def discover_all_agents(
        self,
        endpoints: list[str],
        max_concurrent: int = 10,
    ) -> list[DiscoveryResult]:
        """Discover agents from multiple endpoints concurrently.

        Task T067: Implement discover_all_agents via A2A protocol

        Args:
            endpoints: List of agent base URLs to discover
            max_concurrent: Maximum concurrent discovery requests

        Returns:
            List of DiscoveryResult for each endpoint
        """
        if not endpoints:
            return []

        logger.info(f"Discovering {len(endpoints)} agents with max concurrency {max_concurrent}")

        semaphore = asyncio.Semaphore(max_concurrent)

        async def discover_one(endpoint: str) -> DiscoveryResult:
            async with semaphore:
                try:
                    card = await self.fetch_agent_card(endpoint)
                    return DiscoveryResult(
                        endpoint=endpoint,
                        agent_card=card,
                        success=True,
                    )
                except DiscoveryError as e:
                    return DiscoveryResult(
                        endpoint=endpoint,
                        success=False,
                        error=str(e),
                    )

        tasks = [discover_one(ep) for ep in endpoints]
        results = await asyncio.gather(*tasks)

        successful = sum(1 for r in results if r.success)
        logger.info(f"Discovered {successful}/{len(endpoints)} agents successfully")

        return list(results)

    def fetch_agent_card_sync(self, endpoint: str) -> AgentCard:
        """Synchronous wrapper for fetch_agent_card.

        Args:
            endpoint: The base URL of the agent

        Returns:
            The agent's AgentCard
        """
        return asyncio.run(self.fetch_agent_card(endpoint))

    def discover_all_agents_sync(
        self,
        endpoints: list[str],
        max_concurrent: int = 10,
    ) -> list[DiscoveryResult]:
        """Synchronous wrapper for discover_all_agents.

        Args:
            endpoints: List of agent base URLs to discover
            max_concurrent: Maximum concurrent discovery requests

        Returns:
            List of DiscoveryResult for each endpoint
        """
        return asyncio.run(self.discover_all_agents(endpoints, max_concurrent))

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
