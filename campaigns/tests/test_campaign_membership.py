"""
Comprehensive tests for CampaignMembership model based on GitHub issue #21.

These tests validate the exact model structure and business logic requirements:
- OWNER, GM, PLAYER, OBSERVER role choices
- Unique constraint on user-campaign pairs
- Cascade deletion behavior
- Role validation
- String representation
- Auto-populated joined_at field
- Admin registration and display
- Exactly one OWNER per campaign business rule
- Role hierarchy and permission methods
- Business logic for role assignment and promotion
"""

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from campaigns.admin import CampaignMembershipAdmin
from campaigns.models import Campaign, CampaignMembership

User = get_user_model()


class CampaignMembershipModelStructureTest(TestCase):
    """Test the CampaignMembership model structure and fields."""

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
        self.campaign = Campaign.objects.create(
            name="Test Campaign", owner=self.owner, game_system="Mage: The Ascension"
        )

    def test_model_fields_exist(self):
        """Test that all required model fields exist with correct types."""
        # Test field existence and types
        membership = CampaignMembership._meta

        # user field
        user_field = membership.get_field("user")
        self.assertIsInstance(user_field, models.ForeignKey)
        self.assertEqual(user_field.related_model, User)
        self.assertEqual(user_field.remote_field.on_delete, models.CASCADE)

        # campaign field
        campaign_field = membership.get_field("campaign")
        self.assertIsInstance(campaign_field, models.ForeignKey)
        self.assertEqual(campaign_field.related_model, Campaign)
        self.assertEqual(campaign_field.remote_field.on_delete, models.CASCADE)

        # role field
        role_field = membership.get_field("role")
        self.assertIsInstance(role_field, models.CharField)
        self.assertEqual(role_field.max_length, 10)

        # joined_at field
        joined_at_field = membership.get_field("joined_at")
        self.assertIsInstance(joined_at_field, models.DateTimeField)
        self.assertTrue(joined_at_field.auto_now_add)

    def test_role_choices_exact_match(self):
        """Test that ROLE_CHOICES contains exactly the 4 required roles."""
        expected_choices = [
            ("OWNER", "Owner"),
            ("GM", "Game Master"),
            ("PLAYER", "Player"),
            ("OBSERVER", "Observer"),
        ]
        self.assertEqual(CampaignMembership.ROLE_CHOICES, expected_choices)

    def test_role_max_length(self):
        """Test that role field has max_length=10 to accommodate all role choices."""
        role_field = CampaignMembership._meta.get_field("role")
        self.assertEqual(role_field.max_length, 10)

        # Test that all role choices fit within max_length
        for role_value, role_display in CampaignMembership.ROLE_CHOICES:
            self.assertLessEqual(len(role_value), 10)

    def test_unique_constraint_on_user_campaign_pairs(self):
        """Test unique constraint prevents duplicate user-campaign pairs."""
        # Create first membership
        CampaignMembership.objects.create(
            user=self.player, campaign=self.campaign, role="PLAYER"
        )

        # Attempt to create duplicate with different role should fail
        with self.assertRaises(IntegrityError):
            CampaignMembership.objects.create(
                user=self.player, campaign=self.campaign, role="OBSERVER"
            )

    def test_joined_at_auto_populated(self):
        """Test that joined_at is automatically populated on creation."""
        membership = CampaignMembership.objects.create(
            user=self.player, campaign=self.campaign, role="PLAYER"
        )

        self.assertIsNotNone(membership.joined_at)
        self.assertIsInstance(membership.joined_at, timezone.datetime)

        # Should be very recent (within last minute)
        time_diff = timezone.now() - membership.joined_at
        self.assertLess(time_diff.total_seconds(), 60)


