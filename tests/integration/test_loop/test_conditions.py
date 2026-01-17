"""Integration tests for exit condition evaluation with Code Interpreter (T058).

These tests require actual AWS credentials and Code Interpreter access.
They are marked with @pytest.mark.integration to be skipped in CI.
"""

import pytest

from src.loop.conditions import ExitConditionEvaluator
from src.loop.models import (
    ExitConditionConfig,
    ExitConditionStatusValue,
    ExitConditionType,
)


@pytest.mark.integration
class TestCodeInterpreterIntegration:
    """Integration tests with real Code Interpreter (T058)."""

    @pytest.fixture
    def evaluator(self):
        """Create evaluator with real Code Interpreter client."""
        # Skip if AWS credentials not available
        import os

        if not os.getenv("AWS_REGION"):
            pytest.skip("AWS credentials not configured")

        # Clear any moto mock credentials that might interfere
        # Code Interpreter needs real AWS credentials
        # Use yield to keep credentials cleared for the entire test duration
        mock_keys = [
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "AWS_SECURITY_TOKEN",
            "AWS_SESSION_TOKEN",
        ]
        original_values = {}
        for key in mock_keys:
            if key in os.environ and os.environ[key] == "testing":
                original_values[key] = os.environ.pop(key)

        region = os.getenv("AWS_REGION", "us-east-1")
        evaluator = ExitConditionEvaluator(region=region, timeout_seconds=60)

        # Yield evaluator - credentials stay cleared during test execution
        yield evaluator

        # Restore original values after test completes
        for key, value in original_values.items():
            os.environ[key] = value

    def test_real_code_interpreter_pytest(self, evaluator):
        """Should execute real pytest command via Code Interpreter."""
        config = ExitConditionConfig(
            type=ExitConditionType.ALL_TESTS_PASS,
            tool_arguments={"path": "tests/unit/test_loop/", "markers": "not integration"},
        )

        # This will actually call Code Interpreter
        status = evaluator.evaluate_tests(config, iteration=1)

        # Verify we got a real result
        assert status.type == ExitConditionType.ALL_TESTS_PASS
        assert status.tool_name == "pytest"
        assert status.evaluated_at is not None
        assert status.iteration_evaluated == 1
        # Status should be MET or NOT_MET, not ERROR
        assert status.status in (
            ExitConditionStatusValue.MET,
            ExitConditionStatusValue.NOT_MET,
        )

    def test_real_code_interpreter_ruff(self, evaluator):
        """Should execute real ruff check via Code Interpreter."""
        config = ExitConditionConfig(
            type=ExitConditionType.LINTING_CLEAN, tool_arguments={"path": "src/loop/"}
        )

        # This will actually call Code Interpreter
        status = evaluator.evaluate_linting(config, iteration=1)

        # Verify we got a real result
        assert status.type == ExitConditionType.LINTING_CLEAN
        assert status.tool_name == "ruff"
        assert status.evaluated_at is not None
        assert status.iteration_evaluated == 1
        # Status should be MET or NOT_MET, not ERROR
        assert status.status in (
            ExitConditionStatusValue.MET,
            ExitConditionStatusValue.NOT_MET,
        )

    def test_real_code_interpreter_timeout(self, evaluator):
        """Should enforce timeout on long-running commands."""
        # Create evaluator with very short timeout
        short_timeout_evaluator = ExitConditionEvaluator(region=evaluator.region, timeout_seconds=2)

        config = ExitConditionConfig(
            type=ExitConditionType.ALL_TESTS_PASS,
            tool_arguments={
                # This command will sleep for longer than timeout
                "path": "tests/",
            },
        )

        # Override execute_code to simulate long-running command
        import time

        original_execute = short_timeout_evaluator.code_interpreter.execute_code

        def slow_execute(cmd):
            time.sleep(5)  # Sleep longer than 2s timeout
            return original_execute(cmd)

        short_timeout_evaluator.code_interpreter.execute_code = slow_execute

        status = short_timeout_evaluator.evaluate_tests(config, iteration=1)

        # Should timeout and mark as ERROR
        assert status.status == ExitConditionStatusValue.ERROR
        assert "timeout" in status.error_message.lower()


@pytest.mark.integration
def test_code_interpreter_session_lifecycle():
    """Test Code Interpreter session lifecycle."""
    import os

    if not os.getenv("AWS_REGION"):
        pytest.skip("AWS credentials not configured")

    region = os.getenv("AWS_REGION", "us-east-1")
    evaluator = ExitConditionEvaluator(region=region)

    # Code Interpreter should not be initialized yet
    assert evaluator._code_interpreter is None

    # Access should trigger initialization
    ci = evaluator.code_interpreter
    assert ci is not None
    assert evaluator._code_interpreter is not None

    # Subsequent access should return same instance
    ci2 = evaluator.code_interpreter
    assert ci2 is ci
