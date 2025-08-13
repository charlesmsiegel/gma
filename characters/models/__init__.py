from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from polymorphic.managers import PolymorphicManager  # type: ignore[import-untyped]
from polymorphic.models import PolymorphicModel  # type: ignore[import-untyped]

from campaigns.models import Campaign

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser


class CharacterQuerySet(models.QuerySet):
    """Custom QuerySet for Character with filtering methods."""

    def for_campaign(self, campaign: Campaign) -> "CharacterQuerySet":
        """Filter characters belonging to a specific campaign.

        Args:
            campaign: The campaign to filter by

        Returns:
            QuerySet of characters in the campaign
        """
        if campaign is None:
            raise ValueError("Campaign parameter cannot be None")
        return self.filter(campaign=campaign)

    def owned_by(self, user: Optional["AbstractUser"]) -> "CharacterQuerySet":
        """Filter characters owned by a specific user.

        Args:
            user: The user to filter by, or None for no characters

        Returns:
            QuerySet of characters owned by the user
        """
        if user is None:
            return self.none()
        return self.filter(player_owner=user)

    def with_campaign_memberships(self) -> "CharacterQuerySet":
        """Prefetch campaign memberships to optimize permission checks.

        Use this method when you need to check permissions for multiple characters
        to avoid N+1 queries.

        Returns:
            QuerySet with prefetched campaign memberships
        """
        return self.select_related("campaign", "campaign__owner").prefetch_related(
            "campaign__memberships__user"
        )

    def editable_by(
        self, user: Optional["AbstractUser"], campaign: Campaign
    ) -> "CharacterQuerySet":
        """Filter characters that can be edited by a user in a campaign.

        Args:
            user: The user to check edit permissions for
            campaign: The campaign to check within

        Returns:
            QuerySet of characters the user can edit
        """
        if user is None:
            return self.none()

        if campaign is None:
            raise ValueError("Campaign parameter cannot be None")

        # Get user's role in the campaign (this is a single query, not N+1 issue)
        user_role = campaign.get_user_role(user)

        if user_role is None:
            # Non-members cannot edit any characters
            return self.none()
        elif user_role in ["OWNER", "GM"]:
            # Campaign owners and GMs can edit all characters in their campaign
            return self.filter(campaign=campaign)
        elif user_role in ["PLAYER"]:
            # Players can only edit their own characters
            return self.filter(campaign=campaign, player_owner=user)
        else:
            # Observers and others cannot edit any characters
            return self.none()


class CharacterManager(PolymorphicManager):
    """Custom manager for Character with query methods."""

    def get_queryset(self) -> CharacterQuerySet:
        """Return the custom QuerySet for additional methods."""
        return CharacterQuerySet(self.model, using=self._db)

    def for_campaign(self, campaign: Campaign) -> CharacterQuerySet:
        """Get characters for a specific campaign.

        Args:
            campaign: The campaign to get characters for

        Returns:
            QuerySet of characters in the campaign
        """
        return self.get_queryset().for_campaign(campaign)

    def owned_by(self, user: Optional["AbstractUser"]) -> CharacterQuerySet:
        """Get characters owned by a specific user.

        Args:
            user: The user to get characters for

        Returns:
            QuerySet of characters owned by the user
        """
        return self.get_queryset().owned_by(user)

    def editable_by(
        self, user: Optional["AbstractUser"], campaign: Campaign
    ) -> CharacterQuerySet:
        """Get characters that can be edited by a user in a campaign.

        Args:
            user: The user to check edit permissions for
            campaign: The campaign to check within

        Returns:
            QuerySet of characters the user can edit
        """
        return self.get_queryset().editable_by(user, campaign)

    def with_campaign_memberships(self) -> CharacterQuerySet:
        """Get characters with prefetched campaign memberships.

        Returns:
            QuerySet with prefetched campaign memberships for optimization
        """
        return self.get_queryset().with_campaign_memberships()


