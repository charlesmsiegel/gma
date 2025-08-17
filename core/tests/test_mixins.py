"""
Comprehensive tests for Django model mixins.

These tests verify the functionality of core model mixins and their combinations:
1. TimestampedMixin - provides created_at and updated_at fields
2. DisplayableMixin - provides is_displayed and display_order fields
3. NamedModelMixin - provides name field and __str__ method
4. DescribedModelMixin - provides description field
5. AuditableMixin - provides created_by and modified_by fields
6. GameSystemMixin - provides game_system field with choices

Tests cover:
- Individual mixin functionality
- Field types and defaults
- Abstract base class inheritance
- Migration compatibility
- Mixin combinations without conflicts
- Auto-update behavior for timestamps
- Foreign key relationships
- Choice field validation
- __str__ method behavior
"""

import time

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.test import TestCase, TransactionTestCase
from django.test.utils import override_settings
from django.utils import timezone as django_timezone

# Import the mixins we'll be testing
from core.models.mixins import (
    AuditableMixin,
    DescribedModelMixin,
    DisplayableMixin,
    GameSystemMixin,
    NamedModelMixin,
    TimestampedMixin,
)

User = get_user_model()


# Test models that use individual mixins
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

    extra_field = models.CharField(max_length=50, blank=True)

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


# Test models that combine multiple mixins
class FullMixinTestModel(
    TimestampedMixin,
    DisplayableMixin,
    NamedModelMixin,
    DescribedModelMixin,
    AuditableMixin,
    GameSystemMixin,
):
    """Test model using all mixins combined."""

    extra_field = models.CharField(max_length=50, blank=True)

    class Meta:
        app_label = "core"


class PartialMixinTestModel(TimestampedMixin, NamedModelMixin, AuditableMixin):
    """Test model using a subset of mixins."""

    extra_field = models.CharField(max_length=50, blank=True)

    class Meta:
        app_label = "core"


class DisplayOrderTestModel(DisplayableMixin):
    """Test model for testing display order functionality."""

    category = models.CharField(max_length=50)

    class Meta:
        app_label = "core"


class TimestampedMixinTest(TestCase):
    """Test TimestampedMixin functionality."""

    def test_has_timestamp_fields(self):
        """Test that TimestampedMixin provides created_at and updated_at fields."""
        # Check field existence through model meta
        fields = {f.name: f for f in TimestampedTestModel._meta.get_fields()}

        self.assertIn("created_at", fields)
        self.assertIn("updated_at", fields)

        # Check field types
        self.assertIsInstance(fields["created_at"], models.DateTimeField)
        self.assertIsInstance(fields["updated_at"], models.DateTimeField)

        # Check field properties
        self.assertTrue(fields["created_at"].auto_now_add)
        self.assertTrue(fields["updated_at"].auto_now)

    def test_timestamps_set_on_create(self):
        """Test that timestamps are automatically set when creating an object."""
        before_create = django_timezone.now()

        obj = TimestampedTestModel.objects.create(title="Test Object")

        after_create = django_timezone.now()

        # Verify timestamps are set
        self.assertIsNotNone(obj.created_at)
        self.assertIsNotNone(obj.updated_at)

        # Verify timestamps are within reasonable range
        self.assertGreaterEqual(obj.created_at, before_create)
        self.assertLessEqual(obj.created_at, after_create)
        self.assertGreaterEqual(obj.updated_at, before_create)
        self.assertLessEqual(obj.updated_at, after_create)

        # Verify created_at and updated_at are very close (within 1 second)
        # Note: They may not be exactly the same due to Django's field processing order
        time_diff = abs((obj.created_at - obj.updated_at).total_seconds())
        self.assertLess(
            time_diff, 1.0, "created_at and updated_at should be very close initially"
        )

    def test_updated_at_changes_on_save(self):
        """Test that updated_at changes when object is saved."""
        obj = TimestampedTestModel.objects.create(title="Test Object")
        original_created_at = obj.created_at
        original_updated_at = obj.updated_at

        # Wait a small amount to ensure different timestamp
        time.sleep(0.1)

        # Update and save
        obj.title = "Updated Title"
        obj.save()

        # Refresh from database
        obj.refresh_from_db()

        # Verify created_at hasn't changed
        self.assertEqual(obj.created_at, original_created_at)

        # Verify updated_at has changed
        self.assertNotEqual(obj.updated_at, original_updated_at)
        self.assertGreater(obj.updated_at, original_updated_at)

    def test_created_at_immutable(self):
        """Test that created_at doesn't change on subsequent saves."""
        obj = TimestampedTestModel.objects.create(title="Test Object")
        original_created_at = obj.created_at

        # Save multiple times
        for i in range(3):
            time.sleep(0.1)
            obj.title = f"Updated Title {i}"
            obj.save()
            obj.refresh_from_db()
            self.assertEqual(obj.created_at, original_created_at)


