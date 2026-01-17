"""SAM Local integration tests for registry API handlers.

These tests invoke actual Lambda functions via sam local invoke,
hitting LocalStack DynamoDB. They verify:
- Lambda packages bundle correctly
- Handler entry points work
- DynamoDB operations function
- API Gateway event parsing works
- Response format is correct
"""

import json
import uuid

import pytest

pytestmark = [
    pytest.mark.sam_local,
    pytest.mark.slow,
]


class TestListAgentsHandler:
    """Integration tests for ListAgentsFunction."""

    def test_list_agents_with_event_file(self, sam_invoker):
        """List agents handler works with pre-defined event file."""
        response = sam_invoker.invoke_with_event_file("ListAgentsFunction", "list_agents.json")

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "agents" in body
        assert isinstance(body["agents"], list)

    def test_list_agents_returns_registered_agents(self, sam_invoker, clean_test_data):
        """List agents returns agents after registration."""
        # First, register an agent
        test_name = f"test-list-{uuid.uuid4().hex[:6]}"
        register_event = {
            "httpMethod": "PUT",
            "path": f"/agents/{test_name}/metadata",
            "pathParameters": {"agent_name": test_name},
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "version": "1.0.0",
                    "input_schemas": [],
                    "output_schemas": [],
                }
            ),
        }
        sam_invoker.invoke("UpdateMetadataFunction", register_event)

        # Now list
        list_event = {
            "httpMethod": "GET",
            "path": "/agents",
            "queryStringParameters": None,
            "headers": {"Content-Type": "application/json"},
            "body": None,
        }

        response = sam_invoker.invoke("ListAgentsFunction", list_event)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        agent_names = [a["agent_name"] for a in body["agents"]]
        assert test_name in agent_names


class TestGetAgentHandler:
    """Integration tests for GetAgentFunction."""

    def test_get_agent_with_event_file(self, sam_invoker):
        """Get agent handler works with pre-defined event file."""
        response = sam_invoker.invoke_with_event_file("GetAgentFunction", "get_agent.json")

        # May be 404 if agent doesn't exist, or 200 if it does
        assert response["statusCode"] in [200, 404]

    def test_get_agent_not_found(self, sam_invoker):
        """Get non-existent agent returns 404."""
        event = {
            "httpMethod": "GET",
            "path": "/agents/nonexistent-agent-xyz",
            "pathParameters": {"agent_name": "nonexistent-agent-xyz"},
            "queryStringParameters": None,
            "headers": {"Content-Type": "application/json"},
            "body": None,
        }

        response = sam_invoker.invoke("GetAgentFunction", event)

        assert response["statusCode"] == 404

    def test_get_agent_success(self, sam_invoker, clean_test_data):
        """Get existing agent returns agent data."""
        # Register first
        test_name = f"test-get-{uuid.uuid4().hex[:6]}"
        register_event = {
            "httpMethod": "PUT",
            "path": f"/agents/{test_name}/metadata",
            "pathParameters": {"agent_name": test_name},
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "version": "2.0.0",
                    "input_schemas": [],
                    "output_schemas": [],
                }
            ),
        }
        sam_invoker.invoke("UpdateMetadataFunction", register_event)

        # Now get
        get_event = {
            "httpMethod": "GET",
            "path": f"/agents/{test_name}",
            "pathParameters": {"agent_name": test_name},
            "queryStringParameters": None,
            "headers": {"Content-Type": "application/json"},
            "body": None,
        }

        response = sam_invoker.invoke("GetAgentFunction", get_event)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["agent_name"] == test_name
        assert body["version"] == "2.0.0"


class TestUpdateMetadataHandler:
    """Integration tests for UpdateMetadataFunction."""

    def test_update_metadata_with_event_file(self, sam_invoker):
        """Update metadata handler works with pre-defined event file."""
        response = sam_invoker.invoke_with_event_file(
            "UpdateMetadataFunction", "update_metadata.json"
        )

        assert response["statusCode"] in [200, 201]

    def test_update_metadata_creates_new(self, sam_invoker, clean_test_data):
        """Update metadata creates new agent if not exists."""
        test_name = f"test-new-{uuid.uuid4().hex[:6]}"
        event = {
            "httpMethod": "PUT",
            "path": f"/agents/{test_name}/metadata",
            "pathParameters": {"agent_name": test_name},
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "version": "1.0.0",
                    "input_schemas": [],
                    "output_schemas": [],
                }
            ),
        }

        response = sam_invoker.invoke("UpdateMetadataFunction", event)

        assert response["statusCode"] in [200, 201]

    def test_update_metadata_invalid_body(self, sam_invoker):
        """Update metadata with invalid JSON returns 400."""
        event = {
            "httpMethod": "PUT",
            "path": "/agents/test-bad/metadata",
            "pathParameters": {"agent_name": "test-bad"},
            "headers": {"Content-Type": "application/json"},
            "body": "not valid json",
        }

        response = sam_invoker.invoke("UpdateMetadataFunction", event)

        assert response["statusCode"] == 400


class TestCheckCompatibilityHandler:
    """Integration tests for CheckCompatibilityFunction."""

    def test_check_compatibility_with_event_file(self, sam_invoker):
        """Check compatibility handler works with pre-defined event file."""
        response = sam_invoker.invoke_with_event_file(
            "CheckCompatibilityFunction", "check_compatibility.json"
        )

        # Handler should return a valid response (may be 404 if agents don't exist)
        assert response["statusCode"] in [200, 404]


class TestUpdateStatusHandler:
    """Integration tests for UpdateStatusFunction."""

    def test_update_status_with_event_file(self, sam_invoker):
        """Update status handler works with pre-defined event file."""
        response = sam_invoker.invoke_with_event_file("UpdateStatusFunction", "update_status.json")

        assert response["statusCode"] in [200, 201]

    def test_update_status_success(self, sam_invoker, clean_test_data):
        """Update agent status works correctly."""
        test_name = f"test-status-{uuid.uuid4().hex[:6]}"

        # First register the agent
        register_event = {
            "httpMethod": "PUT",
            "path": f"/agents/{test_name}/metadata",
            "pathParameters": {"agent_name": test_name},
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "version": "1.0.0",
                    "input_schemas": [],
                    "output_schemas": [],
                }
            ),
        }
        sam_invoker.invoke("UpdateMetadataFunction", register_event)

        # Now update status
        status_event = {
            "httpMethod": "PUT",
            "path": f"/agents/{test_name}/status",
            "pathParameters": {"agent_name": test_name},
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "status": "active",
                    "health_check": "passing",
                }
            ),
        }

        response = sam_invoker.invoke("UpdateStatusFunction", status_event)

        assert response["statusCode"] in [200, 201]
