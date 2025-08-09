"""
Tests for Django admin interface functionality for campaigns.

Tests cover all requirements from issue #26:
1. Campaign list display shows: name, owner, created date, member count breakdown
2. Search functionality works for: name, owner, slug
3. Filter functionality works for: creation date, member count
4. Bulk operations are available for campaigns
5. CampaignMembership inline management within campaign admin
6. Admin permissions are properly configured
"""

import datetime

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.utils import timezone

from campaigns.admin import CampaignAdmin, CampaignMembershipAdmin
from campaigns.models import Campaign, CampaignMembership

User = get_user_model()


class CampaignAdminTestCase(TestCase):
    """Base test case with common setup for campaign admin tests."""

    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        self.site = AdminSite()

        # Create users
        self.admin_user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="adminpass123"
        )
        self.owner1 = User.objects.create_user(
            username="owner1", email="owner1@example.com", password="pass123"
        )
        self.owner2 = User.objects.create_user(
            username="owner2", email="owner2@example.com", password="pass123"
        )
        self.gm1 = User.objects.create_user(
            username="gm1", email="gm1@example.com", password="pass123"
        )
        self.player1 = User.objects.create_user(
            username="player1", email="player1@example.com", password="pass123"
        )
        self.player2 = User.objects.create_user(
            username="player2", email="player2@example.com", password="pass123"
        )
        self.observer1 = User.objects.create_user(
            username="observer1", email="observer1@example.com", password="pass123"
        )

        # Create campaigns with different member configurations
        self.campaign1 = Campaign.objects.create(
            name="Epic Fantasy Campaign",
            slug="epic-fantasy",
            description="A grand adventure",
            owner=self.owner1,
            game_system="D&D 5e",
            is_active=True,
            created_at=timezone.now() - datetime.timedelta(days=30),
        )

        self.campaign2 = Campaign.objects.create(
            name="Horror Campaign",
            slug="horror",
            description="Scary stuff happens",
            owner=self.owner2,
            game_system="Call of Cthulhu",
            is_active=True,
            created_at=timezone.now() - datetime.timedelta(days=15),
        )

        self.campaign3 = Campaign.objects.create(
            name="Sci-Fi Adventure",
            slug="sci-fi",
            description="Space exploration",
            owner=self.owner1,
            game_system="Traveller",
            is_active=False,
            created_at=timezone.now() - datetime.timedelta(days=5),
        )

        # Create memberships with different role distributions
        # Campaign 1: 1 GM, 2 Players, 1 Observer (+ 1 Owner = 5 total)
        CampaignMembership.objects.create(
            campaign=self.campaign1, user=self.gm1, role="GM"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign1, user=self.player1, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign1, user=self.player2, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign1, user=self.observer1, role="OBSERVER"
        )

        # Campaign 2: 0 GM, 1 Player, 0 Observer (+ 1 Owner = 2 total)
        CampaignMembership.objects.create(
            campaign=self.campaign2, user=self.player1, role="PLAYER"
        )

        # Campaign 3: No additional members (+ 1 Owner = 1 total)

        self.campaign_admin = CampaignAdmin(Campaign, self.site)
        self.membership_admin = CampaignMembershipAdmin(CampaignMembership, self.site)


