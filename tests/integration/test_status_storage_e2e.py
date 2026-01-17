"""End-to-end integration tests for status storage with real DynamoDB.

Tests actual AWS DynamoDB operations against deployed tables.
"""

import os
from datetime import UTC, datetime

import pytest

from src.exceptions import AgentNotFoundError
from src.registry.models import AgentStatusValue, HealthCheckStatus
from src.registry.status import AgentStatus, StatusStorage

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


@pytest.fixture
def status_storage():
    """Create status storage connected to real DynamoDB."""
    return StatusStorage(
        table_name=os.getenv("AGENT_STATUS_TABLE", "AgentStatus"),
        region=os.getenv("AWS_REGION", "us-east-1"),
    )


@pytest.fixture
def sample_status():
    """Sample agent status for testing."""
    return AgentStatus(
        agent_name="test-status-agent",
        status=AgentStatusValue.ACTIVE,
        last_ping=datetime.now(tz=UTC),
        health_check=HealthCheckStatus.PASSING,
    )


class TestStatusStorageE2E:
    """End-to-end tests for status storage."""

    def test_put_and_get_status(self, status_storage, sample_status):
        """Test storing and retrieving agent status."""
        # Put status
        status_storage.put_status(sample_status)

        # Get status back
        retrieved = status_storage.get_status(sample_status.agent_name)

        assert retrieved is not None
        assert retrieved.agent_name == sample_status.agent_name
        assert retrieved.status == AgentStatusValue.ACTIVE
        assert retrieved.health_check == HealthCheckStatus.PASSING

    def test_update_status(self, status_storage, sample_status):
        """Test updating agent status."""
        # Store initial status
        status_storage.put_status(sample_status)

        # Update to inactive
        status_storage.update_status(sample_status.agent_name, status=AgentStatusValue.INACTIVE)

        # Verify update
        retrieved = status_storage.get_status(sample_status.agent_name)
        assert retrieved.status == AgentStatusValue.INACTIVE

    def test_update_health_check(self, status_storage, sample_status):
        """Test updating health check status."""
        # Store initial status
        status_storage.put_status(sample_status)

        # Update health check
        status_storage.update_status(
            sample_status.agent_name, health_check=HealthCheckStatus.FAILING
        )

        # Verify update
        retrieved = status_storage.get_status(sample_status.agent_name)
        assert retrieved.health_check == HealthCheckStatus.FAILING

    def test_update_multiple_fields(self, status_storage, sample_status):
        """Test updating multiple status fields at once."""
        # Store initial status
        status_storage.put_status(sample_status)

        # Update multiple fields
        status_storage.update_status(
            sample_status.agent_name,
            status=AgentStatusValue.DEGRADED,
            health_check=HealthCheckStatus.WARNING,
            error_message="processing-request-123",
        )

        # Verify all updates
        retrieved = status_storage.get_status(sample_status.agent_name)
        assert retrieved.status == AgentStatusValue.DEGRADED
        assert retrieved.health_check == HealthCheckStatus.WARNING
        assert retrieved.error_message == "processing-request-123"

    def test_list_all_statuses(self, status_storage, sample_status):
        """Test listing all agent statuses."""
        # Store status
        status_storage.put_status(sample_status)

        # List all
        all_statuses = status_storage.list_all_statuses()

        # Should have at least our test agent
        agent_names = [s.agent_name for s in all_statuses]
        assert sample_status.agent_name in agent_names

    def test_get_status_summary(self, status_storage, sample_status):
        """Test getting aggregated status summary."""
        # Store multiple agents with different statuses
        status_storage.put_status(sample_status)

        status2 = AgentStatus(
            agent_name="test-agent-2",
            status=AgentStatusValue.INACTIVE,
            last_ping=datetime.now(tz=UTC),
            health_check=HealthCheckStatus.PASSING,
        )
        status_storage.put_status(status2)

        status3 = AgentStatus(
            agent_name="test-agent-3",
            status=AgentStatusValue.ACTIVE,
            last_ping=datetime.now(tz=UTC),
            health_check=HealthCheckStatus.FAILING,
        )
        status_storage.put_status(status3)

        # Get summary
        summary = status_storage.get_status_summary()

        assert summary.total_agents >= 3
        assert summary.active_count >= 2  # sample_status and status3
        assert summary.inactive_count >= 1  # status2
        assert summary.healthy_count >= 1  # Only sample_status (ACTIVE + PASSING)
        assert summary.unhealthy_count >= 2  # status2 (INACTIVE) and status3 (FAILING)

    def test_delete_status(self, status_storage, sample_status):
        """Test deleting agent status."""
        # Store status
        status_storage.put_status(sample_status)

        # Verify it exists
        assert status_storage.get_status(sample_status.agent_name) is not None

        # Delete it
        status_storage.delete_status(sample_status.agent_name)

        # Verify it raises exception when not found
        with pytest.raises(AgentNotFoundError):
            status_storage.get_status(sample_status.agent_name)

    def test_get_status_not_found(self, status_storage):
        """Test getting non-existent status raises exception."""
        with pytest.raises(AgentNotFoundError, match="non-existent-agent"):
            status_storage.get_status("non-existent-agent")

    def test_agent_status_is_healthy_method(self, status_storage):
        """Test AgentStatus is_healthy() method with real data."""
        # Create active+passing status
        passing_status = AgentStatus(
            agent_name="test-passing-agent",
            status=AgentStatusValue.ACTIVE,
            last_ping=datetime.now(tz=UTC),
            health_check=HealthCheckStatus.PASSING,
        )
        status_storage.put_status(passing_status)

        retrieved = status_storage.get_status("test-passing-agent")
        assert retrieved.is_healthy() is True

        # Update to failing
        status_storage.update_status("test-passing-agent", health_check=HealthCheckStatus.FAILING)
        retrieved = status_storage.get_status("test-passing-agent")
        assert retrieved.is_healthy() is False

    def test_mark_active_and_inactive(self, status_storage):
        """Test mark_active() and mark_inactive() helper methods."""
        status = AgentStatus(
            agent_name="test-toggle-agent",
            status=AgentStatusValue.INACTIVE,
            last_ping=datetime.now(tz=UTC),
            health_check=HealthCheckStatus.PASSING,
        )
        status_storage.put_status(status)

        # Mark active
        retrieved = status_storage.get_status("test-toggle-agent")
        retrieved.mark_active()
        status_storage.put_status(retrieved)

        retrieved = status_storage.get_status("test-toggle-agent")
        assert retrieved.status == AgentStatusValue.ACTIVE

        # Mark inactive
        retrieved.mark_inactive()
        status_storage.put_status(retrieved)

        retrieved = status_storage.get_status("test-toggle-agent")
        assert retrieved.status == AgentStatusValue.INACTIVE
