"""
Django app configuration for the prerequisites app.

This app provides prerequisite management functionality for tabletop RPG campaigns,
allowing prerequisites to be attached to any model (characters, items, etc.)
using GenericForeignKey relationships.
"""

from django.apps import AppConfig


class PrerequisitesConfig(AppConfig):
    """Configuration for the prerequisites app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "prerequisites"
    verbose_name = "Prerequisites"
    verbose_name_plural = "Prerequisites"
