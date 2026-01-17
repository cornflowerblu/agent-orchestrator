"""Unit tests for loop framework models.

T021: Tests for all enums
T022: Tests for LoopConfig validation
T023: Tests for ExitConditionStatus methods
"""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from src.loop.models import (
    Checkpoint,
    ExitConditionConfig,
    ExitConditionStatus,
    ExitConditionStatusValue,
    ExitConditionType,
    IterationEvent,
    IterationEventType,
    LoopConfig,
    LoopOutcome,
    LoopPhase,
    LoopResult,
    LoopState,
)

# =============================================================================
# T021: Enum Tests
# =============================================================================


class TestExitConditionType:
    """Tests for ExitConditionType enum (T007)."""

    def test_all_values_exist(self) -> None:
        """Verify all expected exit condition types exist."""
        assert ExitConditionType.ALL_TESTS_PASS.value == "all_tests_pass"
        assert ExitConditionType.BUILD_SUCCEEDS.value == "build_succeeds"
        assert ExitConditionType.LINTING_CLEAN.value == "linting_clean"
        assert ExitConditionType.SECURITY_SCAN_CLEAN.value == "security_scan_clean"
        assert ExitConditionType.CUSTOM.value == "custom"

    def test_enum_count(self) -> None:
        """Verify we have exactly 5 exit condition types."""
        assert len(ExitConditionType) == 5

    def test_is_str_enum(self) -> None:
        """Verify ExitConditionType is a string enum."""
        assert isinstance(ExitConditionType.ALL_TESTS_PASS, str)
        assert ExitConditionType.ALL_TESTS_PASS == "all_tests_pass"

    def test_can_create_from_string(self) -> None:
        """Verify enum can be created from string value."""
        condition_type = ExitConditionType("all_tests_pass")
        assert condition_type == ExitConditionType.ALL_TESTS_PASS


class TestExitConditionStatusValue:
    """Tests for ExitConditionStatusValue enum (T008)."""

    def test_all_values_exist(self) -> None:
        """Verify all expected status values exist."""
        assert ExitConditionStatusValue.PENDING.value == "pending"
        assert ExitConditionStatusValue.MET.value == "met"
        assert ExitConditionStatusValue.NOT_MET.value == "not_met"
        assert ExitConditionStatusValue.ERROR.value == "error"
        assert ExitConditionStatusValue.SKIPPED.value == "skipped"

    def test_enum_count(self) -> None:
        """Verify we have exactly 5 status values."""
        assert len(ExitConditionStatusValue) == 5

    def test_is_str_enum(self) -> None:
        """Verify ExitConditionStatusValue is a string enum."""
        assert isinstance(ExitConditionStatusValue.PENDING, str)
        assert ExitConditionStatusValue.PENDING == "pending"


class TestLoopPhase:
    """Tests for LoopPhase enum (T009)."""

    def test_all_values_exist(self) -> None:
        """Verify all expected loop phases exist."""
        assert LoopPhase.INITIALIZING.value == "initializing"
        assert LoopPhase.RUNNING.value == "running"
        assert LoopPhase.EVALUATING_CONDITIONS.value == "evaluating_conditions"
        assert LoopPhase.SAVING_CHECKPOINT.value == "saving_checkpoint"
        assert LoopPhase.COMPLETING.value == "completing"
        assert LoopPhase.COMPLETED.value == "completed"
        assert LoopPhase.ERROR.value == "error"

    def test_enum_count(self) -> None:
        """Verify we have exactly 7 loop phases."""
        assert len(LoopPhase) == 7

    def test_is_str_enum(self) -> None:
        """Verify LoopPhase is a string enum."""
        assert isinstance(LoopPhase.RUNNING, str)
        assert LoopPhase.RUNNING == "running"


class TestLoopOutcome:
    """Tests for LoopOutcome enum (T010)."""

    def test_all_values_exist(self) -> None:
        """Verify all expected loop outcomes exist."""
        assert LoopOutcome.COMPLETED.value == "completed"
        assert LoopOutcome.ITERATION_LIMIT.value == "iteration_limit"
        assert LoopOutcome.ERROR.value == "error"
        assert LoopOutcome.CANCELLED.value == "cancelled"
        assert LoopOutcome.TIMEOUT.value == "timeout"

    def test_enum_count(self) -> None:
        """Verify we have exactly 5 loop outcomes."""
        assert len(LoopOutcome) == 5

    def test_is_str_enum(self) -> None:
        """Verify LoopOutcome is a string enum."""
        assert isinstance(LoopOutcome.COMPLETED, str)
        assert LoopOutcome.COMPLETED == "completed"


class TestIterationEventType:
    """Tests for IterationEventType enum (T011)."""

    def test_all_values_exist(self) -> None:
        """Verify all expected event types exist."""
        assert IterationEventType.LOOP_STARTED.value == "loop.started"
        assert IterationEventType.ITERATION_STARTED.value == "loop.iteration.started"
        assert IterationEventType.ITERATION_COMPLETED.value == "loop.iteration.completed"
        assert IterationEventType.CHECKPOINT_SAVED.value == "loop.checkpoint.saved"
        assert IterationEventType.EXIT_CONDITION_EVALUATED.value == "loop.exit_condition.evaluated"
        assert IterationEventType.LOOP_COMPLETED.value == "loop.completed"
        assert IterationEventType.LOOP_ERROR.value == "loop.error"
        assert IterationEventType.POLICY_WARNING.value == "loop.policy.warning"
        assert IterationEventType.POLICY_VIOLATION.value == "loop.policy.violation"

    def test_enum_count(self) -> None:
        """Verify we have exactly 9 event types."""
        assert len(IterationEventType) == 9

    def test_is_str_enum(self) -> None:
        """Verify IterationEventType is a string enum."""
        assert isinstance(IterationEventType.LOOP_STARTED, str)
        assert IterationEventType.LOOP_STARTED == "loop.started"


