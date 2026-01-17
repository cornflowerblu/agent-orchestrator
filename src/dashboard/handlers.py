"""API handlers for dashboard endpoints.

This module provides HTTP request handlers for dashboard API endpoints
that query AgentCore Observability and Memory for loop progress.

Maps to User Story 5 (FR-013): Dashboard queries for real-time progress.
"""

from typing import Any

from src.dashboard.queries import ObservabilityQueries
from src.dashboard.models import LoopProgress


class DashboardHandlers:
    """HTTP API handlers for dashboard endpoints.

    Provides handlers for querying loop progress, events, checkpoints,
    and exit condition history via HTTP endpoints.

    Example:
        handlers = DashboardHandlers(region="us-east-1")
        result = handlers.get_progress("loop-session-123")
    """

    def __init__(self, region: str = "us-east-1"):
        """Initialize dashboard handlers with ObservabilityQueries.

        Args:
            region: AWS region for queries
        """
        self.region = region
        self.queries = ObservabilityQueries(region=region)

    def get_progress(self, session_id: str) -> dict[str, Any]:
        """Handler for GET /progress/{session_id}.

        Returns current loop progress including iteration, phase, and
        exit condition status.

        Args:
            session_id: Loop session ID to query

        Returns:
            Dictionary with status and data:
            {
                "status": "success" | "not_found" | "error",
                "data": LoopProgress dict or None,
                "error": error message if status is "error"
            }

        Example:
            result = handlers.get_progress("loop-session-123")
            if result["status"] == "success":
                print(f"Iteration {result['data']['current_iteration']}")
        """
        try:
            progress = self.queries.get_loop_progress(session_id=session_id)

            if progress is None:
                return {
                    "status": "not_found",
                    "data": None,
                    "message": f"No progress data found for session {session_id}"
                }

            # Convert LoopProgress model to dict for JSON response
            return {
                "status": "success",
                "data": progress.model_dump(),
            }

        except Exception as e:
            return {
                "status": "error",
                "data": None,
                "error": str(e)
            }

    def get_events(
        self,
        session_id: str,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Handler for GET /events/{session_id}.

        Returns recent loop events (iteration started/completed, checkpoint saved, etc.)

        Args:
            session_id: Loop session ID to query
            limit: Maximum number of events to return

        Returns:
            Dictionary with status and data:
            {
                "status": "success" | "error",
                "data": list of event dicts,
                "count": number of events returned
            }

        Example:
            result = handlers.get_events("loop-session-123", limit=20)
            for event in result["data"]:
                print(f"{event['timestamp']}: {event['event_type']}")
        """
        try:
            events = self.queries.get_recent_events(
                session_id=session_id,
                limit=limit
            )

            return {
                "status": "success",
                "data": events,
                "count": len(events),
            }

        except Exception as e:
            return {
                "status": "error",
                "data": [],
                "count": 0,
                "error": str(e)
            }

    def get_checkpoints(
        self,
        session_id: str,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Handler for GET /checkpoints/{session_id}.

        Returns list of checkpoints saved during loop execution.

        Args:
            session_id: Loop session ID to query
            limit: Maximum number of checkpoints to return

        Returns:
            Dictionary with status and data:
            {
                "status": "success" | "error",
                "data": list of checkpoint dicts,
                "count": number of checkpoints returned
            }

        Example:
            result = handlers.get_checkpoints("loop-session-123")
            for cp in result["data"]:
                print(f"Checkpoint at iteration {cp['iteration']}")
        """
        try:
            checkpoints = self.queries.list_checkpoints(
                session_id=session_id,
                limit=limit
            )

            return {
                "status": "success",
                "data": checkpoints,
                "count": len(checkpoints),
            }

        except Exception as e:
            return {
                "status": "error",
                "data": [],
                "count": 0,
                "error": str(e)
            }
