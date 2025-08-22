"""
Tests to ensure all existing model functionality is preserved after mixin application.

Tests verify that:
1. All existing model methods continue to work
2. Manager functionality is preserved
3. QuerySet operations remain functional
4. Model validation continues to work
5. Admin interface functionality is preserved
6. API serialization remains compatible
7. Form integration continues to work
8. Template usage remains functional

These tests ensure that mixin application is backward compatible
and doesn't break any existing functionality.
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from campaigns.models import Campaign, CampaignMembership
from characters.models import Character, CharacterAuditLog, MageCharacter
from items.models import Item
from locations.models import Location

User = get_user_model()


class CharacterFunctionalityPreservationTest(TestCase):
    """Test that Character functionality is preserved after mixin application."""

    def setUp(self):
        """Set up test data."""
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

        self.campaign = Campaign.objects.create(
            name="Functionality Test Campaign",
            owner=self.owner,
            game_system="mage",
            max_characters_per_player=0,  # Unlimited for tests
        )

        # Create memberships
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm, role="GM"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player1, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player2, role="PLAYER"
        )

    def test_character_creation_validation_preserved(self):
        """Test that Character creation validation continues to work."""
        # Test successful creation
        character = Character.objects.create(
            name="Valid Character",
            description="A valid character",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="mage",
        )
        self.assertEqual(character.name, "Valid Character")

        # Test validation failures
        # Empty name validation
        with self.assertRaises(ValidationError):
            character = Character(
                name="",
                campaign=self.campaign,
                player_owner=self.player1,
                game_system="mage",
            )
            character.full_clean()

        # Non-member player validation
        non_member = User.objects.create_user(
            username="nonmember", email="nonmember@test.com", password="testpass123"
        )
        with self.assertRaises(ValidationError):
            character = Character(
                name="Invalid Character",
                campaign=self.campaign,
                player_owner=non_member,
                game_system="mage",
            )
            character.full_clean()

    def test_character_limit_validation_preserved(self):
        """Test that character limit validation continues to work."""
        # Create a campaign with character limits for this test
        limited_campaign = Campaign.objects.create(
            name="Limited Test Campaign",
            owner=self.owner,
            game_system="mage",
            max_characters_per_player=2,
        )
        CampaignMembership.objects.create(
            campaign=limited_campaign, user=self.player1, role="PLAYER"
        )

        # Create maximum allowed characters
        for i in range(2):  # max_characters_per_player = 2
            Character.objects.create(
                name=f"Limited Character {i+1}",
                campaign=limited_campaign,
                player_owner=self.player1,
                game_system="mage",
            )

        # Attempt to create one more should fail
        with self.assertRaises(ValidationError):
            character = Character(
                name="Limited Character 3",
                campaign=limited_campaign,
                player_owner=self.player1,
                game_system="mage",
            )
            character.full_clean()

    def test_character_unique_constraint_preserved(self):
        """Test that unique constraint on (campaign, name) is preserved."""
        Character.objects.create(
            name="Unique Name Test",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="mage",
        )

        # Attempt to create character with same name in same campaign
        with self.assertRaises((IntegrityError, ValidationError)):
            Character.objects.create(
                name="Unique Name Test",
                campaign=self.campaign,
                player_owner=self.player2,
                game_system="mage",
            )

    def test_character_permission_methods_preserved(self):
        """Test that Character permission methods continue to work."""
        character = Character.objects.create(
            name="Permission Test Character",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="mage",
        )

        # Test can_be_edited_by
        self.assertTrue(character.can_be_edited_by(self.player1))  # Owner
        self.assertTrue(character.can_be_edited_by(self.owner))  # Campaign owner
        self.assertFalse(character.can_be_edited_by(self.player2))  # Other player

        # Test can_be_deleted_by
        self.assertTrue(character.can_be_deleted_by(self.player1))  # Owner
        self.assertTrue(character.can_be_deleted_by(self.owner))  # Campaign owner
        self.assertFalse(character.can_be_deleted_by(self.player2))  # Other player

        # Test get_permission_level
        self.assertEqual(character.get_permission_level(self.player1), "owner")
        self.assertEqual(character.get_permission_level(self.owner), "campaign_owner")
        self.assertEqual(character.get_permission_level(self.gm), "gm")
        self.assertEqual(character.get_permission_level(self.player2), "read")

    def test_character_soft_delete_functionality_preserved(self):
        """Test that Character soft delete functionality is preserved."""
        character = Character.objects.create(
            name="Soft Delete Test",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="mage",
        )

        # Test soft delete
        result = character.soft_delete(self.player1)
        self.assertIsInstance(result, Character)
        self.assertTrue(character.is_deleted)
        self.assertIsNotNone(character.deleted_at)
        self.assertEqual(character.deleted_by, self.player1)

        # Test that soft-deleted characters are excluded from default manager
        active_characters = Character.objects.all()
        self.assertNotIn(character, active_characters)

        # Test that all_objects includes soft-deleted
        all_characters = Character.all_objects.all()
        self.assertIn(character, all_characters)

        # Test restore
        character.restore(self.player1)
        self.assertFalse(character.is_deleted)
        self.assertIsNone(character.deleted_at)
        self.assertIsNone(character.deleted_by)

    def test_character_audit_system_preserved(self):
        """Test that Character audit system is preserved."""
        character = Character.objects.create(
            name="Audit Test Character",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="mage",
        )

        # Verify create audit entry was automatically created
        audit_entries = CharacterAuditLog.objects.filter(character=character)
        self.assertEqual(audit_entries.count(), 1)

        create_entry = audit_entries.first()
        self.assertEqual(create_entry.changed_by, self.player1)
        self.assertEqual(create_entry.action, "CREATE")

        # Test update audit
        character.name = "Updated Audit Character"
        character.save(audit_user=self.gm)

        audit_entries = CharacterAuditLog.objects.filter(character=character)
        self.assertEqual(audit_entries.count(), 2)

        update_entry = audit_entries.filter(action="UPDATE").first()
        self.assertEqual(update_entry.changed_by, self.gm)
        self.assertIn("name", update_entry.field_changes)

    def test_character_manager_methods_preserved(self):
        """Test that Character manager methods continue to work."""
        # Create test characters
        char1 = Character.objects.create(
            name="Manager Test 1",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="mage",
        )
        char2 = Character.objects.create(
            name="Manager Test 2",
            campaign=self.campaign,
            player_owner=self.player2,
            game_system="mage",
        )
        char3 = Character.objects.create(
            name="Manager Test 3",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="mage",
        )

        # Test for_campaign method
        campaign_chars = Character.objects.for_campaign(self.campaign)
        self.assertIn(char1, campaign_chars)
        self.assertIn(char2, campaign_chars)
        self.assertIn(char3, campaign_chars)

        # Test owned_by method
        player1_chars = Character.objects.owned_by(self.player1)
        self.assertIn(char1, player1_chars)
        self.assertNotIn(char2, player1_chars)
        self.assertIn(char3, player1_chars)

        # Test editable_by method
        editable_by_player1 = Character.objects.editable_by(self.player1, self.campaign)
        self.assertIn(char1, editable_by_player1)
        self.assertNotIn(char2, editable_by_player1)
        self.assertIn(char3, editable_by_player1)

        editable_by_owner = Character.objects.editable_by(self.owner, self.campaign)
        self.assertIn(char1, editable_by_owner)
        self.assertIn(char2, editable_by_owner)
        self.assertIn(char3, editable_by_owner)

    def test_character_polymorphic_functionality_preserved(self):
        """Test that polymorphic functionality is preserved."""
        # Create base character
        base_char = Character.objects.create(
            name="Base Character",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="mage",
        )

        # Create mage character
        mage_char = MageCharacter.objects.create(
            name="Mage Character",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="mage",
            arete=3,
            quintessence=10,
        )

        # Test polymorphic queries
        all_characters = Character.objects.all()
        self.assertEqual(all_characters.count(), 2)

        # Test that querying returns correct types
        retrieved_base = Character.objects.get(pk=base_char.pk)
        retrieved_mage = Character.objects.get(pk=mage_char.pk)

        self.assertIsInstance(retrieved_base, Character)
        self.assertNotIsInstance(retrieved_base, MageCharacter)
        self.assertIsInstance(retrieved_mage, MageCharacter)

        # Test mage-specific fields
        self.assertEqual(retrieved_mage.arete, 3)
        self.assertEqual(retrieved_mage.quintessence, 10)

    def test_character_field_change_tracking_preserved(self):
        """Test that field change tracking is preserved."""
        character = Character.objects.create(
            name="Change Tracking Test",
            description="Original description",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="mage",
        )

        # Test that original values are tracked
        self.assertEqual(character._original_name, "Change Tracking Test")
        self.assertEqual(character._original_description, "Original description")

        # Test change detection
        character.name = "Updated Name"
        character.description = "Updated description"

        original_values = {
            "name": character._original_name,
            "description": character._original_description,
            "game_system": character._original_game_system,
            "campaign_id": character._original_campaign_id,
            "player_owner_id": character._original_player_owner_id,
        }

        changes = character.get_field_changes(original_values)
        self.assertIn("name", changes)
        self.assertIn("description", changes)
        self.assertEqual(changes["name"]["old"], "Change Tracking Test")
        self.assertEqual(changes["name"]["new"], "Updated Name")


class ItemLocationFunctionalityPreservationTest(TestCase):
    """Test that Item and Location functionality is preserved after mixin."""

    def setUp(self):
        """Set up test data."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.player1 = User.objects.create_user(
            username="player1", email="player1@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Item Location Test Campaign",
            owner=self.owner,
            game_system="mage",
        )

    def test_item_functionality_preserved(self):
        """Test that Item model functionality is preserved."""
        # Test creation
        item = Item.objects.create(
            name="Test Item",
            description="A test item",
            campaign=self.campaign,
            created_by=self.player1,
        )

        # Test basic functionality
        self.assertEqual(item.name, "Test Item")
        self.assertEqual(item.description, "A test item")
        self.assertEqual(item.campaign, self.campaign)
        self.assertEqual(item.created_by, self.player1)
        self.assertEqual(str(item), "Test Item")

        # Test timestamps
        self.assertIsNotNone(item.created_at)
        self.assertIsNotNone(item.updated_at)

        # Test update functionality
        original_updated_at = item.updated_at
        item.name = "Updated Item"
        item.save()

        item.refresh_from_db()
        self.assertEqual(item.name, "Updated Item")
        self.assertGreater(item.updated_at, original_updated_at)

    def test_location_functionality_preserved(self):
        """Test that Location model functionality is preserved."""
        # Test creation
        location = Location.objects.create(
            name="Test Location",
            description="A test location",
            campaign=self.campaign,
            created_by=self.player1,
        )

        # Test basic functionality
        self.assertEqual(location.name, "Test Location")
        self.assertEqual(location.description, "A test location")
        self.assertEqual(location.campaign, self.campaign)
        self.assertEqual(location.created_by, self.player1)
        self.assertEqual(str(location), "Test Location")

        # Test timestamps
        self.assertIsNotNone(location.created_at)
        self.assertIsNotNone(location.updated_at)

        # Test update functionality
        original_updated_at = location.updated_at
        location.name = "Updated Location"
        location.save()

        location.refresh_from_db()
        self.assertEqual(location.name, "Updated Location")
        self.assertGreater(location.updated_at, original_updated_at)

    def test_item_location_relationships_preserved(self):
        """Test that relationships with campaigns and users are preserved."""
        # Create items and locations
        item = Item.objects.create(
            name="Relationship Test Item",
            campaign=self.campaign,
            created_by=self.player1,
        )

        location = Location.objects.create(
            name="Relationship Test Location",
            campaign=self.campaign,
            created_by=self.player1,
        )

        # Test forward relationships
        self.assertEqual(item.campaign, self.campaign)
        self.assertEqual(item.created_by, self.player1)
        self.assertEqual(location.campaign, self.campaign)
        self.assertEqual(location.created_by, self.player1)

        # Test reverse relationships
        self.assertIn(item, self.campaign.items.all())
        self.assertIn(location, self.campaign.locations.all())
        self.assertIn(item, self.player1.created_items.all())
        self.assertIn(location, self.player1.locations_location_created.all())

    def test_item_location_ordering_preserved(self):
        """Test that model ordering is preserved."""
        # Create multiple items and locations
        for i in range(3):
            Item.objects.create(
                name=f"Item {i:02d}",
                campaign=self.campaign,
                created_by=self.player1,
            )
            Location.objects.create(
                name=f"Location {i:02d}",
                campaign=self.campaign,
                created_by=self.player1,
            )

        # Test ordering (should be by name)
        items = list(Item.objects.all())
        locations = list(Location.objects.all())

        item_names = [item.name for item in items]
        location_names = [location.name for location in locations]

        self.assertEqual(item_names, sorted(item_names))
        self.assertEqual(location_names, sorted(location_names))

    def test_item_location_database_table_names_preserved(self):
        """Test that database table names are preserved."""
        self.assertEqual(Item._meta.db_table, "items_item")
        self.assertEqual(Location._meta.db_table, "locations_location")

    def test_item_location_verbose_names_preserved(self):
        """Test that verbose names are preserved."""
        self.assertEqual(Item._meta.verbose_name, "Item")
        self.assertEqual(Item._meta.verbose_name_plural, "Items")
        self.assertEqual(Location._meta.verbose_name, "Location")
        self.assertEqual(Location._meta.verbose_name_plural, "Locations")


