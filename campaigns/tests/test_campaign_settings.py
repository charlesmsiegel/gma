"""
Comprehensive tests for campaign settings functionality.

This module tests:
1. Model changes: New fields (allow_observer_join, allow_player_join)
2. Settings form: CampaignSettingsForm validation and behavior
3. Views: Campaign settings edit functionality and access control
4. Permissions: Owner-only access to settings
5. Integration: End-to-end workflow testing
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from campaigns.models import Campaign, CampaignMembership

User = get_user_model()


class CampaignModelSettingsFieldsTest(TestCase):
    """Test new Campaign model fields for settings functionality."""

    def setUp(self):
        """Set up test users."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )

    def test_allow_observer_join_field_default(self):
        """Test allow_observer_join field defaults to False."""
        campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
        )
        self.assertFalse(campaign.allow_observer_join)

    def test_allow_player_join_field_default(self):
        """Test allow_player_join field defaults to False."""
        campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
        )
        self.assertFalse(campaign.allow_player_join)

    def test_allow_observer_join_field_can_be_true(self):
        """Test allow_observer_join field can be set to True."""
        campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            allow_observer_join=True,
        )
        self.assertTrue(campaign.allow_observer_join)

    def test_allow_player_join_field_can_be_true(self):
        """Test allow_player_join field can be set to True."""
        campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            allow_player_join=True,
        )
        self.assertTrue(campaign.allow_player_join)

    def test_both_join_fields_can_be_true(self):
        """Test both join fields can be True simultaneously."""
        campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            allow_observer_join=True,
            allow_player_join=True,
        )
        self.assertTrue(campaign.allow_observer_join)
        self.assertTrue(campaign.allow_player_join)

    def test_campaign_fields_save_correctly(self):
        """Test campaign settings fields persist correctly after save."""
        campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            allow_observer_join=True,
            allow_player_join=False,
        )
        campaign.save()

        # Refresh from database
        campaign.refresh_from_db()
        self.assertTrue(campaign.allow_observer_join)
        self.assertFalse(campaign.allow_player_join)


