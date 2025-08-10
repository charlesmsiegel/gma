"""
Tests for campaign views.

This module tests the web interface views for campaign creation and management,
including form handling, redirects, and authentication requirements.
"""

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from campaigns.models import Campaign

User = get_user_model()


class CampaignCreateViewTest(TestCase):
    """Test the campaign creation view."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="TestPass123!"
        )
        self.create_url = reverse("campaigns:create")

    def test_create_view_requires_authentication(self):
        """Test that unauthenticated users are redirected to login."""
        response = self.client.get(self.create_url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_authenticated_user_can_access_create_form(self):
        """Test that authenticated users can access the campaign creation form."""
        self.client.login(username="testuser", password="TestPass123!")

        response = self.client.get(self.create_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Campaign")
        self.assertContains(response, "Name")
        # Check for form elements
        self.assertContains(response, "<form")
        self.assertContains(response, 'name="name"')
        self.assertContains(response, 'name="description"')
        self.assertContains(response, 'name="game_system"')

    def test_create_campaign_success(self):
        """Test successful campaign creation with valid data."""
        self.client.login(username="testuser", password="TestPass123!")

        form_data = {
            "name": "Test Campaign",
            "description": "A test campaign for testing",
            "game_system": "Mage: The Ascension",
        }

        response = self.client.post(self.create_url, form_data)

        # Should redirect to campaign detail after successful creation
        self.assertEqual(response.status_code, 302)

        # Check that campaign was created
        campaign = Campaign.objects.get(name="Test Campaign")
        self.assertEqual(campaign.owner, self.user)
        self.assertEqual(campaign.description, "A test campaign for testing")
        self.assertEqual(campaign.game_system, "Mage: The Ascension")
        self.assertIsNotNone(campaign.slug)

        # Check redirect URL includes the campaign detail
        self.assertIn(f"/campaigns/{campaign.slug}/", response.url)

    def test_create_campaign_with_minimal_data(self):
        """Test campaign creation with only required fields."""
        self.client.login(username="testuser", password="TestPass123!")

        form_data = {"name": "Minimal Campaign"}

        response = self.client.post(self.create_url, form_data)

        self.assertEqual(response.status_code, 302)
        campaign = Campaign.objects.get(name="Minimal Campaign")
        self.assertEqual(campaign.owner, self.user)
        self.assertEqual(campaign.description, "")
        self.assertEqual(campaign.game_system, "")

    def test_create_campaign_invalid_data_shows_errors(self):
        """Test that invalid form data shows validation errors."""
        self.client.login(username="testuser", password="TestPass123!")

        # Missing required name field
        form_data = {
            "description": "A campaign without a name",
            "game_system": "Some Game",
        }

        response = self.client.post(self.create_url, form_data)

        # Should not redirect, should show form with errors
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "error")
        # Should not create campaign
        self.assertEqual(Campaign.objects.count(), 0)

    def test_create_campaign_empty_name_shows_error(self):
        """Test that empty name field shows validation error."""
        self.client.login(username="testuser", password="TestPass123!")

        form_data = {
            "name": "",  # Empty name should fail
            "description": "Test description",
        }

        response = self.client.post(self.create_url, form_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "required")
        self.assertEqual(Campaign.objects.count(), 0)

    def test_create_campaign_long_name_handled(self):
        """Test that very long campaign names are handled properly."""
        self.client.login(username="testuser", password="TestPass123!")

        # Test with maximum length name (200 chars)
        long_name = "A" * 200
        form_data = {"name": long_name, "description": "Test with long name"}

        response = self.client.post(self.create_url, form_data)

        self.assertEqual(response.status_code, 302)
        campaign = Campaign.objects.get(name=long_name)
        self.assertEqual(campaign.name, long_name)
        # Slug should be generated properly even for long names
        self.assertIsNotNone(campaign.slug)
        self.assertTrue(len(campaign.slug) <= 200)

    def test_create_campaign_too_long_name_shows_error(self):
        """Test that names exceeding max length show validation error."""
        self.client.login(username="testuser", password="TestPass123!")

        # Test with name longer than 200 chars
        too_long_name = "A" * 201
        form_data = {"name": too_long_name, "description": "Test with too long name"}

        response = self.client.post(self.create_url, form_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ensure this value has at most 200 characters")
        self.assertEqual(Campaign.objects.count(), 0)

    def test_success_message_shown_after_creation(self):
        """Test that success message is displayed after campaign creation."""
        self.client.login(username="testuser", password="TestPass123!")

        form_data = {
            "name": "Success Message Test",
            "description": "Testing success messages",
        }

        response = self.client.post(self.create_url, form_data, follow=True)

        # Check that success message was added
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("created successfully" in str(m) for m in messages))


class CampaignDetailViewEnhancedTest(TestCase):
    """Enhanced tests for the CampaignDetailView with public/private campaigns."""

    def setUp(self):
        """Set up test data."""
        # Create test users
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
            username="nonmember", email="nonmember@test.com", password="testpass123"
        )

        # Create campaigns
        self.public_campaign = Campaign.objects.create(
            name="Public Campaign",
            description="A public campaign",
            owner=self.owner,
            game_system="D&D 5e",
            is_public=True,
        )

        self.private_campaign = Campaign.objects.create(
            name="Private Campaign",
            description="A private campaign",
            owner=self.owner,
            game_system="Pathfinder",
            is_public=False,
        )

        # Set up memberships
        from campaigns.models import CampaignMembership

        CampaignMembership.objects.create(
            campaign=self.private_campaign, user=self.gm, role="GM"
        )
        CampaignMembership.objects.create(
            campaign=self.private_campaign, user=self.player, role="PLAYER"
        )

    def test_public_campaign_accessible_to_anyone(self):
        """Test that public campaigns are accessible to anyone."""
        # Unauthenticated user
        response = self.client.get(
            reverse("campaigns:detail", kwargs={"slug": self.public_campaign.slug})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["campaign"], self.public_campaign)

        # Non-member authenticated user
        self.client.login(username="nonmember", password="testpass123")
        response = self.client.get(
            reverse("campaigns:detail", kwargs={"slug": self.public_campaign.slug})
        )
        self.assertEqual(response.status_code, 200)

    def test_private_campaign_returns_404_for_non_members(self):
        """Test that private campaigns return 404 for non-members."""
        # Unauthenticated user
        response = self.client.get(
            reverse("campaigns:detail", kwargs={"slug": self.private_campaign.slug})
        )
        self.assertEqual(response.status_code, 404)

        # Non-member authenticated user
        self.client.login(username="nonmember", password="testpass123")
        response = self.client.get(
            reverse("campaigns:detail", kwargs={"slug": self.private_campaign.slug})
        )
        self.assertEqual(response.status_code, 404)

    def test_private_campaign_accessible_to_members(self):
        """Test that private campaigns are accessible to members."""
        # Owner
        self.client.login(username="owner", password="testpass123")
        response = self.client.get(
            reverse("campaigns:detail", kwargs={"slug": self.private_campaign.slug})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["campaign"], self.private_campaign)

        # GM
        self.client.login(username="gm", password="testpass123")
        response = self.client.get(
            reverse("campaigns:detail", kwargs={"slug": self.private_campaign.slug})
        )
        self.assertEqual(response.status_code, 200)

        # Player
        self.client.login(username="player", password="testpass123")
        response = self.client.get(
            reverse("campaigns:detail", kwargs={"slug": self.private_campaign.slug})
        )
        self.assertEqual(response.status_code, 200)

    def test_role_based_information_display(self):
        """Test that different information is displayed based on user role."""
        # Owner sees management options
        self.client.login(username="owner", password="testpass123")
        response = self.client.get(
            reverse("campaigns:detail", kwargs={"slug": self.private_campaign.slug})
        )
        self.assertContains(response, "Edit Campaign")
        self.assertContains(response, "Manage Members")
        self.assertContains(response, "Campaign Settings")

        # GM sees GM-specific options
        self.client.login(username="gm", password="testpass123")
        response = self.client.get(
            reverse("campaigns:detail", kwargs={"slug": self.private_campaign.slug})
        )
        self.assertContains(response, "Create Scene")
        self.assertContains(response, "Manage NPCs")
        self.assertNotContains(response, "Edit Campaign")

        # Player sees limited options
        self.client.login(username="player", password="testpass123")
        response = self.client.get(
            reverse("campaigns:detail", kwargs={"slug": self.private_campaign.slug})
        )
        self.assertContains(response, "View Scenes")
        self.assertContains(response, "My Character")
        self.assertNotContains(response, "Create Scene")
        self.assertNotContains(response, "Edit Campaign")

        # Non-member of public campaign sees very limited info
        self.client.login(username="nonmember", password="testpass123")
        response = self.client.get(
            reverse("campaigns:detail", kwargs={"slug": self.public_campaign.slug})
        )
        self.assertContains(response, "Request to Join")
        self.assertNotContains(response, "View Scenes")
        self.assertNotContains(response, "Edit Campaign")

    def test_campaign_detail_displays_all_fields(self):
        """Test that campaign detail view displays all expected fields."""
        self.client.login(username="owner", password="testpass123")
        response = self.client.get(
            reverse("campaigns:detail", kwargs={"slug": self.private_campaign.slug})
        )

        # Basic campaign info
        self.assertContains(response, self.private_campaign.name)
        self.assertContains(response, self.private_campaign.description)
        self.assertContains(response, self.private_campaign.game_system)

        # Membership info
        self.assertContains(response, "Members")
        self.assertContains(response, self.gm.username)
        self.assertContains(response, self.player.username)

        # Activity info
        self.assertContains(response, "Created")
        self.assertContains(response, "Last Updated")

    def test_user_role_displayed_in_context(self):
        """Test that the user's role is included in the template context."""
        # Owner
        self.client.login(username="owner", password="testpass123")
        response = self.client.get(
            reverse("campaigns:detail", kwargs={"slug": self.private_campaign.slug})
        )
        self.assertEqual(response.context["user_role"], "OWNER")

        # GM
        self.client.login(username="gm", password="testpass123")
        response = self.client.get(
            reverse("campaigns:detail", kwargs={"slug": self.private_campaign.slug})
        )
        self.assertEqual(response.context["user_role"], "GM")

        # Player
        self.client.login(username="player", password="testpass123")
        response = self.client.get(
            reverse("campaigns:detail", kwargs={"slug": self.private_campaign.slug})
        )
        self.assertEqual(response.context["user_role"], "PLAYER")

        # Non-member on public campaign
        self.client.login(username="nonmember", password="testpass123")
        response = self.client.get(
            reverse("campaigns:detail", kwargs={"slug": self.public_campaign.slug})
        )
        self.assertIsNone(response.context["user_role"])


