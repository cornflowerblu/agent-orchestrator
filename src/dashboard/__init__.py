"""Dashboard module for progress monitoring.

This module provides query capabilities for monitoring autonomous agent
loop progress via AgentCore Observability service.

Modules:
    queries: ObservabilityQueries for trace/checkpoint queries
    handlers: API handlers for dashboard endpoints
    models: Response models for dashboard data
"""

# Query utilities
# API handlers
from src.dashboard.handlers import DashboardHandlers

# Response models
from src.dashboard.models import LoopProgress
from src.dashboard.queries import ObservabilityQueries

__all__ = [
    "DashboardHandlers",
    "LoopProgress",
    "ObservabilityQueries",
]