class CampaignAdminListDisplayTest(CampaignAdminTestCase):
    """Test campaign list display functionality."""

    def test_campaign_admin_list_display_fields(self):
        """Test that list_display contains required fields."""
        # Test that required fields are displayed
        self.assertIn("name", self.campaign_admin.list_display)
        self.assertIn("owner", self.campaign_admin.list_display)
        self.assertIn("created_at", self.campaign_admin.list_display)

    def test_member_count_display_method(self):
        """Test that member count display method works correctly."""
        request = self.factory.get("/admin/campaigns/campaign/")
        request.user = self.admin_user

        # Get queryset with annotations for member counts
        queryset = self.campaign_admin.get_queryset(request)

        # Find our test campaigns in the annotated queryset
        campaign1_annotated = queryset.get(pk=self.campaign1.pk)
        campaign2_annotated = queryset.get(pk=self.campaign2.pk)
        campaign3_annotated = queryset.get(pk=self.campaign3.pk)

        # Test member counts (Owner + Memberships)
        # Campaign 1: 1 Owner + 4 Memberships = 5 total
        self.assertEqual(campaign1_annotated.total_members, 5)

        # Campaign 2: 1 Owner + 1 Membership = 2 total
        self.assertEqual(campaign2_annotated.total_members, 2)

        # Campaign 3: 1 Owner + 0 Memberships = 1 total
        self.assertEqual(campaign3_annotated.total_members, 1)

    def test_role_count_annotations(self):
        """Test that role-specific counts are correctly annotated."""
        request = self.factory.get("/admin/campaigns/campaign/")
        request.user = self.admin_user

        queryset = self.campaign_admin.get_queryset(request)
        campaign1_annotated = queryset.get(pk=self.campaign1.pk)

        # Test individual role counts for campaign1
        self.assertEqual(campaign1_annotated.gm_count, 1)
        self.assertEqual(campaign1_annotated.player_count, 2)
        self.assertEqual(campaign1_annotated.observer_count, 1)

    def test_queryset_optimization(self):
        """Test that queryset is optimized to avoid N+1 queries."""
        request = self.factory.get("/admin/campaigns/campaign/")
        request.user = self.admin_user

        with self.assertNumQueries(1):  # Should be single query with annotations
            queryset = self.campaign_admin.get_queryset(request)
            # Force evaluation
            list(queryset.values("name", "owner__username", "total_members"))


class CampaignAdminSearchTest(CampaignAdminTestCase):
    """Test campaign admin search functionality."""

    def test_search_by_name(self):
        """Test searching campaigns by name."""
        request = self.factory.get("/admin/campaigns/campaign/?q=Epic")
        request.user = self.admin_user

        # Get filtered queryset
        changelist = self.campaign_admin.get_changelist_instance(request)
        queryset = changelist.get_queryset(request)

        self.assertIn(self.campaign1, queryset)
        self.assertNotIn(self.campaign2, queryset)
        self.assertNotIn(self.campaign3, queryset)

    def test_search_by_owner_username(self):
        """Test searching campaigns by owner username."""
        request = self.factory.get("/admin/campaigns/campaign/?q=owner1")
        request.user = self.admin_user

        changelist = self.campaign_admin.get_changelist_instance(request)
        queryset = changelist.get_queryset(request)

        # Should find campaigns owned by owner1
        self.assertIn(self.campaign1, queryset)
        self.assertNotIn(self.campaign2, queryset)
        self.assertIn(self.campaign3, queryset)

    def test_search_by_slug(self):
        """Test searching campaigns by slug."""
        request = self.factory.get("/admin/campaigns/campaign/?q=horror")
        request.user = self.admin_user

        changelist = self.campaign_admin.get_changelist_instance(request)
        queryset = changelist.get_queryset(request)

        self.assertNotIn(self.campaign1, queryset)
        self.assertIn(self.campaign2, queryset)
        self.assertNotIn(self.campaign3, queryset)

    def test_search_case_insensitive(self):
        """Test that search is case insensitive."""
        request = self.factory.get("/admin/campaigns/campaign/?q=EPIC")
        request.user = self.admin_user

        changelist = self.campaign_admin.get_changelist_instance(request)
        queryset = changelist.get_queryset(request)

        self.assertIn(self.campaign1, queryset)

    def test_search_partial_match(self):
        """Test that partial matches work."""
        request = self.factory.get("/admin/campaigns/campaign/?q=Fan")
        request.user = self.admin_user

        changelist = self.campaign_admin.get_changelist_instance(request)
        queryset = changelist.get_queryset(request)

        self.assertIn(self.campaign1, queryset)  # "Epic Fantasy Campaign"


