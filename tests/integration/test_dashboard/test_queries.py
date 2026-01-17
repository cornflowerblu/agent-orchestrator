"""Integration tests for dashboard query functionality.

Tests end-to-end flow of querying ObservabilityQueries with mocked
AWS services (CloudWatch, X-Ray).
"""

from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest


@pytest.mark.integration
class TestObservabilityQueriesIntegration:
    """Integration tests for ObservabilityQueries with mocked AWS services."""

    @patch("src.dashboard.queries.boto3")
    def test_end_to_end_progress_query_flow(self, mock_boto3):
        """Test complete flow from query initialization to progress retrieval."""
        from src.dashboard.models import LoopProgress
        from src.dashboard.queries import ObservabilityQueries

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

    @patch("src.dashboard.queries.boto3")
    def test_list_checkpoints_flow(self, mock_boto3):
        """Test checkpoint listing from CloudWatch Logs."""
        from src.dashboard.queries import ObservabilityQueries

        # Setup mock CloudWatch Logs client with checkpoint data
        mock_logs_client = Mock()
        mock_logs_client.start_query.return_value = {"queryId": "checkpoint-query-123"}
        mock_logs_client.get_query_results.return_value = {
            "status": "Complete",
            "results": [
                [
                    {"field": "@timestamp", "value": "2026-01-17T10:00:00Z"},
                    {"field": "event_type", "value": "loop.checkpoint.saved"},
                    {"field": "iteration", "value": "5"},
                    {"field": "checkpoint_id", "value": "checkpoint-1"},
                ],
                [
                    {"field": "@timestamp", "value": "2026-01-17T10:05:00Z"},
                    {"field": "event_type", "value": "loop.checkpoint.saved"},
                    {"field": "iteration", "value": "10"},
                    {"field": "checkpoint_id", "value": "checkpoint-2"},
                ],
            ]
        }

        # Initialize queries and list checkpoints
        queries = ObservabilityQueries(region="us-east-1", logs_client=mock_logs_client)
        checkpoints = queries.list_checkpoints(session_id="loop-checkpoint-test")

        # Verify checkpoints were retrieved
        assert checkpoints is not None
        assert isinstance(checkpoints, list)
        assert len(checkpoints) == 2
        assert checkpoints[0]["iteration"] == "5"
        assert checkpoints[1]["iteration"] == "10"

    @patch("src.dashboard.queries.boto3")
    def test_get_exit_condition_history_flow(self, mock_boto3):
        """Test exit condition history retrieval."""
        from src.dashboard.queries import ObservabilityQueries

        # Setup mock CloudWatch Logs client with exit condition data
        mock_logs_client = Mock()
        mock_logs_client.start_query.return_value = {"queryId": "exit-condition-query-456"}
        mock_logs_client.get_query_results.return_value = {
            "status": "Complete",
            "results": [
                [
                    {"field": "@timestamp", "value": "2026-01-17T10:00:00Z"},
                    {"field": "condition_type", "value": "all_tests_pass"},
                    {"field": "status", "value": "not_met"},
                    {"field": "iteration", "value": "1"},
                ],
                [
                    {"field": "@timestamp", "value": "2026-01-17T10:05:00Z"},
                    {"field": "condition_type", "value": "all_tests_pass"},
                    {"field": "status", "value": "met"},
                    {"field": "iteration", "value": "15"},
                ],
            ]
        }

        # Initialize queries and get history
        queries = ObservabilityQueries(region="us-east-1", logs_client=mock_logs_client)
        history = queries.get_exit_condition_history(session_id="loop-exit-condition-test")

        # Verify history was retrieved
        assert history is not None
        assert isinstance(history, list)
        assert len(history) == 2
        assert history[0]["condition_type"] == "all_tests_pass"
        assert history[0]["status"] == "not_met"
        assert history[1]["status"] == "met"

    @patch("src.dashboard.queries.boto3")
    def test_stream_progress_yields_updates(self, mock_boto3):
        """Test progress streaming with generator."""
        from src.dashboard.queries import ObservabilityQueries

        # Setup mock X-Ray client to return different progress on each call
        mock_xray_client = Mock()
        call_count = 0

        def mock_get_trace_summaries(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return {
                "TraceSummaries": [
                    {
                        "Id": f"trace-stream-{call_count}",
                        "StartTime": datetime(2026, 1, 17, 10, 0, 0, tzinfo=UTC),
                        "Annotations": {
                            "session_id": [{"AnnotationValue": {"StringValue": "loop-stream-test"}}],
                            "iteration.number": [{"AnnotationValue": {"NumberValue": call_count * 10}}],
                            "iteration.max": [{"AnnotationValue": {"NumberValue": 100}}],
                            "loop.agent_name": [{"AnnotationValue": {"StringValue": "stream-test-agent"}}],
                            "loop.phase": [{"AnnotationValue": {"StringValue": "running"}}],
                        }
                    }
                ]
            }

        mock_xray_client.get_trace_summaries.side_effect = mock_get_trace_summaries

        # Initialize queries and stream progress
        queries = ObservabilityQueries(region="us-east-1", xray_client=mock_xray_client)
        progress_generator = queries.stream_progress(
            session_id="loop-stream-test",
            poll_interval=0.1,
            max_duration=1  # 1 second max duration, will get ~3 updates at 0.1s intervals
        )

        # Collect streamed progress updates (limit to 3 for test)
        progress_updates = []
        for i, progress in enumerate(progress_generator):
            progress_updates.append(progress)
            if i >= 2:  # Stop after 3 updates
                break

        # Verify streaming behavior
        assert len(progress_updates) == 3
        assert progress_updates[0].current_iteration == 10
        assert progress_updates[1].current_iteration == 20
        assert progress_updates[2].current_iteration == 30