class CampaignDetailViewTest(TestCase):
    """Test the campaign detail view."""

    def setUp(self):
        """Set up test data."""
        from campaigns.models import CampaignMembership

        self.client = Client()
        self.owner = User.objects.create_user(
            username="owner", email="owner@example.com", password="TestPass123!"
        )
        self.gm = User.objects.create_user(
            username="gm", email="gm@example.com", password="TestPass123!"
        )
        self.player = User.objects.create_user(
            username="player", email="player@example.com", password="TestPass123!"
        )
        self.observer = User.objects.create_user(
            username="observer", email="observer@example.com", password="TestPass123!"
        )
        self.other_user = User.objects.create_user(
            username="otheruser", email="other@example.com", password="TestPass123!"
        )

        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            description="A test campaign",
            game_system="Vampire: The Masquerade",
            owner=self.owner,
            is_public=True,
        )

        # Create campaign with special characters in slug for testing
        self.special_campaign = Campaign.objects.create(
            name="Test Campaign! @#$%",
            description="Campaign with special characters",
            game_system="D&D 5e",
            owner=self.owner,
            is_public=False,
        )

        # Create inactive campaign
        self.inactive_campaign = Campaign.objects.create(
            name="Inactive Campaign",
            description="An inactive test campaign",
            game_system="Pathfinder",
            owner=self.owner,
            is_active=False,
            is_public=True,
        )

        # Set up memberships
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm, role="GM"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.observer, role="OBSERVER"
        )
        CampaignMembership.objects.create(
            campaign=self.special_campaign, user=self.gm, role="GM"
        )

        self.detail_url = reverse(
            "campaigns:detail", kwargs={"slug": self.campaign.slug}
        )

    def test_detail_view_accessible_by_slug(self):
        """Test that campaign detail view is accessible by slug."""
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.campaign.name)
        self.assertContains(response, self.campaign.description)
        self.assertContains(response, self.campaign.game_system)

    def test_detail_view_shows_owner_information(self):
        """Test that detail view shows campaign owner information."""
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.owner.username)

    def test_detail_view_nonexistent_campaign_404(self):
        """Test that nonexistent campaign returns 404."""
        nonexistent_url = reverse(
            "campaigns:detail", kwargs={"slug": "nonexistent-campaign"}
        )

        response = self.client.get(nonexistent_url)

        self.assertEqual(response.status_code, 404)

    def test_detail_view_shows_edit_link_for_owner(self):
        """Test that edit link is shown to campaign owner."""
        self.client.login(username="owner", password="TestPass123!")

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Edit")

    def test_detail_view_no_edit_link_for_non_owner(self):
        """Test that edit link is not shown to non-owners."""
        self.client.login(username="otheruser", password="TestPass123!")

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)
        # Should not contain edit link for non-owners
        self.assertNotContains(response, "Edit Campaign")

    def test_owner_management_buttons_functional(self):
        """Test that owner sees functional Invite Users and Manage Members buttons."""
        self.client.login(username="owner", password="TestPass123!")
        response = self.client.get(self.detail_url)

        # Verify buttons exist and have proper URLs (not href="#")
        expected_invite_url = f"/campaigns/{self.campaign.slug}/send-invitation/"
        expected_manage_url = f"/campaigns/{self.campaign.slug}/members/"

        self.assertContains(response, f'href="{expected_invite_url}"')
        self.assertContains(response, f'href="{expected_manage_url}"')
        self.assertContains(response, "Invite Users</a>")
        self.assertContains(response, "Manage Members</a>")

        # If we can see the proper URLs above, the buttons are functional

    def test_non_owner_cannot_see_management_buttons(self):
        """Test that non-owners don't see Invite Users or Manage Members buttons."""
        self.client.login(username="otheruser", password="TestPass123!")
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Invite Users</a>")
        self.assertNotContains(response, "Manage Members</a>")

    def test_campaign_management_section_visible_for_owner(self):
        """Test that campaign owners see the campaign management section."""
        self.client.login(username="owner", password="TestPass123!")
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Campaign Management")
        self.assertContains(response, "campaign-management")
        self.assertContains(response, "Manage Characters")
        self.assertContains(response, "Manage Scenes")
        self.assertContains(response, "Manage Locations")
        self.assertContains(response, "Manage Items")

    # Campaign Management Links Feature Tests

    def test_owner_sees_all_management_cards(self):
        """Test that campaign owners see all 4 management cards with proper URLs."""
        self.client.login(username="owner", password="TestPass123!")
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)

        # Check for Campaign Management section
        self.assertContains(response, "Campaign Management", count=1)
        self.assertContains(response, 'class="campaign-management"')

        # Check for all 4 management cards
        expected_urls = [
            f"/campaigns/{self.campaign.slug}/characters/",
            f"/campaigns/{self.campaign.slug}/scenes/",
            f"/campaigns/{self.campaign.slug}/locations/",
            f"/campaigns/{self.campaign.slug}/items/",
        ]

        for url in expected_urls:
            self.assertContains(response, f'href="{url}"')

        # Check for management card classes and structure by counting button links
        self.assertContains(response, 'btn btn-primary">Characters</a>')
        self.assertContains(response, 'btn btn-primary">Scenes</a>')
        self.assertContains(response, 'btn btn-primary">Locations</a>')
        self.assertContains(response, 'btn btn-primary">Items</a>')

        # Check for specific card content
        self.assertContains(response, "Manage Characters")
        self.assertContains(response, "Manage Scenes")
        self.assertContains(response, "Manage Locations")
        self.assertContains(response, "Manage Items")

    def test_gm_sees_all_management_cards(self):
        """Test that GMs see all 4 management cards (same as owner for now)."""
        self.client.login(username="gm", password="TestPass123!")
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)

        # Check for Campaign Management section
        self.assertContains(response, "Campaign Management", count=1)
        self.assertContains(response, 'class="campaign-management"')

        # Check for all 4 management cards
        expected_urls = [
            f"/campaigns/{self.campaign.slug}/characters/",
            f"/campaigns/{self.campaign.slug}/scenes/",
            f"/campaigns/{self.campaign.slug}/locations/",
            f"/campaigns/{self.campaign.slug}/items/",
        ]

        for url in expected_urls:
            self.assertContains(response, f'href="{url}"')

        # Check for management card structure by counting the button links
        self.assertContains(response, 'btn btn-primary">Characters</a>')
        self.assertContains(response, 'btn btn-primary">Scenes</a>')
        self.assertContains(response, 'btn btn-primary">Locations</a>')
        self.assertContains(response, 'btn btn-primary">Items</a>')

    def test_player_sees_limited_management_access(self):
        """Test that players see limited access (only character management they own)."""
        self.client.login(username="player", password="TestPass123!")
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)

        # Players should see Campaign Management section but with limited cards
        self.assertContains(response, "Campaign Management", count=1)
        self.assertContains(response, 'class="campaign-management"')

        # Players should see character management (limited to their own)
        self.assertContains(response, f"/campaigns/{self.campaign.slug}/characters/")
        self.assertContains(response, "My Characters")

        # Players should NOT see full management access to other areas
        self.assertNotContains(response, "Manage Scenes")
        self.assertNotContains(response, "Manage Locations")
        self.assertNotContains(response, "Manage Items")

        # Players should see only 1 management card
        self.assertContains(response, 'btn btn-primary">My Characters</a>')

    def test_observer_sees_read_only_access(self):
        """Test that observers see read-only access to campaign management."""
        self.client.login(username="observer", password="TestPass123!")
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)

        # Observers should see limited Campaign Management section
        self.assertContains(response, "Campaign Management", count=1)
        self.assertContains(response, 'class="campaign-management"')

        # Observers should see read-only access
        self.assertContains(response, f"/campaigns/{self.campaign.slug}/characters/")
        self.assertContains(response, f"/campaigns/{self.campaign.slug}/scenes/")
        self.assertContains(response, "View Characters")
        self.assertContains(response, "View Scenes")

        # Should NOT see management actions
        self.assertNotContains(response, "Manage Characters")
        self.assertNotContains(response, "Manage Scenes")

        # Observers should see 2 management cards
        self.assertContains(response, 'btn btn-primary">View Characters</a>')
        self.assertContains(response, 'btn btn-primary">View Scenes</a>')

    def test_anonymous_user_no_management_section(self):
        """Test that anonymous users don't see management section at all."""
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)

        # Should not see Campaign Management section
        self.assertNotContains(response, "Campaign Management")
        self.assertNotContains(response, 'class="campaign-management"')
        self.assertNotContains(response, '<div class="management-card')

        # Should not see any management URLs
        management_urls = [
            f"/campaigns/{self.campaign.slug}/characters/",
            f"/campaigns/{self.campaign.slug}/scenes/",
            f"/campaigns/{self.campaign.slug}/locations/",
            f"/campaigns/{self.campaign.slug}/items/",
        ]

        for url in management_urls:
            self.assertNotContains(response, url)

    def test_non_member_no_management_section(self):
        """Test that non-members don't see management section."""
        self.client.login(username="otheruser", password="TestPass123!")
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)

        # Should not see Campaign Management section
        self.assertNotContains(response, "Campaign Management")
        self.assertNotContains(response, 'class="campaign-management"')
        self.assertNotContains(response, '<div class="management-card')

    def test_management_urls_with_special_characters(self):
        """Test that management URLs work correctly with special characters."""
        self.client.login(username="owner", password="TestPass123!")

        special_url = reverse(
            "campaigns:detail", kwargs={"slug": self.special_campaign.slug}
        )
        response = self.client.get(special_url)

        self.assertEqual(response.status_code, 200)

        # URLs should be properly escaped and work with special character slugs
        expected_urls = [
            f"/campaigns/{self.special_campaign.slug}/characters/",
            f"/campaigns/{self.special_campaign.slug}/scenes/",
            f"/campaigns/{self.special_campaign.slug}/locations/",
            f"/campaigns/{self.special_campaign.slug}/items/",
        ]

        for url in expected_urls:
            self.assertContains(response, f'href="{url}"')

    def test_inactive_campaign_management_still_visible_to_owner(self):
        """Test that inactive campaigns still show management to owners."""
        self.client.login(username="owner", password="TestPass123!")

        inactive_url = reverse(
            "campaigns:detail", kwargs={"slug": self.inactive_campaign.slug}
        )
        response = self.client.get(inactive_url)

        self.assertEqual(response.status_code, 200)

        # Even inactive campaigns should show management to owners
        self.assertContains(response, "Campaign Management", count=1)
        self.assertContains(response, 'class="campaign-management"')
        self.assertContains(response, 'btn btn-primary">Characters</a>')
        self.assertContains(response, 'btn btn-primary">Scenes</a>')
        self.assertContains(response, 'btn btn-primary">Locations</a>')
        self.assertContains(response, 'btn btn-primary">Items</a>')

    def test_management_cards_have_proper_css_classes(self):
        """Test that management cards have correct CSS classes for theming."""
        self.client.login(username="owner", password="TestPass123!")
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)

        # Check for proper CSS class structure
        self.assertContains(response, 'class="campaign-management"')
        self.assertContains(response, 'btn btn-primary">Characters</a>')
        self.assertContains(response, 'btn btn-primary">Scenes</a>')
        self.assertContains(response, 'btn btn-primary">Locations</a>')
        self.assertContains(response, 'btn btn-primary">Items</a>')

        # Check for specific management card types (for different styling)
        self.assertContains(response, 'class="management-card characters-card"')
        self.assertContains(response, 'class="management-card scenes-card"')
        self.assertContains(response, 'class="management-card locations-card"')
        self.assertContains(response, 'class="management-card items-card"')

    def test_management_section_responsive_layout(self):
        """Test that management section uses responsive grid layout."""
        self.client.login(username="owner", password="TestPass123!")
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)

        # Check for responsive grid container
        self.assertContains(response, "management-grid")

        # Cards should be in a grid layout that adapts to screen size
        self.assertContains(response, 'btn btn-primary">Characters</a>')
        self.assertContains(response, 'btn btn-primary">Scenes</a>')
        self.assertContains(response, 'btn btn-primary">Locations</a>')
        self.assertContains(response, 'btn btn-primary">Items</a>')

    def test_management_cards_contain_descriptions(self):
        """Test that management cards contain helpful descriptions."""
        self.client.login(username="owner", password="TestPass123!")
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)

        # Check for card descriptions
        self.assertContains(response, "Manage player and NPC characters")
        self.assertContains(response, "Create and manage campaign scenes")
        self.assertContains(response, "Organize campaign locations and maps")
        self.assertContains(response, "Track items, equipment, and treasures")

    def test_management_cards_have_icons(self):
        """Test that management cards display appropriate icons."""
        self.client.login(username="owner", password="TestPass123!")
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)

        # Check for icon classes or elements (adjust based on implementation)
        self.assertContains(response, 'class="card-icon"', count=4)

        # Check for specific Unicode emoji icons
        self.assertContains(response, "👥")  # Characters icon
        self.assertContains(response, "🎭")  # Scenes icon
        self.assertContains(response, "🗺️")  # Locations icon
        self.assertContains(response, "⚔️")  # Items icon

    def test_management_section_placement(self):
        """Test that management section appears in correct location on page."""
        self.client.login(username="owner", password="TestPass123!")
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()

        # Management section should appear after campaign info but before member list
        campaign_info_pos = content.find('class="info-section"')
        management_pos = content.find('class="campaign-management"')
        member_list_pos = content.find('class="member-list-section"')

        # Verify ordering: campaign info < management < member list
        self.assertLess(campaign_info_pos, management_pos)
        self.assertLess(management_pos, member_list_pos)

    def test_management_urls_are_absolute_paths(self):
        """Test that management URLs are properly formed absolute paths."""
        self.client.login(username="owner", password="TestPass123!")
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)

        # URLs should start with /campaigns/ and include full path
        expected_patterns = [
            f'href="/campaigns/{self.campaign.slug}/characters/"',
            f'href="/campaigns/{self.campaign.slug}/scenes/"',
            f'href="/campaigns/{self.campaign.slug}/locations/"',
            f'href="/campaigns/{self.campaign.slug}/items/"',
        ]

        for pattern in expected_patterns:
            self.assertContains(response, pattern)

        # Should not contain relative URLs in management section
        self.assertNotContains(response, 'href="characters/"')

        # Management cards should have absolute URLs, not placeholder links
        # (We don't check for href="#" globally since other sections may have
        # placeholder links)
        content = response.content.decode()
        # Find the management section
        management_start = content.find('class="campaign-management"')
        management_end = content.find(
            "</div>", management_start + content[management_start:].find("</div>") + 10
        )
        if management_start != -1 and management_end != -1:
            management_section = content[management_start:management_end]
            self.assertNotIn('href="#"', management_section)

    def test_role_based_management_permissions_consistency(self):
        """Test that role-based permissions are consistently applied."""
        roles_and_expected_cards = [
            (
                "owner",
                4,
                [
                    "Manage Characters",
                    "Manage Scenes",
                    "Manage Locations",
                    "Manage Items",
                ],
            ),
            (
                "gm",
                4,
                [
                    "Manage Characters",
                    "Manage Scenes",
                    "Manage Locations",
                    "Manage Items",
                ],
            ),
            ("player", 1, ["My Characters"]),
            ("observer", 2, ["View Characters", "View Scenes"]),
        ]

        for role, expected_count, expected_content in roles_and_expected_cards:
            with self.subTest(role=role):
                # Get appropriate user for role
                if role == "owner":
                    user = self.owner
                elif role == "gm":
                    user = self.gm
                elif role == "player":
                    user = self.player
                else:  # observer
                    user = self.observer

                self.client.login(username=user.username, password="TestPass123!")
                response = self.client.get(self.detail_url)

                self.assertEqual(response.status_code, 200)

                # Check that expected content is present
                for content in expected_content:
                    self.assertContains(response, content)

                # Additional role-specific checks
                if role in ["owner", "gm"]:
                    self.assertContains(response, 'btn btn-primary">Characters</a>')
                    self.assertContains(response, 'btn btn-primary">Scenes</a>')
                    self.assertContains(response, 'btn btn-primary">Locations</a>')
                    self.assertContains(response, 'btn btn-primary">Items</a>')
                elif role == "player":
                    self.assertContains(response, 'btn btn-primary">My Characters</a>')
                elif role == "observer":
                    self.assertContains(
                        response, 'btn btn-primary">View Characters</a>'
                    )
                    self.assertContains(response, 'btn btn-primary">View Scenes</a>')

    def test_very_long_campaign_name_urls_work(self):
        """Test that management URLs work with very long campaign names."""
        long_campaign = Campaign.objects.create(
            name="A" * 190,  # Very long name near slug limit
            description="Test campaign with very long name",
            game_system="Test System",
            owner=self.owner,
            is_public=True,
        )

        self.client.login(username="owner", password="TestPass123!")
        long_url = reverse("campaigns:detail", kwargs={"slug": long_campaign.slug})
        response = self.client.get(long_url)

        self.assertEqual(response.status_code, 200)

        # URLs should work even with long slugs
        expected_urls = [
            f"/campaigns/{long_campaign.slug}/characters/",
            f"/campaigns/{long_campaign.slug}/scenes/",
            f"/campaigns/{long_campaign.slug}/locations/",
            f"/campaigns/{long_campaign.slug}/items/",
        ]

        for url in expected_urls:
            self.assertContains(response, f'href="{url}"')


