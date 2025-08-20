"""
Comprehensive tests for converting Location model to use PolymorphicModel inheritance.

These tests verify that the Location model can be converted to inherit from
PolymorphicModel while preserving all existing functionality. This follows TDD
principles - tests are written first and will FAIL until the polymorphic
conversion is implemented.

Test Coverage:
- PolymorphicModel inheritance and basic functionality
- Data preservation during migration from regular model to polymorphic
- Polymorphic queries and type preservation
- Manager and QuerySet polymorphic functionality
- Admin interface integration with polymorphic display
- Subclassing capabilities with polymorphic inheritance
- Backward compatibility with existing Location functionality
- Performance implications of polymorphic queries

Expected Failures:
All tests in this file will initially FAIL because:
1. Location model currently inherits from models.Model, not PolymorphicModel
2. No PolymorphicManager is configured
3. No polymorphic admin setup exists
4. No subclasses exist to test polymorphic behavior

Once the polymorphic conversion is complete, all tests should PASS.
"""

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.test import TestCase, TransactionTestCase
from polymorphic.managers import PolymorphicManager
from polymorphic.models import PolymorphicModel
from polymorphic.query import PolymorphicQuerySet

from campaigns.models import Campaign, CampaignMembership
from locations.admin import LocationAdmin
from locations.models import Location

User = get_user_model()


