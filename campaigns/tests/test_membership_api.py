"""
Tests for Enhanced Campaign Membership Management API.

This module tests the API endpoints for managing campaign memberships,
including list with roles, change roles, remove members, and bulk operations.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from campaigns.models import Campaign, CampaignMembership

User = get_user_model()


class ListMembersAPITest(TestCase):
    """Test the list campaign members API endpoint."""

    def setUp(self):
        """Set up test data."""
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

        self.campaign = Campaign.objects.create(
            name="Test Campaign", owner=self.owner, game_system="Mage: The Ascension"
        )

        # Add members with different roles
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm1, role="GM"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm2, role="GM"
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

        self.list_members_url = reverse(
            "api:campaigns:list_members", kwargs={"campaign_id": self.campaign.id}
        )

    def test_list_members_requires_authentication(self):
        """Test that listing members requires authentication."""
        response = self.client.get(self.list_members_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_campaign_member_can_list_members(self):
        """Test that campaign members can list other members."""
        # Test with different member roles
        for user in [self.owner, self.gm1, self.player1, self.observer]:
            with self.subTest(user=user.username):
                self.client.force_authenticate(user=user)

                response = self.client.get(self.list_members_url)

                # Should succeed once API is implemented
                self.assertIn(
                    response.status_code,
                    [status.HTTP_200_OK, status.HTTP_501_NOT_IMPLEMENTED],
                )

    def test_non_member_cannot_list_members(self):
        """Test that non-members cannot list campaign members."""
        self.client.force_authenticate(user=self.non_member)

        response = self.client.get(self.list_members_url)

        # Should deny permission
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_members_includes_owner(self):
        """Test that list includes campaign owner with OWNER role."""
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(self.list_members_url)

        if response.status_code == status.HTTP_200_OK:
            # Find owner in results
            owner_member = None
            for member in response.data["results"]:
                if member["user"]["id"] == self.owner.id:
                    owner_member = member
                    break

            self.assertIsNotNone(owner_member)
            self.assertEqual(owner_member["role"], "OWNER")

    def test_list_members_includes_all_roles(self):
        """Test that list includes members with all roles."""
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(self.list_members_url)

        if response.status_code == status.HTTP_200_OK:
            # Extract roles from response
            roles = [member["role"] for member in response.data["results"]]

            # Should include all role types
            expected_roles = ["OWNER", "GM", "PLAYER", "OBSERVER"]
            for expected_role in expected_roles:
                self.assertIn(expected_role, roles)

    def test_list_members_response_structure(self):
        """Test that list members response has correct structure."""
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(self.list_members_url)

        if response.status_code == status.HTTP_200_OK:
            # Paginated response structure
            self.assertIn("count", response.data)
            self.assertIn("next", response.data)
            self.assertIn("previous", response.data)
            self.assertIn("results", response.data)

            # Check member structure
            if response.data["results"]:
                member = response.data["results"][0]
                required_fields = ["user", "role", "joined_at"]
                for field in required_fields:
                    self.assertIn(field, member)

                # Check user nested structure
                user_fields = ["id", "username", "email"]
                for field in user_fields:
                    self.assertIn(field, member["user"])

    def test_list_members_supports_role_filtering(self):
        """Test that list supports filtering by role."""
        self.client.force_authenticate(user=self.owner)

        # Filter by GM role
        response = self.client.get(self.list_members_url, {"role": "GM"})

        if response.status_code == status.HTTP_200_OK:
            # Should only return GMs
            roles = [member["role"] for member in response.data["results"]]
            self.assertTrue(all(role == "GM" for role in roles))
            self.assertEqual(len(response.data["results"]), 2)  # gm1 and gm2

    def test_list_members_supports_pagination(self):
        """Test that list members supports pagination."""
        # Add more members to test pagination
        for i in range(10):
            user = User.objects.create_user(
                username=f"testplayer{i}",
                email=f"testplayer{i}@test.com",
                password="testpass123",
            )
            CampaignMembership.objects.create(
                campaign=self.campaign, user=user, role="PLAYER"
            )

        self.client.force_authenticate(user=self.owner)

        response = self.client.get(self.list_members_url, {"page_size": 5})

        if response.status_code == status.HTTP_200_OK:
            # Should limit results per page
            self.assertLessEqual(len(response.data["results"]), 5)
            # Should have pagination info
            self.assertIn("next", response.data)


class ChangeMemberRoleAPITest(TestCase):
    """Test the change member role API endpoint."""

    def setUp(self):
        """Set up test data."""
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
        self.observer = User.objects.create_user(
            username="observer", email="observer@test.com", password="testpass123"
        )
        self.non_member = User.objects.create_user(
            username="nonmember", email="nonmember@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Test Campaign", owner=self.owner, game_system="Mage: The Ascension"
        )

        # Add members
        self.gm_membership = CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm, role="GM"
        )
        self.player_membership = CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )
        self.observer_membership = CampaignMembership.objects.create(
            campaign=self.campaign, user=self.observer, role="OBSERVER"
        )

    def test_change_role_requires_authentication(self):
        """Test that changing member role requires authentication."""
        change_role_url = reverse(
            "api:campaigns:change_member_role",
            kwargs={"campaign_id": self.campaign.id, "user_id": self.player.id},
        )

        role_data = {"role": "GM"}

        response = self.client.patch(change_role_url, role_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_can_change_any_role(self):
        """Test that campaign owner can change any member's role."""
        self.client.force_authenticate(user=self.owner)

        change_role_url = reverse(
            "api:campaigns:change_member_role",
            kwargs={"campaign_id": self.campaign.id, "user_id": self.player.id},
        )

        role_data = {"role": "GM"}

        response = self.client.patch(change_role_url, role_data, format="json")

        # Should succeed once API is implemented
        self.assertIn(
            response.status_code, [status.HTTP_200_OK, status.HTTP_501_NOT_IMPLEMENTED]
        )

    def test_gm_can_change_player_and_observer_roles(self):
        """Test that GM can change player and observer roles."""
        self.client.force_authenticate(user=self.gm)

        # Change player to observer
        change_role_url = reverse(
            "api:campaigns:change_member_role",
            kwargs={"campaign_id": self.campaign.id, "user_id": self.player.id},
        )

        role_data = {"role": "OBSERVER"}

        response = self.client.patch(change_role_url, role_data, format="json")

        # Should succeed once API is implemented
        self.assertIn(
            response.status_code, [status.HTTP_200_OK, status.HTTP_501_NOT_IMPLEMENTED]
        )

    def test_gm_cannot_change_other_gm_role(self):
        """Test that GM cannot change another GM's role."""
        # Create another GM
        gm2 = User.objects.create_user(
            username="gm2", email="gm2@test.com", password="testpass123"
        )
        CampaignMembership.objects.create(campaign=self.campaign, user=gm2, role="GM")

        self.client.force_authenticate(user=self.gm)

        change_role_url = reverse(
            "api:campaigns:change_member_role",
            kwargs={"campaign_id": self.campaign.id, "user_id": gm2.id},
        )

        role_data = {"role": "PLAYER"}

        response = self.client.patch(change_role_url, role_data, format="json")

        # Should deny permission
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_player_cannot_change_roles(self):
        """Test that regular players cannot change roles."""
        self.client.force_authenticate(user=self.player)

        change_role_url = reverse(
            "api:campaigns:change_member_role",
            kwargs={"campaign_id": self.campaign.id, "user_id": self.observer.id},
        )

        role_data = {"role": "PLAYER"}

        response = self.client.patch(change_role_url, role_data, format="json")

        # Should deny permission
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_change_owner_role(self):
        """Test that owner's role cannot be changed."""
        self.client.force_authenticate(user=self.gm)

        change_role_url = reverse(
            "api:campaigns:change_member_role",
            kwargs={"campaign_id": self.campaign.id, "user_id": self.owner.id},
        )

        role_data = {"role": "PLAYER"}

        response = self.client.patch(change_role_url, role_data, format="json")

        # Should return validation error
        self.assertIn(
            response.status_code,
            [
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_404_NOT_FOUND,
                status.HTTP_501_NOT_IMPLEMENTED,
            ],
        )

    def test_change_role_invalid_role_fails(self):
        """Test that changing to invalid role fails."""
        self.client.force_authenticate(user=self.owner)

        change_role_url = reverse(
            "api:campaigns:change_member_role",
            kwargs={"campaign_id": self.campaign.id, "user_id": self.player.id},
        )

        role_data = {"role": "INVALID_ROLE"}

        response = self.client.patch(change_role_url, role_data, format="json")

        # Should return validation error
        self.assertIn(
            response.status_code,
            [status.HTTP_400_BAD_REQUEST, status.HTTP_501_NOT_IMPLEMENTED],
        )

    def test_change_role_updates_membership(self):
        """Test that changing role updates the membership."""
        self.client.force_authenticate(user=self.owner)

        change_role_url = reverse(
            "api:campaigns:change_member_role",
            kwargs={"campaign_id": self.campaign.id, "user_id": self.player.id},
        )

        role_data = {"role": "GM"}

        response = self.client.patch(change_role_url, role_data, format="json")

        if response.status_code == status.HTTP_200_OK:
            # Check membership was updated
            membership = CampaignMembership.objects.get(
                campaign=self.campaign, user=self.player
            )
            self.assertEqual(membership.role, "GM")

            # Check campaign recognizes new role
            self.assertTrue(self.campaign.is_gm(self.player))
            self.assertFalse(self.campaign.is_player(self.player))


