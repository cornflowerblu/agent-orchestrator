"""Unit tests for LoopFramework.

T037: Tests for LoopFramework initialization
T038: Tests for LoopFramework.run()
T039: Tests for loop termination conditions
T040: Tests for re-entry prevention
"""

import uuid

import pytest

from src.loop.framework import LoopFramework
from src.loop.models import (
    ExitConditionConfig,
    ExitConditionStatusValue,
    ExitConditionType,
    LoopConfig,
    LoopOutcome,
    LoopPhase,
    LoopState,
)

# =============================================================================
# Module-level fixture to mock Memory for all framework tests
# =============================================================================


@pytest.fixture(autouse=True)
def mock_memory_for_framework(mock_memory):
    """Auto-use mock_memory for all framework tests.

    LoopFramework uses CheckpointManager which needs Memory mocked.
    """
    return mock_memory


# =============================================================================
# T037: LoopFramework Initialization Tests
# =============================================================================


class TestLoopFrameworkInitialization:
    """Tests for LoopFramework initialization (T025, T026, T027)."""

    @pytest.mark.asyncio
    async def test_initialize_async_minimal_config(self) -> None:
        """Test async initialization with minimal config."""
        config = LoopConfig(
            agent_name="test-agent",
            max_iterations=50,
        )

        framework = await LoopFramework.initialize(config)

        assert framework is not None
        assert framework.config == config
        assert framework.state is not None
        assert framework.state.agent_name == "test-agent"
        assert framework.state.max_iterations == 50
        assert framework.state.phase == LoopPhase.INITIALIZING
        assert isinstance(framework.state.session_id, str)

    @pytest.mark.asyncio
    async def test_initialize_async_with_session_id(self) -> None:
        """Test async initialization with provided session_id."""
        session_id = "custom-session-123"
        config = LoopConfig(
            agent_name="test-agent",
            max_iterations=50,
            session_id=session_id,
        )

        framework = await LoopFramework.initialize(config)

        assert framework.state.session_id == session_id

    @pytest.mark.asyncio
    async def test_initialize_async_auto_generates_session_id(self) -> None:
        """Test async initialization auto-generates session_id if not provided."""
        config = LoopConfig(
            agent_name="test-agent",
            max_iterations=50,
        )

        framework = await LoopFramework.initialize(config)

        # Should be a valid UUID format
        assert framework.state.session_id is not None
        assert len(framework.state.session_id) > 0
        # Try to parse as UUID to verify format
        uuid.UUID(framework.state.session_id)

    @pytest.mark.asyncio
    async def test_initialize_async_with_exit_conditions(self) -> None:
        """Test async initialization with exit conditions."""
        config = LoopConfig(
            agent_name="test-agent",
            max_iterations=50,
            exit_conditions=[
                ExitConditionConfig(type=ExitConditionType.ALL_TESTS_PASS),
                ExitConditionConfig(type=ExitConditionType.LINTING_CLEAN),
            ],
        )

        framework = await LoopFramework.initialize(config)

        assert len(framework.state.exit_conditions) == 2
        assert framework.state.exit_conditions[0].type == ExitConditionType.ALL_TESTS_PASS
        assert framework.state.exit_conditions[1].type == ExitConditionType.LINTING_CLEAN

    def test_initialize_sync_minimal_config(self) -> None:
        """Test sync initialization with minimal config."""
        config = LoopConfig(
            agent_name="test-agent",
            max_iterations=50,
        )

        framework = LoopFramework.initialize_sync(config)

        assert framework is not None
        assert framework.config == config
        assert framework.state is not None
        assert framework.state.agent_name == "test-agent"
        assert framework.state.max_iterations == 50

    def test_initialize_sync_with_session_id(self) -> None:
        """Test sync initialization with provided session_id."""
        session_id = "sync-session-456"
        config = LoopConfig(
            agent_name="test-agent",
            max_iterations=50,
            session_id=session_id,
        )

        framework = LoopFramework.initialize_sync(config)

        assert framework.state.session_id == session_id

    def test_initialize_sync_auto_generates_session_id(self) -> None:
        """Test sync initialization auto-generates session_id if not provided."""
        config = LoopConfig(
            agent_name="test-agent",
            max_iterations=50,
        )

        framework = LoopFramework.initialize_sync(config)

        # Should be a valid UUID format
        assert framework.state.session_id is not None
        uuid.UUID(framework.state.session_id)

    @pytest.mark.asyncio
    async def test_initialize_sets_up_tracer(self) -> None:
        """Test that initialization sets up OTEL tracer (T034)."""
        config = LoopConfig(
            agent_name="test-agent",
            max_iterations=50,
        )

        framework = await LoopFramework.initialize(config)

        assert framework.tracer is not None

    def test_get_state(self) -> None:
        """Test get_state() method returns current state (T029)."""
        config = LoopConfig(
            agent_name="test-agent",
            max_iterations=50,
        )

        framework = LoopFramework.initialize_sync(config)
        state = framework.get_state()

        assert state is not None
        assert isinstance(state, LoopState)
        assert state.agent_name == "test-agent"
        assert state.max_iterations == 50

    def test_get_exit_condition_status(self) -> None:
        """Test get_exit_condition_status() method (T030)."""
        config = LoopConfig(
            agent_name="test-agent",
            max_iterations=50,
            exit_conditions=[
                ExitConditionConfig(type=ExitConditionType.ALL_TESTS_PASS),
            ],
        )

        framework = LoopFramework.initialize_sync(config)
        conditions = framework.get_exit_condition_status()

        assert len(conditions) == 1
        assert conditions[0].type == ExitConditionType.ALL_TESTS_PASS

    def test_get_exit_condition_status_empty(self) -> None:
        """Test get_exit_condition_status() with no conditions."""
        config = LoopConfig(
            agent_name="test-agent",
            max_iterations=50,
            exit_conditions=[],
        )

        framework = LoopFramework.initialize_sync(config)
        conditions = framework.get_exit_condition_status()

        assert conditions == []


