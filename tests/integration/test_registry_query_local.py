"""Local integration tests for agent registry query using moto.

Fast feedback loop for development - no AWS deployment needed.
"""

import pytest

from src.agents.models import AgentCapabilities, AgentCard, Skill
from src.consultation.rules import ConsultationPhase, ConsultationRequirement
from src.exceptions import AgentNotFoundError, ValidationError
from src.metadata.models import (
    CustomAgentMetadata,
    InputSchema,
    OutputSchema,
    SemanticType,
)
from src.metadata.storage import MetadataStorage
from src.registry.query import AgentRegistry

# Mark all tests in this module as local integration tests
pytestmark = pytest.mark.integration_local


@pytest.fixture
def metadata_storage(dynamodb_local):
    """Create metadata storage with mocked DynamoDB."""
    return MetadataStorage(table_name="AgentMetadata", region="us-east-1")


@pytest.fixture
def registry(metadata_storage):
    """Create agent registry with metadata storage."""
    return AgentRegistry(metadata_storage=metadata_storage)


@pytest.fixture
def sample_agent_card():
    """Sample agent card for testing."""
    return AgentCard(
        name="test-agent",
        description="Test agent for integration tests",
        version="1.0.0",
        url="https://example.com/test-agent",
        capabilities=AgentCapabilities(streaming=True),
        default_input_modes=["text"],
        default_output_modes=["text"],
        skills=[
            Skill(
                id="skill-001",
                name="Document Processing",
                description="Process documents for analysis",
            )
        ],
    )


@pytest.fixture
def sample_metadata():
    """Sample agent metadata for testing."""
    return CustomAgentMetadata(
        agent_name="test-agent",
        version="1.0.0",
        input_schemas=[
            InputSchema(
                semantic_type=SemanticType.DOCUMENT,
                name="input_doc",
                description="Input document",
                required=True,
            )
        ],
        output_schemas=[
            OutputSchema(
                semantic_type=SemanticType.ARTIFACT,
                name="output",
                description="Processed output",
                guaranteed=True,
            )
        ],
    )


