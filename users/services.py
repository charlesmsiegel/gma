"""
Email verification service for user registration with email confirmation.

This service provides business logic for email verification functionality
for Issue #135, handling token generation, email sending, and verification.
"""

import logging
from typing import TYPE_CHECKING, Optional

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from .models import EmailVerification
from .models.password_reset import PasswordReset

# from django.utils import timezone  # Removed unused import


if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser
logger = logging.getLogger(__name__)


class EmailVerificationService:
    """
    Service for managing email verification functionality.

    Handles the complete email verification workflow including
    token generation, email sending, and verification processing.
    """

    def __init__(self):
        """Initialize the email verification service."""
        self.from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@example.com")
        self.site_name = getattr(settings, "SITE_NAME", "Game Master Application")

    def create_verification_for_user(
        self, user: "AbstractUser", expires_in_hours: int = 24
    ) -> EmailVerification:
        """
        Create a new email verification for a user.

        Args:
            user: The user to create verification for
            expires_in_hours: Hours until verification expires

        Returns:
            EmailVerification: The created verification instance
        """
        return EmailVerification.create_for_user(user, expires_in_hours)

    def send_verification_email(self, user: "AbstractUser") -> bool:
        """
        Send verification email to user.

        Args:
            user: User to send verification email to

        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        try:
            # Get or create active verification
            verification = EmailVerification.get_active_for_user(user)
            if not verification:
                verification = self.create_verification_for_user(user)
                # Update user's verification fields
                user.email_verification_token = verification.token
                user.email_verification_sent_at = verification.created_at
                user.save(
                    update_fields=[
                        "email_verification_token",
                        "email_verification_sent_at",
                    ]
                )

            # Build verification URL
            verification_url = self._build_verification_url(verification.token)

            # Prepare email context
            context = {
                "user": user,
                "verification": verification,
                "verification_url": verification_url,
                "site_name": self.site_name,
                "expires_in_hours": 24,  # Default expiration
            }

            # Render email content
            subject = f"Verify your email address - {self.site_name}"

            # Try to use templates if they exist
            try:
                html_message = render_to_string(
                    "users/emails/email_verification.html", context
                )
                text_message = render_to_string(
                    "users/emails/email_verification.txt", context
                )
            except Exception:
                # Fallback to simple text message
                text_message = self._get_fallback_email_content(
                    user.username, verification_url, self.site_name
                )
                html_message = None

            # Send email
            send_mail(
                subject=subject,
                message=text_message,
                from_email=self.from_email,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )

            logger.info(f"Verification email sent to user ID {user.id}")
            return True

        except Exception as e:
            logger.error(f"Failed to send verification email to {user.email}: {str(e)}")
            return False

    def verify_email(self, token: str) -> tuple[bool, Optional["AbstractUser"], str]:
        """
        Verify email using token.

        Args:
            token: Verification token

        Returns:
            tuple: (success, user, message)
        """
        try:
            verification = EmailVerification.objects.filter(token=token).first()

            if not verification:
                return False, None, "Invalid verification token."

            # Check if user is active
            if not verification.user.is_active:
                return False, verification.user, "User account is inactive."

            if verification.is_verified():
                return True, verification.user, "Email already verified."

            if verification.is_expired():
                return False, verification.user, "Verification token has expired."

            # Perform verification
            success = verification.verify()
            if success:
                # Clear user's verification token fields since it's now used
                verification.user.email_verification_token = ""  # nosec B105
                verification.user.email_verification_sent_at = None
                verification.user.save(
                    update_fields=[
                        "email_verification_token",
                        "email_verification_sent_at",
                    ]
                )

                logger.info(f"Email verified for user {verification.user.email}")
                return True, verification.user, "Email verified successfully."
            else:
                return False, verification.user, "Verification failed."

        except Exception as e:
            logger.error(f"Error during email verification for token {token}: {str(e)}")
            return False, None, "An error occurred during verification."

    def resend_verification_email(self, user: "AbstractUser") -> bool:
        """
        Resend verification email to user.

        Args:
            user: User to resend verification email to

        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        try:
            # Check if user's email is already verified
            if user.email_verified:
                logger.info(f"User {user.email} already verified, not resending")
                return False

            # Create new verification (this will deactivate old ones)
            verification = self.create_verification_for_user(user)

            # Update user's verification fields
            user.email_verification_token = verification.token
            user.email_verification_sent_at = verification.created_at
            user.save(
                update_fields=["email_verification_token", "email_verification_sent_at"]
            )

            # Send the email
            return self.send_verification_email(user)

        except Exception as e:
            logger.error(
                f"Failed to resend verification email to {user.email}: {str(e)}"
            )
            return False

    def is_verification_required(self, user: "AbstractUser") -> bool:
        """
        Check if email verification is required for user.

        Args:
            user: User to check

        Returns:
            bool: True if verification is required, False otherwise
        """
        return not user.email_verified

    def get_verification_status(self, user: "AbstractUser") -> dict:
        """
        Get verification status information for user.

        Args:
            user: User to get status for

        Returns:
            dict: Status information
        """
        verification = EmailVerification.get_active_for_user(user)

        return {
            "email_verified": user.email_verified,
            "verification_required": self.is_verification_required(user),
            "verification_sent_at": user.email_verification_sent_at,
            "has_active_verification": verification is not None,
            "verification_expires_at": (
                verification.expires_at if verification else None
            ),
        }

    def cleanup_expired_verifications(self) -> int:
        """
        Clean up expired verification records.

        Returns:
            int: Number of expired records deleted
        """
        return EmailVerification.cleanup_expired()

    def _build_verification_url(self, token: str) -> str:
        """
        Build the verification URL for the given token.

        Args:
            token: Verification token

        Returns:
            str: Complete verification URL
        """
        # Get domain from settings or use localhost
        allowed_hosts = getattr(settings, "ALLOWED_HOSTS", ["localhost"])
        if allowed_hosts and allowed_hosts[0] != "*":
            domain = allowed_hosts[0]
        else:
            domain = "localhost:8000"

        # Use HTTPS in production, HTTP in development
        protocol = "https" if not settings.DEBUG else "http"

        # Build the URL - this points to the API endpoint for email verification
        return f"{protocol}://{domain}/verify-email/{token}/"

    def _get_fallback_email_content(
        self,
        username: str,
        verification_url: str,
        site_name: str,
    ) -> str:
        """
        Generate fallback email content when templates are not available.

        Args:
            username: User's username
            verification_url: URL for verification
            site_name: Name of the site

        Returns:
            str: Email content
        """
        return f"""
Hello {username},

Thank you for registering with {site_name}!

To complete your registration, please verify your email address by clicking
the link below:

{verification_url}

This verification link will expire in 24 hours.

If you did not create an account, please ignore this email.

Thank you,
The {site_name} Team
        """.strip()


