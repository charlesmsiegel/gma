"""
Tests for Location API hierarchy-specific functionality.

This module tests location hierarchy operations including validation of
circular references, depth limits, hierarchy serialization, and tree
traversal functionality through the API.
"""

from django.contrib.auth import get_user_model
from rest_framework import status

from locations.models import Location

from .test_location_api_base import BaseLocationAPITestCase

User = get_user_model()


class LocationHierarchyValidationTest(BaseLocationAPITestCase):
    """Test location hierarchy validation through the API."""

    def test_create_prevents_circular_reference(self):
        """Test that creating a location prevents circular references."""
        self.client.force_authenticate(user=self.owner)

        # Try to make location1 a child of its own descendant
        location_data = {
            "name": "Circular Test",
            "campaign": self.campaign.pk,
            "parent": self.grandchild_location.pk,  # This would create a circle
        }

        response = self.client.post(self.list_url, data=location_data)
        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED
        )  # Creation succeeds

        # Now try to update grandchild_location to have location1 as parent (circular)
        created_location = Location.objects.get(name="Circular Test")
        detail_url = self.get_detail_url(self.grandchild_location.pk)

        update_data = {
            "name": "Coffee Shop",
            "parent": created_location.pk,
        }

        response = self.client.put(detail_url, data=update_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("parent", response.json())

    def test_update_prevents_self_parent(self):
        """Test that updating a location prevents it from being its own parent."""
        self.client.force_authenticate(user=self.owner)

        update_data = {
            "name": "Test City",
            "parent": self.location1.pk,  # Self as parent
        }

        response = self.client.put(self.detail_url1, data=update_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("parent", response.json())

    def test_create_validates_maximum_depth(self):
        """Test that location creation validates maximum depth."""
        self.client.force_authenticate(user=self.owner)

        # Create a deep hierarchy (9 levels deep)
        current_parent = self.location1
        for i in range(8):  # This will create locations at depth 1-8
            location = Location.objects.create(
                name=f"Deep Level {i+1}",
                campaign=self.campaign,
                parent=current_parent,
                created_by=self.owner,
            )
            current_parent = location

        # Now try to create one more level (would be depth 9, which is allowed)
        location_data = {
            "name": "Depth 9 Location",
            "campaign": self.campaign.pk,
            "parent": current_parent.pk,
        }

        response = self.client.post(self.list_url, data=location_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Create another location that would exceed max depth (depth 10)
        created_location = Location.objects.get(name="Depth 9 Location")
        location_data = {
            "name": "Too Deep Location",
            "campaign": self.campaign.pk,
            "parent": created_location.pk,
        }

        response = self.client.post(self.list_url, data=location_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("parent", response.json())

    def test_update_validates_cross_campaign_parent(self):
        """Test that updating parent validates same campaign constraint."""
        self.client.force_authenticate(user=self.owner)

        # Try to set parent from different campaign
        update_data = {
            "name": "Test City",
            "parent": self.public_location.pk,  # Different campaign
        }

        response = self.client.put(self.detail_url1, data=update_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("parent", response.json())


class LocationHierarchySerializationTest(BaseLocationAPITestCase):
    """Test location hierarchy information in API responses."""

    def test_detail_includes_full_hierarchy_path(self):
        """Test that detail view includes full hierarchy path."""
        self.client.force_authenticate(user=self.player1)

        # Get detail of grandchild location
        detail_url = self.get_detail_url(self.grandchild_location.pk)
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        # Should include hierarchy path
        self.assertIn("hierarchy_path", data)
        expected_path = (
            f"{self.location1.name} > {self.child_location1.name} > "
            f"{self.grandchild_location.name}"
        )
        self.assertEqual(data["hierarchy_path"], expected_path)

    def test_detail_includes_depth_information(self):
        """Test that detail view includes depth information."""
        self.client.force_authenticate(user=self.player1)

        # Root location (depth 0)
        response = self.client.get(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["depth"], 0)

        # Child location (depth 1)
        child_detail_url = self.get_detail_url(self.child_location1.pk)
        response = self.client.get(child_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["depth"], 1)

        # Grandchild location (depth 2)
        grandchild_detail_url = self.get_detail_url(self.grandchild_location.pk)
        response = self.client.get(grandchild_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["depth"], 2)

    def test_detail_includes_ancestor_information(self):
        """Test that detail view includes ancestor information."""
        self.client.force_authenticate(user=self.player1)

        # Grandchild should include ancestors
        detail_url = self.get_detail_url(self.grandchild_location.pk)
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIn("ancestors", data)
        self.assertEqual(len(data["ancestors"]), 2)  # parent and grandparent

        # Verify order (should be from immediate parent to root)
        self.assertEqual(data["ancestors"][0]["id"], self.child_location1.pk)
        self.assertEqual(data["ancestors"][1]["id"], self.location1.pk)

    def test_detail_includes_children_information(self):
        """Test that detail view includes children information."""
        self.client.force_authenticate(user=self.player1)

        # Parent location should include children
        response = self.client.get(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIn("children", data)
        self.assertEqual(len(data["children"]), 1)
        self.assertEqual(data["children"][0]["id"], self.child_location1.pk)

    def test_detail_includes_siblings_information(self):
        """Test that detail view includes siblings information."""
        # Create a sibling for child_location1
        sibling = Location.objects.create(
            name="Sibling Location",
            campaign=self.campaign,
            parent=self.location1,  # Same parent as child_location1
            created_by=self.owner,
        )

        self.client.force_authenticate(user=self.player1)

        child_detail_url = self.get_detail_url(self.child_location1.pk)
        response = self.client.get(child_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIn("siblings", data)
        self.assertEqual(len(data["siblings"]), 1)
        self.assertEqual(data["siblings"][0]["id"], sibling.pk)

    def test_list_includes_hierarchy_indicators(self):
        """Test that list view includes hierarchy indicators."""
        self.client.force_authenticate(user=self.player1)

        response = self.client.get(self.list_url, {"campaign": self.campaign.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        results = data.get("results", data)  # Handle both paginated and non-paginated

        # Find locations and check hierarchy indicators
        locations_by_name = {loc["name"]: loc for loc in results}

        # Root location should have no parent and have children
        root_loc = locations_by_name["Test City"]
        self.assertIsNone(root_loc["parent"])
        self.assertGreater(root_loc["children_count"], 0)

        # Child location should have parent and children
        child_loc = locations_by_name["City Center"]
        self.assertEqual(child_loc["parent"]["id"], self.location1.pk)
        self.assertGreater(child_loc["children_count"], 0)

        # Leaf location should have parent but no children
        leaf_loc = locations_by_name["Coffee Shop"]
        self.assertEqual(leaf_loc["parent"]["id"], self.child_location1.pk)
        self.assertEqual(leaf_loc["children_count"], 0)


class LocationHierarchyTreeOperationsTest(BaseLocationAPITestCase):
    """Test location hierarchy tree operations through API endpoints."""

    def test_get_descendants_endpoint(self):
        """Test getting all descendants of a location."""
        self.client.force_authenticate(user=self.player1)

        descendants_url = f"{self.detail_url1}descendants/"
        response = self.client.get(descendants_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        # Should include child_location1 and grandchild_location
        descendant_names = {loc["name"] for loc in data}
        self.assertIn("City Center", descendant_names)
        self.assertIn("Coffee Shop", descendant_names)
        self.assertEqual(len(data), 2)

    def test_get_ancestors_endpoint(self):
        """Test getting all ancestors of a location."""
        self.client.force_authenticate(user=self.player1)

        ancestors_url = f"{self.get_detail_url(self.grandchild_location.pk)}ancestors/"
        response = self.client.get(ancestors_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        # Should include child_location1 and location1 in order
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["id"], self.child_location1.pk)
        self.assertEqual(data[1]["id"], self.location1.pk)

    def test_get_siblings_endpoint(self):
        """Test getting siblings of a location."""
        # Create a sibling
        sibling = Location.objects.create(
            name="Sibling Location",
            campaign=self.campaign,
            parent=self.location1,
            created_by=self.owner,
        )

        self.client.force_authenticate(user=self.player1)

        siblings_url = f"{self.get_detail_url(self.child_location1.pk)}siblings/"
        response = self.client.get(siblings_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], sibling.pk)

    def test_get_path_from_root_endpoint(self):
        """Test getting the path from root to a location."""
        self.client.force_authenticate(user=self.player1)

        path_url = f"{self.get_detail_url(self.grandchild_location.pk)}path/"
        response = self.client.get(path_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        # Should include the full path from root to location
        self.assertEqual(len(data), 3)
        self.assertEqual(data[0]["id"], self.location1.pk)
        self.assertEqual(data[1]["id"], self.child_location1.pk)
        self.assertEqual(data[2]["id"], self.grandchild_location.pk)

    def test_move_location_endpoint(self):
        """Test moving a location to a different parent."""
        self.client.force_authenticate(user=self.owner)

        # Move grandchild_location to be a direct child of location1
        move_url = f"{self.get_detail_url(self.grandchild_location.pk)}move/"
        move_data = {"new_parent": self.location1.pk}

        response = self.client.post(move_url, data=move_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify the move
        self.grandchild_location.refresh_from_db()
        self.assertEqual(self.grandchild_location.parent, self.location1)

    def test_move_location_validates_circular_reference(self):
        """Test that move operation validates circular references."""
        self.client.force_authenticate(user=self.owner)

        # Try to move parent under its own child
        move_url = f"{self.detail_url1}move/"
        move_data = {"new_parent": self.child_location1.pk}

        response = self.client.post(move_url, data=move_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("new_parent", response.json())

    def test_move_location_validates_same_campaign(self):
        """Test that move operation validates same campaign constraint."""
        self.client.force_authenticate(user=self.owner)

        move_url = f"{self.detail_url1}move/"
        move_data = {"new_parent": self.public_location.pk}

        response = self.client.post(move_url, data=move_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("new_parent", response.json())

    def test_move_location_permission_check(self):
        """Test that move operation requires appropriate permissions."""
        self.client.force_authenticate(user=self.player2)

        # Try to move a location not owned by player2
        move_url = f"{self.detail_url1}move/"
        move_data = {}  # Move to root (omit new_parent)

        response = self.client.post(move_url, data=move_data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class LocationHierarchyDeletionHandlingTest(BaseLocationAPITestCase):
    """Test location hierarchy handling during deletion operations."""

    def test_delete_parent_promotes_children_to_grandparent(self):
        """Test that deleting a parent promotes children to grandparent."""
        self.client.force_authenticate(user=self.gm)

        # Delete the middle level (child_location1)
        detail_url = self.get_detail_url(self.child_location1.pk)
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify grandchild is promoted to child of original grandparent
        self.grandchild_location.refresh_from_db()
        self.assertEqual(self.grandchild_location.parent, self.location1)

        # Verify through API
        self.client.force_authenticate(user=self.player1)
        grandchild_detail_url = self.get_detail_url(self.grandchild_location.pk)
        response = self.client.get(grandchild_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data["parent"]["id"], self.location1.pk)
        self.assertEqual(data["depth"], 1)  # Reduced from depth 2 to depth 1

    def test_delete_root_makes_children_roots(self):
        """Test that deleting a root location makes its children root locations."""
        self.client.force_authenticate(user=self.owner)

        # Delete the root location
        response = self.client.delete(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify child becomes root and grandchild is promoted
        self.child_location1.refresh_from_db()
        self.grandchild_location.refresh_from_db()

        self.assertIsNone(self.child_location1.parent)  # Now a root
        self.assertEqual(self.grandchild_location.parent, self.child_location1)

        # Verify through API
        self.client.force_authenticate(user=self.player1)
        child_detail_url = self.get_detail_url(self.child_location1.pk)
        response = self.client.get(child_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIsNone(data["parent"])
        self.assertEqual(data["depth"], 0)  # Now root level

    def test_bulk_delete_handles_hierarchy_correctly(self):
        """Test that bulk delete operations handle hierarchy correctly."""
        self.client.force_authenticate(user=self.owner)

        # Bulk delete multiple locations in hierarchy
        bulk_data = {
            "action": "delete",
            "location_ids": [self.location1.pk, self.child_location1.pk],
        }

        response = self.client.post(self.bulk_url, data=bulk_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify both locations are deleted
        self.assertFalse(Location.objects.filter(pk=self.location1.pk).exists())
        self.assertFalse(Location.objects.filter(pk=self.child_location1.pk).exists())

        # Verify grandchild still exists as root
        self.assertTrue(
            Location.objects.filter(pk=self.grandchild_location.pk).exists()
        )
        self.grandchild_location.refresh_from_db()
        self.assertIsNone(self.grandchild_location.parent)


class LocationHierarchyPerformanceTest(BaseLocationAPITestCase):
    """Test location hierarchy operations performance and query optimization."""

    def test_list_optimizes_queries_for_hierarchy(self):
        """Test that list endpoint optimizes queries for hierarchy information."""
        self.client.force_authenticate(user=self.player1)

        with self.assertNumQueries(6):  # Includes pagination count query
            response = self.client.get(self.list_url, {"campaign": self.campaign.pk})
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            # Access hierarchy data to ensure it's properly prefetched
            data = response.json()
            results = data.get(
                "results", data
            )  # Handle both paginated and non-paginated
            for location in results:
                # These should not trigger additional queries
                _ = location.get("parent")
                _ = location.get("children_count")

    def test_detail_optimizes_queries_for_full_hierarchy(self):
        """Test that detail endpoint optimizes queries for full hierarchy data."""
        self.client.force_authenticate(user=self.player1)

        with self.assertNumQueries(6):  # Optimized for all hierarchy operations
            detail_url = self.get_detail_url(self.grandchild_location.pk)
            response = self.client.get(detail_url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            # Access all hierarchy data to ensure proper prefetching
            data = response.json()
            _ = data.get("parent")
            _ = data.get("children")
            _ = data.get("ancestors")
            _ = data.get("siblings")
            _ = data.get("hierarchy_path")

    def test_descendants_endpoint_handles_deep_hierarchy(self):
        """Test that descendants endpoint handles deep hierarchies efficiently."""
        # Create a deeper hierarchy
        current_parent = self.grandchild_location
        for i in range(5):  # Add 5 more levels
            location = Location.objects.create(
                name=f"Deep Level {i+1}",
                campaign=self.campaign,
                parent=current_parent,
                created_by=self.owner,
            )
            current_parent = location

        self.client.force_authenticate(user=self.player1)

        descendants_url = f"{self.detail_url1}descendants/"
        response = self.client.get(descendants_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        # Should return all descendants (original 2 + new 5 = 7 total)
        self.assertEqual(len(data), 7)
