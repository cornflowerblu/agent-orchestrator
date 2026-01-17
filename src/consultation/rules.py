"""Consultation rules models for inter-agent consultation requirements.

This module provides Pydantic models for defining and managing consultation
requirements between agents as specified in the Agent Orchestrator Platform
Constitution (Principle V: Inter-Agent Consultation Protocol).

Task T052: ConsultationPhase enum
Task T053: ConsultationCondition model
Task T054: ConsultationRequirement model
Task T055: ConsultationOutcome model
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ConsultationPhase(str, Enum):
    """Phases during task execution when consultations can occur.

    Per custom-metadata.schema.json:
    - pre-execution: Before starting work
    - design-review: During design phase
    - pre-completion: Before marking work complete
    - on-error: When an error occurs
    """

    PRE_EXECUTION = "pre-execution"
    DESIGN_REVIEW = "design-review"
    PRE_COMPLETION = "pre-completion"
    ON_ERROR = "on-error"


# Valid operators for consultation conditions
VALID_OPERATORS = ["equals", "not_equals", "contains", "not_contains", "in", "not_in"]


class ConsultationCondition(BaseModel):
    """Conditional logic for when a consultation is required.

    Allows consultation requirements to be triggered based on task context,
    such as task type, tags, or other properties.

    Task T053: Create ConsultationCondition Pydantic model
    """

    field: str = Field(
        ..., description="The field path to evaluate (e.g., 'task.type', 'task.tags')"
    )
    operator: str = Field(..., description="The comparison operator to use")
    value: Any = Field(..., description="The value to compare against")

    @field_validator("operator")
    @classmethod
    def validate_operator(cls, v: str) -> str:
        """Ensure operator is one of the valid operators."""
        if v not in VALID_OPERATORS:
            raise ValueError(f"Invalid operator '{v}'. Must be one of: {VALID_OPERATORS}")
        return v


class ConsultationRequirement(BaseModel):
    """A requirement to consult with another agent during task execution.

    Defines which agent must be consulted, at what phase, and under what
    conditions (if any).

    Task T054: Create ConsultationRequirement Pydantic model
    """

    agent_name: str = Field(
        ..., description="Name of the agent to consult (must match Agent Card name)"
    )
    phase: ConsultationPhase = Field(
        ..., description="The phase during which consultation should occur"
    )
    mandatory: bool = Field(
        default=False,
        description="Whether this consultation is required (blocks completion if missing)",
    )
    condition: ConsultationCondition | None = Field(
        default=None,
        description="Optional condition that must be met for consultation to be required",
    )
    description: str | None = Field(
        default=None, description="Human-readable description of why this consultation is needed"
    )


# Valid consultation outcome statuses
VALID_STATUSES = ["pending", "approved", "rejected", "skipped"]


class ConsultationOutcome(BaseModel):
    """The result of a consultation with another agent.

    Records whether the consultation was completed, approved/rejected,
    and any feedback from the consulted agent.

    Task T055: Create ConsultationOutcome Pydantic model
    """

    requirement_id: str = Field(
        ..., description="Unique identifier linking to the ConsultationRequirement"
    )
    agent_name: str = Field(..., description="Name of the agent that was consulted")
    status: str = Field(..., description="Outcome status: pending, approved, rejected, or skipped")
    comments: str | None = Field(
        default=None, description="Feedback or comments from the consulted agent"
    )
    trace_id: str | None = Field(
        default=None, description="AgentCore Observability trace ID for audit"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now, description="When the consultation occurred"
    )

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Ensure status is one of the valid statuses."""
        if v not in VALID_STATUSES:
            raise ValueError(f"Invalid status '{v}'. Must be one of: {VALID_STATUSES}")
        return v
