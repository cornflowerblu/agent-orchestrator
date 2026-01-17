"""Shared fixtures for integration tests.

Provides both moto-based local fixtures and real AWS fixtures.
"""

import os
from typing import Iterator

import boto3
import pytest
from moto import mock_aws


@pytest.fixture
def aws_credentials_moto():
    """Mock AWS credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture
def dynamodb_local(aws_credentials_moto) -> Iterator[boto3.resource]:
    """Create mocked DynamoDB resource for local testing."""
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

        # Create AgentMetadata table
        metadata_table = dynamodb.create_table(
            TableName="AgentMetadata",
            KeySchema=[{"AttributeName": "agent_name", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "agent_name", "AttributeType": "S"},
                {"AttributeName": "skill_id", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "SkillIndex",
                    "KeySchema": [{"AttributeName": "skill_id", "KeyType": "HASH"}],
                    "Projection": {
                        "ProjectionType": "INCLUDE",
                        "NonKeyAttributes": ["agent_name", "version"],
                    },
                }
            ],
            StreamSpecification={
                "StreamEnabled": True,
                "StreamViewType": "NEW_AND_OLD_IMAGES",
            },
        )

        # Create AgentStatus table
        status_table = dynamodb.create_table(
            TableName="AgentStatus",
            KeySchema=[{"AttributeName": "agent_name", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "agent_name", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        # Wait for tables to be created
        metadata_table.meta.client.get_waiter("table_exists").wait(TableName="AgentMetadata")
        status_table.meta.client.get_waiter("table_exists").wait(TableName="AgentStatus")

        yield dynamodb


@pytest.fixture
def dynamodb_real() -> boto3.resource:
    """
    Create real DynamoDB resource for AWS integration tests.

    Requires actual AWS credentials and deployed tables.
    """
    return boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION", "us-east-1"))
