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

import asyncio
import uuid
from typing import Any, Callable

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from src.loop.models import (
    ExitConditionStatus,
    ExitConditionStatusValue,
    IterationEvent,
    IterationEventType,
    LoopConfig,
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
        tracer = trace.get_tracer(f"loop.framework.{agent_name}")
        return tracer

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
    ) -> LoopResult:
        """Run the autonomous loop.

        Maps to T028: Implement LoopFramework.run() main loop logic.

        This is a placeholder that will be implemented in subsequent tasks.

        Args:
            work_function: Async function to call each iteration
            initial_state: Optional initial agent state

        Returns:
            LoopResult with final outcome
        """
        # TODO: Implement in T028
        raise NotImplementedError("LoopFramework.run() will be implemented in T028")

    async def emit_event(
        self,
        event_type: IterationEventType,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Emit an event to Observability.

        Maps to T035: Implement LoopFramework.emit_event() for Observability.

        This is a placeholder that will be implemented in subsequent tasks.

        Args:
            event_type: Type of event to emit
            details: Optional event-specific details
        """
        # TODO: Implement in T035
        pass

    async def save_checkpoint(self, custom_data: dict[str, Any] | None = None) -> None:
        """Save a checkpoint to Memory.

        This is a placeholder for future checkpoint functionality (US2).

        Args:
            custom_data: Optional custom data to include in checkpoint
        """
        # TODO: Implement in Phase 5 (User Story 2)
        pass
