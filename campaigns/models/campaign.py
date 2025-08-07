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

    def is_owner(self, user: Optional[AbstractUser]) -> bool:
        """Check if the user is the campaign owner."""
        if not user or not user.is_authenticated:
            return False
        return self.owner == user

    def is_gm(self, user: Optional[AbstractUser]) -> bool:
        """Check if the user is a GM of this campaign."""
        if not user or not user.is_authenticated:
            return False
        return self.memberships.filter(user=user, role="gm", is_active=True).exists()

    def is_player(self, user: Optional[AbstractUser]) -> bool:
        """Check if the user is a player in this campaign."""
        if not user or not user.is_authenticated:
            return False
        return self.memberships.filter(
            user=user, role="player", is_active=True
        ).exists()

    def is_observer(self, user: Optional[AbstractUser]) -> bool:
        """Check if the user is an observer of this campaign."""
        if not user or not user.is_authenticated:
            return False
        return self.memberships.filter(
            user=user, role="observer", is_active=True
        ).exists()

    def is_member(self, user: Optional[AbstractUser]) -> bool:
        """Check if the user has any membership in this campaign."""
        if not user or not user.is_authenticated:
            return False
        return self.memberships.filter(user=user, is_active=True).exists()

    def get_user_role(self, user: Optional[AbstractUser]) -> Optional[str]:
        """Get the highest role for a user in this campaign.

        Args:
            user: The user to check permissions for

        Returns:
            The user's role ('owner', 'gm', 'player', 'observer') or None
        """
        if not user or not user.is_authenticated:
            return None

        # Owner has the highest permission level
        if self.is_owner(user):
            return "owner"

        # Check membership roles
        membership = self.memberships.filter(user=user, is_active=True).first()
        if membership:
            return membership.role

        return None


class CampaignMembership(models.Model):
    """Membership relationship between users and campaigns."""

    ROLE_CHOICES = [
        ("gm", "Game Master"),
        ("player", "Player"),
        ("observer", "Observer"),
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
        max_length=20,
        choices=ROLE_CHOICES,
        help_text="The user's role in the campaign",
    )
    is_active = models.BooleanField(
        default=True, help_text="Whether this membership is currently active"
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "campaigns_membership"
        unique_together = [["campaign", "user"]]
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
            # Validate campaign owner membership logic
            if self.campaign.owner == self.user:
                # Campaign owners can have any role, but we recommend GM
                if self.role not in ["gm", "player", "observer"]:
                    raise ValidationError(
                        "Campaign owner must have a valid role "
                        "(gm, player, or observer)."
                    )
                # Note: We could add a warning here for non-GM roles, but
                # Django's clean method doesn't have a standard way to issue
                # warnings. This could be handled in the admin interface or
                # view layer.
