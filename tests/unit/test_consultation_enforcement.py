"""Unit tests for consultation enforcement engine.

Tests for ConsultationEngine methods to improve coverage.
"""

from unittest.mock import MagicMock

import pytest

from src.consultation.enforcement import ConsultationEngine, ValidationResult
from src.consultation.rules import (
    ConsultationCondition,
    ConsultationOutcome,
    ConsultationPhase,
    ConsultationRequirement,
)


class TestConsultationEngineInit:
    """Tests for ConsultationEngine initialization."""

    def test_init_with_no_requirements(self):
        """Test initialization with no requirements."""
        engine = ConsultationEngine()
        assert engine._requirements == []
        assert engine._observability_client is None

    def test_init_with_requirements(self):
        """Test initialization with requirements list."""
        requirements = [
            ConsultationRequirement(
                agent_name="security-agent", phase=ConsultationPhase.PRE_COMPLETION, mandatory=True
            )
        ]
        engine = ConsultationEngine(requirements=requirements)
        assert len(engine._requirements) == 1

    def test_init_with_observability_client(self):
        """Test initialization with observability client."""
        mock_client = MagicMock()
        engine = ConsultationEngine(observability_client=mock_client)
        assert engine._observability_client == mock_client


class TestGetRequirements:
    """Tests for get_requirements method."""

    @pytest.fixture
    def engine_with_requirements(self):
        """Create engine with mixed requirements."""
        requirements = [
            ConsultationRequirement(
                agent_name="security-agent", phase=ConsultationPhase.PRE_COMPLETION, mandatory=True
            ),
            ConsultationRequirement(
                agent_name="testing-agent", phase=ConsultationPhase.PRE_COMPLETION, mandatory=False
            ),
            ConsultationRequirement(
                agent_name="architect-agent", phase=ConsultationPhase.DESIGN_REVIEW, mandatory=True
            ),
            ConsultationRequirement(
                agent_name="error-handler", phase=ConsultationPhase.ON_ERROR, mandatory=True
            ),
        ]
        return ConsultationEngine(requirements=requirements)

    def test_get_requirements_all_phases(self, engine_with_requirements):
        """Test getting requirements for all phases."""
        pre_completion = engine_with_requirements.get_requirements(ConsultationPhase.PRE_COMPLETION)
        assert len(pre_completion) == 2

        design_review = engine_with_requirements.get_requirements(ConsultationPhase.DESIGN_REVIEW)
        assert len(design_review) == 1

        on_error = engine_with_requirements.get_requirements(ConsultationPhase.ON_ERROR)
        assert len(on_error) == 1

        pre_execution = engine_with_requirements.get_requirements(ConsultationPhase.PRE_EXECUTION)
        assert len(pre_execution) == 0

    def test_get_requirements_mandatory_only(self, engine_with_requirements):
        """Test filtering for mandatory requirements only."""
        mandatory = engine_with_requirements.get_requirements(
            ConsultationPhase.PRE_COMPLETION, mandatory_only=True
        )
        assert len(mandatory) == 1
        assert mandatory[0].agent_name == "security-agent"


