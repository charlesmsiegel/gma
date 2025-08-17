"""
Tests for core model mixins.

Comprehensive tests for all 6 mixins required by issue #193:
- TimestampedMixin (created_at, updated_at)
- DisplayableMixin (is_displayed, display_order)
- NamedModelMixin (name field, __str__ method)
- DescribedModelMixin (description field)
- AuditableMixin (created_by, modified_by)
- GameSystemMixin (game_system choices)

Tests cover individual mixin functionality, mixin combinations,
field type validation, default values, and abstract base class inheritance.
"""

import time

from django.contrib.auth import get_user_model
from django.db import models
from django.test import TestCase
from django.utils import timezone as django_timezone

from core.models.mixins import (
    AuditableMixin,
    DescribedModelMixin,
    DisplayableMixin,
    GameSystemMixin,
    NamedModelMixin,
    TimestampedMixin,
)

User = get_user_model()


# Test models for individual mixins
class TimestampedTestModel(TimestampedMixin):
    """Test model using only TimestampedMixin."""

    title = models.CharField(max_length=100)

    class Meta:
        app_label = "core"


class DisplayableTestModel(DisplayableMixin):
    """Test model using only DisplayableMixin."""

    title = models.CharField(max_length=100)

    class Meta:
        app_label = "core"


class NamedTestModel(NamedModelMixin):
    """Test model using only NamedModelMixin."""

    extra_field = models.CharField(max_length=50, default="extra")

    class Meta:
        app_label = "core"


class DescribedTestModel(DescribedModelMixin):
    """Test model using only DescribedModelMixin."""

    title = models.CharField(max_length=100)

    class Meta:
        app_label = "core"


class AuditableTestModel(AuditableMixin):
    """Test model using only AuditableMixin."""

    title = models.CharField(max_length=100)

    class Meta:
        app_label = "core"


class GameSystemTestModel(GameSystemMixin):
    """Test model using only GameSystemMixin."""

    title = models.CharField(max_length=100)

    class Meta:
        app_label = "core"


# Test models for mixin combinations
class FullMixinTestModel(
    TimestampedMixin,
    DisplayableMixin,
    NamedModelMixin,
    DescribedModelMixin,
    AuditableMixin,
    GameSystemMixin,
):
    """Test model using all 6 mixins combined."""

    extra_field = models.CharField(max_length=50, default="extra")

    class Meta:
        app_label = "core"


class PartialMixinTestModel(TimestampedMixin, NamedModelMixin, GameSystemMixin):
    """Test model using a partial combination of mixins."""

    extra_field = models.CharField(max_length=50, default="extra")

    class Meta:
        app_label = "core"


class TimestampedMixinTest(TestCase):
    """Test TimestampedMixin functionality."""

    def test_has_timestamp_fields(self):
        """Test that TimestampedMixin provides created_at and updated_at fields."""
        fields = {f.name: f for f in TimestampedTestModel._meta.get_fields()}

        self.assertIn("created_at", fields)
        self.assertIn("updated_at", fields)
        self.assertIsInstance(fields["created_at"], models.DateTimeField)
        self.assertIsInstance(fields["updated_at"], models.DateTimeField)

    def test_timestamp_field_properties(self):
        """Test that timestamp fields have correct properties."""
        fields = {f.name: f for f in TimestampedTestModel._meta.get_fields()}

        created_at_field = fields["created_at"]
        updated_at_field = fields["updated_at"]

        self.assertTrue(created_at_field.auto_now_add)
        self.assertFalse(created_at_field.auto_now)
        self.assertFalse(updated_at_field.auto_now_add)
        self.assertTrue(updated_at_field.auto_now)

    def test_timestamps_set_on_create(self):
        """Test that timestamps are automatically set when creating an object."""
        before_create = django_timezone.now()
        obj = TimestampedTestModel.objects.create(title="Test Object")
        after_create = django_timezone.now()

        self.assertIsNotNone(obj.created_at)
        self.assertIsNotNone(obj.updated_at)
        self.assertGreaterEqual(obj.created_at, before_create)
        self.assertLessEqual(obj.created_at, after_create)
        # Initially created_at and updated_at should be very close (within 1 second)
        time_diff = abs((obj.created_at - obj.updated_at).total_seconds())
        self.assertLess(time_diff, 1.0)

    def test_updated_at_changes_on_save(self):
        """Test that updated_at changes when object is saved."""
        obj = TimestampedTestModel.objects.create(title="Test Object")
        original_created_at = obj.created_at
        original_updated_at = obj.updated_at

        time.sleep(0.1)
        obj.title = "Updated Title"
        obj.save()
        obj.refresh_from_db()

        self.assertEqual(obj.created_at, original_created_at)
        self.assertGreater(obj.updated_at, original_updated_at)

    def test_abstract_base_class(self):
        """Test that TimestampedMixin is an abstract base class."""
        self.assertTrue(TimestampedMixin._meta.abstract)


