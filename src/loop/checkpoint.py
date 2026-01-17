"""Checkpoint manager for saving/loading loop state.

This module implements checkpoint management with a hybrid storage approach:
1. Try AgentCore Memory first (preferred when available)
2. Fall back to DynamoDB when Memory service is unavailable

Maps to:
- FR-005: Framework MUST provide checkpoint save helpers
- FR-006: Checkpoint MUST include iteration number, state, timestamp
- FR-012: Support loading state from Memory for recovery
- SC-006: Recovery within one iteration of checkpoint
"""

import json
import logging
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import boto3
from botocore.exceptions import ClientError

from src.exceptions import CheckpointRecoveryError
from src.loop.models import Checkpoint, LoopState

logger = logging.getLogger(__name__)


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal types from DynamoDB."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super().default(obj)


def _convert_floats_to_decimal(obj: Any) -> Any:
    """Convert floats to Decimals for DynamoDB compatibility."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: _convert_floats_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_floats_to_decimal(v) for v in obj]
    return obj


class CheckpointManager:
    """Manages checkpoint save/load operations with hybrid storage.

    Storage strategy:
        1. Attempts AgentCore Memory first (future-proof)
        2. Falls back to DynamoDB when Memory is unavailable
        3. Caches which backend is working to avoid repeated failures

    DynamoDB schema (LoopCheckpoints table):
        - partition_key: session_id (String)
        - sort_key: iteration (Number)
        - checkpoint_data: Full checkpoint as JSON
        - agent_name: Agent identifier
        - created_at: ISO timestamp

    Example:
        manager = CheckpointManager(session_id="loop-123", agent_name="my-agent")

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
        agent_name: str = "loop-agent",
        region: str | None = None,
        memory_name: str | None = None,
        table_name: str | None = None,
    ):
        """Initialize CheckpointManager.

        Args:
            session_id: Loop session ID for checkpoint storage
            agent_name: Name of the agent (used as actor_id in Memory)
            region: AWS region (default: from env or us-east-1)
            memory_name: Memory store name (default: from env or "LoopCheckpoints")
            table_name: DynamoDB table name (default: from env or "LoopCheckpoints")
        """
        self.session_id = session_id
        self.agent_name = agent_name
        self.region = region or os.getenv("AWS_REGION", "us-east-1")
        self.memory_name = memory_name or os.getenv(
            "CHECKPOINT_MEMORY_NAME", "LoopCheckpoints"
        )
        self.table_name = table_name or os.getenv(
            "CHECKPOINT_TABLE_NAME", "LoopCheckpoints"
        )

        # Lazy-initialized clients
        self._memory_client: Any | None = None
        self._dynamodb_client: Any | None = None
        self._dynamodb_table: Any | None = None
        self._memory_id: str | None = None

        # Track which backend to use (None = not yet determined)
        # Can be forced via CHECKPOINT_BACKEND env var ("dynamodb" or "memory")
        force_backend = os.getenv("CHECKPOINT_BACKEND", "").lower()
        if force_backend == "dynamodb":
            self._use_memory: bool | None = False
            logger.info("Forced DynamoDB backend via CHECKPOINT_BACKEND env var")
        elif force_backend == "memory":
            self._use_memory = True
            logger.info("Forced Memory backend via CHECKPOINT_BACKEND env var")
        else:
            self._use_memory = None

    def _get_dynamodb_table(self) -> Any:
        """Get or create the DynamoDB table resource.

        Returns:
            DynamoDB Table resource
        """
        if self._dynamodb_table is None:
            dynamodb = boto3.resource("dynamodb", region_name=self.region)
            self._dynamodb_table = dynamodb.Table(self.table_name)
            logger.info(f"Connected to DynamoDB table {self.table_name}")
        return self._dynamodb_table

    def _try_memory_client(self) -> Any | None:
        """Try to get the Memory client, return None if unavailable.

        Returns:
            MemoryClient instance or None if not available
        """
        if self._memory_client is not None:
            return self._memory_client

        try:
            from bedrock_agentcore.memory.client import MemoryClient

            self._memory_client = MemoryClient(
                region_name=self.region,
                integration_source="agent-orchestrator",
            )
            logger.info(f"Created MemoryClient for region {self.region}")
            return self._memory_client
        except ImportError:
            logger.info("bedrock_agentcore.memory not available, using DynamoDB")
            return None
        except Exception as e:
            logger.warning(f"Failed to create MemoryClient: {e}, using DynamoDB")
            return None

    def _try_create_memory(self, timeout_seconds: int = 10) -> str | None:
        """Try to create/get Memory store, return None if unavailable.

        Args:
            timeout_seconds: Max time to wait for Memory service (default: 10s)

        Returns:
            Memory ID or None if Memory service unavailable
        """
        if self._memory_id is not None:
            return self._memory_id

        client = self._try_memory_client()
        if client is None:
            return None

        import concurrent.futures

        def _create_memory() -> str | None:
            result = client.create_or_get_memory(
                name=self.memory_name,
                description="Loop checkpoint storage for agent orchestrator",
                event_expiry_days=7,
            )
            return result.get("memoryId") or result.get("memory_id")

        try:
            # Use ThreadPoolExecutor to add timeout to the blocking call
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_create_memory)
                self._memory_id = future.result(timeout=timeout_seconds)

            if self._memory_id:
                logger.info(f"Connected to Memory store {self.memory_name}")
                return self._memory_id
        except concurrent.futures.TimeoutError:
            logger.warning(
                f"Memory service timed out after {timeout_seconds}s, falling back to DynamoDB"
            )
        except Exception as e:
            logger.warning(f"Memory service unavailable: {e}, falling back to DynamoDB")

        return None

    def _determine_backend(self) -> bool:
        """Determine which backend to use.

        Returns:
            True if using Memory, False if using DynamoDB
        """
        if self._use_memory is not None:
            return self._use_memory

        # Try Memory first
        memory_id = self._try_create_memory()
        self._use_memory = memory_id is not None

        if self._use_memory:
            logger.info("Using AgentCore Memory for checkpoints")
        else:
            logger.info("Using DynamoDB for checkpoints")

        return self._use_memory

    def save_checkpoint(self, loop_state: LoopState) -> str:
        """Save checkpoint to storage.

        Maps to T065: Implement CheckpointManager.save_checkpoint().
        Maps to FR-005: Framework MUST provide checkpoint save helpers.
        Maps to FR-006: Checkpoint MUST include iteration number, state, timestamp.

        Args:
            loop_state: Current loop state to checkpoint

        Returns:
            Checkpoint ID for the saved checkpoint
        """
        checkpoint = Checkpoint.from_loop_state(loop_state)

        if self._determine_backend():
            return self._save_to_memory(checkpoint, loop_state)
        else:
            return self._save_to_dynamodb(checkpoint, loop_state)

    def _save_to_memory(self, checkpoint: Checkpoint, loop_state: LoopState) -> str:
        """Save checkpoint to AgentCore Memory."""
        try:
            client = self._try_memory_client()
            if client is None:
                raise Exception("Memory client unavailable")

            blob_data = {
                "checkpoint_id": checkpoint.checkpoint_id,
                "iteration": checkpoint.iteration,
                "checkpoint_data": checkpoint.model_dump(),
            }

            # Serialize as JSON string to avoid SDK's weird serialization
            client.create_blob_event(
                memory_id=self._memory_id,
                actor_id=self.agent_name,
                session_id=self.session_id,
                blob_data=json.dumps(blob_data),
            )

            logger.debug(
                f"Saved checkpoint {checkpoint.checkpoint_id} to Memory "
                f"at iteration {loop_state.current_iteration}"
            )
            return checkpoint.checkpoint_id

        except Exception as e:
            logger.warning(f"Memory save failed: {e}, falling back to DynamoDB")
            self._use_memory = False
            return self._save_to_dynamodb(checkpoint, loop_state)

    def _save_to_dynamodb(self, checkpoint: Checkpoint, loop_state: LoopState) -> str:
        """Save checkpoint to DynamoDB."""
        try:
            table = self._get_dynamodb_table()

            # Convert checkpoint data for DynamoDB (handle floats -> Decimal)
            checkpoint_data = _convert_floats_to_decimal(checkpoint.model_dump())

            item = {
                "session_id": self.session_id,
                "iteration": loop_state.current_iteration,
                "checkpoint_id": checkpoint.checkpoint_id,
                "agent_name": self.agent_name,
                "checkpoint_data": checkpoint_data,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            table.put_item(Item=item)

            logger.debug(
                f"Saved checkpoint {checkpoint.checkpoint_id} to DynamoDB "
                f"at iteration {loop_state.current_iteration}"
            )
            return checkpoint.checkpoint_id

        except ClientError as e:
            error_msg = f"Failed to save checkpoint to DynamoDB: {e}"
            logger.exception(error_msg)
            raise CheckpointRecoveryError(
                checkpoint_id=checkpoint.checkpoint_id,
                reason=error_msg,
                session_id=self.session_id,
            ) from e

    def load_checkpoint(self, iteration: int) -> LoopState:
        """Load checkpoint from storage.

        Maps to T066: Implement CheckpointManager.load_checkpoint().
        Maps to FR-012: Support loading state from Memory for recovery.

        Args:
            iteration: Iteration number of checkpoint to load

        Returns:
            LoopState reconstructed from checkpoint

        Raises:
            CheckpointRecoveryError: If checkpoint not found or invalid
        """
        if self._determine_backend():
            return self._load_from_memory(iteration)
        else:
            return self._load_from_dynamodb(iteration)

    def _load_from_memory(self, iteration: int) -> LoopState:
        """Load checkpoint from AgentCore Memory."""
        try:
            client = self._try_memory_client()
            if client is None:
                raise Exception("Memory client unavailable")

            events = client.list_events(
                memory_id=self._memory_id,
                actor_id=self.agent_name,
                session_id=self.session_id,
                include_payload=True,
            )

            for event in events:
                # Handle various response formats from Memory service
                payload = event.get("payload") or event.get("blobData") or event.get("data") or {}

                # If payload is a list, extract blob data
                if isinstance(payload, list) and len(payload) > 0:
                    first_item = payload[0]
                    if isinstance(first_item, dict):
                        # Check for 'blob' key (SDK wraps data this way)
                        if "blob" in first_item:
                            payload = first_item["blob"]
                        elif "iteration" in first_item:
                            payload = first_item

                # Parse JSON string
                if isinstance(payload, str):
                    try:
                        payload = json.loads(payload)
                    except json.JSONDecodeError:
                        # Not valid JSON, skip this event
                        continue

                if not isinstance(payload, dict):
                    continue

                if payload.get("iteration") == iteration:
                    checkpoint_data = payload.get("checkpoint_data", {})
                    checkpoint = Checkpoint(**checkpoint_data)
                    logger.info(f"Loaded checkpoint from Memory at iteration {iteration}")
                    return checkpoint.to_loop_state()

            raise CheckpointRecoveryError(
                checkpoint_id=f"{self.session_id}/{iteration}",
                reason="Checkpoint not found in Memory",
                session_id=self.session_id,
            )

        except CheckpointRecoveryError:
            raise
        except Exception as e:
            logger.warning(f"Memory load failed: {e}, trying DynamoDB")
            self._use_memory = False
            return self._load_from_dynamodb(iteration)

    def _load_from_dynamodb(self, iteration: int) -> LoopState:
        """Load checkpoint from DynamoDB."""
        try:
            table = self._get_dynamodb_table()

            response = table.get_item(
                Key={
                    "session_id": self.session_id,
                    "iteration": iteration,
                }
            )

            item = response.get("Item")
            if not item:
                raise CheckpointRecoveryError(
                    checkpoint_id=f"{self.session_id}/{iteration}",
                    reason="Checkpoint not found in DynamoDB",
                    session_id=self.session_id,
                )

            # Convert Decimals back to native types
            checkpoint_data = json.loads(
                json.dumps(item.get("checkpoint_data", {}), cls=DecimalEncoder)
            )
            checkpoint = Checkpoint(**checkpoint_data)
            logger.info(f"Loaded checkpoint from DynamoDB at iteration {iteration}")
            return checkpoint.to_loop_state()

        except CheckpointRecoveryError:
            raise
        except ClientError as e:
            raise CheckpointRecoveryError(
                checkpoint_id=f"{self.session_id}/{iteration}",
                reason=f"Failed to load from DynamoDB: {e}",
                session_id=self.session_id,
            ) from e

    def load_latest_checkpoint(self) -> LoopState | None:
        """Load the most recent checkpoint for this session.

        Returns:
            LoopState from latest checkpoint, or None if no checkpoints exist
        """
        checkpoints = self.list_checkpoints()
        if not checkpoints:
            return None

        latest = max(checkpoints, key=lambda c: c.get("iteration", 0))
        iteration = latest.get("iteration")

        if iteration is not None:
            return self.load_checkpoint(iteration)

        return None

    def list_checkpoints(self) -> list[dict[str, Any]]:
        """List all checkpoints for this session.

        Maps to T067: Implement CheckpointManager.list_checkpoints().

        Returns:
            List of checkpoint metadata dictionaries
        """
        if self._determine_backend():
            return self._list_from_memory()
        else:
            return self._list_from_dynamodb()

    def _list_from_memory(self) -> list[dict[str, Any]]:
        """List checkpoints from AgentCore Memory."""
        try:
            client = self._try_memory_client()
            if client is None:
                return self._list_from_dynamodb()

            events = client.list_events(
                memory_id=self._memory_id,
                actor_id=self.agent_name,
                session_id=self.session_id,
                include_payload=True,
            )

            checkpoints = []
            for event in events:
                # Handle various response formats from Memory service
                payload = event.get("payload") or event.get("blobData") or event.get("data") or {}

                # If payload is a list, extract blob data
                if isinstance(payload, list) and len(payload) > 0:
                    first_item = payload[0]
                    if isinstance(first_item, dict):
                        # Check for 'blob' key (SDK wraps data this way)
                        if "blob" in first_item:
                            payload = first_item["blob"]
                        elif "iteration" in first_item:
                            payload = first_item

                # Parse JSON string
                if isinstance(payload, str):
                    try:
                        payload = json.loads(payload)
                    except json.JSONDecodeError:
                        continue

                if not isinstance(payload, dict):
                    continue

                if "iteration" in payload:
                    checkpoints.append(
                        {
                            "iteration": payload["iteration"],
                            "checkpoint_id": payload.get("checkpoint_id"),
                            "session_id": self.session_id,
                            "timestamp": event.get("eventTimestamp"),
                        }
                    )

            return checkpoints

        except Exception as e:
            logger.warning(f"Memory list failed: {e}, trying DynamoDB")
            self._use_memory = False
            return self._list_from_dynamodb()

    def _list_from_dynamodb(self) -> list[dict[str, Any]]:
        """List checkpoints from DynamoDB."""
        try:
            table = self._get_dynamodb_table()

            response = table.query(
                KeyConditionExpression="session_id = :sid",
                ExpressionAttributeValues={":sid": self.session_id},
                ProjectionExpression="iteration, checkpoint_id, created_at",
            )

            checkpoints = []
            for item in response.get("Items", []):
                checkpoints.append(
                    {
                        "iteration": int(item.get("iteration", 0)),
                        "checkpoint_id": item.get("checkpoint_id"),
                        "session_id": self.session_id,
                        "timestamp": item.get("created_at"),
                    }
                )

            return checkpoints

        except ClientError as e:
            logger.warning(f"Failed to list checkpoints from DynamoDB: {e}")
            return []


# Backwards compatibility alias
CheckpointManagerDynamoDB = CheckpointManager
