"""Status tracking storage for agents.

Task T074: Implement status tracking storage
"""

import os
from datetime import UTC, datetime
from typing import Any

import boto3
from botocore.exceptions import ClientError

from src.exceptions import AgentNotFoundError, ValidationError
from src.logging_config import get_logger
from src.registry.models import (
    AgentStatus,
    AgentStatusSummary,
    AgentStatusValue,
    HealthCheckStatus,
)

logger = get_logger(__name__)


class StatusStorage:
    """DynamoDB storage for agent status tracking.

    Task T074: Implement status tracking storage
    """

    def __init__(self, table_name: str | None = None, region: str | None = None):
        """Initialize status storage.

        Args:
            table_name: DynamoDB table name (defaults to AGENT_STATUS_TABLE env var)
            region: AWS region (defaults to AWS_REGION env var or us-east-1)
        """
        self.table_name = table_name or os.getenv("AGENT_STATUS_TABLE", "AgentStatus")
        self.region = region or os.getenv("AWS_REGION", "us-east-1")

        self.dynamodb = boto3.resource("dynamodb", region_name=self.region)
        self.table = self.dynamodb.Table(self.table_name)

        logger.info(f"Initialized status storage for table '{self.table_name}'")

    def get_status(self, agent_name: str) -> AgentStatus:
        """Get the current status of an agent.

        Args:
            agent_name: Name of the agent

        Returns:
            AgentStatus for the agent

        Raises:
            AgentNotFoundError: If no status exists for the agent
        """
        try:
            logger.debug(f"Getting status for agent '{agent_name}'")

            response = self.table.get_item(Key={"agent_name": agent_name})

            if "Item" not in response:
                raise AgentNotFoundError(agent_name)

            item = response["Item"]
            return AgentStatus(
                agent_name=item["agent_name"],
                status=AgentStatusValue(item.get("status", "unknown")),
                health_check=HealthCheckStatus(item.get("health_check", "unknown")),
                last_seen=item.get("last_seen", ""),
                endpoint=item.get("endpoint"),
                version=item.get("version"),
                metrics=item.get("metrics", {}),
                error_message=item.get("error_message"),
                updated_at=item.get("updated_at", ""),
            )

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            logger.exception(f"DynamoDB error getting status for '{agent_name}': {error_code}")
            raise ValidationError(
                f"Failed to get status for '{agent_name}'",
                details={
                    "error": str(e),
                    "error_code": error_code,
                    "agent_name": agent_name,
                    "table": self.table_name,
                },
            ) from e

    def update_status(
        self,
        agent_name: str,
        status: AgentStatusValue | None = None,
        health_check: HealthCheckStatus | None = None,
        endpoint: str | None = None,
        version: str | None = None,
        metrics: dict[str, Any] | None = None,
        error_message: str | None = None,
    ) -> AgentStatus:
        """Update the status of an agent.

        Args:
            agent_name: Name of the agent
            status: New status value
            health_check: New health check status
            endpoint: Agent endpoint URL
            version: Agent version
            metrics: Optional metrics dict
            error_message: Optional error message

        Returns:
            Updated AgentStatus

        Raises:
            AgentNotFoundError: If no status exists for the agent
            ValidationError: If update fails due to DynamoDB error
        """
        try:
            now = datetime.now(UTC).isoformat()

            # Build update expression dynamically
            update_parts = ["#updated_at = :updated_at", "#last_seen = :last_seen"]
            expression_names = {
                "#updated_at": "updated_at",
                "#last_seen": "last_seen",
            }
            expression_values: dict[str, Any] = {
                ":updated_at": now,
                ":last_seen": now,
            }

            if status is not None:
                update_parts.append("#status = :status")
                expression_names["#status"] = "status"
                expression_values[":status"] = status.value

            if health_check is not None:
                update_parts.append("#health_check = :health_check")
                expression_names["#health_check"] = "health_check"
                expression_values[":health_check"] = health_check.value

            if endpoint is not None:
                update_parts.append("#endpoint = :endpoint")
                expression_names["#endpoint"] = "endpoint"
                expression_values[":endpoint"] = endpoint

            if version is not None:
                update_parts.append("#version = :version")
                expression_names["#version"] = "version"
                expression_values[":version"] = version

            if metrics is not None:
                update_parts.append("#metrics = :metrics")
                expression_names["#metrics"] = "metrics"
                expression_values[":metrics"] = metrics

            if error_message is not None:
                update_parts.append("#error_message = :error_message")
                expression_names["#error_message"] = "error_message"
                expression_values[":error_message"] = error_message

            update_expression = "SET " + ", ".join(update_parts)

            logger.debug(f"Updating status for agent '{agent_name}'")

            # Use conditional expression to ensure item exists before updating
            self.table.update_item(
                Key={"agent_name": agent_name},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_names,
                ExpressionAttributeValues=expression_values,
                ConditionExpression="attribute_exists(agent_name)",
            )

            # Return the updated status
            return self.get_status(agent_name)

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")

            # Handle conditional check failure (item doesn't exist)
            if error_code == "ConditionalCheckFailedException":
                raise AgentNotFoundError(agent_name) from e

            logger.exception(f"DynamoDB error updating status for '{agent_name}': {error_code}")
            raise ValidationError(
                f"Failed to update status for '{agent_name}'",
                details={
                    "error": str(e),
                    "error_code": error_code,
                    "agent_name": agent_name,
                    "table": self.table_name,
                },
            ) from e

    def put_status(self, status: AgentStatus) -> AgentStatus:
        """Create or replace an agent status.

        Args:
            status: AgentStatus to store

        Returns:
            The stored AgentStatus
        """
        try:
            status.updated_at = datetime.now(UTC).isoformat()

            item = status.model_dump()

            # Convert enums to strings
            item["status"] = status.status.value
            item["health_check"] = status.health_check.value

            logger.debug(f"Storing status for agent '{status.agent_name}'")

            self.table.put_item(Item=item)

            logger.info(f"Stored status for agent '{status.agent_name}'")

            return status

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            logger.exception(
                f"DynamoDB error storing status for '{status.agent_name}': {error_code}"
            )
            raise ValidationError(
                f"Failed to store status for '{status.agent_name}'",
                details={
                    "error": str(e),
                    "error_code": error_code,
                    "agent_name": status.agent_name,
                    "table": self.table_name,
                },
            ) from e

    def delete_status(self, agent_name: str) -> None:
        """Delete status for an agent.

        Args:
            agent_name: Name of the agent
        """
        try:
            logger.debug(f"Deleting status for agent '{agent_name}'")

            self.table.delete_item(Key={"agent_name": agent_name})

            logger.info(f"Deleted status for agent '{agent_name}'")

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            logger.exception(f"DynamoDB error deleting status for '{agent_name}': {error_code}")
            raise ValidationError(
                f"Failed to delete status for '{agent_name}'",
                details={
                    "error": str(e),
                    "error_code": error_code,
                    "agent_name": agent_name,
                    "table": self.table_name,
                },
            ) from e

    def list_all_statuses(self) -> list[AgentStatus]:
        """List status for all agents.

        Returns:
            List of AgentStatus for all agents
        """
        try:
            logger.debug("Scanning all agent statuses")

            response = self.table.scan()
            items = response.get("Items", [])

            # Handle pagination
            while "LastEvaluatedKey" in response:
                response = self.table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
                items.extend(response.get("Items", []))

            statuses = []
            for item in items:
                statuses.append(
                    AgentStatus(
                        agent_name=item["agent_name"],
                        status=AgentStatusValue(item.get("status", "unknown")),
                        health_check=HealthCheckStatus(item.get("health_check", "unknown")),
                        last_seen=item.get("last_seen", ""),
                        endpoint=item.get("endpoint"),
                        version=item.get("version"),
                        metrics=item.get("metrics", {}),
                        error_message=item.get("error_message"),
                        updated_at=item.get("updated_at", ""),
                    )
                )

            logger.info(f"Retrieved {len(statuses)} status records")

            return statuses

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            logger.exception(f"DynamoDB error listing statuses: {error_code}")
            raise ValidationError(
                "Failed to list agent statuses",
                details={
                    "error": str(e),
                    "error_code": error_code,
                    "table": self.table_name,
                },
            ) from e

    def get_status_summary(self) -> AgentStatusSummary:
        """Get a summary of all agent statuses.

        Returns:
            AgentStatusSummary with counts by status
        """
        statuses = self.list_all_statuses()

        summary = AgentStatusSummary(
            total_agents=len(statuses),
            active_count=sum(1 for s in statuses if s.status == AgentStatusValue.ACTIVE),
            inactive_count=sum(1 for s in statuses if s.status == AgentStatusValue.INACTIVE),
            degraded_count=sum(1 for s in statuses if s.status == AgentStatusValue.DEGRADED),
            healthy_count=sum(1 for s in statuses if s.is_healthy()),
            unhealthy_count=sum(1 for s in statuses if not s.is_healthy()),
        )

        return summary
