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

    class Meta:
        model = Campaign
        fields = ["name", "description", "game_system"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Enter campaign name"}),
            "description": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Enter campaign description (optional)",
                }
            ),
            "game_system": forms.TextInput(
                attrs={"placeholder": "e.g. Mage: The Ascension"}
            ),
        }

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
        ]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Enter campaign name"}),
            "description": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Enter campaign description (optional)",
                }
            ),
            "game_system": forms.TextInput(
                attrs={"placeholder": "e.g. Mage: The Ascension"}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_public": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "allow_observer_join": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "allow_player_join": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }
        labels = {
            "is_active": "Campaign is active",
            "is_public": "Campaign is public (visible to non-members)",
            "allow_observer_join": "Anyone can join as observer",
            "allow_player_join": "Anyone can join as player",
        }
        help_texts = {
            "is_active": "Inactive campaigns are hidden from lists",
            "is_public": "Public campaigns are visible to all users",
            "allow_observer_join": "Observers can view but not participate",
            "allow_player_join": "Players can participate in scenes",
        }


class SendInvitationForm(forms.Form):
    """Form for sending campaign invitations."""

    invited_user = forms.ModelChoiceField(
        queryset=User.objects.all(),
        widget=forms.Select(attrs={"class": "form-control"}),
        label="User to invite",
    )
    role = forms.ChoiceField(
        choices=CampaignMembership.ROLE_CHOICES,
        widget=forms.Select(attrs={"class": "form-control"}),
        label="Role",
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        required=False,
        label="Optional message",
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
        widget=forms.Select(attrs={"class": "form-control"}),
        label="Member",
    )
    new_role = forms.ChoiceField(
        choices=CampaignMembership.ROLE_CHOICES,
        widget=forms.Select(attrs={"class": "form-control"}),
        label="New Role",
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
        choices=ACTION_CHOICES, widget=forms.RadioSelect, label="Action"
    )
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Select Users",
    )
    role = forms.ChoiceField(
        choices=CampaignMembership.ROLE_CHOICES,
        widget=forms.Select(attrs={"class": "form-control"}),
        required=False,
        label="Role (for add/change operations)",
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