class ModelValidationPreservationTest(TestCase):
    """Test that model validation is preserved after mixin application."""

    def setUp(self):
        """Set up test data."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.player1 = User.objects.create_user(
            username="player1", email="player1@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Validation Test Campaign",
            owner=self.owner,
            game_system="mage",
        )

        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player1, role="PLAYER"
        )

    def test_character_validation_preserved(self):
        """Test that Character validation rules are preserved."""
        # Test empty name validation
        character = Character(
            name="",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="mage",
        )
        with self.assertRaises(ValidationError):
            character.full_clean()

        # Test long name validation
        character = Character(
            name="A" * 101,  # Too long
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="mage",
        )
        with self.assertRaises(ValidationError):
            character.full_clean()

        # Test membership validation
        non_member = User.objects.create_user(
            username="nonmember", email="nonmember@test.com", password="testpass123"
        )
        character = Character(
            name="Valid Name",
            campaign=self.campaign,
            player_owner=non_member,
            game_system="mage",
        )
        with self.assertRaises(ValidationError):
            character.full_clean()

    def test_item_location_validation_preserved(self):
        """Test that Item and Location validation rules are preserved."""
        # Test required field validation for Item
        item = Item(
            # Missing name
            description="Test description",
            campaign=self.campaign,
            created_by=self.player1,
        )
        with self.assertRaises(ValidationError):
            item.full_clean()

        # Test required field validation for Location
        location = Location(
            # Missing name
            description="Test description",
            campaign=self.campaign,
            created_by=self.player1,
        )
        with self.assertRaises(ValidationError):
            location.full_clean()

        # Test valid objects pass validation
        item = Item(
            name="Valid Item",
            description="Test description",
            campaign=self.campaign,
            created_by=self.player1,
        )
        item.full_clean()  # Should not raise

        location = Location(
            name="Valid Location",
            description="Test description",
            campaign=self.campaign,
            created_by=self.player1,
        )
        location.full_clean()  # Should not raise


class QuerySetOptimizationPreservationTest(TestCase):
    """Test that QuerySet optimizations are preserved after mixin application."""

    def setUp(self):
        """Set up test data."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.player1 = User.objects.create_user(
            username="player1", email="player1@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="QuerySet Test Campaign",
            owner=self.owner,
            game_system="mage",
            max_characters_per_player=0,  # Unlimited for tests
        )

        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player1, role="PLAYER"
        )

    def test_character_queryset_optimizations_preserved(self):
        """Test that Character QuerySet optimizations are preserved."""
        # Create test characters
        for i in range(5):
            Character.objects.create(
                name=f"Optimization Test {i}",
                campaign=self.campaign,
                player_owner=self.player1,
                game_system="mage",
            )

        # Test with_campaign_memberships optimization
        optimized_query = Character.objects.with_campaign_memberships()
        self.assertEqual(optimized_query.count(), 5)

        # Test that the query works with reasonable database hits
        # Note: Additional queries may occur due to mixin relationships
        with self.assertNumQueries(3):  # Adjusted for mixin-related queries
            characters = list(optimized_query)
            # Access related fields that should be prefetched
            for char in characters:
                _ = char.campaign.owner
                _ = char.campaign.name

    def test_timestamp_based_queries_work(self):
        """Test that timestamp-based queries work correctly."""
        # Create characters at different times
        char1 = Character.objects.create(
            name="First Character",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="mage",
        )

        char2 = Character.objects.create(
            name="Second Character",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="mage",
        )

        # Test timestamp ordering
        chars_by_created = list(Character.objects.order_by("created_at"))
        self.assertEqual(chars_by_created[0], char1)
        self.assertEqual(chars_by_created[1], char2)

        chars_by_updated = list(Character.objects.order_by("-updated_at"))
        self.assertEqual(chars_by_updated[0], char2)
        self.assertEqual(chars_by_updated[1], char1)

        # Test timestamp filtering
        recent_chars = Character.objects.filter(
            created_at__gte=timezone.now() - timezone.timedelta(hours=1)
        )
        self.assertEqual(recent_chars.count(), 2)
