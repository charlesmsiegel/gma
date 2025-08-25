"""
Django admin interface for prerequisite management (Issue #192).

Provides comprehensive admin interface with visual builder integration,
list views, search/filter capabilities, and bulk operations.
"""

import json

from django import forms
from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.db import models
from django.shortcuts import render
from django.utils.safestring import mark_safe

from .forms import PrerequisiteRequiredForm
from .models import Prerequisite, PrerequisiteCheckResult
from .widgets import PrerequisiteBuilderWidget


class PrerequisiteAdminMixin:
    """
    Mixin for adding prerequisite functionality to Django admin.

    Provides visual builder integration, custom list display,
    search/filter capabilities, and bulk operations.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if hasattr(self.model, "requirements"):
            # Add requirements field to form if model has it
            self.formfield_overrides = getattr(self, "formfield_overrides", {})
            self.formfield_overrides.update(
                {models.JSONField: {"widget": PrerequisiteBuilderWidget}}
            )

    def get_list_display(self):
        """Add prerequisite-related columns to list display."""
        list_display = list(getattr(self, "list_display", []))

        if hasattr(self.model, "requirements"):
            # Add prerequisite columns if not already present
            if "prerequisite_summary" not in list_display:
                list_display.append("prerequisite_summary")
            if "prerequisite_count" not in list_display:
                list_display.append("prerequisite_count")

        return list_display

    def get_list_filter(self):
        """Add prerequisite-related filters."""
        list_filter = list(getattr(self, "list_filter", []))

        if hasattr(self.model, "requirements"):
            if "has_prerequisites" not in list_filter:
                list_filter.append("has_prerequisites")

        return list_filter

    def get_search_fields(self):
        """Add prerequisite content to search fields."""
        search_fields = list(getattr(self, "search_fields", []))

        if hasattr(self.model, "requirements"):
            if "requirements" not in search_fields:
                search_fields.append("requirements")

        return search_fields

    def prerequisite_summary(self, obj):
        """Display summary of prerequisites in list view."""
        if not hasattr(obj, "requirements") or not obj.requirements:
            return "No prerequisites"

        try:
            # Basic summary of requirement structure
            reqs = obj.requirements
            if isinstance(reqs, dict):
                if "any" in reqs:
                    return f"Any of {len(reqs['any'])} conditions"
                elif "all" in reqs:
                    return f"All of {len(reqs['all'])} conditions"
                elif "trait" in reqs:
                    trait = reqs["trait"]
                    return f"Trait: {trait.get('name', '?')} ≥ {trait.get('min', 0)}"
                elif "has" in reqs:
                    has = reqs["has"]
                    return f"Has: {has.get('name', '?')}"
                else:
                    return "Custom requirement"
            return "Complex requirement"
        except (TypeError, KeyError, AttributeError):
            return "Invalid prerequisite data"

    prerequisite_summary.short_description = "Prerequisites"

    def prerequisite_count(self, obj):
        """Display count of prerequisite conditions."""
        if not hasattr(obj, "requirements") or not obj.requirements:
            return 0

        try:
            reqs = obj.requirements
            if isinstance(reqs, dict):
                if "any" in reqs and isinstance(reqs["any"], list):
                    return len(reqs["any"])
                elif "all" in reqs and isinstance(reqs["all"], list):
                    return len(reqs["all"])
                elif any(key in reqs for key in ["trait", "has", "count_tag"]):
                    return 1
            return 0
        except (TypeError, KeyError, AttributeError):
            return 0

    prerequisite_count.short_description = "# Conditions"

    def has_prerequisites(self, obj):
        """Boolean indicator for filtering."""
        return bool(hasattr(obj, "requirements") and obj.requirements)

    has_prerequisites.boolean = True
    has_prerequisites.short_description = "Has Prerequisites"

    def get_actions(self, request):
        """Add prerequisite-related bulk actions."""
        actions = super().get_actions(request)

        if hasattr(self.model, "requirements"):
            actions["update_prerequisites"] = (
                self.update_prerequisites_action,
                "update_prerequisites",
                "Update prerequisites for selected items",
            )
            actions["clear_prerequisites"] = (
                self.clear_prerequisites_action,
                "clear_prerequisites",
                "Clear prerequisites for selected items",
            )
            actions["copy_prerequisites"] = (
                self.copy_prerequisites_action,
                "copy_prerequisites",
                "Copy prerequisites to selected items",
            )

        return actions

    def update_prerequisites_action(self, request, queryset):
        """Bulk action to update prerequisites."""
        if request.method == "POST" and "apply" in request.POST:
            # Get new requirements from form
            form = PrerequisiteRequiredForm(request.POST)
            if form.is_valid():
                requirements = form.cleaned_data["requirements"]
                count = queryset.update(requirements=requirements)
                self.message_user(request, f"Updated prerequisites for {count} items.")
                return None

        # Show form for entering new prerequisites
        form = PrerequisiteRequiredForm()
        context = {
            "title": "Update Prerequisites",
            "objects": queryset,
            "form": form,
            "action": "update_prerequisites",
        }
        return render(request, "admin/prerequisites_bulk_action.html", context)

    def clear_prerequisites_action(self, request, queryset):
        """Bulk action to clear prerequisites."""
        count = queryset.update(requirements=None)
        self.message_user(request, f"Cleared prerequisites for {count} items.")

    def copy_prerequisites_action(self, request, queryset):
        """Bulk action to copy prerequisites from one item to others."""
        if request.method == "POST" and "apply" in request.POST:
            source_id = request.POST.get("source_id")
            if source_id:
                try:
                    source_obj = self.model.objects.get(id=source_id)
                    if hasattr(source_obj, "requirements"):
                        count = queryset.exclude(id=source_id).update(
                            requirements=source_obj.requirements
                        )
                        self.message_user(
                            request, f"Copied prerequisites to {count} items."
                        )
                        return None
                except self.model.DoesNotExist:
                    self.message_user(request, "Source item not found.", level="ERROR")

        # Show form for selecting source item
        context = {
            "title": "Copy Prerequisites",
            "objects": queryset,
            "source_choices": [
                (obj.id, f"{obj} - {self.prerequisite_summary(obj)}")
                for obj in queryset
                if hasattr(obj, "requirements") and obj.requirements
            ],
            "action": "copy_prerequisites",
        }
        return render(request, "admin/prerequisites_copy_action.html", context)


class PrerequisiteCheckResultAdmin(ModelAdmin):
    """Admin interface for PrerequisiteCheckResult model."""

    list_display = [
        "content_object_display",
        "character_name",
        "result",
        "checked_at",
        "requirements_summary",
    ]

    list_filter = [
        "result",
        "checked_at",
        "content_type",
    ]

    search_fields = [
        "character__name",
        "requirements",
        "failure_reasons",
    ]

    readonly_fields = [
        "content_type",
        "object_id",
        "character",
        "requirements",
        "result",
        "failure_reasons",
        "checked_at",
    ]

    def content_object_display(self, obj):
        """Display the object being checked."""
        if obj.content_object:
            return str(obj.content_object)
        return f"{obj.content_type} #{obj.object_id}"

    content_object_display.short_description = "Object"

    def character_name(self, obj):
        """Display character name."""
        return obj.character.name if obj.character else "N/A"

    character_name.short_description = "Character"

    def requirements_summary(self, obj):
        """Display summary of requirements that were checked."""
        if not obj.requirements:
            return "No requirements"

        try:
            reqs = obj.requirements
            if isinstance(reqs, dict):
                if "any" in reqs:
                    return f"Any of {len(reqs['any'])} conditions"
                elif "all" in reqs:
                    return f"All of {len(reqs['all'])} conditions"
                elif "trait" in reqs:
                    trait = reqs["trait"]
                    return f"Trait: {trait.get('name', '?')} ≥ {trait.get('min', 0)}"
                else:
                    return "Custom requirement"
            return "Complex requirement"
        except (TypeError, KeyError):
            return "Invalid data"

    requirements_summary.short_description = "Requirements"

    def has_add_permission(self, request):
        """Don't allow manual creation - these are created automatically."""
        return False

    def has_change_permission(self, request, obj=None):
        """Don't allow editing - these are read-only records."""
        return False


