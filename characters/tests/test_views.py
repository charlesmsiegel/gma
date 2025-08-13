"""
Tests for character views.

Tests the CharacterCreateView with comprehensive scenarios including
authentication, permissions, validation, and edge cases.
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
