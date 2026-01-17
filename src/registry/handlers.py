"""Lambda handlers for the registry API.

Task T076: Implement listAgents Lambda handler
Task T077: Implement getAgent Lambda handler
Task T078: Implement updateAgentMetadata Lambda handler
Task T079: Implement getConsultationRequirements Lambda handler
Task T080: Implement checkCompatibility Lambda handler
Task T081: Implement findCompatibleAgents Lambda handler
Task T082: Implement getAgentStatus Lambda handler
Task T083: Implement updateAgentStatus Lambda handler
"""

import json
from functools import lru_cache
from typing import Any

from botocore.exceptions import ClientError

from src.exceptions import AgentNotFoundError, ValidationError
from src.logging_config import get_logger
from src.metadata.models import CustomAgentMetadata, SemanticType
from src.metadata.storage import MetadataStorage
from src.registry.models import AgentStatusValue, HealthCheckStatus
from src.registry.query import AgentRegistry
from src.registry.status import StatusStorage

logger = get_logger(__name__)


# Singleton instances
_registry: AgentRegistry | None = None
_metadata_storage: MetadataStorage | None = None
_status_storage: StatusStorage | None = None


@lru_cache(maxsize=1)
def get_registry() -> AgentRegistry:
    """Get the singleton AgentRegistry instance."""
    global _registry  # noqa: PLW0603
    if _registry is None:
        _registry = AgentRegistry(
            metadata_storage=get_metadata_storage(),
        )
    return _registry


@lru_cache(maxsize=1)
def get_metadata_storage() -> MetadataStorage:
    """Get the singleton MetadataStorage instance."""
    global _metadata_storage  # noqa: PLW0603
    if _metadata_storage is None:
        _metadata_storage = MetadataStorage()
    return _metadata_storage


@lru_cache(maxsize=1)
def get_status_storage() -> StatusStorage:
    """Get the singleton StatusStorage instance."""
    global _status_storage  # noqa: PLW0603
    if _status_storage is None:
        _status_storage = StatusStorage()
    return _status_storage


def _create_response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    """Create an API Gateway response.

    Args:
        status_code: HTTP status code
        body: Response body dict

    Returns:
        API Gateway response dict
    """
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body, default=str),
    }


def _get_path_param(event: dict[str, Any], param: str) -> str | None:
    """Get a path parameter from the event.

    Args:
        event: API Gateway event
        param: Parameter name

    Returns:
        Parameter value or None
    """
    params = event.get("pathParameters") or {}
    return params.get(param)


def _get_body(event: dict[str, Any]) -> dict[str, Any]:
    """Parse the request body.

    Args:
        event: API Gateway event

    Returns:
        Parsed body dict

    Raises:
        ValueError: If body is invalid JSON
    """
    body = event.get("body")
    if body is None:
        return {}
    if isinstance(body, str):
        return json.loads(body)
    return body


def list_agents_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """List all registered agents.

    Task T076: Implement listAgents Lambda handler

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        API Gateway response with list of agents
    """
    try:
        logger.info("Handling listAgents request")

        registry = get_registry()
        agents = registry.list_all_agents()

        return _create_response(
            200,
            {
                "agents": [a.model_dump() for a in agents],
                "count": len(agents),
            },
        )

    except ClientError:
        logger.exception("AWS service error listing agents")
        return _create_response(503, {"error": "Service temporarily unavailable"})

    except Exception:
        logger.exception("Unexpected error listing agents")
        return _create_response(500, {"error": "Internal server error"})


def get_agent_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Get a specific agent by name.

    Task T077: Implement getAgent Lambda handler

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        API Gateway response with agent details
    """
    try:
        agent_name = _get_path_param(event, "agent_name")
        if not agent_name:
            return _create_response(400, {"error": "agent_name is required"})

        logger.info(f"Handling getAgent request for '{agent_name}'")

        registry = get_registry()
        card = registry.get_agent_card(agent_name)

        return _create_response(200, card.model_dump())

    except AgentNotFoundError as e:
        return _create_response(404, {"error": str(e)})

    except ClientError:
        logger.exception("AWS service error getting agent")
        return _create_response(503, {"error": "Service temporarily unavailable"})

    except Exception:
        logger.exception("Unexpected error getting agent")
        return _create_response(500, {"error": "Internal server error"})


def update_agent_metadata_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Update custom metadata for an agent.

    Task T078: Implement updateAgentMetadata Lambda handler

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        API Gateway response with updated metadata
    """
    try:
        agent_name = _get_path_param(event, "agent_name")
        if not agent_name:
            return _create_response(400, {"error": "agent_name is required"})

        body = _get_body(event)
        logger.info(f"Handling updateAgentMetadata request for '{agent_name}'")

        # Build metadata from body
        metadata = CustomAgentMetadata(
            agent_name=agent_name,
            version=body.get("version", "1.0.0"),
            input_schemas=body.get("input_schemas", []),
            output_schemas=body.get("output_schemas", []),
            consultation_requirements=body.get("consultation_requirements", []),
        )

        storage = get_metadata_storage()
        result = storage.put_metadata(metadata)

        return _create_response(200, result)

    except json.JSONDecodeError as e:
        return _create_response(400, {"error": f"Invalid JSON: {e}"})

    except ValidationError as e:
        return _create_response(400, {"error": str(e)})

    except ClientError:
        logger.exception("AWS service error updating metadata")
        return _create_response(503, {"error": "Service temporarily unavailable"})

    except Exception:
        logger.exception("Unexpected error updating metadata")
        return _create_response(500, {"error": "Internal server error"})


