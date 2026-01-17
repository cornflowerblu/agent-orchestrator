"""Local integration tests for metadata semantic type validation.

Fast feedback loop for development - no AWS deployment needed.
"""

import pytest

from src.exceptions import IncompatibleTypeError
from src.metadata.models import InputSchema, OutputSchema, SemanticType
from src.metadata.validation import (
    get_compatibility_matrix,
    is_type_compatible,
    validate_input_compatibility,
    validate_output_compatibility,
)

# Mark all tests in this module as local integration tests
pytestmark = pytest.mark.integration_local


class TestMetadataValidationLocal:
    """Local integration tests for metadata validation."""

    def test_get_compatibility_matrix(self):
        """Test getting the compatibility matrix."""
        matrix = get_compatibility_matrix()

        assert SemanticType.DOCUMENT in matrix
        assert SemanticType.ARTIFACT in matrix
        assert SemanticType.COLLECTION in matrix
        assert SemanticType.REFERENCE in matrix
        assert SemanticType.COMMENT in matrix

    def test_is_type_compatible_document_to_document(self):
        """Test DOCUMENT output is compatible with DOCUMENT input."""
        assert is_type_compatible(SemanticType.DOCUMENT, SemanticType.DOCUMENT) is True

    def test_is_type_compatible_artifact_to_artifact(self):
        """Test ARTIFACT output is compatible with ARTIFACT input."""
        assert is_type_compatible(SemanticType.ARTIFACT, SemanticType.ARTIFACT) is True

    def test_is_type_compatible_artifact_to_document(self):
        """Test ARTIFACT output is compatible with DOCUMENT input."""
        assert is_type_compatible(SemanticType.ARTIFACT, SemanticType.DOCUMENT) is True

    def test_is_type_compatible_reference_to_reference(self):
        """Test REFERENCE output is compatible with REFERENCE input."""
        assert is_type_compatible(SemanticType.REFERENCE, SemanticType.REFERENCE) is True

    def test_is_type_compatible_reference_to_document(self):
        """Test REFERENCE output is compatible with DOCUMENT input."""
        assert is_type_compatible(SemanticType.REFERENCE, SemanticType.DOCUMENT) is True

    def test_is_type_compatible_comment_to_comment(self):
        """Test COMMENT output is compatible with COMMENT input."""
        assert is_type_compatible(SemanticType.COMMENT, SemanticType.COMMENT) is True

    def test_is_type_compatible_comment_to_document(self):
        """Test COMMENT output is compatible with DOCUMENT input."""
        assert is_type_compatible(SemanticType.COMMENT, SemanticType.DOCUMENT) is True

    def test_is_type_compatible_incompatible_types(self):
        """Test incompatible type combinations."""
        # DOCUMENT cannot be used as ARTIFACT
        assert is_type_compatible(SemanticType.DOCUMENT, SemanticType.ARTIFACT) is False

        # COLLECTION can only be COLLECTION
        assert is_type_compatible(SemanticType.COLLECTION, SemanticType.DOCUMENT) is False
        assert is_type_compatible(SemanticType.DOCUMENT, SemanticType.COLLECTION) is False

    def test_validate_input_compatibility_compatible(self):
        """Test validating compatible input/output types."""
        # ARTIFACT can satisfy DOCUMENT input
        input_schema = InputSchema(
            semantic_type=SemanticType.DOCUMENT,
            name="input",
            description="Test input",
            required=True,
        )

        result = validate_input_compatibility(input_schema, SemanticType.ARTIFACT)
        assert result is True

    def test_validate_input_compatibility_incompatible(self):
        """Test validating incompatible input/output types."""
        # DOCUMENT cannot satisfy ARTIFACT input
        input_schema = InputSchema(
            semantic_type=SemanticType.ARTIFACT,
            name="input",
            description="Test input",
            required=True,
        )

        with pytest.raises(IncompatibleTypeError) as exc_info:
            validate_input_compatibility(input_schema, SemanticType.DOCUMENT)

        assert "document" in str(exc_info.value).lower()
        assert "artifact" in str(exc_info.value).lower()

    def test_validate_output_compatibility_compatible(self):
        """Test validating compatible output/input types."""
        # ARTIFACT output can satisfy DOCUMENT input
        output_schema = OutputSchema(
            semantic_type=SemanticType.ARTIFACT,
            name="output",
            description="Test output",
            guaranteed=True,
        )

        result = validate_output_compatibility(output_schema, SemanticType.DOCUMENT)
        assert result is True

    def test_validate_output_compatibility_incompatible(self):
        """Test validating incompatible output/input types."""
        # DOCUMENT output cannot satisfy ARTIFACT input
        output_schema = OutputSchema(
            semantic_type=SemanticType.DOCUMENT,
            name="output",
            description="Test output",
            guaranteed=True,
        )

        with pytest.raises(IncompatibleTypeError) as exc_info:
            validate_output_compatibility(output_schema, SemanticType.ARTIFACT)

        assert "document" in str(exc_info.value).lower()
        assert "artifact" in str(exc_info.value).lower()
