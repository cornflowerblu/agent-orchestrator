"""Unit tests for registry Lambda handlers.

Tests for T076-T083: Lambda handlers
"""

import json
import pytest
from unittest.mock import MagicMock, patch

from src.agents.models import AgentCard, AgentCapabilities, Skill
from src.consultation.rules import ConsultationRequirement, ConsultationPhase
from src.exceptions import AgentNotFoundError
from src.registry.models import AgentStatus, AgentStatusValue, HealthCheckStatus
from src.registry.query import CompatibilityResult


@pytest.fixture
def mock_context():
    """Create mock Lambda context."""
    context = MagicMock()
    context.function_name = "test-handler"
    context.aws_request_id = "test-id"
    return context


@pytest.fixture
def sample_agent_card():
    """Create a sample agent card."""
    return AgentCard(
        name="test-agent",
        description="Test agent for testing purposes",
        version="1.0.0",
        url="https://test.example.com/invoke",
        capabilities=AgentCapabilities(streaming=True),
        skills=[
            Skill(
                id="test-skill",
                name="Test Skill",
                description="A test skill for testing"
            )
        ],
        defaultInputModes=["text"],
        defaultOutputModes=["text"]
    )


class TestListAgentsHandler:
    """Tests for list_agents_handler (T076)."""

    def test_list_agents_success(self, mock_context, sample_agent_card):
        """Test listing agents successfully."""
        from src.registry.handlers import list_agents_handler

        with patch('src.registry.handlers.get_registry') as mock_get:
            mock_registry = MagicMock()
            mock_registry.list_all_agents.return_value = [sample_agent_card]
            mock_get.return_value = mock_registry

            response = list_agents_handler({}, mock_context)

            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            assert body["count"] == 1
            assert len(body["agents"]) == 1

    def test_list_agents_empty(self, mock_context):
        """Test listing when no agents exist."""
        from src.registry.handlers import list_agents_handler

        with patch('src.registry.handlers.get_registry') as mock_get:
            mock_registry = MagicMock()
            mock_registry.list_all_agents.return_value = []
            mock_get.return_value = mock_registry

            response = list_agents_handler({}, mock_context)

            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            assert body["count"] == 0

    def test_list_agents_error(self, mock_context):
        """Test error handling in list_agents."""
        from src.registry.handlers import list_agents_handler

        with patch('src.registry.handlers.get_registry') as mock_get:
            mock_get.side_effect = Exception("Test error")

            response = list_agents_handler({}, mock_context)

            assert response["statusCode"] == 500


class TestGetAgentHandler:
    """Tests for get_agent_handler (T077)."""

    def test_get_agent_success(self, mock_context, sample_agent_card):
        """Test getting an agent successfully."""
        from src.registry.handlers import get_agent_handler

        event = {"pathParameters": {"agent_name": "test-agent"}}

        with patch('src.registry.handlers.get_registry') as mock_get:
            mock_registry = MagicMock()
            mock_registry.get_agent_card.return_value = sample_agent_card
            mock_get.return_value = mock_registry

            response = get_agent_handler(event, mock_context)

            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            assert body["name"] == "test-agent"

    def test_get_agent_not_found(self, mock_context):
        """Test getting a non-existent agent."""
        from src.registry.handlers import get_agent_handler

        event = {"pathParameters": {"agent_name": "missing-agent"}}

        with patch('src.registry.handlers.get_registry') as mock_get:
            mock_registry = MagicMock()
            mock_registry.get_agent_card.side_effect = AgentNotFoundError("missing-agent")
            mock_get.return_value = mock_registry

            response = get_agent_handler(event, mock_context)

            assert response["statusCode"] == 404

    def test_get_agent_missing_param(self, mock_context):
        """Test missing agent_name parameter."""
        from src.registry.handlers import get_agent_handler

        event = {"pathParameters": None}

        response = get_agent_handler(event, mock_context)

        assert response["statusCode"] == 400