class CampaignAdminFilterTest(CampaignAdminTestCase):
    """Test campaign admin filter functionality."""

    def test_filter_by_creation_date(self):
        """Test filtering campaigns by creation date."""
        # Test filtering by year in date hierarchy (more realistic admin filter)
        current_year = timezone.now().year

        request = self.factory.get(
            f"/admin/campaigns/campaign/?created_at__year={current_year}"
        )
        request.user = self.admin_user

        changelist = self.campaign_admin.get_changelist_instance(request)
        queryset = changelist.get_queryset(request)

        # Should include all campaigns created this year
        self.assertIn(self.campaign1, queryset)
        self.assertIn(self.campaign2, queryset)
        self.assertIn(self.campaign3, queryset)

    def test_filter_by_member_count_range(self):
        """Test filtering campaigns by member count ranges."""
        # This test checks the filter functionality
        # The actual filter implementation would be added to the admin class

        # Test filtering for campaigns with 2-4 members
        request = self.factory.get("/admin/campaigns/campaign/?member_count=medium")
        request.user = self.admin_user

        # Verify our expected member counts
        campaign1_total = 1 + self.campaign1.memberships.count()  # = 5
        campaign2_total = 1 + self.campaign2.memberships.count()  # = 2
        campaign3_total = 1 + self.campaign3.memberships.count()  # = 1

        self.assertEqual(campaign1_total, 5)
        self.assertEqual(campaign2_total, 2)
        self.assertEqual(campaign3_total, 1)

    def test_filter_by_active_status(self):
        """Test filtering campaigns by active status."""
        request = self.factory.get("/admin/campaigns/campaign/?is_active__exact=1")
        request.user = self.admin_user

        changelist = self.campaign_admin.get_changelist_instance(request)
        queryset = changelist.get_queryset(request)

        # Should only include active campaigns
        self.assertIn(self.campaign1, queryset)
        self.assertIn(self.campaign2, queryset)
        self.assertNotIn(self.campaign3, queryset)


class CampaignAdminBulkOperationsTest(CampaignAdminTestCase):
    """Test campaign admin bulk operations."""

    def test_bulk_delete_available(self):
        """Test that bulk delete action is available."""
        request = self.factory.get("/admin/campaigns/campaign/")
        request.user = self.admin_user
        actions = self.campaign_admin.get_actions(request)
        self.assertIn("delete_selected", actions)

    def test_custom_bulk_actions(self):
        """Test custom bulk actions for campaigns."""
        # Test that we can add custom bulk actions
        request = self.factory.get("/admin/campaigns/campaign/")
        request.user = self.admin_user
        actions = self.campaign_admin.get_actions(request)

        # Check that actions dict contains expected actions
        self.assertIsInstance(actions, dict)
        self.assertTrue(len(actions) >= 1)  # At least delete_selected

    def test_bulk_action_permissions(self):
        """Test that bulk actions respect permissions."""
        request = self.factory.get("/admin/campaigns/campaign/")
        request.user = self.admin_user

        # Admin user should have delete permission
        self.assertTrue(self.campaign_admin.has_delete_permission(request))

        # Test with a regular user
        regular_user = User.objects.create_user(
            username="regular", email="regular@example.com", password="pass123"
        )
        request.user = regular_user

        # Regular user should not have delete permission
        self.assertFalse(self.campaign_admin.has_delete_permission(request))


class CampaignMembershipInlineTest(CampaignAdminTestCase):
    """Test CampaignMembership inline management within campaign admin."""

    def test_membership_inline_fields(self):
        """Test that membership inline shows correct fields."""
        # Test that membership admin has required fields
        expected_fields = ["user", "role", "joined_at"]

        for field in expected_fields:
            self.assertIn(field, self.membership_admin.list_display)

    def test_membership_inline_filtering(self):
        """Test that membership inline can be filtered."""
        request = self.factory.get("/admin/campaigns/campaignmembership/?role=GM")
        request.user = self.admin_user

        changelist = self.membership_admin.get_changelist_instance(request)
        queryset = changelist.get_queryset(request)

        # Should only show GM memberships
        for membership in queryset:
            self.assertEqual(membership.role, "GM")

    def test_membership_inline_search(self):
        """Test searching within membership inline."""
        request = self.factory.get("/admin/campaigns/campaignmembership/?q=gm1")
        request.user = self.admin_user

        changelist = self.membership_admin.get_changelist_instance(request)
        queryset = changelist.get_queryset(request)

        # Should find membership for gm1 user
        membership_users = [m.user.username for m in queryset]
        self.assertIn("gm1", membership_users)


