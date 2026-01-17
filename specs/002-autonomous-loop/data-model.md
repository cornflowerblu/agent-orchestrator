# Data Model: Autonomous Loop Execution

**Branch**: `002-autonomous-loop` | **Date**: 2026-01-17 | **Spec**: [spec.md](./spec.md)
**Research**: [research.md](./research.md) | **Plan**: [plan.md](./plan.md)

## Overview

This document defines the data entities for the Agent Loop Framework. All models use Pydantic for validation and serialization, following patterns established in the existing codebase (`src/registry/models.py`, `src/metadata/models.py`).

---

## Entity Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Agent Loop Framework                                │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌──────────────┐      ┌───────────────┐      ┌─────────────────────────────────┐│
│  │  LoopConfig  │─────▶│   LoopState   │─────▶│         Checkpoint              ││
│  │              │      │               │      │  (stored in AgentCore Memory)   ││
│  │ - max_iters  │      │ - iteration   │      │  - iteration                    ││
│  │ - interval   │      │ - phase       │      │  - state                        ││
│  │ - conditions │      │ - timestamps  │      │  - exit_conditions              ││
│  └──────────────┘      └───────────────┘      └─────────────────────────────────┘│
│         │                     │                              ▲                   │
│         │                     │                              │                   │
│         ▼                     ▼                              │                   │
│  ┌──────────────────────────────────────────────────────────────────────────────┐│
│  │                           ExitCondition[]                                    ││
│  │  - type (all_tests_pass, build_succeeds, linting_clean, security_scan_clean) ││
│  │  - status (pending, met, not_met, error)                                     ││
│  │  - tool_name, tool_output                                                    ││
│  └──────────────────────────────────────────────────────────────────────────────┘│
│                                      │                                           │
│                                      ▼                                           │
│  ┌──────────────────────────────────────────────────────────────────────────────┐│
│  │                           IterationEvent                                     ││
│  │  (emitted to AgentCore Observability as OTEL spans)                         ││
│  │  - span_kind: loop.iteration, loop.checkpoint, loop.exit_condition          ││
│  └──────────────────────────────────────────────────────────────────────────────┘│
│                                      │                                           │
│                                      ▼                                           │
│  ┌──────────────────────────────────────────────────────────────────────────────┐│
│  │                              LoopResult                                      ││
│  │  - outcome (completed, iteration_limit, error, cancelled)                   ││
│  │  - final_state, duration, iterations_used                                   ││
│  └──────────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 1. LoopConfig

Configuration for an autonomous loop execution. Passed to `LoopFramework.initialize()`.

### Pydantic Model

