"""Unit tests for custom exception classes."""

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


class TestAgentFrameworkError:
    """Tests for base AgentFrameworkError."""

    def test_base_error_creation(self):
        """Test base error can be instantiated."""
        error = AgentFrameworkError("Base error message")
        assert str(error) == "Base error message"

    def test_base_error_inheritance(self):
        """Test AgentFrameworkError inherits from Exception."""
        assert issubclass(AgentFrameworkError, Exception)


class TestAgentNotFoundError:
    """Tests for AgentNotFoundError."""

    def test_error_message_format(self):
        """Test error message includes agent name."""
        error = AgentNotFoundError("test-agent")
        assert "test-agent" in str(error)
        assert "not found" in str(error)

    def test_agent_name_attribute(self):
        """Test agent_name attribute is set."""
        error = AgentNotFoundError("my-agent")
        assert error.agent_name == "my-agent"

    def test_inheritance(self):
        """Test inherits from AgentFrameworkError."""
        assert issubclass(AgentNotFoundError, AgentFrameworkError)


class TestValidationError:
    """Tests for ValidationError."""

    def test_error_with_message_only(self):
        """Test error with just a message."""
        error = ValidationError("Invalid input")
        assert str(error) == "Invalid input"
        assert error.details == {}

    def test_error_with_details(self):
        """Test error with details dict."""
        details = {"field": "name", "reason": "too short"}
        error = ValidationError("Validation failed", details=details)
        assert error.details == details
        assert error.details["field"] == "name"

    def test_inheritance(self):
        """Test inherits from AgentFrameworkError."""
        assert issubclass(ValidationError, AgentFrameworkError)


class TestConsultationRequiredError:
    """Tests for ConsultationRequiredError."""

    def test_error_message_format(self):
        """Test error message includes all parameters."""
        error = ConsultationRequiredError(
            agent_name="dev-agent",
            required_consultation="security-agent",
            phase="pre-completion"
        )
        message = str(error)
        assert "dev-agent" in message
        assert "security-agent" in message
        assert "pre-completion" in message

    def test_attributes(self):
        """Test all attributes are set correctly."""
        error = ConsultationRequiredError(
            agent_name="my-agent",
            required_consultation="review-agent",
            phase="design-review"
        )
        assert error.agent_name == "my-agent"
        assert error.required_consultation == "review-agent"
        assert error.phase == "design-review"

    def test_inheritance(self):
        """Test inherits from AgentFrameworkError."""
        assert issubclass(ConsultationRequiredError, AgentFrameworkError)


class TestDuplicateAgentError:
    """Tests for DuplicateAgentError."""

    def test_error_message_format(self):
        """Test error message includes agent name."""
        error = DuplicateAgentError("existing-agent")
        message = str(error)
        assert "existing-agent" in message
        assert "already exists" in message

    def test_agent_name_attribute(self):
        """Test agent_name attribute is set."""
        error = DuplicateAgentError("duplicate-agent")
        assert error.agent_name == "duplicate-agent"

    def test_inheritance(self):
        """Test inherits from AgentFrameworkError."""
        assert issubclass(DuplicateAgentError, AgentFrameworkError)


class TestToolUnavailableError:
    """Tests for ToolUnavailableError."""

    def test_error_message_format(self):
        """Test error message includes tool name and reason."""
        error = ToolUnavailableError("s3-uploader", "connection timeout")
        message = str(error)
        assert "s3-uploader" in message
        assert "connection timeout" in message
        assert "unavailable" in message

    def test_attributes(self):
        """Test tool_name and reason attributes are set."""
        error = ToolUnavailableError("my-tool", "service down")
        assert error.tool_name == "my-tool"
        assert error.reason == "service down"

    def test_inheritance(self):
        """Test inherits from AgentFrameworkError."""
        assert issubclass(ToolUnavailableError, AgentFrameworkError)


class TestIncompatibleTypeError:
    """Tests for IncompatibleTypeError."""

    def test_error_message_format(self):
        """Test error message includes both types."""
        error = IncompatibleTypeError("document", "code")
        message = str(error)
        assert "document" in message
        assert "code" in message
        assert "Incompatible" in message

    def test_attributes(self):
        """Test output_type and input_type attributes are set."""
        error = IncompatibleTypeError("artifact", "config")
        assert error.output_type == "artifact"
        assert error.input_type == "config"

    def test_inheritance(self):
        """Test inherits from ValidationError."""
        assert issubclass(IncompatibleTypeError, ValidationError)
        # Also inherits from AgentFrameworkError
        assert issubclass(IncompatibleTypeError, AgentFrameworkError)

    def test_details_attribute_empty(self):
        """Test IncompatibleTypeError has empty details from parent."""
        error = IncompatibleTypeError("type_a", "type_b")
        assert error.details == {}


class TestExceptionRaising:
    """Tests that verify exceptions can be raised and caught."""

    def test_catch_agent_not_found(self):
        """Test AgentNotFoundError can be caught by base class."""
        with pytest.raises(AgentFrameworkError):
            raise AgentNotFoundError("test")

    def test_catch_validation_error(self):
        """Test ValidationError can be caught by base class."""
        with pytest.raises(AgentFrameworkError):
            raise ValidationError("test")

    def test_catch_consultation_required(self):
        """Test ConsultationRequiredError can be caught by base class."""
        with pytest.raises(AgentFrameworkError):
            raise ConsultationRequiredError("a", "b", "c")

    def test_catch_incompatible_as_validation(self):
        """Test IncompatibleTypeError can be caught as ValidationError."""
        with pytest.raises(ValidationError):
            raise IncompatibleTypeError("a", "b")
