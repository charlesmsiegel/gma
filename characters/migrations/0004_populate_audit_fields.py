"""
Data migration to populate audit fields for existing Character records.

This migration sets default values for created_by and modified_by fields
that were added by the mixin application in migration 0003.
"""

from django.db import migrations


def populate_audit_fields(apps, schema_editor):
    """
    Populate created_by and modified_by fields for existing characters.

    Strategy:
    - Set created_by to player_owner (most logical default)
    - Set modified_by to player_owner (assuming they last modified their own character)
    - Timestamps are already handled by auto_now_add and auto_now
    """
    Character = apps.get_model("characters", "Character")

    # Update all existing characters to set audit fields
    for character in Character.objects.all():
        if character.created_by_id is None:
            character.created_by_id = character.player_owner_id
        if character.modified_by_id is None:
            character.modified_by_id = character.player_owner_id
        character.save(update_fields=["created_by_id", "modified_by_id"])


def reverse_audit_fields(apps, schema_editor):
    """
    Reverse the population of audit fields.

    Sets created_by and modified_by back to NULL for rollback safety.
    """
    Character = apps.get_model("characters", "Character")

    # Set audit fields back to NULL
    Character.objects.update(created_by=None, modified_by=None)


class Migration(migrations.Migration):
    """Data migration to populate audit fields for Characters."""

    dependencies = [
        ("characters", "0003_character_created_by_character_modified_by_and_more"),
    ]

    operations = [
        migrations.RunPython(
            populate_audit_fields,
            reverse_audit_fields,
            elidable=True,  # This migration can be squashed/optimized later
        ),
    ]
