"""Unit tests for LoopFramework.

T037: Tests for LoopFramework initialization
T038: Tests for LoopFramework.run()
T039: Tests for loop termination conditions
T040: Tests for re-entry prevention
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.loop.framework import LoopFramework
from src.loop.models import (
    ExitConditionConfig,
    ExitConditionType,
    LoopConfig,
    LoopPhase,
    LoopState,
)


# =============================================================================
# T037: LoopFramework Initialization Tests
# =============================================================================


class TestLoopFrameworkInitialization:
    """Tests for LoopFramework initialization (T025, T026, T027)."""

    @pytest.mark.asyncio
    async def test_initialize_async_minimal_config(self) -> None:
        """Test async initialization with minimal config."""
        config = LoopConfig(
            agent_name="test-agent",
            max_iterations=50,
        )

        framework = await LoopFramework.initialize(config)

        assert framework is not None
        assert framework.config == config
        assert framework.state is not None
        assert framework.state.agent_name == "test-agent"
        assert framework.state.max_iterations == 50
        assert framework.state.phase == LoopPhase.INITIALIZING
        assert isinstance(framework.state.session_id, str)

    @pytest.mark.asyncio
    async def test_initialize_async_with_session_id(self) -> None:
        """Test async initialization with provided session_id."""
        session_id = "custom-session-123"
        config = LoopConfig(
            agent_name="test-agent",
            max_iterations=50,
            session_id=session_id,
        )

        framework = await LoopFramework.initialize(config)

        assert framework.state.session_id == session_id

    @pytest.mark.asyncio
    async def test_initialize_async_auto_generates_session_id(self) -> None:
        """Test async initialization auto-generates session_id if not provided."""
        config = LoopConfig(
            agent_name="test-agent",
            max_iterations=50,
        )

        framework = await LoopFramework.initialize(config)

        # Should be a valid UUID format
        assert framework.state.session_id is not None
        assert len(framework.state.session_id) > 0
        # Try to parse as UUID to verify format
        uuid.UUID(framework.state.session_id)

    @pytest.mark.asyncio
    async def test_initialize_async_with_exit_conditions(self) -> None:
        """Test async initialization with exit conditions."""
        config = LoopConfig(
            agent_name="test-agent",
            max_iterations=50,
            exit_conditions=[
                ExitConditionConfig(type=ExitConditionType.ALL_TESTS_PASS),
                ExitConditionConfig(type=ExitConditionType.LINTING_CLEAN),
            ],
        )

        framework = await LoopFramework.initialize(config)

        assert len(framework.state.exit_conditions) == 2
        assert framework.state.exit_conditions[0].type == ExitConditionType.ALL_TESTS_PASS
        assert framework.state.exit_conditions[1].type == ExitConditionType.LINTING_CLEAN

    def test_initialize_sync_minimal_config(self) -> None:
        """Test sync initialization with minimal config."""
        config = LoopConfig(
            agent_name="test-agent",
            max_iterations=50,
        )

        framework = LoopFramework.initialize_sync(config)

        assert framework is not None
        assert framework.config == config
        assert framework.state is not None
        assert framework.state.agent_name == "test-agent"
        assert framework.state.max_iterations == 50

    def test_initialize_sync_with_session_id(self) -> None:
        """Test sync initialization with provided session_id."""
        session_id = "sync-session-456"
        config = LoopConfig(
            agent_name="test-agent",
            max_iterations=50,
            session_id=session_id,
        )

        framework = LoopFramework.initialize_sync(config)

        assert framework.state.session_id == session_id

    def test_initialize_sync_auto_generates_session_id(self) -> None:
        """Test sync initialization auto-generates session_id if not provided."""
        config = LoopConfig(
            agent_name="test-agent",
            max_iterations=50,
        )

        framework = LoopFramework.initialize_sync(config)

        # Should be a valid UUID format
        assert framework.state.session_id is not None
        uuid.UUID(framework.state.session_id)

    @pytest.mark.asyncio
    async def test_initialize_sets_up_tracer(self) -> None:
        """Test that initialization sets up OTEL tracer (T034)."""
        config = LoopConfig(
            agent_name="test-agent",
            max_iterations=50,
        )

        framework = await LoopFramework.initialize(config)

        assert framework.tracer is not None

    def test_get_state(self) -> None:
        """Test get_state() method returns current state (T029)."""
        config = LoopConfig(
            agent_name="test-agent",
            max_iterations=50,
        )

        framework = LoopFramework.initialize_sync(config)
        state = framework.get_state()

        assert state is not None
        assert isinstance(state, LoopState)
        assert state.agent_name == "test-agent"
        assert state.max_iterations == 50

    def test_get_exit_condition_status(self) -> None:
        """Test get_exit_condition_status() method (T030)."""
        config = LoopConfig(
            agent_name="test-agent",
            max_iterations=50,
            exit_conditions=[
                ExitConditionConfig(type=ExitConditionType.ALL_TESTS_PASS),
            ],
        )

        framework = LoopFramework.initialize_sync(config)
        conditions = framework.get_exit_condition_status()

        assert len(conditions) == 1
        assert conditions[0].type == ExitConditionType.ALL_TESTS_PASS

    def test_get_exit_condition_status_empty(self) -> None:
        """Test get_exit_condition_status() with no conditions."""
        config = LoopConfig(
            agent_name="test-agent",
            max_iterations=50,
            exit_conditions=[],
        )

        framework = LoopFramework.initialize_sync(config)
        conditions = framework.get_exit_condition_status()

        assert conditions == []
