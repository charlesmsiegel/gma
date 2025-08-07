from django.contrib.auth import get_user_model
from django.http import Http404
from django.test import RequestFactory, TestCase
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from campaigns.models import Campaign, CampaignMembership
from campaigns.permissions import (
    CampaignPermissionMixin,
    IsCampaignGM,
    IsCampaignMember,
    IsCampaignOwner,
    IsCampaignOwnerOrGM,
)

User = get_user_model()


class PermissionClassesTest(TestCase):
    """Test the campaign permission classes."""

    def setUp(self):
        """Set up test data."""
        self.factory = APIRequestFactory()

        # Create users
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

        # Create campaign
        self.campaign = Campaign.objects.create(
            name="Test Campaign", owner=self.owner, game_system="mage"
        )

        # Create memberships
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm, role="gm"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="player"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.observer, role="observer"
        )

        # Create a simple view for testing
        self.view = APIView()
        self.view.kwargs = {"campaign_id": self.campaign.id}

    def test_is_campaign_owner_permission(self):
        """Test IsCampaignOwner permission class."""
        permission = IsCampaignOwner()

        # Owner should have permission
        request = self.factory.get("/")
        request.user = self.owner
        self.assertTrue(permission.has_permission(request, self.view))

        # GM should not have permission
        request.user = self.gm
        self.assertFalse(permission.has_permission(request, self.view))

        # Player should not have permission
        request.user = self.player
        self.assertFalse(permission.has_permission(request, self.view))

        # Non-member should not have permission
        request.user = self.non_member
        self.assertFalse(permission.has_permission(request, self.view))

    def test_is_campaign_gm_permission(self):
        """Test IsCampaignGM permission class."""
        permission = IsCampaignGM()

        # GM should have permission
        request = self.factory.get("/")
        request.user = self.gm
        self.assertTrue(permission.has_permission(request, self.view))

        # Owner should not have permission (unless also GM)
        request.user = self.owner
        self.assertFalse(permission.has_permission(request, self.view))

        # Player should not have permission
        request.user = self.player
        self.assertFalse(permission.has_permission(request, self.view))

        # Observer should not have permission
        request.user = self.observer
        self.assertFalse(permission.has_permission(request, self.view))

    def test_is_campaign_member_permission(self):
        """Test IsCampaignMember permission class."""
        permission = IsCampaignMember()

        # All members should have permission
        request = self.factory.get("/")

        request.user = self.gm
        self.assertTrue(permission.has_permission(request, self.view))

        request.user = self.player
        self.assertTrue(permission.has_permission(request, self.view))

        request.user = self.observer
        self.assertTrue(permission.has_permission(request, self.view))

        # Owner without membership should not have permission
        request.user = self.owner
        self.assertFalse(permission.has_permission(request, self.view))

        # Non-member should not have permission
        request.user = self.non_member
        self.assertFalse(permission.has_permission(request, self.view))

    def test_is_campaign_owner_or_gm_permission(self):
        """Test IsCampaignOwnerOrGM permission class."""
        permission = IsCampaignOwnerOrGM()

        request = self.factory.get("/")

        # Owner should have permission
        request.user = self.owner
        self.assertTrue(permission.has_permission(request, self.view))

        # GM should have permission
        request.user = self.gm
        self.assertTrue(permission.has_permission(request, self.view))

        # Player should not have permission
        request.user = self.player
        self.assertFalse(permission.has_permission(request, self.view))

        # Observer should not have permission
        request.user = self.observer
        self.assertFalse(permission.has_permission(request, self.view))

    def test_permission_with_nonexistent_campaign(self):
        """Test permissions with non-existent campaign ID."""
        permission = IsCampaignMember()
        self.view.kwargs = {"campaign_id": 99999}

        request = self.factory.get("/")
        request.user = self.owner

        # Should return False for non-existent campaign
        self.assertFalse(permission.has_permission(request, self.view))

    def test_permission_with_anonymous_user(self):
        """Test permissions with anonymous user."""
        from django.contrib.auth.models import AnonymousUser

        permission = IsCampaignMember()
        request = self.factory.get("/")
        request.user = AnonymousUser()

        self.assertFalse(permission.has_permission(request, self.view))

    def test_owner_with_gm_membership(self):
        """Test that owner with GM membership has both permissions."""
        # Add GM membership for owner
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.owner, role="gm"
        )

        request = self.factory.get("/")
        request.user = self.owner

        # Should have all permissions
        self.assertTrue(IsCampaignOwner().has_permission(request, self.view))
        self.assertTrue(IsCampaignGM().has_permission(request, self.view))
        self.assertTrue(IsCampaignMember().has_permission(request, self.view))
        self.assertTrue(IsCampaignOwnerOrGM().has_permission(request, self.view))