# =============================================================================
# T022: LoopConfig Validation Tests
# =============================================================================


class TestLoopConfigValidation:
    """Tests for LoopConfig validation (T022)."""

    def test_minimal_valid_config(self) -> None:
        """Verify minimal config with just agent_name is valid."""
        config = LoopConfig(agent_name="test-agent")
        assert config.agent_name == "test-agent"
        assert config.max_iterations == 100
        assert config.checkpoint_interval == 5
        assert config.exit_conditions == []

    def test_full_valid_config(self) -> None:
        """Verify full config with all fields is valid."""
        config = LoopConfig(
            agent_name="test-agent",
            session_id="session-123",
            max_iterations=50,
            checkpoint_interval=10,
            checkpoint_expiry_seconds=7200,
            exit_conditions=[
                ExitConditionConfig(type=ExitConditionType.ALL_TESTS_PASS),
                ExitConditionConfig(
                    type=ExitConditionType.LINTING_CLEAN,
                    tool_name="ruff",
                ),
            ],
            iteration_timeout_seconds=600,
            verification_timeout_seconds=60,
            policy_engine_arn="arn:aws:bedrock-agent:us-east-1:123:policy/test",
            gateway_url="https://gateway.example.com",
            region="us-west-2",
            custom_metadata={"team": "platform"},
        )
        assert config.max_iterations == 50
        assert len(config.exit_conditions) == 2
        assert config.region == "us-west-2"

    def test_agent_name_required(self) -> None:
        """Verify agent_name is required."""
        with pytest.raises(ValidationError) as exc_info:
            LoopConfig()  # type: ignore[call-arg]
        assert "agent_name" in str(exc_info.value)

    def test_agent_name_min_length(self) -> None:
        """Verify agent_name cannot be empty."""
        with pytest.raises(ValidationError) as exc_info:
            LoopConfig(agent_name="")
        assert "agent_name" in str(exc_info.value)

    def test_agent_name_max_length(self) -> None:
        """Verify agent_name cannot exceed 64 characters."""
        with pytest.raises(ValidationError) as exc_info:
            LoopConfig(agent_name="a" * 65)
        assert "agent_name" in str(exc_info.value)

    def test_max_iterations_min_value(self) -> None:
        """Verify max_iterations must be at least 1."""
        with pytest.raises(ValidationError) as exc_info:
            LoopConfig(agent_name="test", max_iterations=0)
        assert "max_iterations" in str(exc_info.value)

    def test_max_iterations_max_value(self) -> None:
        """Verify max_iterations cannot exceed 10000."""
        with pytest.raises(ValidationError) as exc_info:
            LoopConfig(agent_name="test", max_iterations=10001)
        assert "max_iterations" in str(exc_info.value)

    def test_checkpoint_interval_min_value(self) -> None:
        """Verify checkpoint_interval must be at least 1."""
        with pytest.raises(ValidationError) as exc_info:
            LoopConfig(agent_name="test", checkpoint_interval=0)
        assert "checkpoint_interval" in str(exc_info.value)

    def test_checkpoint_interval_max_value(self) -> None:
        """Verify checkpoint_interval cannot exceed 100."""
        with pytest.raises(ValidationError) as exc_info:
            LoopConfig(agent_name="test", checkpoint_interval=101)
        assert "checkpoint_interval" in str(exc_info.value)

    def test_checkpoint_expiry_min_value(self) -> None:
        """Verify checkpoint_expiry_seconds must be at least 3600 (1 hour)."""
        with pytest.raises(ValidationError) as exc_info:
            LoopConfig(agent_name="test", checkpoint_expiry_seconds=3599)
        assert "checkpoint_expiry_seconds" in str(exc_info.value)

    def test_checkpoint_expiry_max_value(self) -> None:
        """Verify checkpoint_expiry_seconds cannot exceed 604800 (7 days)."""
        with pytest.raises(ValidationError) as exc_info:
            LoopConfig(agent_name="test", checkpoint_expiry_seconds=604801)
        assert "checkpoint_expiry_seconds" in str(exc_info.value)

    def test_iteration_timeout_min_value(self) -> None:
        """Verify iteration_timeout_seconds must be at least 30."""
        with pytest.raises(ValidationError) as exc_info:
            LoopConfig(agent_name="test", iteration_timeout_seconds=29)
        assert "iteration_timeout_seconds" in str(exc_info.value)

    def test_iteration_timeout_max_value(self) -> None:
        """Verify iteration_timeout_seconds cannot exceed 3600."""
        with pytest.raises(ValidationError) as exc_info:
            LoopConfig(agent_name="test", iteration_timeout_seconds=3601)
        assert "iteration_timeout_seconds" in str(exc_info.value)

    def test_verification_timeout_min_value(self) -> None:
        """Verify verification_timeout_seconds must be at least 5."""
        with pytest.raises(ValidationError) as exc_info:
            LoopConfig(agent_name="test", verification_timeout_seconds=4)
        assert "verification_timeout_seconds" in str(exc_info.value)

    def test_verification_timeout_max_value(self) -> None:
        """Verify verification_timeout_seconds cannot exceed 120."""
        with pytest.raises(ValidationError) as exc_info:
            LoopConfig(agent_name="test", verification_timeout_seconds=121)
        assert "verification_timeout_seconds" in str(exc_info.value)

    def test_custom_condition_requires_evaluator(self) -> None:
        """Verify CUSTOM condition type requires custom_evaluator."""
        with pytest.raises(ValidationError) as exc_info:
            LoopConfig(
                agent_name="test",
                exit_conditions=[
                    ExitConditionConfig(type=ExitConditionType.CUSTOM),
                ],
            )
        assert "custom_evaluator" in str(exc_info.value)

    def test_custom_condition_with_evaluator_valid(self) -> None:
        """Verify CUSTOM condition with evaluator is valid."""
        config = LoopConfig(
            agent_name="test",
            exit_conditions=[
                ExitConditionConfig(
                    type=ExitConditionType.CUSTOM,
                    custom_evaluator="mymodule.check_custom",
                ),
            ],
        )
        assert len(config.exit_conditions) == 1
        assert config.exit_conditions[0].custom_evaluator == "mymodule.check_custom"

    def test_empty_exit_conditions_allowed(self) -> None:
        """Verify empty exit_conditions list is allowed."""
        config = LoopConfig(agent_name="test", exit_conditions=[])
        assert config.exit_conditions == []

    def test_default_values(self) -> None:
        """Verify all default values are set correctly."""
        config = LoopConfig(agent_name="test")
        assert config.session_id is None
        assert config.max_iterations == 100
        assert config.checkpoint_interval == 5
        assert config.checkpoint_expiry_seconds == 86400
        assert config.exit_conditions == []
        assert config.iteration_timeout_seconds == 300
        assert config.verification_timeout_seconds == 30
        assert config.policy_engine_arn is None
        assert config.gateway_url is None
        assert config.region == "us-east-1"
        assert config.custom_metadata == {}


