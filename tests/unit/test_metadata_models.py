"""Unit tests for metadata Pydantic models."""

import pytest
from pydantic import ValidationError

from src.metadata.models import (
    InputSchema,
    OutputSchema,
    SemanticType,
)


class TestSemanticType:
    """Test SemanticType enum."""

    def test_semantic_types_defined(self):
        """Should have all required semantic types."""
        assert SemanticType.DOCUMENT == "document"
        assert SemanticType.ARTIFACT == "artifact"
        assert SemanticType.COLLECTION == "collection"
        assert SemanticType.REFERENCE == "reference"
        assert SemanticType.COMMENT == "comment"


class TestInputSchema:
    """Test InputSchema model."""

    def test_create_input_schema(self):
        """Should create valid InputSchema."""
        schema = InputSchema(
            name="source-code",
            semantic_type=SemanticType.ARTIFACT,
            description="Source code files to analyze",
            required=True,
        )

        assert schema.name == "source-code"
        assert schema.semantic_type == SemanticType.ARTIFACT
        assert schema.required is True

    def test_input_schema_validation(self):
        """Should validate InputSchema fields."""
        # Missing required field
        with pytest.raises(ValidationError):
            InputSchema(
                name="test",
                semantic_type=SemanticType.DOCUMENT,
                # Missing description
                required=True,
            )


class TestOutputSchema:
    """Test OutputSchema model."""

    def test_create_output_schema(self):
        """Should create valid OutputSchema."""
        schema = OutputSchema(
            name="analysis-report",
            semantic_type=SemanticType.DOCUMENT,
            description="Code analysis results",
            guaranteed=True,
        )

        assert schema.name == "analysis-report"
        assert schema.semantic_type == SemanticType.DOCUMENT
        assert schema.guaranteed is True


class TestCustomAgentMetadata:
    """Test CustomAgentMetadata model."""

    def test_create_metadata(self):
        """Should create valid CustomAgentMetadata."""
        # Will be tested once CustomAgentMetadata is implemented

    def test_metadata_with_consultation_requirements(self):
        """Should support consultation requirements."""
        # Will be tested once CustomAgentMetadata is implemented