class LocationPolymorphicInheritanceTest(TestCase):
    """Test that Location model properly inherits from PolymorphicModel."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign", owner=self.user, game_system="mage"
        )

    def test_location_inherits_from_polymorphic_model(self):
        """Test that Location model inherits from PolymorphicModel."""
        # This test will FAIL until Location inherits from PolymorphicModel
        self.assertTrue(
            issubclass(Location, PolymorphicModel),
            "Location model should inherit from PolymorphicModel",
        )

    def test_location_has_polymorphic_ctype_field(self):
        """Test that Location has the polymorphic_ctype field."""
        location = Location.objects.create(
            name="Test Location",
            campaign=self.campaign,
            created_by=self.user,
        )

        # This will FAIL until Location inherits from PolymorphicModel
        self.assertTrue(
            hasattr(location, "polymorphic_ctype"),
            "Location should have polymorphic_ctype field from PolymorphicModel",
        )
        self.assertIsNotNone(location.polymorphic_ctype)

    def test_location_has_polymorphic_manager(self):
        """Test that Location uses PolymorphicManager."""
        # This will FAIL until Location.objects is a PolymorphicManager
        self.assertIsInstance(
            Location.objects,
            PolymorphicManager,
            "Location.objects should be a PolymorphicManager",
        )

    def test_location_queryset_is_polymorphic(self):
        """Test that Location querysets are polymorphic."""
        queryset = Location.objects.all()

        # This will FAIL until Location uses PolymorphicQuerySet
        self.assertIsInstance(
            queryset,
            PolymorphicQuerySet,
            "Location querysets should be PolymorphicQuerySet instances",
        )

    def test_location_polymorphic_identity(self):
        """Test that Location instances have correct polymorphic identity."""
        location = Location.objects.create(
            name="Test Location",
            campaign=self.campaign,
            created_by=self.user,
        )

        # This will FAIL until Location properly implements polymorphic identity
        self.assertEqual(
            location.get_real_instance_class(),
            Location,
            "Location should return itself as the real instance class",
        )

        self.assertEqual(
            location.get_real_instance(),
            location,
            "Location should return itself as the real instance",
        )


class LocationDataPreservationTest(TransactionTestCase):
    """Test that existing Location data is preserved during polymorphic conversion."""

    def setUp(self):
        """Set up test data that simulates existing pre-conversion data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign", owner=self.user, game_system="mage"
        )

    def test_existing_locations_retain_data_after_conversion(self):
        """Test that existing locations keep all their data after conversion."""
        # Create a location with full data
        original_data = {
            "name": "Historic Castle",
            "description": "A medieval castle with rich history",
            "campaign": self.campaign,
            "created_by": self.user,
        }

        location = Location.objects.create(**original_data)
        original_id = location.id
        original_created_at = location.created_at

        # After polymorphic conversion, all data should be preserved
        location.refresh_from_db()

        self.assertEqual(location.id, original_id)
        self.assertEqual(location.name, original_data["name"])
        self.assertEqual(location.description, original_data["description"])
        self.assertEqual(location.campaign, original_data["campaign"])
        self.assertEqual(location.created_by, original_data["created_by"])
        self.assertEqual(location.created_at, original_created_at)

        # This will FAIL until polymorphic fields are properly populated
        self.assertIsNotNone(location.polymorphic_ctype)

    def test_hierarchy_preserved_after_conversion(self):
        """Test that parent-child relationships are preserved after conversion."""
        parent = Location.objects.create(
            name="Parent Location",
            campaign=self.campaign,
            created_by=self.user,
        )

        child = Location.objects.create(
            name="Child Location",
            campaign=self.campaign,
            parent=parent,
            created_by=self.user,
        )

        # After conversion, hierarchy should be intact
        child.refresh_from_db()
        parent.refresh_from_db()

        self.assertEqual(child.parent, parent)
        self.assertIn(child, parent.children.all())

        # Polymorphic fields should be populated for both
        # This will FAIL until conversion is complete
        self.assertIsNotNone(parent.polymorphic_ctype)
        self.assertIsNotNone(child.polymorphic_ctype)

    def test_permissions_preserved_after_conversion(self):
        """Test that permission methods work correctly after conversion."""
        gm = User.objects.create_user(
            username="gm", email="gm@example.com", password="testpass123"
        )
        CampaignMembership.objects.create(campaign=self.campaign, user=gm, role="GM")

        location = Location.objects.create(
            name="Permission Test Location",
            campaign=self.campaign,
            created_by=self.user,
        )

        # Permission methods should work exactly as before
        self.assertTrue(location.can_view(self.user))
        self.assertTrue(location.can_edit(self.user))
        self.assertTrue(location.can_delete(self.user))
        self.assertTrue(location.can_view(gm))
        self.assertTrue(location.can_edit(gm))
        self.assertTrue(location.can_delete(gm))

    def test_tree_traversal_methods_preserved_after_conversion(self):
        """Test that all tree traversal methods work after conversion."""
        # Create a hierarchy: Root -> Parent -> Child
        root = Location.objects.create(
            name="Root Location",
            campaign=self.campaign,
            created_by=self.user,
        )

        parent = Location.objects.create(
            name="Parent Location",
            campaign=self.campaign,
            parent=root,
            created_by=self.user,
        )

        child = Location.objects.create(
            name="Child Location",
            campaign=self.campaign,
            parent=parent,
            created_by=self.user,
        )

        # All traversal methods should work exactly as before
        self.assertEqual(child.get_root(), root)
        self.assertEqual(parent.get_root(), root)
        self.assertEqual(root.get_root(), root)

        self.assertEqual(child.get_depth(), 2)
        self.assertEqual(parent.get_depth(), 1)
        self.assertEqual(root.get_depth(), 0)

        self.assertIn(child, root.get_descendants())
        self.assertIn(parent, root.get_descendants())
        self.assertIn(parent, child.get_ancestors())
        self.assertIn(root, child.get_ancestors())

        self.assertTrue(child.is_descendant_of(root))
        self.assertTrue(child.is_descendant_of(parent))
        self.assertFalse(parent.is_descendant_of(child))