# =============================================================================
# T038: LoopFramework.run() Tests
# =============================================================================


class TestLoopFrameworkRun:
    """Tests for LoopFramework.run() main loop logic (T028, T031)."""

    @pytest.mark.asyncio
    async def test_run_executes_work_function(self) -> None:
        """Test that run() executes work_function each iteration."""
        config = LoopConfig(
            agent_name="test-agent",
            max_iterations=5,
        )
        framework = await LoopFramework.initialize(config)

        call_count = 0

        async def work_func(iteration: int, state: dict, fw: LoopFramework) -> dict:
            nonlocal call_count
            call_count += 1
            state["iteration"] = iteration
            return state

        await framework.run(work_function=work_func, initial_state={})

        # Should execute for max_iterations (5)
        assert call_count == 5

    @pytest.mark.asyncio
    async def test_run_passes_correct_iteration_number(self) -> None:
        """Test that run() passes correct iteration number to work_function."""
        config = LoopConfig(
            agent_name="test-agent",
            max_iterations=3,
        )
        framework = await LoopFramework.initialize(config)

        iterations_seen = []

        async def work_func(iteration: int, state: dict, fw: LoopFramework) -> dict:
            iterations_seen.append(iteration)
            return state

        await framework.run(work_function=work_func, initial_state={})

        assert iterations_seen == [0, 1, 2]

    @pytest.mark.asyncio
    async def test_run_passes_state_between_iterations(self) -> None:
        """Test that run() passes state from one iteration to next."""
        config = LoopConfig(
            agent_name="test-agent",
            max_iterations=3,
        )
        framework = await LoopFramework.initialize(config)

        async def work_func(iteration: int, state: dict, fw: LoopFramework) -> dict:
            state["count"] = state.get("count", 0) + 1
            return state

        result = await framework.run(work_function=work_func, initial_state={"count": 0})

        # State should accumulate across iterations
        assert result.final_state["count"] == 3

    @pytest.mark.asyncio
    async def test_run_passes_framework_to_work_function(self) -> None:
        """Test that run() passes framework instance to work_function."""
        config = LoopConfig(
            agent_name="test-agent",
            max_iterations=2,
        )
        framework = await LoopFramework.initialize(config)

        framework_passed = None

        async def work_func(iteration: int, state: dict, fw: LoopFramework) -> dict:
            nonlocal framework_passed
            framework_passed = fw
            return state

        await framework.run(work_function=work_func, initial_state={})

        assert framework_passed is framework

    @pytest.mark.asyncio
    async def test_run_updates_loop_state_iteration(self) -> None:
        """Test that run() updates state.current_iteration."""
        config = LoopConfig(
            agent_name="test-agent",
            max_iterations=3,
        )
        framework = await LoopFramework.initialize(config)

        async def work_func(iteration: int, state: dict, fw: LoopFramework) -> dict:
            # Check that framework state is updated
            assert fw.state.current_iteration == iteration
            return state

        await framework.run(work_function=work_func, initial_state={})


