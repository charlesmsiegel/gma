"""
Tests for Location API bulk operations.

This module tests bulk location operations including bulk create, update, delete,
and move operations with proper permission checks, validation, and partial
success handling.
"""

from django.contrib.auth import get_user_model
from rest_framework import status

from locations.models import Location

from .test_location_api_base import BaseLocationAPITestCase

User = get_user_model()


class LocationBulkCreateTest(BaseLocationAPITestCase):
    """Test bulk location creation functionality."""

    def test_bulk_create_multiple_locations(self):
        """Test creating multiple locations in one request."""
        self.client.force_authenticate(user=self.player1)

        bulk_data = {
            "action": "create",
            "locations": [
                {
                    "name": "Bulk Location 1",
                    "description": "First bulk created location",
                    "campaign": self.campaign.pk,
                },
                {
                    "name": "Bulk Location 2",
                    "description": "Second bulk created location",
                    "campaign": self.campaign.pk,
                    "parent": self.location1.pk,
                },
                {
                    "name": "Bulk Location 3",
                    "campaign": self.campaign.pk,
                    "owned_by": self.character1.pk,
                },
            ],
        }

        response = self.client.post(self.bulk_url, data=bulk_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIn("created", data)
        self.assertIn("failed", data)
        self.assertEqual(len(data["created"]), 3)
        self.assertEqual(len(data["failed"]), 0)

        # Verify locations were created
        for location_data in data["created"]:
            location = Location.objects.get(pk=location_data["id"])
            self.assertEqual(location.campaign, self.campaign)
            self.assertEqual(location.created_by, self.player1)

    def test_bulk_create_with_hierarchy(self):
        """Test bulk creating locations with hierarchical relationships."""
        self.client.force_authenticate(user=self.gm)

        # First create parent location
        parent_data = {
            "action": "create",
            "locations": [
                {
                    "name": "Parent Location",
                    "campaign": self.campaign.pk,
                }
            ],
        }

        parent_response = self.client.post(
            self.bulk_url, data=parent_data, format="json"
        )
        self.assertEqual(parent_response.status_code, status.HTTP_200_OK)
        parent_id = parent_response.json()["created"][0]["id"]

        # Then create child location with reference to parent
        child_data = {
            "action": "create",
            "locations": [
                {
                    "name": "Child Location",
                    "campaign": self.campaign.pk,
                    "parent": parent_id,
                }
            ],
        }

        child_response = self.client.post(self.bulk_url, data=child_data, format="json")
        self.assertEqual(child_response.status_code, status.HTTP_200_OK)

        # Verify hierarchy was established
        parent = Location.objects.get(name="Parent Location")
        child = Location.objects.get(name="Child Location")
        self.assertEqual(child.parent, parent)

    def test_bulk_create_partial_success(self):
        """Test bulk create with some successful and some failed locations."""
        self.client.force_authenticate(user=self.player1)

        bulk_data = {
            "action": "create",
            "locations": [
                {
                    "name": "Valid Location",
                    "campaign": self.campaign.pk,
                },
                {
                    "name": "",  # Invalid: empty name
                    "campaign": self.campaign.pk,
                },
                {
                    "name": "Another Valid Location",
                    "campaign": self.campaign.pk,
                    "parent": self.location1.pk,
                },
                {
                    "name": "Invalid Campaign Location",
                    "campaign": 99999,  # Non-existent campaign
                },
            ],
        }

        response = self.client.post(self.bulk_url, data=bulk_data, format="json")
        if response.status_code != status.HTTP_200_OK:
            print(f"Debug: Unexpected status {response.status_code}")
            print(f"Debug: Response data: {response.json()}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data["created"]), 2)
        self.assertEqual(len(data["failed"]), 2)

        # Check failed items have error messages
        for failed_item in data["failed"]:
            self.assertIn("error", failed_item)

    def test_bulk_create_permission_check(self):
        """Test that bulk create respects permission checks."""
        self.client.force_authenticate(user=self.observer)

        bulk_data = {
            "action": "create",
            "locations": [
                {
                    "name": "Observer Location",
                    "campaign": self.campaign.pk,
                }
            ],
        }

        response = self.client.post(self.bulk_url, data=bulk_data, format="json")
        if response.status_code != status.HTTP_200_OK:
            print(f"Debug permission test: Unexpected status {response.status_code}")
            print(f"Debug permission test: Response data: {response.json()}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data["created"]), 0)
        self.assertEqual(len(data["failed"]), 1)
        self.assertIn("permission", data["failed"][0]["error"].lower())

    def test_bulk_create_validates_ownership(self):
        """Test that bulk create validates character ownership."""
        self.client.force_authenticate(user=self.player2)

        bulk_data = {
            "action": "create",
            "locations": [
                {
                    "name": "Valid Own Character Location",
                    "campaign": self.campaign.pk,
                    "owned_by": self.character2.pk,  # Player2's character - OK
                },
                {
                    "name": "Invalid Other Character Location",
                    "campaign": self.campaign.pk,
                    "owned_by": self.character1.pk,  # Player1's character - Should fail
                },
            ],
        }

        response = self.client.post(self.bulk_url, data=bulk_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data["created"]), 1)
        self.assertEqual(len(data["failed"]), 1)


class LocationBulkUpdateTest(BaseLocationAPITestCase):
    """Test bulk location update functionality."""

    def test_bulk_update_multiple_locations(self):
        """Test updating multiple locations in one request."""
        self.client.force_authenticate(user=self.owner)

        bulk_data = {
            "action": "update",
            "updates": [
                {
                    "id": self.location1.pk,
                    "name": "Updated Test City",
                    "description": "Updated via bulk operation",
                },
                {
                    "id": self.child_location1.pk,
                    "name": "Updated City Center",
                },
            ],
        }

        response = self.client.post(self.bulk_url, data=bulk_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data["updated"]), 2)
        self.assertEqual(len(data["failed"]), 0)

        # Verify updates were applied
        self.location1.refresh_from_db()
        self.child_location1.refresh_from_db()
        self.assertEqual(self.location1.name, "Updated Test City")
        self.assertEqual(self.child_location1.name, "Updated City Center")

    def test_bulk_update_with_ownership_changes(self):
        """Test bulk updating location ownership."""
        self.client.force_authenticate(user=self.gm)

        bulk_data = {
            "action": "update",
            "updates": [
                {
                    "id": self.location1.pk,
                    "owned_by": self.npc_character.pk,
                },
                {
                    "id": self.child_location1.pk,
                    "owned_by": self.character2.pk,
                },
            ],
        }

        response = self.client.post(self.bulk_url, data=bulk_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data["updated"]), 2)

        # Verify ownership changes
        self.location1.refresh_from_db()
        self.child_location1.refresh_from_db()
        self.assertEqual(self.location1.owned_by, self.npc_character)
        self.assertEqual(self.child_location1.owned_by, self.character2)

    def test_bulk_update_hierarchy_changes(self):
        """Test bulk updating location hierarchy."""
        self.client.force_authenticate(user=self.owner)

        bulk_data = {
            "action": "update",
            "updates": [
                {
                    "id": self.grandchild_location.pk,
                    "parent": self.location2.pk,  # Move to different parent
                },
                {
                    "id": self.child_location2.pk,
                    "parent": None,  # Make it a root location
                },
            ],
        }

        response = self.client.post(self.bulk_url, data=bulk_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data["updated"]), 2)

        # Verify hierarchy changes
        self.grandchild_location.refresh_from_db()
        self.child_location2.refresh_from_db()
        self.assertEqual(self.grandchild_location.parent, self.location2)
        self.assertIsNone(self.child_location2.parent)

    def test_bulk_update_permission_filtering(self):
        """Test that bulk update only affects locations user can edit."""
        self.client.force_authenticate(user=self.player1)

        bulk_data = {
            "action": "update",
            "updates": [
                {
                    "id": self.location2.pk,  # Player1 owns this via character
                    "name": "Player1 Updated House",
                },
                {
                    "id": self.location1.pk,  # Player1 cannot edit this
                    "name": "Unauthorized Update",
                },
            ],
        }

        response = self.client.post(self.bulk_url, data=bulk_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data["updated"]), 1)
        self.assertEqual(len(data["failed"]), 1)

        # Verify only authorized update was applied
        self.location2.refresh_from_db()
        self.location1.refresh_from_db()
        self.assertEqual(self.location2.name, "Player1 Updated House")
        self.assertNotEqual(self.location1.name, "Unauthorized Update")

    def test_bulk_update_validates_hierarchy_constraints(self):
        """Test that bulk update validates hierarchy constraints."""
        self.client.force_authenticate(user=self.owner)

        bulk_data = {
            "action": "update",
            "updates": [
                {
                    "id": self.location1.pk,
                    "parent": self.grandchild_location.pk,  # Would create circular ref
                }
            ],
        }

        response = self.client.post(self.bulk_url, data=bulk_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data["updated"]), 0)
        self.assertEqual(len(data["failed"]), 1)
        self.assertIn("parent", data["failed"][0]["errors"])

    def test_bulk_update_nonexistent_locations(self):
        """Test bulk update handles non-existent locations gracefully."""
        self.client.force_authenticate(user=self.owner)

        bulk_data = {
            "action": "update",
            "updates": [
                {
                    "id": 99999,  # Non-existent
                    "name": "Does Not Exist",
                },
                {
                    "id": self.location1.pk,
                    "name": "Valid Update",
                },
            ],
        }

        response = self.client.post(self.bulk_url, data=bulk_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data["updated"]), 1)
        self.assertEqual(len(data["failed"]), 1)


