"""
Tests for Character API endpoints.

Comprehensive tests for all character API operations including:
- CRUD operations (GET, POST, PUT, DELETE)
- Polymorphic serialization
- Permission checks and role-based access
- Pagination and filtering
- Error handling and status codes
- Soft delete handling
- Audit trail integration
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from campaigns.models import Campaign, CampaignMembership
from characters.models import Character

User = get_user_model()


class BaseCharacterAPITestCase(APITestCase):
    """Base test case with common setup for character API tests."""

    def setUp(self):
        """Set up test users, campaigns, and characters."""
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
            max_characters_per_player=0,  # 0 = unlimited for testing pagination
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
        self.character1 = Character.objects.create(
            name="Player1 Character",
            description="Character owned by player1",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )
        self.character2 = Character.objects.create(
            name="Player2 Character",
            description="Character owned by player2",
            campaign=self.campaign,
            player_owner=self.player2,
            game_system="Mage: The Ascension",
        )
        self.gm_character = Character.objects.create(
            name="GM NPC",
            description="NPC managed by GM",
            campaign=self.campaign,
            player_owner=self.gm,
            game_system="Mage: The Ascension",
        )

        # API URLs
        self.list_url = reverse("api:characters-list")
        self.detail_url1 = reverse(
            "api:characters-detail", kwargs={"pk": self.character1.pk}
        )
        self.detail_url2 = reverse(
            "api:characters-detail", kwargs={"pk": self.character2.pk}
        )


class CharacterListAPITest(BaseCharacterAPITestCase):
    """Test Character list API endpoint."""

    def test_list_requires_authentication(self):
        """Test that character list requires authentication."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_all_characters_as_superuser(self):
        """Test that superusers can list all characters."""
        admin_user = User.objects.create_superuser(
            username="admin", email="admin@test.com", password="testpass123"
        )
        self.client.force_authenticate(user=admin_user)

        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data["count"], 3)  # All 3 characters
        character_names = [char["name"] for char in data["results"]]
        self.assertIn("Player1 Character", character_names)
        self.assertIn("Player2 Character", character_names)
        self.assertIn("GM NPC", character_names)

    def test_list_filtered_by_campaign(self):
        """Test character list filtering by campaign."""
        self.client.force_authenticate(user=self.owner)

        # Test with campaign filter
        response = self.client.get(self.list_url, {"campaign": self.campaign.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data["count"], 3)

        # All characters should belong to the test campaign
        for char in data["results"]:
            self.assertEqual(char["campaign"]["id"], self.campaign.pk)

    def test_list_filtered_by_user(self):
        """Test character list filtering by user (player_owner)."""
        self.client.force_authenticate(user=self.gm)

        # Test filtering by player1
        response = self.client.get(
            self.list_url, {"campaign": self.campaign.pk, "user": self.player1.pk}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["name"], "Player1 Character")
        self.assertEqual(data["results"][0]["player_owner"]["id"], self.player1.pk)

    def test_list_player_sees_only_own_characters(self):
        """Test that players see only their own characters by default."""
        self.client.force_authenticate(user=self.player1)

        response = self.client.get(self.list_url, {"campaign": self.campaign.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["name"], "Player1 Character")

    def test_list_gm_sees_all_campaign_characters(self):
        """Test that GMs see all characters in their campaigns."""
        self.client.force_authenticate(user=self.gm)

        response = self.client.get(self.list_url, {"campaign": self.campaign.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data["count"], 3)  # All characters in campaign

    def test_list_owner_sees_all_campaign_characters(self):
        """Test that campaign owners see all characters in their campaigns."""
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(self.list_url, {"campaign": self.campaign.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data["count"], 3)  # All characters in campaign

    def test_list_observer_sees_all_campaign_characters(self):
        """Test that observers see all characters in campaigns they observe."""
        self.client.force_authenticate(user=self.observer)

        response = self.client.get(self.list_url, {"campaign": self.campaign.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data["count"], 3)  # All characters in campaign

    def test_list_non_member_sees_no_characters(self):
        """Test that non-members see no characters."""
        self.client.force_authenticate(user=self.non_member)

        response = self.client.get(self.list_url, {"campaign": self.campaign.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data["count"], 0)

    def test_list_pagination(self):
        """Test character list pagination."""
        # Create additional characters to test pagination
        for i in range(25):
            Character.objects.create(
                name=f"Test Character {i}",
                campaign=self.campaign,
                player_owner=self.player1,
                game_system="Mage: The Ascension",
            )

        self.client.force_authenticate(user=self.owner)

        # Test default pagination
        response = self.client.get(self.list_url, {"campaign": self.campaign.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data["results"]), 20)  # Default page size
        self.assertIsNotNone(data["next"])
        self.assertIsNone(data["previous"])

        # Test custom page size
        response = self.client.get(
            self.list_url, {"campaign": self.campaign.pk, "page_size": 10}
        )
        data = response.json()
        self.assertEqual(len(data["results"]), 10)

    def test_list_search_by_name(self):
        """Test character search by name."""
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(
            self.list_url, {"campaign": self.campaign.pk, "search": "Player1"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["name"], "Player1 Character")

    def test_list_ordering(self):
        """Test character list ordering."""
        self.client.force_authenticate(user=self.owner)

        # Test default ordering (by name)
        response = self.client.get(self.list_url, {"campaign": self.campaign.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        names = [char["name"] for char in data["results"]]
        self.assertEqual(names, sorted(names))

        # Test reverse ordering
        response = self.client.get(
            self.list_url, {"campaign": self.campaign.pk, "ordering": "-name"}
        )
        data = response.json()
        names = [char["name"] for char in data["results"]]
        self.assertEqual(names, sorted(names, reverse=True))

    def test_list_includes_deleted_flag(self):
        """Test that list includes deleted flag and can filter by it."""
        # Soft delete a character
        self.character1.soft_delete(self.player1)

        self.client.force_authenticate(user=self.owner)

        # Test including deleted characters
        response = self.client.get(
            self.list_url, {"campaign": self.campaign.pk, "include_deleted": "true"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data["count"], 3)  # Including deleted character

        # Find the deleted character in results
        deleted_char = next(
            char for char in data["results"] if char["name"] == "Player1 Character"
        )
        self.assertTrue(deleted_char["is_deleted"])
        self.assertIsNotNone(deleted_char["deleted_at"])
        self.assertEqual(deleted_char["deleted_by"]["id"], self.player1.pk)

        # Test excluding deleted characters (default)
        response = self.client.get(self.list_url, {"campaign": self.campaign.pk})
        data = response.json()
        self.assertEqual(data["count"], 2)  # Excluding deleted character

    def test_list_serializer_includes_all_fields(self):
        """Test that list serializer includes all expected fields."""
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(self.list_url, {"campaign": self.campaign.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        character = data["results"][0]

        expected_fields = [
            "id",
            "name",
            "description",
            "game_system",
            "created_at",
            "updated_at",
            "campaign",
            "player_owner",
            "is_deleted",
            "deleted_at",
            "deleted_by",
        ]
        for field in expected_fields:
            self.assertIn(field, character)

        # Test nested serialization
        self.assertIn("id", character["campaign"])
        self.assertIn("name", character["campaign"])
        self.assertIn("id", character["player_owner"])
        self.assertIn("username", character["player_owner"])


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

    def test_detail_character_owner_access(self):
        """Test that character owners can access their character details."""
        self.client.force_authenticate(user=self.player1)

        response = self.client.get(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data["name"], "Player1 Character")
        self.assertEqual(data["id"], self.character1.pk)

    def test_detail_gm_access(self):
        """Test that GMs can access character details in their campaigns."""
        self.client.force_authenticate(user=self.gm)

        response = self.client.get(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_detail_campaign_owner_access(self):
        """Test that campaign owners can access character details."""
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_detail_observer_access(self):
        """Test that observers can access character details."""
        self.client.force_authenticate(user=self.observer)

        response = self.client.get(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_detail_other_player_access(self):
        """Test that other players can access character details in same campaign."""
        self.client.force_authenticate(user=self.player2)

        response = self.client.get(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_detail_non_member_denied(self):
        """Test that non-members cannot access character details."""
        self.client.force_authenticate(user=self.non_member)

        response = self.client.get(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_detail_nonexistent_character(self):
        """Test that nonexistent characters return 404."""
        self.client.force_authenticate(user=self.player1)

        nonexistent_url = reverse("api:characters-detail", kwargs={"pk": 99999})
        response = self.client.get(nonexistent_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_detail_includes_all_fields(self):
        """Test that detail view includes all expected fields."""
        self.client.force_authenticate(user=self.player1)

        response = self.client.get(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        expected_fields = [
            "id",
            "name",
            "description",
            "game_system",
            "created_at",
            "updated_at",
            "campaign",
            "player_owner",
            "is_deleted",
            "deleted_at",
            "deleted_by",
        ]
        for field in expected_fields:
            self.assertIn(field, data)

    def test_detail_soft_deleted_character_access(self):
        """Test access to soft deleted characters."""
        # Soft delete the character
        self.character1.soft_delete(self.player1)

        self.client.force_authenticate(user=self.player1)

        response = self.client.get(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertTrue(data["is_deleted"])
        self.assertIsNotNone(data["deleted_at"])
        self.assertEqual(data["deleted_by"]["id"], self.player1.pk)


class CharacterUpdateAPITest(BaseCharacterAPITestCase):
    """Test Character update API endpoint."""

    def test_update_requires_authentication(self):
        """Test that character update requires authentication."""
        update_data = {"name": "Updated Name"}

        response = self.client.patch(self.detail_url1, data=update_data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_character_as_owner(self):
        """Test character update as character owner."""
        self.client.force_authenticate(user=self.player1)

        update_data = {
            "name": "Updated Player1 Character",
            "description": "Updated description",
        }

        response = self.client.patch(self.detail_url1, data=update_data)
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

        response = self.client.patch(self.detail_url1, data=update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_character_as_campaign_owner(self):
        """Test character update as campaign owner."""
        self.client.force_authenticate(user=self.owner)

        update_data = {"name": "Owner Updated Character"}

        response = self.client.patch(self.detail_url1, data=update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_character_other_player_denied(self):
        """Test that other players cannot update characters they don't own."""
        self.client.force_authenticate(user=self.player2)

        update_data = {"name": "Unauthorized Update"}

        response = self.client.patch(self.detail_url1, data=update_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_character_observer_denied(self):
        """Test that observers cannot update characters."""
        self.client.force_authenticate(user=self.observer)

        update_data = {"name": "Observer Update"}

        response = self.client.patch(self.detail_url1, data=update_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_character_non_member_denied(self):
        """Test that non-members cannot update characters."""
        self.client.force_authenticate(user=self.non_member)

        update_data = {"name": "Non-member Update"}

        response = self.client.patch(self.detail_url1, data=update_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_character_validates_name_uniqueness(self):
        """Test that update validates name uniqueness."""
        self.client.force_authenticate(user=self.player2)

        update_data = {"name": "Player1 Character"}  # Existing name

        response = self.client.patch(self.detail_url2, data=update_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.json())

    def test_update_character_preserves_readonly_fields(self):
        """Test that update preserves readonly fields."""
        self.client.force_authenticate(user=self.player1)

        original_campaign = self.character1.campaign
        original_owner = self.character1.player_owner
        original_created = self.character1.created_at

        update_data = {
            "name": "Updated Name",
            "campaign": self.campaign.pk + 999,  # Try to change campaign
            "player_owner": self.player2.pk,  # Try to change owner
            "game_system": "Different System",  # Try to change game system
        }

        response = self.client.patch(self.detail_url1, data=update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.character1.refresh_from_db()
        # Name should be updated
        self.assertEqual(self.character1.name, "Updated Name")
        # But other fields should be preserved
        self.assertEqual(self.character1.campaign, original_campaign)
        self.assertEqual(self.character1.player_owner, original_owner)
        self.assertEqual(self.character1.created_at, original_created)

    def test_update_character_creates_audit_trail(self):
        """Test that character update creates audit trail entry."""
        self.client.force_authenticate(user=self.player1)

        update_data = {"name": "Audit Update Test"}

        response = self.client.patch(self.detail_url1, data=update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check for audit trail (will fail until implemented)
        from characters.models import CharacterAuditLog

        audit_entries = CharacterAuditLog.objects.filter(
            character=self.character1, action="UPDATE"
        )
        self.assertGreater(audit_entries.count(), 0)

        audit_entry = audit_entries.first()
        self.assertEqual(audit_entry.user, self.player1)
        self.assertIn("name", audit_entry.changes)

    def test_full_update_with_put(self):
        """Test full character update using PUT."""
        self.client.force_authenticate(user=self.player1)

        full_data = {
            "name": "Fully Updated Character",
            "description": "Completely new description",
        }

        response = self.client.put(self.detail_url1, data=full_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data["name"], "Fully Updated Character")
        self.assertEqual(data["description"], "Completely new description")


class CharacterDeleteAPITest(BaseCharacterAPITestCase):
    """Test Character delete API endpoint."""

    def test_delete_requires_authentication(self):
        """Test that character deletion requires authentication."""
        response = self.client.delete(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_soft_delete_character_as_owner(self):
        """Test soft deleting character as owner."""
        self.client.force_authenticate(user=self.player1)

        response = self.client.delete(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Character should be soft deleted
        self.character1.refresh_from_db()
        self.assertTrue(self.character1.is_deleted)
        self.assertEqual(self.character1.deleted_by, self.player1)

    def test_soft_delete_character_as_campaign_owner(self):
        """Test soft deleting character as campaign owner."""
        self.client.force_authenticate(user=self.owner)

        response = self.client.delete(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.character1.refresh_from_db()
        self.assertTrue(self.character1.is_deleted)
        self.assertEqual(self.character1.deleted_by, self.owner)

    def test_delete_character_gm_denied_by_default(self):
        """Test that GMs cannot delete characters by default."""
        self.client.force_authenticate(user=self.gm)

        response = self.client.delete(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_character_gm_allowed_when_enabled(self):
        """Test that GMs can delete when setting is enabled."""
        # Enable GM character deletion
        self.campaign.allow_gm_character_deletion = True
        self.campaign.save()

        self.client.force_authenticate(user=self.gm)

        response = self.client.delete(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_character_other_player_denied(self):
        """Test that other players cannot delete characters."""
        self.client.force_authenticate(user=self.player2)

        response = self.client.delete(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_character_observer_denied(self):
        """Test that observers cannot delete characters."""
        self.client.force_authenticate(user=self.observer)

        response = self.client.delete(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_character_non_member_denied(self):
        """Test that non-members cannot delete characters."""
        self.client.force_authenticate(user=self.non_member)

        response = self.client.delete(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_character_creates_audit_trail(self):
        """Test that character deletion creates audit trail entry."""
        self.client.force_authenticate(user=self.player1)

        response = self.client.delete(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Check for audit trail (will fail until implemented)
        from characters.models import CharacterAuditLog

        audit_entries = CharacterAuditLog.objects.filter(
            character=self.character1, action="DELETE"
        )
        self.assertGreater(audit_entries.count(), 0)

        audit_entry = audit_entries.first()
        self.assertEqual(audit_entry.user, self.player1)
        self.assertIn("is_deleted", audit_entry.changes)

    def test_hard_delete_admin_only(self):
        """Test that hard delete is admin only via special endpoint."""
        # This would be a separate endpoint for admin hard delete
        admin_user = User.objects.create_superuser(
            username="admin", email="admin@test.com", password="testpass123"
        )
        self.client.force_authenticate(user=admin_user)

        # Hard delete endpoint (to be implemented)
        hard_delete_url = reverse(
            "api:characters-hard-delete", kwargs={"pk": self.character1.pk}
        )
        response = self.client.delete(hard_delete_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Character should be completely removed
        with self.assertRaises(Character.DoesNotExist):
            Character.all_objects.get(pk=self.character1.pk)

    def test_delete_already_deleted_character(self):
        """Test attempting to delete an already soft-deleted character."""
        # Soft delete the character first
        self.character1.soft_delete(self.player1)

        self.client.force_authenticate(user=self.player1)

        response = self.client.delete(self.detail_url1)
        # Should still return success (idempotent)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_campaign_owner_delete_permission_setting(self):
        """Test that campaign owner delete permission can be disabled."""
        # Disable owner character deletion
        self.campaign.allow_owner_character_deletion = False
        self.campaign.save()

        self.client.force_authenticate(user=self.owner)

        response = self.client.delete(self.detail_url1)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class CharacterPolymorphicSerializationTest(BaseCharacterAPITestCase):
    """Test polymorphic serialization for different character types."""

    def setUp(self):
        """Set up additional character types for testing."""
        super().setUp()

        # Create different character types
        # (these will fail until polymorphic models exist)
        try:
            from characters.models import MageCharacter

            self.mage_character = MageCharacter.objects.create(
                name="Mage Character",
                campaign=self.campaign,
                player_owner=self.player1,
                game_system="Mage: The Ascension",
                # Mage-specific fields
                arete=3,
                quintessence=10,
                paradox=0,
            )
        except ImportError:
            # If polymorphic models don't exist yet, skip these tests
            self.mage_character = None

    def test_polymorphic_character_serialization(self):
        """Test that polymorphic characters are serialized with type-specific fields."""
        if not self.mage_character:
            self.skipTest("Polymorphic character models not implemented yet")

        self.client.force_authenticate(user=self.player1)

        mage_detail_url = reverse(
            "api:characters-detail", kwargs={"pk": self.mage_character.pk}
        )
        response = self.client.get(mage_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        # Should include base character fields
        self.assertIn("name", data)
        self.assertIn("campaign", data)

        # Should include polymorphic type
        self.assertEqual(data["character_type"], "MageCharacter")

        # Should include Mage-specific fields
        self.assertIn("arete", data)
        self.assertIn("quintessence", data)
        self.assertIn("paradox", data)

    def test_polymorphic_character_list_serialization(self):
        """Test that character list properly handles mixed polymorphic types."""
        if not self.mage_character:
            self.skipTest("Polymorphic character models not implemented yet")

        self.client.force_authenticate(user=self.owner)

        response = self.client.get(self.list_url, {"campaign": self.campaign.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        # Should have mixed character types
        character_types = [char["character_type"] for char in data["results"]]
        self.assertIn("Character", character_types)  # Base characters
        self.assertIn("MageCharacter", character_types)  # Mage character

    def test_polymorphic_character_creation(self):
        """Test creating polymorphic characters via API."""
        if not self.mage_character:
            self.skipTest("Polymorphic character models not implemented yet")

        self.client.force_authenticate(user=self.player1)

        mage_data = {
            "name": "New Mage",
            "campaign": self.campaign.pk,
            "character_type": "MageCharacter",
            "arete": 2,
            "quintessence": 15,
            "paradox": 1,
        }

        response = self.client.post(self.list_url, data=mage_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.json()
        self.assertEqual(data["character_type"], "MageCharacter")
        self.assertEqual(data["arete"], 2)


class CharacterAPIErrorHandlingTest(BaseCharacterAPITestCase):
    """Test error handling in Character API endpoints."""

    def test_invalid_campaign_id(self):
        """Test handling of invalid campaign IDs."""
        self.client.force_authenticate(user=self.player1)

        # Test with non-existent campaign
        character_data = {
            "name": "Invalid Campaign Character",
            "campaign": 99999,
        }

        response = self.client.post(self.list_url, data=character_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("campaign", response.json())

    def test_invalid_json_data(self):
        """Test handling of invalid JSON data."""
        self.client.force_authenticate(user=self.player1)

        response = self.client.post(
            self.list_url, data="invalid json", content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_content_type(self):
        """Test that API handles missing content type properly."""
        self.client.force_authenticate(user=self.player1)

        character_data = {
            "name": "Content Type Test",
            "campaign": self.campaign.pk,
        }

        # Send as form data (should still work)
        response = self.client.post(self.list_url, data=character_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_method_not_allowed(self):
        """Test that unsupported HTTP methods return proper errors."""
        self.client.force_authenticate(user=self.player1)

        # PATCH on list endpoint
        response = self.client.patch(self.list_url, data={})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_rate_limiting(self):
        """Test API rate limiting (if implemented)."""
        self.client.force_authenticate(user=self.player1)

        # This test would verify rate limiting is working
        # Implementation depends on rate limiting configuration

        # For now, just verify normal requests work
        response = self.client.get(self.list_url, {"campaign": self.campaign.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_server_error_handling(self):
        """Test handling of server errors."""
        self.client.force_authenticate(user=self.player1)

        # Mock a server error in the get_queryset method
        with patch("api.views.character_views.Character.objects.all") as mock_all:
            mock_all.side_effect = Exception("Database error")

            response = self.client.get(self.list_url, {"campaign": self.campaign.pk})
            self.assertEqual(
                response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def test_concurrent_modification_handling(self):
        """Test handling of concurrent modifications."""
        self.client.force_authenticate(user=self.player1)

        # Simulate concurrent modification by updating character between read and write
        # Another user updates the character
        self.character1.name = "Concurrently Modified"
        self.character1.save()

        # Try to update with potentially stale data
        update_data = {
            "name": "My Update",
            "description": "Updated description",
        }

        response = self.client.patch(self.detail_url1, data=update_data)
        # Should still succeed (last write wins)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify final state
        self.character1.refresh_from_db()
        self.assertEqual(self.character1.name, "My Update")
