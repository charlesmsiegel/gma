"""
Requirement checking engine for Issue #189.

This module provides the check_requirement function that validates whether a character
meets specific requirements defined in JSON format.

Key features:
- Support for all requirement types (trait, has, any, all, count_tag)
- Recursive checking for nested requirements
- Efficient queries to minimize database hits
- Extensible system for custom requirement types
- Clear error handling and informative results
- Performance optimized for ~5 depth levels max

Usage:
    from prerequisites.checkers import check_requirement
    from prerequisites.helpers import trait_req, any_of

    # Check a simple requirement
    requirement = trait_req("strength", minimum=3)
    result = check_requirement(character, requirement)  # Returns RequirementCheckResult

    # Check complex requirements
    complex_req = any_of(
        trait_req("strength", minimum=4),
        trait_req("dexterity", minimum=4)
    )
    result = check_requirement(character, complex_req)

The checking engine integrates with the existing Character model and its polymorphic
hierarchy (Character → WoDCharacter → MageCharacter).
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from django.core.exceptions import ValidationError
from django.db import models

from prerequisites import validators


class RequirementCheckResult:
    """
    Result of a requirement check operation.

    Contains information about whether the requirement was satisfied,
    a human-readable message, and detailed information for debugging
    or display purposes.
    """

    def __init__(
        self,
        success: bool,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a requirement check result.

        Args:
            success: Whether the requirement was satisfied
            message: Human-readable description of the result
            details: Optional additional details about the check
        """
        self.success = success
        self.message = message
        self.details = details or {}

    def __bool__(self) -> bool:
        """Return success status for boolean conversion."""
        return self.success

    def __str__(self) -> str:
        """Return string representation of the result."""
        status = "SUCCESS" if self.success else "FAILED"
        return f"{status}: {self.message}"

    def __repr__(self) -> str:
        """Return detailed string representation."""
        return (
            f"RequirementCheckResult(success={self.success}, message='{self.message}')"
        )


# Registry for requirement checkers
_REQUIREMENT_CHECKERS: Dict[
    str, Callable[["models.Model", Dict[str, Any]], RequirementCheckResult]
] = {}


def check_requirement(
    character: "models.Model", requirement: Dict[str, Any]
) -> RequirementCheckResult:
    """
    Check whether a character meets a specific requirement.

    This is the main entry point for requirement checking. It validates
    the requirement structure and delegates to specific checker functions
    based on the requirement type.

    Args:
        character: The character to check requirements against
        requirement: JSON requirement structure to validate

    Returns:
        RequirementCheckResult with success status and details

    Raises:
        ValidationError: If character is None, requirement is invalid,
                        or requirement type is unknown

    Examples:
        # Simple trait check
        result = check_requirement(character, {"trait": {"name": "strength", "min": 3}})

        # Complex logical check
        result = check_requirement(character, {
            "any": [
                {"trait": {"name": "strength", "min": 4}},
                {"trait": {"name": "dexterity", "min": 4}}
            ]
        })
    """
    # Input validation
    if character is None:
        raise ValidationError("Character cannot be None")

    if requirement is None:
        raise ValidationError("Requirement cannot be None")

    # Basic requirement structure validation
    if not isinstance(requirement, dict):
        raise ValidationError(
            f"Requirement must be a dictionary, got {type(requirement).__name__}"
        )

    if not requirement:
        raise ValidationError("Requirement cannot be empty")

    requirement_types = list(requirement.keys())
    if len(requirement_types) != 1:
        raise ValidationError(
            f"Requirement must contain exactly one requirement type, "
            f"got {len(requirement_types)}: {requirement_types}"
        )

    # Extract requirement type and data
    requirement_type = requirement_types[0]
    requirement_data = requirement[requirement_type]

    # Check if we have a registered checker
    if requirement_type not in _REQUIREMENT_CHECKERS:
        raise ValidationError(f"Unknown requirement type: {requirement_type}")

    # For built-in types, validate using the validators module
    if requirement_type in ["trait", "has", "any", "all", "count_tag"]:
        try:
            validators.validate_requirements(requirement)
        except ValidationError as e:
            raise ValidationError(f"Invalid requirement structure: {e}")

    checker_func = _REQUIREMENT_CHECKERS[requirement_type]

    # Execute checker with error handling
    try:
        return checker_func(character, requirement_data)
    except Exception as e:
        raise ValidationError(f"Error checking requirement '{requirement_type}': {e}")