```python
"""Loop configuration model.

File: src/loop/models.py
"""

from datetime import timedelta
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ExitConditionType(str, Enum):
    """Standard exit condition types supported by the framework.

    Maps to FR-004: Framework MUST support standard exit conditions.
    """

    ALL_TESTS_PASS = "all_tests_pass"
    BUILD_SUCCEEDS = "build_succeeds"
    LINTING_CLEAN = "linting_clean"
    SECURITY_SCAN_CLEAN = "security_scan_clean"
    CUSTOM = "custom"  # For user-defined conditions


class LoopConfig(BaseModel):
    """Configuration for autonomous loop execution.

    Maps to FR-001: Loop Framework MUST provide initialization helpers.
    Maps to FR-002: Policy MUST support configurable iteration limits.
    Maps to FR-005: Framework MUST provide checkpoint save helpers.

    Example:
        config = LoopConfig(
            agent_name="test-runner-agent",
            max_iterations=100,
            checkpoint_interval=5,
            exit_conditions=[
                ExitConditionConfig(type=ExitConditionType.ALL_TESTS_PASS),
                ExitConditionConfig(type=ExitConditionType.BUILD_SUCCEEDS),
            ],
        )
        framework = LoopFramework.initialize(config)
    """

    agent_name: str = Field(
        ...,
        description="Name of the agent executing the loop",
        min_length=1,
        max_length=64,
    )

    session_id: str | None = Field(
        default=None,
        description="Optional session ID for Memory storage. Auto-generated if not provided.",
    )

    max_iterations: int = Field(
        default=100,
        description="Maximum iterations before Policy terminates loop",
        ge=1,
        le=10000,
    )

    checkpoint_interval: int = Field(
        default=5,
        description="Save checkpoint every N iterations to Memory",
        ge=1,
        le=100,
    )

    checkpoint_expiry_seconds: int = Field(
        default=86400,  # 24 hours
        description="Memory event expiry for checkpoints (eventExpiryDuration)",
        ge=3600,  # 1 hour minimum
        le=604800,  # 7 days maximum
    )

    exit_conditions: list["ExitConditionConfig"] = Field(
        default_factory=list,
        description="Exit conditions to evaluate each iteration",
    )

    iteration_timeout_seconds: int = Field(
        default=300,  # 5 minutes
        description="Maximum time per iteration before timeout",
        ge=30,
        le=3600,
    )

    verification_timeout_seconds: int = Field(
        default=30,
        description="Maximum time per verification tool invocation (SC-002)",
        ge=5,
        le=120,
    )

    policy_engine_arn: str | None = Field(
        default=None,
        description="ARN of Cedar policy engine for iteration limit enforcement",
    )

    gateway_url: str | None = Field(
        default=None,
        description="URL of AgentCore Gateway for MCP tool discovery",
    )

    region: str = Field(
        default="us-east-1",
        description="AWS region for AgentCore services",
    )

    custom_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional metadata to include in checkpoints and traces",
    )

    @field_validator("exit_conditions")
    @classmethod
    def validate_exit_conditions(cls, v: list) -> list:
        """Ensure at least one exit condition or allow empty for manual control."""
        # Empty list is allowed - loop runs until iteration limit
        return v


class ExitConditionConfig(BaseModel):
    """Configuration for a single exit condition.

    Maps to FR-003: Framework MUST provide exit condition evaluation helpers.
    Maps to FR-004: Support standard exit conditions.
    """

    type: ExitConditionType = Field(
        ...,
        description="Type of exit condition to evaluate",
    )

    tool_name: str | None = Field(
        default=None,
        description="Specific tool to invoke (auto-detected if not provided)",
    )

    tool_arguments: dict[str, Any] = Field(
        default_factory=dict,
        description="Arguments to pass to verification tool",
    )

    custom_evaluator: str | None = Field(
        default=None,
        description="Python callable path for CUSTOM type (e.g., 'mymodule.check_custom')",
    )

    description: str = Field(
        default="",
        description="Human-readable description of this condition",
    )
```

### JSON Schema (for contracts/)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "LoopConfig",
  "type": "object",
  "required": ["agent_name"],
  "properties": {
    "agent_name": { "type": "string", "minLength": 1, "maxLength": 64 },
    "session_id": { "type": ["string", "null"] },
    "max_iterations": { "type": "integer", "minimum": 1, "maximum": 10000, "default": 100 },
    "checkpoint_interval": { "type": "integer", "minimum": 1, "maximum": 100, "default": 5 },
    "checkpoint_expiry_seconds": { "type": "integer", "minimum": 3600, "maximum": 604800, "default": 86400 },
    "exit_conditions": { "type": "array", "items": { "$ref": "#/$defs/ExitConditionConfig" } },
    "iteration_timeout_seconds": { "type": "integer", "minimum": 30, "maximum": 3600, "default": 300 },
    "verification_timeout_seconds": { "type": "integer", "minimum": 5, "maximum": 120, "default": 30 },
    "policy_engine_arn": { "type": ["string", "null"] },
    "gateway_url": { "type": ["string", "null"] },
    "region": { "type": "string", "default": "us-east-1" },
    "custom_metadata": { "type": "object", "additionalProperties": true }
  },
  "$defs": {
    "ExitConditionConfig": {
      "type": "object",
      "required": ["type"],
      "properties": {
        "type": { "enum": ["all_tests_pass", "build_succeeds", "linting_clean", "security_scan_clean", "custom"] },
        "tool_name": { "type": ["string", "null"] },
        "tool_arguments": { "type": "object", "additionalProperties": true },
        "custom_evaluator": { "type": ["string", "null"] },
        "description": { "type": "string", "default": "" }
      }
    }
  }
}
```

---

## 2. LoopState

Current state of an executing loop. Managed internally by `LoopFramework`.

### Pydantic Model

```python
"""Loop state tracking model.

File: src/loop/models.py
"""

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field


