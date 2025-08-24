"""
Tests for scene permission system.

Tests comprehensive permission checking for Issues 37-41:
- Campaign membership requirements
- Role-based permissions (OWNER, GM, PLAYER, OBSERVER)
- Character ownership permissions for participation management
- Security considerations (404 vs 403 responses)
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from campaigns.models import Campaign, CampaignMembership
from characters.models import Character
from scenes.models import Scene

User = get_user_model()


class ScenePermissionTestCase(TestCase):
    """Base test case for scene permissions with common setup."""

    def setUp(self):
        """Set up test users, campaigns, and scenes."""
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

        # Create test scene
        self.scene = Scene.objects.create(
            name="Test Scene",
            description="A test scene",
            campaign=self.campaign,
            created_by=self.gm,
            status="ACTIVE",
        )
        self.scene.participants.add(self.character1)


class SceneViewPermissionTest(ScenePermissionTestCase):
    """Test permissions for scene views (web interface)."""

    def test_scene_list_permission_matrix(self):
        """Test scene list permissions for all user types."""
        url = reverse(
            "scenes:campaign_scenes", kwargs={"campaign_slug": self.campaign.slug}
        )

        # Owner should have access
        self.client.login(username="owner", password="testpass123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["can_create_scene"])
        self.assertTrue(response.context["can_manage_scenes"])

        # GM should have access
        self.client.login(username="gm", password="testpass123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["can_create_scene"])
        self.assertTrue(response.context["can_manage_scenes"])

        # Player should have read-only access
        self.client.login(username="player1", password="testpass123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["can_create_scene"])
        self.assertFalse(response.context["can_manage_scenes"])

        # Observer should have read-only access
        self.client.login(username="observer", password="testpass123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["can_create_scene"])
        self.assertFalse(response.context["can_manage_scenes"])

        # Non-member should get 404
        self.client.login(username="nonmember", password="testpass123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_scene_detail_permission_matrix(self):
        """Test scene detail permissions for all user types."""
        url = reverse("scenes:scene_detail", kwargs={"pk": self.scene.pk})

        # Owner should have management access
        self.client.login(username="owner", password="testpass123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["can_manage_scene"])

        # GM should have management access
        self.client.login(username="gm", password="testpass123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["can_manage_scene"])

        # Player should have read-only access
        self.client.login(username="player1", password="testpass123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["can_manage_scene"])

        # Observer should have read-only access
        self.client.login(username="observer", password="testpass123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["can_manage_scene"])

        # Non-member should get 404
        self.client.login(username="nonmember", password="testpass123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_scene_create_permission_matrix(self):
        """Test scene creation permissions."""
        url = reverse(
            "scenes:scene_create", kwargs={"campaign_slug": self.campaign.slug}
        )

        # Owner can create
        self.client.login(username="owner", password="testpass123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # GM can create
        self.client.login(username="gm", password="testpass123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Player cannot create
        self.client.login(username="player1", password="testpass123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        # Observer cannot create
        self.client.login(username="observer", password="testpass123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        # Non-member gets 404
        self.client.login(username="nonmember", password="testpass123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_scene_edit_permission_matrix(self):
        """Test scene editing permissions."""
        url = reverse("scenes:scene_edit", kwargs={"pk": self.scene.pk})

        # Owner can edit
        self.client.login(username="owner", password="testpass123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # GM can edit
        self.client.login(username="gm", password="testpass123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Player cannot edit
        self.client.login(username="player1", password="testpass123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        # Observer cannot edit
        self.client.login(username="observer", password="testpass123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        # Non-member gets 404
        self.client.login(username="nonmember", password="testpass123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_scene_status_change_permissions(self):
        """Test scene status change permissions."""
        url = reverse("scenes:change_status", kwargs={"pk": self.scene.pk})

        # Owner can change status
        self.client.login(username="owner", password="testpass123")
        response = self.client.post(url, {"status": "CLOSED"})
        self.assertEqual(response.status_code, 302)  # Redirect after success

        # Reset status for next test
        self.scene.status = "ACTIVE"
        self.scene.save()

        # GM can change status
        self.client.login(username="gm", password="testpass123")
        response = self.client.post(url, {"status": "CLOSED"})
        self.assertEqual(response.status_code, 302)

        # Reset status for next test
        self.scene.status = "ACTIVE"
        self.scene.save()

        # Player cannot change status
        self.client.login(username="player1", password="testpass123")
        response = self.client.post(url, {"status": "CLOSED"})
        self.assertEqual(response.status_code, 403)

        # Observer cannot change status
        self.client.login(username="observer", password="testpass123")
        response = self.client.post(url, {"status": "CLOSED"})
        self.assertEqual(response.status_code, 403)

        # Non-member gets 404
        self.client.login(username="nonmember", password="testpass123")
        response = self.client.post(url, {"status": "CLOSED"})
        self.assertEqual(response.status_code, 404)


class SceneParticipantPermissionTest(ScenePermissionTestCase):
    """Test permissions for participant management."""

    def test_add_participant_permission_matrix(self):
        """Test permissions for adding participants."""
        url = reverse("scenes:add_participant", kwargs={"pk": self.scene.pk})
        data = {"character_id": self.gm_character.pk}

        # Owner can add any character
        self.client.login(username="owner", password="testpass123")
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)

        # Remove for next test
        self.scene.participants.remove(self.gm_character)

        # GM can add any character
        self.client.login(username="gm", password="testpass123")
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)

    def test_player_can_only_add_own_characters(self):
        """Test that players can only add their own characters."""
        # Create additional character for player1
        player1_char2 = Character.objects.create(
            name="Player1 Second Character",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Test System",
        )

        url = reverse("scenes:add_participant", kwargs={"pk": self.scene.pk})

        self.client.login(username="player1", password="testpass123")

        # Can add own character
        response = self.client.post(url, {"character_id": player1_char2.pk})
        self.assertEqual(response.status_code, 200)

        # Cannot add another player's character
        response = self.client.post(url, {"character_id": self.character2.pk})
        self.assertEqual(response.status_code, 403)

        # Cannot add GM character
        response = self.client.post(url, {"character_id": self.gm_character.pk})
        self.assertEqual(response.status_code, 403)

    def test_remove_participant_permission_matrix(self):
        """Test permissions for removing participants."""
        # Add gm_character to scene for testing
        self.scene.participants.add(self.gm_character)

        url = reverse(
            "scenes:remove_participant",
            kwargs={"pk": self.scene.pk, "character_id": self.gm_character.pk},
        )

        # Owner can remove any participant
        self.client.login(username="owner", password="testpass123")
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 200)

        # Add back for next test
        self.scene.participants.add(self.gm_character)

        # GM can remove any participant
        self.client.login(username="gm", password="testpass123")
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 200)

    def test_player_can_only_remove_own_characters(self):
        """Test that players can only remove their own characters."""
        # Add character2 to scene
        self.scene.participants.add(self.character2)

        self.client.login(username="player1", password="testpass123")

        # Can remove own character
        url = reverse(
            "scenes:remove_participant",
            kwargs={"pk": self.scene.pk, "character_id": self.character1.pk},
        )
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 200)

        # Cannot remove another player's character
        url = reverse(
            "scenes:remove_participant",
            kwargs={"pk": self.scene.pk, "character_id": self.character2.pk},
        )
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 403)

    def test_observer_cannot_manage_participants(self):
        """Test that observers cannot add or remove participants."""
        url_add = reverse("scenes:add_participant", kwargs={"pk": self.scene.pk})
        url_remove = reverse(
            "scenes:remove_participant",
            kwargs={"pk": self.scene.pk, "character_id": self.character1.pk},
        )

        self.client.login(username="observer", password="testpass123")

        # Cannot add participant
        response = self.client.post(url_add, {"character_id": self.gm_character.pk})
        self.assertEqual(response.status_code, 403)

        # Cannot remove participant
        response = self.client.delete(url_remove)
        self.assertEqual(response.status_code, 403)

    def test_non_member_participant_management_denied(self):
        """Test that non-members cannot manage participants."""
        url_add = reverse("scenes:add_participant", kwargs={"pk": self.scene.pk})
        url_remove = reverse(
            "scenes:remove_participant",
            kwargs={"pk": self.scene.pk, "character_id": self.character1.pk},
        )

        self.client.login(username="nonmember", password="testpass123")

        # Both operations should return 404
        response = self.client.post(url_add, {"character_id": self.gm_character.pk})
        self.assertEqual(response.status_code, 404)

        response = self.client.delete(url_remove)
        self.assertEqual(response.status_code, 404)


class SceneAPIPermissionTest(ScenePermissionTestCase, APITestCase):
    """Test API permissions for scenes."""

    def test_api_authentication_required(self):
        """Test that all API endpoints require authentication."""
        endpoints = [
            reverse("api:scenes-list"),
            reverse("api:scenes-detail", kwargs={"pk": self.scene.pk}),
            reverse("api:scenes-add-participant", kwargs={"pk": self.scene.pk}),
            reverse(
                "api:scenes-remove-participant",
                kwargs={"pk": self.scene.pk, "character_id": self.character1.pk},
            ),
        ]

        for url in endpoints:
            response = self.client.get(url)
            self.assertEqual(
                response.status_code,
                status.HTTP_401_UNAUTHORIZED,
                f"Endpoint {url} should require authentication",
            )

    def test_api_scene_list_permissions(self):
        """Test API scene list permissions."""
        url = reverse("api:scenes-list")

        # Campaign members can list scenes
        for user in [self.owner, self.gm, self.player1, self.observer]:
            self.client.force_authenticate(user=user)
            response = self.client.get(url, {"campaign": self.campaign.pk})
            self.assertIn(
                response.status_code,
                [status.HTTP_200_OK],
                f"User {user.username} should be able to list scenes",
            )

        # Non-members get 404
        self.client.force_authenticate(user=self.non_member)
        response = self.client.get(url, {"campaign": self.campaign.pk})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_api_scene_create_permissions(self):
        """Test API scene creation permissions."""
        url = reverse("api:scenes-list")
        scene_data = {
            "name": "API Test Scene",
            "description": "Created via API",
            "campaign": self.campaign.pk,
        }

        # Owner and GM can create
        for user in [self.owner, self.gm]:
            self.client.force_authenticate(user=user)
            response = self.client.post(url, data=scene_data)
            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                f"User {user.username} should be able to create scenes",
            )
            # Clean up
            Scene.objects.filter(name="API Test Scene").delete()

        # Players and observers cannot create
        for user in [self.player1, self.observer]:
            self.client.force_authenticate(user=user)
            response = self.client.post(url, data=scene_data)
            self.assertEqual(
                response.status_code,
                status.HTTP_403_FORBIDDEN,
                f"User {user.username} should not be able to create scenes",
            )

        # Non-members get 404
        self.client.force_authenticate(user=self.non_member)
        response = self.client.post(url, data=scene_data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_api_scene_update_permissions(self):
        """Test API scene update permissions."""
        url = reverse("api:scenes-detail", kwargs={"pk": self.scene.pk})
        update_data = {"name": "Updated Scene Name"}

        # Owner and GM can update
        for user in [self.owner, self.gm]:
            self.client.force_authenticate(user=user)
            response = self.client.patch(url, data=update_data)
            self.assertEqual(
                response.status_code,
                status.HTTP_200_OK,
                f"User {user.username} should be able to update scenes",
            )

        # Players and observers cannot update
        for user in [self.player1, self.observer]:
            self.client.force_authenticate(user=user)
            response = self.client.patch(url, data=update_data)
            self.assertEqual(
                response.status_code,
                status.HTTP_403_FORBIDDEN,
                f"User {user.username} should not be able to update scenes",
            )

        # Non-members get 404
        self.client.force_authenticate(user=self.non_member)
        response = self.client.patch(url, data=update_data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_api_participant_management_permissions(self):
        """Test API participant management permissions."""
        add_url = reverse("api:scenes-add-participant", kwargs={"pk": self.scene.pk})
        remove_url = reverse(
            "api:scenes-remove-participant",
            kwargs={"pk": self.scene.pk, "character_id": self.character1.pk},
        )

        # Owner and GM can manage any participants
        for user in [self.owner, self.gm]:
            self.client.force_authenticate(user=user)

            # Can add GM character
            response = self.client.post(add_url, {"character": self.gm_character.pk})
            self.assertIn(
                response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED]
            )

            # Can remove character
            response = self.client.delete(remove_url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            # Add back for next test
            self.scene.participants.add(self.character1)

    def test_api_player_participant_restrictions(self):
        """Test that players can only manage their own characters via API."""
        # Create additional character for player1
        player1_char2 = Character.objects.create(
            name="Player1 Second Character",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Test System",
        )

        add_url = reverse("api:scenes-add-participant", kwargs={"pk": self.scene.pk})

        self.client.force_authenticate(user=self.player1)

        # Can add own character
        response = self.client.post(add_url, {"character": player1_char2.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Cannot add other player's character
        response = self.client.post(add_url, {"character": self.character2.pk})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Can remove own character
        remove_url = reverse(
            "api:scenes-remove-participant",
            kwargs={"pk": self.scene.pk, "character_id": self.character1.pk},
        )
        response = self.client.delete(remove_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Cannot remove other player's character (add character2 first)
        self.scene.participants.add(self.character2)
        remove_url2 = reverse(
            "api:scenes-remove-participant",
            kwargs={"pk": self.scene.pk, "character_id": self.character2.pk},
        )
        response = self.client.delete(remove_url2)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_cross_campaign_character_protection(self):
        """Test that characters from other campaigns cannot be used."""
        # Create another campaign and character
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

        self.client.force_authenticate(user=self.owner)

        add_url = reverse("api:scenes-add-participant", kwargs={"pk": self.scene.pk})

        # Should not be able to add character from different campaign
        response = self.client.post(add_url, {"character": other_character.pk})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_api_permission_error_format(self):
        """Test that API permission errors return proper format."""
        self.client.force_authenticate(user=self.player1)

        # Try to create scene as player
        url = reverse("api:scenes-list")
        response = self.client.post(url, {"name": "Test", "campaign": self.campaign.pk})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        data = response.json()

        # Should have proper error structure
        self.assertIn("detail", data)

    def test_api_non_member_returns_404_not_403(self):
        """Test that non-members get 404 (not 403) to hide resource existence."""
        self.client.force_authenticate(user=self.non_member)

        endpoints_and_methods = [
            (reverse("api:scenes-list"), "get", {"campaign": self.campaign.pk}),
            (reverse("api:scenes-detail", kwargs={"pk": self.scene.pk}), "get", {}),
            (
                reverse("api:scenes-detail", kwargs={"pk": self.scene.pk}),
                "patch",
                {"name": "Test"},
            ),
        ]

        for url, method, data in endpoints_and_methods:
            response = getattr(self.client, method)(url, data=data)
            self.assertEqual(
                response.status_code,
                status.HTTP_404_NOT_FOUND,
                f"Non-member should get 404 for {method.upper()} {url}",
            )


class ScenePermissionEdgeCaseTest(ScenePermissionTestCase):
    """Test edge cases and security considerations for scene permissions."""

    def test_permission_check_with_deleted_campaign_membership(self):
        """Test permission handling when membership is deleted."""
        membership = CampaignMembership.objects.get(
            campaign=self.campaign, user=self.player1
        )

        # User has access initially
        self.client.login(username="player1", password="testpass123")
        url = reverse("scenes:scene_detail", kwargs={"pk": self.scene.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Delete membership
        membership.delete()

        # User should now be denied access
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_permission_check_with_changed_role(self):
        """Test permission handling when user role changes."""
        self.client.login(username="player1", password="testpass123")

        # Player initially cannot create scenes
        url = reverse(
            "scenes:scene_create", kwargs={"campaign_slug": self.campaign.slug}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        # Promote to GM
        membership = CampaignMembership.objects.get(
            campaign=self.campaign, user=self.player1
        )
        membership.role = "GM"
        membership.save()

        # Should now have create permissions
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_character_ownership_change_affects_participation_permissions(self):
        """Test that changing character ownership affects participation permissions."""
        self.client.login(username="player1", password="testpass123")

        # Player1 can initially remove their own character
        url = reverse(
            "scenes:remove_participant",
            kwargs={"pk": self.scene.pk, "character_id": self.character1.pk},
        )
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 200)

        # Add character back and change ownership
        self.scene.participants.add(self.character1)
        self.character1.player_owner = self.player2
        self.character1.save()

        # Player1 should no longer be able to remove the character
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 403)

    def test_scene_from_different_campaign_access_denied(self):
        """Test that users cannot access scenes from campaigns they're not in."""
        # Create another campaign with a scene
        other_campaign = Campaign.objects.create(
            name="Other Campaign",
            slug="other-campaign",
            owner=self.owner,
            max_characters_per_player=0,  # Unlimited
        )
        other_scene = Scene.objects.create(
            name="Other Scene",
            campaign=other_campaign,
            created_by=self.owner,
        )

        # Player1 is not a member of other_campaign
        self.client.login(username="player1", password="testpass123")
        url = reverse("scenes:scene_detail", kwargs={"pk": other_scene.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_permission_caching_edge_cases(self):
        """Test that permission checks don't rely on stale cached data."""
        self.client.login(username="observer", password="testpass123")

        # Observer initially cannot create scenes
        url = reverse(
            "scenes:scene_create", kwargs={"campaign_slug": self.campaign.slug}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        # Promote observer to GM in the same session
        membership = CampaignMembership.objects.get(
            campaign=self.campaign, user=self.observer
        )
        membership.role = "GM"
        membership.save()

        # Should immediately have create permissions (no stale cache)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_superuser_permissions(self):
        """Test that superusers have full access to all scenes."""
        User.objects.create_superuser(
            username="admin", email="admin@test.com", password="adminpass123"
        )

        self.client.login(username="admin", password="adminpass123")

        # Should have access to scene detail
        url = reverse("scenes:scene_detail", kwargs={"pk": self.scene.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Should be able to create scenes
        url = reverse(
            "scenes:scene_create", kwargs={"campaign_slug": self.campaign.slug}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Should be able to change status
        url = reverse("scenes:change_status", kwargs={"pk": self.scene.pk})
        response = self.client.post(url, {"status": "CLOSED"})
        self.assertEqual(response.status_code, 302)

    def test_anonymous_user_permissions(self):
        """Test that anonymous users are properly redirected."""
        # Ensure user is logged out
        self.client.logout()

        endpoints = [
            reverse(
                "scenes:campaign_scenes", kwargs={"campaign_slug": self.campaign.slug}
            ),
            reverse("scenes:scene_detail", kwargs={"pk": self.scene.pk}),
            reverse(
                "scenes:scene_create", kwargs={"campaign_slug": self.campaign.slug}
            ),
        ]

        for url in endpoints:
            response = self.client.get(url)

            self.assertEqual(
                response.status_code,
                302,
                f"Anonymous user should be redirected for {url}",
            )

            self.assertTrue(
                response.url.startswith("/users/login/"),
                f"Should redirect to login for {url}",
            )

    def test_scene_permission_with_campaign_ownership_transfer(self):
        """Test scene permissions when campaign ownership changes."""
        self.client.login(username="owner", password="testpass123")

        # Owner initially can manage scenes
        url = reverse("scenes:scene_edit", kwargs={"pk": self.scene.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Transfer ownership to GM
        self.campaign.owner = self.gm
        self.campaign.save()

        # Original owner should lose management permissions
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)  # Now just a regular member

        # New owner (GM) should gain permissions
        self.client.login(username="gm", password="testpass123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_bulk_permission_operations(self):
        """Test permissions for bulk operations on scenes and participants."""
        # TODO: Implement bulk operations endpoints
        self.skipTest("Bulk operations not yet implemented")
        # Create multiple characters for testing
        characters = []
        for i in range(3):
            char = Character.objects.create(
                name=f"Bulk Test Character {i}",
                campaign=self.campaign,
                player_owner=self.player1,
                game_system="Test System",
            )
            characters.append(char)

        self.client.login(username="player1", password="testpass123")

        # Player should be able to bulk add their own characters
        url = reverse("scenes:bulk_add_participants", kwargs={"pk": self.scene.pk})
        character_ids = [char.pk for char in characters]

        response = self.client.post(url, {"characters": character_ids})
        # Should succeed for owned characters
        self.assertIn(response.status_code, [200, 302])

        # But not be able to add others' characters in bulk
        other_char = Character.objects.create(
            name="Other Player Character",
            campaign=self.campaign,
            player_owner=self.player2,
            game_system="Test System",
        )

        response = self.client.post(
            url, {"characters": [characters[0].pk, other_char.pk]}
        )
        # Should be denied due to mixed ownership
        self.assertEqual(response.status_code, 403)

    def test_scene_permission_method_security(self):
        """Test that HTTP method restrictions are enforced."""
        self.client.login(username="player1", password="testpass123")

        # Some endpoints should only accept specific HTTP methods
        read_only_urls = [
            reverse(
                "scenes:campaign_scenes", kwargs={"campaign_slug": self.campaign.slug}
            ),
            reverse("scenes:scene_detail", kwargs={"pk": self.scene.pk}),
        ]

        for url in read_only_urls:
            # POST should not be allowed for read-only endpoints
            response = self.client.post(url, {})
            self.assertIn(
                response.status_code, [405, 403]
            )  # Method not allowed or forbidden
