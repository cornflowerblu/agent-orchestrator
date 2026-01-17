"""Unit tests for exit condition evaluation (T054-T057)."""

from bedrock_agentcore.tools.code_interpreter_client import CodeInterpreter

from src.gateway.tools import GatewayClient
from src.loop.conditions import ExitConditionEvaluator
from src.loop.models import (
    ExitConditionConfig,
    ExitConditionStatus,
    ExitConditionStatusValue,
    ExitConditionType,
)


def create_streaming_response(exit_code: int, stdout: str, stderr: str = "") -> dict:
    """Create a mock streaming response for Code Interpreter execute_command.

    Args:
        exit_code: Command exit code
        stdout: Standard output
        stderr: Standard error

    Returns:
        Mock response dict with stream iterator
    """

    def stream_iter():
        yield {
            "result": {
                "content": [{"type": "text", "text": stdout or stderr}],
                "structuredContent": {
                    "stdout": stdout,
                    "stderr": stderr,
                    "exitCode": exit_code,
                    "executionTime": 0.1,
                },
                "isError": exit_code != 0,
            }
        }

    return {"stream": stream_iter()}


class TestExitConditionEvaluator:
    """Test ExitConditionEvaluator class (T054)."""

    def test_evaluator_initialization(self):
        """Should initialize evaluator with region and optional gateway URL."""
        evaluator = ExitConditionEvaluator(region="us-east-1")

        assert evaluator.region == "us-east-1"
        assert evaluator.gateway_url is None
        assert evaluator.timeout_seconds == 30  # Default from SC-002

    def test_evaluator_with_custom_timeout(self):
        """Should allow custom timeout configuration."""
        evaluator = ExitConditionEvaluator(region="us-east-1", timeout_seconds=60)

        assert evaluator.timeout_seconds == 60

    def test_evaluator_with_gateway_url(self):
        """Should initialize with custom Gateway URL."""
        evaluator = ExitConditionEvaluator(
            region="us-east-1", gateway_url="https://test-gateway.com"
        )

        assert evaluator.gateway_url == "https://test-gateway.com"

    def test_code_interpreter_initialization(self):
        """Should lazily initialize Code Interpreter client (T042)."""
        evaluator = ExitConditionEvaluator(region="us-east-1")

        # Should be None until first use
        assert evaluator._code_interpreter is None

        # Access code_interpreter property
        code_interpreter = evaluator.code_interpreter

        # Should now be initialized
        assert code_interpreter is not None
        assert evaluator._code_interpreter is not None
        assert isinstance(evaluator._code_interpreter, CodeInterpreter)

    def test_gateway_client_initialization(self):
        """Should lazily initialize Gateway client when URL provided."""
        evaluator = ExitConditionEvaluator(
            region="us-east-1", gateway_url="https://test-gateway.com"
        )

        # Should be None until first use
        assert evaluator._gateway_client is None

        # Access gateway_client property
        gateway_client = evaluator.gateway_client

        # Should now be initialized
        assert gateway_client is not None
        assert evaluator._gateway_client is not None
        assert isinstance(evaluator._gateway_client, GatewayClient)