class LoopPhase(str, Enum):
    """Phase of loop execution.

    Maps to FR-013: Agent code MUST implement loop logic to prevent re-entry.
    """

    INITIALIZING = "initializing"
    RUNNING = "running"
    EVALUATING_CONDITIONS = "evaluating_conditions"
    SAVING_CHECKPOINT = "saving_checkpoint"
    COMPLETING = "completing"
    COMPLETED = "completed"
    ERROR = "error"


class LoopState(BaseModel):
    """Current state of loop execution.

    Internal model managed by LoopFramework. Serialized into Checkpoint.

    Maps to FR-006: Checkpoint MUST include iteration number, state, timestamp.
    Maps to FR-013: Prevent re-entry during active execution.
    """

    session_id: str = Field(
        ...,
        description="Unique identifier for this loop session",
    )

    agent_name: str = Field(
        ...,
        description="Name of the executing agent",
    )

    current_iteration: int = Field(
        default=0,
        description="Current iteration number (0-indexed)",
        ge=0,
    )

    max_iterations: int = Field(
        ...,
        description="Maximum iterations allowed by Policy",
        ge=1,
    )

    phase: LoopPhase = Field(
        default=LoopPhase.INITIALIZING,
        description="Current execution phase",
    )

    started_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="ISO timestamp when loop started (FR-014)",
    )

    last_iteration_at: str | None = Field(
        default=None,
        description="ISO timestamp of last completed iteration",
    )

    last_checkpoint_at: str | None = Field(
        default=None,
        description="ISO timestamp of last checkpoint save",
    )

    last_checkpoint_iteration: int | None = Field(
        default=None,
        description="Iteration number of last checkpoint",
    )

    exit_conditions: list["ExitConditionStatus"] = Field(
        default_factory=list,
        description="Current status of each exit condition",
    )

    is_active: bool = Field(
        default=False,
        description="True if loop is currently executing (prevents re-entry)",
    )

    agent_state: dict = Field(
        default_factory=dict,
        description="Agent-specific state data",
    )

    def all_conditions_met(self) -> bool:
        """Check if all exit conditions are met.

        Maps to FR-007: Agent MUST terminate when all conditions met.
        """
        if not self.exit_conditions:
            return False
        return all(c.status == ExitConditionStatusValue.MET for c in self.exit_conditions)

    def progress_percentage(self) -> float:
        """Calculate progress as percentage of max iterations."""
        return (self.current_iteration / self.max_iterations) * 100

    def at_warning_threshold(self, threshold: float = 0.8) -> bool:
        """Check if approaching iteration limit (SC-008: 80% threshold)."""
        return self.progress_percentage() >= (threshold * 100)