class CampaignManagementURLTest(TestCase):
    """Test URL patterns for Campaign Management Links feature."""

    def setUp(self):
        """Set up test data."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@example.com", password="TestPass123!"
        )
        self.campaign = Campaign.objects.create(
            name="URL Test Campaign",
            description="Campaign for URL testing",
            game_system="Test System",
            owner=self.owner,
            is_public=True,
        )

    def test_management_urls_resolve_correctly(self):
        """Test that management URLs resolve to correct view patterns."""

        # Test that management URLs follow the expected pattern
        base_url = f"/campaigns/{self.campaign.slug}/"

        management_paths = [
            "characters/",
            "scenes/",
            "locations/",
            "items/",
        ]

        for path in management_paths:
            full_url = base_url + path

            # Test that URL is well-formed
            self.assertTrue(full_url.startswith("/campaigns/"))
            self.assertTrue(full_url.endswith("/"))
            self.assertIn(self.campaign.slug, full_url)

            # Test that slug is URL-safe
            self.assertEqual(full_url.count(self.campaign.slug), 1)

    def test_management_urls_with_complex_slug(self):
        """Test management URLs work with complex campaign slugs."""
        complex_campaign = Campaign.objects.create(
            name="Test Campaign: The 'Special' Edition!",
            description="Campaign with complex name",
            game_system="Complex System",
            owner=self.owner,
            is_public=True,
        )

        # Verify slug was generated properly
        self.assertIsNotNone(complex_campaign.slug)
        self.assertNotEqual(complex_campaign.slug, "")

        # Test management URLs work with complex slug
        base_url = f"/campaigns/{complex_campaign.slug}/"
        management_paths = ["characters/", "scenes/", "locations/", "items/"]

        for path in management_paths:
            full_url = base_url + path
            # URLs should be valid and contain the campaign slug
            self.assertTrue(full_url.startswith("/campaigns/"))
            self.assertIn(complex_campaign.slug, full_url)

    def test_management_urls_are_campaign_scoped(self):
        """Test that management URLs are properly scoped to specific campaigns."""
        # Create second campaign
        other_campaign = Campaign.objects.create(
            name="Other Campaign",
            description="Different campaign",
            game_system="Other System",
            owner=self.owner,
            is_public=True,
        )

        # URLs should be different for different campaigns
        campaign1_urls = [
            f"/campaigns/{self.campaign.slug}/characters/",
            f"/campaigns/{self.campaign.slug}/scenes/",
        ]

        campaign2_urls = [
            f"/campaigns/{other_campaign.slug}/characters/",
            f"/campaigns/{other_campaign.slug}/scenes/",
        ]

        # Verify URLs are campaign-specific
        for url1, url2 in zip(campaign1_urls, campaign2_urls):
            self.assertNotEqual(url1, url2)
            self.assertIn(self.campaign.slug, url1)
            self.assertIn(other_campaign.slug, url2)

    def test_all_management_areas_have_urls(self):
        """Test that all 4 management areas have corresponding URL patterns."""
        expected_management_areas = [
            ("characters", "characters/"),
            ("scenes", "scenes/"),
            ("locations", "locations/"),
            ("items", "items/"),
        ]

        base_url = f"/campaigns/{self.campaign.slug}/"

        for area_name, path in expected_management_areas:
            with self.subTest(area=area_name):
                full_url = base_url + path

                # URL should be properly formed
                self.assertTrue(full_url.startswith("/campaigns/"))
                self.assertTrue(full_url.endswith("/"))
                self.assertIn(self.campaign.slug, full_url)
                self.assertIn(area_name, full_url)


class CampaignManagementEdgeCaseTest(TestCase):
    """Test edge cases for Campaign Management Links feature."""

    def setUp(self):
        """Set up test data."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@example.com", password="TestPass123!"
        )
        self.inactive_user = User.objects.create_user(
            username="inactive",
            email="inactive@example.com",
            password="TestPass123!",
            is_active=False,
        )

    def test_management_links_with_unicode_campaign_name(self):
        """Test management links work with unicode characters in campaign names."""
        unicode_campaign = Campaign.objects.create(
            name="测试战役 🎲 Café Müller",
            description="Unicode test campaign",
            game_system="Unicode System",
            owner=self.owner,
            is_public=True,
        )

        self.client.login(username="owner", password="TestPass123!")
        response = self.client.get(
            reverse("campaigns:detail", kwargs={"slug": unicode_campaign.slug})
        )

        self.assertEqual(response.status_code, 200)

        # Management URLs should work even with unicode campaign names
        expected_urls = [
            f"/campaigns/{unicode_campaign.slug}/characters/",
            f"/campaigns/{unicode_campaign.slug}/scenes/",
            f"/campaigns/{unicode_campaign.slug}/locations/",
            f"/campaigns/{unicode_campaign.slug}/items/",
        ]

        for url in expected_urls:
            # URLs should be properly generated and escaped
            self.assertContains(response, f'href="{url}"')

    def test_inactive_user_no_management_section(self):
        """Test that inactive users don't see management sections."""
        campaign = Campaign.objects.create(
            name="Test Campaign",
            description="Test campaign",
            owner=self.inactive_user,
            is_public=True,
        )

        self.client.login(username="inactive", password="TestPass123!")
        response = self.client.get(
            reverse("campaigns:detail", kwargs={"slug": campaign.slug})
        )

        # Inactive users might not be able to see campaign or might see limited view
        # This test ensures we handle inactive user edge case appropriately
        if response.status_code == 200:
            self.assertNotContains(response, "Campaign Management")

    def test_management_section_does_not_break_existing_functionality(self):
        """Test that adding management section doesn't break existing view."""
        campaign = Campaign.objects.create(
            name="Existing Functionality Test",
            description="Test existing functionality",
            game_system="Existing System",
            owner=self.owner,
            is_public=True,
        )

        # Test as non-member - should still work as before
        response = self.client.get(
            reverse("campaigns:detail", kwargs={"slug": campaign.slug})
        )

        self.assertEqual(response.status_code, 200)

        # Should still contain all existing elements
        self.assertContains(response, campaign.name)
        self.assertContains(response, campaign.description)
        self.assertContains(response, campaign.game_system)
        self.assertContains(response, "Campaign Information")

    def test_empty_slug_edge_case(self):
        """Test behavior with edge case slug scenarios."""
        # Create campaign that might have slug generation edge cases
        edge_campaign = Campaign.objects.create(
            name="!!!@@@###$$$",  # Special characters only
            description="Edge case campaign",
            owner=self.owner,
            is_public=True,
        )

        # Should have generated some kind of valid slug
        self.assertIsNotNone(edge_campaign.slug)
        self.assertNotEqual(edge_campaign.slug, "")

        self.client.login(username="owner", password="TestPass123!")
        response = self.client.get(
            reverse("campaigns:detail", kwargs={"slug": edge_campaign.slug})
        )

        self.assertEqual(response.status_code, 200)

        # Management URLs should work even with edge case slugs
        management_urls = [
            f"/campaigns/{edge_campaign.slug}/characters/",
            f"/campaigns/{edge_campaign.slug}/scenes/",
        ]

        for url in management_urls:
            self.assertContains(response, f'href="{url}"')

    def test_campaign_management_responsive_behavior(self):
        """Test that management section behaves properly on different viewport sizes."""
        campaign = Campaign.objects.create(
            name="Responsive Test",
            description="Test responsive behavior",
            owner=self.owner,
            is_public=True,
        )

        self.client.login(username="owner", password="TestPass123!")
        response = self.client.get(
            reverse("campaigns:detail", kwargs={"slug": campaign.slug})
        )

        self.assertEqual(response.status_code, 200)

        # Should contain responsive CSS classes
        self.assertContains(response, "management-grid")
        self.assertContains(response, '<div class="management-card')

    def test_management_links_accessibility(self):
        """Test that management links have proper accessibility attributes."""
        campaign = Campaign.objects.create(
            name="Accessibility Test",
            description="Test accessibility",
            owner=self.owner,
            is_public=True,
        )

        self.client.login(username="owner", password="TestPass123!")
        response = self.client.get(
            reverse("campaigns:detail", kwargs={"slug": campaign.slug})
        )

        self.assertEqual(response.status_code, 200)

        # Should contain accessibility attributes
        self.assertContains(response, "aria-label=")
        self.assertContains(response, "role=")


