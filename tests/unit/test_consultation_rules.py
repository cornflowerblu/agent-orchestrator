"""Unit tests for consultation rules models and logic.

Tests for User Story 4: Declare Consultation Requirements
Task T050: Unit test for consultation rules
"""

import pytest
from pydantic import ValidationError


class TestConsultationPhase:
    """Tests for ConsultationPhase enum."""

    def test_consultation_phase_values(self):
        """Test that all required consultation phases exist."""
        from src.consultation.rules import ConsultationPhase

        # Per spec: pre-execution, design-review, pre-completion, on-error
        assert ConsultationPhase.PRE_EXECUTION.value == "pre-execution"
        assert ConsultationPhase.DESIGN_REVIEW.value == "design-review"
        assert ConsultationPhase.PRE_COMPLETION.value == "pre-completion"
        assert ConsultationPhase.ON_ERROR.value == "on-error"

    def test_consultation_phase_from_string(self):
        """Test creating ConsultationPhase from string value."""
        from src.consultation.rules import ConsultationPhase

        phase = ConsultationPhase("pre-execution")
        assert phase == ConsultationPhase.PRE_EXECUTION

    def test_consultation_phase_invalid_value(self):
        """Test that invalid phase values raise error."""
        from src.consultation.rules import ConsultationPhase

        with pytest.raises(ValueError, match="invalid-phase"):
            ConsultationPhase("invalid-phase")


class TestConsultationCondition:
    """Tests for ConsultationCondition model."""

    def test_condition_creation_with_required_fields(self):
        """Test creating a consultation condition with all required fields."""
        from src.consultation.rules import ConsultationCondition

        condition = ConsultationCondition(
            field="task.type",
            operator="equals",
            value="infrastructure"
        )
        assert condition.field == "task.type"
        assert condition.operator == "equals"
        assert condition.value == "infrastructure"

    def test_condition_operators(self):
        """Test supported condition operators."""
        from src.consultation.rules import ConsultationCondition

        # Test various operators
        for op in ["equals", "not_equals", "contains", "not_contains", "in", "not_in"]:
            condition = ConsultationCondition(
                field="test.field",
                operator=op,
                value="test_value"
            )
            assert condition.operator == op

    def test_condition_with_list_value(self):
        """Test condition with list value for 'in' operator."""
        from src.consultation.rules import ConsultationCondition

        condition = ConsultationCondition(
            field="task.tags",
            operator="in",
            value=["security", "compliance"]
        )
        assert condition.value == ["security", "compliance"]

    def test_condition_invalid_operator(self):
        """Test that invalid operator raises validation error."""
        from src.consultation.rules import ConsultationCondition

        with pytest.raises(ValidationError):
            ConsultationCondition(
                field="test.field",
                operator="invalid_op",
                value="test"
            )


class TestConsultationRequirement:
    """Tests for ConsultationRequirement model."""

    def test_requirement_creation_mandatory(self):
        """Test creating a mandatory consultation requirement."""
        from src.consultation.rules import ConsultationPhase, ConsultationRequirement

        requirement = ConsultationRequirement(
            agent_name="security-agent",
            phase=ConsultationPhase.PRE_COMPLETION,
            mandatory=True,
            description="Security review before code completion"
        )
        assert requirement.agent_name == "security-agent"
        assert requirement.phase == ConsultationPhase.PRE_COMPLETION
        assert requirement.mandatory is True
        assert requirement.description == "Security review before code completion"

    def test_requirement_creation_with_condition(self):
        """Test creating a consultation requirement with conditional logic."""
        from src.consultation.rules import (
            ConsultationCondition,
            ConsultationPhase,
            ConsultationRequirement,
        )

        condition = ConsultationCondition(
            field="task.impacts_infrastructure",
            operator="equals",
            value=True
        )
        requirement = ConsultationRequirement(
            agent_name="architect-agent",
            phase=ConsultationPhase.DESIGN_REVIEW,
            mandatory=True,
            condition=condition,
            description="Architect review when infrastructure is impacted"
        )
        assert requirement.condition is not None
        assert requirement.condition.field == "task.impacts_infrastructure"

    def test_requirement_optional_condition(self):
        """Test that condition field is optional."""
        from src.consultation.rules import ConsultationPhase, ConsultationRequirement

        requirement = ConsultationRequirement(
            agent_name="review-agent",
            phase=ConsultationPhase.PRE_COMPLETION,
            mandatory=True
        )
        assert requirement.condition is None

    def test_requirement_default_mandatory_false(self):
        """Test that mandatory defaults to False if not specified."""
        from src.consultation.rules import ConsultationPhase, ConsultationRequirement

        requirement = ConsultationRequirement(
            agent_name="testing-agent",
            phase=ConsultationPhase.PRE_COMPLETION
        )
        assert requirement.mandatory is False

    def test_requirement_agent_name_validation(self):
        """Test that agent name follows naming convention."""
        from src.consultation.rules import ConsultationPhase, ConsultationRequirement

        # Valid names
        valid_names = ["security-agent", "code-review", "my_agent", "Agent1"]
        for name in valid_names:
            req = ConsultationRequirement(
                agent_name=name,
                phase=ConsultationPhase.PRE_COMPLETION
            )
            assert req.agent_name == name


