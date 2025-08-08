from typing import Optional

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify


class Campaign(models.Model):
    """Campaign model for tabletop RPG campaigns."""

    name = models.CharField(max_length=200, help_text="Campaign name")
    slug = models.SlugField(
        max_length=200,
        unique=True,
        blank=True,
        help_text="URL-friendly campaign identifier",
    )
    description = models.TextField(blank=True, help_text="Campaign description")

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_campaigns",
        help_text="Campaign owner",
    )

    game_system = models.CharField(
        max_length=100,
        blank=True,
        help_text="The game system being used (free text entry)",
    )

    is_active = models.BooleanField(
        default=True, help_text="Whether the campaign is currently active"
    )

    is_public = models.BooleanField(
        default=False,
        help_text=(
            "Whether the campaign is visible to non-members. "
            "Private campaigns require membership to view."
        ),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "campaigns_campaign"
        ordering = ["-updated_at", "name"]
        verbose_name = "Campaign"
        verbose_name_plural = "Campaigns"

    def __str__(self):
        """Return the campaign name."""
        return self.name

    def save(self, *args, **kwargs):
        """Save the campaign with auto-generated slug."""
        if not self.slug:
            self.slug = self._generate_unique_slug()
        super().save(*args, **kwargs)

    def _generate_unique_slug(self) -> str:
        """Generate a unique slug for the campaign."""
        import uuid

        base_slug = slugify(self.name) or "campaign"

        # Truncate to fit in slug field (200 chars max)
        if len(base_slug) > 190:  # Leave room for suffix
            base_slug = base_slug[:190]

        # Simple uniqueness check
        counter = 0
        slug = base_slug
        while Campaign.objects.filter(slug=slug).exists():
            counter += 1
            if counter > 999:
                # Fallback to UUID after many attempts
                slug = f"{base_slug[:180]}-{uuid.uuid4().hex[:8]}"
                break
            slug = f"{base_slug}-{counter}"

        return slug

    def clean(self):
        """Validate the campaign data."""
        super().clean()
        if not self.name:
            raise ValidationError("Campaign name is required.")

    def get_user_role(self, user: Optional[AbstractUser]) -> Optional[str]:
        """Get user's role in this campaign.

        Args:
            user: The user to check permissions for

        Returns:
            The user's role ('OWNER', 'GM', 'PLAYER', 'OBSERVER') or None if not member
        """
        if not user or not user.is_authenticated:
            return None

        # Check direct ownership first (fastest check, no DB query)
        if self.owner == user:
            return "OWNER"

        # Single database query to get user's membership role
        membership = self.memberships.filter(user=user).first()
        return membership.role if membership else None

    def has_role(self, user: Optional[AbstractUser], *roles: str) -> bool:
        """Check if user has any of the specified roles in this campaign.

        Args:
            user: The user to check permissions for
            roles: One or more role names to check ('OWNER', 'GM', 'PLAYER', 'OBSERVER')

        Returns:
            True if user has any of the specified roles, False otherwise
        """
        user_role = self.get_user_role(user)
        return user_role in roles if user_role else False

    # Convenience methods for backward compatibility
    def is_owner(self, user: Optional[AbstractUser]) -> bool:
        """Check if the user is the campaign owner."""
        return self.has_role(user, "OWNER")

    def is_gm(self, user: Optional[AbstractUser]) -> bool:
        """Check if the user is a GM of this campaign."""
        return self.has_role(user, "GM")

    def is_player(self, user: Optional[AbstractUser]) -> bool:
        """Check if the user is a player in this campaign."""
        return self.has_role(user, "PLAYER")

    def is_observer(self, user: Optional[AbstractUser]) -> bool:
        """Check if the user is an observer of this campaign."""
        return self.has_role(user, "OBSERVER")

    def is_member(self, user: Optional[AbstractUser]) -> bool:
        """Check if the user has any membership in this campaign."""
        return self.has_role(user, "OWNER", "GM", "PLAYER", "OBSERVER")


class CampaignMembership(models.Model):
    """Membership relationship between users and campaigns."""

    ROLE_CHOICES = [
        ("GM", "Game Master"),
        ("PLAYER", "Player"),
        ("OBSERVER", "Observer"),
    ]

    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name="memberships",
        help_text="The campaign",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="campaign_memberships",
        help_text="The user",
    )
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        help_text="The user's role in the campaign",
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "campaigns_membership"
        constraints = [
            models.UniqueConstraint(
                fields=["campaign", "user"], name="unique_campaign_user_membership"
            ),
        ]
        ordering = ["campaign", "role", "user__username"]
        verbose_name = "Campaign Membership"
        verbose_name_plural = "Campaign Memberships"

    def __str__(self):
        """Return a string representation of the membership."""
        return f"{self.user.username} - {self.campaign.name} ({self.role})"

    def clean(self):
        """Validate the membership data."""
        super().clean()
        if self.campaign and self.user:
            # Prevent owner from having membership (handled by Campaign.owner field)
            if self.campaign.owner == self.user:
                raise ValidationError(
                    "Campaign owner cannot have a membership role. "
                    "Ownership is handled automatically."
                )