class TestAgentRegistryLocal:
    """Local integration tests for agent registry."""

    def test_register_and_get_agent_card(self, registry, sample_agent_card):
        """Test registering and retrieving an agent card."""
        # Register
        registry.register_agent_card(sample_agent_card)

        # Retrieve
        retrieved = registry.get_agent_card("test-agent")

        assert retrieved.name == "test-agent"
        assert retrieved.description == "Test agent for integration tests"
        assert len(retrieved.skills) == 1
        assert retrieved.skills[0].id == "skill-001"

    def test_unregister_agent_card(self, registry, sample_agent_card):
        """Test unregistering an agent card."""
        # Register first
        registry.register_agent_card(sample_agent_card)
        assert registry.get_agent_card("test-agent") is not None

        # Unregister
        registry.unregister_agent_card("test-agent")

        # Should raise exception
        with pytest.raises(AgentNotFoundError):
            registry.get_agent_card("test-agent")

    def test_get_agent_card_not_found(self, registry):
        """Test getting non-existent agent card raises exception."""
        with pytest.raises(AgentNotFoundError, match="non-existent-agent"):
            registry.get_agent_card("non-existent-agent")

    def test_list_all_agents(self, registry, sample_agent_card):
        """Test listing all registered agents."""
        # Register multiple agents
        registry.register_agent_card(sample_agent_card)

        agent2 = AgentCard(
            name="agent-2",
            description="Second test agent for testing",
            version="1.0.0",
            url="https://example.com/agent-2",
            capabilities=AgentCapabilities(streaming=True),
            default_input_modes=["text"],
            default_output_modes=["text"],
            skills=[
                Skill(
                    id="skill-002",
                    name="Data Analysis",
                    description="Analyze data for insights",
                )
            ],
        )
        registry.register_agent_card(agent2)

        # List all
        all_agents = registry.list_all_agents()

        assert len(all_agents) == 2
        agent_names = [a.name for a in all_agents]
        assert "test-agent" in agent_names
        assert "agent-2" in agent_names

    def test_find_by_skill_exact_match(self, registry, sample_agent_card):
        """Test finding agents by skill with exact match."""
        registry.register_agent_card(sample_agent_card)

        # Find by skill ID
        results = registry.find_by_skill("skill-001", match_type="exact")
        assert len(results) == 1
        assert results[0].name == "test-agent"

        # Find by skill name
        results = registry.find_by_skill("Document Processing", match_type="exact")
        assert len(results) == 1
        assert results[0].name == "test-agent"

    def test_find_by_skill_partial_match(self, registry, sample_agent_card):
        """Test finding agents by skill with partial match."""
        registry.register_agent_card(sample_agent_card)

        # Partial match on skill name
        results = registry.find_by_skill("Document", match_type="partial")
        assert len(results) == 1
        assert results[0].name == "test-agent"

    def test_find_by_skill_case_insensitive(self, registry, sample_agent_card):
        """Test finding agents by skill case insensitive."""
        registry.register_agent_card(sample_agent_card)

        # Case insensitive search
        results = registry.find_by_skill("DOCUMENT PROCESSING", match_type="exact", case_sensitive=False)
        assert len(results) == 1
        assert results[0].name == "test-agent"

    def test_find_by_skill_no_matches(self, registry, sample_agent_card):
        """Test finding agents by skill with no matches."""
        registry.register_agent_card(sample_agent_card)

        results = registry.find_by_skill("non-existent-skill", match_type="exact")
        assert len(results) == 0

    def test_find_by_input_compatibility(
        self, registry, metadata_storage, sample_agent_card, sample_metadata
    ):
        """Test finding agents by input compatibility."""
        # Register agent card and metadata
        registry.register_agent_card(sample_agent_card)
        metadata_storage.put_metadata(sample_metadata)

        # Find agents that accept DOCUMENT input
        results = registry.find_by_input_compatibility(SemanticType.DOCUMENT)
        assert len(results) == 1
        assert results[0].name == "test-agent"

    def test_find_by_input_compatibility_required_only(
        self, registry, metadata_storage, sample_agent_card, sample_metadata
    ):
        """Test finding agents by required input compatibility."""
        # Register agent card and metadata
        registry.register_agent_card(sample_agent_card)
        metadata_storage.put_metadata(sample_metadata)

        # Find agents with required DOCUMENT input
        results = registry.find_by_input_compatibility(
            SemanticType.DOCUMENT, required_only=True
        )
        assert len(results) == 1
        assert results[0].name == "test-agent"

        # Find agents with required COLLECTION input (should be empty - we only have DOCUMENT)
        results = registry.find_by_input_compatibility(SemanticType.COLLECTION, required_only=True)
        assert len(results) == 0

    def test_find_by_input_compatibility_no_storage(self):
        """Test finding by input compatibility without metadata storage."""
        # Registry without metadata storage
        registry = AgentRegistry()

        results = registry.find_by_input_compatibility(SemanticType.DOCUMENT)
        assert len(results) == 0

    def test_check_compatibility_compatible(
        self, registry, metadata_storage, sample_agent_card, sample_metadata
    ):
        """Test checking compatibility between compatible agents."""
        # Setup source agent
        registry.register_agent_card(sample_agent_card)
        metadata_storage.put_metadata(sample_metadata)

        # Setup target agent that accepts ARTIFACT input
        target_card = AgentCard(
            name="target-agent",
            description="Target agent for processing artifacts",
            version="1.0.0",
            url="https://example.com/target-agent",
            capabilities=AgentCapabilities(streaming=True),
            default_input_modes=["text"],
            default_output_modes=["text"],
            skills=[
                Skill(
                    id="skill-target",
                    name="Artifact Processing",
                    description="Process artifacts for downstream use",
                )
            ],
        )
        registry.register_agent_card(target_card)

        target_metadata = CustomAgentMetadata(
            agent_name="target-agent",
            version="1.0.0",
            input_schemas=[
                InputSchema(
                    semantic_type=SemanticType.ARTIFACT,
                    name="input_artifact",
                    description="Input artifact",
                    required=True,
                )
            ],
            output_schemas=[
                OutputSchema(
                    semantic_type=SemanticType.COMMENT,
                    name="result",
                    description="Processing result",
                    guaranteed=True,
                )
            ],
        )
        metadata_storage.put_metadata(target_metadata)

        # Check compatibility
        result = registry.check_compatibility("test-agent", "target-agent")

        assert result.is_compatible is True
        assert result.source_agent == "test-agent"
        assert result.target_agent == "target-agent"
        assert len(result.details["compatible_pairs"]) > 0

    def test_check_compatibility_incompatible(
        self, registry, metadata_storage, sample_agent_card, sample_metadata
    ):
        """Test checking compatibility between incompatible agents."""
        # Setup source agent
        registry.register_agent_card(sample_agent_card)
        metadata_storage.put_metadata(sample_metadata)

        # Setup target agent that accepts REFERENCE input (incompatible with ARTIFACT output)
        target_card = AgentCard(
            name="target-agent",
            description="Target agent for processing text",
            version="1.0.0",
            url="https://example.com/target-agent",
            capabilities=AgentCapabilities(streaming=True),
            default_input_modes=["text"],
            default_output_modes=["text"],
            skills=[
                Skill(
                    id="skill-target",
                    name="Text Processing",
                    description="Process text for downstream use",
                )
            ],
        )
        registry.register_agent_card(target_card)

        target_metadata = CustomAgentMetadata(
            agent_name="target-agent",
            version="1.0.0",
            input_schemas=[
                InputSchema(
                    semantic_type=SemanticType.REFERENCE,
                    name="input_ref",
                    description="Input reference",
                    required=True,
                )
            ],
            output_schemas=[
                OutputSchema(
                    semantic_type=SemanticType.COMMENT,
                    name="result",
                    description="Processing result",
                    guaranteed=True,
                )
            ],
        )
        metadata_storage.put_metadata(target_metadata)

        # Check compatibility
        result = registry.check_compatibility("test-agent", "target-agent")

        assert result.is_compatible is False
        assert len(result.details["compatible_pairs"]) == 0

    def test_check_compatibility_source_not_found(self, registry, metadata_storage):
        """Test checking compatibility with non-existent source agent."""
        # Setup target agent
        target_card = AgentCard(
            name="target-agent",
            description="Target agent for testing not found scenario",
            version="1.0.0",
            url="https://example.com/target-agent",
            capabilities=AgentCapabilities(streaming=True),
            default_input_modes=["text"],
            default_output_modes=["text"],
            skills=[],
        )
        registry.register_agent_card(target_card)

        target_metadata = CustomAgentMetadata(
            agent_name="target-agent",
            version="1.0.0",
            input_schemas=[],
            output_schemas=[],
        )
        metadata_storage.put_metadata(target_metadata)

        # Check compatibility with non-existent source
        with pytest.raises(AgentNotFoundError, match="non-existent-agent"):
            registry.check_compatibility("non-existent-agent", "target-agent")

    def test_check_compatibility_target_not_found(
        self, registry, metadata_storage, sample_agent_card, sample_metadata
    ):
        """Test checking compatibility with non-existent target agent."""
        # Setup source agent
        registry.register_agent_card(sample_agent_card)
        metadata_storage.put_metadata(sample_metadata)

        # Check compatibility with non-existent target
        with pytest.raises(AgentNotFoundError, match="non-existent-target"):
            registry.check_compatibility("test-agent", "non-existent-target")

    def test_check_compatibility_no_storage(self, sample_agent_card):
        """Test checking compatibility without metadata storage."""
        # Registry without metadata storage
        registry = AgentRegistry()
        registry.register_agent_card(sample_agent_card)

        with pytest.raises(ValidationError, match="not configured with metadata storage"):
            registry.check_compatibility("test-agent", "another-agent")

    def test_get_consultation_requirements(
        self, registry, metadata_storage, sample_metadata
    ):
        """Test getting consultation requirements for an agent."""
        # Store metadata
        metadata_storage.put_metadata(sample_metadata)

        # Add consultation requirements
        requirements = [
            ConsultationRequirement(
                agent_name="reviewer-agent",
                phase=ConsultationPhase.PRE_EXECUTION,
                mandatory=True,
            ),
            ConsultationRequirement(
                agent_name="validator-agent",
                phase=ConsultationPhase.PRE_COMPLETION,
                mandatory=False,
            ),
        ]
        metadata_storage.update_consultation_requirements("test-agent", requirements)

        # Get all requirements
        retrieved = registry.get_consultation_requirements("test-agent")
        assert len(retrieved) == 2

        # Get requirements for specific phase
        pre_exec = registry.get_consultation_requirements(
            "test-agent", phase=ConsultationPhase.PRE_EXECUTION
        )
        assert len(pre_exec) == 1
        assert pre_exec[0].agent_name == "reviewer-agent"

    def test_get_consultation_requirements_no_storage(self):
        """Test getting consultation requirements without metadata storage."""
        # Registry without metadata storage
        registry = AgentRegistry()

        results = registry.get_consultation_requirements("test-agent")
        assert len(results) == 0
