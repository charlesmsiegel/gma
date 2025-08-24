"""
Forms for scene creation and management.

This module provides Django forms for creating and editing scenes,
with proper validation and campaign context handling.
"""

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models

from characters.models import Character

from .models import Scene

User = get_user_model()


class SceneForm(forms.ModelForm):
    """Form for creating and editing scenes."""

    class Meta:
        model = Scene
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control form-control-lg",
                    "placeholder": "Enter scene name",
                    "autocomplete": "off",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": (
                        "Describe the scene setting, atmosphere, "
                        "or initial situation..."
                    ),
                    "style": "resize: vertical;",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add required asterisk styling
        self.fields["name"].widget.attrs.update({"data-required": "true"})

    def clean_name(self):
        """Clean and validate the name field."""
        name = self.cleaned_data.get("name")
        if name:
            name = name.strip()
        return name

    def save(self, campaign=None, created_by=None, commit=True):
        """Save the scene with the specified campaign and creator."""
        scene = super().save(commit=False)
        if campaign:
            scene.campaign = campaign
        if created_by:
            scene.created_by = created_by
        if commit:
            scene.save()
        return scene


class AddParticipantForm(forms.Form):
    """Form for adding a single participant to a scene."""

    character = forms.ModelChoiceField(
        queryset=Character.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Character",
        help_text="Select a character to add to this scene",
    )

    def __init__(self, *args, **kwargs):
        self.scene = kwargs.pop("scene", None)
        super().__init__(*args, **kwargs)

        if self.scene:
            # Only show characters from campaign that aren't already participating
            self.fields["character"].queryset = Character.objects.filter(
                campaign=self.scene.campaign
            ).exclude(participated_scenes=self.scene)

    def save(self):
        """Add the selected character to the scene."""
        character = self.cleaned_data["character"]
        self.scene.participants.add(character)
        return character


class BulkAddParticipantsForm(forms.Form):
    """Form for adding multiple participants to a scene at once."""

    characters = forms.ModelMultipleChoiceField(
        queryset=Character.objects.none(),
        widget=forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
        required=True,
        label="Characters",
        help_text="Select one or more characters to add to this scene",
    )

    def __init__(self, *args, **kwargs):
        self.scene = kwargs.pop("scene", None)
        super().__init__(*args, **kwargs)

        if self.scene:
            # Only show characters from campaign that aren't already participating
            self.fields["characters"].queryset = Character.objects.filter(
                campaign=self.scene.campaign
            ).exclude(participated_scenes=self.scene)

    def save(self):
        """Add all selected characters to the scene."""
        characters = self.cleaned_data["characters"]
        added_count = 0
        for character in characters:
            self.scene.participants.add(character)
            added_count += 1
        return added_count


class SceneStatusChangeForm(forms.ModelForm):
    """Form for changing scene status with validation for proper transitions."""

    STATUS_TRANSITIONS = {
        "ACTIVE": ["CLOSED"],
        "CLOSED": ["ARCHIVED"],
        "ARCHIVED": [],  # Archived scenes cannot change status
    }

    class Meta:
        model = Scene
        fields = ["status"]
        widgets = {
            "status": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            current_status = self.instance.status
            # Filter choices based on valid transitions
            valid_statuses = self.STATUS_TRANSITIONS.get(current_status, [])

            # Create choices from valid transitions
            choices = [
                (status, dict(Scene.STATUS_CHOICES)[status])
                for status in valid_statuses
            ]
            self.fields["status"].choices = choices

    def clean_status(self):
        """Validate that the status transition is allowed."""
        new_status = self.cleaned_data.get("status")

        if not self.instance or not self.instance.pk:
            return new_status

        current_status = self.instance.status
        valid_transitions = self.STATUS_TRANSITIONS.get(current_status, [])

        if new_status not in valid_transitions:
            status_names = dict(Scene.STATUS_CHOICES)
            current_name = status_names.get(current_status, current_status)
            new_name = status_names.get(new_status, new_status)

            if current_status == "ACTIVE" and new_status == "ARCHIVED":
                raise ValidationError(
                    f"Cannot change from {current_name} to {new_name}. "
                    "Active scenes must be Closed before they can be Archived."
                )
            else:
                raise ValidationError(
                    f"Invalid status transition from {current_name} to {new_name}."
                )

        return new_status

    def save(self, commit=True):
        """Save the status change, returning True if status actually changed."""
        if not self.instance or not self.instance.pk:
            return super().save(commit=commit)

        old_status = self.instance.status
        new_status = self.cleaned_data.get("status")

        # If no change, return False
        if old_status == new_status:
            return False

        # Save the change
        if commit:
            super().save(commit=True)
            return True
        else:
            return super().save(commit=False)


class SceneSearchForm(forms.Form):
    """Form for searching and filtering scenes."""

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Search scene names and descriptions...",
            }
        ),
        label="Search",
        help_text="Search in scene names and descriptions",
    )

    status = forms.ChoiceField(
        required=False,
        choices=[("", "All Statuses")] + Scene.STATUS_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Status",
        help_text="Filter by scene status",
    )

    participant = forms.ModelChoiceField(
        queryset=Character.objects.none(),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Participant",
        help_text="Filter by character participation",
    )

    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        label="From Date",
        help_text="Show scenes created on or after this date",
    )

    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        label="To Date",
        help_text="Show scenes created on or before this date",
    )

    def __init__(self, *args, **kwargs):
        self.campaign = kwargs.pop("campaign", None)
        super().__init__(*args, **kwargs)

        if self.campaign:
            # Only show characters from this campaign
            self.fields["participant"].queryset = Character.objects.filter(
                campaign=self.campaign
            ).order_by("name")

            # Add empty choice for participant
            self.fields["participant"].empty_label = "All Characters"

    def clean(self):
        """Validate that date range is logical."""
        cleaned_data = super().clean()
        date_from = cleaned_data.get("date_from")
        date_to = cleaned_data.get("date_to")

        if date_from and date_to and date_from > date_to:
            raise ValidationError({"date_to": "End date must be after start date."})

        return cleaned_data

    def apply_filters(self, queryset):
        """Apply search filters to the given queryset."""
        if not self.is_valid():
            return queryset

        # Text search
        search_text = self.cleaned_data.get("search")
        if search_text:
            queryset = queryset.filter(
                models.Q(name__icontains=search_text)
                | models.Q(description__icontains=search_text)
            )

        # Status filter
        status = self.cleaned_data.get("status")
        if status:
            queryset = queryset.filter(status=status)

        # Participant filter
        participant = self.cleaned_data.get("participant")
        if participant:
            queryset = queryset.filter(participants=participant)

        # Date range filters
        date_from = self.cleaned_data.get("date_from")
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)

        date_to = self.cleaned_data.get("date_to")
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        return queryset