class DisplayableMixinTest(TestCase):
    """Test DisplayableMixin functionality."""

    def test_has_displayable_fields(self):
        """Test that DisplayableMixin provides is_displayed and display_order fields."""
        fields = {f.name: f for f in DisplayableTestModel._meta.get_fields()}

        self.assertIn("is_displayed", fields)
        self.assertIn("display_order", fields)
        self.assertIsInstance(fields["is_displayed"], models.BooleanField)
        self.assertIsInstance(fields["display_order"], models.PositiveIntegerField)

    def test_default_values(self):
        """Test that DisplayableMixin fields have correct default values."""
        obj = DisplayableTestModel.objects.create(title="Test Object")

        self.assertTrue(obj.is_displayed)
        self.assertEqual(obj.display_order, 0)

    def test_custom_values(self):
        """Test that DisplayableMixin fields can be set to custom values."""
        obj = DisplayableTestModel.objects.create(
            title="Test Object", is_displayed=False, display_order=10
        )

        self.assertFalse(obj.is_displayed)
        self.assertEqual(obj.display_order, 10)

    def test_display_order_validation(self):
        """Test that display_order only accepts positive integers."""
        # Positive integers should work
        obj = DisplayableTestModel.objects.create(title="Test", display_order=5)
        self.assertEqual(obj.display_order, 5)

        # Zero should work (it's considered positive in PositiveIntegerField)
        obj = DisplayableTestModel.objects.create(title="Test", display_order=0)
        self.assertEqual(obj.display_order, 0)

    def test_abstract_base_class(self):
        """Test that DisplayableMixin is an abstract base class."""
        self.assertTrue(DisplayableMixin._meta.abstract)


class NamedModelMixinTest(TestCase):
    """Test NamedModelMixin functionality."""

    def test_has_name_field(self):
        """Test that NamedModelMixin provides name field."""
        fields = {f.name: f for f in NamedTestModel._meta.get_fields()}

        self.assertIn("name", fields)
        self.assertIsInstance(fields["name"], models.CharField)
        self.assertEqual(fields["name"].max_length, 100)

    def test_name_field_required(self):
        """Test that name field is required."""
        fields = {f.name: f for f in NamedTestModel._meta.get_fields()}
        name_field = fields["name"]

        self.assertFalse(name_field.blank)
        self.assertFalse(name_field.null)

    def test_str_method(self):
        """Test that NamedModelMixin provides __str__ method that returns name."""
        obj = NamedTestModel.objects.create(name="Test Name")

        self.assertEqual(str(obj), "Test Name")
        self.assertEqual(obj.__str__(), "Test Name")

    def test_str_method_with_special_characters(self):
        """Test __str__ method with special characters and unicode."""
        obj = NamedTestModel.objects.create(name="Test ñame with ünicode & symbols!")

        self.assertEqual(str(obj), "Test ñame with ünicode & symbols!")

    def test_abstract_base_class(self):
        """Test that NamedModelMixin is an abstract base class."""
        self.assertTrue(NamedModelMixin._meta.abstract)


