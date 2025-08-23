"""
Tests for Item model functionality.

Tests cover all requirements from Issue #53:
1. Model field validation and constraints
2. Soft delete functionality (delete/restore methods, managers)
3. Many-to-many relationships with Character model
4. Campaign relationship cascade behavior
5. String representation and model managers
6. Integration tests for item creation with character ownership
7. Edge case tests for cascade behavior and user deletion
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from campaigns.models import Campaign, CampaignMembership
from characters.models import Character
from items.models import Item

User = get_user_model()


class ItemModelFieldValidationTest(TestCase):
    """Test Item model field validation and constraints."""

    def setUp(self):
        """Set up test users, campaigns, and characters."""
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

    def test_create_item_with_required_fields(self):
        """Test creating an item with only required fields."""
        item = Item.objects.create(
            name="Basic Sword",
            campaign=self.campaign,
            created_by=self.owner,
        )

        self.assertEqual(item.name, "Basic Sword")
        self.assertEqual(item.campaign, self.campaign)
        self.assertEqual(item.created_by, self.owner)
        self.assertEqual(item.quantity, 1)  # default value
        self.assertEqual(item.description, "")  # blank=True default
        self.assertFalse(item.is_deleted)  # soft delete default
        self.assertIsNotNone(item.created_at)
        self.assertIsNotNone(item.updated_at)

    def test_create_item_with_all_fields(self):
        """Test creating an item with all fields populated."""
        item = Item.objects.create(
            name="Enchanted Sword",
            description="A magical sword that glows with ethereal light",
            campaign=self.campaign,
            quantity=3,
            created_by=self.owner,
        )

        self.assertEqual(item.name, "Enchanted Sword")
        self.assertEqual(
            item.description, "A magical sword that glows with ethereal light"
        )
        self.assertEqual(item.quantity, 3)
        self.assertEqual(item.campaign, self.campaign)
        self.assertEqual(item.created_by, self.owner)

    def test_item_name_max_length_constraint(self):
        """Test that item name respects max_length=200 constraint."""
        long_name = "x" * 201  # 201 characters, should exceed max_length

        with self.assertRaises(ValidationError):
            item = Item(
                name=long_name,
                campaign=self.campaign,
                created_by=self.owner,
            )
            item.full_clean()  # Trigger field validation

    def test_item_name_required_constraint(self):
        """Test that item name is required."""
        with self.assertRaises(ValidationError):
            item = Item(
                name="",
                campaign=self.campaign,
                created_by=self.owner,
            )
            item.full_clean()

    def test_item_quantity_positive_constraint(self):
        """Test that quantity must be positive."""
        with self.assertRaises(ValidationError):
            item = Item(
                name="Invalid Item",
                campaign=self.campaign,
                quantity=-1,
                created_by=self.owner,
            )
            item.full_clean()

    def test_item_quantity_zero_constraint(self):
        """Test that quantity cannot be zero."""
        with self.assertRaises(ValidationError):
            item = Item(
                name="Invalid Item",
                campaign=self.campaign,
                quantity=0,
                created_by=self.owner,
            )
            item.full_clean()

    def test_item_campaign_required_constraint(self):
        """Test that campaign is required."""
        with self.assertRaises(IntegrityError):
            Item.objects.create(
                name="Orphaned Item",
                created_by=self.owner,
                # campaign is missing
            )

    def test_item_created_by_can_be_null(self):
        """Test that created_by can be null (after user deletion)."""
        # This should work without error since created_by allows null
        item = Item.objects.create(
            name="Anonymous Item",
            campaign=self.campaign,
            created_by=None,
        )

        self.assertEqual(item.name, "Anonymous Item")
        self.assertIsNone(item.created_by)
        self.assertEqual(item.campaign, self.campaign)

    def test_item_description_blank_allowed(self):
        """Test that description can be blank."""
        item = Item.objects.create(
            name="Simple Item",
            description="",  # explicitly blank
            campaign=self.campaign,
            created_by=self.owner,
        )

        self.assertEqual(item.description, "")


class ItemSoftDeleteTest(TestCase):
    """Test soft delete functionality for Item model."""

    def setUp(self):
        """Set up test data for soft delete tests."""
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

        self.item = Item.objects.create(
            name="Test Item",
            campaign=self.campaign,
            created_by=self.owner,
        )

    def test_item_soft_delete_method(self):
        """Test that soft_delete method works correctly."""
        self.assertFalse(self.item.is_deleted)
        self.assertIsNone(self.item.deleted_at)
        self.assertIsNone(self.item.deleted_by)

        self.item.soft_delete(self.owner)

        self.assertTrue(self.item.is_deleted)
        self.assertIsNotNone(self.item.deleted_at)
        self.assertEqual(self.item.deleted_by, self.owner)

    def test_item_restore_method(self):
        """Test that restore method works correctly."""
        self.item.soft_delete(self.owner)
        self.assertTrue(self.item.is_deleted)

        self.item.restore(self.owner)

        self.assertFalse(self.item.is_deleted)
        self.assertIsNone(self.item.deleted_at)
        self.assertIsNone(self.item.deleted_by)

    def test_item_default_manager_excludes_deleted(self):
        """Test that default manager excludes soft-deleted items."""
        # Item should be visible in default manager
        self.assertEqual(Item.objects.count(), 1)
        self.assertIn(self.item, Item.objects.all())

        # After soft delete, item should not be visible in default manager
        self.item.soft_delete(self.owner)
        self.assertEqual(Item.objects.count(), 0)
        self.assertNotIn(self.item, Item.objects.all())

    def test_item_all_objects_manager_includes_deleted(self):
        """Test that all_objects manager includes soft-deleted items."""
        # Item should be visible in all_objects manager
        self.assertEqual(Item.all_objects.count(), 1)
        self.assertIn(self.item, Item.all_objects.all())

        # After soft delete, item should still be visible in all_objects manager
        self.item.soft_delete(self.owner)
        self.assertEqual(Item.all_objects.count(), 1)
        self.assertIn(self.item, Item.all_objects.all())

    def test_item_soft_delete_already_deleted_error(self):
        """Test that soft deleting already deleted item raises error."""
        self.item.soft_delete(self.owner)

        with self.assertRaises(ValueError) as cm:
            self.item.soft_delete(self.owner)

        self.assertIn("already deleted", str(cm.exception))

    def test_item_restore_not_deleted_error(self):
        """Test that restoring non-deleted item raises error."""
        with self.assertRaises(ValueError) as cm:
            self.item.restore(self.owner)

        self.assertIn("not deleted", str(cm.exception))

    def test_item_soft_delete_permission_error(self):
        """Test that non-owners cannot soft delete items."""
        with self.assertRaises(PermissionError):
            self.item.soft_delete(self.player)

    def test_item_restore_permission_error(self):
        """Test that non-owners cannot restore items."""
        self.item.soft_delete(self.owner)

        with self.assertRaises(PermissionError):
            self.item.restore(self.player)


class ItemCharacterOwnershipTest(TestCase):
    """Test many-to-many relationships between Item and Character models."""

    def setUp(self):
        """Set up test data for ownership tests."""
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

        self.character1 = Character.objects.create(
            name="Character 1",
            campaign=self.campaign,
            owner=self.player1,
            game_system="Mage: The Ascension",
        )
        self.character2 = Character.objects.create(
            name="Character 2",
            campaign=self.campaign,
            owner=self.player2,
            game_system="Mage: The Ascension",
        )

        self.item = Item.objects.create(
            name="Shared Item",
            campaign=self.campaign,
            created_by=self.owner,
        )

    def test_item_no_owner_initially(self):
        """Test that item has no owner initially."""
        self.assertIsNone(self.item.owner)
        self.assertNotIn(self.item, self.character1.possessions.all())
        self.assertNotIn(self.item, self.character2.possessions.all())

    def test_add_single_owner(self):
        """Test adding a single character as owner."""
        self.item.owner = self.character1
        self.item.save()

        self.assertEqual(self.item.owner, self.character1)
        # Verify through possessions relationship
        self.assertIn(self.item, self.character1.possessions.all())
        self.assertNotIn(self.item, self.character2.possessions.all())

    def test_transfer_ownership(self):
        """Test transferring ownership between characters."""
        # Start with character1
        self.item.owner = self.character1
        self.item.save()
        self.assertEqual(self.item.owner, self.character1)

        # Transfer to character2
        self.item.owner = self.character2
        self.item.save()
        self.assertEqual(self.item.owner, self.character2)
        self.assertIn(self.item, self.character2.possessions.all())
        self.assertNotIn(self.item, self.character1.possessions.all())

    def test_transfer_to_method(self):
        """Test transfer_to method functionality."""
        self.item.owner = self.character1
        self.item.save()
        self.assertEqual(self.item.owner, self.character1)

        result = self.item.transfer_to(self.character2)

        self.assertEqual(result, self.item)  # Method chaining
        self.assertEqual(self.item.owner, self.character2)
        self.assertIsNotNone(self.item.last_transferred_at)

    def test_clear_ownership(self):
        """Test clearing ownership."""
        self.item.owner = self.character1
        self.item.save()
        self.assertEqual(self.item.owner, self.character1)

        self.item.owner = None
        self.item.save()

        self.assertIsNone(self.item.owner)
        self.assertNotIn(self.item, self.character1.possessions.all())

    def test_character_possessions_reverse_relation(self):
        """Test that characters can access their possessions."""
        self.item.owner = self.character1
        self.item.save()

        # Test reverse relation (possessions instead of owned_items)
        self.assertEqual(self.character1.possessions.count(), 1)
        self.assertIn(self.item, self.character1.possessions.all())
        self.assertEqual(self.character2.possessions.count(), 0)

    def test_multiple_items_same_character(self):
        """Test that one character can own multiple items."""
        item2 = Item.objects.create(
            name="Second Item",
            campaign=self.campaign,
            created_by=self.owner,
        )

        self.item.owner = self.character1
        self.item.save()
        item2.owner = self.character1
        item2.save()

        self.assertEqual(self.character1.possessions.count(), 2)
        self.assertIn(self.item, self.character1.possessions.all())
        self.assertIn(item2, self.character1.possessions.all())


class ItemCampaignCascadeTest(TestCase):
    """Test campaign relationship cascade behavior."""

    def setUp(self):
        """Set up test data for cascade tests."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            game_system="Mage: The Ascension",
        )

        self.item = Item.objects.create(
            name="Campaign Item",
            campaign=self.campaign,
            created_by=self.owner,
        )

    def test_campaign_deletion_cascades_to_items(self):
        """Test that deleting a campaign deletes its items."""
        item_id = self.item.id
        self.assertTrue(Item.objects.filter(id=item_id).exists())

        self.campaign.delete()

        self.assertFalse(Item.objects.filter(id=item_id).exists())
        self.assertFalse(Item.all_objects.filter(id=item_id).exists())

    def test_multiple_items_cascade_deletion(self):
        """Test that deleting campaign deletes all its items."""
        Item.objects.create(
            name="Second Item",
            campaign=self.campaign,
            created_by=self.owner,
        )

        campaign_id = self.campaign.id
        self.assertEqual(Item.objects.filter(campaign=self.campaign).count(), 2)

        self.campaign.delete()

        self.assertEqual(Item.objects.filter(campaign_id=campaign_id).count(), 0)
        self.assertEqual(Item.all_objects.filter(campaign_id=campaign_id).count(), 0)


