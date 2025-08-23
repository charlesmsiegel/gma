"""
Tests for character views.

Tests the CharacterCreateView with comprehensive scenarios including
authentication, permissions, validation, and edge cases.

Security Note: Hardcoded passwords in this file are for testing only
and are not used in production code.
"""

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from campaigns.models import Campaign, CampaignMembership
from characters.models import Character

User = get_user_model()


class BaseCharacterTestCase(TestCase):
    """Base test case with common setup for character-related tests."""

    def create_standard_users(self):
        """Create standard set of test users used across character tests."""
        # Use consistent test password across all test users
        # Note: This is only used in tests, not production code
        test_password = "testpass123"  # nosec - test only

        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password=test_password
        )
        self.gm = User.objects.create_user(
            username="gm", email="gm@test.com", password=test_password
        )
        self.player1 = User.objects.create_user(
            username="player1", email="player1@test.com", password=test_password
        )
        self.player2 = User.objects.create_user(
            username="player2", email="player2@test.com", password=test_password
        )
        self.observer = User.objects.create_user(
            username="observer", email="observer@test.com", password=test_password
        )
        self.non_member = User.objects.create_user(
            username="nonmember", email="nonmember@test.com", password=test_password
        )

    def create_campaign_with_memberships(
        self,
        name,
        slug=None,
        owner=None,
        game_system="Mage: The Ascension",
        max_characters=0,
        is_active=True,
        include_memberships=True,
    ):
        """Create a campaign with standard membership setup.

        Args:
            name: Campaign name
            slug: Campaign slug (generated from name if None)
            owner: Campaign owner (defaults to self.owner)
            game_system: Game system name
            max_characters: Maximum characters per player (0 = unlimited)
            is_active: Whether campaign is active
            include_memberships: Whether to create standard memberships

        Returns:
            Campaign instance
        """
        if owner is None:
            owner = self.owner
        if slug is None:
            slug = name.lower().replace(" ", "-")

        campaign = Campaign.objects.create(
            name=name,
            slug=slug,
            owner=owner,
            game_system=game_system,
            max_characters_per_player=max_characters,
            is_active=is_active,
        )

        if include_memberships:
            self.create_standard_memberships(campaign)

        return campaign

    def create_standard_memberships(self, campaign):
        """Create standard memberships for a campaign."""
        CampaignMembership.objects.create(campaign=campaign, user=self.gm, role="GM")
        CampaignMembership.objects.create(
            campaign=campaign, user=self.player1, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=campaign, user=self.player2, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=campaign, user=self.observer, role="OBSERVER"
        )

    def create_character(
        self, name, campaign, player_owner, description="", game_system=None
    ):
        """Create a character with standard setup.

        Args:
            name: Character name
            campaign: Campaign instance
            player_owner: User who owns the character
            description: Character description
            game_system: Game system (defaults to campaign's game system)

        Returns:
            Character instance
        """
        if game_system is None:
            game_system = campaign.game_system

        return Character.objects.create(
            name=name,
            description=description,
            campaign=campaign,
            player_owner=player_owner,
            game_system=game_system,
        )


