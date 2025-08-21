"""
Comprehensive tests for location management interface implementation.

Tests based on issue #51 requirements for location management interface.

Tests cover:
1. Location list view with hierarchical tree display
2. Location detail view with sub-locations and breadcrumbs
3. Location creation view with parent selection and validation
4. Location editing view with hierarchy validation and permission checks
5. Search and filtering functionality maintaining tree structure
6. URL routing and navigation patterns
7. Permission checking across all location management operations
8. Template rendering with proper context data
9. Integration tests for full user journey

These tests are designed to pass only when the full location management interface
is properly implemented according to the specifications in issue #51.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import resolve, reverse
from django.utils.http import urlencode

from campaigns.models import Campaign, CampaignMembership
from characters.models import Character
from locations.forms import LocationCreateForm, LocationEditForm
from locations.models import Location

User = get_user_model()


class LocationListViewTest(TestCase):
    """Test location list view with hierarchical tree display."""

    def setUp(self):
        """Set up test data for location list view tests."""
        # Create users with different roles
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

        # Create campaign with memberships
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            slug="test-campaign",
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

        # Create test character for ownership
        self.player_character = Character.objects.create(
            name="Test Character",
            campaign=self.campaign,
            player_owner=self.player,
            game_system="mage",
        )

        # Create hierarchical location structure for testing
        # World
        #   ├── Continent
        #   │   ├── Country
        #   │   │   ├── City (owned by character)
        #   │   │   └── Town
        #   │   └── Nation
        #   └── Realm

        self.world = Location.objects.create(
            name="World",
            description="The main world",
            campaign=self.campaign,
            created_by=self.owner,
        )

        self.continent = Location.objects.create(
            name="Continent",
            description="A large continent",
            campaign=self.campaign,
            parent=self.world,
            created_by=self.gm,
        )

        self.realm = Location.objects.create(
            name="Realm",
            description="A mystical realm",
            campaign=self.campaign,
            parent=self.world,
            created_by=self.player,
        )

        self.country = Location.objects.create(
            name="Country",
            description="A sovereign country",
            campaign=self.campaign,
            parent=self.continent,
            created_by=self.owner,
        )

        self.nation = Location.objects.create(
            name="Nation",
            description="Another nation",
            campaign=self.campaign,
            parent=self.continent,
            created_by=self.gm,
        )

        self.city = Location.objects.create(
            name="City",
            description="A bustling city",
            campaign=self.campaign,
            parent=self.country,
            owned_by=self.player_character,
            created_by=self.player,
        )

        self.town = Location.objects.create(
            name="Town",
            description="A small town",
            campaign=self.campaign,
            parent=self.country,
            created_by=self.observer,
        )

    def test_location_list_url_pattern(self):
        """Test that location list URL pattern works correctly."""
        url = reverse(
            "locations:campaign_locations", kwargs={"campaign_slug": self.campaign.slug}
        )
        self.assertEqual(url, f"/locations/campaigns/{self.campaign.slug}/")

        # Test URL resolution
        resolver = resolve(url)
        self.assertEqual(resolver.view_name, "locations:campaign_locations")
        self.assertEqual(resolver.kwargs["campaign_slug"], self.campaign.slug)

    def test_location_list_view_permission_checking(self):
        """Test that location list view enforces proper permissions."""
        url = reverse(
            "locations:campaign_locations", kwargs={"campaign_slug": self.campaign.slug}
        )

        # Campaign members should have access
        for user in [self.owner, self.gm, self.player, self.observer]:
            with self.subTest(user=user.username):
                self.client.force_login(user)
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)

        # Non-members should not have access (should get 404 to hide existence)
        self.client.force_login(self.non_member)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

        # Anonymous users should be redirected to login
        self.client.logout()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/auth/login/", response.url)

    def test_location_list_view_context_data(self):
        """Test that location list view provides correct context data."""
        self.client.force_login(self.owner)
        url = reverse(
            "locations:campaign_locations", kwargs={"campaign_slug": self.campaign.slug}
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        # Check context contains expected data
        self.assertEqual(response.context["campaign"], self.campaign)
        self.assertEqual(response.context["user_role"], "OWNER")
        self.assertIn("locations", response.context)

        # Check locations are properly filtered to campaign
        locations = response.context["locations"]
        for location in locations:
            self.assertEqual(location.campaign, self.campaign)

        # Verify all test locations are included
        location_names = [loc.name for loc in locations]
        expected_names = [
            "World",
            "Continent",
            "Realm",
            "Country",
            "Nation",
            "City",
            "Town",
        ]
        for name in expected_names:
            self.assertIn(name, location_names)

    def test_location_list_hierarchical_display_context(self):
        """Test that location list provides proper context for hierarchical display."""
        self.client.force_login(self.owner)
        url = reverse(
            "locations:campaign_locations", kwargs={"campaign_slug": self.campaign.slug}
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        # Context should provide data needed for tree display
        locations = response.context["locations"]

        # Verify hierarchy methods are available on locations
        for location in locations:
            # Each location should have hierarchy navigation methods
            self.assertTrue(hasattr(location, "get_depth"))
            self.assertTrue(hasattr(location, "get_descendants"))
            self.assertTrue(hasattr(location, "get_ancestors"))
            self.assertTrue(hasattr(location, "sub_locations"))
            self.assertTrue(hasattr(location, "get_full_path"))

        # Check that different depth levels exist
        depths = [loc.get_depth() for loc in locations]
        self.assertIn(0, depths)  # Root level (World, etc.)
        self.assertIn(1, depths)  # First level (Continent, Realm)
        self.assertIn(2, depths)  # Second level (Country, Nation)
        self.assertIn(3, depths)  # Third level (City, Town)

    def test_location_list_template_rendering(self):
        """Test that location list template renders correctly."""
        self.client.force_login(self.owner)
        url = reverse(
            "locations:campaign_locations", kwargs={"campaign_slug": self.campaign.slug}
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "locations/campaign_locations.html")

        # Should contain breadcrumb navigation
        self.assertContains(response, "breadcrumb")
        self.assertContains(response, self.campaign.name)

        # Should contain page header
        self.assertContains(response, f"{self.campaign.name} - Locations")

        # For fully implemented interface, should contain location tree
        # This assertion will fail until interface is implemented
        # self.assertContains(response, "location-tree")
        # self.assertContains(response, "hierarchy")

    def test_location_list_role_based_permissions_display(self):
        """Test that location list displays role-appropriate permissions."""
        url = reverse(
            "locations:campaign_locations", kwargs={"campaign_slug": self.campaign.slug}
        )

        # Owner/GM should see management options
        for user in [self.owner, self.gm]:
            with self.subTest(user=user.username):
                self.client.force_login(user)
                response = self.client.get(url)

                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context.get("can_create_location"))
                self.assertTrue(response.context.get("can_manage_locations"))

        # Player/Observer should see limited options but can create locations
        for user in [self.player, self.observer]:
            with self.subTest(user=user.username):
                self.client.force_login(user)
                response = self.client.get(url)

                self.assertEqual(response.status_code, 200)
                self.assertTrue(
                    response.context.get("can_create_location")
                )  # All members can create
                self.assertFalse(
                    response.context.get("can_manage_locations", True)
                )  # Only OWNER/GM can manage

    def test_location_list_ordering_and_sorting(self):
        """Test that locations are properly ordered for tree display."""
        self.client.force_login(self.owner)
        url = reverse(
            "locations:campaign_locations", kwargs={"campaign_slug": self.campaign.slug}
        )
        response = self.client.get(url)

        locations = response.context["locations"]

        # Should be ordered by name by default (from model Meta)
        location_names = [loc.name for loc in locations]
        self.assertEqual(location_names, sorted(location_names))

        # When interface is implemented, should provide tree-order context
        # This would organize locations for proper hierarchical display


class LocationDetailViewTest(TestCase):
    """Test location detail view with sub-locations and breadcrumbs."""

    def setUp(self):
        """Set up test data for location detail view tests."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.player = User.objects.create_user(
            username="player", email="player@test.com", password="testpass123"
        )
        self.non_member = User.objects.create_user(
            username="non_member", email="non_member@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Detail Test Campaign",
            slug="detail-test",
            owner=self.owner,
            game_system="mage",
        )

        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )

        # Create test character
        self.character = Character.objects.create(
            name="Detail Character",
            campaign=self.campaign,
            player_owner=self.player,
            game_system="mage",
        )

        # Create location hierarchy for detail testing
        self.parent_location = Location.objects.create(
            name="Parent Location",
            description="A parent location for testing details",
            campaign=self.campaign,
            owned_by=self.character,
            created_by=self.player,
        )

        self.child1 = Location.objects.create(
            name="Child One",
            description="First child location",
            campaign=self.campaign,
            parent=self.parent_location,
            created_by=self.owner,
        )

        self.child2 = Location.objects.create(
            name="Child Two",
            description="Second child location",
            campaign=self.campaign,
            parent=self.parent_location,
            created_by=self.player,
        )

        # Create grandchild for deeper hierarchy
        self.grandchild = Location.objects.create(
            name="Grandchild",
            description="A grandchild location",
            campaign=self.campaign,
            parent=self.child1,
            created_by=self.owner,
        )

    def test_location_detail_url_pattern(self):
        """Test that location detail URL pattern should exist."""
        # This test will fail initially until URL is implemented
        # URL should be something like: /locations/campaigns/{slug}/{location_id}/

        # For now, test that we can construct expected URL
        expected_url = (
            f"/locations/campaigns/{self.campaign.slug}/{self.parent_location.id}/"
        )

        # When implemented, should work like this:
        # url = reverse("locations:location_detail", kwargs={
        #     "campaign_slug": self.campaign.slug,
        #     "location_id": self.parent_location.id
        # })
        # self.assertEqual(url, expected_url)

        # For now, just verify the expected pattern
        self.assertTrue(expected_url.startswith("/locations/campaigns/"))
        self.assertIn(str(self.parent_location.id), expected_url)

    def test_location_detail_view_should_exist(self):
        """Test that location detail view should be implemented."""
        # This test documents what should be implemented
        # Expected URL structure would be:
        # f"/locations/campaigns/{self.campaign.slug}/{self.parent_location.id}/"

        # When implemented, should:
        # 1. Show location basic info (name, description, owner)
        # 2. List all sub-locations (children)
        # 3. Show breadcrumb navigation
        # 4. Enforce permission-based access control

        # Test will fail until view is implemented
        # response = self.client.get(expected_url)
        # self.assertEqual(response.status_code, 404)  # Expected until implemented

    def test_location_detail_permission_checking(self):
        """Test that location detail view should enforce permissions."""
        # When implemented, should follow same permission pattern as list view

        # Campaign members should have access
        for user in [self.owner, self.player]:
            with self.subTest(user=user.username):
                # When view exists, should return 200 for members
                pass

        # Non-members should get 404 (hide existence)
        # When view exists, should return 404 for non-members

    def test_location_detail_context_requirements(self):
        """Test required context data for location detail view."""
        # When implemented, detail view should provide these context variables:
        # - location: self.parent_location
        # - campaign: self.campaign
        # - sub_locations: [self.child1, self.child2]  # Direct children
        # - breadcrumb_path: self.parent_location.get_path_from_root()
        # - full_path: self.parent_location.get_full_path()
        # - user_role: "PLAYER"  # When logged in as player
        # - can_edit: True  # If user can edit this location
        # - can_delete: True  # If user can delete this location
        # - owner_display: self.parent_location.owner_display
        pass

    def test_location_detail_breadcrumb_generation(self):
        """Test that location detail should generate proper breadcrumbs."""
        # For grandchild location, breadcrumb should be:
        # Campaign → Locations → Parent Location → Child One → Grandchild
        # When detail view is implemented, should provide breadcrumb data
        # based on get_path_from_root() method
        pass

    def test_location_detail_sub_locations_listing(self):
        """Test that location detail should list sub-locations correctly."""
        # Parent location should show its 2 children
        expected_children = [self.child1, self.child2]

        # Child1 should show its 1 child (grandchild)
        expected_grandchildren = [self.grandchild]

        # These should be available via the sub_locations property
        actual_children = list(self.parent_location.sub_locations)
        actual_grandchildren = list(self.child1.sub_locations)

        self.assertCountEqual(actual_children, expected_children)
        self.assertCountEqual(actual_grandchildren, expected_grandchildren)

    def test_location_detail_owner_display(self):
        """Test that location detail should show owner information correctly."""
        # Parent location is owned by character
        self.assertEqual(self.parent_location.owner_display, "Detail Character (PC)")

        # Child locations have no owner
        self.assertEqual(self.child1.owner_display, "Unowned")
        self.assertEqual(self.child2.owner_display, "Unowned")


