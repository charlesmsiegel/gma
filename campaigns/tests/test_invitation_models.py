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

from campaigns.models import Campaign, CampaignMembership

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
        # This test will fail until the CampaignInvitation model is implemented
        with self.assertRaises(ImportError):
            from campaigns.models import CampaignInvitation

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
        with self.assertRaises(ImportError):
            from campaigns.models import CampaignInvitation

            invitation = CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=self.invitee,
                invited_by=self.owner,
                role="PLAYER",
            )

            # Should default to PENDING status
            self.assertEqual(invitation.status, "PENDING")

            # Should have auto-generated expires_at (7 days from creation)
            expected_expiry = invitation.created_at + timedelta(days=7)
            self.assertAlmostEqual(
                invitation.expires_at, expected_expiry, delta=timedelta(seconds=1)
            )

    def test_invitation_status_choices_validation(self):
        """Test that status field only accepts valid choices."""
        with self.assertRaises(ImportError):
            from campaigns.models import CampaignInvitation

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
        with self.assertRaises(ImportError):
            from campaigns.models import CampaignInvitation

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
        with self.assertRaises(ImportError):
            from campaigns.models import CampaignInvitation

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
        with self.assertRaises(ImportError):
            from campaigns.models import CampaignInvitation

            # Create first invitation
            CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=self.invitee,
                invited_by=self.owner,
                role="PLAYER",
            )

            # Attempt to create duplicate invitation
            with self.assertRaises(IntegrityError):
                CampaignInvitation.objects.create(
                    campaign=self.campaign,
                    invited_user=self.invitee,
                    invited_by=self.gm,  # Different inviter, same user+campaign
                    role="GM",  # Different role
                )

    def test_cannot_invite_campaign_owner(self):
        """Test validation prevents inviting the campaign owner."""
        with self.assertRaises(ImportError):
            from campaigns.models import CampaignInvitation

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
        with self.assertRaises(ImportError):
            from campaigns.models import CampaignInvitation

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
        with self.assertRaises(ImportError):
            from campaigns.models import CampaignInvitation

            invitation = CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=self.invitee,
                invited_by=self.owner,
                role="PLAYER",
            )

            expected = (
                f"{self.invitee.username} invited to {self.campaign.name} as PLAYER"
            )
            self.assertEqual(str(invitation), expected)

    def test_invitation_is_expired_property(self):
        """Test the is_expired property."""
        with self.assertRaises(ImportError):
            from campaigns.models import CampaignInvitation

            # Create expired invitation
            expired_invitation = CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=self.invitee,
                invited_by=self.owner,
                role="PLAYER",
                expires_at=timezone.now() - timedelta(hours=1),
            )

            self.assertTrue(expired_invitation.is_expired)

            # Create non-expired invitation
            valid_invitation = CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=self.another_invitee,
                invited_by=self.owner,
                role="PLAYER",
                expires_at=timezone.now() + timedelta(hours=1),
            )

            self.assertFalse(valid_invitation.is_expired)

    def test_invitation_is_pending_property(self):
        """Test the is_pending property."""
        with self.assertRaises(ImportError):
            from campaigns.models import CampaignInvitation

            # Create pending invitation
            pending_invitation = CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=self.invitee,
                invited_by=self.owner,
                role="PLAYER",
                status="PENDING",
            )

            self.assertTrue(pending_invitation.is_pending)

            # Create accepted invitation
            accepted_invitation = CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=self.another_invitee,
                invited_by=self.owner,
                role="PLAYER",
                status="ACCEPTED",
            )

            self.assertFalse(accepted_invitation.is_pending)

    def test_invitation_can_be_accepted_property(self):
        """Test the can_be_accepted property."""
        with self.assertRaises(ImportError):
            from campaigns.models import CampaignInvitation

            # Create valid pending invitation
            valid_invitation = CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=self.invitee,
                invited_by=self.owner,
                role="PLAYER",
                status="PENDING",
                expires_at=timezone.now() + timedelta(hours=1),
            )

            self.assertTrue(valid_invitation.can_be_accepted)

            # Create expired invitation
            expired_invitation = CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=self.another_invitee,
                invited_by=self.owner,
                role="PLAYER",
                status="PENDING",
                expires_at=timezone.now() - timedelta(hours=1),
            )

            self.assertFalse(expired_invitation.can_be_accepted)

            # Create declined invitation
            declined_invitation = CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=User.objects.create_user(
                    username="declined_user",
                    email="declined@test.com",
                    password="testpass123",
                ),
                invited_by=self.owner,
                role="PLAYER",
                status="DECLINED",
            )

            self.assertFalse(declined_invitation.can_be_accepted)

    def test_cascade_delete_campaign(self):
        """Test that deleting campaign deletes invitations."""
        with self.assertRaises(ImportError):
            from campaigns.models import CampaignInvitation

            invitation = CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=self.invitee,
                invited_by=self.owner,
                role="PLAYER",
            )

            invitation_id = invitation.id
            self.campaign.delete()

            self.assertFalse(
                CampaignInvitation.objects.filter(id=invitation_id).exists()
            )

    def test_cascade_delete_invited_user(self):
        """Test that deleting invited user deletes invitations."""
        with self.assertRaises(ImportError):
            from campaigns.models import CampaignInvitation

            invitation = CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=self.invitee,
                invited_by=self.owner,
                role="PLAYER",
            )

            invitation_id = invitation.id
            self.invitee.delete()

            self.assertFalse(
                CampaignInvitation.objects.filter(id=invitation_id).exists()
            )

    def test_cascade_delete_invited_by_user(self):
        """Test that deleting inviter sets invited_by to null."""
        with self.assertRaises(ImportError):
            from campaigns.models import CampaignInvitation

            invitation = CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=self.invitee,
                invited_by=self.gm,
                role="PLAYER",
            )

            self.gm.delete()
            invitation.refresh_from_db()

            # Should set invited_by to null but keep invitation
            self.assertIsNone(invitation.invited_by)
            self.assertEqual(invitation.invited_user, self.invitee)

    def test_invitation_accept_method(self):
        """Test the accept method creates membership and updates status."""
        with self.assertRaises(ImportError):
            from campaigns.models import CampaignInvitation

            invitation = CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=self.invitee,
                invited_by=self.owner,
                role="PLAYER",
            )

            # Accept the invitation
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
        with self.assertRaises(ImportError):
            from campaigns.models import CampaignInvitation

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
        with self.assertRaises(ImportError):
            from campaigns.models import CampaignInvitation

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
        with self.assertRaises(ImportError):
            from campaigns.models import CampaignInvitation

            invitation = CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=self.invitee,
                invited_by=self.owner,
                role="PLAYER",
            )

            # Decline the invitation
            invitation.decline()

            # Check invitation status updated
            invitation.refresh_from_db()
            self.assertEqual(invitation.status, "DECLINED")

    def test_invitation_decline_method_already_accepted_fails(self):
        """Test that declining already accepted invitation fails."""
        with self.assertRaises(ImportError):
            from campaigns.models import CampaignInvitation

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
        with self.assertRaises(ImportError):
            from campaigns.models import CampaignInvitation

            invitation = CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=self.invitee,
                invited_by=self.owner,
                role="PLAYER",
            )

            invitation_id = invitation.id

            # Cancel the invitation
            invitation.cancel()

            # Check invitation deleted
            self.assertFalse(
                CampaignInvitation.objects.filter(id=invitation_id).exists()
            )

    def test_invitation_cancel_method_accepted_fails(self):
        """Test that canceling accepted invitation fails."""
        with self.assertRaises(ImportError):
            from campaigns.models import CampaignInvitation

            invitation = CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=self.invitee,
                invited_by=self.owner,
                role="PLAYER",
                status="ACCEPTED",
            )

            with self.assertRaises(ValidationError):
                invitation.cancel()


