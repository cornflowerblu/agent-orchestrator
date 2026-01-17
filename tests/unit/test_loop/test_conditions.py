"""Unit tests for exit condition evaluation (T054-T057)."""

import pytest

from src.exceptions import ExitConditionEvaluationError
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
