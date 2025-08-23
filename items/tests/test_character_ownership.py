"""
Tests for Item character ownership conversion (Issue #183).

Tests conversion from many-to-many `owners` to single `owner` ForeignKey
with new functionality including transfer methods and updated relationships.

Test Requirements:
1. Basic ownership functionality (PCs, NPCs, unowned items)
2. Transfer method behavior with timestamp tracking
3. Manager/QuerySet compatibility with single ownership
4. Character relationship testing (possessions)
5. Data migration compatibility simulation
6. Integration testing with existing features
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import transaction
from django.test import TestCase
from django.utils import timezone

from campaigns.models import Campaign, CampaignMembership
from characters.models import Character
from items.models import Item

User = get_user_model()


class ItemSingleOwnershipBasicTest(TestCase):
    """Test basic single ownership functionality."""

    def setUp(self):
        """Set up test users, campaigns, and characters."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.player = User.objects.create_user(
            username="player", email="player@test.com", password="testpass123"
        )
        self.gm = User.objects.create_user(
            username="gm", email="gm@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            game_system="Mage: The Ascension",
        )

        # Create memberships
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm, role="GM"
        )

        # Create Player Character (PC)
        self.pc_character = Character.objects.create(
            name="PC Character",
            description="A player character",
            campaign=self.campaign,
            player_owner=self.player,
            game_system="Mage: The Ascension",
            npc=False,
        )

        # Create Non-Player Character (NPC)
        self.npc_character = Character.objects.create(
            name="NPC Character",
            description="A non-player character",
            campaign=self.campaign,
            player_owner=self.gm,
            game_system="Mage: The Ascension",
            npc=True,
        )

    def test_item_owned_by_pc(self):
        """Test item can be owned by Player Character."""
        item = Item.objects.create(
            name="PC Sword",
            description="A sword owned by PC",
            campaign=self.campaign,
            created_by=self.player,
            owner=self.pc_character,
        )

        self.assertEqual(item.owner, self.pc_character)
        self.assertFalse(item.owner.npc)
        self.assertEqual(item.owner.player_owner, self.player)

    def test_item_owned_by_npc(self):
        """Test item can be owned by Non-Player Character."""
        item = Item.objects.create(
            name="NPC Staff",
            description="A staff owned by NPC",
            campaign=self.campaign,
            created_by=self.gm,
            owner=self.npc_character,
        )

        self.assertEqual(item.owner, self.npc_character)
        self.assertTrue(item.owner.npc)
        self.assertEqual(item.owner.player_owner, self.gm)

    def test_item_unowned(self):
        """Test item can be unowned (owner=None)."""
        item = Item.objects.create(
            name="Unowned Treasure",
            description="A treasure with no owner",
            campaign=self.campaign,
            created_by=self.owner,
            owner=None,
        )

        self.assertIsNone(item.owner)

    def test_character_possessions_relationship(self):
        """Test Character.possessions returns owned items correctly."""
        # Create items with different ownership
        pc_item = Item.objects.create(
            name="PC Item",
            campaign=self.campaign,
            created_by=self.player,
            owner=self.pc_character,
        )
        npc_item = Item.objects.create(
            name="NPC Item",
            campaign=self.campaign,
            created_by=self.gm,
            owner=self.npc_character,
        )
        unowned_item = Item.objects.create(
            name="Unowned Item",
            campaign=self.campaign,
            created_by=self.owner,
            owner=None,
        )

        # Test PC possessions
        pc_possessions = self.pc_character.possessions.all()
        self.assertIn(pc_item, pc_possessions)
        self.assertNotIn(npc_item, pc_possessions)
        self.assertNotIn(unowned_item, pc_possessions)

        # Test NPC possessions
        npc_possessions = self.npc_character.possessions.all()
        self.assertIn(npc_item, npc_possessions)
        self.assertNotIn(pc_item, npc_possessions)
        self.assertNotIn(unowned_item, npc_possessions)

    def test_foreign_key_constraints(self):
        """Test ForeignKey constraints and nullable behavior."""
        # Test valid ForeignKey assignment
        item = Item.objects.create(
            name="Test Item",
            campaign=self.campaign,
            created_by=self.player,
            owner=self.pc_character,
        )
        self.assertEqual(item.owner_id, self.pc_character.id)

        # Test nullable assignment
        item.owner = None
        item.save()
        item.refresh_from_db()
        self.assertIsNone(item.owner)
        self.assertIsNone(item.owner_id)


