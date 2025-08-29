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
            from django.urls import reverse

            # Create password reset email
            subject = "Password Reset Request"

            # Create email body with token - escape HTML for security
            from html import escape

            from django.contrib.sites.shortcuts import get_current_site
            from django.http import HttpRequest

            # Build full URL
            reset_path = reverse(
                "api:auth:password_reset_validate", kwargs={"token": reset.token}
            )

            # Create a fake request to get the current site
            fake_request = HttpRequest()
            fake_request.META["HTTP_HOST"] = "localhost:8000"  # Default for tests
            fake_request.META["SERVER_PORT"] = "8000"
            fake_request.META["wsgi.url_scheme"] = "http"

            try:
                current_site = get_current_site(fake_request)
                reset_url = f"http://{current_site.domain}{reset_path}"
            except Exception:
                # Fallback if site framework is not available
                reset_url = f"http://localhost:8000{reset_path}"

            # Escape user input for security
            safe_username = escape(user.username)

            body = f"""
Hello {safe_username},

You have requested a password reset for your account.
Please click the link below to reset your password:

Token: {reset.token}
Reset URL: {reset_url}

If you did not request this password reset, please ignore this email.

Thank you,
Your Application Team
"""

            # Use internal _send_email method for easier testing
            self._send_email(
                subject=subject,
                message=body,
                from_email=(
                    settings.DEFAULT_FROM_EMAIL
                    if hasattr(settings, "DEFAULT_FROM_EMAIL")
                    else "noreply@example.com"
                ),
                recipient_list=[user.email],
                html_message=None,
            )

            logger.info(f"Password reset email sent for user {user.id}")
            return True

        except Exception as e:
            logger.error(f"Error sending password reset email for user {user.id}: {e}")
            return False

    def _send_email(
        self, subject, message, from_email, recipient_list, html_message=None
    ):
        """
        Internal method to send email. Separated for easier testing.

        Args:
            subject (str): Email subject
            message (str): Email message body
            from_email (str): From email address
            recipient_list (list): List of recipient email addresses
            html_message (str, optional): HTML version of the email
        """
        from django.core.mail import send_mail

        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=recipient_list,
            fail_silently=False,
            html_message=html_message,
        )

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