class Character(PolymorphicModel):
    """Base Character model for all game systems."""

    name: models.CharField = models.CharField(
        max_length=100, help_text="Character name"
    )
    description: models.TextField = models.TextField(
        blank=True, default="", help_text="Character description and background"
    )
    campaign: models.ForeignKey = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name="characters",
        help_text="The campaign this character belongs to",
    )
    player_owner: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_characters",
        help_text="The player who owns this character",
    )
    game_system: models.CharField = models.CharField(
        max_length=100, help_text="The game system this character uses"
    )
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    updated_at: models.DateTimeField = models.DateTimeField(auto_now=True)

    objects = CharacterManager()

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the model and store original field values for change tracking."""
        super().__init__(*args, **kwargs)
        # Store original values for key fields to track changes
        self._original_campaign_id = self.campaign_id
        self._original_player_owner_id = self.player_owner_id

    class Meta:
        db_table = "characters_character"
        constraints = [
            models.UniqueConstraint(
                fields=["campaign", "name"], name="unique_character_name_per_campaign"
            ),
        ]
        indexes = [
            models.Index(
                fields=["campaign", "player_owner"],
                name="characters_character_count_idx",
            ),
        ]
        ordering = ["name"]
        verbose_name = "Character"
        verbose_name_plural = "Characters"

    def __str__(self) -> str:
        """Return the character name."""
        return self.name

    def _has_campaign_changed(self) -> bool:
        """Check if the campaign field has changed since the instance was loaded."""
        return self.campaign_id != self._original_campaign_id

    def _has_player_owner_changed(self) -> bool:
        """Check if the player_owner field has changed since the instance was loaded."""
        return self.player_owner_id != self._original_player_owner_id

    def _should_validate_membership(self) -> bool:
        """
        Determine if membership validation should be performed.

        Returns True if:
        1. This is a new character (pk is None), OR
        2. The campaign or player_owner has changed
        """
        if self.pk is None:
            # Always validate for new characters
            return True

        # For existing characters, only validate if key fields changed
        return self._has_campaign_changed() or self._has_player_owner_changed()

    def clean(self) -> None:
        """Validate the character data."""
        super().clean()

        # Validate character name is not empty/blank
        if not self.name or not self.name.strip():
            raise ValidationError("Character name cannot be empty.")

        # Validate character name length
        if len(self.name) > 100:
            raise ValidationError("Character name cannot exceed 100 characters.")

        # Validate that player is a member of the campaign
        # Check membership for new characters or when campaign/player_owner changes
        if self.campaign and self.player_owner and self._should_validate_membership():
            if not self.campaign.is_member(self.player_owner):
                raise ValidationError(
                    "Only campaign members (players, GMs, owners) can own "
                    "characters in this campaign."
                )

        # Validate max characters per player limit
        if self.campaign and self.player_owner:
            max_chars = self.campaign.max_characters_per_player
            if max_chars > 0:  # 0 means unlimited
                self._validate_character_limit(max_chars)

    @transaction.atomic
    def _validate_character_limit(self, max_chars: int) -> None:
        """
        Validate character limit with atomic protection.

        Args:
            max_chars: Maximum characters allowed per player

        Raises:
            ValidationError: If character limit would be exceeded
        """
        from campaigns.models import Campaign

        # Lock the campaign to prevent concurrent character creation
        Campaign.objects.select_for_update().get(pk=self.campaign.pk)

        # Count existing characters for this player in this campaign
        existing_count = (
            Character.objects.filter(
                campaign=self.campaign, player_owner=self.player_owner
            )
            .exclude(pk=self.pk or 0)
            .count()
        )

        if existing_count >= max_chars:
            raise ValidationError(
                f"You cannot have more than {max_chars} "
                f"character{'s' if max_chars != 1 else ''} in this campaign. "
                "Please delete an existing character before creating a new one."
            )

    def save(self, *args: Any, **kwargs: Any) -> None:
        """
        Save the character with validation.

        Only runs full_clean() for new characters (those without a pk) or when
        explicitly requested via validate=True parameter.
        """
        # Run validation for new characters or when explicitly requested
        validate = kwargs.pop("validate", self.pk is None)
        if validate:
            self.full_clean()
        super().save(*args, **kwargs)

        # Update original values after successful save to reset change tracking
        self._original_campaign_id = self.campaign_id
        self._original_player_owner_id = self.player_owner_id

    def refresh_from_db(self, using: Optional[str] = None, fields: Optional[List[str]] = None) -> None:
        """Refresh the instance from the database and reset change tracking."""
        super().refresh_from_db(using=using, fields=fields)
        # Reset change tracking after refresh
        self._original_campaign_id = self.campaign_id
        self._original_player_owner_id = self.player_owner_id

    def can_be_edited_by(
        self, user: Optional["AbstractUser"], user_role: Optional[str] = None
    ) -> bool:
        """Check if a user can edit this character.

        Args:
            user: The user to check edit permissions for
            user_role: Optional cached user role to avoid database query

        Returns:
            True if the user can edit this character, False otherwise
        """
        if user is None:
            return False

        # Character owners can always edit their characters
        if self.player_owner == user:
            return True

        # Use cached role if provided, otherwise fetch from campaign
        if user_role is None:
            user_role = self._get_cached_user_role(user)

        # Campaign owners and GMs can edit all characters in their campaign
        return user_role in ["OWNER", "GM"]

    def can_be_deleted_by(self, user: Optional["AbstractUser"]) -> bool:
        """Check if a user can delete this character.

        Args:
            user: The user to check delete permissions for

        Returns:
            True if the user can delete this character, False otherwise
        """
        if user is None:
            return False

        # Character owners can always delete their own characters
        if self.player_owner == user:
            return True

        # Get user's role in the campaign
        user_role = self._get_cached_user_role(user)

        if user_role is None:
            return False

        # Check campaign settings for GM/Owner deletion permissions
        if user_role == "OWNER":
            return getattr(self.campaign, "allow_owner_character_deletion", True)
        elif user_role == "GM":
            return getattr(self.campaign, "allow_gm_character_deletion", False)

        # Players, observers, and others cannot delete characters they don't own
        return False

    def get_permission_level(
        self, user: Optional["AbstractUser"], user_role: Optional[str] = None
    ) -> str:
        """Get the permission level a user has for this character.

        Args:
            user: The user to check permissions for
            user_role: Optional cached user role to avoid database query

        Returns:
            Permission level: 'owner', 'campaign_owner', 'gm', 'read', or 'none'
        """
        if user is None:
            return "none"

        # Character owners get highest permission
        if self.player_owner == user:
            return "owner"

        # Use cached role if provided, otherwise fetch from campaign
        if user_role is None:
            user_role = self._get_cached_user_role(user)

        if user_role is None:
            return "none"
        elif user_role == "OWNER":
            return "campaign_owner"
        elif user_role == "GM":
            return "gm"
        elif user_role in ["PLAYER", "OBSERVER"]:
            return "read"
        else:
            return "none"

    def _get_cached_user_role(self, user: "AbstractUser") -> Optional[str]:
        """Get user's role in the campaign.

        Args:
            user: The user to check role for

        Returns:
            User's role in the campaign or None if not a member
        """
        if not user or not user.is_authenticated:
            return None

        return self.campaign.get_user_role(user)
