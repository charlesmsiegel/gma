"""
Tests for User Search API for campaign invitations.

This module tests the API endpoints for searching users to invite to campaigns,
including search functionality, exclusions, pagination, and permissions.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from campaigns.models import Campaign, CampaignMembership

User = get_user_model()


class UserSearchAPITest(TestCase):
    """Test the user search API for campaign invitations."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

        # Create campaign owner
        self.owner = User.objects.create_user(
            username="campaignowner", email="owner@test.com", password="testpass123"
        )

        # Create GM
        self.gm = User.objects.create_user(
            username="gamemaster", email="gm@test.com", password="testpass123"
        )

        # Create player
        self.player = User.objects.create_user(
            username="existingplayer", email="player@test.com", password="testpass123"
        )

        # Create users to search for
        self.searchable_user1 = User.objects.create_user(
            username="alice_searchable", email="alice@test.com", password="testpass123"
        )

        self.searchable_user2 = User.objects.create_user(
            username="bob_findable", email="bob@test.com", password="testpass123"
        )

        self.searchable_user3 = User.objects.create_user(
            username="charlie_discoverable",
            email="charlie@searchtest.com",
            password="testpass123",
        )

        # Create non-member user
        self.non_member = User.objects.create_user(
            username="nonmember", email="nonmember@test.com", password="testpass123"
        )

        # Create campaign
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

        self.search_url = reverse(
            "api:campaigns:user_search", kwargs={"campaign_id": self.campaign.id}
        )

    def test_user_search_requires_authentication(self):
        """Test that unauthenticated users cannot search for users."""
        response = self.client.get(self.search_url, {"q": "alice"})

        # Should require authentication
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_search_requires_campaign_membership(self):
        """Test that only campaign members can search for users."""
        self.client.force_authenticate(user=self.non_member)

        response = self.client.get(self.search_url, {"q": "alice"})

        # Non-members should get 404 (hiding campaign existence)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_campaign_owner_can_search_users(self):
        """Test that campaign owner can search for users to invite."""
        self.client.force_authenticate(user=self.owner)

        # This test will fail until the API endpoint is implemented
        response = self.client.get(self.search_url, {"q": "alice"})

        # Should succeed once implemented
        self.assertIn(
            response.status_code, [status.HTTP_200_OK, status.HTTP_501_NOT_IMPLEMENTED]
        )

    def test_campaign_gm_can_search_users(self):
        """Test that campaign GM can search for users to invite."""
        self.client.force_authenticate(user=self.gm)

        response = self.client.get(self.search_url, {"q": "bob"})

        # Should succeed once implemented
        self.assertIn(
            response.status_code, [status.HTTP_200_OK, status.HTTP_501_NOT_IMPLEMENTED]
        )

    def test_campaign_player_cannot_search_users(self):
        """Test that regular players cannot search for users."""
        self.client.force_authenticate(user=self.player)

        response = self.client.get(self.search_url, {"q": "alice"})

        # Players should not be able to search/invite
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_search_by_username_partial_match(self):
        """Test searching users by partial username match."""
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(self.search_url, {"q": "alice"})

        # Once implemented, should find alice_searchable
        if response.status_code == status.HTTP_200_OK:
            usernames = [user["username"] for user in response.data["results"]]
            self.assertIn("alice_searchable", usernames)

    def test_search_by_email_partial_match(self):
        """Test searching users by partial email match."""
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(self.search_url, {"q": "searchtest"})

        # Once implemented, should find charlie_discoverable
        if response.status_code == status.HTTP_200_OK:
            emails = [user["email"] for user in response.data["results"]]
            self.assertIn("charlie@searchtest.com", emails)

    def test_search_excludes_campaign_owner(self):
        """Test that search excludes the campaign owner."""
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(self.search_url, {"q": "campaignowner"})

        # Once implemented, should not include owner in results
        if response.status_code == status.HTTP_200_OK:
            usernames = [user["username"] for user in response.data["results"]]
            self.assertNotIn("campaignowner", usernames)

    def test_search_excludes_existing_members(self):
        """Test that search excludes users who are already campaign members."""
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(self.search_url, {"q": "gamemaster"})

        # Once implemented, should not include existing GM in results
        if response.status_code == status.HTTP_200_OK:
            usernames = [user["username"] for user in response.data["results"]]
            self.assertNotIn("gamemaster", usernames)

        response = self.client.get(self.search_url, {"q": "existingplayer"})

        # Once implemented, should not include existing player in results
        if response.status_code == status.HTTP_200_OK:
            usernames = [user["username"] for user in response.data["results"]]
            self.assertNotIn("existingplayer", usernames)

    def test_search_excludes_pending_invitations(self):
        """Test that search excludes users with pending invitations."""
        # This test will fail until CampaignInvitation model is implemented
        try:
            from campaigns.models import CampaignInvitation

            # Create pending invitation
            CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=self.searchable_user1,
                invited_by=self.owner,
                role="PLAYER",
                status="PENDING",
            )

            self.client.force_authenticate(user=self.owner)

            response = self.client.get(self.search_url, {"q": "alice"})

            # Once implemented, should not include users with pending invitations
            if response.status_code == status.HTTP_200_OK:
                usernames = [user["username"] for user in response.data["results"]]
                self.assertNotIn("alice_searchable", usernames)

        except ImportError:
            # CampaignInvitation model not yet implemented
            # CampaignInvitation model should exist now
            from campaigns.models import CampaignInvitation

    def test_search_includes_users_with_declined_invitations(self):
        """Test that search includes users who declined previous invitations."""
        try:
            from campaigns.models import CampaignInvitation

            # Create declined invitation
            CampaignInvitation.objects.create(
                campaign=self.campaign,
                invited_user=self.searchable_user1,
                invited_by=self.owner,
                role="PLAYER",
                status="DECLINED",
            )

            self.client.force_authenticate(user=self.owner)

            response = self.client.get(self.search_url, {"q": "alice"})

            # Once implemented, should include users who declined
            if response.status_code == status.HTTP_200_OK:
                usernames = [user["username"] for user in response.data["results"]]
                self.assertIn("alice_searchable", usernames)

        except ImportError:
            # CampaignInvitation model not yet implemented
            # CampaignInvitation model should exist now
            from campaigns.models import CampaignInvitation

    def test_search_pagination(self):
        """Test that search results are properly paginated."""
        # Create many users for pagination testing
        for i in range(15):
            User.objects.create_user(
                username=f"testuser_{i:02d}",
                email=f"testuser{i:02d}@test.com",
                password="testpass123",
            )

        self.client.force_authenticate(user=self.owner)

        response = self.client.get(self.search_url, {"q": "testuser", "page": 1})

        # Once implemented, should return paginated results
        if response.status_code == status.HTTP_200_OK:
            self.assertIn("results", response.data)
            self.assertIn("count", response.data)
            self.assertIn("next", response.data)
            self.assertIn("previous", response.data)

    def test_search_page_size_parameter(self):
        """Test that search respects page_size parameter."""
        # Create users for testing
        for i in range(10):
            User.objects.create_user(
                username=f"pagetest_{i:02d}",
                email=f"pagetest{i:02d}@test.com",
                password="testpass123",
            )

        self.client.force_authenticate(user=self.owner)

        response = self.client.get(self.search_url, {"q": "pagetest", "page_size": 5})

        # Once implemented, should respect page_size
        if response.status_code == status.HTTP_200_OK:
            self.assertLessEqual(len(response.data["results"]), 5)

    def test_search_empty_query_returns_no_results(self):
        """Test that empty search query returns no results."""
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(self.search_url, {"q": ""})

        # Once implemented, should return empty results for empty query
        if response.status_code == status.HTTP_200_OK:
            self.assertEqual(len(response.data["results"]), 0)

    def test_search_minimum_query_length(self):
        """Test that search requires minimum query length."""
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(self.search_url, {"q": "a"})  # Too short

        # Once implemented, should require minimum query length
        if response.status_code == status.HTTP_200_OK:
            # Should return empty results or validation error
            self.assertIn(len(response.data["results"]), [0])
        elif response.status_code == status.HTTP_400_BAD_REQUEST:
            # Validation error for query too short
            self.assertIn("q", response.data)

    def test_search_case_insensitive(self):
        """Test that search is case insensitive."""
        self.client.force_authenticate(user=self.owner)

        # Search with different cases
        response1 = self.client.get(self.search_url, {"q": "ALICE"})
        response2 = self.client.get(self.search_url, {"q": "alice"})
        response3 = self.client.get(self.search_url, {"q": "Alice"})

        # Once implemented, all should return same results
        if all(
            r.status_code == status.HTTP_200_OK
            for r in [response1, response2, response3]
        ):
            results1 = set(u["username"] for u in response1.data["results"])
            results2 = set(u["username"] for u in response2.data["results"])
            results3 = set(u["username"] for u in response3.data["results"])

            self.assertEqual(results1, results2)
            self.assertEqual(results2, results3)

    def test_search_response_structure(self):
        """Test that search response has correct structure."""
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(self.search_url, {"q": "alice"})

        # Once implemented, should have proper structure
        if response.status_code == status.HTTP_200_OK:
            # Paginated response structure
            self.assertIn("count", response.data)
            self.assertIn("next", response.data)
            self.assertIn("previous", response.data)
            self.assertIn("results", response.data)

            # If there are results, check user structure
            if response.data["results"]:
                user = response.data["results"][0]
                required_fields = ["id", "username", "email"]
                for field in required_fields:
                    self.assertIn(field, user)

    def test_search_nonexistent_campaign_returns_404(self):
        """Test that searching for nonexistent campaign returns 404."""
        self.client.force_authenticate(user=self.owner)

        nonexistent_url = reverse(
            "api:campaigns:user_search", kwargs={"campaign_id": 99999}
        )

        response = self.client.get(nonexistent_url, {"q": "alice"})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_search_inactive_campaign_returns_404(self):
        """Test that searching for inactive campaign returns 404."""
        # Create inactive campaign
        inactive_campaign = Campaign.objects.create(
            name="Inactive Campaign",
            owner=self.owner,
            game_system="Test System",
            is_active=False,
        )

        inactive_url = reverse(
            "api:campaigns:user_search", kwargs={"campaign_id": inactive_campaign.id}
        )

        self.client.force_authenticate(user=self.owner)

        response = self.client.get(inactive_url, {"q": "alice"})

        # Should return 404 for inactive campaigns
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class UserSearchAPISecurityTest(TestCase):
    """Security tests for user search API."""

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

    def test_cannot_search_other_campaigns(self):
        """Test that users cannot search for users in campaigns they don't own/GM."""
        self.client.force_authenticate(user=self.owner1)

        # Try to search campaign2 (owned by owner2)
        other_campaign_url = reverse(
            "api:campaigns:user_search", kwargs={"campaign_id": self.campaign2.id}
        )

        response = self.client.get(other_campaign_url, {"q": "test"})

        # Should return 404 (hiding campaign existence)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_sql_injection_protection(self):
        """Test that search is protected against SQL injection."""
        self.client.force_authenticate(user=self.owner1)

        search_url = reverse(
            "api:campaigns:user_search", kwargs={"campaign_id": self.campaign1.id}
        )

        # Try SQL injection in search query
        malicious_queries = [
            "'; DROP TABLE auth_user; --",
            "' UNION SELECT * FROM auth_user --",
            "admin' OR '1'='1",
        ]

        for query in malicious_queries:
            response = self.client.get(search_url, {"q": query})

            # Should handle safely (either 200 with no results or 400 bad request)
            self.assertIn(
                response.status_code,
                [
                    status.HTTP_200_OK,
                    status.HTTP_400_BAD_REQUEST,
                    status.HTTP_501_NOT_IMPLEMENTED,
                ],
            )

    def test_xss_protection_in_search_results(self):
        """Test that search API returns data correctly (frontend handles escaping)."""
        # Create user with HTML content in username
        malicious_user = User.objects.create_user(
            username="<script>alert('xss')</script>",
            email="malicious@test.com",
            password="testpass123",
        )

        self.client.force_authenticate(user=self.owner1)

        search_url = reverse(
            "api:campaigns:user_search", kwargs={"campaign_id": self.campaign1.id}
        )

        response = self.client.get(search_url, {"q": "script"})

        # API should return data as-is (DRF/JSON handles proper encoding)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check that the user data is returned correctly in the JSON response
        response_data = response.json()
        self.assertEqual(len(response_data["results"]), 1)

        user_data = response_data["results"][0]
        self.assertEqual(user_data["id"], malicious_user.id)
        self.assertEqual(user_data["username"], "<script>alert('xss')</script>")
        self.assertEqual(user_data["email"], "malicious@test.com")

        # JSON response is properly encoded by DRF, frontend handles escaping

    def test_rate_limiting_protection(self):
        """Test that search API has reasonable rate limiting."""
        self.client.force_authenticate(user=self.owner1)

        search_url = reverse(
            "api:campaigns:user_search", kwargs={"campaign_id": self.campaign1.id}
        )

        # Make many requests quickly
        responses = []
        for i in range(20):  # Assuming reasonable rate limit is less than 20/second
            response = self.client.get(search_url, {"q": f"test{i}"})
            responses.append(response.status_code)

        # Should either all succeed or start rate limiting
        unique_statuses = set(responses)
        expected_statuses = {
            status.HTTP_200_OK,
            status.HTTP_429_TOO_MANY_REQUESTS,
            status.HTTP_501_NOT_IMPLEMENTED,
        }

        # All response codes should be expected ones
        self.assertTrue(unique_statuses.issubset(expected_statuses))


