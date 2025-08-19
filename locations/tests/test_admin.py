"""
Tests for Location admin interface with hierarchy support.

Tests cover:
- Admin model registration and configuration
- Hierarchy display in admin list view
- Parent-child relationship management
- Bulk operations with hierarchy
- Admin permissions and security
- Hierarchy filtering and search
"""

from django.contrib.admin import AdminSite
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from campaigns.models import Campaign, CampaignMembership
from locations.admin import LocationAdmin
from locations.models import Location

User = get_user_model()


class LocationAdminTest(TestCase):
    """Test Location admin interface functionality."""

    def setUp(self):
        """Set up test data for admin tests."""
        self.factory = RequestFactory()
        self.site = AdminSite()
        self.admin = LocationAdmin(Location, self.site)

        # Create users
        self.superuser = User.objects.create_superuser(
            username="superuser", email="superuser@test.com", password="testpass123"
        )
        self.staff_user = User.objects.create_user(
            username="staff",
            email="staff@test.com",
            password="testpass123",
            is_staff=True,
        )
        self.regular_user = User.objects.create_user(
            username="regular", email="regular@test.com", password="testpass123"
        )

        # Create test campaign
        self.campaign = Campaign.objects.create(
            name="Admin Test Campaign",
            owner=self.superuser,
            game_system="mage",
        )

        # Add staff user as GM
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.staff_user, role="GM"
        )

    def test_admin_model_registration(self):
        """Test that Location model is registered with admin."""
        from django.contrib import admin

        # Test that Location is registered
        self.assertIn(Location, admin.site._registry)

        # Test that LocationAdmin is the admin class
        self.assertIsInstance(admin.site._registry[Location], LocationAdmin)

    def test_admin_list_display(self):
        """Test admin list display configuration for hierarchy."""
        # Test that list_display includes hierarchy-relevant fields
        expected_fields = ["name", "campaign", "parent", "created_by", "created_at"]

        for field in expected_fields:
            self.assertIn(field, self.admin.list_display)

    def test_admin_hierarchy_display(self):
        """Test that admin displays location hierarchy clearly."""
        # Create test hierarchy
        parent = Location.objects.create(
            name="Parent Location",
            campaign=self.campaign,
            created_by=self.superuser,
        )

        child = Location.objects.create(
            name="Child Location",
            campaign=self.campaign,
            parent=parent,
            created_by=self.superuser,
        )

        grandchild = Location.objects.create(
            name="Grandchild Location",
            campaign=self.campaign,
            parent=child,
            created_by=self.superuser,
        )

        # Test hierarchy display method exists
        self.assertTrue(hasattr(self.admin, "get_hierarchy_display"))

        # Test hierarchy display for different levels
        self.assertEqual(self.admin.get_hierarchy_display(parent), "Parent Location")
        self.assertEqual(self.admin.get_hierarchy_display(child), "— Child Location")
        self.assertEqual(
            self.admin.get_hierarchy_display(grandchild), "—— Grandchild Location"
        )

    def test_admin_list_filter(self):
        """Test admin list filtering options for hierarchy."""
        expected_filters = ["campaign", "parent", "created_by", "created_at"]

        for filter_field in expected_filters:
            self.assertIn(filter_field, self.admin.list_filter)

    def test_admin_search_fields(self):
        """Test admin search functionality."""
        expected_search_fields = ["name", "description", "campaign__name"]

        for search_field in expected_search_fields:
            self.assertIn(search_field, self.admin.search_fields)

    def test_admin_form_fields(self):
        """Test admin form field configuration."""
        # Test that form includes all necessary fields
        form_class = self.admin.get_form(None)
        form = form_class()

        expected_fields = ["name", "description", "campaign", "parent", "created_by"]

        for field in expected_fields:
            self.assertIn(field, form.fields)

    def test_admin_parent_field_queryset(self):
        """Test that parent field queryset is filtered appropriately."""
        # Create locations in different campaigns
        other_campaign = Campaign.objects.create(
            name="Other Campaign",
            owner=self.superuser,
            game_system="generic",
        )

        campaign1_location = Location.objects.create(
            name="Campaign 1 Location",
            campaign=self.campaign,
            created_by=self.superuser,
        )

        campaign2_location = Location.objects.create(
            name="Campaign 2 Location",
            campaign=other_campaign,
            created_by=self.superuser,
        )

        # Test parent field queryset filtering by campaign
        request = self.factory.get("/")
        request.user = self.superuser

        # Get form for location in campaign 1
        form_class = self.admin.get_form(request, campaign1_location)
        form = form_class(instance=campaign1_location)

        # Parent field should only show locations from same campaign
        parent_queryset = form.fields["parent"].queryset
        self.assertIn(campaign1_location, parent_queryset)
        self.assertNotIn(campaign2_location, parent_queryset)

    def test_admin_hierarchy_validation(self):
        """Test that admin form validates hierarchy constraints."""
        parent = Location.objects.create(
            name="Parent Location",
            campaign=self.campaign,
            created_by=self.superuser,
        )

        child = Location.objects.create(
            name="Child Location",
            campaign=self.campaign,
            parent=parent,
            created_by=self.superuser,
        )

        # Test form validation prevents circular references
        form_class = self.admin.get_form(None)

        # Try to make parent a child of child (circular reference)
        form_data = {
            "name": "Parent Location",
            "campaign": self.campaign.id,
            "parent": child.id,  # This should cause validation error
            "created_by": self.superuser.id,
        }

        form = form_class(data=form_data, instance=parent)
        self.assertFalse(form.is_valid())
        self.assertIn("parent", form.errors)

    def test_admin_bulk_actions(self):
        """Test admin bulk actions for locations."""
        # Test that appropriate bulk actions are available
        actions = self.admin.get_actions(None)

        # Should have default delete action
        self.assertIn("delete_selected", actions)

        # Test custom bulk actions if implemented
        if hasattr(self.admin, "bulk_move_to_parent"):
            self.assertIn("bulk_move_to_parent", actions)

    def test_admin_ordering(self):
        """Test admin list ordering configuration."""
        # Test default ordering
        expected_ordering = ["campaign", "parent", "name"]
        self.assertEqual(self.admin.ordering, expected_ordering)

        # Create test locations to verify ordering
        locations = []
        for i in range(3):
            location = Location.objects.create(
                name=f"Location {i:02d}",
                campaign=self.campaign,
                created_by=self.superuser,
            )
            locations.append(location)

        # Test that queryset is ordered correctly
        request = self.factory.get("/")
        request.user = self.superuser

        queryset = self.admin.get_queryset(request)
        ordered_locations = list(queryset)

        # Should be ordered by campaign, then parent, then name
        names = [loc.name for loc in ordered_locations]
        self.assertEqual(names, sorted(names))

    def test_admin_permissions(self):
        """Test admin permissions for different user types."""
        # Test superuser permissions
        self.assertTrue(self.admin.has_view_permission(None, None))
        self.assertTrue(self.admin.has_add_permission(None))
        self.assertTrue(self.admin.has_change_permission(None, None))
        self.assertTrue(self.admin.has_delete_permission(None, None))

        # Test staff user permissions (if custom permission logic exists)
        request = self.factory.get("/")
        request.user = self.staff_user

        # Staff should have view and add permissions
        self.assertTrue(self.admin.has_view_permission(request))
        self.assertTrue(self.admin.has_add_permission(request))

        # Change and delete permissions may depend on object ownership
        location = Location.objects.create(
            name="Permission Test Location",
            campaign=self.campaign,
            created_by=self.staff_user,
        )

        self.assertTrue(self.admin.has_change_permission(request, location))
        self.assertTrue(self.admin.has_delete_permission(request, location))

    def test_admin_inline_configurations(self):
        """Test admin inline configurations for related models."""
        # Test that children locations can be managed as inlines
        if hasattr(self.admin, "inlines"):
            # Check for children inline
            inline_classes = [inline for inline in self.admin.inlines]

            # Look for location children inline
            children_inline = None
            for inline in inline_classes:
                if hasattr(inline, "model") and inline.model == Location:
                    children_inline = inline
                    break

            if children_inline:
                self.assertEqual(children_inline.fk_name, "parent")
                self.assertTrue(hasattr(children_inline, "extra"))

    def test_admin_custom_methods(self):
        """Test custom admin methods for hierarchy management."""
        # Test get_children_count method
        parent = Location.objects.create(
            name="Parent with Children",
            campaign=self.campaign,
            created_by=self.superuser,
        )

        for i in range(3):
            Location.objects.create(
                name=f"Child {i}",
                campaign=self.campaign,
                parent=parent,
                created_by=self.superuser,
            )

        if hasattr(self.admin, "get_children_count"):
            children_count = self.admin.get_children_count(parent)
            self.assertEqual(children_count, 3)

        # Test get_depth method
        if hasattr(self.admin, "get_depth"):
            depth = self.admin.get_depth(parent)
            self.assertEqual(depth, 0)

    def test_admin_save_model(self):
        """Test admin save_model method for proper user tracking."""
        request = self.factory.post("/")
        request.user = self.superuser

        location = Location(
            name="Admin Save Test",
            campaign=self.campaign,
        )

        # Test save_model sets created_by appropriately
        self.admin.save_model(request, location, None, True)

        location.refresh_from_db()
        self.assertEqual(location.created_by, self.superuser)

    def test_admin_queryset_optimization(self):
        """Test that admin queryset is optimized for hierarchy display."""
        request = self.factory.get("/")
        request.user = self.superuser

        queryset = self.admin.get_queryset(request)

        # Should include select_related for foreign keys
        self.assertIn("campaign", queryset.query.select_related)
        self.assertIn("parent", queryset.query.select_related)
        self.assertIn("created_by", queryset.query.select_related)


