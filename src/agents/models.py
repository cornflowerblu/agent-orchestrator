"""Pydantic models for A2A Agent Cards and skills."""

from pydantic import BaseModel, Field


class Skill(BaseModel):
    """A named ability the agent can perform."""

    id: str = Field(
        ...,
        description="Unique skill identifier",
        pattern=r"^[a-z][a-z0-9-]{0,63}$",
    )
    name: str = Field(..., description="Human-readable skill name", min_length=3, max_length=100)
    description: str = Field(..., description="What this skill does", min_length=10, max_length=500)
    tags: list[str] = Field(
        default_factory=list,
        description="Categorization tags",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "requirements-gathering",
                    "name": "Requirements Gathering",
                    "description": "Gather and document user requirements and acceptance criteria",
                    "tags": ["requirements", "planning"],
                }
            ]
        }
    }


class AgentCapabilities(BaseModel):
    """Agent capabilities configuration."""

    streaming: bool = Field(..., description="Whether the agent supports streaming responses")


class AgentCard(BaseModel):
    """A2A Protocol Agent Card for agent discovery and capability advertisement."""

    name: str = Field(
        ...,
        description="Unique agent identifier",
        pattern=r"^[a-zA-Z][a-zA-Z0-9-]{0,63}$",
    )
    description: str = Field(
        ...,
        description="Human-readable description of the agent's purpose",
        min_length=10,
        max_length=500,
    )
    version: str = Field(
        ...,
        description="Semantic version of the agent definition",
        pattern=r"^\d+\.\d+\.\d+$",
    )
    url: str = Field(..., description="AgentCore Runtime invocation URL")
    protocol_version: str = Field(
        "0.3.0",
        alias="protocolVersion",
        description="A2A protocol version",
    )
    preferred_transport: str = Field(
        "JSONRPC",
        alias="preferredTransport",
        description="Transport mechanism for A2A communication",
    )
    capabilities: AgentCapabilities = Field(..., description="Agent capabilities")
    default_input_modes: list[str] = Field(
        ...,
        alias="defaultInputModes",
        description="Supported input modalities",
        min_length=1,
    )
    default_output_modes: list[str] = Field(
        ...,
        alias="defaultOutputModes",
        description="Supported output modalities",
        min_length=1,
    )
    skills: list[Skill] = Field(..., description="Skills the agent possesses")

    model_config = {
        "populate_by_name": True,  # Allow both snake_case and camelCase
        "json_schema_extra": {
            "examples": [
                {
                    "name": "requirements-agent",
                    "description": "Agent for gathering and documenting user requirements",
                    "version": "1.0.0",
                    "url": "https://bedrock-agentcore.us-east-1.amazonaws.com/runtimes/req-agent/invocations/",
                    "protocolVersion": "0.3.0",
                    "preferredTransport": "JSONRPC",
                    "capabilities": {"streaming": True},
                    "defaultInputModes": ["text"],
                    "defaultOutputModes": ["text"],
                    "skills": [
                        {
                            "id": "requirements-gathering",
                            "name": "Requirements Gathering",
                            "description": "Gather and document user requirements",
                            "tags": ["requirements"],
                        }
                    ],
                }
            ]
        },
    }
