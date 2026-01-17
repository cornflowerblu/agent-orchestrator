"""Consultation enforcement engine for inter-agent consultation requirements.

This module implements the consultation enforcement logic that ensures
agents consult with required peers before task completion, as specified
in the Agent Orchestrator Platform Constitution (Principle V).

Task T056: Implement ConsultationEngine class
Task T057: Implement get_requirements method
Task T058: Implement evaluate_condition method
Task T059: Implement query_observability_traces method
Task T060: Implement validate_task_completion method
"""

from typing import Any, cast

from pydantic import BaseModel, Field

from src.consultation.rules import (
    ConsultationCondition,
    ConsultationOutcome,
    ConsultationPhase,
    ConsultationRequirement,
)


class ValidationResult(BaseModel):
    """Result of validating task completion against consultation requirements.

    Used to communicate whether all mandatory consultations have been
    completed and any issues that block task completion.
    """

    is_valid: bool = Field(..., description="Whether all consultation requirements are satisfied")
    missing_consultations: list[ConsultationRequirement] = Field(
        default_factory=list, description="Mandatory consultations that haven't been completed"
    )
    rejected_consultations: list[ConsultationOutcome] = Field(
        default_factory=list, description="Consultations that were rejected by the consulted agent"
    )
    message: str = Field(default="", description="Human-readable summary of validation result")


class ConsultationEngine:
    """Engine for managing and enforcing consultation requirements.

    Provides methods for:
    - Getting applicable requirements for a phase
    - Evaluating conditional requirements
    - Querying Observability traces for consultation verification
    - Validating task completion against requirements

    Task T056: Implement ConsultationEngine class
    """

    def __init__(
        self,
        requirements: list[ConsultationRequirement] | None = None,
        observability_client: Any | None = None,
    ):
        """Initialize the consultation engine.

        Args:
            requirements: List of consultation requirements to enforce
            observability_client: Optional AgentCore Observability client for trace queries
        """
        self._requirements = requirements or []
        self._observability_client = observability_client

    def get_requirements(
        self, phase: ConsultationPhase, mandatory_only: bool = False
    ) -> list[ConsultationRequirement]:
        """Get consultation requirements for a specific phase.

        Task T057: Implement get_requirements method

        Args:
            phase: The consultation phase to filter by
            mandatory_only: If True, only return mandatory requirements

        Returns:
            List of ConsultationRequirement matching the criteria
        """
        filtered = [r for r in self._requirements if r.phase == phase]

        if mandatory_only:
            filtered = [r for r in filtered if r.mandatory]

        return filtered

    def evaluate_condition(
        self, condition: ConsultationCondition, task_context: dict[str, Any]
    ) -> bool:
        """Evaluate whether a consultation condition is met.

        Task T058: Implement evaluate_condition method

        Args:
            condition: The condition to evaluate
            task_context: The task context containing data to evaluate against

        Returns:
            True if the condition is met, False otherwise
        """
        # Get the field value from task context using dot notation
        field_value = self._get_nested_value(task_context, condition.field)

        # Apply the operator using a dispatch table
        operator = condition.operator
        expected_value = condition.value

        operators = {
            "equals": lambda f, e: f == e,
            "not_equals": lambda f, e: f != e,
            "contains": self._check_contains,
            # _check_contains returns False for invalid types, so negation returns True (correct)
            "not_contains": lambda f, e: not self._check_contains(f, e),
            "in": lambda f, e: f in e if isinstance(e, (list, tuple, set)) else False,
            "not_in": lambda f, e: f not in e if isinstance(e, (list, tuple, set)) else True,
        }

        handler = operators.get(operator)
        if handler is None:
            return False
        return cast(bool, handler(field_value, expected_value))

    def _check_contains(self, field_value: Any, expected_value: Any, default: bool = False) -> bool:
        """Check if field_value contains expected_value."""
        if isinstance(field_value, (list, tuple, set, str)):
            return expected_value in field_value
        return default

    def _get_nested_value(self, data: dict[str, Any], field_path: str) -> Any:
        """Get a nested value from a dictionary using dot notation.

        Args:
            data: The dictionary to search
            field_path: Dot-separated path (e.g., "task.metadata.type")

        Returns:
            The value at the path, or None if not found
        """
        parts = field_path.split(".")
        current = data

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None

        return current

    def query_observability_traces(
        self, task_id: str, agent_name: str | None = None
    ) -> list[dict[str, Any]]:
        """Query AgentCore Observability traces for A2A consultation verification.

        Task T059: Implement query_observability_traces method

        Args:
            task_id: The task ID to query traces for
            agent_name: Optional agent name to filter traces

        Returns:
            List of trace records matching the criteria
        """
        if self._observability_client is None:
            # Return empty list if no client configured
            return []

        # Query traces from Observability service
        query_params = {"task_id": task_id, "action": "consultation"}

        if agent_name:
            query_params["agent_name"] = agent_name

        return cast(list[dict[str, Any]], self._observability_client.query_traces(**query_params))

    def validate_task_completion(
        self,
        phase: ConsultationPhase,
        outcomes: list[ConsultationOutcome],
        task_context: dict[str, Any],
    ) -> ValidationResult:
        """Validate that all required consultations are complete before task completion.

        Task T060: Implement validate_task_completion method

        Per Constitution Principle V: Agents MUST consult other agents before
        finalizing decisions. This method blocks task completion when mandatory
        consultations are missing or rejected.

        Args:
            phase: The current consultation phase
            outcomes: List of consultation outcomes received
            task_context: Context for evaluating conditional requirements

        Returns:
            ValidationResult indicating whether completion is allowed
        """
        # Get all requirements for this phase
        requirements = self.get_requirements(phase)

        # Track issues
        missing_consultations: list[ConsultationRequirement] = []
        rejected_consultations: list[ConsultationOutcome] = []

        # Build a lookup of outcomes by agent name
        outcomes_by_agent = {o.agent_name: o for o in outcomes}

        for requirement in requirements:
            # Check if this requirement is applicable (evaluate condition if present)
            if requirement.condition is not None:
                condition_met = self.evaluate_condition(requirement.condition, task_context)
                if not condition_met:
                    # Condition not met, this requirement doesn't apply
                    continue

            # Requirement applies - check if we have an outcome
            if requirement.mandatory:
                outcome = outcomes_by_agent.get(requirement.agent_name)

                if outcome is None:
                    # Missing mandatory consultation
                    missing_consultations.append(requirement)
                elif outcome.status == "rejected":
                    # Consultation was rejected
                    rejected_consultations.append(outcome)
                elif outcome.status == "pending":
                    # Consultation not yet complete
                    missing_consultations.append(requirement)

        # Determine overall validity
        is_valid = len(missing_consultations) == 0 and len(rejected_consultations) == 0

        # Build message
        if is_valid:
            message = "All mandatory consultations completed successfully"
        else:
            parts = []
            if missing_consultations:
                agents = [r.agent_name for r in missing_consultations]
                parts.append(f"Missing consultations: {', '.join(agents)}")
            if rejected_consultations:
                agents = [o.agent_name for o in rejected_consultations]
                parts.append(f"Rejected consultations: {', '.join(agents)}")
            message = "; ".join(parts)

        return ValidationResult(
            is_valid=is_valid,
            missing_consultations=missing_consultations,
            rejected_consultations=rejected_consultations,
            message=message,
        )
