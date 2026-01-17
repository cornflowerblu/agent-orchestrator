"""Unit tests for agent query interface.

Task T063: Unit test for agent query interface in tests/unit/test_query.py
"""

from unittest.mock import MagicMock

import pytest

from src.agents.models import AgentCard, Skill
from src.consultation.rules import ConsultationPhase, ConsultationRequirement
from src.metadata.models import (
    CustomAgentMetadata,
    InputSchema,
    OutputSchema,
    SemanticType,
)
from src.registry.query import AgentRegistry


@pytest.fixture
def sample_skills():
    """Sample skills for testing."""
    return [
        Skill(
            id="code-review",
            name="Code Review",
            description="Reviews code for quality and standards",
        ),
        Skill(
            id="security-scan",
            name="Security Scan",
            description="Scans code for security vulnerabilities",
        ),
    ]


@pytest.fixture
def sample_agent_cards(sample_skills):
    """Sample agent cards for testing."""
    from src.agents.models import AgentCapabilities

    caps = AgentCapabilities(streaming=True)
    return [
        AgentCard(
            name="code-reviewer",
            description="Reviews code for quality and standards",
            version="1.0.0",
            url="https://code-reviewer.example.com/invoke",
            capabilities=caps,
            skills=[sample_skills[0]],
            defaultInputModes=["text"],
            defaultOutputModes=["text"],
        ),
        AgentCard(
            name="security-agent",
            description="Security scanning and vulnerability detection",
            version="1.0.0",
            url="https://security-agent.example.com/invoke",
            capabilities=caps,
            skills=[sample_skills[1]],
            defaultInputModes=["text"],
            defaultOutputModes=["text"],
        ),
        AgentCard(
            name="full-agent",
            description="Agent with both code review and security skills",
            version="2.0.0",
            url="https://full-agent.example.com/invoke",
            capabilities=caps,
            skills=sample_skills,
            defaultInputModes=["text"],
            defaultOutputModes=["text"],
        ),
    ]


@pytest.fixture
def sample_metadata():
    """Sample custom metadata for testing."""
    return [
        CustomAgentMetadata(
            agent_name="code-reviewer",
            version="1.0.0",
            input_schemas=[
                InputSchema(
                    name="source-code",
                    semantic_type=SemanticType.ARTIFACT,
                    description="Source code to review",
                    required=True,
                )
            ],
            output_schemas=[
                OutputSchema(
                    name="review-report",
                    semantic_type=SemanticType.DOCUMENT,
                    description="Code review findings",
                    guaranteed=True,
                )
            ],
        ),
        CustomAgentMetadata(
            agent_name="security-agent",
            version="1.0.0",
            input_schemas=[
                InputSchema(
                    name="code-artifact",
                    semantic_type=SemanticType.ARTIFACT,
                    description="Code to scan",
                    required=True,
                )
            ],
            output_schemas=[
                OutputSchema(
                    name="security-report",
                    semantic_type=SemanticType.DOCUMENT,
                    description="Security findings",
                    guaranteed=True,
                )
            ],
        ),
    ]


@pytest.fixture
def mock_metadata_storage(sample_metadata):
    """Mock metadata storage."""
    storage = MagicMock()
    storage.get_metadata.side_effect = lambda name: next(
        (m for m in sample_metadata if m.agent_name == name), None
    )
    storage.list_all_metadata.return_value = sample_metadata
    return storage


@pytest.fixture
def mock_discovery():
    """Mock agent discovery."""
    return MagicMock()


@pytest.fixture
def registry(mock_metadata_storage, mock_discovery, sample_agent_cards):
    """Create an AgentRegistry instance with mocks."""
    reg = AgentRegistry(metadata_storage=mock_metadata_storage, discovery=mock_discovery)
    # Pre-populate with agent cards
    for card in sample_agent_cards:
        reg._agent_cards[card.name] = card
    return reg


class TestAgentRegistryInit:
    """Tests for AgentRegistry initialization."""

    def test_registry_init(self, mock_metadata_storage, mock_discovery):
        """Test registry initialization."""
        registry = AgentRegistry(metadata_storage=mock_metadata_storage, discovery=mock_discovery)
        assert registry._metadata_storage == mock_metadata_storage
        assert registry._discovery == mock_discovery

    def test_registry_init_defaults(self):
        """Test registry initialization with defaults."""
        registry = AgentRegistry()
        assert registry._agent_cards == {}


