"""
Template tags for prerequisite visual builder (Issue #190).

This module provides Django template tags for rendering the
visual prerequisite builder in templates.
"""

import json

from django import template

# Removed unused imports - render_to_string, mark_safe

register = template.Library()


@register.inclusion_tag("widgets/prerequisite_builder_widget.html", takes_context=True)
def prerequisite_builder(context, field_name, initial_value=None):
    """
    Render a visual prerequisite builder widget.

    Usage:
        {% load prerequisite_tags %}
        {% prerequisite_builder field_name="requirements" initial_value=my_req %}
    """

    # Prepare initial data
    initial_data = None
    if initial_value:
        try:
            if isinstance(initial_value, str):
                initial_data = json.loads(initial_value)
            else:
                initial_data = initial_value
        except (json.JSONDecodeError, TypeError):
            initial_data = None

    return {
        "field_name": field_name,
        "initial_value": initial_value,
        "initial_data": initial_data,
        "request": context.get("request"),
    }


@register.simple_tag
def requirement_type_choices():
    """Get available requirement types for the builder."""
    return [
        {
            "value": "trait",
            "label": "Trait Check",
            "description": "Check character trait values",
        },
        {
            "value": "has",
            "label": "Has Item/Feature",
            "description": "Check if character has something",
        },
        {
            "value": "any",
            "label": "Any Of",
            "description": "At least one condition must be met",
        },
        {
            "value": "all",
            "label": "All Of",
            "description": "All conditions must be met",
        },
        {
            "value": "count_tag",
            "label": "Count with Tag",
            "description": "Count items with specific tags",
        },
    ]


@register.filter
def json_pretty(value):
    """Format JSON for pretty display."""
    if not value:
        return ""
    try:
        if isinstance(value, str):
            parsed = json.loads(value)
        else:
            parsed = value
        return json.dumps(parsed, indent=2)
    except (json.JSONDecodeError, TypeError):
        return str(value)
