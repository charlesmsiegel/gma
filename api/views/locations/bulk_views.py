"""
Location API bulk operations views.

This module provides bulk operations for locations including create, update,
delete, and move operations with partial success handling and proper permission
validation.
"""

from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.errors import APIError
from api.serializers import BulkLocationOperationSerializer, LocationSerializer
from locations.models import Location


class LocationBulkAPIView(APIView):
    """
    API view for bulk location operations.

    POST: Perform bulk operations (create, update, delete, move)
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Perform bulk location operations.

        Expected payload:
        {
            "action": "create|update|delete|move",
            "locations": [
                // Array of location data based on action type
            ]
        }
        """
        serializer = BulkLocationOperationSerializer(data=request.data)
        if not serializer.is_valid():
            return APIError.validation_error(serializer.errors)

        action = serializer.validated_data["action"]
        locations_data = serializer.validated_data["locations"]

        # Route to appropriate handler
        if action == "create":
            return self._handle_bulk_create(request, locations_data)
        elif action == "update":
            return self._handle_bulk_update(request, locations_data)
        elif action == "delete":
            return self._handle_bulk_delete(request, locations_data)
        elif action == "move":
            return self._handle_bulk_move(request, locations_data)

        return APIError.validation_error({"action": ["Invalid action type."]})

    def _handle_bulk_create(self, request, locations_data):
        """Handle bulk location creation."""
        created = []
        failed = []
        parent_map = {}  # For tracking parent_name references

        # First pass: create locations without parent_name references
        for i, location_data in enumerate(locations_data):
            try:
                # Check campaign permission
                campaign = location_data.get("campaign")
                if not campaign or not Location.can_create(request.user, campaign):
                    failed.append(
                        {
                            "item_index": i,
                            "name": location_data.get("name", ""),
                            "error": "You don't have permission to create locations "
                            "in this campaign.",
                        }
                    )
                    continue

                # Handle parent_name reference
                parent_name = location_data.pop("parent_name", None)
                if parent_name:
                    # Skip for now, handle in second pass
                    location_data["_parent_name"] = parent_name
                    location_data["_index"] = i

                with transaction.atomic():
                    # Create location
                    location = Location(
                        name=location_data["name"],
                        description=location_data.get("description", ""),
                        campaign=campaign,
                        parent=location_data.get("parent"),
                        owned_by=location_data.get("owned_by"),
                    )
                    location.save(user=request.user)

                    # Track for parent_name resolution
                    if parent_name:
                        parent_map[parent_name] = location

                    created.append(location)

            except Exception as e:
                failed.append(
                    {
                        "item_index": i,
                        "name": location_data.get("name", ""),
                        "error": str(e),
                    }
                )

        # Second pass: handle parent_name references
        deferred_locations = [loc for loc in locations_data if "_parent_name" in loc]
        for location_data in deferred_locations:
            try:
                parent_name = location_data["_parent_name"]
                index = location_data["_index"]

                if parent_name in parent_map:
                    parent = parent_map[parent_name]
                    campaign = location_data.get("campaign")

                    with transaction.atomic():
                        location = Location(
                            name=location_data["name"],
                            description=location_data.get("description", ""),
                            campaign=campaign,
                            parent=parent,
                            owned_by=location_data.get("owned_by"),
                        )
                        location.save(user=request.user)
                        created.append(location)
                else:
                    failed.append(
                        {
                            "item_index": index,
                            "name": location_data.get("name", ""),
                            "error": f"Parent location '{parent_name}' not found "
                            "in this batch.",
                        }
                    )

            except Exception as e:
                failed.append(
                    {
                        "item_index": location_data.get("_index", -1),
                        "name": location_data.get("name", ""),
                        "error": str(e),
                    }
                )

        # Serialize response
        created_serializer = LocationSerializer(
            created, many=True, context={"request": request}
        )

        return Response({"created": created_serializer.data, "failed": failed})

    def _handle_bulk_update(self, request, locations_data):
        """Handle bulk location updates."""
        updated = []
        failed = []

        for i, location_data in enumerate(locations_data):
            try:
                location_id = location_data["id"]

                # Get location
                try:
                    location = Location.objects.get(pk=location_id)
                except Location.DoesNotExist:
                    failed.append(
                        {
                            "item_index": i,
                            "error": f"Location with ID {location_id} not found.",
                        }
                    )
                    continue

                # Check edit permission
                if not location.can_edit(request.user):
                    failed.append(
                        {
                            "item_index": i,
                            "error": f"You don't have permission to edit "
                            f"location '{location.name}'.",
                        }
                    )
                    continue

                with transaction.atomic():
                    # Update fields
                    if "name" in location_data:
                        location.name = location_data["name"]
                    if "description" in location_data:
                        location.description = location_data["description"]
                    if "parent" in location_data:
                        parent = location_data["parent"]
                        if parent and parent.campaign != location.campaign:
                            raise ValueError("Parent must be in the same campaign.")
                        location.parent = parent
                    if "owned_by" in location_data:
                        owned_by = location_data["owned_by"]
                        if owned_by and owned_by.campaign != location.campaign:
                            raise ValueError(
                                "Character owner must be in the same campaign."
                            )
                        location.owned_by = owned_by

                    location.save(user=request.user)
                    updated.append(location)

            except Exception as e:
                failed.append({"item_index": i, "error": str(e)})

        # Serialize response
        updated_serializer = LocationSerializer(
            updated, many=True, context={"request": request}
        )

        return Response({"updated": updated_serializer.data, "failed": failed})

    def _handle_bulk_delete(self, request, locations_data):
        """Handle bulk location deletion."""
        deleted = []
        failed = []

        for i, location_data in enumerate(locations_data):
            try:
                location_id = location_data["id"]

                # Get location
                try:
                    location = Location.objects.get(pk=location_id)
                except Location.DoesNotExist:
                    failed.append(
                        {
                            "item_index": i,
                            "error": f"Location with ID {location_id} not found.",
                        }
                    )
                    continue

                # Check delete permission
                if not location.can_delete(request.user):
                    failed.append(
                        {
                            "item_index": i,
                            "error": f"You don't have permission to delete "
                            f"location '{location.name}'.",
                        }
                    )
                    continue

                with transaction.atomic():
                    deleted_info = {
                        "id": location.id,
                        "name": location.name,
                        "action": "deleted",
                    }
                    location.delete()
                    deleted.append(deleted_info)

            except Exception as e:
                failed.append({"item_index": i, "error": str(e)})

        return Response({"deleted": deleted, "failed": failed})

    def _handle_bulk_move(self, request, locations_data):
        """Handle bulk location moves."""
        moved = []
        failed = []

        for i, location_data in enumerate(locations_data):
            try:
                location_id = location_data["id"]
                new_parent = location_data.get("parent")

                # Get location
                try:
                    location = Location.objects.get(pk=location_id)
                except Location.DoesNotExist:
                    failed.append(
                        {
                            "item_index": i,
                            "error": f"Location with ID {location_id} not found.",
                        }
                    )
                    continue

                # Check edit permission
                if not location.can_edit(request.user):
                    failed.append(
                        {
                            "item_index": i,
                            "error": f"You don't have permission to move "
                            f"location '{location.name}'.",
                        }
                    )
                    continue

                # Validate new parent
                if new_parent:
                    if new_parent.campaign != location.campaign:
                        failed.append(
                            {
                                "item_index": i,
                                "error": "New parent must be in the same campaign.",
                            }
                        )
                        continue

                    # Check for circular reference
                    if new_parent == location or location.is_descendant_of(new_parent):
                        failed.append(
                            {
                                "item_index": i,
                                "error": "Cannot move location to its own descendant "
                                "(circular reference).",
                            }
                        )
                        continue

                with transaction.atomic():
                    location.parent = new_parent
                    location.save(user=request.user)
                    moved.append(location)

            except Exception as e:
                failed.append({"item_index": i, "error": str(e)})

        # Serialize response
        moved_serializer = LocationSerializer(
            moved, many=True, context={"request": request}
        )

        return Response({"moved": moved_serializer.data, "failed": failed})
