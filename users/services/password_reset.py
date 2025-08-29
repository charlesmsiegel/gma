"""
Password reset service for handling password reset functionality.

This service handles password reset functionality for Issue #135,
providing methods for sending password reset emails and managing
reset tokens and state.
"""

import logging

from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger(__name__)


class PasswordResetService:
    """Service class for password reset operations."""

    def send_reset_email(self, user, reset):
        """
        Send password reset email to the user.

        Args:
            user (User): The user to send reset email to
            reset (PasswordReset): The password reset instance

        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        try:
            from django.core.mail import send_mail
            from django.urls import reverse

            # Create password reset email
            subject = "Password Reset Request"

            # Create email body with token
            reset_url = reverse(
                "api:auth:password_reset_validate", kwargs={"token": reset.token}
            )
            body = f"""
Hello {user.username},

You have requested a password reset for your account.
Please click the link below to reset your password:

Token: {reset.token}
Reset URL: {reset_url}

If you did not request this password reset, please ignore this email.

Thank you,
Your Application Team
"""

            send_mail(
                subject=subject,
                message=body,
                from_email=(
                    settings.DEFAULT_FROM_EMAIL
                    if hasattr(settings, "DEFAULT_FROM_EMAIL")
                    else "noreply@example.com"
                ),
                recipient_list=[user.email],
                fail_silently=False,
            )

            logger.info(f"Password reset email sent for user {user.id}")
            return True

        except Exception as e:
            logger.error(f"Error sending password reset email for user {user.id}: {e}")
            return False

    def is_reset_required(self, user):
        """
        Check if password reset is required for the user.

        Args:
            user (User): The user to check

        Returns:
            bool: True if reset is allowed, False otherwise
        """
        # Password reset is allowed for active users
        return user.is_active

    def cleanup_expired_resets(self):
        """
        Clean up expired password reset records.

        Returns:
            int: Number of expired records cleaned up
        """
        from users.models import PasswordReset

        return PasswordReset.objects.cleanup_expired()

    def invalidate_user_resets(self, user):
        """
        Invalidate all password resets for a user.

        Args:
            user (User): The user to invalidate resets for

        Returns:
            int: Number of resets invalidated
        """
        from users.models import PasswordReset

        return PasswordReset.objects.invalidate_user_resets(user)
