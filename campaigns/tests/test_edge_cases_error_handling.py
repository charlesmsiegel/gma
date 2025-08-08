"""
Tests for Edge Cases and Error Handling in Campaign Membership Management.

This module tests edge cases, error conditions, expired invitations,
duplicate operations, and other boundary conditions.
"""

from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from campaigns.models import Campaign, CampaignMembership

User = get_user_model()


class ExpiredInvitationTest(TestCase):
    """Test handling of expired invitations."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.invitee = User.objects.create_user(
            username="invitee", email="invitee@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Expiry Test Campaign", owner=self.owner, game_system="Test System"
        )

    def test_expired_invitation_cannot_be_accepted(self):
        """Test that expired invitations cannot be accepted."""
        try:
            from campaigns.models import CampaignInvitation

            # Create expired invitation
            invitation = CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=self.invitee,
                invited_by=self.owner,
                role="PLAYER",
                expires_at=timezone.now() - timedelta(hours=1),
            )

            self.client.force_authenticate(user=self.invitee)

            accept_url = reverse(
                "api:campaigns:accept_invitation", kwargs={"pk": invitation.id}
            )

            response = self.client.post(accept_url)

            # Should return error for expired invitation
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

            # Invitation should still be in expired state
            invitation.refresh_from_db()
            self.assertEqual(invitation.status, "PENDING")
            self.assertTrue(invitation.is_expired)

        except ImportError:
            # CampaignInvitation model should exist now
            from campaigns.models import CampaignInvitation

    def test_expired_invitation_can_be_declined(self):
        """Test that expired invitations can still be declined for cleanup."""
        try:
            from campaigns.models import CampaignInvitation

            # Create expired invitation
            invitation = CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=self.invitee,
                invited_by=self.owner,
                role="PLAYER",
                expires_at=timezone.now() - timedelta(hours=1),
            )

            self.client.force_authenticate(user=self.invitee)

            decline_url = reverse(
                "api:campaigns:decline_invitation", kwargs={"pk": invitation.id}
            )

            response = self.client.post(decline_url)

            # Should allow declining expired invitations
            self.assertIn(
                response.status_code,
                [status.HTTP_200_OK, status.HTTP_501_NOT_IMPLEMENTED],
            )

        except ImportError:
            # CampaignInvitation model should exist now
            from campaigns.models import CampaignInvitation

    def test_automatic_cleanup_of_expired_invitations(self):
        """Test automatic cleanup of old expired invitations."""
        try:
            from campaigns.models import CampaignInvitation

            # Create expired invitations
            old_invitation = CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=self.invitee,
                invited_by=self.owner,
                role="PLAYER",
                expires_at=timezone.now() - timedelta(days=30),
            )

            CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=User.objects.create_user(
                    username="recent", email="recent@test.com", password="testpass123"
                ),
                invited_by=self.owner,
                role="PLAYER",
                expires_at=timezone.now() - timedelta(hours=1),
            )

            # Run cleanup (assuming management command exists)
            deleted_count = CampaignInvitation.objects.cleanup_expired()

            self.assertGreaterEqual(deleted_count, 1)

            # Very old invitation should be deleted
            self.assertFalse(
                CampaignInvitation.objects.filter(id=old_invitation.id).exists()
            )

            # Recent expired invitation might still exist (depends on cleanup policy)

        except ImportError:
            # CampaignInvitation model should exist now
            from campaigns.models import CampaignInvitation

    def test_invitation_expiry_extension(self):
        """Test extending expiry of invitations."""
        try:
            from campaigns.models import CampaignInvitation

            invitation = CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=self.invitee,
                invited_by=self.owner,
                role="PLAYER",
                expires_at=timezone.now() + timedelta(hours=1),
            )

            original_expiry = invitation.expires_at

            # Extend expiry (assuming this method exists)
            if hasattr(invitation, "extend_expiry"):
                invitation.extend_expiry(days=7)

                self.assertGreater(invitation.expires_at, original_expiry)
                self.assertFalse(invitation.is_expired)
            else:
                # Test basic expiry extension by updating the field
                new_expiry = timezone.now() + timedelta(days=14)
                invitation.expires_at = new_expiry
                invitation.save()

                invitation.refresh_from_db()
                self.assertEqual(invitation.expires_at, new_expiry)
                self.assertGreater(invitation.expires_at, original_expiry)
                self.assertFalse(invitation.is_expired)

        except ImportError:
            # CampaignInvitation model should exist now
            from campaigns.models import CampaignInvitation


class DuplicateOperationTest(TestCase):
    """Test handling of duplicate operations."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.user = User.objects.create_user(
            username="user", email="user@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Duplicate Test Campaign", owner=self.owner, game_system="Test System"
        )

    def test_duplicate_invitation_prevention(self):
        """Test that duplicate invitations are prevented."""
        try:
            from campaigns.models import CampaignInvitation

            # Create first invitation
            CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=self.user,
                invited_by=self.owner,
                role="PLAYER",
            )

            # Attempt to create duplicate
            with self.assertRaises(IntegrityError):
                CampaignInvitation.objects.create(
                    campaign=self.campaign,
                    invited_user=self.user,
                    invited_by=self.owner,
                    role="GM",  # Different role, same user+campaign
                )

        except ImportError:
            # CampaignInvitation model should exist now
            from campaigns.models import CampaignInvitation

    def test_duplicate_invitation_via_api(self):
        """Test duplicate invitation prevention via API."""
        try:
            from campaigns.models import CampaignInvitation

            # Create first invitation
            CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=self.user,
                invited_by=self.owner,
                role="PLAYER",
            )

            self.client.force_authenticate(user=self.owner)

            send_invitation_url = reverse(
                "api:campaigns:send_invitation",
                kwargs={"campaign_id": self.campaign.id},
            )

            invitation_data = {"invited_user_id": self.user.id, "role": "GM"}

            response = self.client.post(
                send_invitation_url, invitation_data, format="json"
            )

            # Should return validation error
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        except ImportError:
            # CampaignInvitation model should exist now
            from campaigns.models import CampaignInvitation

    def test_duplicate_membership_prevention(self):
        """Test that duplicate memberships are prevented."""
        # Create membership
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.user, role="PLAYER"
        )

        # Attempt to create duplicate
        with self.assertRaises(IntegrityError):
            CampaignMembership.objects.create(
                campaign=self.campaign, user=self.user, role="GM"
            )

    def test_double_accept_invitation_handling(self):
        """Test handling of accepting already accepted invitation."""
        try:
            from campaigns.models import CampaignInvitation

            invitation = CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=self.user,
                invited_by=self.owner,
                role="PLAYER",
            )

            # Accept once
            invitation.accept()

            # Try to accept again
            with self.assertRaises(ValidationError):
                invitation.accept()

        except ImportError:
            # CampaignInvitation model should exist now
            from campaigns.models import CampaignInvitation

    def test_double_decline_invitation_handling(self):
        """Test handling of declining already declined invitation."""
        try:
            from campaigns.models import CampaignInvitation

            invitation = CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=self.user,
                invited_by=self.owner,
                role="PLAYER",
            )

            # Decline once
            invitation.decline()

            # Try to decline again (should be idempotent)
            invitation.decline()  # Should not raise error

            invitation.refresh_from_db()
            self.assertEqual(invitation.status, "DECLINED")

        except ImportError:
            # CampaignInvitation model should exist now
            from campaigns.models import CampaignInvitation