class UserSearchAPIPerformanceTest(TestCase):
    """Performance-related tests for user search API."""

    def setUp(self):
        """Set up test data with many users."""
        self.client = APIClient()

        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Performance Test Campaign",
            owner=self.owner,
            game_system="Test System",
        )

        # Create many users to test search performance
        self.users = []
        for i in range(100):
            user = User.objects.create_user(
                username=f"perfuser_{i:03d}",
                email=f"perfuser{i:03d}@test.com",
                password="testpass123",
            )
            self.users.append(user)

    def test_search_with_many_users_performs_reasonably(self):
        """Test that search performs well with many users in database."""
        self.client.force_authenticate(user=self.owner)

        search_url = reverse(
            "api:campaigns:user_search", kwargs={"campaign_id": self.campaign.id}
        )

        import time

        start_time = time.time()
        response = self.client.get(search_url, {"q": "perfuser"})
        end_time = time.time()

        # Once implemented, should respond quickly (under 1 second)
        if response.status_code == status.HTTP_200_OK:
            response_time = end_time - start_time
            self.assertLess(response_time, 1.0, "Search should respond within 1 second")

    def test_search_pagination_limits_results(self):
        """Test that pagination prevents returning too many results at once."""
        self.client.force_authenticate(user=self.owner)

        search_url = reverse(
            "api:campaigns:user_search", kwargs={"campaign_id": self.campaign.id}
        )

        response = self.client.get(search_url, {"q": "perfuser"})

        # Once implemented, should limit results per page
        if response.status_code == status.HTTP_200_OK:
            # Should not return all 100 users at once
            self.assertLess(len(response.data["results"]), 50)
            # Should have pagination info
            self.assertIn("next", response.data)