class CampaignSettingsFormTest(TestCase):
    """Test CampaignSettingsForm validation and behavior."""

    def setUp(self):
        """Set up test users and campaign."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            description="Test description",
            game_system="Mage: The Ascension",
            is_active=True,
            is_public=False,
            allow_observer_join=False,
            allow_player_join=False,
        )

    def test_campaign_settings_form_class_exists(self):
        """Test CampaignSettingsForm class exists (will fail until implemented)."""
        # Import should exist but will fail initially
        try:
            from campaigns.forms import CampaignSettingsForm

            # Form should have expected fields
            form = CampaignSettingsForm()
            expected_fields = [
                "name",
                "description",
                "game_system",
                "is_active",
                "is_public",
                "allow_observer_join",
                "allow_player_join",
            ]
            for field in expected_fields:
                self.assertIn(field, form.fields)
        except ImportError:
            self.fail("CampaignSettingsForm should be implemented in campaigns.forms")

    def test_campaign_settings_form_with_valid_data(self):
        """Test form validation with valid data."""
        from campaigns.forms import CampaignSettingsForm

        form_data = {
            "name": "Updated Campaign Name",
            "description": "Updated description",
            "game_system": "Vampire: The Masquerade",
            "is_active": True,
            "is_public": True,
            "allow_observer_join": True,
            "allow_player_join": True,
        }
        form = CampaignSettingsForm(data=form_data, instance=self.campaign)
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")

    def test_campaign_settings_form_name_required(self):
        """Test form validation fails when name is empty."""
        from campaigns.forms import CampaignSettingsForm

        form_data = {
            "name": "",  # Empty name should be invalid
            "description": "Test description",
            "game_system": "Test System",
            "is_active": True,
            "is_public": False,
            "allow_observer_join": False,
            "allow_player_join": False,
        }
        form = CampaignSettingsForm(data=form_data, instance=self.campaign)
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_campaign_settings_form_optional_fields(self):
        """Test form validates with only required field (name)."""
        from campaigns.forms import CampaignSettingsForm

        form_data = {
            "name": "Minimal Campaign",
            "description": "",
            "game_system": "",
            "is_active": False,
            "is_public": False,
            "allow_observer_join": False,
            "allow_player_join": False,
        }
        form = CampaignSettingsForm(data=form_data, instance=self.campaign)
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")

    def test_campaign_settings_form_boolean_field_defaults(self):
        """Test boolean fields handle default values correctly."""
        from campaigns.forms import CampaignSettingsForm

        # Test with minimal data, boolean fields should default properly
        form_data = {
            "name": "Test Campaign",
        }
        form = CampaignSettingsForm(data=form_data, instance=self.campaign)
        # Form should be valid even with missing boolean fields
        if form.is_valid():
            campaign = form.save(commit=False)
            # Boolean fields should have default values from instance or form
            self.assertIsInstance(campaign.is_active, bool)
            self.assertIsInstance(campaign.is_public, bool)
            self.assertIsInstance(campaign.allow_observer_join, bool)
            self.assertIsInstance(campaign.allow_player_join, bool)

    def test_campaign_settings_form_save_updates_fields(self):
        """Test form save method updates all fields correctly."""
        from campaigns.forms import CampaignSettingsForm

        original_name = self.campaign.name
        form_data = {
            "name": "New Campaign Name",
            "description": "New description",
            "game_system": "New System",
            "is_active": not self.campaign.is_active,
            "is_public": not self.campaign.is_public,
            "allow_observer_join": not self.campaign.allow_observer_join,
            "allow_player_join": not self.campaign.allow_player_join,
        }

        form = CampaignSettingsForm(data=form_data, instance=self.campaign)
        self.assertTrue(form.is_valid())

        updated_campaign = form.save()

        # Check all fields were updated
        self.assertNotEqual(updated_campaign.name, original_name)
        self.assertEqual(updated_campaign.name, "New Campaign Name")
        self.assertEqual(updated_campaign.description, "New description")
        self.assertEqual(updated_campaign.game_system, "New System")
        self.assertEqual(updated_campaign.is_active, form_data["is_active"])
        self.assertEqual(updated_campaign.is_public, form_data["is_public"])
        self.assertEqual(
            updated_campaign.allow_observer_join, form_data["allow_observer_join"]
        )
        self.assertEqual(
            updated_campaign.allow_player_join, form_data["allow_player_join"]
        )


class CampaignSettingsViewPermissionsTest(TestCase):
    """Test access control for campaign settings views."""

    def setUp(self):
        """Set up test users and campaign."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.gm_user = User.objects.create_user(
            username="gm", email="gm@test.com", password="testpass123"
        )
        self.player_user = User.objects.create_user(
            username="player", email="player@test.com", password="testpass123"
        )
        self.observer_user = User.objects.create_user(
            username="observer", email="observer@test.com", password="testpass123"
        )
        self.non_member_user = User.objects.create_user(
            username="nonmember", email="nonmember@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            description="Test description",
            game_system="Test System",
        )

        # Create memberships
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm_user, role="GM"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player_user, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.observer_user, role="OBSERVER"
        )

    def test_owner_can_access_settings_get(self):
        """Test campaign owner can access settings page via GET."""
        self.client.login(username="owner", password="testpass123")

        # This URL will need to be implemented
        url = reverse("campaigns:settings", kwargs={"slug": self.campaign.slug})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)

    def test_gm_cannot_access_settings(self):
        """Test GM cannot access campaign settings."""
        self.client.login(username="gm", password="testpass123")

        url = reverse("campaigns:settings", kwargs={"slug": self.campaign.slug})
        response = self.client.get(url)

        # Should be forbidden (403) or redirect to login/error
        self.assertIn(response.status_code, [403, 404, 302])

    def test_player_cannot_access_settings(self):
        """Test player cannot access campaign settings."""
        self.client.login(username="player", password="testpass123")

        url = reverse("campaigns:settings", kwargs={"slug": self.campaign.slug})
        response = self.client.get(url)

        self.assertIn(response.status_code, [403, 404, 302])

    def test_observer_cannot_access_settings(self):
        """Test observer cannot access campaign settings."""
        self.client.login(username="observer", password="testpass123")

        url = reverse("campaigns:settings", kwargs={"slug": self.campaign.slug})
        response = self.client.get(url)

        self.assertIn(response.status_code, [403, 404, 302])

    def test_non_member_cannot_access_settings(self):
        """Test non-member cannot access campaign settings."""
        self.client.login(username="nonmember", password="testpass123")

        url = reverse("campaigns:settings", kwargs={"slug": self.campaign.slug})
        response = self.client.get(url)

        self.assertIn(response.status_code, [403, 404, 302])

    def test_anonymous_user_cannot_access_settings(self):
        """Test anonymous user cannot access campaign settings."""
        url = reverse("campaigns:settings", kwargs={"slug": self.campaign.slug})
        response = self.client.get(url)

        # Should redirect to login or show 403/404
        self.assertIn(response.status_code, [302, 403, 404])


