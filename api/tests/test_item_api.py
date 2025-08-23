"""
Tests for Item API CRUD operations.

This module tests the item API endpoint functionality including:
- Authentication and permission checks
- CRUD operations (Create, Read, Update, Delete)
- Filtering and search functionality
- Role-based access control
- Soft delete handling
- Single character ownership
- Polymorphic model support preparation
"""

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from campaigns.models import Campaign, CampaignMembership
from characters.models import Character
from items.models import Item

User = get_user_model()


class BaseItemAPITestCase(APITestCase):
    """Base test case with common setup for item API tests."""

    def setUp(self):
        """Set up test users, campaigns, characters, and items."""
        # Create test users
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.gm = User.objects.create_user(
            username="gm", email="gm@test.com", password="testpass123"
        )
        self.player1 = User.objects.create_user(
            username="player1", email="player1@test.com", password="testpass123"
        )
        self.player2 = User.objects.create_user(
            username="player2", email="player2@test.com", password="testpass123"
        )
        self.observer = User.objects.create_user(
            username="observer", email="observer@test.com", password="testpass123"
        )
        self.non_member = User.objects.create_user(
            username="nonmember", email="nonmember@test.com", password="testpass123"
        )

        # Create test campaigns
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            slug="test-campaign",
            owner=self.owner,
            game_system="Mage: The Ascension",
            is_public=False,
        )

        self.other_campaign = Campaign.objects.create(
            name="Other Campaign",
            slug="other-campaign",
            owner=self.owner,
            game_system="Vampire: The Masquerade",
            is_public=False,
        )

        # Create memberships for main campaign
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm, role="GM"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player1, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player2, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.observer, role="OBSERVER"
        )

        # No membership needed for other_campaign - will use campaign owner
        # for character ownership

        # Create test characters
        self.character1 = Character.objects.create(
            name="Player1 Character",
            description="Character owned by player1",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )
        self.character2 = Character.objects.create(
            name="Player2 Character",
            description="Character owned by player2",
            campaign=self.campaign,
            player_owner=self.player2,
            game_system="Mage: The Ascension",
        )
        self.npc_character = Character.objects.create(
            name="GM NPC",
            description="NPC managed by GM",
            campaign=self.campaign,
            player_owner=self.gm,
            game_system="Mage: The Ascension",
            npc=True,
        )

        # Create test items
        self.item1 = Item.objects.create(
            name="Magic Sword",
            description="A powerful magical weapon",
            campaign=self.campaign,
            quantity=1,
            owner=self.character1,
            created_by=self.player1,
        )
        self.item2 = Item.objects.create(
            name="Health Potion",
            description="A healing potion",
            campaign=self.campaign,
            quantity=5,
            owner=self.character2,
            created_by=self.player2,
        )
        self.unowned_item = Item.objects.create(
            name="Ancient Tome",
            description="An unowned book of knowledge",
            campaign=self.campaign,
            quantity=1,
            owner=None,
            created_by=self.gm,
        )
        self.npc_item = Item.objects.create(
            name="Shop Inventory",
            description="Items owned by NPC",
            campaign=self.campaign,
            quantity=10,
            owner=self.npc_character,
            created_by=self.gm,
        )

        # Items in other campaign for cross-campaign testing
        self.other_campaign_character = Character.objects.create(
            name="Other Character",
            campaign=self.other_campaign,
            player_owner=self.owner,  # Use campaign owner instead of player1
            game_system="Vampire: The Masquerade",
        )
        self.other_campaign_item = Item.objects.create(
            name="Cross Campaign Item",
            description="Item in different campaign",
            campaign=self.other_campaign,
            quantity=1,
            owner=self.other_campaign_character,
            created_by=self.player1,
        )

        # API URLs (assuming RESTful URL pattern)
        self.list_url = reverse("api:items-list")
        self.detail_url1 = reverse("api:items-detail", kwargs={"pk": self.item1.pk})
        self.detail_url2 = reverse("api:items-detail", kwargs={"pk": self.item2.pk})
        self.unowned_detail_url = reverse(
            "api:items-detail", kwargs={"pk": self.unowned_item.pk}
        )

    def get_detail_url(self, item_id):
        """Helper to get detail URL for any item."""
        return reverse("api:items-detail", kwargs={"pk": item_id})

    def assertItemOwnership(self, item_data, expected_owner_id=None):
        """Helper to assert item ownership in API response."""
        if expected_owner_id:
            self.assertIn("owner", item_data)
            self.assertEqual(item_data["owner"]["id"], expected_owner_id)
        else:
            self.assertTrue(
                item_data.get("owner") is None,
                f"Expected no owner but got: {item_data.get('owner')}",
            )


