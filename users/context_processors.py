"""
Context processors for the users app.

Provides user-specific context variables to all templates.
"""

from typing import Any, Dict

from django.http import HttpRequest

from .models import User


def theme_context(request: HttpRequest) -> Dict[str, Any]:
    """
    Add user theme to template context.

    Returns both the theme name and theme object (if available).
    """
    # Handle edge cases: missing user attribute or None user
    if not hasattr(request, "user") or request.user is None:
        return {
            "user_theme": "light",
            "theme_object": None,
            "available_themes": [],
        }

    # Handle unauthenticated users
    if not request.user.is_authenticated:
        return {
            "user_theme": "light",
            "theme_object": None,
            "available_themes": _get_available_themes(),
        }

    # Get user theme with new system
    theme_name = request.user.get_theme_name()
    theme_object = request.user.get_theme_object()

    # Validate theme name against active themes
    available_themes = _get_available_themes()
    active_theme_names = [theme.name for theme in available_themes]

    # If no Theme objects exist (like in tests), fallback to legacy validation
    if not available_themes:
        valid_themes = [choice[0] for choice in User.THEME_CHOICES]
        if theme_name not in valid_themes:
            theme_name = "light"
    elif theme_name not in active_theme_names:
        theme_name = "light"

    return {
        "user_theme": theme_name,
        "theme_object": theme_object,
        "available_themes": _get_available_themes(),
    }


def _get_available_themes() -> list:
    """
    Get list of available themes.

    Returns empty list if Theme model is not available (during migrations).
    """
    try:
        from .models import Theme

        return list(Theme.get_available_themes())
    except Exception:
        # During migrations or if Theme model doesn't exist yet
        return []
