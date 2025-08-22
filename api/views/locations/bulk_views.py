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
        # Validate action
        action_result = self._validate_action(request)
        if isinstance(action_result, Response):
            return action_result

        action = action_result

        # Prepare data for the specific action
        data_result = self._prepare_action_data(request, action)
        if isinstance(data_result, Response):
            return data_result

        locations_data, data_field = data_result

        # Validate data constraints
        validation_result = self._validate_data_constraints(locations_data, data_field)
        if isinstance(validation_result, Response):
            return validation_result

        # Route to appropriate handler
        return self._route_to_handler(request, action, locations_data)

    def _validate_action(self, request):
        """Validate the action parameter."""
        action = request.data.get("action")
        if not action:
            return APIError.validation_error({"action": ["This field is required."]})

        valid_actions = ["create", "update", "delete", "move"]
        if action not in valid_actions:
            return APIError.validation_error(
                {
                    "action": [
                        f"Invalid action. Must be one of: {', '.join(valid_actions)}"
                    ]
                }
            )

        return action

    def _prepare_action_data(self, request, action):
        """Prepare and extract data based on action type."""
        if action == "move":
            return self._prepare_move_data(request)
        elif action in ["create", "update"]:
            locations_data = request.data.get("locations", [])
            return locations_data, "locations"
        else:  # delete
            locations_data = request.data.get("location_ids", [])
            return locations_data, "location_ids"

    def _prepare_move_data(self, request):
        """Prepare data for move operations supporting two formats."""
        # Move operations support two formats:
        # 1. "locations": [{"id": 1, "parent": 2}, {"id": 3, "parent": null}]
        # 2. "location_ids": [1, 3], "new_parent": 2
        if "location_ids" in request.data:
            location_ids = request.data.get("location_ids", [])
            new_parent = request.data.get("new_parent")
            # Convert to standard format
            locations_data = [
                {"id": loc_id, "parent": new_parent} for loc_id in location_ids
            ]
            return locations_data, "location_ids"
        else:
            locations_data = request.data.get("locations", [])
            return locations_data, "locations"

    def _validate_data_constraints(self, locations_data, data_field):
        """Validate data type and constraints."""
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

        # Return None to indicate validation passed
        return None

    def _route_to_handler(self, request, action, locations_data):
        """Route request to appropriate action handler."""
        if action == "create":
            return self._handle_bulk_create(request, locations_data)
        if action == "update":
            return self._handle_bulk_update(request, locations_data)
        if action == "delete":
            return self._handle_bulk_delete(request, locations_data)
        if action == "move":
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
        created = []
        failed = []

        for i, location_data in enumerate(locations_data):
            result = self._process_single_creation(user, i, location_data)
            if result.get("success"):
                created.append(result["location"])
            else:
                failed.append(result["error"])

        return created, failed

    def _process_single_creation(self, user, item_index, location_data):
        """Process a single location creation with validation."""
        try:
            # Validate basic requirements
            validation_error = self._validate_creation_requirements(
                item_index, location_data
            )
            if validation_error:
                return validation_error

            # Validate campaign access
            campaign_result = self._validate_creation_campaign(
                user, item_index, location_data
            )
            if not campaign_result.get("success"):
                return campaign_result

            campaign = campaign_result["campaign"]

            # Validate character ownership if specified
            if location_data.get("owned_by"):
                char_result = self._validate_creation_character(
                    user, item_index, location_data, campaign
                )
                if not char_result.get("success"):
                    return char_result

            # Create the location
            location = self._create_location_instance(user, location_data)
            return {"success": True, "location": location}

        except Exception as e:
            return self._create_creation_error(
                item_index, location_data.get("name", ""), str(e)
            )

    def _validate_creation_requirements(self, item_index, location_data):
        """Validate basic requirements for location creation."""
        if not location_data.get("name"):
            return self._create_creation_error(
                item_index, "", "This field is required."
            )

        if not location_data.get("campaign"):
            return self._create_creation_error(
                item_index, location_data.get("name", ""), "Campaign is required."
            )

        return None

    def _validate_creation_campaign(self, user, item_index, location_data):
        """Validate campaign access for location creation."""
        from campaigns.models import Campaign

        campaign_id = location_data.get("campaign")
        try:
            campaign = Campaign.objects.get(pk=campaign_id)
            if not Location.can_create(user, campaign):
                return self._create_creation_error(
                    item_index,
                    location_data.get("name", ""),
                    "You don't have permission to create locations in this campaign.",
                )
            return {"success": True, "campaign": campaign}

        except Campaign.DoesNotExist:
            return self._create_creation_error(
                item_index, location_data.get("name", ""), "Campaign not found."
            )

    def _validate_creation_character(self, user, item_index, location_data, campaign):
        """Validate character ownership for location creation."""
        from characters.models import Character

        owned_by_id = location_data.get("owned_by")
        try:
            owned_by_character = Character.objects.get(pk=owned_by_id)

            # Check campaign membership
            if owned_by_character.campaign_id != campaign.id:
                return self._create_creation_error(
                    item_index,
                    location_data.get("name", ""),
                    "Character must be in the same campaign as the location.",
                )

            # Check role-based permissions
            user_role = campaign.get_user_role(user)
            if (
                user_role not in ["OWNER", "GM"]
                and owned_by_character.player_owner != user
            ):
                return self._create_creation_error(
                    item_index,
                    location_data.get("name", ""),
                    "You can only assign ownership to characters you own.",
                )

            return {"success": True}

        except Character.DoesNotExist:
            return self._create_creation_error(
                item_index,
                location_data.get("name", ""),
                "Specified character does not exist.",
            )

    def _create_location_instance(self, user, location_data):
        """Create and save a new location instance."""
        location = Location(
            name=location_data["name"],
            description=location_data.get("description", ""),
            campaign_id=location_data.get("campaign"),
            parent_id=location_data.get("parent"),
            owned_by_id=location_data.get("owned_by"),
        )
        location.full_clean()
        location.save(user=user)
        return location

    def _create_creation_error(self, item_index, name, error_message):
        """Create a standardized error response for creation operations."""
        return {
            "success": False,
            "error": {
                "item_index": item_index,
                "name": name,
                "error": error_message,
            },
        }

    def _bulk_update_with_individual_validation(self, user, locations_data):
        """Update locations with individual validation for partial success."""
        updated = []
        failed = []

        for i, update_data in enumerate(locations_data):
            result = self._process_single_update(user, i, update_data)
            if result.get("success"):
                updated.append(result["location"])
            else:
                failed.append(result["error"])

        return updated, failed

    def _process_single_update(self, user, item_index, update_data):
        """Process a single location update with validation."""
        try:
            # Validate location ID
            location_id = update_data.get("id")
            if not location_id:
                return self._create_update_error(
                    item_index, "Location ID is required for updates."
                )

            # Get and validate location
            try:
                location = Location.objects.get(pk=location_id)
            except Location.DoesNotExist:
                return self._create_update_error(
                    item_index, f"Location with ID {location_id} not found."
                )

            # Check permissions
            if not location.can_edit(user):
                return self._create_update_error(
                    item_index, "You don't have permission to edit this location."
                )

            # Validate foreign key fields
            validation_result = self._validate_update_foreign_keys(
                user, item_index, location, update_data
            )
            if not validation_result.get("success"):
                return validation_result

            # Apply updates
            self._apply_location_updates(location, update_data, validation_result)
            location.full_clean()
            location.save(user=user)

            return {"success": True, "location": location}

        except Exception as e:
            return self._create_update_error(item_index, str(e))

    def _validate_update_foreign_keys(self, user, item_index, location, update_data):
        """Validate foreign key fields for location updates."""
        validated_character = None
        validated_parent = None

        # Validate character ownership
        if "owned_by" in update_data:
            char_result = self._validate_character_ownership(
                user, item_index, location, update_data["owned_by"]
            )
            if not char_result.get("success"):
                return char_result
            validated_character = char_result.get("character")

        # Validate parent location
        if "parent" in update_data:
            parent_result = self._validate_parent_location(
                item_index, location, update_data["parent"]
            )
            if not parent_result.get("success"):
                return parent_result
            validated_parent = parent_result.get("parent")

        return {
            "success": True,
            "validated_character": validated_character,
            "validated_parent": validated_parent,
        }

    def _validate_character_ownership(self, user, item_index, location, owned_by_id):
        """Validate character ownership assignment."""
        if owned_by_id:
            try:
                from characters.models import Character

                owned_by_character = Character.objects.get(pk=owned_by_id)

                # Check campaign membership
                if owned_by_character.campaign != location.campaign:
                    return self._create_update_error(
                        item_index,
                        "Character must be in the same campaign as the location.",
                    )

                # Check role-based permissions
                user_role = location.campaign.get_user_role(user)
                if (
                    user_role not in ["OWNER", "GM"]
                    and owned_by_character.player_owner != user
                ):
                    return self._create_update_error(
                        item_index,
                        "You can only assign ownership to characters you own.",
                    )

                return {"success": True, "character": owned_by_character}

            except Character.DoesNotExist:
                return self._create_update_error(
                    item_index, "Specified character does not exist."
                )
        else:
            # Setting owned_by to None
            return {"success": True, "character": None}

    def _validate_parent_location(self, item_index, location, parent_id):
        """Validate parent location assignment."""
        if parent_id:
            try:
                parent_location = Location.objects.get(pk=parent_id)

                # Check campaign membership
                if parent_location.campaign != location.campaign:
                    return self._create_update_error(
                        item_index,
                        "Parent must be in the same campaign as the location.",
                    )

                # Check for circular reference
                if location.pk and (
                    parent_location.pk == location.pk
                    or parent_location.is_descendant_of(location)
                ):
                    return self._create_update_error(
                        item_index,
                        "Cannot set parent - would create circular reference "
                        "in location hierarchy.",
                    )

                return {"success": True, "parent": parent_location}

            except Location.DoesNotExist:
                return self._create_update_error(
                    item_index, "Specified parent location does not exist."
                )
        else:
            # Setting parent to None
            return {"success": True, "parent": None}

    def _apply_location_updates(self, location, update_data, validation_result):
        """Apply validated updates to a location."""
        for field, value in update_data.items():
            if field != "id" and hasattr(location, field):
                if field == "owned_by":
                    setattr(
                        location, field, validation_result.get("validated_character")
                    )
                elif field == "parent":
                    setattr(location, field, validation_result.get("validated_parent"))
                else:
                    setattr(location, field, value)

    def _create_update_error(self, item_index, error_message):
        """Create a standardized error response for update operations."""
        return {
            "success": False,
            "error": {
                "item_index": item_index,
                "error": error_message,
            },
        }

    def _handle_bulk_update(self, request, locations_data):
        """Handle bulk location updates using service layer."""
        try:
            # Use individual validation for bulk updates with ownership checking
            updated, failed = self._bulk_update_with_individual_validation(
                request.user, locations_data
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
                status=status.HTTP_200_OK,
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
            status=status.HTTP_200_OK,
        )

    def _handle_bulk_move(self, request, locations_data):
        """Handle bulk location moves using service layer."""
        # Validate cross-campaign moves for bulk operations
        campaign_validation = self._validate_bulk_move_campaigns(request)
        if campaign_validation:
            return campaign_validation

        moved = []
        failed = []

        for i, location_data in enumerate(locations_data):
            result = self._process_single_move(request.user, i, location_data)
            if result.get("success"):
                moved.append(result["location"])
            else:
                failed.append(result["error"])

        return self._create_bulk_move_response(request, moved, failed, locations_data)

    def _validate_bulk_move_campaigns(self, request):
        """Validate that bulk move operations don't cross campaign boundaries."""
        if not (request.data.get("location_ids") and request.data.get("new_parent")):
            return None

        location_ids = request.data.get("location_ids", [])
        new_parent_id = request.data.get("new_parent")

        # Collect campaigns from all involved locations
        campaigns = set()
        for loc_id in location_ids:
            try:
                location = Location.objects.select_related("campaign").get(pk=loc_id)
                campaigns.add(location.campaign_id)
            except Location.DoesNotExist:
                pass  # Will be handled in individual processing

        # Add parent campaign if specified
        if new_parent_id:
            try:
                parent = Location.objects.select_related("campaign").get(
                    pk=new_parent_id
                )
                campaigns.add(parent.campaign_id)
            except Location.DoesNotExist:
                return APIError.validation_error(
                    {"new_parent": ["Parent location not found."]}
                )

        # Ensure all locations are in the same campaign
        if len(campaigns) > 1:
            return APIError.validation_error(
                {
                    "campaign": [
                        "All locations must be in the same campaign for bulk moves."
                    ]
                }
            )

        return None

    def _process_single_move(self, user, item_index, location_data):
        """Process a single location move operation."""
        try:
            location_id = location_data.get("id")
            if not location_id:
                return self._create_move_error(
                    item_index, "Location ID is required for moving."
                )

            # Get location and new parent
            try:
                location = Location.objects.get(pk=location_id)
            except Location.DoesNotExist:
                return self._create_move_error(
                    item_index, f"Location with ID {location_id} not found."
                )

            new_parent = self._get_move_parent(item_index, location_data.get("parent"))
            if isinstance(new_parent, dict) and not new_parent.get("success"):
                return new_parent

            # Perform move using service layer
            LocationService.move_location(
                user=user, location=location, new_parent=new_parent
            )
            return {"success": True, "location": location}

        except Exception as e:
            return self._create_move_error(item_index, str(e))

    def _get_move_parent(self, item_index, parent_id):
        """Get and validate the new parent location for a move operation."""
        if not parent_id:
            return None

        try:
            return Location.objects.get(pk=parent_id)
        except Location.DoesNotExist:
            return self._create_move_error(
                item_index, f"Parent location with ID {parent_id} not found."
            )

    def _create_move_error(self, item_index, error_message):
        """Create a standardized error response for move operations."""
        return {
            "success": False,
            "error": {
                "item_index": item_index,
                "error": error_message,
            },
        }

    def _create_bulk_move_response(self, request, moved, failed, locations_data):
        """Create the response for bulk move operations."""
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
            status=status.HTTP_200_OK,
        )