class ItemTransferMethodTest(TestCase):
    """Test Item.transfer_to() method functionality."""

    def setUp(self):
        """Set up test data for transfer testing."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.player1 = User.objects.create_user(
            username="player1", email="player1@test.com", password="testpass123"
        )
        self.player2 = User.objects.create_user(
            username="player2", email="player2@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            game_system="Mage: The Ascension",
        )

        # Create memberships
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player1, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player2, role="PLAYER"
        )

        # Create characters
        self.character1 = Character.objects.create(
            name="Character 1",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )
        self.character2 = Character.objects.create(
            name="Character 2",
            campaign=self.campaign,
            player_owner=self.player2,
            game_system="Mage: The Ascension",
        )

    def test_transfer_to_method_exists(self):
        """Test that transfer_to method exists on Item model."""
        item = Item.objects.create(
            name="Test Item",
            campaign=self.campaign,
            created_by=self.player1,
            owner=self.character1,
        )

        # Method should exist and be callable
        self.assertTrue(hasattr(item, "transfer_to"))
        self.assertTrue(callable(getattr(item, "transfer_to")))

    def test_transfer_between_characters(self):
        """Test transferring item between different characters."""
        item = Item.objects.create(
            name="Transferable Item",
            campaign=self.campaign,
            created_by=self.player1,
            owner=self.character1,
        )

        # Record initial state
        self.assertEqual(item.owner, self.character1)
        initial_timestamp = item.last_transferred_at

        # Perform transfer
        with patch("django.utils.timezone.now") as mock_now:
            mock_timestamp = timezone.now()
            mock_now.return_value = mock_timestamp

            result = item.transfer_to(self.character2)

            # Verify return value
            self.assertEqual(result, item)

            # Verify ownership changed
            item.refresh_from_db()
            self.assertEqual(item.owner, self.character2)

            # Verify timestamp updated
            self.assertEqual(item.last_transferred_at, mock_timestamp)
            self.assertNotEqual(item.last_transferred_at, initial_timestamp)

    def test_transfer_to_unowned(self):
        """Test transferring item to unowned state (owner=None)."""
        item = Item.objects.create(
            name="Item to Abandon",
            campaign=self.campaign,
            created_by=self.player1,
            owner=self.character1,
        )

        # Transfer to None (unowned)
        with patch("django.utils.timezone.now") as mock_now:
            mock_timestamp = timezone.now()
            mock_now.return_value = mock_timestamp

            item.transfer_to(None)

            # Verify ownership cleared
            item.refresh_from_db()
            self.assertIsNone(item.owner)

            # Verify timestamp updated
            self.assertEqual(item.last_transferred_at, mock_timestamp)

    def test_transfer_from_unowned(self):
        """Test transferring unowned item to character."""
        item = Item.objects.create(
            name="Unowned Item",
            campaign=self.campaign,
            created_by=self.owner,
            owner=None,
        )

        # Transfer from unowned to character
        with patch("django.utils.timezone.now") as mock_now:
            mock_timestamp = timezone.now()
            mock_now.return_value = mock_timestamp

            item.transfer_to(self.character1)

            # Verify ownership assigned
            item.refresh_from_db()
            self.assertEqual(item.owner, self.character1)

            # Verify timestamp updated
            self.assertEqual(item.last_transferred_at, mock_timestamp)

    def test_transfer_to_same_owner_no_op(self):
        """Test transferring to same owner is no-op but updates timestamp."""
        item = Item.objects.create(
            name="Same Owner Item",
            campaign=self.campaign,
            created_by=self.player1,
            owner=self.character1,
        )

        # Transfer to same character
        with patch("django.utils.timezone.now") as mock_now:
            mock_timestamp = timezone.now()
            mock_now.return_value = mock_timestamp

            item.transfer_to(self.character1)

            # Verify owner unchanged
            item.refresh_from_db()
            self.assertEqual(item.owner, self.character1)

            # Verify timestamp still updated (transfer attempt recorded)
            self.assertEqual(item.last_transferred_at, mock_timestamp)

    def test_last_transferred_at_field_exists(self):
        """Test that last_transferred_at field exists and works correctly."""
        item = Item.objects.create(
            name="Timestamp Test Item",
            campaign=self.campaign,
            created_by=self.player1,
            owner=self.character1,
        )

        # Field should exist
        self.assertTrue(hasattr(item, "last_transferred_at"))

        # After transfer, should have a timestamp
        with patch("django.utils.timezone.now") as mock_now:
            mock_timestamp = timezone.now()
            mock_now.return_value = mock_timestamp

            item.transfer_to(self.character2)
            item.refresh_from_db()
            self.assertEqual(item.last_transferred_at, mock_timestamp)


class ItemQuerySetSingleOwnershipTest(TestCase):
    """Test QuerySet methods work with single ownership field."""

    def setUp(self):
        """Set up test data for QuerySet testing."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.player = User.objects.create_user(
            username="player", email="player@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            game_system="Mage: The Ascension",
        )

        # Create membership for player
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )

        self.character = Character.objects.create(
            name="Test Character",
            campaign=self.campaign,
            player_owner=self.player,
            game_system="Mage: The Ascension",
        )

    def test_owned_by_character_queryset_method(self):
        """Test owned_by_character() QuerySet method works with single owner."""
        # Create items with different ownership
        owned_item = Item.objects.create(
            name="Owned Item",
            campaign=self.campaign,
            created_by=self.player,
            owner=self.character,
        )
        unowned_item = Item.objects.create(
            name="Unowned Item",
            campaign=self.campaign,
            created_by=self.owner,
            owner=None,
        )

        # Test QuerySet filtering
        owned_items = Item.objects.owned_by_character(self.character)
        self.assertIn(owned_item, owned_items)
        self.assertNotIn(unowned_item, owned_items)

    def test_owned_by_character_manager_method(self):
        """Test owned_by_character() Manager method works with single owner."""
        # Create items
        owned_item = Item.objects.create(
            name="Manager Owned Item",
            campaign=self.campaign,
            created_by=self.player,
            owner=self.character,
        )
        unowned_item = Item.objects.create(
            name="Manager Unowned Item",
            campaign=self.campaign,
            created_by=self.owner,
            owner=None,
        )

        # Test Manager method
        owned_items = Item.objects.owned_by_character(self.character)
        self.assertIn(owned_item, owned_items)
        self.assertNotIn(unowned_item, owned_items)

    def test_owned_by_character_none_parameter(self):
        """Test owned_by_character() handles None parameter correctly."""
        # Create an item
        Item.objects.create(
            name="Test Item",
            campaign=self.campaign,
            created_by=self.player,
            owner=self.character,
        )

        # Test with None - should return empty QuerySet
        result = Item.objects.owned_by_character(None)
        self.assertEqual(result.count(), 0)

    def test_queryset_chaining_with_ownership(self):
        """Test QuerySet chaining works with ownership filtering."""
        # Create different types of items
        active_owned = Item.objects.create(
            name="Active Owned",
            campaign=self.campaign,
            created_by=self.player,
            owner=self.character,
        )
        deleted_owned = Item.objects.create(
            name="Deleted Owned",
            campaign=self.campaign,
            created_by=self.player,
            owner=self.character,
        )
        deleted_owned.soft_delete(self.owner)

        # Test chaining active() and owned_by_character()
        active_owned_items = Item.all_objects.active().owned_by_character(
            self.character
        )
        self.assertIn(active_owned, active_owned_items)
        self.assertNotIn(deleted_owned, active_owned_items)

        # Test chaining for_campaign() and owned_by_character()
        campaign_owned_items = Item.objects.for_campaign(
            self.campaign
        ).owned_by_character(self.character)
        self.assertIn(active_owned, campaign_owned_items)
        # deleted_owned not included because objects manager excludes deleted


