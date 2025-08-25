"""
JSON requirement validation system for Prerequisites (Issue #187).

This module provides comprehensive validation for JSON requirement structures,
ensuring they follow correct format and constraints for each requirement type.

Key features:
1. Validate required fields for each requirement type
2. Recursive validation for nested requirements (any/all)
3. Clear error messages for invalid structures
4. Support for trait, has, any, all, count_tag types
5. Custom requirement type extensibility

Supported requirement types:
- trait: Character attribute/skill checks with min/max/exact constraints
- has: Object existence checks in specified fields (by id or name)
- any: Logical OR - at least one subrequirement must be met
- all: Logical AND - all subrequirements must be met
- count_tag: Count objects with specific tags (min/max constraints)

Usage:
    from prerequisites.validators import validate_requirements

    # Validate a requirement structure
    requirements = {
        "trait": {
            "name": "strength",
            "min": 3,
            "max": 5
        }
    }

    try:
        validate_requirements(requirements)
    except ValidationError as e:
        print(f"Validation failed: {e}")

Extension:
    # Register custom requirement type
    def validate_custom_type(requirement_data, path=""):
        # Custom validation logic
        pass

    register_requirement_validator("custom", validate_custom_type)
"""

from typing import Any, Callable, Dict, List

from django.core.exceptions import ValidationError

# Registry for requirement type validators
_REQUIREMENT_VALIDATORS: Dict[str, Callable[[Dict[str, Any], str], None]] = {}


def validate_requirements(requirements: Any, path: str = "") -> None:
    """
    Validate a complete requirements structure.

    Args:
        requirements: The requirements data to validate
        path: Current validation path for error reporting

    Raises:
        ValidationError: If validation fails with detailed error message
    """
    # Basic type validation
    if requirements is None:
        raise ValidationError("Requirements must be a dictionary, not None")

    if not isinstance(requirements, dict):
        raise ValidationError(
            f"Requirements must be a dictionary, got {type(requirements).__name__}"
        )

    # Empty requirements are valid
    if not requirements:
        return

    # Must contain exactly one root requirement type
    requirement_types = list(requirements.keys())
    if len(requirement_types) != 1:
        if len(requirement_types) == 0:
            return  # Empty is valid
        raise ValidationError(
            f"Requirements must contain exactly one root requirement type, "
            f"got {len(requirement_types)}: {requirement_types}"
        )

    requirement_type = requirement_types[0]
    requirement_data = requirements[requirement_type]

    # Validate using registered validator
    if requirement_type not in _REQUIREMENT_VALIDATORS:
        raise ValidationError(f"Unknown requirement type: {requirement_type}")

    validator = _REQUIREMENT_VALIDATORS[requirement_type]
    current_path = f"{path}.{requirement_type}" if path else requirement_type

    try:
        validator(requirement_data, current_path)
    except ValidationError:
        # Re-raise with current context
        raise