class DescribedModelMixinTest(TestCase):
    """Test DescribedModelMixin functionality."""

    def test_has_description_field(self):
        """Test that DescribedModelMixin provides description field."""
        fields = {f.name: f for f in DescribedTestModel._meta.get_fields()}

        self.assertIn("description", fields)
        self.assertIsInstance(fields["description"], models.TextField)

    def test_description_field_optional(self):
        """Test that description field is optional."""
        fields = {f.name: f for f in DescribedTestModel._meta.get_fields()}
        description_field = fields["description"]

        self.assertTrue(description_field.blank)
        self.assertEqual(description_field.default, "")

    def test_default_description(self):
        """Test that description has empty string as default."""
        obj = DescribedTestModel.objects.create(title="Test Object")

        self.assertEqual(obj.description, "")

    def test_custom_description(self):
        """Test that description can be set to custom value."""
        description_text = "This is a detailed description of the test object."
        obj = DescribedTestModel.objects.create(
            title="Test Object", description=description_text
        )

        self.assertEqual(obj.description, description_text)

    def test_long_description(self):
        """Test that description can handle long text."""
        long_description = "Lorem ipsum " * 100  # Very long text
        obj = DescribedTestModel.objects.create(
            title="Test Object", description=long_description
        )

        self.assertEqual(obj.description, long_description)

    def test_abstract_base_class(self):
        """Test that DescribedModelMixin is an abstract base class."""
        self.assertTrue(DescribedModelMixin._meta.abstract)


class AuditableMixinTest(TestCase):
    """Test AuditableMixin functionality."""

    def setUp(self):
        """Set up test users."""
        self.user1 = User.objects.create_user(
            username="testuser1", email="test1@example.com", password="testpass123"
        )
        self.user2 = User.objects.create_user(
            username="testuser2", email="test2@example.com", password="testpass123"
        )

    def test_has_audit_fields(self):
        """Test that AuditableMixin provides created_by and modified_by fields."""
        fields = {f.name: f for f in AuditableTestModel._meta.get_fields()}

        self.assertIn("created_by", fields)
        self.assertIn("modified_by", fields)
        self.assertIsInstance(fields["created_by"], models.ForeignKey)
        self.assertIsInstance(fields["modified_by"], models.ForeignKey)

    def test_audit_fields_optional(self):
        """Test that audit fields are optional."""
        fields = {f.name: f for f in AuditableTestModel._meta.get_fields()}

        created_by_field = fields["created_by"]
        modified_by_field = fields["modified_by"]

        self.assertTrue(created_by_field.null)
        self.assertTrue(created_by_field.blank)
        self.assertTrue(modified_by_field.null)
        self.assertTrue(modified_by_field.blank)

    def test_audit_fields_foreign_key_properties(self):
        """Test that audit fields have correct ForeignKey properties."""
        fields = {f.name: f for f in AuditableTestModel._meta.get_fields()}

        created_by_field = fields["created_by"]
        modified_by_field = fields["modified_by"]

        self.assertEqual(created_by_field.related_model, User)
        self.assertEqual(modified_by_field.related_model, User)
        self.assertEqual(created_by_field.remote_field.on_delete, models.CASCADE)
        self.assertEqual(modified_by_field.remote_field.on_delete, models.CASCADE)

    def test_audit_fields_related_names(self):
        """Test that audit fields have proper related names."""
        fields = {f.name: f for f in AuditableTestModel._meta.get_fields()}

        created_by_field = fields["created_by"]
        modified_by_field = fields["modified_by"]

        # Should use %(app_label)s_%(class)s pattern
        self.assertEqual(
            created_by_field.related_query_name(), "core_auditabletestmodel_created"
        )
        self.assertEqual(
            modified_by_field.related_query_name(), "core_auditabletestmodel_modified"
        )

    def test_audit_fields_default_null(self):
        """Test that audit fields default to null."""
        obj = AuditableTestModel.objects.create(title="Test Object")

        self.assertIsNone(obj.created_by)
        self.assertIsNone(obj.modified_by)

    def test_audit_fields_can_be_set(self):
        """Test that audit fields can be set to users."""
        obj = AuditableTestModel.objects.create(
            title="Test Object", created_by=self.user1, modified_by=self.user2
        )

        self.assertEqual(obj.created_by, self.user1)
        self.assertEqual(obj.modified_by, self.user2)

    def test_audit_fields_user_relationship(self):
        """Test that audit fields properly relate to User model."""
        obj = AuditableTestModel.objects.create(
            title="Test Object", created_by=self.user1, modified_by=self.user1
        )

        # Test reverse relationship
        created_objects = self.user1.core_auditabletestmodel_created.all()
        modified_objects = self.user1.core_auditabletestmodel_modified.all()

        self.assertIn(obj, created_objects)
        self.assertIn(obj, modified_objects)

    def test_abstract_base_class(self):
        """Test that AuditableMixin is an abstract base class."""
        self.assertTrue(AuditableMixin._meta.abstract)


