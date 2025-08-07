"""
Forms for campaign creation and management.

This module provides Django forms for creating and editing campaigns,
with proper validation and user assignment.
"""

from django import forms

from .models import Campaign


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
