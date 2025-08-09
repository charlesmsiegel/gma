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

        # Validate that player is a member of the campaign
        if self.campaign and self.player_owner:
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
                        f"Player cannot have more than {max_chars} "
                        "characters in this campaign."
                    )
