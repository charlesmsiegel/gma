import zoneinfo
from typing import TYPE_CHECKING

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models

if TYPE_CHECKING:
    from .theme import Theme


def validate_timezone(value: str) -> None:
    """
    Validate that the timezone string is a valid timezone identifier.

    Uses Python's zoneinfo module to validate timezone identifiers according to
    the IANA Time Zone Database. Accepts standard timezone names such as:
    - 'UTC'
    - 'America/New_York'
    - 'Europe/London'
    - 'Asia/Tokyo'

    Args:
        value (str): The timezone identifier string to validate.

    Raises:
        ValidationError: If the value is empty or not a valid timezone identifier.

    Examples:
        >>> validate_timezone('UTC')  # Valid - passes silently
        >>> validate_timezone('America/New_York')  # Valid - passes silently
        >>> validate_timezone('Invalid/Timezone')  # Raises ValidationError
        >>> validate_timezone('')  # Raises ValidationError
    """
    if not value:
        raise ValidationError("Timezone cannot be empty.")

    try:
        zoneinfo.ZoneInfo(value)
    except zoneinfo.ZoneInfoNotFoundError:
        raise ValidationError(f"'{value}' is not a valid timezone identifier.")


class User(AbstractUser):
    """Custom User model extending Django's AbstractUser."""

    # Legacy theme choices for backward compatibility
    THEME_CHOICES = [
        ("light", "Light"),
        ("dark", "Dark"),
        ("forest", "Forest"),
        ("ocean", "Ocean"),
        ("sunset", "Sunset"),
        ("midnight", "Midnight"),
        ("lavender", "Lavender"),
        ("mint", "Mint"),
        ("high-contrast", "High Contrast"),
        ("warm", "Warm"),
        ("gothic", "Gothic"),
        ("cyberpunk", "Cyberpunk"),
        ("vintage", "Vintage"),
    ]

    display_name = models.CharField(  # type: ignore[var-annotated]
        max_length=100,
        blank=True,
        unique=True,
        null=True,  # Allow NULL for empty names (unique constraint ignores NULL)
        help_text="Optional unique display name for your profile",
    )
    timezone = models.CharField(  # type: ignore[var-annotated]
        max_length=50, default="UTC", validators=[validate_timezone]
    )
    theme = models.CharField(  # type: ignore[var-annotated]
        max_length=20,
        choices=THEME_CHOICES,
        default="light",
        help_text="Choose your preferred theme for the interface",
    )
    notification_preferences = models.JSONField(
        default=dict, blank=True, help_text="User notification preferences"
    )
    # Email verification fields for Issue #135
    email_verified = models.BooleanField(
        default=False, help_text="Whether the user's email address has been verified"
    )  # type: ignore[var-annotated]
    email_verification_token = models.CharField(
        max_length=64, blank=True, help_text="Current email verification token"
    )  # type: ignore[var-annotated]
    email_verification_sent_at = models.DateTimeField(
        null=True, blank=True, help_text="When the last email verification was sent"
    )  # type: ignore[var-annotated]

    created_at = models.DateTimeField(auto_now_add=True)  # type: ignore[var-annotated]
    updated_at = models.DateTimeField(auto_now=True)  # type: ignore[var-annotated]

    class Meta:
        db_table = "users_user"
        ordering = ["username"]
        verbose_name = "User"
        verbose_name_plural = "Users"
        indexes = [
            # For username search performance
            models.Index(fields=["username"]),
            # For email search performance
            models.Index(fields=["email"]),
            # For combined search operations
            models.Index(fields=["username", "email"]),
        ]

    def get_display_name(self) -> str:
        """Return display_name if set, otherwise fall back to username."""
        return self.display_name or self.username

    def get_theme_name(self) -> str:
        """
        Get the user's theme name, with fallback logic.

        This method provides backward compatibility while supporting
        the new Theme model system.
        """
        # First, check if user has a theme preference
        if hasattr(self, "theme_preference") and self.theme_preference.current_theme:
            return self.theme_preference.current_theme.name

        # Fallback to legacy theme field
        if self.theme:
            return self.theme

        # Final fallback to light theme
        return "light"

    def get_theme_object(self) -> "Theme | None":
        """
        Get the Theme object for this user.

        Returns None if Theme model is not available (during migrations).
        """
        try:
            # Import here to avoid circular imports and migration issues
            from .theme import Theme

            # Check if user has a theme preference
            if (
                hasattr(self, "theme_preference")
                and self.theme_preference.current_theme
            ):
                return self.theme_preference.current_theme

            # Try to find theme by name from legacy field
            theme_name = self.theme or "light"
            theme = Theme.objects.filter(name=theme_name, is_active=True).first()

            if theme:
                return theme

            # Fallback to default theme
            return Theme.get_default_theme()
        except Exception:
            # During migrations or if Theme model doesn't exist yet
            return None
