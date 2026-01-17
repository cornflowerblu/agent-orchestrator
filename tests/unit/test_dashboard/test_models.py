"""Unit tests for dashboard data models.

Tests for LoopProgress and other response models used by dashboard queries.
"""

import pytest
from datetime import datetime, UTC


class TestLoopProgress:
    """Test LoopProgress response model."""

    def test_loop_progress_creation(self):
        """Test creating a LoopProgress instance with required fields."""
        from src.dashboard.models import LoopProgress

        progress = LoopProgress(
            session_id="loop-session-123",
            agent_name="test-agent",
            current_iteration=10,
            max_iterations=100,
            phase="running",
            started_at="2026-01-17T10:00:00Z",
        )

        assert progress.session_id == "loop-session-123"
        assert progress.agent_name == "test-agent"
        assert progress.current_iteration == 10
        assert progress.max_iterations == 100
        assert progress.phase == "running"
        assert progress.started_at == "2026-01-17T10:00:00Z"

    def test_loop_progress_with_optional_fields(self):
        """Test LoopProgress with optional fields like completed_at and outcome."""
        from src.dashboard.models import LoopProgress

        progress = LoopProgress(
            session_id="loop-session-456",
            agent_name="test-agent-2",
            current_iteration=100,
            max_iterations=100,
            phase="completed",
            started_at="2026-01-17T09:00:00Z",
            completed_at="2026-01-17T10:00:00Z",
            outcome="completed",
        )

        assert progress.completed_at == "2026-01-17T10:00:00Z"
        assert progress.outcome == "completed"

    def test_loop_progress_with_exit_conditions(self):
        """Test LoopProgress with exit condition status."""
        from src.dashboard.models import LoopProgress

        progress = LoopProgress(
            session_id="loop-session-789",
            agent_name="test-agent-3",
            current_iteration=5,
            max_iterations=50,
            phase="running",
            started_at="2026-01-17T10:00:00Z",
            exit_conditions_met=1,
            exit_conditions_total=3,
        )

        assert progress.exit_conditions_met == 1
        assert progress.exit_conditions_total == 3

    def test_loop_progress_percentage_calculation(self):
        """Test progress percentage calculation method."""
        from src.dashboard.models import LoopProgress

        progress = LoopProgress(
            session_id="loop-session-999",
            agent_name="test-agent",
            current_iteration=25,
            max_iterations=100,
            phase="running",
            started_at="2026-01-17T10:00:00Z",
        )

        assert progress.progress_percentage() == 25.0

    def test_loop_progress_percentage_at_zero(self):
        """Test progress percentage when iteration is 0."""
        from src.dashboard.models import LoopProgress

        progress = LoopProgress(
            session_id="loop-session-000",
            agent_name="test-agent",
            current_iteration=0,
            max_iterations=100,
            phase="initializing",
            started_at="2026-01-17T10:00:00Z",
        )

        assert progress.progress_percentage() == 0.0

    def test_loop_progress_percentage_at_completion(self):
        """Test progress percentage when at max iterations."""
        from src.dashboard.models import LoopProgress

        progress = LoopProgress(
            session_id="loop-session-max",
            agent_name="test-agent",
            current_iteration=100,
            max_iterations=100,
            phase="completed",
            started_at="2026-01-17T09:00:00Z",
        )

        assert progress.progress_percentage() == 100.0