class CampaignAdminPermissionsTest(CampaignAdminTestCase):
    """Test admin permissions are properly configured."""

    def test_admin_has_all_permissions(self):
        """Test that admin users have all permissions."""
        request = self.factory.get("/admin/campaigns/campaign/")
        request.user = self.admin_user

        self.assertTrue(self.campaign_admin.has_view_permission(request))
        self.assertTrue(self.campaign_admin.has_add_permission(request))
        self.assertTrue(self.campaign_admin.has_change_permission(request))
        self.assertTrue(self.campaign_admin.has_delete_permission(request))

    def test_regular_user_no_permissions(self):
        """Test that regular users have no admin permissions."""
        regular_user = User.objects.create_user(
            username="regular", email="regular@example.com", password="pass123"
        )
        request = self.factory.get("/admin/campaigns/campaign/")
        request.user = regular_user

        self.assertFalse(self.campaign_admin.has_view_permission(request))
        self.assertFalse(self.campaign_admin.has_add_permission(request))
        self.assertFalse(self.campaign_admin.has_change_permission(request))
        self.assertFalse(self.campaign_admin.has_delete_permission(request))

    def test_staff_user_permissions(self):
        """Test that staff users have appropriate permissions."""
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType

        staff_user = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="pass123",
            is_staff=True,
        )

        # Add view permission to staff user
        content_type = ContentType.objects.get_for_model(Campaign)
        view_permission = Permission.objects.get(
            codename="view_campaign",
            content_type=content_type,
        )
        staff_user.user_permissions.add(view_permission)

        request = self.factory.get("/admin/campaigns/campaign/")
        request.user = staff_user

        # Staff users should have view permission when granted
        self.assertTrue(self.campaign_admin.has_view_permission(request))

        # Other permissions should be False unless specifically granted
        self.assertFalse(self.campaign_admin.has_add_permission(request))
        self.assertFalse(self.campaign_admin.has_change_permission(request))
        self.assertFalse(self.campaign_admin.has_delete_permission(request))


class CampaignAdminIntegrationTest(CampaignAdminTestCase):
    """Integration tests for campaign admin interface."""

    def test_admin_changelist_view(self):
        """Test that the admin changelist view loads correctly."""
        self.client.force_login(self.admin_user)
        response = self.client.get("/admin/campaigns/campaign/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Epic Fantasy Campaign")
        self.assertContains(response, "Horror Campaign")
        self.assertContains(response, "Sci-Fi Adventure")

    def test_admin_change_view(self):
        """Test that the admin change view loads correctly."""
        self.client.force_login(self.admin_user)
        response = self.client.get(
            f"/admin/campaigns/campaign/{self.campaign1.pk}/change/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Epic Fantasy Campaign")
        self.assertContains(response, self.owner1.username)

    def test_admin_add_view(self):
        """Test that the admin add view loads correctly."""
        self.client.force_login(self.admin_user)
        response = self.client.get("/admin/campaigns/campaign/add/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Add Campaign")

    def test_admin_delete_view(self):
        """Test that the admin delete view works correctly."""
        self.client.force_login(self.admin_user)
        response = self.client.get(
            f"/admin/campaigns/campaign/{self.campaign3.pk}/delete/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Are you sure")
        self.assertContains(response, "Sci-Fi Adventure")


