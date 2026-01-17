"""Shared fixtures for loop tests."""

from typing import Any
from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def mock_memory(mocker):
    """Mock bedrock-agentcore Memory service for all loop tests.

    This fixture is automatically used for all tests to avoid
    requiring the actual Memory SDK implementation.
    """
    mock_memory_instance = MagicMock()
    mock_memory_instance._storage = {}

    # Mock put, get, list methods
    def mock_put(key: str, value: dict[str, Any]) -> None:
        mock_memory_instance._storage[key] = value

    def mock_get(key: str) -> dict[str, Any] | None:
        return mock_memory_instance._storage.get(key)

    def mock_list(prefix: str | None = None) -> list[dict[str, Any]]:
        if prefix:
            return [v for k, v in mock_memory_instance._storage.items() if k.startswith(prefix)]
        return list(mock_memory_instance._storage.values())

    mock_memory_instance.put = mock_put
    mock_memory_instance.get = mock_get
    mock_memory_instance.list = mock_list

    # Create mock Memory class that captures region parameter
    def create_memory_instance(region: str = "us-east-1"):
        mock_memory_instance.region = region
        return mock_memory_instance

    mock_memory_class = MagicMock(side_effect=create_memory_instance)

    # Patch the import
    mocker.patch("src.loop.checkpoint.Memory", mock_memory_class)

    return mock_memory_instance
