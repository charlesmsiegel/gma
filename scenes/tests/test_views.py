"""
Tests for scene views and web interface functionality.

Tests for Issues 37-41:
- Issue 37: Scene creation and management forms
- Issue 38: Character participation management (AJAX)
- Issue 39: Scene list and detail views with search
- Issue 40: Scene status management
"""

import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from campaigns.models import Campaign, CampaignMembership
from characters.models import Character
from scenes.models import Scene, SceneStatusChangeLog

User = get_user_model()


class SceneViewTestCase(TestCase):
    """Base test case for scene views with common setup."""

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
            max_characters_per_player=0,  # Unlimited
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
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Test System",
        )
        self.character2 = Character.objects.create(
            name="Player2 Character",
            campaign=self.campaign,
            player_owner=self.player2,
            game_system="Test System",
        )
        self.gm_character = Character.objects.create(
            name="GM NPC",
            campaign=self.campaign,
            player_owner=self.gm,
            game_system="Test System",
        )

        # Create test scenes
        self.scene1 = Scene.objects.create(
            name="Active Scene",
            description="An active test scene",
            campaign=self.campaign,
            created_by=self.gm,
            status="ACTIVE",
        )
        self.scene1.participants.add(self.character1, self.character2)

        self.scene2 = Scene.objects.create(
            name="Closed Scene",
            description="A closed test scene",
            campaign=self.campaign,
            created_by=self.owner,
            status="CLOSED",
        )

        # URLs
        self.campaign_scenes_url = reverse(
            "scenes:campaign_scenes", kwargs={"campaign_slug": self.campaign.slug}
        )


