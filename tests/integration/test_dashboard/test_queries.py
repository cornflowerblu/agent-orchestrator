"""Integration tests for dashboard query functionality.

Tests end-to-end flow of querying ObservabilityQueries with mocked
AWS services (CloudWatch, X-Ray).
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, UTC


@pytest.mark.integration
class TestObservabilityQueriesIntegration:
    """Integration tests for ObservabilityQueries with mocked AWS services."""

    @patch("src.dashboard.queries.boto3")
    def test_end_to_end_progress_query_flow(self, mock_boto3):
        """Test complete flow from query initialization to progress retrieval."""
        from src.dashboard.queries import ObservabilityQueries
        from src.dashboard.models import LoopProgress

        # Setup mock X-Ray client with realistic trace data
        mock_xray_client = Mock()
        mock_xray_client.get_trace_summaries.return_value = {
            "TraceSummaries": [
                {
                    "Id": "trace-integration-test",
                    "StartTime": datetime(2026, 1, 17, 10, 0, 0, tzinfo=UTC),
                    "Annotations": {
                        "session_id": [{"AnnotationValue": {"StringValue": "loop-integration-123"}}],
                        "iteration.number": [{"AnnotationValue": {"NumberValue": 42}}],
                        "iteration.max": [{"AnnotationValue": {"NumberValue": 100}}],
                        "loop.agent_name": [{"AnnotationValue": {"StringValue": "integration-test-agent"}}],
                        "loop.phase": [{"AnnotationValue": {"StringValue": "running"}}],
                        "exit_conditions.met": [{"AnnotationValue": {"NumberValue": 1}}],
                        "exit_conditions.total": [{"AnnotationValue": {"NumberValue": 3}}],
                    }
                }
            ]
        }

        # Initialize queries and fetch progress
        queries = ObservabilityQueries(region="us-east-1", xray_client=mock_xray_client)
        progress = queries.get_loop_progress(session_id="loop-integration-123")

        # Verify end-to-end flow
        assert progress is not None
        assert isinstance(progress, LoopProgress)
        assert progress.session_id == "loop-integration-123"
        assert progress.agent_name == "integration-test-agent"
        assert progress.current_iteration == 42
        assert progress.max_iterations == 100
        assert progress.phase == "running"
        assert progress.exit_conditions_met == 1
        assert progress.exit_conditions_total == 3

        # Verify progress percentage calculation
        assert progress.progress_percentage() == 42.0

    @patch("src.dashboard.queries.boto3")
    def test_end_to_end_events_query_flow(self, mock_boto3):
        """Test complete flow from query initialization to event retrieval."""
        from src.dashboard.queries import ObservabilityQueries

        # Setup mock CloudWatch Logs client with realistic event data
        mock_logs_client = Mock()
        mock_logs_client.start_query.return_value = {"queryId": "query-integration-456"}
        mock_logs_client.get_query_results.return_value = {
            "status": "Complete",
            "results": [
                [
                    {"field": "@timestamp", "value": "2026-01-17T10:00:00Z"},
                    {"field": "event_type", "value": "loop.started"},
                    {"field": "iteration", "value": "0"},
                    {"field": "session_id", "value": "loop-integration-456"},
                ],
                [
                    {"field": "@timestamp", "value": "2026-01-17T10:01:00Z"},
                    {"field": "event_type", "value": "loop.iteration.started"},
                    {"field": "iteration", "value": "1"},
                    {"field": "session_id", "value": "loop-integration-456"},
                ],
                [
                    {"field": "@timestamp", "value": "2026-01-17T10:02:00Z"},
                    {"field": "event_type", "value": "loop.checkpoint.saved"},
                    {"field": "iteration", "value": "5"},
                    {"field": "session_id", "value": "loop-integration-456"},
                ],
            ]
        }

        # Initialize queries and fetch events
        queries = ObservabilityQueries(region="us-east-1", logs_client=mock_logs_client)
        events = queries.get_recent_events(session_id="loop-integration-456", limit=50)

        # Verify end-to-end flow
        assert events is not None
        assert isinstance(events, list)
        assert len(events) == 3

        # Verify event structure and ordering
        assert events[0]["event_type"] == "loop.started"
        assert events[1]["event_type"] == "loop.iteration.started"
        assert events[2]["event_type"] == "loop.checkpoint.saved"

        # Verify CloudWatch Logs query was executed
        mock_logs_client.start_query.assert_called_once()
        mock_logs_client.get_query_results.assert_called_once()

    @patch("src.dashboard.queries.boto3")
    def test_handlers_integration_with_queries(self, mock_boto3):
        """Test that handlers integrate correctly with queries."""
        from src.dashboard.handlers import DashboardHandlers
        from src.dashboard.models import LoopProgress

        # Setup mock X-Ray client for progress query
        mock_xray_client = Mock()
        mock_xray_client.get_trace_summaries.return_value = {
            "TraceSummaries": [
                {
                    "Id": "trace-handler-test",
                    "StartTime": datetime(2026, 1, 17, 10, 0, 0, tzinfo=UTC),
                    "Annotations": {
                        "session_id": [{"AnnotationValue": {"StringValue": "loop-handler-789"}}],
                        "iteration.number": [{"AnnotationValue": {"NumberValue": 75}}],
                        "iteration.max": [{"AnnotationValue": {"NumberValue": 100}}],
                        "loop.agent_name": [{"AnnotationValue": {"StringValue": "handler-test-agent"}}],
                        "loop.phase": [{"AnnotationValue": {"StringValue": "running"}}],
                    }
                }
            ]
        }

        # Configure boto3 mock to return our mock client
        mock_boto3.client.return_value = mock_xray_client

        # Initialize handlers and get progress
        handlers = DashboardHandlers(region="us-east-1")
        result = handlers.get_progress("loop-handler-789")

        # Verify handler returns structured response
        assert result["status"] == "success"
        assert result["data"] is not None
        assert result["data"]["session_id"] == "loop-handler-789"
        assert result["data"]["current_iteration"] == 75
