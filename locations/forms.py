"""
Forms for Location model with hierarchy support.

Forms handle:
- Location creation and editing with hierarchy validation
- Campaign-based filtering of parent options
- Permission-based field restrictions
- Bulk operation forms for efficient management
"""

from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q

from campaigns.models import Campaign
from locations.models import Location


class LocationForm(forms.ModelForm):
    """Base form for Location creation and editing with hierarchy support."""

    class Meta:
        model = Location
        fields = ["name", "description", "campaign", "parent"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "campaign": forms.Select(attrs={"class": "form-control"}),
            "parent": forms.Select(attrs={"class": "form-control"}),
        }
        help_texts = {
            "name": "Enter a unique name for this location within the campaign.",
            "description": "Optional description of the location.",
            "campaign": "Select the campaign this location belongs to.",
            "parent": "Select a parent location to create a hierarchy (optional).",
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        if self.user:
            # Filter campaigns to only those the user can access
            self.fields["campaign"].queryset = Campaign.objects.filter(
                Q(owner=self.user) | Q(memberships__user=self.user)
            ).distinct()

        # Configure parent field
        self.fields["parent"].empty_label = "No parent (root level)"
        self.fields["parent"].required = False

        # Filter parent options based on campaign selection
        campaign_id = None

        # Try to get campaign from various sources
        if self.instance and self.instance.pk and self.instance.campaign_id:
            campaign_id = self.instance.campaign_id
        elif "initial" in kwargs and "campaign" in kwargs["initial"]:
            campaign_id = kwargs["initial"]["campaign"]
            if hasattr(campaign_id, "pk"):  # If it's a Campaign object
                campaign_id = campaign_id.pk
        elif "data" in kwargs and kwargs["data"] and "campaign" in kwargs["data"]:
            # Try to get from form data
            try:
                campaign_id = int(kwargs["data"]["campaign"])
            except (ValueError, TypeError):
                pass

        if campaign_id:
            queryset = Location.objects.filter(campaign_id=campaign_id).order_by("name")
            if self.instance and self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            self.fields["parent"].queryset = queryset
        else:
            self.fields["parent"].queryset = Location.objects.none()

    def clean_parent(self):
        """Validate parent selection to prevent circular references and enforce depth limits."""
        parent = self.cleaned_data.get("parent")

        if not parent:
            return parent

        # Check for circular reference
        if self.instance and self.instance.pk:
            if parent.pk == self.instance.pk:
                raise ValidationError("A location cannot be its own parent.")

            # Check if parent is a descendant of this location
            if parent.is_descendant_of(self.instance):
                raise ValidationError(
                    "Cannot create a circular reference in the hierarchy."
                )

        # Check maximum depth
        if parent.get_depth() >= 9:  # Max depth of 10 levels (0-9)
            raise ValidationError(
                "Cannot create location: maximum depth of 10 levels would be exceeded."
            )

        return parent

    def clean(self):
        """Additional form-level validation."""
        cleaned_data = super().clean()
        campaign = cleaned_data.get("campaign")
        parent = cleaned_data.get("parent")

        # Ensure parent belongs to the same campaign
        if parent and campaign and parent.campaign != campaign:
            raise ValidationError(
                {"parent": "Parent location must belong to the same campaign."}
            )

        return cleaned_data


class LocationCreateForm(LocationForm):
    """Form for creating new locations."""

    def __init__(self, *args, campaign=None, **kwargs):
        # Set initial data for campaign if provided
        if campaign:
            initial = kwargs.get("initial", {})
            initial["campaign"] = campaign
            kwargs["initial"] = initial

        super().__init__(*args, **kwargs)

        if campaign:
            self.fields["parent"].queryset = Location.objects.filter(campaign=campaign)

    def save(self, commit=True):
        """Save the location with the current user as creator."""
        location = super().save(commit=False)

        if self.user:
            location.created_by = self.user

        if commit:
            location.save()

        return location


class LocationEditForm(LocationForm):
    """Form for editing existing locations."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Campaign should not be changeable in edit mode
        if "campaign" in self.fields:
            self.fields["campaign"].disabled = True
            self.fields["campaign"].help_text = (
                "Campaign cannot be changed after creation."
            )


class BulkLocationMoveForm(forms.Form):
    """Form for moving multiple locations to a new parent."""

    new_parent = forms.ModelChoiceField(
        queryset=Location.objects.none(),
        required=False,
        empty_label="Move to root level (no parent)",
        widget=forms.Select(attrs={"class": "form-control"}),
        help_text="Select the new parent for the selected locations.",
    )

    locations = forms.ModelMultipleChoiceField(
        queryset=Location.objects.none(),
        widget=forms.MultipleHiddenInput(),
    )

    def __init__(self, *args, user=None, campaign=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.campaign = campaign

        if campaign:
            # Filter locations to this campaign only
            self.fields["locations"].queryset = Location.objects.filter(
                campaign=campaign
            )
            self.fields["new_parent"].queryset = Location.objects.filter(
                campaign=campaign
            )

    def clean(self):
        """Validate bulk move operation."""
        cleaned_data = super().clean()
        new_parent = cleaned_data.get("new_parent")
        locations = cleaned_data.get("locations", [])

        if not locations:
            raise ValidationError("No locations selected for move operation.")

        # Check permissions - user must be able to edit all selected locations
        if self.user:
            for location in locations:
                if not location.can_edit(self.user):
                    raise ValidationError(
                        f"You don't have permission to move location: {location.name}"
                    )

        # Prevent circular references
        if new_parent and new_parent in locations:
            raise ValidationError(
                {"locations": "Cannot move a location to be a child of itself."}
            )

        # Check that moving to new parent won't create circular references
        if new_parent:
            for location in locations:
                if new_parent.is_descendant_of(location):
                    raise ValidationError(
                        {
                            "new_parent": f"Cannot move to {new_parent.name} as it would create a circular reference."
                        }
                    )

        return cleaned_data

    def save(self):
        """Execute the bulk move operation."""
        new_parent = self.cleaned_data["new_parent"]
        locations = self.cleaned_data["locations"]

        moved_count = 0
        for location in locations:
            location.parent = new_parent
            location.save()
            moved_count += 1

        return moved_count
