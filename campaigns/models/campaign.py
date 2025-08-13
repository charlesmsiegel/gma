from datetime import timedelta
from typing import Any, Optional, cast

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, QuerySet
from django.utils import timezone
from django.utils.text import slugify


class CampaignInvitationManager(models.Manager):
    """Custom manager for CampaignInvitation model.

    Only contains methods that provide complex business logic beyond Django ORM.
    Use standard Django ORM methods for simple filtering:
    - CampaignInvitation.objects.filter(status="PENDING") instead of .pending()
    - CampaignInvitation.objects.filter(campaign=campaign) instead of
      .for_campaign(campaign)
    - CampaignInvitation.objects.filter(invited_user=user) instead of
      .for_user(user)
    """

    def cleanup_expired(self) -> int:
        """Clean up expired invitations.

        Very old invitations (30+ days expired) are deleted.
        Recently expired invitations are marked as EXPIRED.

        Returns:
            int: Number of invitations processed (updated + deleted)
        """
        now = timezone.now()
        very_old_threshold = now - timedelta(days=30)

        # Delete very old expired invitations
        very_old_expired = self.filter(
            status="PENDING",
            expires_at__isnull=False,
            expires_at__lt=very_old_threshold,
        )
        deleted_count, _ = very_old_expired.delete()

        # Mark recently expired as EXPIRED status
        recently_expired = self.filter(
            status="PENDING",
            expires_at__isnull=False,
            expires_at__lt=now,
            expires_at__gte=very_old_threshold,
        )
        updated_count = recently_expired.update(status="EXPIRED")

        return deleted_count + updated_count


class CampaignManager(models.Manager):
    """Custom manager for Campaign model with visibility filtering."""

    def visible_to_user(self, user: Optional[AbstractUser]) -> "QuerySet[Campaign]":
        """Return campaigns visible to the given user.

        Args:
            user: The user to filter campaigns for

        Returns:
            QuerySet of campaigns visible to the user
        """
        if user and user.is_authenticated:
            # Authenticated users see:
            # 1. Public campaigns
            # 2. Private campaigns where they are members (including owner)
            return self.filter(
                Q(is_public=True)  # Public campaigns
                | Q(owner=user)  # Campaigns they own
                | Q(memberships__user=user)  # Campaigns they're members of
            ).distinct()
        else:
            # Unauthenticated users see only public campaigns
            return self.filter(is_public=True)


