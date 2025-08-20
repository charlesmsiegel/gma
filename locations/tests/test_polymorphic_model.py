"""
Essential tests for Location polymorphic model conversion.

Tests verify that Location has been successfully converted to inherit from
PolymorphicModel while preserving all existing functionality.

Focuses on actual requirements rather than theoretical scenarios.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from polymorphic.managers import PolymorphicManager
from polymorphic.models import PolymorphicModel

from campaigns.models import Campaign
from locations.models import Location

User = get_user_model()


class LocationPolymorphicTest(TestCase):
    """Essential tests for polymorphic Location functionality."""

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
        self.assertTrue(
            issubclass(Location, PolymorphicModel),
            "Location model should inherit from PolymorphicModel",
        )

    def test_location_has_polymorphic_manager(self):
        """Test that Location uses PolymorphicManager."""
        self.assertIsInstance(
            Location.objects,
            PolymorphicManager,
            "Location.objects should be a PolymorphicManager",
        )

    def test_polymorphic_ctype_field_populated(self):
        """Test that polymorphic_ctype field is populated on creation."""
        location = Location.objects.create(
            name="Test Location",
            campaign=self.campaign,
            created_by=self.user,
        )

        self.assertIsNotNone(
            location.polymorphic_ctype,
            "Location should have polymorphic_ctype field populated",
        )

    def test_polymorphic_identity_methods_work(self):
        """Test that polymorphic identity methods work correctly."""
        location = Location.objects.create(
            name="Identity Test",
            campaign=self.campaign,
            created_by=self.user,
        )

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

    def test_existing_functionality_preserved(self):
        """Test that all existing Location functionality still works."""
        # Create hierarchy for testing
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

        # Test hierarchy methods still work
        self.assertEqual(child.get_root(), parent)
        self.assertEqual(child.get_depth(), 1)
        self.assertEqual(parent.get_depth(), 0)
        self.assertTrue(child.is_descendant_of(parent))
        self.assertIn(child, parent.get_descendants())
        self.assertIn(parent, child.get_ancestors())

        # Test permission methods still work
        self.assertTrue(parent.can_view(self.user))
        self.assertTrue(parent.can_edit(self.user))
        self.assertTrue(parent.can_delete(self.user))
        self.assertTrue(Location.can_create(self.user, self.campaign))

    def test_polymorphic_queries_work(self):
        """Test that polymorphic queries work correctly."""
        location = Location.objects.create(
            name="Query Test",
            campaign=self.campaign,
            created_by=self.user,
        )

        # Basic polymorphic query should work
        retrieved = Location.objects.get(id=location.id)
        self.assertEqual(type(retrieved), Location)
        self.assertIsNotNone(retrieved.polymorphic_ctype)

        # Filtering should preserve polymorphic types
        filtered = Location.objects.filter(campaign=self.campaign)
        self.assertIn(location, filtered)
        for loc in filtered:
            self.assertIsInstance(loc, Location)

    def test_backward_compatibility_maintained(self):
        """Test that existing code patterns continue to work."""
        # Standard creation should work
        location = Location.objects.create(
            name="Compatibility Test",
            campaign=self.campaign,
            created_by=self.user,
        )

        # Standard queries should work
        retrieved = Location.objects.get(id=location.id)
        self.assertEqual(retrieved, location)

        # Standard updates should work
        location.description = "Updated description"
        location.save()
        location.refresh_from_db()
        self.assertEqual(location.description, "Updated description")

        # String representation should be unchanged
        self.assertEqual(str(location), "Compatibility Test")
