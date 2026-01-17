"""End-to-end integration tests for metadata storage with real DynamoDB.

Tests actual AWS DynamoDB operations against deployed tables.
"""

import os

import pytest

from src.consultation.rules import (
    ConsultationCondition,
    ConsultationPhase,
    ConsultationRequirement,
)
from src.exceptions import AgentNotFoundError
from src.metadata.models import CustomAgentMetadata, InputSchema, OutputSchema, SemanticType
from src.metadata.storage import MetadataStorage

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


@pytest.fixture
def metadata_storage():
    """Create metadata storage connected to real DynamoDB."""
    # Use environment variables that match deployed table names
    return MetadataStorage(
        table_name=os.getenv("AGENT_METADATA_TABLE", "AgentMetadata"),
        region=os.getenv("AWS_REGION", "us-east-1"),
    )


@pytest.fixture
def sample_metadata():
    """Sample agent metadata for testing."""
    return CustomAgentMetadata(
        agent_name="test-integration-agent",
        version="1.0.0",
        input_schemas=[
            InputSchema(
                semantic_type=SemanticType.DOCUMENT,
                name="input_doc",
                description="Test input",
                required=True,
            )
        ],
        output_schemas=[
            OutputSchema(
                semantic_type=SemanticType.ARTIFACT,
                name="output",
                description="Test output",
                guaranteed=True,
            )
        ],
    )


class TestMetadataStorageE2E:
    """End-to-end tests for metadata storage."""

    def test_put_and_get_metadata(self, metadata_storage, sample_metadata):
        """Test storing and retrieving metadata."""
        # Put metadata
        metadata_storage.put_metadata(sample_metadata)

        # Get metadata back
        retrieved = metadata_storage.get_metadata(sample_metadata.agent_name)

        assert retrieved is not None
        assert retrieved.agent_name == sample_metadata.agent_name
        assert retrieved.version == sample_metadata.version
        assert len(retrieved.input_schemas) == 1
        assert len(retrieved.output_schemas) == 1
        assert retrieved.output_schemas[0].guaranteed is True

    def test_update_metadata(self, metadata_storage, sample_metadata):
        """Test updating existing metadata."""
        # Store initial version
        metadata_storage.put_metadata(sample_metadata)

        # Update version
        sample_metadata.version = "2.0.0"
        metadata_storage.put_metadata(sample_metadata)

        # Verify update
        retrieved = metadata_storage.get_metadata(sample_metadata.agent_name)
        assert retrieved.version == "2.0.0"

    def test_list_all_metadata(self, metadata_storage, sample_metadata):
        """Test listing all metadata entries."""
        # Store metadata
        metadata_storage.put_metadata(sample_metadata)

        # List all
        all_metadata = metadata_storage.list_all_metadata()

        # Should have at least our test agent
        agent_names = [m.agent_name for m in all_metadata]
        assert sample_metadata.agent_name in agent_names

    def test_delete_metadata(self, metadata_storage, sample_metadata):
        """Test deleting metadata."""
        # Store metadata
        metadata_storage.put_metadata(sample_metadata)

        # Verify it exists
        assert metadata_storage.get_metadata(sample_metadata.agent_name) is not None

        # Delete it
        metadata_storage.delete_metadata(sample_metadata.agent_name)

        # Verify it raises exception when not found
        with pytest.raises(AgentNotFoundError):
            metadata_storage.get_metadata(sample_metadata.agent_name)

    def test_consultation_requirements_crud(self, metadata_storage, sample_metadata):
        """Test CRUD operations for consultation requirements."""
        # Store base metadata
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
                condition=ConsultationCondition(
                    field="result.status", operator="equals", value="success"
                ),
            ),
        ]

        metadata_storage.update_consultation_requirements(sample_metadata.agent_name, requirements)

        # Retrieve requirements
        retrieved_reqs = metadata_storage.get_consultation_requirements(sample_metadata.agent_name)

        assert len(retrieved_reqs) == 2
        assert retrieved_reqs[0].agent_name == "reviewer-agent"
        assert retrieved_reqs[0].mandatory is True
        assert retrieved_reqs[1].agent_name == "validator-agent"
        assert retrieved_reqs[1].mandatory is False
        assert retrieved_reqs[1].condition is not None

    def test_add_single_consultation_requirement(self, metadata_storage, sample_metadata):
        """Test adding a single consultation requirement."""
        # Store base metadata
        metadata_storage.put_metadata(sample_metadata)

        # Add first requirement
        requirement = ConsultationRequirement(
            agent_name="first-agent",
            phase=ConsultationPhase.PRE_EXECUTION,
            mandatory=True,
        )
        metadata_storage.add_consultation_requirement(sample_metadata.agent_name, requirement)

        # Verify
        reqs = metadata_storage.get_consultation_requirements(sample_metadata.agent_name)
        assert len(reqs) == 1
        assert reqs[0].agent_name == "first-agent"

        # Add second requirement
        requirement2 = ConsultationRequirement(
            agent_name="second-agent",
            phase=ConsultationPhase.PRE_COMPLETION,
            mandatory=False,
        )
        metadata_storage.add_consultation_requirement(sample_metadata.agent_name, requirement2)

        # Verify both exist
        reqs = metadata_storage.get_consultation_requirements(sample_metadata.agent_name)
        assert len(reqs) == 2

    def test_remove_consultation_requirement(self, metadata_storage, sample_metadata):
        """Test removing a consultation requirement."""
        # Store base metadata with requirements
        metadata_storage.put_metadata(sample_metadata)

        requirements = [
            ConsultationRequirement(
                agent_name="agent-1",
                phase=ConsultationPhase.PRE_EXECUTION,
                mandatory=True,
            ),
            ConsultationRequirement(
                agent_name="agent-2",
                phase=ConsultationPhase.PRE_COMPLETION,
                mandatory=True,
            ),
        ]
        metadata_storage.update_consultation_requirements(sample_metadata.agent_name, requirements)

        # Remove one requirement
        metadata_storage.remove_consultation_requirement(sample_metadata.agent_name, "agent-1")

        # Verify only one remains
        reqs = metadata_storage.get_consultation_requirements(sample_metadata.agent_name)
        assert len(reqs) == 1
        assert reqs[0].agent_name == "agent-2"

    def test_get_metadata_not_found(self, metadata_storage):
        """Test getting non-existent metadata raises exception."""
        with pytest.raises(AgentNotFoundError, match="non-existent-agent"):
            metadata_storage.get_metadata("non-existent-agent")

    def test_get_requirements_for_nonexistent_agent(self, metadata_storage):
        """Test getting requirements for non-existent agent raises exception."""
        with pytest.raises(AgentNotFoundError, match="non-existent-agent"):
            metadata_storage.get_consultation_requirements("non-existent-agent")