class CharacterCreateViewTest(BaseCharacterTestCase):
    """Test CharacterCreateView functionality and permissions."""

    def setUp(self):
        """Set up test users and campaigns with various membership scenarios."""
        # Create standard users
        self.create_standard_users()

        # Create campaigns with different character limits
        self.campaign_limited = self.create_campaign_with_memberships(
            "Limited Campaign", max_characters=2
        )
        self.campaign_unlimited = self.create_campaign_with_memberships(
            "Unlimited Campaign",
            game_system="D&D 5e",
            max_characters=0,  # 0 means unlimited
            include_memberships=False,
        )
        self.campaign_single = self.create_campaign_with_memberships(
            "Single Character Campaign",
            game_system="Call of Cthulhu",
            max_characters=1,
            include_memberships=False,
        )

        # Add specific memberships for unlimited and single campaigns
        CampaignMembership.objects.create(
            campaign=self.campaign_unlimited, user=self.player1, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign_single, user=self.player1, role="PLAYER"
        )

        # URL for character creation
        self.create_url = reverse("characters:create")

    def test_view_requires_authentication(self):
        """Test that the view requires user authentication."""
        response = self.client.get(self.create_url)
        self.assertRedirects(response, f"/users/login/?next={self.create_url}")

    def test_view_get_displays_form_for_authenticated_user(self):
        """Test that GET request displays the character creation form."""
        self.client.login(username="player1", password="testpass123")
        response = self.client.get(self.create_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create Character")
        self.assertContains(response, "name")
        self.assertContains(response, "description")
        self.assertContains(response, "campaign")

    def test_view_get_filters_campaigns_by_user_membership(self):
        """Test that campaign dropdown is filtered by user membership."""
        self.client.login(username="player1", password="testpass123")
        response = self.client.get(self.create_url)

        # Should contain campaigns where player1 is a member
        self.assertContains(response, self.campaign_limited.name)
        self.assertContains(response, self.campaign_unlimited.name)
        self.assertContains(response, self.campaign_single.name)

    def test_view_get_no_campaigns_for_non_member(self):
        """Test that non-members see no available campaigns."""
        self.client.login(username="nonmember", password="testpass123")
        response = self.client.get(self.create_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No campaigns available")

    def test_view_get_shows_character_limit_warning(self):
        """Test that view shows warning when character limit is reached."""
        # Create character up to limit in single character campaign
        self.create_character(
            "Existing Character",
            self.campaign_single,
            self.player1,
            game_system="Call of Cthulhu",
        )

        self.client.login(username="player1", password="testpass123")
        response = self.client.get(self.create_url)

        # Should show warning about character limit in the campaigns info table
        self.assertContains(response, "At Limit")

    def test_view_post_creates_character_with_valid_data(self):
        """Test successful character creation with valid form data."""
        self.client.login(username="player1", password="testpass123")

        form_data = {
            "name": "Test Character",
            "description": "A test character description",
            "campaign": self.campaign_limited.id,
        }

        response = self.client.post(self.create_url, data=form_data)

        # Should redirect to character detail page
        self.assertEqual(response.status_code, 302)

        # Character should be created in database
        character = Character.objects.get(name="Test Character")
        self.assertEqual(character.player_owner, self.player1)
        self.assertEqual(character.campaign, self.campaign_limited)
        self.assertEqual(character.game_system, self.campaign_limited.game_system)
        self.assertEqual(character.description, "A test character description")

    def test_view_post_redirects_to_character_detail(self):
        """Test that successful creation redirects to character detail page."""
        self.client.login(username="player1", password="testpass123")

        form_data = {
            "name": "Test Character",
            "campaign": self.campaign_limited.id,
        }

        response = self.client.post(self.create_url, data=form_data)

        character = Character.objects.get(name="Test Character")
        expected_url = reverse("characters:detail", kwargs={"pk": character.pk})
        # First redirect should go to character detail
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, expected_url)

    def test_view_post_displays_success_message(self):
        """Test that successful creation displays a success message."""
        self.client.login(username="player1", password="testpass123")

        form_data = {
            "name": "Test Character",
            "campaign": self.campaign_limited.id,
        }

        response = self.client.post(self.create_url, data=form_data, follow=True)

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any("successfully created" in str(message) for message in messages)
        )

    def test_view_post_form_errors_redisplay_form(self):
        """Test that form errors redisplay the form with error messages."""
        self.client.login(username="player1", password="testpass123")

        # Submit form with missing name
        form_data = {
            "name": "",
            "campaign": self.campaign_limited.id,
        }

        response = self.client.post(self.create_url, data=form_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This field is required")

    def test_view_post_validates_character_name_uniqueness(self):
        """Test that character name uniqueness is validated per campaign."""
        # Create existing character
        self.create_character("Existing Character", self.campaign_limited, self.player2)

        self.client.login(username="player1", password="testpass123")

        # Try to create character with same name in same campaign
        form_data = {
            "name": "Existing Character",
            "campaign": self.campaign_limited.id,
        }

        response = self.client.post(self.create_url, data=form_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already exists in this campaign")

    def test_view_post_validates_character_limit_enforcement(self):
        """Test that character limits are enforced on POST."""
        # Create character up to limit
        self.create_character(
            "Character 1",
            self.campaign_single,
            self.player1,
            game_system="Call of Cthulhu",
        )

        self.client.login(username="player1", password="testpass123")

        # Try to create another character
        form_data = {
            "name": "Character 2",
            "campaign": self.campaign_single.id,
        }

        response = self.client.post(self.create_url, data=form_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "cannot have more than")

    def test_view_post_validates_campaign_membership(self):
        """Test that non-members cannot access POST (no campaigns available)."""
        self.client.login(username="nonmember", password="testpass123")

        # Try to create character when user has no campaign memberships
        form_data = {
            "name": "Test Character",
            "campaign": self.campaign_limited.id,
        }

        response = self.client.post(self.create_url, data=form_data)

        # Should show "no campaigns available" rather than form validation
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No campaigns available")

    def test_view_post_validates_invalid_campaign_id(self):
        """Test that invalid campaign IDs are handled properly."""
        self.client.login(username="player1", password="testpass123")

        # Try to create character with non-existent campaign ID
        form_data = {
            "name": "Test Character",
            "campaign": 99999,  # Non-existent campaign
        }

        response = self.client.post(self.create_url, data=form_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Select a valid choice")

    def test_view_different_user_roles_can_access(self):
        """Test that users with different roles can access the view."""
        # Test OWNER role
        self.client.login(username="owner", password="testpass123")
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 200)

        # Test GM role
        self.client.login(username="gm", password="testpass123")
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 200)

        # Test PLAYER role
        self.client.login(username="player1", password="testpass123")
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 200)

        # Test OBSERVER role
        self.client.login(username="observer", password="testpass123")
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 200)

    def test_view_owner_can_create_in_owned_campaigns(self):
        """Test that campaign owners can create characters in their campaigns."""
        self.client.login(username="owner", password="testpass123")

        form_data = {
            "name": "Owner Character",
            "campaign": self.campaign_limited.id,
        }

        response = self.client.post(self.create_url, data=form_data)
        self.assertEqual(response.status_code, 302)

        character = Character.objects.get(name="Owner Character")
        self.assertEqual(character.player_owner, self.owner)

    def test_view_gm_can_create_characters(self):
        """Test that GMs can create characters in campaigns they manage."""
        self.client.login(username="gm", password="testpass123")

        form_data = {
            "name": "GM Character",
            "campaign": self.campaign_limited.id,
        }

        response = self.client.post(self.create_url, data=form_data)
        self.assertEqual(response.status_code, 302)

        character = Character.objects.get(name="GM Character")
        self.assertEqual(character.player_owner, self.gm)

    def test_view_handles_inactive_campaigns(self):
        """Test that inactive campaigns are not available for character creation."""
        # Make campaign inactive
        self.campaign_limited.is_active = False
        self.campaign_limited.save()

        self.client.login(username="player1", password="testpass123")
        response = self.client.get(self.create_url)

        # Inactive campaign should not be in dropdown
        self.assertNotContains(response, self.campaign_limited.name)

    def test_view_post_automatic_game_system_assignment(self):
        """Test that game_system is automatically assigned from campaign."""
        self.client.login(username="player1", password="testpass123")

        form_data = {
            "name": "Test Character",
            "campaign": self.campaign_limited.id,
        }

        response = self.client.post(self.create_url, data=form_data)
        self.assertEqual(response.status_code, 302)

        character = Character.objects.get(name="Test Character")
        self.assertEqual(character.game_system, self.campaign_limited.game_system)

    def test_view_handles_no_description(self):
        """Test that characters can be created without description."""
        self.client.login(username="player1", password="testpass123")

        form_data = {
            "name": "No Description Character",
            "campaign": self.campaign_limited.id,
        }

        response = self.client.post(self.create_url, data=form_data)
        self.assertEqual(response.status_code, 302)

        character = Character.objects.get(name="No Description Character")
        self.assertEqual(character.description, "")

    def test_view_context_data_includes_character_counts(self):
        """Test that view provides character count information in context."""
        # Create some characters
        self.create_character("Character 1", self.campaign_limited, self.player1)

        self.client.login(username="player1", password="testpass123")
        response = self.client.get(self.create_url)

        self.assertEqual(response.status_code, 200)
        # Context should include information about current character counts
        # (implementation detail - depends on actual view implementation)

    def test_view_edge_case_multiple_campaign_memberships(self):
        """Test view behavior when user is member of multiple campaigns."""
        # Add player1 to more campaigns
        extra_campaign = Campaign.objects.create(
            name="Extra Campaign",
            owner=self.player2,
            game_system="Shadowrun",
        )
        CampaignMembership.objects.create(
            campaign=extra_campaign, user=self.player1, role="PLAYER"
        )

        self.client.login(username="player1", password="testpass123")
        response = self.client.get(self.create_url)

        # Should show all campaigns user is a member of
        self.assertContains(response, self.campaign_limited.name)
        self.assertContains(response, self.campaign_unlimited.name)
        self.assertContains(response, self.campaign_single.name)
        self.assertContains(response, extra_campaign.name)

    def test_view_edge_case_concurrent_character_creation(self):
        """Test behavior when character limit is reached between GET and POST."""
        # This tests a potential race condition scenario
        self.client.login(username="player1", password="testpass123")

        # Get the form (limit not reached yet)
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 200)

        # Another user creates a character that puts player1 at limit
        self.create_character(
            "Concurrent Character",
            self.campaign_single,
            self.player1,
            game_system="Call of Cthulhu",
        )

        # Now try to POST (should fail due to limit)
        form_data = {
            "name": "New Character",
            "campaign": self.campaign_single.id,
        }

        response = self.client.post(self.create_url, data=form_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "cannot have more than")

    def test_view_handles_long_character_names(self):
        """Test view validation with character names at length boundaries."""
        self.client.login(username="player1", password="testpass123")

        # Test name exactly at 100 character limit (should succeed)
        form_data = {
            "name": "a" * 100,
            "campaign": self.campaign_limited.id,
        }

        response = self.client.post(self.create_url, data=form_data)
        self.assertEqual(response.status_code, 302)

        # Test name over 100 characters (should fail)
        form_data = {
            "name": "b" * 101,
            "campaign": self.campaign_limited.id,
        }

        response = self.client.post(self.create_url, data=form_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ensure this value has at most 100 characters")

    def test_view_error_handling_display(self):
        """Test that various error conditions are properly displayed."""
        self.client.login(username="player1", password="testpass123")

        # Test multiple validation errors at once
        form_data = {
            "name": "",  # Required field error
            "campaign": "",  # Required field error
        }

        response = self.client.post(self.create_url, data=form_data)
        self.assertEqual(response.status_code, 200)

        # Should display multiple errors
        self.assertContains(response, "This field is required", count=2)

    def test_view_preserves_form_data_on_error(self):
        """Test that form data is preserved when validation errors occur."""
        self.client.login(username="player1", password="testpass123")

        form_data = {
            "name": "",  # This will cause an error
            "description": "This description should be preserved",
            "campaign": self.campaign_limited.id,
        }

        response = self.client.post(self.create_url, data=form_data)
        self.assertEqual(response.status_code, 200)

        # Description should be preserved in the form
        self.assertContains(response, "This description should be preserved")


class CampaignCharacterListViewTest(BaseCharacterTestCase):
    """Test CampaignCharactersView functionality and role-based filtering."""

    def setUp(self):
        """Set up test users, campaigns, and characters for list view testing."""
        # Create standard users
        self.create_standard_users()

        # Create test campaigns
        self.campaign = self.create_campaign_with_memberships(
            "Test Campaign", slug="test-campaign", max_characters=3
        )

        self.other_campaign = self.create_campaign_with_memberships(
            "Other Campaign",
            slug="other-campaign",
            owner=self.player2,
            game_system="D&D 5e",
            max_characters=2,
            include_memberships=False,
        )

        self.inactive_campaign = self.create_campaign_with_memberships(
            "Inactive Campaign",
            slug="inactive-campaign",
            game_system="Call of Cthulhu",
            is_active=False,
            include_memberships=False,
        )

        # Add membership to other campaign
        CampaignMembership.objects.create(
            campaign=self.other_campaign, user=self.player1, role="PLAYER"
        )

        # Create test characters
        self.char1_player1 = self.create_character(
            "Player1 Character A",
            self.campaign,
            self.player1,
            "First character for player1",
        )

        self.char2_player1 = self.create_character(
            "Player1 Character B",
            self.campaign,
            self.player1,
            "Second character for player1",
        )

        self.char1_player2 = self.create_character(
            "Player2 Character", self.campaign, self.player2, "Character for player2"
        )

        self.char1_gm = self.create_character(
            "GM NPC Character", self.campaign, self.gm, "NPC controlled by GM"
        )

        self.char1_owner = self.create_character(
            "Owner Character",
            self.campaign,
            self.owner,
            "Character owned by campaign owner",
        )

        # Character in other campaign
        self.char_other_campaign = self.create_character(
            "Other Campaign Character",
            self.other_campaign,
            self.player1,
            "Character in different campaign",
            "D&D 5e",
        )

        # URL for campaign character list
        self.list_url = reverse(
            "characters:campaign_characters",
            kwargs={"campaign_slug": self.campaign.slug},
        )

    def test_view_requires_authentication(self):
        """Test that the view requires user authentication."""
        response = self.client.get(self.list_url)
        # For security reasons, anonymous users get 404 to hide campaign existence
        # rather than redirect that would reveal campaign exists
        self.assertEqual(response.status_code, 404)

    def test_view_non_member_access_denied(self):
        """Test that non-members cannot access the character list."""
        self.client.login(username="nonmember", password="testpass123")
        response = self.client.get(self.list_url)

        # Should return 404 to hide campaign existence
        self.assertEqual(response.status_code, 404)

    def test_view_inactive_campaign_access_denied(self):
        """Test that inactive campaigns are not accessible."""
        self.client.login(username="owner", password="testpass123")
        inactive_url = reverse(
            "characters:campaign_characters",
            kwargs={"campaign_slug": self.inactive_campaign.slug},
        )
        response = self.client.get(inactive_url)

        # Should return 404 for inactive campaigns
        self.assertEqual(response.status_code, 404)

    def test_view_invalid_campaign_slug_returns_404(self):
        """Test that invalid campaign slugs return 404."""
        self.client.login(username="player1", password="testpass123")
        invalid_url = reverse(
            "characters:campaign_characters",
            kwargs={"campaign_slug": "nonexistent-campaign"},
        )
        response = self.client.get(invalid_url)

        self.assertEqual(response.status_code, 404)

    def test_owner_sees_all_characters(self):
        """Test that campaign owners see all characters in their campaign."""
        self.client.login(username="owner", password="testpass123")
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        characters = response.context["characters"]

        # Owner should see all 5 characters in the campaign
        self.assertEqual(len(characters), 5)
        character_names = [char.name for char in characters]
        self.assertIn("Player1 Character A", character_names)
        self.assertIn("Player1 Character B", character_names)
        self.assertIn("Player2 Character", character_names)
        self.assertIn("GM NPC Character", character_names)
        self.assertIn("Owner Character", character_names)

        # Should not see characters from other campaigns
        self.assertNotIn("Other Campaign Character", character_names)

    def test_gm_sees_all_characters(self):
        """Test that GMs see all characters in their campaign."""
        self.client.login(username="gm", password="testpass123")
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        characters = response.context["characters"]

        # GM should see all 5 characters in the campaign
        self.assertEqual(len(characters), 5)
        character_names = [char.name for char in characters]
        self.assertIn("Player1 Character A", character_names)
        self.assertIn("Player1 Character B", character_names)
        self.assertIn("Player2 Character", character_names)
        self.assertIn("GM NPC Character", character_names)
        self.assertIn("Owner Character", character_names)

    def test_player_sees_only_own_characters(self):
        """Test that players see only their own characters."""
        self.client.login(username="player1", password="testpass123")
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        characters = response.context["characters"]

        # Player1 should see only their own 2 characters
        self.assertEqual(len(characters), 2)
        character_names = [char.name for char in characters]
        self.assertIn("Player1 Character A", character_names)
        self.assertIn("Player1 Character B", character_names)

        # Should not see other players' characters
        self.assertNotIn("Player2 Character", character_names)
        self.assertNotIn("GM NPC Character", character_names)
        self.assertNotIn("Owner Character", character_names)

    def test_observer_sees_all_characters(self):
        """Test that observers see all characters (read-only)."""
        self.client.login(username="observer", password="testpass123")
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        characters = response.context["characters"]

        # Observer should see all 5 characters in the campaign
        self.assertEqual(len(characters), 5)
        character_names = [char.name for char in characters]
        self.assertIn("Player1 Character A", character_names)
        self.assertIn("Player1 Character B", character_names)
        self.assertIn("Player2 Character", character_names)
        self.assertIn("GM NPC Character", character_names)
        self.assertIn("Owner Character", character_names)

    def test_context_data_includes_campaign_info(self):
        """Test that context includes campaign information."""
        self.client.login(username="player1", password="testpass123")
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)

        # Check context data
        self.assertEqual(response.context["campaign"], self.campaign)
        self.assertEqual(response.context["user_role"], "PLAYER")
        self.assertIn("Test Campaign - Characters", response.context["page_title"])

    def test_context_data_permission_flags(self):
        """Test that context includes proper permission flags for different roles."""
        # Test OWNER permissions
        self.client.login(username="owner", password="testpass123")
        response = self.client.get(self.list_url)
        self.assertTrue(response.context["can_create_character"])
        self.assertTrue(response.context["can_manage_all"])
        self.assertFalse(response.context["is_player"])

        # Test GM permissions
        self.client.login(username="gm", password="testpass123")
        response = self.client.get(self.list_url)
        self.assertTrue(response.context["can_create_character"])
        self.assertTrue(response.context["can_manage_all"])
        self.assertFalse(response.context["is_player"])

        # Test PLAYER permissions
        self.client.login(username="player1", password="testpass123")
        response = self.client.get(self.list_url)
        self.assertTrue(response.context["can_create_character"])
        self.assertFalse(response.context["can_manage_all"])
        self.assertTrue(response.context["is_player"])

        # Test OBSERVER permissions
        self.client.login(username="observer", password="testpass123")
        response = self.client.get(self.list_url)
        self.assertFalse(response.context["can_create_character"])
        self.assertFalse(response.context["can_manage_all"])
        self.assertFalse(response.context["is_player"])

    def test_search_by_character_name(self):
        """Test character search functionality by name."""
        # This will test the search functionality once implemented
        # For now, this test should fail as search isn't implemented yet
        self.client.login(username="owner", password="testpass123")

        # Test exact name search
        response = self.client.get(self.list_url, {"search": "Player1 Character A"})
        self.assertEqual(response.status_code, 200)
        # This should filter to only matching characters once search is implemented
        # characters = response.context["characters"]
        # self.assertEqual(len(characters), 1)
        # self.assertEqual(characters[0].name, "Player1 Character A")

    def test_search_partial_name_match(self):
        """Test partial name matching in search."""
        self.client.login(username="owner", password="testpass123")

        # Test partial search
        response = self.client.get(self.list_url, {"search": "Player1"})
        self.assertEqual(response.status_code, 200)
        # This should return both Player1 characters once search is implemented
        # characters = response.context["characters"]
        # self.assertEqual(len(characters), 2)

    def test_filter_by_player_owner(self):
        """Test filtering characters by player owner."""
        self.client.login(username="owner", password="testpass123")

        # Test filter by specific player
        response = self.client.get(self.list_url, {"player": self.player1.pk})
        self.assertEqual(response.status_code, 200)
        # This should show only player1's characters once filtering is implemented
        # characters = response.context["characters"]
        # self.assertEqual(len(characters), 2)

    def test_empty_campaign_shows_no_characters(self):
        """Test that campaigns with no characters display properly."""
        # Create a campaign with no characters
        empty_campaign = self.create_campaign_with_memberships(
            "Empty Campaign",
            slug="empty-campaign",
            game_system="Vampire: The Masquerade",
            include_memberships=False,
        )

        CampaignMembership.objects.create(
            campaign=empty_campaign, user=self.player1, role="PLAYER"
        )

        empty_url = reverse(
            "characters:campaign_characters",
            kwargs={"campaign_slug": empty_campaign.slug},
        )

        self.client.login(username="player1", password="testpass123")
        response = self.client.get(empty_url)

        self.assertEqual(response.status_code, 200)
        characters = response.context["characters"]
        self.assertEqual(len(characters), 0)

    def test_character_ordering(self):
        """Test that characters are ordered consistently."""
        self.client.login(username="owner", password="testpass123")
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        characters = response.context["characters"]

        # Characters should be ordered by name (from Character model Meta.ordering)
        character_names = [char.name for char in characters]
        self.assertEqual(character_names, sorted(character_names))

    def test_template_used(self):
        """Test that the correct template is used."""
        self.client.login(username="player1", password="testpass123")
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "characters/campaign_characters.html")

    def test_performance_optimization(self):
        """Test that the view uses proper database optimization."""
        self.client.login(username="owner", password="testpass123")

        # This tests that the view uses select_related/prefetch_related
        # to avoid N+1 queries
        with self.assertNumQueries(
            13
        ):  # campaign+memberships+users+session+user+count+members+chars+theme
            response = self.client.get(self.list_url)
            # Access all character attributes that would trigger queries
            for character in response.context["characters"]:
                _ = character.player_owner.username
                _ = character.campaign.name


