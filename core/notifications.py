"""
Core notification system for the GMA application.

This module provides the foundation for notifications across the application,
including email notifications, in-app notifications, and WebSocket notifications.
"""

from typing import Any, Dict, List

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string

User = get_user_model()


class NotificationManager:
    """Manages all types of notifications in the application."""

    def __init__(self):
        self.enabled = getattr(settings, "NOTIFICATIONS_ENABLED", True)

    def send_email_notification(
        self, user: User, subject: str, template: str, context: Dict[str, Any]
    ) -> bool:
        """
        Send an email notification to a user.

        Args:
            user: User to notify
            subject: Email subject
            template: Template name for email body
            context: Template context data

        Returns:
            bool: True if sent successfully
        """
        if not self.enabled:
            return False

        try:
            html_content = render_to_string(template, context)
            send_mail(
                subject=subject,
                message="",  # Plain text version would go here
                html_message=html_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            return True
        except Exception as e:
            print(f"Failed to send email notification to {user.email}: {e}")
            return False

    def create_in_app_notification(
        self, user: User, message: str, notification_type: str = "info"
    ) -> bool:
        """
        Create an in-app notification for a user.

        Args:
            user: User to notify
            message: Notification message
            notification_type: Type of notification
                ('info', 'success', 'warning', 'error')

        Returns:
            bool: True if created successfully
        """
        if not self.enabled:
            return False

        # Placeholder implementation - in production this would create
        # a database record or add to a message queue
        print(f"In-app notification for {user.username}: {message}")
        return True


# Global notification manager instance
notification_manager = NotificationManager()


def create_notification(user: User, message_type: str, **context) -> bool:
    """
    Create a notification for a user.

    Args:
        user: User to notify
        message_type: Type of notification (e.g., 'invitation_received')
        **context: Additional context data

    Returns:
        bool: True if notification was created successfully
    """
    return notification_manager.create_in_app_notification(
        user=user, message=f"Notification: {message_type}", notification_type="info"
    )


def send_invitation_email(user: User, campaign, invited_by: User, role: str) -> bool:
    """
    Send invitation email notification.

    Args:
        user: User being invited
        campaign: Campaign they're being invited to
        invited_by: User who sent the invitation
        role: Role they're being invited as

    Returns:
        bool: True if sent successfully
    """
    context = {
        "user": user,
        "campaign": campaign,
        "invited_by": invited_by,
        "role": role,
    }

    return notification_manager.send_email_notification(
        user=user,
        subject=f"Invitation to join {campaign.name}",
        template="campaigns/emails/invitation.html",
        context=context,
    )


def send_bulk_notifications(users: List[User], message_type: str, **context) -> int:
    """
    Send notifications to multiple users efficiently.

    Args:
        users: List of users to notify
        message_type: Type of notification
        **context: Additional context data

    Returns:
        int: Number of notifications sent successfully
    """
    success_count = 0
    for user in users:
        if create_notification(user, message_type, **context):
            success_count += 1

    return success_count