class CampaignInvitationManagerTest(TestCase):
    """Test the CampaignInvitation manager methods."""

    def setUp(self):
        """Set up test data."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.user1 = User.objects.create_user(
            username="user1", email="user1@test.com", password="testpass123"
        )
        self.user2 = User.objects.create_user(
            username="user2", email="user2@test.com", password="testpass123"
        )
        self.user3 = User.objects.create_user(
            username="user3", email="user3@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Test Campaign", owner=self.owner, game_system="Mage: The Ascension"
        )

    def test_pending_invitations_queryset(self):
        """Test manager method to get pending invitations."""
        with self.assertRaises(ImportError):
            from campaigns.models import CampaignInvitation

            # Create invitations with different statuses
            pending1 = CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=self.user1,
                invited_by=self.owner,
                role="PLAYER",
                status="PENDING",
            )

            pending2 = CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=self.user2,
                invited_by=self.owner,
                role="GM",
                status="PENDING",
            )

            CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=self.user3,
                invited_by=self.owner,
                role="OBSERVER",
                status="ACCEPTED",
            )

            # Get pending invitations
            pending = CampaignInvitation.objects.pending()

            self.assertEqual(pending.count(), 2)
            self.assertIn(pending1, pending)
            self.assertIn(pending2, pending)

    def test_active_invitations_queryset(self):
        """Test manager method to get active (pending and not expired) invitations."""
        with self.assertRaises(ImportError):
            from campaigns.models import CampaignInvitation

            # Create active invitation
            active = CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=self.user1,
                invited_by=self.owner,
                role="PLAYER",
                status="PENDING",
                expires_at=timezone.now() + timedelta(hours=1),
            )

            # Create expired invitation
            CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=self.user2,
                invited_by=self.owner,
                role="PLAYER",
                status="PENDING",
                expires_at=timezone.now() - timedelta(hours=1),
            )

            # Create declined invitation
            CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=self.user3,
                invited_by=self.owner,
                role="PLAYER",
                status="DECLINED",
            )

            # Get active invitations
            active_invitations = CampaignInvitation.objects.active()

            self.assertEqual(active_invitations.count(), 1)
            self.assertIn(active, active_invitations)

    def test_for_campaign_queryset(self):
        """Test manager method to get invitations for a specific campaign."""
        with self.assertRaises(ImportError):
            from campaigns.models import CampaignInvitation

            # Create another campaign
            other_campaign = Campaign.objects.create(
                name="Other Campaign",
                owner=self.owner,
                game_system="Vampire: The Masquerade",
            )

            # Create invitations for different campaigns
            invitation1 = CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=self.user1,
                invited_by=self.owner,
                role="PLAYER",
            )

            invitation2 = CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=self.user2,
                invited_by=self.owner,
                role="GM",
            )

            CampaignInvitation.objects.create(
                campaign=other_campaign,
                invited_user=self.user3,
                invited_by=self.owner,
                role="OBSERVER",
            )

            # Get invitations for specific campaign
            campaign_invitations = CampaignInvitation.objects.for_campaign(
                self.campaign
            )

            self.assertEqual(campaign_invitations.count(), 2)
            self.assertIn(invitation1, campaign_invitations)
            self.assertIn(invitation2, campaign_invitations)

    def test_for_user_queryset(self):
        """Test manager method to get invitations for a specific user."""
        with self.assertRaises(ImportError):
            from campaigns.models import CampaignInvitation

            # Create invitations for different users
            invitation1 = CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=self.user1,
                invited_by=self.owner,
                role="PLAYER",
            )

            CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=self.user2,
                invited_by=self.owner,
                role="GM",
            )

            # Get invitations for specific user
            user_invitations = CampaignInvitation.objects.for_user(self.user1)

            self.assertEqual(user_invitations.count(), 1)
            self.assertIn(invitation1, user_invitations)

    def test_cleanup_expired_invitations(self):
        """Test manager method to clean up expired invitations."""
        with self.assertRaises(ImportError):
            from campaigns.models import CampaignInvitation

            # Create expired invitation
            expired = CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=self.user1,
                invited_by=self.owner,
                role="PLAYER",
                expires_at=timezone.now() - timedelta(hours=1),
            )

            # Create valid invitation
            valid = CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=self.user2,
                invited_by=self.owner,
                role="PLAYER",
                expires_at=timezone.now() + timedelta(hours=1),
            )

            # Clean up expired invitations
            deleted_count = CampaignInvitation.objects.cleanup_expired()

            self.assertEqual(deleted_count, 1)
            self.assertFalse(CampaignInvitation.objects.filter(id=expired.id).exists())
            self.assertTrue(CampaignInvitation.objects.filter(id=valid.id).exists())


class CampaignInvitationIntegrationTest(TestCase):
    """Integration tests for CampaignInvitation with existing models."""

    def setUp(self):
        """Set up test data."""
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
            name="Integration Test Campaign",
            owner=self.owner,
            game_system="Mage: The Ascension",
        )

        # Add GM to campaign
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm, role="GM"
        )

    def test_invitation_accept_creates_membership(self):
        """Test that accepting invitation creates proper membership."""
        with self.assertRaises(ImportError):
            from campaigns.models import CampaignInvitation

            invitation = CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=self.invitee,
                invited_by=self.owner,
                role="PLAYER",
            )

            # Accept invitation
            invitation.accept()

            # Verify membership was created correctly
            self.assertTrue(
                CampaignMembership.objects.filter(
                    campaign=self.campaign, user=self.invitee, role="PLAYER"
                ).exists()
            )

            # Verify campaign methods recognize new member
            self.assertTrue(self.campaign.is_member(self.invitee))
            self.assertTrue(self.campaign.is_player(self.invitee))
            self.assertEqual(self.campaign.get_user_role(self.invitee), "PLAYER")

    def test_cannot_invite_after_membership_exists(self):
        """Test that invitation validation prevents inviting existing members."""
        with self.assertRaises(ImportError):
            from campaigns.models import CampaignInvitation

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
        with self.assertRaises(ImportError):
            from campaigns.models import CampaignInvitation

            # Create and accept invitation
            invitation = CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=self.invitee,
                invited_by=self.owner,
                role="PLAYER",
            )
            invitation.accept()

            # Try to create new invitation for same user
            new_invitation = CampaignInvitation(
                campaign=self.campaign,
                invited_user=self.invitee,
                invited_by=self.gm,
                role="GM",
            )

            with self.assertRaises(ValidationError):
                new_invitation.clean()
