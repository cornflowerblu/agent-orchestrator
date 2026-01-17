"""CDK stack for integration testing with proper naming and cleanup.

Task T086: Create integration test stack naming and cleanup
"""

import os
from datetime import UTC, datetime
from typing import Any

from aws_cdk import RemovalPolicy, Stack, Tags
from aws_cdk import aws_dynamodb as dynamodb
from botocore.exceptions import ClientError
from constructs import Construct

from src.logging_config import get_logger

logger = get_logger(__name__)


def get_test_stack_name(base_name: str = "AgentFrameworkTest") -> str:
    """Generate a unique test stack name with timestamp.

    Args:
        base_name: Base name for the stack

    Returns:
        Unique stack name with timestamp
    """
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    return f"{base_name}-{timestamp}"


def get_test_resource_name(resource_type: str, base_name: str = "test") -> str:
    """Generate a unique test resource name.

    Args:
        resource_type: Type of resource (e.g., "table", "function")
        base_name: Base name for the resource

    Returns:
        Unique resource name with timestamp
    """
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    return f"{base_name}-{resource_type}-{timestamp}"


class TestStack(Stack):
    """Stack for integration testing with automatic cleanup.

    Creates ephemeral resources for integration tests that can be
    easily torn down after test completion.

    Features:
    - Unique naming with timestamps to prevent conflicts
    - RemovalPolicy.DESTROY for easy cleanup
    - Point-in-time recovery disabled for cost savings
    - Tags for easy identification and cleanup scripts

    Task T086: Create integration test stack naming and cleanup
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str | None = None,
        test_run_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the test stack.

        Args:
            scope: CDK scope
            construct_id: Optional unique ID (auto-generated if not provided)
            test_run_id: Optional test run identifier for correlation
            **kwargs: Additional stack props
        """
        # Generate unique stack name if not provided
        if construct_id is None:
            construct_id = get_test_stack_name()

        super().__init__(scope, construct_id, **kwargs)

        # Generate test run ID if not provided
        self.test_run_id = test_run_id or datetime.now(UTC).strftime("%Y%m%d%H%M%S")

        # Add tags for identification
        Tags.of(self).add("Environment", "test")
        Tags.of(self).add("Purpose", "integration-testing")
        Tags.of(self).add("TestRunId", self.test_run_id)
        Tags.of(self).add("AutoCleanup", "true")
        Tags.of(self).add("CreatedAt", datetime.now(UTC).isoformat())

        # Create test DynamoDB tables with cleanup-friendly settings
        self.metadata_table = dynamodb.Table(
            self,
            "TestAgentMetadata",
            table_name=f"AgentMetadata-test-{self.test_run_id}",
            partition_key=dynamodb.Attribute(
                name="agent_name",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            point_in_time_recovery=False,
        )

        self.status_table = dynamodb.Table(
            self,
            "TestAgentStatus",
            table_name=f"AgentStatus-test-{self.test_run_id}",
            partition_key=dynamodb.Attribute(
                name="agent_name",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            point_in_time_recovery=False,
            time_to_live_attribute="ttl",
        )

        # Add tags to tables for easy identification during cleanup
        Tags.of(self.metadata_table).add("TestResource", "true")
        Tags.of(self.status_table).add("TestResource", "true")


class TestCleanup:
    """Utility class for cleaning up test resources.

    Provides methods to identify and delete test stacks and resources
    based on tags and naming conventions.

    Usage:
        # List old test stacks
        cleanup = TestCleanup(region="us-east-1")
        stacks = cleanup.list_test_stacks(max_age_hours=24)

        # Dry run to see what would be deleted
        result = cleanup.cleanup_old_test_resources(dry_run=True)

        # Actually delete old resources
        result = cleanup.cleanup_old_test_resources(dry_run=False)

    Note:
        This class identifies test resources by naming convention:
        - Stacks: Contains "test" (case-insensitive) and "AgentFramework"
        - Tables: Contains "-test-" and either "AgentMetadata" or "AgentStatus"
    """

    def __init__(self, region: str | None = None):
        """Initialize cleanup utility.

        Args:
            region: AWS region (defaults to AWS_REGION env var or us-east-1)

        Note:
            Requires AWS credentials with CloudFormation and DynamoDB permissions.
        """
        import boto3

        self.region = region or os.getenv("AWS_REGION", "us-east-1")
        self.cloudformation = boto3.client("cloudformation", region_name=self.region)
        self.dynamodb = boto3.client("dynamodb", region_name=self.region)
        logger.info(f"Initialized TestCleanup for region '{self.region}'")

    def list_test_stacks(self, max_age_hours: int = 24) -> list[dict[str, Any]]:
        """List test stacks that can be cleaned up.

        Args:
            max_age_hours: Maximum age in hours for stacks to keep

        Returns:
            List of stack info dicts with name and creation time
        """
        stacks = []
        paginator = self.cloudformation.get_paginator("list_stacks")

        for page in paginator.paginate(
            StackStatusFilter=[
                "CREATE_COMPLETE",
                "UPDATE_COMPLETE",
                "ROLLBACK_COMPLETE",
            ]
        ):
            for stack in page.get("StackSummaries", []):
                stack_name = stack["StackName"]

                # Check if it's a test stack by naming convention
                if "test" in stack_name.lower() and "AgentFramework" in stack_name:
                    creation_time = stack["CreationTime"]
                    age_hours = (
                        datetime.now(UTC) - creation_time.replace(tzinfo=UTC)
                    ).total_seconds() / 3600

                    if age_hours > max_age_hours:
                        stacks.append(
                            {
                                "name": stack_name,
                                "creation_time": creation_time.isoformat(),
                                "age_hours": round(age_hours, 1),
                            }
                        )

        return stacks

    def delete_test_stack(self, stack_name: str) -> bool:
        """Delete a test stack.

        Args:
            stack_name: Name of the stack to delete

        Returns:
            True if deletion initiated successfully
        """
        try:
            self.cloudformation.delete_stack(StackName=stack_name)
        except ClientError:
            logger.exception(f"Failed to delete stack {stack_name}")
            return False
        else:
            logger.info(f"Initiated deletion of stack '{stack_name}'")
            return True

    def list_test_tables(self) -> list[str]:
        """List DynamoDB tables created for testing.

        Returns:
            List of table names matching test naming pattern
        """
        test_tables = []
        paginator = self.dynamodb.get_paginator("list_tables")

        for page in paginator.paginate():
            for table_name in page.get("TableNames", []):
                if "-test-" in table_name and (
                    "AgentMetadata" in table_name or "AgentStatus" in table_name
                ):
                    test_tables.append(table_name)

        return test_tables

    def delete_test_table(self, table_name: str) -> bool:
        """Delete a test DynamoDB table.

        Args:
            table_name: Name of the table to delete

        Returns:
            True if deletion initiated successfully
        """
        try:
            self.dynamodb.delete_table(TableName=table_name)
        except ClientError:
            logger.exception(f"Failed to delete table {table_name}")
            return False
        else:
            logger.info(f"Initiated deletion of table '{table_name}'")
            return True

    def cleanup_old_test_resources(
        self, max_age_hours: int = 24, dry_run: bool = True
    ) -> dict[str, list[str]]:
        """Clean up old test resources.

        Args:
            max_age_hours: Maximum age in hours for resources to keep
            dry_run: If True, only list resources without deleting

        Returns:
            Dict with lists of deleted/to-be-deleted stacks and tables
        """
        result = {
            "stacks": [],
            "tables": [],
        }

        # Clean up stacks
        stacks = self.list_test_stacks(max_age_hours)
        for stack in stacks:
            stack_name = stack["name"]
            result["stacks"].append(stack_name)
            if not dry_run:
                self.delete_test_stack(stack_name)

        # Clean up orphaned tables
        tables = self.list_test_tables()
        for table_name in tables:
            result["tables"].append(table_name)
            if not dry_run:
                self.delete_test_table(table_name)

        return result