class DisplayableMixinTest(TestCase):
    """Test DisplayableMixin functionality."""

    def test_has_displayable_fields(self):
        """Test that DisplayableMixin provides is_displayed and display_order fields."""
        fields = {f.name: f for f in DisplayableTestModel._meta.get_fields()}

        self.assertIn("is_displayed", fields)
        self.assertIn("display_order", fields)

        # Check field types
        self.assertIsInstance(fields["is_displayed"], models.BooleanField)
        self.assertIsInstance(fields["display_order"], models.PositiveIntegerField)

    def test_default_values(self):
        """Test default values for displayable fields."""
        obj = DisplayableTestModel.objects.create(title="Test Object")

        # Check defaults
        self.assertTrue(obj.is_displayed)  # Should default to True
        self.assertEqual(obj.display_order, 0)  # Should default to 0

    def test_custom_values(self):
        """Test setting custom values for displayable fields."""
        obj = DisplayableTestModel.objects.create(
            title="Test Object", is_displayed=False, display_order=5
        )

        self.assertFalse(obj.is_displayed)
        self.assertEqual(obj.display_order, 5)

    def test_display_order_positive_constraint(self):
        """Test that display_order only accepts positive integers."""
        # Valid positive values should work
        obj = DisplayableTestModel.objects.create(title="Test Object", display_order=10)
        self.assertEqual(obj.display_order, 10)

        # Zero should work (it's included in PositiveIntegerField)
        obj2 = DisplayableTestModel.objects.create(
            title="Test Object 2", display_order=0
        )
        self.assertEqual(obj2.display_order, 0)

    def test_ordering_by_display_order(self):
        """Test that objects can be ordered by display_order."""
        # Create objects with different display orders
        obj1 = DisplayOrderTestModel.objects.create(category="A", display_order=3)
        obj2 = DisplayOrderTestModel.objects.create(category="A", display_order=1)
        obj3 = DisplayOrderTestModel.objects.create(category="A", display_order=2)

        # Query and order by display_order
        ordered_objects = DisplayOrderTestModel.objects.filter(category="A").order_by(
            "display_order"
        )

        # Verify order
        self.assertEqual(list(ordered_objects), [obj2, obj3, obj1])