def validate_trait_requirement(requirement_data: Any, path: str = "") -> None:
    """
    Validate trait requirement structure.

    Expected format:
    {
        "name": "attribute_name",  # required, non-empty string
        "min": 1,                  # optional, positive integer
        "max": 5,                  # optional, positive integer >= min
        "exact": 3                 # optional, positive integer (conflicts with min/max)
    }
    """
    if not isinstance(requirement_data, dict):
        raise ValidationError(f"trait requirement must be a dictionary at {path}")

    # Validate name field
    if "name" not in requirement_data:
        raise ValidationError(
            f"trait requirement missing required 'name' field at {path}"
        )

    name = requirement_data["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValidationError(f"trait requirement 'name' cannot be empty at {path}")

    # Extract constraint fields
    min_val = requirement_data.get("min")
    max_val = requirement_data.get("max")
    exact_val = requirement_data.get("exact")

    # Must have at least one constraint
    constraints = [min_val, max_val, exact_val]
    if all(constraint is None for constraint in constraints):
        raise ValidationError(
            f"trait requirement must have at least one constraint "
            f"(min, max, or exact) at {path}"
        )

    # Validate constraint types and values
    for constraint_name, constraint_val in [
        ("min", min_val),
        ("max", max_val),
        ("exact", exact_val),
    ]:
        if constraint_val is not None:
            if not isinstance(constraint_val, int):
                raise ValidationError(
                    f"trait requirement '{constraint_name}' must be an "
                    f"integer at {path}"
                )
            if constraint_val < 0:
                raise ValidationError(
                    f"trait requirement '{constraint_name}' must be "
                    f"non-negative at {path}"
                )

    # Validate constraint relationships
    if min_val is not None and max_val is not None and min_val > max_val:
        raise ValidationError(
            f"trait requirement 'max' ({max_val}) cannot be less than "
            f"'min' ({min_val}) at {path}"
        )

    if exact_val is not None and (min_val is not None or max_val is not None):
        raise ValidationError(
            f"trait requirement 'exact' cannot be used with 'min' or 'max' at {path}"
        )


def validate_has_requirement(requirement_data: Any, path: str = "") -> None:
    """
    Validate has requirement structure.

    Expected format:
    {
        "field": "field_name",     # required, non-empty string
        "id": 123,                 # optional, positive integer
        "name": "object_name",     # optional, string
        "level": 2                 # optional, additional fields allowed
    }

    Must have either "id" or "name" (or both).
    """
    if not isinstance(requirement_data, dict):
        raise ValidationError(f"has requirement must be a dictionary at {path}")

    # Validate field
    if "field" not in requirement_data:
        raise ValidationError(f"has requirement missing required 'field' at {path}")

    field = requirement_data["field"]
    if not isinstance(field, str) or not field.strip():
        raise ValidationError(f"has requirement 'field' cannot be empty at {path}")

    # Must have id or name
    id_val = requirement_data.get("id")
    name_val = requirement_data.get("name")

    if id_val is None and name_val is None:
        raise ValidationError(
            f"has requirement must specify either 'id' or 'name' at {path}"
        )

    # Validate id if present
    if id_val is not None:
        if not isinstance(id_val, int):
            raise ValidationError(f"has requirement 'id' must be an integer at {path}")
        if id_val <= 0:
            raise ValidationError(f"has requirement 'id' must be positive at {path}")

    # Validate name if present
    if name_val is not None:
        if not isinstance(name_val, str):
            raise ValidationError(f"has requirement 'name' must be a string at {path}")


def validate_any_requirement(requirement_data: Any, path: str = "") -> None:
    """
    Validate any (logical OR) requirement structure.

    Expected format:
    [
        { "trait": { ... } },      # First alternative
        { "has": { ... } },        # Second alternative
        ...
    ]

    Must be a non-empty list of valid requirements.
    """
    if not isinstance(requirement_data, list):
        raise ValidationError(f"any requirement must be a list at {path}")

    if len(requirement_data) == 0:
        raise ValidationError(f"any requirement cannot be empty at {path}")

    # Validate each subrequirement
    for i, subrequirement in enumerate(requirement_data):
        sub_path = f"{path}[{i}]"
        validate_requirements(subrequirement, sub_path)


def validate_all_requirement(requirement_data: Any, path: str = "") -> None:
    """
    Validate all (logical AND) requirement structure.

    Expected format:
    [
        { "trait": { ... } },      # First requirement
        { "has": { ... } },        # Second requirement
        ...
    ]

    Must be a non-empty list of valid requirements.
    """
    if not isinstance(requirement_data, list):
        raise ValidationError(f"all requirement must be a list at {path}")

    if len(requirement_data) == 0:
        raise ValidationError(f"all requirement cannot be empty at {path}")

    # Validate each subrequirement
    for i, subrequirement in enumerate(requirement_data):
        sub_path = f"{path}[{i}]"
        validate_requirements(subrequirement, sub_path)


def validate_count_tag_requirement(requirement_data: Any, path: str = "") -> None:
    """
    Validate count_tag requirement structure.

    Expected format:
    {
        "model": "model_name",     # required, non-empty string
        "tag": "tag_name",         # required, non-empty string
        "minimum": 2,              # optional, non-negative integer
        "maximum": 5               # optional, non-negative integer >= minimum
    }

    Must have at least one constraint (minimum or maximum).
    """
    if not isinstance(requirement_data, dict):
        raise ValidationError(f"count_tag requirement must be a dictionary at {path}")

    # Validate model field
    if "model" not in requirement_data:
        raise ValidationError(
            f"count_tag requirement missing required 'model' field at {path}"
        )

    model = requirement_data["model"]
    if not isinstance(model, str) or not model.strip():
        raise ValidationError(
            f"count_tag requirement 'model' cannot be empty at {path}"
        )

    # Validate tag field
    if "tag" not in requirement_data:
        raise ValidationError(
            f"count_tag requirement missing required 'tag' field at {path}"
        )

    tag = requirement_data["tag"]
    if not isinstance(tag, str) or not tag.strip():
        raise ValidationError(f"count_tag requirement 'tag' cannot be empty at {path}")

    # Extract constraint fields
    min_val = requirement_data.get("minimum")
    max_val = requirement_data.get("maximum")

    # Must have at least one constraint
    if min_val is None and max_val is None:
        raise ValidationError(
            f"count_tag requirement must have at least one constraint "
            f"(minimum or maximum) at {path}"
        )

    # Validate constraint types and values
    for constraint_name, constraint_val in [("minimum", min_val), ("maximum", max_val)]:
        if constraint_val is not None:
            if not isinstance(constraint_val, int):
                raise ValidationError(
                    f"count_tag requirement '{constraint_name}' must be an "
                    f"integer at {path}"
                )
            if constraint_val < 0:
                raise ValidationError(
                    f"count_tag requirement '{constraint_name}' must be "
                    f"non-negative at {path}"
                )

    # Validate constraint relationships
    if min_val is not None and max_val is not None and min_val > max_val:
        raise ValidationError(
            f"count_tag requirement 'maximum' ({max_val}) cannot be less "
            f"than 'minimum' ({min_val}) at {path}"
        )


def register_requirement_validator(
    requirement_type: str, validator_func: Callable[[Dict[str, Any], str], None]
) -> None:
    """
    Register a validator function for a requirement type.

    Args:
        requirement_type: The requirement type name (e.g., "custom")
        validator_func: Function that validates requirement data
                       Signature: (requirement_data: Dict[str, Any], path: str) -> None
                       Should raise ValidationError on validation failure
    """
    _REQUIREMENT_VALIDATORS[requirement_type] = validator_func


def unregister_requirement_validator(requirement_type: str) -> bool:
    """
    Unregister a validator function for a requirement type.

    Args:
        requirement_type: The requirement type name to unregister

    Returns:
        True if validator was removed, False if it didn't exist
    """
    return _REQUIREMENT_VALIDATORS.pop(requirement_type, None) is not None


def get_registered_validator_types() -> List[str]:
    """
    Get list of all registered requirement type names.

    Returns:
        List of requirement type names
    """
    return list(_REQUIREMENT_VALIDATORS.keys())


# Register built-in validators
register_requirement_validator("trait", validate_trait_requirement)
register_requirement_validator("has", validate_has_requirement)
register_requirement_validator("any", validate_any_requirement)
register_requirement_validator("all", validate_all_requirement)
register_requirement_validator("count_tag", validate_count_tag_requirement)
