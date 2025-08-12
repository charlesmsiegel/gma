from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
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
            raise AttributeError("'NoneType' object has no attribute 'id'")
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
            raise AttributeError("'NoneType' object has no attribute 'get_user_role'")

        # Get user's role in the campaign
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

    def clean(self) -> None:
        """Validate the character data."""
        super().clean()

        # Validate character name is not empty/blank
        if not self.name or not self.name.strip():
            raise ValidationError("Character name cannot be empty.")

        # Validate character name length
        if len(self.name) > 100:
            raise ValidationError("Character name cannot exceed 100 characters.")

        # Validate that player is a member of the campaign (only for new characters)
        if self.campaign and self.player_owner and self.pk is None:
            if not self.campaign.is_member(self.player_owner):
                raise ValidationError(
                    "Only campaign members (players, GMs, owners) can own "
                    "characters in this campaign."
                )

        # Validate max characters per player limit
        if self.campaign and self.player_owner:
            max_chars = self.campaign.max_characters_per_player
            if max_chars > 0:  # 0 means unlimited
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

    def can_be_edited_by(self, user: Optional["AbstractUser"]) -> bool:
        """Check if a user can edit this character.

        Args:
            user: The user to check edit permissions for

        Returns:
            True if the user can edit this character, False otherwise
        """
        if user is None:
            return False

        # Character owners can always edit their characters
        if self.player_owner == user:
            return True

        # Get user's role in the campaign
        user_role = self.campaign.get_user_role(user)

        # Campaign owners and GMs can edit all characters in their campaign
        return user_role in ["OWNER", "GM"]

    def can_be_deleted_by(self, user: Optional["AbstractUser"]) -> bool:
        """Check if a user can delete this character.

        Args:
            user: The user to check delete permissions for

        Returns:
            True if the user can delete this character, False otherwise
        """
        # Same logic as edit permissions for now
        return self.can_be_edited_by(user)

    def get_permission_level(self, user: Optional["AbstractUser"]) -> str:
        """Get the permission level a user has for this character.

        Args:
            user: The user to check permissions for

        Returns:
            Permission level: 'owner', 'campaign_owner', 'gm', 'read', or 'none'
        """
        if user is None:
            return "none"

        # Character owners get highest permission
        if self.player_owner == user:
            return "owner"

        # Get user's role in the campaign
        user_role = self.campaign.get_user_role(user)

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