```

---

## 3. ExitCondition Status

Status tracking for exit condition evaluations.

### Pydantic Model

```python
"""Exit condition status model.

File: src/loop/models.py
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ExitConditionStatusValue(str, Enum):
    """Evaluation status of an exit condition."""

    PENDING = "pending"  # Not yet evaluated
    MET = "met"  # Condition satisfied
    NOT_MET = "not_met"  # Condition not satisfied
    ERROR = "error"  # Evaluation failed (timeout, tool error)
    SKIPPED = "skipped"  # Intentionally skipped this iteration


class ExitConditionStatus(BaseModel):
    """Status of a single exit condition evaluation.

    Maps to FR-003: Exit condition evaluation helpers.
    Maps to FR-006: Checkpoint includes exit condition status.

    Example (from Observability trace):
        {
            "type": "all_tests_pass",
            "status": "met",
            "tool_name": "pytest",
            "evaluated_at": "2026-01-17T10:30:00Z",
            "tool_exit_code": 0,
            "tool_output": "15 passed in 2.3s"
        }
    """

    type: ExitConditionType = Field(
        ...,
        description="Type of exit condition",
    )

    status: ExitConditionStatusValue = Field(
        default=ExitConditionStatusValue.PENDING,
        description="Current evaluation status",
    )

    tool_name: str | None = Field(
        default=None,
        description="Verification tool used (pytest, ruff, etc.)",
    )

    tool_exit_code: int | None = Field(
        default=None,
        description="Exit code from verification tool",
    )

    tool_output: str | None = Field(
        default=None,
        description="Truncated output from verification tool",
    )

    evaluated_at: str | None = Field(
        default=None,
        description="ISO timestamp of last evaluation",
    )

    evaluation_duration_ms: int | None = Field(
        default=None,
        description="Time taken to evaluate (milliseconds)",
    )

    error_message: str | None = Field(
        default=None,
        description="Error details if status is ERROR",
    )

    iteration_evaluated: int | None = Field(
        default=None,
        description="Iteration number when last evaluated",
    )

    def mark_met(self, tool_name: str, exit_code: int, output: str, iteration: int) -> None:
        """Mark condition as met after successful evaluation."""
        self.status = ExitConditionStatusValue.MET
        self.tool_name = tool_name
        self.tool_exit_code = exit_code
        self.tool_output = output[:1000]  # Truncate for storage
        self.evaluated_at = datetime.now(UTC).isoformat()
        self.iteration_evaluated = iteration

    def mark_not_met(self, tool_name: str, exit_code: int, output: str, iteration: int) -> None:
        """Mark condition as not met after evaluation."""
        self.status = ExitConditionStatusValue.NOT_MET
        self.tool_name = tool_name
        self.tool_exit_code = exit_code
        self.tool_output = output[:1000]
        self.evaluated_at = datetime.now(UTC).isoformat()
        self.iteration_evaluated = iteration

    def mark_error(self, error: str, iteration: int) -> None:
        """Mark condition as error (timeout, tool failure)."""
        self.status = ExitConditionStatusValue.ERROR
        self.error_message = error
        self.evaluated_at = datetime.now(UTC).isoformat()
        self.iteration_evaluated = iteration
```

---

## 4. Checkpoint

Snapshot of loop state persisted to AgentCore Memory.

### Pydantic Model

```python
"""Checkpoint model for Memory persistence.

