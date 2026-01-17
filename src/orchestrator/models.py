"""Orchestrator data models.

This module defines the data entities for the Policy Enforcement and Monitoring
components including:
- PolicyConfig model for Cedar policy configuration
- Alert models for iteration warnings
"""

from pydantic import BaseModel, Field


class PolicyConfig(BaseModel):
    """Configuration for Cedar policy enforcement.

    Maps to FR-002: Policy MUST support configurable iteration limits.
    Maps to FR-007: Policy enforces iteration limits using Cedar rules.

    Example:
        config = PolicyConfig(
            agent_name="test-runner-agent",
            max_iterations=100,
            session_id="loop-session-123",
        )
    """

    agent_name: str = Field(
        ...,
        description="Name of the agent subject to policy",
        min_length=1,
        max_length=64,
    )

    max_iterations: int = Field(
        ...,
        description="Maximum iterations allowed by policy",
        ge=1,
        le=10000,
    )

    session_id: str | None = Field(
        default=None,
        description="Optional loop session ID for policy context",
    )

    policy_engine_name: str = Field(
        default="LoopIterationPolicyEngine",
        description="Name of the Cedar policy engine",
    )

    policy_name_prefix: str = Field(
        default="iteration_limit",
        description="Prefix for policy names (alphanumeric and underscore only)",
    )

    def generate_cedar_statement(self, action: str = "iterate") -> str:
        """Generate Cedar policy statement for iteration limit enforcement.

        Maps to FR-007: Policy uses Cedar syntax to enforce iteration limits.

        Args:
            action: The action to control (default: "iterate")

        Returns:
            Cedar policy statement as string

        Example Cedar output:
            permit(
              principal,
              action == AgentCore::Action::"iterate",
              resource is AgentCore::Gateway
            ) when {
              context.current_iteration < context.max_iterations
            };
        """
        # Cedar policy statement with AgentCore resource type constraint
        return f"""permit(
  principal,
  action == AgentCore::Action::"{action}",
  resource is AgentCore::Gateway
) when {{
  context.current_iteration < context.max_iterations
}};"""