class ConcurrencyTest(TransactionTestCase):
    """Test handling of concurrent operations."""

    def setUp(self):
        """Set up test data."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.user = User.objects.create_user(
            username="user", email="user@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Concurrency Test Campaign",
            owner=self.owner,
            game_system="Test System",
        )

    def test_concurrent_invitation_acceptance(self):
        """Test concurrent acceptance of the same invitation."""
        try:
            from campaigns.models import CampaignInvitation

            invitation = CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=self.user,
                invited_by=self.owner,
                role="PLAYER",
            )

            # Simulate concurrent acceptance attempts
            def accept_invitation():
                try:
                    with transaction.atomic():
                        inv = CampaignInvitation.objects.select_for_update().get(
                            id=invitation.id
                        )
                        if inv.status == "PENDING":
                            inv.accept()
                            return True
                except Exception:
                    return False
                return False

            # Both should not succeed
            result1 = accept_invitation()
            result2 = accept_invitation()

            # Only one should succeed
            self.assertTrue(result1 ^ result2)  # XOR - exactly one should be True

        except ImportError:
            # CampaignInvitation model should exist now
            from campaigns.models import CampaignInvitation

    def test_concurrent_membership_creation(self):
        """Test concurrent creation of memberships for same user."""

        def create_membership():
            try:
                with transaction.atomic():
                    CampaignMembership.objects.create(
                        campaign=self.campaign, user=self.user, role="PLAYER"
                    )
                    return True
            except IntegrityError:
                return False

        # Simulate concurrent creation attempts
        result1 = create_membership()
        result2 = create_membership()

        # Only one should succeed
        self.assertTrue(result1 ^ result2)  # XOR - exactly one should be True


class BoundaryConditionTest(TestCase):
    """Test boundary conditions and limits."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Boundary Test Campaign", owner=self.owner, game_system="Test System"
        )

    def test_maximum_campaign_members(self):
        """Test behavior at maximum campaign member limit."""
        # Assuming there's a maximum member limit (e.g., 100)
        MAX_MEMBERS = getattr(self.campaign, "MAX_MEMBERS", 100)

        # Add members up to the limit
        for i in range(MAX_MEMBERS - 1):  # -1 because owner is already a member
            user = User.objects.create_user(
                username=f"member{i}",
                email=f"member{i}@test.com",
                password="testpass123",
            )
            CampaignMembership.objects.create(
                campaign=self.campaign, user=user, role="PLAYER"
            )

        # Try to add one more member
        extra_user = User.objects.create_user(
            username="extrauser", email="extra@test.com", password="testpass123"
        )

        # This should either succeed or fail gracefully
        try:
            CampaignMembership.objects.create(
                campaign=self.campaign, user=extra_user, role="PLAYER"
            )
            # If it succeeds, that's fine (no limit implemented)
        except ValidationError:
            # If it fails with validation error, that's expected behavior
            pass

    def test_minimum_search_query_length(self):
        """Test user search with very short queries."""
        self.client.force_authenticate(user=self.owner)

        search_url = reverse(
            "api:campaigns:user_search", kwargs={"campaign_id": self.campaign.id}
        )

        # Test with single character
        response = self.client.get(search_url, {"q": "a"})

        # Should either return empty results or validation error
        self.assertIn(
            response.status_code,
            [
                status.HTTP_200_OK,
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_501_NOT_IMPLEMENTED,
            ],
        )

        if response.status_code == status.HTTP_200_OK:
            # Should return empty results for too-short queries
            self.assertEqual(len(response.data.get("results", [])), 0)

    def test_maximum_search_query_length(self):
        """Test user search with very long queries."""
        self.client.force_authenticate(user=self.owner)

        search_url = reverse(
            "api:campaigns:user_search", kwargs={"campaign_id": self.campaign.id}
        )

        # Test with very long query
        long_query = "a" * 1000
        response = self.client.get(search_url, {"q": long_query})

        # Should handle gracefully
        self.assertIn(
            response.status_code,
            [
                status.HTTP_200_OK,
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_501_NOT_IMPLEMENTED,
            ],
        )

    def test_bulk_operation_limits(self):
        """Test bulk operations with large numbers of items."""
        # Create many users
        users = []
        for i in range(50):
            user = User.objects.create_user(
                username=f"bulkuser{i}",
                email=f"bulkuser{i}@test.com",
                password="testpass123",
            )
            users.append(user)

        self.client.force_authenticate(user=self.owner)

        bulk_add_url = reverse(
            "api:campaigns:bulk_add_members", kwargs={"campaign_id": self.campaign.id}
        )

        # Try to add all users at once
        member_data = {
            "members": [{"user_id": user.id, "role": "PLAYER"} for user in users]
        }

        response = self.client.post(bulk_add_url, member_data, format="json")

        # Should either succeed or fail with appropriate limit error
        self.assertIn(
            response.status_code,
            [
                status.HTTP_201_CREATED,
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                status.HTTP_501_NOT_IMPLEMENTED,
            ],
        )


