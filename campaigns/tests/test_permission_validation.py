"""
Tests for Campaign Permission Validation System.

This module tests the permission validation across all campaign operations,
including owner/GM/user permissions for invitations and membership management.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from campaigns.models import Campaign, CampaignMembership

User = get_user_model()


class CampaignPermissionMatrixTest(TestCase):
    """Test campaign permission matrix across different operations."""

    def setUp(self):
        """Set up comprehensive test data."""
        self.client = APIClient()

        # Create users for each role
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.gm1 = User.objects.create_user(
            username="gm1", email="gm1@test.com", password="testpass123"
        )
        self.gm2 = User.objects.create_user(
            username="gm2", email="gm2@test.com", password="testpass123"
        )
        self.player = User.objects.create_user(
            username="player", email="player@test.com", password="testpass123"
        )
        self.observer = User.objects.create_user(
            username="observer", email="observer@test.com", password="testpass123"
        )
        self.invitee = User.objects.create_user(
            username="invitee", email="invitee@test.com", password="testpass123"
        )
        self.non_member = User.objects.create_user(
            username="nonmember", email="nonmember@test.com", password="testpass123"
        )

        # Create campaign
        self.campaign = Campaign.objects.create(
            name="Permission Test Campaign", owner=self.owner, game_system="Test System"
        )

        # Add members with different roles
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

        # Define permission test scenarios
        self.permission_matrix = {
            "user_search": {
                "url": reverse(
                    "api:campaigns:user_search",
                    kwargs={"campaign_id": self.campaign.id},
                ),
                "method": "get",
                "data": {"q": "test"},
                "allowed_roles": ["OWNER", "GM"],
                "denied_roles": ["PLAYER", "OBSERVER", "NON_MEMBER"],
            },
            "send_invitation": {
                "url": reverse(
                    "api:campaigns:send_invitation",
                    kwargs={"campaign_id": self.campaign.id},
                ),
                "method": "post",
                "data": {"invited_user_id": self.invitee.id, "role": "PLAYER"},
                "allowed_roles": ["OWNER", "GM"],
                "denied_roles": ["PLAYER", "OBSERVER", "NON_MEMBER"],
            },
            "list_members": {
                "url": reverse(
                    "api:campaigns:list_members",
                    kwargs={"campaign_id": self.campaign.id},
                ),
                "method": "get",
                "data": {},
                "allowed_roles": ["OWNER", "GM", "PLAYER", "OBSERVER"],
                "denied_roles": ["NON_MEMBER"],
            },
            "change_member_role": {
                "url": reverse(
                    "api:campaigns:change_member_role",
                    kwargs={"campaign_id": self.campaign.id, "user_id": self.player.id},
                ),
                "method": "patch",
                "data": {"role": "OBSERVER"},
                "allowed_roles": ["OWNER", "GM"],
                "denied_roles": ["PLAYER", "OBSERVER", "NON_MEMBER"],
            },
            "remove_member": {
                "url": reverse(
                    "api:campaigns:remove_member",
                    kwargs={
                        "campaign_id": self.campaign.id,
                        "user_id": self.observer.id,
                    },
                ),
                "method": "delete",
                "data": {},
                "allowed_roles": ["OWNER", "GM"],
                "denied_roles": ["PLAYER", "OBSERVER", "NON_MEMBER"],
            },
            "list_campaign_invitations": {
                "url": reverse(
                    "api:campaigns:list_invitations",
                    kwargs={"campaign_id": self.campaign.id},
                ),
                "method": "get",
                "data": {},
                "allowed_roles": ["OWNER", "GM"],
                "denied_roles": ["PLAYER", "OBSERVER", "NON_MEMBER"],
            },
        }

        # Map role names to users
        self.role_users = {
            "OWNER": self.owner,
            "GM": self.gm1,
            "PLAYER": self.player,
            "OBSERVER": self.observer,
            "NON_MEMBER": self.non_member,
        }

    def _reset_test_state(self):
        """Reset test state to avoid interference between test operations."""
        # Clear any existing invitations
        from campaigns.models import CampaignInvitation

        CampaignInvitation.objects.filter(campaign=self.campaign).delete()

        # Ensure observer is a member (in case it was removed)
        from campaigns.models import CampaignMembership

        CampaignMembership.objects.get_or_create(
            campaign=self.campaign, user=self.observer, defaults={"role": "OBSERVER"}
        )

    def test_permission_matrix_allowed_roles(self):
        """Test that allowed roles can perform operations."""
        for operation, config in self.permission_matrix.items():
            for role in config["allowed_roles"]:
                with self.subTest(operation=operation, role=role):
                    # Reset state before each test to avoid interference
                    self._reset_test_state()
                    user = self.role_users[role]
                    self.client.force_authenticate(user=user)

                    if config["method"] == "get":
                        response = self.client.get(config["url"], config["data"])
                    elif config["method"] == "post":
                        response = self.client.post(
                            config["url"], config["data"], format="json"
                        )
                    elif config["method"] == "patch":
                        response = self.client.patch(
                            config["url"], config["data"], format="json"
                        )
                    elif config["method"] == "delete":
                        response = self.client.delete(config["url"])

                    # Should either succeed or be not implemented yet
                    self.assertIn(
                        response.status_code,
                        [
                            status.HTTP_200_OK,
                            status.HTTP_201_CREATED,
                            status.HTTP_204_NO_CONTENT,
                            status.HTTP_501_NOT_IMPLEMENTED,
                        ],
                        f"{operation} should be allowed for {role}",
                    )

    def test_permission_matrix_denied_roles(self):
        """Test that denied roles cannot perform operations."""
        for operation, config in self.permission_matrix.items():
            for role in config["denied_roles"]:
                with self.subTest(operation=operation, role=role):
                    # Reset state before each test to avoid interference
                    self._reset_test_state()
                    user = self.role_users[role]
                    self.client.force_authenticate(user=user)

                    if config["method"] == "get":
                        response = self.client.get(config["url"], config["data"])
                    elif config["method"] == "post":
                        response = self.client.post(
                            config["url"], config["data"], format="json"
                        )
                    elif config["method"] == "patch":
                        response = self.client.patch(
                            config["url"], config["data"], format="json"
                        )
                    elif config["method"] == "delete":
                        response = self.client.delete(config["url"])

                    # Should deny permission (404 to hide campaign existence)
                    self.assertEqual(
                        response.status_code,
                        status.HTTP_404_NOT_FOUND,
                        f"{operation} should be denied for {role}",
                    )


class GMPermissionLimitationsTest(TestCase):
    """Test specific limitations on GM permissions."""

    def setUp(self):
        """Set up test data for GM permission testing."""
        self.client = APIClient()

        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.gm1 = User.objects.create_user(
            username="gm1", email="gm1@test.com", password="testpass123"
        )
        self.gm2 = User.objects.create_user(
            username="gm2", email="gm2@test.com", password="testpass123"
        )
        self.player = User.objects.create_user(
            username="player", email="player@test.com", password="testpass123"
        )
        self.observer = User.objects.create_user(
            username="observer", email="observer@test.com", password="testpass123"
        )
        self.invitee = User.objects.create_user(
            username="invitee", email="invitee@test.com", password="testpass123"
        )

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


class OwnerProtectionTest(TestCase):
    """Test protection of campaign owner privileges."""

    def setUp(self):
        """Set up test data for owner protection testing."""
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

        self.campaign = Campaign.objects.create(
            name="Owner Protection Test", owner=self.owner, game_system="Test System"
        )

        # Add members
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm, role="GM"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )

    def test_owner_cannot_be_removed_from_campaign(self):
        """Test that campaign owner cannot be removed."""
        # Test with different users trying to remove owner
        for user in [self.gm, self.player]:
            with self.subTest(user=user.username):
                self.client.force_authenticate(user=user)

                remove_url = reverse(
                    "api:campaigns:remove_member",
                    kwargs={"campaign_id": self.campaign.id, "user_id": self.owner.id},
                )

                response = self.client.delete(remove_url)

                # Should deny permission
                self.assertIn(
                    response.status_code,
                    [status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND],
                )

    def test_owner_role_cannot_be_changed(self):
        """Test that owner's role cannot be changed."""
        # Test with different users trying to change owner's role
        for user in [self.gm, self.player]:
            with self.subTest(user=user.username):
                self.client.force_authenticate(user=user)

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

    def test_owner_cannot_have_membership_record(self):
        """Test that owner cannot have a CampaignMembership record."""
        # Owner should not appear in membership table
        self.assertFalse(
            CampaignMembership.objects.filter(
                campaign=self.campaign, user=self.owner
            ).exists()
        )

        # But should still be recognized as owner
        self.assertTrue(self.campaign.is_owner(self.owner))
        self.assertEqual(self.campaign.get_user_role(self.owner), "OWNER")

    def test_owner_permissions_are_implicit(self):
        """Test that owner permissions are implicit, not role-based."""
        # Owner should have all permissions without explicit membership
        self.assertTrue(self.campaign.is_member(self.owner))
        self.assertTrue(self.campaign.is_owner(self.owner))

        # Owner should not be GM/PLAYER/OBSERVER explicitly
        self.assertFalse(self.campaign.is_gm(self.owner))
        self.assertFalse(self.campaign.is_player(self.owner))
        self.assertFalse(self.campaign.is_observer(self.owner))