def _check_trait_requirement(
    character: "models.Model", requirement_data: Dict[str, Any]
) -> RequirementCheckResult:
    """
    Check trait requirements using getattr with comparison operators.

    Validates that a character has a specific trait value that meets
    minimum, maximum, or exact constraints.

    Args:
        character: Character to check
        requirement_data: Trait requirement data with name and constraints

    Returns:
        RequirementCheckResult indicating success/failure with details
    """
    trait_name = requirement_data["name"]

    # Use getattr with default 0 for non-existent traits
    actual_value = getattr(character, trait_name, 0)

    details = {
        "trait_name": trait_name,
        "actual_value": actual_value,
    }

    # Check minimum constraint
    if "min" in requirement_data:
        min_val = requirement_data["min"]
        details["required_minimum"] = min_val

        if actual_value < min_val:
            return RequirementCheckResult(
                success=False,
                message=(
                    f"Character has insufficient {trait_name}: "
                    f"{actual_value} < {min_val}"
                ),
                details=details,
            )

    # Check maximum constraint
    if "max" in requirement_data:
        max_val = requirement_data["max"]
        details["required_maximum"] = max_val

        if actual_value > max_val:
            return RequirementCheckResult(
                success=False,
                message=(
                    f"Character's {trait_name} exceeds maximum: "
                    f"{actual_value} > {max_val}"
                ),
                details=details,
            )

    # Check exact constraint
    if "exact" in requirement_data:
        exact_val = requirement_data["exact"]
        details["required_exact"] = exact_val

        if actual_value != exact_val:
            return RequirementCheckResult(
                success=False,
                message=(
                    f"Character's {trait_name} must be exactly {exact_val}, "
                    f"got {actual_value}"
                ),
                details=details,
            )

    # Handle case where trait doesn't exist (actual_value == 0 from getattr default)
    if actual_value == 0 and not hasattr(character, trait_name):
        # Special case: if requirement allows 0, it's still a success
        min_val = requirement_data.get("min", 0)
        exact_val = requirement_data.get("exact")

        if min_val > 0 or (exact_val is not None and exact_val > 0):
            return RequirementCheckResult(
                success=False,
                message=f"Character does not have trait '{trait_name}'",
                details=details,
            )

    # All constraints satisfied
    constraint_parts = []
    if "min" in requirement_data:
        constraint_parts.append(f"minimum {requirement_data['min']}")
    if "max" in requirement_data:
        constraint_parts.append(f"maximum {requirement_data['max']}")
    if "exact" in requirement_data:
        constraint_parts.append(f"exactly {requirement_data['exact']}")

    constraint_desc = " and ".join(constraint_parts)

    return RequirementCheckResult(
        success=True,
        message=(
            f"Character meets {trait_name} requirement "
            f"({constraint_desc}): {actual_value}"
        ),
        details=details,
    )


def _check_has_requirement(
    character: "models.Model", requirement_data: Dict[str, Any]
) -> RequirementCheckResult:
    """
    Check has requirements using Django ORM relationship checking.

    Validates that a character has a specific object in a field/relationship
    identified by ID, name, or other attributes.

    Args:
        character: Character to check
        requirement_data: Has requirement data with field and identifiers

    Returns:
        RequirementCheckResult indicating success/failure with details
    """
    field = requirement_data["field"]

    # Extract search criteria (exclude field name)
    search_criteria = {k: v for k, v in requirement_data.items() if k != "field"}

    details = {
        "field": field,
        **search_criteria,
    }

    # Use helper function to check ORM relationships
    has_object = _check_has_requirement_orm(character, field, search_criteria)

    if has_object:
        criteria_desc = ", ".join(f"{k}={v}" for k, v in search_criteria.items())
        return RequirementCheckResult(
            success=True,
            message=f"Character has required object in {field} ({criteria_desc})",
            details=details,
        )
    else:
        criteria_desc = ", ".join(f"{k}={v}" for k, v in search_criteria.items())
        return RequirementCheckResult(
            success=False,
            message=f"Character does not have required object in {field} ({criteria_desc})",
            details=details,
        )