class Campaign(models.Model):
    """Campaign model for tabletop RPG campaigns."""

    name = models.CharField(  # type: ignore[var-annotated]
        max_length=200, help_text="Campaign name"
    )
    slug = models.SlugField(  # type: ignore[var-annotated]
        max_length=200,
        unique=True,
        blank=True,
        help_text="URL-friendly campaign identifier",
    )
    description = models.TextField(  # type: ignore[var-annotated]
        blank=True, help_text="Campaign description"
    )

    owner = models.ForeignKey(  # type: ignore[var-annotated]
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_campaigns",
        help_text="Campaign owner",
    )

    game_system = models.CharField(  # type: ignore[var-annotated]
        max_length=100,
        blank=True,
        help_text="The game system being used (free text entry)",
    )

    is_active = models.BooleanField(  # type: ignore[var-annotated]
        default=True,
        db_index=True,
        help_text="Whether the campaign is currently active",
    )

    is_public = models.BooleanField(  # type: ignore[var-annotated]
        default=False,
        db_index=True,
        help_text=(
            "Whether the campaign is visible to non-members. "
            "Private campaigns require membership to view."
        ),
    )

    allow_observer_join = models.BooleanField(  # type: ignore[var-annotated]
        default=False,
        help_text="Allow anyone to join as an observer without invitation",
    )

    allow_player_join = models.BooleanField(  # type: ignore[var-annotated]
        default=False,
        help_text="Allow anyone to join as a player without invitation",
    )

    max_characters_per_player = models.PositiveIntegerField(  # type: ignore[var-annotated]  # noqa: E501
        default=1,
        help_text="Maximum number of characters each player can have in this campaign",
    )

    # Character deletion permissions
    # These settings provide granular control over character deletion to protect
    # player investment and campaign continuity in tabletop RPG contexts
    allow_owner_character_deletion = models.BooleanField(  # type: ignore[var-annotated]
        default=True,
        help_text=(
            "Allow campaign owner to delete any character in this campaign. "
            "Default True for backwards compatibility. Players can always "
            "delete their own characters."
        ),
    )

    allow_gm_character_deletion = models.BooleanField(  # type: ignore[var-annotated]
        default=False,
        help_text=(
            "Allow Game Masters to delete any character in this campaign. "
            "Default False to protect player investment. GMs can always "
            "delete their own characters."
        ),
    )

    created_at = models.DateTimeField(auto_now_add=True)  # type: ignore[var-annotated]
    updated_at = models.DateTimeField(auto_now=True)  # type: ignore[var-annotated]

    objects = CampaignManager()

    class Meta:
        db_table = "campaigns_campaign"
        ordering = ["-updated_at", "name"]
        verbose_name = "Campaign"
        verbose_name_plural = "Campaigns"

    def __str__(self) -> str:
        """Return the campaign name."""
        return self.name

    def save(self, *args: Any, **kwargs: Any) -> None:
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

    def clean(self) -> None:
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
        membership = self.memberships.filter(  # type: ignore[attr-defined]
            user=cast(Any, user)
        ).first()
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

    # Convenience methods - use has_role() for most cases or these shortcuts
    # for common patterns
    def is_owner(self, user: Optional[AbstractUser]) -> bool:
        """Check if the user is the campaign owner."""
        return self.has_role(user, "OWNER")

    def is_member(self, user: Optional[AbstractUser]) -> bool:
        """Check if the user has any membership in this campaign.

        For specific role checks, use has_role(user, "ROLE") instead of
        dedicated methods.
        """
        return self.has_role(user, "OWNER", "GM", "PLAYER", "OBSERVER")

    # Legacy methods for backward compatibility - consider migrating to has_role()
    def is_gm(self, user: Optional[AbstractUser]) -> bool:
        """Check if the user is a GM.

        Consider using has_role(user, 'GM') instead.
        """
        return self.has_role(user, "GM")

    def is_player(self, user: Optional[AbstractUser]) -> bool:
        """Check if the user is a player.

        Consider using has_role(user, 'PLAYER') instead.
        """
        return self.has_role(user, "PLAYER")

    def is_observer(self, user: Optional[AbstractUser]) -> bool:
        """Check if the user is an observer.

        Consider using has_role(user, 'OBSERVER') instead.
        """
        return self.has_role(user, "OBSERVER")


class CampaignMembership(models.Model):
    """Membership relationship between users and campaigns."""

    ROLE_CHOICES = [
        ("GM", "Game Master"),
        ("PLAYER", "Player"),
        ("OBSERVER", "Observer"),
    ]

    campaign = models.ForeignKey(  # type: ignore[var-annotated]
        Campaign,
        on_delete=models.CASCADE,
        related_name="memberships",
        help_text="The campaign",
    )
    user = models.ForeignKey(  # type: ignore[var-annotated]
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="campaign_memberships",
        help_text="The user",
    )
    role = models.CharField(  # type: ignore[var-annotated]
        max_length=10,
        choices=ROLE_CHOICES,
        help_text="The user's role in the campaign",
    )
    joined_at = models.DateTimeField(auto_now_add=True)  # type: ignore[var-annotated]

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

    def __str__(self) -> str:
        """Return a string representation of the membership."""
        return f"{self.user.username} - {self.campaign.name} ({self.role})"

    def clean(self) -> None:
        """Validate the membership data."""
        super().clean()
        if self.campaign and self.user:
            # Prevent owner from having membership (handled by Campaign.owner field)
            if self.campaign.owner == self.user:
                raise ValidationError(
                    "Campaign owner cannot have a membership role. "
                    "Ownership is handled automatically."
                )