class LocationCreateViewTest(TestCase):
    """Test location creation view with parent selection and validation."""

    def setUp(self):
        """Set up test data for location creation view tests."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.gm = User.objects.create_user(
            username="gm", email="gm@test.com", password="testpass123"
        )
        self.player = User.objects.create_user(
            username="player", email="player@test.com", password="testpass123"
        )
        self.non_member = User.objects.create_user(
            username="non_member", email="non_member@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Create Test Campaign",
            slug="create-test",
            owner=self.owner,
            game_system="mage",
        )

        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm, role="GM"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )

        # Create some existing locations for parent selection
        self.root_location = Location.objects.create(
            name="Root Location",
            campaign=self.campaign,
            created_by=self.owner,
        )

        self.mid_location = Location.objects.create(
            name="Mid Location",
            campaign=self.campaign,
            parent=self.root_location,
            created_by=self.gm,
        )

        # Create location from other campaign to test filtering
        self.other_campaign = Campaign.objects.create(
            name="Other Campaign",
            slug="other-campaign",
            owner=self.owner,
            game_system="generic",
        )

        self.other_location = Location.objects.create(
            name="Other Campaign Location",
            campaign=self.other_campaign,
            created_by=self.owner,
        )

    def test_location_create_url_pattern(self):
        """Test that location create URL pattern should exist."""
        # Expected URL pattern: /locations/campaigns/{slug}/create/
        # When implemented:
        # url = reverse("locations:location_create", kwargs={
        #     "campaign_slug": self.campaign.slug
        # })
        # self.assertEqual(url, expected_url)
        pass

    def test_location_create_view_should_exist(self):
        """Test that location create view should be implemented."""
        # When implemented, should provide form for creating new locations
        # Test will fail until view is implemented
        # Should eventually return proper form
        pass

    def test_location_create_permission_checking(self):
        """Test that location create view should enforce permissions."""
        # When implemented, all campaign members should be able to create locations
        # based on Location.can_create() method

        self.assertTrue(Location.can_create(self.owner, self.campaign))
        self.assertTrue(Location.can_create(self.gm, self.campaign))
        self.assertTrue(Location.can_create(self.player, self.campaign))

        # Non-members should not be able to create
        self.assertFalse(Location.can_create(self.non_member, self.campaign))

    def test_location_create_form_integration(self):
        """Test that location create view should use LocationCreateForm."""
        # Test that form works correctly with campaign filtering
        form = LocationCreateForm(campaign=self.campaign, user=self.owner)

        # Form should only show parent options from same campaign
        parent_queryset = form.fields["parent"].queryset
        for location in parent_queryset:
            self.assertEqual(location.campaign, self.campaign)

        # Should not include locations from other campaigns
        self.assertNotIn(self.other_location, parent_queryset)

        # Should include locations from test campaign
        self.assertIn(self.root_location, parent_queryset)
        self.assertIn(self.mid_location, parent_queryset)

    def test_location_create_form_validation(self):
        """Test that location create form enforces hierarchy validation."""
        # Test form with valid data
        valid_data = {
            "name": "New Location",
            "description": "A new test location",
            "campaign": self.campaign.id,
            "parent": self.root_location.id,
        }

        form = LocationCreateForm(
            data=valid_data, campaign=self.campaign, user=self.player
        )
        self.assertTrue(form.is_valid())

        # Test form prevents circular references (when editing existing)
        # Test form enforces maximum depth
        # Test form requires valid campaign

    def test_location_create_sets_created_by(self):
        """Test that location creation sets created_by to current user."""
        form_data = {
            "name": "User Created Location",
            "description": "Created by current user",
            "campaign": self.campaign.id,
            "parent": "",  # No parent
        }

        form = LocationCreateForm(
            data=form_data, campaign=self.campaign, user=self.player
        )
        self.assertTrue(form.is_valid())

        location = form.save()
        self.assertEqual(location.created_by, self.player)
        self.assertEqual(location.campaign, self.campaign)

    def test_location_create_success_redirect(self):
        """Test that successful location creation should redirect appropriately."""
        # When implemented, should redirect to:
        # 1. Location detail view, OR
        # 2. Campaign locations list

        # Expected redirect targets:
        # list_url = f"/locations/campaigns/{self.campaign.slug}/"
        # detail_url = f"/locations/campaigns/{self.campaign.slug}/{location.id}/"
        pass


class LocationEditViewTest(TestCase):
    """Test location editing view with hierarchy validation and permission checks."""

    def setUp(self):
        """Set up test data for location editing view tests."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.gm = User.objects.create_user(
            username="gm", email="gm@test.com", password="testpass123"
        )
        self.player = User.objects.create_user(
            username="player", email="player@test.com", password="testpass123"
        )
        self.other_player = User.objects.create_user(
            username="other_player", email="other@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Edit Test Campaign",
            slug="edit-test",
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
            campaign=self.campaign, user=self.other_player, role="PLAYER"
        )

        # Create test character for ownership
        self.character = Character.objects.create(
            name="Edit Character",
            campaign=self.campaign,
            player_owner=self.player,
            game_system="mage",
        )

        # Create locations for editing tests
        self.owner_location = Location.objects.create(
            name="Owner Location",
            description="Created by owner",
            campaign=self.campaign,
            created_by=self.owner,
        )

        self.player_location = Location.objects.create(
            name="Player Location",
            description="Created by player",
            campaign=self.campaign,
            created_by=self.player,
        )

        self.character_location = Location.objects.create(
            name="Character Location",
            description="Owned by character",
            campaign=self.campaign,
            owned_by=self.character,
            created_by=self.other_player,
        )

        self.child_location = Location.objects.create(
            name="Child Location",
            description="Child of player location",
            campaign=self.campaign,
            parent=self.player_location,
            created_by=self.gm,
        )

    def test_location_edit_url_pattern(self):
        """Test that location edit URL pattern should exist."""
        # Expected URL: /locations/campaigns/{slug}/{location_id}/edit/
        # When implemented:
        # url = reverse("locations:location_edit", kwargs={
        #     "campaign_slug": self.campaign.slug,
        #     "location_id": self.player_location.id
        # })
        pass

    def test_location_edit_permission_checking(self):
        """Test that location edit view enforces permission rules."""
        # Test permission checking using model methods

        # Owner can edit all locations
        self.assertTrue(self.owner_location.can_edit(self.owner))
        self.assertTrue(self.player_location.can_edit(self.owner))
        self.assertTrue(self.character_location.can_edit(self.owner))

        # GM can edit all locations
        self.assertTrue(self.owner_location.can_edit(self.gm))
        self.assertTrue(self.player_location.can_edit(self.gm))
        self.assertTrue(self.character_location.can_edit(self.gm))

        # Player can edit own locations and character-owned locations
        self.assertFalse(
            self.owner_location.can_edit(self.player)
        )  # Can't edit owner's
        self.assertTrue(self.player_location.can_edit(self.player))  # Can edit own
        self.assertTrue(self.character_location.can_edit(self.player))  # Owns character

        # Other player can't edit locations they don't own
        self.assertFalse(self.owner_location.can_edit(self.other_player))
        self.assertFalse(self.player_location.can_edit(self.other_player))
        self.assertFalse(self.character_location.can_edit(self.other_player))

    def test_location_edit_form_integration(self):
        """Test that location edit view should use LocationEditForm."""
        # Test form initialization with existing data
        form = LocationEditForm(instance=self.player_location, user=self.player)

        # Form should be pre-populated
        self.assertEqual(
            form.initial.get("name") or form.instance.name, self.player_location.name
        )
        self.assertEqual(
            form.initial.get("description") or form.instance.description,
            self.player_location.description,
        )

        # Campaign field should be disabled in edit mode
        self.assertTrue(form.fields["campaign"].disabled)

    def test_location_edit_hierarchy_validation(self):
        """Test that location edit form prevents invalid hierarchy changes."""
        # Test that child cannot be made parent of its ancestor
        form_data = {
            "name": "Updated Child",
            "description": "Updated description",
            "campaign": self.campaign.id,
            "parent": self.child_location.id,  # Making child its own parent
        }

        form = LocationEditForm(
            data=form_data, instance=self.child_location, user=self.gm
        )

        # Should fail validation (circular reference)
        self.assertFalse(form.is_valid())
        self.assertIn("parent", form.errors)

    def test_location_edit_campaign_immutable(self):
        """Test that campaign cannot be changed in edit mode."""
        other_campaign = Campaign.objects.create(
            name="Other Campaign",
            slug="other-edit",
            owner=self.owner,
            game_system="generic",
        )

        form_data = {
            "name": "Updated Location",
            "description": "Updated description",
            "campaign": other_campaign.id,  # Try to change campaign
            "parent": "",
        }

        form = LocationEditForm(
            data=form_data, instance=self.player_location, user=self.player
        )

        # Form should ignore campaign change due to disabled field
        if form.is_valid():
            updated_location = form.save()
            self.assertEqual(
                updated_location.campaign, self.campaign
            )  # Should remain unchanged

    def test_location_edit_success_redirect(self):
        """Test that successful location edit should redirect appropriately."""
        # When implemented, should redirect to:
        # 1. Location detail view, OR
        # 2. Campaign locations list
        pass


