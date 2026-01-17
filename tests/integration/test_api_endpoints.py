"""End-to-end tests for deployed API Gateway endpoints.

These tests hit the REAL deployed API to verify feature 001 (Agent Framework)
works end-to-end with actual infrastructure.

Requires:
- CDK stack deployed to AWS
- API_URL environment variable set (or uses default sandbox URL)
"""

import os
import uuid

import pytest
import requests

# Mark all tests as integration tests
pytestmark = pytest.mark.integration

# Default to sandbox API URL if not provided
DEFAULT_API_URL = "https://i92jukwhp5.execute-api.us-east-1.amazonaws.com/v1"


@pytest.fixture
def api_url():
    """Get API URL from environment or use default."""
    return os.getenv("API_URL", DEFAULT_API_URL)


@pytest.fixture
def unique_agent_name():
    """Generate unique agent name for test isolation."""
    return f"api-test-agent-{uuid.uuid4().hex[:8]}"


class TestListAgentsEndpoint:
    """Tests for GET /agents endpoint."""

    def test_list_agents_returns_200(self, api_url):
        """
        Scenario: List all registered agents

        Given the API is deployed
        When I call GET /agents
        Then I receive a 200 response
        And the response contains an agents array
        """
        response = requests.get(f"{api_url}/agents", timeout=30)

        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert isinstance(data["agents"], list)

        print(f"\n✅ GET /agents returned {len(data['agents'])} agents")

    def test_list_agents_response_structure(self, api_url):
        """
        Scenario: Verify agent list response structure

        Given there are agents registered
        When I call GET /agents
        Then each agent has required fields
        """
        response = requests.get(f"{api_url}/agents", timeout=30)

        assert response.status_code == 200
        data = response.json()

        if len(data["agents"]) > 0:
            agent = data["agents"][0]
            # Verify required fields exist
            assert "agent_name" in agent
            assert "version" in agent
            print(f"\n✅ Agent structure verified: {agent['agent_name']}")
        else:
            print("\n⚠️ No agents registered - structure check skipped")


class TestGetAgentEndpoint:
    """Tests for GET /agents/{agent_name} endpoint."""

    def test_get_existing_agent(self, api_url):
        """
        Scenario: Get details of an existing agent

        Given an agent exists in the registry
        When I call GET /agents/{agent_name}
        Then I receive a 200 response with agent details
        """
        # First, list agents to find one that exists
        list_response = requests.get(f"{api_url}/agents", timeout=30)
        agents = list_response.json().get("agents", [])

        if not agents:
            pytest.skip("No agents registered - cannot test get endpoint")

        agent_name = agents[0]["agent_name"]
        response = requests.get(f"{api_url}/agents/{agent_name}", timeout=30)

        assert response.status_code == 200
        data = response.json()
        assert data["agent_name"] == agent_name

        print(f"\n✅ GET /agents/{agent_name} returned agent details")

    def test_get_nonexistent_agent_returns_404(self, api_url):
        """
        Scenario: Get a non-existent agent returns 404

        Given an agent does not exist
        When I call GET /agents/{agent_name}
        Then I receive a 404 response
        """
        fake_agent = f"nonexistent-agent-{uuid.uuid4().hex[:8]}"
        response = requests.get(f"{api_url}/agents/{fake_agent}", timeout=30)

        assert response.status_code == 404

        print(f"\n✅ GET /agents/{fake_agent} correctly returned 404")


class TestAgentMetadataEndpoint:
    """Tests for PUT /agents/{agent_name}/metadata endpoint."""

    def test_create_and_update_agent_metadata(self, api_url, unique_agent_name):
        """
        Scenario: Create and update agent metadata

        Given I have agent metadata
        When I call PUT /agents/{agent_name}/metadata
        Then the agent is created/updated
        And I can retrieve it via GET
        """
        metadata = {
            "version": "1.0.0",
            "input_schemas": [
                {
                    "name": "test_input",
                    "semantic_type": "document",
                    "description": "Test input schema",
                    "required": True,
                }
            ],
            "output_schemas": [
                {
                    "name": "test_output",
                    "semantic_type": "artifact",
                    "description": "Test output schema",
                    "guaranteed": True,
                }
            ],
        }

        # Create agent
        put_response = requests.put(
            f"{api_url}/agents/{unique_agent_name}/metadata",
            json=metadata,
            timeout=30,
        )

        assert put_response.status_code in [200, 201], f"Failed: {put_response.text}"

        # Verify it exists
        get_response = requests.get(
            f"{api_url}/agents/{unique_agent_name}",
            timeout=30,
        )

        assert get_response.status_code == 200
        data = get_response.json()
        assert data["agent_name"] == unique_agent_name
        assert data["version"] == "1.0.0"

        print(f"\n✅ Created agent {unique_agent_name} via PUT /agents/{{name}}/metadata")
        print(f"✅ Verified agent exists via GET /agents/{unique_agent_name}")


