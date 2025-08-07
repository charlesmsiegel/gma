"""
Tests for campaign views.

This module tests the web interface views for campaign creation and management,
including form handling, redirects, and authentication requirements.
"""

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import Client, TestCase
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