# =============================================================================
# T023: ExitConditionStatus Method Tests
# =============================================================================


class TestExitConditionStatusMethods:
    """Tests for ExitConditionStatus methods (T023)."""

    def test_initial_state_is_pending(self) -> None:
        """Verify new ExitConditionStatus is in PENDING state."""
        status = ExitConditionStatus(type=ExitConditionType.ALL_TESTS_PASS)
        assert status.status == ExitConditionStatusValue.PENDING
        assert status.tool_name is None
        assert status.tool_exit_code is None
        assert status.tool_output is None
        assert status.evaluated_at is None
        assert status.error_message is None

    def test_mark_met(self) -> None:
        """Verify mark_met sets correct values."""
        status = ExitConditionStatus(type=ExitConditionType.ALL_TESTS_PASS)

        with patch("src.loop.models.datetime") as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = "2026-01-17T10:00:00+00:00"
            mock_datetime.now.return_value = datetime(2026, 1, 17, 10, 0, 0, tzinfo=UTC)
            status.mark_met(
                tool_name="pytest",
                exit_code=0,
                output="15 passed in 2.3s",
                iteration=5,
            )

        assert status.status == ExitConditionStatusValue.MET
        assert status.tool_name == "pytest"
        assert status.tool_exit_code == 0
        assert status.tool_output == "15 passed in 2.3s"
        assert status.iteration_evaluated == 5
        assert status.evaluated_at is not None

    def test_mark_met_truncates_output(self) -> None:
        """Verify mark_met truncates output to 1000 chars."""
        status = ExitConditionStatus(type=ExitConditionType.ALL_TESTS_PASS)
        long_output = "x" * 2000

        status.mark_met(
            tool_name="pytest",
            exit_code=0,
            output=long_output,
            iteration=1,
        )

        assert len(status.tool_output) == 1000

    def test_mark_not_met(self) -> None:
        """Verify mark_not_met sets correct values."""
        status = ExitConditionStatus(type=ExitConditionType.LINTING_CLEAN)

        status.mark_not_met(
            tool_name="ruff",
            exit_code=1,
            output="Found 3 errors",
            iteration=10,
        )

        assert status.status == ExitConditionStatusValue.NOT_MET
        assert status.tool_name == "ruff"
        assert status.tool_exit_code == 1
        assert status.tool_output == "Found 3 errors"
        assert status.iteration_evaluated == 10
        assert status.evaluated_at is not None

    def test_mark_not_met_truncates_output(self) -> None:
        """Verify mark_not_met truncates output to 1000 chars."""
        status = ExitConditionStatus(type=ExitConditionType.LINTING_CLEAN)
        long_output = "y" * 1500

        status.mark_not_met(
            tool_name="ruff",
            exit_code=1,
            output=long_output,
            iteration=1,
        )

        assert len(status.tool_output) == 1000

    def test_mark_error(self) -> None:
        """Verify mark_error sets correct values."""
        status = ExitConditionStatus(type=ExitConditionType.BUILD_SUCCEEDS)

        status.mark_error(
            error="Tool execution timeout after 30s",
            iteration=7,
        )

        assert status.status == ExitConditionStatusValue.ERROR
        assert status.error_message == "Tool execution timeout after 30s"
        assert status.iteration_evaluated == 7
        assert status.evaluated_at is not None

    def test_mark_skipped(self) -> None:
        """Verify mark_skipped sets correct values."""
        status = ExitConditionStatus(type=ExitConditionType.SECURITY_SCAN_CLEAN)

        status.mark_skipped(
            reason="Security scan not configured",
            iteration=3,
        )

        assert status.status == ExitConditionStatusValue.SKIPPED
        assert status.error_message == "Security scan not configured"
        assert status.iteration_evaluated == 3
        assert status.evaluated_at is not None

    def test_is_terminal_met(self) -> None:
        """Verify is_terminal returns True for MET status."""
        status = ExitConditionStatus(type=ExitConditionType.ALL_TESTS_PASS)
        status.status = ExitConditionStatusValue.MET
        assert status.is_terminal() is True

    def test_is_terminal_error(self) -> None:
        """Verify is_terminal returns True for ERROR status."""
        status = ExitConditionStatus(type=ExitConditionType.ALL_TESTS_PASS)
        status.status = ExitConditionStatusValue.ERROR
        assert status.is_terminal() is True

    def test_is_terminal_pending(self) -> None:
        """Verify is_terminal returns False for PENDING status."""
        status = ExitConditionStatus(type=ExitConditionType.ALL_TESTS_PASS)
        status.status = ExitConditionStatusValue.PENDING
        assert status.is_terminal() is False

    def test_is_terminal_not_met(self) -> None:
        """Verify is_terminal returns False for NOT_MET status."""
        status = ExitConditionStatus(type=ExitConditionType.ALL_TESTS_PASS)
        status.status = ExitConditionStatusValue.NOT_MET
        assert status.is_terminal() is False

    def test_is_terminal_skipped(self) -> None:
        """Verify is_terminal returns False for SKIPPED status."""
        status = ExitConditionStatus(type=ExitConditionType.ALL_TESTS_PASS)
        status.status = ExitConditionStatusValue.SKIPPED
        assert status.is_terminal() is False

    def test_reset(self) -> None:
        """Verify reset clears all evaluation data."""
        status = ExitConditionStatus(type=ExitConditionType.ALL_TESTS_PASS)
        status.mark_met("pytest", 0, "10 passed", 5)

        status.reset()

        assert status.status == ExitConditionStatusValue.PENDING
        assert status.tool_exit_code is None
        assert status.tool_output is None
        assert status.evaluated_at is None
        assert status.evaluation_duration_ms is None
        assert status.error_message is None
        assert status.iteration_evaluated is None
        # tool_name should still be set (from the original condition)
        # Actually per the model, reset clears tool values too
        # Let me check the model... the reset method doesn't clear tool_name
        # which is intentional as it may have been set from config