class TestEvaluateCondition:
    """Tests for evaluate_condition method."""

    @pytest.fixture
    def engine(self):
        return ConsultationEngine()

    def test_equals_operator_true(self, engine):
        """Test equals operator when condition is met."""
        condition = ConsultationCondition(field="task.type", operator="equals", value="security")
        context = {"task": {"type": "security"}}
        assert engine.evaluate_condition(condition, context) is True

    def test_equals_operator_false(self, engine):
        """Test equals operator when condition is not met."""
        condition = ConsultationCondition(field="task.type", operator="equals", value="security")
        context = {"task": {"type": "feature"}}
        assert engine.evaluate_condition(condition, context) is False

    def test_not_equals_operator_true(self, engine):
        """Test not_equals operator when values differ."""
        condition = ConsultationCondition(field="task.priority", operator="not_equals", value="low")
        context = {"task": {"priority": "high"}}
        assert engine.evaluate_condition(condition, context) is True

    def test_not_equals_operator_false(self, engine):
        """Test not_equals operator when values are same."""
        condition = ConsultationCondition(field="task.priority", operator="not_equals", value="low")
        context = {"task": {"priority": "low"}}
        assert engine.evaluate_condition(condition, context) is False

    def test_contains_operator_list(self, engine):
        """Test contains operator with list field."""
        condition = ConsultationCondition(field="task.tags", operator="contains", value="security")
        context = {"task": {"tags": ["security", "compliance"]}}
        assert engine.evaluate_condition(condition, context) is True

    def test_contains_operator_string(self, engine):
        """Test contains operator with string field."""
        condition = ConsultationCondition(
            field="task.description", operator="contains", value="security"
        )
        context = {"task": {"description": "This is a security review task"}}
        assert engine.evaluate_condition(condition, context) is True

    def test_contains_operator_not_found(self, engine):
        """Test contains operator when value not found."""
        condition = ConsultationCondition(field="task.tags", operator="contains", value="security")
        context = {"task": {"tags": ["feature", "enhancement"]}}
        assert engine.evaluate_condition(condition, context) is False

    def test_contains_operator_invalid_type(self, engine):
        """Test contains operator with invalid field type."""
        condition = ConsultationCondition(field="task.count", operator="contains", value="test")
        context = {"task": {"count": 42}}
        assert engine.evaluate_condition(condition, context) is False

    def test_not_contains_operator_list(self, engine):
        """Test not_contains operator with list field."""
        condition = ConsultationCondition(
            field="task.tags", operator="not_contains", value="security"
        )
        context = {"task": {"tags": ["feature", "enhancement"]}}
        assert engine.evaluate_condition(condition, context) is True

    def test_not_contains_operator_string(self, engine):
        """Test not_contains operator with string field."""
        condition = ConsultationCondition(
            field="task.description", operator="not_contains", value="security"
        )
        context = {"task": {"description": "This is a feature task"}}
        assert engine.evaluate_condition(condition, context) is True

    def test_not_contains_operator_found(self, engine):
        """Test not_contains operator when value is found."""
        condition = ConsultationCondition(
            field="task.tags", operator="not_contains", value="security"
        )
        context = {"task": {"tags": ["security", "compliance"]}}
        assert engine.evaluate_condition(condition, context) is False

    def test_not_contains_operator_invalid_type(self, engine):
        """Test not_contains operator with invalid field type."""
        condition = ConsultationCondition(field="task.count", operator="not_contains", value="test")
        context = {"task": {"count": 42}}
        assert engine.evaluate_condition(condition, context) is True

    def test_in_operator_true(self, engine):
        """Test in operator when value is in list."""
        condition = ConsultationCondition(
            field="task.priority", operator="in", value=["high", "critical"]
        )
        context = {"task": {"priority": "high"}}
        assert engine.evaluate_condition(condition, context) is True

    def test_in_operator_false(self, engine):
        """Test in operator when value is not in list."""
        condition = ConsultationCondition(
            field="task.priority", operator="in", value=["high", "critical"]
        )
        context = {"task": {"priority": "low"}}
        assert engine.evaluate_condition(condition, context) is False

    def test_in_operator_invalid_expected_value(self, engine):
        """Test in operator with non-list expected value."""
        condition = ConsultationCondition(
            field="task.priority",
            operator="in",
            value="high",  # Not a list
        )
        context = {"task": {"priority": "high"}}
        assert engine.evaluate_condition(condition, context) is False

    def test_not_in_operator_true(self, engine):
        """Test not_in operator when value is not in list."""
        condition = ConsultationCondition(
            field="task.priority", operator="not_in", value=["high", "critical"]
        )
        context = {"task": {"priority": "low"}}
        assert engine.evaluate_condition(condition, context) is True

    def test_not_in_operator_false(self, engine):
        """Test not_in operator when value is in list."""
        condition = ConsultationCondition(
            field="task.priority", operator="not_in", value=["high", "critical"]
        )
        context = {"task": {"priority": "high"}}
        assert engine.evaluate_condition(condition, context) is False

    def test_not_in_operator_invalid_expected_value(self, engine):
        """Test not_in operator with non-list expected value."""
        condition = ConsultationCondition(
            field="task.priority",
            operator="not_in",
            value="high",  # Not a list
        )
        context = {"task": {"priority": "high"}}
        assert engine.evaluate_condition(condition, context) is True

    def test_nested_field_access(self, engine):
        """Test accessing deeply nested fields."""
        condition = ConsultationCondition(
            field="task.metadata.review.required", operator="equals", value=True
        )
        context = {"task": {"metadata": {"review": {"required": True}}}}
        assert engine.evaluate_condition(condition, context) is True

    def test_missing_field_returns_none(self, engine):
        """Test that missing field path returns None for comparison."""
        condition = ConsultationCondition(
            field="task.missing.field", operator="equals", value="test"
        )
        context = {"task": {"type": "feature"}}
        assert engine.evaluate_condition(condition, context) is False

    def test_unknown_operator_returns_false(self, engine):
        """Test that unknown operator returns False."""
        # Bypass validation to test internal behavior
        condition = MagicMock()
        condition.field = "task.type"
        condition.operator = "unknown_op"
        condition.value = "test"

        context = {"task": {"type": "test"}}
        assert engine.evaluate_condition(condition, context) is False


