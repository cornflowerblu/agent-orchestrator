"""Integration tests for consultation enforcement.

Tests for User Story 4: Declare Consultation Requirements
Task T051: Integration test for consultation enforcement
"""

from unittest.mock import patch

import pytest


@pytest.mark.integration
class TestConsultationEnforcement:
    """Integration tests for ConsultationEngine enforcement logic.

    Note: These tests use mocks for AWS services (Observability).
    Full integration requires deployed AgentCore infrastructure.
    """

    @pytest.fixture
    def sample_requirements(self):
        """Create sample consultation requirements for testing."""
        from src.consultation.rules import (
            ConsultationCondition,
            ConsultationPhase,
            ConsultationRequirement,
        )

        return [
            ConsultationRequirement(
                agent_name="security-agent",
                phase=ConsultationPhase.PRE_COMPLETION,
                mandatory=True,
                description="Security review before code completion",
            ),
            ConsultationRequirement(
                agent_name="testing-agent",
                phase=ConsultationPhase.PRE_COMPLETION,
                mandatory=True,
                description="Test coverage verification",
            ),
            ConsultationRequirement(
                agent_name="architect-agent",
                phase=ConsultationPhase.DESIGN_REVIEW,
                mandatory=True,
                condition=ConsultationCondition(
                    field="task.impacts_infrastructure", operator="equals", value=True
                ),
                description="Architecture review when infrastructure impacted",
            ),
        ]

    @pytest.fixture
    def consultation_engine(self, sample_requirements):
        """Create a ConsultationEngine with sample requirements."""
        from src.consultation.enforcement import ConsultationEngine

        return ConsultationEngine(requirements=sample_requirements)

    def test_get_requirements_by_phase(self, consultation_engine):
        """Test getting requirements filtered by phase."""
        from src.consultation.rules import ConsultationPhase

        pre_completion = consultation_engine.get_requirements(
            phase=ConsultationPhase.PRE_COMPLETION
        )
        assert len(pre_completion) == 2

        design_review = consultation_engine.get_requirements(phase=ConsultationPhase.DESIGN_REVIEW)
        assert len(design_review) == 1

    def test_get_requirements_mandatory_only(self, consultation_engine):
        """Test getting only mandatory requirements."""
        from src.consultation.rules import ConsultationPhase

        mandatory = consultation_engine.get_requirements(
            phase=ConsultationPhase.PRE_COMPLETION, mandatory_only=True
        )
        assert all(r.mandatory for r in mandatory)

    def test_evaluate_condition_equals_true(self, consultation_engine):
        """Test condition evaluation when equals condition is met."""
        from src.consultation.rules import ConsultationCondition

        condition = ConsultationCondition(
            field="task.type", operator="equals", value="infrastructure"
        )
        task_context = {"task": {"type": "infrastructure"}}

        result = consultation_engine.evaluate_condition(condition, task_context)
        assert result is True

    def test_evaluate_condition_equals_false(self, consultation_engine):
        """Test condition evaluation when equals condition is not met."""
        from src.consultation.rules import ConsultationCondition

        condition = ConsultationCondition(
            field="task.type", operator="equals", value="infrastructure"
        )
        task_context = {"task": {"type": "feature"}}

        result = consultation_engine.evaluate_condition(condition, task_context)
        assert result is False

    def test_evaluate_condition_contains(self, consultation_engine):
        """Test condition evaluation with contains operator."""
        from src.consultation.rules import ConsultationCondition

        condition = ConsultationCondition(field="task.tags", operator="contains", value="security")
        task_context = {"task": {"tags": ["security", "compliance", "audit"]}}

        result = consultation_engine.evaluate_condition(condition, task_context)
        assert result is True

    def test_evaluate_condition_in_operator(self, consultation_engine):
        """Test condition evaluation with 'in' operator."""
        from src.consultation.rules import ConsultationCondition

        condition = ConsultationCondition(
            field="task.priority", operator="in", value=["high", "critical"]
        )
        task_context = {"task": {"priority": "high"}}

        result = consultation_engine.evaluate_condition(condition, task_context)
        assert result is True

    def test_evaluate_condition_nested_field(self, consultation_engine):
        """Test condition evaluation with nested field path."""
        from src.consultation.rules import ConsultationCondition

        condition = ConsultationCondition(
            field="task.metadata.requires_review", operator="equals", value=True
        )
        task_context = {"task": {"metadata": {"requires_review": True}}}

        result = consultation_engine.evaluate_condition(condition, task_context)
        assert result is True

    @pytest.mark.skip(reason="Requires AgentCore Observability deployment")
    def test_query_observability_traces_real(self, consultation_engine):
        """Test querying real Observability traces for A2A consultations."""
        # This test requires deployed AgentCore infrastructure

    def test_query_observability_traces_mocked(self, consultation_engine):
        """Test querying Observability traces with mocked response."""
        with patch.object(consultation_engine, "_observability_client") as mock_client:
            mock_client.query_traces.return_value = [
                {
                    "trace_id": "trace-123",
                    "agent_name": "security-agent",
                    "action": "consultation",
                    "status": "completed",
                }
            ]

            traces = consultation_engine.query_observability_traces(
                task_id="task-001", agent_name="security-agent"
            )

            assert len(traces) == 1
            assert traces[0]["trace_id"] == "trace-123"

    def test_validate_task_completion_all_consultations_done(self, consultation_engine):
        """Test validation passes when all mandatory consultations are complete."""
        from src.consultation.rules import ConsultationOutcome, ConsultationPhase

        # Mock outcomes for all mandatory consultations
        outcomes = [
            ConsultationOutcome(
                requirement_id="req-1",
                agent_name="security-agent",
                status="approved",
                trace_id="trace-001",
            ),
            ConsultationOutcome(
                requirement_id="req-2",
                agent_name="testing-agent",
                status="approved",
                trace_id="trace-002",
            ),
        ]

        task_context = {"task": {"impacts_infrastructure": False}}

        result = consultation_engine.validate_task_completion(
            phase=ConsultationPhase.PRE_COMPLETION, outcomes=outcomes, task_context=task_context
        )

        assert result.is_valid is True
        assert len(result.missing_consultations) == 0

    def test_validate_task_completion_missing_consultation(self, consultation_engine):
        """Test validation fails when mandatory consultation is missing."""
        from src.consultation.rules import ConsultationOutcome, ConsultationPhase

        # Only one of two mandatory consultations completed
        outcomes = [
            ConsultationOutcome(
                requirement_id="req-1",
                agent_name="security-agent",
                status="approved",
                trace_id="trace-001",
            )
        ]

        task_context = {"task": {"impacts_infrastructure": False}}

        result = consultation_engine.validate_task_completion(
            phase=ConsultationPhase.PRE_COMPLETION, outcomes=outcomes, task_context=task_context
        )

        assert result.is_valid is False
        assert len(result.missing_consultations) == 1
        assert result.missing_consultations[0].agent_name == "testing-agent"

    def test_validate_task_completion_rejected_consultation(self, consultation_engine):
        """Test validation fails when mandatory consultation is rejected."""
        from src.consultation.rules import ConsultationOutcome, ConsultationPhase

        outcomes = [
            ConsultationOutcome(
                requirement_id="req-1",
                agent_name="security-agent",
                status="rejected",
                comments="Security vulnerabilities found",
                trace_id="trace-001",
            ),
            ConsultationOutcome(
                requirement_id="req-2",
                agent_name="testing-agent",
                status="approved",
                trace_id="trace-002",
            ),
        ]

        task_context = {"task": {"impacts_infrastructure": False}}

        result = consultation_engine.validate_task_completion(
            phase=ConsultationPhase.PRE_COMPLETION, outcomes=outcomes, task_context=task_context
        )

        assert result.is_valid is False
        assert len(result.rejected_consultations) == 1
        assert result.rejected_consultations[0].agent_name == "security-agent"

    def test_validate_task_completion_conditional_requirement_met(self, consultation_engine):
        """Test conditional consultation is required when condition is met."""
        from src.consultation.rules import ConsultationPhase

        # Context triggers the conditional requirement
        task_context = {"task": {"impacts_infrastructure": True}}

        # Only pre-completion outcomes, missing design-review
        outcomes = []

        result = consultation_engine.validate_task_completion(
            phase=ConsultationPhase.DESIGN_REVIEW, outcomes=outcomes, task_context=task_context
        )

        assert result.is_valid is False
        assert len(result.missing_consultations) == 1
        assert result.missing_consultations[0].agent_name == "architect-agent"

    def test_validate_task_completion_conditional_requirement_not_met(self, consultation_engine):
        """Test conditional consultation is not required when condition is not met."""
        from src.consultation.rules import ConsultationPhase

        # Context does NOT trigger the conditional requirement
        task_context = {"task": {"impacts_infrastructure": False}}

        outcomes = []

        result = consultation_engine.validate_task_completion(
            phase=ConsultationPhase.DESIGN_REVIEW, outcomes=outcomes, task_context=task_context
        )

        # Should pass because condition is not met
        assert result.is_valid is True


class TestConsultationValidationResult:
    """Tests for the validation result model."""

    def test_validation_result_success(self):
        """Test creating a successful validation result."""
        from src.consultation.enforcement import ValidationResult

        result = ValidationResult(
            is_valid=True,
            missing_consultations=[],
            rejected_consultations=[],
            message="All mandatory consultations completed successfully",
        )

        assert result.is_valid is True
        assert result.message == "All mandatory consultations completed successfully"

    def test_validation_result_failure_missing(self):
        """Test creating a failure result with missing consultations."""
        from src.consultation.enforcement import ValidationResult
        from src.consultation.rules import ConsultationPhase, ConsultationRequirement

        missing = ConsultationRequirement(
            agent_name="security-agent", phase=ConsultationPhase.PRE_COMPLETION, mandatory=True
        )

        result = ValidationResult(
            is_valid=False,
            missing_consultations=[missing],
            rejected_consultations=[],
            message="Missing mandatory consultation with security-agent",
        )

        assert result.is_valid is False
        assert len(result.missing_consultations) == 1
