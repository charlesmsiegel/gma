"""
Tests for Character API list endpoint.

This module tests the character list endpoint functionality including:
- Authentication and permission checks
- Filtering by campaign and user
- Role-based access control
- Pagination and search
- Soft delete handling
"""

from django.contrib.auth import get_user_model
from rest_framework import status

from characters.models import Character

from .test_character_api_base import BaseCharacterAPITestCase

User = get_user_model()


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