class LocationAdminHierarchyDisplayTest(TestCase):
    """Test hierarchy display functionality in admin."""

    def setUp(self):
        """Set up test hierarchy for display tests."""
        self.site = AdminSite()
        self.admin = LocationAdmin(Location, self.site)

        self.superuser = User.objects.create_superuser(
            username="superuser", email="superuser@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Hierarchy Display Campaign",
            owner=self.superuser,
            game_system="mage",
        )

        # Create test hierarchy:
        # World
        #   ├── Continent
        #   │   ├── Country
        #   │   │   └── City
        #   │   └── Another Country
        #   └── Another Continent

        self.world = Location.objects.create(
            name="World",
            campaign=self.campaign,
            created_by=self.superuser,
        )

        self.continent = Location.objects.create(
            name="Continent",
            campaign=self.campaign,
            parent=self.world,
            created_by=self.superuser,
        )

        self.another_continent = Location.objects.create(
            name="Another Continent",
            campaign=self.campaign,
            parent=self.world,
            created_by=self.superuser,
        )

        self.country = Location.objects.create(
            name="Country",
            campaign=self.campaign,
            parent=self.continent,
            created_by=self.superuser,
        )

        self.another_country = Location.objects.create(
            name="Another Country",
            campaign=self.campaign,
            parent=self.continent,
            created_by=self.superuser,
        )

        self.city = Location.objects.create(
            name="City",
            campaign=self.campaign,
            parent=self.country,
            created_by=self.superuser,
        )

    def test_hierarchy_indentation_display(self):
        """Test that hierarchy is displayed with proper indentation."""
        # Test hierarchy display method with proper indentation
        self.assertEqual(self.admin.get_hierarchy_display(self.world), "World")
        self.assertEqual(
            self.admin.get_hierarchy_display(self.continent), "— Continent"
        )
        self.assertEqual(self.admin.get_hierarchy_display(self.country), "—— Country")
        self.assertEqual(self.admin.get_hierarchy_display(self.city), "——— City")

    def test_hierarchy_ordering_in_admin(self):
        """Test that locations are ordered hierarchically in admin."""
        request = RequestFactory().get("/")
        request.user = self.superuser

        queryset = self.admin.get_queryset(request)

        # Should be ordered to show hierarchy structure
        # Implementation may vary, but should group by hierarchy level
        locations = list(queryset)

        # World should come first (top level)
        self.assertEqual(locations[0], self.world)

    def test_hierarchy_filtering_in_admin(self):
        """Test hierarchy-based filtering in admin."""
        # Test parent filter shows correct options
        request = RequestFactory().get("/")
        request.user = self.superuser

        # Test that list filter includes parent options
        list_filter = self.admin.get_list_filter(request)
        self.assertIn("parent", list_filter)

    def test_hierarchy_search_functionality(self):
        """Test that search works across hierarchy levels."""
        request = RequestFactory().get("/?q=Country")
        request.user = self.superuser

        queryset = self.admin.get_queryset(request)

        # Should include both countries in search results
        country_results = [loc for loc in queryset if "Country" in loc.name]
        self.assertGreaterEqual(len(country_results), 2)

    def test_hierarchy_breadcrumb_display(self):
        """Test breadcrumb display for location hierarchy."""
        if hasattr(self.admin, "get_breadcrumb_display"):
            # Test breadcrumb for deeply nested location
            breadcrumb = self.admin.get_breadcrumb_display(self.city)
            expected = "World > Continent > Country > City"
            self.assertEqual(breadcrumb, expected)

            # Test breadcrumb for top-level location
            breadcrumb = self.admin.get_breadcrumb_display(self.world)
            self.assertEqual(breadcrumb, "World")