# =============================================================================
# T039: Loop Termination Tests
# =============================================================================


class TestLoopTermination:
    """Tests for loop termination conditions (T032, T039)."""

    @pytest.mark.asyncio
    async def test_run_terminates_at_max_iterations(self) -> None:
        """Test that loop terminates when max_iterations reached."""
        config = LoopConfig(
            agent_name="test-agent",
            max_iterations=5,
        )
        framework = await LoopFramework.initialize(config)

        call_count = 0

        async def work_func(iteration: int, state: dict, fw: LoopFramework) -> dict:
            nonlocal call_count
            call_count += 1
            return state

        result = await framework.run(work_function=work_func, initial_state={})

        # Should stop at exactly max_iterations
        assert call_count == 5
        assert result.iterations_completed == 5
        assert result.outcome == LoopOutcome.ITERATION_LIMIT

    @pytest.mark.asyncio
    async def test_run_terminates_when_all_conditions_met(self) -> None:
        """Test that loop terminates when all exit conditions are met."""
        config = LoopConfig(
            agent_name="test-agent",
            max_iterations=100,
            exit_conditions=[
                ExitConditionConfig(type=ExitConditionType.ALL_TESTS_PASS),
                ExitConditionConfig(type=ExitConditionType.LINTING_CLEAN),
            ],
        )
        framework = await LoopFramework.initialize(config)

        async def work_func(iteration: int, state: dict, fw: LoopFramework) -> dict:
            # Mark conditions as met on iteration 3
            if iteration == 3:
                for cond in fw.state.exit_conditions:
                    cond.status = ExitConditionStatusValue.MET
            return state

        result = await framework.run(work_function=work_func, initial_state={})

        # Should stop after iteration 3 (when conditions met)
        assert result.iterations_completed == 4  # 0, 1, 2, 3 = 4 iterations
        assert result.outcome == LoopOutcome.COMPLETED

    @pytest.mark.asyncio
    async def test_run_continues_when_some_conditions_not_met(self) -> None:
        """Test that loop continues when only some conditions are met."""
        config = LoopConfig(
            agent_name="test-agent",
            max_iterations=5,
            exit_conditions=[
                ExitConditionConfig(type=ExitConditionType.ALL_TESTS_PASS),
                ExitConditionConfig(type=ExitConditionType.LINTING_CLEAN),
            ],
        )
        framework = await LoopFramework.initialize(config)

        async def work_func(iteration: int, state: dict, fw: LoopFramework) -> dict:
            # Only mark first condition as met
            fw.state.exit_conditions[0].status = ExitConditionStatusValue.MET
            # Leave second condition as pending
            return state

        result = await framework.run(work_function=work_func, initial_state={})

        # Should run to max_iterations since not all conditions met
        assert result.iterations_completed == 5

    @pytest.mark.asyncio
    async def test_run_result_contains_final_state(self) -> None:
        """Test that LoopResult contains final agent state."""
        config = LoopConfig(
            agent_name="test-agent",
            max_iterations=3,
        )
        framework = await LoopFramework.initialize(config)

        async def work_func(iteration: int, state: dict, fw: LoopFramework) -> dict:
            state["last_iteration"] = iteration
            return state

        result = await framework.run(work_function=work_func, initial_state={"start": "value"})

        assert result.final_state["start"] == "value"
        assert result.final_state["last_iteration"] == 2  # Last iteration is 2 (0-indexed)

    @pytest.mark.asyncio
    async def test_run_result_contains_session_info(self) -> None:
        """Test that LoopResult contains session and agent info."""
        config = LoopConfig(
            agent_name="test-agent",
            max_iterations=2,
            session_id="test-session-123",
        )
        framework = await LoopFramework.initialize(config)

        async def work_func(iteration: int, state: dict, fw: LoopFramework) -> dict:
            return state

        result = await framework.run(work_function=work_func, initial_state={})

        assert result.session_id == "test-session-123"
        assert result.agent_name == "test-agent"
        assert result.max_iterations == 2


