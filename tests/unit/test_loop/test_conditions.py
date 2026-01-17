"""Unit tests for exit condition evaluation (T054-T057)."""

import pytest
from bedrock_agentcore.tools.code_interpreter_client import CodeInterpreter

from src.exceptions import ExitConditionEvaluationError
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