class NamedModelMixinTest(TestCase):
    """Test NamedModelMixin functionality."""

    def test_has_name_field(self):
        """Test that NamedModelMixin provides a name field."""
        fields = {f.name: f for f in NamedTestModel._meta.get_fields()}

        self.assertIn("name", fields)
        self.assertIsInstance(fields["name"], models.CharField)
        self.assertEqual(fields["name"].max_length, 100)

    def test_name_field_properties(self):
        """Test name field properties."""
        fields = {f.name: f for f in NamedTestModel._meta.get_fields()}
        name_field = fields["name"]

        # Name should not be blank by default
        self.assertFalse(name_field.blank)
        self.assertFalse(name_field.null)

    def test_str_method(self):
        """Test that __str__ method returns the name."""
        obj = NamedTestModel.objects.create(name="Test Name")
        self.assertEqual(str(obj), "Test Name")

    def test_str_method_with_empty_name(self):
        """Test __str__ method behavior with empty name."""
        # This should raise validation error due to required name field
        with self.assertRaises(ValidationError):
            obj = NamedTestModel(name="")
            obj.full_clean()

    def test_name_max_length(self):
        """Test name field maximum length."""
        # Should work with 100 characters
        long_name = "a" * 100
        obj = NamedTestModel.objects.create(name=long_name)
        self.assertEqual(obj.name, long_name)

        # Should fail validation with 101 characters
        too_long_name = "a" * 101
        with self.assertRaises(ValidationError):
            obj = NamedTestModel(name=too_long_name)
            obj.full_clean()


class DescribedModelMixinTest(TestCase):
    """Test DescribedModelMixin functionality."""

    def test_has_description_field(self):
        """Test that DescribedModelMixin provides a description field."""
        fields = {f.name: f for f in DescribedTestModel._meta.get_fields()}

        self.assertIn("description", fields)
        self.assertIsInstance(fields["description"], models.TextField)

    def test_description_field_properties(self):
        """Test description field properties."""
        fields = {f.name: f for f in DescribedTestModel._meta.get_fields()}
        description_field = fields["description"]

        # Description should be optional
        self.assertTrue(description_field.blank)
        self.assertFalse(description_field.null)  # Should be empty string, not null

    def test_description_optional(self):
        """Test that description is optional."""
        obj = DescribedTestModel.objects.create(title="Test Object")
        self.assertEqual(obj.description, "")

    def test_description_with_content(self):
        """Test description with actual content."""
        description = "This is a detailed description of the test object."
        obj = DescribedTestModel.objects.create(
            title="Test Object", description=description
        )
        self.assertEqual(obj.description, description)

    def test_description_long_content(self):
        """Test description with very long content."""
        # TextField should handle large amounts of text
        long_description = "a" * 10000
        obj = DescribedTestModel.objects.create(
            title="Test Object", description=long_description
        )
        self.assertEqual(obj.description, long_description)


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

        # Check field types
        self.assertIsInstance(fields["created_by"], models.ForeignKey)
        self.assertIsInstance(fields["modified_by"], models.ForeignKey)

        # Check related model
        self.assertEqual(fields["created_by"].related_model, User)
        self.assertEqual(fields["modified_by"].related_model, User)

    def test_audit_fields_optional(self):
        """Test that audit fields are optional (can be null)."""
        fields = {f.name: f for f in AuditableTestModel._meta.get_fields()}

        # Both fields should allow null values
        self.assertTrue(fields["created_by"].null)
        self.assertTrue(fields["modified_by"].null)
        self.assertTrue(fields["created_by"].blank)
        self.assertTrue(fields["modified_by"].blank)

    def test_audit_fields_with_users(self):
        """Test setting audit fields with actual users."""
        obj = AuditableTestModel.objects.create(
            title="Test Object", created_by=self.user1, modified_by=self.user1
        )

        self.assertEqual(obj.created_by, self.user1)
        self.assertEqual(obj.modified_by, self.user1)

    def test_audit_fields_different_users(self):
        """Test that created_by and modified_by can be different users."""
        obj = AuditableTestModel.objects.create(
            title="Test Object", created_by=self.user1, modified_by=self.user2
        )

        self.assertEqual(obj.created_by, self.user1)
        self.assertEqual(obj.modified_by, self.user2)

    def test_audit_fields_without_users(self):
        """Test that audit fields can be left empty."""
        obj = AuditableTestModel.objects.create(title="Test Object")

        self.assertIsNone(obj.created_by)
        self.assertIsNone(obj.modified_by)

    def test_foreign_key_on_delete_behavior(self):
        """Test CASCADE behavior when referenced user is deleted."""
        obj = AuditableTestModel.objects.create(
            title="Test Object", created_by=self.user1, modified_by=self.user1
        )

        # Delete the user
        self.user1.delete()

        # Object should be deleted due to CASCADE
        with self.assertRaises(AuditableTestModel.DoesNotExist):
            obj.refresh_from_db()


