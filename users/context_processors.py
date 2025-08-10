"""
Context processors for the users app.

Provides user-specific context variables to all templates.
"""

from typing import Any, Dict

from django.http import HttpRequest


def theme_context(request: HttpRequest) -> Dict[str, Any]:
    """
    Add user theme to template context.

    Injects the user's selected theme into the template context as 'user_theme'.
    For anonymous users or users without a theme set, defaults to 'light'.

    Args:
        request: The HTTP request object containing user information.

    Returns:
        Dictionary with 'user_theme' key containing the theme name.
    """
    # Handle various edge cases for missing user or theme
    theme = "light"  # Default theme

    # Check if request has user attribute
    if hasattr(request, "user"):
        user = request.user

        # Check if user is authenticated and has theme attribute
        if user and hasattr(user, "is_authenticated") and user.is_authenticated:
            if hasattr(user, "theme"):
                # Get user's theme, validate it's in allowed choices
                user_theme = user.theme

                # List of valid themes
                valid_themes = [
                    "light",
                    "dark",
                    "forest",
                    "ocean",
                    "sunset",
                    "midnight",
                    "lavender",
                    "mint",
                    "high-contrast",
                    "warm",
                    "gothic",
                    "cyberpunk",
                    "vintage",
                ]

                # Use user's theme if valid, otherwise default
                if user_theme in valid_themes:
                    theme = user_theme

    return {"user_theme": theme}