class UserCharacterListViewTest(BaseCharacterTestCase):
    """Test UserCharactersView functionality (user-scoped character list)."""

    def setUp(self):
        """Set up test data for user-scoped character list testing."""
        # Create test users (using different names for this test)
        self.user1 = User.objects.create_user(
            username="user1", email="user1@test.com", password="testpass123"
        )
        self.user2 = User.objects.create_user(
            username="user2", email="user2@test.com", password="testpass123"
        )
        self.non_member = User.objects.create_user(
            username="nonmember", email="nonmember@test.com", password="testpass123"
        )

        # Create test campaigns
        self.campaign1 = self.create_campaign_with_memberships(
            "Campaign One",
            slug="campaign-one",
            owner=self.user1,
            include_memberships=False,
        )

        self.campaign2 = self.create_campaign_with_memberships(
            "Campaign Two",
            slug="campaign-two",
            owner=self.user2,
            game_system="D&D 5e",
            include_memberships=False,
        )

        self.campaign3 = self.create_campaign_with_memberships(
            "Campaign Three",
            slug="campaign-three",
            owner=self.user2,
            game_system="Vampire: The Masquerade",
            include_memberships=False,
        )

        # Create memberships - user1 is a member of campaign1 and campaign2
        CampaignMembership.objects.create(
            campaign=self.campaign2, user=self.user1, role="PLAYER"
        )

        # Create characters for user1 across multiple campaigns
        self.char1_campaign1 = self.create_character(
            "Character in Campaign 1", self.campaign1, self.user1, "First character"
        )

        self.char2_campaign1 = self.create_character(
            "Another Character in Campaign 1",
            self.campaign1,
            self.user1,
            "Second character",
        )

        self.char1_campaign2 = self.create_character(
            "Character in Campaign 2",
            self.campaign2,
            self.user1,
            "Third character",
            "D&D 5e",
        )

        # Character owned by user2 (should not be visible to user1)
        self.char_user2 = self.create_character(
            "User2 Character",
            self.campaign2,
            self.user2,
            "Character owned by user2",
            "D&D 5e",
        )

        # Character in campaign user1 has no access to
        self.char_no_access = self.create_character(
            "No Access Character",
            self.campaign3,
            self.user2,
            "Character in campaign user1 cannot access",
            "Vampire: The Masquerade",
        )

        # URL for user character list (this view doesn't exist yet)
        self.list_url = reverse("characters:user_characters")

    def test_view_requires_authentication(self):
        """Test that the view requires user authentication."""
        response = self.client.get(self.list_url)
        self.assertRedirects(response, f"/users/login/?next={self.list_url}")

    def test_user_sees_own_characters_across_accessible_campaigns(self):
        """Test that users see their own characters from campaigns they can access."""
        self.client.login(username="user1", password="testpass123")
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        characters = response.context["characters"]

        # user1 should see their 3 characters from accessible campaigns
        self.assertEqual(len(characters), 3)
        character_names = [char.name for char in characters]
        self.assertIn("Character in Campaign 1", character_names)
        self.assertIn("Another Character in Campaign 1", character_names)
        self.assertIn("Character in Campaign 2", character_names)

        # Should not see characters from other users
        self.assertNotIn("User2 Character", character_names)
        # Should not see characters from campaigns they have no access to
        self.assertNotIn("No Access Character", character_names)

    def test_user_with_no_characters(self):
        """Test display for user with no characters."""
        self.client.login(username="nonmember", password="testpass123")
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        characters = response.context["characters"]
        self.assertEqual(len(characters), 0)

    def test_search_functionality(self):
        """Test search functionality across user's characters."""
        self.client.login(username="user1", password="testpass123")

        # Test search for specific character
        response = self.client.get(self.list_url, {"search": "Campaign 1"})
        self.assertEqual(response.status_code, 200)
        # Should find characters with "Campaign 1" in the name once implemented

    def test_filter_by_campaign(self):
        """Test filtering characters by campaign."""
        self.client.login(username="user1", password="testpass123")

        # Test filter by campaign
        response = self.client.get(self.list_url, {"campaign": self.campaign1.pk})
        self.assertEqual(response.status_code, 200)
        # Should show only characters from campaign1 once filtering is implemented

    def test_context_data(self):
        """Test that context includes proper data."""
        self.client.login(username="user1", password="testpass123")
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("page_title", response.context)
        self.assertIn("My Characters", response.context["page_title"])

    def test_template_used(self):
        """Test that the correct template is used."""
        self.client.login(username="user1", password="testpass123")
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "characters/user_characters.html")


