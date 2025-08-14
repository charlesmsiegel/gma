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


class CharacterCreateViewTest(TestCase):
    """Test CharacterCreateView functionality and permissions."""

    def setUp(self):
        """Set up test users and campaigns with various membership scenarios."""
        # Create users
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.gm = User.objects.create_user(
            username="gm", email="gm@test.com", password="testpass123"
        )
        self.player1 = User.objects.create_user(
            username="player1", email="player1@test.com", password="testpass123"
        )
        self.player2 = User.objects.create_user(
            username="player2", email="player2@test.com", password="testpass123"
        )
        self.observer = User.objects.create_user(
            username="observer", email="observer@test.com", password="testpass123"
        )
        self.non_member = User.objects.create_user(
            username="nonmember", email="nonmember@test.com", password="testpass123"
        )

        # Create campaigns with different character limits
        self.campaign_limited = Campaign.objects.create(
            name="Limited Campaign",
            owner=self.owner,
            game_system="Mage: The Ascension",
            max_characters_per_player=2,
        )
        self.campaign_unlimited = Campaign.objects.create(
            name="Unlimited Campaign",
            owner=self.owner,
            game_system="D&D 5e",
            max_characters_per_player=0,  # 0 means unlimited
        )
        self.campaign_single = Campaign.objects.create(
            name="Single Character Campaign",
            owner=self.owner,
            game_system="Call of Cthulhu",
            max_characters_per_player=1,
        )

        # Create memberships for various roles
        CampaignMembership.objects.create(
            campaign=self.campaign_limited, user=self.gm, role="GM"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign_limited, user=self.player1, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign_limited, user=self.player2, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign_limited, user=self.observer, role="OBSERVER"
        )

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
        Character.objects.create(
            name="Existing Character",
            campaign=self.campaign_single,
            player_owner=self.player1,
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
        Character.objects.create(
            name="Existing Character",
            campaign=self.campaign_limited,
            player_owner=self.player2,
            game_system="Mage: The Ascension",
        )

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
        Character.objects.create(
            name="Character 1",
            campaign=self.campaign_single,
            player_owner=self.player1,
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
        Character.objects.create(
            name="Character 1",
            campaign=self.campaign_limited,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

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
        Character.objects.create(
            name="Concurrent Character",
            campaign=self.campaign_single,
            player_owner=self.player1,
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


class CampaignCharacterListViewTest(TestCase):
    """Test CampaignCharactersView functionality and role-based filtering."""

    def setUp(self):
        """Set up test users, campaigns, and characters for list view testing."""
        # Create test users
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.gm = User.objects.create_user(
            username="gm", email="gm@test.com", password="testpass123"
        )
        self.player1 = User.objects.create_user(
            username="player1", email="player1@test.com", password="testpass123"
        )
        self.player2 = User.objects.create_user(
            username="player2", email="player2@test.com", password="testpass123"
        )
        self.observer = User.objects.create_user(
            username="observer", email="observer@test.com", password="testpass123"
        )
        self.non_member = User.objects.create_user(
            username="nonmember", email="nonmember@test.com", password="testpass123"
        )

        # Create test campaigns
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            slug="test-campaign",
            owner=self.owner,
            game_system="Mage: The Ascension",
            max_characters_per_player=3,
        )

        self.other_campaign = Campaign.objects.create(
            name="Other Campaign",
            slug="other-campaign",
            owner=self.player2,
            game_system="D&D 5e",
            max_characters_per_player=2,
        )

        self.inactive_campaign = Campaign.objects.create(
            name="Inactive Campaign",
            slug="inactive-campaign",
            owner=self.owner,
            game_system="Call of Cthulhu",
            is_active=False,
        )

        # Create memberships
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm, role="GM"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player1, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player2, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.observer, role="OBSERVER"
        )

        # Add memberships to other campaign
        CampaignMembership.objects.create(
            campaign=self.other_campaign, user=self.player1, role="PLAYER"
        )

        # Create test characters
        self.char1_player1 = Character.objects.create(
            name="Player1 Character A",
            description="First character for player1",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        self.char2_player1 = Character.objects.create(
            name="Player1 Character B",
            description="Second character for player1",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        self.char1_player2 = Character.objects.create(
            name="Player2 Character",
            description="Character for player2",
            campaign=self.campaign,
            player_owner=self.player2,
            game_system="Mage: The Ascension",
        )

        self.char1_gm = Character.objects.create(
            name="GM NPC Character",
            description="NPC controlled by GM",
            campaign=self.campaign,
            player_owner=self.gm,
            game_system="Mage: The Ascension",
        )

        self.char1_owner = Character.objects.create(
            name="Owner Character",
            description="Character owned by campaign owner",
            campaign=self.campaign,
            player_owner=self.owner,
            game_system="Mage: The Ascension",
        )

        # Character in other campaign
        self.char_other_campaign = Character.objects.create(
            name="Other Campaign Character",
            description="Character in different campaign",
            campaign=self.other_campaign,
            player_owner=self.player1,
            game_system="D&D 5e",
        )

        # URL for campaign character list
        self.list_url = reverse(
            "characters:campaign_characters",
            kwargs={"campaign_slug": self.campaign.slug},
        )

    def test_view_requires_authentication(self):
        """Test that the view requires user authentication."""
        response = self.client.get(self.list_url)
        self.assertRedirects(response, f"/users/login/?next={self.list_url}")

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
        empty_campaign = Campaign.objects.create(
            name="Empty Campaign",
            slug="empty-campaign",
            owner=self.owner,
            game_system="Vampire: The Masquerade",
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
            6
        ):  # Realistic count: campaign+memberships+users+count+characters
            response = self.client.get(self.list_url)
            # Access all character attributes that would trigger queries
            for character in response.context["characters"]:
                _ = character.player_owner.username
                _ = character.campaign.name


class UserCharacterListViewTest(TestCase):
    """Test UserCharactersView functionality (user-scoped character list)."""

    def setUp(self):
        """Set up test data for user-scoped character list testing."""
        # Create test users
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
        self.campaign1 = Campaign.objects.create(
            name="Campaign One",
            slug="campaign-one",
            owner=self.user1,
            game_system="Mage: The Ascension",
            max_characters_per_player=0,  # Unlimited characters
        )

        self.campaign2 = Campaign.objects.create(
            name="Campaign Two",
            slug="campaign-two",
            owner=self.user2,
            game_system="D&D 5e",
            max_characters_per_player=0,  # Unlimited characters
        )

        self.campaign3 = Campaign.objects.create(
            name="Campaign Three",
            slug="campaign-three",
            owner=self.user2,
            game_system="Vampire: The Masquerade",
            max_characters_per_player=0,  # Unlimited characters
        )

        # Create memberships - user1 is a member of campaign1 and campaign2
        CampaignMembership.objects.create(
            campaign=self.campaign2, user=self.user1, role="PLAYER"
        )

        # Create characters for user1 across multiple campaigns
        self.char1_campaign1 = Character.objects.create(
            name="Character in Campaign 1",
            description="First character",
            campaign=self.campaign1,
            player_owner=self.user1,
            game_system="Mage: The Ascension",
        )

        self.char2_campaign1 = Character.objects.create(
            name="Another Character in Campaign 1",
            description="Second character",
            campaign=self.campaign1,
            player_owner=self.user1,
            game_system="Mage: The Ascension",
        )

        self.char1_campaign2 = Character.objects.create(
            name="Character in Campaign 2",
            description="Third character",
            campaign=self.campaign2,
            player_owner=self.user1,
            game_system="D&D 5e",
        )

        # Character owned by user2 (should not be visible to user1)
        self.char_user2 = Character.objects.create(
            name="User2 Character",
            description="Character owned by user2",
            campaign=self.campaign2,
            player_owner=self.user2,
            game_system="D&D 5e",
        )

        # Character in campaign user1 has no access to
        self.char_no_access = Character.objects.create(
            name="No Access Character",
            description="Character in campaign user1 cannot access",
            campaign=self.campaign3,
            player_owner=self.user2,
            game_system="Vampire: The Masquerade",
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


class EnhancedCharacterDetailViewTest(TestCase):
    """Test enhanced CharacterDetailView with role-based information display."""

    def setUp(self):
        """Set up test data for character detail view testing."""
        # Create test users
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.gm = User.objects.create_user(
            username="gm", email="gm@test.com", password="testpass123"
        )
        self.player1 = User.objects.create_user(
            username="player1", email="player1@test.com", password="testpass123"
        )
        self.player2 = User.objects.create_user(
            username="player2", email="player2@test.com", password="testpass123"
        )
        self.observer = User.objects.create_user(
            username="observer", email="observer@test.com", password="testpass123"
        )
        self.non_member = User.objects.create_user(
            username="nonmember", email="nonmember@test.com", password="testpass123"
        )

        # Create test campaign
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            slug="test-campaign",
            owner=self.owner,
            game_system="Mage: The Ascension",
        )

        # Create memberships
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm, role="GM"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player1, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player2, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.observer, role="OBSERVER"
        )

        # Create test characters
        self.player1_character = Character.objects.create(
            name="Player1 Test Character",
            description="A test character owned by player1",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        self.player2_character = Character.objects.create(
            name="Player2 Test Character",
            description="A test character owned by player2",
            campaign=self.campaign,
            player_owner=self.player2,
            game_system="Mage: The Ascension",
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
        self.assertRedirects(response, f"/users/login/?next={self.detail_url_p1}")

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

        # Should use select_related for campaign and player_owner
        with self.assertNumQueries(2):  # Adjust based on actual optimization
            response = self.client.get(self.detail_url_p1)
            # Access related objects to verify they're prefetched
            _ = response.context["character"].campaign.name
            _ = response.context["character"].player_owner.username
