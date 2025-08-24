"""
Forms for scene management.

Provides forms for scene creation, editing, and participant management.
"""

from django import forms
from django.contrib.auth import get_user_model
from django.db import models

from characters.models import Character
from scenes.models import Scene

User = get_user_model()


class SceneForm(forms.ModelForm):
    """Form for creating and editing scenes."""

    class Meta:
        model = Scene
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Enter scene name"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Enter scene description (optional)",
                }
            ),
        }

    def clean_name(self):
        """Clean and validate scene name."""
        name = self.cleaned_data.get("name")
        if name:
            return name.strip()
        return name

    def save(self, campaign=None, created_by=None, commit=True):
        """Save scene with campaign and creator."""
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
        empty_label="Select a character...",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, scene=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scene = scene
        if scene:
            # Only show characters from the same campaign who aren't
            # already participating
            self.fields["character"].queryset = Character.objects.filter(
                campaign=scene.campaign
            ).exclude(participated_scenes=scene)

    def save(self, scene=None):
        """Add the selected character to the scene."""
        scene = scene or self.scene
        if scene and self.is_valid():
            character = self.cleaned_data["character"]
            scene.participants.add(character)


class BulkAddParticipantsForm(forms.Form):
    """Form for adding multiple participants to a scene."""

    characters = forms.ModelMultipleChoiceField(
        queryset=Character.objects.none(),
        widget=forms.CheckboxSelectMultiple(),
        required=False,
    )

    def __init__(self, scene=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scene = scene
        if scene:
            # Only show characters from the same campaign who aren't
            # already participating
            self.fields["characters"].queryset = Character.objects.filter(
                campaign=scene.campaign
            ).exclude(participated_scenes=scene)

    def save(self, scene=None):
        """Add selected characters to the scene."""
        scene = scene or self.scene
        if scene and self.is_valid():
            characters = self.cleaned_data["characters"]
            scene.participants.add(*characters)
            return len(characters)
        return 0


class SceneStatusChangeForm(forms.ModelForm):
    """Form for changing scene status with transition validation."""

    class Meta:
        model = Scene
        fields = ["status"]
        widgets = {
            "status": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # Filter status choices based on current status
            current_status = self.instance.status
            if current_status == "ACTIVE":
                choices = [("ACTIVE", "Active"), ("CLOSED", "Closed")]
            elif current_status == "CLOSED":
                choices = [("CLOSED", "Closed"), ("ARCHIVED", "Archived")]
            else:  # ARCHIVED
                choices = [("ARCHIVED", "Archived")]

            self.fields["status"].choices = choices

            # Store original choices for custom validation
            self._original_status_choices = Scene.STATUS_CHOICES
            self._current_status = current_status

    def clean(self):
        """Clean form with custom error messages for invalid status choices."""
        # Check for status field errors and replace with custom message
        if "status" in self.errors:
            raw_status = self.data.get("status")
            if raw_status and hasattr(self, "_current_status"):
                if self._current_status == "ACTIVE" and raw_status == "ARCHIVED":
                    self.errors["status"].clear()
                    self.add_error(
                        "status",
                        "Cannot transition from ACTIVE directly to ARCHIVED. "
                        "Active scenes must be closed first.",
                    )

        return super().clean()

    def clean_status(self):
        """Validate status transitions."""
        new_status = self.cleaned_data.get("status")
        if self.instance and self.instance.pk:
            current_status = self.instance.status

            # Define valid transitions
            valid_transitions = {
                "ACTIVE": ["CLOSED"],
                "CLOSED": ["ARCHIVED"],
                "ARCHIVED": [],
            }

            if new_status != current_status:
                if new_status not in valid_transitions.get(current_status, []):
                    valid_next = valid_transitions.get(current_status, [])
                    if current_status == "ACTIVE" and new_status == "ARCHIVED":
                        raise forms.ValidationError(
                            "Cannot transition from ACTIVE directly to ARCHIVED. "
                            "Active scenes must be closed first."
                        )
                    else:
                        raise forms.ValidationError(
                            f"Cannot transition from {current_status} directly to "
                            f"{new_status}. Valid transitions from {current_status}: "
                            f"{', '.join(valid_next)}"
                        )

        return new_status

    def save(self, commit=True, user=None):
        """Save scene and return whether status changed."""
        if self.instance and self.instance.pk:
            old_status = Scene.objects.get(pk=self.instance.pk).status
            new_status = self.cleaned_data.get("status")

            if old_status != new_status:
                scene = super().save(commit=commit)

                # Log the status change for audit trail
                if user:
                    scene.log_status_change(
                        user=user, old_status=old_status, new_status=new_status
                    )

                return True  # Status changed
            else:
                return False  # No change needed

        return super().save(commit=commit)


class SceneSearchForm(forms.Form):
    """Form for searching and filtering scenes."""

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Search scenes...",
            }
        ),
    )

    status = forms.ChoiceField(
        choices=[("", "All Statuses")] + Scene.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    participant = forms.ModelChoiceField(
        queryset=Character.objects.none(),
        required=False,
        empty_label="All Characters",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "type": "date",
            }
        ),
    )

    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "type": "date",
            }
        ),
    )

    def __init__(self, campaign=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if campaign:
            # Only show characters from this campaign
            self.fields["participant"].queryset = Character.objects.filter(
                campaign=campaign
            )

    def clean(self):
        """Validate date range."""
        cleaned_data = super().clean()
        date_from = cleaned_data.get("date_from")
        date_to = cleaned_data.get("date_to")

        if date_from and date_to and date_from > date_to:
            self.add_error("date_to", "End date must be after start date.")

        return cleaned_data

    def apply_filters(self, queryset):
        """Apply search filters to the queryset."""
        if not self.is_valid():
            return queryset

        search = self.cleaned_data.get("search")
        status = self.cleaned_data.get("status")
        participant = self.cleaned_data.get("participant")
        date_from = self.cleaned_data.get("date_from")
        date_to = self.cleaned_data.get("date_to")

        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search)
                | models.Q(description__icontains=search)
            )

        if status:
            queryset = queryset.filter(status=status)

        if participant:
            queryset = queryset.filter(participants=participant)

        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)

        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        return queryset
