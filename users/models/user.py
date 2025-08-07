import zoneinfo

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models


def validate_timezone(value):
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

    display_name = models.CharField(
        max_length=100,
        blank=True,
        unique=True,
        null=True,  # Allow NULL for empty names (unique constraint ignores NULL)
        help_text="Optional unique display name for your profile",
    )
    timezone = models.CharField(
        max_length=50, default="UTC", validators=[validate_timezone]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users_user"
        ordering = ["username"]
        verbose_name = "User"
        verbose_name_plural = "Users"

    def get_display_name(self):
        """Return display_name if set, otherwise fall back to username."""
        return self.display_name or self.username