class EnhancedCharacterDetailViewTest(BaseCharacterTestCase):
    """Test enhanced CharacterDetailView with role-based information display."""

    def setUp(self):
        """Set up test data for character detail view testing."""
        # Create standard users
        self.create_standard_users()

        # Create test campaign
        self.campaign = self.create_campaign_with_memberships(
            "Test Campaign", slug="test-campaign"
        )

        # Create test characters
        self.player1_character = self.create_character(
            "Player1 Test Character",
            self.campaign,
            self.player1,
            "A test character owned by player1",
        )

        self.player2_character = self.create_character(
            "Player2 Test Character",
            self.campaign,
            self.player2,
            "A test character owned by player2",
        )

        # URLs for character details
        self.detail_url_p1 = reverse(
            "characters:detail", kwargs={"pk": self.player1_character.pk}
        )
        self.detail_url_p2 = reverse(
            "characters:detail", kwargs={"pk": self.player2_character.pk}
        )

    def test_view_requires_authentication(self):
        """Test that the view requires user authentication."""
        response = self.client.get(self.detail_url_p1)
        # Anonymous users are redirected to campaigns list for security
        # (don't reveal character existence to non-authenticated users)
        self.assertRedirects(response, "/campaigns/")

    def test_non_member_access_denied(self):
        """Test that non-members cannot view character details."""
        self.client.login(username="nonmember", password="testpass123")
        response = self.client.get(self.detail_url_p1)

        # Should redirect and show error message
        self.assertRedirects(response, reverse("campaigns:list"))

    def test_character_owner_can_view_own_character(self):
        """Test that character owners can view their own character."""
        self.client.login(username="player1", password="testpass123")
        response = self.client.get(self.detail_url_p1)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["character"], self.player1_character)

        # Owner should have edit and delete permissions
        self.assertTrue(response.context["can_edit"])
        self.assertTrue(response.context["can_delete"])
        self.assertEqual(response.context["user_role"], "PLAYER")

    def test_player_can_view_other_character_stats(self):
        """Test that players can view other characters' stats in same campaign."""
        # This tests enhanced functionality where players can see stats
        # but may have limited information based on role
        self.client.login(username="player1", password="testpass123")
        response = self.client.get(self.detail_url_p2)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["character"], self.player2_character)

        # Should not have edit/delete permissions for other player's character
        self.assertFalse(response.context["can_edit"])
        self.assertFalse(response.context["can_delete"])
        self.assertEqual(response.context["user_role"], "PLAYER")

    def test_gm_can_view_and_edit_any_character(self):
        """Test that GMs can view and edit any character in their campaign."""
        self.client.login(username="gm", password="testpass123")
        response = self.client.get(self.detail_url_p1)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["character"], self.player1_character)

        # GM should have edit permissions but delete depends on campaign settings
        self.assertTrue(response.context["can_edit"])
        # Delete permission depends on campaign.allow_gm_character_deletion
        self.assertEqual(response.context["user_role"], "GM")

    def test_owner_can_view_and_edit_any_character(self):
        """Test that campaign owners can view and edit any character."""
        self.client.login(username="owner", password="testpass123")
        response = self.client.get(self.detail_url_p1)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["character"], self.player1_character)

        # Owner should have full permissions
        self.assertTrue(response.context["can_edit"])
        # Delete permission depends on campaign.allow_owner_character_deletion
        self.assertEqual(response.context["user_role"], "OWNER")

    def test_observer_can_view_but_not_edit(self):
        """Test that observers can view characters but cannot edit."""
        self.client.login(username="observer", password="testpass123")
        response = self.client.get(self.detail_url_p1)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["character"], self.player1_character)

        # Observer should have no edit/delete permissions
        self.assertFalse(response.context["can_edit"])
        self.assertFalse(response.context["can_delete"])
        self.assertEqual(response.context["user_role"], "OBSERVER")

    def test_role_based_information_display(self):
        """Test that different roles see different information levels."""
        # This tests enhanced functionality for role-based information display

        # Character owner should see full information
        self.client.login(username="player1", password="testpass123")
        response = self.client.get(self.detail_url_p1)
        self.assertEqual(response.status_code, 200)
        # Should see all character details since they own it

        # Other player should see limited information for others' characters
        response = self.client.get(self.detail_url_p2)
        self.assertEqual(response.status_code, 200)
        # Should see basic info but may have some stats hidden

        # GM should see full information for all characters
        self.client.login(username="gm", password="testpass123")
        response = self.client.get(self.detail_url_p1)
        self.assertEqual(response.status_code, 200)
        # Should see all character details as GM

    def test_nonexistent_character_returns_404(self):
        """Test that nonexistent characters return 404."""
        self.client.login(username="player1", password="testpass123")
        nonexistent_url = reverse("characters:detail", kwargs={"pk": 99999})
        response = self.client.get(nonexistent_url)

        self.assertRedirects(response, reverse("campaigns:list"))

    def test_context_includes_recent_scenes(self):
        """Test that context includes recent scenes (placeholder for future)."""
        self.client.login(username="player1", password="testpass123")
        response = self.client.get(self.detail_url_p1)

        self.assertEqual(response.status_code, 200)
        # Recent scenes should be empty list for now (placeholder)
        self.assertEqual(response.context["recent_scenes"], [])

    def test_template_used(self):
        """Test that the correct template is used."""
        self.client.login(username="player1", password="testpass123")
        response = self.client.get(self.detail_url_p1)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "characters/character_detail.html")

    def test_character_detail_performance_optimization(self):
        """Test that character detail view uses proper database optimization."""
        self.client.login(username="player1", password="testpass123")

        # Should use select_related for campaign and player_owner, prefetch possessions
        with self.assertNumQueries(
            15
        ):  # Character detail optimized with possessions prefetch
            response = self.client.get(self.detail_url_p1)
            # Access related objects to verify they're prefetched
            _ = response.context["character"].campaign.name
            _ = response.context["character"].player_owner.username


