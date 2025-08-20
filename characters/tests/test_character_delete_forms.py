"""
Tests for character delete forms.

This module tests the CharacterDeleteForm with confirmation validation,
permission checking, and soft delete functionality for character deletion workflow.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from campaigns.models import Campaign, CampaignMembership
from characters.models import Character

User = get_user_model()


class CharacterDeleteFormTest(TestCase):
    """Test CharacterDeleteForm validation and functionality."""

    def setUp(self):
        """Set up test users and campaigns for delete form testing."""
        # Create users
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.player1 = User.objects.create_user(
            username="player1", email="player1@test.com", password="testpass123"
        )
        self.player2 = User.objects.create_user(
            username="player2", email="player2@test.com", password="testpass123"
        )

        # Create campaign
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            game_system="Mage: The Ascension",
        )

        # Create memberships
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player1, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player2, role="PLAYER"
        )

        # Create test character
        self.character = Character.objects.create(
            name="Delete Me Character",
            description="Character to be deleted",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

    def test_delete_form_requires_confirmation_name(self):
        """Test that delete form requires typing character name."""
        from characters.forms import CharacterDeleteForm

        # Empty confirmation should fail
        form_data = {
            "confirmation_name": "",
        }
        form = CharacterDeleteForm(
            data=form_data, instance=self.character, user=self.player1
        )
        self.assertFalse(form.is_valid())
        self.assertIn("confirmation_name", form.errors)

        # Wrong name should fail
        form_data["confirmation_name"] = "Wrong Name"
        form = CharacterDeleteForm(
            data=form_data, instance=self.character, user=self.player1
        )
        self.assertFalse(form.is_valid())
        self.assertIn("confirmation_name", form.errors)

        # Correct name should succeed
        form_data["confirmation_name"] = "Delete Me Character"
        form = CharacterDeleteForm(
            data=form_data, instance=self.character, user=self.player1
        )
        self.assertTrue(form.is_valid())

    def test_delete_form_case_sensitive_name_check(self):
        """Test that name confirmation is case sensitive."""
        from characters.forms import CharacterDeleteForm

        # Different case should fail
        form_data = {
            "confirmation_name": "delete me character",  # lowercase
        }
        form = CharacterDeleteForm(
            data=form_data, instance=self.character, user=self.player1
        )
        self.assertFalse(form.is_valid())
        self.assertIn("confirmation_name", form.errors)

    def test_delete_form_permission_validation_owner(self):
        """Test that character owner can delete their character."""
        from characters.forms import CharacterDeleteForm

        form = CharacterDeleteForm(instance=self.character, user=self.player1)
        # Should not raise permission error
        self.assertIn("confirmation_name", form.fields)

    def test_delete_form_permission_validation_campaign_owner(self):
        """Test that campaign owner can delete characters if settings allow."""
        from characters.forms import CharacterDeleteForm

        # Campaign owner should be able to delete if setting allows (default True)
        form = CharacterDeleteForm(instance=self.character, user=self.owner)
        self.assertIn("confirmation_name", form.fields)

    def test_delete_form_permission_denied_other_player(self):
        """Test that other players cannot delete characters they don't own."""
        from characters.forms import CharacterDeleteForm

        with self.assertRaises(PermissionError):
            CharacterDeleteForm(instance=self.character, user=self.player2)

    def test_delete_form_soft_delete_execution(self):
        """Test that form executes soft delete when saved."""
        from characters.forms import CharacterDeleteForm

        form_data = {
            "confirmation_name": "Delete Me Character",
        }
        form = CharacterDeleteForm(
            data=form_data, instance=self.character, user=self.player1
        )
        self.assertTrue(form.is_valid())

        result = form.delete()
        self.assertTrue(result)

        # Character should be soft deleted
        self.character.refresh_from_db()
        self.assertTrue(self.character.is_deleted)
        self.assertEqual(self.character.deleted_by, self.player1)

    def test_delete_form_user_parameter_required(self):
        """Test that delete form requires user parameter."""
        from characters.forms import CharacterDeleteForm

        with self.assertRaises(TypeError):
            CharacterDeleteForm(instance=self.character)

    def test_delete_form_displays_character_info(self):
        """Test that delete form provides character info in context."""
        from characters.forms import CharacterDeleteForm

        form = CharacterDeleteForm(instance=self.character, user=self.player1)

        # Form should provide character information
        self.assertEqual(form.character_name, "Delete Me Character")
        self.assertEqual(form.character_campaign, self.campaign.name)

        # Help text should include character name
        help_text = form.fields["confirmation_name"].help_text
        self.assertIn("Delete Me Character", help_text)