class TestGetNestedValue:
    """Tests for _get_nested_value helper method."""

    @pytest.fixture
    def engine(self):
        return ConsultationEngine()

    def test_single_level(self, engine):
        """Test single level field access."""
        data = {"name": "test"}
        assert engine._get_nested_value(data, "name") == "test"

    def test_two_level(self, engine):
        """Test two level field access."""
        data = {"task": {"type": "feature"}}
        assert engine._get_nested_value(data, "task.type") == "feature"

    def test_three_level(self, engine):
        """Test three level field access."""
        data = {"task": {"metadata": {"priority": "high"}}}
        assert engine._get_nested_value(data, "task.metadata.priority") == "high"

    def test_missing_intermediate_key(self, engine):
        """Test missing intermediate key returns None."""
        data = {"task": {"type": "feature"}}
        assert engine._get_nested_value(data, "task.metadata.priority") is None

    def test_non_dict_intermediate(self, engine):
        """Test non-dict intermediate value returns None."""
        data = {"task": "string_value"}
        assert engine._get_nested_value(data, "task.type") is None


class TestQueryObservabilityTraces:
    """Tests for query_observability_traces method."""

    def test_no_client_returns_empty(self):
        """Test that missing client returns empty list."""
        engine = ConsultationEngine()
        result = engine.query_observability_traces("task-001")
        assert result == []

    def test_with_mock_client(self):
        """Test with mocked observability client."""
        mock_client = MagicMock()
        mock_client.query_traces.return_value = [
            {"trace_id": "trace-001", "agent_name": "security-agent"}
        ]

        engine = ConsultationEngine(observability_client=mock_client)
        result = engine.query_observability_traces("task-001", "security-agent")

        mock_client.query_traces.assert_called_once_with(
            task_id="task-001", action="consultation", agent_name="security-agent"
        )
        assert len(result) == 1

    def test_without_agent_filter(self):
        """Test querying without agent name filter."""
        mock_client = MagicMock()
        mock_client.query_traces.return_value = []

        engine = ConsultationEngine(observability_client=mock_client)
        engine.query_observability_traces("task-001")

        mock_client.query_traces.assert_called_once_with(task_id="task-001", action="consultation")