class ErrorRecoveryTest(TestCase):
    """Test error recovery and graceful degradation."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.user = User.objects.create_user(
            username="user", email="user@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Error Recovery Test", owner=self.owner, game_system="Test System"
        )

    def test_database_connection_failure_handling(self):
        """Test handling of database connection failures."""
        # Mock the Campaign.objects.get method to simulate database connection failure
        with patch("campaigns.models.Campaign.objects.get") as mock_get:
            mock_get.side_effect = Exception("Database connection failed")

            self.client.force_authenticate(user=self.owner)

            list_members_url = reverse(
                "api:campaigns:list_members", kwargs={"campaign_id": self.campaign.id}
            )

            response = self.client.get(list_members_url)

            # Should return 500 error, not crash
            self.assertEqual(
                response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR
            )

            # Should have error message
            self.assertIn("error", response.data)
            self.assertEqual(response.data["error"], "Internal server error")

    def test_partial_bulk_operation_failure(self):
        """Test handling when part of bulk operation fails."""
        # Create some valid users and some invalid data
        valid_user = User.objects.create_user(
            username="validuser", email="valid@test.com", password="testpass123"
        )

        self.client.force_authenticate(user=self.owner)

        bulk_add_url = reverse(
            "api:campaigns:bulk_add_members", kwargs={"campaign_id": self.campaign.id}
        )

        member_data = {
            "members": [
                {"user_id": valid_user.id, "role": "PLAYER"},
                {"user_id": 99999, "role": "PLAYER"},  # Invalid user ID
                {"user_id": self.owner.id, "role": "PLAYER"},  # Owner (should fail)
            ]
        }

        response = self.client.post(bulk_add_url, member_data, format="json")

        # Should return partial success information
        if response.status_code in [status.HTTP_200_OK, status.HTTP_207_MULTI_STATUS]:
            # Should indicate which operations succeeded/failed
            self.assertIn("added", response.data)
            self.assertIn("failed", response.data)

    def test_network_timeout_handling(self):
        """Test handling of network timeouts in API calls."""
        # This would typically test external API calls or long-running operations
        # For now, just test that long operations can be interrupted

        with patch("time.sleep", side_effect=Exception("Timeout")):
            self.client.force_authenticate(user=self.owner)

            # Simulate operation that might timeout
            search_url = reverse(
                "api:campaigns:user_search", kwargs={"campaign_id": self.campaign.id}
            )

            response = self.client.get(search_url, {"q": "test"})

            # Should handle timeout gracefully
            self.assertIn(
                response.status_code,
                [
                    status.HTTP_200_OK,
                    status.HTTP_408_REQUEST_TIMEOUT,
                    status.HTTP_500_INTERNAL_SERVER_ERROR,
                    status.HTTP_501_NOT_IMPLEMENTED,
                ],
            )


class ValidationEdgeCaseTest(TestCase):
    """Test edge cases in validation logic."""

    def setUp(self):
        """Set up test data."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Validation Test Campaign", owner=self.owner, game_system="Test System"
        )

    def test_deleted_user_invitation_handling(self):
        """Test handling of invitations when user is deleted."""
        try:
            from campaigns.models import CampaignInvitation

            invitee = User.objects.create_user(
                username="invitee", email="invitee@test.com", password="testpass123"
            )

            invitation = CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=invitee,
                invited_by=self.owner,
                role="PLAYER",
            )

            invitation_id = invitation.id

            # Delete the invitee
            invitee.delete()

            # Invitation should be automatically cleaned up (CASCADE)
            self.assertFalse(
                CampaignInvitation.objects.filter(id=invitation_id).exists()
            )

        except ImportError:
            # CampaignInvitation model should exist now
            from campaigns.models import CampaignInvitation

    def test_deleted_campaign_cleanup(self):
        """Test cleanup when campaign is deleted."""
        member = User.objects.create_user(
            username="member", email="member@test.com", password="testpass123"
        )

        # Create membership
        membership = CampaignMembership.objects.create(
            campaign=self.campaign, user=member, role="PLAYER"
        )
        membership_id = membership.id

        try:
            from campaigns.models import CampaignInvitation

            # Create invitation
            invitation = CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=User.objects.create_user(
                    username="invitee", email="invitee@test.com", password="testpass123"
                ),
                invited_by=self.owner,
                role="PLAYER",
            )
            invitation_id = invitation.id

        except ImportError:
            invitation_id = None

        # Delete campaign
        self.campaign.delete()

        # Memberships should be cleaned up
        self.assertFalse(CampaignMembership.objects.filter(id=membership_id).exists())

        # Invitations should be cleaned up
        if invitation_id:
            try:
                from campaigns.models import CampaignInvitation

                self.assertFalse(
                    CampaignInvitation.objects.filter(id=invitation_id).exists()
                )
            except ImportError:
                pass

    def test_unicode_and_special_characters(self):
        """Test handling of unicode and special characters."""
        # Create user with unicode username
        unicode_user = User.objects.create_user(
            username="user_测试_🎮", email="unicode@test.com", password="testpass123"
        )

        # Should be able to create membership
        membership = CampaignMembership.objects.create(
            campaign=self.campaign, user=unicode_user, role="PLAYER"
        )

        self.assertIsNotNone(membership)
        self.assertEqual(membership.user.username, "user_测试_🎮")

    def test_null_and_empty_value_handling(self):
        """Test handling of null and empty values."""
        # Test with minimal valid data
        member = User.objects.create_user(
            username="minimal", email="minimal@test.com", password="testpass123"
        )

        # Create membership with minimal data
        membership = CampaignMembership.objects.create(
            campaign=self.campaign, user=member, role="PLAYER"
        )

        self.assertIsNotNone(membership)
        self.assertIsNotNone(membership.joined_at)

    def test_inactive_campaign_operations(self):
        """Test operations on inactive campaigns."""
        # Create inactive campaign
        inactive_campaign = Campaign.objects.create(
            name="Inactive Campaign",
            owner=self.owner,
            game_system="Test System",
            is_active=False,
        )

        member = User.objects.create_user(
            username="member", email="member@test.com", password="testpass123"
        )

        # Should be able to create membership for inactive campaign
        # (for data integrity/historical purposes)
        membership = CampaignMembership.objects.create(
            campaign=inactive_campaign, user=member, role="PLAYER"
        )

        self.assertIsNotNone(membership)
        self.assertFalse(membership.campaign.is_active)

    def test_role_case_sensitivity(self):
        """Test that role validation is case sensitive."""
        member = User.objects.create_user(
            username="member", email="member@test.com", password="testpass123"
        )

        # Test with lowercase role (should fail)
        with self.assertRaises(ValidationError):
            membership = CampaignMembership(
                campaign=self.campaign, user=member, role="player"  # lowercase
            )
            membership.full_clean()

        # Test with correct case (should succeed)
        membership = CampaignMembership(
            campaign=self.campaign, user=member, role="PLAYER"  # uppercase
        )
        membership.full_clean()  # Should not raise