class TestExitConditionConfig:
    """Tests for ExitConditionConfig model (T012)."""

    def test_minimal_config(self) -> None:
        """Verify minimal config with just type is valid."""
        config = ExitConditionConfig(type=ExitConditionType.ALL_TESTS_PASS)
        assert config.type == ExitConditionType.ALL_TESTS_PASS
        assert config.tool_name is None
        assert config.tool_arguments == {}
        assert config.custom_evaluator is None
        assert config.description == ""

    def test_full_config(self) -> None:
        """Verify full config with all fields."""
        config = ExitConditionConfig(
            type=ExitConditionType.LINTING_CLEAN,
            tool_name="ruff",
            tool_arguments={"path": "src/", "fix": True},
            description="Check linting with ruff",
        )
        assert config.type == ExitConditionType.LINTING_CLEAN
        assert config.tool_name == "ruff"
        assert config.tool_arguments == {"path": "src/", "fix": True}
        assert config.description == "Check linting with ruff"

    def test_custom_with_evaluator(self) -> None:
        """Verify custom config with evaluator."""
        config = ExitConditionConfig(
            type=ExitConditionType.CUSTOM,
            custom_evaluator="myapp.conditions.check_database",
            description="Custom database check",
        )
        assert config.custom_evaluator == "myapp.conditions.check_database"


