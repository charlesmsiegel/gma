from __future__ import annotations

import logging

from django.conf import settings
from django.db import models
from django.utils import timezone

from campaigns.models import Campaign

logger = logging.getLogger(__name__)


class SceneQuerySet(models.QuerySet):
    """Custom queryset for Scene model with optimized methods."""

    def for_user(self, user):
        """Get scenes accessible to a user with optimized query."""
        return self.filter(
            models.Q(campaign__owner=user) | models.Q(campaign__memberships__user=user)
        ).distinct()

    def with_details(self):
        """Get scenes with related data optimized for serialization."""
        return self.select_related("campaign", "created_by").prefetch_related(
            "participants"
        )

    def by_campaign(self, campaign_id):
        """Filter scenes by campaign ID efficiently."""
        return self.filter(campaign_id=campaign_id)

    def by_status(self, status):
        """Filter scenes by status with validation."""
        return self.filter(status=status)

    def active(self):
        """Get only active scenes."""
        return self.filter(status="ACTIVE")


class SceneManager(models.Manager):
    """Custom manager for Scene model."""

    def get_queryset(self):
        """Return custom queryset."""
        return SceneQuerySet(self.model, using=self._db)

    def for_user(self, user):
        """Get scenes accessible to a user."""
        return self.get_queryset().for_user(user)

    def with_details(self):
        """Get scenes with optimized related data loading."""
        return self.get_queryset().with_details()


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

    # Custom manager
    objects = SceneManager()

    class Meta:
        db_table = "scenes_scene"
        ordering = ["-created_at"]
        verbose_name = "Scene"
        verbose_name_plural = "Scenes"
        indexes = [
            # Composite index for common query patterns
            models.Index(fields=["campaign", "-created_at"]),
            models.Index(fields=["campaign", "status"]),
            models.Index(fields=["status", "-created_at"]),
            # Single field indexes
            models.Index(fields=["status"]),
            models.Index(fields=["created_by"]),
        ]

    def __str__(self) -> str:
        """Return the scene name."""
        return self.name

    def log_status_change(self, user, old_status, new_status):
        """
        Log scene status changes for audit trail.

        Args:
            user: The user making the change
            old_status: The previous status
            new_status: The new status
        """
        # Log using Django's logging system
        logger.info(
            "Scene status change: '%s' (%d) from '%s' to '%s' by user '%s' (%d)",
            self.name,
            self.pk,
            old_status,
            new_status,
            user.username,
            user.pk,
        )

        # Create audit log entry in database
        SceneStatusChangeLog.objects.create(
            scene=self,
            user=user,
            old_status=old_status,
            new_status=new_status,
            timestamp=timezone.now(),
        )


class SceneStatusChangeLog(models.Model):
    """
    Audit log for scene status changes.

    Tracks all scene status transitions with user attribution and timestamps
    for compliance and debugging purposes.
    """

    scene = models.ForeignKey(
        Scene,
        on_delete=models.CASCADE,
        related_name="status_change_logs",
        help_text="The scene that had its status changed",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="scene_status_changes",
        help_text="The user who made the status change",
    )
    old_status = models.CharField(
        max_length=10,
        choices=Scene.STATUS_CHOICES,
        help_text="The previous status of the scene",
    )
    new_status = models.CharField(
        max_length=10,
        choices=Scene.STATUS_CHOICES,
        help_text="The new status of the scene",
    )
    timestamp = models.DateTimeField(
        default=timezone.now,
        help_text="When the status change occurred",
    )

    class Meta:
        db_table = "scenes_scene_status_change_log"
        ordering = ["-timestamp"]
        verbose_name = "Scene Status Change Log"
        verbose_name_plural = "Scene Status Change Logs"
        indexes = [
            models.Index(fields=["scene", "-timestamp"]),
            models.Index(fields=["user", "-timestamp"]),
            models.Index(fields=["-timestamp"]),
        ]

    def __str__(self) -> str:
        """Return a readable representation of the status change."""
        return (
            f"Scene '{self.scene.name}' changed from {self.old_status} "
            f"to {self.new_status} by {self.user.username} at {self.timestamp}"
        )