File: src/loop/models.py
"""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class Checkpoint(BaseModel):
    """Snapshot of loop state saved to AgentCore Memory.

    Maps to FR-005: Checkpoint persistence at configurable intervals.
    Maps to FR-006: Checkpoint includes iteration, state, timestamp, exit status.
    Maps to FR-012: Support loading state from Memory for recovery.

    Storage Pattern (from research.md):
        client.create_event(
            memory_id=memory.get("id"),
            actor_id=checkpoint.agent_name,
            session_id=checkpoint.session_id,
            messages=[(checkpoint.model_dump_json(), "TOOL")]
        )
    """

    checkpoint_id: str = Field(
        ...,
        description="Unique identifier for this checkpoint",
    )

    session_id: str = Field(
        ...,
        description="Loop session ID for Memory service",
    )

    agent_name: str = Field(
        ...,
        description="Agent that created this checkpoint",
    )

    iteration: int = Field(
        ...,
        description="Iteration number when checkpoint was saved",
        ge=0,
    )

    max_iterations: int = Field(
        ...,
        description="Max iterations configured for this loop",
    )

    phase: LoopPhase = Field(
        ...,
        description="Loop phase at checkpoint time",
    )

    agent_state: dict[str, Any] = Field(
        default_factory=dict,
        description="Agent-specific state to restore on recovery",
    )

    exit_conditions: list[ExitConditionStatus] = Field(
        default_factory=list,
        description="Exit condition statuses at checkpoint time",
    )

    custom_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Custom data passed to save_checkpoint()",
    )

    created_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="ISO timestamp when checkpoint was created",
    )

    memory_event_id: str | None = Field(
        default=None,
        description="ID assigned by AgentCore Memory after save",
    )

    @classmethod
    def from_loop_state(
        cls,
        state: LoopState,
        checkpoint_id: str,
        custom_data: dict[str, Any] | None = None,
    ) -> "Checkpoint":
        """Create checkpoint from current loop state.

        Args:
            state: Current LoopState to snapshot
            checkpoint_id: Unique ID for this checkpoint
            custom_data: Optional custom data to include

        Returns:
            Checkpoint ready for Memory persistence
        """
        return cls(
            checkpoint_id=checkpoint_id,
            session_id=state.session_id,
            agent_name=state.agent_name,
            iteration=state.current_iteration,
            max_iterations=state.max_iterations,
            phase=state.phase,
            agent_state=state.agent_state.copy(),
            exit_conditions=state.exit_conditions.copy(),
            custom_data=custom_data or {},
        )

    def to_loop_state(self) -> LoopState:
        """Restore LoopState from checkpoint for recovery.

        Maps to FR-012: Load state from Memory for recovery.
        Maps to SC-006: Recovery within one iteration of checkpoint.

        Returns:
            LoopState restored from checkpoint
        """
        return LoopState(
            session_id=self.session_id,
            agent_name=self.agent_name,
            current_iteration=self.iteration,
            max_iterations=self.max_iterations,
            phase=LoopPhase.RUNNING,  # Resume in running state
            exit_conditions=self.exit_conditions.copy(),
            agent_state=self.agent_state.copy(),
            last_checkpoint_at=self.created_at,
            last_checkpoint_iteration=self.iteration,
            is_active=False,  # Not active until run() called
        )
```

### JSON Schema (for Memory storage)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "Checkpoint",
  "type": "object",
  "required": ["checkpoint_id", "session_id", "agent_name", "iteration", "max_iterations", "phase", "created_at"],
  "properties": {
    "checkpoint_id": { "type": "string" },
    "session_id": { "type": "string" },
    "agent_name": { "type": "string" },
    "iteration": { "type": "integer", "minimum": 0 },
    "max_iterations": { "type": "integer", "minimum": 1 },
    "phase": { "enum": ["initializing", "running", "evaluating_conditions", "saving_checkpoint", "completing", "completed", "error"] },
    "agent_state": { "type": "object", "additionalProperties": true },
    "exit_conditions": {
      "type": "array",
      "items": { "$ref": "#/$defs/ExitConditionStatus" }
    },
    "custom_data": { "type": "object", "additionalProperties": true },
    "created_at": { "type": "string", "format": "date-time" },
    "memory_event_id": { "type": ["string", "null"] }
  },
  "$defs": {
    "ExitConditionStatus": {
      "type": "object",
      "required": ["type", "status"],
      "properties": {
        "type": { "enum": ["all_tests_pass", "build_succeeds", "linting_clean", "security_scan_clean", "custom"] },
        "status": { "enum": ["pending", "met", "not_met", "error", "skipped"] },
        "tool_name": { "type": ["string", "null"] },
        "tool_exit_code": { "type": ["integer", "null"] },
        "tool_output": { "type": ["string", "null"] },
        "evaluated_at": { "type": ["string", "null"], "format": "date-time" },
        "evaluation_duration_ms": { "type": ["integer", "null"] },
        "error_message": { "type": ["string", "null"] },
        "iteration_evaluated": { "type": ["integer", "null"] }
      }
    }
  }
}
```

---

## 5. IterationEvent

Event emitted to AgentCore Observability for progress tracking.

### Pydantic Model

```python
"""Iteration event model for Observability.

File: src/loop/models.py
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class IterationEventType(str, Enum):
    """Types of events emitted to Observability.

    Maps to FR-014: Emit OTEL traces recording start/completion time.
    """

    LOOP_STARTED = "loop.started"
    ITERATION_STARTED = "loop.iteration.started"
    ITERATION_COMPLETED = "loop.iteration.completed"
    CHECKPOINT_SAVED = "loop.checkpoint.saved"
    EXIT_CONDITION_EVALUATED = "loop.exit_condition.evaluated"
    LOOP_COMPLETED = "loop.completed"
    LOOP_ERROR = "loop.error"
    POLICY_WARNING = "loop.policy.warning"
    POLICY_VIOLATION = "loop.policy.violation"