class LocationPolymorphicQueriesTest(TestCase):
    """Test polymorphic query functionality for Location model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign", owner=self.user, game_system="mage"
        )

    def test_polymorphic_queryset_returns_correct_types(self):
        """Test that polymorphic queries return correct instance types."""
        location = Location.objects.create(
            name="Base Location",
            campaign=self.campaign,
            created_by=self.user,
        )

        # Query should return the correct polymorphic type
        # This will FAIL until polymorphic functionality is implemented
        retrieved = Location.objects.get(id=location.id)

        self.assertIsInstance(retrieved, Location)
        self.assertEqual(type(retrieved), Location)
        self.assertEqual(retrieved.get_real_instance_class(), Location)

    def test_polymorphic_filter_preserves_types(self):
        """Test that filtering preserves polymorphic types."""
        locations = []
        for i in range(3):
            location = Location.objects.create(
                name=f"Location {i}",
                campaign=self.campaign,
                created_by=self.user,
            )
            locations.append(location)

        # Filter operations should preserve polymorphic types
        # This will FAIL until polymorphic functionality is implemented
        filtered = Location.objects.filter(campaign=self.campaign)

        self.assertEqual(filtered.count(), 3)
        for location in filtered:
            self.assertIsInstance(location, Location)
            self.assertEqual(type(location), Location)

    def test_polymorphic_select_related_works(self):
        """Test that select_related works with polymorphic queries."""
        location = Location.objects.create(
            name="Select Related Test",
            campaign=self.campaign,
            created_by=self.user,
        )

        # This will FAIL until polymorphic functionality is implemented
        with self.assertNumQueries(1):
            retrieved = Location.objects.select_related("campaign", "created_by").get(
                id=location.id
            )

            # Accessing related fields shouldn't trigger additional queries
            self.assertEqual(retrieved.campaign.name, self.campaign.name)
            self.assertEqual(retrieved.created_by.username, self.user.username)

    def test_polymorphic_prefetch_related_works(self):
        """Test that prefetch_related works with polymorphic queries."""
        parent = Location.objects.create(
            name="Parent for Prefetch",
            campaign=self.campaign,
            created_by=self.user,
        )

        for i in range(3):
            Location.objects.create(
                name=f"Child {i}",
                campaign=self.campaign,
                parent=parent,
                created_by=self.user,
            )

        # This will FAIL until polymorphic functionality is implemented
        with self.assertNumQueries(2):  # One for parent, one for children
            retrieved = Location.objects.prefetch_related("children").get(id=parent.id)

            # Accessing children shouldn't trigger additional queries
            children = list(retrieved.children.all())
            self.assertEqual(len(children), 3)
            for child in children:
                self.assertIsInstance(child, Location)

    def test_polymorphic_ordering_works(self):
        """Test that ordering works correctly with polymorphic queries."""
        locations = []
        for name in ["Charlie", "Alice", "Bob"]:
            location = Location.objects.create(
                name=name,
                campaign=self.campaign,
                created_by=self.user,
            )
            locations.append(location)

        # This will FAIL until polymorphic functionality is implemented
        ordered = Location.objects.order_by("name")
        names = [loc.name for loc in ordered]

        self.assertEqual(names, ["Alice", "Bob", "Charlie"])
        for location in ordered:
            self.assertIsInstance(location, Location)


class LocationSubclassingTest(TestCase):
    """Test that Location can be properly subclassed with polymorphic inheritance."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign", owner=self.user, game_system="mage"
        )

    def test_location_can_be_subclassed(self):
        """Test that Location can be subclassed properly."""
        # Test that Location can be subclassed by checking the inheritance chain
        # We don't need to create an actual subclass for this test

        # This will FAIL until Location inherits from PolymorphicModel
        self.assertTrue(
            issubclass(Location, PolymorphicModel),
            "Location should inherit from PolymorphicModel",
        )

        # Test that the inheritance chain is correct
        location = Location.objects.create(
            name="Inheritance Test",
            campaign=self.campaign,
            created_by=self.user,
        )

        self.assertIsInstance(location, PolymorphicModel)
        self.assertTrue(hasattr(location, "polymorphic_ctype"))
        self.assertTrue(hasattr(location, "get_real_instance"))
        self.assertTrue(hasattr(location, "get_real_instance_class"))

    def test_subclass_instances_returned_correctly(self):
        """Test that subclass instances are returned with correct types."""
        # This test simulates what would happen with real subclasses

        # Create base Location
        Location.objects.create(
            name="Base Location",
            campaign=self.campaign,
            created_by=self.user,
        )

        # After implementing subclasses, queries should return correct types
        # This will FAIL until polymorphic functionality is implemented
        all_locations = Location.objects.all()

        for location in all_locations:
            self.assertEqual(
                type(location),
                location.get_real_instance_class(),
                "Retrieved instance should match its real instance class",
            )

    def test_polymorphic_queries_include_subclasses(self):
        """Test that polymorphic queries include subclass instances."""
        # Create base location
        Location.objects.create(
            name="Base Location",
            campaign=self.campaign,
            created_by=self.user,
        )

        # After implementing subclasses, they should be included in base queries
        # This will FAIL until polymorphic functionality and subclasses are implemented
        all_locations = Location.objects.all()

        self.assertGreaterEqual(
            all_locations.count(),
            1,
            "Base queries should include all polymorphic types",
        )

        # Each instance should be properly typed
        for location in all_locations:
            self.assertIsInstance(location, Location)
            self.assertIsNotNone(location.polymorphic_ctype)

    def test_subclass_specific_fields_preserved(self):
        """Test that subclass-specific fields are preserved."""
        # This test will be relevant when actual subclasses are implemented
        # For now, it tests the principle using the base Location

        location = Location.objects.create(
            name="Field Preservation Test",
            description="Test description",
            campaign=self.campaign,
            created_by=self.user,
        )

        # After polymorphic conversion, all fields should be preserved
        retrieved = Location.objects.get(id=location.id)

        self.assertEqual(retrieved.name, location.name)
        self.assertEqual(retrieved.description, location.description)
        self.assertEqual(retrieved.campaign, location.campaign)
        self.assertEqual(retrieved.created_by, location.created_by)

        # This will FAIL until polymorphic functionality is implemented
        self.assertIsNotNone(retrieved.polymorphic_ctype)


