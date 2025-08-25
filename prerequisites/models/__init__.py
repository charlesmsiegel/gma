"""
Prerequisites models for tabletop RPG campaign management.

This module provides the Prerequisite model that can be attached to any model
(characters, items, future powers, etc.) using GenericForeignKey.

Key features:
- GenericForeignKey to attach to any model
- JSON requirements field for structured requirements
- Description field for human-readable requirements
- Database indexes for performance
- Basic validation for JSON structure

Usage:
    from prerequisites.models import Prerequisite

    # Create a standalone prerequisite
    prereq = Prerequisite.objects.create(
        description="Must have Arete 3 or higher",
        requirements={"attributes": {"arete": {"min": 3}}}
    )

    # Attach prerequisite to a character
    character_prereq = Prerequisite.objects.create(
        description="Combat training required",
        requirements={"skills": {"melee": {"min": 2}}},
        content_object=character
    )
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models

from core.models import TimestampedMixin
from prerequisites import validators


def validate_description(value: str) -> None:
    """Validate that description is not empty or whitespace-only."""
    if not value or not value.strip():
        raise ValidationError("Description cannot be empty or whitespace-only.")


class Prerequisite(TimestampedMixin, models.Model):
    """
    Prerequisite model that can be attached to any model via GenericForeignKey.

    Provides structured prerequisite management for RPG campaign elements:
    - Characters can have prerequisites for advancement
    - Items can have prerequisites for use or creation
    - Future: Powers, spells, abilities can have prerequisites

    Features:
    - GenericForeignKey for attaching to any model
    - JSON field for structured requirements
    - Human-readable description
    - Timestamp tracking via TimestampedMixin
    - Database indexes for efficient queries
    """

    description = models.CharField(
        max_length=500,
        validators=[validate_description],
        help_text="Human-readable description of the prerequisite",
    )

    requirements = models.JSONField(
        default=dict, blank=True, help_text="Structured requirements in JSON format"
    )

    # GenericForeignKey to attach prerequisites to any model
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Type of object this prerequisite is attached to",
    )
    object_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="ID of the object this prerequisite is attached to",
    )
    content_object = GenericForeignKey("content_type", "object_id")

    class Meta:
        db_table = "prerequisites_prerequisite"
        ordering = ["-created_at"]  # Newest first
        verbose_name = "Prerequisite"
        verbose_name_plural = "Prerequisites"
        indexes = [
            # Index for GenericForeignKey queries
            models.Index(
                fields=["content_type", "object_id"], name="prereq_content_idx"
            ),
            # Index for filtering by content type
            models.Index(fields=["content_type"], name="prereq_content_type_idx"),
        ]

    def __str__(self) -> str:
        """Return string representation of the prerequisite."""
        if len(self.description) > 100:
            return f"{self.description[:100]}..."
        return self.description

    def clean(self) -> None:
        """Validate the prerequisite data."""
        super().clean()

        # Validate description (also handled by field validator)
        if not self.description or not self.description.strip():
            raise ValidationError(
                {"description": "Description cannot be empty or whitespace-only."}
            )

        # Ensure requirements is a dict (JSONField should handle this)
        if self.requirements is None:
            self.requirements = {}

        if not isinstance(self.requirements, dict):
            raise ValidationError(
                {"requirements": "Requirements must be a JSON object (dictionary)."}
            )

        # Validate requirements structure using the validators module
        try:
            validators.validate_requirements(self.requirements)
        except ValidationError as e:
            raise ValidationError({"requirements": str(e)})

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Save the prerequisite with validation."""
        # Ensure requirements is never null
        if self.requirements is None:
            self.requirements = {}

        self.full_clean()
        super().save(*args, **kwargs)


class PrerequisiteCheckResult(TimestampedMixin, models.Model):
    """
    Records the results of prerequisite checks for auditing and analysis.

    Stores the outcome of checking whether a character meets the requirements
    for a specific object (character advancement, item use, etc.).
    """

    # The object that was checked
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        help_text="Type of object that was checked",
    )
    object_id = models.PositiveIntegerField(
        help_text="ID of the object that was checked"
    )
    content_object = GenericForeignKey("content_type", "object_id")

    # The character that was checked
    character = models.ForeignKey(
        "characters.Character",
        on_delete=models.CASCADE,
        help_text="Character that was checked",
    )

    # The requirements that were evaluated
    requirements = models.JSONField(help_text="Requirements that were checked")

    # The result of the check
    result = models.BooleanField(help_text="Whether the character met the requirements")

    # Details about failures
    failure_reasons = models.JSONField(
        default=list,
        blank=True,
        help_text="List of reasons why requirements were not met",
    )

    # When the check was performed (from TimestampedMixin)
    checked_at = models.DateTimeField(
        auto_now_add=True, help_text="When this check was performed"
    )

    class Meta:
        db_table = "prerequisites_check_result"
        ordering = ["-checked_at"]  # Newest first
        verbose_name = "Prerequisite Check Result"
        verbose_name_plural = "Prerequisite Check Results"
        indexes = [
            # Index for object queries
            models.Index(
                fields=["content_type", "object_id"], name="prereq_check_object_idx"
            ),
            # Index for character queries
            models.Index(fields=["character"], name="prereq_check_char_idx"),
            # Index for result filtering
            models.Index(fields=["result"], name="prereq_check_result_idx"),
            # Index for time-based queries
            models.Index(fields=["checked_at"], name="prereq_check_time_idx"),
        ]

    def __str__(self) -> str:
        """Return string representation of the check result."""
        result_str = "PASSED" if self.result else "FAILED"
        return f"{self.character.name} - {self.content_object} [{result_str}]"