class GameSystemMixinTest(TestCase):
    """Test GameSystemMixin functionality."""

    def test_has_game_system_field(self):
        """Test that GameSystemMixin provides game_system field."""
        fields = {f.name: f for f in GameSystemTestModel._meta.get_fields()}

        self.assertIn("game_system", fields)
        self.assertIsInstance(fields["game_system"], models.CharField)
        self.assertEqual(fields["game_system"].max_length, 50)

    def test_game_system_choices(self):
        """Test that game_system field has correct choices."""
        fields = {f.name: f for f in GameSystemTestModel._meta.get_fields()}
        game_system_field = fields["game_system"]

        expected_choices = [
            ("generic", "Generic/Universal"),
            ("wod", "World of Darkness"),
            ("mage", "Mage: The Ascension"),
            ("vampire", "Vampire: The Masquerade"),
            ("werewolf", "Werewolf: The Apocalypse"),
            ("changeling", "Changeling: The Dreaming"),
            ("wraith", "Wraith: The Oblivion"),
            ("hunter", "Hunter: The Reckoning"),
            ("mummy", "Mummy: The Resurrection"),
            ("demon", "Demon: The Fallen"),
            ("nwod", "Chronicles of Darkness"),
            ("dnd5e", "Dungeons & Dragons 5th Edition"),
            ("pathfinder", "Pathfinder"),
            ("shadowrun", "Shadowrun"),
            ("call_of_cthulhu", "Call of Cthulhu"),
            ("savage_worlds", "Savage Worlds"),
            ("fate", "Fate Core"),
            ("pbta", "Powered by the Apocalypse"),
            ("other", "Other"),
        ]

        self.assertEqual(list(game_system_field.choices), expected_choices)

    def test_game_system_default(self):
        """Test that game_system has correct default value."""
        obj = GameSystemTestModel.objects.create(title="Test Object")

        self.assertEqual(obj.game_system, "generic")

    def test_game_system_valid_choices(self):
        """Test that game_system accepts valid choice values."""
        valid_choices = [
            "generic",
            "wod",
            "mage",
            "vampire",
            "werewolf",
            "changeling",
            "wraith",
            "hunter",
            "mummy",
            "demon",
            "nwod",
            "dnd5e",
            "pathfinder",
            "shadowrun",
            "call_of_cthulhu",
            "savage_worlds",
            "fate",
            "pbta",
            "other",
        ]

        for choice in valid_choices:
            obj = GameSystemTestModel.objects.create(
                title=f"Test {choice}", game_system=choice
            )
            self.assertEqual(obj.game_system, choice)

    def test_game_system_choice_labels(self):
        """Test that game_system choices have proper labels."""
        obj = GameSystemTestModel.objects.create(
            title="Test Object", game_system="mage"
        )

        # Test get_FOO_display() method
        self.assertEqual(obj.get_game_system_display(), "Mage: The Ascension")

    def test_abstract_base_class(self):
        """Test that GameSystemMixin is an abstract base class."""
        self.assertTrue(GameSystemMixin._meta.abstract)


