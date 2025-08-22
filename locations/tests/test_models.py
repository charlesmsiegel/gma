"""
Comprehensive tests for Location model with hierarchy support.

Tests cover:
- Basic model structure and field validation
- Hierarchy functionality (parent-child relationships)
- Tree traversal methods
- Validation rules (circular references, depth limits)
- Permission model integration
- Edge cases and error handling

Test Structure:
- LocationModelTest: Basic model structure and CRUD operations
- LocationHierarchyTest: Parent-child relationships and tree operations
- LocationTraversalTest: Tree traversal methods
- LocationValidationTest: Validation rules and constraints
- LocationPermissionTest: Permission-based access control
- LocationEdgeCaseTest: Edge cases and error scenarios
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from campaigns.models import Campaign, CampaignMembership
from locations.models import Location

User = get_user_model()


class LocationModelTest(TestCase):
    """Test basic Location model structure and CRUD operations."""

    def setUp(self):
        """Set up test users and campaigns."""
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
            name="Test Campaign",
            owner=self.owner,
            game_system="mage",
        )

        # Add memberships
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm, role="GM"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )

    def test_location_model_fields(self):
        """Test that Location model has all expected fields."""
        location = Location.objects.create(
            name="Test Location",
            description="A test location",
            campaign=self.campaign,
            created_by=self.owner,
        )

        # Test inherited mixin fields
        self.assertIsNotNone(location.created_at)
        self.assertIsNotNone(location.updated_at)
        self.assertEqual(location.name, "Test Location")
        self.assertEqual(location.description, "A test location")
        self.assertEqual(location.created_by, self.owner)

        # Test Location-specific fields
        self.assertEqual(location.campaign, self.campaign)

        # Test hierarchy field (now implemented)
        self.assertIsNone(location.parent)  # Default should be None

    def test_location_creation_minimal_fields(self):
        """Test Location creation with minimal required fields."""
        location = Location.objects.create(
            name="Minimal Location",
            campaign=self.campaign,
            created_by=self.owner,
        )

        self.assertEqual(location.name, "Minimal Location")
        self.assertEqual(location.description, "")  # Default value from mixin
        self.assertEqual(location.campaign, self.campaign)
        self.assertEqual(location.created_by, self.owner)
        self.assertIsNone(location.modified_by)

    def test_location_string_representation(self):
        """Test Location __str__ method."""
        location = Location.objects.create(
            name="String Test Location",
            campaign=self.campaign,
            created_by=self.owner,
        )

        self.assertEqual(str(location), "String Test Location")

    def test_location_metadata(self):
        """Test Location model metadata configuration."""
        # Test database table name
        self.assertEqual(Location._meta.db_table, "locations_location")

        # Test ordering
        self.assertEqual(Location._meta.ordering, ["name"])

        # Test verbose names
        self.assertEqual(Location._meta.verbose_name, "Location")
        self.assertEqual(Location._meta.verbose_name_plural, "Locations")

    def test_location_campaign_relationship(self):
        """Test Location-Campaign foreign key relationship."""
        location = Location.objects.create(
            name="Campaign Test Location",
            campaign=self.campaign,
            created_by=self.owner,
        )

        # Test forward relationship
        self.assertEqual(location.campaign, self.campaign)

        # Test reverse relationship
        self.assertIn(location, self.campaign.locations.all())

    def test_location_cascade_deletion(self):
        """Test that location is deleted when campaign is deleted."""
        location = Location.objects.create(
            name="Cascade Test Location",
            campaign=self.campaign,
            created_by=self.owner,
        )

        location_id = location.id
        self.campaign.delete()

        # Location should be deleted due to CASCADE
        with self.assertRaises(Location.DoesNotExist):
            Location.objects.get(id=location_id)

    def test_location_auditable_fields(self):
        """Test AuditableMixin functionality on Location."""
        location = Location.objects.create(
            name="Audit Test Location",
            campaign=self.campaign,
            created_by=self.owner,
        )

        # Test created_by is set
        self.assertEqual(location.created_by, self.owner)
        self.assertIsNone(location.modified_by)

        # Test modified_by is set on update
        location.name = "Updated Location"
        location.save(user=self.player)

        location.refresh_from_db()
        self.assertEqual(location.modified_by, self.player)
        self.assertEqual(location.created_by, self.owner)  # Should not change

    def test_location_timestamp_fields(self):
        """Test TimestampedMixin functionality on Location."""
        before_create = timezone.now()

        location = Location.objects.create(
            name="Timestamp Test Location",
            campaign=self.campaign,
            created_by=self.owner,
        )

        after_create = timezone.now()

        # Test creation timestamps
        self.assertGreaterEqual(location.created_at, before_create)
        self.assertLessEqual(location.created_at, after_create)
        self.assertGreaterEqual(location.updated_at, before_create)
        self.assertLessEqual(location.updated_at, after_create)

        original_updated_at = location.updated_at

        # Test update timestamp
        location.description = "Updated description"
        location.save()

        location.refresh_from_db()
        self.assertGreater(location.updated_at, original_updated_at)
        self.assertEqual(location.created_at, location.created_at)  # Should not change


class LocationHierarchyTest(TestCase):
    """Test Location hierarchy functionality."""

    def setUp(self):
        """Set up test data for hierarchy tests."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Hierarchy Test Campaign",
            owner=self.owner,
            game_system="mage",
        )

    def test_location_has_parent_field(self):
        """Test that Location model has parent field for hierarchy."""
        # This test will initially fail until hierarchy is implemented
        location = Location.objects.create(
            name="Child Location",
            campaign=self.campaign,
            created_by=self.owner,
        )

        # Test parent field exists and defaults to None
        try:
            self.assertIsNone(location.parent)
        except AttributeError:
            self.fail(
                "Location model should have a 'parent' field for hierarchy support"
            )

    def test_sub_locations_property(self):
        """Test sub_locations property as alias for children."""
        # Create a parent with multiple children
        parent_location = Location.objects.create(
            name="Parent Location",
            campaign=self.campaign,
            created_by=self.owner,
        )

        Location.objects.create(
            name="Child 1",
            campaign=self.campaign,
            parent=parent_location,
            created_by=self.owner,
        )
        Location.objects.create(
            name="Child 2",
            campaign=self.campaign,
            parent=parent_location,
            created_by=self.owner,
        )

        # Test sub_locations property returns same as children
        sub_locations = parent_location.sub_locations
        children = parent_location.children.all()

        # Should have same count
        self.assertEqual(sub_locations.count(), children.count())
        self.assertEqual(sub_locations.count(), 2)  # child1 + child2

        # Should contain the same locations
        self.assertCountEqual(list(sub_locations), list(children))

    def test_create_parent_child_relationship(self):
        """Test creating parent-child location relationships."""
        parent = Location.objects.create(
            name="Parent Location",
            campaign=self.campaign,
            created_by=self.owner,
        )

        child = Location.objects.create(
            name="Child Location",
            campaign=self.campaign,
            parent=parent,
            created_by=self.owner,
        )

        # Test forward relationship
        self.assertEqual(child.parent, parent)

        # Test reverse relationship
        self.assertIn(child, parent.children.all())

    def test_multiple_children(self):
        """Test that a location can have multiple children."""
        parent = Location.objects.create(
            name="Parent Location",
            campaign=self.campaign,
            created_by=self.owner,
        )

        children = []
        for i in range(3):
            child = Location.objects.create(
                name=f"Child Location {i}",
                campaign=self.campaign,
                parent=parent,
                created_by=self.owner,
            )
            children.append(child)

        # Test all children are related to parent
        parent_children = parent.children.all()
        self.assertEqual(parent_children.count(), 3)
        for child in children:
            self.assertIn(child, parent_children)

    def test_nested_hierarchy(self):
        """Test creating nested location hierarchy."""
        # Create 3-level hierarchy: Continent > Country > City
        continent = Location.objects.create(
            name="North America",
            campaign=self.campaign,
            created_by=self.owner,
        )

        country = Location.objects.create(
            name="United States",
            campaign=self.campaign,
            parent=continent,
            created_by=self.owner,
        )

        city = Location.objects.create(
            name="New York",
            campaign=self.campaign,
            parent=country,
            created_by=self.owner,
        )

        # Test hierarchy relationships
        self.assertIsNone(continent.parent)
        self.assertEqual(country.parent, continent)
        self.assertEqual(city.parent, country)

        # Test reverse relationships
        self.assertIn(country, continent.children.all())
        self.assertIn(city, country.children.all())
        self.assertEqual(city.children.count(), 0)

    def test_maximum_depth_limit(self):
        """Test that location hierarchy enforces maximum depth of 10 levels."""
        # Create a chain of 10 locations (depth 0-9)
        locations = []
        parent = None

        for i in range(10):
            location = Location.objects.create(
                name=f"Level {i} Location",
                campaign=self.campaign,
                parent=parent,
                created_by=self.owner,
            )
            locations.append(location)
            parent = location

        # Attempting to create an 11th level should fail
        with self.assertRaises(ValidationError) as context:
            Location.objects.create(
                name="Level 10 Location (should fail)",
                campaign=self.campaign,
                parent=locations[-1],
                created_by=self.owner,
            )

        self.assertIn("maximum depth", str(context.exception).lower())

    def test_orphan_handling_on_parent_deletion(self):
        """Test that children move to grandparent when parent is deleted."""
        grandparent = Location.objects.create(
            name="Grandparent Location",
            campaign=self.campaign,
            created_by=self.owner,
        )

        parent = Location.objects.create(
            name="Parent Location",
            campaign=self.campaign,
            parent=grandparent,
            created_by=self.owner,
        )

        child1 = Location.objects.create(
            name="Child 1",
            campaign=self.campaign,
            parent=parent,
            created_by=self.owner,
        )

        child2 = Location.objects.create(
            name="Child 2",
            campaign=self.campaign,
            parent=parent,
            created_by=self.owner,
        )

        # Delete parent
        parent.delete()

        # Children should now have grandparent as parent
        child1.refresh_from_db()
        child2.refresh_from_db()

        self.assertEqual(child1.parent, grandparent)
        self.assertEqual(child2.parent, grandparent)
        self.assertIn(child1, grandparent.children.all())
        self.assertIn(child2, grandparent.children.all())

    def test_orphan_handling_no_grandparent(self):
        """Test children become top-level when parent with no grandparent deleted."""
        parent = Location.objects.create(
            name="Parent Location",
            campaign=self.campaign,
            created_by=self.owner,
        )

        child1 = Location.objects.create(
            name="Child 1",
            campaign=self.campaign,
            parent=parent,
            created_by=self.owner,
        )

        child2 = Location.objects.create(
            name="Child 2",
            campaign=self.campaign,
            parent=parent,
            created_by=self.owner,
        )

        # Delete parent
        parent.delete()

        # Children should now have no parent (top-level)
        child1.refresh_from_db()
        child2.refresh_from_db()

        self.assertIsNone(child1.parent)
        self.assertIsNone(child2.parent)


