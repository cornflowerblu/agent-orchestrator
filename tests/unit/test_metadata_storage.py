"""Unit tests for metadata storage layer.

Tests for the DynamoDB storage layer using moto mocks.
"""


import boto3
import pytest
from moto import mock_aws

from src.consultation.rules import (
    ConsultationPhase,
    ConsultationRequirement,
)
from src.exceptions import AgentNotFoundError
from src.metadata.models import (
    CustomAgentMetadata,
    InputSchema,
    OutputSchema,
    SemanticType,
)


@pytest.fixture
def dynamodb_table():
    """Create a mock DynamoDB table for testing."""
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table = dynamodb.create_table(
            TableName="TestAgentMetadata",
            KeySchema=[
                {"AttributeName": "agent_name", "KeyType": "HASH"}
            ],
            AttributeDefinitions=[
                {"AttributeName": "agent_name", "AttributeType": "S"}
            ],
            BillingMode="PAY_PER_REQUEST"
        )
        table.wait_until_exists()
        yield table


@pytest.fixture
def storage(dynamodb_table):
    """Create a MetadataStorage instance with mock table."""
    from src.metadata.storage import MetadataStorage

    with mock_aws():
        # Recreate table in this context
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        try:
            table = dynamodb.create_table(
                TableName="TestAgentMetadata",
                KeySchema=[
                    {"AttributeName": "agent_name", "KeyType": "HASH"}
                ],
                AttributeDefinitions=[
                    {"AttributeName": "agent_name", "AttributeType": "S"}
                ],
                BillingMode="PAY_PER_REQUEST"
            )
            table.wait_until_exists()
        except Exception:
            pass  # Table may already exist

        storage = MetadataStorage(
            table_name="TestAgentMetadata",
            region="us-east-1"
        )
        yield storage


@pytest.fixture
def sample_metadata():
    """Create sample CustomAgentMetadata for testing."""
    return CustomAgentMetadata(
        agent_name="test-agent",
        version="1.0.0",
        input_schemas=[
            InputSchema(
                name="source-code",
                semantic_type=SemanticType.ARTIFACT,
                description="Source code to review",
                required=True
            )
        ],
        output_schemas=[
            OutputSchema(
                name="review-report",
                semantic_type=SemanticType.DOCUMENT,
                description="Code review findings",
                guaranteed=True
            )
        ]
    )


class TestMetadataStorageInit:
    """Tests for MetadataStorage initialization."""

    def test_storage_init_with_explicit_params(self):
        """Test storage initialization with explicit parameters."""
        with mock_aws():
            from src.metadata.storage import MetadataStorage

            storage = MetadataStorage(
                table_name="MyTable",
                region="eu-west-1"
            )
            assert storage.table_name == "MyTable"
            assert storage.region == "eu-west-1"

    def test_storage_init_with_env_vars(self, monkeypatch):
        """Test storage initialization from environment variables."""
        with mock_aws():
            from src.metadata.storage import MetadataStorage

            monkeypatch.setenv("AGENT_METADATA_TABLE", "EnvTable")
            monkeypatch.setenv("AWS_REGION", "ap-southeast-1")

            storage = MetadataStorage()
            assert storage.table_name == "EnvTable"
            assert storage.region == "ap-southeast-1"


