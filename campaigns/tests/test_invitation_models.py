"""
Tests for CampaignInvitation model.

This module tests the CampaignInvitation model including validation,
constraints, business logic, and auto-expiry functionality.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from campaigns.models import Campaign, CampaignInvitation, CampaignMembership

User = get_user_model()


class CampaignInvitationModelTest(TestCase):
    """Test the CampaignInvitation model."""

    def setUp(self):
        """Set up test users and campaign."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.gm = User.objects.create_user(
            username="gm", email="gm@test.com", password="testpass123"
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
        self.another_invitee = User.objects.create_user(
            username="invitee2", email="invitee2@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Test Campaign", owner=self.owner, game_system="Mage: The Ascension"
        )

        # Add existing members
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm, role="GM"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )

    def test_create_campaign_invitation_with_all_fields(self):
        """Test creating a campaign invitation with all fields."""
        expires_at = timezone.now() + timedelta(days=7)
        invitation = CampaignInvitation.objects.create(
            campaign=self.campaign,
            invited_user=self.invitee,
            invited_by=self.owner,
            role="PLAYER",
            status="PENDING",
            expires_at=expires_at,
        )

        self.assertEqual(invitation.campaign, self.campaign)
        self.assertEqual(invitation.invited_user, self.invitee)
        self.assertEqual(invitation.invited_by, self.owner)
        self.assertEqual(invitation.role, "PLAYER")
        self.assertEqual(invitation.status, "PENDING")
        self.assertEqual(invitation.expires_at, expires_at)
        self.assertIsNotNone(invitation.created_at)

    def test_create_campaign_invitation_default_values(self):
        """Test that invitation has correct default values."""
        invitation = CampaignInvitation.objects.create(
            campaign=self.campaign,
            invited_user=self.invitee,
            invited_by=self.owner,
            role="PLAYER",
        )

        self.assertEqual(invitation.status, "PENDING")
        # Should have auto-generated expires_at (7 days from creation)
        expected_expiry = invitation.created_at + timedelta(days=7)
        self.assertAlmostEqual(
            invitation.expires_at, expected_expiry, delta=timedelta(seconds=1)
        )

    def test_invitation_status_choices_validation(self):
        """Test that status field only accepts valid choices."""
        invitation = CampaignInvitation(
            campaign=self.campaign,
            invited_user=self.invitee,
            invited_by=self.owner,
            role="PLAYER",
            status="INVALID_STATUS",
        )

        with self.assertRaises(ValidationError):
            invitation.full_clean()

    def test_invitation_role_choices_validation(self):
        """Test that role field only accepts valid choices."""
        invitation = CampaignInvitation(
            campaign=self.campaign,
            invited_user=self.invitee,
            invited_by=self.owner,
            role="INVALID_ROLE",
        )

        with self.assertRaises(ValidationError):
            invitation.full_clean()

    def test_invitation_valid_roles(self):
        """Test that all valid roles can be used in invitations."""
        valid_roles = ["GM", "PLAYER", "OBSERVER"]
        for role in valid_roles:
            invitation = CampaignInvitation(
                campaign=self.campaign,
                invited_user=self.another_invitee,
                invited_by=self.owner,
                role=role,
            )
            # Should not raise ValidationError
            invitation.full_clean()

    def test_unique_constraint_campaign_invited_user(self):
        """Test that unique constraint prevents duplicate invitations."""
        # Create first invitation
        CampaignInvitation.objects.create(
            campaign=self.campaign,
            invited_user=self.invitee,
            invited_by=self.owner,
            role="PLAYER",
        )

        # Try to create duplicate
        with self.assertRaises(IntegrityError):
            CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=self.invitee,
                invited_by=self.gm,  # Different inviter, same user+campaign
                role="GM",  # Different role
            )

    def test_cannot_invite_campaign_owner(self):
        """Test validation prevents inviting the campaign owner."""
        invitation = CampaignInvitation(
            campaign=self.campaign,
            invited_user=self.owner,  # Cannot invite owner
            invited_by=self.gm,
            role="PLAYER",
        )

        with self.assertRaises(ValidationError):
            invitation.clean()

    def test_cannot_invite_existing_member(self):
        """Test validation prevents inviting existing members."""
        invitation = CampaignInvitation(
            campaign=self.campaign,
            invited_user=self.player,  # Already a member
            invited_by=self.owner,
            role="GM",
        )

        with self.assertRaises(ValidationError):
            invitation.clean()

    def test_invitation_str_representation(self):
        """Test the string representation of an invitation."""
        invitation = CampaignInvitation.objects.create(
            campaign=self.campaign,
            invited_user=self.invitee,
            invited_by=self.owner,
            role="PLAYER",
        )

        expected = f"{self.invitee.username} invited to {self.campaign.name} as PLAYER"
        self.assertEqual(str(invitation), expected)

    def test_invitation_is_expired_property(self):
        """Test the is_expired property."""
        # Create expired invitation
        expired_invitation = CampaignInvitation.objects.create(
            campaign=self.campaign,
            invited_user=self.invitee,
            invited_by=self.owner,
            role="PLAYER",
            expires_at=timezone.now() - timedelta(hours=1),
        )

        self.assertTrue(expired_invitation.is_expired)

        # Create valid invitation
        valid_invitation = CampaignInvitation.objects.create(
            campaign=self.campaign,
            invited_user=self.another_invitee,
            invited_by=self.owner,
            role="PLAYER",
            expires_at=timezone.now() + timedelta(hours=1),
        )

        self.assertFalse(valid_invitation.is_expired)

    def test_invitation_accept_method(self):
        """Test the accept method creates membership and updates status."""
        invitation = CampaignInvitation.objects.create(
            campaign=self.campaign,
            invited_user=self.invitee,
            invited_by=self.owner,
            role="PLAYER",
        )

        # Accept invitation
        membership = invitation.accept()

        # Check invitation status updated
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, "ACCEPTED")

        # Check membership created
        self.assertIsNotNone(membership)
        self.assertEqual(membership.campaign, self.campaign)
        self.assertEqual(membership.user, self.invitee)
        self.assertEqual(membership.role, "PLAYER")

    def test_invitation_accept_method_expired_fails(self):
        """Test that accepting expired invitation fails."""
        invitation = CampaignInvitation.objects.create(
            campaign=self.campaign,
            invited_user=self.invitee,
            invited_by=self.owner,
            role="PLAYER",
            expires_at=timezone.now() - timedelta(hours=1),
        )

        with self.assertRaises(ValidationError):
            invitation.accept()

    def test_invitation_accept_method_already_accepted_fails(self):
        """Test that accepting already accepted invitation fails."""
        invitation = CampaignInvitation.objects.create(
            campaign=self.campaign,
            invited_user=self.invitee,
            invited_by=self.owner,
            role="PLAYER",
            status="ACCEPTED",
        )

        with self.assertRaises(ValidationError):
            invitation.accept()

    def test_invitation_decline_method(self):
        """Test the decline method updates status."""
        invitation = CampaignInvitation.objects.create(
            campaign=self.campaign,
            invited_user=self.invitee,
            invited_by=self.owner,
            role="PLAYER",
        )

        invitation.decline()

        # Check invitation status updated
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, "DECLINED")

    def test_invitation_decline_method_already_accepted_fails(self):
        """Test that declining already accepted invitation fails."""
        invitation = CampaignInvitation.objects.create(
            campaign=self.campaign,
            invited_user=self.invitee,
            invited_by=self.owner,
            role="PLAYER",
            status="ACCEPTED",
        )

        with self.assertRaises(ValidationError):
            invitation.decline()

    def test_invitation_cancel_method(self):
        """Test the cancel method deletes invitation."""
        invitation = CampaignInvitation.objects.create(
            campaign=self.campaign,
            invited_user=self.invitee,
            invited_by=self.owner,
            role="PLAYER",
        )

        invitation_id = invitation.id
        invitation.cancel()

        # Check invitation deleted
        self.assertFalse(CampaignInvitation.objects.filter(id=invitation_id).exists())

    def test_invitation_cancel_method_accepted_fails(self):
        """Test that canceling accepted invitation fails."""
        invitation = CampaignInvitation.objects.create(
            campaign=self.campaign,
            invited_user=self.invitee,
            invited_by=self.owner,
            role="PLAYER",
            status="ACCEPTED",
        )

        with self.assertRaises(ValidationError):
            invitation.cancel()

    def test_cascade_delete_campaign(self):
        """Test that deleting campaign deletes invitations."""
        invitation = CampaignInvitation.objects.create(
            campaign=self.campaign,
            invited_user=self.invitee,
            invited_by=self.owner,
            role="PLAYER",
        )

        invitation_id = invitation.id
        self.campaign.delete()

        self.assertFalse(CampaignInvitation.objects.filter(id=invitation_id).exists())

    def test_cascade_delete_invited_user(self):
        """Test that deleting invited user deletes invitations."""
        invitation = CampaignInvitation.objects.create(
            campaign=self.campaign,
            invited_user=self.invitee,
            invited_by=self.owner,
            role="PLAYER",
        )

        invitation_id = invitation.id
        self.invitee.delete()

        self.assertFalse(CampaignInvitation.objects.filter(id=invitation_id).exists())

    def test_cleanup_expired_method(self):
        """Test the cleanup_expired class method."""
        # Create expired and active invitations
        CampaignInvitation.objects.create(
            campaign=self.campaign,
            invited_user=self.invitee,
            invited_by=self.owner,
            role="PLAYER",
            expires_at=timezone.now() - timedelta(hours=1),
        )

        active = CampaignInvitation.objects.create(
            campaign=self.campaign,
            invited_user=self.another_invitee,
            invited_by=self.owner,
            role="PLAYER",
            expires_at=timezone.now() + timedelta(hours=1),
        )

        # Run cleanup
        expired_count = CampaignInvitation.cleanup_expired()

        self.assertEqual(expired_count, 1)

        # Check that active invitation is still pending
        active.refresh_from_db()
        self.assertEqual(active.status, "PENDING")


