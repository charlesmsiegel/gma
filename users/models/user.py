import zoneinfo
from typing import TYPE_CHECKING

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models

if TYPE_CHECKING:
    from .theme import Theme


def validate_timezone(value: str) -> None:
    """
    Validate that the timezone string is a valid timezone identifier.

    Uses Python's zoneinfo module to validate timezone identifiers according to
    the IANA Time Zone Database. Accepts standard timezone names such as:
    - 'UTC'
    - 'America/New_York'
    - 'Europe/London'
    - 'Asia/Tokyo'

    Args:
        value (str): The timezone identifier string to validate.

    Raises:
        ValidationError: If the value is empty or not a valid timezone identifier.

    Examples:
        >>> validate_timezone('UTC')  # Valid - passes silently
        >>> validate_timezone('America/New_York')  # Valid - passes silently
        >>> validate_timezone('Invalid/Timezone')  # Raises ValidationError
        >>> validate_timezone('')  # Raises ValidationError
    """
    if not value:
        raise ValidationError("Timezone cannot be empty.")

    try:
        zoneinfo.ZoneInfo(value)
    except zoneinfo.ZoneInfoNotFoundError:
        raise ValidationError(f"'{value}' is not a valid timezone identifier.")


class User(AbstractUser):
    """Custom User model extending Django's AbstractUser."""

    # Legacy theme choices for backward compatibility
    THEME_CHOICES = [
        ("light", "Light"),
        ("dark", "Dark"),
        ("forest", "Forest"),
        ("ocean", "Ocean"),
        ("sunset", "Sunset"),
        ("midnight", "Midnight"),
        ("lavender", "Lavender"),
        ("mint", "Mint"),
        ("high-contrast", "High Contrast"),
        ("warm", "Warm"),
        ("gothic", "Gothic"),
        ("cyberpunk", "Cyberpunk"),
        ("vintage", "Vintage"),
    ]

    display_name = models.CharField(  # type: ignore[var-annotated]
        max_length=100,
        blank=True,
        unique=True,
        null=True,  # Allow NULL for empty names (unique constraint ignores NULL)
        help_text="Optional unique display name for your profile",
    )
    timezone = models.CharField(  # type: ignore[var-annotated]
        max_length=50, default="UTC", validators=[validate_timezone]
    )
    theme = models.CharField(  # type: ignore[var-annotated]
        max_length=20,
        choices=THEME_CHOICES,
        default="light",
        help_text="Choose your preferred theme for the interface",
    )
    notification_preferences = models.JSONField(
        default=dict, blank=True, help_text="User notification preferences"
    )

    # Profile fields for Issue #137: User Profile Management
    bio = models.TextField(
        max_length=500,
        blank=True,
        help_text="A brief description about yourself (max 500 characters)",
    )  # type: ignore[var-annotated]
    avatar = models.ImageField(
        upload_to="avatars/", blank=True, null=True, help_text="Profile picture"
    )  # type: ignore[var-annotated]
    website_url = models.URLField(
        blank=True, help_text="Your personal website or portfolio"
    )  # type: ignore[var-annotated]
    social_links = models.JSONField(
        default=dict,
        blank=True,
        help_text="Social media links (Twitter, Discord, etc.)",
    )  # type: ignore[var-annotated]

    # Privacy settings for Issue #137
    profile_visibility = models.CharField(
        max_length=20,
        choices=[
            ("public", "Public - Visible to everyone"),
            ("members", "Campaign Members - Visible to users in your campaigns"),
            ("private", "Private - Only visible to you"),
        ],
        default="members",
        help_text="Who can view your profile information",
    )  # type: ignore[var-annotated]
    show_email = models.BooleanField(
        default=False,
        help_text="Whether to show your email address in your public profile",
    )  # type: ignore[var-annotated]
    show_real_name = models.BooleanField(
        default=True,
        help_text="Whether to show your first and last name in your public profile",
    )  # type: ignore[var-annotated]
    allow_activity_tracking = models.BooleanField(
        default=True,
        help_text="Whether to allow activity tracking for analytics and recommendations",  # noqa: E501
    )  # type: ignore[var-annotated]
    show_last_login = models.BooleanField(
        default=False, help_text="Whether to show when you were last online"
    )  # type: ignore[var-annotated]

    # Email verification fields for Issue #135
    email_verified = models.BooleanField(
        default=False, help_text="Whether the user's email address has been verified"
    )  # type: ignore[var-annotated]
    email_verification_token = models.CharField(
        max_length=64, blank=True, help_text="Current email verification token"
    )  # type: ignore[var-annotated]
    email_verification_sent_at = models.DateTimeField(
        null=True, blank=True, help_text="When the last email verification was sent"
    )  # type: ignore[var-annotated]

    created_at = models.DateTimeField(auto_now_add=True)  # type: ignore[var-annotated]
    updated_at = models.DateTimeField(auto_now=True)  # type: ignore[var-annotated]

    class Meta:
        db_table = "users_user"
        ordering = ["username"]
        verbose_name = "User"
        verbose_name_plural = "Users"
        indexes = [
            # For username search performance
            models.Index(fields=["username"]),
            # For email search performance
            models.Index(fields=["email"]),
            # For combined search operations
            models.Index(fields=["username", "email"]),
        ]

    def get_display_name(self) -> str:
        """Return display_name if set, otherwise fall back to username."""
        return self.display_name or self.username

    def get_theme_name(self) -> str:
        """
        Get the user's theme name, with fallback logic.

        This method provides backward compatibility while supporting
        the new Theme model system.
        """
        # First, check if user has a theme preference
        if hasattr(self, "theme_preference") and self.theme_preference.current_theme:
            return self.theme_preference.current_theme.name

        # Fallback to legacy theme field
        if self.theme:
            return self.theme

        # Final fallback to light theme
        return "light"

    def get_theme_object(self) -> "Theme | None":
        """
        Get the Theme object for this user.

        Returns None if Theme model is not available (during migrations).
        """
        try:
            # Import here to avoid circular imports and migration issues
            from .theme import Theme

            # Check if user has a theme preference
            if (
                hasattr(self, "theme_preference")
                and self.theme_preference.current_theme
            ):
                return self.theme_preference.current_theme

            # Try to find theme by name from legacy field
            theme_name = self.theme or "light"
            theme = Theme.objects.filter(name=theme_name, is_active=True).first()

            if theme:
                return theme

            # Fallback to default theme
            return Theme.get_default_theme()
        except Exception:
            # During migrations or if Theme model doesn't exist yet
            return None

    def get_full_display_name(self) -> str:
        """
        Get the user's full display name based on privacy settings.

        Returns display_name if available, otherwise first_name + last_name
        if show_real_name is True, otherwise just username.
        """
        if self.display_name:
            return self.display_name

        if self.show_real_name and (self.first_name or self.last_name):
            full_name = f"{self.first_name} {self.last_name}".strip()
            return full_name or self.username

        return self.username

    def get_avatar_url(self) -> str | None:
        """Get the avatar URL if avatar exists."""
        if self.avatar:
            return self.avatar.url
        return None

    def can_view_profile(self, viewer_user=None) -> bool:
        """
        Check if a user can view this user's profile based on privacy settings.

        Args:
            viewer_user: The user trying to view the profile (None for anonymous)

        Returns:
            bool: Whether the profile can be viewed
        """
        # Users can always view their own profile
        if viewer_user and viewer_user.id == self.id:
            return True

        # Check profile visibility setting
        if self.profile_visibility == "public":
            return True
        elif self.profile_visibility == "private":
            return False
        elif self.profile_visibility == "members":
            # Only campaign members can view
            if not viewer_user or not viewer_user.is_authenticated:
                return False

            # Check if they're in any campaigns together
            return self.are_campaign_members(viewer_user)

        return False

    def are_campaign_members(self, other_user) -> bool:
        """
        Check if this user and another user are in any campaigns together.

        Args:
            other_user: The other user to check

        Returns:
            bool: Whether they share campaign membership
        """
        if not other_user or not other_user.is_authenticated:
            return False

        # Import here to avoid circular imports
        from campaigns.models import CampaignMembership

        # Get campaigns where both users are members
        my_campaigns = set(
            CampaignMembership.objects.filter(user=self).values_list(
                "campaign_id", flat=True
            )
        )
        their_campaigns = set(
            CampaignMembership.objects.filter(user=other_user).values_list(
                "campaign_id", flat=True
            )
        )

        return len(my_campaigns & their_campaigns) > 0

    def get_public_profile_data(self, viewer_user=None) -> dict:
        """
        Get profile data that can be shown to a specific viewer based on privacy settings.

        Args:
            viewer_user: The user viewing the profile

        Returns:
            dict: Profile data filtered by privacy settings  # noqa: E501
        """
        if not self.can_view_profile(viewer_user):
            # Return minimal public data
            return {
                "username": self.username,
                "display_name": self.get_display_name(),
                "profile_visible": False,
            }

        data = {
            "id": self.id,
            "username": self.username,
            "display_name": self.get_full_display_name(),
            "bio": self.bio,
            "avatar_url": self.get_avatar_url(),
            "website_url": self.website_url,
            "social_links": self.social_links,
            "date_joined": self.date_joined,
            "profile_visible": True,
        }

        # Add email if allowed
        if self.show_email:
            data["email"] = self.email

        # Add real name if allowed
        if self.show_real_name:
            data["first_name"] = self.first_name
            data["last_name"] = self.last_name

        # Add last login if allowed
        if self.show_last_login:
            data["last_login"] = self.last_login

        return data

    # Email verification methods
    def generate_email_verification_token(self) -> str:
        """
        Generate a new email verification token for the user.

        Returns:
            str: The generated token
        """
        import secrets

        from django.utils import timezone

        self.email_verification_token = secrets.token_urlsafe(32)
        self.email_verification_sent_at = timezone.now()
        return self.email_verification_token

    def clear_email_verification_token(self) -> None:
        """Clear the email verification token."""
        self.email_verification_token = ""  # nosec B105
        self.email_verification_sent_at = None

    def mark_email_verified(self) -> None:
        """Mark the user's email as verified and clear the token."""
        self.email_verified = True
        self.clear_email_verification_token()

    def is_email_verification_token_expired(self) -> bool:
        """
        Check if the email verification token has expired.

        Returns:
            bool: True if token is expired or doesn't exist
        """
        from datetime import timedelta

        from django.utils import timezone

        if not self.email_verification_token or not self.email_verification_sent_at:
            return True

        # Token expires after 24 hours
        expiry_time = self.email_verification_sent_at + timedelta(hours=24)
        return timezone.now() > expiry_time

    def get_email_verification_expiry(self):
        """
        Get the expiry time for the current email verification token.

        Returns:
            datetime or None: The expiry time, or None if no token
        """
        from datetime import timedelta

        if not self.email_verification_sent_at:
            return None

        return self.email_verification_sent_at + timedelta(hours=24)