class TestUpdateAgentMetadataHandler:
    """Tests for update_agent_metadata_handler (T078)."""

    def test_update_metadata_success(self, mock_context):
        """Test updating metadata successfully."""
        from src.registry.handlers import update_agent_metadata_handler

        event = {
            "pathParameters": {"agent_name": "test-agent"},
            "body": json.dumps({
                "version": "2.0.0",
                "input_schemas": [],
                "output_schemas": []
            })
        }

        with patch('src.registry.handlers.get_metadata_storage') as mock_get:
            mock_storage = MagicMock()
            mock_storage.put_metadata.return_value = {"agent_name": "test-agent"}
            mock_get.return_value = mock_storage

            response = update_agent_metadata_handler(event, mock_context)

            assert response["statusCode"] == 200

    def test_update_metadata_invalid_json(self, mock_context):
        """Test handling invalid JSON body."""
        from src.registry.handlers import update_agent_metadata_handler

        event = {
            "pathParameters": {"agent_name": "test-agent"},
            "body": "not valid json"
        }

        response = update_agent_metadata_handler(event, mock_context)

        assert response["statusCode"] == 400

    def test_update_metadata_missing_param(self, mock_context):
        """Test missing agent_name parameter."""
        from src.registry.handlers import update_agent_metadata_handler

        event = {
            "pathParameters": None,
            "body": "{}"
        }

        response = update_agent_metadata_handler(event, mock_context)

        assert response["statusCode"] == 400


class TestGetConsultationRequirementsHandler:
    """Tests for get_consultation_requirements_handler (T079)."""

    def test_get_requirements_success(self, mock_context):
        """Test getting consultation requirements."""
        from src.registry.handlers import get_consultation_requirements_handler

        event = {"pathParameters": {"agent_name": "test-agent"}}

        with patch('src.registry.handlers.get_registry') as mock_get:
            mock_registry = MagicMock()
            mock_registry.get_consultation_requirements.return_value = [
                ConsultationRequirement(
                    agent_name="security-agent",
                    phase=ConsultationPhase.PRE_COMPLETION,
                    mandatory=True
                )
            ]
            mock_get.return_value = mock_registry

            response = get_consultation_requirements_handler(event, mock_context)

            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            assert body["count"] == 1

    def test_get_requirements_missing_param(self, mock_context):
        """Test missing agent_name parameter."""
        from src.registry.handlers import get_consultation_requirements_handler

        event = {"pathParameters": None}

        response = get_consultation_requirements_handler(event, mock_context)

        assert response["statusCode"] == 400


class TestCheckCompatibilityHandler:
    """Tests for check_compatibility_handler (T080)."""

    def test_check_compatibility_success(self, mock_context):
        """Test checking compatibility."""
        from src.registry.handlers import check_compatibility_handler

        event = {
            "body": json.dumps({
                "source_agent": "agent-a",
                "target_agent": "agent-b"
            })
        }

        with patch('src.registry.handlers.get_registry') as mock_get:
            mock_registry = MagicMock()
            mock_registry.check_compatibility.return_value = CompatibilityResult(
                is_compatible=True,
                source_agent="agent-a",
                target_agent="agent-b",
                details={}
            )
            mock_get.return_value = mock_registry

            response = check_compatibility_handler(event, mock_context)

            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            assert body["is_compatible"] is True

    def test_check_compatibility_missing_params(self, mock_context):
        """Test missing parameters."""
        from src.registry.handlers import check_compatibility_handler

        event = {"body": json.dumps({"source_agent": "agent-a"})}

        response = check_compatibility_handler(event, mock_context)

        assert response["statusCode"] == 400

    def test_check_compatibility_not_found(self, mock_context):
        """Test agent not found."""
        from src.registry.handlers import check_compatibility_handler

        event = {
            "body": json.dumps({
                "source_agent": "missing",
                "target_agent": "agent-b"
            })
        }

        with patch('src.registry.handlers.get_registry') as mock_get:
            mock_registry = MagicMock()
            mock_registry.check_compatibility.side_effect = AgentNotFoundError("missing")
            mock_get.return_value = mock_registry

            response = check_compatibility_handler(event, mock_context)

            assert response["statusCode"] == 404


class TestFindCompatibleAgentsHandler:
    """Tests for find_compatible_agents_handler (T081)."""

    def test_find_compatible_success(self, mock_context, sample_agent_card):
        """Test finding compatible agents."""
        from src.registry.handlers import find_compatible_agents_handler

        event = {"body": json.dumps({"input_type": "artifact"})}

        with patch('src.registry.handlers.get_registry') as mock_get:
            mock_registry = MagicMock()
            mock_registry.find_by_input_compatibility.return_value = [sample_agent_card]
            mock_get.return_value = mock_registry

            response = find_compatible_agents_handler(event, mock_context)

            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            assert body["count"] == 1

    def test_find_compatible_missing_type(self, mock_context):
        """Test missing input_type parameter."""
        from src.registry.handlers import find_compatible_agents_handler

        event = {"body": "{}"}

        response = find_compatible_agents_handler(event, mock_context)

        assert response["statusCode"] == 400

    def test_find_compatible_invalid_type(self, mock_context):
        """Test invalid semantic type."""
        from src.registry.handlers import find_compatible_agents_handler

        event = {"body": json.dumps({"input_type": "INVALID_TYPE"})}

        response = find_compatible_agents_handler(event, mock_context)

        assert response["statusCode"] == 400


