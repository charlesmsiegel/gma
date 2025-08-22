"""
Tests for Location API CRUD operations.

This module tests the location create, list, detail, update, and delete endpoint
functionality including authentication, permission checks, validation, and ownership.
"""

from django.contrib.auth import get_user_model
from rest_framework import status

from campaigns.models import Campaign
from characters.models import Character
from locations.models import Location

from .test_location_api_base import BaseLocationAPITestCase

User = get_user_model()


class LocationListAPITest(BaseLocationAPITestCase):
    """Test Location list API endpoint."""

    def test_list_requires_campaign_filter(self):
        """Test that location listing requires campaign filter."""
        self.client.force_authenticate(user=self.player1)

        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("campaign", response.json())

    def test_list_authenticated_campaign_member(self):
        """Test location listing as authenticated campaign member."""
        self.client.force_authenticate(user=self.player1)

        response = self.client.get(self.list_url, {"campaign": self.campaign.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertGreater(len(data), 0)

        # Verify all locations belong to the requested campaign
        for location_data in data:
            self.assertEqual(location_data["campaign"]["id"], self.campaign.pk)

    def test_list_anonymous_public_campaign(self):
        """Test that anonymous users can view locations in public campaigns."""
        response = self.client.get(self.list_url, {"campaign": self.public_campaign.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data), 1)  # Only public_location
        self.assertEqual(data[0]["name"], "Public Location")

    def test_list_anonymous_private_campaign_denied(self):
        """Test that anonymous users cannot view locations in private campaigns."""
        response = self.client.get(self.list_url, {"campaign": self.campaign.pk})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_non_member_private_campaign_denied(self):
        """Test that non-members cannot view locations in private campaigns."""
        self.client.force_authenticate(user=self.non_member)

        response = self.client.get(self.list_url, {"campaign": self.campaign.pk})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_includes_hierarchy_info(self):
        """Test that location listing includes parent/children hierarchy info."""
        self.client.force_authenticate(user=self.player1)

        response = self.client.get(self.list_url, {"campaign": self.campaign.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        # Find root location
        root_location = next((loc for loc in data if loc["name"] == "Test City"), None)
        self.assertIsNotNone(root_location)

        # Should have parent info (null for root)
        self.assertIsNone(root_location["parent"])

        # Should indicate it has children
        self.assertIn("children_count", root_location)
        self.assertGreater(root_location["children_count"], 0)

    def test_list_includes_ownership_info(self):
        """Test that location listing includes ownership information."""
        self.client.force_authenticate(user=self.player1)

        response = self.client.get(self.list_url, {"campaign": self.campaign.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        # Find owned location
        owned_location = next(
            (loc for loc in data if loc["name"] == "Player's House"), None
        )
        self.assertIsNotNone(owned_location)
        self.assertLocationOwnership(owned_location, self.character1.pk)


class LocationCreateAPITest(BaseLocationAPITestCase):
    """Test Location create API endpoint."""

    def test_create_requires_authentication(self):
        """Test that location creation requires authentication."""
        location_data = {
            "name": "Test Location",
            "campaign": self.campaign.pk,
        }

        response = self.client.post(self.list_url, data=location_data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_location_as_player(self):
        """Test location creation as a player."""
        self.client.force_authenticate(user=self.player1)

        location_data = {
            "name": "New Player Location",
            "description": "A new location created via API",
            "campaign": self.campaign.pk,
        }

        response = self.client.post(self.list_url, data=location_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.json()
        self.assertEqual(data["name"], "New Player Location")
        self.assertEqual(data["campaign"]["id"], self.campaign.pk)
        self.assertEqual(data["created_by"]["id"], self.player1.pk)

        # Verify location was created in database
        location = Location.objects.get(name="New Player Location")
        self.assertEqual(location.created_by, self.player1)
        self.assertEqual(location.campaign, self.campaign)

    def test_create_location_as_gm(self):
        """Test location creation as a GM."""
        self.client.force_authenticate(user=self.gm)

        location_data = {
            "name": "GM Location",
            "description": "A location created by GM",
            "campaign": self.campaign.pk,
        }

        response = self.client.post(self.list_url, data=location_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.json()
        self.assertEqual(data["created_by"]["id"], self.gm.pk)

    def test_create_location_as_owner(self):
        """Test location creation as campaign owner."""
        self.client.force_authenticate(user=self.owner)

        location_data = {
            "name": "Owner Location",
            "campaign": self.campaign.pk,
        }

        response = self.client.post(self.list_url, data=location_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_location_observer_denied(self):
        """Test that observers cannot create locations."""
        self.client.force_authenticate(user=self.observer)

        location_data = {
            "name": "Observer Location",
            "campaign": self.campaign.pk,
        }

        response = self.client.post(self.list_url, data=location_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_location_non_member_denied(self):
        """Test that non-members cannot create locations."""
        self.client.force_authenticate(user=self.non_member)

        location_data = {
            "name": "Non-member Location",
            "campaign": self.campaign.pk,
        }

        response = self.client.post(self.list_url, data=location_data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_location_validates_required_fields(self):
        """Test validation of required fields."""
        self.client.force_authenticate(user=self.player1)

        # Missing name
        response = self.client.post(self.list_url, data={"campaign": self.campaign.pk})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.json())

        # Missing campaign
        response = self.client.post(self.list_url, data={"name": "Test Location"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("campaign", response.json())

    def test_create_location_with_parent(self):
        """Test creating a location with a parent."""
        self.client.force_authenticate(user=self.player1)

        location_data = {
            "name": "Child Location",
            "description": "A child of an existing location",
            "campaign": self.campaign.pk,
            "parent": self.location1.pk,
        }

        response = self.client.post(self.list_url, data=location_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.json()
        self.assertLocationHierarchy(data, expected_parent_id=self.location1.pk)

    def test_create_location_with_character_owner(self):
        """Test creating a location owned by a character."""
        self.client.force_authenticate(user=self.player1)

        location_data = {
            "name": "Character Owned Location",
            "campaign": self.campaign.pk,
            "owned_by": self.character1.pk,
        }

        response = self.client.post(self.list_url, data=location_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.json()
        self.assertLocationOwnership(data, expected_owner_id=self.character1.pk)

    def test_create_location_validates_owner_in_same_campaign(self):
        """Test that character owner must be in the same campaign."""
        from campaigns.models import CampaignMembership

        # Create character in different campaign
        other_campaign = Campaign.objects.create(
            name="Other Campaign",
            slug="other-campaign",
            owner=self.owner,
            game_system="Vampire: The Masquerade",
        )
        # Add player to other campaign so they can create characters there
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

        location_data = {
            "name": "Invalid Owner Location",
            "campaign": self.campaign.pk,
            "owned_by": other_character.pk,
        }

        response = self.client.post(self.list_url, data=location_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("owned_by", response.json())

    def test_create_location_validates_parent_in_same_campaign(self):
        """Test that parent location must be in the same campaign."""
        self.client.force_authenticate(user=self.player1)

        location_data = {
            "name": "Invalid Parent Location",
            "campaign": self.campaign.pk,
            "parent": self.public_location.pk,  # Different campaign
        }

        response = self.client.post(self.list_url, data=location_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("parent", response.json())


class LocationDetailAPITest(BaseLocationAPITestCase):
    """Test Location detail API endpoint."""

    def test_detail_requires_authentication_private_campaign(self):
        """Test that location detail requires authentication for private campaigns."""
        response = self.client.get(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_detail_anonymous_public_campaign(self):
        """Test that anonymous users can view locations in public campaigns."""
        public_detail_url = self.get_detail_url(self.public_location.pk)
        response = self.client.get(public_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data["name"], "Public Location")

    def test_detail_location_as_campaign_member(self):
        """Test location detail access as campaign member."""
        self.client.force_authenticate(user=self.player1)

        response = self.client.get(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data["id"], self.location1.pk)
        self.assertEqual(data["name"], "Test City")

    def test_detail_location_as_gm(self):
        """Test location detail access as GM."""
        self.client.force_authenticate(user=self.gm)

        response = self.client.get(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_detail_location_as_campaign_owner(self):
        """Test location detail access as campaign owner."""
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_detail_location_as_observer(self):
        """Test location detail access as observer."""
        self.client.force_authenticate(user=self.observer)

        response = self.client.get(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_detail_location_non_member_denied(self):
        """Test that non-members cannot view locations in private campaigns."""
        self.client.force_authenticate(user=self.non_member)

        response = self.client.get(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_detail_includes_hierarchy_info(self):
        """Test that location detail includes complete hierarchy information."""
        self.client.force_authenticate(user=self.player1)

        # Test parent location
        response = self.client.get(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertLocationHierarchy(
            data, expected_parent_id=None, expected_children_count=1
        )

        # Test child location
        child_detail_url = self.get_detail_url(self.child_location1.pk)
        response = self.client.get(child_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertLocationHierarchy(
            data, expected_parent_id=self.location1.pk, expected_children_count=1
        )

    def test_detail_includes_ownership_info(self):
        """Test that location detail includes ownership information."""
        self.client.force_authenticate(user=self.player1)

        response = self.client.get(self.detail_url2)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertLocationOwnership(data, expected_owner_id=self.character1.pk)


class LocationUpdateAPITest(BaseLocationAPITestCase):
    """Test Location update API endpoint."""

    def test_update_requires_authentication(self):
        """Test that location update requires authentication."""
        update_data = {"name": "Updated Name"}

        response = self.client.put(self.detail_url1, data=update_data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_location_as_owner(self):
        """Test location update as campaign owner."""
        self.client.force_authenticate(user=self.owner)

        update_data = {
            "name": "Updated Test City",
            "description": "Updated description",
        }

        response = self.client.put(self.detail_url1, data=update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data["name"], "Updated Test City")
        self.assertEqual(data["description"], "Updated description")

        # Verify in database
        self.location1.refresh_from_db()
        self.assertEqual(self.location1.name, "Updated Test City")

    def test_update_location_as_gm(self):
        """Test location update as GM."""
        self.client.force_authenticate(user=self.gm)

        update_data = {"name": "GM Updated Location"}

        response = self.client.put(self.detail_url1, data=update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_owned_location_as_character_owner(self):
        """Test updating character-owned location as character's owner."""
        self.client.force_authenticate(user=self.player1)

        update_data = {"name": "Updated Player House"}

        response = self.client.put(self.detail_url2, data=update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_owned_location_as_other_player_denied(self):
        """Test that other players cannot update character-owned locations."""
        self.client.force_authenticate(user=self.player2)

        update_data = {"name": "Unauthorized Update"}

        response = self.client.put(self.detail_url2, data=update_data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_created_location_as_creator(self):
        """Test updating unowned location as its creator."""
        self.client.force_authenticate(user=self.owner)

        update_data = {"name": "Updated by Creator"}

        response = self.client.put(self.detail_url1, data=update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_observer_denied(self):
        """Test that observers cannot update locations."""
        self.client.force_authenticate(user=self.observer)

        update_data = {"name": "Observer Update"}

        response = self.client.put(self.detail_url1, data=update_data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_readonly_fields_ignored(self):
        """Test that read-only fields are ignored in updates."""
        self.client.force_authenticate(user=self.owner)

        original_campaign = self.location1.campaign
        original_creator = self.location1.created_by

        update_data = {
            "name": "Updated Name",
            "campaign": self.public_campaign.pk,  # Try to change campaign
            "created_by": self.player1.pk,  # Try to change creator
        }

        response = self.client.put(self.detail_url1, data=update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify readonly fields weren't changed
        self.location1.refresh_from_db()
        self.assertEqual(self.location1.campaign, original_campaign)
        self.assertEqual(self.location1.created_by, original_creator)
        self.assertEqual(self.location1.name, "Updated Name")  # But this changed

    def test_update_validates_hierarchy_constraints(self):
        """Test that hierarchy constraints are validated on update."""
        self.client.force_authenticate(user=self.owner)

        # Try to create circular reference
        update_data = {
            "name": "Test City",
            "parent": self.child_location1.pk,  # Child becomes parent
        }

        response = self.client.put(self.detail_url1, data=update_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("parent", response.json())


class LocationDeleteAPITest(BaseLocationAPITestCase):
    """Test Location delete API endpoint."""

    def test_delete_requires_authentication(self):
        """Test that location deletion requires authentication."""
        response = self.client.delete(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_location_as_owner(self):
        """Test location deletion as campaign owner."""
        self.client.force_authenticate(user=self.owner)

        response = self.client.delete(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify location was deleted
        self.assertFalse(Location.objects.filter(pk=self.location1.pk).exists())

    def test_delete_location_as_gm(self):
        """Test location deletion as GM."""
        self.client.force_authenticate(user=self.gm)

        response = self.client.delete(self.detail_url2)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_owned_location_as_character_owner(self):
        """Test deleting character-owned location as character's owner."""
        self.client.force_authenticate(user=self.player1)

        response = self.client.delete(self.detail_url2)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_created_location_as_creator(self):
        """Test deleting unowned location as its creator."""
        # Create a location without owner
        unowned_location = Location.objects.create(
            name="Unowned Location",
            campaign=self.campaign,
            created_by=self.player1,
        )

        self.client.force_authenticate(user=self.player1)

        detail_url = self.get_detail_url(unowned_location.pk)
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_location_other_player_denied(self):
        """Test that other players cannot delete locations they don't own/create."""
        self.client.force_authenticate(user=self.player2)

        response = self.client.delete(self.detail_url2)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Verify location wasn't deleted
        self.assertTrue(Location.objects.filter(pk=self.location2.pk).exists())

    def test_delete_location_observer_denied(self):
        """Test that observers cannot delete locations."""
        self.client.force_authenticate(user=self.observer)

        response = self.client.delete(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_location_non_member_denied(self):
        """Test that non-members cannot delete locations."""
        self.client.force_authenticate(user=self.non_member)

        response = self.client.delete(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_handles_orphaned_children(self):
        """Test that deleting a location properly handles orphaned children."""
        self.client.force_authenticate(user=self.owner)

        # Delete parent location
        response = self.client.delete(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify child is now parentless
        self.child_location1.refresh_from_db()
        self.assertIsNone(self.child_location1.parent)

    def test_delete_with_grandchildren_promotes_hierarchy(self):
        """Test that deleting a location with grandchildren promotes them correctly."""
        self.client.force_authenticate(user=self.gm)

        # Delete the middle level (child_location1)
        detail_url = self.get_detail_url(self.child_location1.pk)
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify grandchild is promoted to child of original parent
        self.grandchild_location.refresh_from_db()
        self.assertEqual(self.grandchild_location.parent, self.location1)


class LocationChildrenAPITest(BaseLocationAPITestCase):
    """Test Location children API endpoint."""

    def test_children_requires_authentication_private_campaign(self):
        """Test that children endpoint requires authentication for private campaigns."""
        response = self.client.get(self.children_url1)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_children_anonymous_public_campaign(self):
        """Test that anonymous users can view children in public campaigns."""
        public_children_url = self.get_children_url(self.public_location.pk)
        response = self.client.get(public_children_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_children_as_campaign_member(self):
        """Test children endpoint as campaign member."""
        self.client.force_authenticate(user=self.player1)

        response = self.client.get(self.children_url1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data), 1)  # location1 has 1 child
        self.assertEqual(data[0]["name"], "City Center")
        self.assertEqual(data[0]["parent"]["id"], self.location1.pk)

    def test_children_non_member_denied(self):
        """Test that non-members cannot view children in private campaigns."""
        self.client.force_authenticate(user=self.non_member)

        response = self.client.get(self.children_url1)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_children_location_not_found(self):
        """Test children endpoint with non-existent location."""
        self.client.force_authenticate(user=self.player1)

        non_existent_url = self.get_children_url(99999)
        response = self.client.get(non_existent_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_children_empty_for_leaf_locations(self):
        """Test children endpoint returns empty list for locations without children."""
        self.client.force_authenticate(user=self.player1)

        leaf_children_url = self.get_children_url(self.grandchild_location.pk)
        response = self.client.get(leaf_children_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data), 0)
