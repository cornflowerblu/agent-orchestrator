"""Policy enforcement using AgentCore Policy service and Cedar.

This module provides PolicyEnforcer class for managing Cedar policies
that enforce iteration limits on autonomous agent loops.
"""

from typing import Any

try:
    from bedrock_agentcore_starter_toolkit.operations.policy.client import PolicyClient
except ImportError:
    # For testing and when SDK is not installed
    PolicyClient = None  # type: ignore

from src.orchestrator.models import PolicyConfig
from src.exceptions import PolicyViolationError


class PolicyEnforcer:
    """Enforces iteration limits using AgentCore Policy service with Cedar.

    Maps to FR-002: Policy MUST support configurable iteration limits.
    Maps to FR-007: Policy uses Cedar syntax to enforce iteration limits.
    Maps to FR-008: Agent MUST terminate when iteration limit reached.

    Example:
        config = PolicyConfig(
            agent_name="test-agent",
            max_iterations=100,
        )
        enforcer = PolicyEnforcer(config=config)
        policy_arn = enforcer.create_iteration_policy()

        # Before each iteration:
        is_allowed = enforcer.check_iteration_allowed(
            current_iteration=5,
            session_id="session-123"
        )
    """

    def __init__(self, config: PolicyConfig, region: str = "us-east-1"):
        """Initialize PolicyEnforcer.

        Args:
            config: Policy configuration with iteration limits
            region: AWS region for Policy service (default: us-east-1)
        """
        self.config = config
        self.region = region

        # Initialize Policy client
        if PolicyClient is not None:
            self.policy_client = PolicyClient(region_name=region)
        else:
            self.policy_client = None  # For testing when SDK is not available

        # Cache for policy engine and policy ARNs
        self._policy_engine_cache: dict[str, Any] = {}
        self._policy_cache: dict[str, Any] = {}

    def _get_or_create_policy_engine(self) -> dict[str, Any]:
        """Get or create a Cedar policy engine.

        Returns:
            Dictionary with policyEngineId and policyEngineArn

        Example response:
            {
                "policyEngineId": "engine-123",
                "policyEngineArn": "arn:aws:bedrock-agentcore:us-east-1:123456789:policy-engine/engine-123"
            }
        """
        engine_name = self.config.policy_engine_name

        # Check cache
        if engine_name in self._policy_engine_cache:
            return self._policy_engine_cache[engine_name]

        # Create or get policy engine using AgentCore Policy service
        result = self.policy_client.create_or_get_policy_engine(
            name=engine_name,
            description=f"Enforces iteration limits for {self.config.agent_name}",
        )

        # Cache the result
        self._policy_engine_cache[engine_name] = result
        return result

    def create_iteration_policy(self) -> str:
        """Create a Cedar policy for iteration limit enforcement.

        Maps to FR-007: Policy uses Cedar syntax to enforce iteration limits.

        Returns:
            Policy ARN

        Example:
            enforcer = PolicyEnforcer(config)
            policy_arn = enforcer.create_iteration_policy()
            # Returns: "arn:aws:bedrock-agentcore:us-east-1:123456789:policy/policy-456"
        """
        # Get or create policy engine
        engine = self._get_or_create_policy_engine()
        engine_id = engine["policyEngineId"]

        # Generate policy name
        policy_name = f"{self.config.policy_name_prefix}-{self.config.agent_name}"
        if self.config.session_id:
            policy_name += f"-{self.config.session_id}"

        # Check cache
        if policy_name in self._policy_cache:
            return self._policy_cache[policy_name]["policyArn"]

        # Generate Cedar statement
        cedar_statement = self.config.generate_cedar_statement()

        # Create policy using AgentCore Policy service
        result = self.policy_client.create_or_get_policy(
            policy_engine_id=engine_id,
            name=policy_name,
            description=f"Iteration limit policy for {self.config.agent_name}",
            definition={
                "cedar": {
                    "statement": cedar_statement,
                }
            },
        )

        # Cache the result
        self._policy_cache[policy_name] = result
        return result["policyArn"]

    def check_iteration_allowed(
        self,
        current_iteration: int,
        session_id: str | None = None,
    ) -> bool:
        """Check if the current iteration is allowed by policy.

        Maps to FR-008: Agent MUST terminate when iteration limit reached.

        Args:
            current_iteration: Current iteration number (0-indexed)
            session_id: Optional session ID for context

        Returns:
            True if iteration is allowed

        Raises:
            PolicyViolationError: If policy denies the iteration (limit exceeded)

        Example:
            enforcer = PolicyEnforcer(config)
            try:
                enforcer.check_iteration_allowed(current_iteration=99, session_id="session-123")
                # Continue with iteration
            except PolicyViolationError as e:
                # Handle policy violation
                print(f"Iteration limit exceeded: {e}")
        """
        # Get or create policy engine
        engine = self._get_or_create_policy_engine()

        # Evaluate policy using AgentCore Policy service
        decision = self.policy_client.evaluate(
            principal=self.config.agent_name,
            action="iterate",
            resource=session_id or "loop",
            context={
                "current_iteration": current_iteration,
                "max_iterations": self.config.max_iterations,
            },
        )

        # If policy denies, raise PolicyViolationError
        if decision != "ALLOW":
            raise PolicyViolationError(
                agent_name=self.config.agent_name,
                current_iteration=current_iteration,
                max_iterations=self.config.max_iterations,
                session_id=session_id,
                policy_arn=engine.get("policyEngineArn"),
            )

        return True
