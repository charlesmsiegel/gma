"""
Email verification model for user registration with email confirmation.

This model provides standalone email verification functionality for Issue #135,
allowing users to verify their email addresses after registration.
"""

import secrets
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class EmailVerification(models.Model):
    """
    Model for managing email verification tokens.

    Provides secure token-based email verification with expiration handling
    and security features to prevent abuse.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        help_text="The user this verification token belongs to",
    )
    token = models.CharField(
        max_length=64, unique=True, help_text="Unique verification token"
    )
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="When this verification token was created"
    )
    expires_at = models.DateTimeField(help_text="When this verification token expires")
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this verification was completed (null if not verified)",
    )

    class Meta:
        db_table = "users_email_verification"
        verbose_name = "Email Verification"
        verbose_name_plural = "Email Verifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["token"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self):
        """String representation of the email verification."""
        status = "Verified" if self.verified_at else "Pending"
        return f"{self.user.email} - {status} ({self.created_at.strftime('%Y-%m-%d')})"

    def save(self, *args, **kwargs):
        """Override save to generate token and set expiration if not provided."""
        if not self.token:
            self.token = self.generate_unique_token()

        if not self.expires_at:
            # Default expiration of 24 hours from creation
            self.expires_at = timezone.now() + timedelta(hours=24)

        super().save(*args, **kwargs)

    @classmethod
    def generate_unique_token(cls, max_attempts=10):
        """
        Generate a cryptographically secure unique token.

        Args:
            max_attempts (int): Maximum attempts to generate unique token

        Returns:
            str: A unique 64-character token

        Raises:
            ValidationError: If unable to generate unique token after max_attempts
        """
        for attempt in range(max_attempts):
            # Generate 32 random bytes and convert to 64-character hex string
            token = secrets.token_hex(32)

            # Check if token already exists
            if not cls.objects.filter(token=token).exists():
                return token

        # If we couldn't generate a unique token after max attempts
        raise ValidationError(
            "Unable to generate unique verification token. Please try again."
        )

    def is_expired(self):
        """
        Check if the verification token has expired.

        Returns:
            bool: True if expired, False if still valid
        """
        return timezone.now() > self.expires_at

    def is_verified(self):
        """
        Check if the email has been verified.

        Returns:
            bool: True if verified, False if not verified
        """
        return self.verified_at is not None

    def verify(self):
        """
        Mark this verification as completed.

        Returns:
            bool: True if verification was successful, False if already verified
                or expired
        """
        if self.is_verified():
            return False

        if self.is_expired():
            return False

        self.verified_at = timezone.now()
        self.save(update_fields=["verified_at"])

        # Update user's email verification status
        self.user.email_verified = True
        self.user.save(update_fields=["email_verified"])

        return True

    def clean(self):
        """Validate the EmailVerification instance."""
        super().clean()

        # Check that expires_at is in the future (if being created)
        if not self.pk and self.expires_at and self.expires_at <= timezone.now():
            raise ValidationError(
                {"expires_at": "Expiration time must be in the future."}
            )

        # Check that verified_at is not in the future
        if self.verified_at and self.verified_at > timezone.now():
            raise ValidationError(
                {"verified_at": "Verification time cannot be in the future."}
            )

        # If verified, verified_at should be after created_at
        if self.verified_at and self.created_at and self.verified_at < self.created_at:
            raise ValidationError(
                {"verified_at": "Verification time cannot be before creation time."}
            )

    @classmethod
    def create_for_user(cls, user, expires_in_hours=24):
        """
        Create a new email verification for a user.

        Args:
            user (User): The user to create verification for
            expires_in_hours (int): Hours until verification expires

        Returns:
            EmailVerification: The created verification instance
        """
        # Deactivate any existing verifications for this user
        cls.objects.filter(user=user, verified_at__isnull=True).update(
            expires_at=timezone.now()  # Expire immediately
        )

        verification = cls.objects.create(
            user=user, expires_at=timezone.now() + timedelta(hours=expires_in_hours)
        )

        # Update user's verification fields
        user.email_verification_token = verification.token
        user.email_verification_sent_at = verification.created_at
        user.save(
            update_fields=["email_verification_token", "email_verification_sent_at"]
        )

        return verification

    @classmethod
    def get_active_for_user(cls, user):
        """
        Get the active (non-expired, unverified) verification for a user.

        Args:
            user (User): The user to get verification for

        Returns:
            EmailVerification or None: The active verification or None if not found
        """
        return cls.objects.filter(
            user=user, verified_at__isnull=True, expires_at__gt=timezone.now()
        ).first()

    @classmethod
    def cleanup_expired(cls):
        """
        Clean up expired verification records.

        Returns:
            int: Number of expired records deleted
        """
        expired_count, _ = cls.objects.filter(
            expires_at__lt=timezone.now(), verified_at__isnull=True
        ).delete()

        return expired_count