class PrerequisiteAdminForm(forms.ModelForm):
    """Custom form for Prerequisite admin with visual builder widget."""

    class Meta:
        model = Prerequisite
        fields = "__all__"
        widgets = {
            "requirements": PrerequisiteBuilderWidget(),
        }
        help_texts = {
            "requirements": (
                "Use the visual builder to create complex prerequisite requirements."
            ),
        }

    def clean_requirements(self):
        """Ensure empty requirements return empty dict."""
        requirements_data = self.cleaned_data.get("requirements")

        if not requirements_data:
            return {}

        # If it's already a dict, return it
        if isinstance(requirements_data, dict):
            return requirements_data

        # If it's a string, try to parse it
        try:
            if isinstance(requirements_data, str):
                requirements_data = requirements_data.strip()
                if not requirements_data:
                    return {}
                return json.loads(requirements_data)
            return requirements_data
        except json.JSONDecodeError:
            raise forms.ValidationError("Invalid JSON format in requirements.")


class PrerequisiteAdmin(ModelAdmin):
    """Admin interface for Prerequisite model."""

    form = PrerequisiteAdminForm

    list_display = [
        "description_short",
        "attached_object_display",
        "requirements_summary",
        "created_at",
    ]

    list_filter = [
        "content_type",
        "created_at",
    ]

    search_fields = [
        "description",
        "requirements",
    ]

    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        (None, {"fields": ("description", "requirements")}),
        (
            "Attachment",
            {
                "fields": ("content_type", "object_id"),
                "description": (
                    "Optionally attach this prerequisite to a specific object"
                ),
            },
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def description_short(self, obj):
        """Display shortened description."""
        if len(obj.description) > 50:
            return f"{obj.description[:50]}..."
        return obj.description

    description_short.short_description = "Description"

    def attached_object_display(self, obj):
        """Display the attached object if any."""
        if obj.content_object:
            return str(obj.content_object)
        return mark_safe("<em>Not attached</em>")

    attached_object_display.short_description = "Attached To"

    def requirements_summary(self, obj):
        """Display summary of requirements."""
        if not obj.requirements:
            return mark_safe("<em>No requirements</em>")

        try:
            reqs = obj.requirements
            if isinstance(reqs, dict):
                if "any" in reqs:
                    return f"Any of {len(reqs['any'])} conditions"
                elif "all" in reqs:
                    return f"All of {len(reqs['all'])} conditions"
                elif "trait" in reqs:
                    trait = reqs["trait"]
                    return f"Trait: {trait.get('name', '?')} ≥ {trait.get('min', 0)}"
                elif "has" in reqs:
                    has = reqs["has"]
                    return f"Has: {has.get('name', '?')}"
                else:
                    return "Custom requirement"
            return "Complex requirement"
        except (TypeError, KeyError, AttributeError):
            return mark_safe("<em>Invalid data</em>")

    requirements_summary.short_description = "Requirements"


# Register both admin classes
admin.site.register(Prerequisite, PrerequisiteAdmin)
admin.site.register(PrerequisiteCheckResult, PrerequisiteCheckResultAdmin)


# Helper functions for other apps to easily add prerequisite admin functionality


def register_prerequisite_admin(model_class, admin_class=None):
    """
    Register a model with prerequisite admin functionality.

    Args:
        model_class: The Django model class to register
        admin_class: Optional custom admin class (will be extended with
            PrerequisiteAdminMixin)

    Returns:
        The registered admin class
    """
    if admin_class is None:
        # Create a basic admin class
        admin_class = type(
            f"{model_class.__name__}Admin", (PrerequisiteAdminMixin, ModelAdmin), {}
        )
    else:
        # Extend existing admin class with prerequisite functionality
        admin_class = type(
            f"{admin_class.__name__}WithPrerequisites",
            (PrerequisiteAdminMixin, admin_class),
            {},
        )

    # Register with Django admin
    admin.site.register(model_class, admin_class)
    return admin_class


def add_prerequisite_inline(parent_admin_class, model_class, extra=0):
    """
    Add prerequisite inline editing to an existing admin class.

    Args:
        parent_admin_class: The parent admin class to extend
        model_class: The model class for the inline
        extra: Number of extra inline forms to show

    Returns:
        The inline admin class
    """
    inline_class = type(
        f"{model_class.__name__}PrerequisiteInline",
        (admin.TabularInline,),
        {
            "model": model_class,
            "extra": extra,
            "formfield_overrides": {
                models.JSONField: {"widget": PrerequisiteBuilderWidget}
            },
        },
    )

    # Add to parent admin's inlines
    if not hasattr(parent_admin_class, "inlines"):
        parent_admin_class.inlines = []

    parent_admin_class.inlines = list(parent_admin_class.inlines) + [inline_class]

    return inline_class
