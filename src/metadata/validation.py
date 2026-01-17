"""Semantic type compatibility validation."""

from src.exceptions import IncompatibleTypeError
from src.metadata.models import SemanticType

# Compatibility matrix: which output types can be used as which input types
COMPATIBILITY_MATRIX = {
    SemanticType.DOCUMENT: [SemanticType.DOCUMENT],
    SemanticType.ARTIFACT: [SemanticType.ARTIFACT, SemanticType.DOCUMENT],
    SemanticType.COLLECTION: [SemanticType.COLLECTION],
    SemanticType.REFERENCE: [SemanticType.REFERENCE, SemanticType.DOCUMENT],
    SemanticType.COMMENT: [SemanticType.COMMENT, SemanticType.DOCUMENT],
}


def get_compatibility_matrix() -> dict[SemanticType, list[SemanticType]]:
    """
    Get the semantic type compatibility matrix.

    Returns:
        Dictionary mapping output types to compatible input types
    """
    return COMPATIBILITY_MATRIX


def is_type_compatible(output_type: SemanticType, input_type: SemanticType) -> bool:
    """
    Check if an output type is compatible with an input type.

    Args:
        output_type: The semantic type being produced
        input_type: The semantic type being consumed

    Returns:
        True if the output type can be used as the input type
    """
    compatible_types = COMPATIBILITY_MATRIX.get(output_type, [])
    return input_type in compatible_types


def validate_input_compatibility(input_schema, output_type: SemanticType) -> bool:
    """
    Validate that an output type is compatible with an input requirement.

    Args:
        input_schema: InputSchema requiring a certain semantic type
        output_type: SemanticType being provided as output

    Returns:
        True if compatible

    Raises:
        IncompatibleTypeError: If types are incompatible
    """
    required_type = input_schema.semantic_type

    compatible_types = COMPATIBILITY_MATRIX.get(output_type, [])

    if required_type not in compatible_types:
        raise IncompatibleTypeError(output_type=output_type.value, input_type=required_type.value)

    return True


def validate_output_compatibility(output_schema, expected_input_type: SemanticType) -> bool:
    """
    Validate that an output can satisfy an expected input type.

    Args:
        output_schema: OutputSchema being produced
        expected_input_type: SemanticType expected as input

    Returns:
        True if compatible

    Raises:
        IncompatibleTypeError: If types are incompatible
    """
    output_type = output_schema.semantic_type

    compatible_types = COMPATIBILITY_MATRIX.get(output_type, [])

    if expected_input_type not in compatible_types:
        raise IncompatibleTypeError(
            output_type=output_type.value, input_type=expected_input_type.value
        )

    return True
