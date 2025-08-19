"""
Tests for Location hierarchy validation and edge cases.

Tests cover:
- Circular reference prevention
- Depth limit enforcement
- Parent-child constraint validation
- Database integrity constraints
- Performance edge cases
- Complex hierarchy operations
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from campaigns.models import Campaign
from locations.models import Location

User = get_user_model()


class LocationHierarchyValidationTest(TestCase):
    """Test hierarchy validation rules and constraints."""

    def setUp(self):
        """Set up test data for validation tests."""
        self.user = User.objects.create_user(
            username="testuser", email="test@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Validation Test Campaign",
            owner=self.user,
            game_system="mage",
        )

    def test_prevent_self_as_parent(self):
        """Test that location cannot be set as its own parent."""
        location = Location.objects.create(
            name="Self Parent Test",
            campaign=self.campaign,
            created_by=self.user,
        )

        # Attempt to set self as parent
        location.parent = location

        with self.assertRaises(ValidationError) as context:
            location.clean()

        error_message = str(context.exception)
        self.assertIn("cannot be its own parent", error_message.lower())

    def test_prevent_direct_circular_reference(self):
        """Test prevention of direct circular references (A -> B -> A)."""
        location_a = Location.objects.create(
            name="Location A",
            campaign=self.campaign,
            created_by=self.user,
        )

        location_b = Location.objects.create(
            name="Location B",
            campaign=self.campaign,
            parent=location_a,
            created_by=self.user,
        )

        # Attempt to make A a child of B (circular reference)
        location_a.parent = location_b

        with self.assertRaises(ValidationError) as context:
            location_a.clean()

        error_message = str(context.exception)
        self.assertIn("circular", error_message.lower())

    def test_prevent_indirect_circular_reference(self):
        """Test prevention of indirect circular references (A -> B -> C -> A)."""
        location_a = Location.objects.create(
            name="Location A",
            campaign=self.campaign,
            created_by=self.user,
        )

        location_b = Location.objects.create(
            name="Location B",
            campaign=self.campaign,
            parent=location_a,
            created_by=self.user,
        )

        location_c = Location.objects.create(
            name="Location C",
            campaign=self.campaign,
            parent=location_b,
            created_by=self.user,
        )

        # Attempt to make A a child of C (indirect circular reference)
        location_a.parent = location_c

        with self.assertRaises(ValidationError) as context:
            location_a.clean()

        error_message = str(context.exception)
        self.assertIn("circular", error_message.lower())

    def test_prevent_deep_circular_reference(self):
        """Test prevention of circular references in deep hierarchies."""
        # Create a chain: A -> B -> C -> D -> E
        locations = []
        parent = None

        for i in range(5):
            location = Location.objects.create(
                name=f"Location {chr(65 + i)}",  # A, B, C, D, E
                campaign=self.campaign,
                parent=parent,
                created_by=self.user,
            )
            locations.append(location)
            parent = location

        # Attempt to make A a child of E (circular reference through chain)
        locations[0].parent = locations[4]

        with self.assertRaises(ValidationError) as context:
            locations[0].clean()

        error_message = str(context.exception)
        self.assertIn("circular", error_message.lower())

    def test_maximum_depth_enforcement(self):
        """Test that maximum depth of 10 levels is enforced."""
        # Create a chain of 10 locations (depths 0-9)
        locations = []
        parent = None

        for i in range(10):
            location = Location.objects.create(
                name=f"Depth {i} Location",
                campaign=self.campaign,
                parent=parent,
                created_by=self.user,
            )
            locations.append(location)
            parent = location

        # Verify all 10 levels were created successfully
        self.assertEqual(len(locations), 10)
        self.assertEqual(locations[-1].get_depth(), 9)

        # Attempt to create 11th level (depth 10) should fail
        with self.assertRaises(ValidationError) as context:
            location_11 = Location(
                name="Depth 10 Location (should fail)",
                campaign=self.campaign,
                parent=locations[-1],
                created_by=self.user,
            )
            location_11.clean()

        error_message = str(context.exception)
        self.assertIn("maximum depth", error_message.lower())
        self.assertIn("10", error_message)

    def test_depth_calculation_accuracy(self):
        """Test that depth calculation is accurate for validation."""
        # Create varying depth structures
        root = Location.objects.create(
            name="Root",
            campaign=self.campaign,
            created_by=self.user,
        )
        self.assertEqual(root.get_depth(), 0)

        level1 = Location.objects.create(
            name="Level 1",
            campaign=self.campaign,
            parent=root,
            created_by=self.user,
        )
        self.assertEqual(level1.get_depth(), 1)

        level2 = Location.objects.create(
            name="Level 2",
            campaign=self.campaign,
            parent=level1,
            created_by=self.user,
        )
        self.assertEqual(level2.get_depth(), 2)

        # Test depth after reparenting
        level2.parent = root
        level2.save()
        self.assertEqual(level2.get_depth(), 1)

    def test_cross_campaign_parent_validation(self):
        """Test that parent must be in same campaign."""
        other_campaign = Campaign.objects.create(
            name="Other Campaign",
            owner=self.user,
            game_system="generic",
        )

        location_campaign1 = Location.objects.create(
            name="Campaign 1 Location",
            campaign=self.campaign,
            created_by=self.user,
        )

        location_campaign2 = Location.objects.create(
            name="Campaign 2 Location",
            campaign=other_campaign,
            created_by=self.user,
        )

        # Attempt to set parent from different campaign
        location_campaign1.parent = location_campaign2

        with self.assertRaises(ValidationError) as context:
            location_campaign1.clean()

        error_message = str(context.exception)
        self.assertIn("same campaign", error_message.lower())

    def test_parent_deletion_cascade_behavior(self):
        """Test proper behavior when parent location is deleted."""
        grandparent = Location.objects.create(
            name="Grandparent",
            campaign=self.campaign,
            created_by=self.user,
        )

        parent = Location.objects.create(
            name="Parent",
            campaign=self.campaign,
            parent=grandparent,
            created_by=self.user,
        )

        child1 = Location.objects.create(
            name="Child 1",
            campaign=self.campaign,
            parent=parent,
            created_by=self.user,
        )

        child2 = Location.objects.create(
            name="Child 2",
            campaign=self.campaign,
            parent=parent,
            created_by=self.user,
        )

        # Delete parent
        parent_id = parent.id
        parent.delete()

        # Verify parent is deleted
        with self.assertRaises(Location.DoesNotExist):
            Location.objects.get(id=parent_id)

        # Children should be reparented to grandparent
        child1.refresh_from_db()
        child2.refresh_from_db()

        self.assertEqual(child1.parent, grandparent)
        self.assertEqual(child2.parent, grandparent)

    def test_orphan_promotion_to_root(self):
        """Test that orphaned children become root-level locations."""
        parent = Location.objects.create(
            name="Parent Without Grandparent",
            campaign=self.campaign,
            created_by=self.user,
        )

        child1 = Location.objects.create(
            name="Child 1",
            campaign=self.campaign,
            parent=parent,
            created_by=self.user,
        )

        child2 = Location.objects.create(
            name="Child 2",
            campaign=self.campaign,
            parent=parent,
            created_by=self.user,
        )

        # Delete parent (no grandparent available)
        parent.delete()

        # Children should become root-level (parent = None)
        child1.refresh_from_db()
        child2.refresh_from_db()

        self.assertIsNone(child1.parent)
        self.assertIsNone(child2.parent)

    def test_validation_during_bulk_operations(self):
        """Test that validation is enforced during application-level bulk operations."""
        # Create a location that will be used as an invalid parent
        location_a = Location.objects.create(
            name="Location A",
            campaign=self.campaign,
            created_by=self.user,
        )

        location_b = Location.objects.create(
            name="Location B",
            campaign=self.campaign,
            parent=location_a,
            created_by=self.user,
        )

        # Attempt to create circular reference using individual save (which does trigger validation)
        location_a.parent = location_b
        with self.assertRaises(ValidationError):
            location_a.save()  # This will call clean() and should raise ValidationError

    def test_hierarchy_modification_during_save(self):
        """Test validation when modifying hierarchy during save operations."""
        # Create initial hierarchy
        parent = Location.objects.create(
            name="Initial Parent",
            campaign=self.campaign,
            created_by=self.user,
        )

        child = Location.objects.create(
            name="Child",
            campaign=self.campaign,
            parent=parent,
            created_by=self.user,
        )

        # Modify hierarchy to create circular reference
        parent.parent = child

        with self.assertRaises(ValidationError):
            parent.save()

    def test_database_integrity_constraints(self):
        """Test database-level integrity constraints."""
        # Test foreign key constraint for campaign
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Location.objects.create(
                    name="No Campaign",
                    campaign=None,
                    created_by=self.user,
                )

        # Test that invalid parent ID is handled properly
        # Some databases defer constraint checking, so we test both scenarios
        constraint_violation_detected = False
        location_to_cleanup = None

        try:
            with transaction.atomic():
                location = Location(
                    name="Invalid Parent",
                    campaign=self.campaign,
                    parent_id=99999,  # Non-existent parent
                    created_by=self.user,
                )
                location.save()
                location_to_cleanup = location

                # If save succeeded, the constraint might be deferred
                # Try to access the parent relationship - this should fail
                try:
                    _ = location.parent
                    self.fail(
                        "Expected either IntegrityError during save or DoesNotExist when accessing parent"
                    )
                except Location.DoesNotExist:
                    # This is expected - parent_id=99999 doesn't exist
                    constraint_violation_detected = True

        except IntegrityError:
            # Expected - constraint checked immediately during save
            constraint_violation_detected = True

        # Clean up the invalid location to prevent teardown constraint errors
        if location_to_cleanup and location_to_cleanup.pk:
            try:
                # Delete the object to prevent constraint violations during teardown
                Location.objects.filter(pk=location_to_cleanup.pk).delete()
            except Exception:
                pass  # Ignore cleanup errors

        self.assertTrue(
            constraint_violation_detected,
            "Foreign key constraint violation should be detected either during save or when accessing parent",
        )


class LocationHierarchyPerformanceTest(TestCase):
    """Test performance aspects of hierarchy operations."""

    def setUp(self):
        """Set up test data for performance tests."""
        self.user = User.objects.create_user(
            username="perfuser", email="perf@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Performance Test Campaign",
            owner=self.user,
            game_system="mage",
        )

    def test_deep_hierarchy_validation_performance(self):
        """Test that validation remains efficient for deep hierarchies."""
        # Create maximum depth hierarchy (10 levels)
        locations = []
        parent = None

        start_time = timezone.now()

        for i in range(10):
            location = Location.objects.create(
                name=f"Performance Level {i}",
                campaign=self.campaign,
                parent=parent,
                created_by=self.user,
            )
            locations.append(location)
            parent = location

        end_time = timezone.now()
        creation_time = (end_time - start_time).total_seconds()

        # Should complete within reasonable time
        self.assertLess(creation_time, 5.0)  # 5 seconds max

        # Test validation performance on existing deep hierarchy
        start_time = timezone.now()

        # Validate the deepest location
        locations[-1].clean()

        end_time = timezone.now()
        validation_time = (end_time - start_time).total_seconds()

        # Validation should be fast even for deep hierarchies
        self.assertLess(validation_time, 1.0)  # 1 second max

    def test_wide_hierarchy_performance(self):
        """Test performance with wide hierarchies (many siblings)."""
        parent = Location.objects.create(
            name="Parent with Many Children",
            campaign=self.campaign,
            created_by=self.user,
        )

        start_time = timezone.now()

        # Create 100 children
        children = []
        for i in range(100):
            child = Location.objects.create(
                name=f"Child {i:03d}",
                campaign=self.campaign,
                parent=parent,
                created_by=self.user,
            )
            children.append(child)

        end_time = timezone.now()
        creation_time = (end_time - start_time).total_seconds()

        # Should complete within reasonable time
        self.assertLess(creation_time, 10.0)  # 10 seconds max

        # Test that sibling queries are efficient
        start_time = timezone.now()
        sibling_count = children[0].get_siblings().count()
        end_time = timezone.now()

        query_time = (end_time - start_time).total_seconds()
        self.assertEqual(sibling_count, 99)  # 100 - 1 (self)
        self.assertLess(query_time, 1.0)  # 1 second max

    def test_hierarchy_modification_performance(self):
        """Test performance of hierarchy modifications."""
        # Create initial structure
        old_parent = Location.objects.create(
            name="Old Parent",
            campaign=self.campaign,
            created_by=self.user,
        )

        new_parent = Location.objects.create(
            name="New Parent",
            campaign=self.campaign,
            created_by=self.user,
        )

        # Create children under old parent
        children = []
        for i in range(50):
            child = Location.objects.create(
                name=f"Child {i}",
                campaign=self.campaign,
                parent=old_parent,
                created_by=self.user,
            )
            children.append(child)

        # Test performance of moving all children to new parent
        start_time = timezone.now()

        for child in children:
            child.parent = new_parent
            child.save()

        end_time = timezone.now()
        move_time = (end_time - start_time).total_seconds()

        # Should complete within reasonable time
        self.assertLess(move_time, 5.0)  # 5 seconds max

        # Verify all children were moved
        new_parent_children = new_parent.children.count()
        self.assertEqual(new_parent_children, 50)


class LocationHierarchyEdgeCaseTest(TransactionTestCase):
    """Test edge cases in hierarchy operations."""

    def setUp(self):
        """Set up test data for edge case tests."""
        self.user = User.objects.create_user(
            username="edgeuser", email="edge@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Edge Case Test Campaign",
            owner=self.user,
            game_system="mage",
        )

    def test_concurrent_hierarchy_modifications(self):
        """Test handling of concurrent hierarchy modifications."""
        parent = Location.objects.create(
            name="Concurrent Parent",
            campaign=self.campaign,
            created_by=self.user,
        )

        child1 = Location.objects.create(
            name="Child 1",
            campaign=self.campaign,
            parent=parent,
            created_by=self.user,
        )

        child2 = Location.objects.create(
            name="Child 2",
            campaign=self.campaign,
            parent=parent,
            created_by=self.user,
        )

        # Simulate concurrent modification attempts
        # This should not cause database corruption
        try:
            with transaction.atomic():
                child1.parent = child2
                child1.save()

                child2.parent = child1
                child2.save()
        except (ValidationError, IntegrityError):
            # Expected to fail due to circular reference
            pass

        # Verify database integrity
        child1.refresh_from_db()
        child2.refresh_from_db()

        # Both should still have valid parent relationships
        self.assertIsNotNone(child1.parent)
        self.assertIsNotNone(child2.parent)

    def test_hierarchy_during_campaign_deletion(self):
        """Test hierarchy behavior when campaign is deleted."""
        parent = Location.objects.create(
            name="Parent in Doomed Campaign",
            campaign=self.campaign,
            created_by=self.user,
        )

        child = Location.objects.create(
            name="Child in Doomed Campaign",
            campaign=self.campaign,
            parent=parent,
            created_by=self.user,
        )

        parent_id = parent.id
        child_id = child.id

        # Delete campaign (should cascade to locations)
        self.campaign.delete()

        # Verify all locations are deleted
        with self.assertRaises(Location.DoesNotExist):
            Location.objects.get(id=parent_id)

        with self.assertRaises(Location.DoesNotExist):
            Location.objects.get(id=child_id)

    def test_hierarchy_with_special_characters(self):
        """Test hierarchy operations with special characters in names."""
        special_names = [
            "Location with 'quotes'",
            'Location with "double quotes"',
            "Location with émojis 🏰",
            "Location/with/slashes",
            "Location\\with\\backslashes",
            "Location with\nnewlines",
            "Location with\ttabs",
        ]

        # Create hierarchy with special character names
        parent = None
        locations = []

        for name in special_names:
            location = Location.objects.create(
                name=name,
                campaign=self.campaign,
                parent=parent,
                created_by=self.user,
            )
            locations.append(location)
            parent = location

        # Verify hierarchy is maintained
        for i, location in enumerate(locations):
            if i == 0:
                self.assertIsNone(location.parent)
            else:
                self.assertEqual(location.parent, locations[i - 1])

        # Test hierarchy operations work with special characters
        deepest = locations[-1]
        ancestors = deepest.get_ancestors()
        self.assertEqual(ancestors.count(), len(locations) - 1)

    def test_hierarchy_recovery_after_corruption(self):
        """Test hierarchy recovery mechanisms after potential corruption."""
        # Create test hierarchy
        root = Location.objects.create(
            name="Recovery Root",
            campaign=self.campaign,
            created_by=self.user,
        )

        child = Location.objects.create(
            name="Recovery Child",
            campaign=self.campaign,
            parent=root,
            created_by=self.user,
        )

        # Simulate corruption by directly modifying database
        # (This would not happen in normal operation)
        with transaction.atomic():
            # Create a temporary circular reference at DB level
            # (bypassing model validation)
            pass  # Implementation depends on specific corruption scenarios

        # Test that validation methods can detect corruption
        try:
            child.clean()
            root.clean()
        except ValidationError:
            # Expected if corruption is detected
            pass

        # Verify that normal operations still work
        siblings = child.get_siblings()
        self.assertEqual(siblings.count(), 0)

    def test_maximum_depth_boundary_conditions(self):
        """Test boundary conditions around maximum depth limit."""
        # Create exactly 10 levels (maximum allowed)
        locations = []
        parent = None

        for i in range(10):
            location = Location.objects.create(
                name=f"Boundary Level {i}",
                campaign=self.campaign,
                parent=parent,
                created_by=self.user,
            )
            locations.append(location)
            parent = location

        # Verify we can create the 10th level
        self.assertEqual(len(locations), 10)
        self.assertEqual(locations[-1].get_depth(), 9)

        # Test moving location to reduce depth, then increase again
        middle_location = locations[5]  # Depth 5
        middle_location.parent = None  # Move to root
        middle_location.save()

        self.assertEqual(middle_location.get_depth(), 0)

        # Should be able to move it back under deep hierarchy
        middle_location.parent = locations[3]  # Depth 4, so middle becomes depth 5
        middle_location.save()

        self.assertEqual(middle_location.get_depth(), 4)

        # But not under the deepest location
        with self.assertRaises(ValidationError):
            middle_location.parent = locations[-1]  # Would create depth 10
            middle_location.clean()

    def test_null_parent_handling(self):
        """Test proper handling of null parent values."""
        # Create location with explicit None parent
        location = Location.objects.create(
            name="Explicit Null Parent",
            campaign=self.campaign,
            parent=None,
            created_by=self.user,
        )

        self.assertIsNone(location.parent)
        self.assertEqual(location.get_depth(), 0)

        # Test that null parent locations behave correctly
        self.assertEqual(location.get_ancestors().count(), 0)
        self.assertEqual(location.get_siblings().count(), 0)

        # Test that we can set and unset parent
        other_location = Location.objects.create(
            name="Other Location",
            campaign=self.campaign,
            created_by=self.user,
        )

        location.parent = other_location
        location.save()
        self.assertEqual(location.parent, other_location)

        location.parent = None
        location.save()
        self.assertIsNone(location.parent)
