"""Unit tests for checkpoint manager.

T073: Tests for CheckpointManager class
"""

import json
from decimal import Decimal

import pytest

from src.exceptions import CheckpointRecoveryError
from src.loop.checkpoint import (
    CheckpointManager,
    DecimalEncoder,
    _convert_floats_to_decimal,
)
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
        manager = CheckpointManager(
            session_id="test-session",
            agent_name="test-agent",
            region="us-west-2",
        )

        assert manager.session_id == "test-session"
        assert manager.agent_name == "test-agent"
        assert manager.region == "us-west-2"

    def test_backend_selection_prefers_memory(self, mock_memory) -> None:
        """Test that CheckpointManager prefers Memory when available."""
        manager = CheckpointManager(
            session_id="test-session",
            agent_name="test-agent",
        )

        # Save triggers backend selection
        loop_state = LoopState(
            session_id="test-session",
            agent_name="test-agent",
            max_iterations=100,
            current_iteration=5,
        )
        manager.save_checkpoint(loop_state)

        # Memory should be selected when mock is available
        assert manager._use_memory is True

    def test_save_checkpoint(self, mock_memory) -> None:
        """Test CheckpointManager.save_checkpoint() saves to Memory."""
        manager = CheckpointManager(
            session_id="test-session",
            agent_name="test-agent",
        )

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
        manager = CheckpointManager(
            session_id="test-session",
            agent_name="test-agent",
        )

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
        manager = CheckpointManager(
            session_id="test-session",
            agent_name="test-agent",
        )

        # Save one checkpoint to initialize the backend
        loop_state = LoopState(
            session_id="test-session",
            agent_name="test-agent",
            max_iterations=100,
            current_iteration=5,
        )
        manager.save_checkpoint(loop_state)

        # Attempt to load non-existent checkpoint
        with pytest.raises(CheckpointRecoveryError) as exc_info:
            manager.load_checkpoint(iteration=99)

        assert "Checkpoint not found" in str(exc_info.value)
        assert exc_info.value.checkpoint_id is not None

    def test_list_checkpoints(self, mock_memory) -> None:
        """Test CheckpointManager.list_checkpoints() lists all checkpoints."""
        manager = CheckpointManager(
            session_id="test-session",
            agent_name="test-agent",
        )

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
        manager = CheckpointManager(
            session_id="test-session",
            agent_name="test-agent",
        )

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
        manager = CheckpointManager(
            session_id="test-session",
            agent_name="test-agent",
            region="us-east-1",
        )

        assert manager.region == "us-east-1"

        # Verify manager can save (which initializes backend)
        loop_state = LoopState(
            session_id="test-session",
            agent_name="test-agent",
            max_iterations=100,
            current_iteration=5,
        )
        checkpoint_id = manager.save_checkpoint(loop_state)
        assert checkpoint_id is not None

    def test_checkpoint_roundtrip_preserves_all_state(self, mock_memory) -> None:
        """Test full roundtrip preserves all loop state."""
        manager = CheckpointManager(
            session_id="test-session",
            agent_name="test-agent",
        )

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

    def test_load_latest_checkpoint(self, mock_memory) -> None:
        """Test load_latest_checkpoint returns most recent checkpoint."""
        manager = CheckpointManager(
            session_id="test-session",
            agent_name="test-agent",
        )

        # Save multiple checkpoints
        for iteration in [5, 10, 15]:
            loop_state = LoopState(
                session_id="test-session",
                agent_name="test-agent",
                max_iterations=100,
                current_iteration=iteration,
            )
            manager.save_checkpoint(loop_state)

        # Load latest
        latest_state = manager.load_latest_checkpoint()

        # Should be iteration 15
        assert latest_state is not None
        assert latest_state.current_iteration == 15

    def test_load_latest_checkpoint_empty(self, mock_memory) -> None:
        """Test load_latest_checkpoint returns None when no checkpoints exist."""
        manager = CheckpointManager(
            session_id="empty-session",
            agent_name="test-agent",
        )

        # Should return None (no checkpoints saved)
        latest_state = manager.load_latest_checkpoint()
        assert latest_state is None

    def test_different_sessions_isolated(self, mock_memory) -> None:
        """Test that different sessions have isolated checkpoints."""
        manager1 = CheckpointManager(
            session_id="session-1",
            agent_name="test-agent",
        )
        manager2 = CheckpointManager(
            session_id="session-2",
            agent_name="test-agent",
        )

        # Save checkpoint in session 1
        loop_state = LoopState(
            session_id="session-1",
            agent_name="test-agent",
            max_iterations=100,
            current_iteration=10,
        )
        manager1.save_checkpoint(loop_state)

        # Session 2 should not see it
        checkpoints = manager2.list_checkpoints()
        assert len(checkpoints) == 0

        # Session 1 should see it
        checkpoints = manager1.list_checkpoints()
        assert len(checkpoints) == 1