class TestPutMetadata:
    """Tests for put_metadata operation."""

    def test_put_metadata_success(self, storage, sample_metadata):
        """Test successfully storing metadata."""
        with mock_aws():
            from src.metadata.storage import MetadataStorage

            # Recreate storage in this context
            dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
            try:
                table = dynamodb.create_table(
                    TableName="TestAgentMetadata",
                    KeySchema=[{"AttributeName": "agent_name", "KeyType": "HASH"}],
                    AttributeDefinitions=[{"AttributeName": "agent_name", "AttributeType": "S"}],
                    BillingMode="PAY_PER_REQUEST"
                )
                table.wait_until_exists()
            except Exception:
                pass

            storage = MetadataStorage(table_name="TestAgentMetadata", region="us-east-1")
            result = storage.put_metadata(sample_metadata)

            assert result["agent_name"] == "test-agent"
            assert result["version"] == "1.0.0"
            assert "updated_at" in result

    def test_put_metadata_updates_timestamp(self, sample_metadata):
        """Test that put_metadata updates the timestamp."""
        with mock_aws():
            from src.metadata.storage import MetadataStorage

            dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
            table = dynamodb.create_table(
                TableName="TestAgentMetadata",
                KeySchema=[{"AttributeName": "agent_name", "KeyType": "HASH"}],
                AttributeDefinitions=[{"AttributeName": "agent_name", "AttributeType": "S"}],
                BillingMode="PAY_PER_REQUEST"
            )
            table.wait_until_exists()

            storage = MetadataStorage(table_name="TestAgentMetadata", region="us-east-1")

            original_time = sample_metadata.updated_at
            result = storage.put_metadata(sample_metadata)

            # Timestamp should be updated
            assert result["updated_at"] != original_time


class TestGetMetadata:
    """Tests for get_metadata operation."""

    def test_get_metadata_success(self, sample_metadata):
        """Test successfully retrieving metadata."""
        with mock_aws():
            from src.metadata.storage import MetadataStorage

            dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
            table = dynamodb.create_table(
                TableName="TestAgentMetadata",
                KeySchema=[{"AttributeName": "agent_name", "KeyType": "HASH"}],
                AttributeDefinitions=[{"AttributeName": "agent_name", "AttributeType": "S"}],
                BillingMode="PAY_PER_REQUEST"
            )
            table.wait_until_exists()

            storage = MetadataStorage(table_name="TestAgentMetadata", region="us-east-1")

            # Store first
            storage.put_metadata(sample_metadata)

            # Then retrieve
            result = storage.get_metadata("test-agent")

            assert result.agent_name == "test-agent"
            assert result.version == "1.0.0"
            assert len(result.input_schemas) == 1

    def test_get_metadata_not_found(self):
        """Test getting metadata for non-existent agent raises error."""
        with mock_aws():
            from src.metadata.storage import MetadataStorage

            dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
            table = dynamodb.create_table(
                TableName="TestAgentMetadata",
                KeySchema=[{"AttributeName": "agent_name", "KeyType": "HASH"}],
                AttributeDefinitions=[{"AttributeName": "agent_name", "AttributeType": "S"}],
                BillingMode="PAY_PER_REQUEST"
            )
            table.wait_until_exists()

            storage = MetadataStorage(table_name="TestAgentMetadata", region="us-east-1")

            with pytest.raises(AgentNotFoundError):
                storage.get_metadata("non-existent-agent")


class TestDeleteMetadata:
    """Tests for delete_metadata operation."""

    def test_delete_metadata_success(self, sample_metadata):
        """Test successfully deleting metadata."""
        with mock_aws():
            from src.metadata.storage import MetadataStorage

            dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
            table = dynamodb.create_table(
                TableName="TestAgentMetadata",
                KeySchema=[{"AttributeName": "agent_name", "KeyType": "HASH"}],
                AttributeDefinitions=[{"AttributeName": "agent_name", "AttributeType": "S"}],
                BillingMode="PAY_PER_REQUEST"
            )
            table.wait_until_exists()

            storage = MetadataStorage(table_name="TestAgentMetadata", region="us-east-1")

            # Store first
            storage.put_metadata(sample_metadata)

            # Delete
            storage.delete_metadata("test-agent")

            # Verify deleted
            with pytest.raises(AgentNotFoundError):
                storage.get_metadata("test-agent")