class TestIterationEvent:
    """Tests for IterationEvent model (T015)."""

    def test_minimal_event(self) -> None:
        """Verify minimal event with required fields."""
        event = IterationEvent(
            event_type=IterationEventType.LOOP_STARTED,
            session_id="session-123",
            agent_name="test-agent",
            iteration=0,
            max_iterations=100,
        )
        assert event.event_type == IterationEventType.LOOP_STARTED
        assert event.session_id == "session-123"
        assert event.agent_name == "test-agent"
        assert event.iteration == 0
        assert event.max_iterations == 100
        assert event.timestamp is not None

    def test_to_otel_attributes(self) -> None:
        """Verify to_otel_attributes returns correct dictionary."""
        event = IterationEvent(
            event_type=IterationEventType.ITERATION_COMPLETED,
            session_id="session-123",
            agent_name="test-agent",
            iteration=5,
            max_iterations=100,
            duration_ms=1500,
            exit_conditions_met=2,
            exit_conditions_total=3,
            phase=LoopPhase.RUNNING,
        )

        attrs = event.to_otel_attributes()

        assert attrs["event.type"] == "loop.iteration.completed"
        assert attrs["session.id"] == "session-123"
        assert attrs["loop.agent_name"] == "test-agent"
        assert attrs["iteration.number"] == 5
        assert attrs["iteration.max"] == 100
        assert attrs["loop.phase"] == "running"
        assert attrs["exit_conditions.met"] == 2
        assert attrs["exit_conditions.total"] == 3
        assert attrs["duration.ms"] == 1500
        assert attrs["gen_ai.operation.name"] == "autonomous_loop"
        assert attrs["PlatformType"] == "AWS::BedrockAgentCore"

    def test_to_otel_attributes_with_error(self) -> None:
        """Verify to_otel_attributes includes error message."""
        event = IterationEvent(
            event_type=IterationEventType.LOOP_ERROR,
            session_id="session-123",
            agent_name="test-agent",
            iteration=10,
            max_iterations=100,
            error_message="Tool execution failed",
        )

        attrs = event.to_otel_attributes()

        assert attrs["error.message"] == "Tool execution failed"

    def test_progress_percentage(self) -> None:
        """Verify progress_percentage calculation."""
        event = IterationEvent(
            event_type=IterationEventType.ITERATION_STARTED,
            session_id="session-123",
            agent_name="test-agent",
            iteration=25,
            max_iterations=100,
        )

        assert event.progress_percentage() == 25.0

    def test_progress_percentage_zero_max(self) -> None:
        """Verify progress_percentage handles zero max_iterations."""
        event = IterationEvent(
            event_type=IterationEventType.ITERATION_STARTED,
            session_id="session-123",
            agent_name="test-agent",
            iteration=5,
            max_iterations=0,
        )

        assert event.progress_percentage() == 0.0


class TestLoopResult:
    """Tests for LoopResult model (T016)."""

    def test_minimal_result(self) -> None:
        """Verify minimal result with required fields."""
        result = LoopResult(
            session_id="session-123",
            agent_name="test-agent",
            outcome=LoopOutcome.COMPLETED,
            iterations_completed=50,
            max_iterations=100,
            started_at="2026-01-17T09:00:00+00:00",
            duration_seconds=120.5,
        )
        assert result.outcome == LoopOutcome.COMPLETED
        assert result.iterations_completed == 50

    def test_is_success_completed(self) -> None:
        """Verify is_success returns True for COMPLETED outcome."""
        result = LoopResult(
            session_id="session-123",
            agent_name="test-agent",
            outcome=LoopOutcome.COMPLETED,
            iterations_completed=50,
            max_iterations=100,
            started_at="2026-01-17T09:00:00+00:00",
            duration_seconds=120.5,
        )
        assert result.is_success() is True

    def test_is_success_iteration_limit(self) -> None:
        """Verify is_success returns False for ITERATION_LIMIT outcome."""
        result = LoopResult(
            session_id="session-123",
            agent_name="test-agent",
            outcome=LoopOutcome.ITERATION_LIMIT,
            iterations_completed=100,
            max_iterations=100,
            started_at="2026-01-17T09:00:00+00:00",
            duration_seconds=500.0,
        )
        assert result.is_success() is False

    def test_is_success_error(self) -> None:
        """Verify is_success returns False for ERROR outcome."""
        result = LoopResult(
            session_id="session-123",
            agent_name="test-agent",
            outcome=LoopOutcome.ERROR,
            iterations_completed=25,
            max_iterations=100,
            started_at="2026-01-17T09:00:00+00:00",
            duration_seconds=60.0,
            error_message="Unrecoverable error",
        )
        assert result.is_success() is False

    def test_summary(self) -> None:
        """Verify summary generates correct string."""
        result = LoopResult(
            session_id="session-123",
            agent_name="test-agent",
            outcome=LoopOutcome.COMPLETED,
            iterations_completed=50,
            max_iterations=100,
            started_at="2026-01-17T09:00:00+00:00",
            duration_seconds=120.5,
            final_exit_conditions=[
                ExitConditionStatus(
                    type=ExitConditionType.ALL_TESTS_PASS,
                    status=ExitConditionStatusValue.MET,
                ),
                ExitConditionStatus(
                    type=ExitConditionType.LINTING_CLEAN,
                    status=ExitConditionStatusValue.MET,
                ),
                ExitConditionStatus(
                    type=ExitConditionType.BUILD_SUCCEEDS,
                    status=ExitConditionStatusValue.NOT_MET,
                ),
            ],
        )

        summary = result.summary()

        assert "session-123" in summary
        assert "completed" in summary
        assert "50/100" in summary
        assert "120.5s" in summary
        assert "2/3 met" in summary

    def test_conditions_summary(self) -> None:
        """Verify conditions_summary returns correct counts."""
        result = LoopResult(
            session_id="session-123",
            agent_name="test-agent",
            outcome=LoopOutcome.COMPLETED,
            iterations_completed=50,
            max_iterations=100,
            started_at="2026-01-17T09:00:00+00:00",
            duration_seconds=120.5,
            final_exit_conditions=[
                ExitConditionStatus(
                    type=ExitConditionType.ALL_TESTS_PASS,
                    status=ExitConditionStatusValue.MET,
                ),
                ExitConditionStatus(
                    type=ExitConditionType.LINTING_CLEAN,
                    status=ExitConditionStatusValue.MET,
                ),
                ExitConditionStatus(
                    type=ExitConditionType.BUILD_SUCCEEDS,
                    status=ExitConditionStatusValue.NOT_MET,
                ),
                ExitConditionStatus(
                    type=ExitConditionType.SECURITY_SCAN_CLEAN,
                    status=ExitConditionStatusValue.ERROR,
                ),
            ],
        )

        summary = result.conditions_summary()

        assert summary["met"] == 2
        assert summary["not_met"] == 1
        assert summary["error"] == 1
        assert summary["pending"] == 0
        assert summary["skipped"] == 0


