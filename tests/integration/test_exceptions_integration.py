"""Integration tests for custom exceptions.

Tests exception initialization, attributes, and error messages.
"""

import pytest

from src.exceptions import (
    AgentFrameworkError,
    AgentNotFoundError,
    ConsultationRequiredError,
    DuplicateAgentError,
    IncompatibleTypeError,
    ToolUnavailableError,
    ValidationError,
)

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


class TestCustomExceptions:
    """Integration tests for all custom exceptions."""

    def test_agent_framework_error_base_class(self):
        """Test AgentFrameworkError base exception."""
        error = AgentFrameworkError("Framework error")
        assert str(error) == "Framework error"
        assert isinstance(error, Exception)

    def test_agent_not_found_error(self):
        """Test AgentNotFoundError initialization and message."""
        error = AgentNotFoundError("test-agent")
        assert "test-agent" in str(error)
        assert error.agent_name == "test-agent"
        assert isinstance(error, AgentFrameworkError)

    def test_validation_error(self):
        """Test ValidationError initialization."""
        error = ValidationError("Validation failed")
        assert str(error) == "Validation failed"
        assert isinstance(error, AgentFrameworkError)

        # Test with details
        error_with_details = ValidationError("Validation failed", details={"field": "name"})
        assert error_with_details.details == {"field": "name"}

    def test_consultation_required_error(self):
        """Test ConsultationRequiredError initialization."""
        error = ConsultationRequiredError("agent-1", "security-reviewer", "pre_execution")
        assert "agent-1" in str(error)
        assert "security-reviewer" in str(error)
        assert "pre_execution" in str(error)
        assert error.agent_name == "agent-1"
        assert error.required_consultation == "security-reviewer"
        assert error.phase == "pre_execution"
        assert isinstance(error, AgentFrameworkError)

    def test_duplicate_agent_error(self):
        """Test DuplicateAgentError initialization."""
        # Without version
        error = DuplicateAgentError("duplicate-agent")
        assert "duplicate-agent" in str(error)
        assert error.agent_name == "duplicate-agent"
        assert isinstance(error, AgentFrameworkError)

        # With version
        error_with_version = DuplicateAgentError("duplicate-agent", "1.0.0")
        assert "duplicate-agent" in str(error_with_version)
        assert "1.0.0" in str(error_with_version)
        assert error_with_version.existing_version == "1.0.0"

    def test_tool_unavailable_error(self):
        """Test ToolUnavailableError initialization."""
        error = ToolUnavailableError("semantic-search", "Gateway timeout")
        assert "semantic-search" in str(error)
        assert "Gateway timeout" in str(error)
        assert error.tool_name == "semantic-search"
        assert error.reason == "Gateway timeout"
        assert isinstance(error, AgentFrameworkError)

    def test_incompatible_type_error(self):
        """Test IncompatibleTypeError initialization."""
        error = IncompatibleTypeError("document", "artifact")
        assert "document" in str(error)
        assert "artifact" in str(error)
        assert error.output_type == "document"
        assert error.input_type == "artifact"
        assert isinstance(error, ValidationError)

    def test_exception_inheritance_chain(self):
        """Test exception inheritance relationships."""
        # AgentNotFoundError -> AgentFrameworkError -> Exception
        error = AgentNotFoundError("test")
        assert isinstance(error, AgentNotFoundError)
        assert isinstance(error, AgentFrameworkError)
        assert isinstance(error, Exception)

        # IncompatibleTypeError -> ValidationError -> AgentFrameworkError -> Exception
        error2 = IncompatibleTypeError("doc", "art")
        assert isinstance(error2, IncompatibleTypeError)
        assert isinstance(error2, ValidationError)
        assert isinstance(error2, AgentFrameworkError)
        assert isinstance(error2, Exception)

    def test_exception_raising(self):
        """Test that exceptions can be raised and caught."""
        with pytest.raises(AgentNotFoundError) as exc_info:
            raise AgentNotFoundError("agent-123")
        assert "agent-123" in str(exc_info.value)

        with pytest.raises(IncompatibleTypeError) as exc_info:
            raise IncompatibleTypeError("type1", "type2")
        assert "type1" in str(exc_info.value)
        assert "type2" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            raise ValidationError("validation error")
        assert "validation error" in str(exc_info.value)
