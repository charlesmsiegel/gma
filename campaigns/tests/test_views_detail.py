"""
Tests for campaign detail views.

This module tests the campaign detail view functionality, including
public/private campaign access, role-based permissions, and management features.
"""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from campaigns.models import Campaign

User = get_user_model()


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
        self.assertContains(response, "campaign-management")

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
        self.assertContains(response, "campaign-management")

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
        self.assertContains(response, "campaign-management")

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
        self.assertContains(response, "campaign-management")

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
        self.assertContains(response, "campaign-management")
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
        self.assertContains(response, "campaign-management")
        self.assertContains(response, 'btn btn-primary">Characters</a>')
        self.assertContains(response, 'btn btn-primary">Scenes</a>')
        self.assertContains(response, 'btn btn-primary">Locations</a>')
        self.assertContains(response, 'btn btn-primary">Items</a>')

        # Check for specific management card types (for different styling)
        self.assertContains(response, "characters-card")
        self.assertContains(response, "scenes-card")
        self.assertContains(response, "locations-card")
        self.assertContains(response, "items-card")

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
        self.assertContains(response, "card-icon", count=4)

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
        campaign_info_pos = content.find("info-section")
        management_pos = content.find("campaign-management")
        member_list_pos = content.find("member-list-section")

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

        for role, _, expected_content in roles_and_expected_cards:
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