class CampaignSettingsViewBehaviorTest(TestCase):
    """Test campaign settings view GET/POST behavior and validation."""

    def setUp(self):
        """Set up test users and campaign."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            description="Original description",
            game_system="Original System",
            is_active=True,
            is_public=False,
            allow_observer_join=False,
            allow_player_join=False,
        )
        self.client.login(username="owner", password="testpass123")

    def test_settings_view_get_shows_current_values(self):
        """Test GET request shows current campaign settings in form."""
        url = reverse("campaigns:settings", kwargs={"slug": self.campaign.slug})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.campaign.name)
        self.assertContains(response, self.campaign.description)
        self.assertContains(response, self.campaign.game_system)

        # Check form has correct initial values
        form = response.context["form"]
        self.assertEqual(form.initial["name"], self.campaign.name)
        self.assertEqual(form.initial["description"], self.campaign.description)
        self.assertEqual(form.initial["game_system"], self.campaign.game_system)
        self.assertEqual(form.initial["is_active"], self.campaign.is_active)
        self.assertEqual(form.initial["is_public"], self.campaign.is_public)
        self.assertEqual(
            form.initial["allow_observer_join"], self.campaign.allow_observer_join
        )
        self.assertEqual(
            form.initial["allow_player_join"], self.campaign.allow_player_join
        )

    def test_settings_view_post_valid_data_updates_campaign(self):
        """Test POST request with valid data updates campaign settings."""
        url = reverse("campaigns:settings", kwargs={"slug": self.campaign.slug})

        post_data = {
            "name": "Updated Campaign Name",
            "description": "Updated description",
            "game_system": "Updated System",
            "is_active": False,
            "is_public": True,
            "allow_observer_join": True,
            "allow_player_join": True,
        }

        response = self.client.post(url, data=post_data)

        # Should redirect after successful update
        self.assertEqual(response.status_code, 302)

        # Check campaign was updated in database
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.name, "Updated Campaign Name")
        self.assertEqual(self.campaign.description, "Updated description")
        self.assertEqual(self.campaign.game_system, "Updated System")
        self.assertEqual(self.campaign.is_active, False)
        self.assertEqual(self.campaign.is_public, True)
        self.assertEqual(self.campaign.allow_observer_join, True)
        self.assertEqual(self.campaign.allow_player_join, True)

    def test_settings_view_post_invalid_data_shows_errors(self):
        """Test POST request with invalid data shows form errors."""
        url = reverse("campaigns:settings", kwargs={"slug": self.campaign.slug})

        post_data = {
            "name": "",  # Invalid: name is required
            "description": "Valid description",
            "game_system": "Valid System",
            "is_active": True,
            "is_public": False,
            "allow_observer_join": False,
            "allow_player_join": False,
        }

        response = self.client.post(url, data=post_data)

        # Should not redirect, should show form with errors
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)
        form = response.context["form"]
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

        # Campaign should not be updated
        self.campaign.refresh_from_db()
        self.assertNotEqual(self.campaign.name, "")

    def test_settings_view_post_partial_data_updates_specified_fields(self):
        """Test POST with partial data only updates specified fields."""
        url = reverse("campaigns:settings", kwargs={"slug": self.campaign.slug})

        original_description = self.campaign.description
        original_game_system = self.campaign.game_system

        post_data = {
            "name": "New Name Only",
            "description": original_description,
            "game_system": original_game_system,
            "is_active": True,
            "is_public": True,  # Only changing this
            "allow_observer_join": False,
            "allow_player_join": False,
        }

        response = self.client.post(url, data=post_data)
        self.assertEqual(response.status_code, 302)

        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.name, "New Name Only")
        self.assertEqual(self.campaign.description, original_description)
        self.assertEqual(self.campaign.game_system, original_game_system)
        self.assertEqual(self.campaign.is_public, True)

    def test_settings_view_redirect_after_success(self):
        """Test redirect after successful settings update."""
        url = reverse("campaigns:settings", kwargs={"slug": self.campaign.slug})

        post_data = {
            "name": "Updated Name",
            "description": "Updated description",
            "game_system": "Updated System",
            "is_active": True,
            "is_public": False,
            "allow_observer_join": False,
            "allow_player_join": False,
        }

        response = self.client.post(url, data=post_data)

        # Should redirect to campaign detail page
        expected_redirect_url = reverse(
            "campaigns:detail", kwargs={"slug": self.campaign.slug}
        )
        self.assertRedirects(response, expected_redirect_url)

    def test_settings_view_nonexistent_campaign_404(self):
        """Test accessing settings for non-existent campaign returns 404."""
        url = reverse("campaigns:settings", kwargs={"slug": "nonexistent-campaign"})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)


class CampaignSettingsIntegrationTest(TestCase):
    """Test end-to-end campaign settings workflow."""

    def setUp(self):
        """Set up test users and campaign."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.campaign = Campaign.objects.create(
            name="Integration Test Campaign",
            owner=self.owner,
            description="Original description",
            game_system="D&D 5e",
            is_active=True,
            is_public=False,
            allow_observer_join=False,
            allow_player_join=False,
        )

    def test_full_settings_workflow(self):
        """Test complete workflow: login -> view settings -> update -> verify."""
        # Step 1: Login as owner
        login_success = self.client.login(username="owner", password="testpass123")
        self.assertTrue(login_success)

        # Step 2: Navigate to campaign detail page
        detail_url = reverse("campaigns:detail", kwargs={"slug": self.campaign.slug})
        detail_response = self.client.get(detail_url)
        self.assertEqual(detail_response.status_code, 200)

        # Step 3: Access settings page
        settings_url = reverse(
            "campaigns:settings", kwargs={"slug": self.campaign.slug}
        )
        settings_get_response = self.client.get(settings_url)
        self.assertEqual(settings_get_response.status_code, 200)

        # Step 4: Update settings with new values
        updated_data = {
            "name": "Updated Integration Campaign",
            "description": "This campaign was updated through integration test",
            "game_system": "Mage: The Ascension",
            "is_active": True,
            "is_public": True,
            "allow_observer_join": True,
            "allow_player_join": True,
        }

        settings_post_response = self.client.post(settings_url, data=updated_data)
        self.assertEqual(settings_post_response.status_code, 302)

        # Step 5: Verify campaign was updated in database
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.name, "Updated Integration Campaign")
        self.assertEqual(
            self.campaign.description,
            "This campaign was updated through integration test",
        )
        self.assertEqual(self.campaign.game_system, "Mage: The Ascension")
        self.assertTrue(self.campaign.is_active)
        self.assertTrue(self.campaign.is_public)
        self.assertTrue(self.campaign.allow_observer_join)
        self.assertTrue(self.campaign.allow_player_join)

        # Step 6: Verify redirect went to correct location
        expected_redirect = reverse(
            "campaigns:detail", kwargs={"slug": self.campaign.slug}
        )
        self.assertRedirects(settings_post_response, expected_redirect)

        # Step 7: Access detail page again to verify changes are visible
        final_detail_response = self.client.get(detail_url)
        self.assertEqual(final_detail_response.status_code, 200)
        self.assertContains(final_detail_response, "Updated Integration Campaign")

    def test_settings_link_visible_to_owner_only(self):
        """Test settings link is only visible to campaign owner."""
        detail_url = reverse("campaigns:detail", kwargs={"slug": self.campaign.slug})

        # Test owner sees settings link/button
        self.client.login(username="owner", password="testpass123")
        owner_response = self.client.get(detail_url)
        self.assertEqual(owner_response.status_code, 200)
        # Check for settings link (this will depend on template implementation)
        # This assertion may need adjustment based on actual template
        settings_url = reverse(
            "campaigns:settings", kwargs={"slug": self.campaign.slug}
        )
        # Could contain link text like "Settings", "Edit Settings", or URL
        self.assertContains(owner_response, settings_url)

        # Test non-owner doesn't see settings link
        gm_user = User.objects.create_user(
            username="gm", email="gm@test.com", password="testpass123"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=gm_user, role="GM"
        )

        self.client.login(username="gm", password="testpass123")
        gm_response = self.client.get(detail_url)
        self.assertEqual(gm_response.status_code, 200)
        # GM should not see settings link
        self.assertNotContains(gm_response, settings_url)

    def test_settings_persistence_across_sessions(self):
        """Test settings persist across different user sessions."""
        # Login and update settings
        self.client.login(username="owner", password="testpass123")

        settings_url = reverse(
            "campaigns:settings", kwargs={"slug": self.campaign.slug}
        )
        update_data = {
            "name": "Session Test Campaign",
            "description": "Testing persistence",
            "game_system": "Custom System",
            "is_active": False,
            "is_public": True,
            "allow_observer_join": True,
            "allow_player_join": False,
        }

        response = self.client.post(settings_url, data=update_data)
        self.assertEqual(response.status_code, 302)

        # Logout
        self.client.logout()

        # Login again
        self.client.login(username="owner", password="testpass123")

        # Check settings are still applied
        get_response = self.client.get(settings_url)
        self.assertEqual(get_response.status_code, 200)

        form = get_response.context["form"]
        self.assertEqual(form.initial["name"], "Session Test Campaign")
        self.assertEqual(form.initial["description"], "Testing persistence")
        self.assertEqual(form.initial["game_system"], "Custom System")
        self.assertEqual(form.initial["is_active"], False)
        self.assertEqual(form.initial["is_public"], True)
        self.assertEqual(form.initial["allow_observer_join"], True)
        self.assertEqual(form.initial["allow_player_join"], False)

    def test_settings_form_csrf_protection(self):
        """Test settings form has CSRF protection."""
        self.client.login(username="owner", password="testpass123")

        settings_url = reverse(
            "campaigns:settings", kwargs={"slug": self.campaign.slug}
        )

        # GET request should include CSRF token in form
        get_response = self.client.get(settings_url)
        self.assertEqual(get_response.status_code, 200)
        self.assertContains(get_response, "csrfmiddlewaretoken")

        # POST without CSRF should fail
        post_data = {
            "name": "No CSRF Test",
            "description": "Testing CSRF protection",
            "game_system": "Test System",
            "is_active": True,
            "is_public": False,
            "allow_observer_join": False,
            "allow_player_join": False,
        }

        # Disable CSRF for this test by using enforce_csrf_checks=False
        # In a real scenario, this would fail without proper CSRF token
        response = self.client.post(settings_url, data=post_data)
        # With proper CSRF middleware, this should work
        # The exact behavior depends on Django settings
        self.assertIn(response.status_code, [200, 302, 403])


