"""
Forms for prerequisite system (Issue #190).

This module provides Django forms with visual builder widget integration
for creating and editing prerequisites.
"""

import json

from django import forms

from .models import Prerequisite
from .validators import validate_requirements
from .widgets import PrerequisiteBuilderWidget


class PrerequisiteForm(forms.ModelForm):
    """Form for creating and editing prerequisites with visual builder."""

    requirements = forms.CharField(
        widget=PrerequisiteBuilderWidget(),
        help_text="Use the visual builder to create requirement logic.",
    )

    class Meta:
        model = Prerequisite
        fields = ["description", "requirements"]

    def clean_requirements(self):
        """Validate requirements JSON structure."""
        requirements_data = self.cleaned_data["requirements"]

        if not requirements_data:
            return {}

        try:
            if isinstance(requirements_data, str):
                requirements_json = json.loads(requirements_data)
            else:
                requirements_json = requirements_data

            # Validate using our validator system
            validate_requirements(requirements_json)
            return requirements_json

        except json.JSONDecodeError:
            raise forms.ValidationError("Invalid JSON format in requirements.")
        except Exception as e:
            raise forms.ValidationError(f"Invalid requirement structure: {e}")


class AdminPrerequisiteForm(PrerequisiteForm):
    """Admin-specific form for prerequisites with enhanced validation."""

    class Meta(PrerequisiteForm.Meta):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Customize for admin interface
        self.fields["requirements"].help_text = (
            "Use the visual builder to create complex prerequisite requirements. "
            "The system supports trait checks, item possession, and logical "
            "combinations."
        )