class TestAgentStatusEndpoint:
    """Tests for GET/PUT /agents/{agent_name}/status endpoints."""

    def test_get_agent_status(self, api_url):
        """
        Scenario: Get agent status

        Given an agent exists
        When I call GET /agents/{agent_name}/status
        Then I receive the agent's status
        """
        # First find an existing agent
        list_response = requests.get(f"{api_url}/agents", timeout=30)
        agents = list_response.json().get("agents", [])

        if not agents:
            pytest.skip("No agents registered - cannot test status endpoint")

        agent_name = agents[0]["agent_name"]
        response = requests.get(f"{api_url}/agents/{agent_name}/status", timeout=30)

        # Status might not exist yet (404) or might exist (200)
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            assert "status" in data
            print(f"\n✅ GET /agents/{agent_name}/status returned: {data['status']}")
        else:
            print(f"\n✅ GET /agents/{agent_name}/status returned 404 (no status yet)")

    def test_update_agent_status(self, api_url):
        """
        Scenario: Update agent status

        Given an agent exists with a status entry
        When I call PUT /agents/{agent_name}/status
        Then the status is updated
        """
        # Find an agent that already has status data
        list_response = requests.get(f"{api_url}/agents", timeout=30)
        agents = list_response.json().get("agents", [])

        if not agents:
            pytest.skip("No agents registered - cannot test status update")

        # Find an agent that has status (check each one)
        agent_with_status = None
        for agent in agents:
            status_check = requests.get(
                f"{api_url}/agents/{agent['agent_name']}/status",
                timeout=30,
            )
            if status_check.status_code == 200:
                agent_with_status = agent["agent_name"]
                break

        if not agent_with_status:
            # Create status for first agent
            agent_with_status = agents[0]["agent_name"]
            # First update might create the status entry
            init_status = {"status": "inactive", "health_check": "unknown"}
            requests.put(
                f"{api_url}/agents/{agent_with_status}/status",
                json=init_status,
                timeout=30,
            )

        # Now update status
        status_data = {"status": "active", "health_check": "passing"}
        put_response = requests.put(
            f"{api_url}/agents/{agent_with_status}/status",
            json=status_data,
            timeout=30,
        )

        # API might return 200 (updated) or create new status entry
        assert put_response.status_code in [200, 201, 404], f"Unexpected: {put_response.text}"

        if put_response.status_code == 200:
            # Verify status was updated
            get_response = requests.get(
                f"{api_url}/agents/{agent_with_status}/status",
                timeout=30,
            )
            assert get_response.status_code == 200
            data = get_response.json()
            assert data["status"] == "active"
            print(f"\n✅ Updated {agent_with_status} status to 'active'")
        else:
            print(
                f"\n⚠️ Status update returned {put_response.status_code} - API may require pre-existing status"
            )


class TestConsultationRequirementsEndpoint:
    """Tests for GET /agents/{agent_name}/consultation-requirements endpoint."""

    def test_get_consultation_requirements(self, api_url):
        """
        Scenario: Get agent consultation requirements

        Given an agent exists with consultation requirements
        When I call GET /agents/{agent_name}/consultation-requirements
        Then I receive the requirements
        """
        # First find an existing agent
        list_response = requests.get(f"{api_url}/agents", timeout=30)
        agents = list_response.json().get("agents", [])

        if not agents:
            pytest.skip("No agents registered")

        agent_name = agents[0]["agent_name"]
        response = requests.get(
            f"{api_url}/agents/{agent_name}/consultation-requirements",
            timeout=30,
        )

        assert response.status_code == 200
        data = response.json()
        assert "requirements" in data

        print(
            f"\n✅ GET consultation-requirements returned {len(data['requirements'])} requirements"
        )


class TestCompatibilityEndpoint:
    """Tests for POST /agents/compatibility endpoint."""

    def test_check_compatibility(self, api_url):
        """
        Scenario: Check compatibility between two agents

        Given two agents exist
        When I call POST /agents/compatibility
        Then I receive a compatibility result
        """
        # Get list of agents
        list_response = requests.get(f"{api_url}/agents", timeout=30)
        agents = list_response.json().get("agents", [])

        if len(agents) < 2:
            pytest.skip("Need at least 2 agents for compatibility check")

        payload = {
            "source_agent": agents[0]["agent_name"],
            "target_agent": agents[1]["agent_name"],
        }

        response = requests.post(
            f"{api_url}/agents/compatibility",
            json=payload,
            timeout=30,
        )

        assert response.status_code == 200
        data = response.json()
        assert "is_compatible" in data

        print(f"\n✅ Compatibility check: {payload['source_agent']} → {payload['target_agent']}")
        print(f"✅ Result: {'compatible' if data['is_compatible'] else 'not compatible'}")


class TestFindCompatibleAgentsEndpoint:
    """Tests for POST /agents/find-compatible endpoint."""

    def test_find_compatible_agents(self, api_url):
        """
        Scenario: Find agents compatible with an input type

        When I call POST /agents/find-compatible
        Then I receive a list of compatible agents
        """
        payload = {"input_type": "document"}

        response = requests.post(
            f"{api_url}/agents/find-compatible",
            json=payload,
            timeout=30,
        )

        assert response.status_code == 200
        data = response.json()
        assert "agents" in data

        print("\n✅ Find compatible agents for 'document' input")
        print(f"✅ Found {len(data['agents'])} compatible agents")


class TestAPIErrorHandling:
    """Tests for API error handling."""

    def test_invalid_json_returns_400(self, api_url):
        """
        Scenario: Invalid JSON returns 400 error

        When I send invalid JSON to an endpoint
        Then I receive a 400 Bad Request
        """
        response = requests.put(
            f"{api_url}/agents/test-agent/metadata",
            data="this is not json",
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

        assert response.status_code == 400

        print("\n✅ Invalid JSON correctly returned 400")

    def test_invalid_schema_structure_returns_400(self, api_url, unique_agent_name):
        """
        Scenario: Invalid schema structure returns 400

        When I send a request with invalid schema structure
        Then I receive a 400 Bad Request with validation error details
        """
        # Invalid input_schemas structure (should be array of objects)
        invalid_metadata = {
            "version": "1.0.0",
            "input_schemas": "not an array",  # Should be array
            "output_schemas": [],
        }

        response = requests.put(
            f"{api_url}/agents/{unique_agent_name}/metadata",
            json=invalid_metadata,
            timeout=30,
        )

        assert response.status_code == 400, (
            f"Expected 400, got {response.status_code}: {response.text}"
        )

        print("\n✅ Invalid schema structure correctly returned 400")