# =============================================================================
# T036: LoopState Model Tests
# =============================================================================


class TestLoopState:
    """Tests for LoopState model (T024)."""

    def test_create_minimal_loop_state(self) -> None:
        """Test creating LoopState with minimal required fields."""
        state = LoopState(
            session_id="test-session-123",
            agent_name="test-agent",
            max_iterations=100,
        )

        assert state.session_id == "test-session-123"
        assert state.agent_name == "test-agent"
        assert state.current_iteration == 0
        assert state.max_iterations == 100
        assert state.phase == LoopPhase.INITIALIZING
        assert state.is_active is False
        assert state.exit_conditions == []
        assert state.agent_state == {}

    def test_loop_state_defaults(self) -> None:
        """Test LoopState default values."""
        state = LoopState(
            session_id="test-session",
            agent_name="agent",
            max_iterations=50,
        )

        assert state.current_iteration == 0
        assert state.phase == LoopPhase.INITIALIZING
        assert state.last_iteration_at is None
        assert state.last_checkpoint_at is None
        assert state.last_checkpoint_iteration is None
        assert state.is_active is False
        assert isinstance(state.started_at, str)  # ISO timestamp
        assert state.exit_conditions == []
        assert state.agent_state == {}

    def test_loop_state_with_exit_conditions(self) -> None:
        """Test LoopState with exit conditions."""
        conditions = [
            ExitConditionStatus(
                type=ExitConditionType.ALL_TESTS_PASS,
                status=ExitConditionStatusValue.PENDING,
            ),
            ExitConditionStatus(
                type=ExitConditionType.LINTING_CLEAN,
                status=ExitConditionStatusValue.PENDING,
            ),
        ]

        state = LoopState(
            session_id="test-session",
            agent_name="agent",
            max_iterations=100,
            exit_conditions=conditions,
        )

        assert len(state.exit_conditions) == 2
        assert state.exit_conditions[0].type == ExitConditionType.ALL_TESTS_PASS
        assert state.exit_conditions[1].type == ExitConditionType.LINTING_CLEAN

    def test_all_conditions_met_with_no_conditions(self) -> None:
        """Test all_conditions_met returns False when no conditions."""
        state = LoopState(
            session_id="test-session",
            agent_name="agent",
            max_iterations=100,
            exit_conditions=[],
        )

        assert state.all_conditions_met() is False

    def test_all_conditions_met_with_pending_conditions(self) -> None:
        """Test all_conditions_met returns False when conditions pending."""
        state = LoopState(
            session_id="test-session",
            agent_name="agent",
            max_iterations=100,
            exit_conditions=[
                ExitConditionStatus(
                    type=ExitConditionType.ALL_TESTS_PASS,
                    status=ExitConditionStatusValue.PENDING,
                ),
            ],
        )

        assert state.all_conditions_met() is False

    def test_all_conditions_met_with_some_met(self) -> None:
        """Test all_conditions_met returns False when only some conditions met."""
        state = LoopState(
            session_id="test-session",
            agent_name="agent",
            max_iterations=100,
            exit_conditions=[
                ExitConditionStatus(
                    type=ExitConditionType.ALL_TESTS_PASS,
                    status=ExitConditionStatusValue.MET,
                ),
                ExitConditionStatus(
                    type=ExitConditionType.LINTING_CLEAN,
                    status=ExitConditionStatusValue.PENDING,
                ),
            ],
        )

        assert state.all_conditions_met() is False

    def test_all_conditions_met_with_all_met(self) -> None:
        """Test all_conditions_met returns True when all conditions met."""
        state = LoopState(
            session_id="test-session",
            agent_name="agent",
            max_iterations=100,
            exit_conditions=[
                ExitConditionStatus(
                    type=ExitConditionType.ALL_TESTS_PASS,
                    status=ExitConditionStatusValue.MET,
                ),
                ExitConditionStatus(
                    type=ExitConditionType.LINTING_CLEAN,
                    status=ExitConditionStatusValue.MET,
                ),
            ],
        )

        assert state.all_conditions_met() is True

    def test_progress_percentage(self) -> None:
        """Test progress_percentage calculation."""
        state = LoopState(
            session_id="test-session",
            agent_name="agent",
            max_iterations=100,
            current_iteration=25,
        )

        assert state.progress_percentage() == 25.0

        state.current_iteration = 50
        assert state.progress_percentage() == 50.0

        state.current_iteration = 100
        assert state.progress_percentage() == 100.0

    def test_progress_percentage_zero_iterations(self) -> None:
        """Test progress_percentage when current_iteration is 0."""
        state = LoopState(
            session_id="test-session",
            agent_name="agent",
            max_iterations=100,
            current_iteration=0,
        )

        assert state.progress_percentage() == 0.0

    def test_at_warning_threshold_default(self) -> None:
        """Test at_warning_threshold with default 80% threshold."""
        state = LoopState(
            session_id="test-session",
            agent_name="agent",
            max_iterations=100,
            current_iteration=79,
        )

        assert state.at_warning_threshold() is False

        state.current_iteration = 80
        assert state.at_warning_threshold() is True

        state.current_iteration = 90
        assert state.at_warning_threshold() is True

    def test_at_warning_threshold_custom(self) -> None:
        """Test at_warning_threshold with custom threshold."""
        state = LoopState(
            session_id="test-session",
            agent_name="agent",
            max_iterations=100,
            current_iteration=60,
        )

        assert state.at_warning_threshold(threshold=0.5) is True
        assert state.at_warning_threshold(threshold=0.7) is False

        state.current_iteration = 70
        assert state.at_warning_threshold(threshold=0.7) is True

    def test_loop_state_serialization(self) -> None:
        """Test LoopState can be serialized to dict/JSON."""
        state = LoopState(
            session_id="test-session",
            agent_name="agent",
            max_iterations=100,
            current_iteration=10,
            phase=LoopPhase.RUNNING,
            is_active=True,
            agent_state={"key": "value"},
        )

        data = state.model_dump()

        assert data["session_id"] == "test-session"
        assert data["agent_name"] == "agent"
        assert data["max_iterations"] == 100
        assert data["current_iteration"] == 10
        assert data["phase"] == "running"
        assert data["is_active"] is True
        assert data["agent_state"] == {"key": "value"}

    def test_loop_state_deserialization(self) -> None:
        """Test LoopState can be created from dict."""
        data = {
            "session_id": "test-session",
            "agent_name": "agent",
            "max_iterations": 100,
            "current_iteration": 10,
            "phase": "running",
            "is_active": True,
            "started_at": "2026-01-17T10:00:00Z",
            "agent_state": {"key": "value"},
            "exit_conditions": [],
        }

        state = LoopState(**data)

        assert state.session_id == "test-session"
        assert state.current_iteration == 10
        assert state.phase == LoopPhase.RUNNING
        assert state.is_active is True

    def test_loop_state_validation_negative_iteration(self) -> None:
        """Test LoopState validation rejects negative current_iteration."""
        with pytest.raises(ValidationError) as exc_info:
            LoopState(
                session_id="test-session",
                agent_name="agent",
                max_iterations=100,
                current_iteration=-1,
            )

        assert "current_iteration" in str(exc_info.value)

    def test_loop_state_validation_zero_max_iterations(self) -> None:
        """Test LoopState validation rejects zero max_iterations."""
        with pytest.raises(ValidationError) as exc_info:
            LoopState(
                session_id="test-session",
                agent_name="agent",
                max_iterations=0,
            )

        assert "max_iterations" in str(exc_info.value)

    def test_loop_state_validation_negative_max_iterations(self) -> None:
        """Test LoopState validation rejects negative max_iterations."""
        with pytest.raises(ValidationError) as exc_info:
            LoopState(
                session_id="test-session",
                agent_name="agent",
                max_iterations=-10,
            )

        assert "max_iterations" in str(exc_info.value)