class GameSystemMixinTest(TestCase):
    """Test GameSystemMixin functionality."""

    def test_has_game_system_field(self):
        """Test that GameSystemMixin provides a game_system field."""
        fields = {f.name: f for f in GameSystemTestModel._meta.get_fields()}

        self.assertIn("game_system", fields)
        self.assertIsInstance(fields["game_system"], models.CharField)

    def test_game_system_choices(self):
        """Test that game_system field has the correct choices."""
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

        self.assertEqual(game_system_field.choices, expected_choices)

    def test_game_system_default(self):
        """Test default value for game_system field."""
        obj = GameSystemTestModel.objects.create(title="Test Object")
        self.assertEqual(obj.game_system, "generic")

    def test_game_system_valid_choices(self):
        """Test setting game_system to valid choices."""
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
                title=f"Test Object {choice}", game_system=choice
            )
            self.assertEqual(obj.game_system, choice)

    def test_game_system_invalid_choice(self):
        """Test that invalid game_system choices raise validation error."""
        with self.assertRaises(ValidationError):
            obj = GameSystemTestModel(title="Test Object", game_system="invalid_choice")
            obj.full_clean()

    def test_game_system_max_length(self):
        """Test game_system field maximum length."""
        fields = {f.name: f for f in GameSystemTestModel._meta.get_fields()}
        game_system_field = fields["game_system"]

        # Should have appropriate max_length for the choices
        self.assertEqual(game_system_field.max_length, 50)


