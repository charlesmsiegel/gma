"""
Tests for character creation forms.

This module tests the CharacterCreateForm with comprehensive validation scenarios,
permission checking, character limits, and edge cases for character creation workflow.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from campaigns.models import Campaign, CampaignMembership
from characters.forms import CharacterCreateForm
from characters.models import Character

User = get_user_model()


class CharacterCreateFormTest(TestCase):
    """Test CharacterCreateForm validation and functionality."""

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

    def test_form_fields_present(self):
        """Test that the form has all required fields."""
        form = CharacterCreateForm(user=self.player1)

        expected_fields = ["name", "description", "campaign"]
        for field in expected_fields:
            self.assertIn(field, form.fields)

    def test_name_field_validation(self):
        """Test name field validation requirements."""
        # Test valid name
        form_data = {
            "name": "Test Character",
            "description": "A test character",
            "campaign": self.campaign_limited.id,
        }
        form = CharacterCreateForm(data=form_data, user=self.player1)
        self.assertTrue(form.is_valid())

        # Test empty name
        form_data["name"] = ""
        form = CharacterCreateForm(data=form_data, user=self.player1)
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

        # Test whitespace-only name
        form_data["name"] = "   "
        form = CharacterCreateForm(data=form_data, user=self.player1)
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

        # Test name too long (over 100 characters)
        form_data["name"] = "a" * 101
        form = CharacterCreateForm(data=form_data, user=self.player1)
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

        # Test name exactly 100 characters (should be valid)
        form_data["name"] = "a" * 100
        form = CharacterCreateForm(data=form_data, user=self.player1)
        self.assertTrue(form.is_valid())

    def test_description_field_optional(self):
        """Test that description field is optional."""
        # Test without description
        form_data = {
            "name": "Test Character",
            "campaign": self.campaign_limited.id,
        }
        form = CharacterCreateForm(data=form_data, user=self.player1)
        self.assertTrue(form.is_valid())

        # Test with empty description
        form_data["description"] = ""
        form = CharacterCreateForm(data=form_data, user=self.player1)
        self.assertTrue(form.is_valid())

        # Test with description
        form_data["description"] = "A detailed character background."
        form = CharacterCreateForm(data=form_data, user=self.player1)
        self.assertTrue(form.is_valid())

    def test_campaign_field_filters_by_user_membership(self):
        """Test that campaign choices are filtered by user membership."""
        # Player1 should see campaigns they're a member of
        form = CharacterCreateForm(user=self.player1)
        campaign_choices = [choice[0] for choice in form.fields["campaign"].choices]

        self.assertIn(self.campaign_limited.id, campaign_choices)
        self.assertIn(self.campaign_unlimited.id, campaign_choices)
        self.assertIn(self.campaign_single.id, campaign_choices)

        # Non-member should see no campaigns
        form = CharacterCreateForm(user=self.non_member)
        campaign_choices = [
            choice[0] for choice in form.fields["campaign"].choices if choice[0]
        ]
        self.assertEqual(len(campaign_choices), 0)

        # Observer should see campaigns they're a member of
        form = CharacterCreateForm(user=self.observer)
        campaign_choices = [choice[0] for choice in form.fields["campaign"].choices]
        self.assertIn(self.campaign_limited.id, campaign_choices)

    def test_campaign_field_includes_owned_campaigns(self):
        """Test that campaign choices include campaigns owned by the user."""
        form = CharacterCreateForm(user=self.owner)
        campaign_choices = [choice[0] for choice in form.fields["campaign"].choices]

        # Owner should see all their owned campaigns
        self.assertIn(self.campaign_limited.id, campaign_choices)
        self.assertIn(self.campaign_unlimited.id, campaign_choices)
        self.assertIn(self.campaign_single.id, campaign_choices)

    def test_form_validation_requires_membership(self):
        """Test that form validation requires user membership in selected campaign."""
        # Create a campaign the user is not a member of
        other_campaign = Campaign.objects.create(
            name="Other Campaign",
            owner=self.player2,
            game_system="Vampire: The Masquerade",
        )

        form_data = {
            "name": "Test Character",
            "description": "A test character",
            "campaign": other_campaign.id,
        }
        form = CharacterCreateForm(data=form_data, user=self.player1)
        self.assertFalse(form.is_valid())
        self.assertIn("campaign", form.errors)

    def test_form_validation_character_name_unique_per_campaign(self):
        """Test that character names must be unique per campaign."""
        # Create an existing character
        Character.objects.create(
            name="Existing Character",
            campaign=self.campaign_limited,
            player_owner=self.player2,
            game_system="Mage: The Ascension",
        )

        # Try to create another character with the same name in the same campaign
        form_data = {
            "name": "Existing Character",
            "description": "Another character",
            "campaign": self.campaign_limited.id,
        }
        form = CharacterCreateForm(data=form_data, user=self.player1)
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

        # Same name in different campaign should be allowed
        form_data["campaign"] = self.campaign_unlimited.id
        form = CharacterCreateForm(data=form_data, user=self.player1)
        self.assertTrue(form.is_valid())

    def test_form_validation_character_limit_enforcement(self):
        """Test that form validates character limits per player."""
        # Create characters up to the limit in single character campaign
        Character.objects.create(
            name="Character 1",
            campaign=self.campaign_single,
            player_owner=self.player1,
            game_system="Call of Cthulhu",
        )

        # Try to create another character (should fail due to limit)
        form_data = {
            "name": "Character 2",
            "description": "Another character",
            "campaign": self.campaign_single.id,
        }
        form = CharacterCreateForm(data=form_data, user=self.player1)
        self.assertFalse(form.is_valid())
        self.assertIn("campaign", form.errors)

    def test_form_validation_unlimited_characters(self):
        """Test that unlimited character campaigns don't enforce limits."""
        # Create several characters in unlimited campaign
        for i in range(5):
            Character.objects.create(
                name=f"Character {i}",
                campaign=self.campaign_unlimited,
                player_owner=self.player1,
                game_system="D&D 5e",
            )

        # Should still be able to create more characters
        form_data = {
            "name": "Character 6",
            "description": "Another character",
            "campaign": self.campaign_unlimited.id,
        }
        form = CharacterCreateForm(data=form_data, user=self.player1)
        self.assertTrue(form.is_valid())

    def test_form_validation_multiple_character_limit(self):
        """Test validation with campaigns allowing multiple characters."""
        # Create one character (limit is 2)
        Character.objects.create(
            name="Character 1",
            campaign=self.campaign_limited,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        # Should be able to create second character
        form_data = {
            "name": "Character 2",
            "description": "Second character",
            "campaign": self.campaign_limited.id,
        }
        form = CharacterCreateForm(data=form_data, user=self.player1)
        self.assertTrue(form.is_valid())

        # Create the second character
        Character.objects.create(
            name="Character 2",
            campaign=self.campaign_limited,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        # Third character should fail
        form_data["name"] = "Character 3"
        form = CharacterCreateForm(data=form_data, user=self.player1)
        self.assertFalse(form.is_valid())
        self.assertIn("campaign", form.errors)

    def test_form_save_creates_character_with_correct_attributes(self):
        """Test that form.save() creates a character with correct attributes."""
        form_data = {
            "name": "Test Character",
            "description": "A test character description",
            "campaign": self.campaign_limited.id,
        }
        form = CharacterCreateForm(data=form_data, user=self.player1)
        self.assertTrue(form.is_valid())

        character = form.save()

        self.assertEqual(character.name, "Test Character")
        self.assertEqual(character.description, "A test character description")
        self.assertEqual(character.campaign, self.campaign_limited)
        self.assertEqual(character.player_owner, self.player1)
        self.assertEqual(character.game_system, self.campaign_limited.game_system)

    def test_form_save_commit_false(self):
        """Test that form.save(commit=False) returns unsaved character."""
        form_data = {
            "name": "Test Character",
            "description": "A test character description",
            "campaign": self.campaign_limited.id,
        }
        form = CharacterCreateForm(data=form_data, user=self.player1)
        self.assertTrue(form.is_valid())

        character = form.save(commit=False)

        # Character should have attributes but not be saved
        self.assertEqual(character.name, "Test Character")
        self.assertEqual(character.player_owner, self.player1)
        self.assertIsNone(character.pk)

        # Should not exist in database
        self.assertFalse(Character.objects.filter(name="Test Character").exists())

    def test_different_user_roles_can_create_characters(self):
        """Test that users with different roles can create characters."""
        # Test OWNER role
        form_data = {
            "name": "Owner Character",
            "campaign": self.campaign_limited.id,
        }
        form = CharacterCreateForm(data=form_data, user=self.owner)
        self.assertTrue(form.is_valid())

        # Test GM role
        form_data = {
            "name": "GM Character",
            "campaign": self.campaign_limited.id,
        }
        form = CharacterCreateForm(data=form_data, user=self.gm)
        self.assertTrue(form.is_valid())

        # Test PLAYER role
        form_data = {
            "name": "Player Character",
            "campaign": self.campaign_limited.id,
        }
        form = CharacterCreateForm(data=form_data, user=self.player1)
        self.assertTrue(form.is_valid())

    def test_observer_role_validation(self):
        """Test that observers can create characters if they have PLAYER+ role."""
        # OBSERVER role should be able to create characters
        # (based on the requirement that PLAYER, GM, OWNER roles can create)
        form_data = {
            "name": "Observer Character",
            "campaign": self.campaign_limited.id,
        }
        form = CharacterCreateForm(data=form_data, user=self.observer)
        # This depends on business rules - observers might or might not be allowed
        # For now, assuming they can create characters as they are campaign members
        self.assertTrue(form.is_valid())

    def test_form_invalid_campaign_selection(self):
        """Test form validation with invalid campaign selections."""
        # Test with non-existent campaign ID
        form_data = {
            "name": "Test Character",
            "campaign": 99999,
        }
        form = CharacterCreateForm(data=form_data, user=self.player1)
        self.assertFalse(form.is_valid())
        self.assertIn("campaign", form.errors)

        # Test with None campaign
        form_data["campaign"] = None
        form = CharacterCreateForm(data=form_data, user=self.player1)
        self.assertFalse(form.is_valid())
        self.assertIn("campaign", form.errors)

    def test_form_with_inactive_campaign(self):
        """Test that inactive campaigns are not available for character creation."""
        # Make campaign inactive
        self.campaign_limited.is_active = False
        self.campaign_limited.save()

        form = CharacterCreateForm(user=self.player1)
        campaign_choices = [choice[0] for choice in form.fields["campaign"].choices]

        # Inactive campaign should not be in choices
        self.assertNotIn(self.campaign_limited.id, campaign_choices)

    def test_form_game_system_assignment(self):
        """Test that game_system is automatically assigned from campaign."""
        form_data = {
            "name": "Test Character",
            "campaign": self.campaign_limited.id,
        }
        form = CharacterCreateForm(data=form_data, user=self.player1)
        self.assertTrue(form.is_valid())

        character = form.save()
        self.assertEqual(character.game_system, self.campaign_limited.game_system)

    def test_form_edge_case_empty_form(self):
        """Test form behavior with completely empty data."""
        form = CharacterCreateForm(data={}, user=self.player1)
        self.assertFalse(form.is_valid())

        # Should have errors for required fields
        self.assertIn("name", form.errors)
        self.assertIn("campaign", form.errors)

    def test_form_user_parameter_required(self):
        """Test that form requires user parameter."""
        # Form should raise error without user parameter
        with self.assertRaises(TypeError):
            CharacterCreateForm(data={"name": "Test"})
