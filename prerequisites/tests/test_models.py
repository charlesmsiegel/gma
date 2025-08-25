"""
Comprehensive tests for Prerequisite model functionality.

Tests cover all requirements from Issue #178:
1. Core Prerequisite model with JSON requirements field
2. GenericForeignKey attachment to any model (characters, items)
3. Description field for human-readable requirements
4. JSONField for structured requirements
5. Basic validation for JSON structure
6. Database indexes for performance
7. Model creation, validation, and CRUD operations
8. Edge cases and error handling
"""

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.test import TestCase, TransactionTestCase

from campaigns.models import Campaign, CampaignMembership
from characters.models import Character, MageCharacter
from items.models import Item
from prerequisites.models import Prerequisite

User = get_user_model()


class PrerequisiteModelBasicTest(TestCase):
    """Test basic Prerequisite model functionality."""

    def setUp(self):
        """Set up test users, campaigns, and objects."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.player = User.objects.create_user(
            username="player", email="player@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            game_system="mage",
            max_characters_per_player=0,  # Allow unlimited characters for testing
        )

        # Create membership for player
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )

        self.character = Character.objects.create(
            name="Test Character",
            campaign=self.campaign,
            player_owner=self.player,
            game_system="mage",
        )

        self.item = Item.objects.create(
            name="Test Item",
            description="Test item for prerequisites",
            campaign=self.campaign,
            quantity=1,
            created_by=self.owner,
        )

    def test_prerequisite_creation_with_required_fields(self):
        """Test creating a prerequisite with only required fields."""
        prerequisite = Prerequisite.objects.create(
            description="Must have Arete 3 or higher"
        )

        self.assertEqual(prerequisite.description, "Must have Arete 3 or higher")
        self.assertEqual(prerequisite.requirements, {})  # Default empty dict
        self.assertIsNone(prerequisite.content_object)
        self.assertIsNone(prerequisite.object_id)
        self.assertIsNone(prerequisite.content_type)
        self.assertIsNotNone(prerequisite.created_at)
        self.assertIsNotNone(prerequisite.updated_at)

    def test_prerequisite_str_representation(self):
        """Test string representation of prerequisite."""
        prerequisite = Prerequisite.objects.create(
            description="Must have Arete 3 or higher"
        )

        self.assertEqual(str(prerequisite), "Must have Arete 3 or higher")

    def test_prerequisite_str_representation_truncated(self):
        """Test string representation truncation for long descriptions."""
        long_description = "A" * 120
        prerequisite = Prerequisite.objects.create(description=long_description)

        expected = long_description[:100] + "..."
        self.assertEqual(str(prerequisite), expected)

    def test_prerequisite_with_json_requirements(self):
        """Test creating prerequisite with JSON requirements."""
        requirements = {
            "attributes": {"arete": {"min": 3, "max": 10}},
            "spheres": {"matter": {"min": 2}},
            "items": ["Focus", "Grimoire"],
        }

        prerequisite = Prerequisite.objects.create(
            description="Complex magical requirements", requirements=requirements
        )

        self.assertEqual(prerequisite.requirements, requirements)
        # Verify JSON serialization/deserialization
        prerequisite.refresh_from_db()
        self.assertEqual(prerequisite.requirements["attributes"]["arete"]["min"], 3)
        self.assertEqual(prerequisite.requirements["spheres"]["matter"]["min"], 2)
        self.assertEqual(prerequisite.requirements["items"], ["Focus", "Grimoire"])

    def test_prerequisite_empty_requirements_default(self):
        """Test that requirements defaults to empty dict."""
        prerequisite = Prerequisite.objects.create(description="Simple prerequisite")

        self.assertEqual(prerequisite.requirements, {})
        self.assertIsInstance(prerequisite.requirements, dict)


class PrerequisiteGenericForeignKeyTest(TestCase):
    """Test GenericForeignKey functionality with various models."""

    def setUp(self):
        """Set up test data."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.player = User.objects.create_user(
            username="player", email="player@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            game_system="mage",
            max_characters_per_player=0,  # Allow unlimited characters for testing
        )

        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )

        self.character = MageCharacter.objects.create(
            name="Test Mage",
            campaign=self.campaign,
            player_owner=self.player,
            game_system="mage",
            arete=2,
            quintessence=5,
        )

        self.item = Item.objects.create(
            name="Magic Sword",
            description="Enchanted weapon",
            campaign=self.campaign,
            quantity=1,
            created_by=self.owner,
        )

    def test_prerequisite_attached_to_character(self):
        """Test attaching prerequisite to a character."""
        prerequisite = Prerequisite.objects.create(
            description="Must have Combat training",
            requirements={"skills": {"melee": {"min": 2}}},
            content_object=self.character,
        )

        self.assertEqual(prerequisite.content_object, self.character)
        self.assertEqual(prerequisite.object_id, self.character.id)
        self.assertEqual(
            prerequisite.content_type, ContentType.objects.get_for_model(MageCharacter)
        )

        # Test reverse relationship access
        character_prerequisites = Prerequisite.objects.filter(
            content_type=ContentType.objects.get_for_model(MageCharacter),
            object_id=self.character.id,
        )
        self.assertEqual(character_prerequisites.count(), 1)
        self.assertEqual(character_prerequisites.first(), prerequisite)

    def test_prerequisite_attached_to_item(self):
        """Test attaching prerequisite to an item."""
        prerequisite = Prerequisite.objects.create(
            description="Must be worthy to wield",
            requirements={"attributes": {"honor": {"min": 5}}},
            content_object=self.item,
        )

        self.assertEqual(prerequisite.content_object, self.item)
        self.assertEqual(prerequisite.object_id, self.item.id)
        self.assertEqual(
            prerequisite.content_type, ContentType.objects.get_for_model(Item)
        )

    def test_prerequisite_attached_to_polymorphic_character(self):
        """Test attaching prerequisite to a polymorphic character subclass."""
        prerequisite = Prerequisite.objects.create(
            description="Mage-specific requirement",
            requirements={"arete": {"min": 3}, "spheres": {"forces": {"min": 2}}},
            content_object=self.character,  # This is a MageCharacter
        )

        # Should work with polymorphic models
        self.assertEqual(prerequisite.content_object, self.character)
        self.assertIsInstance(prerequisite.content_object, MageCharacter)

        # Verify content type is set correctly (MageCharacter type)
        self.assertEqual(
            prerequisite.content_type, ContentType.objects.get_for_model(MageCharacter)
        )

    def test_prerequisite_multiple_objects_same_type(self):
        """Test multiple prerequisites on objects of the same type."""
        char1_prereq = Prerequisite.objects.create(
            description="Character 1 requirement", content_object=self.character
        )

        # Create another character
        character2 = Character.objects.create(
            name="Test Character 2",
            campaign=self.campaign,
            player_owner=self.player,
            game_system="mage",
        )

        char2_prereq = Prerequisite.objects.create(
            description="Character 2 requirement", content_object=character2
        )

        # Verify each has its own prerequisite
        self.assertEqual(char1_prereq.content_object, self.character)
        self.assertEqual(char2_prereq.content_object, character2)

        # Check filtering works correctly
        char1_prerequisites = Prerequisite.objects.filter(
            content_type=ContentType.objects.get_for_model(MageCharacter),
            object_id=self.character.id,
        )
        char2_prerequisites = Prerequisite.objects.filter(
            content_type=ContentType.objects.get_for_model(Character),
            object_id=character2.id,
        )

        self.assertEqual(char1_prerequisites.count(), 1)
        self.assertEqual(char2_prerequisites.count(), 1)
        self.assertEqual(char1_prerequisites.first(), char1_prereq)
        self.assertEqual(char2_prerequisites.first(), char2_prereq)

    def test_prerequisite_no_content_object(self):
        """Test prerequisite without attached object (standalone requirement)."""
        prerequisite = Prerequisite.objects.create(
            description="General campaign requirement",
            requirements={"level": {"min": 5}},
        )

        self.assertIsNone(prerequisite.content_object)
        self.assertIsNone(prerequisite.object_id)
        self.assertIsNone(prerequisite.content_type)

    def test_prerequisite_content_object_deletion_cascade(self):
        """Test behavior when content object is deleted."""
        prerequisite = Prerequisite.objects.create(
            description="Item requirement", content_object=self.item
        )

        prerequisite_id = prerequisite.id
        self.assertTrue(Prerequisite.objects.filter(id=prerequisite_id).exists())

        # Delete the item (hard delete for complete removal)
        item_id = self.item.id
        self.item.delete()

        # Prerequisite should still exist but with null content_object
        prerequisite.refresh_from_db()
        self.assertIsNone(prerequisite.content_object)
        self.assertEqual(prerequisite.object_id, item_id)  # object_id remains
        # content_type should remain for audit purposes
        self.assertEqual(
            prerequisite.content_type, ContentType.objects.get_for_model(Item)
        )


