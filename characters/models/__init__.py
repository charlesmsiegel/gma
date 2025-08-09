from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from polymorphic.models import PolymorphicModel

from campaigns.models import Campaign


class Character(PolymorphicModel):
    """Base Character model for all game systems."""

    name = models.CharField(max_length=100, help_text="Character name")
    description = models.TextField(
        blank=True, default="", help_text="Character description and background"
    )
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name="characters",
        help_text="The campaign this character belongs to",
    )
    player_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_characters",
        help_text="The player who owns this character",
    )
    game_system = models.CharField(
        max_length=100, help_text="The game system this character uses"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "characters_character"
        constraints = [
            models.UniqueConstraint(
                fields=["campaign", "name"], name="unique_character_name_per_campaign"
            ),
        ]
        indexes = [
            # Optimized index for character count queries per player per campaign
            models.Index(
                fields=["campaign", "player_owner"],
                name="characters_character_count_idx",
            ),
            # Additional index for player character lookups
            models.Index(
                fields=["player_owner", "campaign"],
                name="characters_player_campaign_idx",
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

        # Validate that player is a member of the campaign
        if self.campaign and self.player_owner:
            if not self.campaign.is_member(self.player_owner):
                raise ValidationError(
                    "Only campaign members (players, GMs, owners) can own "
                    "characters in this campaign."
                )

        # Validate max characters per player limit
        self._validate_character_limit()

    def _validate_character_limit(self) -> None:
        """Validate character limit per player with optimized queries.

        Performance optimizations:
        1. Early exit for unlimited characters (max_chars = 0)
        2. Use exists() instead of count() for better performance
        3. Single query with limit to avoid scanning all rows
        4. Skip validation if required fields are missing
        """
        # Skip validation if required fields are missing
        if not self.campaign or not self.player_owner:
            return

        # Get the character limit (0 means unlimited)
        max_chars = self.campaign.max_characters_per_player

        # Early exit for unlimited characters
        if max_chars == 0:
            return

        # Build optimized query for character count check
        existing_characters = Character.objects.filter(
            campaign_id=self.campaign_id,  # Use _id to avoid additional query
            player_owner_id=self.player_owner_id,  # Use _id to avoid additional query
        )

        # Exclude current instance if updating
        if self.pk:
            existing_characters = existing_characters.exclude(pk=self.pk)

        # Performance optimization: Use exists() with limit instead of count()
        # This stops scanning as soon as we find enough characters
        if existing_characters[:max_chars].exists():
            # Only do a count if we need the exact number for error message
            actual_count = existing_characters.count()
            if actual_count >= max_chars:
                raise ValidationError(
                    f"Player cannot have more than {max_chars} "
                    "characters in this campaign."
                )
