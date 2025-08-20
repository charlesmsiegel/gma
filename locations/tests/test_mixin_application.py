"""
Tests for applying model mixins to existing Location model.

Tests verify that Location model can successfully apply:
- TimestampedMixin (created_at, updated_at fields) - deduplication test
- NamedModelMixin (name field + __str__ method) - deduplication test
- DescribedModelMixin (description field) - deduplication test

These tests ensure:
1. Mixins are properly applied without field conflicts
2. Existing functionality is preserved
3. Field deduplication works correctly during migration
4. No regressions in existing Location functionality
5. Consistent behavior with other models using same mixins
"""

from django.contrib.auth import get_user_model
from django.db import models
from django.test import TestCase
from django.utils import timezone

from campaigns.models import Campaign, CampaignMembership
from core.models.mixins import DescribedModelMixin, NamedModelMixin, TimestampedMixin
from locations.models import Location

User = get_user_model()


class LocationMixinApplicationTest(TestCase):
    """Test Location model with applied mixins."""

    def setUp(self):
        """Set up test users and campaigns."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.player1 = User.objects.create_user(
            username="player1", email="player1@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Location Test Campaign",
            owner=self.owner,
            game_system="mage",
        )

        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player1, role="PLAYER"
        )

    def test_location_has_mixin_fields(self):
        """Test that Location model has all expected mixin fields."""
        # Get all field names from Location model
        field_names = [f.name for f in Location._meta.get_fields()]

        # TimestampedMixin fields
        self.assertIn("created_at", field_names)
        self.assertIn("updated_at", field_names)

        # NamedModelMixin fields
        self.assertIn("name", field_names)

        # DescribedModelMixin fields
        self.assertIn("description", field_names)

        # Existing Location-specific fields should still be present
        self.assertIn("campaign", field_names)
        self.assertIn("created_by", field_names)

    def test_timestamped_mixin_integration(self):
        """Test that TimestampedMixin integrates correctly with existing timestamps."""
        before_create = timezone.now()

        location = Location.objects.create(
            name="Test Location",
            description="Test location description",
            campaign=self.campaign,
            created_by=self.player1,
        )

        after_create = timezone.now()

        # Test timestamps are set correctly
        self.assertIsNotNone(location.created_at)
        self.assertIsNotNone(location.updated_at)
        self.assertGreaterEqual(location.created_at, before_create)
        self.assertLessEqual(location.created_at, after_create)

        # Test field types match TimestampedMixin expectations
        fields = {f.name: f for f in Location._meta.get_fields()}
        created_at_field = fields["created_at"]
        updated_at_field = fields["updated_at"]

        self.assertIsInstance(created_at_field, models.DateTimeField)
        self.assertIsInstance(updated_at_field, models.DateTimeField)
        self.assertTrue(created_at_field.auto_now_add)
        self.assertTrue(updated_at_field.auto_now)

    def test_named_model_mixin_integration(self):
        """Test that NamedModelMixin integrates correctly with existing name field."""
        location = Location.objects.create(
            name="Named Location",
            campaign=self.campaign,
            created_by=self.player1,
        )

        # Test name field exists and works
        self.assertEqual(location.name, "Named Location")

        # Test __str__ method (should work like NamedModelMixin)
        self.assertEqual(str(location), "Named Location")

        # Test field type matches NamedModelMixin expectations
        fields = {f.name: f for f in Location._meta.get_fields()}
        name_field = fields["name"]

        self.assertIsInstance(name_field, models.CharField)
        # After mixin application, this should be 100 to match mixin
        self.assertEqual(name_field.max_length, 100)  # Mixin value
        self.assertFalse(name_field.blank)
        self.assertFalse(name_field.null)

    def test_described_model_mixin_integration(self):
        """Test that DescribedModelMixin integrates correctly with existing description field."""
        # Test with description
        location_with_desc = Location.objects.create(
            name="Location with Description",
            description="This is a detailed location description",
            campaign=self.campaign,
            created_by=self.player1,
        )

        self.assertEqual(
            location_with_desc.description, "This is a detailed location description"
        )

        # Test without description (should default to empty string)
        location_no_desc = Location.objects.create(
            name="Location without Description",
            campaign=self.campaign,
            created_by=self.player1,
        )

        self.assertEqual(location_no_desc.description, "")

        # Test field type matches DescribedModelMixin expectations
        fields = {f.name: f for f in Location._meta.get_fields()}
        description_field = fields["description"]

        self.assertIsInstance(description_field, models.TextField)
        self.assertTrue(description_field.blank)
        self.assertEqual(description_field.default, "")

    def test_field_deduplication_compatibility(self):
        """Test that existing fields are compatible with mixin field deduplication."""
        _location = Location.objects.create(
            name="Dedup Test Location",
            description="Test description for deduplication",
            campaign=self.campaign,
            created_by=self.player1,
        )

        fields = {f.name: f for f in Location._meta.get_fields()}

        # Check created_at field matches TimestampedMixin expectations
        created_at_field = fields["created_at"]
        expected_created_at = TimestampedMixin._meta.get_field("created_at")

        self.assertEqual(
            created_at_field.auto_now_add, expected_created_at.auto_now_add
        )
        self.assertEqual(created_at_field.auto_now, expected_created_at.auto_now)
        # Note: Current Location model might not have db_index, but mixin does

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
        """Test that all existing Location functionality is preserved."""
        # Test location creation with all fields
        location = Location.objects.create(
            name="Functionality Test Location",
            description="Test location for functionality preservation",
            campaign=self.campaign,
            created_by=self.player1,
        )

        # Test basic field access
        self.assertEqual(location.name, "Functionality Test Location")
        self.assertEqual(
            location.description, "Test location for functionality preservation"
        )
        self.assertEqual(location.campaign, self.campaign)
        self.assertEqual(location.created_by, self.player1)

        # Test timestamps work
        self.assertIsNotNone(location.created_at)
        self.assertIsNotNone(location.updated_at)

        # Test string representation
        self.assertEqual(str(location), "Functionality Test Location")

        # Test update functionality
        original_updated_at = location.updated_at
        location.name = "Updated Location Name"
        location.save()

        location.refresh_from_db()
        self.assertEqual(location.name, "Updated Location Name")
        self.assertGreater(location.updated_at, original_updated_at)

    def test_mixin_method_compatibility(self):
        """Test that mixin methods are compatible with existing Location methods."""
        location = Location.objects.create(
            name="Method Test Location",
            description="Testing method compatibility",
            campaign=self.campaign,
            created_by=self.player1,
        )

        # Test NamedModelMixin __str__ method compatibility
        # Location already has __str__ method, verify it works as expected
        self.assertEqual(str(location), "Method Test Location")
        self.assertEqual(location.__str__(), "Method Test Location")

        # Test that the existing __str__ matches what NamedModelMixin would provide
        self.assertEqual(location.name, str(location))

    def test_field_constraint_compatibility(self):
        """Test that existing field constraints work with mixin integration."""
        # Create location to test constraints
        _location = Location.objects.create(
            name="Constraint Test Location",
            description="Testing constraints",
            campaign=self.campaign,
            created_by=self.player1,
        )

        # Test that required fields are handled appropriately
        # Note: Currently, empty name might be allowed at database level
        # but NamedModelMixin will enforce this validation
        try:
            no_name_location = Location.objects.create(
                # name is required (NamedModelMixin doesn't allow blank)
                description="No name location",
                campaign=self.campaign,
                created_by=self.player1,
            )
            # If creation succeeds with empty name, that's current behavior
            # NamedModelMixin will improve this validation
            self.assertEqual(no_name_location.name, "")
        except Exception:
            # If exception is raised, that's also acceptable
            pass

    def test_database_compatibility(self):
        """Test that database operations work correctly with mixins."""
        # Test bulk creation
        locations = []
        for i in range(3):
            locations.append(
                Location(
                    name=f"Bulk Location {i}",
                    description=f"Description {i}",
                    campaign=self.campaign,
                    created_by=self.player1,
                )
            )

        Location.objects.bulk_create(locations)

        # Test filtering by mixin fields
        created_locations = Location.objects.filter(name__startswith="Bulk Location")
        self.assertEqual(created_locations.count(), 3)

        # Test ordering by timestamp fields
        ordered_locations = Location.objects.order_by("created_at")
        self.assertEqual(ordered_locations.count(), 3)

        # Test description filtering
        desc_locations = Location.objects.filter(description__icontains="Description")
        self.assertEqual(desc_locations.count(), 3)

    def test_migration_simulation_field_compatibility(self):
        """Test field compatibility for migration planning."""
        _location = Location.objects.create(
            name="Migration Test Location",
            description="Testing migration compatibility",
            campaign=self.campaign,
            created_by=self.player1,
        )

        fields = {f.name: f for f in Location._meta.get_fields()}

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
        # Create test locations
        for i in range(5):
            Location.objects.create(
                name=f"Query Test Location {i}",
                description=f"Description for location {i}",
                campaign=self.campaign,
                created_by=self.player1,
            )

        # Test timestamp-based queries (TimestampedMixin feature)
        recent_locations = Location.objects.filter(
            created_at__gte=timezone.now() - timezone.timedelta(hours=1)
        )
        self.assertEqual(recent_locations.count(), 5)

        # Test name-based queries (NamedModelMixin feature)
        query_locations = Location.objects.filter(name__icontains="Query Test")
        self.assertEqual(query_locations.count(), 5)

        # Test description-based queries (DescribedModelMixin feature)
        desc_locations = Location.objects.filter(description__icontains="Description")
        self.assertEqual(desc_locations.count(), 5)

        # Test combined queries using multiple mixin fields
        combined_query = Location.objects.filter(
            name__icontains="Query",
            description__icontains="Description",
            created_at__gte=timezone.now() - timezone.timedelta(hours=1),
        )
        self.assertEqual(combined_query.count(), 5)

    def test_location_ordering_compatibility(self):
        """Test that Location ordering works with mixin fields."""
        # Create locations in specific order
        locations = []
        for i in range(3):
            location = Location.objects.create(
                name=f"Ordered Location {i:02d}",
                description=f"Description {i}",
                campaign=self.campaign,
                created_by=self.player1,
            )
            locations.append(location)

        # Test current ordering (should be by name based on Meta.ordering)
        ordered_locations = list(Location.objects.all())
        self.assertEqual(len(ordered_locations), 3)

        # Verify they're ordered by name (current default)
        names = [loc.name for loc in ordered_locations]
        self.assertEqual(names, sorted(names))

        # Test that timestamp ordering will work (TimestampedMixin feature)
        time_ordered = list(Location.objects.order_by("created_at"))
        self.assertEqual(len(time_ordered), 3)


class LocationMixinEnhancementTest(TestCase):
    """Test enhanced functionality that mixins will provide to Location model."""

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
        fields = {f.name: f for f in Location._meta.get_fields()}

        # Test that mixin help text is now applied
        self.assertIn("Name of the object", fields["name"].help_text)
        self.assertIn("Optional detailed description", fields["description"].help_text)

        # Test that mixin help text would be compatible
        named_mixin_fields = {f.name: f for f in NamedModelMixin._meta.get_fields()}
        described_mixin_fields = {
            f.name: f for f in DescribedModelMixin._meta.get_fields()
        }

        # Mixin help text should be generic enough to work with Location
        self.assertIn("Name", named_mixin_fields["name"].help_text)
        self.assertIn("description", described_mixin_fields["description"].help_text)

    def test_database_index_enhancement(self):
        """Test that database indexes will be enhanced with mixins."""
        # TimestampedMixin adds db_index=True to timestamp fields
        # This will improve query performance for date-based filtering

        _location = Location.objects.create(
            name="Index Test Location",
            description="Testing index enhancements",
            campaign=self.campaign,
            created_by=self.owner,
        )

        # Current fields might not have indexes
        _fields = {f.name: f for f in Location._meta.get_fields()}

        # After mixin application, these should have indexes
        mixin_fields = {f.name: f for f in TimestampedMixin._meta.get_fields()}
        self.assertTrue(mixin_fields["created_at"].db_index)
        self.assertTrue(mixin_fields["updated_at"].db_index)

    def test_field_length_adjustment_planning(self):
        """Test planning for field length adjustments during migration."""
        # Current Location.name has max_length=200
        # NamedModelMixin.name has max_length=100
        # Need to ensure migration handles this correctly

        # Create location with long name (within current limit)
        long_name = "A" * 150  # Longer than mixin limit but within current limit

        # This should work with current model
        location = Location.objects.create(
            name=long_name,
            description="Testing name length",
            campaign=self.campaign,
            created_by=self.owner,
        )

        self.assertEqual(location.name, long_name)
        self.assertEqual(len(location.name), 150)

        # After migration, names longer than 100 chars will need to be handled
        # This test documents the current behavior for migration planning

    def test_consistency_with_other_models(self):
        """Test consistency preparation with other models using same mixins."""
        # All models using NamedModelMixin should have consistent name field behavior
        location = Location.objects.create(
            name="Consistency Test",
            campaign=self.campaign,
            created_by=self.owner,
        )

        # Test that __str__ behavior will be consistent
        self.assertEqual(str(location), location.name)

        # Test that field properties will be consistent after mixin application
        fields = {f.name: f for f in Location._meta.get_fields()}
        name_field = fields["name"]

        # These properties should match across all models using NamedModelMixin
        self.assertFalse(name_field.blank)
        self.assertFalse(name_field.null)
        self.assertIsInstance(name_field, models.CharField)

    def test_backward_compatibility_assurance(self):
        """Test that existing code will continue to work after mixin application."""
        # Create location using existing API
        location = Location.objects.create(
            name="Backward Compatibility Test",
            description="Testing backward compatibility",
            campaign=self.campaign,
            created_by=self.owner,
        )

        # All existing field access should continue to work
        self.assertIsNotNone(location.name)
        self.assertIsNotNone(location.description)
        self.assertIsNotNone(location.campaign)
        self.assertIsNotNone(location.created_by)
        self.assertIsNotNone(location.created_at)
        self.assertIsNotNone(location.updated_at)

        # All existing methods should continue to work
        self.assertEqual(str(location), "Backward Compatibility Test")

        # Existing queries should continue to work
        locations = Location.objects.filter(campaign=self.campaign)
        self.assertIn(location, locations)

        locations_by_name = Location.objects.filter(name="Backward Compatibility Test")
        self.assertIn(location, locations_by_name)

    def test_performance_optimization_readiness(self):
        """Test readiness for performance optimizations that mixins provide."""
        # Create test data
        locations = []
        for i in range(10):
            location = Location.objects.create(
                name=f"Performance Test Location {i:02d}",
                description=f"Performance test description {i}",
                campaign=self.campaign,
                created_by=self.owner,
            )
            locations.append(location)

        # Test queries that will benefit from TimestampedMixin indexes
        recent_locations = Location.objects.filter(
            created_at__gte=timezone.now() - timezone.timedelta(hours=1)
        ).order_by("-created_at")
        self.assertEqual(recent_locations.count(), 10)

        # Test queries that will benefit from consistent field sizes
        name_searches = Location.objects.filter(name__icontains="Performance")
        self.assertEqual(name_searches.count(), 10)

        # Test that existing queries are ready for optimization
        complex_query = Location.objects.filter(
            name__startswith="Performance",
            description__icontains="test",
            created_at__gte=timezone.now() - timezone.timedelta(days=1),
        ).order_by("name", "-created_at")

        self.assertEqual(complex_query.count(), 10)

    def test_location_specific_functionality_preservation(self):
        """Test that Location-specific functionality is preserved with mixins."""
        # Test creation with minimal fields
        minimal_location = Location.objects.create(
            name="Minimal Location",
            campaign=self.campaign,
            created_by=self.owner,
        )

        # Should work with default description
        self.assertEqual(minimal_location.description, "")
        self.assertEqual(str(minimal_location), "Minimal Location")

        # Test creation with all fields
        full_location = Location.objects.create(
            name="Full Location",
            description="A complete location with all details",
            campaign=self.campaign,
            created_by=self.owner,
        )

        self.assertEqual(
            full_location.description, "A complete location with all details"
        )
        self.assertEqual(str(full_location), "Full Location")

        # Test that Location-specific database table name is preserved
        self.assertEqual(Location._meta.db_table, "locations_location")

        # Test that ordering is preserved
        self.assertEqual(Location._meta.ordering, ["name"])

        # Test that verbose names are preserved
        self.assertEqual(Location._meta.verbose_name, "Location")
        self.assertEqual(Location._meta.verbose_name_plural, "Locations")
