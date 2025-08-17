#!/bin/bash
# Simple rollback for mixin migrations

set -e

echo "Rolling back mixin migrations..."

python manage.py migrate characters 0002
python manage.py migrate items 0002
python manage.py migrate locations 0002

echo "Done. Mixin fields removed."
