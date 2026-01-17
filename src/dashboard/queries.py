"""Dashboard query helpers for AgentCore Observability.

This module provides query classes for retrieving agent loop progress,
events, checkpoints, and exit condition history from CloudWatch Logs
and X-Ray traces.

Maps to User Story 5 (FR-013): Dashboard queries for real-time progress.
"""

import boto3
from datetime import datetime, UTC, timedelta
from typing import Any

from src.dashboard.models import LoopProgress


class ObservabilityQueries:
    """Query helper for CloudWatch Logs and X-Ray traces.

    Provides methods to query agent loop progress, events, checkpoints,
    and exit condition history from AgentCore Observability data.

    Example:
        queries = ObservabilityQueries(region="us-east-1")
        progress = queries.get_loop_progress(session_id="loop-123")
        events = queries.get_recent_events(session_id="loop-123", limit=10)
    """

    def __init__(
        self,
        region: str = "us-east-1",
        logs_client: Any | None = None,
        xray_client: Any | None = None,
    ):
        """Initialize ObservabilityQueries with CloudWatch and X-Ray clients.

        Args:
            region: AWS region for boto3 clients
            logs_client: Optional custom CloudWatch Logs client for testing
            xray_client: Optional custom X-Ray client for testing
        """
        self.region = region
        self.logs_client = logs_client or boto3.client("logs", region_name=region)
        self.xray_client = xray_client or boto3.client("xray", region_name=region)

    def get_loop_progress(
        self,
        session_id: str,
        time_range_minutes: int = 60,
    ) -> LoopProgress | None:
        """Query X-Ray for loop progress by session ID.

        Queries X-Ray trace summaries for the most recent trace matching
        the session_id and extracts loop progress information.

        Args:
            session_id: Loop session ID to query
            time_range_minutes: How far back to search for traces (default 60)

        Returns:
            LoopProgress model with current progress, or None if no traces found

        Example:
            progress = queries.get_loop_progress("loop-session-123")
            if progress:
                print(f"Iteration {progress.current_iteration}/{progress.max_iterations}")
        """
        # Calculate time range for query
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(minutes=time_range_minutes)

        # Query X-Ray for traces with matching session_id
        # FilterExpression uses X-Ray annotation syntax
        try:
            response = self.xray_client.get_trace_summaries(
                StartTime=start_time,
                EndTime=end_time,
                FilterExpression=f'annotation.session_id = "{session_id}"',
            )

            traces = response.get("TraceSummaries", [])
            if not traces:
                return None

            # Get the most recent trace (traces are sorted by time)
            latest_trace = traces[0]

            # Extract loop progress from trace annotations
            annotations = latest_trace.get("Annotations", {})

            # Helper to extract annotation value
            def get_annotation(key: str, value_type: str = "StringValue") -> Any:
                """Extract annotation value from X-Ray annotation structure."""
                annotation_list = annotations.get(key, [])
                if not annotation_list:
                    return None
                annotation_value = annotation_list[0].get("AnnotationValue", {})
                return annotation_value.get(value_type)

            # Build LoopProgress from trace data
            progress = LoopProgress(
                session_id=get_annotation("session_id") or session_id,
                agent_name=get_annotation("loop.agent_name") or "unknown",
                current_iteration=int(get_annotation("iteration.number", "NumberValue") or 0),
                max_iterations=int(get_annotation("iteration.max", "NumberValue") or 1),
                phase=get_annotation("loop.phase") or "unknown",
                started_at=latest_trace.get("StartTime", datetime.now(UTC)).isoformat(),
                exit_conditions_met=int(get_annotation("exit_conditions.met", "NumberValue") or 0),
                exit_conditions_total=int(get_annotation("exit_conditions.total", "NumberValue") or 0),
            )

            return progress

        except Exception as e:
            # Log error but don't crash - return None to indicate no data available
            # In production, this would use proper logging
            return None
