from django.conf import settings
from django.db import models

from campaigns.models import Campaign


class Item(models.Model):
    """
    Placeholder Item model for campaign management.

    This is a minimal implementation to support URL routing and basic views.
    Full item functionality will be implemented later.
    """

    name = models.CharField(max_length=200, help_text="Item name")
    description = models.TextField(blank=True, default="", help_text="Item description")
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name="items",
        help_text="The campaign this item belongs to",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_items",
        help_text="The user who created this item",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "items_item"
        ordering = ["name"]
        verbose_name = "Item"
        verbose_name_plural = "Items"

    def __str__(self) -> str:
        """Return the item name."""
        return self.name
