from __future__ import annotations

from django.conf import settings
from django.db import models

from campaigns.models import Campaign


class Scene(models.Model):
    """
    Enhanced Scene model for campaign management.

    Manages scenes within campaigns with status tracking and character participation.
    """

    STATUS_CHOICES = [
        ("ACTIVE", "Active"),
        ("CLOSED", "Closed"),
        ("ARCHIVED", "Archived"),
    ]

    name: models.CharField = models.CharField(max_length=200, help_text="Scene name")
    description: models.TextField = models.TextField(
        blank=True, default="", help_text="Scene description"
    )
    campaign: models.ForeignKey = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name="scenes",
        help_text="The campaign this scene belongs to",
    )
    created_by: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_scenes",
        help_text="The user who created this scene",
    )
    status: models.CharField = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="ACTIVE",
        help_text="Current status of the scene",
    )
    participants: models.ManyToManyField = models.ManyToManyField(
        "characters.Character",
        related_name="participated_scenes",
        blank=True,
        help_text="Characters participating in this scene",
    )
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    updated_at: models.DateTimeField = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "scenes_scene"
        ordering = ["-created_at"]
        verbose_name = "Scene"
        verbose_name_plural = "Scenes"

    def __str__(self) -> str:
        """Return the scene name."""
        return self.name
