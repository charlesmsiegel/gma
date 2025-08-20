"""
Tests for campaign list views.

This module tests the campaign list view functionality, including
filtering, searching, pagination, and permission-based visibility.
"""

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse

from campaigns.models import Campaign

User = get_user_model()


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