class SceneListViewTest(SceneViewTestCase):
    """Test scene list functionality (Issue 39)."""

    def test_scene_list_requires_authentication(self):
        """Test that scene list requires authentication."""
        response = self.client.get(self.campaign_scenes_url)
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_scene_list_requires_campaign_membership(self):
        """Test that non-members cannot view scenes."""
        self.client.login(username="nonmember", password="testpass123")
        response = self.client.get(self.campaign_scenes_url)
        self.assertEqual(response.status_code, 404)

    def test_scene_list_as_owner(self):
        """Test scene list view as campaign owner."""
        self.client.login(username="owner", password="testpass123")
        response = self.client.get(self.campaign_scenes_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Active Scene")
        self.assertContains(response, "Closed Scene")
        self.assertContains(response, self.campaign.name)

        # Check context
        self.assertTrue(response.context["can_create_scene"])
        self.assertTrue(response.context["can_manage_scenes"])

    def test_scene_list_as_gm(self):
        """Test scene list view as GM."""
        self.client.login(username="gm", password="testpass123")
        response = self.client.get(self.campaign_scenes_url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["can_create_scene"])
        self.assertTrue(response.context["can_manage_scenes"])

    def test_scene_list_as_player(self):
        """Test scene list view as player."""
        self.client.login(username="player1", password="testpass123")
        response = self.client.get(self.campaign_scenes_url)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["can_create_scene"])
        self.assertFalse(response.context["can_manage_scenes"])

    def test_scene_list_as_observer(self):
        """Test scene list view as observer."""
        self.client.login(username="observer", password="testpass123")
        response = self.client.get(self.campaign_scenes_url)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["can_create_scene"])
        self.assertFalse(response.context["can_manage_scenes"])

    def test_scene_list_displays_scene_info(self):
        """Test that scene list displays proper scene information."""
        self.client.login(username="owner", password="testpass123")
        response = self.client.get(self.campaign_scenes_url)

        self.assertContains(response, "Active Scene")
        self.assertContains(response, "An active test scene")
        self.assertContains(response, "ACTIVE")
        self.assertContains(response, "2 participants")  # character1, character2

    def test_scene_list_with_no_scenes(self):
        """Test scene list when campaign has no scenes."""
        # Create a new campaign without scenes
        empty_campaign = Campaign.objects.create(
            name="Empty Campaign",
            slug="empty-campaign",
            owner=self.owner,
            max_characters_per_player=0,  # Unlimited
        )

        empty_url = reverse(
            "scenes:campaign_scenes", kwargs={"campaign_slug": empty_campaign.slug}
        )

        self.client.login(username="owner", password="testpass123")
        response = self.client.get(empty_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No scenes found")


class SceneDetailViewTest(SceneViewTestCase):
    """Test scene detail view functionality (Issue 39)."""

    def test_scene_detail_requires_authentication(self):
        """Test that scene detail requires authentication."""
        url = reverse("scenes:scene_detail", kwargs={"pk": self.scene1.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_scene_detail_requires_campaign_membership(self):
        """Test that non-members cannot view scene details."""
        self.client.login(username="nonmember", password="testpass123")
        url = reverse("scenes:scene_detail", kwargs={"pk": self.scene1.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_scene_detail_as_member(self):
        """Test scene detail view as campaign member."""
        self.client.login(username="player1", password="testpass123")
        url = reverse("scenes:scene_detail", kwargs={"pk": self.scene1.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Active Scene")
        self.assertContains(response, "An active test scene")
        self.assertContains(response, "Player1 Character")
        self.assertContains(response, "Player2 Character")

    def test_scene_detail_displays_participants(self):
        """Test that scene detail displays participant list."""
        self.client.login(username="gm", password="testpass123")
        url = reverse("scenes:scene_detail", kwargs={"pk": self.scene1.pk})
        response = self.client.get(url)

        self.assertContains(response, "Participants")
        self.assertContains(response, "Player1 Character")
        self.assertContains(response, "Player2 Character")

    def test_scene_detail_shows_management_options_for_gm(self):
        """Test that GMs see management options in scene detail."""
        self.client.login(username="gm", password="testpass123")
        url = reverse("scenes:scene_detail", kwargs={"pk": self.scene1.pk})
        response = self.client.get(url)

        self.assertTrue(response.context["can_manage_scene"])
        self.assertContains(response, "Edit Scene")
        self.assertContains(response, "Add Participants")

    def test_scene_detail_no_management_for_players(self):
        """Test that players don't see management options."""
        self.client.login(username="player1", password="testpass123")
        url = reverse("scenes:scene_detail", kwargs={"pk": self.scene1.pk})
        response = self.client.get(url)

        self.assertFalse(response.context["can_manage_scene"])
        self.assertNotContains(response, "Edit Scene")

    def test_scene_detail_nonexistent_scene(self):
        """Test scene detail for nonexistent scene returns 404."""
        self.client.login(username="owner", password="testpass123")
        url = reverse("scenes:scene_detail", kwargs={"pk": 99999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class SceneCreateViewTest(SceneViewTestCase):
    """Test scene creation functionality (Issue 37)."""

    def test_scene_create_requires_authentication(self):
        """Test that scene creation requires authentication."""
        url = reverse(
            "scenes:scene_create", kwargs={"campaign_slug": self.campaign.slug}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_scene_create_requires_campaign_membership(self):
        """Test that non-members cannot create scenes."""
        self.client.login(username="nonmember", password="testpass123")
        url = reverse(
            "scenes:scene_create", kwargs={"campaign_slug": self.campaign.slug}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_scene_create_permission_owner(self):
        """Test that campaign owner can create scenes."""
        self.client.login(username="owner", password="testpass123")
        url = reverse(
            "scenes:scene_create", kwargs={"campaign_slug": self.campaign.slug}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_scene_create_permission_gm(self):
        """Test that GM can create scenes."""
        self.client.login(username="gm", password="testpass123")
        url = reverse(
            "scenes:scene_create", kwargs={"campaign_slug": self.campaign.slug}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_scene_create_permission_denied_player(self):
        """Test that players cannot create scenes."""
        self.client.login(username="player1", password="testpass123")
        url = reverse(
            "scenes:scene_create", kwargs={"campaign_slug": self.campaign.slug}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_scene_create_permission_denied_observer(self):
        """Test that observers cannot create scenes."""
        self.client.login(username="observer", password="testpass123")
        url = reverse(
            "scenes:scene_create", kwargs={"campaign_slug": self.campaign.slug}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_scene_create_form_displays(self):
        """Test that scene creation form displays properly."""
        self.client.login(username="gm", password="testpass123")
        url = reverse(
            "scenes:scene_create", kwargs={"campaign_slug": self.campaign.slug}
        )
        response = self.client.get(url)

        self.assertContains(response, "Create New Scene")
        self.assertContains(response, 'name="name"')
        self.assertContains(response, 'name="description"')

    def test_scene_create_post_valid_data(self):
        """Test scene creation with valid data."""
        self.client.login(username="gm", password="testpass123")
        url = reverse(
            "scenes:scene_create", kwargs={"campaign_slug": self.campaign.slug}
        )

        data = {
            "name": "New Test Scene",
            "description": "A scene created via form",
        }

        response = self.client.post(url, data)

        # Should redirect to scene detail or scene list
        self.assertEqual(response.status_code, 302)

        # Verify scene was created
        scene = Scene.objects.get(name="New Test Scene")
        self.assertEqual(scene.campaign, self.campaign)
        self.assertEqual(scene.created_by, self.gm)
        self.assertEqual(scene.status, "ACTIVE")

    def test_scene_create_post_invalid_data(self):
        """Test scene creation with invalid data."""
        self.client.login(username="gm", password="testpass123")
        url = reverse(
            "scenes:scene_create", kwargs={"campaign_slug": self.campaign.slug}
        )

        data = {
            "name": "",  # Empty name should fail
            "description": "No name provided",
        }

        response = self.client.post(url, data)

        # Should stay on form with errors
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This field is required")


class SceneSearchViewTest(SceneViewTestCase):
    """Test scene search functionality (Issue 39)."""

    def setUp(self):
        """Set up additional test data for search testing."""
        super().setUp()

        # Create additional scenes for search testing
        self.archived_scene = Scene.objects.create(
            name="Archived Scene",
            description="An archived scene with keywords",
            campaign=self.campaign,
            created_by=self.gm,
            status="ARCHIVED",
        )

        self.keyword_scene = Scene.objects.create(
            name="Special Keywords Scene",
            description="Contains dragon and treasure",
            campaign=self.campaign,
            created_by=self.owner,
            status="ACTIVE",
        )
        self.keyword_scene.participants.add(self.gm_character)

    def test_search_by_text(self):
        """Test text-based scene search."""
        self.client.login(username="owner", password="testpass123")

        # Search for "dragon"
        response = self.client.get(self.campaign_scenes_url, {"search": "dragon"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Special Keywords Scene")
        self.assertNotContains(response, "Active Scene")

    def test_search_by_name(self):
        """Test search by scene name."""
        self.client.login(username="owner", password="testpass123")

        response = self.client.get(self.campaign_scenes_url, {"search": "Archived"})

        self.assertContains(response, "Archived Scene")
        self.assertNotContains(response, "Active Scene")

    def test_search_filter_by_status(self):
        """Test filtering scenes by status."""
        self.client.login(username="owner", password="testpass123")

        # Filter for active scenes only
        response = self.client.get(self.campaign_scenes_url, {"status": "ACTIVE"})

        self.assertContains(response, "Active Scene")
        self.assertContains(response, "Special Keywords Scene")
        self.assertNotContains(response, "Closed Scene")

    def test_search_filter_by_participant(self):
        """Test filtering scenes by participant."""
        self.client.login(username="owner", password="testpass123")

        response = self.client.get(
            self.campaign_scenes_url, {"participant": self.character1.pk}
        )

        self.assertContains(response, "Active Scene")
        self.assertNotContains(response, "Keyword Scene")

    def test_search_date_range_filter(self):
        """Test filtering scenes by date range."""
        self.client.login(username="owner", password="testpass123")

        # Test with future date (should show no scenes)
        from datetime import date, timedelta

        future_date = date.today() + timedelta(days=1)

        response = self.client.get(
            self.campaign_scenes_url, {"date_from": future_date.isoformat()}
        )

        # Should show no scenes created before future date
        self.assertEqual(len(response.context["scenes"]), 0)

    def test_search_combined_filters(self):
        """Test search with multiple filters combined."""
        self.client.login(username="owner", password="testpass123")

        response = self.client.get(
            self.campaign_scenes_url,
            {
                "status": "ACTIVE",
                "search": "Special",
            },
        )

        self.assertContains(response, "Special Keywords Scene")
        self.assertNotContains(response, "Active Scene")  # Different name
        self.assertNotContains(response, "Closed Scene")  # Different status


class SceneStatusManagementTest(SceneViewTestCase):
    """Test scene status management functionality (Issue 40)."""

    def test_status_change_requires_authentication(self):
        """Test that status changes require authentication."""
        url = reverse("scenes:change_status", kwargs={"pk": self.scene1.pk})
        response = self.client.post(url, {"status": "CLOSED"})
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_status_change_requires_campaign_membership(self):
        """Test that non-members cannot change status."""
        self.client.login(username="nonmember", password="testpass123")
        url = reverse("scenes:change_status", kwargs={"pk": self.scene1.pk})
        response = self.client.post(url, {"status": "CLOSED"})
        self.assertEqual(response.status_code, 404)

    def test_status_change_permission_owner(self):
        """Test that campaign owner can change scene status."""
        self.client.login(username="owner", password="testpass123")
        url = reverse("scenes:change_status", kwargs={"pk": self.scene1.pk})

        response = self.client.post(url, {"status": "CLOSED"})

        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.scene1.refresh_from_db()
        self.assertEqual(self.scene1.status, "CLOSED")

    def test_status_change_permission_gm(self):
        """Test that GM can change scene status."""
        self.client.login(username="gm", password="testpass123")
        url = reverse("scenes:change_status", kwargs={"pk": self.scene1.pk})

        response = self.client.post(url, {"status": "CLOSED"})

        self.assertEqual(response.status_code, 302)
        self.scene1.refresh_from_db()
        self.assertEqual(self.scene1.status, "CLOSED")

    def test_status_change_permission_denied_player(self):
        """Test that players cannot change scene status."""
        self.client.login(username="player1", password="testpass123")
        url = reverse("scenes:change_status", kwargs={"pk": self.scene1.pk})
        response = self.client.post(url, {"status": "CLOSED"})
        self.assertEqual(response.status_code, 403)

    def test_status_change_permission_denied_observer(self):
        """Test that observers cannot change scene status."""
        self.client.login(username="observer", password="testpass123")
        url = reverse("scenes:change_status", kwargs={"pk": self.scene1.pk})
        response = self.client.post(url, {"status": "CLOSED"})
        self.assertEqual(response.status_code, 403)

    def test_valid_status_transitions(self):
        """Test valid status transitions."""
        self.client.login(username="gm", password="testpass123")
        url = reverse("scenes:change_status", kwargs={"pk": self.scene1.pk})

        # ACTIVE -> CLOSED
        response = self.client.post(url, {"status": "CLOSED"})
        self.assertEqual(response.status_code, 302)
        self.scene1.refresh_from_db()
        self.assertEqual(self.scene1.status, "CLOSED")

        # CLOSED -> ARCHIVED
        response = self.client.post(url, {"status": "ARCHIVED"})
        self.assertEqual(response.status_code, 302)
        self.scene1.refresh_from_db()
        self.assertEqual(self.scene1.status, "ARCHIVED")

    def test_invalid_status_transitions(self):
        """Test that invalid status transitions are rejected."""
        self.client.login(username="gm", password="testpass123")
        url = reverse("scenes:change_status", kwargs={"pk": self.scene1.pk})

        # Try to skip from ACTIVE directly to ARCHIVED
        response = self.client.post(url, {"status": "ARCHIVED"})

        # Should redirect back to scene detail with error message
        self.assertEqual(response.status_code, 302)
        self.scene1.refresh_from_db()
        self.assertEqual(self.scene1.status, "ACTIVE")  # Unchanged

    def test_status_change_audit_logging(self):
        """Test that status changes are logged for audit trail."""
        self.client.login(username="gm", password="testpass123")
        url = reverse("scenes:change_status", kwargs={"pk": self.scene1.pk})

        # Mock audit logging
        with patch("scenes.models.Scene.log_status_change") as mock_log:
            self.client.post(url, {"status": "CLOSED"})

            mock_log.assert_called_once_with(
                user=self.gm, old_status="ACTIVE", new_status="CLOSED"
            )

    def test_status_change_database_logging(self):
        """Test that status changes are saved to audit log database."""
        self.client.login(username="gm", password="testpass123")
        url = reverse("scenes:change_status", kwargs={"pk": self.scene1.pk})

        # Verify no log entries exist initially
        self.assertEqual(SceneStatusChangeLog.objects.count(), 0)

        # Make status change
        response = self.client.post(url, {"status": "CLOSED"})
        self.assertEqual(response.status_code, 302)

        # Verify scene status was changed
        self.scene1.refresh_from_db()
        self.assertEqual(self.scene1.status, "CLOSED")

        # Verify audit log entry was created
        self.assertEqual(SceneStatusChangeLog.objects.count(), 1)

        log_entry = SceneStatusChangeLog.objects.first()
        self.assertEqual(log_entry.scene, self.scene1)
        self.assertEqual(log_entry.user, self.gm)
        self.assertEqual(log_entry.old_status, "ACTIVE")
        self.assertEqual(log_entry.new_status, "CLOSED")
        self.assertIsNotNone(log_entry.timestamp)


class ParticipantManagementTest(SceneViewTestCase):
    """Test character participation management (Issue 38)."""

    def test_add_participant_requires_authentication(self):
        """Test that adding participants requires authentication."""
        url = reverse("scenes:add_participant", kwargs={"pk": self.scene1.pk})
        response = self.client.post(
            url, {"character_id": self.gm_character.pk}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 401)

    def test_add_participant_requires_campaign_membership(self):
        """Test that non-members cannot add participants."""
        self.client.login(username="nonmember", password="testpass123")
        url = reverse("scenes:add_participant", kwargs={"pk": self.scene1.pk})
        response = self.client.post(
            url,
            json.dumps({"character_id": self.gm_character.pk}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)

    def test_add_participant_as_gm(self):
        """Test that GM can add any character to scene."""
        self.client.login(username="gm", password="testpass123")
        url = reverse("scenes:add_participant", kwargs={"pk": self.scene1.pk})

        response = self.client.post(
            url,
            json.dumps({"character_id": self.gm_character.pk}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            self.scene1.participants.filter(pk=self.gm_character.pk).exists()
        )

    def test_add_participant_as_owner(self):
        """Test that campaign owner can add any character to scene."""
        self.client.login(username="owner", password="testpass123")
        url = reverse("scenes:add_participant", kwargs={"pk": self.scene1.pk})

        response = self.client.post(
            url,
            json.dumps({"character_id": self.gm_character.pk}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            self.scene1.participants.filter(pk=self.gm_character.pk).exists()
        )

    def test_add_own_character_as_player(self):
        """Test that players can add their own characters."""
        # Create a new character for player1 that's not in the scene
        new_char = Character.objects.create(
            name="Player1 Second Character",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Test System",
        )

        self.client.login(username="player1", password="testpass123")
        url = reverse("scenes:add_participant", kwargs={"pk": self.scene1.pk})

        response = self.client.post(
            url,
            json.dumps({"character_id": new_char.pk}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.scene1.participants.filter(pk=new_char.pk).exists())

    def test_add_others_character_as_player_denied(self):
        """Test that players cannot add others' characters."""
        self.client.login(username="player1", password="testpass123")
        url = reverse("scenes:add_participant", kwargs={"pk": self.scene1.pk})

        response = self.client.post(
            url,
            json.dumps({"character_id": self.character2.pk}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)

    def test_remove_participant_as_gm(self):
        """Test that GM can remove any participant."""
        self.client.login(username="gm", password="testpass123")
        url = reverse(
            "scenes:remove_participant",
            kwargs={"pk": self.scene1.pk, "character_id": self.character1.pk},
        )

        response = self.client.delete(url)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            self.scene1.participants.filter(pk=self.character1.pk).exists()
        )

    def test_remove_own_character_as_player(self):
        """Test that players can remove their own characters."""
        self.client.login(username="player1", password="testpass123")
        url = reverse(
            "scenes:remove_participant",
            kwargs={"pk": self.scene1.pk, "character_id": self.character1.pk},
        )

        response = self.client.delete(url)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            self.scene1.participants.filter(pk=self.character1.pk).exists()
        )

    def test_remove_others_character_as_player_denied(self):
        """Test that players cannot remove others' characters."""
        self.client.login(username="player1", password="testpass123")
        url = reverse(
            "scenes:remove_participant",
            kwargs={"pk": self.scene1.pk, "character_id": self.character2.pk},
        )

        response = self.client.delete(url)

        self.assertEqual(response.status_code, 403)

    def test_add_participant_invalid_character(self):
        """Test adding participant with invalid character ID."""
        self.client.login(username="gm", password="testpass123")
        url = reverse("scenes:add_participant", kwargs={"pk": self.scene1.pk})

        response = self.client.post(
            url, json.dumps({"character_id": 99999}), content_type="application/json"
        )

        self.assertEqual(response.status_code, 404)

    def test_add_participant_different_campaign(self):
        """Test that characters from different campaigns cannot be added."""
        # Create character in different campaign
        other_campaign = Campaign.objects.create(
            name="Other Campaign",
            slug="other-campaign",
            owner=self.owner,
            max_characters_per_player=0,  # Unlimited
        )
        other_character = Character.objects.create(
            name="Other Character",
            campaign=other_campaign,
            player_owner=self.owner,
            game_system="Test System",
        )

        self.client.login(username="gm", password="testpass123")
        url = reverse("scenes:add_participant", kwargs={"pk": self.scene1.pk})

        response = self.client.post(
            url,
            json.dumps({"character_id": other_character.pk}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

    def test_add_participant_already_participating(self):
        """Test adding a character that's already participating."""
        self.client.login(username="gm", password="testpass123")
        url = reverse("scenes:add_participant", kwargs={"pk": self.scene1.pk})

        response = self.client.post(
            url,
            json.dumps({"character_id": self.character1.pk}),
            content_type="application/json",
        )

        # Should handle gracefully (idempotent)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("already participating", data["message"].lower())

    def test_participant_filtering_by_campaign(self):
        """Test that character selection is filtered by campaign."""
        self.client.login(username="gm", password="testpass123")
        url = reverse(
            "scenes:get_available_characters",
            kwargs={"campaign_slug": self.campaign.slug},
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Should only include characters from this campaign
        character_ids = [char["id"] for char in data["characters"]]
        self.assertIn(self.character1.pk, character_ids)
        self.assertIn(self.character2.pk, character_ids)
        self.assertIn(self.gm_character.pk, character_ids)

    def test_ajax_response_format(self):
        """Test that AJAX responses have proper JSON format."""
        self.client.login(username="gm", password="testpass123")
        url = reverse("scenes:add_participant", kwargs={"pk": self.scene1.pk})

        response = self.client.post(
            url,
            json.dumps({"character_id": self.gm_character.pk}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")

        data = response.json()
        self.assertIn("success", data)
        self.assertIn("message", data)
        self.assertIn("character", data)
        self.assertEqual(data["character"]["name"], self.gm_character.name)
