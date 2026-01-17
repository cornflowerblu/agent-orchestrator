"""Integration tests for registry API.

Task T064: Integration test for registry API in tests/integration/test_registry_api.py

These tests require AWS deployment and are skipped in unit test runs.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from src.registry.models import AgentStatus, AgentStatusValue, HealthCheckStatus

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


@pytest.fixture
def mock_lambda_context():
    """Create a mock Lambda context."""
    context = MagicMock()
    context.function_name = "test-function"
    context.memory_limit_in_mb = 128
    context.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789:function:test"
    context.aws_request_id = "test-request-id"
    return context


@pytest.fixture
def sample_event_list_agents():
    """Sample API Gateway event for listing agents."""
    return {
        "httpMethod": "GET",
        "path": "/agents",
        "queryStringParameters": None,
        "headers": {"Content-Type": "application/json"},
        "body": None,
    }


@pytest.fixture
def sample_event_get_agent():
    """Sample API Gateway event for getting an agent."""
    return {
        "httpMethod": "GET",
        "path": "/agents/test-agent",
        "pathParameters": {"agent_name": "test-agent"},
        "queryStringParameters": None,
        "headers": {"Content-Type": "application/json"},
        "body": None,
    }


class TestListAgentsHandler:
    """Integration tests for listAgents Lambda handler (T076)."""

    def test_list_agents_empty(self, mock_lambda_context, sample_event_list_agents):
        """Test listing agents when none exist."""
        from src.registry.handlers import list_agents_handler

        with patch("src.registry.handlers.get_registry") as mock_get_registry:
            mock_registry = MagicMock()
            mock_registry.list_all_agents.return_value = []
            mock_get_registry.return_value = mock_registry

            response = list_agents_handler(sample_event_list_agents, mock_lambda_context)

            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            assert body["agents"] == []

    def test_list_agents_with_results(self, mock_lambda_context, sample_event_list_agents):
        """Test listing agents with results."""
        from src.agents.models import AgentCapabilities, AgentCard
        from src.registry.handlers import list_agents_handler

        with patch("src.registry.handlers.get_registry") as mock_get_registry:
            mock_registry = MagicMock()
            caps = AgentCapabilities(streaming=True)
            cards = [
                AgentCard(
                    name="agent-1",
                    description="First agent for testing purposes",
                    version="1.0.0",
                    url="https://agent-1.example.com/invoke",
                    capabilities=caps,
                    skills=[],
                    defaultInputModes=["text"],
                    defaultOutputModes=["text"],
                ),
                AgentCard(
                    name="agent-2",
                    description="Second agent for testing purposes",
                    version="1.0.0",
                    url="https://agent-2.example.com/invoke",
                    capabilities=caps,
                    skills=[],
                    defaultInputModes=["text"],
                    defaultOutputModes=["text"],
                ),
            ]
            mock_registry.list_all_agents.return_value = cards
            mock_get_registry.return_value = mock_registry

            response = list_agents_handler(sample_event_list_agents, mock_lambda_context)

            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            assert len(body["agents"]) == 2


class TestGetAgentHandler:
    """Integration tests for getAgent Lambda handler (T077)."""

    def test_get_agent_success(self, mock_lambda_context, sample_event_get_agent):
        """Test getting an existing agent."""
        from src.agents.models import AgentCapabilities, AgentCard
        from src.registry.handlers import get_agent_handler

        with patch("src.registry.handlers.get_registry") as mock_get_registry:
            mock_registry = MagicMock()
            card = AgentCard(
                name="test-agent",
                description="Test agent for testing purposes",
                version="1.0.0",
                url="https://test-agent.example.com/invoke",
                capabilities=AgentCapabilities(streaming=True),
                skills=[],
                defaultInputModes=["text"],
                defaultOutputModes=["text"],
            )
            mock_registry.get_agent_card.return_value = card
            mock_get_registry.return_value = mock_registry

            response = get_agent_handler(sample_event_get_agent, mock_lambda_context)

            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            assert body["name"] == "test-agent"

    def test_get_agent_not_found(self, mock_lambda_context, sample_event_get_agent):
        """Test getting a non-existent agent."""
        from src.exceptions import AgentNotFoundError
        from src.registry.handlers import get_agent_handler

        with patch("src.registry.handlers.get_registry") as mock_get_registry:
            mock_registry = MagicMock()
            mock_registry.get_agent_card.side_effect = AgentNotFoundError("test-agent")
            mock_get_registry.return_value = mock_registry

            response = get_agent_handler(sample_event_get_agent, mock_lambda_context)

            assert response["statusCode"] == 404


class TestUpdateAgentMetadataHandler:
    """Integration tests for updateAgentMetadata Lambda handler (T078)."""

    def test_update_metadata_success(self, mock_lambda_context):
        """Test updating agent metadata."""
        from src.registry.handlers import update_agent_metadata_handler

        event = {
            "httpMethod": "PUT",
            "path": "/agents/test-agent/metadata",
            "pathParameters": {"agent_name": "test-agent"},
            "body": json.dumps({"version": "2.0.0", "input_schemas": [], "output_schemas": []}),
        }

        with patch("src.registry.handlers.get_metadata_storage") as mock_get_storage:
            mock_storage = MagicMock()
            mock_storage.put_metadata.return_value = {"agent_name": "test-agent"}
            mock_get_storage.return_value = mock_storage

            response = update_agent_metadata_handler(event, mock_lambda_context)

            assert response["statusCode"] in [200, 201]


class TestGetConsultationRequirementsHandler:
    """Integration tests for getConsultationRequirements handler (T079)."""

    def test_get_requirements_success(self, mock_lambda_context):
        """Test getting consultation requirements."""
        from src.consultation.rules import ConsultationPhase, ConsultationRequirement
        from src.registry.handlers import get_consultation_requirements_handler

        event = {
            "httpMethod": "GET",
            "path": "/agents/test-agent/consultation-requirements",
            "pathParameters": {"agent_name": "test-agent"},
        }

        with patch("src.registry.handlers.get_registry") as mock_get_registry:
            mock_registry = MagicMock()
            requirements = [
                ConsultationRequirement(
                    agent_name="security-agent",
                    phase=ConsultationPhase.PRE_COMPLETION,
                    mandatory=True,
                )
            ]
            mock_registry.get_consultation_requirements.return_value = requirements
            mock_get_registry.return_value = mock_registry

            response = get_consultation_requirements_handler(event, mock_lambda_context)

            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            assert len(body["requirements"]) == 1


class TestCheckCompatibilityHandler:
    """Integration tests for checkCompatibility handler (T080)."""

    def test_check_compatibility_success(self, mock_lambda_context):
        """Test checking agent compatibility."""
        from src.registry.handlers import check_compatibility_handler
        from src.registry.query import CompatibilityResult

        event = {
            "httpMethod": "POST",
            "path": "/agents/compatibility",
            "body": json.dumps({"source_agent": "agent-a", "target_agent": "agent-b"}),
        }

        with patch("src.registry.handlers.get_registry") as mock_get_registry:
            mock_registry = MagicMock()
            result = CompatibilityResult(
                is_compatible=True, source_agent="agent-a", target_agent="agent-b", details={}
            )
            mock_registry.check_compatibility.return_value = result
            mock_get_registry.return_value = mock_registry

            response = check_compatibility_handler(event, mock_lambda_context)

            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            assert body["is_compatible"] is True


class TestFindCompatibleAgentsHandler:
    """Integration tests for findCompatibleAgents handler (T081)."""

    def test_find_compatible_agents_success(self, mock_lambda_context):
        """Test finding compatible agents."""
        from src.agents.models import AgentCapabilities, AgentCard
        from src.registry.handlers import find_compatible_agents_handler

        event = {
            "httpMethod": "POST",
            "path": "/agents/find-compatible",
            "body": json.dumps({"input_type": "artifact"}),
        }

        with patch("src.registry.handlers.get_registry") as mock_get_registry:
            mock_registry = MagicMock()
            cards = [
                AgentCard(
                    name="compatible-agent",
                    description="Compatible agent for testing purposes",
                    version="1.0.0",
                    url="https://compatible-agent.example.com/invoke",
                    capabilities=AgentCapabilities(streaming=True),
                    skills=[],
                    defaultInputModes=["text"],
                    defaultOutputModes=["text"],
                )
            ]
            mock_registry.find_by_input_compatibility.return_value = cards
            mock_get_registry.return_value = mock_registry

            response = find_compatible_agents_handler(event, mock_lambda_context)

            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            assert len(body["agents"]) == 1


class TestGetAgentStatusHandler:
    """Integration tests for getAgentStatus handler (T082)."""

    def test_get_status_success(self, mock_lambda_context):
        """Test getting agent status."""
        from src.registry.handlers import get_agent_status_handler

        event = {
            "httpMethod": "GET",
            "path": "/agents/test-agent/status",
            "pathParameters": {"agent_name": "test-agent"},
        }

        with patch("src.registry.handlers.get_status_storage") as mock_get_storage:
            mock_storage = MagicMock()
            mock_storage.get_status.return_value = AgentStatus(
                agent_name="test-agent",
                status=AgentStatusValue.ACTIVE,
                health_check=HealthCheckStatus.PASSING,
                last_seen="2024-01-01T00:00:00Z",
            )
            mock_get_storage.return_value = mock_storage

            response = get_agent_status_handler(event, mock_lambda_context)

            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            assert body["status"] == "active"


class TestUpdateAgentStatusHandler:
    """Integration tests for updateAgentStatus handler (T083)."""

    def test_update_status_success(self, mock_lambda_context):
        """Test updating agent status."""
        from src.registry.handlers import update_agent_status_handler

        event = {
            "httpMethod": "PUT",
            "path": "/agents/test-agent/status",
            "pathParameters": {"agent_name": "test-agent"},
            "body": json.dumps({"status": "active", "health_check": "passing"}),
        }

        with patch("src.registry.handlers.get_status_storage") as mock_get_storage:
            mock_storage = MagicMock()
            mock_storage.update_status.return_value = AgentStatus(
                agent_name="test-agent",
                status=AgentStatusValue.ACTIVE,
                health_check=HealthCheckStatus.PASSING,
                last_seen="2024-01-01T00:00:00Z",
            )
            mock_get_storage.return_value = mock_storage

            response = update_agent_status_handler(event, mock_lambda_context)

            assert response["statusCode"] == 200


class TestErrorHandling:
    """Integration tests for error handling in handlers."""

    def test_handler_validation_error(self, mock_lambda_context):
        """Test handler returns 400 for validation errors."""
        from src.registry.handlers import update_agent_metadata_handler

        event = {
            "httpMethod": "PUT",
            "path": "/agents/test-agent/metadata",
            "pathParameters": {"agent_name": "test-agent"},
            "body": "invalid json",
        }

        response = update_agent_metadata_handler(event, mock_lambda_context)

        assert response["statusCode"] == 400

    def test_handler_internal_error(self, mock_lambda_context):
        """Test handler returns 500 for internal errors."""
        from src.registry.handlers import list_agents_handler

        event = {"httpMethod": "GET", "path": "/agents"}

        with patch("src.registry.handlers.get_registry") as mock_get_registry:
            mock_get_registry.side_effect = Exception("Internal error")

            response = list_agents_handler(event, mock_lambda_context)

            assert response["statusCode"] == 500
