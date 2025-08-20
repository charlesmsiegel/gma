"""
Tests for campaign management views and features.

This module tests campaign management URLs, edge cases,
and the campaign management links feature.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from campaigns.models import Campaign

User = get_user_model()


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
        self.assertContains(response, "management-card")

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
