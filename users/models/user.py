import zoneinfo

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models


def validate_timezone(value):
    """Validate that the timezone string is a valid timezone identifier."""
    if not value:
        raise ValidationError("Timezone cannot be empty.")

    try:
        zoneinfo.ZoneInfo(value)
    except zoneinfo.ZoneInfoNotFoundError:
        raise ValidationError(f"'{value}' is not a valid timezone identifier.")


class User(AbstractUser):
    """Custom User model extending Django's AbstractUser."""

    display_name = models.CharField(max_length=100, blank=True)
    timezone = models.CharField(
        max_length=50, default="UTC", validators=[validate_timezone]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users_user"
        ordering = ["username"]

    def get_display_name(self):
        """Return display_name if set, otherwise fall back to username."""
        return self.display_name or self.username
