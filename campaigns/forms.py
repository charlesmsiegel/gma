"""
Forms for campaign creation and management.

This module provides Django forms for creating and editing campaigns,
with proper validation and user assignment. Business logic is handled
by service layer classes.
"""

from django import forms
from django.contrib.auth import get_user_model

from .models import Campaign, CampaignMembership
from .services import MembershipService

User = get_user_model()


class CampaignForm(forms.ModelForm):
    """Form for creating and editing campaigns."""

    # Popular RPG systems for autocomplete
    GAME_SYSTEMS = [
        "Mage: The Ascension",
        "Vampire: The Masquerade",
        "Werewolf: The Apocalypse",
        "Changeling: The Dreaming",
        "Wraith: The Oblivion",
        "Hunter: The Reckoning",
        "Dungeons & Dragons 5th Edition",
        "Pathfinder 2e",
        "Call of Cthulhu",
        "Shadowrun",
        "Cyberpunk RED",
        "GURPS",
        "Savage Worlds",
        "Fate Core",
        "World of Darkness",
        "Chronicles of Darkness",
        "Star Wars RPG",
        "Warhammer 40,000 RPG",
        "The Witcher RPG",
        "Alien RPG",
        "Blades in the Dark",
        "Powered by the Apocalypse",
        "Custom/Homebrew System",
    ]

    class Meta:
        model = Campaign
        fields = ["name", "description", "game_system"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control form-control-lg",
                    "placeholder": "Enter your campaign name",
                    "autocomplete": "off",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Describe your campaign setting, themes, or story hooks...",  # noqa: E501
                    "style": "resize: vertical;",
                }
            ),
            "game_system": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Start typing to see suggestions...",
                    "list": "game-systems-list",
                    "autocomplete": "off",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add required asterisk styling
        self.fields["name"].widget.attrs.update({"data-required": "true"})

    def save(self, owner=None, commit=True):
        """Save the campaign with the specified owner."""
        campaign = super().save(commit=False)
        if owner:
            campaign.owner = owner
        if commit:
            campaign.save()
        return campaign


class CampaignSettingsForm(forms.ModelForm):
    """Form for editing campaign settings."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make sure game system field has same autocomplete as create form
        self.fields["game_system"].widget.attrs.update(
            {"list": "game-systems-list", "autocomplete": "off"}
        )

    class Meta:
        model = Campaign
        fields = [
            "name",
            "description",
            "game_system",
            "is_active",
            "is_public",
            "allow_observer_join",
            "allow_player_join",
            "max_characters_per_player",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter campaign name",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Enter campaign description (optional)",
                    "style": "resize: vertical;",
                }
            ),
            "game_system": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Start typing to see suggestions...",
                    "list": "game-systems-list",
                    "autocomplete": "off",
                }
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_public": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "allow_observer_join": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "allow_player_join": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "max_characters_per_player": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "max": "10",
                    "placeholder": "0 = unlimited",
                }
            ),
        }
        labels = {
            "is_active": "Campaign is active",
            "is_public": "Campaign is public (visible to non-members)",
            "allow_observer_join": "Anyone can join as observer",
            "allow_player_join": "Anyone can join as player",
            "max_characters_per_player": "Maximum characters per player",
        }
        help_texts = {
            "is_active": "Inactive campaigns are hidden from lists",
            "is_public": "Public campaigns are visible to all users",
            "allow_observer_join": "Observers can view but not participate",
            "allow_player_join": "Players can participate in scenes",
            "max_characters_per_player": (
                "Maximum number of characters each PLAYER can have (0 = unlimited). "
                "OWNER and GM roles are exempt from this limit."
            ),
        }


class SendInvitationForm(forms.Form):
    """Form for sending campaign invitations."""

    invited_user = forms.ModelChoiceField(
        queryset=User.objects.all(),
        widget=forms.Select(attrs={"class": "form-select"}),
        label="User to invite",
        help_text="Select a user to invite to this campaign",
    )
    role = forms.ChoiceField(
        choices=CampaignMembership.ROLE_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Role",
        help_text="Choose what role the user will have in the campaign",
    )
    message = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "class": "form-control",
                "placeholder": "Add a personal message to your invitation (optional)",
                "style": "resize: vertical;",
            }
        ),
        required=False,
        label="Optional message",
        help_text="Personalize your invitation with a custom message",
    )

    def __init__(self, *args, **kwargs):
        self.campaign = kwargs.pop("campaign", None)
        super().__init__(*args, **kwargs)

        if self.campaign:
            # Use service to get available users
            membership_service = MembershipService(self.campaign)
            self.fields["invited_user"].queryset = (
                membership_service.get_available_users_for_invitation()
            )


class ChangeMemberRoleForm(forms.Form):
    """Form for changing member roles."""

    member = forms.ModelChoiceField(
        queryset=CampaignMembership.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Member",
        help_text="Select the member whose role you want to change",
    )
    new_role = forms.ChoiceField(
        choices=CampaignMembership.ROLE_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="New Role",
        help_text="Choose the new role for this member",
    )

    def __init__(self, *args, **kwargs):
        self.campaign = kwargs.pop("campaign", None)
        super().__init__(*args, **kwargs)

        if self.campaign:
            # Use service to get campaign members
            membership_service = MembershipService(self.campaign)
            self.fields["member"].queryset = membership_service.get_campaign_members()


class BulkMemberManagementForm(forms.Form):
    """Form for bulk member operations."""

    ACTION_CHOICES = [
        ("add", "Add Members"),
        ("remove", "Remove Members"),
        ("change_role", "Change Roles"),
    ]

    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
        label="Action",
        help_text="Choose what operation to perform on the selected users",
    )
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
        required=False,
        label="Select Users",
        help_text="Choose which users to apply the action to",
    )
    role = forms.ChoiceField(
        choices=CampaignMembership.ROLE_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
        required=False,
        label="Role (for add/change operations)",
        help_text="Select the role for add or change operations",
    )

    def __init__(self, *args, **kwargs):
        self.campaign = kwargs.pop("campaign", None)
        super().__init__(*args, **kwargs)

        if self.campaign:
            # Exclude campaign owner from bulk operations
            self.fields["users"].queryset = User.objects.exclude(
                id=self.campaign.owner.id
            )

    def clean(self):
        """Validate form data."""
        cleaned_data = super().clean()
        action = cleaned_data.get("action")
        role = cleaned_data.get("role")
        users = cleaned_data.get("users")

        # Validate that role is provided for add/change operations
        if action in ["add", "change_role"] and not role:
            raise forms.ValidationError(f"Role is required for {action} operations.")

        # Validate that users are selected
        if not users:
            raise forms.ValidationError("Please select at least one user.")

        return cleaned_data
