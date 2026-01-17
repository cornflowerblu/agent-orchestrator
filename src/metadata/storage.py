"""DynamoDB storage layer for agent custom metadata.

Task T061: Add consultation requirements to CustomAgentMetadata storage
"""

import os
from datetime import UTC, datetime
from typing import Any

import boto3
from botocore.exceptions import ClientError

from src.consultation.rules import ConsultationRequirement
from src.exceptions import AgentNotFoundError, ValidationError
from src.logging_config import get_logger
from src.metadata.models import CustomAgentMetadata

logger = get_logger(__name__)


class MetadataStorage:
    """
    DynamoDB storage for agent custom metadata.

    Handles CRUD operations for CustomAgentMetadata records.
    """

    def __init__(self, table_name: str | None = None, region: str | None = None):
        """
        Initialize metadata storage.

        Args:
            table_name: DynamoDB table name (defaults to AGENT_METADATA_TABLE env var)
            region: AWS region (defaults to AWS_REGION env var or us-east-1)
        """
        self.table_name = table_name or os.getenv("AGENT_METADATA_TABLE", "AgentMetadata")
        self.region = region or os.getenv("AWS_REGION", "us-east-1")

        self.dynamodb = boto3.resource("dynamodb", region_name=self.region)
        self.table = self.dynamodb.Table(self.table_name)

        logger.info(f"Initialized metadata storage for table '{self.table_name}'")

    def put_metadata(self, metadata: CustomAgentMetadata) -> dict[str, Any]:
        """
        Create or update agent custom metadata.

        Args:
            metadata: CustomAgentMetadata to store

        Returns:
            Stored metadata as dictionary

        Raises:
            ValidationError: If DynamoDB operation fails
        """
        try:
            # Update timestamp
            metadata.updated_at = datetime.now(UTC).isoformat()

            item = metadata.model_dump()

            logger.debug(f"Storing metadata for agent '{metadata.agent_name}'")

            self.table.put_item(Item=item)

            logger.info(f"Stored metadata for agent '{metadata.agent_name}' v{metadata.version}")

            return item

        except ClientError as e:
            logger.exception(f"Failed to store metadata: {e}")
            raise ValidationError(
                f"Failed to store metadata for '{metadata.agent_name}'",
                details={"error": str(e)},
            ) from e

    def get_metadata(self, agent_name: str) -> CustomAgentMetadata:
        """
        Retrieve agent custom metadata.

        Args:
            agent_name: Agent name to lookup

        Returns:
            CustomAgentMetadata for the agent

        Raises:
            AgentNotFoundError: If agent metadata doesn't exist
        """
        try:
            logger.debug(f"Retrieving metadata for agent '{agent_name}'")

            response = self.table.get_item(Key={"agent_name": agent_name})

            if "Item" not in response:
                raise AgentNotFoundError(agent_name)

            metadata = CustomAgentMetadata(**response["Item"])

            logger.info(f"Retrieved metadata for agent '{agent_name}' version {metadata.version}")

            return metadata

        except ClientError as e:
            logger.exception(f"Failed to retrieve metadata: {e}")
            raise ValidationError(
                f"Failed to retrieve metadata for '{agent_name}'", details={"error": str(e)}
            ) from e

    def delete_metadata(self, agent_name: str) -> None:
        """
        Delete agent custom metadata.

        Args:
            agent_name: Agent name to delete

        Raises:
            ValidationError: If DynamoDB operation fails
        """
        try:
            logger.debug(f"Deleting metadata for agent '{agent_name}'")

            self.table.delete_item(Key={"agent_name": agent_name})

            logger.info(f"Deleted metadata for agent '{agent_name}'")

        except ClientError as e:
            logger.exception(f"Failed to delete metadata: {e}")
            raise ValidationError(
                f"Failed to delete metadata for '{agent_name}'", details={"error": str(e)}
            ) from e

    def list_all_metadata(self) -> list[CustomAgentMetadata]:
        """
        List all agent custom metadata records.

        Returns:
            List of CustomAgentMetadata for all agents

        Raises:
            ValidationError: If DynamoDB scan fails
        """
        try:
            logger.debug("Scanning all agent metadata")

            response = self.table.scan()
            items = response.get("Items", [])

            # Handle pagination
            while "LastEvaluatedKey" in response:
                response = self.table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
                items.extend(response.get("Items", []))

            metadata_list = [CustomAgentMetadata(**item) for item in items]

            logger.info(f"Retrieved {len(metadata_list)} metadata records")

            return metadata_list

        except ClientError as e:
            logger.exception(f"Failed to list metadata: {e}")
            raise ValidationError("Failed to list agent metadata", details={"error": str(e)}) from e

    def update_consultation_requirements(
        self, agent_name: str, requirements: list[ConsultationRequirement]
    ) -> CustomAgentMetadata:
        """
        Update consultation requirements for an agent.

        Task T061: Add consultation requirements to CustomAgentMetadata storage

        Args:
            agent_name: Agent name to update
            requirements: List of consultation requirements to set

        Returns:
            Updated CustomAgentMetadata

        Raises:
            AgentNotFoundError: If agent metadata doesn't exist
            ValidationError: If DynamoDB operation fails
        """
        try:
            # Get existing metadata
            metadata = self.get_metadata(agent_name)

            # Convert requirements to dict for storage
            metadata.consultation_requirements = [req.model_dump() for req in requirements]

            # Save updated metadata
            self.put_metadata(metadata)

            logger.info(
                f"Updated {len(requirements)} consultation requirements for agent '{agent_name}'"
            )

            return metadata

        except AgentNotFoundError:
            raise
        except ClientError as e:
            logger.exception(f"Failed to update consultation requirements: {e}")
            raise ValidationError(
                f"Failed to update consultation requirements for '{agent_name}'",
                details={"error": str(e)},
            ) from e

    def get_consultation_requirements(self, agent_name: str) -> list[ConsultationRequirement]:
        """
        Get consultation requirements for an agent.

        Task T061: Add consultation requirements to CustomAgentMetadata storage

        Args:
            agent_name: Agent name to lookup

        Returns:
            List of ConsultationRequirement for the agent

        Raises:
            AgentNotFoundError: If agent metadata doesn't exist
        """
        metadata = self.get_metadata(agent_name)

        # Convert stored dicts back to ConsultationRequirement objects
        requirements = [
            ConsultationRequirement(**req) for req in metadata.consultation_requirements
        ]

        logger.debug(
            f"Retrieved {len(requirements)} consultation requirements for agent '{agent_name}'"
        )

        return requirements

    def add_consultation_requirement(
        self, agent_name: str, requirement: ConsultationRequirement
    ) -> CustomAgentMetadata:
        """
        Add a single consultation requirement to an agent.

        Task T061: Add consultation requirements to CustomAgentMetadata storage

        Args:
            agent_name: Agent name to update
            requirement: Consultation requirement to add

        Returns:
            Updated CustomAgentMetadata

        Raises:
            AgentNotFoundError: If agent metadata doesn't exist
            ValidationError: If DynamoDB operation fails
        """
        # Get existing requirements
        existing = self.get_consultation_requirements(agent_name)

        # Add new requirement
        existing.append(requirement)

        # Save all requirements
        return self.update_consultation_requirements(agent_name, existing)

    def remove_consultation_requirement(
        self, agent_name: str, requirement_agent_name: str
    ) -> CustomAgentMetadata:
        """
        Remove consultation requirements for a specific agent.

        Task T061: Add consultation requirements to CustomAgentMetadata storage

        Args:
            agent_name: Agent name to update
            requirement_agent_name: Name of agent whose requirements to remove

        Returns:
            Updated CustomAgentMetadata

        Raises:
            AgentNotFoundError: If agent metadata doesn't exist
            ValidationError: If DynamoDB operation fails
        """
        # Get existing requirements
        existing = self.get_consultation_requirements(agent_name)

        # Filter out requirements for the specified agent
        filtered = [r for r in existing if r.agent_name != requirement_agent_name]

        removed_count = len(existing) - len(filtered)
        if removed_count > 0:
            logger.info(
                f"Removing {removed_count} consultation requirements for "
                f"'{requirement_agent_name}' from agent '{agent_name}'"
            )

        # Save filtered requirements
        return self.update_consultation_requirements(agent_name, filtered)
