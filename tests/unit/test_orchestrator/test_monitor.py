"""Unit tests for ObservabilityMonitor.

Tests for monitoring agent loop progress via Observability service.
"""


from src.orchestrator.monitor import ObservabilityMonitor


class TestObservabilityMonitor:
    """Tests for ObservabilityMonitor class."""

    def test_create_monitor(self):
        """Test creating ObservabilityMonitor instance."""
        monitor = ObservabilityMonitor(agent_name="test-agent", region="us-east-1")

        assert monitor.agent_name == "test-agent"
        assert monitor.region == "us-east-1"
        assert monitor.alert_manager is not None

    def test_create_monitor_default_region(self):
        """Test ObservabilityMonitor with default region."""
        monitor = ObservabilityMonitor(agent_name="test-agent")

        assert monitor.region == "us-east-1"

    def test_watch_agent(self):
        """Test watching an agent."""
        monitor = ObservabilityMonitor(agent_name="test-agent")

        result = monitor.watch_agent(
            session_id="session-123",
            max_iterations=100,
            threshold=0.8,
        )

        assert result["agent_name"] == "test-agent"
        assert result["session_id"] == "session-123"
        assert result["max_iterations"] == 100
        assert result["threshold"] == 0.8
        assert result["monitoring"] is True

    def test_watch_agent_custom_threshold(self):
        """Test watching agent with custom threshold."""
        monitor = ObservabilityMonitor(agent_name="test-agent")

        result = monitor.watch_agent(
            session_id="session-123",
            max_iterations=100,
            threshold=0.9,
        )

        assert result["threshold"] == 0.9
