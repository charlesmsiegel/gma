"""
Tests for campaign detail page button functionality.

This module tests the button rendering, URL generation, and permission-based
visibility for campaign detail page actions (Invite Users, Manage Members).
"""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from campaigns.models import Campaign, CampaignMembership

User = get_user_model()


class CampaignDetailButtonsTest(TestCase):
    """Test campaign detail page button functionality."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()

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
            username="nonmember", email="nonmember@test.com", password="testpass123"
        )
        self.anonymous_user = None  # For anonymous access tests

        # Create campaign (make it public so all users can access for testing)
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            slug="test-campaign",
            owner=self.owner,
            game_system="Mage: The Ascension",
            description="A test campaign",
            is_public=True,
        )

        # Create memberships for different roles
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm, role="GM"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.observer, role="OBSERVER"
        )

        # URLs
        self.detail_url = reverse(
            "campaigns:detail", kwargs={"slug": self.campaign.slug}
        )
        self.invite_url = reverse(
            "campaigns:send_invitation", kwargs={"slug": self.campaign.slug}
        )
        self.manage_members_url = reverse(
            "campaigns:manage_members", kwargs={"slug": self.campaign.slug}
        )

    def test_owner_sees_invite_and_manage_buttons_with_correct_urls(self):
        """Test that campaign owner sees both buttons with correct URLs."""
        self.client.login(username="owner", password="testpass123")
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'href="{self.invite_url}"')
        self.assertContains(response, f'href="{self.manage_members_url}"')
        self.assertContains(response, "Invite Users</a>")
        self.assertContains(response, "Manage Members</a>")

    def test_owner_buttons_not_href_hash(self):
        """Test that owner's buttons don't use href='#' placeholder."""
        self.client.login(username="owner", password="testpass123")
        response = self.client.get(self.detail_url)

        # Check that the specific buttons don't have href="#"
        content = response.content.decode()

        # Find Invite Users button line and verify it doesn't have href="#"
        invite_button_lines = [
            line for line in content.split("\n") if "Invite Users" in line
        ]
        self.assertTrue(invite_button_lines, "Invite Users button should be present")
        for line in invite_button_lines:
            if "btn" in line and "Invite Users" in line:
                self.assertNotIn(
                    'href="#"', line, "Invite Users button should not have href='#'"
                )

        # Find Manage Members button line and verify it doesn't have href="#"
        manage_button_lines = [
            line for line in content.split("\n") if "Manage Members" in line
        ]
        self.assertTrue(manage_button_lines, "Manage Members button should be present")
        for line in manage_button_lines:
            if "btn" in line and "Manage Members" in line:
                self.assertNotIn(
                    'href="#"', line, "Manage Members button should not have href='#'"
                )

    def test_gm_does_not_see_owner_buttons(self):
        """Test that GM users don't see Invite Users or Manage Members buttons."""
        self.client.login(username="gm", password="testpass123")
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Invite Users</a>")
        self.assertNotContains(response, "Manage Members</a>")

    def test_player_does_not_see_owner_buttons(self):
        """Test that player users don't see Invite Users or Manage Members buttons."""
        self.client.login(username="player", password="testpass123")
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Invite Users</a>")
        self.assertNotContains(response, "Manage Members</a>")

    def test_observer_does_not_see_owner_buttons(self):
        """Test that observer users don't see Invite Users or Manage Members buttons."""
        self.client.login(username="observer", password="testpass123")
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Invite Users</a>")
        self.assertNotContains(response, "Manage Members</a>")

    def test_non_member_does_not_see_owner_buttons(self):
        """Test that non-member users don't see owner buttons."""
        self.client.login(username="nonmember", password="testpass123")
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Invite Users</a>")
        self.assertNotContains(response, "Manage Members</a>")

    def test_anonymous_user_does_not_see_owner_buttons(self):
        """Test that anonymous users don't see owner buttons."""
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Invite Users</a>")
        self.assertNotContains(response, "Manage Members</a>")

    def test_owner_button_visibility_condition(self):
        """Test buttons only visible when user.is_authenticated and is_owner."""
        # Test owner (authenticated + is_owner = True)
        self.client.login(username="owner", password="testpass123")
        response = self.client.get(self.detail_url)
        self.assertContains(response, "Invite Users</a>")
        self.assertContains(response, "Manage Members</a>")

        # Test GM (authenticated + is_owner = False)
        self.client.login(username="gm", password="testpass123")
        response = self.client.get(self.detail_url)
        self.assertNotContains(response, "Invite Users</a>")
        self.assertNotContains(response, "Manage Members</a>")

        # Test anonymous (not authenticated)
        self.client.logout()
        response = self.client.get(self.detail_url)
        self.assertNotContains(response, "Invite Users</a>")
        self.assertNotContains(response, "Manage Members</a>")


