"""Unit tests for dashboard API handlers.

Tests for DashboardHandlers class that provides HTTP endpoint handlers
for querying loop progress, events, and checkpoints.
"""

from unittest.mock import Mock, patch


class TestDashboardHandlersInit:
    """Test DashboardHandlers initialization."""

    def test_init_creates_queries_instance(self):
        """Test that DashboardHandlers initializes ObservabilityQueries."""
        from src.dashboard.handlers import DashboardHandlers

        handlers = DashboardHandlers(region="us-east-1")

        assert handlers is not None
        assert hasattr(handlers, "queries")
        assert handlers.region == "us-east-1"


class TestDashboardHandlersGetProgress:
    """Test DashboardHandlers.get_progress() handler."""

    @patch("src.dashboard.handlers.ObservabilityQueries")
    def test_get_progress_returns_success_with_data(self, mock_queries_class):
        """Test that get_progress returns success status with progress data."""
        from src.dashboard.handlers import DashboardHandlers
        from src.dashboard.models import LoopProgress

        # Setup mock queries
        mock_queries = Mock()
        mock_progress = LoopProgress(
            session_id="loop-123",
            agent_name="test-agent",
            current_iteration=10,
            max_iterations=100,
            phase="running",
            started_at="2026-01-17T10:00:00Z",
        )
        mock_queries.get_loop_progress.return_value = mock_progress
        mock_queries_class.return_value = mock_queries

        handlers = DashboardHandlers(region="us-east-1")
        result = handlers.get_progress("loop-123")

        assert result["status"] == "success"
        assert result["data"]["session_id"] == "loop-123"
        assert result["data"]["current_iteration"] == 10

    @patch("src.dashboard.handlers.ObservabilityQueries")
    def test_get_progress_returns_not_found_if_no_data(self, mock_queries_class):
        """Test that get_progress returns not_found status if no progress data."""
        from src.dashboard.handlers import DashboardHandlers

        # Setup mock queries to return None
        mock_queries = Mock()
        mock_queries.get_loop_progress.return_value = None
        mock_queries_class.return_value = mock_queries

        handlers = DashboardHandlers(region="us-east-1")
        result = handlers.get_progress("nonexistent-session")

        assert result["status"] == "not_found"
        assert result["data"] is None

    @patch("src.dashboard.handlers.ObservabilityQueries")
    def test_get_progress_returns_error_on_exception(self, mock_queries_class):
        """Test that get_progress returns error status on exception."""
        from src.dashboard.handlers import DashboardHandlers

        # Setup mock queries to raise exception
        mock_queries = Mock()
        mock_queries.get_loop_progress.side_effect = Exception("Query failed")
        mock_queries_class.return_value = mock_queries

        handlers = DashboardHandlers(region="us-east-1")
        result = handlers.get_progress("loop-123")

        assert result["status"] == "error"
        assert "error" in result


class TestDashboardHandlersGetEvents:
    """Test DashboardHandlers.get_events() handler."""

    @patch("src.dashboard.handlers.ObservabilityQueries")
    def test_get_events_returns_success_with_events(self, mock_queries_class):
        """Test that get_events returns success status with event list."""
        from src.dashboard.handlers import DashboardHandlers

        # Setup mock queries
        mock_queries = Mock()
        mock_events = [
            {
                "timestamp": "2026-01-17T10:00:00Z",
                "event_type": "loop.iteration.started",
                "iteration": "10",
            },
            {
                "timestamp": "2026-01-17T10:01:00Z",
                "event_type": "loop.iteration.completed",
                "iteration": "10",
            },
        ]
        mock_queries.get_recent_events.return_value = mock_events
        mock_queries_class.return_value = mock_queries

        handlers = DashboardHandlers(region="us-east-1")
        result = handlers.get_events("loop-123", limit=50)

        assert result["status"] == "success"
        assert result["count"] == 2
        assert len(result["data"]) == 2

    @patch("src.dashboard.handlers.ObservabilityQueries")
    def test_get_events_returns_empty_list_if_no_events(self, mock_queries_class):
        """Test that get_events returns empty list if no events found."""
        from src.dashboard.handlers import DashboardHandlers

        # Setup mock queries to return empty list
        mock_queries = Mock()
        mock_queries.get_recent_events.return_value = []
        mock_queries_class.return_value = mock_queries

        handlers = DashboardHandlers(region="us-east-1")
        result = handlers.get_events("loop-123")

        assert result["status"] == "success"
        assert result["count"] == 0
        assert result["data"] == []


class TestDashboardHandlersGetCheckpoints:
    """Test DashboardHandlers.get_checkpoints() handler."""

    @patch("src.dashboard.handlers.ObservabilityQueries")
    def test_get_checkpoints_returns_success_with_checkpoints(self, mock_queries_class):
        """Test that get_checkpoints returns success status with checkpoint list."""
        from src.dashboard.handlers import DashboardHandlers

        # Setup mock queries
        mock_queries = Mock()
        mock_checkpoints = [
            {"iteration": "10", "checkpoint_id": "cp-10", "timestamp": "2026-01-17T10:00:00Z"},
            {"iteration": "5", "checkpoint_id": "cp-5", "timestamp": "2026-01-17T09:30:00Z"},
        ]
        mock_queries.list_checkpoints.return_value = mock_checkpoints
        mock_queries_class.return_value = mock_queries

        handlers = DashboardHandlers(region="us-east-1")
        result = handlers.get_checkpoints("loop-123", limit=20)

        assert result["status"] == "success"
        assert result["count"] == 2
        assert len(result["data"]) == 2

    @patch("src.dashboard.handlers.ObservabilityQueries")
    def test_get_checkpoints_returns_empty_list_if_no_checkpoints(self, mock_queries_class):
        """Test that get_checkpoints returns empty list if no checkpoints found."""
        from src.dashboard.handlers import DashboardHandlers

        # Setup mock queries to return empty list
        mock_queries = Mock()
        mock_queries.list_checkpoints.return_value = []
        mock_queries_class.return_value = mock_queries

        handlers = DashboardHandlers(region="us-east-1")
        result = handlers.get_checkpoints("loop-123")

        assert result["status"] == "success"
        assert result["count"] == 0
        assert result["data"] == []