class IterationEvent(BaseModel):
    """Event for AgentCore Observability (OTEL span).

    Maps to FR-009: Dashboard queries Observability for progress.
    Maps to FR-010: Orchestrator monitors and issues warnings.
    Maps to FR-014: Emit traces for start/completion time.

    OTEL Mapping (from research.md):
        with tracer.start_as_current_span("loop.iteration", context=ctx) as span:
            span.set_attribute("iteration.number", event.iteration)
            span.set_attribute("iteration.max", event.max_iterations)
            span.set_attribute("loop.agent_name", event.agent_name)
            span.set_attribute("loop.session_id", event.session_id)
    """

    event_type: IterationEventType = Field(
        ...,
        description="Type of iteration event",
    )

    session_id: str = Field(
        ...,
        description="Loop session ID for trace correlation",
    )

    agent_name: str = Field(
        ...,
        description="Agent emitting the event",
    )

    iteration: int = Field(
        ...,
        description="Current iteration number",
        ge=0,
    )

    max_iterations: int = Field(
        ...,
        description="Maximum iterations allowed",
    )

    timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="ISO timestamp of event",
    )

    duration_ms: int | None = Field(
        default=None,
        description="Duration in milliseconds (for completed events)",
    )

    exit_conditions_met: int = Field(
        default=0,
        description="Number of exit conditions currently met",
    )

    exit_conditions_total: int = Field(
        default=0,
        description="Total number of exit conditions",
    )

    phase: LoopPhase = Field(
        default=LoopPhase.RUNNING,
        description="Current loop phase",
    )

    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional event-specific details",
    )

    error_message: str | None = Field(
        default=None,
        description="Error details for ERROR event type",
    )

    def to_otel_attributes(self) -> dict[str, Any]:
        """Convert to OTEL span attributes.

        Returns:
            Dictionary of attributes for span.set_attributes()
        """
        attrs = {
            "event.type": self.event_type.value,
            "session.id": self.session_id,
            "loop.agent_name": self.agent_name,
            "iteration.number": self.iteration,
            "iteration.max": self.max_iterations,
            "loop.phase": self.phase.value,
            "exit_conditions.met": self.exit_conditions_met,
            "exit_conditions.total": self.exit_conditions_total,
            "gen_ai.operation.name": "autonomous_loop",
            "PlatformType": "AWS::BedrockAgentCore",
        }
        if self.duration_ms is not None:
            attrs["duration.ms"] = self.duration_ms
        if self.error_message:
            attrs["error.message"] = self.error_message
        return attrs
```

---

## 6. LoopResult

Final outcome of loop execution.

### Pydantic Model

```python
"""Loop result model.

File: src/loop/models.py
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class LoopOutcome(str, Enum):
    """Possible outcomes of loop execution.

    Maps to SC-005: 100% terminate appropriately.
    """

    COMPLETED = "completed"  # All exit conditions met
    ITERATION_LIMIT = "iteration_limit"  # Policy stopped at max iterations
    ERROR = "error"  # Unrecoverable error occurred
    CANCELLED = "cancelled"  # Manual cancellation
    TIMEOUT = "timeout"  # Overall loop timeout exceeded


class LoopResult(BaseModel):
    """Final result of autonomous loop execution.

    Maps to SC-005: 100% of sessions terminate appropriately.
    Maps to FR-007: Terminate when all conditions met.
    Maps to FR-008: Terminate when iteration limit reached.
    """

    session_id: str = Field(
        ...,
        description="Loop session ID",
    )

    agent_name: str = Field(
        ...,
        description="Agent that executed the loop",
    )

    outcome: LoopOutcome = Field(
        ...,
        description="How the loop terminated",
    )

    iterations_completed: int = Field(
        ...,
        description="Total iterations completed",
        ge=0,
    )

    max_iterations: int = Field(
        ...,
        description="Maximum allowed iterations",
    )

    started_at: str = Field(
        ...,
        description="ISO timestamp when loop started",
    )

    completed_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="ISO timestamp when loop ended",
    )

    duration_seconds: float = Field(
        ...,
        description="Total execution time in seconds",
    )

    final_exit_conditions: list[ExitConditionStatus] = Field(
        default_factory=list,
        description="Final status of all exit conditions",
    )

    final_state: dict[str, Any] = Field(
        default_factory=dict,
        description="Agent state at termination",
    )

    last_checkpoint_id: str | None = Field(
        default=None,
        description="ID of last saved checkpoint",
    )

    error_message: str | None = Field(
        default=None,
        description="Error details if outcome is ERROR",
    )

    policy_violation_details: str | None = Field(
        default=None,
        description="Policy details if outcome is ITERATION_LIMIT",
    )

    def is_success(self) -> bool:
        """Check if loop completed successfully (all conditions met)."""
        return self.outcome == LoopOutcome.COMPLETED

    def summary(self) -> str:
        """Generate human-readable summary of loop result."""
        conditions_met = sum(
            1 for c in self.final_exit_conditions
            if c.status == ExitConditionStatusValue.MET
        )
        total_conditions = len(self.final_exit_conditions)

        return (
            f"Loop {self.session_id}: {self.outcome.value}\n"
            f"  Iterations: {self.iterations_completed}/{self.max_iterations}\n"
            f"  Duration: {self.duration_seconds:.1f}s\n"
            f"  Exit conditions: {conditions_met}/{total_conditions} met"
        )
```

---

## 7. PolicyConfig

Configuration for Cedar policy enforcement.

### Pydantic Model

```python
"""Policy configuration model.

