"""
Tests for the bulk_move_to_parent admin action.
"""

from unittest.mock import Mock

from django.contrib.admin import AdminSite
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from campaigns.models import Campaign
from locations.admin import LocationAdmin
from locations.models import Location

User = get_user_model()


class BulkMoveAdminActionTest(TestCase):
    """Test the bulk_move_to_parent admin action functionality."""

    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        self.site = AdminSite()
        self.admin = LocationAdmin(Location, self.site)

        # Mock message_user for tests
        self.admin.message_user = Mock()

        # Create users
        self.superuser = User.objects.create_superuser(
            username="superuser", email="superuser@test.com", password="testpass123"
        )

        # Create test campaign
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.superuser,
            game_system="mage",
        )

        # Create test locations
        self.parent = Location.objects.create(
            name="Parent Location",
            campaign=self.campaign,
            created_by=self.superuser,
        )

        self.new_parent = Location.objects.create(
            name="New Parent Location",
            campaign=self.campaign,
            created_by=self.superuser,
        )

        self.child1 = Location.objects.create(
            name="Child Location 1",
            campaign=self.campaign,
            parent=self.parent,
            created_by=self.superuser,
        )

        self.child2 = Location.objects.create(
            name="Child Location 2",
            campaign=self.campaign,
            parent=self.parent,
            created_by=self.superuser,
        )

        self.orphan = Location.objects.create(
            name="Orphan Location",
            campaign=self.campaign,
            created_by=self.superuser,
        )

    def test_bulk_move_shows_selection_form(self):
        """Test that bulk action shows parent selection form when no parent specified."""
        request = self.factory.post(
            "/admin/locations/location/",
            {
                "action": "bulk_move_to_parent",
                "_selected_action": [self.child1.pk, self.child2.pk],
            },
        )
        request.user = self.superuser

        # Create queryset
        queryset = Location.objects.filter(pk__in=[self.child1.pk, self.child2.pk])

        # Call the bulk action
        response = self.admin.bulk_move_to_parent(request, queryset)

        # Should return a rendered template response
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Select new parent", response.content)

    def test_bulk_move_to_new_parent(self):
        """Test moving locations to a new parent."""
        request = self.factory.post(
            "/admin/locations/location/",
            {
                "action": "bulk_move_to_parent",
                "_selected_action": [self.child1.pk, self.child2.pk],
                "new_parent_id": str(self.new_parent.pk),
            },
        )
        request.user = self.superuser

        # Create queryset
        queryset = Location.objects.filter(pk__in=[self.child1.pk, self.child2.pk])

        # Call the bulk action
        response = self.admin.bulk_move_to_parent(request, queryset)

        # Should redirect back to changelist
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/locations/location/", response.url)

        # Check that locations were moved
        self.child1.refresh_from_db()
        self.child2.refresh_from_db()

        self.assertEqual(self.child1.parent, self.new_parent)
        self.assertEqual(self.child2.parent, self.new_parent)

    def test_bulk_move_to_root_level(self):
        """Test moving locations to root level (no parent)."""
        request = self.factory.post(
            "/admin/locations/location/",
            {
                "action": "bulk_move_to_parent",
                "_selected_action": [self.child1.pk, self.child2.pk],
                "new_parent_id": "",  # Empty string means root level
            },
        )
        request.user = self.superuser

        # Create queryset
        queryset = Location.objects.filter(pk__in=[self.child1.pk, self.child2.pk])

        # Call the bulk action
        response = self.admin.bulk_move_to_parent(request, queryset)

        # Should redirect back to changelist
        self.assertEqual(response.status_code, 302)

        # Check that locations were moved to root
        self.child1.refresh_from_db()
        self.child2.refresh_from_db()

        self.assertIsNone(self.child1.parent)
        self.assertIsNone(self.child2.parent)

    def test_bulk_move_prevents_circular_references(self):
        """Test that bulk move prevents circular references."""
        # Try to move parent to be a child of its own child
        request = self.factory.post(
            "/admin/locations/location/",
            {
                "action": "bulk_move_to_parent",
                "_selected_action": [self.parent.pk],
                "new_parent_id": str(self.child1.pk),
            },
        )
        request.user = self.superuser

        # Create queryset
        queryset = Location.objects.filter(pk=self.parent.pk)

        # Call the bulk action
        response = self.admin.bulk_move_to_parent(request, queryset)

        # Should redirect back with warning message
        self.assertEqual(response.status_code, 302)

        # Check that parent wasn't moved
        self.parent.refresh_from_db()
        self.assertIsNone(self.parent.parent)  # Should still be at root level

    def test_bulk_move_cross_campaign_prevention(self):
        """Test that bulk move prevents cross-campaign parent assignment."""
        # Create another campaign and location
        other_campaign = Campaign.objects.create(
            name="Other Campaign",
            owner=self.superuser,
            game_system="generic",
        )

        other_location = Location.objects.create(
            name="Other Campaign Location",
            campaign=other_campaign,
            created_by=self.superuser,
        )

        # Try to move locations from first campaign to parent in second campaign
        request = self.factory.post(
            "/admin/locations/location/",
            {
                "action": "bulk_move_to_parent",
                "_selected_action": [self.child1.pk, self.child2.pk],
                "new_parent_id": str(other_location.pk),
            },
        )
        request.user = self.superuser

        # Create queryset
        queryset = Location.objects.filter(pk__in=[self.child1.pk, self.child2.pk])

        # Call the bulk action
        response = self.admin.bulk_move_to_parent(request, queryset)

        # Should redirect back with warning message
        self.assertEqual(response.status_code, 302)

        # Check that locations weren't moved
        self.child1.refresh_from_db()
        self.child2.refresh_from_db()

        self.assertEqual(
            self.child1.parent, self.parent
        )  # Should still be original parent
        self.assertEqual(self.child2.parent, self.parent)

    def test_bulk_move_nonexistent_parent_error(self):
        """Test that bulk move handles nonexistent parent gracefully."""
        request = self.factory.post(
            "/admin/locations/location/",
            {
                "action": "bulk_move_to_parent",
                "_selected_action": [self.child1.pk],
                "new_parent_id": "99999",  # Nonexistent ID
            },
        )
        request.user = self.superuser

        # Create queryset
        queryset = Location.objects.filter(pk=self.child1.pk)

        # Call the bulk action
        response = self.admin.bulk_move_to_parent(request, queryset)

        # Should return None (handled by message_user)
        self.assertIsNone(response)

        # Should have called message_user with error
        self.admin.message_user.assert_called_once()

        # Check that location wasn't moved
        self.child1.refresh_from_db()
        self.assertEqual(self.child1.parent, self.parent)

    def test_bulk_move_parent_choices_excludes_selected_locations(self):
        """Test that parent selection form excludes selected locations."""
        request = self.factory.post(
            "/admin/locations/location/",
            {
                "action": "bulk_move_to_parent",
                "_selected_action": [self.child1.pk, self.parent.pk],
            },
        )
        request.user = self.superuser

        # Create queryset
        queryset = Location.objects.filter(pk__in=[self.child1.pk, self.parent.pk])

        # Call the bulk action
        response = self.admin.bulk_move_to_parent(request, queryset)

        # Should return a rendered template response
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 200)

        # Check that selected locations are not in parent choices
        content = response.content.decode()
        self.assertNotIn(f'value="{self.child1.pk}"', content)
        self.assertNotIn(f'value="{self.parent.pk}"', content)

        # But other locations should be available
        self.assertIn(f'value="{self.new_parent.pk}"', content)
        self.assertIn(f'value="{self.orphan.pk}"', content)

    def test_bulk_move_mixed_campaign_parent_filtering(self):
        """Test parent choices when moving locations from different campaigns."""
        # Create another campaign and location
        other_campaign = Campaign.objects.create(
            name="Other Campaign",
            owner=self.superuser,
            game_system="generic",
        )

        other_location = Location.objects.create(
            name="Other Campaign Location",
            campaign=other_campaign,
            created_by=self.superuser,
        )

        # Try to move locations from both campaigns
        request = self.factory.post(
            "/admin/locations/location/",
            {
                "action": "bulk_move_to_parent",
                "_selected_action": [self.child1.pk, other_location.pk],
            },
        )
        request.user = self.superuser

        # Create queryset
        queryset = Location.objects.filter(pk__in=[self.child1.pk, other_location.pk])

        # Call the bulk action
        response = self.admin.bulk_move_to_parent(request, queryset)

        # Should show form with locations from both campaigns as potential parents
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 200)

        content = response.content.decode()
        # Should include locations from both campaigns
        self.assertIn(self.campaign.name, content)
        self.assertIn(other_campaign.name, content)
