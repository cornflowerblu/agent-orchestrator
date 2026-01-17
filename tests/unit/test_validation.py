"""Unit tests for semantic type validation."""

import pytest

from src.exceptions import IncompatibleTypeError
from src.metadata.models import InputSchema, OutputSchema, SemanticType
from src.metadata.validation import get_compatibility_matrix, validate_input_compatibility


class TestSemanticTypeCompatibility:
    """Test semantic type compatibility validation."""

    def test_document_to_document_compatible(self):
        """Document output should be compatible with document input."""
        output = OutputSchema(
            name="spec",
            semantic_type=SemanticType.DOCUMENT,
            description="Specification document",
            guaranteed=True,
        )
        input_schema = InputSchema(
            name="requirements",
            semantic_type=SemanticType.DOCUMENT,
            description="Requirements document",
            required=True,
        )

        # Should not raise exception
        validate_input_compatibility(input_schema, output.semantic_type)

    def test_artifact_to_artifact_compatible(self):
        """Artifact output should be compatible with artifact input."""
        output = OutputSchema(
            name="code",
            semantic_type=SemanticType.ARTIFACT,
            description="Generated code",
            guaranteed=True,
        )
        input_schema = InputSchema(
            name="source",
            semantic_type=SemanticType.ARTIFACT,
            description="Source code",
            required=True,
        )

        validate_input_compatibility(input_schema, output.semantic_type)

    def test_incompatible_types_raise_error(self):
        """Incompatible types should raise IncompatibleTypeError."""
        input_schema = InputSchema(
            name="code",
            semantic_type=SemanticType.ARTIFACT,
            description="Source code",
            required=True,
        )

        with pytest.raises(IncompatibleTypeError):
            validate_input_compatibility(input_schema, SemanticType.COMMENT)

    def test_compatibility_matrix_exists(self):
        """Should have compatibility matrix defined."""
        matrix = get_compatibility_matrix()

        assert matrix is not None
        assert SemanticType.DOCUMENT in matrix
        assert SemanticType.ARTIFACT in matrix
