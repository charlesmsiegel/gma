"""
Simple migration test for mixin field application.

Tests that the essential functionality works after applying mixin fields
to Character, Item, and Location models.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from campaigns.models import Campaign
from characters.models import Character
from items.models import Item
from locations.models import Location

User = get_user_model()


class MixinMigrationTest(TestCase):
    """Test that mixin fields work correctly after migration."""

    def setUp(self):
        """Set up test data."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="pass123"
        )
        self.player = User.objects.create_user(
            username="player", email="player@test.com", password="pass123"
        )

        self.campaign = Campaign.objects.create(
            name="Test Campaign", owner=self.owner, game_system="mage"
        )

    def test_character_mixin_fields(self):
        """Test Character has working mixin fields."""
        character = Character.objects.create(
            name="Test Character",
            campaign=self.campaign,
            player_owner=self.player,
            game_system="mage",
        )

        # Basic fields work
        self.assertEqual(character.name, "Test Character")
        self.assertIsNotNone(character.created_at)
        self.assertIsNotNone(character.updated_at)

        # Audit tracking works
        character.save(user=self.owner)
        character.refresh_from_db()
        self.assertEqual(character.modified_by, self.owner)

    def test_item_mixin_fields(self):
        """Test Item has working mixin fields."""
        item = Item.objects.create(
            name="Test Item", campaign=self.campaign, created_by=self.player
        )

        # Basic fields work
        self.assertEqual(item.name, "Test Item")
        self.assertIsNotNone(item.created_at)
        self.assertEqual(item.created_by, self.player)

        # Audit tracking works
        item.save(user=self.owner)
        item.refresh_from_db()
        self.assertEqual(item.modified_by, self.owner)

    def test_location_mixin_fields(self):
        """Test Location has working mixin fields."""
        location = Location.objects.create(
            name="Test Location", campaign=self.campaign, created_by=self.player
        )

        # Basic fields work
        self.assertEqual(location.name, "Test Location")
        self.assertIsNotNone(location.created_at)
        self.assertEqual(location.created_by, self.player)

        # Audit tracking works
        location.save(user=self.owner)
        location.refresh_from_db()
        self.assertEqual(location.modified_by, self.owner)
