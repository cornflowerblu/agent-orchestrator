"""Exit condition evaluation using Gateway and Code Interpreter.

This module provides the ExitConditionEvaluator class for evaluating exit conditions
during autonomous loop execution. It integrates with:
- AgentCore Code Interpreter for verification tool execution (pytest, ruff, etc.)
- AgentCore Gateway for MCP tool discovery and invocation
- OpenTelemetry for tracing evaluation attempts

Maps to FR-003: Framework MUST provide exit condition evaluation helpers.
Maps to FR-004: Support standard exit conditions (tests, build, linting, security).
Maps to SC-002: Verification timeout of 30 seconds per tool.
"""

import logging

from bedrock_agentcore.tools.code_interpreter_client import CodeInterpreter

from src.gateway.tools import GatewayClient
from src.loop.models import (
    ExitConditionConfig,
    ExitConditionStatus,
)

logger = logging.getLogger(__name__)


class ExitConditionEvaluator:
    """Evaluates exit conditions using verification tools.

    T041: ExitConditionEvaluator class skeleton.

    This class provides methods to evaluate different types of exit conditions:
    - ALL_TESTS_PASS: Run pytest and check exit code
    - LINTING_CLEAN: Run ruff check and verify no errors
    - BUILD_SUCCEEDS: Run build command and check success
    - SECURITY_SCAN_CLEAN: Run security scanner and verify no issues
    - CUSTOM: Execute user-provided evaluation function

    Example:
        evaluator = ExitConditionEvaluator(region="us-east-1")
        config = ExitConditionConfig(type=ExitConditionType.ALL_TESTS_PASS)
        status = evaluator.evaluate(config, iteration=1)
        if status.status == ExitConditionStatusValue.MET:
            print("Tests passed!")
    """

    def __init__(
        self,
        region: str,
        gateway_url: str | None = None,
        timeout_seconds: int = 30,
    ):
        """Initialize exit condition evaluator.

        Args:
            region: AWS region for Code Interpreter and Gateway
            gateway_url: Optional Gateway URL for MCP tool discovery
            timeout_seconds: Timeout per tool invocation (default 30s per SC-002)
        """
        self.region = region
        self.gateway_url = gateway_url
        self.timeout_seconds = timeout_seconds

        # Lazy initialization - clients created on first use
        self._code_interpreter: CodeInterpreter | None = None
        self._gateway_client: GatewayClient | None = None

        logger.info(
            f"Initialized ExitConditionEvaluator for region {region} "
            f"with {timeout_seconds}s timeout"
        )

    @property
    def code_interpreter(self) -> CodeInterpreter:
        """Get or create Code Interpreter client (T042).

        Lazy initialization to avoid creating sessions until needed.

        Returns:
            CodeInterpreter client instance
        """
        if self._code_interpreter is None:
            logger.debug(f"Creating Code Interpreter client for region {self.region}")
            self._code_interpreter = CodeInterpreter(
                region=self.region, integration_source="agent-orchestrator"
            )
        return self._code_interpreter

    @property
    def gateway_client(self) -> GatewayClient:
        """Get or create Gateway client (T042).

        Lazy initialization to avoid creating connections until needed.

        Returns:
            GatewayClient instance

        Raises:
            ValueError: If gateway_url was not provided during initialization
        """
        if self._gateway_client is None:
            if not self.gateway_url:
                raise ValueError("Gateway URL must be provided to use gateway_client")
            logger.debug(f"Creating Gateway client for {self.gateway_url}")
            self._gateway_client = GatewayClient(gateway_url=self.gateway_url)
        return self._gateway_client

    def evaluate_tests(
        self, config: ExitConditionConfig, iteration: int
    ) -> ExitConditionStatus:
        """Evaluate ALL_TESTS_PASS exit condition (T043).

        Executes pytest via Code Interpreter and checks exit code.

        Args:
            config: Exit condition configuration
            iteration: Current iteration number

        Returns:
            ExitConditionStatus with evaluation result

        Raises:
            ExitConditionEvaluationError: If tool execution fails
        """
        status = ExitConditionStatus(type=config.type)

        try:
            # Build pytest command
            path = config.tool_arguments.get("path", "tests/")
            markers = config.tool_arguments.get("markers", "")

            cmd_parts = ["pytest", path]
            if markers:
                cmd_parts.extend(["-m", f'"{markers}"'])

            pytest_cmd = " ".join(cmd_parts)

            logger.debug(f"Evaluating tests with command: {pytest_cmd}")

            # Execute via Code Interpreter
            result = self.code_interpreter.execute_code(pytest_cmd)

            exit_code = result.get("exit_code", 1)
            output = result.get("output", "")

            # Mark status based on exit code
            if exit_code == 0:
                status.mark_met(
                    tool_name="pytest",
                    exit_code=exit_code,
                    output=output,
                    iteration=iteration,
                )
                logger.info(f"Tests passed at iteration {iteration}")
            else:
                status.mark_not_met(
                    tool_name="pytest",
                    exit_code=exit_code,
                    output=output,
                    iteration=iteration,
                )
                logger.warning(f"Tests failed at iteration {iteration}: exit code {exit_code}")

        except Exception as e:
            error_msg = f"Failed to execute pytest: {e}"
            logger.exception(error_msg)
            status.mark_error(error=error_msg, iteration=iteration)

        return status