class TestCheckpointManagerDynamoDBFallback:
    """Tests for DynamoDB fallback when Memory is unavailable."""

    def test_forced_dynamodb_backend_via_env(self, mock_dynamodb, monkeypatch) -> None:
        """Test forcing DynamoDB backend via CHECKPOINT_BACKEND env var."""
        # Disable the auto mock for Memory
        monkeypatch.setenv("CHECKPOINT_BACKEND", "dynamodb")

        manager = CheckpointManager(
            session_id="test-session",
            agent_name="test-agent",
            region="us-east-1",
        )

        # Backend should be forced to DynamoDB
        assert manager._use_memory is False

        # Create test loop state
        loop_state = LoopState(
            session_id="test-session",
            agent_name="test-agent",
            max_iterations=100,
            current_iteration=10,
        )

        # Save checkpoint - should use DynamoDB
        checkpoint_id = manager.save_checkpoint(loop_state)
        assert checkpoint_id is not None
        assert checkpoint_id.startswith("checkpoint-")

        # Backend should still be DynamoDB
        assert manager._use_memory is False

    def test_dynamodb_save_and_load(self, mock_dynamodb, monkeypatch) -> None:
        """Test DynamoDB save and load operations."""
        monkeypatch.setenv("CHECKPOINT_BACKEND", "dynamodb")

        manager = CheckpointManager(
            session_id="test-session",
            agent_name="test-agent",
            region="us-east-1",
        )

        # Create test loop state with exit conditions
        loop_state = LoopState(
            session_id="test-session",
            agent_name="test-agent",
            max_iterations=100,
            current_iteration=25,
            phase=LoopPhase.RUNNING,
            exit_conditions=[
                ExitConditionStatus(
                    type=ExitConditionType.ALL_TESTS_PASS,
                    status=ExitConditionStatusValue.NOT_MET,
                ),
            ],
        )

        # Save checkpoint
        manager.save_checkpoint(loop_state)

        # Load checkpoint
        loaded_state = manager.load_checkpoint(iteration=25)

        # Verify state was restored
        assert loaded_state.session_id == "test-session"
        assert loaded_state.current_iteration == 25
        assert loaded_state.phase == LoopPhase.RUNNING
        assert len(loaded_state.exit_conditions) == 1
        assert loaded_state.exit_conditions[0].type == ExitConditionType.ALL_TESTS_PASS

    def test_dynamodb_list_checkpoints(self, mock_dynamodb, monkeypatch) -> None:
        """Test listing checkpoints from DynamoDB."""
        monkeypatch.setenv("CHECKPOINT_BACKEND", "dynamodb")

        manager = CheckpointManager(
            session_id="test-session",
            agent_name="test-agent",
            region="us-east-1",
        )

        # Save multiple checkpoints
        for iteration in [5, 10, 15]:
            loop_state = LoopState(
                session_id="test-session",
                agent_name="test-agent",
                max_iterations=100,
                current_iteration=iteration,
            )
            manager.save_checkpoint(loop_state)

        # List checkpoints
        checkpoints = manager.list_checkpoints()

        # Verify all checkpoints listed
        assert len(checkpoints) == 3
        iterations = {cp["iteration"] for cp in checkpoints}
        assert iterations == {5, 10, 15}

    def test_dynamodb_load_latest_checkpoint(self, mock_dynamodb, monkeypatch) -> None:
        """Test loading latest checkpoint from DynamoDB."""
        monkeypatch.setenv("CHECKPOINT_BACKEND", "dynamodb")

        manager = CheckpointManager(
            session_id="test-session",
            agent_name="test-agent",
            region="us-east-1",
        )

        # Save checkpoints out of order
        for iteration in [10, 5, 20, 15]:
            loop_state = LoopState(
                session_id="test-session",
                agent_name="test-agent",
                max_iterations=100,
                current_iteration=iteration,
            )
            manager.save_checkpoint(loop_state)

        # Load latest should return iteration 20
        latest = manager.load_latest_checkpoint()
        assert latest is not None
        assert latest.current_iteration == 20

    def test_dynamodb_checkpoint_not_found(self, mock_dynamodb, monkeypatch) -> None:
        """Test loading non-existent checkpoint from DynamoDB."""
        monkeypatch.setenv("CHECKPOINT_BACKEND", "dynamodb")

        manager = CheckpointManager(
            session_id="test-session",
            agent_name="test-agent",
            region="us-east-1",
        )

        # Attempt to load non-existent checkpoint
        with pytest.raises(CheckpointRecoveryError) as exc_info:
            manager.load_checkpoint(iteration=99)

        assert "Checkpoint not found" in str(exc_info.value)

    def test_dynamodb_session_isolation(self, mock_dynamodb, monkeypatch) -> None:
        """Test session isolation in DynamoDB."""
        monkeypatch.setenv("CHECKPOINT_BACKEND", "dynamodb")

        manager1 = CheckpointManager(
            session_id="session-1",
            agent_name="test-agent",
            region="us-east-1",
        )
        manager2 = CheckpointManager(
            session_id="session-2",
            agent_name="test-agent",
            region="us-east-1",
        )

        # Save checkpoint in session 1
        loop_state = LoopState(
            session_id="session-1",
            agent_name="test-agent",
            max_iterations=100,
            current_iteration=10,
        )
        manager1.save_checkpoint(loop_state)

        # Session 2 should not see it
        checkpoints = manager2.list_checkpoints()
        assert len(checkpoints) == 0

        # Session 1 should see it
        checkpoints = manager1.list_checkpoints()
        assert len(checkpoints) == 1