def _check_has_requirement_orm(
    character: "models.Model", field: str, search_criteria: Dict[str, Any]
) -> bool:
    """
    Helper function to check if character has object in field using Django ORM.

    This function handles the actual database queries for has requirements.
    It can be mocked in tests to avoid database dependencies.

    Args:
        character: Character to check
        field: Field/relationship name to search in
        search_criteria: Dictionary of field/value pairs to filter on

    Returns:
        True if character has matching object, False otherwise
    """
    try:
        # Get the related manager for the field
        if hasattr(character, field):
            related_manager = getattr(character, field)

            # Try to filter using the search criteria
            if hasattr(related_manager, "filter"):
                # Related manager (ForeignKey, ManyToMany)
                return related_manager.filter(**search_criteria).exists()
            else:
                # Single related object (OneToOne, ForeignKey without related_name)
                # Check if object matches criteria
                obj = related_manager
                if obj is None:
                    return False

                for key, value in search_criteria.items():
                    if getattr(obj, key, None) != value:
                        return False
                return True
        else:
            # Field doesn't exist
            return False

    except Exception:
        # Any error in ORM query means requirement not met
        return False


def _check_any_requirement(
    character: "models.Model", requirement_data: List[Dict[str, Any]]
) -> RequirementCheckResult:
    """
    Check any (logical OR) requirements with recursion.

    Validates that at least one of the sub-requirements is satisfied.
    Uses recursive calls to check_requirement for nested structures.

    Args:
        character: Character to check
        requirement_data: List of sub-requirements

    Returns:
        RequirementCheckResult with overall success and sub-result details
    """
    sub_results = []
    any_satisfied = False

    for i, sub_requirement in enumerate(requirement_data):
        try:
            result = check_requirement(character, sub_requirement)
            sub_results.append(
                {
                    "index": i,
                    "success": result.success,
                    "message": result.message,
                    "details": result.details,
                }
            )

            if result.success:
                any_satisfied = True

        except ValidationError as e:
            # Sub-requirement failed validation
            sub_results.append(
                {
                    "index": i,
                    "success": False,
                    "message": f"Validation error: {e}",
                    "details": {},
                }
            )

    details = {"sub_results": sub_results}

    if any_satisfied:
        satisfied_count = sum(1 for r in sub_results if r["success"])
        return RequirementCheckResult(
            success=True,
            message=f"At least one requirement satisfied ({satisfied_count}/{len(sub_results)})",
            details=details,
        )
    else:
        return RequirementCheckResult(
            success=False,
            message=f"No requirements satisfied (0/{len(sub_results)})",
            details=details,
        )


def _check_all_requirement(
    character: "models.Model", requirement_data: List[Dict[str, Any]]
) -> RequirementCheckResult:
    """
    Check all (logical AND) requirements with recursion.

    Validates that all sub-requirements are satisfied.
    Uses recursive calls to check_requirement for nested structures.

    Args:
        character: Character to check
        requirement_data: List of sub-requirements

    Returns:
        RequirementCheckResult with overall success and sub-result details
    """
    sub_results = []
    all_satisfied = True

    for i, sub_requirement in enumerate(requirement_data):
        try:
            result = check_requirement(character, sub_requirement)
            sub_results.append(
                {
                    "index": i,
                    "success": result.success,
                    "message": result.message,
                    "details": result.details,
                }
            )

            if not result.success:
                all_satisfied = False

        except ValidationError as e:
            # Sub-requirement failed validation
            sub_results.append(
                {
                    "index": i,
                    "success": False,
                    "message": f"Validation error: {e}",
                    "details": {},
                }
            )
            all_satisfied = False

    details = {"sub_results": sub_results}

    if all_satisfied:
        return RequirementCheckResult(
            success=True,
            message=f"All requirements satisfied ({len(sub_results)}/{len(sub_results)})",
            details=details,
        )
    else:
        satisfied_count = sum(1 for r in sub_results if r["success"])
        return RequirementCheckResult(
            success=False,
            message=f"Not all requirements satisfied ({satisfied_count}/{len(sub_results)})",
            details=details,
        )


