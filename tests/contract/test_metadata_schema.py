"""Contract tests for custom metadata schema validation."""

import json
from pathlib import Path

import pytest
from jsonschema import ValidationError as JsonSchemaValidationError
from jsonschema import validate


@pytest.fixture
def custom_metadata_schema():
    """Load Custom Metadata JSON schema."""
    schema_path = (
        Path(__file__).parents[2]
        / "specs/001-agent-framework/contracts/custom-metadata.schema.json"
    )
    with open(schema_path) as f:
        return json.load(f)


@pytest.fixture
def valid_metadata():
    """Valid custom metadata example."""
    return {
        "agent_name": "test-agent",
        "version": "1.0.0",
        "input_schemas": [
            {
                "name": "source-code",
                "semantic_type": "artifact",
                "description": "Source code files to process",
                "required": True,
            }
        ],
        "output_schemas": [
            {
                "name": "analysis-report",
                "semantic_type": "document",
                "description": "Code analysis results",
                "guaranteed": True,
            }
        ],
        "consultation_requirements": [],
    }


class TestCustomMetadataSchema:
    """Test custom metadata schema validation."""

    def test_valid_metadata(self, custom_metadata_schema, valid_metadata):
        """Valid metadata should pass validation."""
        validate(instance=valid_metadata, schema=custom_metadata_schema)

    def test_missing_agent_name(self, custom_metadata_schema, valid_metadata):
        """Metadata missing agent_name should fail."""
        invalid = valid_metadata.copy()
        del invalid["agent_name"]

        with pytest.raises(JsonSchemaValidationError):
            validate(instance=invalid, schema=custom_metadata_schema)

    def test_invalid_semantic_type(self, custom_metadata_schema, valid_metadata):
        """Invalid semantic type should fail."""
        invalid = valid_metadata.copy()
        invalid["input_schemas"][0]["semantic_type"] = "invalid-type"

        with pytest.raises(JsonSchemaValidationError):
            validate(instance=invalid, schema=custom_metadata_schema)

    def test_empty_schemas_allowed(self, custom_metadata_schema, valid_metadata):
        """Empty input/output schemas should be allowed."""
        metadata_with_empty = valid_metadata.copy()
        metadata_with_empty["input_schemas"] = []
        metadata_with_empty["output_schemas"] = []

        validate(instance=metadata_with_empty, schema=custom_metadata_schema)

    def test_consultation_requirements(self, custom_metadata_schema, valid_metadata):
        """Metadata with consultation requirements should validate."""
        metadata_with_consultation = valid_metadata.copy()
        metadata_with_consultation["consultation_requirements"] = [
            {
                "id": "consult-1",
                "target_agent": "security-agent",
                "phase": "pre-completion",
                "mandatory": True,
            }
        ]

        validate(instance=metadata_with_consultation, schema=custom_metadata_schema)
