"""
Tests for Character API CRUD operations.

This module tests the character create, detail, update, and delete endpoint
functionality
including authentication, permission checks, validation, and audit trail creation.
"""

from django.contrib.auth import get_user_model
from rest_framework import status

from characters.models import Character

from .test_character_api_base import BaseCharacterAPITestCase

User = get_user_model()


class CharacterCreateAPITest(BaseCharacterAPITestCase):
    """Test Character create API endpoint."""

    def test_create_requires_authentication(self):
        """Test that character creation requires authentication."""
        character_data = {
            "name": "Test Character",
            "campaign": self.campaign.pk,
        }

        response = self.client.post(self.list_url, data=character_data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_character_as_player(self):
        """Test character creation as a player."""
        self.client.force_authenticate(user=self.player1)

        character_data = {
            "name": "New Player Character",
            "description": "A new character created via API",
            "campaign": self.campaign.pk,
        }

        response = self.client.post(self.list_url, data=character_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.json()
        self.assertEqual(data["name"], "New Player Character")
        self.assertEqual(data["campaign"]["id"], self.campaign.pk)
        self.assertEqual(data["player_owner"]["id"], self.player1.pk)
        self.assertEqual(data["game_system"], "Mage: The Ascension")

        # Verify character was created in database
        character = Character.objects.get(name="New Player Character")
        self.assertEqual(character.player_owner, self.player1)
        self.assertEqual(character.campaign, self.campaign)

    def test_create_character_as_gm(self):
        """Test character creation as a GM."""
        self.client.force_authenticate(user=self.gm)

        character_data = {
            "name": "GM NPC Character",
            "description": "An NPC created by GM",
            "campaign": self.campaign.pk,
        }

        response = self.client.post(self.list_url, data=character_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.json()
        self.assertEqual(data["player_owner"]["id"], self.gm.pk)

    def test_create_character_as_owner(self):
        """Test character creation as campaign owner."""
        self.client.force_authenticate(user=self.owner)

        character_data = {
            "name": "Owner Character",
            "campaign": self.campaign.pk,
        }

        response = self.client.post(self.list_url, data=character_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_character_observer_denied(self):
        """Test that observers cannot create characters."""
        self.client.force_authenticate(user=self.observer)

        character_data = {
            "name": "Observer Character",
            "campaign": self.campaign.pk,
        }

        response = self.client.post(self.list_url, data=character_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_character_non_member_denied(self):
        """Test that non-members cannot create characters."""
        self.client.force_authenticate(user=self.non_member)

        character_data = {
            "name": "Non-member Character",
            "campaign": self.campaign.pk,
        }

        response = self.client.post(self.list_url, data=character_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_character_validates_required_fields(self):
        """Test validation of required fields."""
        self.client.force_authenticate(user=self.player1)

        # Missing name
        response = self.client.post(self.list_url, data={"campaign": self.campaign.pk})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.json())

        # Missing campaign
        response = self.client.post(self.list_url, data={"name": "Test Character"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("campaign", response.json())

    def test_create_character_validates_name_uniqueness(self):
        """Test that character names must be unique per campaign."""
        self.client.force_authenticate(user=self.player2)

        character_data = {
            "name": "Player1 Character",  # Same as existing character
            "campaign": self.campaign.pk,
        }

        response = self.client.post(self.list_url, data=character_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.json())

    def test_create_character_validates_character_limit(self):
        """Test that character creation respects character limits."""
        # Set low character limit
        self.campaign.max_characters_per_player = 1
        self.campaign.save()

        self.client.force_authenticate(user=self.player1)

        # Player1 already has 1 character, so creating another should fail
        character_data = {
            "name": "Second Character",
            "campaign": self.campaign.pk,
        }

        response = self.client.post(self.list_url, data=character_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("campaign", response.json())

    def test_create_character_auto_assigns_game_system(self):
        """Test that game_system is automatically assigned from campaign."""
        self.client.force_authenticate(user=self.player1)

        character_data = {
            "name": "Auto Game System Character",
            "campaign": self.campaign.pk,
        }

        response = self.client.post(self.list_url, data=character_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.json()
        self.assertEqual(data["game_system"], self.campaign.game_system)

    def test_create_character_creates_audit_trail(self):
        """Test that character creation creates audit trail entry."""
        self.client.force_authenticate(user=self.player1)

        character_data = {
            "name": "Audit Trail Character",
            "campaign": self.campaign.pk,
        }

        response = self.client.post(self.list_url, data=character_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check for audit trail (will fail until implemented)
        from characters.models import CharacterAuditLog

        character = Character.objects.get(name="Audit Trail Character")
        audit_entries = CharacterAuditLog.objects.filter(character=character)
        self.assertGreater(audit_entries.count(), 0)

        audit_entry = audit_entries.first()
        self.assertEqual(audit_entry.action, "CREATE")
        self.assertEqual(audit_entry.user, self.player1)


class CharacterDetailAPITest(BaseCharacterAPITestCase):
    """Test Character detail API endpoint."""

    def test_detail_requires_authentication(self):
        """Test that character detail requires authentication."""
        response = self.client.get(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_detail_character_as_owner(self):
        """Test character detail access as character owner."""
        self.client.force_authenticate(user=self.player1)

        response = self.client.get(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data["id"], self.character1.pk)
        self.assertEqual(data["name"], "Player1 Character")

    def test_detail_character_as_gm(self):
        """Test character detail access as GM."""
        self.client.force_authenticate(user=self.gm)

        response = self.client.get(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_detail_character_as_campaign_owner(self):
        """Test character detail access as campaign owner."""
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_detail_character_as_observer(self):
        """Test character detail access as observer."""
        self.client.force_authenticate(user=self.observer)

        response = self.client.get(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_detail_character_other_player_denied(self):
        """Test that other players cannot view characters they don't own."""
        self.client.force_authenticate(user=self.player2)

        response = self.client.get(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_detail_character_non_member_denied(self):
        """Test that non-members cannot view characters."""
        self.client.force_authenticate(user=self.non_member)

        response = self.client.get(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_detail_deleted_character_visibility(self):
        """Test that deleted characters are visible to appropriate users."""
        # Soft delete the character
        self.character1.soft_delete(self.player1)

        # Owner should see deleted character
        self.client.force_authenticate(user=self.player1)
        response = self.client.get(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertTrue(data["is_deleted"])

        # GM should see deleted character
        self.client.force_authenticate(user=self.gm)
        response = self.client.get(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Other players should not see deleted character
        self.client.force_authenticate(user=self.player2)
        response = self.client.get(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class CharacterUpdateAPITest(BaseCharacterAPITestCase):
    """Test Character update API endpoint."""

    def test_update_requires_authentication(self):
        """Test that character update requires authentication."""
        update_data = {"name": "Updated Name"}

        response = self.client.put(self.detail_url1, data=update_data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_character_as_owner(self):
        """Test character update as character owner."""
        self.client.force_authenticate(user=self.player1)

        update_data = {
            "name": "Updated Player1 Character",
            "description": "Updated description",
        }

        response = self.client.put(self.detail_url1, data=update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data["name"], "Updated Player1 Character")
        self.assertEqual(data["description"], "Updated description")

        # Verify in database
        self.character1.refresh_from_db()
        self.assertEqual(self.character1.name, "Updated Player1 Character")

    def test_update_character_as_gm(self):
        """Test character update as GM."""
        self.client.force_authenticate(user=self.gm)

        update_data = {"name": "GM Updated Character"}

        response = self.client.put(self.detail_url1, data=update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_character_as_campaign_owner(self):
        """Test character update as campaign owner."""
        self.client.force_authenticate(user=self.owner)

        update_data = {"name": "Owner Updated Character"}

        response = self.client.put(self.detail_url1, data=update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_character_other_player_denied(self):
        """Test that other players cannot update characters they don't own."""
        self.client.force_authenticate(user=self.player2)

        update_data = {"name": "Unauthorized Update"}

        response = self.client.put(self.detail_url1, data=update_data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_character_validates_name_uniqueness(self):
        """Test that character name uniqueness is validated on update."""
        self.client.force_authenticate(user=self.player1)

        update_data = {"name": "Player2 Character"}  # Name already exists

        response = self.client.put(self.detail_url1, data=update_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.json())

    def test_update_readonly_fields_ignored(self):
        """Test that read-only fields are ignored in updates."""
        self.client.force_authenticate(user=self.player1)

        original_campaign = self.character1.campaign
        original_player_owner = self.character1.player_owner

        update_data = {
            "name": "Updated Name",
            "campaign": self.campaign.pk + 999,  # Try to change campaign
            "player_owner": self.player2.pk,  # Try to change owner
        }

        response = self.client.put(self.detail_url1, data=update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify readonly fields weren't changed
        self.character1.refresh_from_db()
        self.assertEqual(self.character1.campaign, original_campaign)
        self.assertEqual(self.character1.player_owner, original_player_owner)
        self.assertEqual(self.character1.name, "Updated Name")  # But this changed


class CharacterDeleteAPITest(BaseCharacterAPITestCase):
    """Test Character delete API endpoint."""

    def test_delete_requires_authentication(self):
        """Test that character deletion requires authentication."""
        response = self.client.delete(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_character_as_owner(self):
        """Test character deletion as character owner."""
        self.client.force_authenticate(user=self.player1)

        response = self.client.delete(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify soft delete
        self.character1.refresh_from_db()
        self.assertTrue(self.character1.is_deleted)
        self.assertEqual(self.character1.deleted_by, self.player1)

    def test_delete_character_as_gm(self):
        """Test character deletion as GM."""
        self.client.force_authenticate(user=self.gm)

        response = self.client.delete(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify soft delete with GM as deleter
        self.character1.refresh_from_db()
        self.assertTrue(self.character1.is_deleted)
        self.assertEqual(self.character1.deleted_by, self.gm)

    def test_delete_character_as_campaign_owner(self):
        """Test character deletion as campaign owner."""
        self.client.force_authenticate(user=self.owner)

        response = self.client.delete(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_character_other_player_denied(self):
        """Test that other players cannot delete characters they don't own."""
        self.client.force_authenticate(user=self.player2)

        response = self.client.delete(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Verify character wasn't deleted
        self.character1.refresh_from_db()
        self.assertFalse(self.character1.is_deleted)

    def test_delete_character_non_member_denied(self):
        """Test that non-members cannot delete characters."""
        self.client.force_authenticate(user=self.non_member)

        response = self.client.delete(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_already_deleted_character(self):
        """Test deleting an already deleted character."""
        # First deletion
        self.character1.soft_delete(self.player1)

        self.client.force_authenticate(user=self.player1)

        response = self.client.delete(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
