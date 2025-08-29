"""
Email verification service for user registration and email confirmation.

This service handles email verification functionality for Issue #135,
providing methods for sending verification emails, verifying tokens,
and managing verification state.
"""

import logging

from django.conf import settings
from django.contrib.auth import get_user_model

from users.models import EmailVerification

User = get_user_model()
logger = logging.getLogger(__name__)


class EmailVerificationService:
    """Service class for email verification operations."""

    def is_verification_required(self, user):
        """
        Check if email verification is required for the user.

        Args:
            user (User): The user to check

        Returns:
            bool: True if verification is required, False otherwise
        """
        # In production, email verification should always be required
        # In development, it can be disabled via settings
        verification_required = getattr(settings, "EMAIL_VERIFICATION_REQUIRED", True)

        if not verification_required:
            return False

        # If user already has verified email, no verification needed
        return not user.email_verified

    def verify_email(self, token):
        """
        Verify an email using a verification token.

        Args:
            token (str): The verification token

        Returns:
            tuple: (success, user_or_none, message)
        """
        try:
            # Find the verification record
            verification = EmailVerification.objects.get_by_token(token)

            if not verification:
                return False, None, "Invalid verification token."

            if verification.is_expired():
                return (
                    False,
                    verification.user,
                    "Verification token has expired. Please request a new one.",
                )

            if verification.is_verified():
                return True, verification.user, "Email address is already verified."

            # Verify the token
            success = verification.verify(token)

            if success:
                return True, verification.user, "Email address verified successfully."
            else:
                return False, verification.user, "Failed to verify email address."

        except Exception as e:
            logger.error(f"Error during email verification: {e}")
            return False, None, "An error occurred during verification."

    def send_verification_email(self, user):
        """
        Send verification email to a new user.

        Args:
            user (User): The user to send verification to

        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        try:
            # Create verification for user
            verification = EmailVerification.create_for_user(user)

            # Send the actual email
            self._send_email(user, verification)

            logger.info(f"Email verification sent for user {user.id}")
            return True

        except Exception as e:
            logger.error(f"Error sending verification email for user {user.id}: {e}")
            return False

    def resend_verification_email(self, user):
        """
        Resend verification email to the user.

        Args:
            user (User): The user to send verification to

        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        try:
            # Invalidate any existing verifications for this user
            EmailVerification.objects.invalidate_user_verifications(user)

            # Create new verification
            verification = EmailVerification.create_for_user(user)

            # Send the actual email
            self._send_email(user, verification)

            logger.info(f"Email verification resent for user {user.id}")
            return True

        except Exception as e:
            logger.error(f"Error resending verification email for user {user.id}: {e}")
            return False

    def _send_email(self, user, verification):
        """
        Internal method to send verification email. Separated for easier testing.

        Args:
            user (User): The user to send email to
            verification (EmailVerification): The verification instance
        """
        from html import escape

        from django.core.mail import send_mail
        from django.urls import reverse

        # Create verification email
        subject = "Email Verification Required"

        # Build verification URL
        verify_path = reverse(
            "api:auth:verify_email", kwargs={"token": verification.token}
        )

        # Create a full URL (fallback for tests)
        verify_url = f"http://localhost:8000{verify_path}"

        # Escape user input for security
        safe_username = escape(user.username)

        body = f"""
Hello {safe_username},

Please verify your email address by clicking the link below:

Token: {verification.token}
Verification URL: {verify_url}

If you did not create this account, please ignore this email.

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

    def create_verification_for_user(self, user):
        """
        Create a new email verification for a user.

        Args:
            user (User): The user to create verification for

        Returns:
            EmailVerification: The created verification instance
        """
        return EmailVerification.create_for_user(user)

    def cleanup_expired_verifications(self):
        """
        Clean up expired verification records.

        Returns:
            int: Number of expired records cleaned up
        """
        return EmailVerification.objects.cleanup_expired()

    def get_active_verification_for_user(self, user):
        """
        Get the active verification for a user.

        Args:
            user (User): The user to get verification for

        Returns:
            EmailVerification or None: The active verification or None
        """
        return EmailVerification.get_active_for_user(user)