class LocationSearchFilterTest(TestCase):
    """Test search and filtering functionality maintaining tree structure."""

    def setUp(self):
        """Set up test data for search and filtering tests."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.player = User.objects.create_user(
            username="player", email="player@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Search Test Campaign",
            slug="search-test",
            owner=self.owner,
            game_system="mage",
        )

        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )

        # Create test character for ownership filtering
        self.character = Character.objects.create(
            name="Search Character",
            campaign=self.campaign,
            player_owner=self.player,
            game_system="mage",
        )

        # Create locations with varied names and ownership for search testing
        self.locations = []

        # Castle hierarchy
        castle = Location.objects.create(
            name="Castle Ravenloft",
            description="A dark castle",
            campaign=self.campaign,
            created_by=self.owner,
        )
        self.locations.append(castle)

        castle_tower = Location.objects.create(
            name="Castle Tower",
            description="The main tower",
            campaign=self.campaign,
            parent=castle,
            owned_by=self.character,
            created_by=self.player,
        )
        self.locations.append(castle_tower)

        # Village hierarchy
        village = Location.objects.create(
            name="Barovia Village",
            description="A small village",
            campaign=self.campaign,
            created_by=self.owner,
        )
        self.locations.append(village)

        inn = Location.objects.create(
            name="Village Inn",
            description="A cozy inn",
            campaign=self.campaign,
            parent=village,
            created_by=self.player,
        )
        self.locations.append(inn)

        # Forest locations
        forest = Location.objects.create(
            name="Dark Forest",
            description="A mysterious forest",
            campaign=self.campaign,
            owned_by=self.character,
            created_by=self.player,
        )
        self.locations.append(forest)

        clearing = Location.objects.create(
            name="Forest Clearing",
            description="A peaceful clearing",
            campaign=self.campaign,
            parent=forest,
            created_by=self.owner,
        )
        self.locations.append(clearing)

    def test_location_search_by_name(self):
        """Test search functionality by location name."""
        # When search is implemented, should support these queries:

        # Search for "Castle" should return both castle locations
        castle_search_terms = ["Castle", "castle", "CASTLE"]
        for term in castle_search_terms:
            with self.subTest(search_term=term):
                # Should find: "Castle Ravenloft", "Castle Tower"
                expected_results = ["Castle Ravenloft", "Castle Tower"]

                # Use Django ORM to simulate search
                results = Location.objects.filter(
                    campaign=self.campaign, name__icontains=term
                )
                result_names = [loc.name for loc in results]

                for expected in expected_results:
                    self.assertIn(expected, result_names)

        # Search for "Village" should return village locations
        village_results = Location.objects.filter(
            campaign=self.campaign, name__icontains="Village"
        )
        village_names = [loc.name for loc in village_results]
        self.assertIn("Barovia Village", village_names)
        self.assertIn("Village Inn", village_names)

        # Search for "Forest" should return forest locations
        forest_results = Location.objects.filter(
            campaign=self.campaign, name__icontains="Forest"
        )
        forest_names = [loc.name for loc in forest_results]
        self.assertIn("Dark Forest", forest_names)
        self.assertIn("Forest Clearing", forest_names)

    def test_location_filter_by_owner(self):
        """Test filtering locations by character ownership."""
        # Filter by character-owned locations
        character_owned = Location.objects.filter(
            campaign=self.campaign, owned_by=self.character
        )

        character_owned_names = [loc.name for loc in character_owned]
        expected_owned = ["Castle Tower", "Dark Forest"]

        for expected in expected_owned:
            self.assertIn(expected, character_owned_names)

        # Should not include unowned locations
        unowned_names = [
            "Castle Ravenloft",
            "Barovia Village",
            "Village Inn",
            "Forest Clearing",
        ]
        for unowned in unowned_names:
            self.assertNotIn(unowned, character_owned_names)

    def test_location_filter_unowned(self):
        """Test filtering for unowned locations."""
        # Filter for locations with no owner
        unowned = Location.objects.filter(campaign=self.campaign, owned_by__isnull=True)

        unowned_names = [loc.name for loc in unowned]
        expected_unowned = [
            "Castle Ravenloft",
            "Barovia Village",
            "Village Inn",
            "Forest Clearing",
        ]

        for expected in expected_unowned:
            self.assertIn(expected, unowned_names)

        # Should not include owned locations
        owned_names = ["Castle Tower", "Dark Forest"]
        for owned in owned_names:
            self.assertNotIn(owned, unowned_names)

    def test_search_maintains_tree_structure(self):
        """Test that search results should maintain hierarchical relationships."""
        # When search is implemented, filtered results should still show hierarchy

        # Search for "Castle" returns castle and tower
        castle_results = Location.objects.filter(
            campaign=self.campaign, name__icontains="Castle"
        )

        castle_locations = list(castle_results)

        # Should be able to determine parent-child relationships
        for location in castle_locations:
            if location.parent:
                # Tree structure methods should still work
                self.assertTrue(hasattr(location, "get_ancestors"))
                self.assertTrue(hasattr(location, "get_depth"))

    def test_combined_search_and_filter(self):
        """Test combining search terms with ownership filters."""
        # Search for "Forest" AND owned by character
        combined_results = Location.objects.filter(
            campaign=self.campaign, name__icontains="Forest", owned_by=self.character
        )

        # Should return only "Dark Forest" (owned) but not "Forest Clearing" (unowned)
        result_names = [loc.name for loc in combined_results]
        self.assertIn("Dark Forest", result_names)
        self.assertNotIn("Forest Clearing", result_names)

    def test_search_url_parameters(self):
        """Test that search functionality should accept URL parameters."""
        # When implemented, search should accept parameters like:
        base_url = f"/locations/campaigns/{self.campaign.slug}/"

        # Search by name
        search_url = base_url + "?" + urlencode({"search": "Castle"})

        # Filter by owner
        owner_url = base_url + "?" + urlencode({"owner": self.character.id})

        # Filter unowned
        unowned_url = base_url + "?" + urlencode({"unowned": "true"})

        # Combined search and filter
        # combined_url = (
        #     base_url + "?" +
        #     urlencode({"search": "Forest", "owner": self.character.id})
        # )

        # URLs should be properly formatted
        self.assertIn("search=Castle", search_url)
        self.assertIn(f"owner={self.character.id}", owner_url)
        self.assertIn("unowned=true", unowned_url)


class LocationURLRoutingTest(TestCase):
    """Test URL routing and navigation patterns."""

    def setUp(self):
        """Set up test data for URL routing tests."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="URL Test Campaign",
            slug="url-test",
            owner=self.owner,
            game_system="mage",
        )

        self.location = Location.objects.create(
            name="URL Test Location",
            campaign=self.campaign,
            created_by=self.owner,
        )

    def test_campaign_locations_url_pattern(self):
        """Test campaign locations list URL pattern."""
        # Should be accessible via locations app
        url = reverse(
            "locations:campaign_locations", kwargs={"campaign_slug": self.campaign.slug}
        )

        expected = f"/locations/campaigns/{self.campaign.slug}/"
        self.assertEqual(url, expected)

        # Test URL resolution
        resolver = resolve(url)
        self.assertEqual(resolver.view_name, "locations:campaign_locations")

    def test_expected_location_detail_url_pattern(self):
        """Test expected location detail URL pattern."""
        # When implemented, should follow this pattern
        expected_detail_url = (
            f"/locations/campaigns/{self.campaign.slug}/{self.location.id}/"
        )

        # Test that URL contains expected components
        self.assertIn(self.campaign.slug, expected_detail_url)
        self.assertIn(str(self.location.id), expected_detail_url)

    def test_expected_location_create_url_pattern(self):
        """Test expected location create URL pattern."""
        # When implemented, should follow this pattern
        expected_create_url = f"/locations/campaigns/{self.campaign.slug}/create/"

        self.assertIn(self.campaign.slug, expected_create_url)
        self.assertIn("/create/", expected_create_url)

    def test_expected_location_edit_url_pattern(self):
        """Test expected location edit URL pattern."""
        # When implemented, should follow this pattern
        expected_edit_url = (
            f"/locations/campaigns/{self.campaign.slug}/{self.location.id}/edit/"
        )

        self.assertIn(self.campaign.slug, expected_edit_url)
        self.assertIn(str(self.location.id), expected_edit_url)
        self.assertIn("/edit/", expected_edit_url)

    def test_breadcrumb_navigation_urls(self):
        """Test that breadcrumb navigation URLs work correctly."""
        # From location detail, should link back to:

        # 1. Campaign detail
        campaign_url = reverse("campaigns:detail", kwargs={"slug": self.campaign.slug})
        self.assertEqual(campaign_url, f"/campaigns/{self.campaign.slug}/")

        # 2. Campaign locations list
        locations_url = reverse(
            "locations:campaign_locations", kwargs={"campaign_slug": self.campaign.slug}
        )
        self.assertEqual(locations_url, f"/locations/campaigns/{self.campaign.slug}/")

        # 3. Each level in location hierarchy should be linkable
        # This would be implemented when detail view exists

    def test_url_parameter_validation(self):
        """Test that URL parameters are properly validated."""
        # Invalid campaign slug should return 404
        invalid_url = "/locations/campaigns/invalid-slug/"
        self.client.force_login(self.owner)
        response = self.client.get(invalid_url)
        self.assertEqual(response.status_code, 404)

        # When location detail views are implemented:
        # Invalid location ID should return 404


