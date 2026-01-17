"""Agent Loop Framework for autonomous execution.

This module provides the core framework for implementing autonomous agent loops
with checkpoint management, exit condition evaluation, and progress tracking.

Modules:
    framework: Main LoopFramework class for autonomous execution
    checkpoint: CheckpointManager for Memory service integration
    conditions: ExitConditionEvaluator for verification tools
    models: Data models (LoopConfig, Checkpoint, ExitCondition, etc.)
"""

# Main framework class
# Checkpoint management
from src.loop.checkpoint import CheckpointManager

# Exit condition evaluation
from src.loop.conditions import ExitConditionEvaluator
from src.loop.framework import LoopFramework

# Core models
from src.loop.models import (
    Checkpoint,
    # Configuration
    ExitConditionConfig,
    ExitConditionStatus,
    ExitConditionStatusValue,
    # Enums
    ExitConditionType,
    IterationEvent,
    IterationEventType,
    LoopConfig,
    LoopOutcome,
    LoopPhase,
    # Results and events
    LoopResult,
    # State and status
    LoopState,
)

__all__ = [
    "Checkpoint",
    "CheckpointManager",
    # Configuration
    "ExitConditionConfig",
    "ExitConditionEvaluator",
    "ExitConditionStatus",
    "ExitConditionStatusValue",
    # Enums
    "ExitConditionType",
    "IterationEvent",
    "IterationEventType",
    "LoopConfig",
    # Framework
    "LoopFramework",
    "LoopOutcome",
    "LoopPhase",
    # Results and events
    "LoopResult",
    # State and status
    "LoopState",
]
