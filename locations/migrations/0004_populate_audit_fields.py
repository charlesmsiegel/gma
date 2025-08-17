"""
Data migration to populate audit fields for existing Location records.

This migration sets default values for created_by and modified_by fields
that were added by the mixin application in migration 0003.
"""

from django.db import migrations


def populate_audit_fields(apps, schema_editor):
    """
    Populate created_by and modified_by fields for existing locations.

    Strategy:
    - Set created_by to campaign owner (locations are campaign-level resources)
    - Set modified_by to campaign owner
    - This provides a reasonable default when individual ownership isn't tracked
    """
    Location = apps.get_model("locations", "Location")

    # Update all existing locations to set audit fields based on campaign owner
    for location in Location.objects.select_related("campaign__owner").all():
        if (
            location.created_by_id is None
            and location.campaign
            and location.campaign.owner
        ):
            location.created_by_id = location.campaign.owner_id
        if (
            location.modified_by_id is None
            and location.campaign
            and location.campaign.owner
        ):
            location.modified_by_id = location.campaign.owner_id

        # Only save if we have values to set
        if location.created_by_id or location.modified_by_id:
            update_fields = []
            if location.created_by_id:
                update_fields.append("created_by_id")
            if location.modified_by_id:
                update_fields.append("modified_by_id")
            location.save(update_fields=update_fields)


def reverse_audit_fields(apps, schema_editor):
    """
    Reverse the population of audit fields.

    Sets created_by and modified_by back to NULL for rollback safety.
    """
    Location = apps.get_model("locations", "Location")

    # Set audit fields back to NULL
    Location.objects.update(created_by=None, modified_by=None)


class Migration(migrations.Migration):
    """Data migration to populate audit fields for Locations."""

    dependencies = [
        ("locations", "0003_location_modified_by_alter_location_created_at_and_more"),
    ]

    operations = [
        migrations.RunPython(
            populate_audit_fields,
            reverse_audit_fields,
            elidable=True,  # This migration can be squashed/optimized later
        ),
    ]