def get_consultation_requirements_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Get consultation requirements for an agent.

    Task T079: Implement getConsultationRequirements Lambda handler

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        API Gateway response with consultation requirements
    """
    try:
        agent_name = _get_path_param(event, "agent_name")
        if not agent_name:
            return _create_response(400, {"error": "agent_name is required"})

        logger.info(f"Handling getConsultationRequirements request for '{agent_name}'")

        registry = get_registry()
        requirements = registry.get_consultation_requirements(agent_name)

        return _create_response(
            200,
            {
                "agent_name": agent_name,
                "requirements": [r.model_dump() for r in requirements],
                "count": len(requirements),
            },
        )

    except AgentNotFoundError as e:
        return _create_response(404, {"error": str(e)})

    except ClientError:
        logger.exception("AWS service error getting consultation requirements")
        return _create_response(503, {"error": "Service temporarily unavailable"})

    except Exception:
        logger.exception("Unexpected error getting consultation requirements")
        return _create_response(500, {"error": "Internal server error"})


def check_compatibility_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Check compatibility between two agents.

    Task T080: Implement checkCompatibility Lambda handler

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        API Gateway response with compatibility result
    """
    try:
        body = _get_body(event)
        source_agent = body.get("source_agent")
        target_agent = body.get("target_agent")

        if not source_agent or not target_agent:
            return _create_response(400, {"error": "source_agent and target_agent are required"})

        logger.info(f"Handling checkCompatibility request: {source_agent} -> {target_agent}")

        registry = get_registry()
        result = registry.check_compatibility(source_agent, target_agent)

        return _create_response(200, result.model_dump())

    except json.JSONDecodeError as e:
        return _create_response(400, {"error": f"Invalid JSON: {e}"})

    except AgentNotFoundError as e:
        return _create_response(404, {"error": str(e)})

    except ClientError:
        logger.exception("AWS service error checking compatibility")
        return _create_response(503, {"error": "Service temporarily unavailable"})

    except Exception:
        logger.exception("Unexpected error checking compatibility")
        return _create_response(500, {"error": "Internal server error"})


def find_compatible_agents_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Find agents compatible with a given input type.

    Task T081: Implement findCompatibleAgents Lambda handler

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        API Gateway response with compatible agents
    """
    try:
        body = _get_body(event)
        input_type_str = body.get("input_type")

        if not input_type_str:
            return _create_response(400, {"error": "input_type is required"})

        # Parse semantic type
        try:
            input_type = SemanticType(input_type_str)
        except ValueError:
            return _create_response(400, {"error": f"Invalid input_type: {input_type_str}"})

        logger.info(f"Handling findCompatibleAgents request for type '{input_type}'")

        registry = get_registry()
        agents = registry.find_by_input_compatibility(input_type)

        return _create_response(
            200,
            {
                "input_type": input_type_str,
                "agents": [a.model_dump() for a in agents],
                "count": len(agents),
            },
        )

    except json.JSONDecodeError as e:
        return _create_response(400, {"error": f"Invalid JSON: {e}"})

    except ClientError:
        logger.exception("AWS service error finding compatible agents")
        return _create_response(503, {"error": "Service temporarily unavailable"})

    except Exception:
        logger.exception("Unexpected error finding compatible agents")
        return _create_response(500, {"error": "Internal server error"})


def get_agent_status_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Get the status of an agent.

    Task T082: Implement getAgentStatus Lambda handler

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        API Gateway response with agent status
    """
    try:
        agent_name = _get_path_param(event, "agent_name")
        if not agent_name:
            return _create_response(400, {"error": "agent_name is required"})

        logger.info(f"Handling getAgentStatus request for '{agent_name}'")

        storage = get_status_storage()
        status = storage.get_status(agent_name)

        return _create_response(200, status.model_dump())

    except AgentNotFoundError as e:
        return _create_response(404, {"error": str(e)})

    except ClientError:
        logger.exception("AWS service error getting agent status")
        return _create_response(503, {"error": "Service temporarily unavailable"})

    except Exception:
        logger.exception("Unexpected error getting agent status")
        return _create_response(500, {"error": "Internal server error"})


def update_agent_status_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Update the status of an agent.

    Task T083: Implement updateAgentStatus Lambda handler

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        API Gateway response with updated status
    """
    try:
        agent_name = _get_path_param(event, "agent_name")
        if not agent_name:
            return _create_response(400, {"error": "agent_name is required"})

        body = _get_body(event)
        logger.info(f"Handling updateAgentStatus request for '{agent_name}'")

        # Parse status values
        status = None
        if "status" in body:
            try:
                status = AgentStatusValue(body["status"])
            except ValueError:
                return _create_response(400, {"error": f"Invalid status: {body['status']}"})

        health_check = None
        if "health_check" in body:
            try:
                health_check = HealthCheckStatus(body["health_check"])
            except ValueError:
                return _create_response(
                    400, {"error": f"Invalid health_check: {body['health_check']}"}
                )

        storage = get_status_storage()
        updated = storage.update_status(
            agent_name=agent_name,
            status=status,
            health_check=health_check,
            endpoint=body.get("endpoint"),
            version=body.get("version"),
            metrics=body.get("metrics"),
            error_message=body.get("error_message"),
        )

        return _create_response(200, updated.model_dump())

    except json.JSONDecodeError as e:
        return _create_response(400, {"error": f"Invalid JSON: {e}"})

    except AgentNotFoundError as e:
        return _create_response(404, {"error": str(e)})

    except ClientError:
        logger.exception("AWS service error updating agent status")
        return _create_response(503, {"error": "Service temporarily unavailable"})

    except Exception:
        logger.exception("Unexpected error updating agent status")
        return _create_response(500, {"error": "Internal server error"})