class TestListAllMetadata:
    """Tests for list_all_metadata operation."""

    def test_list_all_metadata_empty(self):
        """Test listing when no metadata exists."""
        with mock_aws():
            from src.metadata.storage import MetadataStorage

            dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
            table = dynamodb.create_table(
                TableName="TestAgentMetadata",
                KeySchema=[{"AttributeName": "agent_name", "KeyType": "HASH"}],
                AttributeDefinitions=[{"AttributeName": "agent_name", "AttributeType": "S"}],
                BillingMode="PAY_PER_REQUEST"
            )
            table.wait_until_exists()

            storage = MetadataStorage(table_name="TestAgentMetadata", region="us-east-1")

            result = storage.list_all_metadata()
            assert result == []

    def test_list_all_metadata_multiple(self):
        """Test listing multiple metadata records."""
        with mock_aws():
            from src.metadata.storage import MetadataStorage

            dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
            table = dynamodb.create_table(
                TableName="TestAgentMetadata",
                KeySchema=[{"AttributeName": "agent_name", "KeyType": "HASH"}],
                AttributeDefinitions=[{"AttributeName": "agent_name", "AttributeType": "S"}],
                BillingMode="PAY_PER_REQUEST"
            )
            table.wait_until_exists()

            storage = MetadataStorage(table_name="TestAgentMetadata", region="us-east-1")

            # Store multiple agents
            for i in range(3):
                metadata = CustomAgentMetadata(
                    agent_name=f"agent-{i}",
                    version="1.0.0"
                )
                storage.put_metadata(metadata)

            result = storage.list_all_metadata()
            assert len(result) == 3
            names = [m.agent_name for m in result]
            assert "agent-0" in names
            assert "agent-1" in names
            assert "agent-2" in names


