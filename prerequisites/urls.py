"""
URL configuration for prerequisites app (Issue #190).

This module provides API endpoints for the visual prerequisite builder system.
"""

from django.urls import path

from . import views

app_name = "prerequisites"

urlpatterns = [
    # API endpoints for visual builder
    path(
        "validate/",
        views.ValidateRequirementView.as_view(),
        name="validate_requirement",
    ),
    path(
        "suggestions/",
        views.RequirementSuggestionsView.as_view(),
        name="requirement_suggestions",
    ),
    path(
        "templates/",
        views.RequirementTemplatesView.as_view(),
        name="requirement_templates",
    ),
]
