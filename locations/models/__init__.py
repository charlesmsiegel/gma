from django.conf import settings
from django.db import models

from campaigns.models import Campaign


class Location(models.Model):
    """
    Placeholder Location model for campaign management.

    This is a minimal implementation to support URL routing and basic views.
    Full location functionality will be implemented later.
    """

    name = models.CharField(max_length=200, help_text="Location name")
    description = models.TextField(
        blank=True, default="", help_text="Location description"
    )
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name="locations",
        help_text="The campaign this location belongs to",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_locations",
        help_text="The user who created this location",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "locations_location"
        ordering = ["name"]
        verbose_name = "Location"
        verbose_name_plural = "Locations"

    def __str__(self) -> str:
        """Return the location name."""
        return self.name