class CampaignInvitation(models.Model):
    """Invitation to join a campaign."""

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("ACCEPTED", "Accepted"),
        ("DECLINED", "Declined"),
        ("EXPIRED", "Expired"),
    ]

    campaign = models.ForeignKey(  # type: ignore[var-annotated]
        Campaign,
        on_delete=models.CASCADE,
        related_name="invitations",
        help_text="The campaign being invited to",
    )
    invited_user = models.ForeignKey(  # type: ignore[var-annotated]
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="campaign_invitations",
        help_text="The user being invited",
    )
    invited_by = models.ForeignKey(  # type: ignore[var-annotated]
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_invitations",
        help_text="The user who sent the invitation",
    )
    role = models.CharField(  # type: ignore[var-annotated]
        max_length=10,
        choices=CampaignMembership.ROLE_CHOICES,
        help_text="The role being offered",
    )
    status = models.CharField(  # type: ignore[var-annotated]
        max_length=10,
        choices=STATUS_CHOICES,
        default="PENDING",
        help_text="Current status of the invitation",
    )
    message = models.TextField(  # type: ignore[var-annotated]
        blank=True,
        help_text="Optional message from the inviter",
    )
    created_at = models.DateTimeField(auto_now_add=True)  # type: ignore[var-annotated]
    expires_at = models.DateTimeField(  # type: ignore[var-annotated]
        null=True, blank=True, help_text="When this invitation expires"
    )

    objects = CampaignInvitationManager()

    class Meta:
        db_table = "campaigns_invitation"
        constraints = [
            models.UniqueConstraint(
                fields=["campaign", "invited_user"],
                name="unique_campaign_user_invitation",
            ),
        ]
        ordering = ["-created_at"]
        verbose_name = "Campaign Invitation"
        verbose_name_plural = "Campaign Invitations"
        indexes = [
            models.Index(fields=["invited_user", "status"]),
            models.Index(fields=["campaign", "status"]),
        ]

    def __str__(self) -> str:
        """Return a string representation of the invitation."""
        return (
            f"{self.invited_user.username} invited to {self.campaign.name} "
            f"as {self.role}"
        )

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Save the invitation with auto-generated expiry."""
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)

    def clean(self) -> None:
        """Validate the invitation data."""
        super().clean()

        if self.campaign and self.invited_user:
            # Prevent inviting campaign owner
            if self.campaign.owner == self.invited_user:
                raise ValidationError("Cannot invite the campaign owner.")

            # Prevent duplicate active invitations
            if self.pk is None:  # Only check on creation
                existing = CampaignInvitation.objects.filter(
                    campaign=self.campaign,
                    invited_user=self.invited_user,
                    status="PENDING",
                ).exists()
                if existing:
                    raise ValidationError(
                        "User already has a pending invitation to this campaign."
                    )

            # Prevent inviting existing members
            if CampaignMembership.objects.filter(
                campaign=self.campaign, user=self.invited_user
            ).exists():
                raise ValidationError("User is already a member of this campaign.")

    @property
    def is_expired(self) -> bool:
        """Check if invitation has expired."""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at

    def accept(self) -> "CampaignMembership":
        """Accept the invitation and create membership."""
        if self.status != "PENDING":
            raise ValidationError("Only pending invitations can be accepted.")

        if self.is_expired:
            raise ValidationError("This invitation has expired.")

        # Create membership
        membership = CampaignMembership.objects.create(
            campaign=self.campaign, user=self.invited_user, role=self.role
        )

        # Update invitation status
        self.status = "ACCEPTED"
        self.save()

        # Notification removed for simplicity

        return membership

    def decline(self) -> None:
        """Decline the invitation."""
        if self.status == "DECLINED":
            # Already declined, idempotent operation
            return
        if self.status != "PENDING":
            raise ValidationError("Only pending invitations can be declined.")

        self.status = "DECLINED"
        self.save()

        # Notification removed for simplicity

    def cancel(self) -> None:
        """Cancel the invitation (for senders/campaign owners)."""
        if self.status != "PENDING":
            raise ValidationError("Only pending invitations can be cancelled.")

        # Notification removed for simplicity

        self.delete()
