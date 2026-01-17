"""Loop framework data models.

This module defines the data entities for the Agent Loop Framework including:
- Configuration models (LoopConfig, ExitConditionConfig)
- State tracking models (LoopState, ExitConditionStatus)
- Result models (LoopResult, IterationEvent)
- Checkpoint model for Memory persistence

All models use Pydantic for validation and serialization, following patterns
established in src/registry/models.py.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

# =============================================================================
# T007-T011: Enums
# =============================================================================


class ExitConditionType(str, Enum):
    """Standard exit condition types supported by the framework.

    Maps to FR-004: Framework MUST support standard exit conditions.

    Attributes:
        ALL_TESTS_PASS: All tests must pass (pytest, etc.)
        BUILD_SUCCEEDS: Build/compile must succeed
        LINTING_CLEAN: No linting errors (ruff, etc.)
        SECURITY_SCAN_CLEAN: No security vulnerabilities
        CUSTOM: User-defined condition with custom evaluator
    """

    ALL_TESTS_PASS = "all_tests_pass"
    BUILD_SUCCEEDS = "build_succeeds"
    LINTING_CLEAN = "linting_clean"
    SECURITY_SCAN_CLEAN = "security_scan_clean"
    CUSTOM = "custom"


class ExitConditionStatusValue(str, Enum):
    """Evaluation status of an exit condition.

    Attributes:
        PENDING: Not yet evaluated
        MET: Condition satisfied
        NOT_MET: Condition not satisfied
        ERROR: Evaluation failed (timeout, tool error)
        SKIPPED: Intentionally skipped this iteration
    """

    PENDING = "pending"
    MET = "met"
    NOT_MET = "not_met"
    ERROR = "error"
    SKIPPED = "skipped"


class LoopPhase(str, Enum):
    """Phase of loop execution.

    Maps to FR-013: Agent code MUST implement loop logic to prevent re-entry.

    Attributes:
        INITIALIZING: Loop is being set up
        RUNNING: Loop is actively executing iterations
        EVALUATING_CONDITIONS: Checking exit conditions
        SAVING_CHECKPOINT: Persisting state to Memory
        COMPLETING: Loop is finishing up
        COMPLETED: Loop has finished successfully
        ERROR: Loop encountered an unrecoverable error
    """

    INITIALIZING = "initializing"
    RUNNING = "running"
    EVALUATING_CONDITIONS = "evaluating_conditions"
    SAVING_CHECKPOINT = "saving_checkpoint"
    COMPLETING = "completing"
    COMPLETED = "completed"
    ERROR = "error"


class LoopOutcome(str, Enum):
    """Possible outcomes of loop execution.

    Maps to SC-005: 100% terminate appropriately.

    Attributes:
        COMPLETED: All exit conditions met
        ITERATION_LIMIT: Policy stopped at max iterations
        ERROR: Unrecoverable error occurred
        CANCELLED: Manual cancellation
        TIMEOUT: Overall loop timeout exceeded
    """

    COMPLETED = "completed"
    ITERATION_LIMIT = "iteration_limit"
    ERROR = "error"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class IterationEventType(str, Enum):
    """Types of events emitted to Observability.

    Maps to FR-014: Emit OTEL traces recording start/completion time.

    Attributes:
        LOOP_STARTED: Loop has started
        ITERATION_STARTED: New iteration has begun
        ITERATION_COMPLETED: Iteration has finished
        CHECKPOINT_SAVED: Checkpoint was saved to Memory
        EXIT_CONDITION_EVALUATED: An exit condition was evaluated
        LOOP_COMPLETED: Loop has finished
        LOOP_ERROR: Loop encountered an error
        POLICY_WARNING: Approaching iteration limit
        POLICY_VIOLATION: Iteration limit exceeded
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


# =============================================================================
# T012: ExitConditionConfig
# =============================================================================