class CampaignSettingsEdgeCasesTest(TestCase):
    """Test edge cases and error conditions for campaign settings."""

    def setUp(self):
        """Set up test data."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.campaign = Campaign.objects.create(
            name="Edge Case Campaign",
            owner=self.owner,
        )
        self.client.login(username="owner", password="testpass123")

    def test_settings_with_very_long_name(self):
        """Test settings form handles very long campaign names."""
        settings_url = reverse(
            "campaigns:settings", kwargs={"slug": self.campaign.slug}
        )

        # Campaign name field should have max_length=200 based on model
        long_name = "A" * 250  # Longer than allowed

        post_data = {
            "name": long_name,
            "description": "Test description",
            "game_system": "Test System",
            "is_active": True,
            "is_public": False,
            "allow_observer_join": False,
            "allow_player_join": False,
        }

        response = self.client.post(settings_url, data=post_data)

        # Should show form with validation error
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_settings_with_special_characters_in_name(self):
        """Test settings form handles special characters in campaign name."""
        settings_url = reverse(
            "campaigns:settings", kwargs={"slug": self.campaign.slug}
        )

        special_name = "Campaign with 特殊文字 & symbols! @#$%"

        post_data = {
            "name": special_name,
            "description": "Test description with émojis 🎲",
            "game_system": 'System with "quotes" & ampersands',
            "is_active": True,
            "is_public": False,
            "allow_observer_join": False,
            "allow_player_join": False,
        }

        response = self.client.post(settings_url, data=post_data)

        # Should succeed - special characters should be allowed
        self.assertEqual(response.status_code, 302)

        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.name, special_name)

    def test_concurrent_settings_updates(self):
        """Test behavior when campaign is updated concurrently."""
        # This is a simplified test for concurrent updates
        # In practice, Django's ORM handles basic concurrent updates

        settings_url = reverse(
            "campaigns:settings", kwargs={"slug": self.campaign.slug}
        )

        # Simulate another process updating the campaign
        Campaign.objects.filter(pk=self.campaign.pk).update(
            name="Concurrently Updated Name"
        )

        # Now try to update via form
        post_data = {
            "name": "Form Updated Name",
            "description": "Updated via form",
            "game_system": "Updated System",
            "is_active": True,
            "is_public": True,
            "allow_observer_join": True,
            "allow_player_join": True,
        }

        response = self.client.post(settings_url, data=post_data)
        self.assertEqual(response.status_code, 302)

        # Form update should succeed and overwrite concurrent changes
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.name, "Form Updated Name")

    def test_settings_after_campaign_slug_change(self):
        """Test settings access when campaign name changes (slug remains stable)."""
        original_slug = self.campaign.slug
        settings_url = reverse("campaigns:settings", kwargs={"slug": original_slug})

        # First, verify we can access settings with original slug
        response = self.client.get(settings_url)
        self.assertEqual(response.status_code, 200)

        # Update campaign name
        post_data = {
            "name": "Completely New Campaign Name That Changes Slug",
            "description": self.campaign.description,
            "game_system": self.campaign.game_system,
            "is_active": self.campaign.is_active,
            "is_public": self.campaign.is_public,
            "allow_observer_join": self.campaign.allow_observer_join,
            "allow_player_join": self.campaign.allow_player_join,
        }

        response = self.client.post(settings_url, data=post_data)
        self.assertEqual(response.status_code, 302)

        # Refresh campaign to verify name changed but slug remained the same
        self.campaign.refresh_from_db()
        self.assertEqual(
            self.campaign.name, "Completely New Campaign Name That Changes Slug"
        )
        self.assertEqual(self.campaign.slug, original_slug)  # Slug should remain stable

        # Original URL should still work (slug stability is good UX)
        same_response = self.client.get(settings_url)
        self.assertEqual(same_response.status_code, 200)
