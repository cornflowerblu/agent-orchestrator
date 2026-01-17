"""Contract tests for Agent Card schema validation."""

import json
from pathlib import Path

import pytest
from jsonschema import ValidationError as JsonSchemaValidationError
from jsonschema import validate


@pytest.fixture
def agent_card_schema():
    """Load Agent Card JSON schema."""
    schema_path = (
        Path(__file__).parents[2] / "specs/001-agent-framework/contracts/agent-card.schema.json"
    )
    with open(schema_path) as f:
        return json.load(f)


@pytest.fixture
def valid_agent_card():
    """Valid Agent Card example."""
    return {
        "name": "test-agent",
        "description": "A test agent for schema validation",
        "version": "1.0.0",
        "url": "https://bedrock-agentcore.us-east-1.amazonaws.com/runtimes/test-agent-123/invocations/",
        "protocolVersion": "0.3.0",
        "preferredTransport": "JSONRPC",
        "capabilities": {"streaming": True},
        "defaultInputModes": ["text"],
        "defaultOutputModes": ["text"],
        "skills": [
            {
                "id": "test-skill",
                "name": "Test Skill",
                "description": "A skill for testing purposes",
                "tags": ["test", "validation"],
            }
        ],
    }


class TestAgentCardSchema:
    """Test Agent Card schema validation."""

    def test_valid_agent_card(self, agent_card_schema, valid_agent_card):
        """Valid Agent Card should pass validation."""
        validate(instance=valid_agent_card, schema=agent_card_schema)

    def test_missing_required_field(self, agent_card_schema, valid_agent_card):
        """Agent Card missing required field should fail."""
        invalid_card = valid_agent_card.copy()
        del invalid_card["name"]

        with pytest.raises(JsonSchemaValidationError):
            validate(instance=invalid_card, schema=agent_card_schema)

    def test_invalid_name_pattern(self, agent_card_schema, valid_agent_card):
        """Agent Card with invalid name pattern should fail."""
        invalid_card = valid_agent_card.copy()
        invalid_card["name"] = "123-invalid"  # Cannot start with number

        with pytest.raises(JsonSchemaValidationError):
            validate(instance=invalid_card, schema=agent_card_schema)

    def test_invalid_version_format(self, agent_card_schema, valid_agent_card):
        """Agent Card with invalid version format should fail."""
        invalid_card = valid_agent_card.copy()
        invalid_card["version"] = "1.0"  # Must be X.Y.Z

        with pytest.raises(JsonSchemaValidationError):
            validate(instance=invalid_card, schema=agent_card_schema)

    def test_empty_skills_array(self, agent_card_schema, valid_agent_card):
        """Agent Card with empty skills array should pass (warned at runtime)."""
        card_with_empty_skills = valid_agent_card.copy()
        card_with_empty_skills["skills"] = []

        # Schema allows empty skills, but orchestrator should warn
        validate(instance=card_with_empty_skills, schema=agent_card_schema)

    def test_invalid_skill_id_pattern(self, agent_card_schema, valid_agent_card):
        """Skill with invalid ID pattern should fail."""
        invalid_card = valid_agent_card.copy()
        invalid_card["skills"][0]["id"] = "Invalid-Skill"  # Must be lowercase

        with pytest.raises(JsonSchemaValidationError):
            validate(instance=invalid_card, schema=agent_card_schema)

    def test_multiple_skills(self, agent_card_schema, valid_agent_card):
        """Agent Card with multiple skills should pass."""
        card_with_multiple_skills = valid_agent_card.copy()
        card_with_multiple_skills["skills"].append(
            {
                "id": "another-skill",
                "name": "Another Skill",
                "description": "A second skill for testing",
                "tags": ["additional"],
            }
        )

        validate(instance=card_with_multiple_skills, schema=agent_card_schema)

    def test_invalid_protocol_version(self, agent_card_schema, valid_agent_card):
        """Agent Card with invalid protocol version should fail."""
        invalid_card = valid_agent_card.copy()
        invalid_card["protocolVersion"] = "0.2.0"  # Must be 0.3.0

        with pytest.raises(JsonSchemaValidationError):
            validate(instance=invalid_card, schema=agent_card_schema)

    def test_invalid_input_mode(self, agent_card_schema, valid_agent_card):
        """Agent Card with invalid input mode should fail."""
        invalid_card = valid_agent_card.copy()
        invalid_card["defaultInputModes"] = ["video"]  # Only text, image, audio allowed

        with pytest.raises(JsonSchemaValidationError):
            validate(instance=invalid_card, schema=agent_card_schema)
