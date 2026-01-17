"""Registry module for agent discovery and query."""

# Note: AgentDiscovery imports are lazy to avoid httpx dependency in Lambda
# Use: from src.registry.discovery import AgentDiscovery
from src.registry.models import (
    AgentStatus,
    AgentStatusSummary,
    AgentStatusValue,
    HealthCheckStatus,
)
from src.registry.query import AgentRegistry, CompatibilityResult
from src.registry.status import StatusStorage

__all__ = [
    "AgentRegistry",
    "AgentStatus",
    "AgentStatusSummary",
    "AgentStatusValue",
    "CompatibilityResult",
    "HealthCheckStatus",
    "StatusStorage",
]