class CampaignDetailButtonIntegrationTest(TestCase):
    """Integration tests for campaign detail page buttons."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()

        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            slug="test-campaign",
            owner=self.owner,
            game_system="Mage: The Ascension",
            description="A test campaign",
            is_public=True,
        )

        self.detail_url = reverse(
            "campaigns:detail", kwargs={"slug": self.campaign.slug}
        )
        self.invite_url = reverse(
            "campaigns:send_invitation", kwargs={"slug": self.campaign.slug}
        )
        self.manage_members_url = reverse(
            "campaigns:manage_members", kwargs={"slug": self.campaign.slug}
        )

    def test_invite_users_button_leads_to_correct_page(self):
        """Test that clicking Invite Users button leads to send invitation page."""
        self.client.login(username="owner", password="testpass123")

        # Navigate to invite page directly (simulating button click)
        response = self.client.get(self.invite_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Send Invitation")
        self.assertContains(response, self.campaign.name)

    def test_manage_members_button_leads_to_correct_page(self):
        """Test that clicking Manage Members button leads to manage members page."""
        self.client.login(username="owner", password="testpass123")

        # Navigate to manage members page directly (simulating button click)
        response = self.client.get(self.manage_members_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Member Management")
        self.assertContains(response, self.campaign.name)

    def test_button_urls_are_accessible_from_detail_page(self):
        """Test that the URLs generated for buttons are accessible."""
        self.client.login(username="owner", password="testpass123")

        # Get detail page to extract button URLs
        detail_response = self.client.get(self.detail_url)
        self.assertEqual(detail_response.status_code, 200)

        # Verify that the URLs in the template are accessible
        invite_response = self.client.get(self.invite_url)
        self.assertEqual(invite_response.status_code, 200)

        manage_response = self.client.get(self.manage_members_url)
        self.assertEqual(manage_response.status_code, 200)

    def test_non_owner_cannot_access_button_destinations(self):
        """Test that non-owners cannot access the pages the buttons lead to."""
        # Create a non-owner user
        User.objects.create_user(
            username="nonowner", email="nonowner@test.com", password="testpass123"
        )

        self.client.login(username="nonowner", password="testpass123")

        # Try to access invite page - should be forbidden or redirected
        invite_response = self.client.get(self.invite_url)
        self.assertIn(
            invite_response.status_code, [302, 403, 404]
        )  # 302=redirect, 403=forbidden, 404=not found

        # Try to access manage members page - should be forbidden or redirected
        manage_response = self.client.get(self.manage_members_url)
        self.assertIn(
            manage_response.status_code, [302, 403, 404]
        )  # 302=redirect, 403=forbidden, 404=not found


class CampaignDetailURLGenerationTest(TestCase):
    """Test URL generation for campaign detail buttons."""

    def setUp(self):
        """Set up test data."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            slug="special-campaign-slug",
            owner=self.owner,
            game_system="Mage: The Ascension",
            description="A test campaign",
            is_public=True,
        )

    def test_url_generation_with_campaign_slug(self):
        """Test that URLs are properly generated with campaign slug."""
        expected_invite_url = f"/campaigns/{self.campaign.slug}/send-invitation/"
        expected_manage_url = f"/campaigns/{self.campaign.slug}/members/"

        actual_invite_url = reverse(
            "campaigns:send_invitation", kwargs={"slug": self.campaign.slug}
        )
        actual_manage_url = reverse(
            "campaigns:manage_members", kwargs={"slug": self.campaign.slug}
        )

        self.assertEqual(actual_invite_url, expected_invite_url)
        self.assertEqual(actual_manage_url, expected_manage_url)

    def test_template_context_provides_correct_urls(self):
        """Test that the template context provides the correct URL variables."""
        self.client = Client()
        self.client.login(username="owner", password="testpass123")

        detail_url = reverse("campaigns:detail", kwargs={"slug": self.campaign.slug})
        response = self.client.get(detail_url)

        # Check that context contains the campaign object needed for URL generation
        self.assertEqual(response.context["campaign"].slug, self.campaign.slug)

        # Check that template can generate URLs with the campaign slug
        expected_invite_url = reverse(
            "campaigns:send_invitation", kwargs={"slug": self.campaign.slug}
        )
        expected_manage_url = reverse(
            "campaigns:manage_members", kwargs={"slug": self.campaign.slug}
        )

        self.assertContains(response, expected_invite_url)
        self.assertContains(response, expected_manage_url)


