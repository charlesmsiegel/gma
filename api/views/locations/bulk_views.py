"""
Location API bulk operations views.

This module provides bulk operations for locations including create, update,
delete, and move operations with partial success handling and proper permission
validation.
"""

from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.errors import APIError
from api.serializers import LocationSerializer
from locations.models import Location
from locations.services import LocationService


class LocationBulkAPIView(APIView):
    """
    API view for bulk location operations.

    POST: Perform bulk operations (create, update, delete, move)
    """

    permission_classes = [IsAuthenticated]
    MAX_BULK_OPERATIONS = LocationService.MAX_BULK_OPERATIONS

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
        # Basic validation
        action = request.data.get("action")
        if not action:
            return APIError.validation_error({"action": ["This field is required."]})

        # Validate action type
        valid_actions = ["create", "update", "delete", "move"]
        if action not in valid_actions:
            return APIError.validation_error(
                {
                    "action": [
                        f"Invalid action. Must be one of: {', '.join(valid_actions)}"
                    ]
                }
            )

        # Get data based on action type
        if action in ["create", "update", "move"]:
            locations_data = request.data.get("locations", [])
            data_field = "locations"
        else:  # delete
            locations_data = request.data.get("location_ids", [])
            data_field = "location_ids"

        if not isinstance(locations_data, list):
            return APIError.validation_error({data_field: ["Must be a list."]})

        # Check bulk operation limit
        if len(locations_data) > self.MAX_BULK_OPERATIONS:
            return APIError.validation_error(
                {
                    data_field: [
                        f"Maximum {self.MAX_BULK_OPERATIONS} locations can be "
                        f"processed at once."
                    ]
                }
            )

        if len(locations_data) == 0:
            return APIError.validation_error(
                {data_field: ["At least one location is required."]}
            )

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
        """Handle bulk location creation using service layer."""
        # For bulk operations, we'll process items individually and handle
        # permissions/validation per item rather than rejecting the entire batch
        try:
            # Use service layer for bulk creation with individual validation
            created, failed = self._bulk_create_with_individual_validation(
                request.user, locations_data
            )

            # Serialize response
            created_serializer = LocationSerializer(
                created, many=True, context={"request": request}
            )

            return Response(
                {
                    "created": created_serializer.data,
                    "failed": failed,
                    "summary": {
                        "total_requested": len(locations_data),
                        "successful": len(created),
                        "failed": len(failed),
                    },
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return APIError.validation_error({"detail": [str(e)]})

    def _bulk_create_with_individual_validation(self, user, locations_data):
        """Create locations with individual validation for partial success."""
        from campaigns.models import Campaign

        created = []
        failed = []

        for i, location_data in enumerate(locations_data):
            try:
                # Validate required fields
                if not location_data.get("name"):
                    failed.append(
                        {
                            "item_index": i,
                            "name": location_data.get("name", ""),
                            "error": "This field is required.",
                        }
                    )
                    continue

                campaign_id = location_data.get("campaign")
                if not campaign_id:
                    failed.append(
                        {
                            "item_index": i,
                            "name": location_data.get("name", ""),
                            "error": "Campaign is required.",
                        }
                    )
                    continue

                # Check campaign exists and user has permission
                try:
                    campaign = Campaign.objects.get(pk=campaign_id)
                    if not Location.can_create(user, campaign):
                        failed.append(
                            {
                                "item_index": i,
                                "name": location_data.get("name", ""),
                                "error": (
                                    "You don't have permission to create "
                                    "locations in this campaign."
                                ),
                            }
                        )
                        continue
                except Campaign.DoesNotExist:
                    failed.append(
                        {
                            "item_index": i,
                            "name": location_data.get("name", ""),
                            "error": "Campaign not found.",
                        }
                    )
                    continue

                # Create the location
                location = Location(
                    name=location_data["name"],
                    description=location_data.get("description", ""),
                    campaign_id=campaign_id,
                    parent_id=location_data.get("parent"),
                    owned_by_id=location_data.get("owned_by"),
                )
                location.full_clean()
                location.save(user=user)
                created.append(location)

            except Exception as e:
                failed.append(
                    {
                        "item_index": i,
                        "name": location_data.get("name", ""),
                        "error": str(e),
                    }
                )

        return created, failed

    def _handle_bulk_update(self, request, locations_data):
        """Handle bulk location updates using service layer."""
        try:
            # Use service layer for bulk updates
            updated, failed = LocationService.bulk_update_locations(
                user=request.user, updates_data=locations_data
            )

            # Serialize response
            updated_serializer = LocationSerializer(
                updated, many=True, context={"request": request}
            )

            return Response(
                {
                    "updated": updated_serializer.data,
                    "failed": failed,
                    "summary": {
                        "total_requested": len(locations_data),
                        "successful": len(updated),
                        "failed": len(failed),
                    },
                },
                status=status.HTTP_200_OK if updated else status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            return APIError.validation_error({"detail": [str(e)]})

    def _handle_bulk_delete(self, request, location_ids):
        """Handle bulk location deletion with proper validation and limits."""
        deleted = []
        failed = []

        for i, location_id in enumerate(location_ids):
            try:
                if not location_id:
                    failed.append(
                        {
                            "item_index": i,
                            "error": "Location ID is required for deletion.",
                        }
                    )
                    continue

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

                # Check delete permission using standardized method
                if not LocationService.check_permission(
                    location, request.user, "delete"
                ):
                    failed.append(
                        {
                            "item_index": i,
                            "error": f"You don't have permission to delete location "
                            f"'{location.name}'.",
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

        return Response(
            {
                "deleted": deleted,
                "failed": failed,
                "summary": {
                    "total_requested": len(location_ids),
                    "successful": len(deleted),
                    "failed": len(failed),
                },
            },
            status=status.HTTP_200_OK if deleted else status.HTTP_400_BAD_REQUEST,
        )

    def _handle_bulk_move(self, request, locations_data):
        """Handle bulk location moves using service layer."""
        moved = []
        failed = []

        for i, location_data in enumerate(locations_data):
            try:
                location_id = location_data.get("id")
                new_parent_id = location_data.get("parent")

                if not location_id:
                    failed.append(
                        {
                            "item_index": i,
                            "error": "Location ID is required for moving.",
                        }
                    )
                    continue

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

                # Get new parent if specified
                new_parent = None
                if new_parent_id:
                    try:
                        new_parent = Location.objects.get(pk=new_parent_id)
                    except Location.DoesNotExist:
                        failed.append(
                            {
                                "item_index": i,
                                "error": f"Parent location with ID {new_parent_id} "
                                f"not found.",
                            }
                        )
                        continue

                # Use service layer for move operation
                try:
                    LocationService.move_location(
                        user=request.user, location=location, new_parent=new_parent
                    )
                    moved.append(location)
                except Exception as e:
                    failed.append({"item_index": i, "error": str(e)})

            except Exception as e:
                failed.append({"item_index": i, "error": str(e)})

        # Serialize response
        moved_serializer = LocationSerializer(
            moved, many=True, context={"request": request}
        )

        return Response(
            {
                "moved": moved_serializer.data,
                "failed": failed,
                "summary": {
                    "total_requested": len(locations_data),
                    "successful": len(moved),
                    "failed": len(failed),
                },
            },
            status=status.HTTP_200_OK if moved else status.HTTP_400_BAD_REQUEST,
        )
