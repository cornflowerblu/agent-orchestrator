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

    def _execute_command_with_timeout(self, command: str) -> dict:
        """Execute shell command via Code Interpreter with timeout (T051).

        Enforces timeout per SC-002 (30s default).
        Uses execute_command for shell commands (not execute_code which runs Python).

        Args:
            command: Shell command to execute

        Returns:
            Result dictionary with exit_code and output

        Raises:
            TimeoutError: If execution exceeds timeout
        """
        import concurrent.futures

        def _run_command() -> dict:
            """Execute command and parse streaming response."""
            result = self.code_interpreter.execute_command(command)

            # Parse streaming response
            exit_code = 1
            output = ""

            if result.get("stream"):
                for event in result["stream"]:
                    if "result" in event:
                        structured = event["result"].get("structuredContent", {})
                        exit_code = structured.get("exitCode", 1)
                        stdout = structured.get("stdout", "")
                        stderr = structured.get("stderr", "")
                        output = stdout if stdout else stderr

            return {"exit_code": exit_code, "output": output}

        # Use ThreadPoolExecutor for timeout enforcement
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_run_command)

            try:
                return future.result(timeout=self.timeout_seconds)
            except concurrent.futures.TimeoutError as e:
                error_msg = f"Code execution timeout after {self.timeout_seconds}s"
                logger.warning(error_msg)
                # Cancel the future
                future.cancel()
                raise TimeoutError(error_msg) from e

    def evaluate_tests(self, config: ExitConditionConfig, iteration: int) -> ExitConditionStatus:
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

            # Execute via Code Interpreter with timeout
            result = self._execute_command_with_timeout(pytest_cmd)

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

    def evaluate_linting(self, config: ExitConditionConfig, iteration: int) -> ExitConditionStatus:
        """Evaluate LINTING_CLEAN exit condition (T044).

        Executes ruff check via Code Interpreter and checks exit code.

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
            # Build ruff command
            path = config.tool_arguments.get("path", ".")
            ruff_cmd = f"ruff check {path}"

            logger.debug(f"Evaluating linting with command: {ruff_cmd}")

            # Execute via Code Interpreter with timeout
            result = self._execute_command_with_timeout(ruff_cmd)

            exit_code = result.get("exit_code", 1)
            output = result.get("output", "")

            # Mark status based on exit code
            if exit_code == 0:
                status.mark_met(
                    tool_name="ruff",
                    exit_code=exit_code,
                    output=output,
                    iteration=iteration,
                )
                logger.info(f"Linting passed at iteration {iteration}")
            else:
                status.mark_not_met(
                    tool_name="ruff",
                    exit_code=exit_code,
                    output=output,
                    iteration=iteration,
                )
                logger.warning(f"Linting failed at iteration {iteration}: exit code {exit_code}")

        except Exception as e:
            error_msg = f"Failed to execute ruff: {e}"
            logger.exception(error_msg)
            status.mark_error(error=error_msg, iteration=iteration)

        return status

    def evaluate_build(self, config: ExitConditionConfig, iteration: int) -> ExitConditionStatus:
        """Evaluate BUILD_SUCCEEDS exit condition (T045).

        Executes build command via Code Interpreter and checks exit code.

        Args:
            config: Exit condition configuration
            iteration: Current iteration number

        Returns:
            ExitConditionStatus with evaluation result
        """
        status = ExitConditionStatus(type=config.type)

        try:
            # Build command (default to common Python build)
            build_cmd = config.tool_arguments.get("command", "python -m build")

            logger.debug(f"Evaluating build with command: {build_cmd}")

            # Execute via Code Interpreter with timeout
            result = self._execute_command_with_timeout(build_cmd)

            exit_code = result.get("exit_code", 1)
            output = result.get("output", "")

            # Mark status based on exit code
            if exit_code == 0:
                status.mark_met(
                    tool_name="build",
                    exit_code=exit_code,
                    output=output,
                    iteration=iteration,
                )
                logger.info(f"Build succeeded at iteration {iteration}")
            else:
                status.mark_not_met(
                    tool_name="build",
                    exit_code=exit_code,
                    output=output,
                    iteration=iteration,
                )
                logger.warning(f"Build failed at iteration {iteration}: exit code {exit_code}")

        except Exception as e:
            error_msg = f"Failed to execute build: {e}"
            logger.exception(error_msg)
            status.mark_error(error=error_msg, iteration=iteration)

        return status

    def evaluate_security_scan(
        self, config: ExitConditionConfig, iteration: int
    ) -> ExitConditionStatus:
        """Evaluate SECURITY_SCAN_CLEAN exit condition (T046).

        Executes security scanner via Code Interpreter and checks exit code.

        Args:
            config: Exit condition configuration
            iteration: Current iteration number

        Returns:
            ExitConditionStatus with evaluation result
        """
        status = ExitConditionStatus(type=config.type)

        try:
            # Security scan command (default to bandit for Python)
            scan_cmd = config.tool_arguments.get("command", "bandit -r .")

            logger.debug(f"Evaluating security with command: {scan_cmd}")

            # Execute via Code Interpreter with timeout
            result = self._execute_command_with_timeout(scan_cmd)

            exit_code = result.get("exit_code", 1)
            output = result.get("output", "")

            # Mark status based on exit code
            if exit_code == 0:
                status.mark_met(
                    tool_name="security-scanner",
                    exit_code=exit_code,
                    output=output,
                    iteration=iteration,
                )
                logger.info(f"Security scan clean at iteration {iteration}")
            else:
                status.mark_not_met(
                    tool_name="security-scanner",
                    exit_code=exit_code,
                    output=output,
                    iteration=iteration,
                )
                logger.warning(
                    f"Security scan found issues at iteration {iteration}: exit code {exit_code}"
                )

        except Exception as e:
            error_msg = f"Failed to execute security scan: {e}"
            logger.exception(error_msg)
            status.mark_error(error=error_msg, iteration=iteration)

        return status

    def evaluate_custom(self, config: ExitConditionConfig, iteration: int) -> ExitConditionStatus:
        """Evaluate CUSTOM exit condition (T047).

        Imports and executes user-provided custom evaluator function.

        Args:
            config: Exit condition configuration (must have custom_evaluator set)
            iteration: Current iteration number

        Returns:
            ExitConditionStatus with evaluation result

        Raises:
            ExitConditionEvaluationError: If custom evaluator is not configured
        """
        status = ExitConditionStatus(type=config.type)

        if not config.custom_evaluator:
            error_msg = "CUSTOM exit condition requires custom_evaluator to be set"
            logger.error(error_msg)
            status.mark_error(error=error_msg, iteration=iteration)
            return status

        try:
            # Import custom evaluator function
            module_path, func_name = config.custom_evaluator.rsplit(".", 1)

            logger.debug(f"Importing custom evaluator: {config.custom_evaluator}")

            # Dynamic import
            import importlib

            module = importlib.import_module(module_path)
            evaluator_func = getattr(module, func_name)

            # Execute custom evaluator
            # Custom evaluator should return dict with 'passed' boolean and optional 'output'
            result = evaluator_func(config.tool_arguments)

            passed = result.get("passed", False)
            output = result.get("output", "Custom evaluator executed")

            # Mark status based on result
            if passed:
                status.mark_met(
                    tool_name="custom-evaluator",
                    exit_code=0,
                    output=output,
                    iteration=iteration,
                )
                logger.info(f"Custom condition met at iteration {iteration}")
            else:
                status.mark_not_met(
                    tool_name="custom-evaluator",
                    exit_code=1,
                    output=output,
                    iteration=iteration,
                )
                logger.warning(f"Custom condition not met at iteration {iteration}")

        except Exception as e:
            error_msg = f"Failed to execute custom evaluator: {e}"
            logger.exception(error_msg)
            status.mark_error(error=error_msg, iteration=iteration)

        return status

    def evaluate(self, config: ExitConditionConfig, iteration: int) -> ExitConditionStatus:
        """Evaluate an exit condition based on its type (T048).

        Dispatcher method that routes to the appropriate evaluation method.

        Args:
            config: Exit condition configuration
            iteration: Current iteration number

        Returns:
            ExitConditionStatus with evaluation result

        Raises:
            ExitConditionEvaluationError: If condition type is not supported
        """
        from src.loop.models import ExitConditionType

        logger.info(f"Evaluating exit condition: {config.type} (iteration {iteration})")

        # Route to appropriate evaluation method
        if config.type == ExitConditionType.ALL_TESTS_PASS:
            return self.evaluate_tests(config, iteration)
        if config.type == ExitConditionType.LINTING_CLEAN:
            return self.evaluate_linting(config, iteration)
        if config.type == ExitConditionType.BUILD_SUCCEEDS:
            return self.evaluate_build(config, iteration)
        if config.type == ExitConditionType.SECURITY_SCAN_CLEAN:
            return self.evaluate_security_scan(config, iteration)
        if config.type == ExitConditionType.CUSTOM:
            return self.evaluate_custom(config, iteration)
        error_msg = f"Unsupported exit condition type: {config.type}"
        logger.error(error_msg)
        status = ExitConditionStatus(type=config.type)
        status.mark_error(error=error_msg, iteration=iteration)
        return status