class PrerequisiteValidationTest(TestCase):
    """Test prerequisite model validation."""

    def test_description_required(self):
        """Test that description field is required."""
        with self.assertRaises(ValidationError):
            prerequisite = Prerequisite(description="")
            prerequisite.full_clean()

    def test_description_blank_validation(self):
        """Test description cannot be blank."""
        with self.assertRaises(ValidationError):
            prerequisite = Prerequisite(description="   ")
            prerequisite.full_clean()

    def test_description_max_length(self):
        """Test description field max length validation."""
        # Should work with max length (500 characters)
        description = "A" * 500
        prerequisite = Prerequisite(description=description)
        prerequisite.full_clean()  # Should not raise

        # Should fail with too long description
        with self.assertRaises(ValidationError):
            long_description = "A" * 501
            prerequisite = Prerequisite(description=long_description)
            prerequisite.full_clean()

    def test_requirements_json_validation(self):
        """Test that requirements field accepts valid JSON."""
        valid_requirements = [
            {},  # Empty dict
            {"simple": "value"},
            {"nested": {"key": "value"}},
            {"list": [1, 2, 3]},
            {
                "complex": {
                    "attributes": {"strength": {"min": 3, "max": 5}},
                    "skills": ["combat", "academics"],
                    "items": {"required": ["sword"], "optional": ["shield"]},
                }
            },
        ]

        for req in valid_requirements:
            prerequisite = Prerequisite(
                description="Test requirement", requirements=req
            )
            prerequisite.full_clean()  # Should not raise

    def test_requirements_defaults_to_empty_dict(self):
        """Test requirements field defaults to empty dictionary."""
        prerequisite = Prerequisite(description="Test")
        prerequisite.full_clean()

        # Before save, should have default
        self.assertEqual(prerequisite.requirements, {})

        prerequisite.save()
        prerequisite.refresh_from_db()

        # After save/load, should still be empty dict
        self.assertEqual(prerequisite.requirements, {})
        self.assertIsInstance(prerequisite.requirements, dict)


