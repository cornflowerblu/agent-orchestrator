"""Local integration tests for consultation enforcement engine.

Fast comments loop for development - no AWS deployment needed.
"""

import pytest

from src.consultation.enforcement import ConsultationEngine, ValidationResult
from src.consultation.rules import (
    ConsultationCondition,
    ConsultationOutcome,
    ConsultationPhase,
    ConsultationRequirement,
)

# Mark all tests in this module as local integration tests
pytestmark = pytest.mark.integration_local


@pytest.fixture
def sample_requirements():
    """Sample consultation requirements for testing."""
    return [
        ConsultationRequirement(
            agent_name="security-reviewer",
            phase=ConsultationPhase.PRE_EXECUTION,
            mandatory=True,
        ),
        ConsultationRequirement(
            agent_name="code-reviewer",
            phase=ConsultationPhase.PRE_COMPLETION,
            mandatory=True,
        ),
        ConsultationRequirement(
            agent_name="optional-advisor",
            phase=ConsultationPhase.PRE_COMPLETION,
            mandatory=False,
        ),
        ConsultationRequirement(
            agent_name="conditional-validator",
            phase=ConsultationPhase.PRE_COMPLETION,
            mandatory=True,
            condition=ConsultationCondition(
                field="result.status", operator="equals", value="success"
            ),
        ),
    ]


@pytest.fixture
def engine(sample_requirements):
    """Create consultation engine with sample requirements."""
    return ConsultationEngine(requirements=sample_requirements)


