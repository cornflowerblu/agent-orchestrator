"""Unit tests for checkpoint manager.

T073: Tests for CheckpointManager class
"""

from unittest.mock import MagicMock, patch

import pytest

from src.exceptions import CheckpointRecoveryError
from src.loop.checkpoint import CheckpointManager
from src.loop.models import Checkpoint, ExitConditionStatus, ExitConditionStatusValue, ExitConditionType, LoopPhase, LoopState


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

    def test_create_memory_for_session(self) -> None:
        """Test CheckpointManager.create_memory() creates Memory instance."""
        with patch("src.loop.checkpoint.Memory") as mock_memory_class:
            mock_memory_instance = MagicMock()
            mock_memory_class.return_value = mock_memory_instance

            manager = CheckpointManager(session_id="test-session")
            memory = manager.create_memory()

            # Verify Memory was created
            mock_memory_class.assert_called_once()
            assert memory == mock_memory_instance

    def test_save_checkpoint(self) -> None:
        """Test CheckpointManager.save_checkpoint() saves to Memory."""
        with patch("src.loop.checkpoint.Memory") as mock_memory_class:
            mock_memory = MagicMock()
            mock_memory_class.return_value = mock_memory

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
            mock_memory.put.assert_called_once()

            # Verify the data structure saved
            call_args = mock_memory.put.call_args
            assert "key" in call_args.kwargs
            assert "value" in call_args.kwargs
            assert call_args.kwargs["key"].startswith("checkpoint/test-session/")

    def test_load_checkpoint_success(self) -> None:
        """Test CheckpointManager.load_checkpoint() loads from Memory."""
        with patch("src.loop.checkpoint.Memory") as mock_memory_class:
            mock_memory = MagicMock()
            mock_memory_class.return_value = mock_memory

            # Setup mock Memory to return checkpoint data
            mock_memory.get.return_value = {
                "checkpoint_id": "checkpoint-123",
                "session_id": "test-session",
                "iteration": 10,
                "loop_state_snapshot": {
                    "session_id": "test-session",
                    "agent_name": "test-agent",
                    "max_iterations": 100,
                    "current_iteration": 10,
                    "phase": "running",
                    "is_active": False,
                    "started_at": "2026-01-17T10:00:00Z",
                    "exit_conditions": [],
                    "agent_state": {},
                },
                "created_at": "2026-01-17T10:05:00Z",
                "agent_name": "test-agent",
            }

            manager = CheckpointManager(session_id="test-session")

            # Load checkpoint
            loop_state = manager.load_checkpoint(iteration=10)

            # Verify checkpoint was loaded
            assert loop_state is not None
            assert loop_state.session_id == "test-session"
            assert loop_state.current_iteration == 10
            assert loop_state.agent_name == "test-agent"
            mock_memory.get.assert_called_once()

    def test_load_checkpoint_not_found(self) -> None:
        """Test CheckpointManager.load_checkpoint() raises error if not found."""
        with patch("src.loop.checkpoint.Memory") as mock_memory_class:
            mock_memory = MagicMock()
            mock_memory_class.return_value = mock_memory

            # Setup mock Memory to return None (checkpoint not found)
            mock_memory.get.return_value = None

            manager = CheckpointManager(session_id="test-session")

            # Attempt to load non-existent checkpoint
            with pytest.raises(CheckpointRecoveryError) as exc_info:
                manager.load_checkpoint(iteration=99)

            assert "Checkpoint not found" in str(exc_info.value)
            assert exc_info.value.checkpoint_id is not None

    def test_load_checkpoint_invalid_data(self) -> None:
        """Test CheckpointManager.load_checkpoint() raises error for invalid data."""
        with patch("src.loop.checkpoint.Memory") as mock_memory_class:
            mock_memory = MagicMock()
            mock_memory_class.return_value = mock_memory

            # Setup mock Memory to return invalid checkpoint data
            mock_memory.get.return_value = {
                "checkpoint_id": "checkpoint-123",
                "session_id": "test-session",
                # Missing required fields
            }

            manager = CheckpointManager(session_id="test-session")

            # Attempt to load invalid checkpoint
            with pytest.raises(CheckpointRecoveryError) as exc_info:
                manager.load_checkpoint(iteration=10)

            assert "Invalid checkpoint data" in str(exc_info.value)

    def test_list_checkpoints(self) -> None:
        """Test CheckpointManager.list_checkpoints() lists all checkpoints."""
        with patch("src.loop.checkpoint.Memory") as mock_memory_class:
            mock_memory = MagicMock()
            mock_memory_class.return_value = mock_memory

            # Setup mock Memory to return list of checkpoints
            mock_memory.list.return_value = [
                {
                    "checkpoint_id": "checkpoint-1",
                    "session_id": "test-session",
                    "iteration": 5,
                    "created_at": "2026-01-17T10:00:00Z",
                    "agent_name": "test-agent",
                },
                {
                    "checkpoint_id": "checkpoint-2",
                    "session_id": "test-session",
                    "iteration": 10,
                    "created_at": "2026-01-17T10:05:00Z",
                    "agent_name": "test-agent",
                },
            ]

            manager = CheckpointManager(session_id="test-session")

            # List checkpoints
            checkpoints = manager.list_checkpoints()

            # Verify checkpoints were listed
            assert len(checkpoints) == 2
            assert checkpoints[0]["iteration"] == 5
            assert checkpoints[1]["iteration"] == 10
            mock_memory.list.assert_called_once()

    def test_save_checkpoint_preserves_exit_conditions(self) -> None:
        """Test that save_checkpoint preserves exit condition state."""
        with patch("src.loop.checkpoint.Memory") as mock_memory_class:
            mock_memory = MagicMock()
            mock_memory_class.return_value = mock_memory

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

            # Save checkpoint
            checkpoint_id = manager.save_checkpoint(loop_state)

            # Verify checkpoint was saved with exit conditions
            call_args = mock_memory.put.call_args
            saved_data = call_args.kwargs["value"]
            assert "loop_state_snapshot" in saved_data
            assert len(saved_data["loop_state_snapshot"]["exit_conditions"]) == 1
            assert saved_data["loop_state_snapshot"]["exit_conditions"][0]["type"] == "all_tests_pass"

    def test_checkpoint_manager_with_custom_region(self) -> None:
        """Test CheckpointManager uses custom AWS region."""
        with patch("src.loop.checkpoint.Memory") as mock_memory_class:
            mock_memory = MagicMock()
            mock_memory_class.return_value = mock_memory

            manager = CheckpointManager(session_id="test-session", region="eu-west-1")

            assert manager.region == "eu-west-1"
            # When creating memory, region should be passed if needed
            # This depends on the Memory API implementation
