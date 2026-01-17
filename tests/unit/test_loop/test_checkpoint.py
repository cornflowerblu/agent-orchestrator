"""Unit tests for checkpoint manager.

T073: Tests for CheckpointManager class
"""

import pytest

from src.exceptions import CheckpointRecoveryError
from src.loop.checkpoint import CheckpointManager
from src.loop.models import (
    ExitConditionStatus,
    ExitConditionStatusValue,
    ExitConditionType,
    LoopPhase,
    LoopState,
)

# =============================================================================
# T073: CheckpointManager Tests (User Story 2)
# =============================================================================


class TestCheckpointManager:
    """Tests for CheckpointManager class (T062-T067)."""

    def test_init_checkpoint_manager(self) -> None:
        """Test CheckpointManager initialization."""
        manager = CheckpointManager(session_id="test-session", region="us-west-2")

        assert manager.session_id == "test-session"
        assert manager.region == "us-west-2"

    def test_create_memory_for_session(self, mock_memory) -> None:
        """Test CheckpointManager.create_memory() creates Memory instance."""
        manager = CheckpointManager(session_id="test-session")
        memory = manager.create_memory()

        # Verify Memory was created
        assert memory is not None
        assert hasattr(memory, "put")
        assert hasattr(memory, "get")
        assert hasattr(memory, "list")

    def test_save_checkpoint(self, mock_memory) -> None:
        """Test CheckpointManager.save_checkpoint() saves to Memory."""
        manager = CheckpointManager(session_id="test-session")

        # Create test loop state
        loop_state = LoopState(
            session_id="test-session",
            agent_name="test-agent",
            max_iterations=100,
            current_iteration=10,
            phase=LoopPhase.RUNNING,
        )

        # Save checkpoint
        checkpoint_id = manager.save_checkpoint(loop_state)

        # Verify checkpoint was saved
        assert checkpoint_id is not None
        assert checkpoint_id.startswith("checkpoint-")

    def test_load_checkpoint_success(self, mock_memory) -> None:
        """Test CheckpointManager.load_checkpoint() loads from Memory."""
        manager = CheckpointManager(session_id="test-session")

        # Create and save a checkpoint first
        loop_state = LoopState(
            session_id="test-session",
            agent_name="test-agent",
            max_iterations=100,
            current_iteration=10,
            phase=LoopPhase.RUNNING,
        )
        manager.save_checkpoint(loop_state)

        # Load checkpoint
        loaded_state = manager.load_checkpoint(iteration=10)

        # Verify checkpoint was loaded
        assert loaded_state is not None
        assert loaded_state.session_id == "test-session"
        assert loaded_state.current_iteration == 10
        assert loaded_state.agent_name == "test-agent"

    def test_load_checkpoint_not_found(self, mock_memory) -> None:
        """Test CheckpointManager.load_checkpoint() raises error if not found."""
        manager = CheckpointManager(session_id="test-session")

        # Attempt to load non-existent checkpoint
        with pytest.raises(CheckpointRecoveryError) as exc_info:
            manager.load_checkpoint(iteration=99)

        assert "Checkpoint not found" in str(exc_info.value)
        assert exc_info.value.checkpoint_id is not None

    def test_load_checkpoint_invalid_data(self, mock_memory) -> None:
        """Test CheckpointManager.load_checkpoint() raises error for invalid data."""
        manager = CheckpointManager(session_id="test-session")

        # Manually put invalid data into Memory
        manager.create_memory()
        manager._memory._storage["checkpoint/test-session/10"] = {  # type: ignore[union-attr]
            "checkpoint_id": "checkpoint-123",
            "session_id": "test-session",
            # Missing required fields
        }

        # Attempt to load invalid checkpoint
        with pytest.raises(CheckpointRecoveryError) as exc_info:
            manager.load_checkpoint(iteration=10)

        assert "Invalid checkpoint data" in str(exc_info.value)

    def test_list_checkpoints(self, mock_memory) -> None:
        """Test CheckpointManager.list_checkpoints() lists all checkpoints."""
        manager = CheckpointManager(session_id="test-session")

        # Save two checkpoints
        for iteration in [5, 10]:
            loop_state = LoopState(
                session_id="test-session",
                agent_name="test-agent",
                max_iterations=100,
                current_iteration=iteration,
            )
            manager.save_checkpoint(loop_state)

        # List checkpoints
        checkpoints = manager.list_checkpoints()

        # Verify checkpoints were listed
        assert len(checkpoints) == 2
        iterations = {cp["iteration"] for cp in checkpoints}
        assert 5 in iterations
        assert 10 in iterations

    def test_save_checkpoint_preserves_exit_conditions(self, mock_memory) -> None:
        """Test that save_checkpoint preserves exit condition state."""
        manager = CheckpointManager(session_id="test-session")

        # Create loop state with exit conditions
        loop_state = LoopState(
            session_id="test-session",
            agent_name="test-agent",
            max_iterations=100,
            current_iteration=15,
            exit_conditions=[
                ExitConditionStatus(
                    type=ExitConditionType.ALL_TESTS_PASS,
                    status=ExitConditionStatusValue.MET,
                    tool_name="pytest",
                    tool_exit_code=0,
                    tool_output="20 passed",
                    iteration_evaluated=15,
                ),
            ],
        )

        # Save and load checkpoint
        manager.save_checkpoint(loop_state)
        loaded_state = manager.load_checkpoint(iteration=15)

        # Verify exit conditions were preserved
        assert len(loaded_state.exit_conditions) == 1
        assert loaded_state.exit_conditions[0].type == ExitConditionType.ALL_TESTS_PASS
        assert loaded_state.exit_conditions[0].status == ExitConditionStatusValue.MET
        assert loaded_state.exit_conditions[0].tool_name == "pytest"

    def test_checkpoint_manager_with_custom_region(self, mock_memory) -> None:
        """Test CheckpointManager uses custom AWS region."""
        manager = CheckpointManager(session_id="test-session", region="eu-west-1")

        assert manager.region == "eu-west-1"
        # When creating memory, region should be passed if needed
        memory = manager.create_memory()
        assert hasattr(memory, "region")
        assert memory.region == "eu-west-1"

    def test_checkpoint_roundtrip_preserves_all_state(self, mock_memory) -> None:
        """Test full roundtrip preserves all loop state."""
        manager = CheckpointManager(session_id="test-session")

        # Create complex loop state
        original_state = LoopState(
            session_id="test-session",
            agent_name="test-agent",
            max_iterations=200,
            current_iteration=75,
            phase=LoopPhase.EVALUATING_CONDITIONS,
            is_active=True,
            started_at="2026-01-17T10:00:00Z",
            last_iteration_at="2026-01-17T10:15:00Z",
            last_checkpoint_at="2026-01-17T10:10:00Z",
            last_checkpoint_iteration=70,
            exit_conditions=[
                ExitConditionStatus(
                    type=ExitConditionType.ALL_TESTS_PASS,
                    status=ExitConditionStatusValue.MET,
                ),
                ExitConditionStatus(
                    type=ExitConditionType.LINTING_CLEAN,
                    status=ExitConditionStatusValue.NOT_MET,
                ),
            ],
            agent_state={"key": "value", "counter": 42},
        )

        # Save and load
        manager.save_checkpoint(original_state)
        restored_state = manager.load_checkpoint(iteration=75)

        # Verify all fields match
        assert restored_state.model_dump() == original_state.model_dump()