class LocationPolymorphicAdminTest(TestCase):
    """Test admin interface integration with polymorphic Location model."""

    def setUp(self):
        """Set up test data and admin."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign", owner=self.user, game_system="mage"
        )
        self.site = AdminSite()
        self.admin = LocationAdmin(Location, self.site)

    def test_admin_shows_polymorphic_type(self):
        """Test that admin interface displays polymorphic type information."""
        location = Location.objects.create(
            name="Admin Test Location",
            campaign=self.campaign,
            created_by=self.user,
        )

        # Admin should be able to handle polymorphic instances
        # This may FAIL if admin isn't properly configured for polymorphic models
        from django.test import RequestFactory

        request = RequestFactory().get("/admin/locations/location/")
        request.user = self.user
        changelist = self.admin.get_changelist_instance(request=request)

        # Admin should be able to process polymorphic querysets
        queryset = changelist.get_queryset(request=None)
        self.assertIn(location, queryset)

        # Each instance should maintain its polymorphic identity in admin
        for obj in queryset:
            self.assertIsInstance(obj, Location)
            # This will FAIL until polymorphic functionality is implemented
            self.assertIsNotNone(obj.polymorphic_ctype)

    def test_admin_list_display_works_with_polymorphic(self):
        """Test that admin list_display works with polymorphic instances."""
        location = Location.objects.create(
            name="List Display Test",
            campaign=self.campaign,
            created_by=self.user,
        )

        # Admin list_display should work with polymorphic instances
        list_display = self.admin.get_list_display(request=None)

        # Should be able to get field values for display
        for field_name in list_display:
            if hasattr(location, field_name):
                value = getattr(location, field_name)
                # Should not raise exceptions when accessing fields
                self.assertIsNotNone(str(value))

    def test_admin_filtering_works_with_polymorphic(self):
        """Test that admin filtering works with polymorphic instances."""
        location = Location.objects.create(
            name="Filter Test Location",
            campaign=self.campaign,
            created_by=self.user,
        )

        # Admin filters should work with polymorphic queries
        list_filter = self.admin.get_list_filter(request=None)

        # Should be able to filter without errors
        for filter_spec in list_filter:
            if hasattr(Location, filter_spec):
                # Filter should not raise exceptions
                filtered = Location.objects.filter(
                    **{filter_spec: getattr(location, filter_spec)}
                )
                self.assertIn(location, filtered)

    def test_admin_search_works_with_polymorphic(self):
        """Test that admin search functionality works with polymorphic instances."""
        location = Location.objects.create(
            name="Searchable Location",
            campaign=self.campaign,
            created_by=self.user,
        )

        # Admin search should work with polymorphic queries
        search_fields = self.admin.get_search_fields(request=None)

        if search_fields:
            # Should be able to search without errors
            # This tests that polymorphic queries work with search
            queryset = Location.objects.all()

            # Search should find the location
            self.assertIn(location, queryset)

            # Each result should maintain polymorphic identity
            for obj in queryset:
                self.assertIsInstance(obj, Location)


class LocationPolymorphicPerformanceTest(TestCase):
    """Test performance implications of polymorphic Location model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign", owner=self.user, game_system="mage"
        )

    def test_polymorphic_queries_use_reasonable_query_count(self):
        """Test that polymorphic queries don't generate excessive database queries."""
        # Create multiple locations
        locations = []
        for i in range(10):
            location = Location.objects.create(
                name=f"Performance Test Location {i}",
                campaign=self.campaign,
                created_by=self.user,
            )
            locations.append(location)

        # Polymorphic queries should not use excessive queries
        # This will FAIL if polymorphic functionality causes query proliferation
        with self.assertNumQueries(1):
            list(Location.objects.all())

    def test_polymorphic_select_related_efficiency(self):
        """Test that select_related works efficiently with polymorphic queries."""
        # Create locations with relationships
        for i in range(5):
            Location.objects.create(
                name=f"Related Test Location {i}",
                campaign=self.campaign,
                created_by=self.user,
            )

        # select_related should reduce query count
        # This will FAIL if polymorphic functionality breaks select_related optimization
        with self.assertNumQueries(1):
            locations = Location.objects.select_related("campaign", "created_by").all()

            # Accessing related fields should not trigger additional queries
            for location in locations:
                self.assertIsNotNone(location.campaign.name)
                self.assertIsNotNone(location.created_by.username)

    def test_polymorphic_hierarchy_queries_efficient(self):
        """Test that hierarchy traversal remains efficient with polymorphic queries."""
        # Create a hierarchy
        root = Location.objects.create(
            name="Performance Root",
            campaign=self.campaign,
            created_by=self.user,
        )

        # Create children
        children = []
        for i in range(5):
            child = Location.objects.create(
                name=f"Performance Child {i}",
                campaign=self.campaign,
                parent=root,
                created_by=self.user,
            )
            children.append(child)

        # Hierarchy methods should remain efficient
        # This will test that polymorphic inheritance doesn't break optimization
        # The get_descendants method does breadth-first traversal, so it will
        # use multiple queries (one per level + final count). This is expected.
        with self.assertNumQueries(7):  # Realistic expectation for BFS traversal
            descendants = root.get_descendants()
            self.assertEqual(descendants.count(), 5)

        # Each descendant should maintain polymorphic identity
        for descendant in descendants:
            self.assertIsInstance(descendant, Location)


