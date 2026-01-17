"""Custom exception classes for the agent framework."""


class AgentFrameworkError(Exception):
    """Base exception for all agent framework errors."""


class AgentNotFoundError(AgentFrameworkError):
    """Raised when an agent is not found in the registry."""

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        super().__init__(f"Agent '{agent_name}' not found")


class ValidationError(AgentFrameworkError):
    """Raised when validation fails for agent inputs, outputs, or metadata."""

    def __init__(self, message: str, details: dict | None = None):
        self.details = details or {}
        super().__init__(message)


class ConsultationRequiredError(AgentFrameworkError):
    """Raised when required agent consultation is missing or incomplete."""

    def __init__(self, agent_name: str, required_consultation: str, phase: str):
        self.agent_name = agent_name
        self.required_consultation = required_consultation
        self.phase = phase
        super().__init__(
            f"Agent '{agent_name}' requires consultation with '{required_consultation}' "
            f"during phase '{phase}'"
        )


class DuplicateAgentError(AgentFrameworkError):
    """Raised when attempting to deploy an agent with a duplicate name."""

    def __init__(self, agent_name: str, existing_version: str | None = None):
        self.agent_name = agent_name
        self.existing_version = existing_version
        if existing_version:
            msg = f"Agent '{agent_name}' already deployed (version {existing_version})"
        else:
            msg = f"Agent '{agent_name}' already exists"
        super().__init__(msg)


class ToolUnavailableError(AgentFrameworkError):
    """Raised when a Gateway tool is unavailable or fails to execute."""

    def __init__(self, tool_name: str, reason: str):
        self.tool_name = tool_name
        self.reason = reason
        super().__init__(f"Tool '{tool_name}' unavailable: {reason}")


class IncompatibleTypeError(ValidationError):
    """Raised when semantic types are incompatible between agents."""

    def __init__(self, output_type: str, input_type: str):
        self.output_type = output_type
        self.input_type = input_type
        super().__init__(
            f"Incompatible types: output '{output_type}' cannot be used as input '{input_type}'"
        )
