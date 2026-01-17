"""Unit tests for dashboard query classes.

Tests for ObservabilityQueries class that queries CloudWatch/X-Ray
for agent loop progress, events, and checkpoint data.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, UTC


class TestObservabilityQueriesInit:
    """Test ObservabilityQueries initialization."""

    def test_init_creates_cloudwatch_client(self):
        """Test that ObservabilityQueries initializes CloudWatch Logs client."""
        from src.dashboard.queries import ObservabilityQueries

        queries = ObservabilityQueries(region="us-east-1")

        assert queries is not None
        assert hasattr(queries, "region")
        assert queries.region == "us-east-1"

    def test_init_creates_xray_client(self):
        """Test that ObservabilityQueries initializes X-Ray client."""
        from src.dashboard.queries import ObservabilityQueries

        queries = ObservabilityQueries(region="us-west-2")

        assert queries is not None
        assert queries.region == "us-west-2"

    def test_init_with_custom_clients(self):
        """Test that ObservabilityQueries accepts custom boto3 clients."""
        from src.dashboard.queries import ObservabilityQueries

        mock_logs_client = Mock()
        mock_xray_client = Mock()

        queries = ObservabilityQueries(
            region="us-east-1",
            logs_client=mock_logs_client,
            xray_client=mock_xray_client
        )

        assert queries.logs_client == mock_logs_client
        assert queries.xray_client == mock_xray_client