class LocationBulkDeleteTest(BaseLocationAPITestCase):
    """Test bulk location deletion functionality."""

    def test_bulk_delete_multiple_locations(self):
        """Test deleting multiple locations in one request."""
        # Create additional locations for deletion
        delete_location1 = Location.objects.create(
            name="Delete Me 1",
            campaign=self.campaign,
            created_by=self.player1,
        )
        delete_location2 = Location.objects.create(
            name="Delete Me 2",
            campaign=self.campaign,
            created_by=self.player1,
        )

        self.client.force_authenticate(user=self.owner)

        bulk_data = {
            "action": "delete",
            "location_ids": [delete_location1.pk, delete_location2.pk],
        }

        response = self.client.post(self.bulk_url, data=bulk_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data["deleted"]), 2)
        self.assertEqual(len(data["failed"]), 0)

        # Verify locations were deleted
        self.assertFalse(Location.objects.filter(pk=delete_location1.pk).exists())
        self.assertFalse(Location.objects.filter(pk=delete_location2.pk).exists())

    def test_bulk_delete_handles_hierarchy(self):
        """Test that bulk delete properly handles hierarchy relationships."""
        self.client.force_authenticate(user=self.owner)

        # Delete parent and child - should handle orphaned grandchild
        bulk_data = {
            "action": "delete",
            "location_ids": [self.location1.pk, self.child_location1.pk],
        }

        response = self.client.post(self.bulk_url, data=bulk_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data["deleted"]), 2)

        # Verify grandchild still exists but is now orphaned
        self.assertTrue(
            Location.objects.filter(pk=self.grandchild_location.pk).exists()
        )
        self.grandchild_location.refresh_from_db()
        self.assertIsNone(self.grandchild_location.parent)

    def test_bulk_delete_permission_filtering(self):
        """Test that bulk delete only affects locations user can delete."""
        self.client.force_authenticate(user=self.player1)

        bulk_data = {
            "action": "delete",
            "location_ids": [
                self.location2.pk,  # Player1 can delete (owns via character)
                self.location1.pk,  # Player1 cannot delete (not owner/creator)
            ],
        }

        response = self.client.post(self.bulk_url, data=bulk_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data["deleted"]), 1)
        self.assertEqual(len(data["failed"]), 1)

        # Verify only authorized deletion occurred
        self.assertFalse(Location.objects.filter(pk=self.location2.pk).exists())
        self.assertTrue(Location.objects.filter(pk=self.location1.pk).exists())

    def test_bulk_delete_nonexistent_locations(self):
        """Test bulk delete handles non-existent locations gracefully."""
        self.client.force_authenticate(user=self.owner)

        bulk_data = {
            "action": "delete",
            "location_ids": [99999, self.location1.pk],  # One fake, one real
        }

        response = self.client.post(self.bulk_url, data=bulk_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data["deleted"]), 1)
        self.assertEqual(len(data["failed"]), 1)

    def test_bulk_delete_empty_list(self):
        """Test bulk delete with empty location list."""
        self.client.force_authenticate(user=self.owner)

        bulk_data = {"action": "delete", "location_ids": []}

        response = self.client.post(self.bulk_url, data=bulk_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("location_ids", response.json())


class LocationBulkMoveTest(BaseLocationAPITestCase):
    """Test bulk location move functionality."""

    def test_bulk_move_to_new_parent(self):
        """Test moving multiple locations to a new parent."""
        # Create additional locations to move
        move_location1 = Location.objects.create(
            name="Move Me 1",
            campaign=self.campaign,
            created_by=self.owner,
        )
        move_location2 = Location.objects.create(
            name="Move Me 2",
            campaign=self.campaign,
            created_by=self.owner,
        )

        self.client.force_authenticate(user=self.owner)

        bulk_data = {
            "action": "move",
            "location_ids": [move_location1.pk, move_location2.pk],
            "new_parent": self.location1.pk,
        }

        response = self.client.post(self.bulk_url, data=bulk_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data["moved"]), 2)
        self.assertEqual(len(data["failed"]), 0)

        # Verify locations were moved
        move_location1.refresh_from_db()
        move_location2.refresh_from_db()
        self.assertEqual(move_location1.parent, self.location1)
        self.assertEqual(move_location2.parent, self.location1)

    def test_bulk_move_to_root(self):
        """Test moving multiple locations to root level (no parent)."""
        self.client.force_authenticate(user=self.owner)

        bulk_data = {
            "action": "move",
            "location_ids": [self.child_location1.pk, self.grandchild_location.pk],
            "new_parent": None,
        }

        response = self.client.post(self.bulk_url, data=bulk_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data["moved"]), 2)

        # Verify locations are now at root level
        self.child_location1.refresh_from_db()
        self.grandchild_location.refresh_from_db()
        self.assertIsNone(self.child_location1.parent)
        self.assertIsNone(self.grandchild_location.parent)

    def test_bulk_move_validates_circular_references(self):
        """Test that bulk move validates against circular references."""
        self.client.force_authenticate(user=self.owner)

        bulk_data = {
            "action": "move",
            "location_ids": [self.location1.pk],  # Root location
            "new_parent": self.child_location1.pk,  # Its own child
        }

        response = self.client.post(self.bulk_url, data=bulk_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data["moved"]), 0)
        self.assertEqual(len(data["failed"]), 1)
        self.assertIn("circular", data["failed"][0]["error"].lower())

    def test_bulk_move_validates_same_campaign(self):
        """Test that bulk move validates same campaign constraint."""
        self.client.force_authenticate(user=self.owner)

        bulk_data = {
            "action": "move",
            "location_ids": [self.location1.pk],
            "new_parent": self.public_location.pk,  # Different campaign
        }

        response = self.client.post(self.bulk_url, data=bulk_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("campaign", response.json())

    def test_bulk_move_permission_filtering(self):
        """Test that bulk move respects permission checks."""
        self.client.force_authenticate(user=self.player1)

        bulk_data = {
            "action": "move",
            "location_ids": [
                self.location2.pk,  # Player1 can move (owns via character)
                self.location1.pk,  # Player1 cannot move (not owner)
            ],
            "new_parent": None,
        }

        response = self.client.post(self.bulk_url, data=bulk_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data["moved"]), 1)
        self.assertEqual(len(data["failed"]), 1)

        # Verify only authorized move occurred
        self.location2.refresh_from_db()
        self.location1.refresh_from_db()
        self.assertIsNone(self.location2.parent)  # Was moved to root
        self.assertIsNotNone(self.location1.parent)  # Unchanged


