"""
Tests for Item management views.

Tests cover all requirements from Issue #54:
1. Item creation view & form (GET/POST with validation and permissions)
2. Item detail view (show all information with proper permissions)
3. Item edit view & form (GET/POST with validation, permissions, transfer functionality)
4. Enhanced item list view (search, filtering, pagination)
5. Permission system integration (OWNER/GM have full CRUD, PLAYER/OBSERVER read-only)
"""

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import Client, TestCase
from django.urls import reverse

from campaigns.models import Campaign, CampaignMembership
from characters.models import Character
from items.models import Item

User = get_user_model()


class ItemCreateViewTest(TestCase):
    """Test the item creation view."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()

        # Create users
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.gm = User.objects.create_user(
            username="gm", email="gm@test.com", password="testpass123"
        )
        self.player = User.objects.create_user(
            username="player", email="player@test.com", password="testpass123"
        )
        self.observer = User.objects.create_user(
            username="observer", email="observer@test.com", password="testpass123"
        )
        self.outsider = User.objects.create_user(
            username="outsider", email="outsider@test.com", password="testpass123"
        )

        # Create campaign
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            game_system="Mage: The Ascension",
        )

        # Create memberships
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm, role="GM"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.observer, role="OBSERVER"
        )

        # Create a character for ownership testing
        self.character = Character.objects.create(
            name="Test Character",
            player_owner=self.player,
            campaign=self.campaign,
            game_system="Mage: The Ascension",
        )

        self.create_url = reverse(
            "items:create", kwargs={"campaign_slug": self.campaign.slug}
        )

    def test_create_view_requires_authentication(self):
        """Test that unauthenticated users get 404 (hiding campaign existence)."""
        response = self.client.get(self.create_url)

        self.assertEqual(response.status_code, 404)

    def test_owner_can_access_create_form(self):
        """Test that campaign owners can access the item creation form."""
        self.client.login(username="owner", password="testpass123")

        response = self.client.get(self.create_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create Item")
        self.assertContains(response, "Name")
        self.assertContains(response, "Description")
        self.assertContains(response, "Quantity")
        self.assertContains(response, "<form")
        self.assertContains(response, 'name="name"')
        self.assertContains(response, 'name="description"')
        self.assertContains(response, 'name="quantity"')

    def test_gm_can_access_create_form(self):
        """Test that GMs can access the item creation form."""
        self.client.login(username="gm", password="testpass123")

        response = self.client.get(self.create_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create Item")

    def test_player_cannot_access_create_form(self):
        """Test that players cannot access the item creation form."""
        self.client.login(username="player", password="testpass123")

        response = self.client.get(self.create_url)

        self.assertEqual(response.status_code, 404)  # Hide existence for unauthorized

    def test_observer_cannot_access_create_form(self):
        """Test that observers cannot access the item creation form."""
        self.client.login(username="observer", password="testpass123")

        response = self.client.get(self.create_url)

        self.assertEqual(response.status_code, 404)  # Hide existence for unauthorized

    def test_outsider_cannot_access_create_form(self):
        """Test that non-members cannot access the item creation form."""
        self.client.login(username="outsider", password="testpass123")

        response = self.client.get(self.create_url)

        self.assertEqual(response.status_code, 404)  # Hide existence for unauthorized

    def test_create_item_success_minimal_data(self):
        """Test successful item creation with minimal required data."""
        self.client.login(username="owner", password="testpass123")

        form_data = {
            "name": "Test Item",
            "quantity": 1,
        }

        response = self.client.post(self.create_url, form_data)

        # Should redirect to item detail or campaign items after successful creation
        self.assertEqual(response.status_code, 302)

        # Check that item was created
        item = Item.objects.get(name="Test Item")
        self.assertEqual(item.campaign, self.campaign)
        self.assertEqual(item.created_by, self.owner)
        self.assertEqual(item.quantity, 1)
        self.assertEqual(item.description, "")
        self.assertIsNone(item.owner)  # No owner assigned by default

    def test_create_item_success_full_data(self):
        """Test successful item creation with all data including owner."""
        self.client.login(username="owner", password="testpass123")

        form_data = {
            "name": "Test Item Full",
            "description": "A comprehensive test item",
            "quantity": 5,
            "owner": self.character.id,
        }

        response = self.client.post(self.create_url, form_data)

        self.assertEqual(response.status_code, 302)

        # Check that item was created with all data
        item = Item.objects.get(name="Test Item Full")
        self.assertEqual(item.campaign, self.campaign)
        self.assertEqual(item.created_by, self.owner)
        self.assertEqual(item.description, "A comprehensive test item")
        self.assertEqual(item.quantity, 5)
        self.assertEqual(item.owner, self.character)

    def test_create_item_invalid_data_shows_errors(self):
        """Test that invalid form data shows validation errors."""
        self.client.login(username="owner", password="testpass123")

        # Missing required name field
        form_data = {
            "description": "An item without a name",
            "quantity": 1,
        }

        response = self.client.post(self.create_url, form_data)

        self.assertEqual(response.status_code, 200)  # Form shows again with errors
        self.assertFormError(response, "form", "name", "This field is required.")

    def test_create_item_invalid_quantity_shows_errors(self):
        """Test that invalid quantity shows validation errors."""
        self.client.login(username="owner", password="testpass123")

        # Invalid quantity (0)
        form_data = {
            "name": "Test Item",
            "quantity": 0,
        }

        response = self.client.post(self.create_url, form_data)

        self.assertEqual(response.status_code, 200)  # Form shows again with errors
        self.assertFormError(
            response,
            "form",
            "quantity",
            "Ensure this value is greater than or equal to 1.",
        )

    def test_create_item_sets_campaign_context(self):
        """Test that created item is properly associated with the campaign."""
        self.client.login(username="owner", password="testpass123")

        form_data = {
            "name": "Campaign Context Test",
            "quantity": 1,
        }

        response = self.client.post(self.create_url, form_data)

        self.assertEqual(response.status_code, 302)

        item = Item.objects.get(name="Campaign Context Test")
        self.assertEqual(item.campaign, self.campaign)

    def test_create_item_gm_permission(self):
        """Test that GMs can create items successfully."""
        self.client.login(username="gm", password="testpass123")

        form_data = {
            "name": "GM Created Item",
            "quantity": 1,
        }

        response = self.client.post(self.create_url, form_data)

        self.assertEqual(response.status_code, 302)

        item = Item.objects.get(name="GM Created Item")
        self.assertEqual(item.created_by, self.gm)
        self.assertEqual(item.campaign, self.campaign)


class ItemDetailViewTest(TestCase):
    """Test the item detail view."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()

        # Create users
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.gm = User.objects.create_user(
            username="gm", email="gm@test.com", password="testpass123"
        )
        self.player = User.objects.create_user(
            username="player", email="player@test.com", password="testpass123"
        )
        self.observer = User.objects.create_user(
            username="observer", email="observer@test.com", password="testpass123"
        )
        self.outsider = User.objects.create_user(
            username="outsider", email="outsider@test.com", password="testpass123"
        )

        # Create campaign
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            game_system="Mage: The Ascension",
        )

        # Create memberships
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm, role="GM"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.observer, role="OBSERVER"
        )

        # Create character and item
        self.character = Character.objects.create(
            name="Test Character",
            player_owner=self.player,
            campaign=self.campaign,
            game_system="Mage: The Ascension",
        )

        self.item = Item.objects.create(
            name="Test Item",
            description="A test item for detailed viewing",
            quantity=3,
            campaign=self.campaign,
            created_by=self.owner,
            owner=self.character,
        )

        self.detail_url = reverse(
            "items:detail",
            kwargs={"campaign_slug": self.campaign.slug, "item_id": self.item.id},
        )

    def test_detail_view_requires_authentication(self):
        """Test that unauthenticated users are redirected to login."""
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_owner_can_view_item_detail(self):
        """Test that campaign owners can view item details."""
        self.client.login(username="owner", password="testpass123")

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Item")
        self.assertContains(response, "A test item for detailed viewing")
        self.assertContains(response, "3")  # quantity
        self.assertContains(response, "Test Character")  # owner name
        self.assertContains(response, "owner")  # created by

    def test_gm_can_view_item_detail(self):
        """Test that GMs can view item details."""
        self.client.login(username="gm", password="testpass123")

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Item")

    def test_player_can_view_item_detail(self):
        """Test that players can view item details."""
        self.client.login(username="player", password="testpass123")

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Item")

    def test_observer_can_view_item_detail(self):
        """Test that observers can view item details."""
        self.client.login(username="observer", password="testpass123")

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Item")

    def test_outsider_cannot_view_item_detail(self):
        """Test that non-members cannot view item details."""
        self.client.login(username="outsider", password="testpass123")

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 404)

    def test_detail_shows_all_item_information(self):
        """Test that detail view shows all item information."""
        self.client.login(username="owner", password="testpass123")

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.item.name)
        self.assertContains(response, self.item.description)
        self.assertContains(response, str(self.item.quantity))
        self.assertContains(response, self.character.name)  # owner
        self.assertContains(response, self.owner.username)  # created_by
        # Should show timestamps
        self.assertContains(response, "Created")
        self.assertContains(response, "Updated")

    def test_detail_shows_edit_button_for_authorized_users(self):
        """Test that edit buttons are visible for users with edit permissions."""
        self.client.login(username="owner", password="testpass123")

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Edit")
        self.assertContains(response, "Delete")

    def test_detail_shows_edit_button_for_gm(self):
        """Test that edit buttons are visible for GMs."""
        self.client.login(username="gm", password="testpass123")

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Edit")

    def test_detail_hides_edit_button_for_player(self):
        """Test that edit buttons are hidden for players."""
        self.client.login(username="player", password="testpass123")

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Edit")
        self.assertNotContains(response, "Delete")

    def test_detail_hides_edit_button_for_observer(self):
        """Test that edit buttons are hidden for observers."""
        self.client.login(username="observer", password="testpass123")

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Edit")
        self.assertNotContains(response, "Delete")

    def test_detail_shows_character_ownership_integration(self):
        """Test that character ownership is properly displayed."""
        self.client.login(username="owner", password="testpass123")

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Current Owner")
        self.assertContains(response, self.character.name)

    def test_detail_shows_unowned_item(self):
        """Test that unowned items display properly."""
        unowned_item = Item.objects.create(
            name="Unowned Item",
            description="An item with no owner",
            quantity=1,
            campaign=self.campaign,
            created_by=self.owner,
        )

        detail_url = reverse(
            "items:detail",
            kwargs={"campaign_slug": self.campaign.slug, "item_id": unowned_item.id},
        )

        self.client.login(username="owner", password="testpass123")
        response = self.client.get(detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Unowned Item")
        self.assertContains(response, "Unowned")


class ItemEditViewTest(TestCase):
    """Test the item edit view."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()

        # Create users
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.gm = User.objects.create_user(
            username="gm", email="gm@test.com", password="testpass123"
        )
        self.player = User.objects.create_user(
            username="player", email="player@test.com", password="testpass123"
        )
        self.observer = User.objects.create_user(
            username="observer", email="observer@test.com", password="testpass123"
        )
        self.outsider = User.objects.create_user(
            username="outsider", email="outsider@test.com", password="testpass123"
        )

        # Create campaign
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            game_system="Mage: The Ascension",
        )

        # Create memberships
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm, role="GM"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.observer, role="OBSERVER"
        )

        # Create characters and item
        self.character1 = Character.objects.create(
            name="Character One",
            player_owner=self.player,
            campaign=self.campaign,
            game_system="Mage: The Ascension",
        )
        self.character2 = Character.objects.create(
            name="Character Two",
            player_owner=self.gm,
            campaign=self.campaign,
            game_system="Mage: The Ascension",
        )

        self.item = Item.objects.create(
            name="Test Item",
            description="A test item for editing",
            quantity=2,
            campaign=self.campaign,
            created_by=self.owner,
            owner=self.character1,
        )

        self.edit_url = reverse(
            "items:edit",
            kwargs={"campaign_slug": self.campaign.slug, "item_id": self.item.id},
        )

    def test_edit_view_requires_authentication(self):
        """Test that unauthenticated users get 404 (hiding campaign existence)."""
        response = self.client.get(self.edit_url)

        self.assertEqual(response.status_code, 404)

    def test_owner_can_access_edit_form(self):
        """Test that campaign owners can access the item edit form."""
        self.client.login(username="owner", password="testpass123")

        response = self.client.get(self.edit_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Update Item")
        self.assertContains(response, 'value="Test Item"')  # Pre-populated name
        self.assertContains(
            response, "A test item for editing"
        )  # Pre-populated description
        self.assertContains(response, 'value="2"')  # Pre-populated quantity

    def test_gm_can_access_edit_form(self):
        """Test that GMs can access the item edit form."""
        self.client.login(username="gm", password="testpass123")

        response = self.client.get(self.edit_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Update Item")

    def test_player_cannot_access_edit_form(self):
        """Test that players cannot access the item edit form."""
        self.client.login(username="player", password="testpass123")

        response = self.client.get(self.edit_url)

        self.assertEqual(response.status_code, 404)

    def test_observer_cannot_access_edit_form(self):
        """Test that observers cannot access the item edit form."""
        self.client.login(username="observer", password="testpass123")

        response = self.client.get(self.edit_url)

        self.assertEqual(response.status_code, 404)

    def test_outsider_cannot_access_edit_form(self):
        """Test that non-members cannot access the item edit form."""
        self.client.login(username="outsider", password="testpass123")

        response = self.client.get(self.edit_url)

        self.assertEqual(response.status_code, 404)

    def test_edit_item_success(self):
        """Test successful item editing."""
        self.client.login(username="owner", password="testpass123")

        form_data = {
            "name": "Updated Item",
            "description": "This item has been updated",
            "quantity": 5,
            "owner": self.character2.id,
        }

        response = self.client.post(self.edit_url, form_data)

        self.assertEqual(response.status_code, 302)

        # Check that item was updated
        self.item.refresh_from_db()
        self.assertEqual(self.item.name, "Updated Item")
        self.assertEqual(self.item.description, "This item has been updated")
        self.assertEqual(self.item.quantity, 5)
        self.assertEqual(self.item.owner, self.character2)
        self.assertEqual(self.item.modified_by, self.owner)

    def test_edit_item_transfer_ownership(self):
        """Test transferring item ownership updates transfer timestamp."""
        self.client.login(username="owner", password="testpass123")

        original_transfer_time = self.item.last_transferred_at

        form_data = {
            "name": self.item.name,
            "description": self.item.description,
            "quantity": self.item.quantity,
            "owner": self.character2.id,  # Change ownership
        }

        response = self.client.post(self.edit_url, form_data)

        self.assertEqual(response.status_code, 302)

        # Check that transfer timestamp was updated
        self.item.refresh_from_db()
        self.assertEqual(self.item.owner, self.character2)
        self.assertNotEqual(self.item.last_transferred_at, original_transfer_time)
        self.assertIsNotNone(self.item.last_transferred_at)

    def test_edit_item_remove_ownership(self):
        """Test removing item ownership."""
        self.client.login(username="owner", password="testpass123")

        form_data = {
            "name": self.item.name,
            "description": self.item.description,
            "quantity": self.item.quantity,
            "owner": "",  # Remove ownership
        }

        response = self.client.post(self.edit_url, form_data)

        self.assertEqual(response.status_code, 302)

        # Check that ownership was removed
        self.item.refresh_from_db()
        self.assertIsNone(self.item.owner)

    def test_edit_item_form_validation(self):
        """Test that form validation works on edit."""
        self.client.login(username="owner", password="testpass123")

        # Invalid quantity
        form_data = {
            "name": "Valid Name",
            "quantity": 0,  # Invalid
        }

        response = self.client.post(self.edit_url, form_data)

        self.assertEqual(response.status_code, 200)  # Form shows again with errors
        self.assertFormError(
            response,
            "form",
            "quantity",
            "Ensure this value is greater than or equal to 1.",
        )

    def test_edit_item_gm_permission(self):
        """Test that GMs can edit items successfully."""
        self.client.login(username="gm", password="testpass123")

        form_data = {
            "name": "GM Updated Item",
            "description": self.item.description,
            "quantity": self.item.quantity,
        }

        response = self.client.post(self.edit_url, form_data)

        self.assertEqual(response.status_code, 302)

        self.item.refresh_from_db()
        self.assertEqual(self.item.name, "GM Updated Item")
        self.assertEqual(self.item.modified_by, self.gm)


class ItemListViewTest(TestCase):
    """Test the enhanced item list view with search and filtering."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()

        # Create users
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.player = User.objects.create_user(
            username="player", email="player@test.com", password="testpass123"
        )

        # Create campaign
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            game_system="Mage: The Ascension",
        )

        # Create membership
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )

        # Create characters
        self.character1 = Character.objects.create(
            name="Character One",
            player_owner=self.player,
            campaign=self.campaign,
            game_system="Mage: The Ascension",
        )
        self.character2 = Character.objects.create(
            name="Character Two",
            player_owner=self.owner,
            campaign=self.campaign,
            game_system="Mage: The Ascension",
        )

        # Create test items
        self.item1 = Item.objects.create(
            name="Magic Sword",
            description="A powerful enchanted blade",
            quantity=1,
            campaign=self.campaign,
            created_by=self.owner,
            owner=self.character1,
        )
        self.item2 = Item.objects.create(
            name="Health Potion",
            description="Restores health when consumed",
            quantity=5,
            campaign=self.campaign,
            created_by=self.player,
            owner=self.character2,
        )
        self.item3 = Item.objects.create(
            name="Ancient Tome",
            description="Contains arcane knowledge and forbidden secrets",
            quantity=1,
            campaign=self.campaign,
            created_by=self.owner,
        )

        self.list_url = reverse(
            "items:campaign_items", kwargs={"campaign_slug": self.campaign.slug}
        )

    def test_list_view_shows_all_items(self):
        """Test that list view shows all campaign items."""
        self.client.login(username="owner", password="testpass123")

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Magic Sword")
        self.assertContains(response, "Health Potion")
        self.assertContains(response, "Ancient Tome")

    def test_list_view_search_by_name(self):
        """Test searching items by name."""
        self.client.login(username="owner", password="testpass123")

        response = self.client.get(self.list_url, {"search": "Magic"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Magic Sword")
        self.assertNotContains(response, "Health Potion")
        self.assertNotContains(response, "Ancient Tome")

    def test_list_view_search_by_description(self):
        """Test searching items by description."""
        self.client.login(username="owner", password="testpass123")

        response = self.client.get(self.list_url, {"search": "forbidden"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, "Ancient Tome"
        )  # Contains "forbidden" in description
        self.assertNotContains(response, "Health Potion")

    def test_list_view_filter_by_owner(self):
        """Test filtering items by character owner."""
        self.client.login(username="owner", password="testpass123")

        response = self.client.get(self.list_url, {"owner": self.character1.id})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Magic Sword")
        self.assertNotContains(response, "Health Potion")
        self.assertNotContains(response, "Ancient Tome")

    def test_list_view_filter_unowned_items(self):
        """Test filtering for unowned items."""
        self.client.login(username="owner", password="testpass123")

        response = self.client.get(self.list_url, {"owner": "0"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ancient Tome")
        self.assertNotContains(response, "Magic Sword")
        self.assertNotContains(response, "Health Potion")

    def test_list_view_shows_item_information(self):
        """Test that list view shows relevant item information."""
        self.client.login(username="owner", password="testpass123")

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        # Check for item names
        self.assertContains(response, "Magic Sword")
        self.assertContains(response, "Health Potion")
        # Check for quantities
        self.assertContains(response, "1")  # Magic Sword quantity
        self.assertContains(response, "5")  # Health Potion quantity
        # Check for owners
        self.assertContains(response, "Character One")
        self.assertContains(response, "Character Two")

    def test_list_view_pagination_support(self):
        """Test that list view supports pagination for large item sets."""
        # Create many items to test pagination
        for i in range(25):  # Assuming page size is 20
            Item.objects.create(
                name=f"Test Item {i}",
                quantity=1,
                campaign=self.campaign,
                created_by=self.owner,
            )

        self.client.login(username="owner", password="testpass123")

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        # Should show pagination controls
        self.assertContains(response, "page")

    def test_list_view_shows_create_button_for_authorized_users(self):
        """Test that create button is visible for users with create permissions."""
        self.client.login(username="owner", password="testpass123")

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create Item")

    def test_list_view_hides_create_button_for_players(self):
        """Test that create button is hidden for players."""
        self.client.login(username="player", password="testpass123")

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Create Item")

    def test_list_view_search_and_filter_combination(self):
        """Test combining search and filter parameters."""
        self.client.login(username="owner", password="testpass123")

        response = self.client.get(
            self.list_url, {"search": "Potion", "owner": self.character2.id}
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Health Potion")
        self.assertNotContains(response, "Magic Sword")
        self.assertNotContains(response, "Ancient Tome")

    def test_list_view_empty_search_results(self):
        """Test handling of search queries with no results."""
        self.client.login(username="owner", password="testpass123")

        response = self.client.get(self.list_url, {"search": "NonexistentItem"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No items match your search criteria")

    def test_list_view_case_insensitive_search(self):
        """Test that search is case insensitive."""
        self.client.login(username="owner", password="testpass123")

        response = self.client.get(self.list_url, {"search": "MAGIC"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Magic Sword")


class ItemDeleteViewTest(TestCase):
    """Test the item soft delete functionality."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()

        # Create users
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.gm = User.objects.create_user(
            username="gm", email="gm@test.com", password="testpass123"
        )
        self.player = User.objects.create_user(
            username="player", email="player@test.com", password="testpass123"
        )
        self.observer = User.objects.create_user(
            username="observer", email="observer@test.com", password="testpass123"
        )
        self.item_creator = User.objects.create_user(
            username="creator", email="creator@test.com", password="testpass123"
        )

        # Create campaign
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            game_system="Mage: The Ascension",
        )

        # Create memberships
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.owner, role="OWNER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm, role="GM"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.observer, role="OBSERVER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.item_creator, role="PLAYER"
        )

        # Create item
        self.item = Item.objects.create(
            name="Test Item",
            description="A test item for deletion",
            quantity=1,
            campaign=self.campaign,
            created_by=self.item_creator,
        )

        self.delete_url = reverse(
            "items:delete",
            kwargs={"campaign_slug": self.campaign.slug, "item_id": self.item.id},
        )

    def test_owner_can_delete_item(self):
        """Test that campaign owners can delete items."""
        self.client.login(username="owner", password="testpass123")

        response = self.client.post(self.delete_url)

        self.assertEqual(response.status_code, 302)  # Redirect after deletion

        # Check that item was soft deleted
        self.item.refresh_from_db()
        self.assertTrue(self.item.is_deleted)
        self.assertEqual(self.item.deleted_by, self.owner)
        self.assertIsNotNone(self.item.deleted_at)

    def test_gm_can_delete_item(self):
        """Test that GMs can delete items."""
        self.client.login(username="gm", password="testpass123")

        response = self.client.post(self.delete_url)

        self.assertEqual(response.status_code, 302)

        self.item.refresh_from_db()
        self.assertTrue(self.item.is_deleted)
        self.assertEqual(self.item.deleted_by, self.gm)

    def test_item_creator_can_delete_own_item(self):
        """Test that item creators can delete their own items."""
        self.client.login(username="creator", password="testpass123")

        response = self.client.post(self.delete_url)

        self.assertEqual(response.status_code, 302)

        self.item.refresh_from_db()
        self.assertTrue(self.item.is_deleted)
        self.assertEqual(self.item.deleted_by, self.item_creator)

    def test_player_cannot_delete_others_item(self):
        """Test that players cannot delete items they didn't create."""
        self.client.login(username="player", password="testpass123")

        response = self.client.post(self.delete_url)

        self.assertEqual(response.status_code, 404)  # Hide existence

        self.item.refresh_from_db()
        self.assertFalse(self.item.is_deleted)

    def test_observer_cannot_delete_item(self):
        """Test that observers cannot delete items."""
        self.client.login(username="observer", password="testpass123")

        response = self.client.post(self.delete_url)

        self.assertEqual(response.status_code, 404)

        self.item.refresh_from_db()
        self.assertFalse(self.item.is_deleted)

    def test_delete_requires_post_method(self):
        """Test that deletion requires POST method."""
        self.client.login(username="owner", password="testpass123")

        response = self.client.get(self.delete_url)

        # Should show confirmation form or redirect, not delete
        self.assertNotEqual(response.status_code, 302)

        self.item.refresh_from_db()
        self.assertFalse(self.item.is_deleted)

    def test_delete_shows_confirmation_message(self):
        """Test that successful deletion shows confirmation message."""
        self.client.login(username="owner", password="testpass123")

        response = self.client.post(self.delete_url, follow=True)

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("deleted" in str(message).lower() for message in messages))