class TestConsultationEngineLocal:
    """Local integration tests for consultation engine."""

    def test_get_requirements_by_phase(self, engine):
        """Test getting requirements for a specific phase."""
        # Pre-execution phase
        pre_exec = engine.get_requirements(ConsultationPhase.PRE_EXECUTION)
        assert len(pre_exec) == 1
        assert pre_exec[0].agent_name == "security-reviewer"

        # Pre-completion phase
        pre_comp = engine.get_requirements(ConsultationPhase.PRE_COMPLETION)
        assert len(pre_comp) == 3

    def test_get_requirements_mandatory_only(self, engine):
        """Test getting only mandatory requirements."""
        # Pre-completion phase, mandatory only
        mandatory = engine.get_requirements(
            ConsultationPhase.PRE_COMPLETION, mandatory_only=True
        )
        assert len(mandatory) == 2
        agent_names = [r.agent_name for r in mandatory]
        assert "code-reviewer" in agent_names
        assert "conditional-validator" in agent_names
        assert "optional-advisor" not in agent_names

    def test_evaluate_condition_equals(self, engine):
        """Test evaluating equals condition."""
        condition = ConsultationCondition(
            field="result.status", operator="equals", value="success"
        )

        # Condition met
        context = {"result": {"status": "success"}}
        assert engine.evaluate_condition(condition, context) is True

        # Condition not met
        context = {"result": {"status": "failure"}}
        assert engine.evaluate_condition(condition, context) is False

    def test_evaluate_condition_not_equals(self, engine):
        """Test evaluating not_equals condition."""
        condition = ConsultationCondition(
            field="result.code", operator="not_equals", value=0
        )

        # Condition met (not equal)
        context = {"result": {"code": 1}}
        assert engine.evaluate_condition(condition, context) is True

        # Condition not met (equal)
        context = {"result": {"code": 0}}
        assert engine.evaluate_condition(condition, context) is False

    def test_evaluate_condition_contains(self, engine):
        """Test evaluating contains condition."""
        condition = ConsultationCondition(
            field="tags", operator="contains", value="security"
        )

        # List contains value
        context = {"tags": ["security", "compliance", "audit"]}
        assert engine.evaluate_condition(condition, context) is True

        # List doesn't contain value
        context = {"tags": ["performance", "optimization"]}
        assert engine.evaluate_condition(condition, context) is False

        # String contains value
        condition_str = ConsultationCondition(
            field="message", operator="contains", value="error"
        )
        context = {"message": "An error occurred"}
        assert engine.evaluate_condition(condition_str, context) is True

    def test_evaluate_condition_not_contains(self, engine):
        """Test evaluating not_contains condition."""
        condition = ConsultationCondition(
            field="tags", operator="not_contains", value="deprecated"
        )

        # List doesn't contain value (condition met)
        context = {"tags": ["new", "experimental"]}
        assert engine.evaluate_condition(condition, context) is True

        # List contains value (condition not met)
        context = {"tags": ["old", "deprecated"]}
        assert engine.evaluate_condition(condition, context) is False

    def test_evaluate_condition_in(self, engine):
        """Test evaluating in condition."""
        condition = ConsultationCondition(
            field="status", operator="in", value=["approved", "pending"]
        )

        # Value in list
        context = {"status": "approved"}
        assert engine.evaluate_condition(condition, context) is True

        # Value not in list
        context = {"status": "rejected"}
        assert engine.evaluate_condition(condition, context) is False

    def test_evaluate_condition_not_in(self, engine):
        """Test evaluating not_in condition."""
        condition = ConsultationCondition(
            field="status", operator="not_in", value=["rejected", "cancelled"]
        )

        # Value not in list (condition met)
        context = {"status": "approved"}
        assert engine.evaluate_condition(condition, context) is True

        # Value in list (condition not met)
        context = {"status": "rejected"}
        assert engine.evaluate_condition(condition, context) is False

    def test_evaluate_condition_nested_field(self, engine):
        """Test evaluating condition with nested field path."""
        condition = ConsultationCondition(
            field="task.metadata.priority", operator="equals", value="high"
        )

        # Nested field exists
        context = {"task": {"metadata": {"priority": "high"}}}
        assert engine.evaluate_condition(condition, context) is True

        # Nested field doesn't exist
        context = {"task": {"metadata": {}}}
        assert engine.evaluate_condition(condition, context) is False

    def test_query_observability_traces_no_client(self, engine):
        """Test querying observability traces without client."""
        # Should return empty list when no client configured
        traces = engine.query_observability_traces("task-123")
        assert traces == []

    def test_validate_task_completion_all_satisfied(self, engine):
        """Test validation when all mandatory consultations are satisfied."""
        # Provide outcomes for all mandatory consultations
        outcomes = [
            ConsultationOutcome(
                requirement_id="req-security",
                agent_name="security-reviewer",
                status="approved",
                timestamp="2024-01-01T00:00:00Z",
            ),
            ConsultationOutcome(
                requirement_id="req-code",
                agent_name="code-reviewer",
                status="approved",
                timestamp="2024-01-01T00:00:00Z",
            ),
        ]

        # Task context that doesn't trigger conditional requirement
        context = {"result": {"status": "failure"}}

        result = engine.validate_task_completion(
            ConsultationPhase.PRE_COMPLETION, outcomes, context
        )

        assert result.is_valid is True
        assert len(result.missing_consultations) == 0
        assert len(result.rejected_consultations) == 0
        assert "successfully" in result.message.lower()

    def test_validate_task_completion_missing_mandatory(self, engine):
        """Test validation when mandatory consultation is missing."""
        # Missing code-reviewer consultation
        outcomes = [
            ConsultationOutcome(
                requirement_id="req-security",
                agent_name="security-reviewer",
                status="approved",
                timestamp="2024-01-01T00:00:00Z",
            ),
        ]

        context = {"result": {"status": "failure"}}

        result = engine.validate_task_completion(
            ConsultationPhase.PRE_COMPLETION, outcomes, context
        )

        assert result.is_valid is False
        assert len(result.missing_consultations) == 1
        assert result.missing_consultations[0].agent_name == "code-reviewer"
        assert "missing" in result.message.lower()

    def test_validate_task_completion_rejected(self, engine):
        """Test validation when consultation is rejected."""
        outcomes = [
            ConsultationOutcome(
                requirement_id="req-security",
                agent_name="security-reviewer",
                status="approved",
                timestamp="2024-01-01T00:00:00Z",
            ),
            ConsultationOutcome(
                requirement_id="req-code",
                agent_name="code-reviewer",
                status="rejected",
                timestamp="2024-01-01T00:00:00Z",
                comments="Code quality issues found",
            ),
        ]

        context = {"result": {"status": "failure"}}

        result = engine.validate_task_completion(
            ConsultationPhase.PRE_COMPLETION, outcomes, context
        )

        assert result.is_valid is False
        assert len(result.rejected_consultations) == 1
        assert result.rejected_consultations[0].agent_name == "code-reviewer"
        assert "rejected" in result.message.lower()

    def test_validate_task_completion_pending(self, engine):
        """Test validation when consultation is still pending."""
        outcomes = [
            ConsultationOutcome(
                requirement_id="req-security",
                agent_name="security-reviewer",
                status="approved",
                timestamp="2024-01-01T00:00:00Z",
            ),
            ConsultationOutcome(
                requirement_id="req-code",
                agent_name="code-reviewer",
                status="pending",
                timestamp="2024-01-01T00:00:00Z",
            ),
        ]

        context = {"result": {"status": "failure"}}

        result = engine.validate_task_completion(
            ConsultationPhase.PRE_COMPLETION, outcomes, context
        )

        assert result.is_valid is False
        assert len(result.missing_consultations) == 1
        assert result.missing_consultations[0].agent_name == "code-reviewer"

    def test_validate_task_completion_conditional_triggered(self, engine):
        """Test validation when conditional requirement is triggered."""
        outcomes = [
            ConsultationOutcome(
                requirement_id="req-security",
                agent_name="security-reviewer",
                status="approved",
                timestamp="2024-01-01T00:00:00Z",
            ),
            ConsultationOutcome(
                requirement_id="req-code",
                agent_name="code-reviewer",
                status="approved",
                timestamp="2024-01-01T00:00:00Z",
            ),
            # Missing conditional-validator
        ]

        # Condition is met (result.status == "success")
        context = {"result": {"status": "success"}}

        result = engine.validate_task_completion(
            ConsultationPhase.PRE_COMPLETION, outcomes, context
        )

        assert result.is_valid is False
        assert len(result.missing_consultations) == 1
        assert result.missing_consultations[0].agent_name == "conditional-validator"

    def test_validate_task_completion_conditional_not_triggered(self, engine):
        """Test validation when conditional requirement is not triggered."""
        outcomes = [
            ConsultationOutcome(
                requirement_id="req-security",
                agent_name="security-reviewer",
                status="approved",
                timestamp="2024-01-01T00:00:00Z",
            ),
            ConsultationOutcome(
                requirement_id="req-code",
                agent_name="code-reviewer",
                status="approved",
                timestamp="2024-01-01T00:00:00Z",
            ),
            # Missing conditional-validator, but condition not met
        ]

        # Condition is not met (result.status != "success")
        context = {"result": {"status": "failure"}}

        result = engine.validate_task_completion(
            ConsultationPhase.PRE_COMPLETION, outcomes, context
        )

        # Should be valid because conditional requirement doesn't apply
        assert result.is_valid is True
        assert len(result.missing_consultations) == 0

    def test_validate_task_completion_optional_ignored(self, engine):
        """Test that optional consultations don't block validation."""
        outcomes = [
            ConsultationOutcome(
                requirement_id="req-security",
                agent_name="security-reviewer",
                status="approved",
                timestamp="2024-01-01T00:00:00Z",
            ),
            ConsultationOutcome(
                requirement_id="req-code",
                agent_name="code-reviewer",
                status="approved",
                timestamp="2024-01-01T00:00:00Z",
            ),
            # Missing optional-advisor
        ]

        context = {"result": {"status": "failure"}}

        result = engine.validate_task_completion(
            ConsultationPhase.PRE_COMPLETION, outcomes, context
        )

        # Should be valid - optional consultations don't block
        assert result.is_valid is True

    def test_validate_task_completion_multiple_issues(self, engine):
        """Test validation with both missing and rejected consultations."""
        # In PRE_EXECUTION phase
        outcomes = [
            ConsultationOutcome(
                requirement_id="req-security",
                agent_name="security-reviewer",
                status="rejected",
                timestamp="2024-01-01T00:00:00Z",
                comments="Security vulnerabilities found",
            ),
        ]

        context = {"result": {"status": "failure"}}

        # Use PRE_EXECUTION phase where security-reviewer is mandatory
        result = engine.validate_task_completion(
            ConsultationPhase.PRE_EXECUTION, outcomes, context
        )

        assert result.is_valid is False
        assert len(result.missing_consultations) == 0  # No missing in this phase
        assert len(result.rejected_consultations) == 1
        assert "rejected" in result.message.lower()

    def test_empty_requirements(self):
        """Test engine with no requirements."""
        engine = ConsultationEngine(requirements=[])

        # Should return valid for any phase with no outcomes
        result = engine.validate_task_completion(
            ConsultationPhase.PRE_EXECUTION, [], {}
        )

        assert result.is_valid is True
        assert len(result.missing_consultations) == 0