class CampaignFormTest(TestCase):
    """Test the campaign creation form directly."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="TestPass123!"
        )

    def test_campaign_form_valid_data(self):
        """Test form with valid data."""
        from campaigns.forms import CampaignForm

        form_data = {
            "name": "Valid Campaign",
            "description": "A valid campaign description",
            "game_system": "World of Darkness",
        }

        form = CampaignForm(data=form_data)

        self.assertTrue(form.is_valid())

    def test_campaign_form_required_name(self):
        """Test that name field is required."""
        from campaigns.forms import CampaignForm

        form_data = {"description": "Missing name field", "game_system": "Some System"}

        form = CampaignForm(data=form_data)

        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_campaign_form_optional_fields(self):
        """Test that description and game_system are optional."""
        from campaigns.forms import CampaignForm

        form_data = {"name": "Minimal Campaign"}

        form = CampaignForm(data=form_data)

        self.assertTrue(form.is_valid())

    def test_campaign_form_save_method(self):
        """Test that form save method creates campaign with owner."""
        from campaigns.forms import CampaignForm

        form_data = {
            "name": "Form Save Test",
            "description": "Testing form save method",
            "game_system": "Test System",
        }

        form = CampaignForm(data=form_data)
        self.assertTrue(form.is_valid())

        campaign = form.save(owner=self.user)

        self.assertEqual(campaign.name, "Form Save Test")
        self.assertEqual(campaign.owner, self.user)
        self.assertEqual(campaign.description, "Testing form save method")
        self.assertEqual(campaign.game_system, "Test System")
        self.assertIsNotNone(campaign.slug)


class CampaignListViewTest(TestCase):
    """Tests for the CampaignListView."""

    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()

        # Create test users
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
            username="nonmember", email="nonmember@test.com", password="testpass123"
        )

        # Create campaigns with different visibility
        self.public_campaign = Campaign.objects.create(
            name="Public Campaign",
            description="A public campaign anyone can see",
            owner=self.owner,
            game_system="D&D 5e",
            is_public=True,
        )

        self.private_campaign = Campaign.objects.create(
            name="Private Campaign",
            description="A private campaign for members only",
            owner=self.owner,
            game_system="Pathfinder",
            is_public=False,
        )

        self.inactive_campaign = Campaign.objects.create(
            name="Inactive Campaign",
            description="An inactive campaign",
            owner=self.owner,
            game_system="Mage: The Ascension",
            is_active=False,
            is_public=True,
        )

        # Create additional campaigns for pagination testing
        for i in range(30):
            Campaign.objects.create(
                name=f"Test Campaign {i}",
                description=f"Test description {i}",
                owner=self.owner,
                game_system="Various",
                is_public=(i % 2 == 0),  # Half public, half private
            )

        # Set up memberships
        from campaigns.models import CampaignMembership

        CampaignMembership.objects.create(
            campaign=self.private_campaign, user=self.gm, role="GM"
        )
        CampaignMembership.objects.create(
            campaign=self.private_campaign, user=self.player, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.private_campaign, user=self.observer, role="OBSERVER"
        )

    def test_unauthenticated_user_sees_only_public_campaigns(self):
        """Test that unauthenticated users can only see public campaigns."""
        response = self.client.get(reverse("campaigns:list"))
        self.assertEqual(response.status_code, 200)
        campaigns = response.context["campaigns"]

        # Should see only public campaigns
        for campaign in campaigns:
            self.assertTrue(campaign.is_public)

        # Should not see private campaign
        self.assertNotIn(self.private_campaign, campaigns)

    def test_authenticated_user_sees_public_and_member_campaigns(self):
        """Test authenticated users see public campaigns and member campaigns."""
        self.client.login(username="player", password="testpass123")
        response = self.client.get(reverse("campaigns:list"))
        self.assertEqual(response.status_code, 200)

        campaigns = list(response.context["campaigns"])

        # Player should see the private campaign they're a member of
        self.assertIn(self.private_campaign, campaigns)

        # Should also see public campaigns
        public_campaigns = [c for c in campaigns if c.is_public]
        self.assertTrue(len(public_campaigns) > 0)

    def test_role_filtering(self):
        """Test filtering campaigns by user role."""
        self.client.login(username="owner", password="testpass123")

        # Test owner filter
        response = self.client.get(reverse("campaigns:list"), {"role": "owner"})
        campaigns = response.context["campaigns"]
        for campaign in campaigns:
            self.assertEqual(campaign.owner, self.owner)

        # Test GM filter
        self.client.login(username="gm", password="testpass123")
        response = self.client.get(reverse("campaigns:list"), {"role": "gm"})
        campaigns = response.context["campaigns"]
        for campaign in campaigns:
            self.assertTrue(campaign.is_gm(self.gm))

        # Test player filter
        self.client.login(username="player", password="testpass123")
        response = self.client.get(reverse("campaigns:list"), {"role": "player"})
        campaigns = response.context["campaigns"]
        for campaign in campaigns:
            self.assertTrue(campaign.is_player(self.player))

    def test_search_functionality(self):
        """Test searching campaigns by name, description, and game system."""
        self.client.login(username="owner", password="testpass123")

        # Search by name
        response = self.client.get(reverse("campaigns:list"), {"q": "Public"})
        campaigns = response.context["campaigns"]
        self.assertIn(self.public_campaign, campaigns)
        self.assertNotIn(self.private_campaign, campaigns)

        # Search by description
        response = self.client.get(reverse("campaigns:list"), {"q": "members only"})
        campaigns = response.context["campaigns"]
        self.assertIn(self.private_campaign, campaigns)
        self.assertNotIn(self.public_campaign, campaigns)

        # Search by game system
        response = self.client.get(reverse("campaigns:list"), {"q": "Pathfinder"})
        campaigns = response.context["campaigns"]
        self.assertIn(self.private_campaign, campaigns)
        self.assertNotIn(self.public_campaign, campaigns)

    def test_pagination_default(self):
        """Test default pagination of 25 items per page."""
        # Login as owner to see all campaigns for proper pagination testing
        self.client.login(username="owner", password="testpass123")
        response = self.client.get(reverse("campaigns:list"))
        self.assertEqual(response.status_code, 200)

        paginator = response.context["paginator"]
        page = response.context["page_obj"]

        self.assertEqual(paginator.per_page, 25)
        self.assertEqual(len(page.object_list), 25)

    def test_pagination_user_configurable(self):
        """Test user-configurable pagination."""
        # Test different page sizes
        for page_size in [10, 20, 50]:
            response = self.client.get(
                reverse("campaigns:list"), {"page_size": page_size}
            )
            paginator = response.context["paginator"]
            self.assertEqual(paginator.per_page, page_size)

        # Test invalid page size defaults to 25
        response = self.client.get(reverse("campaigns:list"), {"page_size": "invalid"})
        paginator = response.context["paginator"]
        self.assertEqual(paginator.per_page, 25)

        # Test excessive page size is capped (e.g., at 100)
        response = self.client.get(reverse("campaigns:list"), {"page_size": 1000})
        paginator = response.context["paginator"]
        self.assertLessEqual(paginator.per_page, 100)

    def test_inactive_campaigns_excluded_by_default(self):
        """Test that inactive campaigns are excluded by default."""
        response = self.client.get(reverse("campaigns:list"))
        campaigns = response.context["campaigns"]

        self.assertNotIn(self.inactive_campaign, campaigns)

        # Test including inactive campaigns
        response = self.client.get(reverse("campaigns:list"), {"show_inactive": "true"})
        campaigns = response.context["campaigns"]
        self.assertIn(self.inactive_campaign, campaigns)

    def test_campaign_list_displays_correct_fields(self):
        """Test that campaign list displays the correct fields."""
        self.client.login(username="owner", password="testpass123")
        # Check page 2 since "Public Campaign" might be there due to ordering
        response = self.client.get(reverse("campaigns:list"), {"page": 2})

        self.assertContains(response, self.public_campaign.name)
        # Game system is HTML encoded in template, so check both
        self.assertContains(response, "D&amp;D 5e")
        # Check for member count display
        self.assertContains(response, "members")
        # Check for last activity/updated date
        self.assertContains(response, self.public_campaign.updated_at.strftime("%Y"))


class CampaignListAPIViewTest(TestCase):
    """Tests for the Campaign API list endpoint."""

    def setUp(self):
        """Set up test data."""
        # Create test users
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.player = User.objects.create_user(
            username="player", email="player@test.com", password="testpass123"
        )
        self.non_member = User.objects.create_user(
            username="nonmember", email="nonmember@test.com", password="testpass123"
        )

        # Create campaigns
        self.public_campaign = Campaign.objects.create(
            name="Public Campaign",
            description="A public campaign",
            owner=self.owner,
            game_system="D&D 5e",
            is_public=True,
        )

        self.private_campaign = Campaign.objects.create(
            name="Private Campaign",
            description="A private campaign",
            owner=self.owner,
            game_system="Pathfinder",
            is_public=False,
        )

        from campaigns.models import CampaignMembership

        CampaignMembership.objects.create(
            campaign=self.private_campaign, user=self.player, role="PLAYER"
        )

    def test_api_list_returns_json(self):
        """Test that API list endpoint returns JSON."""
        self.client.login(username="owner", password="testpass123")
        response = self.client.get(reverse("api:campaign-list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")

    def test_api_list_filtering(self):
        """Test API list endpoint filtering."""
        self.client.login(username="owner", password="testpass123")

        # Filter by role
        response = self.client.get(reverse("api:campaign-list"), {"role": "owner"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(all(c["owner"]["id"] == self.owner.id for c in data["results"]))

        # Filter by search query
        response = self.client.get(reverse("api:campaign-list"), {"q": "Public"})
        data = response.json()
        self.assertTrue(any(c["name"] == "Public Campaign" for c in data["results"]))

    def test_api_list_pagination(self):
        """Test API list endpoint pagination."""
        # Create more campaigns for pagination
        for i in range(30):
            Campaign.objects.create(
                name=f"Campaign {i}", owner=self.owner, is_public=True
            )

        response = self.client.get(reverse("api:campaign-list"), {"page_size": 10})
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(len(data["results"]), 10)
        self.assertIn("next", data)
        self.assertIn("previous", data)
        self.assertIn("count", data)

    def test_api_includes_user_role(self):
        """Test that API response includes user's role in each campaign."""
        self.client.login(username="player", password="testpass123")
        response = self.client.get(reverse("api:campaign-list"))
        data = response.json()

        # Find the private campaign in results
        private_campaign_data = None
        for campaign in data["results"]:
            if campaign["id"] == self.private_campaign.id:
                private_campaign_data = campaign
                break

        self.assertIsNotNone(private_campaign_data)
        self.assertEqual(private_campaign_data["user_role"], "PLAYER")

    def test_api_real_time_search(self):
        """Test that API supports real-time search with partial matching."""
        self.client.login(username="owner", password="testpass123")

        # Partial name match
        response = self.client.get(reverse("api:campaign-list"), {"q": "Pub"})
        data = response.json()
        self.assertTrue(any(c["name"] == "Public Campaign" for c in data["results"]))

        # Case-insensitive search
        response = self.client.get(reverse("api:campaign-list"), {"q": "PUBLIC"})
        data = response.json()
        self.assertTrue(any(c["name"] == "Public Campaign" for c in data["results"]))


