"""Shared fixtures for loop tests."""

from typing import Any
from unittest.mock import patch

import pytest


class MockMemoryClient:
    """Mock MemoryClient for unit testing CheckpointManager.

    Simulates AgentCore Memory service behavior using in-memory storage.
    """

    def __init__(self, region_name: str | None = None, integration_source: str | None = None):
        self.region_name = region_name
        self.integration_source = integration_source
        self._memories: dict[str, dict[str, Any]] = {}
        self._events: dict[str, list[dict[str, Any]]] = {}
        self._memory_counter = 0

    def create_or_get_memory(
        self,
        name: str,
        description: str | None = None,
        event_expiry_days: int = 90,
        **kwargs,
    ) -> dict[str, Any]:
        """Create or get a memory store."""
        if name not in self._memories:
            self._memory_counter += 1
            memory_id = f"memory-{self._memory_counter}"
            self._memories[name] = {
                "memoryId": memory_id,
                "name": name,
                "description": description,
                "event_expiry_days": event_expiry_days,
            }
            self._events[memory_id] = []
        return self._memories[name]

    def create_blob_event(
        self,
        memory_id: str,
        actor_id: str,
        session_id: str,
        blob_data: Any,
        **kwargs,
    ) -> dict[str, Any]:
        """Create a blob event in memory."""
        if memory_id not in self._events:
            self._events[memory_id] = []

        event = {
            "eventId": f"event-{len(self._events[memory_id]) + 1}",
            "memoryId": memory_id,
            "actorId": actor_id,
            "sessionId": session_id,
            "blobData": blob_data,
            "eventTimestamp": "2026-01-17T10:00:00Z",
        }
        self._events[memory_id].append(event)
        return event

    def list_events(
        self,
        memory_id: str,
        actor_id: str,
        session_id: str,
        include_payload: bool = True,
        **kwargs,
    ) -> list[dict[str, Any]]:
        """List events for a session."""
        if memory_id not in self._events:
            return []

        # Filter by actor_id and session_id
        return [
            event
            for event in self._events[memory_id]
            if event.get("actorId") == actor_id and event.get("sessionId") == session_id
        ]

    def clear(self) -> None:
        """Clear all stored data (for test isolation)."""
        self._memories.clear()
        self._events.clear()
        self._memory_counter = 0


@pytest.fixture
def mock_memory_client():
    """Create a mock MemoryClient for testing.

    Returns:
        MockMemoryClient instance
    """
    return MockMemoryClient()


@pytest.fixture
def mock_memory(mock_memory_client):
    """Mock AgentCore Memory for checkpoint tests.

    Use this fixture explicitly in tests that need Memory mocked.
    For DynamoDB fallback tests, use mock_dynamodb instead.
    """
    with patch(
        "bedrock_agentcore.memory.client.MemoryClient",
        return_value=mock_memory_client,
    ):
        yield mock_memory_client


# Keep DynamoDB mock for backwards compatibility with tests that still need it
# TODO: Remove after all tests are migrated
@pytest.fixture
def mock_dynamodb():
    """Legacy DynamoDB mock - deprecated, use mock_memory instead."""
    import boto3
    from moto import mock_aws

    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

        # Create LoopCheckpoints table for legacy tests
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
        table.meta.client.get_waiter("table_exists").wait(TableName="LoopCheckpoints")

        yield dynamodb
