from django.conf import settings
from django.db import models

from campaigns.models import Campaign


class Scene(models.Model):
    """
    Placeholder Scene model for campaign management.

    This is a minimal implementation to support URL routing and basic views.
    Full scene functionality will be implemented later.
    """

    name = models.CharField(max_length=200, help_text="Scene name")
    description = models.TextField(
        blank=True, default="", help_text="Scene description"
    )
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name="scenes",
        help_text="The campaign this scene belongs to",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_scenes",
        help_text="The user who created this scene",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "scenes_scene"
        ordering = ["-created_at"]
        verbose_name = "Scene"
        verbose_name_plural = "Scenes"

    def __str__(self) -> str:
        """Return the scene name."""
        return self.name
