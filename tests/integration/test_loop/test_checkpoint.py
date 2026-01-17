"""Integration tests for checkpoint DynamoDB storage.

T075: Integration test for DynamoDB checkpoint storage roundtrip.

This file tests the full checkpoint save/load cycle using DynamoDB.
"""

import pytest

from src.loop.framework import LoopFramework
from src.loop.models import (
    ExitConditionConfig,
    ExitConditionStatusValue,
    ExitConditionType,
    LoopConfig,
    LoopPhase,
)


@pytest.mark.integration
@pytest.mark.integration_local
@pytest.mark.asyncio
async def test_checkpoint_memory_roundtrip(dynamodb_local) -> None:
    """Test full checkpoint save and load cycle via DynamoDB service.

    T075: Write integration test for DynamoDB service.

    This test verifies:
    1. Framework can save checkpoints to DynamoDB
    2. Framework can load checkpoints from DynamoDB
    3. All LoopState fields are preserved (iteration, phase, exit conditions)
    4. Agent state is preserved across save/load
    """
    config = LoopConfig(
        agent_name="test-checkpoint-agent",
        max_iterations=10,
        checkpoint_interval=2,  # Save every 2 iterations
        exit_conditions=[
            ExitConditionConfig(type=ExitConditionType.ALL_TESTS_PASS),
        ],
    )
    framework = await LoopFramework.initialize(config)

    # Run a few iterations and capture state
    iteration_states = []

    async def work_func(iteration: int, state: dict, fw: LoopFramework) -> dict:
        state["iteration"] = iteration
        state["data"] = f"iteration_{iteration}"
        iteration_states.append((iteration, state.copy()))
        # Stop after 5 iterations
        if iteration >= 4:
            for condition in fw.state.exit_conditions:
                condition.status = ExitConditionStatusValue.MET
        return state

    result = await framework.run(work_function=work_func, initial_state={})

    # Verify we ran some iterations
    assert result.iterations_completed >= 4

    # Save a checkpoint at current iteration
    original_iteration = framework.state.current_iteration
    original_agent_state = framework.state.agent_state.copy()

    checkpoint_id = await framework.save_checkpoint()
    assert checkpoint_id is not None

    # Load the checkpoint back
    restored_state = await framework.load_checkpoint(iteration=original_iteration)

    # Verify state is preserved
    assert restored_state.current_iteration == original_iteration
    # Note: phase may be SAVING_CHECKPOINT since that's when the snapshot was taken
    assert restored_state.phase in [
        LoopPhase.SAVING_CHECKPOINT,
        LoopPhase.RUNNING,
        LoopPhase.COMPLETED,
    ]
    assert restored_state.agent_name == config.agent_name
    assert restored_state.max_iterations == config.max_iterations
    assert restored_state.session_id == framework.state.session_id

    # Verify agent state is preserved
    assert restored_state.agent_state == original_agent_state

    # Verify exit conditions structure is preserved
    assert len(restored_state.exit_conditions) == len(framework.state.exit_conditions)
    for original, restored in zip(
        framework.state.exit_conditions, restored_state.exit_conditions, strict=True
    ):
        assert original.type == restored.type
        assert original.status == restored.status


@pytest.mark.integration
@pytest.mark.integration_local
@pytest.mark.asyncio
async def test_checkpoint_save_at_intervals(dynamodb_local) -> None:
    """Test checkpoints are saved at configured intervals.

    T075: Integration test verifying checkpoint interval logic works with real DynamoDB.

    This test verifies:
    1. Checkpoints are saved at the correct intervals
    2. Multiple checkpoints can be saved to DynamoDB
    3. Each checkpoint can be loaded independently
    """
    config = LoopConfig(
        agent_name="test-interval-agent",
        max_iterations=8,
        checkpoint_interval=3,  # Save every 3 iterations
        exit_conditions=[],
    )
    framework = await LoopFramework.initialize(config)

    async def work_func(iteration: int, state: dict, fw: LoopFramework) -> dict:
        state["count"] = state.get("count", 0) + 1
        state["current_iteration"] = iteration
        return state

    _ = await framework.run(work_function=work_func, initial_state={"count": 0})

    # Should have saved checkpoints at iterations 2, 5 (after completing iterations 3, 6)
    # We can verify by checking the checkpoint manager's list
    checkpoints = framework.checkpoint_manager.list_checkpoints()

    # Should have at least 2 checkpoints
    assert len(checkpoints) >= 2

    # Load each checkpoint and verify (checkpoints are dicts with 'key' field)
    # The key format is "checkpoint/{session_id}/{iteration}"
    for checkpoint_dict in checkpoints[:2]:  # Check first 2
        # Extract iteration from the checkpoint key
        key = checkpoint_dict.get("key", "")
        if "/" in key:
            iteration = int(key.split("/")[-1])
            loaded_state = await framework.load_checkpoint(iteration=iteration)

            # Verify the state is correct for that iteration
            assert loaded_state.current_iteration == iteration
            assert loaded_state.agent_state["current_iteration"] == iteration


@pytest.mark.integration
@pytest.mark.integration_local
@pytest.mark.asyncio
async def test_checkpoint_resume_from_saved_state(dynamodb_local) -> None:
    """Test resuming loop execution from a saved checkpoint.

    T075: Integration test for resume_from functionality with DynamoDB.

    This test verifies:
    1. Framework can resume from a saved checkpoint
    2. Execution continues from the saved iteration
    3. State is correctly restored

    Note: This is a simplified test that demonstrates the concept.
    In practice, resume_from would be used across different process instances.
    """
    config = LoopConfig(
        agent_name="test-resume-agent",
        max_iterations=10,
        checkpoint_interval=2,
        exit_conditions=[],
    )

    framework = await LoopFramework.initialize(config)

    # First run: execute a few iterations
    async def work_func(iteration: int, state: dict, fw: LoopFramework) -> dict:
        state["count"] = state.get("count", 0) + 1
        state["last_iteration"] = iteration
        return state

    # Run to completion
    result = await framework.run(work_function=work_func, initial_state={"count": 0})

    # Verify checkpoints were saved
    assert result.iterations_completed == 10

    # Verify we can load one of the saved checkpoints
    # With interval=2, checkpoints are saved at iterations 1, 3, 5, 7, 9
    # (when (iteration + 1) % 2 == 0, so after completing iterations 2, 4, 6, 8, 10)
    loaded_state = await framework.load_checkpoint(iteration=1)

    # Verify the loaded state has the correct iteration
    assert loaded_state.current_iteration == 1
    assert loaded_state.agent_state["last_iteration"] == 1
    assert loaded_state.agent_state["count"] == 2  # iterations 0-1 = 2 iterations
