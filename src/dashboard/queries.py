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

    def get_recent_events(
        self,
        session_id: str,
        limit: int = 50,
        time_range_minutes: int = 60,
        log_group_name: str = "/aws/bedrock/agent-loops",
    ) -> list[dict[str, Any]]:
        """Query CloudWatch Logs for recent loop events by session ID.

        Uses CloudWatch Logs Insights to query for loop events like
        iteration started/completed, checkpoint saved, exit condition evaluated.

        Args:
            session_id: Loop session ID to query
            limit: Maximum number of events to return (default 50)
            time_range_minutes: How far back to search (default 60)
            log_group_name: CloudWatch Log Group name (default /aws/bedrock/agent-loops)

        Returns:
            List of event dictionaries with timestamp, event_type, iteration, etc.

        Example:
            events = queries.get_recent_events("loop-session-123", limit=20)
            for event in events:
                print(f"{event['timestamp']}: {event['event_type']}")
        """
        # Calculate time range for query
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(minutes=time_range_minutes)

        # CloudWatch Logs Insights query
        query_string = f"""
            fields @timestamp, event_type, iteration, session_id, phase, details
            | filter session_id = "{session_id}"
            | sort @timestamp desc
            | limit {limit}
        """

        try:
            # Start the query
            start_response = self.logs_client.start_query(
                logGroupName=log_group_name,
                startTime=int(start_time.timestamp()),
                endTime=int(end_time.timestamp()),
                queryString=query_string.strip(),
            )

            query_id = start_response["queryId"]

            # Poll for query results (simple implementation - waits for completion)
            # In production, this should use exponential backoff or async polling
            import time
            max_attempts = 10
            for attempt in range(max_attempts):
                results_response = self.logs_client.get_query_results(queryId=query_id)

                if results_response["status"] == "Complete":
                    # Convert results to list of event dictionaries
                    events = []
                    for result in results_response.get("results", []):
                        # Each result is a list of field/value pairs
                        event = {}
                        for field_data in result:
                            field_name = field_data.get("field", "")
                            field_value = field_data.get("value", "")
                            # Remove @ prefix from CloudWatch field names
                            clean_field_name = field_name.lstrip("@")
                            event[clean_field_name] = field_value
                        events.append(event)

                    return events

                if results_response["status"] == "Failed":
                    return []

                # Wait before polling again
                time.sleep(0.5)

            # Query timed out
            return []

        except Exception as e:
            # Log error but don't crash - return empty list
            return []

    def list_checkpoints(
        self,
        session_id: str,
        limit: int = 20,
        time_range_minutes: int = 1440,  # 24 hours default
        log_group_name: str = "/aws/bedrock/agent-loops",
    ) -> list[dict[str, Any]]:
        """Query CloudWatch Logs for checkpoint events by session ID.

        Finds all checkpoint save events for a loop session, sorted by
        iteration number (most recent first).

        Args:
            session_id: Loop session ID to query
            limit: Maximum number of checkpoints to return (default 20)
            time_range_minutes: How far back to search (default 1440 = 24 hours)
            log_group_name: CloudWatch Log Group name

        Returns:
            List of checkpoint dictionaries with iteration, timestamp, checkpoint_id

        Example:
            checkpoints = queries.list_checkpoints("loop-session-123")
            for cp in checkpoints:
                print(f"Iteration {cp['iteration']}: {cp['timestamp']}")
        """
        # Calculate time range for query
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(minutes=time_range_minutes)

        # CloudWatch Logs Insights query for checkpoint events
        query_string = f"""
            fields @timestamp, iteration, checkpoint_id, session_id
            | filter session_id = "{session_id}" and event_type = "loop.checkpoint.saved"
            | sort iteration desc
            | limit {limit}
        """

        try:
            # Start the query
            start_response = self.logs_client.start_query(
                logGroupName=log_group_name,
                startTime=int(start_time.timestamp()),
                endTime=int(end_time.timestamp()),
                queryString=query_string.strip(),
            )

            query_id = start_response["queryId"]

            # Poll for query results
            import time
            max_attempts = 10
            for attempt in range(max_attempts):
                results_response = self.logs_client.get_query_results(queryId=query_id)

                if results_response["status"] == "Complete":
                    # Convert results to list of checkpoint dictionaries
                    checkpoints = []
                    for result in results_response.get("results", []):
                        checkpoint = {}
                        for field_data in result:
                            field_name = field_data.get("field", "").lstrip("@")
                            checkpoint[field_name] = field_data.get("value", "")
                        checkpoints.append(checkpoint)

                    return checkpoints

                if results_response["status"] == "Failed":
                    return []

                time.sleep(0.5)

            return []

        except Exception as e:
            return []

    def get_exit_condition_history(
        self,
        session_id: str,
        limit: int = 50,
        time_range_minutes: int = 60,
        log_group_name: str = "/aws/bedrock/agent-loops",
    ) -> list[dict[str, Any]]:
        """Query CloudWatch Logs for exit condition evaluation history.

        Retrieves all exit condition evaluation events for a loop session,
        showing how conditions changed over time.

        Args:
            session_id: Loop session ID to query
            limit: Maximum number of evaluations to return (default 50)
            time_range_minutes: How far back to search (default 60)
            log_group_name: CloudWatch Log Group name

        Returns:
            List of evaluation dictionaries with condition_type, status, iteration

        Example:
            history = queries.get_exit_condition_history("loop-session-123")
            for eval in history:
                print(f"Iteration {eval['iteration']}: {eval['condition_type']} = {eval['status']}")
        """
        # Calculate time range for query
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(minutes=time_range_minutes)

        # CloudWatch Logs Insights query for exit condition events
        query_string = f"""
            fields @timestamp, iteration, condition_type, status, tool_name, tool_exit_code
            | filter session_id = "{session_id}" and event_type = "loop.exit_condition.evaluated"
            | sort @timestamp desc
            | limit {limit}
        """

        try:
            # Start the query
            start_response = self.logs_client.start_query(
                logGroupName=log_group_name,
                startTime=int(start_time.timestamp()),
                endTime=int(end_time.timestamp()),
                queryString=query_string.strip(),
            )

            query_id = start_response["queryId"]

            # Poll for query results
            import time
            max_attempts = 10
            for attempt in range(max_attempts):
                results_response = self.logs_client.get_query_results(queryId=query_id)

                if results_response["status"] == "Complete":
                    # Convert results to list of evaluation dictionaries
                    evaluations = []
                    for result in results_response.get("results", []):
                        evaluation = {}
                        for field_data in result:
                            field_name = field_data.get("field", "").lstrip("@")
                            evaluation[field_name] = field_data.get("value", "")
                        evaluations.append(evaluation)

                    return evaluations

                if results_response["status"] == "Failed":
                    return []

                time.sleep(0.5)

            return []

        except Exception as e:
            return []