# =============================================================================
# T040: Re-entry Prevention Tests
# =============================================================================


class TestReentryPrevention:
    """Tests for re-entry prevention (T033, T040)."""

    @pytest.mark.asyncio
    async def test_run_prevents_reentry_during_execution(self) -> None:
        """Test that run() prevents re-entry while loop is active."""
        config = LoopConfig(
            agent_name="test-agent",
            max_iterations=5,
        )
        framework = await LoopFramework.initialize(config)

        async def work_func(iteration: int, state: dict, fw: LoopFramework) -> dict:
            # Try to call run() again during execution
            if iteration == 1:
                from src.exceptions import LoopFrameworkError

                with pytest.raises(LoopFrameworkError, match="already active"):
                    await fw.run(work_function=work_func, initial_state={})
            return state

        await framework.run(work_function=work_func, initial_state={})

    @pytest.mark.asyncio
    async def test_run_sets_is_active_flag(self) -> None:
        """Test that run() sets is_active flag during execution."""
        config = LoopConfig(
            agent_name="test-agent",
            max_iterations=3,
        )
        framework = await LoopFramework.initialize(config)

        active_flags = []

        async def work_func(iteration: int, state: dict, fw: LoopFramework) -> dict:
            active_flags.append(fw.state.is_active)
            return state

        assert framework.state.is_active is False

        await framework.run(work_function=work_func, initial_state={})

        # Should be active during all iterations
        assert all(active_flags)
        # Should be inactive after run completes
        assert framework.state.is_active is False

    @pytest.mark.asyncio
    async def test_run_clears_is_active_after_completion(self) -> None:
        """Test that is_active is cleared even after normal completion."""
        config = LoopConfig(
            agent_name="test-agent",
            max_iterations=2,
        )
        framework = await LoopFramework.initialize(config)

        async def work_func(iteration: int, state: dict, fw: LoopFramework) -> dict:
            return state

        await framework.run(work_function=work_func, initial_state={})

        assert framework.state.is_active is False

    @pytest.mark.asyncio
    async def test_run_clears_is_active_after_error(self) -> None:
        """Test that is_active is cleared even if work_function raises error."""
        config = LoopConfig(
            agent_name="test-agent",
            max_iterations=5,
        )
        framework = await LoopFramework.initialize(config)

        async def work_func(iteration: int, state: dict, fw: LoopFramework) -> dict:
            if iteration == 2:
                raise ValueError("Test error")
            return state

        result = await framework.run(work_function=work_func, initial_state={})

        # Should be inactive after error
        assert framework.state.is_active is False
        # Should report error outcome
        assert result.outcome == LoopOutcome.ERROR


# =============================================================================
# T074: Checkpoint Interval Tests
# =============================================================================