class TestEvaluateTests:
    """Test evaluate_tests() method (T055)."""

    def test_evaluate_tests_success(self, mocker):
        """Should mark condition as MET when tests pass."""
        evaluator = ExitConditionEvaluator(region="us-east-1")
        config = ExitConditionConfig(
            type=ExitConditionType.ALL_TESTS_PASS,
            tool_arguments={"path": "tests/"},
        )

        # Mock Code Interpreter with streaming response
        mock_code_interpreter = mocker.Mock()
        mock_code_interpreter.execute_command.return_value = create_streaming_response(
            exit_code=0, stdout="===== 15 passed in 2.3s ====="
        )
        evaluator._code_interpreter = mock_code_interpreter

        status = evaluator.evaluate_tests(config, iteration=1)

        # Verify status is MET
        assert status.status == ExitConditionStatusValue.MET
        assert status.tool_exit_code == 0
        assert "passed" in status.tool_output.lower()
        assert status.iteration_evaluated == 1

        # Verify Code Interpreter was called
        mock_code_interpreter.execute_command.assert_called_once()

    def test_evaluate_tests_failure(self, mocker):
        """Should mark condition as NOT_MET when tests fail."""
        evaluator = ExitConditionEvaluator(region="us-east-1")
        config = ExitConditionConfig(type=ExitConditionType.ALL_TESTS_PASS)

        # Mock Code Interpreter with streaming response
        mock_code_interpreter = mocker.Mock()
        mock_code_interpreter.execute_command.return_value = create_streaming_response(
            exit_code=1, stdout="===== 3 failed, 12 passed in 2.5s ====="
        )
        evaluator._code_interpreter = mock_code_interpreter

        status = evaluator.evaluate_tests(config, iteration=2)

        # Verify status is NOT_MET
        assert status.status == ExitConditionStatusValue.NOT_MET
        assert status.tool_exit_code == 1
        assert "failed" in status.tool_output.lower()
        assert status.iteration_evaluated == 2

    def test_evaluate_tests_with_custom_arguments(self, mocker):
        """Should pass custom arguments to pytest."""
        evaluator = ExitConditionEvaluator(region="us-east-1")
        config = ExitConditionConfig(
            type=ExitConditionType.ALL_TESTS_PASS,
            tool_arguments={"path": "tests/unit", "markers": "not integration"},
        )

        # Mock Code Interpreter with streaming response
        mock_code_interpreter = mocker.Mock()
        mock_code_interpreter.execute_command.return_value = create_streaming_response(
            exit_code=0, stdout="10 passed"
        )
        evaluator._code_interpreter = mock_code_interpreter

        evaluator.evaluate_tests(config, iteration=1)

        # Verify custom arguments were included
        call_args = mock_code_interpreter.execute_command.call_args[0][0]
        assert "tests/unit" in call_args
        assert "not integration" in call_args


class TestEvaluateLinting:
    """Test evaluate_linting() method (T056)."""

    def test_evaluate_linting_success(self, mocker):
        """Should mark condition as MET when linting passes."""
        evaluator = ExitConditionEvaluator(region="us-east-1")
        config = ExitConditionConfig(
            type=ExitConditionType.LINTING_CLEAN,
            tool_arguments={"path": "src/"},
        )

        # Mock Code Interpreter with streaming response
        mock_code_interpreter = mocker.Mock()
        mock_code_interpreter.execute_command.return_value = create_streaming_response(
            exit_code=0, stdout="All checks passed!"
        )
        evaluator._code_interpreter = mock_code_interpreter

        status = evaluator.evaluate_linting(config, iteration=1)

        # Verify status is MET
        assert status.status == ExitConditionStatusValue.MET
        assert status.tool_exit_code == 0
        assert status.iteration_evaluated == 1

        # Verify Code Interpreter was called with ruff command
        call_args = mock_code_interpreter.execute_command.call_args[0][0]
        assert "ruff check" in call_args

    def test_evaluate_linting_failure(self, mocker):
        """Should mark condition as NOT_MET when linting fails."""
        evaluator = ExitConditionEvaluator(region="us-east-1")
        config = ExitConditionConfig(type=ExitConditionType.LINTING_CLEAN)

        # Mock Code Interpreter with streaming response
        mock_code_interpreter = mocker.Mock()
        mock_code_interpreter.execute_command.return_value = create_streaming_response(
            exit_code=1, stdout="Found 5 errors in 3 files"
        )
        evaluator._code_interpreter = mock_code_interpreter

        status = evaluator.evaluate_linting(config, iteration=2)

        # Verify status is NOT_MET
        assert status.status == ExitConditionStatusValue.NOT_MET
        assert status.tool_exit_code == 1
        assert status.iteration_evaluated == 2

    def test_evaluate_linting_with_custom_path(self, mocker):
        """Should use custom path for ruff check."""
        evaluator = ExitConditionEvaluator(region="us-east-1")
        config = ExitConditionConfig(
            type=ExitConditionType.LINTING_CLEAN,
            tool_arguments={"path": "src/loop/"},
        )

        # Mock Code Interpreter with streaming response
        mock_code_interpreter = mocker.Mock()
        mock_code_interpreter.execute_command.return_value = create_streaming_response(
            exit_code=0, stdout="OK"
        )
        evaluator._code_interpreter = mock_code_interpreter

        evaluator.evaluate_linting(config, iteration=1)

        # Verify custom path was used
        call_args = mock_code_interpreter.execute_command.call_args[0][0]
        assert "src/loop/" in call_args