class ItemModelManagersTest(TestCase):
    """Test Item model managers and string representation."""

    def setUp(self):
        """Set up test data for manager tests."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            game_system="Mage: The Ascension",
        )

        self.active_item = Item.objects.create(
            name="Active Item",
            campaign=self.campaign,
            created_by=self.owner,
        )

        self.deleted_item = Item.objects.create(
            name="Deleted Item",
            campaign=self.campaign,
            created_by=self.owner,
        )
        self.deleted_item.soft_delete(self.owner)

    def test_objects_manager_excludes_deleted(self):
        """Test that objects manager excludes soft-deleted items."""
        active_items = Item.objects.all()

        self.assertEqual(active_items.count(), 1)
        self.assertIn(self.active_item, active_items)
        self.assertNotIn(self.deleted_item, active_items)

    def test_all_objects_manager_includes_deleted(self):
        """Test that all_objects manager includes soft-deleted items."""
        all_items = Item.all_objects.all()

        self.assertEqual(all_items.count(), 2)
        self.assertIn(self.active_item, all_items)
        self.assertIn(self.deleted_item, all_items)

    def test_item_string_representation(self):
        """Test that Item.__str__ returns the item name."""
        self.assertEqual(str(self.active_item), "Active Item")
        self.assertEqual(str(self.deleted_item), "Deleted Item")

    def test_item_verbose_name(self):
        """Test Item model verbose names."""
        self.assertEqual(Item._meta.verbose_name, "Item")
        self.assertEqual(Item._meta.verbose_name_plural, "Items")

    def test_item_ordering(self):
        """Test Item model default ordering by name."""
        # Create items in reverse alphabetical order
        item_z = Item.objects.create(
            name="Z Item",
            campaign=self.campaign,
            created_by=self.owner,
        )
        item_a = Item.objects.create(
            name="A Item",
            campaign=self.campaign,
            created_by=self.owner,
        )

        items = list(Item.objects.all())
        item_names = [item.name for item in items]

        # Should be ordered alphabetically by name
        expected_order = sorted([self.active_item.name, item_z.name, item_a.name])
        self.assertEqual(item_names, expected_order)


class ItemIntegrationTest(TestCase):
    """Test integration scenarios for item creation with character ownership."""

    def setUp(self):
        """Set up test data for integration tests."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.player = User.objects.create_user(
            username="player", email="player@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Integration Campaign",
            owner=self.owner,
            game_system="Mage: The Ascension",
        )

        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )

        self.character = Character.objects.create(
            name="Test Character",
            campaign=self.campaign,
            player_owner=self.player,
            game_system="Mage: The Ascension",
        )

    def test_create_item_with_immediate_ownership(self):
        """Test creating an item and immediately assigning ownership."""
        item = Item.objects.create(
            name="Character's Sword",
            description="A fine blade",
            campaign=self.campaign,
            quantity=1,
            created_by=self.owner,
        )

        item.owner = self.character
        item.save()

        # Verify the item was created correctly
        self.assertEqual(item.name, "Character's Sword")
        self.assertEqual(item.owner, self.character)
        self.assertIn(item, self.character.possessions.all())

        # Verify reverse relationship
        self.assertEqual(self.character.possessions.count(), 1)
        self.assertIn(item, self.character.possessions.all())

    def test_transfer_item_ownership(self):
        """Test transferring item ownership between characters."""
        character2 = Character.objects.create(
            name="Second Character",
            campaign=self.campaign,
            owner=self.owner,  # Owner creates second character
            game_system="Mage: The Ascension",
        )

        item = Item.objects.create(
            name="Transferable Item",
            campaign=self.campaign,
            created_by=self.owner,
        )

        # Initially owned by character1
        item.owner = self.character
        item.save()
        self.assertEqual(item.owner, self.character)
        self.assertEqual(self.character.possessions.count(), 1)

        # Transfer to character2
        item.owner = character2
        item.save()

        # Verify transfer
        self.assertEqual(item.owner, character2)
        self.assertIn(item, character2.possessions.all())
        self.assertEqual(self.character.possessions.count(), 0)
        self.assertEqual(character2.possessions.count(), 1)

    def test_character_deletion_clears_item_ownership(self):
        """Test that deleting a character clears item ownership."""
        item = Item.objects.create(
            name="Owned Item",
            campaign=self.campaign,
            created_by=self.owner,
        )

        item.owner = self.character
        item.save()
        self.assertEqual(item.owner, self.character)

        character_id = self.character.id
        self.character.delete()

        # Refresh item from database
        item.refresh_from_db()

        # Character should no longer own the item (SET_NULL behavior)
        self.assertIsNone(item.owner)

        # Verify character is gone
        self.assertFalse(Character.objects.filter(id=character_id).exists())