class LocationBulkMixedOperationsTest(BaseLocationAPITestCase):
    """Test mixed bulk operations and edge cases."""

    def test_bulk_invalid_action(self):
        """Test bulk operation with invalid action."""
        self.client.force_authenticate(user=self.owner)

        bulk_data = {"action": "invalid_action", "location_ids": [self.location1.pk]}

        response = self.client.post(self.bulk_url, data=bulk_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("action", response.json())

    def test_bulk_missing_required_fields(self):
        """Test bulk operation with missing required fields."""
        self.client.force_authenticate(user=self.owner)

        # Missing action
        response = self.client.post(self.bulk_url, data={}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bulk_authentication_required(self):
        """Test that bulk operations require authentication."""
        bulk_data = {"action": "delete", "location_ids": [self.location1.pk]}

        response = self.client.post(self.bulk_url, data=bulk_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_bulk_large_operation_performance(self):
        """Test bulk operation performance with many locations."""
        # Create many locations
        locations = []
        for i in range(50):
            location = Location.objects.create(
                name=f"Bulk Performance Location {i}",
                campaign=self.campaign,
                created_by=self.owner,
            )
            locations.append(location)

        self.client.force_authenticate(user=self.owner)

        # Test bulk update
        bulk_data = {
            "action": "update",
            "updates": [
                {"id": loc.pk, "description": f"Updated description {i}"}
                for i, loc in enumerate(locations)
            ],
        }

        response = self.client.post(self.bulk_url, data=bulk_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data["updated"]), 50)
        self.assertEqual(len(data["failed"]), 0)

    def test_bulk_operation_transaction_rollback(self):
        """Test that bulk operations handle transaction rollback properly."""
        # This test would verify that if a bulk operation partially fails
        # due to database constraints, it doesn't leave the database in an
        # inconsistent state. This is implementation-dependent and would
        # require specific scenarios to test properly.
        pass


class LocationBulkResponseFormatTest(BaseLocationAPITestCase):
    """Test bulk operation response formatting."""

    def test_bulk_create_response_format(self):
        """Test that bulk create response has correct format."""
        self.client.force_authenticate(user=self.player1)

        bulk_data = {
            "action": "create",
            "locations": [{"name": "Test Location", "campaign": self.campaign.pk}],
        }

        response = self.client.post(self.bulk_url, data=bulk_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        # Check response structure
        self.assertIn("created", data)
        self.assertIn("failed", data)
        self.assertIn("summary", data)

        # Check created item format
        if data["created"]:
            created_item = data["created"][0]
            self.assertIn("id", created_item)
            self.assertIn("name", created_item)
            self.assertIn("campaign", created_item)

    def test_bulk_update_response_format(self):
        """Test that bulk update response has correct format."""
        self.client.force_authenticate(user=self.owner)

        bulk_data = {
            "action": "update",
            "updates": [{"id": self.location1.pk, "name": "Updated Name"}],
        }

        response = self.client.post(self.bulk_url, data=bulk_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        # Check response structure
        self.assertIn("updated", data)
        self.assertIn("failed", data)
        self.assertIn("summary", data)

    def test_bulk_delete_response_format(self):
        """Test that bulk delete response has correct format."""
        delete_location = Location.objects.create(
            name="Delete Test",
            campaign=self.campaign,
            created_by=self.owner,
        )

        self.client.force_authenticate(user=self.owner)

        bulk_data = {"action": "delete", "location_ids": [delete_location.pk]}

        response = self.client.post(self.bulk_url, data=bulk_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        # Check response structure
        self.assertIn("deleted", data)
        self.assertIn("failed", data)
        self.assertIn("summary", data)

    def test_bulk_failed_items_include_errors(self):
        """Test that failed bulk operations include error details."""
        self.client.force_authenticate(user=self.player1)

        bulk_data = {
            "action": "create",
            "locations": [
                {"name": "", "campaign": self.campaign.pk}  # Invalid: empty name
            ],
        }

        response = self.client.post(self.bulk_url, data=bulk_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data["failed"]), 1)

        failed_item = data["failed"][0]
        self.assertIn("error", failed_item)
        self.assertIn("item_index", failed_item)  # Item index for tracking

    def test_bulk_summary_statistics(self):
        """Test that bulk operations include summary statistics."""
        self.client.force_authenticate(user=self.owner)

        bulk_data = {
            "action": "update",
            "updates": [
                {"id": self.location1.pk, "name": "Updated 1"},
                {"id": 99999, "name": "Invalid ID"},  # Will fail
            ],
        }

        response = self.client.post(self.bulk_url, data=bulk_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        summary = data["summary"]

        self.assertIn("total_requested", summary)
        self.assertIn("successful", summary)
        self.assertIn("failed", summary)
        self.assertEqual(summary["total_requested"], 2)
        self.assertEqual(summary["successful"], 1)
        self.assertEqual(summary["failed"], 1)