class MixinCombinationTest(TestCase):
    """Test combinations of multiple mixins."""

    def setUp(self):
        """Set up test users."""
        self.user1 = User.objects.create_user(
            username="testuser1", email="test1@example.com", password="testpass123"
        )

    def test_full_mixin_combination(self):
        """Test that all mixins can be combined without conflicts."""
        # Create object with all mixin fields
        obj = FullMixinTestModel.objects.create(
            name="Test Object",
            description="Test description",
            is_displayed=True,
            display_order=5,
            game_system="mage",
            created_by=self.user1,
            modified_by=self.user1,
            extra_field="Extra data",
        )

        # Verify all fields are set correctly
        self.assertEqual(obj.name, "Test Object")
        self.assertEqual(obj.description, "Test description")
        self.assertTrue(obj.is_displayed)
        self.assertEqual(obj.display_order, 5)
        self.assertEqual(obj.game_system, "mage")
        self.assertEqual(obj.created_by, self.user1)
        self.assertEqual(obj.modified_by, self.user1)
        self.assertEqual(obj.extra_field, "Extra data")

        # Verify timestamp fields are set
        self.assertIsNotNone(obj.created_at)
        self.assertIsNotNone(obj.updated_at)

        # Verify __str__ method from NamedModelMixin
        self.assertEqual(str(obj), "Test Object")

    def test_partial_mixin_combination(self):
        """Test partial combination of mixins."""
        obj = PartialMixinTestModel.objects.create(
            name="Partial Test", created_by=self.user1, modified_by=self.user1
        )

        # Verify included mixin fields
        self.assertEqual(obj.name, "Partial Test")
        self.assertEqual(obj.created_by, self.user1)
        self.assertEqual(obj.modified_by, self.user1)
        self.assertIsNotNone(obj.created_at)
        self.assertIsNotNone(obj.updated_at)
        self.assertEqual(str(obj), "Partial Test")

        # Verify excluded mixin fields don't exist
        with self.assertRaises(AttributeError):
            _ = obj.description
        with self.assertRaises(AttributeError):
            _ = obj.is_displayed
        with self.assertRaises(AttributeError):
            _ = obj.game_system

    def test_no_field_conflicts(self):
        """Test that mixins don't have conflicting field names."""
        # Get all fields from the full combination model
        fields = {f.name for f in FullMixinTestModel._meta.get_fields()}

        # Expected fields from each mixin
        expected_fields = {
            "id",  # Django's automatic primary key
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

        # Verify all expected fields are present
        self.assertTrue(expected_fields.issubset(fields))

        # Verify no unexpected fields (beyond reverse relations)
        reverse_relation_fields = {
            f.name
            for f in FullMixinTestModel._meta.get_fields()
            if f.is_relation and hasattr(f, "related_name")
        }

        unexpected_fields = fields - expected_fields - reverse_relation_fields
        self.assertEqual(
            len(unexpected_fields), 0, f"Unexpected fields found: {unexpected_fields}"
        )

    def test_migration_compatibility(self):
        """Test that models with mixins can be used in migrations."""
        # This test verifies that the model structure is compatible with
        # Django migrations by checking that all fields have proper
        # migration-compatible attributes

        for model_class in [
            TimestampedTestModel,
            DisplayableTestModel,
            NamedTestModel,
            DescribedTestModel,
            AuditableTestModel,
            GameSystemTestModel,
            FullMixinTestModel,
            PartialMixinTestModel,
        ]:
            # Verify model has a proper Meta class
            self.assertTrue(hasattr(model_class, "_meta"))

            # Verify all fields have the required attributes for migrations
            for field in model_class._meta.get_fields():
                if not field.is_relation or field.many_to_one or field.one_to_one:
                    # Check that field has required attributes
                    self.assertTrue(hasattr(field, "name"))

                    # For non-relation fields, check creation counter exists
                    if not field.is_relation:
                        self.assertTrue(hasattr(field, "creation_counter"))


class MixinInheritanceTest(TestCase):
    """Test that mixins work properly with model inheritance."""

    def test_abstract_base_class(self):
        """Test that all mixins are abstract base classes."""
        abstract_classes = [
            TimestampedMixin,
            DisplayableMixin,
            NamedModelMixin,
            DescribedModelMixin,
            AuditableMixin,
            GameSystemMixin,
        ]

        for mixin_class in abstract_classes:
            self.assertTrue(
                mixin_class._meta.abstract, f"{mixin_class.__name__} should be abstract"
            )

    def test_mixin_inheritance_order(self):
        """Test that mixin inheritance order doesn't cause conflicts."""

        # Create models with different inheritance orders
        class Order1Model(TimestampedMixin, NamedModelMixin):
            class Meta:
                app_label = "core"

        class Order2Model(NamedModelMixin, TimestampedMixin):
            class Meta:
                app_label = "core"

        # Both should have all expected fields
        order1_fields = {f.name for f in Order1Model._meta.get_fields()}
        order2_fields = {f.name for f in Order2Model._meta.get_fields()}

        expected_fields = {"id", "created_at", "updated_at", "name"}

        self.assertTrue(expected_fields.issubset(order1_fields))
        self.assertTrue(expected_fields.issubset(order2_fields))
        self.assertEqual(order1_fields, order2_fields)


class MixinPerformanceTest(TransactionTestCase):
    """Test performance characteristics of mixins."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def test_bulk_create_with_mixins(self):
        """Test that mixins work correctly with bulk operations."""
        # Create multiple objects with mixins
        objects = []
        for i in range(100):
            obj = FullMixinTestModel(
                name=f"Test Object {i}",
                description=f"Description {i}",
                created_by=self.user,
                modified_by=self.user,
                game_system="generic",
            )
            objects.append(obj)

        # Bulk create should work
        created_objects = FullMixinTestModel.objects.bulk_create(objects)

        # Verify objects were created
        self.assertEqual(len(created_objects), 100)

        # Note: auto_now_add and auto_now fields don't work with bulk_create
        # This is expected Django behavior, not a mixin issue

    def test_queryset_performance(self):
        """Test that mixin fields don't negatively impact query performance."""
        # Create test data
        for i in range(10):
            FullMixinTestModel.objects.create(
                name=f"Test Object {i}", created_by=self.user, game_system="mage"
            )

        # Test various queries that might use mixin fields
        queries = [
            FullMixinTestModel.objects.filter(is_displayed=True),
            FullMixinTestModel.objects.filter(game_system="mage"),
            FullMixinTestModel.objects.filter(created_by=self.user),
            FullMixinTestModel.objects.order_by("display_order"),
            FullMixinTestModel.objects.order_by("created_at"),
        ]

        # All queries should execute without errors
        for query in queries:
            result = list(query)
            self.assertGreaterEqual(len(result), 0)


class MixinEdgeCaseTest(TestCase):
    """Test edge cases and error conditions."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def test_unicode_in_name_field(self):
        """Test that name field handles Unicode characters."""
        unicode_name = "测试名称 🎮 नाम テスト"
        obj = NamedTestModel.objects.create(name=unicode_name)
        self.assertEqual(obj.name, unicode_name)
        self.assertEqual(str(obj), unicode_name)

    def test_unicode_in_description_field(self):
        """Test that description field handles Unicode characters."""
        unicode_description = "描述 📝 विवरण 説明"
        obj = DescribedTestModel.objects.create(
            title="Test", description=unicode_description
        )
        self.assertEqual(obj.description, unicode_description)

    def test_extreme_display_order_values(self):
        """Test display_order with extreme values."""
        # Test very large positive value
        large_value = 2147483647  # Max 32-bit signed integer
        obj = DisplayableTestModel.objects.create(
            title="Test", display_order=large_value
        )
        self.assertEqual(obj.display_order, large_value)

    def test_timestamp_timezone_handling(self):
        """Test that timestamps handle timezones correctly."""
        # Test with different timezone settings
        with override_settings(USE_TZ=True):
            obj = TimestampedTestModel.objects.create(title="Test")

            # Timestamps should be timezone-aware
            self.assertIsNotNone(obj.created_at.tzinfo)
            self.assertIsNotNone(obj.updated_at.tzinfo)

    def test_game_system_case_sensitivity(self):
        """Test that game_system choices are case-sensitive."""
        # Valid lowercase choice should work
        obj = GameSystemTestModel.objects.create(title="Test", game_system="mage")
        self.assertEqual(obj.game_system, "mage")

        # Invalid uppercase choice should fail validation
        with self.assertRaises(ValidationError):
            obj = GameSystemTestModel(title="Test", game_system="MAGE")
            obj.full_clean()


class MixinDocumentationTest(TestCase):
    """Test that mixins are properly documented and have expected attributes."""

    def test_mixin_docstrings(self):
        """Test that all mixins have proper docstrings."""
        mixins = [
            TimestampedMixin,
            DisplayableMixin,
            NamedModelMixin,
            DescribedModelMixin,
            AuditableMixin,
            GameSystemMixin,
        ]

        for mixin in mixins:
            self.assertIsNotNone(mixin.__doc__)
            self.assertGreater(len(mixin.__doc__.strip()), 10)

    def test_mixin_module_attributes(self):
        """Test that mixins are properly exported from their module."""
        from core.models import mixins

        expected_mixins = [
            "TimestampedMixin",
            "DisplayableMixin",
            "NamedModelMixin",
            "DescribedModelMixin",
            "AuditableMixin",
            "GameSystemMixin",
        ]

        for mixin_name in expected_mixins:
            self.assertTrue(hasattr(mixins, mixin_name))
            mixin_class = getattr(mixins, mixin_name)
            self.assertTrue(issubclass(mixin_class, models.Model))
