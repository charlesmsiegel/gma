"""
Requirement helper functions for Issue #188.

This module provides intuitive helper functions that generate JSON requirement
structures for the prerequisite system. These helpers make it easy to
programmatically create requirements without needing to know the underlying
JSON structure.

Key features:
1. Simple, intuitive API for creating requirements
2. Automatic validation via the validators module
3. Clear parameter names and documentation
4. Support for all requirement types (trait, has, any, all, count_tag)
5. Graceful error handling with clear error messages

Usage:
    from prerequisites.helpers import (
        trait_req, has_item, any_of, all_of, count_with_tag
    )

    # Simple trait requirement
    strength_req = trait_req("strength", minimum=3)

    # Has item requirement
    sword_req = has_item("weapons", id=123, name="Magic Sword")

    # Logical combinations
    combat_req = any_of(
        trait_req("strength", minimum=4),
        trait_req("dexterity", minimum=4)
    )

    # Complex requirements
    advanced_req = all_of(
        trait_req("arete", minimum=3),
        has_item("foci", name="Crystal Orb"),
        count_with_tag("spheres", "elemental", minimum=2)
    )

The generated JSON is guaranteed to pass validation from Issue #187.
"""

from typing import Any, Dict, List, Optional, Union

from django.core.exceptions import ValidationError

from prerequisites import validators