class TestGetAgentStatusHandler:
    """Tests for get_agent_status_handler (T082)."""

    def test_get_status_success(self, mock_context):
        """Test getting agent status."""
        from src.registry.handlers import get_agent_status_handler

        event = {"pathParameters": {"agent_name": "test-agent"}}

        with patch('src.registry.handlers.get_status_storage') as mock_get:
            mock_storage = MagicMock()
            mock_storage.get_status.return_value = AgentStatus(
                agent_name="test-agent",
                status=AgentStatusValue.ACTIVE,
                health_check=HealthCheckStatus.PASSING
            )
            mock_get.return_value = mock_storage

            response = get_agent_status_handler(event, mock_context)

            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            assert body["agent_name"] == "test-agent"

    def test_get_status_not_found(self, mock_context):
        """Test getting status for non-existent agent."""
        from src.registry.handlers import get_agent_status_handler

        event = {"pathParameters": {"agent_name": "missing"}}

        with patch('src.registry.handlers.get_status_storage') as mock_get:
            mock_storage = MagicMock()
            mock_storage.get_status.side_effect = AgentNotFoundError("missing")
            mock_get.return_value = mock_storage

            response = get_agent_status_handler(event, mock_context)

            assert response["statusCode"] == 404

    def test_get_status_missing_param(self, mock_context):
        """Test missing agent_name parameter."""
        from src.registry.handlers import get_agent_status_handler

        event = {"pathParameters": None}

        response = get_agent_status_handler(event, mock_context)

        assert response["statusCode"] == 400


class TestUpdateAgentStatusHandler:
    """Tests for update_agent_status_handler (T083)."""

    def test_update_status_success(self, mock_context):
        """Test updating agent status."""
        from src.registry.handlers import update_agent_status_handler

        event = {
            "pathParameters": {"agent_name": "test-agent"},
            "body": json.dumps({
                "status": "active",
                "health_check": "passing"
            })
        }

        with patch('src.registry.handlers.get_status_storage') as mock_get:
            mock_storage = MagicMock()
            mock_storage.update_status.return_value = AgentStatus(
                agent_name="test-agent",
                status=AgentStatusValue.ACTIVE,
                health_check=HealthCheckStatus.PASSING
            )
            mock_get.return_value = mock_storage

            response = update_agent_status_handler(event, mock_context)

            assert response["statusCode"] == 200

    def test_update_status_invalid_value(self, mock_context):
        """Test invalid status value."""
        from src.registry.handlers import update_agent_status_handler

        event = {
            "pathParameters": {"agent_name": "test-agent"},
            "body": json.dumps({"status": "invalid_status"})
        }

        response = update_agent_status_handler(event, mock_context)

        assert response["statusCode"] == 400

    def test_update_status_missing_param(self, mock_context):
        """Test missing agent_name parameter."""
        from src.registry.handlers import update_agent_status_handler

        event = {
            "pathParameters": None,
            "body": json.dumps({"status": "active"})
        }

        response = update_agent_status_handler(event, mock_context)

        assert response["statusCode"] == 400


class TestHelperFunctions:
    """Tests for handler helper functions."""

    def test_create_response(self):
        """Test response creation."""
        from src.registry.handlers import _create_response

        response = _create_response(200, {"message": "ok"})

        assert response["statusCode"] == 200
        assert "Content-Type" in response["headers"]
        body = json.loads(response["body"])
        assert body["message"] == "ok"

    def test_get_path_param_exists(self):
        """Test getting existing path parameter."""
        from src.registry.handlers import _get_path_param

        event = {"pathParameters": {"name": "value"}}
        assert _get_path_param(event, "name") == "value"

    def test_get_path_param_missing(self):
        """Test getting missing path parameter."""
        from src.registry.handlers import _get_path_param

        event = {"pathParameters": None}
        assert _get_path_param(event, "name") is None

    def test_get_body_json(self):
        """Test parsing JSON body."""
        from src.registry.handlers import _get_body

        event = {"body": '{"key": "value"}'}
        body = _get_body(event)
        assert body["key"] == "value"

    def test_get_body_none(self):
        """Test handling None body."""
        from src.registry.handlers import _get_body

        event = {"body": None}
        body = _get_body(event)
        assert body == {}

    def test_get_body_dict(self):
        """Test handling dict body."""
        from src.registry.handlers import _get_body

        event = {"body": {"key": "value"}}
        body = _get_body(event)
        assert body["key"] == "value"