class CampaignPermissionMixinTest(TestCase):
    """Test the CampaignPermissionMixin."""

    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()

        # Create users
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.gm = User.objects.create_user(
            username="gm", email="gm@test.com", password="testpass123"
        )
        self.player = User.objects.create_user(
            username="player", email="player@test.com", password="testpass123"
        )
        self.non_member = User.objects.create_user(
            username="nonmember", email="nonmember@test.com", password="testpass123"
        )

        # Create campaigns
        self.campaign = Campaign.objects.create(
            name="Test Campaign", owner=self.owner, game_system="mage"
        )
        self.inactive_campaign = Campaign.objects.create(
            name="Inactive Campaign",
            owner=self.owner,
            game_system="mage",
            is_active=False,
        )

        # Create memberships
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm, role="gm"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="player"
        )

    def test_get_campaign_success(self):
        """Test successful campaign retrieval."""
        mixin = CampaignPermissionMixin()
        mixin.kwargs = {"campaign_id": self.campaign.id}

        campaign = mixin.get_campaign()
        self.assertEqual(campaign, self.campaign)

    def test_get_campaign_not_found(self):
        """Test campaign not found raises Http404."""
        mixin = CampaignPermissionMixin()
        mixin.kwargs = {"campaign_id": 99999}

        with self.assertRaises(Http404):
            mixin.get_campaign()

    def test_get_campaign_inactive(self):
        """Test inactive campaign raises Http404."""
        mixin = CampaignPermissionMixin()
        mixin.kwargs = {"campaign_id": self.inactive_campaign.id}

        with self.assertRaises(Http404):
            mixin.get_campaign()

    def test_check_campaign_permission_owner(self):
        """Test check_campaign_permission for owner."""
        mixin = CampaignPermissionMixin()
        mixin.kwargs = {"campaign_id": self.campaign.id}

        # Owner should pass all permission checks
        mixin.check_campaign_permission(self.owner, "owner")
        mixin.check_campaign_permission(self.owner, "owner_or_gm")

        # Owner without membership should not pass member check
        with self.assertRaises(Http404):
            mixin.check_campaign_permission(self.owner, "member")

    def test_check_campaign_permission_gm(self):
        """Test check_campaign_permission for GM."""
        mixin = CampaignPermissionMixin()
        mixin.kwargs = {"campaign_id": self.campaign.id}

        # GM should pass appropriate checks
        mixin.check_campaign_permission(self.gm, "gm")
        mixin.check_campaign_permission(self.gm, "owner_or_gm")
        mixin.check_campaign_permission(self.gm, "member")

        # GM should not pass owner check
        with self.assertRaises(Http404):
            mixin.check_campaign_permission(self.gm, "owner")

    def test_check_campaign_permission_player(self):
        """Test check_campaign_permission for player."""
        mixin = CampaignPermissionMixin()
        mixin.kwargs = {"campaign_id": self.campaign.id}

        # Player should only pass member check
        mixin.check_campaign_permission(self.player, "member")

        # Player should not pass other checks
        with self.assertRaises(Http404):
            mixin.check_campaign_permission(self.player, "owner")

        with self.assertRaises(Http404):
            mixin.check_campaign_permission(self.player, "gm")

        with self.assertRaises(Http404):
            mixin.check_campaign_permission(self.player, "owner_or_gm")

    def test_check_campaign_permission_non_member(self):
        """Test check_campaign_permission for non-member."""
        mixin = CampaignPermissionMixin()
        mixin.kwargs = {"campaign_id": self.campaign.id}

        # Non-member should fail all checks
        with self.assertRaises(Http404):
            mixin.check_campaign_permission(self.non_member, "owner")

        with self.assertRaises(Http404):
            mixin.check_campaign_permission(self.non_member, "gm")

        with self.assertRaises(Http404):
            mixin.check_campaign_permission(self.non_member, "member")

    def test_check_campaign_permission_invalid_level(self):
        """Test check_campaign_permission with invalid permission level."""
        mixin = CampaignPermissionMixin()
        mixin.kwargs = {"campaign_id": self.campaign.id}

        with self.assertRaises(ValueError):
            mixin.check_campaign_permission(self.owner, "invalid_level")

    def test_require_campaign_owner_decorator(self):
        """Test require_campaign_owner decorator."""
        from django.http import HttpResponse
        from django.views import View

        from campaigns.permissions import require_campaign_owner

        @require_campaign_owner
        class TestView(View):
            def get(self, request, campaign_id):
                return HttpResponse("Success")

        view = TestView.as_view()

        # Owner should succeed
        request = self.factory.get("/")
        request.user = self.owner
        response = view(request, campaign_id=self.campaign.id)
        self.assertEqual(response.status_code, 200)

        # GM should get 404
        request.user = self.gm
        with self.assertRaises(Http404):
            view(request, campaign_id=self.campaign.id)

        # Non-member should get 404
        request.user = self.non_member
        with self.assertRaises(Http404):
            view(request, campaign_id=self.campaign.id)

    def test_require_campaign_gm_decorator(self):
        """Test require_campaign_gm decorator."""
        from django.http import HttpResponse
        from django.views import View

        from campaigns.permissions import require_campaign_gm

        @require_campaign_gm
        class TestView(View):
            def get(self, request, campaign_id):
                return HttpResponse("Success")

        view = TestView.as_view()

        # GM should succeed
        request = self.factory.get("/")
        request.user = self.gm
        response = view(request, campaign_id=self.campaign.id)
        self.assertEqual(response.status_code, 200)

        # Owner (not GM) should get 404
        request.user = self.owner
        with self.assertRaises(Http404):
            view(request, campaign_id=self.campaign.id)

        # Player should get 404
        request.user = self.player
        with self.assertRaises(Http404):
            view(request, campaign_id=self.campaign.id)

    def test_require_campaign_member_decorator(self):
        """Test require_campaign_member decorator."""
        from django.http import HttpResponse
        from django.views import View

        from campaigns.permissions import require_campaign_member

        @require_campaign_member
        class TestView(View):
            def get(self, request, campaign_id):
                return HttpResponse("Success")

        view = TestView.as_view()
        request = self.factory.get("/")

        # All members should succeed
        request.user = self.gm
        response = view(request, campaign_id=self.campaign.id)
        self.assertEqual(response.status_code, 200)

        request.user = self.player
        response = view(request, campaign_id=self.campaign.id)
        self.assertEqual(response.status_code, 200)

        # Non-member should get 404
        request.user = self.non_member
        with self.assertRaises(Http404):
            view(request, campaign_id=self.campaign.id)

    def test_require_campaign_owner_or_gm_decorator(self):
        """Test require_campaign_owner_or_gm decorator."""
        from django.http import HttpResponse
        from django.views import View

        from campaigns.permissions import require_campaign_owner_or_gm

        @require_campaign_owner_or_gm
        class TestView(View):
            def get(self, request, campaign_id):
                return HttpResponse("Success")

        view = TestView.as_view()
        request = self.factory.get("/")

        # Owner should succeed
        request.user = self.owner
        response = view(request, campaign_id=self.campaign.id)
        self.assertEqual(response.status_code, 200)

        # GM should succeed
        request.user = self.gm
        response = view(request, campaign_id=self.campaign.id)
        self.assertEqual(response.status_code, 200)

        # Player should get 404
        request.user = self.player
        with self.assertRaises(Http404):
            view(request, campaign_id=self.campaign.id)
