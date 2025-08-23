"""
Tests for Item management interface integration.

Tests cover all requirements from Issue #54:
1. Integration with campaign management interface
2. Character detail pages show owned items
3. URL patterns and navigation work correctly
4. Cross-app functionality and relationships
5. End-to-end workflow testing
"""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from campaigns.models import Campaign, CampaignMembership
from characters.models import Character
from items.models import Item

User = get_user_model()


class ItemCampaignIntegrationTest(TestCase):
    """Test integration between items and campaign management."""

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

        # Create campaign
        self.campaign = Campaign.objects.create(
            name="Integration Test Campaign",
            player_owner=self.owner,
            game_system="Mage: The Ascension",
        )

        # Create memberships
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm, role="GM"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )

        # Create character and items
        self.character = Character.objects.create(
            name="Test Character",
            player_owner=self.player,
            campaign=self.campaign,
        )

        self.item1 = Item.objects.create(
            name="Character Item",
            description="An item owned by the character",
            quantity=1,
            campaign=self.campaign,
            created_by=self.owner,
            player_owner=self.character,
        )

        self.item2 = Item.objects.create(
            name="Campaign Item",
            description="An unowned campaign item",
            quantity=5,
            campaign=self.campaign,
            created_by=self.gm,
        )

    def test_campaign_detail_shows_item_management_link(self):
        """Test that campaign detail page includes link to item management."""
        self.client.login(username="owner", password="testpass123")

        campaign_detail_url = reverse(
            "campaigns:detail", kwargs={"slug": self.campaign.slug}
        )
        response = self.client.get(campaign_detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Items")
        
        # Check for link to items management
        items_url = reverse(
            "items:campaign_items", kwargs={"campaign_slug": self.campaign.slug}
        )
        self.assertContains(response, items_url)

    def test_campaign_detail_shows_item_count(self):
        """Test that campaign detail page shows item count."""
        self.client.login(username="owner", password="testpass123")

        campaign_detail_url = reverse(
            "campaigns:detail", kwargs={"slug": self.campaign.slug}
        )
        response = self.client.get(campaign_detail_url)

        self.assertEqual(response.status_code, 200)
        # Should show item count (2 items total)
        self.assertContains(response, "2")  # Item count

    def test_campaign_navigation_to_items(self):
        """Test navigation from campaign to items works correctly."""
        self.client.login(username="owner", password="testpass123")

        # Start at campaign detail
        campaign_detail_url = reverse(
            "campaigns:detail", kwargs={"slug": self.campaign.slug}
        )
        response = self.client.get(campaign_detail_url)

        # Navigate to items
        items_url = reverse(
            "items:campaign_items", kwargs={"campaign_slug": self.campaign.slug}
        )
        response = self.client.get(items_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Character Item")
        self.assertContains(response, "Campaign Item")

    def test_campaign_breadcrumb_navigation(self):
        """Test breadcrumb navigation from items back to campaign."""
        self.client.login(username="owner", password="testpass123")

        items_url = reverse(
            "items:campaign_items", kwargs={"campaign_slug": self.campaign.slug}
        )
        response = self.client.get(items_url)

        self.assertEqual(response.status_code, 200)
        
        # Should have breadcrumb back to campaign
        campaign_detail_url = reverse(
            "campaigns:detail", kwargs={"slug": self.campaign.slug}
        )
        self.assertContains(response, campaign_detail_url)
        self.assertContains(response, self.campaign.name)


class ItemCharacterIntegrationTest(TestCase):
    """Test integration between items and character management."""

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
            name="Character Integration Campaign",
            player_owner=self.owner,
            game_system="Mage: The Ascension",
        )

        # Create membership
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )

        # Create character and items
        self.character = Character.objects.create(
            name="Equipped Character",
            player_owner=self.player,
            campaign=self.campaign,
        )

        self.owned_item1 = Item.objects.create(
            name="Magic Sword",
            description="A powerful blade",
            quantity=1,
            campaign=self.campaign,
            created_by=self.owner,
            player_owner=self.character,
        )

        self.owned_item2 = Item.objects.create(
            name="Health Potion",
            description="Restores vitality",
            quantity=3,
            campaign=self.campaign,
            created_by=self.owner,
            player_owner=self.character,
        )

        self.unowned_item = Item.objects.create(
            name="Treasure Chest",
            description="A chest full of gold",
            quantity=1,
            campaign=self.campaign,
            created_by=self.owner,
        )

    def test_character_detail_shows_owned_items(self):
        """Test that character detail page shows character's items."""
        self.client.login(username="player", password="testpass123")

        character_detail_url = reverse(
            "characters:detail",
            kwargs={
                "campaign_slug": self.campaign.slug,
                "character_id": self.character.id,
            },
        )
        response = self.client.get(character_detail_url)

        self.assertEqual(response.status_code, 200)
        
        # Should show owned items
        self.assertContains(response, "Magic Sword")
        self.assertContains(response, "Health Potion")
        self.assertContains(response, "Possessions")  # Section header
        
        # Should not show unowned items
        self.assertNotContains(response, "Treasure Chest")

    def test_character_detail_shows_item_quantities(self):
        """Test that character detail shows item quantities."""
        self.client.login(username="player", password="testpass123")

        character_detail_url = reverse(
            "characters:detail",
            kwargs={
                "campaign_slug": self.campaign.slug,
                "character_id": self.character.id,
            },
        )
        response = self.client.get(character_detail_url)

        self.assertEqual(response.status_code, 200)
        
        # Should show quantities
        self.assertContains(response, "1")  # Magic Sword quantity
        self.assertContains(response, "3")  # Health Potion quantity

    def test_character_detail_links_to_item_details(self):
        """Test that character detail has links to individual item details."""
        self.client.login(username="player", password="testpass123")

        character_detail_url = reverse(
            "characters:detail",
            kwargs={
                "campaign_slug": self.campaign.slug,
                "character_id": self.character.id,
            },
        )
        response = self.client.get(character_detail_url)

        self.assertEqual(response.status_code, 200)
        
        # Should have links to item detail pages
        item_detail_url = reverse(
            "items:detail",
            kwargs={
                "campaign_slug": self.campaign.slug,
                "item_id": self.owned_item1.id,
            },
        )
        self.assertContains(response, item_detail_url)

    def test_character_item_list_filtering(self):
        """Test that item list can be filtered by character owner."""
        self.client.login(username="owner", password="testpass123")

        items_url = reverse(
            "items:campaign_items", kwargs={"campaign_slug": self.campaign.slug}
        )
        
        # Filter by character owner
        response = self.client.get(items_url, {"owner": self.character.id})

        self.assertEqual(response.status_code, 200)
        
        # Should show only items owned by this character
        self.assertContains(response, "Magic Sword")
        self.assertContains(response, "Health Potion")
        self.assertNotContains(response, "Treasure Chest")

    def test_character_deletion_handles_items(self):
        """Test that character deletion properly handles owned items."""
        self.client.login(username="owner", password="testpass123")

        # Delete the character (this should be handled by the Character model's deletion)
        self.character.delete()

        # Items should become unowned (owner=NULL due to SET_NULL)
        self.owned_item1.refresh_from_db()
        self.owned_item2.refresh_from_db()
        
        self.assertIsNone(self.owned_item1.owner)
        self.assertIsNone(self.owned_item2.owner)