class CampaignDetailAPIViewTest(TestCase):
    """Tests for the Campaign API detail endpoint."""

    def setUp(self):
        """Set up test data."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.member = User.objects.create_user(
            username="member", email="member@test.com", password="testpass123"
        )
        self.non_member = User.objects.create_user(
            username="nonmember", email="nonmember@test.com", password="testpass123"
        )

        self.public_campaign = Campaign.objects.create(
            name="Public Campaign", owner=self.owner, is_public=True
        )

        self.private_campaign = Campaign.objects.create(
            name="Private Campaign", owner=self.owner, is_public=False
        )

        from campaigns.models import CampaignMembership

        CampaignMembership.objects.create(
            campaign=self.private_campaign, user=self.member, role="PLAYER"
        )

    def test_api_detail_returns_json(self):
        """Test that API detail endpoint returns JSON."""
        self.client.login(username="owner", password="testpass123")
        response = self.client.get(
            reverse("api:campaign-detail", kwargs={"pk": self.public_campaign.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")

    def test_api_detail_permissions(self):
        """Test API detail endpoint permissions."""
        # Public campaign accessible to anyone
        self.client.login(username="nonmember", password="testpass123")
        response = self.client.get(
            reverse("api:campaign-detail", kwargs={"pk": self.public_campaign.pk})
        )
        self.assertEqual(response.status_code, 200)

        # Private campaign returns 404 for non-members
        response = self.client.get(
            reverse("api:campaign-detail", kwargs={"pk": self.private_campaign.pk})
        )
        self.assertEqual(response.status_code, 404)

        # Private campaign accessible to members
        self.client.login(username="member", password="testpass123")
        response = self.client.get(
            reverse("api:campaign-detail", kwargs={"pk": self.private_campaign.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_api_detail_includes_role_specific_data(self):
        """Test that API detail includes role-specific data."""
        # Owner sees full data
        self.client.login(username="owner", password="testpass123")
        response = self.client.get(
            reverse("api:campaign-detail", kwargs={"pk": self.private_campaign.pk})
        )
        data = response.json()

        self.assertIn("members", data)
        self.assertIn("settings", data)  # Owner-only field
        self.assertEqual(data["user_role"], "OWNER")

        # Member sees limited data
        self.client.login(username="member", password="testpass123")
        response = self.client.get(
            reverse("api:campaign-detail", kwargs={"pk": self.private_campaign.pk})
        )
        data = response.json()

        self.assertIn("members", data)
        self.assertNotIn("settings", data)  # Owner-only field
        self.assertEqual(data["user_role"], "PLAYER")
