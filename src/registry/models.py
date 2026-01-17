"""Registry models for agent status and metadata.

Task T073: Create AgentStatus Pydantic model
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AgentStatusValue(str, Enum):
    """Possible status values for an agent."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"
    UNKNOWN = "unknown"


class HealthCheckStatus(str, Enum):
    """Health check status values."""

    PASSING = "passing"
    FAILING = "failing"
    WARNING = "warning"
    UNKNOWN = "unknown"


class AgentStatus(BaseModel):
    """Status information for an agent.

    Task T073: Create AgentStatus Pydantic model

    Tracks the operational status of an agent including health checks,
    last seen timestamp, and any relevant metrics.
    """

    agent_name: str = Field(..., description="Name of the agent")
    status: AgentStatusValue = Field(
        default=AgentStatusValue.UNKNOWN,
        description="Current operational status"
    )
    health_check: HealthCheckStatus = Field(
        default=HealthCheckStatus.UNKNOWN,
        description="Latest health check status"
    )
    last_seen: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="ISO timestamp of last activity"
    )
    endpoint: str | None = Field(
        default=None,
        description="Agent's endpoint URL"
    )
    version: str | None = Field(
        default=None,
        description="Agent version"
    )
    metrics: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional metrics about the agent"
    )
    error_message: str | None = Field(
        default=None,
        description="Error message if status is degraded or inactive"
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="ISO timestamp of last status update"
    )

    def is_healthy(self) -> bool:
        """Check if the agent is in a healthy state.

        Returns:
            True if status is active and health check is passing
        """
        return (
            self.status == AgentStatusValue.ACTIVE
            and self.health_check == HealthCheckStatus.PASSING
        )

    def mark_active(self) -> None:
        """Mark the agent as active."""
        self.status = AgentStatusValue.ACTIVE
        self.last_seen = datetime.utcnow().isoformat()
        self.updated_at = datetime.utcnow().isoformat()

    def mark_inactive(self, reason: str | None = None) -> None:
        """Mark the agent as inactive.

        Args:
            reason: Optional reason for inactivity
        """
        self.status = AgentStatusValue.INACTIVE
        self.error_message = reason
        self.updated_at = datetime.utcnow().isoformat()

    def update_health_check(self, status: HealthCheckStatus) -> None:
        """Update the health check status.

        Args:
            status: New health check status
        """
        self.health_check = status
        self.last_seen = datetime.utcnow().isoformat()
        self.updated_at = datetime.utcnow().isoformat()


class AgentStatusSummary(BaseModel):
    """Summary of agent statuses across the registry."""

    total_agents: int = Field(default=0, description="Total number of agents")
    active_count: int = Field(default=0, description="Number of active agents")
    inactive_count: int = Field(default=0, description="Number of inactive agents")
    degraded_count: int = Field(default=0, description="Number of degraded agents")
    healthy_count: int = Field(default=0, description="Number of healthy agents")
    unhealthy_count: int = Field(default=0, description="Number of unhealthy agents")