class CampaignDetailButtonPermissionEdgeCasesTest(TestCase):
    """Test edge cases for button permissions."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()

        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            slug="test-campaign",
            owner=self.owner,
            game_system="Mage: The Ascension",
            is_public=True,
        )

    def test_inactive_user_cannot_see_buttons(self):
        """Test that inactive users cannot see owner buttons."""
        self.owner.is_active = False
        self.owner.save()

        # Should not be able to login
        login_success = self.client.login(username="owner", password="testpass123")
        self.assertFalse(login_success)

        # Should not see buttons when accessing page
        detail_url = reverse("campaigns:detail", kwargs={"slug": self.campaign.slug})
        response = self.client.get(detail_url)

        self.assertNotContains(response, "Invite Users</a>")
        self.assertNotContains(response, "Manage Members</a>")

    def test_campaign_with_special_characters_in_slug(self):
        """Test URL generation works with special characters in campaign slug."""
        special_campaign = Campaign.objects.create(
            name="Special Campaign",
            slug="test-campaign-with-dashes",
            owner=self.owner,
            game_system="Mage: The Ascension",
            is_public=True,
        )

        self.client.login(username="owner", password="testpass123")

        detail_url = reverse("campaigns:detail", kwargs={"slug": special_campaign.slug})
        response = self.client.get(detail_url)

        expected_invite_url = reverse(
            "campaigns:send_invitation", kwargs={"slug": special_campaign.slug}
        )
        expected_manage_url = reverse(
            "campaigns:manage_members", kwargs={"slug": special_campaign.slug}
        )

        self.assertContains(response, expected_invite_url)
        self.assertContains(response, expected_manage_url)

    def test_button_visibility_with_different_authentication_states(self):
        """Test button visibility across different authentication states."""
        detail_url = reverse("campaigns:detail", kwargs={"slug": self.campaign.slug})

        # Test 1: Anonymous user
        response = self.client.get(detail_url)
        self.assertNotContains(response, "Invite Users</a>")
        self.assertNotContains(response, "Manage Members</a>")

        # Test 2: Authenticated owner
        self.client.login(username="owner", password="testpass123")
        response = self.client.get(detail_url)
        self.assertContains(response, "Invite Users</a>")
        self.assertContains(response, "Manage Members</a>")

        # Test 3: After logout
        self.client.logout()
        response = self.client.get(detail_url)
        self.assertNotContains(response, "Invite Users</a>")
        self.assertNotContains(response, "Manage Members</a>")
