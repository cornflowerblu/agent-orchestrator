"""Base agent class with AgentCore Runtime integration."""

import json
import re
from pathlib import Path
from typing import Any, ClassVar

from bedrock_agentcore import BedrockAgentCoreApp

from src.agents.models import AgentCard
from src.exceptions import DuplicateAgentError, ValidationError
from src.logging_config import get_logger

logger = get_logger(__name__)


class BaseAgent:
    """
    Base class for all agents in the orchestration platform.

    Integrates with AWS Bedrock AgentCore Runtime and provides:
    - Agent Card loading and validation
    - Duplicate name detection
    - Version management
    - Runtime deployment via @app.entrypoint
    """

    # Class-level registry to track deployed agents
    _deployed_agents: ClassVar[dict[str, "BaseAgent"]] = {}

    def __init__(self, agent_card: AgentCard):
        """
        Initialize agent with Agent Card.

        Args:
            agent_card: A2A Agent Card defining agent capabilities

        Raises:
            DuplicateAgentError: If agent with same name already exists
        """
        self.agent_card = agent_card
        self.name = agent_card.name
        self.version = agent_card.version
        self.skills = agent_card.skills

        # Check for duplicate names
        if self.name in self._deployed_agents:
            raise DuplicateAgentError(self.name, self._deployed_agents[self.name].version)

        # Register this agent
        self._deployed_agents[self.name] = self
        logger.info(f"Initialized agent '{self.name}' version {self.version}")

    @classmethod
    def load_from_json(cls, manifest_path: str | Path) -> "BaseAgent":
        """
        Load Agent Card from JSON manifest file.

        Args:
            manifest_path: Path to Agent Card JSON file

        Returns:
            BaseAgent instance with loaded Agent Card

        Raises:
            FileNotFoundError: If manifest file doesn't exist
            ValidationError: If Agent Card JSON is invalid
        """
        manifest_path = Path(manifest_path)

        if not manifest_path.exists():
            raise FileNotFoundError(f"Agent Card manifest not found: {manifest_path}")

        logger.info(f"Loading Agent Card from {manifest_path}")

        with manifest_path.open() as f:
            card_data = json.load(f)

        # Pydantic will validate the structure
        agent_card = AgentCard(**card_data)

        return cls(agent_card=agent_card)

    def to_agent_card_json(self) -> dict[str, Any]:
        """
        Export Agent Card as JSON-serializable dict.

        Returns:
            Agent Card as dictionary (ready for A2A serving)
        """
        return self.agent_card.model_dump(by_alias=True, exclude_none=True)

    def update_version(self, new_version: str) -> None:
        """
        Update agent version (for A2A versioning support).

        Args:
            new_version: New semantic version (X.Y.Z format)

        Raises:
            ValidationError: If version format is invalid
        """
        # Validate version format
        if not re.match(r"^\d+\.\d+\.\d+$", new_version):
            raise ValidationError(f"Invalid version: {new_version}")

        old_version = self.version
        self.version = new_version
        self.agent_card.version = new_version

        logger.info(f"Updated agent '{self.name}' version {old_version} → {new_version}")

    @classmethod
    def get_deployed_agents(cls) -> dict[str, "BaseAgent"]:
        """
        Get all deployed agents.

        Returns:
            Dictionary of agent_name -> BaseAgent instance
        """
        return cls._deployed_agents.copy()

    @classmethod
    def is_agent_deployed(cls, agent_name: str) -> bool:
        """
        Check if an agent is already deployed.

        Args:
            agent_name: Agent name to check

        Returns:
            True if agent is deployed, False otherwise
        """
        return agent_name in cls._deployed_agents


def create_agent_runtime(agent: BaseAgent) -> BedrockAgentCoreApp:
    """
    Create AgentCore Runtime app for agent deployment.

    Args:
        agent: BaseAgent instance to deploy

    Returns:
        BedrockAgentCoreApp configured with agent entrypoint

    Example:
        >>> agent = BaseAgent.load_from_json("manifests/my-agent.json")
        >>> app = create_agent_runtime(agent)
        >>> @app.entrypoint
        >>> async def handle_request(event):
        >>>     # Agent logic here
        >>>     return {"output": "response"}
        >>> app.run()  # Deploy to AgentCore
    """
    app = BedrockAgentCoreApp()

    # Agent Card will be served at /.well-known/agent-card.json by AgentCore
    logger.info(f"Created AgentCore Runtime for agent '{agent.name}' version {agent.version}")

    return app