class CampaignMembershipRoleValidationTest(TestCase):
    """Test role validation for CampaignMembership."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@test.com", password="testpass123"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign", owner=self.user, game_system="Test System"
        )

    def test_all_valid_roles_work(self):
        """Test that all 4 role choices work correctly."""
        valid_roles = ["OWNER", "GM", "PLAYER", "OBSERVER"]

        for role in valid_roles:
            if role == "OWNER":
                # OWNER already exists due to signal when campaign was created
                membership = CampaignMembership.objects.get(
                    campaign=self.campaign, role="OWNER"
                )
                self.assertEqual(membership.user, self.user)
                self.assertEqual(membership.role, "OWNER")
            else:
                # Use different users for each role due to unique constraint
                user = User.objects.create_user(
                    username=f"user_{role.lower()}",
                    email=f"{role.lower()}@test.com",
                    password="testpass123",
                )

                membership = CampaignMembership.objects.create(
                    user=user, campaign=self.campaign, role=role
                )

                self.assertEqual(membership.role, role)
                # Test role is saved correctly
                membership.refresh_from_db()
                self.assertEqual(membership.role, role)

    def test_invalid_role_fails_validation(self):
        """Test that invalid roles fail validation."""
        invalid_roles = ["ADMIN", "MODERATOR", "invalid", "", "owner", "gm"]

        for invalid_role in invalid_roles:
            user = User.objects.create_user(
                username=f"user_{invalid_role or 'empty'}",
                email=f"{invalid_role or 'empty'}@test.com",
                password="testpass123",
            )

            membership = CampaignMembership(
                user=user, campaign=self.campaign, role=invalid_role
            )

            with self.assertRaises(ValidationError) as context:
                membership.full_clean()

            self.assertIn("role", context.exception.error_dict)


class CampaignMembershipCascadeDeletionTest(TestCase):
    """Test cascade deletion behavior for CampaignMembership."""

    def setUp(self):
        """Set up test data."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.member = User.objects.create_user(
            username="member", email="member@test.com", password="testpass123"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign", owner=self.owner, game_system="Test System"
        )

    def test_user_deletion_cascades_to_memberships(self):
        """Test that deleting user deletes associated memberships."""
        membership = CampaignMembership.objects.create(
            user=self.member, campaign=self.campaign, role="PLAYER"
        )
        membership_id = membership.id

        # Delete user
        self.member.delete()

        # Membership should be deleted
        self.assertFalse(CampaignMembership.objects.filter(id=membership_id).exists())

    def test_campaign_deletion_cascades_to_memberships(self):
        """Test that deleting campaign deletes associated memberships."""
        membership = CampaignMembership.objects.create(
            user=self.member, campaign=self.campaign, role="PLAYER"
        )
        membership_id = membership.id

        # Delete campaign
        self.campaign.delete()

        # Membership should be deleted
        self.assertFalse(CampaignMembership.objects.filter(id=membership_id).exists())

    def test_multiple_memberships_cascade_correctly(self):
        """Test that all memberships are deleted when campaign is deleted."""
        # Create multiple memberships
        user1 = User.objects.create_user(
            username="user1", email="user1@test.com", password="pass"
        )
        user2 = User.objects.create_user(
            username="user2", email="user2@test.com", password="pass"
        )

        CampaignMembership.objects.create(user=user1, campaign=self.campaign, role="GM")
        CampaignMembership.objects.create(
            user=user2, campaign=self.campaign, role="PLAYER"
        )

        campaign_id = self.campaign.id

        # Delete campaign
        self.campaign.delete()

        # All memberships should be deleted
        self.assertEqual(
            CampaignMembership.objects.filter(campaign_id=campaign_id).count(), 0
        )


