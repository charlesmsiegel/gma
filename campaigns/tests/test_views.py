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
        self.client = Client()
        self.owner = User.objects.create_user(
            username="owner", email="owner@example.com", password="TestPass123!"
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