class TestEvaluateDispatcher:
    """Test evaluate() dispatcher method (T054)."""

    def test_dispatcher_routes_to_tests(self, mocker):
        """Should route ALL_TESTS_PASS to evaluate_tests()."""
        evaluator = ExitConditionEvaluator(region="us-east-1")
        config = ExitConditionConfig(type=ExitConditionType.ALL_TESTS_PASS)

        # Mock evaluate_tests
        mock_evaluate = mocker.patch.object(
            evaluator,
            "evaluate_tests",
            return_value=ExitConditionStatus(type=ExitConditionType.ALL_TESTS_PASS),
        )

        evaluator.evaluate(config, iteration=1)

        mock_evaluate.assert_called_once_with(config, 1)

    def test_dispatcher_routes_to_linting(self, mocker):
        """Should route LINTING_CLEAN to evaluate_linting()."""
        evaluator = ExitConditionEvaluator(region="us-east-1")
        config = ExitConditionConfig(type=ExitConditionType.LINTING_CLEAN)

        # Mock evaluate_linting
        mock_evaluate = mocker.patch.object(
            evaluator,
            "evaluate_linting",
            return_value=ExitConditionStatus(type=ExitConditionType.LINTING_CLEAN),
        )

        evaluator.evaluate(config, iteration=1)

        mock_evaluate.assert_called_once_with(config, 1)

    def test_dispatcher_routes_to_build(self, mocker):
        """Should route BUILD_SUCCEEDS to evaluate_build()."""
        evaluator = ExitConditionEvaluator(region="us-east-1")
        config = ExitConditionConfig(type=ExitConditionType.BUILD_SUCCEEDS)

        # Mock evaluate_build
        mock_evaluate = mocker.patch.object(
            evaluator,
            "evaluate_build",
            return_value=ExitConditionStatus(type=ExitConditionType.BUILD_SUCCEEDS),
        )

        evaluator.evaluate(config, iteration=1)

        mock_evaluate.assert_called_once_with(config, 1)

    def test_dispatcher_routes_to_security(self, mocker):
        """Should route SECURITY_SCAN_CLEAN to evaluate_security_scan()."""
        evaluator = ExitConditionEvaluator(region="us-east-1")
        config = ExitConditionConfig(type=ExitConditionType.SECURITY_SCAN_CLEAN)

        # Mock evaluate_security_scan
        mock_evaluate = mocker.patch.object(
            evaluator,
            "evaluate_security_scan",
            return_value=ExitConditionStatus(type=ExitConditionType.SECURITY_SCAN_CLEAN),
        )

        evaluator.evaluate(config, iteration=1)

        mock_evaluate.assert_called_once_with(config, 1)

    def test_dispatcher_routes_to_custom(self, mocker):
        """Should route CUSTOM to evaluate_custom()."""
        evaluator = ExitConditionEvaluator(region="us-east-1")
        config = ExitConditionConfig(
            type=ExitConditionType.CUSTOM, custom_evaluator="mymodule.check"
        )

        # Mock evaluate_custom
        mock_evaluate = mocker.patch.object(
            evaluator,
            "evaluate_custom",
            return_value=ExitConditionStatus(type=ExitConditionType.CUSTOM),
        )

        evaluator.evaluate(config, iteration=1)

        mock_evaluate.assert_called_once_with(config, 1)


class TestTimeoutEnforcement:
    """Test timeout enforcement per SC-002."""

    def test_timeout_enforcement(self, mocker):
        """Should raise TimeoutError when command exceeds timeout."""
        import time

        evaluator = ExitConditionEvaluator(region="us-east-1", timeout_seconds=1)

        # Mock Code Interpreter to simulate slow execution
        def slow_execute(command):
            time.sleep(3)  # Sleep longer than timeout
            return create_streaming_response(exit_code=0, stdout="Done")

        mock_code_interpreter = mocker.Mock()
        mock_code_interpreter.execute_command.side_effect = slow_execute
        evaluator._code_interpreter = mock_code_interpreter

        config = ExitConditionConfig(type=ExitConditionType.LINTING_CLEAN)
        status = evaluator.evaluate_linting(config, iteration=1)

        # Should mark as ERROR due to timeout
        assert status.status == ExitConditionStatusValue.ERROR
        assert "timeout" in status.error_message.lower()