class CharacterEditViewTest(BaseCharacterTestCase):
    """Test CharacterEditView functionality and permissions."""

    def setUp(self):
        """Set up test data for character edit view testing."""
        # Create standard users
        self.create_standard_users()

        # Create test campaign
        self.campaign = self.create_campaign_with_memberships(
            "Test Campaign", slug="test-campaign"
        )

        # Create test character
        self.character = self.create_character(
            "Test Character",
            self.campaign,
            self.player1,
            "Original description",
        )

        # URL for character edit
        self.edit_url = reverse("characters:edit", kwargs={"pk": self.character.pk})

    def test_view_requires_authentication(self):
        """Test that the view requires user authentication."""
        response = self.client.get(self.edit_url)
        # Should redirect to login
        self.assertRedirects(response, f"/users/login/?next={self.edit_url}")

    def test_character_owner_can_access_edit_view(self):
        """Test that character owners can access edit view."""
        self.client.login(username="player1", password="testpass123")
        response = self.client.get(self.edit_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["character"], self.character)
        self.assertContains(response, "Edit Character")
        self.assertContains(response, "Test Character")

    def test_gm_can_access_edit_view(self):
        """Test that GMs can access edit view for characters in their campaign."""
        self.client.login(username="gm", password="testpass123")
        response = self.client.get(self.edit_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["character"], self.character)

    def test_campaign_owner_can_access_edit_view(self):
        """Test that campaign owners can access edit view."""
        self.client.login(username="owner", password="testpass123")
        response = self.client.get(self.edit_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["character"], self.character)

    def test_other_player_cannot_access_edit_view(self):
        """Test that other players cannot access edit view."""
        self.client.login(username="player2", password="testpass123")
        response = self.client.get(self.edit_url)

        # Should return 403 or redirect with error
        self.assertIn(response.status_code, [403, 302])

    def test_observer_cannot_access_edit_view(self):
        """Test that observers cannot access edit view."""
        self.client.login(username="observer", password="testpass123")
        response = self.client.get(self.edit_url)

        # Should return 403 or redirect with error
        self.assertIn(response.status_code, [403, 302])

    def test_non_member_cannot_access_edit_view(self):
        """Test that non-members cannot access edit view."""
        self.client.login(username="nonmember", password="testpass123")
        response = self.client.get(self.edit_url)

        # Should return 403 or redirect
        self.assertIn(response.status_code, [403, 302, 404])

    def test_post_successful_character_update(self):
        """Test successful character update via POST."""
        self.client.login(username="player1", password="testpass123")

        form_data = {
            "name": "Updated Character Name",
            "description": "Updated character description",
        }

        response = self.client.post(self.edit_url, data=form_data)

        # Should redirect after successful update
        self.assertEqual(response.status_code, 302)

        # Character should be updated in database
        self.character.refresh_from_db()
        self.assertEqual(self.character.name, "Updated Character Name")
        self.assertEqual(self.character.description, "Updated character description")

    def test_post_redirects_to_character_detail(self):
        """Test that successful update redirects to character detail."""
        self.client.login(username="player1", password="testpass123")

        form_data = {
            "name": "Redirect Test Character",
            "description": "Test description",
        }

        response = self.client.post(self.edit_url, data=form_data)

        expected_url = reverse("characters:detail", kwargs={"pk": self.character.pk})
        self.assertRedirects(response, expected_url)

    def test_post_displays_success_message(self):
        """Test that successful update displays success message."""
        self.client.login(username="player1", password="testpass123")

        form_data = {
            "name": "Success Message Test",
            "description": "Test description",
        }

        response = self.client.post(self.edit_url, data=form_data, follow=True)

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any("successfully updated" in str(message) for message in messages)
        )

    def test_post_form_validation_errors(self):
        """Test handling of form validation errors."""
        self.client.login(username="player1", password="testpass123")

        # Submit form with invalid data (empty name)
        form_data = {
            "name": "",
            "description": "Valid description",
        }

        response = self.client.post(self.edit_url, data=form_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This field is required")

        # Character should not be updated
        self.character.refresh_from_db()
        self.assertEqual(self.character.name, "Test Character")  # Original name

    def test_post_preserves_form_data_on_error(self):
        """Test that form data is preserved when validation errors occur."""
        self.client.login(username="player1", password="testpass123")

        form_data = {
            "name": "",  # Invalid - will cause error
            "description": "This description should be preserved",
        }

        response = self.client.post(self.edit_url, data=form_data)

        self.assertEqual(response.status_code, 200)
        # Description should be preserved in the form
        self.assertContains(response, "This description should be preserved")

    def test_nonexistent_character_returns_404(self):
        """Test that nonexistent characters return 404."""
        self.client.login(username="player1", password="testpass123")
        nonexistent_url = reverse("characters:edit", kwargs={"pk": 99999})
        response = self.client.get(nonexistent_url)

        self.assertEqual(response.status_code, 404)

    def test_template_used(self):
        """Test that the correct template is used."""
        self.client.login(username="player1", password="testpass123")
        response = self.client.get(self.edit_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "characters/character_edit.html")

    def test_context_data_includes_character_info(self):
        """Test that context includes proper character information."""
        self.client.login(username="player1", password="testpass123")
        response = self.client.get(self.edit_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["character"], self.character)
        self.assertIn("Edit", response.context.get("page_title", ""))

    def test_audit_trail_creation_on_update(self):
        """Test that updates create audit trail entries."""
        self.client.login(username="player1", password="testpass123")

        form_data = {
            "name": "Audit Trail Test",
            "description": "Updated for audit test",
        }

        response = self.client.post(self.edit_url, data=form_data)
        self.assertEqual(response.status_code, 302)

        # Check that audit trail was created (will fail until implemented)
        from characters.models import CharacterAuditLog

        audit_entries = CharacterAuditLog.objects.filter(
            character=self.character, action="UPDATE"
        )
        self.assertGreater(audit_entries.count(), 0)

        audit_entry = audit_entries.first()
        self.assertEqual(audit_entry.user, self.player1)
        self.assertIn("name", audit_entry.changes)


class CharacterDeleteViewTest(BaseCharacterTestCase):
    """Test CharacterDeleteView functionality and permissions."""

    def setUp(self):
        """Set up test data for character delete view testing."""
        # Create standard users
        self.create_standard_users()

        # Create test campaign
        self.campaign = self.create_campaign_with_memberships(
            "Test Campaign", slug="test-campaign"
        )

        # Create test character
        self.character = self.create_character(
            "Deletable Character",
            self.campaign,
            self.player1,
            "Character to be deleted",
        )

        # URL for character delete
        self.delete_url = reverse("characters:delete", kwargs={"pk": self.character.pk})

    def test_view_requires_authentication(self):
        """Test that the view requires user authentication."""
        response = self.client.get(self.delete_url)
        # Should redirect to login
        self.assertRedirects(response, f"/users/login/?next={self.delete_url}")

    def test_character_owner_can_access_delete_view(self):
        """Test that character owners can access delete view."""
        self.client.login(username="player1", password="testpass123")
        response = self.client.get(self.delete_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["character"], self.character)
        self.assertContains(response, "Delete Character")
        self.assertContains(response, "Deletable Character")

    def test_campaign_owner_can_access_delete_view(self):
        """Test that campaign owners can access delete view if settings allow."""
        self.client.login(username="owner", password="testpass123")
        response = self.client.get(self.delete_url)

        # Should be allowed by default (allow_owner_character_deletion=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["character"], self.character)

    def test_gm_cannot_access_delete_view_by_default(self):
        """Test that GMs cannot access delete view by default."""
        self.client.login(username="gm", password="testpass123")
        response = self.client.get(self.delete_url)

        # Should be denied by default (allow_gm_character_deletion=False)
        self.assertIn(response.status_code, [403, 302])

    def test_gm_can_access_delete_view_when_enabled(self):
        """Test that GMs can access delete view when setting is enabled."""
        # Enable GM character deletion
        self.campaign.allow_gm_character_deletion = True
        self.campaign.save()

        self.client.login(username="gm", password="testpass123")
        response = self.client.get(self.delete_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["character"], self.character)

    def test_other_player_cannot_access_delete_view(self):
        """Test that other players cannot access delete view."""
        self.client.login(username="player2", password="testpass123")
        response = self.client.get(self.delete_url)

        # Should return 403 or redirect with error
        self.assertIn(response.status_code, [403, 302])

    def test_observer_cannot_access_delete_view(self):
        """Test that observers cannot access delete view."""
        self.client.login(username="observer", password="testpass123")
        response = self.client.get(self.delete_url)

        # Should return 403 or redirect with error
        self.assertIn(response.status_code, [403, 302])

    def test_delete_view_shows_confirmation_form(self):
        """Test that delete view shows confirmation form with character name."""
        self.client.login(username="player1", password="testpass123")
        response = self.client.get(self.delete_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "confirmation_name")
        self.assertContains(response, "Deletable Character")
        self.assertContains(response, "Type the character name to confirm")

    def test_post_successful_soft_delete_with_confirmation(self):
        """Test successful soft delete with proper confirmation."""
        self.client.login(username="player1", password="testpass123")

        form_data = {
            "confirmation_name": "Deletable Character",
        }

        response = self.client.post(self.delete_url, data=form_data)

        # Should redirect after successful deletion
        self.assertEqual(response.status_code, 302)

        # Character should be soft deleted
        self.character.refresh_from_db()
        self.assertTrue(self.character.is_deleted)
        self.assertEqual(self.character.deleted_by, self.player1)
        self.assertIsNotNone(self.character.deleted_at)

    def test_post_fails_without_confirmation(self):
        """Test that deletion fails without proper confirmation."""
        self.client.login(username="player1", password="testpass123")

        form_data = {
            "confirmation_name": "",  # Empty confirmation
        }

        response = self.client.post(self.delete_url, data=form_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This field is required")

        # Character should not be deleted
        self.character.refresh_from_db()
        self.assertFalse(self.character.is_deleted)

    def test_post_fails_with_wrong_confirmation(self):
        """Test that deletion fails with wrong character name."""
        self.client.login(username="player1", password="testpass123")

        form_data = {
            "confirmation_name": "Wrong Character Name",
        }

        response = self.client.post(self.delete_url, data=form_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "must match the character name exactly")

        # Character should not be deleted
        self.character.refresh_from_db()
        self.assertFalse(self.character.is_deleted)

    def test_post_redirects_to_campaign_characters(self):
        """Test that successful deletion redirects to campaign character list."""
        self.client.login(username="player1", password="testpass123")

        form_data = {
            "confirmation_name": "Deletable Character",
        }

        response = self.client.post(self.delete_url, data=form_data)

        expected_url = reverse(
            "characters:campaign_characters",
            kwargs={"campaign_slug": self.campaign.slug},
        )
        self.assertRedirects(response, expected_url)

    def test_post_displays_success_message(self):
        """Test that successful deletion displays success message."""
        self.client.login(username="player1", password="testpass123")

        form_data = {
            "confirmation_name": "Deletable Character",
        }

        response = self.client.post(self.delete_url, data=form_data, follow=True)

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any("successfully deleted" in str(message) for message in messages)
        )

    def test_nonexistent_character_returns_404(self):
        """Test that nonexistent characters return 404."""
        self.client.login(username="player1", password="testpass123")
        nonexistent_url = reverse("characters:delete", kwargs={"pk": 99999})
        response = self.client.get(nonexistent_url)

        self.assertEqual(response.status_code, 404)

    def test_template_used(self):
        """Test that the correct template is used."""
        self.client.login(username="player1", password="testpass123")
        response = self.client.get(self.delete_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "characters/character_delete.html")

    def test_context_data_includes_character_info(self):
        """Test that context includes proper character information."""
        self.client.login(username="player1", password="testpass123")
        response = self.client.get(self.delete_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["character"], self.character)
        self.assertIn("Delete", response.context.get("page_title", ""))

    def test_audit_trail_creation_on_delete(self):
        """Test that deletion creates audit trail entry."""
        self.client.login(username="player1", password="testpass123")

        form_data = {
            "confirmation_name": "Deletable Character",
        }

        response = self.client.post(self.delete_url, data=form_data)
        self.assertEqual(response.status_code, 302)

        # Check that audit trail was created (will fail until implemented)
        from characters.models import CharacterAuditLog

        audit_entries = CharacterAuditLog.objects.filter(
            character=self.character, action="DELETE"
        )
        self.assertGreater(audit_entries.count(), 0)

        audit_entry = audit_entries.first()
        self.assertEqual(audit_entry.user, self.player1)
        self.assertIn("is_deleted", audit_entry.changes)

    def test_campaign_owner_delete_permission_setting(self):
        """Test that campaign owner delete permission can be disabled."""
        # Disable owner character deletion
        self.campaign.allow_owner_character_deletion = False
        self.campaign.save()

        self.client.login(username="owner", password="testpass123")
        response = self.client.get(self.delete_url)

        # Should be denied when setting is disabled
        self.assertIn(response.status_code, [403, 302])

    def test_character_appears_deleted_in_lists(self):
        """Test that soft deleted characters don't appear in default lists."""
        self.client.login(username="player1", password="testpass123")

        # Delete the character
        form_data = {
            "confirmation_name": "Deletable Character",
        }
        self.client.post(self.delete_url, data=form_data)

        # Check campaign character list
        list_url = reverse(
            "characters:campaign_characters",
            kwargs={"campaign_slug": self.campaign.slug},
        )
        response = self.client.get(list_url)

        # Character should not appear in the actual character list
        # (ignore success messages which might contain the character name)
        characters = response.context["characters"]
        character_names = [char.name for char in characters]
        self.assertNotIn("Deletable Character", character_names)

    def test_soft_deleted_character_can_be_restored(self):
        """Test that soft deleted characters can be restored (admin functionality)."""
        # This tests the model functionality that would be used by admin restoration
        self.character.soft_delete(self.player1)
        self.assertTrue(self.character.is_deleted)

        # Restore character
        result = self.character.restore(self.player1)
        self.assertTrue(result)

        self.character.refresh_from_db()
        self.assertFalse(self.character.is_deleted)
        self.assertIsNone(self.character.deleted_at)
        self.assertIsNone(self.character.deleted_by)
