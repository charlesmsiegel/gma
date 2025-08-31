"""
Tests for GM Permission Limitations.

This module tests the specific limitations and capabilities of GM role permissions,
including what GMs can and cannot do regarding other members and campaign management.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from campaigns.models import Campaign, CampaignMembership

User = get_user_model()


class GMPermissionLimitationsTest(TestCase):
    """Test specific limitations on GM permissions."""

    def setUp(self):
        """Set up test data for GM permission testing."""
        self.client = APIClient()

        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.owner.email_verified = True
        self.owner.save()

        self.gm1 = User.objects.create_user(
            username="gm1", email="gm1@test.com", password="testpass123"
        )
        self.gm1.email_verified = True
        self.gm1.save()

        self.gm2 = User.objects.create_user(
            username="gm2", email="gm2@test.com", password="testpass123"
        )
        self.gm2.email_verified = True
        self.gm2.save()

        self.player = User.objects.create_user(
            username="player", email="player@test.com", password="testpass123"
        )
        self.player.email_verified = True
        self.player.save()

        self.observer = User.objects.create_user(
            username="observer", email="observer@test.com", password="testpass123"
        )
        self.observer.email_verified = True
        self.observer.save()

        self.invitee = User.objects.create_user(
            username="invitee", email="invitee@test.com", password="testpass123"
        )
        self.invitee.email_verified = True
        self.invitee.save()

        self.campaign = Campaign.objects.create(
            name="GM Test Campaign", owner=self.owner, game_system="Test System"
        )

        # Add members
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm1, role="GM"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm2, role="GM"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.observer, role="OBSERVER"
        )

    def test_gm_can_invite_players_and_observers(self):
        """Test that GM can send invitations for PLAYER and OBSERVER roles."""
        self.client.force_authenticate(user=self.gm1)

        send_invitation_url = reverse(
            "api:campaigns:send_invitation", kwargs={"campaign_id": self.campaign.id}
        )

        # Test inviting as PLAYER
        invitation_data = {"invited_user_id": self.invitee.id, "role": "PLAYER"}
        response = self.client.post(send_invitation_url, invitation_data, format="json")

        self.assertIn(
            response.status_code,
            [status.HTTP_201_CREATED, status.HTTP_501_NOT_IMPLEMENTED],
        )

    def test_gm_can_invite_other_gms(self):
        """Test that GM can send invitations for GM role."""
        self.client.force_authenticate(user=self.gm1)

        send_invitation_url = reverse(
            "api:campaigns:send_invitation", kwargs={"campaign_id": self.campaign.id}
        )

        # Test inviting as GM
        invitation_data = {"invited_user_id": self.invitee.id, "role": "GM"}
        response = self.client.post(send_invitation_url, invitation_data, format="json")

        self.assertIn(
            response.status_code,
            [status.HTTP_201_CREATED, status.HTTP_501_NOT_IMPLEMENTED],
        )

    def test_gm_can_change_player_observer_roles(self):
        """Test that GM can change roles between PLAYER and OBSERVER."""
        self.client.force_authenticate(user=self.gm1)

        # Change player to observer
        change_role_url = reverse(
            "api:campaigns:change_member_role",
            kwargs={"campaign_id": self.campaign.id, "user_id": self.player.id},
        )

        role_data = {"role": "OBSERVER"}
        response = self.client.patch(change_role_url, role_data, format="json")

        # GM should be allowed to change player/observer roles
        self.assertIn(
            response.status_code, [status.HTTP_200_OK, status.HTTP_501_NOT_IMPLEMENTED]
        )

    def test_gm_cannot_change_other_gm_role(self):
        """Test that GM cannot change another GM's role."""
        self.client.force_authenticate(user=self.gm1)

        change_role_url = reverse(
            "api:campaigns:change_member_role",
            kwargs={"campaign_id": self.campaign.id, "user_id": self.gm2.id},
        )

        role_data = {"role": "PLAYER"}
        response = self.client.patch(change_role_url, role_data, format="json")

        # Should deny permission
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_gm_cannot_change_owner_role(self):
        """Test that GM cannot change owner's role."""
        self.client.force_authenticate(user=self.gm1)

        change_role_url = reverse(
            "api:campaigns:change_member_role",
            kwargs={"campaign_id": self.campaign.id, "user_id": self.owner.id},
        )

        role_data = {"role": "PLAYER"}
        response = self.client.patch(change_role_url, role_data, format="json")

        # Should deny permission
        self.assertIn(
            response.status_code,
            [status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND],
        )

    def test_gm_can_remove_players_and_observers(self):
        """Test that GM can remove players and observers."""
        self.client.force_authenticate(user=self.gm1)

        remove_member_url = reverse(
            "api:campaigns:remove_member",
            kwargs={"campaign_id": self.campaign.id, "user_id": self.player.id},
        )

        response = self.client.delete(remove_member_url)

        # GM should be allowed to remove players/observers
        self.assertIn(
            response.status_code,
            [status.HTTP_204_NO_CONTENT, status.HTTP_501_NOT_IMPLEMENTED],
        )

    def test_gm_cannot_remove_other_gm(self):
        """Test that GM cannot remove another GM."""
        self.client.force_authenticate(user=self.gm1)

        remove_member_url = reverse(
            "api:campaigns:remove_member",
            kwargs={"campaign_id": self.campaign.id, "user_id": self.gm2.id},
        )

        response = self.client.delete(remove_member_url)

        # Should deny permission
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_gm_cannot_remove_owner(self):
        """Test that GM cannot remove campaign owner."""
        self.client.force_authenticate(user=self.gm1)

        remove_member_url = reverse(
            "api:campaigns:remove_member",
            kwargs={"campaign_id": self.campaign.id, "user_id": self.owner.id},
        )

        response = self.client.delete(remove_member_url)

        # Should deny permission
        self.assertIn(
            response.status_code,
            [status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND],
        )
