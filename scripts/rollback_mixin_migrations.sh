#!/bin/bash
# Rollback script for mixin migrations
# This script provides a safe way to rollback mixin field additions if needed

set -e  # Exit on error

echo "========================================="
echo "Mixin Migration Rollback Script"
echo "========================================="
echo ""
echo "This script will rollback the mixin field migrations for:"
echo "  - Characters (0004 and 0003)"
echo "  - Items (0004 and 0003)"
echo "  - Locations (0004 and 0003)"
echo ""
echo "WARNING: This will remove created_by, modified_by fields"
echo "and reset timestamps to their original state."
echo ""

# Safety confirmation
read -p "Are you sure you want to rollback? (yes/no): " confirmation
if [ "$confirmation" != "yes" ]; then
    echo "Rollback cancelled."
    exit 0
fi

# Check if we're in the right directory
if [ ! -f "manage.py" ]; then
    echo "Error: manage.py not found. Please run this script from the project root."
    exit 1
fi

# Activate virtual environment if needed
if [ -n "$CONDA_PREFIX" ]; then
    echo "Using conda environment: $CONDA_PREFIX"
    PYTHON="$CONDA_PREFIX/bin/python"
else
    PYTHON="python"
fi

echo ""
echo "Starting rollback process..."
echo ""

# Function to rollback a specific app
rollback_app() {
    local app=$1
    local target_migration=$2

    echo "----------------------------------------"
    echo "Rolling back $app to migration $target_migration..."
    echo "----------------------------------------"

    # Show current state
    echo "Current migration state for $app:"
    "$PYTHON" manage.py showmigrations "$app"

    # Perform rollback
    "$PYTHON" manage.py migrate "$app" "$target_migration"

    # Show new state
    echo ""
    echo "New migration state for $app:"
    "$PYTHON" manage.py showmigrations "$app"
    echo ""
}

# Rollback data migrations first (0004)
echo "Step 1: Rolling back data migrations..."
rollback_app "characters" "0003"
rollback_app "items" "0003"
rollback_app "locations" "0003"

# Then rollback schema migrations (0003)
echo ""
echo "Step 2: Rolling back schema migrations..."
rollback_app "characters" "0002"
rollback_app "items" "0002"
rollback_app "locations" "0002"

echo ""
echo "========================================="
echo "Rollback Complete!"
echo "========================================="
echo ""
echo "The following migrations have been rolled back:"
echo "  ✓ characters/0004_populate_audit_fields"
echo "  ✓ characters/0003_character_created_by_character_modified_by_and_more"
echo "  ✓ items/0004_populate_audit_fields"
echo "  ✓ items/0003_item_modified_by_alter_item_created_at_and_more"
echo "  ✓ locations/0004_populate_audit_fields"
echo "  ✓ locations/0003_location_modified_by_alter_location_created_at_and_more"
echo ""
echo "To reapply the migrations, run: python manage.py migrate"
