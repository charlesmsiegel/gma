"""
Simplified behavior-focused tests for Campaign Membership system.

This test suite focuses on business logic and behavior rather than
implementation details, making it easier to maintain.
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from campaigns.models import Campaign, CampaignMembership

User = get_user_model()


class CampaignMembershipBehaviorTest(TestCase):
    """Test campaign membership business logic and behavior."""

    def setUp(self):
        """Set up test data."""
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
        self.campaign = Campaign.objects.create(
            name="Test Campaign", owner=self.owner, game_system="Test System"
        )

    def test_role_hierarchy_works(self):
        """Test that campaign role hierarchy functions correctly."""
        # Create memberships
        CampaignMembership.objects.create(
            user=self.gm, campaign=self.campaign, role="GM"
        )
        CampaignMembership.objects.create(
            user=self.player, campaign=self.campaign, role="PLAYER"
        )
        CampaignMembership.objects.create(
            user=self.observer, campaign=self.campaign, role="OBSERVER"
        )

        # Test role checking
        self.assertEqual(self.campaign.get_user_role(self.owner), "OWNER")
        self.assertEqual(self.campaign.get_user_role(self.gm), "GM")
        self.assertEqual(self.campaign.get_user_role(self.player), "PLAYER")
        self.assertEqual(self.campaign.get_user_role(self.observer), "OBSERVER")

    def test_has_role_method_works_with_multiple_roles(self):
        """Test that has_role method works with multiple role arguments."""
        CampaignMembership.objects.create(
            user=self.gm, campaign=self.campaign, role="GM"
        )

        # Test multiple role checking
        self.assertTrue(self.campaign.has_role(self.owner, "OWNER", "GM"))
        self.assertTrue(self.campaign.has_role(self.gm, "OWNER", "GM"))
        self.assertFalse(self.campaign.has_role(self.player, "OWNER", "GM"))

    def test_backward_compatibility_methods_work(self):
        """Test that is_owner, is_gm, etc. methods still work."""
        CampaignMembership.objects.create(
            user=self.gm, campaign=self.campaign, role="GM"
        )

        self.assertTrue(self.campaign.is_owner(self.owner))
        self.assertTrue(self.campaign.is_gm(self.gm))
        self.assertFalse(self.campaign.is_gm(self.player))

    def test_unique_user_per_campaign_constraint(self):
        """Test that users can only have one membership per campaign."""
        CampaignMembership.objects.create(
            user=self.player, campaign=self.campaign, role="PLAYER"
        )

        # Attempt to create duplicate should fail
        with self.assertRaises(IntegrityError):
            CampaignMembership.objects.create(
                user=self.player, campaign=self.campaign, role="GM"
            )

    def test_valid_roles_work(self):
        """Test that all valid roles can be created."""
        valid_roles = ["GM", "PLAYER", "OBSERVER"]
        users = [self.gm, self.player, self.observer]

        for user, role in zip(users, valid_roles):
            membership = CampaignMembership.objects.create(
                user=user, campaign=self.campaign, role=role
            )
            self.assertEqual(membership.role, role)

    def test_invalid_roles_fail_validation(self):
        """Test that invalid roles fail validation."""
        membership = CampaignMembership(
            user=self.player, campaign=self.campaign, role="INVALID"
        )

        with self.assertRaises(ValidationError):
            membership.full_clean()

    def test_owner_cannot_have_membership_role(self):
        """Test that campaign owner cannot have a membership role."""
        membership = CampaignMembership(
            user=self.owner, campaign=self.campaign, role="GM"
        )

        with self.assertRaises(ValidationError) as context:
            membership.clean()

        self.assertIn(
            "Campaign owner cannot have a membership role", str(context.exception)
        )

    def test_cascade_deletion_works(self):
        """Test that cascade deletion works correctly."""
        membership = CampaignMembership.objects.create(
            user=self.player, campaign=self.campaign, role="PLAYER"
        )
        membership_id = membership.id

        # Delete user - membership should be deleted
        self.player.delete()
        self.assertFalse(CampaignMembership.objects.filter(id=membership_id).exists())

    def test_membership_string_representation(self):
        """Test that membership string representation is correct."""
        membership = CampaignMembership.objects.create(
            user=self.player, campaign=self.campaign, role="PLAYER"
        )

        expected_str = f"{self.player.username} - {self.campaign.name} (PLAYER)"
        self.assertEqual(str(membership), expected_str)

    def test_performance_single_query_for_role_check(self):
        """Test that role checking uses efficient queries."""
        CampaignMembership.objects.create(
            user=self.gm, campaign=self.campaign, role="GM"
        )

        # This should be fast - owner check doesn't require DB query
        with self.assertNumQueries(0):
            self.assertTrue(self.campaign.is_owner(self.owner))

        # This should use only 1 query
        with self.assertNumQueries(1):
            self.assertTrue(self.campaign.is_gm(self.gm))


class CampaignPermissionIntegrationTest(TestCase):
    """Test campaign permissions integration."""

    def setUp(self):
        """Set up test data."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.gm = User.objects.create_user(
            username="gm", email="gm@test.com", password="testpass123"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign", owner=self.owner, game_system="Test System"
        )
        CampaignMembership.objects.create(
            user=self.gm, campaign=self.campaign, role="GM"
        )

    def test_permission_system_integration(self):
        """Test that simplified permission system works with campaign roles."""
        from campaigns.permissions import CampaignPermission

        # Test single role permission
        owner_permission = CampaignPermission("OWNER")
        self.assertTrue(owner_permission.required_roles == ["OWNER"])

        # Test multiple role permission
        admin_permission = CampaignPermission(["OWNER", "GM"])
        self.assertEqual(admin_permission.required_roles, ["OWNER", "GM"])

        # Test any member permission
        member_permission = CampaignPermission.any_member()
        expected_roles = ["OWNER", "GM", "PLAYER", "OBSERVER"]
        self.assertEqual(member_permission.required_roles, expected_roles)