class MixinCombinationTest(TestCase):
    """Test that mixins work correctly when combined."""

    def setUp(self):
        """Set up test user for auditable tests."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def test_full_mixin_combination_fields(self):
        """Test that all mixins can be combined without field conflicts."""
        fields = {f.name: f for f in FullMixinTestModel._meta.get_fields()}

        # TimestampedMixin fields
        self.assertIn("created_at", fields)
        self.assertIn("updated_at", fields)

        # DisplayableMixin fields
        self.assertIn("is_displayed", fields)
        self.assertIn("display_order", fields)

        # NamedModelMixin fields
        self.assertIn("name", fields)

        # DescribedModelMixin fields
        self.assertIn("description", fields)

        # AuditableMixin fields
        self.assertIn("created_by", fields)
        self.assertIn("modified_by", fields)

        # GameSystemMixin fields
        self.assertIn("game_system", fields)

        # Model's own field
        self.assertIn("extra_field", fields)

    def test_full_mixin_combination_functionality(self):
        """Test that all mixin functionality works when combined."""
        before_create = django_timezone.now()

        obj = FullMixinTestModel.objects.create(
            name="Test Full Mixin",
            description="This is a test description",
            is_displayed=False,
            display_order=5,
            game_system="mage",
            created_by=self.user,
            modified_by=self.user,
        )

        after_create = django_timezone.now()

        # Test TimestampedMixin
        self.assertIsNotNone(obj.created_at)
        self.assertIsNotNone(obj.updated_at)
        self.assertGreaterEqual(obj.created_at, before_create)
        self.assertLessEqual(obj.created_at, after_create)

        # Test DisplayableMixin
        self.assertFalse(obj.is_displayed)
        self.assertEqual(obj.display_order, 5)

        # Test NamedModelMixin
        self.assertEqual(obj.name, "Test Full Mixin")
        self.assertEqual(str(obj), "Test Full Mixin")

        # Test DescribedModelMixin
        self.assertEqual(obj.description, "This is a test description")

        # Test AuditableMixin
        self.assertEqual(obj.created_by, self.user)
        self.assertEqual(obj.modified_by, self.user)

        # Test GameSystemMixin
        self.assertEqual(obj.game_system, "mage")
        self.assertEqual(obj.get_game_system_display(), "Mage: The Ascension")

    def test_partial_mixin_combination(self):
        """Test that partial mixin combinations work correctly."""
        obj = PartialMixinTestModel.objects.create(
            name="Partial Test", game_system="dnd5e"
        )

        # Should have TimestampedMixin, NamedModelMixin, and GameSystemMixin fields
        self.assertIsNotNone(obj.created_at)
        self.assertIsNotNone(obj.updated_at)
        self.assertEqual(obj.name, "Partial Test")
        self.assertEqual(str(obj), "Partial Test")
        self.assertEqual(obj.game_system, "dnd5e")

        # Should NOT have DisplayableMixin, DescribedModelMixin, or
        # AuditableMixin fields
        fields = {f.name: f for f in PartialMixinTestModel._meta.get_fields()}
        self.assertNotIn("is_displayed", fields)
        self.assertNotIn("display_order", fields)
        self.assertNotIn("description", fields)
        self.assertNotIn("created_by", fields)
        self.assertNotIn("modified_by", fields)

    def test_mixin_default_values_in_combination(self):
        """Test that mixin default values work correctly when combined."""
        obj = FullMixinTestModel.objects.create(name="Default Test")

        # Test default values from each mixin
        self.assertTrue(obj.is_displayed)  # DisplayableMixin
        self.assertEqual(obj.display_order, 0)  # DisplayableMixin
        self.assertEqual(obj.description, "")  # DescribedModelMixin
        self.assertIsNone(obj.created_by)  # AuditableMixin
        self.assertIsNone(obj.modified_by)  # AuditableMixin
        self.assertEqual(obj.game_system, "generic")  # GameSystemMixin

    def test_mixin_method_inheritance(self):
        """Test that mixin methods work correctly in combinations."""
        obj = FullMixinTestModel.objects.create(name="Method Test")

        # NamedModelMixin __str__ method should work
        self.assertEqual(str(obj), "Method Test")

        # GameSystemMixin get_FOO_display method should work
        obj.game_system = "vampire"
        obj.save()
        self.assertEqual(obj.get_game_system_display(), "Vampire: The Masquerade")

    def test_abstract_inheritance(self):
        """Test that all mixins properly inherit as abstract base classes."""
        # All mixins should be abstract
        self.assertTrue(TimestampedMixin._meta.abstract)
        self.assertTrue(DisplayableMixin._meta.abstract)
        self.assertTrue(NamedModelMixin._meta.abstract)
        self.assertTrue(DescribedModelMixin._meta.abstract)
        self.assertTrue(AuditableMixin._meta.abstract)
        self.assertTrue(GameSystemMixin._meta.abstract)

        # Combined models should not be abstract
        self.assertFalse(FullMixinTestModel._meta.abstract)
        self.assertFalse(PartialMixinTestModel._meta.abstract)

    def test_no_field_conflicts(self):
        """Test that mixins don't create field name conflicts."""
        # Get all field names from the full combination model
        field_names = [f.name for f in FullMixinTestModel._meta.get_fields()]

        # Check that each field name appears only once
        self.assertEqual(len(field_names), len(set(field_names)))

        # Verify expected field count (6 mixins + 1 extra field + 1 id field)
        expected_fields = {
            "id",  # Auto-generated primary key
            "created_at",
            "updated_at",  # TimestampedMixin
            "is_displayed",
            "display_order",  # DisplayableMixin
            "name",  # NamedModelMixin
            "description",  # DescribedModelMixin
            "created_by",
            "modified_by",  # AuditableMixin
            "game_system",  # GameSystemMixin
            "extra_field",  # Model's own field
        }

        self.assertEqual(set(field_names), expected_fields)