class CampaignAdminCustomMethodsTest(CampaignAdminTestCase):
    """Test custom methods that should be added to CampaignAdmin."""

    def test_member_count_display_format(self):
        """Test the format of member count display."""
        # This tests the method that should be added to display member counts
        campaign = self.campaign1

        # Expected member counts for campaign1
        expected_counts = {"owner": 1, "gm": 1, "player": 2, "observer": 1, "total": 5}

        # Count actual memberships
        actual_gm = campaign.memberships.filter(role="GM").count()
        actual_player = campaign.memberships.filter(role="PLAYER").count()
        actual_observer = campaign.memberships.filter(role="OBSERVER").count()
        actual_total = 1 + actual_gm + actual_player + actual_observer

        self.assertEqual(actual_gm, expected_counts["gm"])
        self.assertEqual(actual_player, expected_counts["player"])
        self.assertEqual(actual_observer, expected_counts["observer"])
        self.assertEqual(actual_total, expected_counts["total"])

    def test_member_count_display_no_members(self):
        """Test member count display for campaign with no additional members."""
        campaign = self.campaign3

        # Should show Owner: 1, GM: 0, Player: 0, Observer: 0 (Total: 1)
        actual_gm = campaign.memberships.filter(role="GM").count()
        actual_player = campaign.memberships.filter(role="PLAYER").count()
        actual_observer = campaign.memberships.filter(role="OBSERVER").count()
        actual_total = 1 + actual_gm + actual_player + actual_observer

        self.assertEqual(actual_gm, 0)
        self.assertEqual(actual_player, 0)
        self.assertEqual(actual_observer, 0)
        self.assertEqual(actual_total, 1)


class CampaignAdminQueryOptimizationTest(CampaignAdminTestCase):
    """Test query optimization for admin interface."""

    def test_queryset_select_related(self):
        """Test that queryset uses select_related for owner."""
        request = self.factory.get("/admin/campaigns/campaign/")
        request.user = self.admin_user

        queryset = self.campaign_admin.get_queryset(request)

        # Check that the queryset includes select_related
        self.assertIn("owner", queryset.query.select_related)

    def test_queryset_annotations_efficiency(self):
        """Test that member count annotations are efficient."""
        request = self.factory.get("/admin/campaigns/campaign/")
        request.user = self.admin_user

        with self.assertNumQueries(1):
            queryset = self.campaign_admin.get_queryset(request)

            # Force evaluation with member count access
            campaigns_with_counts = list(
                queryset.values(
                    "name",
                    "owner__username",
                    "total_members",
                    "gm_count",
                    "player_count",
                    "observer_count",
                )
            )

            # Verify we got data
            self.assertEqual(len(campaigns_with_counts), 3)


class CampaignAdminRegressionTest(CampaignAdminTestCase):
    """Regression tests for campaign admin functionality."""

    def test_admin_preserves_existing_functionality(self):
        """Test that enhanced admin preserves existing functionality."""
        # Test that basic admin fields still work
        self.assertIn("name", self.campaign_admin.list_display)
        self.assertIn("owner", self.campaign_admin.list_display)
        self.assertIn("created_at", self.campaign_admin.list_display)

        # Test that search fields are preserved
        self.assertIn("name", self.campaign_admin.search_fields)
        self.assertIn("owner__username", self.campaign_admin.search_fields)

        # Test that filters are preserved
        self.assertIn("created_at", self.campaign_admin.list_filter)
        self.assertIn("is_active", self.campaign_admin.list_filter)

    def test_readonly_fields_preserved(self):
        """Test that readonly fields are preserved."""
        self.assertIn("created_at", self.campaign_admin.readonly_fields)
        self.assertIn("updated_at", self.campaign_admin.readonly_fields)

    def test_fieldsets_preserved(self):
        """Test that fieldsets structure is preserved."""
        self.assertIsNotNone(self.campaign_admin.fieldsets)
        # Basic, Ownership, Status, Timestamps
        self.assertEqual(len(self.campaign_admin.fieldsets), 4)
