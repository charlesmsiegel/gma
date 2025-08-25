"""
Custom Django widgets for prerequisite visual builder (Issue #190).

This module provides custom form widgets that integrate the visual
prerequisite builder into Django forms and admin interfaces.
"""

import json

from django import forms
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe


class PrerequisiteBuilderWidget(forms.Widget):
    """
    Custom widget for visual prerequisite building.

    Renders a rich JavaScript interface for building complex prerequisite
    requirements without requiring users to write JSON manually.
    """

    template_name = "admin/widgets/prerequisite_builder.html"

    class Media:
        css = {
            "all": (
                "admin/css/prerequisite-builder.css",
                "admin/css/drag-drop-builder.css",
            )
        }
        js = (
            "admin/js/prerequisite-builder.js",
            "admin/js/drag-drop-builder.js",
            "admin/js/drag-drop-palette.js",
            "admin/js/drag-drop-canvas.js",
            "admin/js/accessibility-manager.js",
            "admin/js/undo-redo-manager.js",
            "admin/js/touch-handler.js",
        )

    def __init__(self, attrs=None):
        default_attrs = {
            "class": "prerequisite-builder-widget",
            "data-widget-type": "prerequisite-builder",
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)

    def render(self, name, value, attrs=None, renderer=None):
        """Render the widget HTML."""
        if attrs is None:
            attrs = {}

        attrs.update(self.attrs)

        # Prepare initial data
        initial_data = None
        if value:
            try:
                if isinstance(value, str):
                    initial_data = json.loads(value)
                else:
                    initial_data = value
            except (json.JSONDecodeError, TypeError):
                initial_data = None

        context = {
            "widget": {
                "name": name,
                "value": value,
                "attrs": attrs,
                "initial_data": initial_data,
            }
        }

        return mark_safe(render_to_string(self.template_name, context))  # nosec

    def value_from_datadict(self, data, files, name):
        """Extract value from form submission data."""
        value = data.get(name)
        if value:
            try:
                # Validate that it's proper JSON
                json.loads(value)
                return value
            except json.JSONDecodeError:
                return None
        return None

    def format_value(self, value):
        """Format value for display in the widget."""
        if value is None:
            return ""
        if isinstance(value, dict):
            return json.dumps(value)
        return value
