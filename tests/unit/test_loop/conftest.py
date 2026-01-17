"""Shared fixtures for loop tests."""

import boto3
import pytest
from moto import mock_aws


@pytest.fixture(autouse=True)
def mock_dynamodb():
    """Mock DynamoDB for all loop tests.

    This fixture automatically creates a mocked DynamoDB environment
    with the LoopCheckpoints table for checkpoint storage tests.
    """
    with mock_aws():
        # Create DynamoDB resource
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

        # Create LoopCheckpoints table
        table = dynamodb.create_table(
            TableName="LoopCheckpoints",
            KeySchema=[
                {"AttributeName": "session_id", "KeyType": "HASH"},
                {"AttributeName": "iteration", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "session_id", "AttributeType": "S"},
                {"AttributeName": "iteration", "AttributeType": "N"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        # Wait for table to be active
        table.meta.client.get_waiter("table_exists").wait(TableName="LoopCheckpoints")

        yield dynamodb