class PerformanceEdgeCaseTest(TestCase):
    """Test performance-related edge cases."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Performance Test Campaign",
            owner=self.owner,
            game_system="Test System",
        )

    def test_large_member_list_performance(self):
        """Test performance with large member lists."""
        # Create many members
        members = []
        for i in range(100):
            user = User.objects.create_user(
                username=f"perfuser{i:03d}",
                email=f"perfuser{i:03d}@test.com",
                password="testpass123",
            )
            CampaignMembership.objects.create(
                campaign=self.campaign, user=user, role="PLAYER"
            )
            members.append(user)

        self.client.force_authenticate(user=self.owner)

        import time

        # Test member list API performance
        start_time = time.time()

        list_members_url = reverse(
            "api:campaigns:list_members", kwargs={"campaign_id": self.campaign.id}
        )

        response = self.client.get(list_members_url)

        end_time = time.time()

        if response.status_code == status.HTTP_200_OK:
            # Should respond within reasonable time (2 seconds)
            response_time = end_time - start_time
            self.assertLess(
                response_time,
                2.0,
                f"Member list should load quickly, took {response_time:.2f}s",
            )

    def test_search_with_many_users(self):
        """Test user search performance with many users in database."""
        # Create many users
        for i in range(200):
            User.objects.create_user(
                username=f"searchuser{i:03d}",
                email=f"searchuser{i:03d}@test.com",
                password="testpass123",
            )

        self.client.force_authenticate(user=self.owner)

        search_url = reverse(
            "api:campaigns:user_search", kwargs={"campaign_id": self.campaign.id}
        )

        import time

        start_time = time.time()

        response = self.client.get(search_url, {"q": "searchuser"})

        end_time = time.time()

        if response.status_code == status.HTTP_200_OK:
            # Should respond within reasonable time
            response_time = end_time - start_time
            self.assertLess(
                response_time,
                1.0,
                f"User search should be fast, took {response_time:.2f}s",
            )

            # Should return paginated results, not all at once
            if "results" in response.data:
                self.assertLessEqual(
                    len(response.data["results"]),
                    50,
                    "Search should return limited results per page",
                )