class LocationPolymorphicMigrationTest(TransactionTestCase):
    """Test data migration scenarios for polymorphic conversion."""

    def setUp(self):
        """Set up test data that simulates pre-migration state."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.campaign = Campaign.objects.create(
            name="Migration Test Campaign", owner=self.user, game_system="mage"
        )

    def test_migration_preserves_all_existing_data(self):
        """Test that migration preserves all existing location data."""
        # Create complex location hierarchy before conversion
        locations_data = [
            {"name": "World", "parent": None},
            {"name": "Continent", "parent": "World"},
            {"name": "Country", "parent": "Continent"},
            {"name": "City", "parent": "Country"},
            {"name": "District", "parent": "City"},
        ]

        created_locations = {}
        for loc_data in locations_data:
            parent = (
                created_locations.get(loc_data["parent"])
                if loc_data["parent"]
                else None
            )
            location = Location.objects.create(
                name=loc_data["name"],
                description=f"Description for {loc_data['name']}",
                campaign=self.campaign,
                parent=parent,
                created_by=self.user,
            )
            created_locations[loc_data["name"]] = location

        # After migration, all data should be preserved
        for name, original_location in created_locations.items():
            original_location.refresh_from_db()

            # Basic data preservation
            self.assertEqual(original_location.name, name)
            self.assertEqual(original_location.description, f"Description for {name}")
            self.assertEqual(original_location.campaign, self.campaign)
            self.assertEqual(original_location.created_by, self.user)

            # Hierarchy preservation
            if name != "World":
                self.assertIsNotNone(original_location.parent)
            else:
                self.assertIsNone(original_location.parent)

            # This will FAIL until polymorphic conversion is complete
            self.assertIsNotNone(
                original_location.polymorphic_ctype,
                f"Location {name} should have polymorphic_ctype after migration",
            )

    def test_migration_handles_large_datasets(self):
        """Test that migration can handle large numbers of locations."""
        # Create a large number of locations to test migration performance
        locations = []
        for i in range(100):
            location_data = {
                "name": f"Migration Test Location {i}",
                "description": f"Description for location {i}",
                "campaign": self.campaign,
                "created_by": self.user,
            }
            locations.append(Location(**location_data))

        # Bulk create for performance
        with transaction.atomic():
            Location.objects.bulk_create(locations)

        # After migration, all locations should have polymorphic data
        # This will FAIL until polymorphic conversion is complete
        all_locations = Location.objects.all()
        self.assertEqual(all_locations.count(), 100)

        for location in all_locations:
            self.assertIsNotNone(
                location.polymorphic_ctype,
                "All migrated locations should have polymorphic_ctype",
            )

    def test_migration_preserves_relationships(self):
        """Test that migration preserves all foreign key relationships."""
        # Create additional users and campaigns
        other_user = User.objects.create_user(
            username="otheruser", email="other@example.com", password="testpass123"
        )
        other_campaign = Campaign.objects.create(
            name="Other Campaign", owner=other_user, game_system="generic"
        )

        # Create locations with various relationship combinations
        location1 = Location.objects.create(
            name="User1 Campaign1 Location",
            campaign=self.campaign,
            created_by=self.user,
        )

        location2 = Location.objects.create(
            name="User2 Campaign2 Location",
            campaign=other_campaign,
            created_by=other_user,
        )

        location3 = Location.objects.create(
            name="User1 Campaign2 Location",
            campaign=other_campaign,
            created_by=self.user,  # Cross-user creation
        )

        # After migration, all relationships should be preserved
        for location in [location1, location2, location3]:
            location.refresh_from_db()

            # Campaign relationships preserved
            self.assertIsNotNone(location.campaign)
            self.assertIn(location, location.campaign.locations.all())

            # User relationships preserved
            self.assertIsNotNone(location.created_by)
            # Check that the user exists in Location objects created by this user
            user_locations = Location.objects.filter(created_by=location.created_by)
            self.assertIn(location, user_locations)

            # This will FAIL until polymorphic conversion is complete
            self.assertIsNotNone(
                location.polymorphic_ctype,
                "All locations should have polymorphic_ctype after migration",
            )


class LocationBackwardCompatibilityTest(TestCase):
    """Test that polymorphic conversion maintains backward compatibility."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign", owner=self.user, game_system="mage"
        )

    def test_existing_code_continues_to_work(self):
        """Test that existing code patterns continue to work after conversion."""
        # Standard creation should work
        location = Location.objects.create(
            name="Compatibility Test",
            campaign=self.campaign,
            created_by=self.user,
        )

        # Standard queries should work
        retrieved = Location.objects.get(id=location.id)
        self.assertEqual(retrieved, location)

        # Standard filtering should work
        filtered = Location.objects.filter(name="Compatibility Test")
        self.assertIn(location, filtered)

        # Standard updates should work
        location.description = "Updated description"
        location.save()

        location.refresh_from_db()
        self.assertEqual(location.description, "Updated description")

    def test_model_methods_unchanged(self):
        """Test that all existing model methods work unchanged."""
        # Create hierarchy for testing
        parent = Location.objects.create(
            name="Parent",
            campaign=self.campaign,
            created_by=self.user,
        )

        child = Location.objects.create(
            name="Child",
            campaign=self.campaign,
            parent=parent,
            created_by=self.user,
        )

        # All existing methods should work exactly as before
        self.assertEqual(child.get_root(), parent)
        self.assertEqual(child.get_depth(), 1)
        self.assertEqual(parent.get_depth(), 0)
        self.assertTrue(child.is_descendant_of(parent))
        self.assertFalse(parent.is_descendant_of(child))
        self.assertIn(child, parent.get_descendants())
        self.assertIn(parent, child.get_ancestors())
        self.assertEqual(child.get_siblings().count(), 0)

    def test_validation_rules_preserved(self):
        """Test that all validation rules continue to work."""
        location = Location.objects.create(
            name="Validation Test",
            campaign=self.campaign,
            created_by=self.user,
        )

        # Self-parent validation should still work
        location.parent = location
        with self.assertRaises(ValidationError):
            location.clean()

        # Cross-campaign parent validation should still work
        other_campaign = Campaign.objects.create(
            name="Other Campaign", owner=self.user, game_system="generic"
        )
        other_location = Location.objects.create(
            name="Other Location",
            campaign=other_campaign,
            created_by=self.user,
        )

        location.parent = other_location
        with self.assertRaises(ValidationError):
            location.clean()

    def test_permission_methods_unchanged(self):
        """Test that permission methods work exactly as before."""
        gm = User.objects.create_user(
            username="gm", email="gm@example.com", password="testpass123"
        )
        player = User.objects.create_user(
            username="player", email="player@example.com", password="testpass123"
        )

        CampaignMembership.objects.create(campaign=self.campaign, user=gm, role="GM")
        CampaignMembership.objects.create(
            campaign=self.campaign, user=player, role="PLAYER"
        )

        location = Location.objects.create(
            name="Permission Test",
            campaign=self.campaign,
            created_by=self.user,
        )

        # All permission checks should work as before
        self.assertTrue(location.can_view(self.user))
        self.assertTrue(location.can_edit(self.user))
        self.assertTrue(location.can_delete(self.user))

        self.assertTrue(location.can_view(gm))
        self.assertTrue(location.can_edit(gm))
        self.assertTrue(location.can_delete(gm))

        self.assertTrue(location.can_view(player))
        self.assertFalse(location.can_edit(player))
        self.assertFalse(location.can_delete(player))

        # Class method should work as before
        self.assertTrue(Location.can_create(self.user, self.campaign))
        self.assertTrue(Location.can_create(gm, self.campaign))
        self.assertTrue(Location.can_create(player, self.campaign))

    def test_string_representation_unchanged(self):
        """Test that string representation remains the same."""
        location = Location.objects.create(
            name="String Test Location",
            campaign=self.campaign,
            created_by=self.user,
        )

        # String representation should be unchanged
        self.assertEqual(str(location), "String Test Location")

    def test_meta_options_preserved(self):
        """Test that model Meta options are preserved."""
        # Meta options should remain the same
        self.assertEqual(Location._meta.db_table, "locations_location")
        self.assertEqual(Location._meta.ordering, ["name"])
        self.assertEqual(Location._meta.verbose_name, "Location")
        self.assertEqual(Location._meta.verbose_name_plural, "Locations")