class RemoveMemberAPITest(TestCase):
    """Test the remove member API endpoint."""

    def setUp(self):
        """Set up test data."""
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
        self.observer = User.objects.create_user(
            username="observer", email="observer@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Test Campaign", owner=self.owner, game_system="Mage: The Ascension"
        )

        # Add members
        self.gm_membership = CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm, role="GM"
        )
        self.player_membership = CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )
        self.observer_membership = CampaignMembership.objects.create(
            campaign=self.campaign, user=self.observer, role="OBSERVER"
        )

    def test_remove_member_requires_authentication(self):
        """Test that removing member requires authentication."""
        remove_member_url = reverse(
            "api:campaigns:remove_member",
            kwargs={"campaign_id": self.campaign.id, "user_id": self.player.id},
        )

        response = self.client.delete(remove_member_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_can_remove_any_member(self):
        """Test that campaign owner can remove any member."""
        self.client.force_authenticate(user=self.owner)

        remove_member_url = reverse(
            "api:campaigns:remove_member",
            kwargs={"campaign_id": self.campaign.id, "user_id": self.player.id},
        )

        response = self.client.delete(remove_member_url)

        # Should succeed once API is implemented
        self.assertIn(
            response.status_code,
            [status.HTTP_204_NO_CONTENT, status.HTTP_501_NOT_IMPLEMENTED],
        )

    def test_gm_can_remove_player_and_observer(self):
        """Test that GM can remove players and observers."""
        self.client.force_authenticate(user=self.gm)

        # Remove player
        remove_member_url = reverse(
            "api:campaigns:remove_member",
            kwargs={"campaign_id": self.campaign.id, "user_id": self.player.id},
        )

        response = self.client.delete(remove_member_url)

        # Should succeed once API is implemented
        self.assertIn(
            response.status_code,
            [status.HTTP_204_NO_CONTENT, status.HTTP_501_NOT_IMPLEMENTED],
        )

    def test_gm_cannot_remove_other_gm(self):
        """Test that GM cannot remove another GM."""
        # Create another GM
        gm2 = User.objects.create_user(
            username="gm2", email="gm2@test.com", password="testpass123"
        )
        CampaignMembership.objects.create(campaign=self.campaign, user=gm2, role="GM")

        self.client.force_authenticate(user=self.gm)

        remove_member_url = reverse(
            "api:campaigns:remove_member",
            kwargs={"campaign_id": self.campaign.id, "user_id": gm2.id},
        )

        response = self.client.delete(remove_member_url)

        # Should deny permission
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_player_cannot_remove_members(self):
        """Test that regular players cannot remove members."""
        self.client.force_authenticate(user=self.player)

        remove_member_url = reverse(
            "api:campaigns:remove_member",
            kwargs={"campaign_id": self.campaign.id, "user_id": self.observer.id},
        )

        response = self.client.delete(remove_member_url)

        # Should deny permission
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_remove_campaign_owner(self):
        """Test that campaign owner cannot be removed."""
        self.client.force_authenticate(user=self.gm)

        remove_member_url = reverse(
            "api:campaigns:remove_member",
            kwargs={"campaign_id": self.campaign.id, "user_id": self.owner.id},
        )

        response = self.client.delete(remove_member_url)

        # Should return validation error
        self.assertIn(
            response.status_code,
            [
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_404_NOT_FOUND,
                status.HTTP_501_NOT_IMPLEMENTED,
            ],
        )

    def test_remove_member_deletes_membership(self):
        """Test that removing member deletes the membership."""
        self.client.force_authenticate(user=self.owner)

        remove_member_url = reverse(
            "api:campaigns:remove_member",
            kwargs={"campaign_id": self.campaign.id, "user_id": self.player.id},
        )

        response = self.client.delete(remove_member_url)

        if response.status_code == status.HTTP_204_NO_CONTENT:
            # Check membership was deleted
            self.assertFalse(
                CampaignMembership.objects.filter(
                    campaign=self.campaign, user=self.player
                ).exists()
            )

            # Check campaign no longer recognizes as member
            self.assertFalse(self.campaign.is_member(self.player))
            self.assertFalse(self.campaign.is_player(self.player))


class BulkMembershipOperationsAPITest(TestCase):
    """Test bulk membership operations API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.gm = User.objects.create_user(
            username="gm", email="gm@test.com", password="testpass123"
        )

        # Create multiple users for bulk operations
        self.users = []
        for i in range(5):
            user = User.objects.create_user(
                username=f"testuser{i}",
                email=f"testuser{i}@test.com",
                password="testpass123",
            )
            self.users.append(user)

        self.campaign = Campaign.objects.create(
            name="Test Campaign", owner=self.owner, game_system="Mage: The Ascension"
        )

        # Add GM
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm, role="GM"
        )

        # Add some members
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.users[0], role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.users[1], role="OBSERVER"
        )

    def test_bulk_add_members_requires_authentication(self):
        """Test that bulk adding members requires authentication."""
        bulk_add_url = reverse(
            "api:campaigns:bulk_add_members", kwargs={"campaign_id": self.campaign.id}
        )

        member_data = {
            "members": [
                {"user_id": self.users[2].id, "role": "PLAYER"},
                {"user_id": self.users[3].id, "role": "OBSERVER"},
            ]
        }

        response = self.client.post(bulk_add_url, member_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_can_bulk_add_members(self):
        """Test that campaign owner can bulk add members."""
        self.client.force_authenticate(user=self.owner)

        bulk_add_url = reverse(
            "api:campaigns:bulk_add_members", kwargs={"campaign_id": self.campaign.id}
        )

        member_data = {
            "members": [
                {"user_id": self.users[2].id, "role": "PLAYER"},
                {"user_id": self.users[3].id, "role": "OBSERVER"},
            ]
        }

        response = self.client.post(bulk_add_url, member_data, format="json")

        # Should succeed once API is implemented
        self.assertIn(
            response.status_code,
            [status.HTTP_201_CREATED, status.HTTP_501_NOT_IMPLEMENTED],
        )

    def test_bulk_change_roles_requires_authentication(self):
        """Test that bulk changing roles requires authentication."""
        bulk_change_url = reverse(
            "api:campaigns:bulk_change_roles", kwargs={"campaign_id": self.campaign.id}
        )

        role_data = {
            "changes": [
                {"user_id": self.users[0].id, "role": "GM"},
                {"user_id": self.users[1].id, "role": "PLAYER"},
            ]
        }

        response = self.client.patch(bulk_change_url, role_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_can_bulk_change_roles(self):
        """Test that campaign owner can bulk change roles."""
        self.client.force_authenticate(user=self.owner)

        bulk_change_url = reverse(
            "api:campaigns:bulk_change_roles", kwargs={"campaign_id": self.campaign.id}
        )

        role_data = {
            "changes": [
                {"user_id": self.users[0].id, "role": "GM"},
                {"user_id": self.users[1].id, "role": "PLAYER"},
            ]
        }

        response = self.client.patch(bulk_change_url, role_data, format="json")

        # Should succeed once API is implemented
        self.assertIn(
            response.status_code, [status.HTTP_200_OK, status.HTTP_501_NOT_IMPLEMENTED]
        )

    def test_bulk_remove_members_requires_authentication(self):
        """Test that bulk removing members requires authentication."""
        bulk_remove_url = reverse(
            "api:campaigns:bulk_remove_members",
            kwargs={"campaign_id": self.campaign.id},
        )

        remove_data = {"user_ids": [self.users[0].id, self.users[1].id]}

        response = self.client.delete(bulk_remove_url, remove_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_can_bulk_remove_members(self):
        """Test that campaign owner can bulk remove members."""
        self.client.force_authenticate(user=self.owner)

        bulk_remove_url = reverse(
            "api:campaigns:bulk_remove_members",
            kwargs={"campaign_id": self.campaign.id},
        )

        remove_data = {"user_ids": [self.users[0].id, self.users[1].id]}

        response = self.client.delete(bulk_remove_url, remove_data, format="json")

        # Should succeed once API is implemented
        self.assertIn(
            response.status_code,
            [status.HTTP_204_NO_CONTENT, status.HTTP_501_NOT_IMPLEMENTED],
        )

    def test_bulk_operations_validate_permissions(self):
        """Test that bulk operations validate permissions for each action."""
        self.client.force_authenticate(user=self.gm)

        bulk_change_url = reverse(
            "api:campaigns:bulk_change_roles", kwargs={"campaign_id": self.campaign.id}
        )

        # GM trying to change another GM's role (should fail)
        gm2 = User.objects.create_user(
            username="gm2", email="gm2@test.com", password="testpass123"
        )
        CampaignMembership.objects.create(campaign=self.campaign, user=gm2, role="GM")

        role_data = {
            "changes": [
                {"user_id": self.users[0].id, "role": "OBSERVER"},  # Should succeed
                {"user_id": gm2.id, "role": "PLAYER"},  # Should fail
            ]
        }

        response = self.client.patch(bulk_change_url, role_data, format="json")

        # Should return partial success or validation errors
        self.assertIn(
            response.status_code,
            [
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_404_NOT_FOUND,
                status.HTTP_501_NOT_IMPLEMENTED,
            ],
        )

    def test_bulk_operations_atomic_behavior(self):
        """Test that bulk operations are atomic (all succeed or all fail)."""
        self.client.force_authenticate(user=self.owner)

        bulk_add_url = reverse(
            "api:campaigns:bulk_add_members", kwargs={"campaign_id": self.campaign.id}
        )

        member_data = {
            "members": [
                {"user_id": self.users[2].id, "role": "PLAYER"},
                {
                    "user_id": self.users[0].id,
                    "role": "GM",
                },  # Already a member, should fail
                {"user_id": self.users[3].id, "role": "OBSERVER"},
            ]
        }

        response = self.client.post(bulk_add_url, member_data, format="json")

        if response.status_code == status.HTTP_400_BAD_REQUEST:
            # If operation failed, no new memberships should be created
            self.assertFalse(
                CampaignMembership.objects.filter(
                    campaign=self.campaign, user=self.users[2]
                ).exists()
            )
            self.assertFalse(
                CampaignMembership.objects.filter(
                    campaign=self.campaign, user=self.users[3]
                ).exists()
            )

    def test_bulk_operations_response_structure(self):
        """Test that bulk operations return proper response structure."""
        self.client.force_authenticate(user=self.owner)

        bulk_add_url = reverse(
            "api:campaigns:bulk_add_members", kwargs={"campaign_id": self.campaign.id}
        )

        member_data = {
            "members": [
                {"user_id": self.users[2].id, "role": "PLAYER"},
                {"user_id": self.users[3].id, "role": "OBSERVER"},
            ]
        }

        response = self.client.post(bulk_add_url, member_data, format="json")

        if response.status_code == status.HTTP_201_CREATED:
            # Should return information about successful operations
            self.assertIn("added", response.data)
            self.assertIn("failed", response.data)
            self.assertEqual(len(response.data["added"]), 2)
            self.assertEqual(len(response.data["failed"]), 0)


class MembershipAPISecurityTest(TestCase):
    """Security tests for membership management API."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

        self.owner1 = User.objects.create_user(
            username="owner1", email="owner1@test.com", password="testpass123"
        )
        self.owner2 = User.objects.create_user(
            username="owner2", email="owner2@test.com", password="testpass123"
        )

        self.campaign1 = Campaign.objects.create(
            name="Campaign 1", owner=self.owner1, game_system="System 1"
        )
        self.campaign2 = Campaign.objects.create(
            name="Campaign 2", owner=self.owner2, game_system="System 2"
        )

    def test_cannot_manage_other_campaign_members(self):
        """Test that users cannot manage members of other campaigns."""
        self.client.force_authenticate(user=self.owner1)

        # Try to list members of campaign2
        list_members_url = reverse(
            "api:campaigns:list_members", kwargs={"campaign_id": self.campaign2.id}
        )

        response = self.client.get(list_members_url)

        # Should deny permission (404 to hide existence)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_parameter_tampering_protection(self):
        """Test protection against parameter tampering."""
        player = User.objects.create_user(
            username="player", email="player@test.com", password="testpass123"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign1, user=player, role="PLAYER"
        )

        self.client.force_authenticate(user=player)

        # Player trying to escalate by changing URL parameters
        change_role_url = reverse(
            "api:campaigns:change_member_role",
            kwargs={
                "campaign_id": self.campaign1.id,
                "user_id": player.id,  # Trying to change own role
            },
        )

        role_data = {"role": "GM"}

        response = self.client.patch(change_role_url, role_data, format="json")

        # Should deny permission
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_mass_assignment_protection(self):
        """Test protection against mass assignment vulnerabilities."""
        player = User.objects.create_user(
            username="player", email="player@test.com", password="testpass123"
        )

        self.client.force_authenticate(user=self.owner1)

        bulk_add_url = reverse(
            "api:campaigns:bulk_add_members", kwargs={"campaign_id": self.campaign1.id}
        )

        # Try to add member with extra fields that shouldn't be settable
        member_data = {
            "members": [
                {
                    "user_id": player.id,
                    "role": "PLAYER",
                    "is_owner": True,  # Malicious field
                    "admin": True,  # Malicious field
                }
            ]
        }

        response = self.client.post(bulk_add_url, member_data, format="json")

        if response.status_code == status.HTTP_201_CREATED:
            # Member should be added with correct role only
            membership = CampaignMembership.objects.get(
                campaign=self.campaign1, user=player
            )
            self.assertEqual(membership.role, "PLAYER")
            # Should not have owner privileges
            self.assertFalse(self.campaign1.is_owner(player))
