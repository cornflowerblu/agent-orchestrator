"""Pydantic models for agent custom metadata."""

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field


class SemanticType(str, Enum):
    """Semantic type categories for agent inputs and outputs."""

    DOCUMENT = "document"  # Structured text documents (specs, designs, etc.)
    ARTIFACT = "artifact"  # Code, binaries, or generated files
    COLLECTION = "collection"  # Array of related items
    REFERENCE = "reference"  # Pointer to external resource
    COMMENT = "comment"  # Feedback or annotations


class ValidationRule(BaseModel):
    """Validation rule for input/output schemas."""

    type: str = Field(..., description="Validation type: format, length, pattern, enum")
    value: str | int | list[str] = Field(..., description="Validation value or constraint")
    message: str = Field(..., description="Error message if validation fails")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "type": "length",
                    "value": 1000,
                    "message": "Input must be less than 1000 characters",
                },
                {
                    "type": "pattern",
                    "value": "^[a-zA-Z0-9-]+$",
                    "message": "Must contain only alphanumeric characters and hyphens",
                },
            ]
        }
    }


class InputSchema(BaseModel):
    """Semantic type declaration for agent inputs."""

    name: str = Field(..., description="Input identifier")
    semantic_type: SemanticType = Field(..., description="Type category")
    description: str = Field(..., description="What this input represents")
    required: bool = Field(..., description="Must be provided for task assignment")
    validation_rules: list[ValidationRule] = Field(
        default_factory=list, description="Optional validation rules"
    )


class OutputSchema(BaseModel):
    """Semantic type declaration for agent outputs."""

    name: str = Field(..., description="Output identifier")
    semantic_type: SemanticType = Field(..., description="Type category")
    description: str = Field(..., description="What this output represents")
    guaranteed: bool = Field(..., description="Always produced vs conditional")


class CustomAgentMetadata(BaseModel):
    """Platform-specific extensions to Agent Cards."""

    agent_name: str = Field(..., description="Links to Agent Card name")
    version: str = Field(..., description="Should match Agent Card version")
    input_schemas: list[InputSchema] = Field(
        default_factory=list, description="Enhanced I/O beyond basic modes"
    )
    output_schemas: list[OutputSchema] = Field(default_factory=list, description="Enhanced outputs")
    consultation_requirements: list[dict] = Field(
        default_factory=list,
        description="Consultation requirements (defined in consultation module)",
    )
    created_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(), description="ISO8601 timestamp"
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(), description="ISO8601 timestamp"
    )