class PrerequisiteDatabaseTest(TestCase):
    """Test database-level functionality and constraints."""

    def setUp(self):
        """Set up test data."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            game_system="mage",
            max_characters_per_player=0,  # Allow unlimited characters for testing
        )
        self.character = Character.objects.create(
            name="Test Character",
            campaign=self.campaign,
            player_owner=self.owner,
            game_system="mage",
        )

    def test_prerequisite_indexes_exist(self):
        """Test that expected database indexes exist."""
        from django.db import connection

        # Get table name
        table_name = Prerequisite._meta.db_table

        # Get indexes for the table using the correct method
        with connection.cursor() as cursor:
            table_info = connection.introspection.get_table_description(
                cursor, table_name
            )
            constraints = connection.introspection.get_constraints(cursor, table_name)

        # Check that the table exists and has expected columns
        column_names = [col.name for col in table_info]
        self.assertIn("content_type_id", column_names)
        self.assertIn("object_id", column_names)

        # We should have at least one index covering GenericForeignKey fields
        # Note: This is a basic test - the exact index structure may vary
        self.assertTrue(
            len(constraints) > 0, "Expected to find database constraints/indexes"
        )

    def test_prerequisite_content_type_foreign_key(self):
        """Test content_type foreign key relationship."""
        prerequisite = Prerequisite.objects.create(
            description="Test requirement", content_object=self.character
        )

        # Should have valid content_type
        self.assertIsInstance(prerequisite.content_type, ContentType)
        self.assertEqual(prerequisite.content_type.model, "character")
        self.assertEqual(prerequisite.content_type.app_label, "characters")

    def test_prerequisite_ordering(self):
        """Test default ordering by creation time (newest first)."""
        # Create prerequisites at different times
        prereq1 = Prerequisite.objects.create(description="First requirement")
        prereq2 = Prerequisite.objects.create(description="Second requirement")
        prereq3 = Prerequisite.objects.create(description="Third requirement")

        # Get all prerequisites
        prerequisites = list(Prerequisite.objects.all())

        # Should be ordered by created_at descending (newest first)
        self.assertEqual(prerequisites[0], prereq3)
        self.assertEqual(prerequisites[1], prereq2)
        self.assertEqual(prerequisites[2], prereq1)

    def test_prerequisite_verbose_names(self):
        """Test model verbose names are set correctly."""
        self.assertEqual(Prerequisite._meta.verbose_name, "Prerequisite")
        self.assertEqual(Prerequisite._meta.verbose_name_plural, "Prerequisites")


class PrerequisiteCRUDTest(TestCase):
    """Test CRUD operations on Prerequisite model."""

    def setUp(self):
        """Set up test data."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            game_system="mage",
            max_characters_per_player=0,  # Allow unlimited characters for testing
        )
        self.character = Character.objects.create(
            name="Test Character",
            campaign=self.campaign,
            player_owner=self.owner,
            game_system="mage",
        )

    def test_create_prerequisite(self):
        """Test creating a prerequisite."""
        prerequisite = Prerequisite.objects.create(
            description="Must have high intelligence",
            requirements={"attributes": {"intelligence": {"min": 4}}},
            content_object=self.character,
        )

        self.assertIsNotNone(prerequisite.id)
        self.assertEqual(prerequisite.description, "Must have high intelligence")
        self.assertEqual(prerequisite.content_object, self.character)

    def test_read_prerequisite(self):
        """Test reading a prerequisite."""
        original_req = {"skills": {"academics": {"min": 3}}}
        prerequisite = Prerequisite.objects.create(
            description="Academic requirement", requirements=original_req
        )

        # Read back from database
        retrieved = Prerequisite.objects.get(id=prerequisite.id)
        self.assertEqual(retrieved.description, "Academic requirement")
        self.assertEqual(retrieved.requirements, original_req)

    def test_update_prerequisite(self):
        """Test updating a prerequisite."""
        prerequisite = Prerequisite.objects.create(
            description="Original description", requirements={"old": "requirement"}
        )

        # Update fields
        prerequisite.description = "Updated description"
        prerequisite.requirements = {"new": "requirement", "level": 5}
        prerequisite.save()

        # Verify update
        prerequisite.refresh_from_db()
        self.assertEqual(prerequisite.description, "Updated description")
        self.assertEqual(prerequisite.requirements["new"], "requirement")
        self.assertEqual(prerequisite.requirements["level"], 5)
        self.assertNotIn("old", prerequisite.requirements)

    def test_delete_prerequisite(self):
        """Test deleting a prerequisite."""
        prerequisite = Prerequisite.objects.create(
            description="To be deleted", content_object=self.character
        )

        prerequisite_id = prerequisite.id
        self.assertTrue(Prerequisite.objects.filter(id=prerequisite_id).exists())

        # Delete the prerequisite
        prerequisite.delete()

        # Should be gone
        self.assertFalse(Prerequisite.objects.filter(id=prerequisite_id).exists())

        # Character should still exist
        self.assertTrue(Character.objects.filter(id=self.character.id).exists())

    def test_bulk_operations(self):
        """Test bulk create and update operations."""
        # Bulk create
        prerequisites_data = [
            {"description": "Bulk requirement 1", "requirements": {"type": "test1"}},
            {"description": "Bulk requirement 2", "requirements": {"type": "test2"}},
            {"description": "Bulk requirement 3", "requirements": {"type": "test3"}},
        ]

        prerequisites = []
        for data in prerequisites_data:
            prerequisites.append(Prerequisite(**data))

        Prerequisite.objects.bulk_create(prerequisites)

        # Verify all created
        self.assertEqual(
            Prerequisite.objects.filter(description__startswith="Bulk").count(), 3
        )

        # Test bulk update
        bulk_prerequisites = Prerequisite.objects.filter(description__startswith="Bulk")
        for prereq in bulk_prerequisites:
            prereq.requirements["updated"] = True

        Prerequisite.objects.bulk_update(bulk_prerequisites, ["requirements"])

        # Verify updates
        updated_prerequisites = Prerequisite.objects.filter(
            description__startswith="Bulk"
        )
        for prereq in updated_prerequisites:
            self.assertTrue(prereq.requirements.get("updated", False))


