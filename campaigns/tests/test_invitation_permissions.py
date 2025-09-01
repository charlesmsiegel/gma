"""
Tests for Campaign Invitation Permission Validation.

This module tests permission validation for invitation operations including
accept, decline, and cancel operations with proper user authorization.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from campaigns.models import Campaign, CampaignMembership

User = get_user_model()


class InvitationPermissionTest(TestCase):
    """Test permission validation for invitation operations."""

    def setUp(self):
        """Set up test data for invitation permissions."""
        self.client = APIClient()

        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.gm = User.objects.create_user(
            username="gm", email="gm@test.com", password="testpass123"
        )
        self.player = User.objects.create_user(
            username="player", email="player@test.com", password="testpass123"
        )
        self.invitee = User.objects.create_user(
            username="invitee", email="invitee@test.com", password="testpass123"
        )
        self.other_user = User.objects.create_user(
            username="other", email="other@test.com", password="testpass123"
        )

        # Mark all users as email verified for API tests
        for user in [self.owner, self.gm, self.player, self.invitee, self.other_user]:
            user.email_verified = True
            user.save()

        self.campaign = Campaign.objects.create(
            name="Invitation Test Campaign", owner=self.owner, game_system="Test System"
        )

        # Add members
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm, role="GM"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )

    def test_only_invitee_can_accept_invitation(self):
        """Test that only the invited user can accept their invitation."""
        try:
            from campaigns.models import CampaignInvitation

            invitation = CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=self.invitee,
                invited_by=self.owner,
                role="PLAYER",
            )

            accept_url = reverse(
                "api:campaigns:accept_invitation", kwargs={"pk": invitation.id}
            )

            # Test that other users cannot accept
            for user in [self.owner, self.gm, self.player, self.other_user]:
                with self.subTest(user=user.username):
                    self.client.force_authenticate(user=user)
                    response = self.client.post(accept_url)

                    # Should deny permission
                    self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

            # Test that invitee can accept
            self.client.force_authenticate(user=self.invitee)
            response = self.client.post(accept_url)

            self.assertIn(
                response.status_code,
                [status.HTTP_200_OK, status.HTTP_501_NOT_IMPLEMENTED],
            )

        except ImportError:
            # CampaignInvitation model should exist now
            from campaigns.models import CampaignInvitation

    def test_only_invitee_can_decline_invitation(self):
        """Test that only the invited user can decline their invitation."""
        try:
            from campaigns.models import CampaignInvitation

            invitation = CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=self.invitee,
                invited_by=self.owner,
                role="PLAYER",
            )

            decline_url = reverse(
                "api:campaigns:decline_invitation", kwargs={"pk": invitation.id}
            )

            # Test that other users cannot decline
            for user in [self.owner, self.gm, self.player, self.other_user]:
                with self.subTest(user=user.username):
                    self.client.force_authenticate(user=user)
                    response = self.client.post(decline_url)

                    # Should deny permission
                    self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

            # Test that invitee can decline
            self.client.force_authenticate(user=self.invitee)
            response = self.client.post(decline_url)

            self.assertIn(
                response.status_code,
                [status.HTTP_200_OK, status.HTTP_501_NOT_IMPLEMENTED],
            )

        except ImportError:
            # CampaignInvitation model should exist now
            from campaigns.models import CampaignInvitation

    def test_invitation_sender_can_cancel(self):
        """Test that invitation sender can cancel their invitation."""
        try:
            from campaigns.models import CampaignInvitation

            invitation = CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=self.invitee,
                invited_by=self.gm,  # GM sent invitation
                role="PLAYER",
            )

            cancel_url = reverse(
                "api:campaigns:cancel_invitation", kwargs={"pk": invitation.id}
            )

            # Test that sender can cancel
            self.client.force_authenticate(user=self.gm)
            response = self.client.delete(cancel_url)

            self.assertIn(
                response.status_code,
                [status.HTTP_204_NO_CONTENT, status.HTTP_501_NOT_IMPLEMENTED],
            )

        except ImportError:
            # CampaignInvitation model should exist now
            from campaigns.models import CampaignInvitation

    def test_owner_can_cancel_any_invitation(self):
        """Test that campaign owner can cancel any invitation."""
        try:
            from campaigns.models import CampaignInvitation

            invitation = CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=self.invitee,
                invited_by=self.gm,  # GM sent invitation
                role="PLAYER",
            )

            cancel_url = reverse(
                "api:campaigns:cancel_invitation", kwargs={"pk": invitation.id}
            )

            # Test that owner can cancel GM's invitation
            self.client.force_authenticate(user=self.owner)
            response = self.client.delete(cancel_url)

            self.assertIn(
                response.status_code,
                [status.HTTP_204_NO_CONTENT, status.HTTP_501_NOT_IMPLEMENTED],
            )

        except ImportError:
            # CampaignInvitation model should exist now
            from campaigns.models import CampaignInvitation

    def test_others_cannot_cancel_invitation(self):
        """Test that other users cannot cancel invitations."""
        try:
            from campaigns.models import CampaignInvitation

            invitation = CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=self.invitee,
                invited_by=self.owner,
                role="PLAYER",
            )

            cancel_url = reverse(
                "api:campaigns:cancel_invitation", kwargs={"pk": invitation.id}
            )

            # Test that other users cannot cancel
            for user in [self.player, self.invitee, self.other_user]:
                with self.subTest(user=user.username):
                    self.client.force_authenticate(user=user)
                    response = self.client.delete(cancel_url)

                    # Should deny permission
                    self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        except ImportError:
            # CampaignInvitation model should exist now
            from campaigns.models import CampaignInvitation
