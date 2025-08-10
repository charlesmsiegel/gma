"""
Context processors for the users app.

Provides user-specific context variables to all templates.
"""

from typing import Any, Dict

from django.http import HttpRequest

from .models import User


def theme_context(request: HttpRequest) -> Dict[str, Any]:
    """Add user theme to template context."""
    # Handle edge cases: missing user attribute or None user
    if not hasattr(request, "user") or request.user is None:
        return {"user_theme": "light"}

    # Handle unauthenticated users
    if not request.user.is_authenticated:
        return {"user_theme": "light"}

    # Get user theme with validation
    theme = getattr(request.user, "theme", "light")
    valid_themes = [choice[0] for choice in User.THEME_CHOICES]

    return {"user_theme": theme if theme in valid_themes else "light"}
