from __future__ import annotations

from django.db import models

from campaigns.models import Campaign
from core.models import (
    AuditableMixin,
    DescribedModelMixin,
    NamedModelMixin,
    TimestampedMixin,
)


class Location(
    TimestampedMixin, NamedModelMixin, DescribedModelMixin, AuditableMixin, models.Model
):
    """
    Location model for campaign management with mixin-based functionality.

    Provides standardized fields through mixins:
    - TimestampedMixin: created_at, updated_at fields with indexing
    - NamedModelMixin: name field with __str__ method
    - DescribedModelMixin: description field
    - AuditableMixin: created_by, modified_by tracking with enhanced save()
    """

    campaign: models.ForeignKey = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name="locations",
        help_text="The campaign this location belongs to",
    )

    class Meta:
        db_table = "locations_location"
        ordering = ["name"]
        verbose_name = "Location"
        verbose_name_plural = "Locations"