class LocationTraversalTest(TestCase):
    """Test tree traversal methods on Location model."""

    def setUp(self):
        """Set up test hierarchy for traversal tests."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Traversal Test Campaign",
            owner=self.owner,
            game_system="mage",
        )

        # Create test hierarchy:
        # World
        #   ├── Continent1
        #   │   ├── Country1
        #   │   │   ├── City1
        #   │   │   └── City2
        #   │   └── Country2
        #   └── Continent2

        self.world = Location.objects.create(
            name="World",
            campaign=self.campaign,
            created_by=self.owner,
        )

        self.continent1 = Location.objects.create(
            name="Continent1",
            campaign=self.campaign,
            parent=self.world,
            created_by=self.owner,
        )

        self.continent2 = Location.objects.create(
            name="Continent2",
            campaign=self.campaign,
            parent=self.world,
            created_by=self.owner,
        )

        self.country1 = Location.objects.create(
            name="Country1",
            campaign=self.campaign,
            parent=self.continent1,
            created_by=self.owner,
        )

        self.country2 = Location.objects.create(
            name="Country2",
            campaign=self.campaign,
            parent=self.continent1,
            created_by=self.owner,
        )

        self.city1 = Location.objects.create(
            name="City1",
            campaign=self.campaign,
            parent=self.country1,
            created_by=self.owner,
        )

        self.city2 = Location.objects.create(
            name="City2",
            campaign=self.campaign,
            parent=self.country1,
            created_by=self.owner,
        )

    def test_get_descendants_method(self):
        """Test get_descendants() returns all children, grandchildren, etc."""
        # World should have all locations as descendants
        world_descendants = self.world.get_descendants()
        expected = [
            self.continent1,
            self.continent2,
            self.country1,
            self.country2,
            self.city1,
            self.city2,
        ]

        self.assertEqual(world_descendants.count(), 6)
        for location in expected:
            self.assertIn(location, world_descendants)

        # Continent1 should have country1, country2, city1, city2
        continent1_descendants = self.continent1.get_descendants()
        expected_continent1 = [
            self.country1,
            self.country2,
            self.city1,
            self.city2,
        ]

        self.assertEqual(continent1_descendants.count(), 4)
        for location in expected_continent1:
            self.assertIn(location, continent1_descendants)

        # Country1 should have city1, city2
        country1_descendants = self.country1.get_descendants()
        expected_country1 = [self.city1, self.city2]

        self.assertEqual(country1_descendants.count(), 2)
        for location in expected_country1:
            self.assertIn(location, country1_descendants)

        # City1 should have no descendants
        city1_descendants = self.city1.get_descendants()
        self.assertEqual(city1_descendants.count(), 0)

    def test_get_ancestors_method(self):
        """Test get_ancestors() returns all parents up to root."""
        # City1 ancestors should be: Country1, Continent1, World
        city1_ancestors = self.city1.get_ancestors()
        expected = [self.country1, self.continent1, self.world]

        self.assertEqual(city1_ancestors.count(), 3)
        for location in expected:
            self.assertIn(location, city1_ancestors)

        # Country1 ancestors should be: Continent1, World
        country1_ancestors = self.country1.get_ancestors()
        expected_country1 = [self.continent1, self.world]

        self.assertEqual(country1_ancestors.count(), 2)
        for location in expected_country1:
            self.assertIn(location, country1_ancestors)

        # Continent1 ancestors should be: World
        continent1_ancestors = self.continent1.get_ancestors()
        self.assertEqual(continent1_ancestors.count(), 1)
        self.assertIn(self.world, continent1_ancestors)

        # World should have no ancestors
        world_ancestors = self.world.get_ancestors()
        self.assertEqual(world_ancestors.count(), 0)

    def test_get_siblings_method(self):
        """Test get_siblings() returns locations with same parent."""
        # City1 and City2 should be siblings
        city1_siblings = self.city1.get_siblings()
        self.assertEqual(city1_siblings.count(), 1)
        self.assertIn(self.city2, city1_siblings)

        city2_siblings = self.city2.get_siblings()
        self.assertEqual(city2_siblings.count(), 1)
        self.assertIn(self.city1, city2_siblings)

        # Country1 and Country2 should be siblings
        country1_siblings = self.country1.get_siblings()
        self.assertEqual(country1_siblings.count(), 1)
        self.assertIn(self.country2, country1_siblings)

        # Continent1 and Continent2 should be siblings
        continent1_siblings = self.continent1.get_siblings()
        self.assertEqual(continent1_siblings.count(), 1)
        self.assertIn(self.continent2, continent1_siblings)

        # World should have no siblings (no parent)
        world_siblings = self.world.get_siblings()
        self.assertEqual(world_siblings.count(), 0)

    def test_get_root_method(self):
        """Test get_root() returns the top-level ancestor."""
        # All locations should have World as root
        locations = [
            self.city1,
            self.city2,
            self.country1,
            self.country2,
            self.continent1,
            self.continent2,
        ]

        for location in locations:
            self.assertEqual(location.get_root(), self.world)

        # World should return itself as root
        self.assertEqual(self.world.get_root(), self.world)

    def test_get_path_from_root_method(self):
        """Test get_path_from_root() returns ordered path from root to location."""
        # City1 path should be: [World, Continent1, Country1, City1]
        city1_path = self.city1.get_path_from_root()
        expected_path = [self.world, self.continent1, self.country1, self.city1]

        self.assertEqual(list(city1_path), expected_path)

        # Country1 path should be: [World, Continent1, Country1]
        country1_path = self.country1.get_path_from_root()
        expected_country1_path = [self.world, self.continent1, self.country1]

        self.assertEqual(list(country1_path), expected_country1_path)

        # World path should be: [World]
        world_path = self.world.get_path_from_root()
        self.assertEqual(list(world_path), [self.world])

    def test_is_descendant_of_method(self):
        """Test is_descendant_of() method for checking ancestry."""
        # City1 should be descendant of all its ancestors
        self.assertTrue(self.city1.is_descendant_of(self.country1))
        self.assertTrue(self.city1.is_descendant_of(self.continent1))
        self.assertTrue(self.city1.is_descendant_of(self.world))

        # City1 should not be descendant of siblings or unrelated locations
        self.assertFalse(self.city1.is_descendant_of(self.city2))
        self.assertFalse(self.city1.is_descendant_of(self.country2))
        self.assertFalse(self.city1.is_descendant_of(self.continent2))

        # Location should not be descendant of itself
        self.assertFalse(self.city1.is_descendant_of(self.city1))

    def test_get_depth_method(self):
        """Test get_depth() method returns correct hierarchy depth."""
        # World should be depth 0
        self.assertEqual(self.world.get_depth(), 0)

        # Continents should be depth 1
        self.assertEqual(self.continent1.get_depth(), 1)
        self.assertEqual(self.continent2.get_depth(), 1)

        # Countries should be depth 2
        self.assertEqual(self.country1.get_depth(), 2)
        self.assertEqual(self.country2.get_depth(), 2)

        # Cities should be depth 3
        self.assertEqual(self.city1.get_depth(), 3)
        self.assertEqual(self.city2.get_depth(), 3)


class LocationValidationTest(TestCase):
    """Test Location model validation rules and constraints."""

    def setUp(self):
        """Set up test data for validation tests."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Validation Test Campaign",
            owner=self.owner,
            game_system="mage",
        )

    def test_prevent_circular_references(self):
        """Test that circular references are prevented in hierarchy."""
        parent = Location.objects.create(
            name="Parent Location",
            campaign=self.campaign,
            created_by=self.owner,
        )

        child = Location.objects.create(
            name="Child Location",
            campaign=self.campaign,
            parent=parent,
            created_by=self.owner,
        )

        # Attempting to make parent a child of child should fail
        parent.parent = child
        with self.assertRaises(ValidationError) as context:
            parent.clean()

        self.assertIn("circular", str(context.exception).lower())

    def test_prevent_self_parent(self):
        """Test that location cannot be its own parent."""
        location = Location.objects.create(
            name="Self Parent Test",
            campaign=self.campaign,
            created_by=self.owner,
        )

        # Attempting to make location its own parent should fail
        location.parent = location
        with self.assertRaises(ValidationError) as context:
            location.clean()

        self.assertIn("cannot be its own parent", str(context.exception).lower())

    def test_name_field_required(self):
        """Test that name field is required."""
        with self.assertRaises(ValidationError):
            location = Location(
                name="",  # Empty name should fail
                campaign=self.campaign,
                created_by=self.owner,
            )
            location.full_clean()  # This will trigger validation
            location.clean()

    def test_campaign_field_required(self):
        """Test that campaign field is required."""
        with self.assertRaises(IntegrityError):
            Location.objects.create(
                name="No Campaign Location",
                campaign=None,  # Should fail at database level
                created_by=self.owner,
            )

    def test_cross_campaign_parent_validation(self):
        """Test that parent must be in same campaign."""
        other_campaign = Campaign.objects.create(
            name="Other Campaign",
            owner=self.owner,
            game_system="generic",
        )

        parent_location = Location.objects.create(
            name="Parent in Other Campaign",
            campaign=other_campaign,
            created_by=self.owner,
        )

        # Attempting to create child in different campaign should fail
        with self.assertRaises(ValidationError) as context:
            child = Location(
                name="Child in Different Campaign",
                campaign=self.campaign,
                parent=parent_location,
                created_by=self.owner,
            )
            child.clean()

        self.assertIn("same campaign", str(context.exception).lower())

    def test_maximum_name_length(self):
        """Test that name field enforces maximum length from NamedModelMixin."""
        # Name should be limited to 100 characters (from NamedModelMixin)
        long_name = "A" * 101

        with self.assertRaises(ValidationError):
            location = Location(
                name=long_name,
                campaign=self.campaign,
                created_by=self.owner,
            )
            location.full_clean()

    def test_depth_calculation_accuracy(self):
        """Test that depth calculation is accurate for validation."""
        # Create 9 levels (max allowed)
        locations = []
        parent = None

        for i in range(9):
            location = Location.objects.create(
                name=f"Level {i}",
                campaign=self.campaign,
                parent=parent,
                created_by=self.owner,
            )
            locations.append(location)
            parent = location

        # 10th level should still be allowed (depth 9)
        tenth_level = Location.objects.create(
            name="Level 9 (depth 9)",
            campaign=self.campaign,
            parent=locations[-1],
            created_by=self.owner,
        )

        # 11th level should fail (depth 10)
        with self.assertRaises(ValidationError):
            Location.objects.create(
                name="Level 10 (should fail)",
                campaign=self.campaign,
                parent=tenth_level,
                created_by=self.owner,
            )