class TestCheckpointHelperFunctions:
    """Tests for checkpoint helper functions."""

    def test_decimal_encoder_int(self) -> None:
        """Test DecimalEncoder converts Decimal to int when no fractional part."""
        data = {"value": Decimal("42")}
        result = json.dumps(data, cls=DecimalEncoder)
        assert result == '{"value": 42}'

    def test_decimal_encoder_float(self) -> None:
        """Test DecimalEncoder converts Decimal to float when has fractional part."""
        data = {"value": Decimal("3.14")}
        result = json.dumps(data, cls=DecimalEncoder)
        assert result == '{"value": 3.14}'

    def test_decimal_encoder_nested(self) -> None:
        """Test DecimalEncoder handles nested structures."""
        data = {
            "int_val": Decimal("10"),
            "float_val": Decimal("2.5"),
            "nested": {"value": Decimal("100")},
        }
        result = json.loads(json.dumps(data, cls=DecimalEncoder))
        assert result["int_val"] == 10
        assert result["float_val"] == 2.5
        assert result["nested"]["value"] == 100

    def test_convert_floats_to_decimal_simple(self) -> None:
        """Test _convert_floats_to_decimal with simple float."""
        result = _convert_floats_to_decimal(3.14)
        assert isinstance(result, Decimal)
        assert result == Decimal("3.14")

    def test_convert_floats_to_decimal_dict(self) -> None:
        """Test _convert_floats_to_decimal with dict containing floats."""
        data = {"a": 1.5, "b": 2.5}
        result = _convert_floats_to_decimal(data)
        assert isinstance(result["a"], Decimal)
        assert isinstance(result["b"], Decimal)

    def test_convert_floats_to_decimal_list(self) -> None:
        """Test _convert_floats_to_decimal with list containing floats."""
        data = [1.1, 2.2, 3.3]
        result = _convert_floats_to_decimal(data)
        assert all(isinstance(v, Decimal) for v in result)

    def test_convert_floats_to_decimal_nested(self) -> None:
        """Test _convert_floats_to_decimal with nested structures."""
        data = {
            "outer": 1.5,
            "nested": {"inner": 2.5},
            "list": [3.5, 4.5],
        }
        result = _convert_floats_to_decimal(data)
        assert isinstance(result["outer"], Decimal)
        assert isinstance(result["nested"]["inner"], Decimal)
        assert all(isinstance(v, Decimal) for v in result["list"])

    def test_convert_floats_to_decimal_non_float(self) -> None:
        """Test _convert_floats_to_decimal preserves non-float types."""
        data = {"string": "hello", "int": 42, "none": None}
        result = _convert_floats_to_decimal(data)
        assert result["string"] == "hello"
        assert result["int"] == 42
        assert result["none"] is None

    def test_forced_memory_backend_via_env(self, mock_memory, monkeypatch) -> None:
        """Test forcing Memory backend via CHECKPOINT_BACKEND env var."""
        monkeypatch.setenv("CHECKPOINT_BACKEND", "memory")

        manager = CheckpointManager(
            session_id="test-session",
            agent_name="test-agent",
        )

        # Backend should be forced to Memory
        assert manager._use_memory is True
