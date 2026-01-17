"""Unit tests for status storage module.

Tests for T073-T074: AgentStatus model and status tracking storage
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

import boto3
from moto import mock_aws

from src.registry.models import (
    AgentStatus,
    AgentStatusSummary,
    AgentStatusValue,
    HealthCheckStatus,
)


class TestAgentStatusModel:
    """Tests for AgentStatus Pydantic model (T073)."""

    def test_status_default_values(self):
        """Test AgentStatus with default values."""
        status = AgentStatus(agent_name="test-agent")

        assert status.agent_name == "test-agent"
        assert status.status == AgentStatusValue.UNKNOWN
        assert status.health_check == HealthCheckStatus.UNKNOWN
        assert status.endpoint is None

    def test_status_all_values(self):
        """Test AgentStatus with all values."""
        status = AgentStatus(
            agent_name="test-agent",
            status=AgentStatusValue.ACTIVE,
            health_check=HealthCheckStatus.PASSING,
            endpoint="https://example.com",
            version="1.0.0",
            metrics={"requests": 100},
            error_message=None
        )

        assert status.agent_name == "test-agent"
        assert status.status == AgentStatusValue.ACTIVE
        assert status.health_check == HealthCheckStatus.PASSING
        assert status.endpoint == "https://example.com"
        assert status.version == "1.0.0"
        assert status.metrics["requests"] == 100

    def test_is_healthy_true(self):
        """Test is_healthy returns True for active+passing."""
        status = AgentStatus(
            agent_name="test-agent",
            status=AgentStatusValue.ACTIVE,
            health_check=HealthCheckStatus.PASSING
        )

        assert status.is_healthy() is True

    def test_is_healthy_false_inactive(self):
        """Test is_healthy returns False for inactive."""
        status = AgentStatus(
            agent_name="test-agent",
            status=AgentStatusValue.INACTIVE,
            health_check=HealthCheckStatus.PASSING
        )

        assert status.is_healthy() is False

    def test_is_healthy_false_failing(self):
        """Test is_healthy returns False for failing health check."""
        status = AgentStatus(
            agent_name="test-agent",
            status=AgentStatusValue.ACTIVE,
            health_check=HealthCheckStatus.FAILING
        )

        assert status.is_healthy() is False

    def test_mark_active(self):
        """Test mark_active updates status."""
        status = AgentStatus(
            agent_name="test-agent",
            status=AgentStatusValue.INACTIVE
        )

        original_time = status.last_seen
        status.mark_active()

        assert status.status == AgentStatusValue.ACTIVE
        # Last seen should be updated
        assert status.last_seen != original_time

    def test_mark_inactive(self):
        """Test mark_inactive updates status."""
        status = AgentStatus(
            agent_name="test-agent",
            status=AgentStatusValue.ACTIVE
        )

        status.mark_inactive("Connection lost")

        assert status.status == AgentStatusValue.INACTIVE
        assert status.error_message == "Connection lost"

    def test_update_health_check(self):
        """Test update_health_check updates status."""
        status = AgentStatus(agent_name="test-agent")

        original_time = status.last_seen
        status.update_health_check(HealthCheckStatus.PASSING)

        assert status.health_check == HealthCheckStatus.PASSING
        assert status.last_seen != original_time


class TestAgentStatusSummary:
    """Tests for AgentStatusSummary model."""

    def test_summary_default_values(self):
        """Test AgentStatusSummary with defaults."""
        summary = AgentStatusSummary()

        assert summary.total_agents == 0
        assert summary.active_count == 0
        assert summary.healthy_count == 0

    def test_summary_with_values(self):
        """Test AgentStatusSummary with values."""
        summary = AgentStatusSummary(
            total_agents=10,
            active_count=8,
            inactive_count=2,
            degraded_count=0,
            healthy_count=7,
            unhealthy_count=3
        )

        assert summary.total_agents == 10
        assert summary.active_count == 8


class TestStatusStorage:
    """Tests for StatusStorage DynamoDB operations (T074)."""

    @pytest.fixture
    def status_storage(self):
        """Create a StatusStorage instance with mock DynamoDB."""
        with mock_aws():
            dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
            table = dynamodb.create_table(
                TableName="TestAgentStatus",
                KeySchema=[{"AttributeName": "agent_name", "KeyType": "HASH"}],
                AttributeDefinitions=[
                    {"AttributeName": "agent_name", "AttributeType": "S"}
                ],
                BillingMode="PAY_PER_REQUEST"
            )
            table.wait_until_exists()

            from src.registry.status import StatusStorage
            storage = StatusStorage(
                table_name="TestAgentStatus",
                region="us-east-1"
            )
            yield storage

    def test_storage_init(self):
        """Test StatusStorage initialization."""
        with mock_aws():
            from src.registry.status import StatusStorage
            storage = StatusStorage(
                table_name="TestTable",
                region="eu-west-1"
            )
            assert storage.table_name == "TestTable"
            assert storage.region == "eu-west-1"

    def test_put_and_get_status(self, status_storage):
        """Test putting and getting status."""
        status = AgentStatus(
            agent_name="test-agent",
            status=AgentStatusValue.ACTIVE,
            health_check=HealthCheckStatus.PASSING
        )

        status_storage.put_status(status)
        retrieved = status_storage.get_status("test-agent")

        assert retrieved.agent_name == "test-agent"
        assert retrieved.status == AgentStatusValue.ACTIVE

    def test_get_status_not_found(self, status_storage):
        """Test getting non-existent status."""
        from src.exceptions import AgentNotFoundError

        with pytest.raises(AgentNotFoundError):
            status_storage.get_status("non-existent")

    def test_update_status(self, status_storage):
        """Test updating status."""
        # First create
        status = AgentStatus(
            agent_name="test-agent",
            status=AgentStatusValue.ACTIVE
        )
        status_storage.put_status(status)

        # Then update
        updated = status_storage.update_status(
            agent_name="test-agent",
            status=AgentStatusValue.DEGRADED,
            error_message="High latency"
        )

        assert updated.status == AgentStatusValue.DEGRADED
        assert updated.error_message == "High latency"

    def test_delete_status(self, status_storage):
        """Test deleting status."""
        from src.exceptions import AgentNotFoundError

        # Create
        status = AgentStatus(agent_name="test-agent")
        status_storage.put_status(status)

        # Delete
        status_storage.delete_status("test-agent")

        # Verify deleted
        with pytest.raises(AgentNotFoundError):
            status_storage.get_status("test-agent")

    def test_list_all_statuses(self, status_storage):
        """Test listing all statuses."""
        # Create multiple
        for i in range(3):
            status = AgentStatus(
                agent_name=f"agent-{i}",
                status=AgentStatusValue.ACTIVE
            )
            status_storage.put_status(status)

        # List
        statuses = status_storage.list_all_statuses()

        assert len(statuses) == 3
        names = [s.agent_name for s in statuses]
        assert "agent-0" in names
        assert "agent-1" in names
        assert "agent-2" in names

    def test_list_all_statuses_empty(self, status_storage):
        """Test listing when no statuses exist."""
        statuses = status_storage.list_all_statuses()
        assert statuses == []

    def test_get_status_summary(self, status_storage):
        """Test getting status summary."""
        # Create mixed statuses
        status_storage.put_status(AgentStatus(
            agent_name="active-1",
            status=AgentStatusValue.ACTIVE,
            health_check=HealthCheckStatus.PASSING
        ))
        status_storage.put_status(AgentStatus(
            agent_name="active-2",
            status=AgentStatusValue.ACTIVE,
            health_check=HealthCheckStatus.FAILING
        ))
        status_storage.put_status(AgentStatus(
            agent_name="inactive-1",
            status=AgentStatusValue.INACTIVE
        ))

        summary = status_storage.get_status_summary()

        assert summary.total_agents == 3
        assert summary.active_count == 2
        assert summary.inactive_count == 1
        assert summary.healthy_count == 1
        assert summary.unhealthy_count == 2

    def test_update_status_with_all_fields(self, status_storage):
        """Test updating all status fields."""
        # Create initial
        status_storage.put_status(AgentStatus(agent_name="test-agent"))

        # Update all fields
        updated = status_storage.update_status(
            agent_name="test-agent",
            status=AgentStatusValue.ACTIVE,
            health_check=HealthCheckStatus.PASSING,
            endpoint="https://example.com",
            version="2.0.0",
            metrics={"count": 100},
            error_message=None
        )

        assert updated.status == AgentStatusValue.ACTIVE
        assert updated.endpoint == "https://example.com"
        assert updated.version == "2.0.0"


class TestAgentStatusEnums:
    """Tests for status enum values."""

    def test_agent_status_values(self):
        """Test all AgentStatusValue enum values."""
        assert AgentStatusValue.ACTIVE == "active"
        assert AgentStatusValue.INACTIVE == "inactive"
        assert AgentStatusValue.DEGRADED == "degraded"
        assert AgentStatusValue.MAINTENANCE == "maintenance"
        assert AgentStatusValue.UNKNOWN == "unknown"

    def test_health_check_values(self):
        """Test all HealthCheckStatus enum values."""
        assert HealthCheckStatus.PASSING == "passing"
        assert HealthCheckStatus.FAILING == "failing"
        assert HealthCheckStatus.WARNING == "warning"
        assert HealthCheckStatus.UNKNOWN == "unknown"