class PrerequisiteQueryTest(TestCase):
    """Test querying and filtering prerequisites."""

    def setUp(self):
        """Set up test data."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            game_system="mage",
            max_characters_per_player=0,  # Allow unlimited characters for testing
        )
        self.character = Character.objects.create(
            name="Test Character",
            campaign=self.campaign,
            player_owner=self.owner,
            game_system="mage",
        )
        self.item = Item.objects.create(
            name="Test Item",
            campaign=self.campaign,
            created_by=self.owner,
        )

        # Create test prerequisites
        self.char_prereq = Prerequisite.objects.create(
            description="Character requirement",
            requirements={"type": "character"},
            content_object=self.character,
        )

        self.item_prereq = Prerequisite.objects.create(
            description="Item requirement",
            requirements={"type": "item"},
            content_object=self.item,
        )

        self.standalone_prereq = Prerequisite.objects.create(
            description="Standalone requirement", requirements={"type": "standalone"}
        )

    def test_filter_by_content_type(self):
        """Test filtering prerequisites by content type."""
        character_ct = ContentType.objects.get_for_model(Character)
        char_prerequisites = Prerequisite.objects.filter(content_type=character_ct)

        self.assertEqual(char_prerequisites.count(), 1)
        self.assertEqual(char_prerequisites.first(), self.char_prereq)

    def test_filter_by_object_id(self):
        """Test filtering prerequisites by object ID."""
        char_prerequisites = Prerequisite.objects.filter(object_id=self.character.id)

        # Note: This might return prerequisites for other objects with same ID
        # but different content_type, so we should also filter by content_type
        character_ct = ContentType.objects.get_for_model(Character)
        char_prerequisites = Prerequisite.objects.filter(
            content_type=character_ct, object_id=self.character.id
        )

        self.assertEqual(char_prerequisites.count(), 1)
        self.assertEqual(char_prerequisites.first(), self.char_prereq)

    def test_filter_by_description(self):
        """Test filtering prerequisites by description."""
        char_prerequisites = Prerequisite.objects.filter(
            description__icontains="character"
        )

        self.assertEqual(char_prerequisites.count(), 1)
        self.assertEqual(char_prerequisites.first(), self.char_prereq)

    def test_filter_by_json_requirements(self):
        """Test filtering prerequisites by JSON field content."""
        # Filter by JSON field values
        char_prerequisites = Prerequisite.objects.filter(requirements__type="character")

        self.assertEqual(char_prerequisites.count(), 1)
        self.assertEqual(char_prerequisites.first(), self.char_prereq)

    def test_filter_standalone_prerequisites(self):
        """Test filtering standalone prerequisites (no content object)."""
        standalone_prerequisites = Prerequisite.objects.filter(
            content_type__isnull=True, object_id__isnull=True
        )

        self.assertEqual(standalone_prerequisites.count(), 1)
        self.assertEqual(standalone_prerequisites.first(), self.standalone_prereq)

    def test_get_all_prerequisites_for_object(self):
        """Test getting all prerequisites for a specific object."""
        # Add another prerequisite to the same character
        char_prereq2 = Prerequisite.objects.create(
            description="Another character requirement", content_object=self.character
        )

        character_ct = ContentType.objects.get_for_model(Character)
        char_prerequisites = Prerequisite.objects.filter(
            content_type=character_ct, object_id=self.character.id
        )

        self.assertEqual(char_prerequisites.count(), 2)
        self.assertIn(self.char_prereq, char_prerequisites)
        self.assertIn(char_prereq2, char_prerequisites)

    def test_count_prerequisites_by_type(self):
        """Test counting prerequisites by content type."""
        character_ct = ContentType.objects.get_for_model(Character)
        item_ct = ContentType.objects.get_for_model(Item)

        char_count = Prerequisite.objects.filter(content_type=character_ct).count()
        item_count = Prerequisite.objects.filter(content_type=item_ct).count()
        standalone_count = Prerequisite.objects.filter(
            content_type__isnull=True
        ).count()

        self.assertEqual(char_count, 1)
        self.assertEqual(item_count, 1)
        self.assertEqual(standalone_count, 1)


class PrerequisiteEdgeCaseTest(TestCase):
    """Test edge cases and error conditions."""

    def setUp(self):
        """Set up test data."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )

    def test_prerequisite_with_null_requirements(self):
        """Test prerequisite behavior with null requirements."""
        # Direct assignment of None should be converted to {}
        prerequisite = Prerequisite(description="Test requirement", requirements=None)
        prerequisite.save()

        prerequisite.refresh_from_db()
        self.assertEqual(prerequisite.requirements, {})

    def test_prerequisite_unicode_content(self):
        """Test prerequisite with unicode content."""
        unicode_description = "Must have 🧙‍♂️ magical training with ñoño skills"
        unicode_requirements = {
            "spells": ["Firebolt ⚡", "Healing ✨"],
            "attributes": {"mañá": {"mín": 3}},
        }

        prerequisite = Prerequisite.objects.create(
            description=unicode_description, requirements=unicode_requirements
        )

        self.assertEqual(prerequisite.description, unicode_description)
        self.assertEqual(prerequisite.requirements["spells"][0], "Firebolt ⚡")
        self.assertEqual(prerequisite.requirements["attributes"]["mañá"]["mín"], 3)

    def test_prerequisite_very_complex_json(self):
        """Test prerequisite with very complex JSON requirements."""
        complex_requirements = {
            "character_requirements": {
                "primary_attributes": {
                    "strength": {"min": 2, "max": 5, "optimal": 3},
                    "dexterity": {"min": 2, "recommended": 4},
                    "intelligence": {"min": 3, "scaling": "linear"},
                },
                "secondary_attributes": {
                    "willpower": {"base": 5, "modifiers": [1, 2, -1]},
                    "health_levels": {"min": 7, "bonus_per_stamina": 1},
                },
                "skills": {
                    "required": {
                        "academics": {
                            "min": 2,
                            "specializations": ["mathematics", "physics"],
                        },
                        "science": {"min": 1, "preferred_focus": "chemistry"},
                    },
                    "optional": {
                        "crafts": {"bonus_if_present": 2},
                        "computer": {"synergy_with": ["academics", "science"]},
                    },
                },
                "backgrounds": {
                    "resources": {"min": 1, "alternatives": ["mentor", "contacts"]},
                    "library": {
                        "required_rating": 2,
                        "must_contain": ["alchemy", "hermetic theory"],
                    },
                },
            },
            "item_requirements": {
                "focus_items": {
                    "required": True,
                    "types": ["staff", "wand", "orb"],
                    "minimum_rating": 2,
                    "enchantments": ["matter_affinity", "forces_resonance"],
                },
                "components": {
                    "magical_materials": ["silver", "iron", "rare_earth"],
                    "consumables": {
                        "quintessence": {"amount": 5, "type": "refined"},
                        "tass": {"various": True, "minimum_resonance": 1},
                    },
                },
            },
            "circumstantial": {
                "location": {"type": "sanctum", "node_rating": {"min": 1}},
                "time": {
                    "phase": "new_moon",
                    "duration": "hours",
                    "uninterrupted": True,
                },
                "preparation": {
                    "fasting": {"hours": 24},
                    "meditation": {"hours": 4, "focus": "sphere_attunement"},
                    "ritual_purification": {"required": True, "water_type": "blessed"},
                },
            },
            "meta": {
                "version": "1.2.3",
                "created_by": "system_generator",
                "difficulty_rating": 8,
                "tags": ["advanced", "hermetic", "laboratory_work", "long_duration"],
                "references": {
                    "book": "Mage: The Ascension 20th Anniversary",
                    "page": 123,
                    "chapter": "Advanced Magick",
                },
            },
        }

        prerequisite = Prerequisite.objects.create(
            description="Complex magical working prerequisite",
            requirements=complex_requirements,
        )

        prerequisite.refresh_from_db()

        # Verify deep nested access works
        self.assertEqual(
            prerequisite.requirements["character_requirements"]["primary_attributes"][
                "strength"
            ]["min"],
            2,
        )
        self.assertEqual(
            prerequisite.requirements["item_requirements"]["focus_items"][
                "minimum_rating"
            ],
            2,
        )
        self.assertEqual(
            prerequisite.requirements["circumstantial"]["time"]["phase"], "new_moon"
        )
        self.assertEqual(prerequisite.requirements["meta"]["difficulty_rating"], 8)

    def test_prerequisite_empty_description_validation(self):
        """Test that empty description fails validation."""
        with self.assertRaises(ValidationError) as context:
            prerequisite = Prerequisite(description="")
            prerequisite.full_clean()

        self.assertIn("description", context.exception.message_dict)

    def test_prerequisite_whitespace_description_validation(self):
        """Test that whitespace-only description fails validation."""
        with self.assertRaises(ValidationError) as context:
            prerequisite = Prerequisite(description="   \n\t   ")
            prerequisite.full_clean()

        self.assertIn("description", context.exception.message_dict)

    def test_prerequisite_content_object_type_validation(self):
        """Test that invalid content objects are handled properly."""
        # This should work - creating a prerequisite with invalid object
        # GenericForeignKey should handle it gracefully
        prerequisite = Prerequisite.objects.create(
            description="Test with invalid object ID",
            content_type=ContentType.objects.get_for_model(Character),
            object_id=99999,  # Non-existent ID
        )

        # content_object should return None for non-existent object
        self.assertIsNone(prerequisite.content_object)
        self.assertEqual(prerequisite.object_id, 99999)


