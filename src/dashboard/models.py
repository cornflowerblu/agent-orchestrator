"""Dashboard data models.

Response models for dashboard API endpoints that query
AgentCore Observability and Memory for loop progress.

Maps to User Story 5 (FR-013): Dashboard queries for real-time progress.
"""

from pydantic import BaseModel, Field
from typing import Any


class LoopProgress(BaseModel):
    """Loop execution progress summary.

    Response model for dashboard progress queries. Contains current
    iteration, phase, exit condition status, and timestamps.

    Maps to FR-013: Dashboard queries Observability for progress.

    Example:
        {
            "session_id": "loop-session-123",
            "agent_name": "test-agent",
            "current_iteration": 25,
            "max_iterations": 100,
            "phase": "running",
            "started_at": "2026-01-17T10:00:00Z",
            "exit_conditions_met": 1,
            "exit_conditions_total": 3
        }
    """

    session_id: str = Field(
        ...,
        description="Loop session ID",
    )

    agent_name: str = Field(
        ...,
        description="Name of the executing agent",
    )

    current_iteration: int = Field(
        ...,
        description="Current iteration number",
        ge=0,
    )

    max_iterations: int = Field(
        ...,
        description="Maximum iterations allowed",
        ge=1,
    )

    phase: str = Field(
        ...,
        description="Current loop phase (initializing, running, completed, etc.)",
    )

    started_at: str = Field(
        ...,
        description="ISO timestamp when loop started",
    )

    completed_at: str | None = Field(
        default=None,
        description="ISO timestamp when loop completed",
    )

    outcome: str | None = Field(
        default=None,
        description="Loop outcome (completed, iteration_limit, error, etc.)",
    )

    exit_conditions_met: int = Field(
        default=0,
        description="Number of exit conditions currently met",
        ge=0,
    )

    exit_conditions_total: int = Field(
        default=0,
        description="Total number of exit conditions",
        ge=0,
    )

    last_checkpoint_at: str | None = Field(
        default=None,
        description="ISO timestamp of last checkpoint save",
    )

    last_checkpoint_iteration: int | None = Field(
        default=None,
        description="Iteration number of last checkpoint",
    )

    error_message: str | None = Field(
        default=None,
        description="Error details if phase is ERROR",
    )

    custom_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional custom metadata from agent",
    )

    def progress_percentage(self) -> float:
        """Calculate progress as percentage of max iterations.

        Returns:
            Progress percentage (0-100)
        """
        if self.max_iterations <= 0:
            return 0.0
        return (self.current_iteration / self.max_iterations) * 100