def trait_req(
    name: str,
    minimum: Optional[int] = None,
    maximum: Optional[int] = None,
    exact: Optional[int] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Generate a trait requirement JSON structure.

    Creates a requirement for a character trait (attribute, skill, etc.)
    with optional minimum, maximum, or exact value constraints.

    Args:
        name: The name of the trait (e.g., "strength", "arete", "melee")
        minimum: Optional minimum value for the trait (non-negative integer)
        maximum: Optional maximum value for the trait (non-negative integer >= minimum)
        exact: Optional exact value for the trait (conflicts with min/max)

    Returns:
        Dictionary containing the trait requirement in JSON format

    Raises:
        ValidationError: If parameters are invalid or constraints conflict

    Examples:
        >>> trait_req("strength", minimum=3)
        {"trait": {"name": "strength", "min": 3}}

        >>> trait_req("dexterity", minimum=2, maximum=5)
        {"trait": {"name": "dexterity", "min": 2, "max": 5}}

        >>> trait_req("arete", exact=3)
        {"trait": {"name": "arete", "exact": 3}}
    """
    if not isinstance(name, str) or not name.strip():
        raise ValidationError("Trait name must be a non-empty string")

    # Build trait data
    trait_data = {"name": name.strip()}

    # Add constraints if provided
    if minimum is not None:
        if not isinstance(minimum, int) or minimum < 0:
            raise ValidationError("Minimum must be a non-negative integer")
        trait_data["min"] = minimum

    if maximum is not None:
        if not isinstance(maximum, int) or maximum < 0:
            raise ValidationError("Maximum must be a non-negative integer")
        trait_data["max"] = maximum

    if exact is not None:
        if not isinstance(exact, int) or exact < 0:
            raise ValidationError("Exact must be a non-negative integer")
        trait_data["exact"] = exact

    # Ensure at least one constraint is provided
    constraints = [minimum, maximum, exact]
    if all(constraint is None for constraint in constraints):
        raise ValidationError(
            "At least one constraint (minimum, maximum, or exact) must be specified"
        )

    # Create the requirement structure
    requirement = {"trait": trait_data}

    # Validate the generated structure
    try:
        validators.validate_requirements(requirement)
    except ValidationError as e:
        raise ValidationError(f"Generated trait requirement is invalid: {e}")

    return requirement


def has_item(
    field: str, id: Optional[int] = None, name: Optional[str] = None, **kwargs: Any
) -> Dict[str, Dict[str, Any]]:
    """
    Generate a has item requirement JSON structure.

    Creates a requirement for having a specific item or object identified
    by ID, name, or both, in a specified field/category.

    Args:
        field: The field/category where the item should exist (e.g., "weapons", "foci")
        id: Optional ID of the specific item (positive integer)
        name: Optional name of the item (string)
        **kwargs: Additional fields for the has requirement

    Returns:
        Dictionary containing the has requirement in JSON format

    Raises:
        ValidationError: If parameters are invalid or neither id nor name is provided

    Examples:
        >>> has_item("weapons", id=123)
        {"has": {"field": "weapons", "id": 123}}

        >>> has_item("foci", name="Crystal Orb")
        {"has": {"field": "foci", "name": "Crystal Orb"}}

        >>> has_item("weapons", id=123, name="Magic Sword", level=2)
        {"has": {"field": "weapons", "id": 123, "name": "Magic Sword", "level": 2}}
    """
    if not isinstance(field, str) or not field.strip():
        raise ValidationError("Field must be a non-empty string")

    if id is None and name is None:
        raise ValidationError("At least one of 'id' or 'name' must be provided")

    # Build has data
    has_data = {"field": field.strip()}

    # Add identifiers if provided
    if id is not None:
        if not isinstance(id, int) or id <= 0:
            raise ValidationError("ID must be a positive integer")
        has_data["id"] = id

    if name is not None:
        if not isinstance(name, str):
            raise ValidationError("Name must be a string")
        has_data["name"] = name

    # Add any additional fields
    for key, value in kwargs.items():
        has_data[key] = value

    # Create the requirement structure
    requirement = {"has": has_data}

    # Validate the generated structure
    try:
        validators.validate_requirements(requirement)
    except ValidationError as e:
        raise ValidationError(f"Generated has requirement is invalid: {e}")

    return requirement


def any_of(
    *requirements: Union[Dict[str, Any], List[Dict[str, Any]]]
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Generate an any (logical OR) requirement JSON structure.

    Creates a requirement where at least one of the provided sub-requirements
    must be satisfied.

    Args:
        *requirements: Variable number of requirement dictionaries or a single list

    Returns:
        Dictionary containing the any requirement in JSON format

    Raises:
        ValidationError: If no requirements provided or requirements are invalid

    Examples:
        >>> any_of(
        ...     trait_req("strength", minimum=4),
        ...     trait_req("dexterity", minimum=4)
        ... )
        {"any": [
            {"trait": {"name": "strength", "min": 4}},
            {"trait": {"name": "dexterity", "min": 4}}
        ]}

        >>> # Can also pass a list
        >>> reqs = [trait_req("str", minimum=3), trait_req("dex", minimum=3)]
        >>> any_of(reqs)
        {"any": [
            {"trait": {"name": "str", "min": 3}},
            {"trait": {"name": "dex", "min": 3}}
        ]}
    """
    # Handle the case where a single list is passed
    if len(requirements) == 1 and isinstance(requirements[0], list):
        req_list = requirements[0]
    else:
        req_list = list(requirements)

    if not req_list:
        raise ValidationError("At least one requirement must be provided for any_of")

    # Validate each requirement is a dictionary
    for i, req in enumerate(req_list):
        if not isinstance(req, dict):
            raise ValidationError(f"Requirement {i} must be a dictionary")

        # Validate each sub-requirement
        try:
            validators.validate_requirements(req)
        except ValidationError as e:
            raise ValidationError(f"Requirement {i} is invalid: {e}")

    # Create the requirement structure
    requirement = {"any": req_list}

    # Validate the generated structure
    try:
        validators.validate_requirements(requirement)
    except ValidationError as e:
        raise ValidationError(f"Generated any requirement is invalid: {e}")

    return requirement


def all_of(
    *requirements: Union[Dict[str, Any], List[Dict[str, Any]]]
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Generate an all (logical AND) requirement JSON structure.

    Creates a requirement where all of the provided sub-requirements
    must be satisfied.

    Args:
        *requirements: Variable number of requirement dictionaries or a single list

    Returns:
        Dictionary containing the all requirement in JSON format

    Raises:
        ValidationError: If no requirements provided or requirements are invalid

    Examples:
        >>> all_of(
        ...     trait_req("arete", minimum=3),
        ...     has_item("foci", name="Crystal Orb")
        ... )
        {"all": [
            {"trait": {"name": "arete", "min": 3}},
            {"has": {"field": "foci", "name": "Crystal Orb"}}
        ]}

        >>> # Can also pass a list
        >>> reqs = [trait_req("str", minimum=3), has_item("weapons", id=123)]
        >>> all_of(reqs)
        {"all": [
            {"trait": {"name": "str", "min": 3}},
            {"has": {"field": "weapons", "id": 123}}
        ]}
    """
    # Handle the case where a single list is passed
    if len(requirements) == 1 and isinstance(requirements[0], list):
        req_list = requirements[0]
    else:
        req_list = list(requirements)

    if not req_list:
        raise ValidationError("At least one requirement must be provided for all_of")

    # Validate each requirement is a dictionary
    for i, req in enumerate(req_list):
        if not isinstance(req, dict):
            raise ValidationError(f"Requirement {i} must be a dictionary")

        # Validate each sub-requirement
        try:
            validators.validate_requirements(req)
        except ValidationError as e:
            raise ValidationError(f"Requirement {i} is invalid: {e}")

    # Create the requirement structure
    requirement = {"all": req_list}

    # Validate the generated structure
    try:
        validators.validate_requirements(requirement)
    except ValidationError as e:
        raise ValidationError(f"Generated all requirement is invalid: {e}")

    return requirement


def count_with_tag(
    model: str,
    tag: str,
    minimum: Optional[int] = None,
    maximum: Optional[int] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Generate a count_tag requirement JSON structure.

    Creates a requirement for counting objects with a specific tag within
    a model/category, with optional minimum and maximum constraints.

    Args:
        model: The model/category to count in (e.g., "spheres", "charms")
        tag: The tag to count (e.g., "elemental", "martial_arts")
        minimum: Optional minimum count (non-negative integer)
        maximum: Optional maximum count (non-negative integer >= minimum)

    Returns:
        Dictionary containing the count_tag requirement in JSON format

    Raises:
        ValidationError: If parameters are invalid or no constraints provided

    Examples:
        >>> count_with_tag("spheres", "elemental", minimum=2)
        {"count_tag": {"model": "spheres", "tag": "elemental", "minimum": 2}}

        >>> count_with_tag("charms", "martial_arts", minimum=1, maximum=5)
        {"count_tag": {
            "model": "charms",
            "tag": "martial_arts",
            "minimum": 1,
            "maximum": 5
        }}
    """
    if not isinstance(model, str) or not model.strip():
        raise ValidationError("Model must be a non-empty string")

    if not isinstance(tag, str) or not tag.strip():
        raise ValidationError("Tag must be a non-empty string")

    # Ensure at least one constraint is provided
    if minimum is None and maximum is None:
        raise ValidationError(
            "At least one constraint (minimum or maximum) must be specified"
        )

    # Build count_tag data
    count_data = {"model": model.strip(), "tag": tag.strip()}

    # Add constraints if provided
    if minimum is not None:
        if not isinstance(minimum, int) or minimum < 0:
            raise ValidationError("Minimum must be a non-negative integer")
        count_data["minimum"] = minimum

    if maximum is not None:
        if not isinstance(maximum, int) or maximum < 0:
            raise ValidationError("Maximum must be a non-negative integer")
        count_data["maximum"] = maximum

    # Create the requirement structure
    requirement = {"count_tag": count_data}

    # Validate the generated structure
    try:
        validators.validate_requirements(requirement)
    except ValidationError as e:
        raise ValidationError(f"Generated count_tag requirement is invalid: {e}")

    return requirement


# Convenience aliases for backward compatibility or alternative naming
trait = trait_req
has = has_item
any_requirement = any_of
all_requirement = all_of
count_tag = count_with_tag