class ItemURLPatternsTest(TestCase):
    """Test URL patterns and routing for item management."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        self.user = User.objects.create_user(
            username="testuser", email="test@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="URL Test Campaign",
            player_owner=self.user,
            game_system="Mage: The Ascension",
        )

        self.character = Character.objects.create(
            name="URL Test Character",
            player_owner=self.user,
            campaign=self.campaign,
        )

        self.item = Item.objects.create(
            name="URL Test Item",
            quantity=1,
            campaign=self.campaign,
            created_by=self.user,
            player_owner=self.character,
        )

    def test_item_list_url_pattern(self):
        """Test that item list URL pattern works correctly."""
        url = reverse("items:campaign_items", kwargs={"campaign_slug": self.campaign.slug})
        
        self.assertEqual(url, f"/items/campaigns/{self.campaign.slug}/")
        
        # Test that URL is accessible
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_item_create_url_pattern(self):
        """Test that item create URL pattern works correctly."""
        url = reverse("items:create", kwargs={"campaign_slug": self.campaign.slug})
        
        expected_url = f"/items/campaigns/{self.campaign.slug}/create/"
        self.assertEqual(url, expected_url)

    def test_item_detail_url_pattern(self):
        """Test that item detail URL pattern works correctly."""
        url = reverse(
            "items:detail",
            kwargs={"campaign_slug": self.campaign.slug, "item_id": self.item.id},
        )
        
        expected_url = f"/items/campaigns/{self.campaign.slug}/{self.item.id}/"
        self.assertEqual(url, expected_url)

    def test_item_edit_url_pattern(self):
        """Test that item edit URL pattern works correctly."""
        url = reverse(
            "items:edit",
            kwargs={"campaign_slug": self.campaign.slug, "item_id": self.item.id},
        )
        
        expected_url = f"/items/campaigns/{self.campaign.slug}/{self.item.id}/edit/"
        self.assertEqual(url, expected_url)

    def test_item_delete_url_pattern(self):
        """Test that item delete URL pattern works correctly."""
        url = reverse(
            "items:delete",
            kwargs={"campaign_slug": self.campaign.slug, "item_id": self.item.id},
        )
        
        expected_url = f"/items/campaigns/{self.campaign.slug}/{self.item.id}/delete/"
        self.assertEqual(url, expected_url)

    def test_invalid_campaign_slug_returns_404(self):
        """Test that invalid campaign slug returns 404."""
        self.client.login(username="testuser", password="testpass123")
        
        url = reverse("items:campaign_items", kwargs={"campaign_slug": "nonexistent-campaign"})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)

    def test_invalid_item_id_returns_404(self):
        """Test that invalid item ID returns 404."""
        self.client.login(username="testuser", password="testpass123")
        
        url = reverse(
            "items:detail",
            kwargs={"campaign_slug": self.campaign.slug, "item_id": 99999},
        )
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)


class ItemWorkflowIntegrationTest(TestCase):
    """Test end-to-end workflows for item management."""

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

        # Create campaign
        self.campaign = Campaign.objects.create(
            name="Workflow Test Campaign",
            player_owner=self.owner,
            game_system="Mage: The Ascension",
        )

        # Create memberships
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm, role="GM"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )

        # Create characters
        self.character1 = Character.objects.create(
            name="Character One",
            player_owner=self.player,
            campaign=self.campaign,
        )
        self.character2 = Character.objects.create(
            name="Character Two",
            player_owner=self.gm,
            campaign=self.campaign,
        )

    def test_complete_item_management_workflow(self):
        """Test complete workflow: create -> view -> edit -> transfer -> delete."""
        self.client.login(username="owner", password="testpass123")

        # Step 1: Create item
        create_url = reverse("items:create", kwargs={"campaign_slug": self.campaign.slug})
        create_data = {
            "name": "Workflow Test Item",
            "description": "Testing complete workflow",
            "quantity": 2,
            "owner": self.character1.id,
        }
        
        response = self.client.post(create_url, create_data)
        self.assertEqual(response.status_code, 302)  # Redirect after creation

        # Find the created item
        item = Item.objects.get(name="Workflow Test Item")
        self.assertEqual(item.owner, self.character1)

        # Step 2: View item detail
        detail_url = reverse(
            "items:detail",
            kwargs={"campaign_slug": self.campaign.slug, "item_id": item.id},
        )
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Workflow Test Item")

        # Step 3: Edit item and transfer ownership
        edit_url = reverse(
            "items:edit",
            kwargs={"campaign_slug": self.campaign.slug, "item_id": item.id},
        )
        edit_data = {
            "name": "Updated Workflow Item",
            "description": "Updated description",
            "quantity": 3,
            "owner": self.character2.id,  # Transfer to different character
        }
        
        response = self.client.post(edit_url, edit_data)
        self.assertEqual(response.status_code, 302)

        # Verify changes
        item.refresh_from_db()
        self.assertEqual(item.name, "Updated Workflow Item")
        self.assertEqual(item.quantity, 3)
        self.assertEqual(item.owner, self.character2)
        self.assertIsNotNone(item.last_transferred_at)

        # Step 4: Delete item
        delete_url = reverse(
            "items:delete",
            kwargs={"campaign_slug": self.campaign.slug, "item_id": item.id},
        )
        response = self.client.post(delete_url)
        self.assertEqual(response.status_code, 302)

        # Verify soft deletion
        item.refresh_from_db()
        self.assertTrue(item.is_deleted)
        self.assertEqual(item.deleted_by, self.owner)

    def test_gm_item_creation_and_management_workflow(self):
        """Test that GMs can create and manage items effectively."""
        self.client.login(username="gm", password="testpass123")

        # GM creates item for campaign
        create_url = reverse("items:create", kwargs={"campaign_slug": self.campaign.slug})
        create_data = {
            "name": "GM Created Treasure",
            "description": "Treasure created by GM",
            "quantity": 1,
        }
        
        response = self.client.post(create_url, create_data)
        self.assertEqual(response.status_code, 302)

        # Find the created item
        item = Item.objects.get(name="GM Created Treasure")
        self.assertEqual(item.created_by, self.gm)
        self.assertIsNone(item.owner)  # No initial owner

        # GM assigns item to character
        edit_url = reverse(
            "items:edit",
            kwargs={"campaign_slug": self.campaign.slug, "item_id": item.id},
        )
        edit_data = {
            "name": "GM Created Treasure",
            "description": "Treasure created by GM",
            "quantity": 1,
            "owner": self.character1.id,  # Assign to character
        }
        
        response = self.client.post(edit_url, edit_data)
        self.assertEqual(response.status_code, 302)

        # Verify assignment
        item.refresh_from_db()
        self.assertEqual(item.owner, self.character1)
        self.assertIsNotNone(item.last_transferred_at)

    def test_player_view_only_workflow(self):
        """Test that players can view but not modify items."""
        # Create an item as owner
        item = Item.objects.create(
            name="Player View Test Item",
            description="For testing player view access",
            quantity=1,
            campaign=self.campaign,
            created_by=self.owner,
            player_owner=self.character1,
        )

        self.client.login(username="player", password="testpass123")

        # Player can view item list
        list_url = reverse("items:campaign_items", kwargs={"campaign_slug": self.campaign.slug})
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Player View Test Item")

        # Player can view item detail
        detail_url = reverse(
            "items:detail",
            kwargs={"campaign_slug": self.campaign.slug, "item_id": item.id},
        )
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Player View Test Item")

        # Player cannot access create form
        create_url = reverse("items:create", kwargs={"campaign_slug": self.campaign.slug})
        response = self.client.get(create_url)
        self.assertEqual(response.status_code, 404)

        # Player cannot access edit form
        edit_url = reverse(
            "items:edit",
            kwargs={"campaign_slug": self.campaign.slug, "item_id": item.id},
        )
        response = self.client.get(edit_url)
        self.assertEqual(response.status_code, 404)

        # Player cannot delete item
        delete_url = reverse(
            "items:delete",
            kwargs={"campaign_slug": self.campaign.slug, "item_id": item.id},
        )
        response = self.client.post(delete_url)
        self.assertEqual(response.status_code, 404)

    def test_cross_campaign_isolation_workflow(self):
        """Test that items are properly isolated between campaigns."""
        # Create another campaign
        other_campaign = Campaign.objects.create(
            name="Other Campaign",
            player_owner=self.owner,
            game_system="Vampire: The Masquerade",
        )

        other_character = Character.objects.create(
            name="Other Character",
            player_owner=self.owner,
            campaign=other_campaign,
        )

        # Create items in both campaigns
        item1 = Item.objects.create(
            name="Campaign 1 Item",
            quantity=1,
            campaign=self.campaign,
            created_by=self.owner,
        )

        item2 = Item.objects.create(
            name="Campaign 2 Item",
            quantity=1,
            campaign=other_campaign,
            created_by=self.owner,
        )

        self.client.login(username="owner", password="testpass123")

        # Items in first campaign
        list_url1 = reverse("items:campaign_items", kwargs={"campaign_slug": self.campaign.slug})
        response = self.client.get(list_url1)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Campaign 1 Item")
        self.assertNotContains(response, "Campaign 2 Item")

        # Items in second campaign
        list_url2 = reverse("items:campaign_items", kwargs={"campaign_slug": other_campaign.slug})
        response = self.client.get(list_url2)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Campaign 2 Item")
        self.assertNotContains(response, "Campaign 1 Item")

        # Cannot edit item from other campaign
        edit_url = reverse(
            "items:edit",
            kwargs={"campaign_slug": self.campaign.slug, "item_id": item2.id},
        )
        response = self.client.get(edit_url)
        self.assertEqual(response.status_code, 404)  # Item doesn't exist in this campaign context