def _check_count_tag_requirement(
    character: "models.Model", requirement_data: Dict[str, Any]
) -> RequirementCheckResult:
    """
    Check count_tag requirements for counting objects with tags.

    Validates that a character has the required number of objects
    with a specific tag in a model/category.

    Args:
        character: Character to check
        requirement_data: Count requirement data with model, tag, and constraints

    Returns:
        RequirementCheckResult indicating success/failure with count details
    """
    model_name = requirement_data["model"]
    tag = requirement_data["tag"]

    # Get actual count using helper function
    actual_count = _count_objects_with_tag(character, model_name, tag)

    details = {
        "model": model_name,
        "tag": tag,
        "actual_count": actual_count,
    }

    # Check minimum constraint
    if "minimum" in requirement_data:
        min_count = requirement_data["minimum"]
        details["required_minimum"] = min_count

        if actual_count < min_count:
            return RequirementCheckResult(
                success=False,
                message=f"Insufficient count of {model_name} with tag '{tag}': {actual_count} < {min_count}",
                details=details,
            )

    # Check maximum constraint
    if "maximum" in requirement_data:
        max_count = requirement_data["maximum"]
        details["required_maximum"] = max_count

        if actual_count > max_count:
            return RequirementCheckResult(
                success=False,
                message=f"Too many {model_name} with tag '{tag}' exceeds maximum: {actual_count} > {max_count}",
                details=details,
            )

    # All constraints satisfied
    constraint_parts = []
    if "minimum" in requirement_data:
        constraint_parts.append(f"minimum {requirement_data['minimum']}")
    if "maximum" in requirement_data:
        constraint_parts.append(f"maximum {requirement_data['maximum']}")

    constraint_desc = " and ".join(constraint_parts)

    return RequirementCheckResult(
        success=True,
        message=f"Sufficient count of {model_name} with tag '{tag}' ({constraint_desc}): {actual_count}",
        details=details,
    )


def _count_objects_with_tag(
    character: "models.Model", model_name: str, tag: str
) -> int:
    """
    Helper function to count objects with a specific tag for a character.

    This function handles the actual database queries for count_tag requirements.
    It can be mocked in tests to avoid database dependencies.

    Args:
        character: Character to count objects for
        model_name: Name of the model/relationship to count in
        tag: Tag to filter objects by

    Returns:
        Number of objects with the specified tag
    """
    try:
        # Get the related manager for the model
        if hasattr(character, model_name):
            related_manager = getattr(character, model_name)

            # Try to filter by tag using common tag field patterns
            if hasattr(related_manager, "filter"):
                # Try common tag field names
                tag_fields = ["tag", "tags", "category", "type"]

                for tag_field in tag_fields:
                    try:
                        # For single tag field
                        count = related_manager.filter(**{tag_field: tag}).count()
                        if count > 0:
                            return count
                    except Exception:
                        pass

                    try:
                        # For ManyToMany tag field (tags__name)
                        count = related_manager.filter(
                            **{f"{tag_field}__name": tag}
                        ).count()
                        if count > 0:
                            return count
                    except Exception:
                        pass

                # If no tag field worked, return 0
                return 0
            else:
                # Single related object - check if it has the tag
                obj = related_manager
                if obj is None:
                    return 0

                # Check common tag attributes
                for tag_attr in ["tag", "tags", "category", "type"]:
                    if hasattr(obj, tag_attr):
                        attr_val = getattr(obj, tag_attr)
                        if attr_val == tag:
                            return 1
                        elif (
                            hasattr(attr_val, "filter")
                            and attr_val.filter(name=tag).exists()
                        ):
                            return 1

                return 0
        else:
            # Model/field doesn't exist
            return 0

    except Exception:
        # Any error in counting means 0
        return 0


def register_requirement_checker(
    requirement_type: str,
    checker_func: Callable[["models.Model", Dict[str, Any]], RequirementCheckResult],
) -> None:
    """
    Register a custom requirement checker function.

    Allows extending the requirement checking system with custom requirement types.
    Custom checkers can override built-in ones.

    Args:
        requirement_type: The requirement type name (e.g., "custom")
        checker_func: Function that checks requirements
                     Signature: (character: Model, requirement_data: Dict) -> RequirementCheckResult

    Example:
        def custom_checker(character, requirement_data):
            # Custom checking logic
            return RequirementCheckResult(success=True, message="Custom check passed")

        register_requirement_checker("custom", custom_checker)
    """
    _REQUIREMENT_CHECKERS[requirement_type] = checker_func


def unregister_requirement_checker(requirement_type: str) -> bool:
    """
    Unregister a requirement checker function.

    Args:
        requirement_type: The requirement type name to unregister

    Returns:
        True if checker was removed, False if it didn't exist
    """
    return _REQUIREMENT_CHECKERS.pop(requirement_type, None) is not None


def get_registered_checker_types() -> List[str]:
    """
    Get list of all registered requirement checker type names.

    Returns:
        List of requirement type names that can be used with check_requirement
    """
    return list(_REQUIREMENT_CHECKERS.keys())


# Register built-in requirement checkers
register_requirement_checker("trait", _check_trait_requirement)
register_requirement_checker("has", _check_has_requirement)
register_requirement_checker("any", _check_any_requirement)
register_requirement_checker("all", _check_all_requirement)
register_requirement_checker("count_tag", _check_count_tag_requirement)