File: src/orchestrator/models.py
"""

from pydantic import BaseModel, Field


class PolicyConfig(BaseModel):
    """Configuration for Cedar iteration limit policy.

    Maps to FR-002: Policy MUST support Cedar rules for iteration limits.
    Maps to FR-011: Administrators can update Policy rules.

    Cedar Statement Template (from research.md):
        permit(
          principal is AgentCore::Agent,
          action == AgentCore::Action::"loop_iteration",
          resource == AgentCore::Gateway::"{gateway_arn}"
        )
        when {
          context.input.current_iteration < context.input.max_iterations
        };
    """

    policy_engine_id: str = Field(
        ...,
        description="ID of Cedar policy engine",
    )

    policy_engine_arn: str = Field(
        ...,
        description="ARN of Cedar policy engine",
    )

    policy_name: str = Field(
        default="iteration_limit_policy",
        description="Name of the Cedar policy",
    )

    max_iterations: int = Field(
        default=100,
        description="Default max iterations for agents without specific config",
        ge=1,
        le=10000,
    )

    warning_threshold: float = Field(
        default=0.8,
        description="Percentage of max iterations that triggers warning (SC-008)",
        ge=0.5,
        le=0.95,
    )

    gateway_arn: str | None = Field(
        default=None,
        description="Gateway ARN for policy resource matching",
    )

    enforce_mode: bool = Field(
        default=True,
        description="True for ENFORCE mode, False for MONITOR only",
    )

    def generate_cedar_statement(self, agent_name: str, max_iterations: int) -> str:
        """Generate Cedar policy statement for an agent.

        Args:
            agent_name: Name of agent to create policy for
            max_iterations: Maximum iterations to allow

        Returns:
            Cedar policy statement string
        """
        return f'''
permit(
  principal is AgentCore::Agent,
  action == AgentCore::Action::"loop_iteration",
  resource == AgentCore::Gateway::"{self.gateway_arn or '*'}"
)
when {{
  context.input.agent_name == "{agent_name}" &&
  context.input.current_iteration < {max_iterations}
}};

forbid(
  principal is AgentCore::Agent,
  action == AgentCore::Action::"loop_iteration",
  resource
)
when {{
  context.input.agent_name == "{agent_name}" &&
  context.input.current_iteration >= {max_iterations}
}};
'''
```

---

## Summary

| Entity | Purpose | Storage | FR/SC Mapping |
|--------|---------|---------|---------------|
| **LoopConfig** | Initialize loop with parameters | Config file / Agent code | FR-001, FR-002, FR-005 |
| **LoopState** | Track current execution state | In-memory | FR-006, FR-013 |
| **ExitConditionConfig** | Configure conditions to evaluate | LoopConfig.exit_conditions | FR-003, FR-004 |
| **ExitConditionStatus** | Track condition evaluation results | LoopState, Checkpoint | FR-006 |
| **Checkpoint** | Persist state to Memory | AgentCore Memory | FR-005, FR-006, FR-012, SC-006 |
| **IterationEvent** | Emit progress to Observability | AgentCore Observability | FR-009, FR-010, FR-014 |
| **LoopResult** | Final execution outcome | Return value | FR-007, FR-008, SC-005 |
| **PolicyConfig** | Configure Cedar iteration limits | AgentCore Policy | FR-002, FR-011, SC-008 |

---

## Next Steps

1. **contracts/loop-framework.schema.json** - Combine JSON schemas for API validation
2. **quickstart.md** - Show how to use these models in agent implementation
