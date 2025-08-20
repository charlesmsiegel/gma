"""
Base test case for Character API tests.

This module provides the common setup and utilities for character API endpoint tests,
including test users, campaigns, characters, and authentication handling.
"""

from django.contrib.auth import get_user_model
from django.urls import reverse
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
            allow_gm_character_deletion=True,  # Enable GM deletion for tests
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