class ItemListAPITest(BaseItemAPITestCase):
    """Test Item list API endpoint."""

    def test_list_requires_authentication(self):
        """Test that item listing requires authentication."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_requires_campaign_filter(self):
        """Test that item listing requires campaign filter."""
        self.client.force_authenticate(user=self.player1)

        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("campaign_id", response.json())

    def test_list_items_as_player(self):
        """Test item listing as authenticated campaign member."""
        self.client.force_authenticate(user=self.player1)

        response = self.client.get(self.list_url, {"campaign_id": self.campaign.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        results = data.get("results", data)  # Handle both paginated and non-paginated
        self.assertGreater(len(results), 0)

        # Verify all items belong to the requested campaign
        for item_data in results:
            self.assertEqual(item_data["campaign"]["id"], self.campaign.pk)

    def test_list_items_as_gm(self):
        """Test item listing as GM sees all campaign items."""
        self.client.force_authenticate(user=self.gm)

        response = self.client.get(self.list_url, {"campaign_id": self.campaign.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        results = data.get("results", data)
        self.assertEqual(len(results), 4)  # All items in campaign

    def test_list_items_as_campaign_owner(self):
        """Test item listing as campaign owner sees all campaign items."""
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(self.list_url, {"campaign_id": self.campaign.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        results = data.get("results", data)
        self.assertEqual(len(results), 4)  # All items in campaign

    def test_list_items_non_member_denied(self):
        """Test that non-members cannot view items in private campaigns."""
        self.client.force_authenticate(user=self.non_member)

        response = self.client.get(self.list_url, {"campaign_id": self.campaign.pk})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_filter_by_owner(self):
        """Test filtering items by character owner."""
        self.client.force_authenticate(user=self.gm)

        # Filter by character1
        response = self.client.get(
            self.list_url,
            {"campaign_id": self.campaign.pk, "owner": self.character1.pk},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        results = data.get("results", data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Magic Sword")
        self.assertItemOwnership(results[0], expected_owner_id=self.character1.pk)

    def test_list_filter_by_created_by(self):
        """Test filtering items by creator."""
        self.client.force_authenticate(user=self.gm)

        # Filter by player1's items
        response = self.client.get(
            self.list_url,
            {"campaign_id": self.campaign.pk, "created_by": self.player1.pk},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        results = data.get("results", data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["created_by"]["id"], self.player1.pk)

    def test_list_filter_by_quantity_range(self):
        """Test filtering items by quantity ranges."""
        self.client.force_authenticate(user=self.gm)

        # Filter by quantity >= 5
        response = self.client.get(
            self.list_url,
            {"campaign_id": self.campaign.pk, "quantity_min": 5},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        results = data.get("results", data)
        self.assertEqual(len(results), 2)  # Health Potion (5) and Shop Inventory (10)

        # Filter by quantity <= 1
        response = self.client.get(
            self.list_url,
            {"campaign_id": self.campaign.pk, "quantity_max": 1},
        )
        data = response.json()
        results = data.get("results", data)
        self.assertEqual(len(results), 2)  # Magic Sword and Ancient Tome

        # Filter by exact quantity range
        response = self.client.get(
            self.list_url,
            {"campaign_id": self.campaign.pk, "quantity_min": 5, "quantity_max": 5},
        )
        data = response.json()
        results = data.get("results", data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Health Potion")

    def test_list_search_by_name(self):
        """Test searching items by name within campaign."""
        self.client.force_authenticate(user=self.gm)

        response = self.client.get(
            self.list_url, {"campaign_id": self.campaign.pk, "search": "Magic"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        results = data.get("results", data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Magic Sword")

    def test_list_search_by_description(self):
        """Test searching items by description within campaign."""
        self.client.force_authenticate(user=self.gm)

        response = self.client.get(
            self.list_url, {"campaign_id": self.campaign.pk, "search": "healing"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        results = data.get("results", data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Health Potion")

    def test_list_excludes_soft_deleted_by_default(self):
        """Test that soft-deleted items are excluded from list by default."""
        # Soft delete an item
        self.item1.soft_delete(self.player1)

        self.client.force_authenticate(user=self.gm)

        response = self.client.get(self.list_url, {"campaign_id": self.campaign.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        results = data.get("results", data)
        self.assertEqual(len(results), 3)  # One less item

        # Verify deleted item is not in results
        item_names = [item["name"] for item in results]
        self.assertNotIn("Magic Sword", item_names)

    def test_list_includes_deleted_with_parameter(self):
        """Test that deleted items can be included with parameter."""
        # Soft delete an item
        self.item1.soft_delete(self.player1)

        self.client.force_authenticate(user=self.gm)

        response = self.client.get(
            self.list_url,
            {"campaign_id": self.campaign.pk, "include_deleted": "true"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        results = data.get("results", data)
        self.assertEqual(len(results), 4)  # All items including deleted

        # Find the deleted item and verify it's marked as deleted
        deleted_item = next(
            (item for item in results if item["name"] == "Magic Sword"), None
        )
        self.assertIsNotNone(deleted_item)
        self.assertTrue(deleted_item["is_deleted"])

    def test_list_includes_ownership_info(self):
        """Test that item listing includes ownership information."""
        self.client.force_authenticate(user=self.gm)

        response = self.client.get(self.list_url, {"campaign_id": self.campaign.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        results = data.get("results", data)

        # Find owned item
        owned_item = next(
            (item for item in results if item["name"] == "Magic Sword"), None
        )
        self.assertIsNotNone(owned_item)
        self.assertItemOwnership(owned_item, expected_owner_id=self.character1.pk)

        # Find unowned item
        unowned_item = next(
            (item for item in results if item["name"] == "Ancient Tome"), None
        )
        self.assertIsNotNone(unowned_item)
        self.assertItemOwnership(unowned_item, expected_owner_id=None)


class ItemCreateAPITest(BaseItemAPITestCase):
    """Test Item create API endpoint."""

    def test_create_requires_authentication(self):
        """Test that item creation requires authentication."""
        item_data = {
            "name": "Test Item",
            "campaign": self.campaign.pk,
            "quantity": 1,
        }

        response = self.client.post(self.list_url, data=item_data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_item_as_player(self):
        """Test item creation as a player."""
        self.client.force_authenticate(user=self.player1)

        item_data = {
            "name": "New Player Item",
            "description": "A new item created via API",
            "campaign": self.campaign.pk,
            "quantity": 2,
            "owner": self.character1.pk,
        }

        response = self.client.post(self.list_url, data=item_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.json()
        self.assertEqual(data["name"], "New Player Item")
        self.assertEqual(data["campaign"]["id"], self.campaign.pk)
        self.assertEqual(data["created_by"]["id"], self.player1.pk)
        self.assertEqual(data["quantity"], 2)
        self.assertItemOwnership(data, expected_owner_id=self.character1.pk)

        # Verify item was created in database
        item = Item.objects.get(name="New Player Item")
        self.assertEqual(item.created_by, self.player1)
        self.assertEqual(item.campaign, self.campaign)
        self.assertEqual(item.owner, self.character1)

    def test_create_item_as_gm(self):
        """Test item creation as a GM."""
        self.client.force_authenticate(user=self.gm)

        item_data = {
            "name": "GM Item",
            "description": "An item created by GM",
            "campaign": self.campaign.pk,
            "quantity": 1,
        }

        response = self.client.post(self.list_url, data=item_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.json()
        self.assertEqual(data["created_by"]["id"], self.gm.pk)

    def test_create_item_as_owner(self):
        """Test item creation as campaign owner."""
        self.client.force_authenticate(user=self.owner)

        item_data = {
            "name": "Owner Item",
            "campaign": self.campaign.pk,
            "quantity": 1,
        }

        response = self.client.post(self.list_url, data=item_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_item_observer_denied(self):
        """Test that observers cannot create items."""
        self.client.force_authenticate(user=self.observer)

        item_data = {
            "name": "Observer Item",
            "campaign": self.campaign.pk,
            "quantity": 1,
        }

        response = self.client.post(self.list_url, data=item_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_item_non_member_denied(self):
        """Test that non-members cannot create items."""
        self.client.force_authenticate(user=self.non_member)

        item_data = {
            "name": "Non-member Item",
            "campaign": self.campaign.pk,
            "quantity": 1,
        }

        response = self.client.post(self.list_url, data=item_data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_item_validates_required_fields(self):
        """Test validation of required fields."""
        self.client.force_authenticate(user=self.player1)

        # Missing name
        response = self.client.post(
            self.list_url, data={"campaign": self.campaign.pk, "quantity": 1}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.json())

        # Missing campaign
        response = self.client.post(
            self.list_url, data={"name": "Test Item", "quantity": 1}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("campaign", response.json())

    def test_create_item_validates_quantity(self):
        """Test that quantity validation works."""
        self.client.force_authenticate(user=self.player1)

        # Zero quantity should fail
        item_data = {
            "name": "Zero Quantity Item",
            "campaign": self.campaign.pk,
            "quantity": 0,
        }
        response = self.client.post(self.list_url, data=item_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("quantity", response.json())

        # Negative quantity should fail
        item_data["quantity"] = -1
        response = self.client.post(self.list_url, data=item_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("quantity", response.json())

    def test_create_item_with_character_owner(self):
        """Test creating an item owned by a character."""
        self.client.force_authenticate(user=self.player1)

        item_data = {
            "name": "Character Owned Item",
            "campaign": self.campaign.pk,
            "quantity": 1,
            "owner": self.character1.pk,
        }

        response = self.client.post(self.list_url, data=item_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.json()
        self.assertItemOwnership(data, expected_owner_id=self.character1.pk)

    def test_create_item_validates_owner_in_same_campaign(self):
        """Test that character owner must be in the same campaign."""
        self.client.force_authenticate(user=self.player1)

        item_data = {
            "name": "Invalid Owner Item",
            "campaign": self.campaign.pk,
            "quantity": 1,
            "owner": self.other_campaign_character.pk,  # Different campaign
        }

        response = self.client.post(self.list_url, data=item_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("owner", response.json())

    def test_create_item_default_quantity(self):
        """Test that default quantity is 1 when not specified."""
        self.client.force_authenticate(user=self.player1)

        item_data = {
            "name": "Default Quantity Item",
            "campaign": self.campaign.pk,
        }

        response = self.client.post(self.list_url, data=item_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.json()
        self.assertEqual(data["quantity"], 1)


class ItemDetailAPITest(BaseItemAPITestCase):
    """Test Item detail API endpoint."""

    def test_detail_requires_authentication(self):
        """Test that item detail requires authentication."""
        response = self.client.get(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_detail_item_as_campaign_member(self):
        """Test item detail access as campaign member."""
        self.client.force_authenticate(user=self.player1)

        response = self.client.get(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data["id"], self.item1.pk)
        self.assertEqual(data["name"], "Magic Sword")

    def test_detail_item_as_gm(self):
        """Test item detail access as GM."""
        self.client.force_authenticate(user=self.gm)

        response = self.client.get(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_detail_item_as_campaign_owner(self):
        """Test item detail access as campaign owner."""
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_detail_item_as_observer(self):
        """Test item detail access as observer."""
        self.client.force_authenticate(user=self.observer)

        response = self.client.get(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_detail_item_non_member_denied(self):
        """Test that non-members cannot view items in private campaigns."""
        self.client.force_authenticate(user=self.non_member)

        response = self.client.get(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_detail_includes_ownership_info(self):
        """Test that item detail includes ownership information."""
        self.client.force_authenticate(user=self.gm)

        response = self.client.get(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertItemOwnership(data, expected_owner_id=self.character1.pk)

        # Test unowned item
        response = self.client.get(self.unowned_detail_url)
        data = response.json()
        self.assertItemOwnership(data, expected_owner_id=None)

    def test_detail_soft_deleted_item_visibility(self):
        """Test visibility of soft-deleted items."""
        # Soft delete the item
        self.item1.soft_delete(self.player1)

        # Creator should see deleted item
        self.client.force_authenticate(user=self.player1)
        response = self.client.get(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertTrue(data["is_deleted"])

        # GM should see deleted item
        self.client.force_authenticate(user=self.gm)
        response = self.client.get(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Campaign owner should see deleted item
        self.client.force_authenticate(user=self.owner)
        response = self.client.get(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Other players should not see deleted item
        self.client.force_authenticate(user=self.player2)
        response = self.client.get(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class ItemUpdateAPITest(BaseItemAPITestCase):
    """Test Item update API endpoint."""

    def test_update_requires_authentication(self):
        """Test that item update requires authentication."""
        update_data = {"name": "Updated Name"}

        response = self.client.put(self.detail_url1, data=update_data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_item_as_creator(self):
        """Test item update as item creator."""
        self.client.force_authenticate(user=self.player1)

        update_data = {
            "name": "Updated Magic Sword",
            "description": "Updated description",
            "quantity": 2,
        }

        response = self.client.put(self.detail_url1, data=update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data["name"], "Updated Magic Sword")
        self.assertEqual(data["description"], "Updated description")
        self.assertEqual(data["quantity"], 2)

        # Verify in database
        self.item1.refresh_from_db()
        self.assertEqual(self.item1.name, "Updated Magic Sword")

    def test_update_item_as_gm(self):
        """Test item update as GM."""
        self.client.force_authenticate(user=self.gm)

        update_data = {"name": "GM Updated Item"}

        response = self.client.put(self.detail_url1, data=update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_item_as_campaign_owner(self):
        """Test item update as campaign owner."""
        self.client.force_authenticate(user=self.owner)

        update_data = {"name": "Owner Updated Item"}

        response = self.client.put(self.detail_url1, data=update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_item_other_player_denied(self):
        """Test that other players cannot update items they don't own/create."""
        self.client.force_authenticate(user=self.player2)

        update_data = {"name": "Unauthorized Update"}

        response = self.client.put(self.detail_url1, data=update_data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_item_observer_denied(self):
        """Test that observers cannot update items."""
        self.client.force_authenticate(user=self.observer)

        update_data = {"name": "Observer Update"}

        response = self.client.put(self.detail_url1, data=update_data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_readonly_fields_ignored(self):
        """Test that read-only fields are ignored in updates."""
        self.client.force_authenticate(user=self.player1)

        original_campaign = self.item1.campaign
        original_creator = self.item1.created_by

        update_data = {
            "name": "Updated Name",
            "campaign": self.other_campaign.pk,  # Try to change campaign
            "created_by": self.player2.pk,  # Try to change creator
        }

        response = self.client.put(self.detail_url1, data=update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify readonly fields weren't changed
        self.item1.refresh_from_db()
        self.assertEqual(self.item1.campaign, original_campaign)
        self.assertEqual(self.item1.created_by, original_creator)
        self.assertEqual(self.item1.name, "Updated Name")  # But this changed

    def test_update_item_owner_transfer(self):
        """Test updating item owner (transfer functionality)."""
        self.client.force_authenticate(user=self.gm)

        update_data = {
            "name": "Magic Sword",
            "owner": self.character2.pk,  # Transfer to different character
        }

        response = self.client.put(self.detail_url1, data=update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertItemOwnership(data, expected_owner_id=self.character2.pk)

        # Verify transfer timestamp was updated
        self.item1.refresh_from_db()
        self.assertIsNotNone(self.item1.last_transferred_at)

    def test_update_validates_quantity(self):
        """Test quantity validation on update."""
        self.client.force_authenticate(user=self.player1)

        # Zero quantity should fail
        update_data = {"name": "Magic Sword", "quantity": 0}
        response = self.client.put(self.detail_url1, data=update_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("quantity", response.json())


class ItemDeleteAPITest(BaseItemAPITestCase):
    """Test Item delete API endpoint (soft delete)."""

    def test_delete_requires_authentication(self):
        """Test that item deletion requires authentication."""
        response = self.client.delete(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_item_as_creator(self):
        """Test item soft deletion as item creator."""
        self.client.force_authenticate(user=self.player1)

        response = self.client.delete(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify soft delete (item still exists but marked as deleted)
        self.item1.refresh_from_db()
        self.assertTrue(self.item1.is_deleted)
        self.assertEqual(self.item1.deleted_by, self.player1)
        self.assertIsNotNone(self.item1.deleted_at)

        # Item should not appear in default queryset
        self.assertFalse(Item.objects.filter(pk=self.item1.pk).exists())
        # But should appear in all_objects
        self.assertTrue(Item.all_objects.filter(pk=self.item1.pk).exists())

    def test_delete_item_as_gm(self):
        """Test item soft deletion as GM."""
        self.client.force_authenticate(user=self.gm)

        response = self.client.delete(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify soft delete with GM as deleter
        self.item1.refresh_from_db()
        self.assertTrue(self.item1.is_deleted)
        self.assertEqual(self.item1.deleted_by, self.gm)

    def test_delete_item_as_campaign_owner(self):
        """Test item soft deletion as campaign owner."""
        self.client.force_authenticate(user=self.owner)

        response = self.client.delete(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify soft delete
        self.item1.refresh_from_db()
        self.assertTrue(self.item1.is_deleted)
        self.assertEqual(self.item1.deleted_by, self.owner)

    def test_delete_item_other_player_denied(self):
        """Test that other players cannot delete items they don't own/create."""
        self.client.force_authenticate(user=self.player2)

        response = self.client.delete(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Verify item wasn't deleted
        self.item1.refresh_from_db()
        self.assertFalse(self.item1.is_deleted)

    def test_delete_item_observer_denied(self):
        """Test that observers cannot delete items."""
        self.client.force_authenticate(user=self.observer)

        response = self.client.delete(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_item_non_member_denied(self):
        """Test that non-members cannot delete items."""
        self.client.force_authenticate(user=self.non_member)

        response = self.client.delete(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_already_deleted_item(self):
        """Test deleting an already soft-deleted item."""
        # First deletion
        self.item1.soft_delete(self.player1)

        self.client.force_authenticate(user=self.player1)

        response = self.client.delete(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_unowned_item_as_gm(self):
        """Test that GMs can delete unowned items."""
        self.client.force_authenticate(user=self.gm)

        response = self.client.delete(self.unowned_detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify soft delete
        self.unowned_item.refresh_from_db()
        self.assertTrue(self.unowned_item.is_deleted)
        self.assertEqual(self.unowned_item.deleted_by, self.gm)


class ItemSecurityTest(BaseItemAPITestCase):
    """Test Item API security scenarios."""

    def test_cross_campaign_item_access_denied(self):
        """Test that users cannot access items from campaigns they're not in."""
        self.client.force_authenticate(user=self.player1)

        # Try to access item from other campaign
        other_detail_url = self.get_detail_url(self.other_campaign_item.pk)
        response = self.client.get(other_detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cross_campaign_filtering_isolation(self):
        """Test that campaign filtering prevents cross-campaign data leakage."""
        self.client.force_authenticate(user=self.player1)

        # Request items from campaign user is not member of
        response = self.client.get(
            self.list_url, {"campaign_id": self.other_campaign.pk}
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_invalid_campaign_id_handled(self):
        """Test handling of invalid campaign IDs."""
        self.client.force_authenticate(user=self.player1)

        response = self.client.get(self.list_url, {"campaign_id": 99999})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_character_ownership_cross_campaign_validation(self):
        """Test that character owner validation prevents cross-campaign assignment."""
        self.client.force_authenticate(user=self.player1)

        # Try to create item owned by character from different campaign
        item_data = {
            "name": "Cross Campaign Owner Item",
            "campaign": self.campaign.pk,
            "quantity": 1,
            "owner": self.other_campaign_character.pk,
        }

        response = self.client.post(self.list_url, data=item_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("owner", response.json())

    def test_permission_boundaries_respected(self):
        """Test that permission boundaries are properly enforced."""
        # Create item as player1
        test_item = Item.objects.create(
            name="Permission Test Item",
            campaign=self.campaign,
            quantity=1,
            created_by=self.player1,
        )

        # Player2 should not be able to update it
        self.client.force_authenticate(user=self.player2)
        detail_url = self.get_detail_url(test_item.pk)

        update_data = {"name": "Hacked Item"}
        response = self.client.put(detail_url, data=update_data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Verify item wasn't changed
        test_item.refresh_from_db()
        self.assertEqual(test_item.name, "Permission Test Item")


class ItemPolymorphicPreparationTest(BaseItemAPITestCase):
    """Test Item API readiness for polymorphic inheritance."""

    def test_polymorphic_type_field_present(self):
        """Test that polymorphic type information is included in responses."""
        self.client.force_authenticate(user=self.gm)

        response = self.client.get(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        # Item should have polymorphic_ctype field for future subclass support
        self.assertIn("polymorphic_ctype", data)

    def test_polymorphic_manager_compatibility(self):
        """Test that API works with polymorphic managers."""
        self.client.force_authenticate(user=self.gm)

        response = self.client.get(self.list_url, {"campaign_id": self.campaign.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        results = data.get("results", data)

        # All items should be returned as base Item type for now
        for item in results:
            self.assertEqual(item["polymorphic_ctype"]["model"], "item")

    def test_base_item_crud_operations(self):
        """Test that all CRUD operations work with base Item type."""
        self.client.force_authenticate(user=self.player1)

        # Create
        create_data = {
            "name": "Polymorphic Test Item",
            "campaign": self.campaign.pk,
            "quantity": 1,
        }
        response = self.client.post(self.list_url, data=create_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        item_id = response.json()["id"]
        detail_url = self.get_detail_url(item_id)

        # Read
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Update
        update_data = {"name": "Updated Polymorphic Item"}
        response = self.client.put(detail_url, data=update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Delete (soft delete)
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
