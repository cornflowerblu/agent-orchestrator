"""Policy enforcement using AgentCore Policy service and Cedar.

This module provides PolicyEnforcer class for managing Cedar policies
that enforce iteration limits on autonomous agent loops.
"""

from typing import Any

try:
    from bedrock_agentcore_starter_toolkit.operations.policy.client import PolicyClient
except ImportError:
    # For testing and when SDK is not installed
    PolicyClient = None  # type: ignore[assignment]

from src.exceptions import PolicyViolationError
from src.orchestrator.models import PolicyConfig


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
                "policyEngineArn": "arn:aws:bedrock-agentcore:...:policy-engine/engine-123"
            }
        """
        engine_name = self.config.policy_engine_name

        # Check cache
        if engine_name in self._policy_engine_cache:
            cached_result: dict[str, Any] = self._policy_engine_cache[engine_name]
            return cached_result

        # Create or get policy engine using AgentCore Policy service
        result: dict[str, Any] = self.policy_client.create_or_get_policy_engine(
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
            return str(self._policy_cache[policy_name]["policyArn"])

        # Generate Cedar statement
        cedar_statement: str = self.config.generate_cedar_statement()

        # Create policy using AgentCore Policy service
        result: dict[str, Any] = self.policy_client.create_or_get_policy(
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
        return str(result["policyArn"])

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

    def update_policy(
        self,
        new_config: PolicyConfig,
        policy_id: str,
    ) -> str:
        """Update an existing policy with new configuration.

        Args:
            new_config: New PolicyConfig with updated iteration limits
            policy_id: ID of the policy to update

        Returns:
            Updated policy ARN

        Example:
            enforcer = PolicyEnforcer(config)
            new_config = PolicyConfig(agent_name="test-agent", max_iterations=200)
            policy_arn = enforcer.update_policy(new_config=new_config, policy_id="policy-456")
        """
        # Generate new Cedar statement with updated config
        cedar_statement = new_config.generate_cedar_statement()

        # Update policy using AgentCore Policy service
        result = self.policy_client.update_policy(
            policy_id=policy_id,
            definition={
                "cedar": {
                    "statement": cedar_statement,
                }
            },
        )

        # Update cache
        policy_name = f"{new_config.policy_name_prefix}-{new_config.agent_name}"
        if new_config.session_id:
            policy_name += f"-{new_config.session_id}"
        self._policy_cache[policy_name] = result

        return str(result["policyArn"])

    def get_policy(self, policy_id: str) -> dict[str, Any]:
        """Retrieve an existing policy by ID.

        Args:
            policy_id: ID of the policy to retrieve

        Returns:
            Policy details including ID, ARN, name, and definition

        Example:
            enforcer = PolicyEnforcer(config)
            policy = enforcer.get_policy(policy_id="policy-456")
            print(policy["name"])  # "iteration-limit-test-agent"
        """
        # Get policy using AgentCore Policy service
        result: dict[str, Any] = self.policy_client.get_policy(policy_id=policy_id)
        return result