class MixinDatabaseMigrationTest(TestCase):
    """Test that mixins work correctly with database migrations."""

    def test_model_creation_succeeds(self):
        """Test that models using mixins can be created successfully."""
        # This test verifies that the database schema is created correctly
        # and that all mixin fields are properly included in the tables

        # Test individual mixin models
        TimestampedTestModel.objects.create(title="Timestamped Test")
        DisplayableTestModel.objects.create(title="Displayable Test")
        NamedTestModel.objects.create(name="Named Test")
        DescribedTestModel.objects.create(title="Described Test")
        AuditableTestModel.objects.create(title="Auditable Test")
        GameSystemTestModel.objects.create(title="GameSystem Test")

        # Test combination models
        FullMixinTestModel.objects.create(name="Full Test")
        PartialMixinTestModel.objects.create(name="Partial Test")

        # If we get here without exceptions, the database schema is correct
        self.assertTrue(True)

    def test_model_field_database_types(self):
        """Test that mixin fields have correct database column types."""
        from django.conf import settings
        from django.db import connection

        # Skip this test for SQLite as it doesn't have information_schema
        if "sqlite" in settings.DATABASES["default"]["ENGINE"]:
            self.skipTest("SQLite doesn't support information_schema queries")

        # Get table description for full mixin model (PostgreSQL specific)
        with connection.cursor() as cursor:
            table_name = FullMixinTestModel._meta.db_table
            cursor.execute(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_name = %s",
                [table_name],
            )
            columns = {row[0]: row[1] for row in cursor.fetchall()}

        # Verify expected column types exist (this confirms migrations worked)
        expected_columns = {
            "created_at": "timestamp",
            "updated_at": "timestamp",
            "is_displayed": "boolean",
            "display_order": "integer",
            "name": "character",
            "description": "text",
            "game_system": "character",
        }

        for column_name, expected_type in expected_columns.items():
            self.assertIn(column_name, columns)
            # PostgreSQL specific type checking
            if expected_type == "timestamp":
                self.assertIn(
                    columns[column_name],
                    ["timestamp with time zone", "timestamp without time zone"],
                )
            elif expected_type == "character":
                self.assertIn(columns[column_name], ["character varying", "varchar"])
            elif expected_type in ["boolean", "integer", "text"]:
                self.assertEqual(columns[column_name], expected_type)

    def test_model_field_attributes_verification(self):
        """Test that mixin fields have correct attributes (database-agnostic)."""
        # This test works with any database backend
        fields = {f.name: f for f in FullMixinTestModel._meta.get_fields()}

        # Verify all expected fields exist
        expected_field_names = {
            "id",
            "created_at",
            "updated_at",
            "is_displayed",
            "display_order",
            "name",
            "description",
            "created_by",
            "modified_by",
            "game_system",
            "extra_field",
        }
        actual_field_names = set(fields.keys())
        self.assertEqual(actual_field_names, expected_field_names)

        # Test specific field attributes
        self.assertTrue(fields["created_at"].auto_now_add)
        self.assertTrue(fields["updated_at"].auto_now)
        self.assertEqual(fields["name"].max_length, 100)
        self.assertEqual(fields["game_system"].max_length, 50)
        self.assertTrue(fields["description"].blank)
        self.assertTrue(fields["created_by"].null)
        self.assertTrue(fields["modified_by"].blank)
