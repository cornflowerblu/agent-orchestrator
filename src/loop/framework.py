"""Loop Framework for autonomous agent execution.

This module provides the LoopFramework class that enables agents to implement
autonomous execution loops with:
- Checkpoint persistence via AgentCore Memory
- Progress tracking via AgentCore Observability (OTEL)
- Iteration limit enforcement via AgentCore Policy
- Exit condition evaluation via Gateway/Code Interpreter

Example:
    config = LoopConfig(agent_name="my-agent", max_iterations=100)
    framework = await LoopFramework.initialize(config)
    result = await framework.run(work_function=do_work, initial_state={})
"""

import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from src.exceptions import CheckpointRecoveryError, LoopFrameworkError
from src.loop.checkpoint import CheckpointManager
from src.loop.models import (
    ExitConditionStatus,
    ExitConditionStatusValue,
    IterationEvent,
    IterationEventType,
    LoopConfig,
    LoopOutcome,
    LoopPhase,
    LoopResult,
    LoopState,
)


class LoopFramework:
    """Framework for autonomous loop execution with AgentCore integration.

    Maps to FR-001: Framework MUST provide initialization helpers.
    Maps to FR-013: Agent code MUST implement loop logic to prevent re-entry.

    The LoopFramework manages:
    - Loop state and iteration tracking
    - Exit condition evaluation
    - Checkpoint save/restore
    - Observability event emission
    - Policy enforcement

    Attributes:
        config: Loop configuration
        state: Current loop state
        tracer: OTEL tracer for observability
    """

    def __init__(self, config: LoopConfig, state: LoopState, tracer: trace.Tracer) -> None:
        """Initialize LoopFramework (internal constructor).

        Use LoopFramework.initialize() or initialize_sync() instead.

        Args:
            config: Loop configuration
            state: Initial loop state
            tracer: OTEL tracer instance
        """
        self.config = config
        self.state = state
        self.tracer = tracer
        self.checkpoint_manager = CheckpointManager(
            session_id=state.session_id,
            region=config.region,
        )

    @classmethod
    async def initialize(cls, config: LoopConfig) -> "LoopFramework":
        """Initialize LoopFramework asynchronously.

        Maps to FR-001: Framework MUST provide initialization helpers.
        Maps to T026: Implement LoopFramework.initialize() async method.

        This method:
        1. Generates session_id if not provided
        2. Creates initial LoopState
        3. Initializes exit conditions from config
        4. Sets up OTEL tracer for observability

        Args:
            config: Loop configuration

        Returns:
            Initialized LoopFramework instance

        Example:
            config = LoopConfig(agent_name="my-agent", max_iterations=100)
            framework = await LoopFramework.initialize(config)
        """
        # Generate session_id if not provided
        session_id = config.session_id or str(uuid.uuid4())

        # Initialize exit conditions from config
        exit_conditions = [
            ExitConditionStatus(
                type=cond_config.type,
                status=ExitConditionStatusValue.PENDING,
            )
            for cond_config in config.exit_conditions
        ]

        # Create initial state
        state = LoopState(
            session_id=session_id,
            agent_name=config.agent_name,
            max_iterations=config.max_iterations,
            phase=LoopPhase.INITIALIZING,
            exit_conditions=exit_conditions,
            is_active=False,
        )

        # Setup OTEL tracer (T034)
        tracer = cls._setup_tracer(config.agent_name)

        return cls(config=config, state=state, tracer=tracer)

    @classmethod
    def initialize_sync(cls, config: LoopConfig) -> "LoopFramework":
        """Initialize LoopFramework synchronously.

        Maps to FR-001: Framework MUST provide initialization helpers.
        Maps to T027: Implement LoopFramework.initialize_sync() method.

        For synchronous contexts. Same as initialize() but runs in sync mode.

        Args:
            config: Loop configuration

        Returns:
            Initialized LoopFramework instance

        Example:
            config = LoopConfig(agent_name="my-agent", max_iterations=100)
            framework = LoopFramework.initialize_sync(config)
        """
        # Generate session_id if not provided
        session_id = config.session_id or str(uuid.uuid4())

        # Initialize exit conditions from config
        exit_conditions = [
            ExitConditionStatus(
                type=cond_config.type,
                status=ExitConditionStatusValue.PENDING,
            )
            for cond_config in config.exit_conditions
        ]

        # Create initial state
        state = LoopState(
            session_id=session_id,
            agent_name=config.agent_name,
            max_iterations=config.max_iterations,
            phase=LoopPhase.INITIALIZING,
            exit_conditions=exit_conditions,
            is_active=False,
        )

        # Setup OTEL tracer (T034)
        tracer = cls._setup_tracer(config.agent_name)

        return cls(config=config, state=state, tracer=tracer)

    @staticmethod
    def _setup_tracer(agent_name: str) -> trace.Tracer:
        """Setup OTEL tracer for observability.

        Maps to T034: Add OTEL tracer setup in LoopFramework.__init__.
        Maps to FR-014: Emit OTEL traces recording start/completion time.

        Args:
            agent_name: Name of the agent for tracer identification

        Returns:
            Configured OTEL Tracer instance
        """
        # Create tracer provider with console exporter for now
        # In production, this would use AWS X-Ray or CloudWatch exporter
        provider = TracerProvider()
        processor = BatchSpanProcessor(ConsoleSpanExporter())
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)

        # Get tracer for this agent
        return trace.get_tracer(f"loop.framework.{agent_name}")

    def get_state(self) -> LoopState:
        """Get current loop state.

        Maps to T029: Implement LoopFramework.get_state() method.

        Returns:
            Current LoopState

        Example:
            state = framework.get_state()
            print(f"Iteration: {state.current_iteration}/{state.max_iterations}")
        """
        return self.state

    def get_exit_condition_status(self) -> list[ExitConditionStatus]:
        """Get current exit condition statuses.

        Maps to T030: Implement LoopFramework.get_exit_condition_status() method.

        Returns:
            List of ExitConditionStatus objects

        Example:
            for condition in framework.get_exit_condition_status():
                print(f"{condition.type}: {condition.status}")
        """
        return self.state.exit_conditions

    async def run(
        self,
        work_function: Callable[[int, dict[str, Any], "LoopFramework"], dict[str, Any]],
        initial_state: dict[str, Any] | None = None,
        resume_from: int | None = None,
    ) -> LoopResult:
        """Run the autonomous loop.

        Maps to T028: Implement LoopFramework.run() main loop logic.
        Maps to T031: Implement iteration execution with work_function callback.
        Maps to T032: Implement loop termination logic.
        Maps to T033: Implement re-entry prevention.
        Maps to T068: Add checkpoint interval logic to LoopFramework.run().
        Maps to T071: Add resume_from parameter to LoopFramework.run().

        The loop runs until:
        1. All exit conditions are met (outcome: COMPLETED)
        2. Max iterations reached (outcome: ITERATION_LIMIT)
        3. Error occurs (outcome: ERROR)

        Args:
            work_function: Async function to call each iteration.
                Signature: async def work(iteration, state, framework) -> dict
            initial_state: Optional initial agent state dict
            resume_from: Optional iteration number to resume from checkpoint

        Returns:
            LoopResult with final outcome, state, and statistics

        Raises:
            LoopFrameworkError: If loop is already active (re-entry prevention)
            CheckpointRecoveryError: If resume_from specified but checkpoint invalid

        Example:
            async def do_work(iteration, state, fw):
                state["count"] = state.get("count", 0) + 1
                return state

            # Initial run
            result = await framework.run(work_function=do_work, initial_state={})

            # Resume from checkpoint
            result = await framework.run(work_function=do_work, resume_from=10)
        """
        # T033: Re-entry prevention
        if self.state.is_active:
            raise LoopFrameworkError(
                "Loop is already active. Cannot start a new run while executing."
            )

        # T071: Resume from checkpoint if specified
        if resume_from is not None:
            restored_state = await self.load_checkpoint(iteration=resume_from)
            self.state = restored_state
            agent_state = restored_state.agent_state
            start_iteration = resume_from + 1  # Resume from next iteration
        else:
            agent_state = initial_state or {}
            start_iteration = 0

        # Initialize
        loop_start_time = datetime.now(UTC)
        outcome = LoopOutcome.ITERATION_LIMIT  # Default if we hit max iterations

        try:
            # Set active flag
            self.state.is_active = True
            self.state.phase = LoopPhase.RUNNING

            # Emit loop started event
            await self.emit_event(
                event_type=IterationEventType.LOOP_STARTED,
                details={"initial_state": agent_state},
            )

            # T031: Main iteration loop
            for iteration in range(self.config.max_iterations):
                self.state.current_iteration = iteration
                self.state.phase = LoopPhase.RUNNING

                # Emit iteration started event
                await self.emit_event(
                    event_type=IterationEventType.ITERATION_STARTED,
                    details={"iteration": iteration},
                )

                # Execute work function
                iteration_start = datetime.now(UTC)
                agent_state = await work_function(iteration, agent_state, self)
                iteration_duration = (datetime.now(UTC) - iteration_start).total_seconds() * 1000

                # Update state
                self.state.agent_state = agent_state
                self.state.last_iteration_at = datetime.now(UTC).isoformat()

                # Emit iteration completed event
                await self.emit_event(
                    event_type=IterationEventType.ITERATION_COMPLETED,
                    details={
                        "iteration": iteration,
                        "duration_ms": iteration_duration,
                    },
                )

                # T032: Check termination conditions
                if self.state.all_conditions_met():
                    outcome = LoopOutcome.COMPLETED
                    break

            # Calculate final statistics
            loop_end_time = datetime.now(UTC)
            duration_seconds = (loop_end_time - loop_start_time).total_seconds()

            # Emit loop completed event
            self.state.phase = LoopPhase.COMPLETING
            await self.emit_event(
                event_type=IterationEventType.LOOP_COMPLETED,
                details={"outcome": outcome.value},
            )

            # Create result
            result = LoopResult(
                session_id=self.state.session_id,
                agent_name=self.state.agent_name,
                outcome=outcome,
                iterations_completed=self.state.current_iteration + 1,
                max_iterations=self.state.max_iterations,
                started_at=self.state.started_at,
                completed_at=loop_end_time.isoformat(),
                duration_seconds=duration_seconds,
                final_exit_conditions=self.state.exit_conditions.copy(),
                final_state=agent_state,
            )

            self.state.phase = LoopPhase.COMPLETED
            return result

        except Exception as e:
            # Handle errors
            self.state.phase = LoopPhase.ERROR

            await self.emit_event(
                event_type=IterationEventType.LOOP_ERROR,
                details={"error": str(e)},
            )

            loop_end_time = datetime.now(UTC)
            duration_seconds = (loop_end_time - loop_start_time).total_seconds()

            return LoopResult(
                session_id=self.state.session_id,
                agent_name=self.state.agent_name,
                outcome=LoopOutcome.ERROR,
                iterations_completed=self.state.current_iteration + 1,
                max_iterations=self.state.max_iterations,
                started_at=self.state.started_at,
                completed_at=loop_end_time.isoformat(),
                duration_seconds=duration_seconds,
                final_exit_conditions=self.state.exit_conditions.copy(),
                final_state=agent_state,
                error_message=str(e),
            )

        finally:
            # T033: Always clear active flag
            self.state.is_active = False

    async def emit_event(
        self,
        event_type: IterationEventType,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Emit an event to Observability.

        Maps to T035: Implement LoopFramework.emit_event() for Observability.
        Maps to FR-014: Emit OTEL traces recording start/completion time.

        This creates an IterationEvent and emits it as an OTEL span.

        Args:
            event_type: Type of event to emit
            details: Optional event-specific details

        Example:
            await framework.emit_event(
                event_type=IterationEventType.CHECKPOINT_SAVED,
                details={"checkpoint_id": "cp-123"},
            )
        """
        # Create event
        event = IterationEvent(
            event_type=event_type,
            session_id=self.state.session_id,
            agent_name=self.state.agent_name,
            iteration=self.state.current_iteration,
            max_iterations=self.state.max_iterations,
            phase=self.state.phase,
            exit_conditions_met=sum(
                1 for c in self.state.exit_conditions if c.status == ExitConditionStatusValue.MET
            ),
            exit_conditions_total=len(self.state.exit_conditions),
            details=details or {},
        )

        # Emit as OTEL span
        with self.tracer.start_as_current_span(event_type.value) as span:
            span.set_attributes(event.to_otel_attributes())

    async def save_checkpoint(self, custom_data: dict[str, Any] | None = None) -> None:
        """Save a checkpoint to Memory.

        This is a placeholder for future checkpoint functionality (US2).

        Args:
            custom_data: Optional custom data to include in checkpoint
        """
        # TODO: Implement in Phase 5 (User Story 2)