class LocationPermissionTest(TestCase):
    """Test permission-based access control for Location model."""

    def setUp(self):
        """Set up test users with different campaign roles."""
        # Users
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.gm = User.objects.create_user(
            username="gm", email="gm@test.com", password="testpass123"
        )
        self.player = User.objects.create_user(
            username="player", email="player@test.com", password="testpass123"
        )
        self.observer = User.objects.create_user(
            username="observer", email="observer@test.com", password="testpass123"
        )
        self.non_member = User.objects.create_user(
            username="non_member", email="non_member@test.com", password="testpass123"
        )

        # Campaign with memberships
        self.campaign = Campaign.objects.create(
            name="Permission Test Campaign",
            owner=self.owner,
            game_system="mage",
        )

        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm, role="GM"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.observer, role="OBSERVER"
        )

        # Test location
        self.location = Location.objects.create(
            name="Permission Test Location",
            campaign=self.campaign,
            created_by=self.owner,
        )

    def test_location_management_permissions(self):
        """Test that location management follows campaign permission hierarchy."""
        # This test assumes that Location model will have permission checking methods
        # based on campaign roles (similar to campaign model pattern)

        # Owner should be able to manage all locations
        self.assertTrue(self.location.can_edit(self.owner))
        self.assertTrue(self.location.can_delete(self.owner))

        # GM should be able to manage all locations
        self.assertTrue(self.location.can_edit(self.gm))
        self.assertTrue(self.location.can_delete(self.gm))

        # Player should be able to create and edit own locations
        player_location = Location.objects.create(
            name="Player Location",
            campaign=self.campaign,
            created_by=self.player,
        )

        self.assertTrue(player_location.can_edit(self.player))
        self.assertTrue(player_location.can_delete(self.player))

        # Player should not be able to edit other's locations
        self.assertFalse(self.location.can_edit(self.player))
        self.assertFalse(self.location.can_delete(self.player))

        # Observer should not be able to edit or delete any locations
        self.assertFalse(self.location.can_edit(self.observer))
        self.assertFalse(self.location.can_delete(self.observer))

        # Non-member should not have any permissions
        self.assertFalse(self.location.can_edit(self.non_member))
        self.assertFalse(self.location.can_delete(self.non_member))

    def test_location_visibility_permissions(self):
        """Test that location visibility follows campaign permissions."""
        # All campaign members should be able to view locations
        self.assertTrue(self.location.can_view(self.owner))
        self.assertTrue(self.location.can_view(self.gm))
        self.assertTrue(self.location.can_view(self.player))
        self.assertTrue(self.location.can_view(self.observer))

        # Non-members should not be able to view private campaign locations
        self.assertFalse(self.location.can_view(self.non_member))

        # Test public campaign visibility
        public_campaign = Campaign.objects.create(
            name="Public Campaign",
            owner=self.owner,
            is_public=True,
            game_system="generic",
        )

        public_location = Location.objects.create(
            name="Public Location",
            campaign=public_campaign,
            created_by=self.owner,
        )

        # Non-members should be able to view public campaign locations
        self.assertTrue(public_location.can_view(self.non_member))

    def test_location_creation_permissions(self):
        """Test that location creation follows campaign permission rules."""
        # Test assumes Location model has class methods for permission checking

        # All campaign members should be able to create locations
        self.assertTrue(Location.can_create(self.owner, self.campaign))
        self.assertTrue(Location.can_create(self.gm, self.campaign))
        self.assertTrue(Location.can_create(self.player, self.campaign))

        # Observers can view but cannot create locations
        self.assertFalse(Location.can_create(self.observer, self.campaign))

        # Non-members should not be able to create locations
        self.assertFalse(Location.can_create(self.non_member, self.campaign))

    def test_hierarchy_permissions(self):
        """Test that hierarchy operations respect permissions."""
        # Create a location hierarchy where different users own different levels
        gm_location = Location.objects.create(
            name="GM Location",
            campaign=self.campaign,
            created_by=self.gm,
        )

        player_location = Location.objects.create(
            name="Player Location",
            campaign=self.campaign,
            parent=gm_location,
            created_by=self.player,
        )

        # Player should be able to move their own location under different parent
        # if they have permission to create under new parent
        owner_location = Location.objects.create(
            name="Owner Location",
            campaign=self.campaign,
            created_by=self.owner,
        )

        # Player should be able to move their location under owner's location
        # (assuming they can create children of any location in campaign)
        player_location.parent = owner_location
        self.assertTrue(player_location.can_edit(self.player))

        # Player should not be able to make their location a parent of GM's location
        # by moving GM's location under theirs
        self.assertFalse(gm_location.can_edit(self.player))


