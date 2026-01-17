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


# =============================================================================
# Loop Framework Exceptions (T017-T020)
# =============================================================================


class LoopFrameworkError(AgentFrameworkError):
    """Base exception for all loop framework errors.

    T017: Base exception class for the autonomous loop framework.
    All loop-specific exceptions should inherit from this class.
    """

    def __init__(self, message: str, session_id: str | None = None):
        self.session_id = session_id
        super().__init__(message)


class PolicyViolationError(LoopFrameworkError):
    """Raised when a loop iteration violates Policy rules.

    T018: Exception for Policy service violations, typically iteration limit exceeded.

    Maps to FR-002: Policy MUST support configurable iteration limits.
    Maps to FR-008: Agent MUST terminate when iteration limit reached.
    """

    def __init__(
        self,
        agent_name: str,
        current_iteration: int,
        max_iterations: int,
        session_id: str | None = None,
        policy_arn: str | None = None,
    ):
        self.agent_name = agent_name
        self.current_iteration = current_iteration
        self.max_iterations = max_iterations
        self.policy_arn = policy_arn
        super().__init__(
            f"Policy violation: Agent '{agent_name}' exceeded iteration limit "
            f"({current_iteration}/{max_iterations})",
            session_id=session_id,
        )


class CheckpointRecoveryError(LoopFrameworkError):
    """Raised when checkpoint recovery fails.

    T019: Exception for Memory service checkpoint recovery failures.

    Maps to FR-012: Support loading state from Memory for recovery.
    Maps to SC-006: Recovery within one iteration of checkpoint.
    """

    def __init__(
        self,
        checkpoint_id: str,
        reason: str,
        session_id: str | None = None,
    ):
        self.checkpoint_id = checkpoint_id
        self.reason = reason
        super().__init__(
            f"Checkpoint recovery failed for '{checkpoint_id}': {reason}",
            session_id=session_id,
        )


class ExitConditionEvaluationError(LoopFrameworkError):
    """Raised when exit condition evaluation fails.

    T020: Exception for verification tool failures during exit condition evaluation.

    Maps to FR-003: Framework MUST provide exit condition evaluation helpers.
    Maps to SC-002: Verification timeout of 30 seconds.
    """

    def __init__(
        self,
        condition_type: str,
        reason: str,
        tool_name: str | None = None,
        session_id: str | None = None,
        iteration: int | None = None,
    ):
        self.condition_type = condition_type
        self.reason = reason
        self.tool_name = tool_name
        self.iteration = iteration
        tool_info = f" (tool: {tool_name})" if tool_name else ""
        super().__init__(
            f"Exit condition '{condition_type}' evaluation failed{tool_info}: {reason}",
            session_id=session_id,
        )
