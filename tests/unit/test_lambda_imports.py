"""Smoke tests to validate Lambda handlers can be imported.

These tests catch packaging/import issues before deploying to AWS.
If a handler can't be imported, the Lambda will fail at runtime.
"""

import pytest


@pytest.mark.unit
class TestLambdaImports:
    """Validate all Lambda handlers can be imported."""

    def test_registry_handlers_import(self):
        """Validate registry handlers can be imported."""
        from src.registry.handlers import (
            check_compatibility_handler,
            find_compatible_agents_handler,
            get_agent_handler,
            get_agent_status_handler,
            get_consultation_requirements_handler,
            list_agents_handler,
            update_agent_metadata_handler,
            update_agent_status_handler,
        )

        # Verify they're callable
        assert callable(list_agents_handler)
        assert callable(get_agent_handler)
        assert callable(update_agent_metadata_handler)
        assert callable(get_consultation_requirements_handler)
        assert callable(check_compatibility_handler)
        assert callable(find_compatible_agents_handler)
        assert callable(get_agent_status_handler)
        assert callable(update_agent_status_handler)

    def test_policy_enforcer_import(self):
        """Validate policy enforcer handler can be imported."""
        import importlib.util
        from pathlib import Path

        # Load module directly from file path
        lambda_file = (
            Path(__file__).resolve().parents[2]
            / "infrastructure"
            / "cdk"
            / "lambda"
            / "policy_enforcer.py"
        )
        assert lambda_file.exists(), f"Lambda file not found: {lambda_file}"

        spec = importlib.util.spec_from_file_location("policy_enforcer", lambda_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        assert hasattr(module, "handler")
        assert callable(module.handler)

    def test_tool_registry_import(self):
        """Validate tool registry handler can be imported."""
        import importlib.util
        from pathlib import Path

        # Load module directly from file path
        lambda_file = (
            Path(__file__).resolve().parents[2]
            / "infrastructure"
            / "cdk"
            / "lambda"
            / "tool_registry.py"
        )
        assert lambda_file.exists(), f"Lambda file not found: {lambda_file}"

        spec = importlib.util.spec_from_file_location("tool_registry", lambda_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        assert hasattr(module, "handler")
        assert callable(module.handler)

    def test_handler_signatures(self):
        """Validate handlers accept event and context parameters."""
        import inspect

        from src.registry.handlers import list_agents_handler

        sig = inspect.signature(list_agents_handler)
        params = list(sig.parameters.keys())

        # Lambda handlers must accept event and context
        assert "event" in params
        assert "context" in params
