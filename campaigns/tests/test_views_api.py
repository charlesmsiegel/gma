"""
Tests for campaign API views.

This module tests the API endpoints for campaign listing and detail views,
including filtering, pagination, permissions, and serialization.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from campaigns.models import Campaign

User = get_user_model()


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