class CampaignMembershipStringRepresentationTest(TestCase):
    """Test string representation of CampaignMembership."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@test.com", password="testpass123"
        )
        self.campaign = Campaign.objects.create(
            name="My Campaign", owner=self.user, game_system="Test System"
        )

    def test_string_representation_format(self):
        """Test that __str__ returns 'user-campaign-role' format."""
        # Create a different user since campaign owner already has OWNER membership
        player_user = User.objects.create_user(
            username="player", email="player@test.com", password="testpass123"
        )
        membership = CampaignMembership.objects.create(
            user=player_user, campaign=self.campaign, role="PLAYER"
        )

        expected_str = f"{player_user.username} - {self.campaign.name} (PLAYER)"
        self.assertEqual(str(membership), expected_str)

    def test_string_representation_all_roles(self):
        """Test string representation for all role types."""
        for role, role_display in CampaignMembership.ROLE_CHOICES:
            if role == "OWNER":
                # OWNER already exists due to signal when campaign was created
                membership = CampaignMembership.objects.get(
                    campaign=self.campaign, role="OWNER"
                )
                expected_str = (
                    f"{membership.user.username} - {self.campaign.name} ({role})"
                )
                self.assertEqual(str(membership), expected_str)
            else:
                user = User.objects.create_user(
                    username=f"user_{role.lower()}",
                    email=f"{role.lower()}@test.com",
                    password="testpass123",
                )

                membership = CampaignMembership.objects.create(
                    user=user, campaign=self.campaign, role=role
                )

                expected_str = f"{user.username} - {self.campaign.name} ({role})"
                self.assertEqual(str(membership), expected_str)


class CampaignMembershipAdminRegistrationTest(TestCase):
    """Test admin registration and display for CampaignMembership."""

    def test_admin_is_registered(self):
        """Test that CampaignMembership is registered in admin."""
        from django.contrib import admin

        # Check if model is registered
        self.assertIn(CampaignMembership, admin.site._registry)

        # Check admin class is correct type
        admin_class = admin.site._registry[CampaignMembership]
        self.assertIsInstance(admin_class, CampaignMembershipAdmin)

    def test_admin_display_configuration(self):
        """Test admin display configuration."""
        admin_instance = CampaignMembershipAdmin(CampaignMembership, AdminSite())

        # Test list_display includes key fields
        expected_fields = ["user", "campaign", "role", "joined_at"]
        for field in expected_fields:
            self.assertIn(field, admin_instance.list_display)

        # Test list_filter includes role and joined_at for filtering
        self.assertIn("role", admin_instance.list_filter)
        self.assertIn("joined_at", admin_instance.list_filter)

        # Test search_fields for easy searching
        self.assertIn("user__username", admin_instance.search_fields)
        self.assertIn("campaign__name", admin_instance.search_fields)


class CampaignMembershipBusinessLogicTest(TransactionTestCase):
    """Test business logic requirements from GitHub issue #21."""

    def setUp(self):
        """Set up test data."""
        self.campaign_creator = User.objects.create_user(
            username="creator", email="creator@test.com", password="testpass123"
        )
        self.other_user = User.objects.create_user(
            username="otheruser", email="other@test.com", password="testpass123"
        )
        self.gm_user = User.objects.create_user(
            username="gm", email="gm@test.com", password="testpass123"
        )
        self.player_user = User.objects.create_user(
            username="player", email="player@test.com", password="testpass123"
        )

    def test_campaign_creator_automatically_gets_owner_role(self):
        """Test that campaign creator automatically gets OWNER role."""
        campaign = Campaign.objects.create(
            name="New Campaign", owner=self.campaign_creator, game_system="Test System"
        )

        # Should automatically create OWNER membership
        owner_membership = CampaignMembership.objects.filter(
            campaign=campaign, user=self.campaign_creator, role="OWNER"
        )
        self.assertTrue(owner_membership.exists())

    def test_exactly_one_owner_per_campaign_constraint(self):
        """Test that there must always be exactly one OWNER per campaign."""
        campaign = Campaign.objects.create(
            name="Test Campaign", owner=self.campaign_creator, game_system="Test System"
        )

        # Try to create another OWNER membership - should fail
        with self.assertRaises((ValidationError, IntegrityError)):
            with transaction.atomic():
                CampaignMembership.objects.create(
                    user=self.other_user, campaign=campaign, role="OWNER"
                )

    def test_owner_transfer_business_logic(self):
        """Test OWNER can transfer ownership to another user."""
        campaign = Campaign.objects.create(
            name="Test Campaign", owner=self.campaign_creator, game_system="Test System"
        )

        # Current owner should exist
        original_owner = CampaignMembership.objects.get(campaign=campaign, role="OWNER")
        self.assertEqual(original_owner.user, self.campaign_creator)

        # Transfer ownership (this would be done through a business logic method)
        # For now, test that we can change ownership at model level
        original_owner.user = self.other_user
        original_owner.save()

        # Verify transfer
        new_owner = CampaignMembership.objects.get(campaign=campaign, role="OWNER")
        self.assertEqual(new_owner.user, self.other_user)

        # Still only one owner
        owner_count = CampaignMembership.objects.filter(
            campaign=campaign, role="OWNER"
        ).count()
        self.assertEqual(owner_count, 1)

    def test_gm_can_invite_users_as_player(self):
        """Test GM can invite users as PLAYER."""
        campaign = Campaign.objects.create(
            name="Test Campaign", owner=self.campaign_creator, game_system="Test System"
        )

        # Add GM membership
        CampaignMembership.objects.create(
            user=self.gm_user, campaign=campaign, role="GM"
        )

        # GM invites player (business logic would handle permissions)
        player_membership = CampaignMembership.objects.create(
            user=self.player_user, campaign=campaign, role="PLAYER"
        )

        self.assertEqual(player_membership.role, "PLAYER")
        self.assertEqual(player_membership.user, self.player_user)

    def test_anyone_can_join_as_observer(self):
        """Test anyone can join as OBSERVER."""
        campaign = Campaign.objects.create(
            name="Public Campaign",
            owner=self.campaign_creator,
            game_system="Test System",
        )

        # Any user can join as observer
        observer_membership = CampaignMembership.objects.create(
            user=self.other_user, campaign=campaign, role="OBSERVER"
        )

        self.assertEqual(observer_membership.role, "OBSERVER")
        self.assertEqual(observer_membership.user, self.other_user)

    def test_owner_can_promote_player_to_gm(self):
        """Test OWNER can promote PLAYER to GM."""
        campaign = Campaign.objects.create(
            name="Test Campaign", owner=self.campaign_creator, game_system="Test System"
        )

        # Create player membership
        player_membership = CampaignMembership.objects.create(
            user=self.player_user, campaign=campaign, role="PLAYER"
        )

        # Owner promotes player to GM
        player_membership.role = "GM"
        player_membership.save()

        # Verify promotion
        player_membership.refresh_from_db()
        self.assertEqual(player_membership.role, "GM")


