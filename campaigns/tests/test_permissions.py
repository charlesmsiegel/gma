"""Test the campaign permissions system."""

from django.contrib.auth import get_user_model
from django.http import Http404
from django.test import RequestFactory, TestCase

from campaigns.models import Campaign, CampaignMembership
from campaigns.permissions import CampaignPermission, CampaignPermissionMixin

User = get_user_model()


class CampaignPermissionTest(TestCase):
    """Test CampaignPermission class."""

    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
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
        self.non_member = User.objects.create_user(
            username="nonmember", email="nonmember@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Test Campaign", owner=self.owner, game_system="Mage: The Ascension"
        )

        # Create memberships
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm, role="GM"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.observer, role="OBSERVER"
        )

    def test_permission_system_integration(self):
        """Test that simplified permission system works correctly."""
        # Test single role permission
        owner_perm = CampaignPermission("OWNER")
        gm_perm = CampaignPermission("GM")
        member_perm = CampaignPermission.any_member()

        # Test that they have the expected roles
        self.assertEqual(owner_perm.required_roles, ["OWNER"])
        self.assertEqual(gm_perm.required_roles, ["GM"])
        self.assertEqual(
            member_perm.required_roles, ["OWNER", "GM", "PLAYER", "OBSERVER"]
        )


class CampaignPermissionMixinTest(TestCase):
    """Test CampaignPermissionMixin."""

    def setUp(self):
        """Set up test data."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.gm = User.objects.create_user(
            username="gm", email="gm@test.com", password="testpass123"
        )
        self.non_member = User.objects.create_user(
            username="nonmember", email="nonmember@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Test Campaign", owner=self.owner, game_system="Mage: The Ascension"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm, role="GM"
        )

    def test_check_campaign_permission_owner(self):
        """Test check_campaign_permission for owner."""
        mixin = CampaignPermissionMixin()
        mixin.kwargs = {"campaign_id": self.campaign.id}

        # Owner should pass OWNER role check
        mixin.check_campaign_permission(self.owner, "OWNER")
        # Owner should pass multi-role check
        mixin.check_campaign_permission(self.owner, "OWNER", "GM")

    def test_check_campaign_permission_gm(self):
        """Test check_campaign_permission for GM."""
        mixin = CampaignPermissionMixin()
        mixin.kwargs = {"campaign_id": self.campaign.id}

        # GM should pass GM role check
        mixin.check_campaign_permission(self.gm, "GM")
        # GM should pass multi-role check that includes GM
        mixin.check_campaign_permission(self.gm, "OWNER", "GM")

        # GM should not pass owner-only check
        with self.assertRaises(Http404):
            mixin.check_campaign_permission(self.gm, "OWNER")

    def test_check_campaign_permission_invalid_role(self):
        """Test check_campaign_permission with non-existent roles."""
        mixin = CampaignPermissionMixin()
        mixin.kwargs = {"campaign_id": self.campaign.id}

        # Invalid/non-existent roles should result in Http404 (no permission)
        with self.assertRaises(Http404):
            mixin.check_campaign_permission(self.owner, "INVALID_ROLE")
