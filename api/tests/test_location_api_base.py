"""
Base test case for Location API tests.

This module provides the common setup and utilities for location API endpoint tests,
including test users, campaigns, characters, locations, and authentication handling.
"""

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from campaigns.models import Campaign, CampaignMembership
from characters.models import Character
from locations.models import Location

User = get_user_model()


class BaseLocationAPITestCase(APITestCase):
    """Base test case with common setup for location API tests."""

    def setUp(self):
        """Set up test users, campaigns, characters, and locations."""
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

        # Create test campaigns - one public, one private
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            slug="test-campaign",
            owner=self.owner,
            game_system="Mage: The Ascension",
            is_public=False,
        )

        self.public_campaign = Campaign.objects.create(
            name="Public Campaign",
            slug="public-campaign",
            owner=self.owner,
            game_system="Mage: The Ascension",
            is_public=True,
        )

        # Create memberships for main campaign
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
        self.npc_character = Character.objects.create(
            name="GM NPC",
            description="NPC managed by GM",
            campaign=self.campaign,
            player_owner=self.gm,
            game_system="Mage: The Ascension",
            npc=True,
        )

        # Create test locations with hierarchy
        # Root level locations
        self.location1 = Location.objects.create(
            name="Test City",
            description="A large test city",
            campaign=self.campaign,
            created_by=self.owner,
        )

        self.location2 = Location.objects.create(
            name="Player's House",
            description="A house owned by player1's character",
            campaign=self.campaign,
            owned_by=self.character1,
            created_by=self.player1,
        )

        # Child locations
        self.child_location1 = Location.objects.create(
            name="City Center",
            description="The central district of the city",
            campaign=self.campaign,
            parent=self.location1,
            created_by=self.gm,
        )

        self.child_location2 = Location.objects.create(
            name="Living Room",
            description="The main living area",
            campaign=self.campaign,
            parent=self.location2,
            owned_by=self.character1,
            created_by=self.player1,
        )

        # Grandchild location
        self.grandchild_location = Location.objects.create(
            name="Coffee Shop",
            description="A popular coffee shop in the city center",
            campaign=self.campaign,
            parent=self.child_location1,
            owned_by=self.npc_character,
            created_by=self.gm,
        )

        # Location in public campaign
        self.public_location = Location.objects.create(
            name="Public Location",
            description="A location in the public campaign",
            campaign=self.public_campaign,
            created_by=self.owner,
        )

        # API URLs (will be defined when location API is implemented)
        self.list_url = reverse("api:locations-list")
        self.detail_url1 = reverse(
            "api:locations-detail", kwargs={"pk": self.location1.pk}
        )
        self.detail_url2 = reverse(
            "api:locations-detail", kwargs={"pk": self.location2.pk}
        )
        self.children_url1 = reverse(
            "api:locations-children", kwargs={"pk": self.location1.pk}
        )
        self.bulk_url = reverse("api:locations-bulk")

    def get_detail_url(self, location_id):
        """Helper to get detail URL for any location."""
        return reverse("api:locations-detail", kwargs={"pk": location_id})

    def get_children_url(self, location_id):
        """Helper to get children URL for any location."""
        return reverse("api:locations-children", kwargs={"pk": location_id})

    def assertLocationHierarchy(
        self, location_data, expected_parent_id=None, expected_children_count=0
    ):
        """Helper to assert location hierarchy in API response."""
        if expected_parent_id:
            self.assertIn("parent", location_data)
            self.assertEqual(location_data["parent"]["id"], expected_parent_id)
        else:
            self.assertTrue(
                location_data.get("parent") is None,
                f"Expected no parent but got: {location_data.get('parent')}",
            )

        if "children" in location_data:
            self.assertEqual(
                len(location_data["children"]),
                expected_children_count,
                f"Expected {expected_children_count} children but got "
                f"{len(location_data['children'])}",
            )

    def assertLocationOwnership(self, location_data, expected_owner_id=None):
        """Helper to assert location ownership in API response."""
        if expected_owner_id:
            self.assertIn("owned_by", location_data)
            self.assertEqual(location_data["owned_by"]["id"], expected_owner_id)
        else:
            self.assertTrue(
                location_data.get("owned_by") is None,
                f"Expected no owner but got: {location_data.get('owned_by')}",
            )
