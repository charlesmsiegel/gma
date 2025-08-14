"""
Forms for character management.

Provides forms for creating and editing characters with proper validation
and permission checking.
"""

from django import forms
from django.core.exceptions import ValidationError
from django.db import models

from campaigns.models import Campaign
from characters.models import Character


class CharacterCreateForm(forms.ModelForm):
    """Form for creating new characters with campaign-specific validation."""

    class Meta:
        model = Character
        fields = ["name", "description", "campaign"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter character name",
                    "maxlength": 100,
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Describe your character's background",
                    "rows": 4,
                }
            ),
            "campaign": forms.Select(attrs={"class": "form-control"}),
        }
        help_texts = {
            "name": "Character name (required, max 100 characters)",
            "description": "Optional character description and background",
            "campaign": "Select a campaign where you have at least PLAYER role",
        }

    def __init__(self, *args, user=None, **kwargs):
        """Initialize form with user-specific campaign filtering."""
        if user is None:
            raise TypeError("CharacterCreateForm requires 'user' parameter")

        self.user = user
        super().__init__(*args, **kwargs)

        # Filter campaigns to only show those where user has PLAYER+ role
        # This includes campaigns they own and campaigns where they're a member
        user_campaigns = (
            Campaign.objects.filter(
                models.Q(owner=user)  # Campaigns they own
                | models.Q(memberships__user=user),  # Campaigns they're a member of
                is_active=True,  # Only active campaigns
            )
            .distinct()
            .order_by("name")
        )

        self.fields["campaign"].queryset = user_campaigns

        # If no campaigns available, show helpful message
        if not user_campaigns.exists():
            self.fields["campaign"].empty_label = (
                "No campaigns available - you must be a member of a campaign "
                "to create characters"
            )
        else:
            self.fields["campaign"].empty_label = "Select a campaign"

    def clean_name(self):
        """Validate character name field."""
        name = self.cleaned_data.get("name")

        if not name:
            raise ValidationError("Character name is required.")

        # Strip whitespace and check if empty
        name = name.strip()
        if not name:
            raise ValidationError("Character name cannot be empty or only whitespace.")

        if len(name) > 100:
            raise ValidationError("Character name cannot exceed 100 characters.")

        return name

    def clean_campaign(self):
        """Validate campaign selection and user permissions."""
        campaign = self.cleaned_data.get("campaign")

        if not campaign:
            raise ValidationError("Campaign selection is required.")

        # Check if user has permission to create characters in this campaign
        # This includes: OWNER (campaign owner), GM, PLAYER, and OBSERVER roles
        user_role = campaign.get_user_role(self.user)
        if user_role is None:
            raise ValidationError(
                "You must be a member of the selected campaign to create characters."
            )

        # Check character limit for this user in this campaign
        if campaign.max_characters_per_player > 0:  # 0 means unlimited
            existing_count = Character.objects.filter(
                campaign=campaign, player_owner=self.user
            ).count()

            if existing_count >= campaign.max_characters_per_player:
                max_chars = campaign.max_characters_per_player
                raise ValidationError(
                    f"You cannot have more than {max_chars} "
                    f"character{'s' if max_chars != 1 else ''} in this campaign. "
                    "Please delete an existing character before creating a new one."
                )

        return campaign

    def clean(self):
        """Perform cross-field validation."""
        cleaned_data = super().clean()
        name = cleaned_data.get("name")
        campaign = cleaned_data.get("campaign")

        if name and campaign:
            # Check for unique character name per campaign
            existing_character = Character.all_objects.filter(
                campaign=campaign, name=name
            ).first()

            if existing_character:
                self.add_error(
                    "name",
                    f"A character named '{name}' already exists in this "
                    "campaign. Character names must be unique within "
                    "each campaign.",
                )

        return cleaned_data

    def _post_clean(self):
        """Set cleaned data on instance but skip model validation until save()."""
        # Copy cleaned form data to the instance without running model validation
        exclude = self._get_validation_exclusions()
        for f in self.instance._meta.fields:
            if f.name in self.cleaned_data and f.name not in exclude:
                setattr(self.instance, f.name, self.cleaned_data[f.name])

        # Don't call super()._post_clean() which would call instance.full_clean()
        # We'll validate in save() after setting player_owner and game_system

    def save(self, commit=True):
        """Save the character with automatic field assignment."""
        character = super().save(commit=False)

        # Automatically assign player_owner to current user
        character.player_owner = self.user

        # Automatically assign game_system from campaign
        campaign = self.cleaned_data.get("campaign")
        if campaign:
            character.campaign = campaign
            character.game_system = campaign.game_system

        if commit:
            # Use validate=True to ensure full validation is run during save
            character.save(validate=True)

        return character


