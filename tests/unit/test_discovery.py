"""Unit tests for A2A agent discovery.

Task T062: Unit test for agent discovery in tests/unit/test_discovery.py
"""

from unittest.mock import patch

import httpx
import pytest

from src.agents.models import AgentCard
from src.registry.discovery import (
    AgentDiscovery,
    DiscoveryError,
    DiscoveryResult,
)


@pytest.fixture
def sample_agent_card_data():
    """Sample agent card JSON data."""
    return {
        "name": "test-agent",
        "description": "A test agent for testing purposes",
        "version": "1.0.0",
        "url": "https://agent.example.com/invoke",
        "capabilities": {"streaming": True},
        "skills": [
            {
                "id": "test-skill",
                "name": "Test Skill",
                "description": "A test skill for testing purposes",
            }
        ],
        "defaultInputModes": ["text"],
        "defaultOutputModes": ["text"]
    }


@pytest.fixture
def discovery():
    """Create an AgentDiscovery instance."""
    return AgentDiscovery()


class TestAgentDiscovery:
    """Tests for AgentDiscovery class initialization."""

    def test_discovery_init_default(self):
        """Test default initialization."""
        discovery = AgentDiscovery()
        assert discovery.timeout == 30.0
        assert discovery.well_known_path == "/.well-known/agent-card.json"

    def test_discovery_init_custom_timeout(self):
        """Test initialization with custom timeout."""
        discovery = AgentDiscovery(timeout=60.0)
        assert discovery.timeout == 60.0

    def test_discovery_init_custom_path(self):
        """Test initialization with custom well-known path."""
        discovery = AgentDiscovery(well_known_path="/custom/agent.json")
        assert discovery.well_known_path == "/custom/agent.json"


class TestFetchAgentCard:
    """Tests for fetch_agent_card method (T066)."""

    @pytest.mark.asyncio
    async def test_fetch_agent_card_success(self, discovery, sample_agent_card_data):
        """Test successful agent card fetch."""
        with patch.object(discovery, '_http_get') as mock_get:
            mock_get.return_value = sample_agent_card_data

            result = await discovery.fetch_agent_card("https://agent.example.com")

            assert result.name == "test-agent"
            assert result.version == "1.0.0"
            assert len(result.skills) == 1
            mock_get.assert_called_once_with(
                "https://agent.example.com/.well-known/agent-card.json"
            )

    @pytest.mark.asyncio
    async def test_fetch_agent_card_with_trailing_slash(self, discovery, sample_agent_card_data):
        """Test fetch handles URL with trailing slash."""
        with patch.object(discovery, '_http_get') as mock_get:
            mock_get.return_value = sample_agent_card_data

            await discovery.fetch_agent_card("https://agent.example.com/")

            mock_get.assert_called_once_with(
                "https://agent.example.com/.well-known/agent-card.json"
            )

    @pytest.mark.asyncio
    async def test_fetch_agent_card_connection_error(self, discovery):
        """Test handling of connection errors."""
        with patch.object(discovery, '_http_get') as mock_get:
            mock_get.side_effect = httpx.ConnectError("Connection refused")

            with pytest.raises(DiscoveryError) as exc_info:
                await discovery.fetch_agent_card("https://unreachable.example.com")

            assert "Connection refused" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_fetch_agent_card_timeout(self, discovery):
        """Test handling of timeout errors."""
        with patch.object(discovery, '_http_get') as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Request timed out")

            with pytest.raises(DiscoveryError) as exc_info:
                await discovery.fetch_agent_card("https://slow.example.com")

            assert "timed out" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_fetch_agent_card_invalid_json(self, discovery):
        """Test handling of invalid JSON response."""
        with patch.object(discovery, '_http_get') as mock_get:
            mock_get.side_effect = ValueError("Invalid JSON")

            with pytest.raises(DiscoveryError) as exc_info:
                await discovery.fetch_agent_card("https://invalid.example.com")

            assert "Invalid" in str(exc_info.value)


