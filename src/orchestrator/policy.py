"""Policy enforcement using AgentCore Policy service and Cedar.

This module provides PolicyEnforcer class for managing Cedar policies
that enforce iteration limits on autonomous agent loops.

AgentCore Policy evaluates Cedar policies automatically at the Gateway level
when tools are invoked. For iteration limit enforcement, we:
1. Create Cedar policies that can be attached to Gateways
2. Perform local iteration checks for immediate enforcement
3. Policy definitions serve as auditable documentation and Gateway integration

Maps to FR-002: Policy MUST support configurable iteration limits.
Maps to FR-007: Policy uses Cedar syntax to enforce iteration limits.
Maps to FR-008: Agent MUST terminate when iteration limit reached.
"""

import logging
import re
from typing import Any

try:
    from bedrock_agentcore_starter_toolkit.operations.policy.client import PolicyClient
except ImportError:
    # For testing and when SDK is not installed
    PolicyClient = None  # type: ignore[assignment]

from src.exceptions import PolicyViolationError
from src.orchestrator.models import PolicyConfig

logger = logging.getLogger(__name__)


class PolicyEnforcer:
    """Enforces iteration limits using AgentCore Policy service with Cedar.

    The PolicyEnforcer provides:
    1. Local iteration limit checks (immediate enforcement)
    2. Cedar policy creation for Gateway-level enforcement
    3. Policy management (create, update, retrieve)

    AgentCore Policy evaluates policies at Gateway tool invocation time.
    For standalone iteration checking, we use local enforcement while
    maintaining Cedar policies for audit and Gateway integration.

    Example:
        config = PolicyConfig(
            agent_name="test-agent",
            max_iterations=100,
        )
        enforcer = PolicyEnforcer(config=config)

        # Create Cedar policy (for Gateway integration)
        policy_arn = enforcer.create_iteration_policy()

        # Check iteration (local enforcement)
        try:
            enforcer.check_iteration_allowed(current_iteration=5, session_id="session-123")
        except PolicyViolationError:
            print("Iteration limit exceeded!")
    """

    def __init__(self, config: PolicyConfig, region: str = "us-east-1"):
        """Initialize PolicyEnforcer.

        Args:
            config: Policy configuration with iteration limits
            region: AWS region for Policy service (default: us-east-1)
        """
        self.config = config
        self.region = region

        # Initialize Policy client (lazy - created on first use)
        self._policy_client: PolicyClient | None = None

        # Cache for policy engine and policy ARNs
        self._policy_engine_cache: dict[str, Any] = {}
        self._policy_cache: dict[str, Any] = {}

        logger.info(
            f"Initialized PolicyEnforcer for {config.agent_name} "
            f"with max_iterations={config.max_iterations}"
        )

    @property
    def policy_client(self) -> PolicyClient | None:
        """Get or create the Policy client (lazy initialization).

        Returns:
            PolicyClient instance or None if SDK not available
        """
        if self._policy_client is None and PolicyClient is not None:
            try:
                self._policy_client = PolicyClient(region_name=self.region)
                logger.debug(f"Created PolicyClient for region {self.region}")
            except Exception as e:
                logger.warning(f"Failed to create PolicyClient: {e}")
                self._policy_client = None
        return self._policy_client

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

        Note: AgentCore Policy evaluates tool-specific actions at Gateway level.
        Iteration limits are enforced locally via check_iteration_allowed().
        This method creates a policy that can be used for audit/documentation
        or extended for tool-specific Gateway policies.

        Returns:
            Policy ARN (or simulated ARN if PolicyClient unavailable)

        Example:
            enforcer = PolicyEnforcer(config)
            policy_arn = enforcer.create_iteration_policy()
        """
        # Generate policy name (must match ^[A-Za-z][A-Za-z0-9_]*$)
        sanitized_agent = re.sub(r"[^A-Za-z0-9]", "_", self.config.agent_name)
        policy_name = f"{self.config.policy_name_prefix}_{sanitized_agent}"
        if self.config.session_id:
            sanitized_session = re.sub(r"[^A-Za-z0-9]", "_", self.config.session_id)
            policy_name += f"_{sanitized_session}"

        # Check cache
        if policy_name in self._policy_cache:
            return str(self._policy_cache[policy_name]["policyArn"])

        # If PolicyClient not available, return simulated ARN
        if self.policy_client is None:
            simulated_arn = f"arn:aws:bedrock-agentcore:{self.region}:local:policy/{policy_name}"
            self._policy_cache[policy_name] = {"policyArn": simulated_arn}
            logger.info(f"PolicyClient not available, using simulated ARN: {simulated_arn}")
            return simulated_arn

        # Get or create policy engine
        engine = self._get_or_create_policy_engine()
        engine_id = engine["policyEngineId"]

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

        This performs local iteration limit enforcement. The Cedar policy
        (created via create_iteration_policy) can be attached to a Gateway
        for tool-level enforcement.

        Args:
            current_iteration: Current iteration number (0-indexed)
            session_id: Optional session ID for context

        Returns:
            True if iteration is allowed

        Raises:
            PolicyViolationError: If iteration limit exceeded

        Example:
            enforcer = PolicyEnforcer(config)
            try:
                enforcer.check_iteration_allowed(current_iteration=99, session_id="session-123")
                # Continue with iteration
            except PolicyViolationError as e:
                # Handle policy violation
                print(f"Iteration limit exceeded: {e}")
        """
        # Local enforcement: check if current iteration exceeds limit
        # Note: current_iteration is 0-indexed, max_iterations is the count
        if current_iteration >= self.config.max_iterations:
            logger.warning(
                f"Iteration limit reached: {current_iteration} >= {self.config.max_iterations} "
                f"for agent {self.config.agent_name}"
            )
            raise PolicyViolationError(
                agent_name=self.config.agent_name,
                current_iteration=current_iteration,
                max_iterations=self.config.max_iterations,
                session_id=session_id,
                policy_arn=self._policy_cache.get(
                    f"{self.config.policy_name_prefix}-{self.config.agent_name}", {}
                ).get("policyArn"),
            )

        logger.debug(
            f"Iteration {current_iteration}/{self.config.max_iterations} allowed "
            f"for agent {self.config.agent_name}"
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