class TestValidateTaskCompletion:
    """Tests for validate_task_completion method."""

    @pytest.fixture
    def engine(self):
        requirements = [
            ConsultationRequirement(
                agent_name="security-agent", phase=ConsultationPhase.PRE_COMPLETION, mandatory=True
            ),
            ConsultationRequirement(
                agent_name="testing-agent", phase=ConsultationPhase.PRE_COMPLETION, mandatory=True
            ),
            ConsultationRequirement(
                agent_name="optional-agent", phase=ConsultationPhase.PRE_COMPLETION, mandatory=False
            ),
            ConsultationRequirement(
                agent_name="architect-agent",
                phase=ConsultationPhase.DESIGN_REVIEW,
                mandatory=True,
                condition=ConsultationCondition(
                    field="task.impacts_infrastructure", operator="equals", value=True
                ),
            ),
        ]
        return ConsultationEngine(requirements=requirements)

    def test_all_mandatory_completed(self, engine):
        """Test validation passes when all mandatory consultations done."""
        outcomes = [
            ConsultationOutcome(
                requirement_id="req-1", agent_name="security-agent", status="approved"
            ),
            ConsultationOutcome(
                requirement_id="req-2", agent_name="testing-agent", status="approved"
            ),
        ]

        result = engine.validate_task_completion(
            ConsultationPhase.PRE_COMPLETION, outcomes, {"task": {}}
        )

        assert result.is_valid is True
        assert len(result.missing_consultations) == 0
        assert "successfully" in result.message

    def test_missing_mandatory(self, engine):
        """Test validation fails when mandatory consultation missing."""
        outcomes = [
            ConsultationOutcome(
                requirement_id="req-1", agent_name="security-agent", status="approved"
            )
        ]

        result = engine.validate_task_completion(
            ConsultationPhase.PRE_COMPLETION, outcomes, {"task": {}}
        )

        assert result.is_valid is False
        assert len(result.missing_consultations) == 1
        assert result.missing_consultations[0].agent_name == "testing-agent"
        assert "Missing" in result.message

    def test_rejected_consultation(self, engine):
        """Test validation fails when consultation is rejected."""
        outcomes = [
            ConsultationOutcome(
                requirement_id="req-1",
                agent_name="security-agent",
                status="rejected",
                comments="Security issues found",
            ),
            ConsultationOutcome(
                requirement_id="req-2", agent_name="testing-agent", status="approved"
            ),
        ]

        result = engine.validate_task_completion(
            ConsultationPhase.PRE_COMPLETION, outcomes, {"task": {}}
        )

        assert result.is_valid is False
        assert len(result.rejected_consultations) == 1
        assert result.rejected_consultations[0].agent_name == "security-agent"
        assert "Rejected" in result.message

    def test_pending_consultation(self, engine):
        """Test validation fails when consultation is pending."""
        outcomes = [
            ConsultationOutcome(
                requirement_id="req-1", agent_name="security-agent", status="pending"
            ),
            ConsultationOutcome(
                requirement_id="req-2", agent_name="testing-agent", status="approved"
            ),
        ]

        result = engine.validate_task_completion(
            ConsultationPhase.PRE_COMPLETION, outcomes, {"task": {}}
        )

        assert result.is_valid is False
        assert len(result.missing_consultations) == 1

    def test_conditional_requirement_applies(self, engine):
        """Test conditional requirement applies when condition met."""
        outcomes = []

        result = engine.validate_task_completion(
            ConsultationPhase.DESIGN_REVIEW, outcomes, {"task": {"impacts_infrastructure": True}}
        )

        assert result.is_valid is False
        assert len(result.missing_consultations) == 1
        assert result.missing_consultations[0].agent_name == "architect-agent"

    def test_conditional_requirement_does_not_apply(self, engine):
        """Test conditional requirement skipped when condition not met."""
        outcomes = []

        result = engine.validate_task_completion(
            ConsultationPhase.DESIGN_REVIEW, outcomes, {"task": {"impacts_infrastructure": False}}
        )

        assert result.is_valid is True
        assert len(result.missing_consultations) == 0

    def test_optional_not_required(self, engine):
        """Test that optional consultations don't block completion."""
        outcomes = [
            ConsultationOutcome(
                requirement_id="req-1", agent_name="security-agent", status="approved"
            ),
            ConsultationOutcome(
                requirement_id="req-2", agent_name="testing-agent", status="approved"
            ),
            # Note: optional-agent outcome is missing
        ]

        result = engine.validate_task_completion(
            ConsultationPhase.PRE_COMPLETION, outcomes, {"task": {}}
        )

        assert result.is_valid is True


class TestValidationResult:
    """Tests for ValidationResult model."""

    def test_validation_result_defaults(self):
        """Test ValidationResult default values."""
        result = ValidationResult(is_valid=True)
        assert result.missing_consultations == []
        assert result.rejected_consultations == []
        assert result.message == ""

    def test_validation_result_with_all_fields(self):
        """Test ValidationResult with all fields populated."""
        missing = ConsultationRequirement(
            agent_name="security-agent", phase=ConsultationPhase.PRE_COMPLETION, mandatory=True
        )
        rejected = ConsultationOutcome(
            requirement_id="req-1", agent_name="testing-agent", status="rejected"
        )

        result = ValidationResult(
            is_valid=False,
            missing_consultations=[missing],
            rejected_consultations=[rejected],
            message="Validation failed",
        )

        assert result.is_valid is False
        assert len(result.missing_consultations) == 1
        assert len(result.rejected_consultations) == 1
        assert result.message == "Validation failed"