class ItemCharacterRelationshipTest(TestCase):
    """Test Character-Item relationship functionality."""

    def setUp(self):
        """Set up test data for relationship testing."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.player1 = User.objects.create_user(
            username="player1", email="player1@test.com", password="testpass123"
        )
        self.player2 = User.objects.create_user(
            username="player2", email="player2@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            game_system="Mage: The Ascension",
        )

        # Create memberships
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player1, role="PLAYER"
        )

        # Create both PC and NPC
        self.pc_character = Character.objects.create(
            name="PC Character",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
            npc=False,
        )
        self.npc_character = Character.objects.create(
            name="NPC Character",
            campaign=self.campaign,
            player_owner=self.owner,  # GM owns NPC
            game_system="Mage: The Ascension",
            npc=True,
        )

    def test_possessions_related_name(self):
        """Test Character.possessions related name works correctly."""
        # Create items for both characters
        pc_item1 = Item.objects.create(
            name="PC Item 1",
            campaign=self.campaign,
            created_by=self.player1,
            owner=self.pc_character,
        )
        pc_item2 = Item.objects.create(
            name="PC Item 2",
            campaign=self.campaign,
            created_by=self.player1,
            owner=self.pc_character,
        )
        npc_item = Item.objects.create(
            name="NPC Item",
            campaign=self.campaign,
            created_by=self.owner,
            owner=self.npc_character,
        )

        # Test PC possessions
        pc_possessions = list(self.pc_character.possessions.all())
        self.assertIn(pc_item1, pc_possessions)
        self.assertIn(pc_item2, pc_possessions)
        self.assertNotIn(npc_item, pc_possessions)
        self.assertEqual(len(pc_possessions), 2)

        # Test NPC possessions
        npc_possessions = list(self.npc_character.possessions.all())
        self.assertIn(npc_item, npc_possessions)
        self.assertNotIn(pc_item1, npc_possessions)
        self.assertNotIn(pc_item2, npc_possessions)
        self.assertEqual(len(npc_possessions), 1)

    def test_both_pc_and_npc_ownership(self):
        """Test both Player Characters and NPCs can own items."""
        # PC ownership
        pc_item = Item.objects.create(
            name="PC Weapon",
            campaign=self.campaign,
            created_by=self.player1,
            owner=self.pc_character,
        )
        self.assertEqual(pc_item.owner, self.pc_character)
        self.assertFalse(pc_item.owner.npc)

        # NPC ownership
        npc_item = Item.objects.create(
            name="NPC Treasure",
            campaign=self.campaign,
            created_by=self.owner,
            owner=self.npc_character,
        )
        self.assertEqual(npc_item.owner, self.npc_character)
        self.assertTrue(npc_item.owner.npc)

    def test_character_deletion_cascade_behavior(self):
        """Test cascade behavior when character is deleted."""
        # Create item owned by character
        item = Item.objects.create(
            name="Character Item",
            campaign=self.campaign,
            created_by=self.player1,
            owner=self.pc_character,
        )

        # Verify initial ownership
        self.assertEqual(item.owner, self.pc_character)

        # Delete the character (this should trigger cascade behavior)
        self.pc_character.delete()

        # Test that item handles character deletion appropriately
        # This depends on the ForeignKey's on_delete behavior
        item.refresh_from_db()
        # If SET_NULL: owner should be None
        # If CASCADE: item should be deleted
        # If PROTECT: deletion should be prevented
        # Test based on expected behavior (assuming SET_NULL for safety)
        try:
            item.refresh_from_db()
            # If item still exists, owner should be None (SET_NULL)
            self.assertIsNone(item.owner)
        except Item.DoesNotExist:
            # If item was deleted (CASCADE), that's also valid
            pass


class ItemDataMigrationCompatibilityTest(TestCase):
    """Test data migration compatibility for many-to-many to ForeignKey conversion."""

    def setUp(self):
        """Set up test data for migration simulation."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.player1 = User.objects.create_user(
            username="player1", email="player1@test.com", password="testpass123"
        )
        self.player2 = User.objects.create_user(
            username="player2", email="player2@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Migration Test Campaign",
            owner=self.owner,
            game_system="Mage: The Ascension",
        )

        # Create memberships
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player1, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player2, role="PLAYER"
        )

        self.character1 = Character.objects.create(
            name="Character 1",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )
        self.character2 = Character.objects.create(
            name="Character 2",
            campaign=self.campaign,
            player_owner=self.player2,
            game_system="Mage: The Ascension",
        )

    def test_single_owner_migration_simulation(self):
        """Simulate migration of item with single owner from many-to-many."""
        # This test simulates what would happen during migration
        # when an item had exactly one owner in the many-to-many field

        item = Item.objects.create(
            name="Single Owner Item",
            campaign=self.campaign,
            created_by=self.player1,
        )

        # Simulate current many-to-many state (would be handled by migration)
        # In real migration, this would read from the m2m table and set owner field
        item.owner = self.character1
        item.save()

        # Verify the conversion worked
        self.assertEqual(item.owner, self.character1)

        # Verify possessions relationship
        self.assertIn(item, self.character1.possessions.all())

    def test_multiple_owner_migration_edge_case(self):
        """Test handling of items with multiple owners during migration."""
        # This test documents expected behavior when an item had multiple owners
        # The migration would need to handle this case (e.g., pick first owner)

        item = Item.objects.create(
            name="Multi Owner Item",
            campaign=self.campaign,
            created_by=self.player1,
        )

        # Simulate migration decision: pick first owner or handle as unowned
        # This documents the expected migration behavior
        item.owner = self.character1  # Migration strategy: pick first
        item.save()

        # Verify single ownership
        self.assertEqual(item.owner, self.character1)

    def test_unowned_item_migration(self):
        """Test migration of items with no owners."""
        item = Item.objects.create(
            name="No Owner Item",
            campaign=self.campaign,
            created_by=self.owner,
            owner=None,  # This would be the migration result for unowned items
        )

        # Verify unowned state
        self.assertIsNone(item.owner)

    def test_migration_preserves_other_fields(self):
        """Test that migration preserves all other Item fields."""
        item = Item.objects.create(
            name="Migration Test Item",
            description="Test description",
            campaign=self.campaign,
            quantity=5,
            created_by=self.player1,
            owner=self.character1,
        )

        # All fields should be preserved
        self.assertEqual(item.name, "Migration Test Item")
        self.assertEqual(item.description, "Test description")
        self.assertEqual(item.campaign, self.campaign)
        self.assertEqual(item.quantity, 5)
        self.assertEqual(item.created_by, self.player1)
        self.assertEqual(item.owner, self.character1)