# =============================================================================
# T072: Checkpoint Model Tests (User Story 2)
# =============================================================================


class TestCheckpoint:
    """Tests for Checkpoint model (T059, T060, T061)."""

    def test_from_loop_state_creates_checkpoint(self) -> None:
        """Test Checkpoint.from_loop_state() creates checkpoint from LoopState."""
        # Create a LoopState with test data
        loop_state = LoopState(
            session_id="test-session-123",
            agent_name="test-agent",
            max_iterations=100,
            current_iteration=10,
            phase=LoopPhase.RUNNING,
            is_active=True,
            exit_conditions=[
                ExitConditionStatus(
                    type=ExitConditionType.ALL_TESTS_PASS,
                    status=ExitConditionStatusValue.MET,
                ),
            ],
            agent_state={"key": "value"},
        )

        # Create checkpoint from loop state
        checkpoint = Checkpoint.from_loop_state(loop_state)

        # Verify checkpoint contains correct data
        assert checkpoint.session_id == "test-session-123"
        assert checkpoint.iteration == 10
        assert checkpoint.loop_state_snapshot == loop_state.model_dump()
        assert checkpoint.created_at is not None
        assert checkpoint.agent_name == "test-agent"

    def test_to_loop_state_reconstructs_state(self) -> None:
        """Test Checkpoint.to_loop_state() reconstructs LoopState from checkpoint."""
        # Create original LoopState
        original_state = LoopState(
            session_id="test-session-456",
            agent_name="test-agent",
            max_iterations=50,
            current_iteration=25,
            phase=LoopPhase.EVALUATING_CONDITIONS,
            is_active=False,
            exit_conditions=[
                ExitConditionStatus(
                    type=ExitConditionType.LINTING_CLEAN,
                    status=ExitConditionStatusValue.NOT_MET,
                ),
            ],
            agent_state={"counter": 42},
        )

        # Create checkpoint and reconstruct
        checkpoint = Checkpoint.from_loop_state(original_state)
        reconstructed_state = checkpoint.to_loop_state()

        # Verify reconstructed state matches original
        assert reconstructed_state.session_id == original_state.session_id
        assert reconstructed_state.agent_name == original_state.agent_name
        assert reconstructed_state.max_iterations == original_state.max_iterations
        assert reconstructed_state.current_iteration == original_state.current_iteration
        assert reconstructed_state.phase == original_state.phase
        assert reconstructed_state.is_active == original_state.is_active
        assert len(reconstructed_state.exit_conditions) == 1
        assert reconstructed_state.exit_conditions[0].type == ExitConditionType.LINTING_CLEAN
        assert reconstructed_state.agent_state == {"counter": 42}

    def test_checkpoint_roundtrip(self) -> None:
        """Test full roundtrip: LoopState -> Checkpoint -> LoopState."""
        # Create a complex LoopState
        original_state = LoopState(
            session_id="roundtrip-session",
            agent_name="roundtrip-agent",
            max_iterations=200,
            current_iteration=75,
            phase=LoopPhase.RUNNING,
            is_active=True,
            started_at="2026-01-17T10:00:00Z",
            last_iteration_at="2026-01-17T10:05:00Z",
            last_checkpoint_at="2026-01-17T10:04:00Z",
            last_checkpoint_iteration=70,
            exit_conditions=[
                ExitConditionStatus(
                    type=ExitConditionType.ALL_TESTS_PASS,
                    status=ExitConditionStatusValue.MET,
                ),
                ExitConditionStatus(
                    type=ExitConditionType.BUILD_SUCCEEDS,
                    status=ExitConditionStatusValue.NOT_MET,
                ),
            ],
            agent_state={"nested": {"data": [1, 2, 3]}, "flag": True},
        )

        # Roundtrip
        checkpoint = Checkpoint.from_loop_state(original_state)
        restored_state = checkpoint.to_loop_state()

        # Verify all fields preserved
        assert restored_state.model_dump() == original_state.model_dump()

    def test_checkpoint_has_unique_id(self) -> None:
        """Test that each checkpoint has a unique checkpoint_id."""
        loop_state = LoopState(
            session_id="test-session",
            agent_name="test-agent",
            max_iterations=100,
            current_iteration=5,
        )

        checkpoint1 = Checkpoint.from_loop_state(loop_state)
        checkpoint2 = Checkpoint.from_loop_state(loop_state)

        # Each checkpoint should have an ID
        assert checkpoint1.checkpoint_id is not None
        assert checkpoint2.checkpoint_id is not None
        # IDs should be different (UUID-based)
        assert checkpoint1.checkpoint_id != checkpoint2.checkpoint_id

    def test_checkpoint_serialization(self) -> None:
        """Test Checkpoint can be serialized to dict/JSON for Memory storage."""
        loop_state = LoopState(
            session_id="test-session",
            agent_name="test-agent",
            max_iterations=100,
            current_iteration=10,
            phase=LoopPhase.RUNNING,
        )

        checkpoint = Checkpoint.from_loop_state(loop_state)
        data = checkpoint.model_dump()

        # Verify serialized format
        assert "checkpoint_id" in data
        assert "session_id" in data
        assert "iteration" in data
        assert "loop_state_snapshot" in data
        assert "created_at" in data
        assert "agent_name" in data
        assert data["session_id"] == "test-session"
        assert data["iteration"] == 10

    def test_checkpoint_deserialization(self) -> None:
        """Test Checkpoint can be created from dict (from Memory)."""
        data = {
            "checkpoint_id": "checkpoint-123",
            "session_id": "test-session",
            "iteration": 15,
            "loop_state_snapshot": {
                "session_id": "test-session",
                "agent_name": "test-agent",
                "max_iterations": 100,
                "current_iteration": 15,
                "phase": "running",
                "is_active": False,
                "started_at": "2026-01-17T10:00:00Z",
                "exit_conditions": [],
                "agent_state": {},
            },
            "created_at": "2026-01-17T10:05:00Z",
            "agent_name": "test-agent",
        }

        checkpoint = Checkpoint(**data)

        assert checkpoint.checkpoint_id == "checkpoint-123"
        assert checkpoint.session_id == "test-session"
        assert checkpoint.iteration == 15
        assert checkpoint.agent_name == "test-agent"
        assert checkpoint.loop_state_snapshot["current_iteration"] == 15

    def test_checkpoint_preserves_exit_condition_state(self) -> None:
        """Test that checkpoint preserves full exit condition status."""
        loop_state = LoopState(
            session_id="test-session",
            agent_name="test-agent",
            max_iterations=100,
            current_iteration=20,
            exit_conditions=[
                ExitConditionStatus(
                    type=ExitConditionType.ALL_TESTS_PASS,
                    status=ExitConditionStatusValue.MET,
                    tool_name="pytest",
                    tool_exit_code=0,
                    tool_output="25 passed in 3.5s",
                    evaluated_at="2026-01-17T10:00:00Z",
                    iteration_evaluated=20,
                ),
                ExitConditionStatus(
                    type=ExitConditionType.LINTING_CLEAN,
                    status=ExitConditionStatusValue.NOT_MET,
                    tool_name="ruff",
                    tool_exit_code=1,
                    tool_output="Found 5 errors",
                    evaluated_at="2026-01-17T10:00:01Z",
                    iteration_evaluated=20,
                ),
            ],
        )

        checkpoint = Checkpoint.from_loop_state(loop_state)
        restored = checkpoint.to_loop_state()

        # Verify exit conditions preserved
        assert len(restored.exit_conditions) == 2
        assert restored.exit_conditions[0].status == ExitConditionStatusValue.MET
        assert restored.exit_conditions[0].tool_name == "pytest"
        assert restored.exit_conditions[0].tool_exit_code == 0
        assert restored.exit_conditions[0].iteration_evaluated == 20
        assert restored.exit_conditions[1].status == ExitConditionStatusValue.NOT_MET
        assert restored.exit_conditions[1].tool_name == "ruff"
