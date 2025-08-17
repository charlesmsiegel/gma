"""
Data migration to populate audit fields for existing Item records.

This migration sets default values for created_by and modified_by fields
that were added by the mixin application in migration 0003.
"""

from django.db import migrations


def populate_audit_fields(apps, schema_editor):
    """
    Populate created_by and modified_by fields for existing items.

    Strategy:
    - Set created_by to campaign owner (items are campaign-level resources)
    - Set modified_by to campaign owner
    - This provides a reasonable default when individual ownership isn't tracked
    """
    Item = apps.get_model("items", "Item")

    # Update all existing items to set audit fields based on campaign owner
    for item in Item.objects.select_related("campaign__owner").all():
        if item.created_by_id is None and item.campaign and item.campaign.owner:
            item.created_by_id = item.campaign.owner_id
        if item.modified_by_id is None and item.campaign and item.campaign.owner:
            item.modified_by_id = item.campaign.owner_id

        # Only save if we have values to set
        if item.created_by_id or item.modified_by_id:
            update_fields = []
            if item.created_by_id:
                update_fields.append("created_by_id")
            if item.modified_by_id:
                update_fields.append("modified_by_id")
            item.save(update_fields=update_fields)


def reverse_audit_fields(apps, schema_editor):
    """
    Reverse the population of audit fields.

    Sets created_by and modified_by back to NULL for rollback safety.
    """
    Item = apps.get_model("items", "Item")

    # Set audit fields back to NULL
    Item.objects.update(created_by=None, modified_by=None)


class Migration(migrations.Migration):
    """Data migration to populate audit fields for Items."""

    dependencies = [
        ("items", "0003_item_modified_by_alter_item_created_at_and_more"),
    ]

    operations = [
        migrations.RunPython(
            populate_audit_fields,
            reverse_audit_fields,
            elidable=True,  # This migration can be squashed/optimized later
        ),
    ]
