import zoneinfo

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models


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

    # Theme choices for interface customization
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
    created_at = models.DateTimeField(auto_now_add=True)  # type: ignore[var-annotated]
    updated_at = models.DateTimeField(auto_now=True)  # type: ignore[var-annotated]

    class Meta:
        db_table = "users_user"
        ordering = ["username"]
        verbose_name = "User"
        verbose_name_plural = "Users"

    def get_display_name(self) -> str:
        """Return display_name if set, otherwise fall back to username."""
        return self.display_name or self.username
