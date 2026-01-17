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

        # Mock Code Interpreter to simulate successful pytest run
        mock_execute = mocker.patch.object(
            evaluator.code_interpreter,
            "execute_code",
            return_value={
                "exit_code": 0,
                "output": "===== 15 passed in 2.3s =====",
            },
        )

        status = evaluator.evaluate_tests(config, iteration=1)

        # Verify status is MET
        assert status.status == ExitConditionStatusValue.MET
        assert status.tool_exit_code == 0
        assert "passed" in status.tool_output.lower()
        assert status.iteration_evaluated == 1

        # Verify Code Interpreter was called with pytest command
        mock_execute.assert_called_once()

    def test_evaluate_tests_failure(self, mocker):
        """Should mark condition as NOT_MET when tests fail."""
        evaluator = ExitConditionEvaluator(region="us-east-1")
        config = ExitConditionConfig(type=ExitConditionType.ALL_TESTS_PASS)

        # Mock Code Interpreter to simulate failed pytest run
        mocker.patch.object(
            evaluator.code_interpreter,
            "execute_code",
            return_value={
                "exit_code": 1,
                "output": "===== 3 failed, 12 passed in 2.5s =====",
            },
        )

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

        mock_execute = mocker.patch.object(
            evaluator.code_interpreter,
            "execute_code",
            return_value={"exit_code": 0, "output": "10 passed"},
        )

        evaluator.evaluate_tests(config, iteration=1)

        # Verify custom arguments were included
        call_args = mock_execute.call_args[0][0]
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

        # Mock Code Interpreter to simulate clean ruff check
        mock_execute = mocker.patch.object(
            evaluator.code_interpreter,
            "execute_code",
            return_value={
                "exit_code": 0,
                "output": "All checks passed!",
            },
        )

        status = evaluator.evaluate_linting(config, iteration=1)

        # Verify status is MET
        assert status.status == ExitConditionStatusValue.MET
        assert status.tool_exit_code == 0
        assert status.iteration_evaluated == 1

        # Verify Code Interpreter was called with ruff command
        call_args = mock_execute.call_args[0][0]
        assert "ruff check" in call_args

    def test_evaluate_linting_failure(self, mocker):
        """Should mark condition as NOT_MET when linting fails."""
        evaluator = ExitConditionEvaluator(region="us-east-1")
        config = ExitConditionConfig(type=ExitConditionType.LINTING_CLEAN)

        # Mock Code Interpreter to simulate ruff errors
        mocker.patch.object(
            evaluator.code_interpreter,
            "execute_code",
            return_value={
                "exit_code": 1,
                "output": "Found 5 errors in 3 files",
            },
        )

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

        mock_execute = mocker.patch.object(
            evaluator.code_interpreter,
            "execute_code",
            return_value={"exit_code": 0, "output": "OK"},
        )

        evaluator.evaluate_linting(config, iteration=1)

        # Verify custom path was used
        call_args = mock_execute.call_args[0][0]
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


class TestTimeoutHandling:
    """Test timeout handling (T057)."""

    def test_timeout_enforcement(self, mocker):
        """Should enforce timeout and mark condition as ERROR."""
        import concurrent.futures

        evaluator = ExitConditionEvaluator(region="us-east-1", timeout_seconds=1)
        config = ExitConditionConfig(type=ExitConditionType.ALL_TESTS_PASS)

        # Mock execute_code to raise TimeoutError
        mocker.patch.object(
            evaluator.code_interpreter, "execute_code", side_effect=TimeoutError("Timeout")
        )

        # Mock ThreadPoolExecutor to simulate timeout
        def mock_submit(func, *args):
            future = mocker.Mock()
            future.result.side_effect = concurrent.futures.TimeoutError()
            future.cancel = mocker.Mock()
            return future

        mock_executor = mocker.Mock()
        mock_executor.__enter__ = mocker.Mock(return_value=mock_executor)
        mock_executor.__exit__ = mocker.Mock(return_value=None)
        mock_executor.submit = mock_submit

        mocker.patch(
            "concurrent.futures.ThreadPoolExecutor", return_value=mock_executor
        )

        status = evaluator.evaluate_tests(config, iteration=1)

        # Should mark as ERROR
        assert status.status == ExitConditionStatusValue.ERROR
        assert "timeout" in status.error_message.lower()
        assert status.iteration_evaluated == 1

    def test_custom_timeout_value(self):
        """Should allow custom timeout configuration."""
        evaluator = ExitConditionEvaluator(region="us-east-1", timeout_seconds=60)

        assert evaluator.timeout_seconds == 60