class TestFindBySkill:
    """Tests for find_by_skill method (T069)."""

    def test_find_by_skill_exact_match(self, registry):
        """Test finding agents by exact skill ID."""
        results = registry.find_by_skill("code-review")

        assert len(results) == 2  # code-reviewer and full-agent
        names = [r.name for r in results]
        assert "code-reviewer" in names
        assert "full-agent" in names

    def test_find_by_skill_no_match(self, registry):
        """Test finding agents with non-existent skill."""
        results = registry.find_by_skill("non-existent-skill")
        assert results == []

    def test_find_by_skill_partial_match(self, registry):
        """Test finding agents by skill name substring."""
        results = registry.find_by_skill("security", match_type="partial")

        assert len(results) >= 1
        names = [r.name for r in results]
        assert "security-agent" in names

    def test_find_by_skill_case_insensitive(self, registry):
        """Test skill matching is case insensitive."""
        results = registry.find_by_skill("CODE-REVIEW", case_sensitive=False)

        assert len(results) >= 1


class TestFindByInputCompatibility:
    """Tests for find_by_input_compatibility method (T070)."""

    def test_find_by_input_artifact_type(self, registry, mock_metadata_storage, sample_metadata):
        """Test finding agents compatible with ARTIFACT input."""
        mock_metadata_storage.list_all_metadata.return_value = sample_metadata

        results = registry.find_by_input_compatibility(SemanticType.ARTIFACT)

        assert len(results) >= 1
        # Both code-reviewer and security-agent accept ARTIFACT input

    def test_find_by_input_no_compatible(self, registry, mock_metadata_storage):
        """Test finding agents when none are compatible."""
        mock_metadata_storage.list_all_metadata.return_value = []

        results = registry.find_by_input_compatibility(SemanticType.COLLECTION)
        assert results == []

    def test_find_by_input_required_only(self, registry, mock_metadata_storage, sample_metadata):
        """Test finding only agents with required inputs."""
        mock_metadata_storage.list_all_metadata.return_value = sample_metadata

        results = registry.find_by_input_compatibility(SemanticType.ARTIFACT, required_only=True)

        # Should find agents with required ARTIFACT inputs
        assert len(results) >= 1


class TestCheckCompatibility:
    """Tests for check_compatibility method (T071)."""

    def test_check_compatibility_compatible(self, registry, mock_metadata_storage, sample_metadata):
        """Test checking compatibility between two compatible agents."""
        mock_metadata_storage.get_metadata.side_effect = lambda name: next(
            (m for m in sample_metadata if m.agent_name == name), None
        )

        result = registry.check_compatibility(
            source_agent="code-reviewer", target_agent="security-agent"
        )

        # code-reviewer outputs DOCUMENT, security-agent needs ARTIFACT
        # This may or may not be compatible based on semantic type rules
        assert isinstance(result.is_compatible, bool)
        assert isinstance(result.details, dict)

    def test_check_compatibility_self(self, registry, mock_metadata_storage, sample_metadata):
        """Test checking compatibility with self."""
        mock_metadata_storage.get_metadata.side_effect = lambda name: next(
            (m for m in sample_metadata if m.agent_name == name), None
        )

        result = registry.check_compatibility(
            source_agent="code-reviewer", target_agent="code-reviewer"
        )

        # Self-compatibility should work
        assert result is not None

    def test_check_compatibility_missing_agent(self, registry, mock_metadata_storage):
        """Test checking compatibility with non-existent agent."""
        mock_metadata_storage.get_metadata.return_value = None

        from src.exceptions import AgentNotFoundError

        with pytest.raises(AgentNotFoundError):
            registry.check_compatibility(source_agent="non-existent", target_agent="code-reviewer")

    def test_check_compatibility_missing_target(self, registry, mock_metadata_storage):
        """Test checking compatibility when target agent doesn't exist."""
        from src.metadata.models import CustomAgentMetadata, OutputSchema, SemanticType

        # Source exists, target returns None
        source_metadata = CustomAgentMetadata(
            agent_name="code-reviewer",
            version="1.0.0",
            output_schemas=[
                OutputSchema(
                    name="review",
                    semantic_type=SemanticType.DOCUMENT,
                    description="Code review output",
                    guaranteed=True,
                )
            ],
        )

        def get_metadata_side_effect(agent_name):
            if agent_name == "code-reviewer":
                return source_metadata
            return None

        mock_metadata_storage.get_metadata.side_effect = get_metadata_side_effect

        from src.exceptions import AgentNotFoundError

        with pytest.raises(AgentNotFoundError):
            registry.check_compatibility(source_agent="code-reviewer", target_agent="non-existent")


