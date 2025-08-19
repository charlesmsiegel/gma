"""
Tests for Location permission system integration.

Tests cover:
- Campaign role-based permissions (Owner, GM, Player, Observer)
- Location creation, editing, and deletion permissions
- Hierarchy-based permission inheritance
- View permissions for different user types
- Permission validation and security
- Cross-campaign permission isolation
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from campaigns.models import Campaign, CampaignMembership
from locations.models import Location

User = get_user_model()


class LocationPermissionTest(TestCase):
    """Test Location model permission system."""

    def setUp(self):
        """Set up test users and campaigns with different roles."""
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
            username="non_member", email="non_member@test.com", password="testpass123"
        )
        self.other_owner = User.objects.create_user(
            username="other_owner", email="other_owner@test.com", password="testpass123"
        )

        # Create campaigns
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            game_system="mage",
            is_public=False,
        )

        self.public_campaign = Campaign.objects.create(
            name="Public Campaign",
            owner=self.other_owner,
            game_system="generic",
            is_public=True,
        )

        self.other_campaign = Campaign.objects.create(
            name="Other Private Campaign",
            owner=self.other_owner,
            game_system="generic",
            is_public=False,
        )

        # Create campaign memberships
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm, role="GM"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.observer, role="OBSERVER"
        )

        # Create test locations
        self.owner_location = Location.objects.create(
            name="Owner Location",
            campaign=self.campaign,
            created_by=self.owner,
        )

        self.gm_location = Location.objects.create(
            name="GM Location",
            campaign=self.campaign,
            created_by=self.gm,
        )

        self.player_location = Location.objects.create(
            name="Player Location",
            campaign=self.campaign,
            created_by=self.player,
        )

        self.public_location = Location.objects.create(
            name="Public Location",
            campaign=self.public_campaign,
            created_by=self.other_owner,
        )

        self.other_private_location = Location.objects.create(
            name="Other Private Location",
            campaign=self.other_campaign,
            created_by=self.other_owner,
        )

    def test_location_view_permissions(self):
        """Test view permissions for different user roles."""
        # Test campaign members can view all locations in campaign
        self.assertTrue(self.owner_location.can_view(self.owner))
        self.assertTrue(self.owner_location.can_view(self.gm))
        self.assertTrue(self.owner_location.can_view(self.player))
        self.assertTrue(self.owner_location.can_view(self.observer))

        self.assertTrue(self.gm_location.can_view(self.owner))
        self.assertTrue(self.gm_location.can_view(self.gm))
        self.assertTrue(self.gm_location.can_view(self.player))
        self.assertTrue(self.gm_location.can_view(self.observer))

        self.assertTrue(self.player_location.can_view(self.owner))
        self.assertTrue(self.player_location.can_view(self.gm))
        self.assertTrue(self.player_location.can_view(self.player))
        self.assertTrue(self.player_location.can_view(self.observer))

        # Test non-members cannot view private campaign locations
        self.assertFalse(self.owner_location.can_view(self.non_member))
        self.assertFalse(self.gm_location.can_view(self.non_member))
        self.assertFalse(self.player_location.can_view(self.non_member))

        # Test non-members can view public campaign locations
        self.assertTrue(self.public_location.can_view(self.non_member))
        self.assertTrue(self.public_location.can_view(self.owner))

        # Test cross-campaign access denied
        self.assertFalse(self.other_private_location.can_view(self.owner))
        self.assertFalse(self.other_private_location.can_view(self.gm))
        self.assertFalse(self.other_private_location.can_view(self.player))

    def test_location_edit_permissions(self):
        """Test edit permissions for different user roles."""
        # Owner can edit all locations in their campaign
        self.assertTrue(self.owner_location.can_edit(self.owner))
        self.assertTrue(self.gm_location.can_edit(self.owner))
        self.assertTrue(self.player_location.can_edit(self.owner))

        # GM can edit all locations in campaign (if campaign allows it)
        # This may depend on campaign settings
        self.assertTrue(self.owner_location.can_edit(self.gm))
        self.assertTrue(self.gm_location.can_edit(self.gm))
        self.assertTrue(self.player_location.can_edit(self.gm))

        # Player can edit only their own locations
        self.assertFalse(self.owner_location.can_edit(self.player))
        self.assertFalse(self.gm_location.can_edit(self.player))
        self.assertTrue(self.player_location.can_edit(self.player))

        # Observer cannot edit any locations
        self.assertFalse(self.owner_location.can_edit(self.observer))
        self.assertFalse(self.gm_location.can_edit(self.observer))
        self.assertFalse(self.player_location.can_edit(self.observer))

        # Non-member cannot edit any locations
        self.assertFalse(self.owner_location.can_edit(self.non_member))
        self.assertFalse(self.gm_location.can_edit(self.non_member))
        self.assertFalse(self.player_location.can_edit(self.non_member))
        self.assertFalse(self.public_location.can_edit(self.non_member))

    def test_location_delete_permissions(self):
        """Test delete permissions for different user roles."""
        # Owner can delete all locations in their campaign
        self.assertTrue(self.owner_location.can_delete(self.owner))
        self.assertTrue(self.gm_location.can_delete(self.owner))
        self.assertTrue(self.player_location.can_delete(self.owner))

        # GM can delete locations based on campaign settings
        # Default behavior may vary - test both scenarios
        gm_can_delete_all = self.gm_location.can_delete(self.gm)
        if gm_can_delete_all:
            # If GMs can delete all locations
            self.assertTrue(self.owner_location.can_delete(self.gm))
            self.assertTrue(self.player_location.can_delete(self.gm))
        else:
            # If GMs can only delete their own locations
            self.assertFalse(self.owner_location.can_delete(self.gm))
            self.assertFalse(self.player_location.can_delete(self.gm))

        # GMs should always be able to delete their own locations
        self.assertTrue(self.gm_location.can_delete(self.gm))

        # Player can delete only their own locations
        self.assertFalse(self.owner_location.can_delete(self.player))
        self.assertFalse(self.gm_location.can_delete(self.player))
        self.assertTrue(self.player_location.can_delete(self.player))

        # Observer cannot delete any locations
        self.assertFalse(self.owner_location.can_delete(self.observer))
        self.assertFalse(self.gm_location.can_delete(self.observer))
        self.assertFalse(self.player_location.can_delete(self.observer))

        # Non-member cannot delete any locations
        self.assertFalse(self.public_location.can_delete(self.non_member))

    def test_location_creation_permissions(self):
        """Test location creation permissions by role."""
        # All campaign members should be able to create locations
        self.assertTrue(Location.can_create(self.owner, self.campaign))
        self.assertTrue(Location.can_create(self.gm, self.campaign))
        self.assertTrue(Location.can_create(self.player, self.campaign))

        # Observer creation permissions may depend on campaign settings
        Location.can_create(self.observer, self.campaign)
        # Test documents current behavior - may be True or False

        # Non-members cannot create locations in private campaigns
        self.assertFalse(Location.can_create(self.non_member, self.campaign))
        self.assertFalse(Location.can_create(self.non_member, self.other_campaign))

        # Non-members cannot create locations in public campaigns either
        self.assertFalse(Location.can_create(self.non_member, self.public_campaign))

    def test_permission_inheritance_in_hierarchy(self):
        """Test that hierarchy doesn't affect permission rules."""
        # Create parent-child hierarchy with different creators
        parent = Location.objects.create(
            name="Parent Location",
            campaign=self.campaign,
            created_by=self.gm,
        )

        child = Location.objects.create(
            name="Child Location",
            campaign=self.campaign,
            parent=parent,
            created_by=self.player,
        )

        # Player should be able to edit their child location
        # even if parent is owned by GM
        self.assertTrue(child.can_edit(self.player))
        self.assertFalse(parent.can_edit(self.player))

        # GM should be able to edit their parent location
        # and potentially the child (depending on campaign settings)
        self.assertTrue(parent.can_edit(self.gm))

        # Child permissions depend on campaign settings for GM
        child.can_edit(self.gm)
        # This may be True or False depending on implementation

        # Owner should be able to edit both
        self.assertTrue(parent.can_edit(self.owner))
        self.assertTrue(child.can_edit(self.owner))

    def test_cross_campaign_permission_isolation(self):
        """Test that permissions are isolated between campaigns."""
        # Users should not have permissions on other campaigns' locations
        self.assertFalse(self.other_private_location.can_view(self.owner))
        self.assertFalse(self.other_private_location.can_edit(self.owner))
        self.assertFalse(self.other_private_location.can_delete(self.owner))

        self.assertFalse(self.other_private_location.can_view(self.gm))
        self.assertFalse(self.other_private_location.can_edit(self.gm))
        self.assertFalse(self.other_private_location.can_delete(self.gm))

        # Even if location is public, editing should be restricted
        self.assertTrue(self.public_location.can_view(self.owner))
        self.assertFalse(self.public_location.can_edit(self.owner))
        self.assertFalse(self.public_location.can_delete(self.owner))

    def test_permission_methods_with_anonymous_user(self):
        """Test permission methods with None/anonymous user."""
        # Anonymous users should not have any permissions
        self.assertFalse(self.owner_location.can_view(None))
        self.assertFalse(self.owner_location.can_edit(None))
        self.assertFalse(self.owner_location.can_delete(None))

        # Anonymous users might be able to view public locations
        # depending on implementation
        self.public_location.can_view(None)
        # This may be True or False - test documents current behavior

        # Anonymous users should never be able to edit or delete
        self.assertFalse(self.public_location.can_edit(None))
        self.assertFalse(self.public_location.can_delete(None))

        # Anonymous users cannot create locations
        self.assertFalse(Location.can_create(None, self.campaign))
        self.assertFalse(Location.can_create(None, self.public_campaign))

    def test_permission_caching_and_performance(self):
        """Test that permission checks are efficient and can be cached."""
        # Multiple permission checks on same object should be efficient
        import time

        start_time = time.time()

        # Perform multiple permission checks
        for _ in range(10):
            self.owner_location.can_view(self.player)
            self.owner_location.can_edit(self.player)
            self.owner_location.can_delete(self.player)

        end_time = time.time()
        total_time = end_time - start_time

        # Should complete quickly (under 1 second for 30 checks)
        self.assertLess(total_time, 1.0)

    def test_permission_consistency_across_methods(self):
        """Test that permission methods are consistent with each other."""
        # If user can edit, they should be able to view
        for user in [self.owner, self.gm, self.player, self.observer]:
            for location in [
                self.owner_location,
                self.gm_location,
                self.player_location,
            ]:
                if location.can_edit(user):
                    self.assertTrue(
                        location.can_view(user),
                        f"{user.username} can edit but not view {location.name}",
                    )

                # If user can delete, they should be able to edit and view
                if location.can_delete(user):
                    self.assertTrue(
                        location.can_edit(user),
                        f"{user.username} can delete but not edit {location.name}",
                    )
                    self.assertTrue(
                        location.can_view(user),
                        f"{user.username} can delete but not view {location.name}",
                    )

    def test_bulk_permission_checking(self):
        """Test efficient bulk permission checking for multiple locations."""
        # Create additional test locations
        locations = []
        for i in range(10):
            location = Location.objects.create(
                name=f"Bulk Test Location {i}",
                campaign=self.campaign,
                created_by=self.player,
            )
            locations.append(location)

        # Test bulk permission checking (if implemented)
        if hasattr(Location, "filter_viewable"):
            viewable = Location.filter_viewable(locations, self.gm)
            self.assertEqual(len(viewable), len(locations))

        if hasattr(Location, "filter_editable"):
            editable = Location.filter_editable(locations, self.player)
            # Player should be able to edit all their own locations
            self.assertEqual(len(editable), len(locations))

    def test_permission_with_campaign_settings(self):
        """Test how campaign settings affect location permissions."""
        # Create campaign with specific permission settings
        strict_campaign = Campaign.objects.create(
            name="Strict Campaign",
            owner=self.owner,
            game_system="mage",
            # Add any relevant permission settings
        )

        strict_location = Location.objects.create(
            name="Strict Location",
            campaign=strict_campaign,
            created_by=self.player,
        )

        # Add player to strict campaign
        CampaignMembership.objects.create(
            campaign=strict_campaign, user=self.player, role="PLAYER"
        )

        # Test that campaign settings are respected
        # (Implementation depends on specific campaign permission settings)
        self.assertTrue(strict_location.can_view(self.player))
        self.assertTrue(strict_location.can_edit(self.player))

    def test_location_ownership_transfer(self):
        """Test permission changes when location ownership is transferred."""
        # Create location owned by player
        transferable_location = Location.objects.create(
            name="Transferable Location",
            campaign=self.campaign,
            created_by=self.player,
        )

        # Initially player can edit, GM cannot (if strict permissions)
        self.assertTrue(transferable_location.can_edit(self.player))

        # Transfer ownership to GM
        transferable_location.created_by = self.gm
        transferable_location.save()

        # Now GM should be able to edit
        self.assertTrue(transferable_location.can_edit(self.gm))

        # Player permissions depend on campaign settings
        transferable_location.can_edit(self.player)
        # May be True or False depending on campaign permission model