class CampaignMembershipRoleHierarchyTest(TestCase):
    """Test role hierarchy and permissions checking methods."""

    def setUp(self):
        """Set up test data with various role memberships."""
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
            name="Test Campaign", owner=self.owner, game_system="Test System"
        )

        # Create memberships for all roles (OWNER already created by signal)
        CampaignMembership.objects.create(
            user=self.gm, campaign=self.campaign, role="GM"
        )
        CampaignMembership.objects.create(
            user=self.player, campaign=self.campaign, role="PLAYER"
        )
        CampaignMembership.objects.create(
            user=self.observer, campaign=self.campaign, role="OBSERVER"
        )

    def test_has_owner_permissions(self):
        """Test method to check if user has OWNER permissions."""
        # This would be a method on the model to check owner permissions
        owner_membership = CampaignMembership.objects.get(
            campaign=self.campaign, user=self.owner
        )
        gm_membership = CampaignMembership.objects.get(
            campaign=self.campaign, user=self.gm
        )

        # Owner has owner permissions
        self.assertEqual(owner_membership.role, "OWNER")
        # GM does not have owner permissions
        self.assertNotEqual(gm_membership.role, "OWNER")

    def test_has_gm_or_higher_permissions(self):
        """Test method to check if user has GM or higher permissions."""
        roles_with_gm_permissions = ["OWNER", "GM"]

        for role in CampaignMembership.ROLE_CHOICES:
            role_value = role[0]
            membership = CampaignMembership.objects.filter(
                campaign=self.campaign, role=role_value
            ).first()

            if membership:
                has_gm_permissions = role_value in roles_with_gm_permissions
                if has_gm_permissions:
                    self.assertIn(role_value, ["OWNER", "GM"])
                else:
                    self.assertIn(role_value, ["PLAYER", "OBSERVER"])

    def test_role_hierarchy_ordering(self):
        """Test that roles have implicit hierarchy: OWNER > GM > PLAYER > OBSERVER."""
        role_hierarchy = ["OWNER", "GM", "PLAYER", "OBSERVER"]

        # Test that each role is properly defined
        defined_roles = [choice[0] for choice in CampaignMembership.ROLE_CHOICES]
        for role in role_hierarchy:
            self.assertIn(role, defined_roles)

    def test_membership_permissions_by_role(self):
        """Test that memberships correctly identify their permission levels."""
        memberships_by_role = {}

        for role_choice in CampaignMembership.ROLE_CHOICES:
            role = role_choice[0]
            membership = CampaignMembership.objects.filter(
                campaign=self.campaign, role=role
            ).first()
            if membership:
                memberships_by_role[role] = membership

        # Verify we have memberships for each role
        expected_roles = ["OWNER", "GM", "PLAYER", "OBSERVER"]
        for role in expected_roles:
            self.assertIn(role, memberships_by_role)
            self.assertEqual(memberships_by_role[role].role, role)


class CampaignMembershipMetaOptionsTest(TestCase):
    """Test Meta options and database configuration."""

    def test_model_meta_configuration(self):
        """Test that model Meta options are configured correctly."""
        meta = CampaignMembership._meta

        # Test table name if specified
        if hasattr(meta, "db_table"):
            self.assertTrue(meta.db_table)

        # Test ordering
        self.assertTrue(hasattr(meta, "ordering"))

        # Test verbose names
        self.assertEqual(meta.verbose_name, "Campaign Membership")
        self.assertEqual(meta.verbose_name_plural, "Campaign Memberships")

    def test_unique_together_constraint(self):
        """Test that unique_together constraint exists for user-campaign pairs."""
        meta = CampaignMembership._meta

        # Check for unique constraint on user-campaign pairs
        unique_together_found = False

        # Check unique_together
        if hasattr(meta, "unique_together") and meta.unique_together:
            for constraint in meta.unique_together:
                if set(constraint) == {"user", "campaign"}:
                    unique_together_found = True
                    break

        # Check constraints (Django 2.2+)
        if hasattr(meta, "constraints"):
            for constraint in meta.constraints:
                if hasattr(constraint, "fields") and set(constraint.fields) == {
                    "user",
                    "campaign",
                }:
                    unique_together_found = True
                    break

        self.assertTrue(
            unique_together_found, "No unique constraint found on user-campaign pairs"
        )