class ExitConditionConfig(BaseModel):
    """Configuration for a single exit condition.

    Maps to FR-003: Framework MUST provide exit condition evaluation helpers.
    Maps to FR-004: Support standard exit conditions.

    Example:
        config = ExitConditionConfig(
            type=ExitConditionType.ALL_TESTS_PASS,
            tool_name="pytest",
            tool_arguments={"path": "tests/"},
        )
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


# =============================================================================
# T013: ExitConditionStatus
# =============================================================================


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
        """Mark condition as met after successful evaluation.

        Args:
            tool_name: Name of the verification tool used
            exit_code: Exit code from the tool (should be 0)
            output: Output from the tool
            iteration: Current iteration number
        """
        self.status = ExitConditionStatusValue.MET
        self.tool_name = tool_name
        self.tool_exit_code = exit_code
        self.tool_output = output[:1000]  # Truncate for storage
        self.evaluated_at = datetime.now(UTC).isoformat()
        self.iteration_evaluated = iteration

    def mark_not_met(self, tool_name: str, exit_code: int, output: str, iteration: int) -> None:
        """Mark condition as not met after evaluation.

        Args:
            tool_name: Name of the verification tool used
            exit_code: Exit code from the tool (non-zero)
            output: Output from the tool
            iteration: Current iteration number
        """
        self.status = ExitConditionStatusValue.NOT_MET
        self.tool_name = tool_name
        self.tool_exit_code = exit_code
        self.tool_output = output[:1000]
        self.evaluated_at = datetime.now(UTC).isoformat()
        self.iteration_evaluated = iteration

    def mark_error(self, error: str, iteration: int) -> None:
        """Mark condition as error (timeout, tool failure).

        Args:
            error: Error message describing the failure
            iteration: Current iteration number
        """
        self.status = ExitConditionStatusValue.ERROR
        self.error_message = error
        self.evaluated_at = datetime.now(UTC).isoformat()
        self.iteration_evaluated = iteration

    def mark_skipped(self, reason: str, iteration: int) -> None:
        """Mark condition as skipped for this iteration.

        Args:
            reason: Reason for skipping
            iteration: Current iteration number
        """
        self.status = ExitConditionStatusValue.SKIPPED
        self.error_message = reason
        self.evaluated_at = datetime.now(UTC).isoformat()
        self.iteration_evaluated = iteration

    def is_terminal(self) -> bool:
        """Check if condition is in a terminal state (met or error).

        Returns:
            True if condition is MET or ERROR
        """
        return self.status in (
            ExitConditionStatusValue.MET,
            ExitConditionStatusValue.ERROR,
        )

    def reset(self) -> None:
        """Reset condition to pending state for re-evaluation."""
        self.status = ExitConditionStatusValue.PENDING
        self.tool_exit_code = None
        self.tool_output = None
        self.evaluated_at = None
        self.evaluation_duration_ms = None
        self.error_message = None
        self.iteration_evaluated = None


# =============================================================================
# T014: LoopConfig
# =============================================================================


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

    exit_conditions: list[ExitConditionConfig] = Field(
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
    def validate_exit_conditions(cls, v: list[ExitConditionConfig]) -> list[ExitConditionConfig]:
        """Ensure exit conditions are valid.

        Empty list is allowed - loop runs until iteration limit.
        Custom conditions must have a custom_evaluator defined.
        """
        for condition in v:
            if condition.type == ExitConditionType.CUSTOM and not condition.custom_evaluator:
                raise ValueError("CUSTOM exit condition type requires custom_evaluator to be set")
        return v


# =============================================================================
# T015: IterationEvent
# =============================================================================


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
        attrs: dict[str, Any] = {
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

    def progress_percentage(self) -> float:
        """Calculate progress as percentage of max iterations.

        Returns:
            Progress percentage (0-100)
        """
        if self.max_iterations <= 0:
            return 0.0
        return (self.iteration / self.max_iterations) * 100


# =============================================================================
# T016: LoopResult
# =============================================================================


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
        """Check if loop completed successfully (all conditions met).

        Returns:
            True if outcome is COMPLETED
        """
        return self.outcome == LoopOutcome.COMPLETED

    def summary(self) -> str:
        """Generate human-readable summary of loop result.

        Returns:
            Multi-line summary string
        """
        conditions_met = sum(
            1 for c in self.final_exit_conditions if c.status == ExitConditionStatusValue.MET
        )
        total_conditions = len(self.final_exit_conditions)

        return (
            f"Loop {self.session_id}: {self.outcome.value}\n"
            f"  Iterations: {self.iterations_completed}/{self.max_iterations}\n"
            f"  Duration: {self.duration_seconds:.1f}s\n"
            f"  Exit conditions: {conditions_met}/{total_conditions} met"
        )

    def conditions_summary(self) -> dict[str, int]:
        """Get a summary of exit condition statuses.

        Returns:
            Dictionary with counts per status value
        """
        summary: dict[str, int] = {status.value: 0 for status in ExitConditionStatusValue}
        for condition in self.final_exit_conditions:
            summary[condition.status.value] += 1
        return summary


# =============================================================================
# T024: LoopState
# =============================================================================


class LoopState(BaseModel):
    """Current state of loop execution.

    Internal model managed by LoopFramework. Serialized into Checkpoint.

    Maps to FR-006: Checkpoint MUST include iteration number, state, timestamp.
    Maps to FR-013: Prevent re-entry during active execution.

    Example:
        state = LoopState(
            session_id="loop-session-123",
            agent_name="test-agent",
            max_iterations=100,
        )
        state.current_iteration = 5
        state.phase = LoopPhase.RUNNING
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

    exit_conditions: list[ExitConditionStatus] = Field(
        default_factory=list,
        description="Current status of each exit condition",
    )

    is_active: bool = Field(
        default=False,
        description="True if loop is currently executing (prevents re-entry)",
    )

    agent_state: dict[str, Any] = Field(
        default_factory=dict,
        description="Agent-specific state data",
    )

    def all_conditions_met(self) -> bool:
        """Check if all exit conditions are met.

        Maps to FR-007: Agent MUST terminate when all conditions met.

        Returns:
            True if all exit conditions are MET, False otherwise
        """
        if not self.exit_conditions:
            return False
        return all(c.status == ExitConditionStatusValue.MET for c in self.exit_conditions)

    def progress_percentage(self) -> float:
        """Calculate progress as percentage of max iterations.

        Returns:
            Progress percentage (0-100)
        """
        return (self.current_iteration / self.max_iterations) * 100

    def at_warning_threshold(self, threshold: float = 0.8) -> bool:
        """Check if approaching iteration limit (SC-008: 80% threshold).

        Args:
            threshold: Warning threshold as fraction (default 0.8 = 80%)

        Returns:
            True if progress >= threshold percentage
        """
        return self.progress_percentage() >= (threshold * 100)