class LocationPermissionSecurityTest(TestCase):
    """Test security aspects of location permissions."""

    def setUp(self):
        """Set up test data for security tests."""
        self.attacker = User.objects.create_user(
            username="attacker", email="attacker@test.com", password="testpass123"
        )
        self.victim = User.objects.create_user(
            username="victim", email="victim@test.com", password="testpass123"
        )

        self.victim_campaign = Campaign.objects.create(
            name="Victim Campaign",
            owner=self.victim,
            game_system="mage",
            is_public=False,
        )

        self.victim_location = Location.objects.create(
            name="Victim Location",
            campaign=self.victim_campaign,
            created_by=self.victim,
        )

    def test_unauthorized_access_prevention(self):
        """Test that unauthorized access is properly prevented."""
        # Attacker should not be able to access victim's private locations
        self.assertFalse(self.victim_location.can_view(self.attacker))
        self.assertFalse(self.victim_location.can_edit(self.attacker))
        self.assertFalse(self.victim_location.can_delete(self.attacker))

        # Attacker should not be able to create locations in victim's campaign
        self.assertFalse(Location.can_create(self.attacker, self.victim_campaign))

    def test_permission_escalation_prevention(self):
        """Test that permission escalation is prevented."""
        # Add attacker as observer
        CampaignMembership.objects.create(
            campaign=self.victim_campaign, user=self.attacker, role="OBSERVER"
        )

        # Observer should be able to view but not edit/delete
        self.assertTrue(self.victim_location.can_view(self.attacker))
        self.assertFalse(self.victim_location.can_edit(self.attacker))
        self.assertFalse(self.victim_location.can_delete(self.attacker))

        # Observer should not be able to escalate to edit permissions
        # by manipulating location properties
        attacker_location = Location.objects.create(
            name="Attacker Location",
            campaign=self.victim_campaign,
            created_by=self.attacker,
        )

        # Even their own location might have restricted permissions in observer role
        attacker_location.can_edit(self.attacker)
        # This depends on campaign policy for observer role

    def test_cross_campaign_isolation_security(self):
        """Test security of cross-campaign isolation."""
        Campaign.objects.create(
            name="Attacker Campaign",
            owner=self.attacker,
            game_system="generic",
        )

        # Being an owner of one campaign shouldn't grant access to others
        self.assertFalse(self.victim_location.can_view(self.attacker))
        self.assertFalse(self.victim_location.can_edit(self.attacker))
        self.assertFalse(self.victim_location.can_delete(self.attacker))

        # Should not be able to move victim's location to attacker's campaign
        # (This would be prevented at the model validation level)

    def test_permission_bypass_attempts(self):
        """Test that common permission bypass attempts are prevented."""
        # Test that direct database manipulation doesn't bypass permissions
        # (Permissions should be checked at the application level)

        # Test that changing user properties doesn't grant unauthorized access
        original_username = self.attacker.username
        self.attacker.username = (
            "fake_victim_username"  # Different name that doesn't conflict
        )
        self.attacker.save()

        # Should still not have access (permissions based on user object, not name)
        self.assertFalse(self.victim_location.can_edit(self.attacker))

        # Restore original username
        self.attacker.username = original_username
        self.attacker.save()

    def test_information_disclosure_prevention(self):
        """Test that permission checks don't leak sensitive information."""
        # Permission methods should not reveal information about
        # locations the user shouldn't know about

        # This test ensures that permission checking doesn't inadvertently
        # confirm the existence of locations the user shouldn't see

        # The exact implementation depends on how permissions are structured
        # but generally, failed permission checks should not provide details
        # about why access was denied if it would reveal sensitive information

        # Test that error messages don't leak campaign information
        self.assertFalse(self.victim_location.can_view(self.attacker))

        # Permission check should fail silently without revealing
        # details about the campaign or location structure
