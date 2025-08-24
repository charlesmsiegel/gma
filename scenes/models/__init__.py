from __future__ import annotations

import logging

from django.conf import settings
from django.core.exceptions import ValidationError
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


class MessageQuerySet(models.QuerySet):
    """Custom queryset for Message model with optimized methods."""

    def for_scene(self, scene_id):
        """Get messages for a specific scene."""
        return self.filter(scene_id=scene_id)

    def public_messages(self):
        """Get only public messages."""
        return self.filter(message_type="PUBLIC")

    def private_messages(self):
        """Get only private messages."""
        return self.filter(message_type="PRIVATE")

    def system_messages(self):
        """Get only system messages."""
        return self.filter(message_type="SYSTEM")

    def ooc_messages(self):
        """Get only out-of-character messages."""
        return self.filter(message_type="OOC")

    def by_character(self, character):
        """Get messages sent by a specific character."""
        return self.filter(character=character)

    def by_sender(self, user):
        """Get messages sent by a specific user."""
        return self.filter(sender=user)

    def with_details(self):
        """Get messages with related data optimized for serialization."""
        return self.select_related(
            "scene", "character", "sender", "scene__campaign"
        ).prefetch_related("recipients")


class MessageManager(models.Manager):
    """Custom manager for Message model."""

    def get_queryset(self):
        """Return custom queryset."""
        return MessageQuerySet(self.model, using=self._db)

    def for_scene(self, scene_id):
        """Get messages for a specific scene."""
        return self.get_queryset().for_scene(scene_id)

    def with_details(self):
        """Get messages with optimized related data loading."""
        return self.get_queryset().with_details()


class Message(models.Model):
    """
    Message model for storing chat messages in scenes.

    Supports both in-character (IC) and out-of-character (OOC) messages
    with proper relationships to scenes and characters.
    """

    TYPE_CHOICES = [
        ("PUBLIC", "Public"),
        ("PRIVATE", "Private"),
        ("SYSTEM", "System"),
        ("OOC", "Out of Character"),
    ]

    scene = models.ForeignKey(
        Scene,
        on_delete=models.CASCADE,
        related_name="messages",
        help_text="The scene this message belongs to",
    )
    character = models.ForeignKey(
        "characters.Character",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_messages",
        help_text="Character sending the message (for IC messages)",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="sent_messages",
        help_text="User who sent the message",
    )
    content = models.TextField(help_text="The message content (supports Markdown)")
    message_type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES,
        default="PUBLIC",
        help_text="Type of message",
    )
    recipients = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="received_private_messages",
        blank=True,
        help_text="Recipients for private messages",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the message was sent",
    )

    # Custom manager
    objects = MessageManager()

    class Meta:
        db_table = "scenes_message"
        ordering = ["created_at"]
        verbose_name = "Message"
        verbose_name_plural = "Messages"
        indexes = [
            # Composite indexes for common query patterns
            models.Index(fields=["scene", "created_at"]),
            models.Index(fields=["scene", "message_type"]),
            models.Index(fields=["sender", "created_at"]),
            models.Index(fields=["message_type", "created_at"]),
            # Single field indexes
            models.Index(fields=["message_type"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        """Return a readable representation of the message."""
        if self.character:
            return f"[{self.scene.name}] {self.character.name}: {self.content[:50]}"
        elif self.message_type == "OOC":
            username = self.sender.username if self.sender else "[Deleted User]"
            return f"[{self.scene.name}] {username} (OOC): {self.content[:50]}"
        else:
            username = self.sender.username if self.sender else "[Deleted User]"
            return f"[{self.scene.name}] {username}: {self.content[:50]}"

    def clean(self):
        """Validate the message model."""
        super().clean()

        # Only enforce character requirement for certain message types
        # The test expects that not all message types require characters

        # OOC messages cannot have character attribution
        if self.message_type == "OOC" and self.character:
            raise ValidationError("OOC messages cannot have character attribution")

        # Only GMs can send system messages (skip if sender is None due to deletion)
        if self.message_type == "SYSTEM" and self.sender:
            campaign = self.scene.campaign
            user_role = campaign.get_user_role(self.sender)
            if user_role not in ["OWNER", "GM"]:
                raise ValidationError("Only GMs can send system messages")

        # Character must belong to the same campaign as the scene
        if self.character and self.character.campaign != self.scene.campaign:
            raise ValidationError(
                "Character must belong to the same campaign as the scene"
            )

        # Character must be owned by the sender
        # (unless GM/Owner or sender is None due to deletion)
        if (
            self.character
            and self.sender
            and self.character.player_owner != self.sender
        ):
            campaign = self.scene.campaign
            user_role = campaign.get_user_role(self.sender)
            if user_role not in ["OWNER", "GM"]:
                raise ValidationError(
                    "You can only send messages as characters you own"
                )

        # Sender must be a participant in the scene or campaign owner/GM
        # (skip if sender is None due to deletion)
        if self.sender and not self.can_send_message():
            raise ValidationError("Sender must be a participant in the scene")

        # Sender is required for new messages
        # (but can be None if user deleted)
        if not self.pk and not self.sender:  # Only for new instances
            raise ValidationError("Sender is required when creating a message")

        # Content length validation
        if len(self.content.strip()) == 0:
            raise ValidationError("Message content cannot be empty")

        if len(self.content) > 20000:  # Allow up to 20k characters
            raise ValidationError("Message content cannot exceed 20000 characters")

    def can_send_message(self):
        """Check if the sender can send messages in this scene."""
        # If sender is None (deleted), can't validate permissions
        if not self.sender:
            return True

        campaign = self.scene.campaign

        # Campaign owner can always send messages
        if campaign.owner == self.sender:
            return True

        # Check if sender is a campaign member
        if campaign.is_member(self.sender):
            return True

        # Check if sender is a scene participant through their characters
        user_characters = self.sender.characters.filter(campaign=campaign)
        scene_participants = self.scene.participants.all()

        return user_characters.filter(
            id__in=scene_participants.values_list("id", flat=True)
        ).exists()

    def can_be_seen_by(self, user):
        """Check if a user can see this message."""
        campaign = self.scene.campaign

        # Campaign owners and GMs can see all messages
        user_role = campaign.get_user_role(user)
        if user_role in ["OWNER", "GM"]:
            return True

        # Public and OOC messages can be seen by all scene participants
        if self.message_type in ["PUBLIC", "OOC", "SYSTEM"]:
            return campaign.is_member(user)

        # Private messages can be seen by sender and recipients
        if self.message_type == "PRIVATE":
            if self.sender and user == self.sender:
                return True
            return self.recipients.filter(id=user.id).exists()

        return False

    def get_display_name(self):
        """Get the display name for the message sender."""
        if self.character:
            return self.character.name
        if self.sender:
            return self.sender.username
        return "[Deleted User]"

    def is_ic_message(self):
        """Check if this is an in-character message."""
        return self.character is not None and self.message_type == "PUBLIC"

    def is_ooc_message(self):
        """Check if this is an out-of-character message."""
        return self.message_type == "OOC"

    def is_private_message(self):
        """Check if this is a private message."""
        return self.message_type == "PRIVATE"

    def is_system_message(self):
        """Check if this is a system message."""
        return self.message_type == "SYSTEM"