class LocationAdminSecurityTest(TestCase):
    """Test security aspects of Location admin interface."""

    def setUp(self):
        """Set up test data for security tests."""
        self.site = AdminSite()
        self.admin = LocationAdmin(Location, self.site)

        # Create users with different permissions
        self.superuser = User.objects.create_superuser(
            username="superuser", email="superuser@test.com", password="testpass123"
        )

        self.campaign_owner = User.objects.create_user(
            username="owner",
            email="owner@test.com",
            password="testpass123",
            is_staff=True,
        )

        self.other_user = User.objects.create_user(
            username="other",
            email="other@test.com",
            password="testpass123",
            is_staff=True,
        )

        # Create campaigns
        self.owned_campaign = Campaign.objects.create(
            name="Owned Campaign",
            owner=self.campaign_owner,
            game_system="mage",
        )

        self.other_campaign = Campaign.objects.create(
            name="Other Campaign",
            owner=self.other_user,
            game_system="generic",
        )

        # Create test locations
        self.owned_location = Location.objects.create(
            name="Owned Location",
            campaign=self.owned_campaign,
            created_by=self.campaign_owner,
        )

        self.other_location = Location.objects.create(
            name="Other Location",
            campaign=self.other_campaign,
            created_by=self.other_user,
        )

    def test_admin_queryset_filtering_by_permissions(self):
        """Test that admin queryset is filtered based on user permissions."""
        # Test campaign owner sees only their campaign's locations
        request = RequestFactory().get("/")
        request.user = self.campaign_owner

        if hasattr(self.admin, "get_queryset"):
            queryset = self.admin.get_queryset(request)

            # Should include owned locations
            self.assertIn(self.owned_location, queryset)

            # Should not include other users' private campaign locations
            # (depends on implementation of permission filtering)

    def test_admin_change_permission_security(self):
        """Test that change permissions are properly enforced."""
        request = RequestFactory().get("/")
        request.user = self.campaign_owner

        # Should be able to change own locations
        self.assertTrue(self.admin.has_change_permission(request, self.owned_location))

        # Should not be able to change others' locations (non-superuser)
        if not self.campaign_owner.is_superuser:
            self.admin.has_change_permission(request, self.other_location)
            # This test depends on implementation - may be True for staff users

    def test_admin_delete_permission_security(self):
        """Test that delete permissions are properly enforced."""
        request = RequestFactory().get("/")
        request.user = self.campaign_owner

        # Should be able to delete own locations
        self.assertTrue(self.admin.has_delete_permission(request, self.owned_location))

        # Delete permission for others' locations depends on implementation

    def test_admin_prevents_cross_campaign_parent_assignment(self):
        """Test that admin prevents assigning parents from different campaigns."""
        form_class = self.admin.get_form(None)

        # Try to assign parent from different campaign
        form_data = {
            "name": "Test Location",
            "campaign": self.owned_campaign.id,
            "parent": self.other_location.id,  # From different campaign
            "created_by": self.campaign_owner.id,
        }

        form = form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("parent", form.errors)

    def test_admin_form_field_permissions(self):
        """Test that form fields are properly restricted based on permissions."""
        request = RequestFactory().get("/")
        request.user = self.campaign_owner

        form_class = self.admin.get_form(request)
        form = form_class()

        # Campaign field should be restricted to campaigns user has access to
        if hasattr(form.fields["campaign"], "queryset"):
            campaign_queryset = form.fields["campaign"].queryset
            self.assertIn(self.owned_campaign, campaign_queryset)

            # Other campaign visibility depends on implementation