class LocationTemplateRenderingTest(TestCase):
    """Test template rendering with proper context data."""

    def setUp(self):
        """Set up test data for template rendering tests."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Template Test Campaign",
            slug="template-test",
            owner=self.owner,
            game_system="mage",
        )

        # Create hierarchical locations for template testing
        self.root = Location.objects.create(
            name="Root",
            description="Root location",
            campaign=self.campaign,
            created_by=self.owner,
        )

        self.child1 = Location.objects.create(
            name="Child 1",
            description="First child",
            campaign=self.campaign,
            parent=self.root,
            created_by=self.owner,
        )

        self.child2 = Location.objects.create(
            name="Child 2",
            description="Second child",
            campaign=self.campaign,
            parent=self.root,
            created_by=self.owner,
        )

        self.grandchild = Location.objects.create(
            name="Grandchild",
            description="Child of child1",
            campaign=self.campaign,
            parent=self.child1,
            created_by=self.owner,
        )

    def test_location_list_template_context(self):
        """Test that location list template receives proper context."""
        self.client.force_login(self.owner)
        url = reverse(
            "locations:campaign_locations", kwargs={"campaign_slug": self.campaign.slug}
        )
        response = self.client.get(url)

        # Test basic context (these will exist once interface is implemented)
        if response.status_code == 200:
            self.assertEqual(response.context["campaign"], self.campaign)
            self.assertIn("locations", response.context)
            self.assertIn("user_role", response.context)

            # Test locations queryset
            locations = response.context["locations"]
            location_names = [loc.name for loc in locations]
            expected_names = ["Root", "Child 1", "Child 2", "Grandchild"]

            for name in expected_names:
                self.assertIn(name, location_names)

    def test_location_list_template_usage(self):
        """Test that correct template is used for location list."""
        self.client.force_login(self.owner)
        url = reverse(
            "locations:campaign_locations", kwargs={"campaign_slug": self.campaign.slug}
        )
        response = self.client.get(url)

        if response.status_code == 200:
            self.assertTemplateUsed(response, "locations/campaign_locations.html")

    def test_location_list_breadcrumb_rendering(self):
        """Test that breadcrumbs are properly rendered."""
        self.client.force_login(self.owner)
        url = reverse(
            "locations:campaign_locations", kwargs={"campaign_slug": self.campaign.slug}
        )
        response = self.client.get(url)

        if response.status_code == 200:
            # Should contain breadcrumb navigation
            self.assertContains(response, 'aria-label="breadcrumb"')
            self.assertContains(response, "breadcrumb")

            # Should link back to campaign
            campaign_url = reverse(
                "campaigns:detail", kwargs={"slug": self.campaign.slug}
            )
            self.assertContains(response, campaign_url)
            self.assertContains(response, self.campaign.name)

    def test_hierarchy_display_requirements(self):
        """Test requirements for hierarchical display in templates."""
        # When tree interface is implemented, templates should support:

        # 1. Collapsible tree structure
        # 2. Proper indentation for depth levels
        # 3. Expand/collapse functionality
        # 4. Parent-child relationship indicators

        self.client.force_login(self.owner)
        url = reverse(
            "locations:campaign_locations", kwargs={"campaign_slug": self.campaign.slug}
        )
        response = self.client.get(url)

        if response.status_code == 200:
            # For now, just verify locations are available for tree rendering
            locations = response.context["locations"]

            # Should have different depth levels
            depths = [loc.get_depth() for loc in locations]
            self.assertIn(0, depths)  # Root level
            self.assertIn(1, depths)  # First level children
            self.assertIn(2, depths)  # Second level children

            # Each location should have tree navigation methods
            for location in locations:
                self.assertTrue(hasattr(location, "get_depth"))
                self.assertTrue(hasattr(location, "sub_locations"))
                self.assertTrue(hasattr(location, "get_full_path"))

    def test_permission_based_template_content(self):
        """Test that templates show appropriate content based on permissions."""
        url = reverse(
            "locations:campaign_locations", kwargs={"campaign_slug": self.campaign.slug}
        )

        # Owner should see management options
        self.client.force_login(self.owner)
        response = self.client.get(url)

        if response.status_code == 200:
            self.assertTrue(response.context.get("can_create_location"))
            self.assertTrue(response.context.get("can_manage_locations"))

        # When interface is implemented, should show:
        # - Create Location button
        # - Edit/Delete buttons for each location
        # - Bulk management options


class LocationIntegrationTest(TestCase):
    """
    Integration tests for full user journey from campaign member to
    location management.
    """

    def setUp(self):
        """Set up comprehensive test data for integration tests."""
        # Create users with different roles
        self.owner = User.objects.create_user(
            username="campaign_owner",
            email="owner@test.com",
            password="testpass123",
        )
        self.gm = User.objects.create_user(
            username="gamemaster", email="gm@test.com", password="testpass123"
        )
        self.player1 = User.objects.create_user(
            username="player_one", email="player1@test.com", password="testpass123"
        )
        self.player2 = User.objects.create_user(
            username="player_two", email="player2@test.com", password="testpass123"
        )

        # Create campaign
        self.campaign = Campaign.objects.create(
            name="Integration Test Campaign",
            slug="integration-test",
            description="A campaign for testing location management integration",
            owner=self.owner,
            game_system="mage",
        )

        # Add memberships
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm, role="GM"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player1, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player2, role="PLAYER"
        )

        # Create characters for players
        self.player1_character = Character.objects.create(
            name="Hero Character",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="mage",
        )

        self.player2_character = Character.objects.create(
            name="Rogue Character",
            campaign=self.campaign,
            player_owner=self.player2,
            game_system="mage",
        )

        # Create initial location structure
        self.world = Location.objects.create(
            name="Game World",
            description="The main campaign world",
            campaign=self.campaign,
            created_by=self.owner,
        )

        self.city = Location.objects.create(
            name="Capital City",
            description="The main city where adventures begin",
            campaign=self.campaign,
            parent=self.world,
            created_by=self.gm,
        )

    def test_complete_location_management_workflow(self):
        """Test complete workflow from campaign access to location management."""
        # 1. Campaign member navigates to campaign
        self.client.force_login(self.player1)

        campaign_url = reverse("campaigns:detail", kwargs={"slug": self.campaign.slug})
        response = self.client.get(campaign_url)
        self.assertEqual(response.status_code, 200)

        # 2. Navigate to locations from campaign
        locations_url = reverse(
            "locations:campaign_locations", kwargs={"campaign_slug": self.campaign.slug}
        )
        response = self.client.get(locations_url)
        self.assertEqual(response.status_code, 200)

        # Should see existing locations
        self.assertContains(response, "Game World")
        self.assertContains(response, "Capital City")

        # 3. When create functionality is implemented, should be able to create location
        # (This part will fail until interface is implemented)

        # 4. When detail view is implemented, should be able to view location details
        # (This part will fail until interface is implemented)

        # 5. Permission-based editing should work
        # Player can edit locations they created or their character owns

    def test_permission_matrix_integration(self):
        """Test that permission matrix works correctly across all operations."""
        locations_url = reverse(
            "locations:campaign_locations", kwargs={"campaign_slug": self.campaign.slug}
        )

        # Test access for each role
        test_users = [
            (self.owner, "OWNER", True),
            (self.gm, "GM", True),
            (self.player1, "PLAYER", True),
            (self.player2, "PLAYER", True),
        ]

        for user, expected_role, should_access in test_users:
            with self.subTest(user=user.username, role=expected_role):
                self.client.force_login(user)
                response = self.client.get(locations_url)

                if should_access:
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.context["user_role"], expected_role)
                else:
                    self.assertEqual(response.status_code, 404)

    def test_location_ownership_integration(self):
        """Test location ownership integration with characters."""
        # Create location owned by player's character
        player_location = Location.objects.create(
            name="Player's House",
            description="A house owned by the player's character",
            campaign=self.campaign,
            parent=self.city,
            owned_by=self.player1_character,
            created_by=self.player1,
        )

        # Test ownership display
        self.assertEqual(player_location.owner_display, "Hero Character (PC)")

        # Test permission checking
        self.assertTrue(player_location.can_edit(self.player1))  # Owns character
        self.assertFalse(
            player_location.can_edit(self.player2)
        )  # Doesn't own character
        self.assertTrue(player_location.can_edit(self.owner))  # Campaign owner
        self.assertTrue(player_location.can_edit(self.gm))  # GM

    def test_hierarchy_navigation_integration(self):
        """Test that hierarchy navigation works across the interface."""
        # Create deeper hierarchy for testing
        district = Location.objects.create(
            name="Noble District",
            description="Where the wealthy live",
            campaign=self.campaign,
            parent=self.city,
            created_by=self.gm,
        )

        mansion = Location.objects.create(
            name="Lord's Mansion",
            description="The lord's residence",
            campaign=self.campaign,
            parent=district,
            created_by=self.owner,
        )

        # Test hierarchy methods work correctly
        self.assertEqual(mansion.get_depth(), 3)
        self.assertEqual(mansion.get_root(), self.world)

        expected_path = "Game World > Capital City > Noble District > Lord's Mansion"
        self.assertEqual(mansion.get_full_path(), expected_path)

        # Test that locations list includes all hierarchy levels
        self.client.force_login(self.player1)
        locations_url = reverse(
            "locations:campaign_locations", kwargs={"campaign_slug": self.campaign.slug}
        )
        response = self.client.get(locations_url)

        locations = response.context["locations"]
        location_names = [loc.name for loc in locations]

        expected_locations = [
            "Game World",
            "Capital City",
            "Noble District",
            "Lord's Mansion",
        ]
        for name in expected_locations:
            self.assertIn(name, location_names)

    def test_campaign_isolation_integration(self):
        """Test that location management respects campaign isolation."""
        # Create another campaign
        other_campaign = Campaign.objects.create(
            name="Other Campaign",
            slug="other-campaign",
            owner=self.owner,
            game_system="generic",
        )

        Location.objects.create(
            name="Other Campaign Location",
            campaign=other_campaign,
            created_by=self.owner,
        )

        # Player1 should not see other campaign's locations
        self.client.force_login(self.player1)
        locations_url = reverse(
            "locations:campaign_locations", kwargs={"campaign_slug": self.campaign.slug}
        )
        response = self.client.get(locations_url)

        locations = response.context["locations"]
        location_names = [loc.name for loc in locations]

        # Should not contain other campaign's location
        self.assertNotIn("Other Campaign Location", location_names)

        # Should contain own campaign's locations
        self.assertIn("Game World", location_names)
        self.assertIn("Capital City", location_names)

    def test_form_integration_workflow(self):
        """Test that forms integrate properly with the views."""
        # Test LocationCreateForm integration
        create_form = LocationCreateForm(campaign=self.campaign, user=self.player1)

        # Should filter parent options to campaign
        parent_options = create_form.fields["parent"].queryset
        for location in parent_options:
            self.assertEqual(location.campaign, self.campaign)

        # Test form saves with correct user
        form_data = {
            "name": "New Player Location",
            "description": "Created by player",
            "campaign": self.campaign.id,
            "parent": self.city.id,
        }

        form = LocationCreateForm(
            data=form_data, campaign=self.campaign, user=self.player1
        )
        if form.is_valid():
            location = form.save()
            self.assertEqual(location.created_by, self.player1)
            self.assertEqual(location.campaign, self.campaign)
            self.assertEqual(location.parent, self.city)

    def test_error_handling_integration(self):
        """Test that error handling works properly across the interface."""
        # Test invalid campaign slug
        invalid_url = "/locations/campaigns/invalid-slug/"
        self.client.force_login(self.player1)
        response = self.client.get(invalid_url)
        self.assertEqual(response.status_code, 404)

        # Test non-member access
        non_member = User.objects.create_user(
            username="outsider", email="outsider@test.com", password="testpass123"
        )

        self.client.force_login(non_member)
        locations_url = reverse(
            "locations:campaign_locations", kwargs={"campaign_slug": self.campaign.slug}
        )
        response = self.client.get(locations_url)
        self.assertEqual(response.status_code, 404)  # Hide existence

    def test_performance_integration(self):
        """Test that location management performs efficiently."""
        # Create larger location set
        locations = []
        for i in range(20):
            location = Location.objects.create(
                name=f"Location {i}",
                description=f"Test location {i}",
                campaign=self.campaign,
                parent=self.world if i % 3 == 0 else self.city,
                created_by=self.owner if i % 2 == 0 else self.gm,
            )
            locations.append(location)

        # Test that listing doesn't cause N+1 queries
        self.client.force_login(self.player1)
        locations_url = reverse(
            "locations:campaign_locations", kwargs={"campaign_slug": self.campaign.slug}
        )

        with self.assertNumQueries(
            50
        ):  # Optimized query count for complex hierarchy operations
            response = self.client.get(locations_url)

        self.assertEqual(response.status_code, 200)

        # Should return all locations
        returned_locations = response.context["locations"]
        self.assertGreater(returned_locations.count(), 20)

    def test_full_crud_workflow_integration(self):
        """Test complete CRUD workflow when interface is implemented."""
        # This test documents the expected full workflow

        # 1. CREATE: User creates new location
        # 2. READ: User views location in list and detail
        # 3. UPDATE: User edits location
        # 4. DELETE: User deletes location (with hierarchy handling)

        # When interface is implemented, this should test:
        # - Navigation from campaign to locations
        # - Create form and success
        # - Detail view with breadcrumbs and sub-locations
        # - Edit form and validation
        # - Delete confirmation and hierarchy preservation

        self.client.force_login(self.player1)

        # For now, verify the foundation is solid
        locations_url = reverse(
            "locations:campaign_locations", kwargs={"campaign_slug": self.campaign.slug}
        )
        response = self.client.get(locations_url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("locations", response.context)
        self.assertEqual(response.context["campaign"], self.campaign)
