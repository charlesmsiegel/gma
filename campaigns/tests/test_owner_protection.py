"""
Tests for Campaign Owner Protection.

This module tests the protection of campaign owner privileges, ensuring that
owner permissions are implicit and cannot be modified or removed by other users.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from campaigns.models import Campaign, CampaignMembership

User = get_user_model()


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