class TestConsultationOutcome:
    """Tests for ConsultationOutcome model."""

    def test_outcome_creation_approved(self):
        """Test creating an approved consultation outcome."""
        from src.consultation.rules import ConsultationOutcome

        outcome = ConsultationOutcome(
            requirement_id="req-001",
            agent_name="security-agent",
            status="approved",
            comments="Security review passed, no issues found",
            trace_id="trace-abc123"
        )
        assert outcome.requirement_id == "req-001"
        assert outcome.agent_name == "security-agent"
        assert outcome.status == "approved"
        assert outcome.comments == "Security review passed, no issues found"
        assert outcome.trace_id == "trace-abc123"

    def test_outcome_creation_rejected(self):
        """Test creating a rejected consultation outcome."""
        from src.consultation.rules import ConsultationOutcome

        outcome = ConsultationOutcome(
            requirement_id="req-002",
            agent_name="architect-agent",
            status="rejected",
            comments="Design violates scalability requirements"
        )
        assert outcome.status == "rejected"

    def test_outcome_creation_pending(self):
        """Test creating a pending consultation outcome."""
        from src.consultation.rules import ConsultationOutcome

        outcome = ConsultationOutcome(
            requirement_id="req-003",
            agent_name="testing-agent",
            status="pending"
        )
        assert outcome.status == "pending"

    def test_outcome_status_values(self):
        """Test that only valid status values are accepted."""
        from src.consultation.rules import ConsultationOutcome

        valid_statuses = ["pending", "approved", "rejected", "skipped"]
        for status in valid_statuses:
            outcome = ConsultationOutcome(
                requirement_id="req-test",
                agent_name="test-agent",
                status=status
            )
            assert outcome.status == status

    def test_outcome_invalid_status(self):
        """Test that invalid status raises validation error."""
        from src.consultation.rules import ConsultationOutcome

        with pytest.raises(ValidationError):
            ConsultationOutcome(
                requirement_id="req-test",
                agent_name="test-agent",
                status="invalid-status"
            )

    def test_outcome_optional_fields(self):
        """Test that comments and trace_id are optional."""
        from src.consultation.rules import ConsultationOutcome

        outcome = ConsultationOutcome(
            requirement_id="req-minimal",
            agent_name="test-agent",
            status="pending"
        )
        assert outcome.comments is None
        assert outcome.trace_id is None

    def test_outcome_timestamp_auto_generated(self):
        """Test that timestamp is auto-generated if not provided."""
        from datetime import datetime

        from src.consultation.rules import ConsultationOutcome

        outcome = ConsultationOutcome(
            requirement_id="req-time",
            agent_name="test-agent",
            status="approved"
        )
        assert outcome.timestamp is not None
        assert isinstance(outcome.timestamp, datetime)


class TestConsultationRequirementList:
    """Tests for working with lists of consultation requirements."""

    def test_multiple_requirements_for_agent(self):
        """Test an agent can have multiple consultation requirements."""
        from src.consultation.rules import ConsultationPhase, ConsultationRequirement

        requirements = [
            ConsultationRequirement(
                agent_name="security-agent",
                phase=ConsultationPhase.PRE_COMPLETION,
                mandatory=True,
                description="Security review"
            ),
            ConsultationRequirement(
                agent_name="testing-agent",
                phase=ConsultationPhase.PRE_COMPLETION,
                mandatory=True,
                description="Test coverage verification"
            ),
            ConsultationRequirement(
                agent_name="architect-agent",
                phase=ConsultationPhase.DESIGN_REVIEW,
                mandatory=False,
                description="Optional architecture review"
            )
        ]
        assert len(requirements) == 3
        mandatory = [r for r in requirements if r.mandatory]
        assert len(mandatory) == 2

    def test_filter_requirements_by_phase(self):
        """Test filtering requirements by consultation phase."""
        from src.consultation.rules import ConsultationPhase, ConsultationRequirement

        requirements = [
            ConsultationRequirement(
                agent_name="security-agent",
                phase=ConsultationPhase.PRE_COMPLETION
            ),
            ConsultationRequirement(
                agent_name="architect-agent",
                phase=ConsultationPhase.DESIGN_REVIEW
            ),
            ConsultationRequirement(
                agent_name="review-agent",
                phase=ConsultationPhase.PRE_COMPLETION
            )
        ]

        pre_completion = [r for r in requirements if r.phase == ConsultationPhase.PRE_COMPLETION]
        assert len(pre_completion) == 2
