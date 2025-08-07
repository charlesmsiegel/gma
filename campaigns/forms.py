"""
Forms for campaign creation and management.

This module provides Django forms for creating and editing campaigns,
with proper validation and user assignment.
"""

from django import forms
from django.core.exceptions import ValidationError

from .models import Campaign


class CampaignForm(forms.ModelForm):
    """Form for creating and editing campaigns."""

    class Meta:
        model = Campaign
        fields = ["name", "description", "game_system"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter campaign name",
                    "maxlength": 200,
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter campaign description (optional)",
                    "rows": 4,
                }
            ),
            "game_system": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter game system (e.g. Mage: The Ascension)",
                    "maxlength": 100,
                }
            ),
        }
        help_texts = {
            "name": "The name of your campaign (required)",
            "description": "A brief description of your campaign (optional)",
            "game_system": "The tabletop RPG system you'll be using (optional)",
        }

    def __init__(self, *args, **kwargs):
        """Initialize the form with custom styling and validation."""
        super().__init__(*args, **kwargs)

        # Mark required fields
        self.fields["name"].required = True
        self.fields["description"].required = False
        self.fields["game_system"].required = False

        # Add Bootstrap classes and attributes
        for field_name, field in self.fields.items():
            field.widget.attrs.update(
                {"class": field.widget.attrs.get("class", "") + " form-control"}
            )
            if field.required:
                field.widget.attrs.update({"required": True, "aria-required": "true"})

    def clean_name(self):
        """Validate the campaign name."""
        name = self.cleaned_data.get("name")
        if not name or not name.strip():
            raise ValidationError("Campaign name is required.")

        # Trim whitespace
        name = name.strip()

        if len(name) > 200:
            raise ValidationError("Campaign name must not exceed 200 characters.")

        return name

    def clean_description(self):
        """Clean and validate description field."""
        description = self.cleaned_data.get("description", "")
        return description.strip() if description else ""

    def clean_game_system(self):
        """Clean and validate game system field."""
        game_system = self.cleaned_data.get("game_system", "")
        return game_system.strip() if game_system else ""

    def save(self, owner=None, commit=True):
        """Save the campaign with the specified owner."""
        campaign = super().save(commit=False)

        if owner is not None:
            campaign.owner = owner
        elif not campaign.owner_id:
            raise ValidationError("Campaign must have an owner.")

        if commit:
            campaign.save()

        return campaign
