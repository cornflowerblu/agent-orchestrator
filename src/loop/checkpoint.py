"""Checkpoint manager for saving/loading loop state to/from Memory service.

This module implements checkpoint management functionality using AgentCore Memory
service for persistence. Checkpoints enable loop recovery after interruptions.

Maps to:
- FR-005: Framework MUST provide checkpoint save helpers
- FR-006: Checkpoint MUST include iteration number, state, timestamp
- FR-012: Support loading state from Memory for recovery
- SC-006: Recovery within one iteration of checkpoint
"""

from typing import Any

from src.exceptions import CheckpointRecoveryError
from src.loop.models import Checkpoint, LoopState


class CheckpointManager:
    """Manages checkpoint save/load operations using AgentCore Memory service.

    The CheckpointManager coordinates checkpoint operations with the Memory service,
    providing methods to save loop state, load checkpoints, and list available
    checkpoints for a session.

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

    def __init__(self, session_id: str, region: str = "us-east-1"):
        """Initialize CheckpointManager.

        Args:
            session_id: Loop session ID for checkpoint storage
            region: AWS region for Memory service (default: us-east-1)
        """
        self.session_id = session_id
        self.region = region
        self._memory: Any | None = None

    def create_memory(self) -> Any:
        """Create Memory service instance for checkpoint storage.

        Maps to T064: Implement CheckpointManager.create_memory().

        Returns:
            Memory service instance

        Note:
            This method initializes the AgentCore Memory service client.
            The actual Memory class will be imported from bedrock-agentcore
            when the SDK is available.
        """
        # TODO: Replace with actual Memory import when bedrock-agentcore is available
        # from bedrock_agentcore import Memory
        # self._memory = Memory(region=self.region)

        # For now, create a mock Memory object for testing
        class MockMemory:
            def __init__(self, region: str = "us-east-1"):
                self.region = region
                self._storage: dict[str, Any] = {}

            def put(self, key: str, value: dict[str, Any]) -> None:
                """Store checkpoint data."""
                self._storage[key] = value

            def get(self, key: str) -> dict[str, Any] | None:
                """Retrieve checkpoint data."""
                return self._storage.get(key)

            def list(self, prefix: str | None = None) -> list[dict[str, Any]]:
                """List checkpoint metadata."""
                if prefix:
                    return [v for k, v in self._storage.items() if k.startswith(prefix)]
                return list(self._storage.values())

        if self._memory is None:
            self._memory = MockMemory(region=self.region)

        return self._memory

    def save_checkpoint(self, loop_state: LoopState) -> str:
        """Save checkpoint to Memory service.

        Maps to T065: Implement CheckpointManager.save_checkpoint().
        Maps to FR-005: Framework MUST provide checkpoint save helpers.
        Maps to FR-006: Checkpoint MUST include iteration number, state, timestamp.

        Args:
            loop_state: Current loop state to checkpoint

        Returns:
            Checkpoint ID for the saved checkpoint
        """
        # Ensure Memory is initialized
        if self._memory is None:
            self.create_memory()

        # Create checkpoint from loop state
        checkpoint = Checkpoint.from_loop_state(loop_state)

        # Store checkpoint in Memory
        key = f"checkpoint/{self.session_id}/{loop_state.current_iteration}"
        self._memory.put(key=key, value=checkpoint.model_dump())  # type: ignore[union-attr]

        return checkpoint.checkpoint_id

    def load_checkpoint(self, iteration: int) -> LoopState:
        """Load checkpoint from Memory service.

        Maps to T066: Implement CheckpointManager.load_checkpoint().
        Maps to FR-012: Support loading state from Memory for recovery.
        Maps to SC-006: Recovery within one iteration of checkpoint.

        Args:
            iteration: Iteration number of checkpoint to load

        Returns:
            LoopState reconstructed from checkpoint

        Raises:
            CheckpointRecoveryError: If checkpoint not found or invalid
        """
        # Ensure Memory is initialized
        if self._memory is None:
            self.create_memory()

        # Load checkpoint from Memory
        key = f"checkpoint/{self.session_id}/{iteration}"
        checkpoint_data = self._memory.get(key=key)  # type: ignore[union-attr]

        if checkpoint_data is None:
            raise CheckpointRecoveryError(
                checkpoint_id=key,
                reason="Checkpoint not found in Memory",
                session_id=self.session_id,
            )

        # Reconstruct checkpoint and loop state
        try:
            checkpoint = Checkpoint(**checkpoint_data)
            return checkpoint.to_loop_state()
        except Exception as e:
            raise CheckpointRecoveryError(
                checkpoint_id=key,
                reason=f"Invalid checkpoint data: {e!s}",
                session_id=self.session_id,
            ) from e

    def list_checkpoints(self) -> list[dict[str, Any]]:
        """List all checkpoints for this session.

        Maps to T067: Implement CheckpointManager.list_checkpoints().

        Returns:
            List of checkpoint metadata dictionaries
        """
        # Ensure Memory is initialized
        if self._memory is None:
            self.create_memory()

        # List all checkpoints for this session
        prefix = f"checkpoint/{self.session_id}/"
        return self._memory.list(prefix=prefix)  # type: ignore[union-attr]
