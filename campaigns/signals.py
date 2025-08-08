"""
Django signals for campaign membership management.

This module contains signal handlers for campaign-related events like
invitations, membership changes, and notifications.
"""

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save, pre_delete, pre_save
from django.dispatch import receiver

User = get_user_model()


def send_notification(user, title, message, notification_type, **kwargs):
    """
    Send a notification to a user.

    Args:
        user: User to notify
        title: Notification title
        message: Notification message
        notification_type: Type of notification (e.g., 'invitation_received')
        **kwargs: Additional context data for the notification
    """
    # For now, this is a placeholder implementation
    # In production, this would integrate with a notification system
    print(f"Notification to {user.username}: {title} - {message}")
    return True


def send_websocket_notification(user, message_type, data=None, **kwargs):
    """
    Send a real-time WebSocket notification to a user.

    Args:
        user: User to notify
        message_type: Type of notification (e.g., 'invitation_received')
        data: Optional data dictionary for the notification
        **kwargs: Additional context data for the notification
    """
    # Placeholder implementation for WebSocket notifications
    data_str = f" - {data}" if data else ""
    print(f"WebSocket notification to {user.username}: {message_type}{data_str}")
    return True


def create_bulk_notifications(users, message_type, **kwargs):
    """
    Create bulk notifications for multiple users efficiently.

    Args:
        users: List of users to notify
        message_type: Type of notification
        **kwargs: Additional context data
    """
    # Placeholder implementation for bulk notifications
    for user in users:
        send_notification(user, message_type, **kwargs)
    return len(users)


# Signal handlers for campaign events
@receiver(post_save, sender="campaigns.CampaignInvitation")
def invitation_created_handler(sender, instance, created, **kwargs):
    """Handle invitation creation."""
    if created:
        # Check user notification preferences
        prefs = getattr(instance.invited_user, "notification_preferences", {})
        if prefs.get("invitation_emails", True):  # Default to True if not set
            send_notification(
                user=instance.invited_user,
                title="Campaign Invitation",
                message=(
                    f"{instance.invited_by.username} invited you to join "
                    f"{instance.campaign.name} as a {instance.role}"
                ),
                notification_type="invitation_received",
            )

            # Send WebSocket notification
            send_websocket_notification(
                user=instance.invited_user,
                message_type="invitation_received",
                data={
                    "campaign_name": instance.campaign.name,
                    "invited_by": instance.invited_by.username,
                    "role": instance.role,
                },
            )


@receiver(pre_save, sender="campaigns.CampaignMembership")
def membership_pre_save_handler(sender, instance, **kwargs):
    """Store old role before saving."""
    if instance.pk:  # Only for updates, not creates
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            instance._old_role = old_instance.role
        except sender.DoesNotExist:
            instance._old_role = None
    else:
        instance._old_role = None


@receiver(post_save, sender="campaigns.CampaignMembership")
def membership_created_handler(sender, instance, created, **kwargs):
    """Handle membership creation and updates."""
    if created:
        send_notification(
            user=instance.campaign.owner,
            title="New Member Joined",
            message=(
                f"{instance.user.username} joined {instance.campaign.name} "
                f"as a {instance.role}"
            ),
            notification_type="member_joined",
        )
    else:
        # Handle role changes
        old_role = getattr(instance, "_old_role", None)
        if old_role and old_role != instance.role:
            send_notification(
                user=instance.user,
                title="Role Changed",
                message=(
                    f"Your role in {instance.campaign.name} has been changed to "
                    f"{instance.role}"
                ),
                notification_type="role_changed",
            )


@receiver(pre_delete, sender="campaigns.CampaignMembership")
def membership_pre_delete_handler(sender, instance, **kwargs):
    """Handle membership deletion."""
    # Send notification to the removed member
    send_notification(
        user=instance.user,
        title="Removed from Campaign",
        message=f"You have been removed from {instance.campaign.name}",
        notification_type="member_removed",
    )


# Additional signal handlers that tests expect
def send_invitation_accepted_notification(invitation):
    """Send notification when invitation is accepted."""
    send_notification(
        user=invitation.invited_by,
        title="Invitation Accepted",
        message=(
            f"{invitation.invited_user.username} accepted your invitation "
            f"to join {invitation.campaign.name}"
        ),
        notification_type="invitation_accepted",
    )

    # Send WebSocket notification
    send_websocket_notification(
        user=invitation.invited_by,
        message_type="invitation_accepted",
        data={
            "invitee": invitation.invited_user.username,
            "campaign_name": invitation.campaign.name,
            "role": invitation.role,
        },
    )


def send_invitation_declined_notification(invitation):
    """Send notification when invitation is declined."""
    send_notification(
        user=invitation.invited_by,
        title="Invitation Declined",
        message=(
            f"{invitation.invited_user.username} declined your invitation "
            f"to join {invitation.campaign.name}"
        ),
        notification_type="invitation_declined",
    )


def send_invitation_canceled_notification(invitation):
    """Send notification when invitation is canceled."""
    send_notification(
        user=invitation.invited_user,
        title="Invitation Canceled",
        message=(
            f"Your invitation to join {invitation.campaign.name} " f"has been canceled"
        ),
        notification_type="invitation_canceled",
    )


def send_member_removed_notification(campaign, removed_user, removed_by):
    """Send notification when member is removed."""
    # Notify the removed user
    send_notification(
        user=removed_user,
        title="Removed from Campaign",
        message=f"You have been removed from {campaign.name}",
        notification_type="member_removed",
    )

    # Also notify the campaign owner (if they weren't the one removed)
    if removed_user != campaign.owner:
        send_notification(
            user=campaign.owner,
            title="Member Removed",
            message=f"{removed_user.username} was removed from {campaign.name}",
            notification_type="member_removed",
        )