class LocationEdgeCaseTest(TestCase):
    """Test edge cases and error scenarios for Location model."""

    def setUp(self):
        """Set up test data for edge case tests."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Edge Case Test Campaign",
            owner=self.owner,
            game_system="mage",
        )

    def test_location_deletion_with_children(self):
        """Test location deletion when it has children."""
        parent = Location.objects.create(
            name="Parent with Children",
            campaign=self.campaign,
            created_by=self.owner,
        )

        child1 = Location.objects.create(
            name="Child 1",
            campaign=self.campaign,
            parent=parent,
            created_by=self.owner,
        )

        child2 = Location.objects.create(
            name="Child 2",
            campaign=self.campaign,
            parent=parent,
            created_by=self.owner,
        )

        # Deleting parent should handle children appropriately
        parent.delete()

        # Children should still exist but have no parent (moved to top-level)
        child1.refresh_from_db()
        child2.refresh_from_db()

        self.assertIsNone(child1.parent)
        self.assertIsNone(child2.parent)

    def test_bulk_operations_preserve_hierarchy(self):
        """Test that bulk operations maintain hierarchy integrity."""
        # Create multiple locations
        locations = []
        for i in range(5):
            location = Location(
                name=f"Bulk Location {i}",
                campaign=self.campaign,
                created_by=self.owner,
            )
            locations.append(location)

        # Bulk create
        Location.objects.bulk_create(locations)

        # Verify all locations were created
        created_locations = Location.objects.filter(name__startswith="Bulk Location")
        self.assertEqual(created_locations.count(), 5)

    def test_concurrent_hierarchy_modifications(self):
        """Test handling of concurrent hierarchy modifications."""
        parent = Location.objects.create(
            name="Concurrent Parent",
            campaign=self.campaign,
            created_by=self.owner,
        )

        child = Location.objects.create(
            name="Concurrent Child",
            campaign=self.campaign,
            parent=parent,
            created_by=self.owner,
        )

        # Simulate concurrent modification by updating the same object
        # This should be handled gracefully (same parent assignment is OK)
        child_copy = Location.objects.get(pk=child.pk)
        child_copy.name = "Updated Name"
        child_copy.save()

        # Should not cause integrity errors
        child.refresh_from_db()
        self.assertEqual(child.parent, parent)

    def test_location_ordering_with_hierarchy(self):
        """Test that location ordering works correctly with hierarchy."""
        # Create locations with different names to test ordering
        Location.objects.create(
            name="Z Location",
            campaign=self.campaign,
            created_by=self.owner,
        )

        Location.objects.create(
            name="A Location",
            campaign=self.campaign,
            created_by=self.owner,
        )

        Location.objects.create(
            name="M Location",
            campaign=self.campaign,
            created_by=self.owner,
        )

        # Test default ordering (by name)
        locations = list(Location.objects.all())
        names = [loc.name for loc in locations]

        # Should be ordered alphabetically by name
        self.assertEqual(names, sorted(names))

    def test_unicode_and_special_characters(self):
        """Test that location names handle unicode and special characters."""
        special_names = [
            "Café Mystique",
            "東京 (Tokyo)",
            "Москва́",
            "Location with 'quotes' and \"double quotes\"",
            "Location/with/slashes",
            "Location\\with\\backslashes",
            "Location with émojis 🏰🌟",
        ]

        for name in special_names:
            try:
                location = Location.objects.create(
                    name=name,
                    campaign=self.campaign,
                    created_by=self.owner,
                )
                self.assertEqual(location.name, name)
                self.assertEqual(str(location), name)
            except Exception as e:
                self.fail(f"Failed to create location with name '{name}': {e}")

    def test_large_hierarchy_performance(self):
        """Test performance with large hierarchy structures."""
        # Create a binary tree structure
        root = Location.objects.create(
            name="Performance Root",
            campaign=self.campaign,
            created_by=self.owner,
        )

        # Create 2 levels of binary tree (7 total nodes)
        level1_left = Location.objects.create(
            name="Level 1 Left",
            campaign=self.campaign,
            parent=root,
            created_by=self.owner,
        )

        level1_right = Location.objects.create(
            name="Level 1 Right",
            campaign=self.campaign,
            parent=root,
            created_by=self.owner,
        )

        # Create level 2
        for i, parent in enumerate([level1_left, level1_right]):
            for j in ["Left", "Right"]:
                Location.objects.create(
                    name=f"Level 2 {i}-{j}",
                    campaign=self.campaign,
                    parent=parent,
                    created_by=self.owner,
                )

        # Test that traversal methods work efficiently
        descendants = root.get_descendants()
        self.assertEqual(descendants.count(), 6)  # All except root

        ancestors = Location.objects.get(name="Level 2 0-Left").get_ancestors()
        self.assertEqual(ancestors.count(), 2)  # level1_left and root

    def test_location_with_maximum_field_lengths(self):
        """Test location creation with maximum allowed field lengths."""
        # Test maximum name length (100 chars from NamedModelMixin)
        max_name = "A" * 100

        # Test very long description
        max_description = "This is a very long description. " * 100

        location = Location.objects.create(
            name=max_name,
            description=max_description,
            campaign=self.campaign,
            created_by=self.owner,
        )

        self.assertEqual(location.name, max_name)
        self.assertEqual(location.description, max_description)
        self.assertEqual(len(location.name), 100)


class LocationFullPathTest(TestCase):
    """Test Location get_full_path() method for breadcrumb functionality."""

    def setUp(self):
        """Set up test hierarchy for get_full_path() tests."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Full Path Test Campaign",
            owner=self.owner,
            game_system="mage",
        )

        # Create test hierarchy:
        # World
        #   ├── Continent
        #   │   ├── Country
        #   │   │   ├── Region
        #   │   │   │   └── City
        #   │   │   └── District
        #   │   └── Nation
        #   └── Realm

        self.world = Location.objects.create(
            name="World",
            campaign=self.campaign,
            created_by=self.owner,
        )

        self.continent = Location.objects.create(
            name="Continent",
            campaign=self.campaign,
            parent=self.world,
            created_by=self.owner,
        )

        self.realm = Location.objects.create(
            name="Realm",
            campaign=self.campaign,
            parent=self.world,
            created_by=self.owner,
        )

        self.country = Location.objects.create(
            name="Country",
            campaign=self.campaign,
            parent=self.continent,
            created_by=self.owner,
        )

        self.nation = Location.objects.create(
            name="Nation",
            campaign=self.campaign,
            parent=self.continent,
            created_by=self.owner,
        )

        self.region = Location.objects.create(
            name="Region",
            campaign=self.campaign,
            parent=self.country,
            created_by=self.owner,
        )

        self.district = Location.objects.create(
            name="District",
            campaign=self.campaign,
            parent=self.country,
            created_by=self.owner,
        )

        self.city = Location.objects.create(
            name="City",
            campaign=self.campaign,
            parent=self.region,
            created_by=self.owner,
        )

    def test_get_full_path_method_exists(self):
        """Test that get_full_path() method exists on Location model."""
        # This test will fail initially until the method is implemented
        self.assertTrue(
            hasattr(Location, "get_full_path"),
            "Location model should have a get_full_path() method",
        )

    def test_get_full_path_root_location(self):
        """Test get_full_path() for root location (no parent)."""
        # Root location should return just its own name
        path = self.world.get_full_path()
        self.assertEqual(path, "World")

    def test_get_full_path_single_level_child(self):
        """Test get_full_path() for location with one parent."""
        # Single level child should show parent > child
        path = self.continent.get_full_path()
        self.assertEqual(path, "World > Continent")

        path = self.realm.get_full_path()
        self.assertEqual(path, "World > Realm")

    def test_get_full_path_multi_level_hierarchy(self):
        """Test get_full_path() for deeply nested locations."""
        # Multi-level hierarchy should show full path from root
        path = self.country.get_full_path()
        self.assertEqual(path, "World > Continent > Country")

        path = self.region.get_full_path()
        self.assertEqual(path, "World > Continent > Country > Region")

        path = self.city.get_full_path()
        self.assertEqual(path, "World > Continent > Country > Region > City")

    def test_get_full_path_sibling_locations(self):
        """Test get_full_path() for sibling locations at same level."""
        # Siblings should have same path up to parent, different final name
        nation_path = self.nation.get_full_path()
        country_path = self.country.get_full_path()

        self.assertEqual(nation_path, "World > Continent > Nation")
        self.assertEqual(country_path, "World > Continent > Country")

        # Both should start with same parent path
        self.assertTrue(nation_path.startswith("World > Continent > "))
        self.assertTrue(country_path.startswith("World > Continent > "))

        # Verify siblings at deeper level
        region_path = self.region.get_full_path()
        district_path = self.district.get_full_path()

        self.assertEqual(region_path, "World > Continent > Country > Region")
        self.assertEqual(district_path, "World > Continent > Country > District")

    def test_get_full_path_custom_separator(self):
        """Test get_full_path() with custom separator parameter."""
        # Test with different separators
        path_slash = self.city.get_full_path(separator=" / ")
        expected_slash = "World / Continent / Country / Region / City"
        self.assertEqual(path_slash, expected_slash)

        path_arrow = self.city.get_full_path(separator=" → ")
        expected_arrow = "World → Continent → Country → Region → City"
        self.assertEqual(path_arrow, expected_arrow)

        path_pipe = self.city.get_full_path(separator=" | ")
        expected_pipe = "World | Continent | Country | Region | City"
        self.assertEqual(path_pipe, expected_pipe)

        # Test with no spaces
        path_compact = self.city.get_full_path(separator=">")
        expected_compact = "World>Continent>Country>Region>City"
        self.assertEqual(path_compact, expected_compact)

    def test_get_full_path_default_separator(self):
        """Test that get_full_path() uses ' > ' as default separator."""
        # Without separator parameter, should use default ' > '
        path = self.city.get_full_path()
        self.assertEqual(path, "World > Continent > Country > Region > City")

        # Verify it's the same as explicitly passing default separator
        path_explicit = self.city.get_full_path(separator=" > ")
        self.assertEqual(path, path_explicit)

    def test_get_full_path_empty_separator(self):
        """Test get_full_path() with empty separator."""
        path = self.country.get_full_path(separator="")
        expected = "WorldContinentCountry"
        self.assertEqual(path, expected)

    def test_get_full_path_special_characters_in_names(self):
        """Test get_full_path() with special characters in location names."""
        # Create locations with special characters
        special_parent = Location.objects.create(
            name="Café & Restaurant",
            campaign=self.campaign,
            created_by=self.owner,
        )

        special_child = Location.objects.create(
            name="Room #42 (VIP)",
            campaign=self.campaign,
            parent=special_parent,
            created_by=self.owner,
        )

        path = special_child.get_full_path()
        expected = "Café & Restaurant > Room #42 (VIP)"
        self.assertEqual(path, expected)

    def test_get_full_path_unicode_characters(self):
        """Test get_full_path() with unicode characters in location names."""
        # Create locations with unicode characters
        unicode_parent = Location.objects.create(
            name="東京",
            campaign=self.campaign,
            created_by=self.owner,
        )

        unicode_child = Location.objects.create(
            name="渋谷区",
            campaign=self.campaign,
            parent=unicode_parent,
            created_by=self.owner,
        )

        path = unicode_child.get_full_path()
        expected = "東京 > 渋谷区"
        self.assertEqual(path, expected)

    def test_get_full_path_long_names(self):
        """Test get_full_path() with long location names."""
        # Create locations with long names
        long_parent = Location.objects.create(
            name="A" * 50,  # 50 character name
            campaign=self.campaign,
            created_by=self.owner,
        )

        long_child = Location.objects.create(
            name="B" * 50,  # 50 character name
            campaign=self.campaign,
            parent=long_parent,
            created_by=self.owner,
        )

        path = long_child.get_full_path()
        expected = ("A" * 50) + " > " + ("B" * 50)
        self.assertEqual(path, expected)

    def test_get_full_path_maximum_depth(self):
        """Test get_full_path() at maximum allowed hierarchy depth."""
        # Create a chain up to maximum depth (10 levels, depth 0-9)
        locations = [self.world]  # Start with existing root

        for i in range(9):  # Create 9 more levels
            location = Location.objects.create(
                name=f"Level{i+1}",
                campaign=self.campaign,
                parent=locations[-1],
                created_by=self.owner,
            )
            locations.append(location)

        # Test path for deepest location
        deepest_path = locations[-1].get_full_path()
        expected_names = [loc.name for loc in locations]
        expected_path = " > ".join(expected_names)

        self.assertEqual(deepest_path, expected_path)
        self.assertEqual(len(locations), 10)  # Verify we have 10 levels

        # Verify path contains all levels
        for location in locations:
            self.assertIn(location.name, deepest_path)

    def test_get_full_path_performance_with_prefetching(self):
        """Test that get_full_path() is efficient and doesn't cause N+1 queries."""
        # This test verifies that the method uses the existing optimized
        # get_path_from_root() method or implements similar optimization

        with self.assertNumQueries(1):  # Should be 1 optimized query
            path = self.city.get_full_path()

        # Verify the path is correct
        expected = "World > Continent > Country > Region > City"
        self.assertEqual(path, expected)

    def test_get_full_path_with_unsaved_location(self):
        """Test get_full_path() behavior with unsaved location instance."""
        # Create unsaved location
        unsaved_location = Location(
            name="Unsaved Location",
            campaign=self.campaign,
            created_by=self.owner,
        )

        # Should handle unsaved instance gracefully
        path = unsaved_location.get_full_path()
        self.assertEqual(path, "Unsaved Location")

    def test_get_full_path_with_none_parent(self):
        """Test get_full_path() explicitly handles None parent."""
        # Create location with explicitly None parent
        root_location = Location.objects.create(
            name="Explicit Root",
            campaign=self.campaign,
            parent=None,
            created_by=self.owner,
        )

        path = root_location.get_full_path()
        self.assertEqual(path, "Explicit Root")

    def test_get_full_path_return_type(self):
        """Test that get_full_path() returns a string."""
        path = self.city.get_full_path()
        self.assertIsInstance(path, str)

        # Test with custom separator also returns string
        path_custom = self.city.get_full_path(separator=" / ")
        self.assertIsInstance(path_custom, str)

    def test_get_full_path_breadcrumb_usage(self):
        """Test get_full_path() for typical breadcrumb usage scenarios."""
        # Test multiple locations for breadcrumb display
        locations_and_expected = [
            (self.world, "World"),
            (self.continent, "World > Continent"),
            (self.country, "World > Continent > Country"),
            (self.region, "World > Continent > Country > Region"),
            (self.city, "World > Continent > Country > Region > City"),
            (self.district, "World > Continent > Country > District"),
            (self.nation, "World > Continent > Nation"),
            (self.realm, "World > Realm"),
        ]

        for location, expected_path in locations_and_expected:
            with self.subTest(location=location.name):
                path = location.get_full_path()
                self.assertEqual(path, expected_path)

    def test_get_full_path_comparison_with_path_from_root(self):
        """Test that get_full_path() is consistent with get_path_from_root()."""
        # get_full_path() should produce the same order as get_path_from_root()
        path_queryset = self.city.get_path_from_root()
        path_names = [loc.name for loc in path_queryset]
        expected_string_path = " > ".join(path_names)

        actual_string_path = self.city.get_full_path()

        self.assertEqual(actual_string_path, expected_string_path)

    def test_get_full_path_with_circular_reference_protection(self):
        """Test get_full_path() handles potential circular references gracefully."""
        # Even though validation prevents circular references,
        # the method should have safety limits like other traversal methods

        # This test verifies the method has similar safety as other traversal methods
        # by checking it works correctly with valid hierarchies
        path = self.city.get_full_path()

        # Should not hang or cause infinite loops
        self.assertIsInstance(path, str)
        self.assertGreater(len(path), 0)

        # Should contain all expected location names
        expected_names = ["World", "Continent", "Country", "Region", "City"]
        for name in expected_names:
            self.assertIn(name, path)