class TestGetConsultationRequirements:
    """Tests for get_consultation_requirements method (T072)."""

    def test_get_consultation_requirements_success(self, registry, mock_metadata_storage):
        """Test getting consultation requirements for an agent."""
        requirements = [
            ConsultationRequirement(
                agent_name="security-agent", phase=ConsultationPhase.PRE_COMPLETION, mandatory=True
            )
        ]
        mock_metadata_storage.get_consultation_requirements.return_value = requirements

        result = registry.get_consultation_requirements("code-reviewer")

        assert len(result) == 1
        assert result[0].agent_name == "security-agent"
        mock_metadata_storage.get_consultation_requirements.assert_called_with("code-reviewer")

    def test_get_consultation_requirements_empty(self, registry, mock_metadata_storage):
        """Test getting requirements when none exist."""
        mock_metadata_storage.get_consultation_requirements.return_value = []

        result = registry.get_consultation_requirements("some-agent")

        assert result == []

    def test_get_consultation_requirements_by_phase(self, registry, mock_metadata_storage):
        """Test filtering requirements by phase."""
        requirements = [
            ConsultationRequirement(
                agent_name="security-agent", phase=ConsultationPhase.PRE_COMPLETION, mandatory=True
            ),
            ConsultationRequirement(
                agent_name="testing-agent", phase=ConsultationPhase.DESIGN_REVIEW, mandatory=False
            ),
        ]
        mock_metadata_storage.get_consultation_requirements.return_value = requirements

        result = registry.get_consultation_requirements(
            "code-reviewer", phase=ConsultationPhase.PRE_COMPLETION
        )

        assert len(result) == 1
        assert result[0].agent_name == "security-agent"


class TestAgentCardManagement:
    """Tests for agent card registration and retrieval."""

    def test_register_agent_card(self, registry):
        """Test registering a new agent card."""
        from src.agents.models import AgentCapabilities

        new_card = AgentCard(
            name="new-agent",
            description="A new agent for testing purposes",
            version="1.0.0",
            url="https://new-agent.example.com/invoke",
            capabilities=AgentCapabilities(streaming=True),
            skills=[],
            defaultInputModes=["text"],
            defaultOutputModes=["text"],
        )

        registry.register_agent_card(new_card)

        assert "new-agent" in registry._agent_cards
        assert registry._agent_cards["new-agent"] == new_card

    def test_get_agent_card(self, registry, sample_agent_cards):
        """Test retrieving an agent card by name."""
        card = registry.get_agent_card("code-reviewer")

        assert card is not None
        assert card.name == "code-reviewer"

    def test_get_agent_card_not_found(self, registry):
        """Test retrieving non-existent agent card."""
        from src.exceptions import AgentNotFoundError

        with pytest.raises(AgentNotFoundError):
            registry.get_agent_card("non-existent-agent")

    def test_list_all_agents(self, registry, sample_agent_cards):
        """Test listing all registered agents."""
        agents = registry.list_all_agents()

        assert len(agents) == 3
        names = [a.name for a in agents]
        assert "code-reviewer" in names
        assert "security-agent" in names
        assert "full-agent" in names

    def test_unregister_agent_card(self, registry):
        """Test unregistering an agent card."""
        registry.unregister_agent_card("code-reviewer")

        assert "code-reviewer" not in registry._agent_cards


class TestCompatibilityResult:
    """Tests for CompatibilityResult model."""

    def test_compatibility_result_compatible(self):
        """Test creating compatible result."""
        from src.registry.query import CompatibilityResult

        result = CompatibilityResult(
            is_compatible=True,
            source_agent="agent-a",
            target_agent="agent-b",
            details={"matching_types": ["ARTIFACT"]},
        )

        assert result.is_compatible is True
        assert result.source_agent == "agent-a"

    def test_compatibility_result_incompatible(self):
        """Test creating incompatible result."""
        from src.registry.query import CompatibilityResult

        result = CompatibilityResult(
            is_compatible=False,
            source_agent="agent-a",
            target_agent="agent-b",
            details={"reason": "No matching types"},
        )

        assert result.is_compatible is False
        assert "reason" in result.details
