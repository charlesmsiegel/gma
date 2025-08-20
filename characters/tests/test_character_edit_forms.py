"""
Tests for character edit forms.

This module tests the CharacterEditForm with validation, permission checking,
audit tracking, and field preservation for character editing workflow.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from campaigns.models import Campaign, CampaignMembership
from characters.models import Character

User = get_user_model()


class CharacterEditFormTest(TestCase):
    """Test CharacterEditForm validation and functionality."""

    def setUp(self):
        """Set up test users and campaigns for edit form testing."""
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
        self.non_member = User.objects.create_user(
            username="nonmember", email="nonmember@test.com", password="testpass123"
        )

        # Create campaign
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            game_system="Mage: The Ascension",
            max_characters_per_player=3,
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

        # Create test character
        self.character = Character.objects.create(
            name="Test Character",
            description="Original description",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

    def test_edit_form_fields_present(self):
        """Test that edit form has required fields."""
        from characters.forms import CharacterEditForm

        form = CharacterEditForm(instance=self.character, user=self.player1)

        expected_fields = ["name", "description"]
        for field in expected_fields:
            self.assertIn(field, form.fields)

        # Campaign should not be editable
        self.assertNotIn("campaign", form.fields)

    def test_edit_form_populates_existing_data(self):
        """Test that edit form populates with existing character data."""
        from characters.forms import CharacterEditForm

        form = CharacterEditForm(instance=self.character, user=self.player1)

        self.assertEqual(form.initial["name"], "Test Character")
        self.assertEqual(form.initial["description"], "Original description")

    def test_edit_form_name_validation(self):
        """Test name field validation in edit form."""
        from characters.forms import CharacterEditForm

        # Valid name change
        form_data = {
            "name": "Updated Character Name",
            "description": "Updated description",
        }
        form = CharacterEditForm(
            data=form_data, instance=self.character, user=self.player1
        )
        self.assertTrue(form.is_valid())

        # Empty name should fail
        form_data["name"] = ""
        form = CharacterEditForm(
            data=form_data, instance=self.character, user=self.player1
        )
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

        # Name too long should fail
        form_data["name"] = "a" * 101
        form = CharacterEditForm(
            data=form_data, instance=self.character, user=self.player1
        )
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_edit_form_name_uniqueness_excludes_self(self):
        """Test that name uniqueness validation excludes current character."""
        from characters.forms import CharacterEditForm

        # Create another character with different name
        Character.objects.create(
            name="Other Character",
            campaign=self.campaign,
            player_owner=self.player2,
            game_system="Mage: The Ascension",
        )

        # Should be able to keep same name (editing self)
        form_data = {
            "name": "Test Character",  # Same as original
            "description": "Updated description",
        }
        form = CharacterEditForm(
            data=form_data, instance=self.character, user=self.player1
        )
        self.assertTrue(form.is_valid())

        # Should not be able to use other character's name
        form_data["name"] = "Other Character"
        form = CharacterEditForm(
            data=form_data, instance=self.character, user=self.player1
        )
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_edit_form_permission_validation_owner(self):
        """Test that character owner can edit their character."""
        from characters.forms import CharacterEditForm

        form_data = {
            "name": "Owner Updated Name",
            "description": "Owner updated description",
        }
        form = CharacterEditForm(
            data=form_data, instance=self.character, user=self.player1
        )
        self.assertTrue(form.is_valid())

    def test_edit_form_permission_validation_gm(self):
        """Test that GM can edit characters in their campaign."""
        from characters.forms import CharacterEditForm

        form_data = {
            "name": "GM Updated Name",
            "description": "GM updated description",
        }
        form = CharacterEditForm(data=form_data, instance=self.character, user=self.gm)
        self.assertTrue(form.is_valid())

    def test_edit_form_permission_validation_campaign_owner(self):
        """Test that campaign owner can edit characters in their campaign."""
        from characters.forms import CharacterEditForm

        form_data = {
            "name": "Owner Updated Name",
            "description": "Owner updated description",
        }
        form = CharacterEditForm(
            data=form_data, instance=self.character, user=self.owner
        )
        self.assertTrue(form.is_valid())

    def test_edit_form_permission_denied_other_player(self):
        """Test that other players cannot edit characters they don't own."""
        from characters.forms import CharacterEditForm

        with self.assertRaises(PermissionError):
            CharacterEditForm(instance=self.character, user=self.player2)

    def test_edit_form_permission_denied_non_member(self):
        """Test that non-members cannot edit any characters."""
        from characters.forms import CharacterEditForm

        with self.assertRaises(PermissionError):
            CharacterEditForm(instance=self.character, user=self.non_member)

    def test_edit_form_save_preserves_readonly_fields(self):
        """Test that save preserves fields that shouldn't be changed."""
        from characters.forms import CharacterEditForm

        original_campaign = self.character.campaign
        original_player_owner = self.character.player_owner
        original_game_system = self.character.game_system
        original_created_at = self.character.created_at

        form_data = {
            "name": "Updated Name",
            "description": "Updated description",
        }
        form = CharacterEditForm(
            data=form_data, instance=self.character, user=self.player1
        )
        self.assertTrue(form.is_valid())

        updated_character = form.save()

        # Changed fields
        self.assertEqual(updated_character.name, "Updated Name")
        self.assertEqual(updated_character.description, "Updated description")

        # Preserved fields
        self.assertEqual(updated_character.campaign, original_campaign)
        self.assertEqual(updated_character.player_owner, original_player_owner)
        self.assertEqual(updated_character.game_system, original_game_system)
        self.assertEqual(updated_character.created_at, original_created_at)

    def test_edit_form_save_commit_false(self):
        """Test that form.save(commit=False) returns unsaved character."""
        from characters.forms import CharacterEditForm

        form_data = {
            "name": "Uncommitted Name",
            "description": "Uncommitted description",
        }
        form = CharacterEditForm(
            data=form_data, instance=self.character, user=self.player1
        )
        self.assertTrue(form.is_valid())

        updated_character = form.save(commit=False)

        # Character should have new attributes but not be saved
        self.assertEqual(updated_character.name, "Uncommitted Name")
        self.assertEqual(updated_character.description, "Uncommitted description")

        # Should not be saved to database yet
        self.character.refresh_from_db()
        self.assertEqual(self.character.name, "Test Character")  # Original name
        self.assertEqual(
            self.character.description, "Original description"
        )  # Original description

    def test_edit_form_user_parameter_required(self):
        """Test that edit form requires user parameter."""
        from characters.forms import CharacterEditForm

        # Form should raise error without user parameter
        with self.assertRaises(TypeError):
            CharacterEditForm(instance=self.character)

    def test_edit_form_with_empty_description(self):
        """Test that description can be empty in edit form."""
        from characters.forms import CharacterEditForm

        form_data = {
            "name": "Name Only Character",
            "description": "",
        }
        form = CharacterEditForm(
            data=form_data, instance=self.character, user=self.player1
        )
        self.assertTrue(form.is_valid())

        updated_character = form.save()
        self.assertEqual(updated_character.description, "")

    def test_edit_form_tracks_changes_for_audit(self):
        """Test that form tracks what fields changed for audit trail."""
        from characters.forms import CharacterEditForm

        form_data = {
            "name": "Audit Test Name",
            "description": "Original description",  # No change
        }
        form = CharacterEditForm(
            data=form_data, instance=self.character, user=self.player1
        )
        self.assertTrue(form.is_valid())

        # Check that form can identify what changed
        changed_fields = form.get_changed_fields()
        self.assertIn("name", changed_fields)
        self.assertNotIn("description", changed_fields)  # No change

        # Check old and new values
        changes = form.get_field_changes()
        self.assertEqual(changes["name"]["old"], "Test Character")
        self.assertEqual(changes["name"]["new"], "Audit Test Name")
