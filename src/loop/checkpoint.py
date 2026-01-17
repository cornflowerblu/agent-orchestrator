"""Checkpoint manager for saving/loading loop state to/from DynamoDB.

This module implements checkpoint management functionality using DynamoDB
for persistence. Checkpoints enable loop recovery after interruptions.

Maps to:
- FR-005: Framework MUST provide checkpoint save helpers
- FR-006: Checkpoint MUST include iteration number, state, timestamp
- FR-012: Support loading state from DynamoDB for recovery
- SC-006: Recovery within one iteration of checkpoint
"""

import logging
import os
from typing import Any

import boto3
from botocore.exceptions import ClientError

from src.exceptions import CheckpointRecoveryError
from src.loop.models import Checkpoint, LoopState

logger = logging.getLogger(__name__)


class CheckpointManager:
    """Manages checkpoint save/load operations using DynamoDB.

    The CheckpointManager coordinates checkpoint operations with DynamoDB,
    providing methods to save loop state, load checkpoints, and list available
    checkpoints for a session.

    Table schema:
        - Partition key: session_id (S)
        - Sort key: iteration (N)
        - Attributes: checkpoint_data (M), checkpoint_id (S), timestamp (S)

    Example:
        manager = CheckpointManager(session_id="loop-123")

        # Save checkpoint every N iterations
        if loop_state.current_iteration % 5 == 0:
            checkpoint_id = manager.save_checkpoint(loop_state)

        # Load checkpoint for recovery
        try:
            loop_state = manager.load_checkpoint(iteration=10)
        except CheckpointRecoveryError:
            # Handle recovery failure
            pass
    """

    def __init__(
        self,
        session_id: str,
        region: str = "us-east-1",
        table_name: str | None = None,
    ):
        """Initialize CheckpointManager.

        Args:
            session_id: Loop session ID for checkpoint storage
            region: AWS region for DynamoDB (default: us-east-1)
            table_name: DynamoDB table name (default: from env CHECKPOINT_TABLE_NAME
                       or "LoopCheckpoints")
        """
        self.session_id = session_id
        self.region = region
        self.table_name = table_name or os.getenv(
            "CHECKPOINT_TABLE_NAME", "LoopCheckpoints"
        )
        self._dynamodb: Any | None = None
        self._table: Any | None = None

    def create_table(self) -> Any:
        """Create or get DynamoDB table for checkpoint storage.

        Maps to T064: Implement CheckpointManager.create_memory().
        (Renamed from create_memory to create_table for DynamoDB)

        Returns:
            DynamoDB Table resource

        Raises:
            CheckpointRecoveryError: If table creation or access fails
        """
        if self._table is None:
            try:
                if self._dynamodb is None:
                    self._dynamodb = boto3.resource("dynamodb", region_name=self.region)

                self._table = self._dynamodb.Table(self.table_name)
                # Verify table exists by loading metadata
                self._table.load()
                logger.info(f"Connected to DynamoDB table {self.table_name}")
            except ClientError as e:
                error_msg = f"Failed to access DynamoDB table {self.table_name}: {e}"
                logger.error(error_msg)
                raise CheckpointRecoveryError(
                    checkpoint_id="N/A",
                    reason=error_msg,
                    session_id=self.session_id,
                ) from e

        return self._table

    def save_checkpoint(self, loop_state: LoopState) -> str:
        """Save checkpoint to DynamoDB.

        Maps to T065: Implement CheckpointManager.save_checkpoint().
        Maps to FR-005: Framework MUST provide checkpoint save helpers.
        Maps to FR-006: Checkpoint MUST include iteration number, state, timestamp.

        Args:
            loop_state: Current loop state to checkpoint

        Returns:
            Checkpoint ID for the saved checkpoint
        """
        # Ensure table is initialized
        if self._table is None:
            self.create_table()

        # Create checkpoint from loop state
        checkpoint = Checkpoint.from_loop_state(loop_state)

        # Store checkpoint in DynamoDB
        try:
            self._table.put_item(  # type: ignore[union-attr]
                Item={
                    "session_id": self.session_id,
                    "iteration": loop_state.current_iteration,
                    "checkpoint_id": checkpoint.checkpoint_id,
                    "checkpoint_data": checkpoint.model_dump(),
                }
            )
            logger.debug(
                f"Saved checkpoint {checkpoint.checkpoint_id} "
                f"for session {self.session_id} at iteration {loop_state.current_iteration}"
            )
        except ClientError as e:
            error_msg = f"Failed to save checkpoint: {e}"
            logger.error(error_msg)
            raise CheckpointRecoveryError(
                checkpoint_id=checkpoint.checkpoint_id,
                reason=error_msg,
                session_id=self.session_id,
            ) from e

        return checkpoint.checkpoint_id

    def load_checkpoint(self, iteration: int) -> LoopState:
        """Load checkpoint from DynamoDB.

        Maps to T066: Implement CheckpointManager.load_checkpoint().
        Maps to FR-012: Support loading state from DynamoDB for recovery.
        Maps to SC-006: Recovery within one iteration of checkpoint.

        Args:
            iteration: Iteration number of checkpoint to load

        Returns:
            LoopState reconstructed from checkpoint

        Raises:
            CheckpointRecoveryError: If checkpoint not found or invalid
        """
        # Ensure table is initialized
        if self._table is None:
            self.create_table()

        # Load checkpoint from DynamoDB
        try:
            response = self._table.get_item(  # type: ignore[union-attr]
                Key={"session_id": self.session_id, "iteration": iteration}
            )

            if "Item" not in response:
                raise CheckpointRecoveryError(
                    checkpoint_id=f"{self.session_id}/{iteration}",
                    reason="Checkpoint not found in DynamoDB",
                    session_id=self.session_id,
                )

            # Extract checkpoint data
            checkpoint_data = response["Item"]["checkpoint_data"]

            # Reconstruct checkpoint and loop state
            checkpoint = Checkpoint(**checkpoint_data)
            return checkpoint.to_loop_state()
        except CheckpointRecoveryError:
            raise
        except Exception as e:
            raise CheckpointRecoveryError(
                checkpoint_id=f"{self.session_id}/{iteration}",
                reason=f"Invalid checkpoint data: {e!s}",
                session_id=self.session_id,
            ) from e

    def list_checkpoints(self) -> list[dict[str, Any]]:
        """List all checkpoints for this session.

        Maps to T067: Implement CheckpointManager.list_checkpoints().

        Returns:
            List of checkpoint metadata dictionaries containing:
            - iteration: Checkpoint iteration number
            - checkpoint_id: Unique checkpoint identifier
            - timestamp: When checkpoint was created
        """
        # Ensure table is initialized
        if self._table is None:
            self.create_table()

        # Query all checkpoints for this session
        try:
            response = self._table.query(  # type: ignore[union-attr]
                KeyConditionExpression="session_id = :sid",
                ExpressionAttributeValues={":sid": self.session_id},
            )

            # Format response to match expected interface
            checkpoints = []
            for item in response.get("Items", []):
                checkpoints.append(
                    {
                        "iteration": item["iteration"],
                        "checkpoint_id": item.get("checkpoint_id"),
                        "session_id": item["session_id"],
                    }
                )

            return checkpoints
        except ClientError as e:
            error_msg = f"Failed to list checkpoints: {e}"
            logger.error(error_msg)
            # Return empty list instead of raising to be more forgiving
            return []