class TestCheckpointInterval:
    """Tests for checkpoint interval logic (T074)."""

    @pytest.mark.asyncio
    async def test_checkpoint_saves_at_correct_intervals(self) -> None:
        """Test checkpoints saved at configured intervals."""
        from unittest.mock import Mock

        config = LoopConfig(
            agent_name="test-agent",
            max_iterations=10,
            checkpoint_interval=3,  # Save every 3 iterations
            exit_conditions=[],
        )
        framework = await LoopFramework.initialize(config)

        # Mock the checkpoint manager
        framework.checkpoint_manager.save_checkpoint = Mock(return_value="checkpoint-id")

        async def work_func(iteration: int, state: dict, fw: LoopFramework) -> dict:
            state["count"] = state.get("count", 0) + 1
            return state

        await framework.run(work_function=work_func, initial_state={})

        # With max_iterations=10 and interval=3, should save at iterations 2, 5, 8
        # (0-indexed, so after completing iterations 3, 6, 9)
        assert framework.checkpoint_manager.save_checkpoint.call_count == 3

    @pytest.mark.asyncio
    async def test_checkpoint_interval_1_saves_every_iteration(self) -> None:
        """Test checkpoint_interval=1 saves after every iteration."""
        from unittest.mock import Mock

        config = LoopConfig(
            agent_name="test-agent",
            max_iterations=5,
            checkpoint_interval=1,  # Save every iteration
            exit_conditions=[],
        )
        framework = await LoopFramework.initialize(config)

        # Mock the checkpoint manager
        framework.checkpoint_manager.save_checkpoint = Mock(return_value="checkpoint-id")

        async def work_func(iteration: int, state: dict, fw: LoopFramework) -> dict:
            return state

        await framework.run(work_function=work_func, initial_state={})

        # Should save after each of the 5 iterations
        assert framework.checkpoint_manager.save_checkpoint.call_count == 5

    @pytest.mark.asyncio
    async def test_checkpoint_not_saved_when_interval_not_reached(self) -> None:
        """Test checkpoint NOT saved when interval not reached."""
        from unittest.mock import Mock

        config = LoopConfig(
            agent_name="test-agent",
            max_iterations=5,
            checkpoint_interval=10,  # Interval larger than max_iterations
            exit_conditions=[],
        )
        framework = await LoopFramework.initialize(config)

        # Mock the checkpoint manager
        framework.checkpoint_manager.save_checkpoint = Mock(return_value="checkpoint-id")

        async def work_func(iteration: int, state: dict, fw: LoopFramework) -> dict:
            return state

        await framework.run(work_function=work_func, initial_state={})

        # Should never save since interval (10) > max_iterations (5)
        assert framework.checkpoint_manager.save_checkpoint.call_count == 0

    @pytest.mark.asyncio
    async def test_checkpoint_interval_5_saves_correctly(self) -> None:
        """Test checkpoint_interval=5 saves at correct iterations."""
        from unittest.mock import Mock

        config = LoopConfig(
            agent_name="test-agent",
            max_iterations=12,
            checkpoint_interval=5,  # Save every 5 iterations
            exit_conditions=[],
        )
        framework = await LoopFramework.initialize(config)

        # Mock the checkpoint manager
        framework.checkpoint_manager.save_checkpoint = Mock(return_value="checkpoint-id")

        async def work_func(iteration: int, state: dict, fw: LoopFramework) -> dict:
            return state

        await framework.run(work_function=work_func, initial_state={})

        # Should save at iterations 4 and 9 (after completing iterations 5 and 10)
        assert framework.checkpoint_manager.save_checkpoint.call_count == 2

    @pytest.mark.asyncio
    async def test_checkpoint_interval_with_early_termination(self) -> None:
        """Test checkpoint saves correctly when loop terminates early."""
        from unittest.mock import Mock

        config = LoopConfig(
            agent_name="test-agent",
            max_iterations=20,
            checkpoint_interval=3,
            exit_conditions=[ExitConditionConfig(type=ExitConditionType.ALL_TESTS_PASS)],
        )
        framework = await LoopFramework.initialize(config)

        # Mock the checkpoint manager
        framework.checkpoint_manager.save_checkpoint = Mock(return_value="checkpoint-id")

        async def work_func(iteration: int, state: dict, fw: LoopFramework) -> dict:
            # Terminate after 7 iterations
            if iteration >= 6:
                # Mark all conditions as met to trigger termination
                for condition in fw.state.exit_conditions:
                    condition.status = ExitConditionStatusValue.MET
            return state

        await framework.run(work_function=work_func, initial_state={})

        # Should save at iterations 2 and 5 (after completing iterations 3 and 6)
        # before terminating at iteration 7
        assert framework.checkpoint_manager.save_checkpoint.call_count == 2