class CharacterEditForm(forms.ModelForm):
    """Form for editing existing characters with permission validation."""

    class Meta:
        model = Character
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter character name",
                    "maxlength": 100,
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Describe your character's background",
                    "rows": 4,
                }
            ),
        }
        help_texts = {
            "name": "Character name (required, max 100 characters)",
            "description": "Character description and background",
        }

    def __init__(self, *args, user=None, character=None, **kwargs):
        """Initialize form with user and character for permission checking."""
        if user is None:
            raise TypeError("CharacterEditForm requires 'user' parameter")

        # Support both character= and instance= patterns
        if character is None:
            character = kwargs.get("instance")
        if character is None:
            raise TypeError(
                "CharacterEditForm requires 'character' parameter or instance"
            )

        self.user = user
        self.character = character

        # Store original values for change tracking
        self._original_values = {}
        if character:
            for field_name in self._meta.fields:
                self._original_values[field_name] = getattr(character, field_name, None)

        # Check permissions
        if not character.can_be_edited_by(user):
            raise PermissionError(f"You don't have permission to edit {character.name}")

        super().__init__(*args, **kwargs)

    def clean_name(self):
        """Validate character name field."""
        name = self.cleaned_data.get("name")

        if not name:
            raise ValidationError("Character name is required.")

        # Strip whitespace and check if empty
        name = name.strip()
        if not name:
            raise ValidationError("Character name cannot be empty or only whitespace.")

        if len(name) > 100:
            raise ValidationError("Character name cannot exceed 100 characters.")

        return name

    def clean(self):
        """Perform cross-field validation."""
        cleaned_data = super().clean()
        name = cleaned_data.get("name")

        if name and self.character:
            # Check for unique character name per campaign (excluding current character)
            existing_character = (
                Character.all_objects.filter(
                    campaign=self.character.campaign, name=name
                )
                .exclude(pk=self.character.pk)
                .first()
            )

            if existing_character:
                self.add_error(
                    "name",
                    f"A character named '{name}' already exists in this "
                    "campaign. Character names must be unique within "
                    "each campaign.",
                )

        return cleaned_data

    def save(self, commit=True):
        """Save the character with audit trail."""
        character = super().save(commit=False)

        if commit:
            # Save with audit user for audit trail
            character.save(audit_user=self.user)

        return character

    def get_changed_fields(self):
        """Get list of fields that changed for audit tracking."""
        if not hasattr(self, "changed_data"):
            return []
        return self.changed_data

    def get_field_changes(self):
        """Get detailed field changes for audit tracking.

        Returns:
            dict: Dictionary with field names as keys, each containing
                'old' and 'new' values
        """
        changes = {}
        if hasattr(self, "changed_data"):
            for field_name in self.changed_data:
                if (
                    field_name in self._original_values
                    and field_name in self.cleaned_data
                ):
                    changes[field_name] = {
                        "old": self._original_values[field_name],
                        "new": self.cleaned_data[field_name],
                    }
        return changes


class CharacterDeleteForm(forms.Form):
    """Form for deleting characters with confirmation."""

    confirmation_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Type the character name to confirm deletion",
            }
        ),
        help_text="Type the character name exactly to confirm deletion",
    )

    def __init__(self, *args, character=None, user=None, **kwargs):
        """Initialize form with character and user for validation."""
        # Support both character= and instance= patterns
        if character is None:
            character = kwargs.pop("instance", None)
        if character is None:
            raise TypeError(
                "CharacterDeleteForm requires 'character' parameter or instance"
            )
        if user is None:
            raise TypeError("CharacterDeleteForm requires 'user' parameter")

        self.character = character
        self.user = user

        # Check permissions before allowing form creation
        if not character.can_be_deleted_by(user):
            raise PermissionError(
                f"You don't have permission to delete {character.name}"
            )

        super().__init__(*args, **kwargs)

        # Update help text to include character name
        self.fields["confirmation_name"].help_text = (
            f"Type the character name exactly to confirm deletion: {character.name}"
        )

    @property
    def character_name(self):
        """Get the character's name for template display."""
        return self.character.name

    @property
    def character_campaign(self):
        """Get the character's campaign name for template display."""
        return self.character.campaign.name

    def clean_confirmation_name(self):
        """Validate that the confirmation matches the character name exactly."""
        confirmation = self.cleaned_data.get("confirmation_name")

        if not confirmation:
            raise ValidationError(
                "You must type the character name to confirm deletion."
            )

        # Case-sensitive comparison as required
        if confirmation != self.character.name:
            raise ValidationError(
                f"You must type '{self.character.name}' - must match the "
                f"character name exactly."
            )

        return confirmation

    def delete(self):
        """Execute soft delete on the character.

        Returns:
            bool: True if deletion was successful

        Raises:
            PermissionError: If user doesn't have permission
                (already checked in __init__)
        """
        self.character.soft_delete(self.user)
        return True

    def delete_character(self, hard_delete=False):
        """Delete the character (soft delete by default, hard delete for admins).

        Args:
            hard_delete: Whether to permanently delete (admin only)

        Returns:
            The character that was deleted

        Raises:
            PermissionError: If user doesn't have permission
        """
        if hard_delete:
            self.character.hard_delete(self.user)
        else:
            self.character.soft_delete(self.user)

        return self.character
