"""Unit tests for BaseAgent class."""

import pytest
from src.agents.base_agent import BaseAgent
from src.agents.models import AgentCard, Skill
from src.exceptions import DuplicateAgentError


@pytest.fixture
def sample_agent_card():
    """Sample Agent Card for testing."""
    return AgentCard(
        name="test-agent",
        description="A test agent for unit testing",
        version="1.0.0",
        url="https://bedrock-agentcore.us-east-1.amazonaws.com/runtimes/test/invocations/",
        protocol_version="0.3.0",
        preferred_transport="JSONRPC",
        capabilities={"streaming": True},
        default_input_modes=["text"],
        default_output_modes=["text"],
        skills=[
            Skill(
                id="test-skill",
                name="Test Skill",
                description="A skill for testing purposes",
                tags=["test"],
            )
        ],
    )


class TestBaseAgent:
    """Test BaseAgent functionality."""

    def test_create_agent(self, sample_agent_card):
        """Should create agent with valid Agent Card."""
        agent = BaseAgent(agent_card=sample_agent_card)

        assert agent.name == "test-agent"
        assert agent.version == "1.0.0"
        assert len(agent.skills) == 1
        assert agent.skills[0].id == "test-skill"

    def test_agent_card_validation(self):
        """Should validate Agent Card fields during creation."""
        # This will be tested once BaseAgent implements validation
        pass

    def test_load_agent_card_from_json(self, tmp_path):
        """Should load Agent Card from JSON file."""
        # This will be tested once load_from_json is implemented
        pass

    def test_duplicate_agent_detection(self):
        """Should detect duplicate agent names."""
        # This will be tested once deployment logic is implemented
        pass

    def test_version_increment(self, sample_agent_card):
        """Should support version updates."""
        # This will be tested once versioning is implemented
        pass
