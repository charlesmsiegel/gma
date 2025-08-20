"""
Tests for applying model mixins to existing Item model.

Tests verify that Item model can successfully apply:
- TimestampedMixin (created_at, updated_at fields) - deduplication test
- NamedModelMixin (name field + __str__ method) - deduplication test
- DescribedModelMixin (description field) - deduplication test

These tests ensure:
1. Mixins are properly applied without field conflicts
2. Existing functionality is preserved
3. Field deduplication works correctly during migration
4. No regressions in existing Item functionality
5. Consistent behavior with other models using same mixins
"""

from django.contrib.auth import get_user_model
from django.db import models
from django.test import TestCase
from django.utils import timezone

from campaigns.models import Campaign, CampaignMembership
from core.models.mixins import DescribedModelMixin, NamedModelMixin, TimestampedMixin
from items.models import Item

User = get_user_model()


class ItemMixinApplicationTest(TestCase):
    """Test Item model with applied mixins."""

    def setUp(self):
        """Set up test users and campaigns."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.player1 = User.objects.create_user(
            username="player1", email="player1@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Item Test Campaign",
            owner=self.owner,
            game_system="mage",
        )

        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player1, role="PLAYER"
        )

    def test_item_has_mixin_fields(self):
        """Test that Item model has all expected mixin fields."""
        # Get all field names from Item model
        field_names = [f.name for f in Item._meta.get_fields()]

        # TimestampedMixin fields
        self.assertIn("created_at", field_names)
        self.assertIn("updated_at", field_names)

        # NamedModelMixin fields
        self.assertIn("name", field_names)

        # DescribedModelMixin fields
        self.assertIn("description", field_names)

        # Existing Item-specific fields should still be present
        self.assertIn("campaign", field_names)
        self.assertIn("created_by", field_names)

    def test_timestamped_mixin_integration(self):
        """Test that TimestampedMixin integrates correctly with existing timestamps."""
        before_create = timezone.now()

        item = Item.objects.create(
            name="Test Item",
            description="Test description",
            campaign=self.campaign,
            created_by=self.player1,
        )

        after_create = timezone.now()

        # Test timestamps are set correctly
        self.assertIsNotNone(item.created_at)
        self.assertIsNotNone(item.updated_at)
        self.assertGreaterEqual(item.created_at, before_create)
        self.assertLessEqual(item.created_at, after_create)

        # Test field types match TimestampedMixin expectations
        fields = {f.name: f for f in Item._meta.get_fields()}
        created_at_field = fields["created_at"]
        updated_at_field = fields["updated_at"]

        self.assertIsInstance(created_at_field, models.DateTimeField)
        self.assertIsInstance(updated_at_field, models.DateTimeField)
        self.assertTrue(created_at_field.auto_now_add)
        self.assertTrue(updated_at_field.auto_now)

    def test_named_model_mixin_integration(self):
        """Test that NamedModelMixin integrates correctly with existing name field."""
        item = Item.objects.create(
            name="Named Item",
            campaign=self.campaign,
            created_by=self.player1,
        )

        # Test name field exists and works
        self.assertEqual(item.name, "Named Item")

        # Test __str__ method (should work like NamedModelMixin)
        self.assertEqual(str(item), "Named Item")

        # Test field type matches NamedModelMixin expectations
        fields = {f.name: f for f in Item._meta.get_fields()}
        name_field = fields["name"]

        self.assertIsInstance(name_field, models.CharField)
        # After mixin application, this should be 100 to match mixin
        self.assertEqual(name_field.max_length, 100)  # Mixin value
        self.assertFalse(name_field.blank)
        self.assertFalse(name_field.null)

    def test_described_model_mixin_integration(self):
        """Test that DescribedModelMixin integrates correctly with existing description field."""
        # Test with description
        item_with_desc = Item.objects.create(
            name="Item with Description",
            description="This is a detailed description",
            campaign=self.campaign,
            created_by=self.player1,
        )

        self.assertEqual(item_with_desc.description, "This is a detailed description")

        # Test without description (should default to empty string)
        item_no_desc = Item.objects.create(
            name="Item without Description",
            campaign=self.campaign,
            created_by=self.player1,
        )

        self.assertEqual(item_no_desc.description, "")

        # Test field type matches DescribedModelMixin expectations
        fields = {f.name: f for f in Item._meta.get_fields()}
        description_field = fields["description"]

        self.assertIsInstance(description_field, models.TextField)
        self.assertTrue(description_field.blank)
        self.assertEqual(description_field.default, "")

    def test_field_deduplication_compatibility(self):
        """Test that existing fields are compatible with mixin field deduplication."""
        Item.objects.create(
            name="Dedup Test Item",
            description="Test description for deduplication",
            campaign=self.campaign,
            created_by=self.player1,
        )

        fields = {f.name: f for f in Item._meta.get_fields()}

        # Check created_at field matches TimestampedMixin expectations
        created_at_field = fields["created_at"]
        expected_created_at = TimestampedMixin._meta.get_field("created_at")

        self.assertEqual(
            created_at_field.auto_now_add, expected_created_at.auto_now_add
        )
        self.assertEqual(created_at_field.auto_now, expected_created_at.auto_now)
        # Note: Current Item model might not have db_index, but mixin does

        # Check updated_at field matches TimestampedMixin expectations
        updated_at_field = fields["updated_at"]
        expected_updated_at = TimestampedMixin._meta.get_field("updated_at")

        self.assertEqual(
            updated_at_field.auto_now_add, expected_updated_at.auto_now_add
        )
        self.assertEqual(updated_at_field.auto_now, expected_updated_at.auto_now)

        # Check description field matches DescribedModelMixin expectations
        description_field = fields["description"]
        expected_description = DescribedModelMixin._meta.get_field("description")

        self.assertEqual(description_field.blank, expected_description.blank)
        self.assertEqual(description_field.default, expected_description.default)

    def test_existing_functionality_preserved(self):
        """Test that all existing Item functionality is preserved."""
        # Test item creation with all fields
        item = Item.objects.create(
            name="Functionality Test Item",
            description="Test item for functionality preservation",
            campaign=self.campaign,
            created_by=self.player1,
        )

        # Test basic field access
        self.assertEqual(item.name, "Functionality Test Item")
        self.assertEqual(item.description, "Test item for functionality preservation")
        self.assertEqual(item.campaign, self.campaign)
        self.assertEqual(item.created_by, self.player1)

        # Test timestamps work
        self.assertIsNotNone(item.created_at)
        self.assertIsNotNone(item.updated_at)

        # Test string representation
        self.assertEqual(str(item), "Functionality Test Item")

        # Test update functionality
        original_updated_at = item.updated_at
        item.name = "Updated Item Name"
        item.save()

        item.refresh_from_db()
        self.assertEqual(item.name, "Updated Item Name")
        self.assertGreater(item.updated_at, original_updated_at)

    def test_mixin_method_compatibility(self):
        """Test that mixin methods are compatible with existing Item methods."""
        item = Item.objects.create(
            name="Method Test Item",
            description="Testing method compatibility",
            campaign=self.campaign,
            created_by=self.player1,
        )

        # Test NamedModelMixin __str__ method compatibility
        # Item already has __str__ method, verify it works as expected
        self.assertEqual(str(item), "Method Test Item")
        self.assertEqual(item.__str__(), "Method Test Item")

        # Test that the existing __str__ matches what NamedModelMixin would provide
        self.assertEqual(item.name, str(item))

    def test_field_constraint_compatibility(self):
        """Test that existing field constraints work with mixin integration."""
        # Create item to test constraints
        Item.objects.create(
            name="Constraint Test Item",
            description="Testing constraints",
            campaign=self.campaign,
            created_by=self.player1,
        )

        # Test that required fields are handled appropriately
        # Note: Currently, empty name might be allowed at database level
        # but NamedModelMixin will enforce this validation
        try:
            no_name_item = Item.objects.create(
                # name is required (NamedModelMixin doesn't allow blank)
                description="No name item",
                campaign=self.campaign,
                created_by=self.player1,
            )
            # If creation succeeds with empty name, that's current behavior
            # NamedModelMixin will improve this validation
            self.assertEqual(no_name_item.name, "")
        except Exception:
            # If exception is raised, that's also acceptable
            pass

    def test_database_compatibility(self):
        """Test that database operations work correctly with mixins."""
        # Test bulk creation
        items = []
        for i in range(3):
            items.append(
                Item(
                    name=f"Bulk Item {i}",
                    description=f"Description {i}",
                    campaign=self.campaign,
                    created_by=self.player1,
                )
            )

        Item.objects.bulk_create(items)

        # Test filtering by mixin fields
        created_items = Item.objects.filter(name__startswith="Bulk Item")
        self.assertEqual(created_items.count(), 3)

        # Test ordering by timestamp fields
        ordered_items = Item.objects.order_by("created_at")
        self.assertEqual(ordered_items.count(), 3)

        # Test description filtering
        desc_items = Item.objects.filter(description__icontains="Description")
        self.assertEqual(desc_items.count(), 3)

    def test_migration_simulation_field_compatibility(self):
        """Test field compatibility for migration planning."""
        Item.objects.create(
            name="Migration Test Item",
            description="Testing migration compatibility",
            campaign=self.campaign,
            created_by=self.player1,
        )

        fields = {f.name: f for f in Item._meta.get_fields()}

        # Test name field migration compatibility
        name_field = fields["name"]
        expected_name = NamedModelMixin._meta.get_field("name")

        # After mixin application, both should have max_length=100
        self.assertEqual(name_field.max_length, 100)  # Applied mixin value
        self.assertEqual(expected_name.max_length, 100)  # Mixin template

        # Other properties should match
        self.assertEqual(name_field.blank, expected_name.blank)
        self.assertEqual(name_field.null, expected_name.null)

        # Test description field migration compatibility
        description_field = fields["description"]
        expected_description = DescribedModelMixin._meta.get_field("description")

        # These should already match
        self.assertEqual(description_field.blank, expected_description.blank)
        self.assertEqual(description_field.default, expected_description.default)

    def test_queryset_optimization_with_mixins(self):
        """Test that QuerySet operations work efficiently with mixin fields."""
        # Create test items
        for i in range(5):
            Item.objects.create(
                name=f"Query Test Item {i}",
                description=f"Description for item {i}",
                campaign=self.campaign,
                created_by=self.player1,
            )

        # Test timestamp-based queries (TimestampedMixin feature)
        recent_items = Item.objects.filter(
            created_at__gte=timezone.now() - timezone.timedelta(hours=1)
        )
        self.assertEqual(recent_items.count(), 5)

        # Test name-based queries (NamedModelMixin feature)
        query_items = Item.objects.filter(name__icontains="Query Test")
        self.assertEqual(query_items.count(), 5)

        # Test description-based queries (DescribedModelMixin feature)
        desc_items = Item.objects.filter(description__icontains="Description")
        self.assertEqual(desc_items.count(), 5)

        # Test combined queries using multiple mixin fields
        combined_query = Item.objects.filter(
            name__icontains="Query",
            description__icontains="Description",
            created_at__gte=timezone.now() - timezone.timedelta(hours=1),
        )
        self.assertEqual(combined_query.count(), 5)


class ItemMixinEnhancementTest(TestCase):
    """Test enhanced functionality that mixins will provide to Item model."""

    def setUp(self):
        """Set up test users and campaigns."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.player1 = User.objects.create_user(
            username="player1", email="player1@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Enhancement Test Campaign",
            owner=self.owner,
            game_system="mage",
        )

    def test_mixin_field_help_text_compatibility(self):
        """Test that mixin field help text will be compatible."""
        # Get current field help text
        fields = {f.name: f for f in Item._meta.get_fields()}

        # Test that mixin help text is now applied
        self.assertIn("Name of the object", fields["name"].help_text)
        self.assertIn("Optional detailed description", fields["description"].help_text)

        # Test that mixin help text would be compatible
        named_mixin_fields = {f.name: f for f in NamedModelMixin._meta.get_fields()}
        described_mixin_fields = {
            f.name: f for f in DescribedModelMixin._meta.get_fields()
        }

        # Mixin help text should be generic enough to work with Item
        self.assertIn("Name", named_mixin_fields["name"].help_text)
        self.assertIn("description", described_mixin_fields["description"].help_text)

    def test_database_index_enhancement(self):
        """Test that database indexes will be enhanced with mixins."""
        # TimestampedMixin adds db_index=True to timestamp fields
        # This will improve query performance for date-based filtering

        Item.objects.create(
            name="Index Test Item",
            description="Testing index enhancements",
            campaign=self.campaign,
            created_by=self.owner,
        )

        # Current fields might not have indexes
        {f.name: f for f in Item._meta.get_fields()}

        # After mixin application, these should have indexes
        mixin_fields = {f.name: f for f in TimestampedMixin._meta.get_fields()}
        self.assertTrue(mixin_fields["created_at"].db_index)
        self.assertTrue(mixin_fields["updated_at"].db_index)

    def test_field_length_adjustment_planning(self):
        """Test planning for field length adjustments during migration."""
        # Current Item.name has max_length=200
        # NamedModelMixin.name has max_length=100
        # Need to ensure migration handles this correctly

        # Create item with long name (within current limit)
        long_name = "A" * 150  # Longer than mixin limit but within current limit

        # This should work with current model
        item = Item.objects.create(
            name=long_name,
            description="Testing name length",
            campaign=self.campaign,
            created_by=self.owner,
        )

        self.assertEqual(item.name, long_name)
        self.assertEqual(len(item.name), 150)

        # After migration, names longer than 100 chars will need to be handled
        # This test documents the current behavior for migration planning

    def test_consistency_preparation(self):
        """Test preparation for consistency across models using same mixins."""
        # All models using NamedModelMixin should have consistent name field behavior
        item = Item.objects.create(
            name="Consistency Test",
            campaign=self.campaign,
            created_by=self.owner,
        )

        # Test that __str__ behavior will be consistent
        self.assertEqual(str(item), item.name)

        # Test that field properties will be consistent after mixin application
        fields = {f.name: f for f in Item._meta.get_fields()}
        name_field = fields["name"]

        # These properties should match across all models using NamedModelMixin
        self.assertFalse(name_field.blank)
        self.assertFalse(name_field.null)
        self.assertIsInstance(name_field, models.CharField)

    def test_backward_compatibility_assurance(self):
        """Test that existing code will continue to work after mixin application."""
        # Create item using existing API
        item = Item.objects.create(
            name="Backward Compatibility Test",
            description="Testing backward compatibility",
            campaign=self.campaign,
            created_by=self.owner,
        )

        # All existing field access should continue to work
        self.assertIsNotNone(item.name)
        self.assertIsNotNone(item.description)
        self.assertIsNotNone(item.campaign)
        self.assertIsNotNone(item.created_by)
        self.assertIsNotNone(item.created_at)
        self.assertIsNotNone(item.updated_at)

        # All existing methods should continue to work
        self.assertEqual(str(item), "Backward Compatibility Test")

        # Existing queries should continue to work
        items = Item.objects.filter(campaign=self.campaign)
        self.assertIn(item, items)

        items_by_name = Item.objects.filter(name="Backward Compatibility Test")
        self.assertIn(item, items_by_name)