class ItemIntegrationTest(TestCase):
    """Test integration with existing Item functionality."""

    def setUp(self):
        """Set up comprehensive test data."""
        self.superuser = User.objects.create_superuser(
            username="admin", email="admin@test.com", password="adminpass123"
        )
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.gm = User.objects.create_user(
            username="gm", email="gm@test.com", password="testpass123"
        )
        self.player = User.objects.create_user(
            username="player", email="player@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Integration Test Campaign",
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

        self.character = Character.objects.create(
            name="Integration Character",
            campaign=self.campaign,
            player_owner=self.player,
            game_system="Mage: The Ascension",
        )

    def test_soft_delete_preserves_ownership(self):
        """Test soft delete functionality preserves ownership information."""
        item = Item.objects.create(
            name="Delete Test Item",
            campaign=self.campaign,
            created_by=self.player,
            owner=self.character,
        )

        # Soft delete the item
        item.soft_delete(self.owner)
        item.refresh_from_db()

        # Verify soft delete fields
        self.assertTrue(item.is_deleted)
        self.assertIsNotNone(item.deleted_at)
        self.assertEqual(item.deleted_by, self.owner)

        # Verify ownership preserved
        self.assertEqual(item.owner, self.character)

    def test_restore_preserves_ownership(self):
        """Test restore functionality preserves ownership information."""
        item = Item.objects.create(
            name="Restore Test Item",
            campaign=self.campaign,
            created_by=self.player,
            owner=self.character,
        )

        # Soft delete then restore
        item.soft_delete(self.owner)
        item.restore(self.owner)
        item.refresh_from_db()

        # Verify restoration
        self.assertFalse(item.is_deleted)
        self.assertIsNone(item.deleted_at)
        self.assertIsNone(item.deleted_by)

        # Verify ownership preserved
        self.assertEqual(item.owner, self.character)

    def test_permission_system_with_ownership(self):
        """Test permission system works with single ownership."""
        item = Item.objects.create(
            name="Permission Test Item",
            campaign=self.campaign,
            created_by=self.player,
            owner=self.character,
        )

        # Test various permission levels
        self.assertTrue(item.can_be_deleted_by(self.superuser))
        self.assertTrue(item.can_be_deleted_by(self.owner))  # Campaign owner
        self.assertTrue(item.can_be_deleted_by(self.gm))  # GM
        self.assertTrue(item.can_be_deleted_by(self.player))  # Item creator

        # Create non-member user
        outsider = User.objects.create_user(
            username="outsider", email="outsider@test.com", password="testpass123"
        )
        self.assertFalse(item.can_be_deleted_by(outsider))

    def test_polymorphic_inheritance_compatibility(self):
        """Test that single ownership works with polymorphic inheritance."""
        item = Item.objects.create(
            name="Polymorphic Test Item",
            campaign=self.campaign,
            created_by=self.player,
            owner=self.character,
        )

        # Test polymorphic queries work with ownership
        items_with_owner = Item.objects.filter(owner__isnull=False)
        self.assertIn(item, items_with_owner)

        items_without_owner = Item.objects.filter(owner__isnull=True)
        self.assertNotIn(item, items_without_owner)

    def test_manager_methods_integration(self):
        """Test all manager methods work correctly with single ownership."""
        # Create various items
        owned_item = Item.objects.create(
            name="Owned Item",
            campaign=self.campaign,
            created_by=self.player,
            owner=self.character,
        )
        unowned_item = Item.objects.create(
            name="Unowned Item",
            campaign=self.campaign,
            created_by=self.owner,
            owner=None,
        )
        deleted_item = Item.objects.create(
            name="Deleted Item",
            campaign=self.campaign,
            created_by=self.player,
            owner=self.character,
        )
        deleted_item.soft_delete(self.owner)

        # Test active manager
        active_items = Item.objects.active()
        self.assertIn(owned_item, active_items)
        self.assertIn(unowned_item, active_items)
        self.assertNotIn(deleted_item, active_items)

        # Test for_campaign manager
        campaign_items = Item.objects.for_campaign(self.campaign)
        self.assertIn(owned_item, campaign_items)
        self.assertIn(unowned_item, campaign_items)
        self.assertNotIn(deleted_item, campaign_items)

        # Test owned_by_character manager
        character_items = Item.objects.owned_by_character(self.character)
        self.assertIn(owned_item, character_items)
        self.assertNotIn(unowned_item, character_items)
        self.assertNotIn(deleted_item, character_items)

        # Test all_objects manager includes deleted
        all_items = Item.all_objects.all()
        self.assertIn(owned_item, all_items)
        self.assertIn(unowned_item, all_items)
        self.assertIn(deleted_item, all_items)


class ItemOwnershipEdgeCasesTest(TestCase):
    """Test edge cases and error conditions for ownership functionality."""

    def setUp(self):
        """Set up test data for edge case testing."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.player = User.objects.create_user(
            username="player", email="player@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Edge Case Campaign",
            owner=self.owner,
            game_system="Mage: The Ascension",
        )

        # Create membership for player
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )

        self.character = Character.objects.create(
            name="Edge Case Character",
            campaign=self.campaign,
            player_owner=self.player,
            game_system="Mage: The Ascension",
        )

    def test_transfer_to_invalid_character(self):
        """Test transfer_to with invalid character parameter."""
        item = Item.objects.create(
            name="Invalid Transfer Item",
            campaign=self.campaign,
            created_by=self.player,
            owner=self.character,
        )

        # Test with non-existent character (invalid ID)
        with self.assertRaises((Character.DoesNotExist, ValueError, AttributeError)):
            # This depends on implementation - could raise different exceptions
            fake_character = Character(id=99999)  # Non-existent
            item.transfer_to(fake_character)

    def test_ownership_with_soft_deleted_character(self):
        """Test ownership behavior with soft-deleted characters."""
        # Create item owned by character
        item = Item.objects.create(
            name="Soft Deleted Character Item",
            campaign=self.campaign,
            created_by=self.player,
            owner=self.character,
        )

        # Soft delete the character
        self.character.is_deleted = True
        self.character.deleted_at = timezone.now()
        self.character.deleted_by = self.owner
        self.character.save()

        # Item should still have ownership reference
        item.refresh_from_db()
        self.assertEqual(item.owner, self.character)

        # But character should be marked as deleted
        self.assertTrue(item.owner.is_deleted)

    def test_bulk_operations_with_ownership(self):
        """Test bulk operations work correctly with ownership."""
        # Create multiple items with different ownership
        items = []
        for i in range(5):
            item = Item.objects.create(
                name=f"Bulk Item {i}",
                campaign=self.campaign,
                created_by=self.player,
                owner=self.character if i % 2 == 0 else None,  # Alternate owned/unowned
            )
            items.append(item)

        # Test bulk update of ownership
        unowned_items = Item.objects.filter(owner__isnull=True)

        # Bulk assign ownership
        unowned_items.update(owner=self.character)

        # Verify all items now owned
        total_owned = Item.objects.filter(owner=self.character).count()
        self.assertEqual(total_owned, 5)  # All items should now be owned

    def test_queryset_performance_with_ownership(self):
        """Test QuerySet performance with ownership relationships."""
        # Create items with ownership
        for i in range(10):
            Item.objects.create(
                name=f"Performance Item {i}",
                campaign=self.campaign,
                created_by=self.player,
                owner=self.character,
            )

        # Test that select_related works for owner relationship
        with self.assertNumQueries(1):  # Should be single query with select_related
            items = Item.objects.select_related("owner").filter(owner=self.character)
            # Access owner attribute to trigger relationship
            for item in items:
                _ = item.owner.name  # Should not trigger additional queries

    def test_concurrent_ownership_changes(self):
        """Test concurrent ownership changes for data integrity."""
        item = Item.objects.create(
            name="Concurrent Test Item",
            campaign=self.campaign,
            created_by=self.player,
            owner=None,
        )

        # Simulate concurrent access (basic test)
        # In a real scenario, this would involve threading or async testing
        with transaction.atomic():
            item.owner = self.character
            item.save()

        # Verify final state
        item.refresh_from_db()
        self.assertEqual(item.owner, self.character)

    def test_string_representation_with_ownership(self):
        """Test string representation includes ownership information appropriately."""
        owned_item = Item.objects.create(
            name="Owned String Item",
            campaign=self.campaign,
            created_by=self.player,
            owner=self.character,
        )
        unowned_item = Item.objects.create(
            name="Unowned String Item",
            campaign=self.campaign,
            created_by=self.player,
            owner=None,
        )

        # Basic string representation should work
        owned_str = str(owned_item)
        unowned_str = str(unowned_item)

        self.assertIsInstance(owned_str, str)
        self.assertIsInstance(unowned_str, str)
        self.assertIn("Owned String Item", owned_str)
        self.assertIn("Unowned String Item", unowned_str)
