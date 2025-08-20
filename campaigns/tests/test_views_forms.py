"""
Tests for campaign forms.

This module tests the campaign creation and management forms,
including validation, field requirements, and form save methods.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()


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