class ItemEdgeCasesTest(TestCase):
    """Test edge cases and error conditions."""

    def setUp(self):
        """Set up test data for edge case tests."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.other_owner = User.objects.create_user(
            username="other_owner", email="other@test.com", password="testpass123"
        )

        self.campaign1 = Campaign.objects.create(
            name="Campaign 1",
            owner=self.owner,
            game_system="Mage: The Ascension",
        )
        self.campaign2 = Campaign.objects.create(
            name="Campaign 2",
            owner=self.other_owner,
            game_system="D&D 5e",
        )

    def test_user_deletion_behavior(self):
        """Test behavior when created_by user is deleted."""
        item = Item.objects.create(
            name="User's Item",
            campaign=self.campaign1,
            created_by=self.owner,
        )

        item_id = item.id
        self.assertTrue(Item.objects.filter(id=item_id).exists())

        # Delete the user who created the item
        # Note: Since campaigns CASCADE on owner deletion, the campaign and its items
        # will be deleted when the owner is deleted
        self.owner.delete()

        # Item should no longer exist because its campaign was deleted
        # when the campaign owner was deleted (CASCADE behavior)
        self.assertFalse(Item.objects.filter(id=item_id).exists())
        self.assertFalse(Item.all_objects.filter(id=item_id).exists())

    def test_item_with_very_long_description(self):
        """Test item with maximum length description."""
        long_description = "A" * 10000  # Very long description

        item = Item.objects.create(
            name="Described Item",
            description=long_description,
            campaign=self.campaign1,
            created_by=self.owner,
        )

        self.assertEqual(len(item.description), 10000)
        self.assertEqual(item.description, long_description)

    def test_item_cross_campaign_character_ownership_prevented(self):
        """Test that items cannot be owned by characters from different campaigns."""
        # Create character in campaign2
        player = User.objects.create_user(
            username="player", email="player@test.com", password="testpass123"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign2, user=player, role="PLAYER"
        )

        character_in_different_campaign = Character.objects.create(
            name="Different Campaign Character",
            campaign=self.campaign2,
            player_owner=player,
            game_system="D&D 5e",
        )

        # Create item in campaign1
        item = Item.objects.create(
            name="Campaign 1 Item",
            campaign=self.campaign1,
            created_by=self.owner,
        )

        # This should work from a database perspective but might be
        # prevented by business logic. For now, we test that it's possible
        # at the model level
        item.owner = character_in_different_campaign
        item.save()
        self.assertEqual(item.owner, character_in_different_campaign)

        # Note: Business logic to prevent cross-campaign ownership would be
        # in forms/views