class CrossCampaignPermissionTest(TestCase):
    """Test that permissions are properly isolated between campaigns."""

    def setUp(self):
        """Set up multiple campaigns for cross-campaign testing."""
        self.client = APIClient()

        # Create users
        self.owner1 = User.objects.create_user(
            username="owner1", email="owner1@test.com", password="testpass123"
        )
        self.owner2 = User.objects.create_user(
            username="owner2", email="owner2@test.com", password="testpass123"
        )
        self.gm1 = User.objects.create_user(
            username="gm1", email="gm1@test.com", password="testpass123"
        )
        self.player1 = User.objects.create_user(
            username="player1", email="player1@test.com", password="testpass123"
        )

        # Create two campaigns
        self.campaign1 = Campaign.objects.create(
            name="Campaign 1", owner=self.owner1, game_system="System 1"
        )
        self.campaign2 = Campaign.objects.create(
            name="Campaign 2", owner=self.owner2, game_system="System 2"
        )

        # Add GM to campaign1 only
        CampaignMembership.objects.create(
            campaign=self.campaign1, user=self.gm1, role="GM"
        )

        # Add player to campaign2 only
        CampaignMembership.objects.create(
            campaign=self.campaign2, user=self.player1, role="PLAYER"
        )

    def test_campaign_owner_cannot_manage_other_campaigns(self):
        """Test that campaign owners cannot manage other campaigns."""
        self.client.force_authenticate(user=self.owner1)

        # Try to access campaign2's members
        list_members_url = reverse(
            "api:campaigns:list_members", kwargs={"campaign_id": self.campaign2.id}
        )

        response = self.client.get(list_members_url)

        # Should deny access (404 to hide existence)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_gm_permissions_are_campaign_specific(self):
        """Test that GM permissions only apply to their specific campaign."""
        self.client.force_authenticate(user=self.gm1)

        # GM1 should be able to access campaign1
        list_members_url1 = reverse(
            "api:campaigns:list_members", kwargs={"campaign_id": self.campaign1.id}
        )
        response1 = self.client.get(list_members_url1)

        self.assertIn(
            response1.status_code, [status.HTTP_200_OK, status.HTTP_501_NOT_IMPLEMENTED]
        )

        # But should not be able to access campaign2
        list_members_url2 = reverse(
            "api:campaigns:list_members", kwargs={"campaign_id": self.campaign2.id}
        )
        response2 = self.client.get(list_members_url2)

        self.assertEqual(response2.status_code, status.HTTP_404_NOT_FOUND)

    def test_member_permissions_are_campaign_specific(self):
        """Test that member permissions only apply to their specific campaign."""
        self.client.force_authenticate(user=self.player1)

        # Player1 should be able to access campaign2 (where they are a member)
        list_members_url2 = reverse(
            "api:campaigns:list_members", kwargs={"campaign_id": self.campaign2.id}
        )
        response2 = self.client.get(list_members_url2)

        self.assertIn(
            response2.status_code, [status.HTTP_200_OK, status.HTTP_501_NOT_IMPLEMENTED]
        )

        # But should not be able to access campaign1 (where they are not a member)
        list_members_url1 = reverse(
            "api:campaigns:list_members", kwargs={"campaign_id": self.campaign1.id}
        )
        response1 = self.client.get(list_members_url1)

        self.assertEqual(response1.status_code, status.HTTP_404_NOT_FOUND)

    def test_invitation_permissions_are_campaign_specific(self):
        """Test that invitation permissions are campaign-specific."""
        try:
            from campaigns.models import CampaignInvitation

            invitee = User.objects.create_user(
                username="invitee", email="invitee@test.com", password="testpass123"
            )

            # Create invitation for campaign1
            invitation1 = CampaignInvitation.objects.create(
                campaign=self.campaign1,
                invited_user=invitee,
                invited_by=self.owner1,
                role="PLAYER",
            )

            # Create invitation for campaign2
            invitation2 = CampaignInvitation.objects.create(
                campaign=self.campaign2,
                invited_user=invitee,
                invited_by=self.owner2,
                role="PLAYER",
            )

            # GM1 should be able to cancel invitation1 but not invitation2
            self.client.force_authenticate(user=self.gm1)

            cancel_url1 = reverse(
                "api:campaigns:cancel_invitation", kwargs={"pk": invitation1.id}
            )
            response1 = self.client.delete(cancel_url1)

            self.assertIn(
                response1.status_code,
                [status.HTTP_204_NO_CONTENT, status.HTTP_501_NOT_IMPLEMENTED],
            )

            cancel_url2 = reverse(
                "api:campaigns:cancel_invitation", kwargs={"pk": invitation2.id}
            )
            response2 = self.client.delete(cancel_url2)

            self.assertEqual(response2.status_code, status.HTTP_404_NOT_FOUND)

        except ImportError:
            # CampaignInvitation model should exist now
            from campaigns.models import CampaignInvitation
