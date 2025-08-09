"""
Forms for campaign creation and management.

This module provides Django forms for creating and editing campaigns,
with proper validation and user assignment.
"""

from django import forms
from django.contrib.auth import get_user_model

from .models import Campaign, CampaignInvitation, CampaignMembership

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
            # Exclude users who are already members or have pending invitations
            existing_users = set([self.campaign.owner.id])
            existing_users.update(
                self.campaign.memberships.values_list("user_id", flat=True)
            )
            existing_users.update(
                CampaignInvitation.objects.filter(
                    campaign=self.campaign, status="PENDING"
                ).values_list("invited_user_id", flat=True)
            )

            self.fields["invited_user"].queryset = User.objects.exclude(
                id__in=existing_users
            )

    def save(self, invited_by, campaign):
        """Create the invitation."""
        invitation = CampaignInvitation.objects.create(
            campaign=campaign,
            invited_user=self.cleaned_data["invited_user"],
            invited_by=invited_by,
            role=self.cleaned_data["role"],
            message=self.cleaned_data.get("message", ""),
        )
        return invitation


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
            self.fields["member"].queryset = self.campaign.memberships.select_related(
                "user"
            )

    def save(self):
        """Update the member's role."""
        membership = self.cleaned_data["member"]
        membership.role = self.cleaned_data["new_role"]
        membership.save()
        return membership


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
            # Adjust user queryset based on action
            self.fields["users"].queryset = User.objects.exclude(
                id=self.campaign.owner.id
            )

    def process_bulk_operation(self):
        """Process the bulk operation."""
        action = self.cleaned_data["action"]
        users = self.cleaned_data.get("users", [])
        role = self.cleaned_data.get("role")

        results = {"added": 0, "removed": 0, "updated": 0}

        if action == "add" and role:
            for user in users:
                if not CampaignMembership.objects.filter(
                    campaign=self.campaign, user=user
                ).exists():
                    CampaignMembership.objects.create(
                        campaign=self.campaign, user=user, role=role
                    )
                    results["added"] += 1

        elif action == "remove":
            memberships = CampaignMembership.objects.filter(
                campaign=self.campaign, user__in=users
            )
            results["removed"] = memberships.count()
            memberships.delete()

        elif action == "change_role" and role:
            memberships = CampaignMembership.objects.filter(
                campaign=self.campaign, user__in=users
            )
            results["updated"] = memberships.update(role=role)

        return results


class CampaignSettingsForm(CampaignForm):
    """Form for editing campaign settings, extends basic campaign form."""

    class Meta(CampaignForm.Meta):
        model = Campaign
        fields = CampaignForm.Meta.fields + [
            "is_active",
            "is_public",
            "allow_observer_join",
            "allow_player_join",
        ]
        widgets = {
            **CampaignForm.Meta.widgets,
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
            **getattr(CampaignForm.Meta, "labels", {}),
            "is_active": "Campaign is active",
            "is_public": "Campaign is public (visible to non-members)",
            "allow_observer_join": "Anyone can join as observer",
            "allow_player_join": "Anyone can join as player",
        }
        help_texts = {
            **getattr(CampaignForm.Meta, "help_texts", {}),
            "is_active": "Inactive campaigns are hidden from lists",
            "is_public": "Public campaigns are visible to all users",
            "allow_observer_join": "Observers can view but not participate",
            "allow_player_join": "Players can participate in scenes",
        }