class PasswordResetService:
    """
    Service for managing password reset functionality.

    Handles the complete password reset workflow including
    token generation, email sending, and password reset processing.
    """

    def __init__(self):
        """Initialize the password reset service."""
        self.from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@example.com")
        self.site_name = getattr(settings, "SITE_NAME", "Game Master Application")

    def create_reset_for_user(
        self, user: "AbstractUser", ip_address: Optional[str] = None
    ) -> PasswordReset:
        """
        Create a new password reset for a user.

        Args:
            user: The user to create password reset for
            ip_address: Optional IP address of the requester

        Returns:
            PasswordReset: The created password reset instance
        """
        return PasswordReset.objects.create_for_user(user, ip_address)

    def send_reset_email(self, user: "AbstractUser", reset: PasswordReset) -> bool:
        """
        Send password reset email to user.

        Args:
            user: User to send password reset email to
            reset: Password reset instance

        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        try:
            # Build reset URL
            reset_url = self._build_reset_url(reset.token)

            # Prepare email context
            context = {
                "user": user,
                "reset": reset,
                "reset_url": reset_url,
                "site_name": self.site_name,
                "expires_in_hours": 24,  # Default expiration
            }

            # Render email content
            subject = f"Password Reset - {self.site_name}"

            # Try to use templates if they exist
            try:
                html_message = render_to_string(
                    "users/emails/password_reset.html", context
                )
                text_message = render_to_string(
                    "users/emails/password_reset.txt", context
                )
            except Exception:
                # Fallback to simple text message
                text_message = self._get_fallback_reset_email_content(
                    user.username, reset_url, self.site_name
                )
                html_message = None

            # Send email
            send_mail(
                subject=subject,
                message=text_message,
                from_email=self.from_email,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )

            logger.info(f"Password reset email sent to user ID {user.id}")
            return True

        except Exception as e:
            logger.error(
                f"Failed to send password reset email to {user.email}: {str(e)}"
            )
            return False

    def validate_reset_token(self, token: str) -> Optional[PasswordReset]:
        """
        Validate password reset token.

        Args:
            token: Reset token

        Returns:
            PasswordReset or None: Reset instance if valid, None otherwise
        """
        return PasswordReset.objects.get_valid_reset_by_token(token)

    def reset_password(self, token: str, new_password: str) -> tuple[bool, str]:
        """
        Reset user password using token.

        Args:
            token: Reset token
            new_password: New password

        Returns:
            tuple: (success, message)
        """
        try:
            reset = self.validate_reset_token(token)

            if not reset:
                return False, "Invalid or expired reset token."

            # Reset password
            user = reset.user
            user.set_password(new_password)
            user.save()

            # Mark token as used
            reset.mark_as_used()

            logger.info(f"Password reset successful for user {user.email}")
            return True, "Password reset successful."

        except Exception as e:
            logger.error(f"Error during password reset for token {token}: {str(e)}")
            return False, "An error occurred during password reset."

    def cleanup_expired_resets(self) -> int:
        """
        Clean up expired password reset records.

        Returns:
            int: Number of expired records deleted
        """
        return PasswordReset.objects.cleanup_expired()

    def _build_reset_url(self, token: str) -> str:
        """
        Build the password reset URL for the given token.

        Args:
            token: Reset token

        Returns:
            str: Complete password reset URL
        """
        # Get domain from settings or use localhost
        allowed_hosts = getattr(settings, "ALLOWED_HOSTS", ["localhost"])
        if allowed_hosts and allowed_hosts[0] != "*":
            domain = allowed_hosts[0]
        else:
            domain = "localhost:8000"

        # Use HTTPS in production, HTTP in development
        protocol = "https" if not settings.DEBUG else "http"

        # Build the URL - this points to the frontend password reset page
        return f"{protocol}://{domain}/reset-password/{token}/"

    def _get_fallback_reset_email_content(
        self,
        username: str,
        reset_url: str,
        site_name: str,
    ) -> str:
        """
        Generate fallback password reset email content when templates are not available.

        Args:
            username: User's username
            reset_url: URL for password reset
            site_name: Name of the site

        Returns:
            str: Email content
        """
        return f"""
Hello {username},

We received a request to reset your password for your {site_name} account.

To reset your password, please click the link below:

{reset_url}

This password reset link will expire in 24 hours.

If you did not request a password reset, please ignore this email.
Your password will not be changed.

Thank you,
The {site_name} Team
        """.strip()
