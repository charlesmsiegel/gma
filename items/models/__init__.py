from __future__ import annotations

from django.db import models

from campaigns.models import Campaign
from core.models import (
    AuditableMixin,
    DescribedModelMixin,
    NamedModelMixin,
    TimestampedMixin,
)


class Item(
    TimestampedMixin, NamedModelMixin, DescribedModelMixin, AuditableMixin, models.Model
):
    """
    Item model for campaign management with mixin-based functionality.

    Provides standardized fields through mixins:
    - TimestampedMixin: created_at, updated_at fields with indexing
    - NamedModelMixin: name field with __str__ method
    - DescribedModelMixin: description field
    - AuditableMixin: created_by, modified_by tracking with enhanced save()
    """

    campaign: models.ForeignKey = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name="items",
        help_text="The campaign this item belongs to",
    )

    class Meta:
        db_table = "items_item"
        ordering = ["name"]
        verbose_name = "Item"
        verbose_name_plural = "Items"
