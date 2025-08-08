"""
Notification models for campaign-related events.
"""

from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class Notification(models.Model):
    """
    Represents a notification for a user.
    """

    NOTIFICATION_TYPES = [
        ("invitation_received", "Invitation Received"),
        ("invitation_accepted", "Invitation Accepted"),
        ("invitation_declined", "Invitation Declined"),
        ("member_joined", "Member Joined"),
        ("member_left", "Member Left"),
        ("role_changed", "Role Changed"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="notifications"
    )
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Optional foreign key to campaign for campaign-related notifications
    campaign = models.ForeignKey(
        "Campaign",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.user.username}: {self.title}"

    def mark_read(self):
        """Mark this notification as read."""
        self.is_read = True
        self.save(update_fields=["is_read", "updated_at"])
