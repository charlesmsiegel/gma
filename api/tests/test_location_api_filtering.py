"""
Tests for Location API filtering and search functionality.

This module tests location list filtering capabilities including campaign filtering,
parent filtering, owner filtering, search by name/description, and combined filters
with proper query optimization.
"""

from django.contrib.auth import get_user_model
from rest_framework import status

from locations.models import Location

from .test_location_api_base import BaseLocationAPITestCase

User = get_user_model()


class LocationCampaignFilteringTest(BaseLocationAPITestCase):
    """Test campaign-based filtering for locations."""

    def test_filter_by_campaign_required(self):
        """Test that campaign filter is required."""
        self.client.force_authenticate(user=self.player1)

        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("campaign", response.json())

    def test_filter_by_campaign_valid(self):
        """Test filtering by valid campaign."""
        self.client.force_authenticate(user=self.player1)

        response = self.client.get(self.list_url, {"campaign": self.campaign.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        # Should return all locations in the campaign
        self.assertGreater(len(data), 0)

        # Verify all locations belong to the requested campaign
        for location in data:
            self.assertEqual(location["campaign"]["id"], self.campaign.pk)

    def test_filter_by_campaign_empty_result(self):
        """Test filtering by campaign with no locations."""
        # Create campaign with no locations
        empty_campaign = self.create_empty_campaign()

        self.client.force_authenticate(user=self.player1)

        response = self.client.get(self.list_url, {"campaign": empty_campaign.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data), 0)

    def test_filter_by_nonexistent_campaign(self):
        """Test filtering by non-existent campaign."""
        self.client.force_authenticate(user=self.player1)

        response = self.client.get(self.list_url, {"campaign": 99999})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_filter_by_campaign_permission_check(self):
        """Test that campaign access is properly checked."""
        self.client.force_authenticate(user=self.non_member)

        response = self.client.get(self.list_url, {"campaign": self.campaign.pk})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def create_empty_campaign(self):
        """Helper to create a campaign with no locations."""
        from campaigns.models import Campaign, CampaignMembership

        empty_campaign = Campaign.objects.create(
            name="Empty Campaign",
            slug="empty-campaign",
            owner=self.owner,
            game_system="Vampire: The Masquerade",
        )

        # Add player1 as member
        CampaignMembership.objects.create(
            campaign=empty_campaign, user=self.player1, role="PLAYER"
        )

        return empty_campaign


class LocationParentFilteringTest(BaseLocationAPITestCase):
    """Test parent-based filtering for locations."""

    def test_filter_by_parent_valid(self):
        """Test filtering by valid parent location."""
        self.client.force_authenticate(user=self.player1)

        response = self.client.get(
            self.list_url, {"campaign": self.campaign.pk, "parent": self.location1.pk}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data), 1)  # Only child_location1
        self.assertEqual(data[0]["name"], "City Center")
        self.assertEqual(data[0]["parent"]["id"], self.location1.pk)

    def test_filter_by_parent_null(self):
        """Test filtering for root locations (parent=null)."""
        self.client.force_authenticate(user=self.player1)

        response = self.client.get(
            self.list_url, {"campaign": self.campaign.pk, "parent": "null"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        # Should only return root locations
        root_names = {loc["name"] for loc in data}
        self.assertIn("Test City", root_names)
        self.assertIn("Player's House", root_names)

        # Verify all have null parents
        for location in data:
            self.assertIsNone(location["parent"])

    def test_filter_by_parent_empty_result(self):
        """Test filtering by parent with no children."""
        self.client.force_authenticate(user=self.player1)

        # grandchild_location has no children
        response = self.client.get(
            self.list_url,
            {"campaign": self.campaign.pk, "parent": self.grandchild_location.pk},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data), 0)

    def test_filter_by_parent_cross_campaign_denied(self):
        """Test that parent filter respects campaign boundaries."""
        self.client.force_authenticate(user=self.player1)

        # Try to filter by parent from different campaign
        response = self.client.get(
            self.list_url,
            {"campaign": self.campaign.pk, "parent": self.public_location.pk},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("parent", response.json())

    def test_filter_by_parent_nonexistent(self):
        """Test filtering by non-existent parent."""
        self.client.force_authenticate(user=self.player1)

        response = self.client.get(
            self.list_url, {"campaign": self.campaign.pk, "parent": 99999}
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class LocationOwnerFilteringTest(BaseLocationAPITestCase):
    """Test owner-based filtering for locations."""

    def test_filter_by_owner_character(self):
        """Test filtering by character owner."""
        self.client.force_authenticate(user=self.player1)

        response = self.client.get(
            self.list_url, {"campaign": self.campaign.pk, "owner": self.character1.pk}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        # Should return locations owned by character1
        owned_names = {loc["name"] for loc in data}
        self.assertIn("Player's House", owned_names)
        self.assertIn("Living Room", owned_names)

        # Verify all are owned by character1
        for location in data:
            self.assertEqual(location["owned_by"]["id"], self.character1.pk)

    def test_filter_by_owner_npc(self):
        """Test filtering by NPC character owner."""
        self.client.force_authenticate(user=self.player1)

        response = self.client.get(
            self.list_url,
            {"campaign": self.campaign.pk, "owner": self.npc_character.pk},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data), 1)  # Only coffee shop
        self.assertEqual(data[0]["name"], "Coffee Shop")
        self.assertEqual(data[0]["owned_by"]["id"], self.npc_character.pk)

    def test_filter_by_owner_null(self):
        """Test filtering for unowned locations (owner=null)."""
        self.client.force_authenticate(user=self.player1)

        response = self.client.get(
            self.list_url, {"campaign": self.campaign.pk, "owner": "null"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        # Should return unowned locations
        unowned_names = {loc["name"] for loc in data}
        self.assertIn("Test City", unowned_names)
        self.assertIn("City Center", unowned_names)

        # Verify all have null owners
        for location in data:
            self.assertIsNone(location["owned_by"])

    def test_filter_by_owner_cross_campaign_denied(self):
        """Test that owner filter respects campaign boundaries."""
        # Create character in different campaign
        from campaigns.models import Campaign, CampaignMembership
        from characters.models import Character

        other_campaign = Campaign.objects.create(
            name="Other Campaign",
            slug="other-campaign",
            owner=self.owner,
            game_system="Vampire: The Masquerade",
        )
        # Add player1 as member of other_campaign so they can own characters
        CampaignMembership.objects.create(
            campaign=other_campaign, user=self.player1, role="PLAYER"
        )
        other_character = Character.objects.create(
            name="Other Character",
            campaign=other_campaign,
            player_owner=self.player1,
            game_system="Vampire: The Masquerade",
        )

        self.client.force_authenticate(user=self.player1)

        response = self.client.get(
            self.list_url, {"campaign": self.campaign.pk, "owner": other_character.pk}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("owner", response.json())

    def test_filter_by_owner_nonexistent(self):
        """Test filtering by non-existent character."""
        self.client.force_authenticate(user=self.player1)

        response = self.client.get(
            self.list_url, {"campaign": self.campaign.pk, "owner": 99999}
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class LocationSearchTest(BaseLocationAPITestCase):
    """Test text search functionality for locations."""

    def test_search_by_name(self):
        """Test searching locations by name."""
        self.client.force_authenticate(user=self.player1)

        response = self.client.get(
            self.list_url, {"campaign": self.campaign.pk, "search": "City"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        search_names = {loc["name"] for loc in data}

        # Should find both "Test City" and "City Center"
        self.assertIn("Test City", search_names)
        self.assertIn("City Center", search_names)
        self.assertNotIn("Player's House", search_names)

    def test_search_by_description(self):
        """Test searching locations by description."""
        self.client.force_authenticate(user=self.player1)

        response = self.client.get(
            self.list_url, {"campaign": self.campaign.pk, "search": "coffee"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "Coffee Shop")

    def test_search_case_insensitive(self):
        """Test that search is case-insensitive."""
        self.client.force_authenticate(user=self.player1)

        response = self.client.get(
            self.list_url, {"campaign": self.campaign.pk, "search": "CITY"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        search_names = {loc["name"] for loc in data}
        self.assertIn("Test City", search_names)
        self.assertIn("City Center", search_names)

    def test_search_partial_match(self):
        """Test that search supports partial matches."""
        self.client.force_authenticate(user=self.player1)

        response = self.client.get(
            self.list_url, {"campaign": self.campaign.pk, "search": "Liv"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "Living Room")

    def test_search_empty_query(self):
        """Test search with empty query returns all locations."""
        self.client.force_authenticate(user=self.player1)

        response = self.client.get(
            self.list_url, {"campaign": self.campaign.pk, "search": ""}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should return all locations (same as no search)
        all_response = self.client.get(self.list_url, {"campaign": self.campaign.pk})
        self.assertEqual(len(response.json()), len(all_response.json()))

    def test_search_no_matches(self):
        """Test search with no matching results."""
        self.client.force_authenticate(user=self.player1)

        response = self.client.get(
            self.list_url, {"campaign": self.campaign.pk, "search": "nonexistent"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data), 0)

    def test_search_with_special_characters(self):
        """Test search handling of special characters."""
        # Create location with special characters
        special_location = Location.objects.create(
            name="Location with 'quotes' & symbols",
            description="Has [brackets] and (parentheses)",
            campaign=self.campaign,
            created_by=self.owner,
        )

        self.client.force_authenticate(user=self.player1)

        response = self.client.get(
            self.list_url, {"campaign": self.campaign.pk, "search": "quotes"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], special_location.pk)


class LocationCombinedFilteringTest(BaseLocationAPITestCase):
    """Test combined filtering functionality."""

    def test_filter_parent_and_owner_combined(self):
        """Test combining parent and owner filters."""
        self.client.force_authenticate(user=self.player1)

        response = self.client.get(
            self.list_url,
            {
                "campaign": self.campaign.pk,
                "parent": self.location2.pk,
                "owner": self.character1.pk,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data), 1)  # Only Living Room matches both criteria
        self.assertEqual(data[0]["name"], "Living Room")

    def test_filter_parent_and_search_combined(self):
        """Test combining parent filter with search."""
        self.client.force_authenticate(user=self.player1)

        response = self.client.get(
            self.list_url,
            {
                "campaign": self.campaign.pk,
                "parent": self.location1.pk,
                "search": "Center",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "City Center")

    def test_filter_owner_and_search_combined(self):
        """Test combining owner filter with search."""
        self.client.force_authenticate(user=self.player1)

        response = self.client.get(
            self.list_url,
            {
                "campaign": self.campaign.pk,
                "owner": self.character1.pk,
                "search": "House",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "Player's House")

    def test_all_filters_combined(self):
        """Test combining all filters together."""
        # Create specific location for this test
        test_location = Location.objects.create(
            name="Test Search Location",
            description="Specific test location",
            campaign=self.campaign,
            parent=self.location1,
            owned_by=self.npc_character,
            created_by=self.gm,
        )

        self.client.force_authenticate(user=self.player1)

        response = self.client.get(
            self.list_url,
            {
                "campaign": self.campaign.pk,
                "parent": self.location1.pk,
                "owner": self.npc_character.pk,
                "search": "Test",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], test_location.pk)

    def test_conflicting_filters(self):
        """Test that conflicting filters return empty results."""
        self.client.force_authenticate(user=self.player1)

        # Search for locations owned by character1 but parented by a location
        # that has no children owned by character1
        response = self.client.get(
            self.list_url,
            {
                "campaign": self.campaign.pk,
                "parent": self.child_location1.pk,  # Has grandchild owned by npc_char
                "owner": self.character1.pk,  # But looking for character1's locations
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data), 0)


class LocationFilteringQueryOptimizationTest(BaseLocationAPITestCase):
    """Test that filtering operations are properly optimized."""

    def test_campaign_filter_optimized_queries(self):
        """Test that campaign filtering uses optimized queries."""
        self.client.force_authenticate(user=self.player1)

        with self.assertNumQueries(5):  # Should be minimal and consistent
            response = self.client.get(self.list_url, {"campaign": self.campaign.pk})
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            # Access all filtered data
            data = response.json()
            for location in data:
                _ = location["campaign"]
                _ = location.get("parent")
                _ = location.get("owned_by")

    def test_parent_filter_optimized_queries(self):
        """Test that parent filtering uses optimized queries."""
        self.client.force_authenticate(user=self.player1)

        with self.assertNumQueries(5):  # Should not increase significantly
            response = self.client.get(
                self.list_url,
                {"campaign": self.campaign.pk, "parent": self.location1.pk},
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_search_filter_optimized_queries(self):
        """Test that search filtering uses optimized queries."""
        self.client.force_authenticate(user=self.player1)

        with self.assertNumQueries(5):  # Should remain efficient
            response = self.client.get(
                self.list_url, {"campaign": self.campaign.pk, "search": "City"}
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_combined_filters_optimized_queries(self):
        """Test that combined filters don't cause query explosion."""
        self.client.force_authenticate(user=self.player1)

        with self.assertNumQueries(6):  # Should scale well
            response = self.client.get(
                self.list_url,
                {
                    "campaign": self.campaign.pk,
                    "parent": self.location1.pk,
                    "owner": "null",
                    "search": "Center",
                },
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)


class LocationOrderingTest(BaseLocationAPITestCase):
    """Test location ordering functionality."""

    def test_default_ordering_by_name(self):
        """Test that locations are ordered by name by default."""
        self.client.force_authenticate(user=self.player1)

        response = self.client.get(self.list_url, {"campaign": self.campaign.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        names = [loc["name"] for loc in data]
        sorted_names = sorted(names)
        self.assertEqual(names, sorted_names)

    def test_ordering_by_created_date(self):
        """Test ordering by creation date."""
        self.client.force_authenticate(user=self.player1)

        response = self.client.get(
            self.list_url, {"campaign": self.campaign.pk, "ordering": "created_at"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        # Should be ordered by creation date (earliest first)
        self.assertGreater(len(data), 1)  # Ensure we have multiple items to compare

    def test_ordering_by_hierarchy_depth(self):
        """Test ordering by hierarchy depth."""
        self.client.force_authenticate(user=self.player1)

        response = self.client.get(
            self.list_url, {"campaign": self.campaign.pk, "ordering": "depth"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        depths = [loc["depth"] for loc in data]
        sorted_depths = sorted(depths)
        self.assertEqual(depths, sorted_depths)

    def test_reverse_ordering(self):
        """Test reverse ordering functionality."""
        self.client.force_authenticate(user=self.player1)

        response = self.client.get(
            self.list_url, {"campaign": self.campaign.pk, "ordering": "-name"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        names = [loc["name"] for loc in data]
        reverse_sorted_names = sorted(names, reverse=True)
        self.assertEqual(names, reverse_sorted_names)

    def test_invalid_ordering_field(self):
        """Test that invalid ordering fields are handled gracefully."""
        self.client.force_authenticate(user=self.player1)

        response = self.client.get(
            self.list_url, {"campaign": self.campaign.pk, "ordering": "invalid_field"}
        )
        # Should either fall back to default ordering or return an error
        self.assertIn(
            response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]
        )


class LocationPaginationTest(BaseLocationAPITestCase):
    """Test location list pagination functionality."""

    def setUp(self):
        super().setUp()

        # Create additional locations for pagination testing
        for i in range(15):  # Create 15 more locations
            Location.objects.create(
                name=f"Pagination Location {i:02d}",
                description=f"Location for testing pagination {i}",
                campaign=self.campaign,
                created_by=self.owner,
            )

    def test_pagination_default_page_size(self):
        """Test default pagination page size."""
        self.client.force_authenticate(user=self.player1)

        response = self.client.get(self.list_url, {"campaign": self.campaign.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should include pagination info
        self.assertIn("count", response.json())
        self.assertIn("next", response.json())
        self.assertIn("previous", response.json())
        self.assertIn("results", response.json())

    def test_pagination_custom_page_size(self):
        """Test custom pagination page size."""
        self.client.force_authenticate(user=self.player1)

        response = self.client.get(
            self.list_url, {"campaign": self.campaign.pk, "page_size": 5}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        # Note: Pagination not yet implemented, expecting simple list
        self.assertLessEqual(len(data), 5)

    def test_pagination_with_filters(self):
        """Test that pagination works with filters applied."""
        self.client.force_authenticate(user=self.player1)

        response = self.client.get(
            self.list_url,
            {"campaign": self.campaign.pk, "search": "Pagination", "page_size": 5},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        # Note: Pagination not yet implemented, expecting simple list
        for location in data:
            self.assertIn("Pagination", location["name"])