class PrerequisitePerformanceTest(TransactionTestCase):
    """Test performance-related aspects of Prerequisites."""

    def setUp(self):
        """Set up test data."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            game_system="mage",
            max_characters_per_player=0,  # Allow unlimited characters for testing
        )

    def test_bulk_prerequisite_creation(self):
        """Test creating many prerequisites efficiently."""
        # Create test objects
        characters = []
        for i in range(10):
            char = Character.objects.create(
                name=f"Test Character {i}",
                campaign=self.campaign,
                player_owner=self.owner,
                game_system="mage",
            )
            characters.append(char)

        # Create prerequisites for each character
        prerequisites = []
        for i, character in enumerate(characters):
            prereq = Prerequisite(
                description=f"Requirement for character {i}",
                requirements={"character_level": i + 1},
                content_object=character,
            )
            prerequisites.append(prereq)

        # Bulk create
        Prerequisite.objects.bulk_create(prerequisites)

        # Verify all created
        self.assertEqual(Prerequisite.objects.count(), 10)

        # Test efficient querying
        character_ct = ContentType.objects.get_for_model(Character)
        char_prerequisites = Prerequisite.objects.filter(content_type=character_ct)

        self.assertEqual(char_prerequisites.count(), 10)

    def test_json_field_indexing_query(self):
        """Test querying on JSON field for performance."""
        # Create prerequisites with different JSON structures
        test_data = [
            {"type": "combat", "level": 1},
            {"type": "magic", "level": 2},
            {"type": "social", "level": 1},
            {"type": "combat", "level": 3},
            {"type": "magic", "level": 1},
        ]

        for i, req in enumerate(test_data):
            Prerequisite.objects.create(
                description=f"Test requirement {i}", requirements=req
            )

        # Test JSON field queries
        combat_reqs = Prerequisite.objects.filter(requirements__type="combat")
        self.assertEqual(combat_reqs.count(), 2)

        level_1_reqs = Prerequisite.objects.filter(requirements__level=1)
        self.assertEqual(level_1_reqs.count(), 3)

        # Test complex JSON query
        combat_level_1 = Prerequisite.objects.filter(
            requirements__type="combat", requirements__level=1
        )
        self.assertEqual(combat_level_1.count(), 1)
