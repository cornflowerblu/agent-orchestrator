"""Agent registry query interface.

Task T068: Create AgentRegistry class
Task T069: Implement find_by_skill method
Task T070: Implement find_by_input_compatibility method
Task T071: Implement check_compatibility method
Task T072: Implement get_consultation_requirements method
"""

from typing import Any

from pydantic import BaseModel, Field

from src.agents.models import AgentCard
from src.consultation.rules import ConsultationPhase, ConsultationRequirement
from src.exceptions import AgentNotFoundError
from src.logging_config import get_logger
from src.metadata.models import CustomAgentMetadata, SemanticType
from src.metadata.validation import is_type_compatible

logger = get_logger(__name__)


class CompatibilityResult(BaseModel):
    """Result of checking compatibility between agents."""

    is_compatible: bool = Field(..., description="Whether the agents are compatible")
    source_agent: str = Field(..., description="Source agent name")
    target_agent: str = Field(..., description="Target agent name")
    details: dict[str, Any] = Field(
        default_factory=dict, description="Details about compatibility"
    )


class AgentRegistry:
    """Registry for discovering and querying agent capabilities.

    Provides methods to:
    - Register and retrieve agent cards
    - Find agents by skill
    - Check semantic type compatibility
    - Get consultation requirements

    Task T068: Create AgentRegistry class
    """

    def __init__(
        self,
        metadata_storage: Any | None = None,
        discovery: Any | None = None,
    ):
        """Initialize the agent registry.

        Args:
            metadata_storage: Optional MetadataStorage for custom metadata
            discovery: Optional AgentDiscovery for A2A discovery
        """
        self._agent_cards: dict[str, AgentCard] = {}
        self._metadata_storage = metadata_storage
        self._discovery = discovery

        logger.info("Initialized AgentRegistry")

    def register_agent_card(self, card: AgentCard) -> None:
        """Register an agent card.

        Args:
            card: The AgentCard to register
        """
        self._agent_cards[card.name] = card
        logger.info(f"Registered agent card for '{card.name}'")

    def unregister_agent_card(self, agent_name: str) -> None:
        """Unregister an agent card.

        Args:
            agent_name: Name of the agent to unregister
        """
        if agent_name in self._agent_cards:
            del self._agent_cards[agent_name]
            logger.info(f"Unregistered agent card for '{agent_name}'")

    def get_agent_card(self, agent_name: str) -> AgentCard:
        """Get an agent card by name.

        Args:
            agent_name: Name of the agent

        Returns:
            The agent's AgentCard

        Raises:
            AgentNotFoundError: If the agent is not registered
        """
        if agent_name not in self._agent_cards:
            raise AgentNotFoundError(agent_name)
        return self._agent_cards[agent_name]

    def list_all_agents(self) -> list[AgentCard]:
        """List all registered agent cards.

        Returns:
            List of all registered AgentCards
        """
        return list(self._agent_cards.values())

    def find_by_skill(
        self,
        skill_id: str,
        match_type: str = "exact",
        case_sensitive: bool = True,
    ) -> list[AgentCard]:
        """Find agents that have a specific skill.

        Task T069: Implement find_by_skill method

        Args:
            skill_id: Skill ID or name to search for
            match_type: "exact" for exact match, "partial" for substring match
            case_sensitive: Whether matching is case sensitive

        Returns:
            List of AgentCards that have the matching skill
        """
        results = []
        search_term = skill_id if case_sensitive else skill_id.lower()

        for card in self._agent_cards.values():
            for skill in card.skills:
                skill_identifier = skill.id if case_sensitive else skill.id.lower()
                skill_name = skill.name if case_sensitive else skill.name.lower()

                if match_type == "exact":
                    if skill_identifier == search_term or skill_name == search_term:
                        results.append(card)
                        break
                elif match_type == "partial":
                    if search_term in skill_identifier or search_term in skill_name:
                        results.append(card)
                        break

        logger.debug(f"Found {len(results)} agents with skill '{skill_id}'")
        return results

    def find_by_input_compatibility(
        self,
        semantic_type: SemanticType,
        required_only: bool = False,
    ) -> list[AgentCard]:
        """Find agents compatible with a given input semantic type.

        Task T070: Implement find_by_input_compatibility method

        Args:
            semantic_type: The semantic type to match
            required_only: If True, only match required inputs

        Returns:
            List of AgentCards that accept the given semantic type
        """
        if self._metadata_storage is None:
            logger.warning("No metadata storage configured, cannot check input compatibility")
            return []

        results = []
        all_metadata = self._metadata_storage.list_all_metadata()

        for metadata in all_metadata:
            for input_schema in metadata.input_schemas:
                # Check if the input type is compatible
                if is_type_compatible(semantic_type, input_schema.semantic_type):
                    if required_only and not input_schema.required:
                        continue

                    # Find the corresponding agent card
                    if metadata.agent_name in self._agent_cards:
                        results.append(self._agent_cards[metadata.agent_name])
                        break

        logger.debug(
            f"Found {len(results)} agents compatible with input type '{semantic_type.value}'"
        )
        return results

    def check_compatibility(
        self,
        source_agent: str,
        target_agent: str,
    ) -> CompatibilityResult:
        """Check if output of source agent is compatible with input of target agent.

        Task T071: Implement check_compatibility method

        Args:
            source_agent: Name of the source agent (produces output)
            target_agent: Name of the target agent (consumes input)

        Returns:
            CompatibilityResult with compatibility details

        Raises:
            AgentNotFoundError: If either agent is not found
        """
        if self._metadata_storage is None:
            raise AgentNotFoundError(source_agent)

        try:
            source_metadata = self._metadata_storage.get_metadata(source_agent)
        except Exception:
            raise AgentNotFoundError(source_agent)

        try:
            target_metadata = self._metadata_storage.get_metadata(target_agent)
        except Exception:
            raise AgentNotFoundError(target_agent)

        if source_metadata is None:
            raise AgentNotFoundError(source_agent)
        if target_metadata is None:
            raise AgentNotFoundError(target_agent)

        # Check if any output from source is compatible with any input of target
        compatible_pairs = []
        for output_schema in source_metadata.output_schemas:
            for input_schema in target_metadata.input_schemas:
                if is_type_compatible(output_schema.semantic_type, input_schema.semantic_type):
                    compatible_pairs.append({
                        "output": output_schema.name,
                        "output_type": output_schema.semantic_type.value,
                        "input": input_schema.name,
                        "input_type": input_schema.semantic_type.value,
                    })

        is_compatible = len(compatible_pairs) > 0

        return CompatibilityResult(
            is_compatible=is_compatible,
            source_agent=source_agent,
            target_agent=target_agent,
            details={
                "compatible_pairs": compatible_pairs,
                "source_outputs": [o.name for o in source_metadata.output_schemas],
                "target_inputs": [i.name for i in target_metadata.input_schemas],
            },
        )

    def get_consultation_requirements(
        self,
        agent_name: str,
        phase: ConsultationPhase | None = None,
    ) -> list[ConsultationRequirement]:
        """Get consultation requirements for an agent.

        Task T072: Implement get_consultation_requirements method

        Args:
            agent_name: Name of the agent
            phase: Optional phase to filter requirements

        Returns:
            List of ConsultationRequirements for the agent
        """
        if self._metadata_storage is None:
            logger.warning("No metadata storage configured")
            return []

        requirements = self._metadata_storage.get_consultation_requirements(agent_name)

        if phase is not None:
            requirements = [r for r in requirements if r.phase == phase]

        logger.debug(
            f"Found {len(requirements)} consultation requirements for '{agent_name}'"
        )
        return requirements
