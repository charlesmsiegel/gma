"""
Password Reset model for Issue #136: Password Reset and Recovery System.

This model handles password reset tokens and their lifecycle:
- Secure token generation
- Expiration handling (24 hours default)
- One-time use enforcement
- IP address tracking for security
- Rate limiting support
"""

import secrets
from datetime import timedelta
from typing import Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class PasswordResetManager(models.Manager):
    """Manager for PasswordReset model with convenience methods."""

    def create_for_user(
        self, user, ip_address: Optional[str] = None
    ) -> "PasswordReset":
        """
        Create a password reset for a user, invalidating any existing resets.

        Args:
            user: The user requesting password reset
            ip_address: Optional IP address of the requester

        Returns:
            PasswordReset: The created password reset instance
        """
        from django.db import transaction

        # Use atomic transaction to prevent race conditions
        with transaction.atomic():
            # Invalidate any existing password resets for this user
            # Use select_for_update to lock the rows we're about to modify
            existing_resets = list(
                self.select_for_update().filter(user=user, used_at__isnull=True)
            )

            # Mark them as used
            for reset in existing_resets:
                reset.used_at = timezone.now()
                reset.save(update_fields=["used_at"])

            # Create new password reset
            return self.create(user=user, ip_address=ip_address)

    def get_valid_reset_by_token(self, token: str) -> Optional["PasswordReset"]:
        """
        Get a valid (not expired, not used) password reset by token.

        Args:
            token: The reset token to look up

        Returns:
            PasswordReset or None: The reset if valid, None otherwise
        """
        try:
            reset = self.get(token=token)
            return reset if reset.is_valid() else None
        except self.model.DoesNotExist:
            return None

    def cleanup_expired(self) -> int:
        """
        Remove expired and used password resets.

        Returns:
            int: Number of resets deleted
        """
        now = timezone.now()
        expired_resets = self.filter(
            models.Q(expires_at__lt=now) | models.Q(used_at__isnull=False)
        )
        count = expired_resets.count()
        expired_resets.delete()
        return count

    def get_recent_requests_for_user(self, user, minutes: int = 60) -> models.QuerySet:
        """
        Get recent password reset requests for a user.

        Args:
            user: The user to check
            minutes: How many minutes back to look

        Returns:
            QuerySet: Recent password reset requests
        """
        since = timezone.now() - timedelta(minutes=minutes)
        return self.filter(user=user, created_at__gte=since)

    def get_recent_requests_for_ip(
        self, ip_address: str, minutes: int = 60
    ) -> models.QuerySet:
        """
        Get recent password reset requests for an IP address.

        Args:
            ip_address: The IP address to check
            minutes: How many minutes back to look

        Returns:
            QuerySet: Recent password reset requests from this IP
        """
        since = timezone.now() - timedelta(minutes=minutes)
        return self.filter(ip_address=ip_address, created_at__gte=since)


class PasswordReset(models.Model):
    """
    Password reset token model.

    Each password reset request creates a record with:
    - Unique, cryptographically secure token
    - Expiration time (24 hours default)
    - Usage tracking (one-time use)
    - IP address logging for security
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="password_resets",
        help_text="User who requested the password reset",
    )

    token = models.CharField(
        max_length=64,
        unique=True,
        help_text="Unique token for password reset (64-character hex string)",
    )

    created_at = models.DateTimeField(
        auto_now_add=True, help_text="When the password reset was requested"
    )

    expires_at = models.DateTimeField(help_text="When the password reset token expires")

    used_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the password reset was used (None if unused)",
    )

    ip_address = models.GenericIPAddressField(
        null=True, blank=True, help_text="IP address from which the reset was requested"
    )

    objects = PasswordResetManager()

    class Meta:
        db_table = "users_password_reset"
        ordering = ["-created_at"]
        verbose_name = "Password Reset"
        verbose_name_plural = "Password Resets"

        indexes = [
            # For fast token lookups
            models.Index(fields=["token"]),
            # For recent request queries
            models.Index(fields=["user", "created_at"]),
            # For cleanup operations
            models.Index(fields=["expires_at"]),
        ]

    def save(self, *args, **kwargs):
        """Override save to generate token and set expiration."""
        if not self.token:
            self.token = self._generate_unique_token()

        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)

        super().save(*args, **kwargs)

    def _generate_token(self) -> str:
        """
        Generate a cryptographically secure token.

        Returns:
            str: 64-character hexadecimal token
        """
        return secrets.token_hex(32)  # 32 bytes = 64 hex characters

    def _generate_unique_token(self) -> str:
        """
        Generate a unique token, handling collisions.

        Returns:
            str: 64-character hexadecimal token that's unique in the database
        """
        max_attempts = 10
        for attempt in range(max_attempts):
            token = self._generate_token()

            # Check if token already exists
            if not PasswordReset.objects.filter(token=token).exists():
                return token

        # If we get here, we had extreme bad luck with randomness
        # This should practically never happen with 256-bit tokens
        raise ValueError("Unable to generate unique token after maximum attempts")

    def __str__(self) -> str:
        """String representation of the password reset."""
        return f"Password reset for {self.user.email} ({self.token[:8]}...)"

    def is_expired(self) -> bool:
        """
        Check if the password reset token has expired.

        Returns:
            bool: True if expired, False otherwise
        """
        return timezone.now() > self.expires_at

    def is_used(self) -> bool:
        """
        Check if the password reset token has been used.

        Returns:
            bool: True if used, False otherwise
        """
        return self.used_at is not None

    def is_valid(self) -> bool:
        """
        Check if the password reset token is valid (not expired and not used).

        Returns:
            bool: True if valid, False otherwise
        """
        return not self.is_expired() and not self.is_used()

    def mark_as_used(self) -> None:
        """
        Mark the password reset as used.

        This is idempotent - calling multiple times has no additional effect.
        """
        if not self.is_used():
            self.used_at = timezone.now()
            self.save(update_fields=["used_at"])

    def clean(self):
        """Validate the model fields."""
        super().clean()

        # Validate token length if set
        if self.token and len(self.token) != 64:
            raise ValidationError({"token": "Token must be exactly 64 characters long"})

        # Validate that token is hexadecimal if set
        if self.token:
            try:
                int(self.token, 16)
            except ValueError:
                raise ValidationError(
                    {"token": "Token must be a valid hexadecimal string"}
                )
