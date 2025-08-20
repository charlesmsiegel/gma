"""
Tests for specialized Character API functionality.

This module tests specialized functionality including polymorphic serialization,
error handling, and advanced API features for character endpoints.
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status

from .test_character_api_base import BaseCharacterAPITestCase

User = get_user_model()


class CharacterPolymorphicSerializationTest(BaseCharacterAPITestCase):
    """Test polymorphic serialization for different character types."""

    def setUp(self):
        """Set up additional character types for testing."""
        super().setUp()

        # Create different character types
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

    def test_polymorphic_character_serialization(self):
        """Test that polymorphic characters are serialized with type-specific fields."""
        if not self.mage_character:
            self.fail("Failed to create MageCharacter in setUp")

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
            self.fail("Failed to create MageCharacter in setUp")

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
            self.fail("Failed to create MageCharacter in setUp")

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