class CampaignInvitationIntegrationTest(TestCase):
    """Integration tests for CampaignInvitation with other models."""

    def setUp(self):
        """Set up test users and campaign."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.gm = User.objects.create_user(
            username="gm", email="gm@test.com", password="testpass123"
        )
        self.invitee = User.objects.create_user(
            username="invitee", email="invitee@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Test Campaign", owner=self.owner, game_system="Mage: The Ascension"
        )

        # Add GM to campaign
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm, role="GM"
        )

    def test_invitation_accept_creates_membership(self):
        """Test that accepting invitation creates proper membership."""
        invitation = CampaignInvitation.objects.create(
            campaign=self.campaign,
            invited_user=self.invitee,
            invited_by=self.owner,
            role="PLAYER",
        )

        invitation.accept()

        # Verify membership exists
        self.assertTrue(
            CampaignMembership.objects.filter(
                campaign=self.campaign, user=self.invitee
            ).exists()
        )

        # Verify campaign methods recognize new member
        self.assertTrue(self.campaign.is_member(self.invitee))
        self.assertTrue(self.campaign.is_player(self.invitee))
        self.assertEqual(self.campaign.get_user_role(self.invitee), "PLAYER")

    def test_cannot_invite_after_membership_exists(self):
        """Test that invitation validation prevents inviting existing members."""
        # Create membership first
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.invitee, role="OBSERVER"
        )

        # Try to create invitation
        invitation = CampaignInvitation(
            campaign=self.campaign,
            invited_user=self.invitee,
            invited_by=self.owner,
            role="PLAYER",
        )

        with self.assertRaises(ValidationError):
            invitation.clean()

    def test_invitation_prevents_duplicate_after_acceptance(self):
        """Test that accepting invitation prevents future duplicate invitations."""
        # Create and accept invitation
        invitation = CampaignInvitation.objects.create(
            campaign=self.campaign,
            invited_user=self.invitee,
            invited_by=self.owner,
            role="PLAYER",
        )

        invitation.accept()

        # Try to create new invitation for same user
        duplicate_invitation = CampaignInvitation(
            campaign=self.campaign,
            invited_user=self.invitee,
            invited_by=self.gm,
            role="OBSERVER",
        )

        with self.assertRaises(ValidationError):
            duplicate_invitation.clean()