class TestDiscoverAllAgents:
    """Tests for discover_all_agents method (T067)."""

    @pytest.mark.asyncio
    async def test_discover_all_agents_success(self, discovery, sample_agent_card_data):
        """Test discovering multiple agents successfully."""
        endpoints = [
            "https://agent1.example.com",
            "https://agent2.example.com",
        ]

        with patch.object(discovery, 'fetch_agent_card') as mock_fetch:
            # Create different cards for each agent
            card1 = AgentCard(**sample_agent_card_data)
            card2_data = sample_agent_card_data.copy()
            card2_data["name"] = "agent-2"
            card2 = AgentCard(**card2_data)

            mock_fetch.side_effect = [card1, card2]

            results = await discovery.discover_all_agents(endpoints)

            assert len(results) == 2
            assert results[0].agent_card.name == "test-agent"
            assert results[1].agent_card.name == "agent-2"
            assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_discover_all_agents_partial_failure(self, discovery, sample_agent_card_data):
        """Test discovery continues when some agents fail."""
        endpoints = [
            "https://good.example.com",
            "https://bad.example.com",
        ]

        with patch.object(discovery, 'fetch_agent_card') as mock_fetch:
            card = AgentCard(**sample_agent_card_data)
            mock_fetch.side_effect = [
                card,
                DiscoveryError("Connection refused")
            ]

            results = await discovery.discover_all_agents(endpoints)

            assert len(results) == 2
            assert results[0].success is True
            assert results[0].agent_card is not None
            assert results[1].success is False
            assert results[1].error is not None

    @pytest.mark.asyncio
    async def test_discover_all_agents_empty_list(self, discovery):
        """Test discovery with empty endpoint list."""
        results = await discovery.discover_all_agents([])
        assert results == []

    @pytest.mark.asyncio
    async def test_discover_all_agents_concurrent(self, discovery, sample_agent_card_data):
        """Test that discovery fetches agents concurrently."""
        endpoints = [f"https://agent{i}.example.com" for i in range(5)]

        with patch.object(discovery, 'fetch_agent_card') as mock_fetch:
            card = AgentCard(**sample_agent_card_data)
            mock_fetch.return_value = card

            results = await discovery.discover_all_agents(endpoints, max_concurrent=3)

            assert len(results) == 5
            assert mock_fetch.call_count == 5


class TestDiscoveryResult:
    """Tests for DiscoveryResult model."""

    def test_discovery_result_success(self, sample_agent_card_data):
        """Test successful discovery result."""
        card = AgentCard(**sample_agent_card_data)
        result = DiscoveryResult(
            endpoint="https://agent.example.com",
            agent_card=card,
            success=True
        )

        assert result.success is True
        assert result.agent_card is not None
        assert result.error is None
        assert result.endpoint == "https://agent.example.com"

    def test_discovery_result_failure(self):
        """Test failed discovery result."""
        result = DiscoveryResult(
            endpoint="https://failed.example.com",
            success=False,
            error="Connection refused"
        )

        assert result.success is False
        assert result.agent_card is None
        assert result.error == "Connection refused"


class TestDiscoveryError:
    """Tests for DiscoveryError exception."""

    def test_discovery_error_message(self):
        """Test error message format."""
        error = DiscoveryError("Agent not reachable", endpoint="https://example.com")
        assert "Agent not reachable" in str(error)
        assert error.endpoint == "https://example.com"

    def test_discovery_error_without_endpoint(self):
        """Test error without endpoint."""
        error = DiscoveryError("General error")
        assert error.endpoint is None


class TestSyncMethods:
    """Tests for synchronous wrapper methods."""

    def test_fetch_agent_card_sync(self, discovery, sample_agent_card_data):
        """Test synchronous fetch_agent_card_sync method."""
        with patch.object(discovery, 'fetch_agent_card') as mock_fetch:
            card = AgentCard(**sample_agent_card_data)
            # Create a coroutine that returns the card
            async def mock_coro(*args):
                return card
            mock_fetch.return_value = mock_coro()

            # Use the sync method
            with patch('asyncio.run') as mock_run:
                mock_run.return_value = card
                result = discovery.fetch_agent_card_sync("https://example.com")
                assert result.name == "test-agent"

    def test_discover_all_agents_sync(self, discovery, sample_agent_card_data):
        """Test synchronous discover_all_agents_sync method."""
        with patch('asyncio.run') as mock_run:
            card = AgentCard(**sample_agent_card_data)
            results = [
                DiscoveryResult(endpoint="https://example.com", agent_card=card, success=True)
            ]
            mock_run.return_value = results

            result = discovery.discover_all_agents_sync(["https://example.com"])
            assert len(result) == 1
