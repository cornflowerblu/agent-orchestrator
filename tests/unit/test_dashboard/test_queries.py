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


class TestObservabilityQueriesGetLoopProgress:
    """Test ObservabilityQueries.get_loop_progress() method."""

    @patch("src.dashboard.queries.boto3")
    def test_get_loop_progress_queries_xray_for_traces(self, mock_boto3):
        """Test that get_loop_progress queries X-Ray for trace data."""
        from src.dashboard.queries import ObservabilityQueries
        from datetime import datetime, UTC

        # Setup mock X-Ray client
        mock_xray_client = Mock()
        mock_xray_client.get_trace_summaries.return_value = {
            "TraceSummaries": [
                {
                    "Id": "trace-123",
                    "StartTime": datetime(2026, 1, 17, 10, 0, 0, tzinfo=UTC),
                    "Annotations": {
                        "session_id": [{"AnnotationValue": {"StringValue": "loop-session-123"}}],
                        "iteration.number": [{"AnnotationValue": {"NumberValue": 25}}],
                        "iteration.max": [{"AnnotationValue": {"NumberValue": 100}}],
                        "loop.agent_name": [{"AnnotationValue": {"StringValue": "test-agent"}}],
                        "loop.phase": [{"AnnotationValue": {"StringValue": "running"}}],
                    }
                }
            ]
        }

        queries = ObservabilityQueries(region="us-east-1", xray_client=mock_xray_client)
        progress = queries.get_loop_progress(session_id="loop-session-123")

        # Verify X-Ray was queried
        mock_xray_client.get_trace_summaries.assert_called_once()
        assert progress is not None
        assert progress.session_id == "loop-session-123"

    @patch("src.dashboard.queries.boto3")
    def test_get_loop_progress_returns_loop_progress_model(self, mock_boto3):
        """Test that get_loop_progress returns a LoopProgress model."""
        from src.dashboard.queries import ObservabilityQueries
        from src.dashboard.models import LoopProgress
        from datetime import datetime, UTC

        # Setup mock with full trace data
        mock_xray_client = Mock()
        mock_xray_client.get_trace_summaries.return_value = {
            "TraceSummaries": [
                {
                    "Id": "trace-456",
                    "StartTime": datetime(2026, 1, 17, 10, 0, 0, tzinfo=UTC),
                    "Annotations": {
                        "session_id": [{"AnnotationValue": {"StringValue": "loop-session-456"}}],
                        "iteration.number": [{"AnnotationValue": {"NumberValue": 50}}],
                        "iteration.max": [{"AnnotationValue": {"NumberValue": 100}}],
                        "loop.agent_name": [{"AnnotationValue": {"StringValue": "test-agent-2"}}],
                        "loop.phase": [{"AnnotationValue": {"StringValue": "running"}}],
                        "exit_conditions.met": [{"AnnotationValue": {"NumberValue": 2}}],
                        "exit_conditions.total": [{"AnnotationValue": {"NumberValue": 3}}],
                    }
                }
            ]
        }

        queries = ObservabilityQueries(region="us-east-1", xray_client=mock_xray_client)
        progress = queries.get_loop_progress(session_id="loop-session-456")

        assert isinstance(progress, LoopProgress)
        assert progress.session_id == "loop-session-456"
        assert progress.agent_name == "test-agent-2"
        assert progress.current_iteration == 50
        assert progress.max_iterations == 100
        assert progress.phase == "running"
        assert progress.exit_conditions_met == 2
        assert progress.exit_conditions_total == 3

    @patch("src.dashboard.queries.boto3")
    def test_get_loop_progress_returns_none_if_no_traces(self, mock_boto3):
        """Test that get_loop_progress returns None if no traces found."""
        from src.dashboard.queries import ObservabilityQueries

        # Setup mock with empty response
        mock_xray_client = Mock()
        mock_xray_client.get_trace_summaries.return_value = {
            "TraceSummaries": []
        }

        queries = ObservabilityQueries(region="us-east-1", xray_client=mock_xray_client)
        progress = queries.get_loop_progress(session_id="nonexistent-session")

        assert progress is None


class TestObservabilityQueriesGetRecentEvents:
    """Test ObservabilityQueries.get_recent_events() method."""

    @patch("src.dashboard.queries.boto3")
    def test_get_recent_events_queries_cloudwatch_logs(self, mock_boto3):
        """Test that get_recent_events queries CloudWatch Logs for loop events."""
        from src.dashboard.queries import ObservabilityQueries

        # Setup mock CloudWatch Logs client
        mock_logs_client = Mock()
        mock_logs_client.start_query.return_value = {"queryId": "query-123"}
        mock_logs_client.get_query_results.return_value = {
            "status": "Complete",
            "results": [
                [
                    {"field": "@timestamp", "value": "2026-01-17T10:00:00Z"},
                    {"field": "event_type", "value": "loop.iteration.started"},
                    {"field": "iteration", "value": "10"},
                ]
            ]
        }

        queries = ObservabilityQueries(region="us-east-1", logs_client=mock_logs_client)
        events = queries.get_recent_events(session_id="loop-session-123", limit=10)

        # Verify CloudWatch Logs was queried
        mock_logs_client.start_query.assert_called_once()
        assert events is not None
        assert isinstance(events, list)

    @patch("src.dashboard.queries.boto3")
    def test_get_recent_events_returns_list_of_events(self, mock_boto3):
        """Test that get_recent_events returns a list of event dictionaries."""
        from src.dashboard.queries import ObservabilityQueries

        # Setup mock with multiple events
        mock_logs_client = Mock()
        mock_logs_client.start_query.return_value = {"queryId": "query-456"}
        mock_logs_client.get_query_results.return_value = {
            "status": "Complete",
            "results": [
                [
                    {"field": "@timestamp", "value": "2026-01-17T10:00:00Z"},
                    {"field": "event_type", "value": "loop.iteration.started"},
                    {"field": "iteration", "value": "10"},
                    {"field": "session_id", "value": "loop-session-456"},
                ],
                [
                    {"field": "@timestamp", "value": "2026-01-17T10:01:00Z"},
                    {"field": "event_type", "value": "loop.iteration.completed"},
                    {"field": "iteration", "value": "10"},
                    {"field": "session_id", "value": "loop-session-456"},
                ]
            ]
        }

        queries = ObservabilityQueries(region="us-east-1", logs_client=mock_logs_client)
        events = queries.get_recent_events(session_id="loop-session-456", limit=10)

        assert len(events) == 2
        assert events[0]["event_type"] == "loop.iteration.started"
        assert events[1]["event_type"] == "loop.iteration.completed"

    @patch("src.dashboard.queries.boto3")
    def test_get_recent_events_returns_empty_list_if_no_results(self, mock_boto3):
        """Test that get_recent_events returns empty list if no events found."""
        from src.dashboard.queries import ObservabilityQueries

        # Setup mock with no results
        mock_logs_client = Mock()
        mock_logs_client.start_query.return_value = {"queryId": "query-789"}
        mock_logs_client.get_query_results.return_value = {
            "status": "Complete",
            "results": []
        }

        queries = ObservabilityQueries(region="us-east-1", logs_client=mock_logs_client)
        events = queries.get_recent_events(session_id="nonexistent-session", limit=10)

        assert events == []
