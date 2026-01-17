"""Dashboard query helpers for AgentCore Observability.

This module provides query classes for retrieving agent loop progress,
events, checkpoints, and exit condition history from CloudWatch Logs
and X-Ray traces.

Maps to User Story 5 (FR-013): Dashboard queries for real-time progress.
"""

import boto3
from typing import Any


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
