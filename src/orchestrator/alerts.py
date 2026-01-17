"""Alert management for iteration warnings.

This module provides AlertManager class for sending warnings when agents
approach their iteration limits (SC-008: 80% threshold).
"""

import logging

logger = logging.getLogger(__name__)


class AlertManager:
    """Manages alerts for iteration limit warnings.

    Maps to FR-010: Orchestrator monitors Observability and issues warnings.
    Maps to SC-008: Alert at 80% threshold.

    Example:
        manager = AlertManager(agent_name="test-agent")
        if manager.send_warning(
            current_iteration=80,
            max_iterations=100,
            threshold=0.8,
            session_id="session-123"
        ):
            print("Warning sent: approaching iteration limit")
    """

    def __init__(self, agent_name: str, region: str = "us-east-1"):
        """Initialize AlertManager.

        Args:
            agent_name: Name of the agent to monitor
            region: AWS region for alert services (default: us-east-1)
        """
        self.agent_name = agent_name
        self.region = region

    def send_warning(
        self,
        current_iteration: int,
        max_iterations: int,
        threshold: float = 0.8,
        session_id: str | None = None,
    ) -> bool:
        """Send warning alert if at or above threshold.

        Maps to SC-008: Alert at 80% threshold of max iterations.

        Args:
            current_iteration: Current iteration number
            max_iterations: Maximum allowed iterations
            threshold: Warning threshold as fraction (default 0.8 = 80%)
            session_id: Optional session ID for context

        Returns:
            True if warning was sent, False if below threshold

        Example:
            manager = AlertManager(agent_name="test-agent")
            sent = manager.send_warning(
                current_iteration=80,
                max_iterations=100,
                threshold=0.8,
                session_id="session-123"
            )
            if sent:
                print("Warning: 80% of iterations complete")
        """
        # Calculate progress percentage
        progress = (current_iteration / max_iterations) if max_iterations > 0 else 0.0

        # Check if at or above threshold
        if progress >= threshold:
            # Log warning
            logger.warning(
                f"Agent '{self.agent_name}' approaching iteration limit: "
                f"{current_iteration}/{max_iterations} ({progress * 100:.1f}%) "
                f"[session: {session_id or 'N/A'}]"
            )

            # In a full implementation, this would:
            # - Send CloudWatch alarm
            # - Publish SNS notification
            # - Emit OTEL event
            # For now, we just log

            return True

        return False
