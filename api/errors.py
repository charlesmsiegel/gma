"""
Standardized error handling utilities for GMA API views.

This module provides consistent, security-focused error response builders
that ensure uniform error handling across all API endpoints while preventing
information leakage.

Key Features:
- Consistent error response formats
- Security-focused responses that don't leak resource existence
- Standardized validation error formatting
- Reusable error response builders
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Model, QuerySet
from rest_framework import status
from rest_framework.response import Response

User = get_user_model()


class APIError:
    """Standard API error response builder."""

    # Standard error messages - generic to prevent information leakage
    RESOURCE_NOT_FOUND = "Resource not found."
    PERMISSION_DENIED = "Permission denied."
    VALIDATION_ERROR = "Validation error."
    BAD_REQUEST = "Bad request."
    UNAUTHORIZED = "Authentication required."

    # Field validation messages
    FIELD_REQUIRED = "This field is required."
    FIELD_INVALID = "This field is invalid."

    @staticmethod
    def not_found(detail: Optional[str] = None) -> Response:
        """
        Return a standard 404 Not Found response.

        Args:
            detail: Custom error message. If None, uses standard message.

        Returns:
            Response with 404 status and standard error format.
        """
        return Response(
            {"detail": detail or APIError.RESOURCE_NOT_FOUND},
            status=status.HTTP_404_NOT_FOUND,
        )

    @staticmethod
    def permission_denied(detail: Optional[str] = None) -> Response:
        """
        Return a standard 403 Permission Denied response.

        For security, this often returns 404 to hide resource existence.

        Args:
            detail: Custom error message. If None, uses standard message.

        Returns:
            Response with 403 status and standard error format.
        """
        return Response(
            {"detail": detail or APIError.PERMISSION_DENIED},
            status=status.HTTP_403_FORBIDDEN,
        )

    @staticmethod
    def permission_denied_as_not_found(detail: Optional[str] = None) -> Response:
        """
        Return a 404 response for permission denied to hide resource existence.

        This is the preferred approach for security - makes private resources
        indistinguishable from non-existent ones.

        Args:
            detail: Custom error message. If None, uses standard not found message.

        Returns:
            Response with 404 status to hide resource existence.
        """
        return Response(
            {"detail": detail or APIError.RESOURCE_NOT_FOUND},
            status=status.HTTP_404_NOT_FOUND,
        )

    @staticmethod
    def bad_request(detail: Optional[str] = None) -> Response:
        """
        Return a standard 400 Bad Request response.

        Args:
            detail: Custom error message. If None, uses standard message.

        Returns:
            Response with 400 status and standard error format.
        """
        return Response(
            {"detail": detail or APIError.BAD_REQUEST},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @staticmethod
    def validation_error(
        errors: Union[Dict[str, List[str]], str, DjangoValidationError]
    ) -> Response:
        """
        Return a standardized validation error response.

        Args:
            errors: Validation errors in various formats:
                   - Dict mapping field names to error lists
                   - String for general validation error
                   - Django ValidationError instance

        Returns:
            Response with 400 status and standardized error format.
        """
        if isinstance(errors, DjangoValidationError):
            if hasattr(errors, "message_dict"):
                # Field-specific errors
                formatted_errors = {}
                for field, messages in errors.message_dict.items():
                    if isinstance(messages, list):
                        formatted_errors[field] = messages
                    else:
                        formatted_errors[field] = [str(messages)]
                return Response(formatted_errors, status=status.HTTP_400_BAD_REQUEST)
            else:
                # Non-field errors - extract message from list if needed
                error_message = str(errors)
                if hasattr(errors, "messages") and errors.messages:
                    # Handle case where error.messages is a list
                    if isinstance(errors.messages, list) and len(errors.messages) > 0:
                        error_message = str(errors.messages[0])
                return Response(
                    {"detail": error_message}, status=status.HTTP_400_BAD_REQUEST
                )
        elif isinstance(errors, dict):
            # Already in field: [errors] format
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)
        elif isinstance(errors, str):
            # General error message
            return Response({"detail": errors}, status=status.HTTP_400_BAD_REQUEST)
        else:
            # Fallback for unexpected error types
            return Response(
                {"detail": APIError.VALIDATION_ERROR},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @staticmethod
    def unauthorized(detail: Optional[str] = None) -> Response:
        """
        Return a standard 401 Unauthorized response.

        Args:
            detail: Custom error message. If None, uses standard message.

        Returns:
            Response with 401 status and standard error format.
        """
        return Response(
            {"detail": detail or APIError.UNAUTHORIZED},
            status=status.HTTP_401_UNAUTHORIZED,
        )


class FieldValidator:
    """Standard field validation helpers."""

    @staticmethod
    def required_field(field_name: str, value: Any) -> Optional[Dict[str, List[str]]]:
        """
        Validate that a required field has a value.

        Args:
            field_name: Name of the field being validated.
            value: The field value to check.

        Returns:
            None if valid, or error dict if field is missing/empty.
        """
        if not value:
            return {field_name: [APIError.FIELD_REQUIRED]}
        return None

    @staticmethod
    def validate_user_exists(user_id: Any) -> Any:
        """
        Validate that a user exists by ID.

        Args:
            user_id: The user ID to validate.

        Returns:
            User instance if found, None if not found.
        """
        if not user_id:
            return None

        try:
            return User.objects.get(id=user_id)
        except (User.DoesNotExist, ValueError, TypeError):
            return None

    @staticmethod
    def build_field_errors(
        **field_errors: Union[str, List[str]]
    ) -> Dict[str, List[str]]:
        """
        Build a field errors dictionary from keyword arguments.

        Args:
            **field_errors: Field names mapped to error messages.

        Returns:
            Dictionary in DRF field error format.

        Example:
            >>> FieldValidator.build_field_errors(
            ...     username=["Username is required."],
            ...     email="Invalid email format."
            ... )
            {'username': ['Username is required.'], 'email': ['Invalid email format.']}
        """
        result = {}
        for field_name, error in field_errors.items():
            if isinstance(error, list):
                result[field_name] = error
            else:
                result[field_name] = [str(error)]
        return result


class SecurityResponseHelper:
    """Helper for security-focused API responses."""

    @staticmethod
    def resource_access_denied() -> Response:
        """
        Standard response when user doesn't have access to a resource.

        Returns 404 to hide the existence of the resource, making private
        resources indistinguishable from non-existent ones.

        Returns:
            Response with 404 status using standard not found message.
        """
        return APIError.not_found()

    @staticmethod
    def safe_get_or_404(
        queryset: QuerySet[Model],
        user: Any,
        permission_check: Optional[Callable[[Any, Model], bool]] = None,
        **filter_kwargs: Any,
    ) -> Tuple[Optional[Model], Optional[Response]]:
        """
        Safely get an object or return 404 response, with optional permission check.

        Args:
            queryset: Django queryset to search in.
            user: User making the request.
            permission_check: Optional callable that takes (user, obj) and returns bool.
            **filter_kwargs: Additional filters for the queryset.

        Returns:
            Tuple of (object, None) if found and authorized, or (None, Response) if not.

        Example:
            >>> campaign, error_response = SecurityResponseHelper.safe_get_or_404(
            ...     Campaign.objects,
            ...     request.user,
            ...     lambda u, c: c.has_role(u, "OWNER", "GM"),
            ...     id=campaign_id,
            ...     is_active=True
            ... )
            >>> if error_response:
            ...     return error_response
        """
        try:
            obj = queryset.get(**filter_kwargs)
        except (queryset.model.DoesNotExist, ValueError, TypeError):
            return None, APIError.not_found()

        # Check permission if provided
        if permission_check and not permission_check(user, obj):
            # Return 404 to hide resource existence for security
            return None, APIError.not_found()

        return obj, None


def handle_django_validation_error(e: DjangoValidationError) -> Response:
    """
    Convert Django ValidationError to standardized API response.

    Args:
        e: Django ValidationError instance.

    Returns:
        Standardized API error response.
    """
    return APIError.validation_error(e)


def handle_common_api_exceptions(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator to handle common API exceptions with standardized responses.

    This decorator catches common exceptions and converts them to standard
    API responses. Apply to API view methods that perform database operations.

    Args:
        func: The view method to wrap.

    Returns:
        Wrapped function with exception handling.
    """

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except DjangoValidationError as e:
            return handle_django_validation_error(e)
        except Exception:
            # Log unexpected errors but don't leak details
            # TODO: Add proper logging here
            return APIError.bad_request("An error occurred processing your request.")

    return wrapper