class TestConsultationRequirementStorage:
    """Tests for consultation requirement storage operations (T061)."""

    def test_update_consultation_requirements(self):
        """Test updating consultation requirements for an agent."""
        with mock_aws():
            from src.metadata.storage import MetadataStorage

            dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
            table = dynamodb.create_table(
                TableName="TestAgentMetadata",
                KeySchema=[{"AttributeName": "agent_name", "KeyType": "HASH"}],
                AttributeDefinitions=[{"AttributeName": "agent_name", "AttributeType": "S"}],
                BillingMode="PAY_PER_REQUEST"
            )
            table.wait_until_exists()

            storage = MetadataStorage(table_name="TestAgentMetadata", region="us-east-1")

            # Create initial metadata
            metadata = CustomAgentMetadata(
                agent_name="development-agent",
                version="1.0.0"
            )
            storage.put_metadata(metadata)

            # Create requirements
            requirements = [
                ConsultationRequirement(
                    agent_name="security-agent",
                    phase=ConsultationPhase.PRE_COMPLETION,
                    mandatory=True,
                    description="Security review"
                ),
                ConsultationRequirement(
                    agent_name="testing-agent",
                    phase=ConsultationPhase.PRE_COMPLETION,
                    mandatory=True
                )
            ]

            # Update requirements
            result = storage.update_consultation_requirements(
                "development-agent",
                requirements
            )

            assert len(result.consultation_requirements) == 2

    def test_get_consultation_requirements(self):
        """Test retrieving consultation requirements for an agent."""
        with mock_aws():
            from src.metadata.storage import MetadataStorage

            dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
            table = dynamodb.create_table(
                TableName="TestAgentMetadata",
                KeySchema=[{"AttributeName": "agent_name", "KeyType": "HASH"}],
                AttributeDefinitions=[{"AttributeName": "agent_name", "AttributeType": "S"}],
                BillingMode="PAY_PER_REQUEST"
            )
            table.wait_until_exists()

            storage = MetadataStorage(table_name="TestAgentMetadata", region="us-east-1")

            # Create metadata with requirements
            metadata = CustomAgentMetadata(
                agent_name="development-agent",
                version="1.0.0"
            )
            storage.put_metadata(metadata)

            requirements = [
                ConsultationRequirement(
                    agent_name="security-agent",
                    phase=ConsultationPhase.PRE_COMPLETION,
                    mandatory=True
                )
            ]
            storage.update_consultation_requirements("development-agent", requirements)

            # Retrieve requirements
            result = storage.get_consultation_requirements("development-agent")

            assert len(result) == 1
            assert result[0].agent_name == "security-agent"
            assert result[0].phase == ConsultationPhase.PRE_COMPLETION
            assert result[0].mandatory is True

    def test_add_consultation_requirement(self):
        """Test adding a single consultation requirement."""
        with mock_aws():
            from src.metadata.storage import MetadataStorage

            dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
            table = dynamodb.create_table(
                TableName="TestAgentMetadata",
                KeySchema=[{"AttributeName": "agent_name", "KeyType": "HASH"}],
                AttributeDefinitions=[{"AttributeName": "agent_name", "AttributeType": "S"}],
                BillingMode="PAY_PER_REQUEST"
            )
            table.wait_until_exists()

            storage = MetadataStorage(table_name="TestAgentMetadata", region="us-east-1")

            # Create metadata
            metadata = CustomAgentMetadata(
                agent_name="development-agent",
                version="1.0.0"
            )
            storage.put_metadata(metadata)

            # Add first requirement
            req1 = ConsultationRequirement(
                agent_name="security-agent",
                phase=ConsultationPhase.PRE_COMPLETION,
                mandatory=True
            )
            storage.add_consultation_requirement("development-agent", req1)

            # Add second requirement
            req2 = ConsultationRequirement(
                agent_name="testing-agent",
                phase=ConsultationPhase.PRE_COMPLETION,
                mandatory=True
            )
            result = storage.add_consultation_requirement("development-agent", req2)

            assert len(result.consultation_requirements) == 2

    def test_remove_consultation_requirement(self):
        """Test removing consultation requirements for a specific agent."""
        with mock_aws():
            from src.metadata.storage import MetadataStorage

            dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
            table = dynamodb.create_table(
                TableName="TestAgentMetadata",
                KeySchema=[{"AttributeName": "agent_name", "KeyType": "HASH"}],
                AttributeDefinitions=[{"AttributeName": "agent_name", "AttributeType": "S"}],
                BillingMode="PAY_PER_REQUEST"
            )
            table.wait_until_exists()

            storage = MetadataStorage(table_name="TestAgentMetadata", region="us-east-1")

            # Create metadata with multiple requirements
            metadata = CustomAgentMetadata(
                agent_name="development-agent",
                version="1.0.0"
            )
            storage.put_metadata(metadata)

            requirements = [
                ConsultationRequirement(
                    agent_name="security-agent",
                    phase=ConsultationPhase.PRE_COMPLETION,
                    mandatory=True
                ),
                ConsultationRequirement(
                    agent_name="testing-agent",
                    phase=ConsultationPhase.PRE_COMPLETION,
                    mandatory=True
                )
            ]
            storage.update_consultation_requirements("development-agent", requirements)

            # Remove security-agent requirements
            storage.remove_consultation_requirement(
                "development-agent",
                "security-agent"
            )

            # Should only have testing-agent left
            remaining = storage.get_consultation_requirements("development-agent")
            assert len(remaining) == 1
            assert remaining[0].agent_name == "testing-agent"

    def test_update_consultation_requirements_not_found(self):
        """Test updating requirements for non-existent agent raises error."""
        with mock_aws():
            from src.metadata.storage import MetadataStorage

            dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
            table = dynamodb.create_table(
                TableName="TestAgentMetadata",
                KeySchema=[{"AttributeName": "agent_name", "KeyType": "HASH"}],
                AttributeDefinitions=[{"AttributeName": "agent_name", "AttributeType": "S"}],
                BillingMode="PAY_PER_REQUEST"
            )
            table.wait_until_exists()

            storage = MetadataStorage(table_name="TestAgentMetadata", region="us-east-1")

            requirements = [
                ConsultationRequirement(
                    agent_name="security-agent",
                    phase=ConsultationPhase.PRE_COMPLETION,
                    mandatory=True
                )
            ]

            with pytest.raises(AgentNotFoundError):
                storage.update_consultation_requirements(
                    "non-existent-agent",
                    requirements
                )
