"""
Centralized error messages for consistent API responses.

This module provides a single source of truth for all error messages used
across the API, ensuring consistency and making maintenance easier.
"""


class ErrorMessages:
    """Centralized error messages for consistent API responses."""

    # Resource not found messages
    RESOURCE_NOT_FOUND = "Resource not found."
    CAMPAIGN_NOT_FOUND = "Campaign not found."
    MEMBER_NOT_FOUND = "Member not found."
    CHARACTER_NOT_FOUND = "Character not found."
    USER_NOT_FOUND = "User not found."
    INVITATION_NOT_FOUND = "Invitation not found."

    # Permission messages
    PERMISSION_DENIED = "Permission denied."
    INVALID_ROLE = "Invalid role."
    UNAUTHORIZED = "Authentication required."

    # Validation messages
    FIELD_REQUIRED = "This field is required."
    FIELD_INVALID = "This field is invalid."
    BAD_REQUEST = "Bad request."
    VALIDATION_ERROR = "Validation error."

    # Character-specific validation
    CHARACTER_NAME_EXISTS_IN_CAMPAIGN = (
        "A character with this name already exists in this campaign."
    )
    CAMPAIGN_AND_NAME_UNIQUE = "The fields campaign, name must make a unique set."

    # Campaign-specific validation
    CAMPAIGN_PARAMETER_CANNOT_BE_NONE = "Campaign parameter cannot be None."

    @staticmethod
    def character_name_exists_in_campaign_message():
        """Return the character name uniqueness error message."""
        return ErrorMessages.CHARACTER_NAME_EXISTS_IN_CAMPAIGN

    @staticmethod
    def campaign_and_name_unique_message():
        """Return the campaign and name uniqueness error message."""
        return ErrorMessages.CAMPAIGN_AND_NAME_UNIQUE


class FieldErrorMessages:
    """Field-specific error message builders."""

    @staticmethod
    def required(field_name: str) -> str:
        """Build a required field error message."""
        return f"{field_name} is required."

    @staticmethod
    def invalid(field_name: str) -> str:
        """Build an invalid field error message."""
        return f"{field_name} is invalid."

    @staticmethod
    def not_found(resource_name: str) -> str:
        """Build a resource not found error message."""
        return f"{resource_name} not found."

    @staticmethod
    def already_exists(resource_name: str, context: str = "") -> str:
        """Build an already exists error message."""
        if context:
            return f"A {resource_name} with this name already exists {context}."
        return f"A {resource_name} with this name already exists."
