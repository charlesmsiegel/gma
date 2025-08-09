"""Utility functions for user authentication and management."""

from typing import Optional

from django.contrib.auth import authenticate, get_user_model
from django.http import HttpRequest


def authenticate_by_email_or_username(
    request: Optional[HttpRequest], username: str, password: str
) -> Optional[object]:
    """
    Authenticate user by username or email.

    This function handles both email and username authentication in a consistent way:
    - If the username contains '@', it treats it as an email and looks up the user
    - Falls back to regular username authentication if email lookup fails
    - Returns the authenticated user or None if authentication fails

    Args:
        request: The HTTP request object (can be None for API contexts)
        username: Username or email address
        password: User's password

    Returns:
        User object if authentication succeeds, None otherwise
    """
    if not username or not password:
        return None

    User = get_user_model()

    # Check if input looks like email and try to get user by email first
    if "@" in username:
        try:
            # Look up user by email (case-insensitive)
            user_obj = User.objects.get(email__iexact=username)
            # Use the found user's username for authentication
            return authenticate(
                request=request,
                username=user_obj.username,
                password=password,
            )
        except User.DoesNotExist:
            # Fall back to regular username authentication
            pass

    # Input is likely a username, or email lookup failed - authenticate directly
    return authenticate(
        request=request,
        username=username,
        password=password,
    )
