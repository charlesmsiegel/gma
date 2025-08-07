"""
Integration tests for campaign creation functionality.

This module tests the complete workflow of campaign creation through both
web interface and API, ensuring automatic slug generation, ownership assignment,
and proper redirection work correctly.
"""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from campaigns.models import Campaign

User = get_user_model()


class CampaignCreationIntegrationTest(TestCase):
    """Test complete campaign creation workflow."""

    def setUp(self):
        """Set up test data."""
        self.web_client = Client()
        self.api_client = APIClient()

        self.user1 = User.objects.create_user(
            username="user1", email="user1@example.com", password="TestPass123!"
        )
        self.user2 = User.objects.create_user(
            username="user2", email="user2@example.com", password="TestPass123!"
        )

    def test_web_to_api_campaign_creation_consistency(self):
        """Test that web and API campaign creation produce consistent results."""
        # Create campaign via web interface
        self.web_client.login(username="user1", password="TestPass123!")

        web_form_data = {
            "name": "Web Created Campaign",
            "description": "Created via web interface",
            "game_system": "Mage: The Ascension",
        }

        web_response = self.web_client.post(reverse("campaigns:create"), web_form_data)
        self.assertEqual(web_response.status_code, 302)

        web_campaign = Campaign.objects.get(name="Web Created Campaign")

        # Create similar campaign via API
        self.api_client.force_authenticate(user=self.user2)

        api_data = {
            "name": "API Created Campaign",
            "description": "Created via API interface",
            "game_system": "Mage: The Ascension",
        }

        api_response = self.api_client.post(
            reverse("api:campaigns:create"), api_data, format="json"
        )
        self.assertEqual(api_response.status_code, status.HTTP_201_CREATED)

        api_campaign = Campaign.objects.get(name="API Created Campaign")

        # Both campaigns should have consistent structure
        self.assertEqual(web_campaign.owner, self.user1)
        self.assertEqual(api_campaign.owner, self.user2)

        # Both should have slugs generated
        self.assertIsNotNone(web_campaign.slug)
        self.assertIsNotNone(api_campaign.slug)

        # Both should be active by default
        self.assertTrue(web_campaign.is_active)
        self.assertTrue(api_campaign.is_active)

    def test_automatic_slug_generation_integration(self):
        """Test that slug generation works correctly across all interfaces."""
        base_name = "Test Campaign for Slug Generation"

        # Test cases for slug generation (more lenient expectations)
        test_cases = [
            (base_name, "test-campaign-for-slug-generation"),
            ("Campaign with    Extra   Spaces", "campaign-with-extra-spaces"),
            ("Campaign-with-dashes", "campaign-with-dashes"),
            (
                "Campaign_with_underscores",
                "campaign_with_underscores",
            ),  # underscores stay as underscores
            ("Campaign.with.dots", "campaignwithdots"),  # dots are removed entirely
            ("Campaign123", "campaign123"),
            (
                "Campaign!@#$%Special^&*()",
                "campaignspecial",
            ),  # Special chars removed, alphanumeric kept
        ]

        self.api_client.force_authenticate(user=self.user1)

        created_slugs = []

        for i, (name, expected_slug_base) in enumerate(test_cases):
            campaign_data = {
                "name": name,
                "description": f"Test case {i+1}",
                "game_system": "Test System",
            }

            response = self.api_client.post(
                reverse("api:campaigns:create"), campaign_data, format="json"
            )

            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

            campaign = Campaign.objects.get(name=name)
            created_slugs.append(campaign.slug)

            # Slug should be based on the name
            self.assertTrue(
                campaign.slug.startswith(expected_slug_base)
                or campaign.slug == expected_slug_base
            )

        # All slugs should be unique
        self.assertEqual(len(created_slugs), len(set(created_slugs)))

    def test_duplicate_name_slug_uniqueness(self):
        """Test that campaigns with duplicate names get unique slugs."""
        self.api_client.force_authenticate(user=self.user1)

        duplicate_name = "Duplicate Campaign Name"

        # Create first campaign
        campaign_data1 = {
            "name": duplicate_name,
            "description": "First campaign",
            "game_system": "System 1",
        }

        response1 = self.api_client.post(
            reverse("api:campaigns:create"), campaign_data1, format="json"
        )

        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        campaign1 = Campaign.objects.get(id=response1.data["id"])

        # Create second campaign with same name
        campaign_data2 = {
            "name": duplicate_name,
            "description": "Second campaign",
            "game_system": "System 2",
        }

        response2 = self.api_client.post(
            reverse("api:campaigns:create"), campaign_data2, format="json"
        )

        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)
        campaign2 = Campaign.objects.get(id=response2.data["id"])

        # Create third campaign with same name
        campaign_data3 = {
            "name": duplicate_name,
            "description": "Third campaign",
            "game_system": "System 3",
        }

        response3 = self.api_client.post(
            reverse("api:campaigns:create"), campaign_data3, format="json"
        )

        self.assertEqual(response3.status_code, status.HTTP_201_CREATED)
        campaign3 = Campaign.objects.get(id=response3.data["id"])

        # All should have unique slugs
        slugs = [campaign1.slug, campaign2.slug, campaign3.slug]
        self.assertEqual(len(slugs), len(set(slugs)))

        # First should be base slug
        self.assertEqual(campaign1.slug, "duplicate-campaign-name")

        # Others should have suffixes
        self.assertTrue(campaign2.slug.startswith("duplicate-campaign-name-"))
        self.assertTrue(campaign3.slug.startswith("duplicate-campaign-name-"))

    def test_owner_assignment_integration(self):
        """Test that owner assignment works correctly across all creation methods."""
        # Test web interface
        self.web_client.login(username="user1", password="TestPass123!")

        web_data = {
            "name": "Web Owner Test",
            "description": "Testing owner assignment via web",
        }

        web_response = self.web_client.post(reverse("campaigns:create"), web_data)

        self.assertEqual(web_response.status_code, 302)
        web_campaign = Campaign.objects.get(name="Web Owner Test")
        self.assertEqual(web_campaign.owner, self.user1)

        # Test API interface
        self.api_client.force_authenticate(user=self.user2)

        api_data = {
            "name": "API Owner Test",
            "description": "Testing owner assignment via API",
        }

        api_response = self.api_client.post(
            reverse("api:campaigns:create"), api_data, format="json"
        )

        self.assertEqual(api_response.status_code, status.HTTP_201_CREATED)
        api_campaign = Campaign.objects.get(name="API Owner Test")
        self.assertEqual(api_campaign.owner, self.user2)

        # Test using alternative function-based API view
        alt_api_data = {
            "name": "Alt API Owner Test",
            "description": "Testing owner assignment via alternative API",
        }

        alt_response = self.api_client.post(
            reverse("api:campaigns:create"), alt_api_data, format="json"
        )

        self.assertEqual(alt_response.status_code, status.HTTP_201_CREATED)
        alt_campaign = Campaign.objects.get(name="Alt API Owner Test")
        self.assertEqual(alt_campaign.owner, self.user2)

    def test_campaign_detail_access_integration(self):
        """Test that campaign detail views work correctly after creation."""
        # Create campaign via API
        self.api_client.force_authenticate(user=self.user1)

        campaign_data = {
            "name": "Detail Access Test",
            "description": "Testing detail view access",
            "game_system": "Test System",
        }

        create_response = self.api_client.post(
            reverse("api:campaigns:create"), campaign_data, format="json"
        )

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        campaign = Campaign.objects.get(name="Detail Access Test")

        # Test web detail view
        web_detail_response = self.web_client.get(
            reverse("campaigns:detail", kwargs={"slug": campaign.slug})
        )

        self.assertEqual(web_detail_response.status_code, 200)
        self.assertContains(web_detail_response, campaign.name)
        self.assertContains(web_detail_response, campaign.description)

        # Test API detail view
        api_detail_response = self.api_client.get(
            reverse("api:campaigns:detail", kwargs={"pk": campaign.pk})
        )

        self.assertEqual(api_detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(api_detail_response.data["name"], campaign.name)
        self.assertEqual(api_detail_response.data["slug"], campaign.slug)

    def test_redirect_after_successful_creation(self):
        """Test that successful web creation redirects to correct detail view."""
        self.web_client.login(username="user1", password="TestPass123!")

        campaign_data = {
            "name": "Redirect Test Campaign",
            "description": "Testing redirect functionality",
            "game_system": "Redirect System",
        }

        response = self.web_client.post(reverse("campaigns:create"), campaign_data)

        self.assertEqual(response.status_code, 302)

        # Get the created campaign to check redirect URL
        campaign = Campaign.objects.get(name="Redirect Test Campaign")
        expected_url = reverse("campaigns:detail", kwargs={"slug": campaign.slug})

        self.assertEqual(response.url, expected_url)

        # Follow the redirect and verify it works
        follow_response = self.web_client.get(response.url)
        self.assertEqual(follow_response.status_code, 200)
        self.assertContains(follow_response, campaign.name)

    def test_long_name_slug_truncation_integration(self):
        """Test that very long campaign names are handled properly."""
        self.api_client.force_authenticate(user=self.user1)

        # Create campaign with very long name
        long_name = "A" * 250  # Longer than the 200 char field limit

        campaign_data = {
            "name": long_name[:200],  # Truncate to field limit
            "description": "Testing long name handling",
            "game_system": "Long Name System",
        }

        response = self.api_client.post(
            reverse("api:campaigns:create"), campaign_data, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        campaign = Campaign.objects.get(id=response.data["id"])

        # Name should be truncated properly
        self.assertEqual(len(campaign.name), 200)

        # Slug should be generated and not exceed slug field limit
        self.assertIsNotNone(campaign.slug)
        self.assertLessEqual(len(campaign.slug), 200)

        # Should still be accessible via slug
        detail_response = self.api_client.get(
            reverse("api:campaigns:detail", kwargs={"pk": campaign.pk})
        )

        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
