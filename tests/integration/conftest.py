"""Shared fixtures for integration tests.

Integration test layers:
1. SAM Local + LocalStack (tests/integration/sam_local/) - pre-deploy sanity
2. Real AWS (tests/integration/) - full end-to-end validation

For local testing, use SAM local with LocalStack instead of moto mocks.
See infrastructure/sam-local/README.md for setup instructions.
"""

import os

import boto3
import pytest

LOCALSTACK_ENDPOINT = "http://localhost:4566"


def _localstack_available() -> bool:
    """Check if LocalStack is running."""
    try:
        client = boto3.client(
            "dynamodb",
            endpoint_url=LOCALSTACK_ENDPOINT,
            region_name="us-east-1",
            aws_access_key_id="test",
            aws_secret_access_key="test",
        )
        client.list_tables()
        return True
    except Exception:
        return False


@pytest.fixture
def dynamodb_real() -> boto3.resource:
    """
    Create real DynamoDB resource for AWS integration tests.

    Requires actual AWS credentials and deployed tables.
    """
    return boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION", "us-east-1"))


@pytest.fixture
def dynamodb_localstack():
    """
    Create LocalStack DynamoDB resource for local integration tests.

    Requires LocalStack running:
        docker-compose -f infrastructure/sam-local/docker-compose.yml up -d

    The init-localstack.sh script creates the required tables automatically.
    """
    if not _localstack_available():
        pytest.skip(
            "LocalStack not running. Start it with:\n"
            "  docker-compose -f infrastructure/sam-local/docker-compose.yml up -d"
        )

    # Set environment for CheckpointManager to use LocalStack
    os.environ["CHECKPOINT_BACKEND"] = "dynamodb"
    os.environ["CHECKPOINT_TABLE_NAME"] = "LoopCheckpoints"
    os.environ["AWS_ENDPOINT_URL"] = LOCALSTACK_ENDPOINT
    os.environ["AWS_ACCESS_KEY_ID"] = "test"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "test"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

    return boto3.resource(
        "dynamodb",
        endpoint_url=LOCALSTACK_ENDPOINT,
        region_name="us-east-1",
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )


@pytest.fixture
def aws_region() -> str:
    """Get AWS region from environment."""
    return os.getenv("AWS_REGION", "us-east-1")
