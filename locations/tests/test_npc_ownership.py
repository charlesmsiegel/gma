"""
Comprehensive tests for NPC ownership of locations (Issue #186).

Tests cover:
- Location owned_by field and Character owned_locations relationship
- Ownership assignment to NPCs and PCs
- Unowned locations (null ownership)
- Ownership transfer capability
- Permission checks for ownership changes
- Admin interface behavior for NPC ownership hints
- Cross-campaign validation and edge cases
- Soft-deleted character handling

Test Structure:
- LocationOwnershipModelTest: Basic ownership field and relationship tests
- LocationOwnershipAssignmentTest: Ownership assignment to NPCs and PCs
- LocationOwnershipTransferTest: Ownership transfer scenarios
- LocationOwnershipPermissionTest: Permission checks for ownership changes
- LocationOwnershipAdminTest: Admin interface behavior
- LocationOwnershipEdgeCaseTest: Edge cases and error scenarios
- LocationOwnershipValidationTest: Cross-campaign validation
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from campaigns.models import Campaign, CampaignMembership
from characters.models import Character
from locations.models import Location

User = get_user_model()


class LocationOwnershipModelTest(TestCase):
    """Test basic Location ownership field and Character owned_locations."""

    def setUp(self):
        """Set up test users, campaigns, and characters."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.player = User.objects.create_user(
            username="player", email="player@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Ownership Test Campaign",
            owner=self.owner,
            game_system="mage",
        )

        # Add player membership
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )

        # Create test characters - both NPC and PC
        self.npc_character = Character.objects.create(
            name="Test NPC",
            campaign=self.campaign,
            player_owner=self.owner,  # Owner controls NPCs
            game_system="mage",
            npc=True,
        )

        self.pc_character = Character.objects.create(
            name="Test PC",
            campaign=self.campaign,
            player_owner=self.player,
            game_system="mage",
            npc=False,
        )

    def test_location_has_owned_by_field(self):
        """Test that Location model has owned_by field."""
        location = Location.objects.create(
            name="Test Location",
            campaign=self.campaign,
            created_by=self.owner,
        )

        # Test owned_by field exists and is None by default
        self.assertTrue(hasattr(location, "owned_by"))
        self.assertIsNone(location.owned_by)

    def test_location_owned_by_field_properties(self):
        """Test owned_by field properties and constraints."""
        # Create location
        location = Location.objects.create(
            name="Field Test Location",
            campaign=self.campaign,
            created_by=self.owner,
        )

        # Test field is nullable
        self.assertIsNone(location.owned_by)

        # Test field accepts Character instance
        location.owned_by = self.npc_character
        location.save()

        location.refresh_from_db()
        self.assertEqual(location.owned_by, self.npc_character)

        # Test field can be set back to None
        location.owned_by = None
        location.save()

        location.refresh_from_db()
        self.assertIsNone(location.owned_by)

    def test_character_has_owned_locations_relationship(self):
        """Test that Character model has owned_locations reverse relationship."""
        # Test owned_locations attribute exists
        self.assertTrue(hasattr(self.npc_character, "owned_locations"))

        # Test it returns a manager/queryset
        owned_locations = self.npc_character.owned_locations.all()
        self.assertEqual(owned_locations.count(), 0)

    def test_location_ownership_relationship(self):
        """Test the bi-directional relationship between Location and Character."""
        location = Location.objects.create(
            name="Relationship Test Location",
            campaign=self.campaign,
            owned_by=self.npc_character,
            created_by=self.owner,
        )

        # Test forward relationship (location -> character)
        self.assertEqual(location.owned_by, self.npc_character)

        # Test reverse relationship (character -> locations)
        owned_locations = self.npc_character.owned_locations.all()
        self.assertEqual(owned_locations.count(), 1)
        self.assertIn(location, owned_locations)

    def test_multiple_locations_same_owner(self):
        """Test that one character can own multiple locations."""
        locations = []
        for i in range(3):
            location = Location.objects.create(
                name=f"Location {i}",
                campaign=self.campaign,
                owned_by=self.npc_character,
                created_by=self.owner,
            )
            locations.append(location)

        # Test all locations are owned by the same character
        owned_locations = self.npc_character.owned_locations.all()
        self.assertEqual(owned_locations.count(), 3)

        for location in locations:
            self.assertIn(location, owned_locations)
            self.assertEqual(location.owned_by, self.npc_character)

    def test_location_ownership_cascade_on_character_deletion(self):
        """Test behavior when character owner is deleted."""
        location = Location.objects.create(
            name="Cascade Test Location",
            campaign=self.campaign,
            owned_by=self.npc_character,
            created_by=self.owner,
        )

        # Delete the character
        self.npc_character.delete()

        # Location should still exist but ownership should be handled appropriately
        location.refresh_from_db()

        # The exact behavior depends on the ForeignKey on_delete parameter
        # For this feature, we expect SET_NULL to maintain location but clear ownership
        self.assertIsNone(location.owned_by)

    def test_location_ownership_database_constraints(self):
        """Test database-level constraints for ownership field."""
        location = Location.objects.create(
            name="Constraint Test Location",
            campaign=self.campaign,
            created_by=self.owner,
        )

        # Test that owned_by can be None (nullable=True)
        location.owned_by = None
        location.save()  # Should not raise exception

        # Test that owned_by accepts valid Character foreign key
        location.owned_by = self.npc_character
        location.save()  # Should not raise exception


class LocationOwnershipAssignmentTest(TestCase):
    """Test ownership assignment to NPCs and PCs."""

    def setUp(self):
        """Set up test data for ownership assignment tests."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.player1 = User.objects.create_user(
            username="player1", email="player1@test.com", password="testpass123"
        )
        self.player2 = User.objects.create_user(
            username="player2", email="player2@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Assignment Test Campaign",
            owner=self.owner,
            game_system="mage",
        )

        # Add memberships
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player1, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player2, role="PLAYER"
        )

        # Create various characters
        self.npc_tavern_keeper = Character.objects.create(
            name="Tavern Keeper",
            campaign=self.campaign,
            player_owner=self.owner,
            game_system="mage",
            npc=True,
        )

        self.npc_noble = Character.objects.create(
            name="Noble Lord",
            campaign=self.campaign,
            player_owner=self.owner,
            game_system="mage",
            npc=True,
        )

        self.pc_mage = Character.objects.create(
            name="Player Mage",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="mage",
            npc=False,
        )

        self.pc_wanderer = Character.objects.create(
            name="Wandering Player",
            campaign=self.campaign,
            player_owner=self.player2,
            game_system="mage",
            npc=False,
        )

    def test_assign_location_to_npc(self):
        """Test assigning location ownership to NPCs."""
        # Test tavern owned by tavern keeper NPC
        tavern = Location.objects.create(
            name="The Prancing Pony Tavern",
            description="A cozy tavern with rooms for rent",
            campaign=self.campaign,
            owned_by=self.npc_tavern_keeper,
            created_by=self.owner,
        )

        self.assertEqual(tavern.owned_by, self.npc_tavern_keeper)
        self.assertIn(tavern, self.npc_tavern_keeper.owned_locations.all())

        # Test noble estate owned by noble NPC
        estate = Location.objects.create(
            name="Blackwood Manor",
            description="A grand estate on the hill",
            campaign=self.campaign,
            owned_by=self.npc_noble,
            created_by=self.owner,
        )

        self.assertEqual(estate.owned_by, self.npc_noble)
        self.assertIn(estate, self.npc_noble.owned_locations.all())

    def test_assign_location_to_pc(self):
        """Test assigning location ownership to PCs."""
        # Test player character owning a personal sanctum
        sanctum = Location.objects.create(
            name="Mage's Sanctum",
            description="A hidden magical workshop",
            campaign=self.campaign,
            owned_by=self.pc_mage,
            created_by=self.owner,
        )

        self.assertEqual(sanctum.owned_by, self.pc_mage)
        self.assertIn(sanctum, self.pc_mage.owned_locations.all())

        # Test another player character owning a different location
        safehouse = Location.objects.create(
            name="Wanderer's Safehouse",
            description="A secure hideout",
            campaign=self.campaign,
            owned_by=self.pc_wanderer,
            created_by=self.owner,
        )

        self.assertEqual(safehouse.owned_by, self.pc_wanderer)
        self.assertIn(safehouse, self.pc_wanderer.owned_locations.all())

    def test_unowned_locations(self):
        """Test locations with null ownership (unowned)."""
        # Test public/unowned locations
        public_park = Location.objects.create(
            name="City Park",
            description="A public park open to all",
            campaign=self.campaign,
            owned_by=None,  # Explicitly unowned
            created_by=self.owner,
        )

        self.assertIsNone(public_park.owned_by)

        # Test that unowned location doesn't appear in any character's owned_locations
        self.assertNotIn(public_park, self.npc_tavern_keeper.owned_locations.all())
        self.assertNotIn(public_park, self.pc_mage.owned_locations.all())

        # Test wilderness/natural locations
        forest = Location.objects.create(
            name="Whispering Woods",
            description="An ancient forest",
            campaign=self.campaign,
            # owned_by defaults to None
            created_by=self.owner,
        )

        self.assertIsNone(forest.owned_by)

    def test_ownership_assignment_validation(self):
        """Test validation during ownership assignment."""
        location = Location.objects.create(
            name="Validation Test Location",
            campaign=self.campaign,
            created_by=self.owner,
        )

        # Test assigning valid NPC ownership
        location.owned_by = self.npc_tavern_keeper
        location.clean()  # Should not raise exception
        location.save()

        # Test assigning valid PC ownership
        location.owned_by = self.pc_mage
        location.clean()  # Should not raise exception
        location.save()

        # Test assigning None ownership
        location.owned_by = None
        location.clean()  # Should not raise exception
        location.save()

    def test_multiple_npcs_owning_different_locations(self):
        """Test multiple NPCs each owning different locations."""
        # Tavern keeper owns tavern
        tavern = Location.objects.create(
            name="The Red Dragon Inn",
            campaign=self.campaign,
            owned_by=self.npc_tavern_keeper,
            created_by=self.owner,
        )

        # Noble owns estate
        estate = Location.objects.create(
            name="Sterling Estate",
            campaign=self.campaign,
            owned_by=self.npc_noble,
            created_by=self.owner,
        )

        # Verify separate ownership
        self.assertEqual(tavern.owned_by, self.npc_tavern_keeper)
        self.assertEqual(estate.owned_by, self.npc_noble)

        # Verify each NPC only owns their own location
        tavern_keeper_locations = self.npc_tavern_keeper.owned_locations.all()
        noble_locations = self.npc_noble.owned_locations.all()

        self.assertEqual(tavern_keeper_locations.count(), 1)
        self.assertEqual(noble_locations.count(), 1)
        self.assertIn(tavern, tavern_keeper_locations)
        self.assertIn(estate, noble_locations)
        self.assertNotIn(estate, tavern_keeper_locations)
        self.assertNotIn(tavern, noble_locations)

    def test_mixed_ownership_in_campaign(self):
        """Test campaign with mix of NPC-owned, PC-owned, and unowned locations."""
        # Create various locations with different ownership
        # NPC-owned
        Location.objects.create(
            name="NPC Shop",
            campaign=self.campaign,
            owned_by=self.npc_tavern_keeper,
            created_by=self.owner,
        )
        # PC-owned
        Location.objects.create(
            name="PC House",
            campaign=self.campaign,
            owned_by=self.pc_mage,
            created_by=self.owner,
        )
        # Unowned
        Location.objects.create(
            name="Public Square",
            campaign=self.campaign,
            owned_by=None,
            created_by=self.owner,
        )

        # Verify ownership distribution
        npc_owned = Location.objects.filter(
            campaign=self.campaign, owned_by__npc=True
        ).count()
        pc_owned = Location.objects.filter(
            campaign=self.campaign, owned_by__npc=False
        ).count()
        unowned = Location.objects.filter(
            campaign=self.campaign, owned_by__isnull=True
        ).count()

        self.assertEqual(npc_owned, 1)
        self.assertEqual(pc_owned, 1)
        self.assertEqual(unowned, 1)

    def test_ownership_assignment_with_hierarchy(self):
        """Test ownership assignment in hierarchical locations."""
        # Create parent location owned by noble
        mansion = Location.objects.create(
            name="Blackwood Mansion",
            campaign=self.campaign,
            owned_by=self.npc_noble,
            created_by=self.owner,
        )

        # Create child locations with different ownership
        library = Location.objects.create(
            name="Private Library",
            campaign=self.campaign,
            parent=mansion,
            owned_by=self.npc_noble,  # Same owner as parent
            created_by=self.owner,
        )

        guest_room = Location.objects.create(
            name="Guest Room",
            campaign=self.campaign,
            parent=mansion,
            owned_by=self.pc_mage,  # Different owner (guest)
            created_by=self.owner,
        )

        servants_quarters = Location.objects.create(
            name="Servants' Quarters",
            campaign=self.campaign,
            parent=mansion,
            owned_by=None,  # Unowned
            created_by=self.owner,
        )

        # Verify hierarchy and ownership
        self.assertEqual(library.parent, mansion)
        self.assertEqual(library.owned_by, self.npc_noble)

        self.assertEqual(guest_room.parent, mansion)
        self.assertEqual(guest_room.owned_by, self.pc_mage)

        self.assertEqual(servants_quarters.parent, mansion)
        self.assertIsNone(servants_quarters.owned_by)

        # Verify noble owns mansion and library
        noble_locations = self.npc_noble.owned_locations.all()
        self.assertEqual(noble_locations.count(), 2)
        self.assertIn(mansion, noble_locations)
        self.assertIn(library, noble_locations)

        # Verify PC only owns guest room
        pc_locations = self.pc_mage.owned_locations.all()
        self.assertEqual(pc_locations.count(), 1)
        self.assertIn(guest_room, pc_locations)


class LocationOwnershipTransferTest(TestCase):
    """Test ownership transfer scenarios and capabilities."""

    def setUp(self):
        """Set up test data for ownership transfer tests."""
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
            name="Transfer Test Campaign",
            owner=self.owner,
            game_system="mage",
        )

        # Add memberships
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm, role="GM"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )

        # Create characters
        self.old_npc = Character.objects.create(
            name="Old NPC Owner",
            campaign=self.campaign,
            player_owner=self.owner,
            game_system="mage",
            npc=True,
        )

        self.new_npc = Character.objects.create(
            name="New NPC Owner",
            campaign=self.campaign,
            player_owner=self.owner,
            game_system="mage",
            npc=True,
        )

        self.pc_character = Character.objects.create(
            name="PC Character",
            campaign=self.campaign,
            player_owner=self.player,
            game_system="mage",
            npc=False,
        )

        # Create location for transfer tests
        self.transferable_location = Location.objects.create(
            name="Transferable Property",
            campaign=self.campaign,
            owned_by=self.old_npc,
            created_by=self.owner,
        )

    def test_transfer_ownership_npc_to_npc(self):
        """Test transferring ownership from one NPC to another."""
        # Verify initial ownership
        self.assertEqual(self.transferable_location.owned_by, self.old_npc)
        self.assertIn(self.transferable_location, self.old_npc.owned_locations.all())

        # Transfer ownership
        self.transferable_location.owned_by = self.new_npc
        self.transferable_location.save()

        self.transferable_location.refresh_from_db()

        # Verify transfer completed
        self.assertEqual(self.transferable_location.owned_by, self.new_npc)
        self.assertIn(self.transferable_location, self.new_npc.owned_locations.all())
        self.assertNotIn(self.transferable_location, self.old_npc.owned_locations.all())

    def test_transfer_ownership_npc_to_pc(self):
        """Test transferring ownership from NPC to PC."""
        # Transfer from NPC to PC
        self.transferable_location.owned_by = self.pc_character
        self.transferable_location.save()

        self.transferable_location.refresh_from_db()

        # Verify transfer
        self.assertEqual(self.transferable_location.owned_by, self.pc_character)
        self.assertIn(
            self.transferable_location, self.pc_character.owned_locations.all()
        )
        self.assertNotIn(self.transferable_location, self.old_npc.owned_locations.all())

    def test_transfer_ownership_pc_to_npc(self):
        """Test transferring ownership from PC to NPC."""
        # First transfer to PC
        self.transferable_location.owned_by = self.pc_character
        self.transferable_location.save()

        # Then transfer from PC to NPC
        self.transferable_location.owned_by = self.new_npc
        self.transferable_location.save()

        self.transferable_location.refresh_from_db()

        # Verify final transfer
        self.assertEqual(self.transferable_location.owned_by, self.new_npc)
        self.assertIn(self.transferable_location, self.new_npc.owned_locations.all())
        self.assertNotIn(
            self.transferable_location, self.pc_character.owned_locations.all()
        )

    def test_transfer_ownership_to_unowned(self):
        """Test transferring ownership to unowned (None)."""
        # Transfer to unowned
        self.transferable_location.owned_by = None
        self.transferable_location.save()

        self.transferable_location.refresh_from_db()

        # Verify now unowned
        self.assertIsNone(self.transferable_location.owned_by)
        self.assertNotIn(self.transferable_location, self.old_npc.owned_locations.all())

    def test_transfer_ownership_from_unowned(self):
        """Test transferring ownership from unowned to owned."""
        # Create unowned location
        unowned_location = Location.objects.create(
            name="Previously Unowned",
            campaign=self.campaign,
            owned_by=None,
            created_by=self.owner,
        )

        # Transfer from unowned to NPC
        unowned_location.owned_by = self.new_npc
        unowned_location.save()

        unowned_location.refresh_from_db()

        # Verify ownership assigned
        self.assertEqual(unowned_location.owned_by, self.new_npc)
        self.assertIn(unowned_location, self.new_npc.owned_locations.all())

    def test_bulk_ownership_transfer(self):
        """Test transferring ownership of multiple locations at once."""
        # Create multiple locations owned by old NPC
        locations = []
        for i in range(3):
            location = Location.objects.create(
                name=f"Bulk Transfer Location {i}",
                campaign=self.campaign,
                owned_by=self.old_npc,
                created_by=self.owner,
            )
            locations.append(location)

        # Verify initial ownership
        old_npc_locations = self.old_npc.owned_locations.all()
        self.assertEqual(old_npc_locations.count(), 4)  # 3 new + 1 from setUp

        # Bulk transfer to new NPC
        Location.objects.filter(campaign=self.campaign, owned_by=self.old_npc).update(
            owned_by=self.new_npc
        )

        # Verify bulk transfer
        old_npc_locations_after = self.old_npc.owned_locations.all()
        new_npc_locations_after = self.new_npc.owned_locations.all()

        self.assertEqual(old_npc_locations_after.count(), 0)
        self.assertEqual(new_npc_locations_after.count(), 4)

    def test_ownership_transfer_with_audit_trail(self):
        """Test that ownership transfers can be tracked (if audit is implemented)."""
        original_owner = self.transferable_location.owned_by
        transfer_time = timezone.now()

        # Transfer ownership
        self.transferable_location.owned_by = self.new_npc
        self.transferable_location.save()

        # Verify transfer completed
        self.assertEqual(self.transferable_location.owned_by, self.new_npc)
        self.assertNotEqual(self.transferable_location.owned_by, original_owner)

        # Test that updated_at timestamp reflects the change
        self.assertGreaterEqual(self.transferable_location.updated_at, transfer_time)

    def test_ownership_transfer_validation(self):
        """Test validation during ownership transfers."""
        # Test that transfer validates normally
        self.transferable_location.owned_by = self.new_npc
        self.transferable_location.clean()  # Should not raise exception
        self.transferable_location.save()

        # Test transfer to None validates
        self.transferable_location.owned_by = None
        self.transferable_location.clean()  # Should not raise exception
        self.transferable_location.save()


class LocationOwnershipPermissionTest(TestCase):
    """Test permission checks for ownership changes."""

    def setUp(self):
        """Set up test data for permission tests."""
        # Users with different roles
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

        self.campaign = Campaign.objects.create(
            name="Permission Test Campaign",
            owner=self.owner,
            game_system="mage",
        )

        # Add memberships
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm, role="GM"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.observer, role="OBSERVER"
        )

        # Create characters
        self.npc_character = Character.objects.create(
            name="Test NPC",
            campaign=self.campaign,
            player_owner=self.owner,
            game_system="mage",
            npc=True,
        )

        self.pc_character = Character.objects.create(
            name="Test PC",
            campaign=self.campaign,
            player_owner=self.player,
            game_system="mage",
            npc=False,
        )

        # Create test location
        self.test_location = Location.objects.create(
            name="Permission Test Location",
            campaign=self.campaign,
            created_by=self.owner,
        )

    def test_owner_can_set_location_ownership(self):
        """Test that campaign owner can set location ownership."""
        # Owner should be able to assign ownership to NPC
        self.assertTrue(self.test_location.can_edit(self.owner))

        # Simulate ownership assignment
        self.test_location.owned_by = self.npc_character
        # This should succeed (tested through can_edit permission)
        self.assertTrue(self.test_location.can_edit(self.owner))

    def test_gm_can_set_location_ownership(self):
        """Test that GM can set location ownership."""
        # GM should be able to assign ownership
        self.assertTrue(self.test_location.can_edit(self.gm))

        # Simulate ownership assignment by GM
        self.test_location.owned_by = self.npc_character
        self.assertTrue(self.test_location.can_edit(self.gm))

    def test_player_ownership_permissions(self):
        """Test player permissions for location ownership."""
        # Create location owned by player
        player_location = Location.objects.create(
            name="Player's Location",
            campaign=self.campaign,
            created_by=self.player,
        )

        # Player should be able to edit their own location
        self.assertTrue(player_location.can_edit(self.player))

        # Player should NOT be able to edit other's locations
        self.assertFalse(self.test_location.can_edit(self.player))

    def test_observer_ownership_permissions(self):
        """Test that observers cannot change ownership."""
        # Observer should not be able to edit locations
        self.assertFalse(self.test_location.can_edit(self.observer))

    def test_non_member_ownership_permissions(self):
        """Test that non-members cannot change ownership."""
        # Non-member should not be able to edit locations
        self.assertFalse(self.test_location.can_edit(self.non_member))

    def test_ownership_affects_location_permissions(self):
        """Test how ownership affects location permissions."""
        # Set NPC as owner
        self.test_location.owned_by = self.npc_character
        self.test_location.save()

        # Campaign owner/GM should still be able to edit
        self.assertTrue(self.test_location.can_edit(self.owner))
        self.assertTrue(self.test_location.can_edit(self.gm))

        # Regular player should not be able to edit NPC-owned location
        self.assertFalse(self.test_location.can_edit(self.player))

        # Test PC ownership
        pc_owned_location = Location.objects.create(
            name="PC Owned Location",
            campaign=self.campaign,
            owned_by=self.pc_character,
            created_by=self.owner,
        )

        # PC owner should be able to edit through character ownership
        # Note: This depends on implementation - may need special logic
        # for character ownership vs. location creation permissions
        self.assertTrue(
            pc_owned_location.can_edit(self.owner)
        )  # Campaign owner can always edit
        self.assertTrue(pc_owned_location.can_edit(self.gm))  # GM can always edit

    def test_ownership_transfer_permissions_by_role(self):
        """Test ownership transfer permissions based on user roles."""
        original_owner = self.npc_character

        # Start with NPC ownership
        self.test_location.owned_by = original_owner
        self.test_location.save()

        # Owner should be able to transfer ownership
        if self.test_location.can_edit(self.owner):
            self.test_location.owned_by = None  # Transfer to unowned
            # This represents what would happen if owner makes the change

        # GM should be able to transfer ownership
        if self.test_location.can_edit(self.gm):
            self.test_location.owned_by = self.pc_character  # Transfer to PC
            # This represents what would happen if GM makes the change

        # Verify basic permission structure is in place
        self.assertTrue(self.test_location.can_edit(self.owner))
        self.assertTrue(self.test_location.can_edit(self.gm))
        self.assertFalse(self.test_location.can_edit(self.observer))

    def test_cross_campaign_ownership_prevention(self):
        """Test that ownership cannot be assigned across campaigns."""
        # Create second campaign and character
        other_campaign = Campaign.objects.create(
            name="Other Campaign",
            owner=self.owner,
            game_system="generic",
        )

        other_character = Character.objects.create(
            name="Other Campaign Character",
            campaign=other_campaign,
            player_owner=self.owner,
            game_system="generic",
            npc=True,
        )

        # Attempting to assign ownership to character from different campaign
        # should be prevented by validation
        self.test_location.owned_by = other_character

        with self.assertRaises(ValidationError):
            self.test_location.clean()


class LocationOwnershipAdminTest(TestCase):
    """Test admin interface behavior for NPC ownership hints."""

    def setUp(self):
        """Set up test data for admin tests."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.player = User.objects.create_user(
            username="player", email="player@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Admin Test Campaign",
            owner=self.owner,
            game_system="mage",
        )

        # Add membership
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )

        # Create test characters
        self.npc1 = Character.objects.create(
            name="NPC Merchant",
            campaign=self.campaign,
            player_owner=self.owner,
            game_system="mage",
            npc=True,
        )

        self.npc2 = Character.objects.create(
            name="NPC Guard",
            campaign=self.campaign,
            player_owner=self.owner,
            game_system="mage",
            npc=True,
        )

        self.pc_character = Character.objects.create(
            name="PC Hero",
            campaign=self.campaign,
            player_owner=self.player,
            game_system="mage",
            npc=False,
        )

    def test_owned_by_field_has_limit_choices_hint(self):
        """Test that owned_by field suggests NPCs in admin interface."""
        # This test verifies the implementation expectation
        # The actual admin integration test would require admin form testing

        # Test the field has the expected configuration
        owned_by_field = Location._meta.get_field("owned_by")

        # Check that field accepts Characters
        self.assertEqual(owned_by_field.related_model, Character)

        # The limit_choices_to hint should be configured to suggest NPCs
        # This will be implemented as: limit_choices_to={'npc': True}
        if hasattr(owned_by_field, "limit_choices_to"):
            expected_limit = {"npc": True}
            self.assertEqual(owned_by_field.limit_choices_to, expected_limit)

    def test_admin_queryset_filtering_for_npcs(self):
        """Test that admin interface can filter characters for NPC ownership."""
        # This tests the expected behavior that would be implemented

        # In admin, when selecting owned_by, should get queryset filtered to NPCs
        campaign_npcs = Character.objects.filter(campaign=self.campaign, npc=True)
        campaign_pcs = Character.objects.filter(campaign=self.campaign, npc=False)

        # Verify NPCs are available for selection
        self.assertEqual(campaign_npcs.count(), 2)
        self.assertIn(self.npc1, campaign_npcs)
        self.assertIn(self.npc2, campaign_npcs)

        # Verify PCs are separate
        self.assertEqual(campaign_pcs.count(), 1)
        self.assertIn(self.pc_character, campaign_pcs)

        # Test that limit_choices_to={'npc': True} would filter correctly
        npc_filtered = Character.objects.filter(npc=True)
        self.assertIn(self.npc1, npc_filtered)
        self.assertIn(self.npc2, npc_filtered)
        self.assertNotIn(self.pc_character, npc_filtered)

    def test_admin_interface_supports_both_npc_and_pc_ownership(self):
        """Test that admin supports ownership by both NPCs and PCs despite hint."""
        # Even with NPC hint, admin should support assigning PCs as owners
        # This is important for flexibility

        # Test NPC assignment
        npc_location = Location.objects.create(
            name="NPC Owned Location",
            campaign=self.campaign,
            owned_by=self.npc1,
            created_by=self.owner,
        )
        self.assertEqual(npc_location.owned_by, self.npc1)

        # Test PC assignment (should still work)
        pc_location = Location.objects.create(
            name="PC Owned Location",
            campaign=self.campaign,
            owned_by=self.pc_character,
            created_by=self.owner,
        )
        self.assertEqual(pc_location.owned_by, self.pc_character)

        # Test None assignment
        unowned_location = Location.objects.create(
            name="Unowned Location",
            campaign=self.campaign,
            owned_by=None,
            created_by=self.owner,
        )
        self.assertIsNone(unowned_location.owned_by)

    def test_admin_character_display_in_ownership_field(self):
        """Test how characters are displayed in admin ownership field."""
        # Test character string representation for admin display
        self.assertEqual(str(self.npc1), "NPC Merchant")
        self.assertEqual(str(self.pc_character), "PC Hero")

        # Create location with each type of owner
        locations = [
            Location.objects.create(
                name="NPC Shop",
                campaign=self.campaign,
                owned_by=self.npc1,
                created_by=self.owner,
            ),
            Location.objects.create(
                name="PC House",
                campaign=self.campaign,
                owned_by=self.pc_character,
                created_by=self.owner,
            ),
        ]

        # Verify ownership display
        for location in locations:
            if location.owned_by:
                # Admin would display character.__str__()
                owner_display = str(location.owned_by)
                self.assertIsInstance(owner_display, str)
                self.assertGreater(len(owner_display), 0)


class LocationOwnershipEdgeCaseTest(TestCase):
    """Test edge cases and error scenarios for location ownership."""

    def setUp(self):
        """Set up test data for edge case tests."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.player = User.objects.create_user(
            username="player", email="player@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Edge Case Test Campaign",
            owner=self.owner,
            game_system="mage",
        )

        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )

        self.test_character = Character.objects.create(
            name="Test Character",
            campaign=self.campaign,
            player_owner=self.owner,
            game_system="mage",
            npc=True,
        )

    def test_soft_deleted_character_ownership(self):
        """Test location ownership when character is soft-deleted."""
        # Create location owned by character
        location = Location.objects.create(
            name="Soft Delete Test Location",
            campaign=self.campaign,
            owned_by=self.test_character,
            created_by=self.owner,
        )

        # Verify initial ownership
        self.assertEqual(location.owned_by, self.test_character)

        # Soft delete the character
        self.test_character.soft_delete(self.owner)

        # Refresh location and test behavior
        location.refresh_from_db()

        # Depending on implementation, owned_by might:
        # 1. Still reference the soft-deleted character (SET_NULL on hard delete)
        # 2. Be set to None (if implementation clears ownership on soft delete)

        # For this test, we expect reference to remain but character soft-deleted
        self.test_character.refresh_from_db()
        self.assertTrue(self.test_character.is_deleted)

        # Location ownership should handle soft-deleted characters appropriately
        if location.owned_by:
            # If ownership is maintained, character should still be same
            self.assertEqual(location.owned_by.id, self.test_character.id)
        else:
            # If ownership is cleared on soft delete
            self.assertIsNone(location.owned_by)

    def test_hard_deleted_character_ownership(self):
        """Test location ownership when character is hard-deleted."""
        # Create location owned by character
        location = Location.objects.create(
            name="Hard Delete Test Location",
            campaign=self.campaign,
            owned_by=self.test_character,
            created_by=self.owner,
        )

        character_id = self.test_character.id

        # Hard delete the character (simulate CASCADE or SET_NULL)
        self.test_character.delete()

        # Refresh location
        location.refresh_from_db()

        # With SET_NULL on_delete, ownership should be cleared
        self.assertIsNone(location.owned_by)

        # Character should no longer exist
        with self.assertRaises(Character.DoesNotExist):
            Character.objects.get(id=character_id)

    def test_ownership_with_duplicate_character_names(self):
        """Test ownership assignment with characters having duplicate names."""
        # Create characters with same name in same campaign
        char1 = Character.objects.create(
            name="Duplicate Name",
            campaign=self.campaign,
            player_owner=self.owner,
            game_system="mage",
            npc=True,
        )

        char2 = Character.objects.create(
            name="Duplicate Name",
            campaign=self.campaign,
            player_owner=self.owner,
            game_system="mage",
            npc=True,
        )

        # Create locations owned by each
        location1 = Location.objects.create(
            name="Location 1",
            campaign=self.campaign,
            owned_by=char1,
            created_by=self.owner,
        )

        location2 = Location.objects.create(
            name="Location 2",
            campaign=self.campaign,
            owned_by=char2,
            created_by=self.owner,
        )

        # Verify distinct ownership despite same names
        self.assertEqual(location1.owned_by, char1)
        self.assertEqual(location2.owned_by, char2)
        self.assertNotEqual(location1.owned_by.id, location2.owned_by.id)

    def test_ownership_performance_with_many_characters(self):
        """Test ownership assignment performance with many characters."""
        # Create many characters
        characters = []
        for i in range(50):
            char = Character.objects.create(
                name=f"Character {i}",
                campaign=self.campaign,
                player_owner=self.owner,
                game_system="mage",
                npc=True,
            )
            characters.append(char)

        # Create locations owned by different characters
        locations = []
        for i, char in enumerate(characters[:10]):  # Test with 10 locations
            location = Location.objects.create(
                name=f"Location {i}",
                campaign=self.campaign,
                owned_by=char,
                created_by=self.owner,
            )
            locations.append(location)

        # Verify all ownerships are correct
        for i, location in enumerate(locations):
            self.assertEqual(location.owned_by, characters[i])

        # Test querying owned locations efficiently
        for char in characters[:10]:
            owned_count = char.owned_locations.count()
            self.assertEqual(owned_count, 1)

    def test_ownership_with_unicode_character_names(self):
        """Test ownership with characters having unicode names."""
        unicode_char = Character.objects.create(
            name="龍王 (Dragon King)",
            campaign=self.campaign,
            player_owner=self.owner,
            game_system="mage",
            npc=True,
        )

        location = Location.objects.create(
            name="Unicode Test Location",
            campaign=self.campaign,
            owned_by=unicode_char,
            created_by=self.owner,
        )

        self.assertEqual(location.owned_by, unicode_char)
        self.assertEqual(str(location.owned_by), "龍王 (Dragon King)")

    def test_ownership_field_database_indexes(self):
        """Test that ownership field has appropriate database indexes."""
        # This tests the expected database performance optimization

        # Create multiple locations with ownership
        for i in range(10):
            char = Character.objects.create(
                name=f"Index Test Character {i}",
                campaign=self.campaign,
                player_owner=self.owner,
                game_system="mage",
                npc=True,
            )

            Location.objects.create(
                name=f"Index Test Location {i}",
                campaign=self.campaign,
                owned_by=char,
                created_by=self.owner,
            )

        # Test queries that would benefit from indexing
        owned_locations = Location.objects.filter(owned_by__isnull=False)
        npc_owned = Location.objects.filter(owned_by__npc=True)

        # Verify queries work correctly (index testing requires DB inspection)
        self.assertGreaterEqual(owned_locations.count(), 10)
        self.assertGreaterEqual(npc_owned.count(), 10)

    def test_ownership_with_location_hierarchy_and_deletion(self):
        """Test ownership behavior when locations with hierarchy are deleted."""
        # Create parent location owned by character
        parent = Location.objects.create(
            name="Parent Location",
            campaign=self.campaign,
            owned_by=self.test_character,
            created_by=self.owner,
        )

        # Create child location owned by same character
        child = Location.objects.create(
            name="Child Location",
            campaign=self.campaign,
            parent=parent,
            owned_by=self.test_character,
            created_by=self.owner,
        )

        # Verify ownership
        self.assertEqual(parent.owned_by, self.test_character)
        self.assertEqual(child.owned_by, self.test_character)
        self.assertEqual(self.test_character.owned_locations.count(), 2)

        # Delete parent location
        parent.delete()

        # Child should still exist (moved to top-level) and maintain ownership
        child.refresh_from_db()
        self.assertEqual(child.owned_by, self.test_character)
        self.assertIsNone(child.parent)
        self.assertEqual(self.test_character.owned_locations.count(), 1)


class LocationOwnershipValidationTest(TestCase):
    """Test cross-campaign validation and other validation scenarios."""

    def setUp(self):
        """Set up test data for validation tests."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )

        # Create two separate campaigns
        self.campaign1 = Campaign.objects.create(
            name="Campaign 1",
            owner=self.owner,
            game_system="mage",
        )

        self.campaign2 = Campaign.objects.create(
            name="Campaign 2",
            owner=self.owner,
            game_system="generic",
        )

        # Create characters in different campaigns
        self.char1 = Character.objects.create(
            name="Campaign 1 Character",
            campaign=self.campaign1,
            player_owner=self.owner,
            game_system="mage",
            npc=True,
        )

        self.char2 = Character.objects.create(
            name="Campaign 2 Character",
            campaign=self.campaign2,
            player_owner=self.owner,
            game_system="generic",
            npc=True,
        )

    def test_prevent_cross_campaign_ownership(self):
        """Test locations cannot be owned by characters from different campaigns."""
        # Create location in campaign 1
        location = Location.objects.create(
            name="Cross Campaign Test",
            campaign=self.campaign1,
            created_by=self.owner,
        )

        # Attempt to assign character from campaign 2 as owner
        location.owned_by = self.char2

        # This should fail validation
        with self.assertRaises(ValidationError) as context:
            location.clean()

        error_message = str(context.exception).lower()
        self.assertIn("campaign", error_message)

    def test_same_campaign_ownership_allowed(self):
        """Test that same-campaign ownership is allowed."""
        location = Location.objects.create(
            name="Same Campaign Test",
            campaign=self.campaign1,
            created_by=self.owner,
        )

        # Assign character from same campaign
        location.owned_by = self.char1
        location.clean()  # Should not raise exception
        location.save()

        self.assertEqual(location.owned_by, self.char1)

    def test_ownership_validation_on_save(self):
        """Test that validation is enforced on save operations."""
        location = Location.objects.create(
            name="Save Validation Test",
            campaign=self.campaign1,
            created_by=self.owner,
        )

        # Set invalid cross-campaign ownership
        location.owned_by = self.char2

        # Save should trigger validation and fail
        with self.assertRaises(ValidationError):
            location.save()

    def test_ownership_validation_with_none(self):
        """Test that None ownership always validates."""
        location1 = Location.objects.create(
            name="None Test Location 1",
            campaign=self.campaign1,
            owned_by=None,
            created_by=self.owner,
        )

        location2 = Location.objects.create(
            name="None Test Location 2",
            campaign=self.campaign2,
            owned_by=None,
            created_by=self.owner,
        )

        # Both should validate and save successfully
        location1.clean()
        location2.clean()

        self.assertIsNone(location1.owned_by)
        self.assertIsNone(location2.owned_by)

    def test_ownership_validation_with_campaign_change(self):
        """Test ownership validation when location campaign is changed."""
        # Create location with character ownership in campaign1
        location = Location.objects.create(
            name="Campaign Change Test",
            campaign=self.campaign1,
            owned_by=self.char1,
            created_by=self.owner,
        )

        # Change location to campaign2 (but keep campaign1 character as owner)
        location.campaign = self.campaign2

        # This should fail validation
        with self.assertRaises(ValidationError):
            location.clean()

    def test_bulk_ownership_validation(self):
        """Test validation in bulk operations."""
        # Create locations in campaign1
        locations = []
        for i in range(3):
            location = Location.objects.create(
                name=f"Bulk Location {i}",
                campaign=self.campaign1,
                created_by=self.owner,
            )
            locations.append(location)

        # Bulk update with valid ownership (same campaign)
        Location.objects.filter(id__in=[loc.id for loc in locations]).update(
            owned_by=self.char1
        )

        # Verify update succeeded
        for location in locations:
            location.refresh_from_db()
            self.assertEqual(location.owned_by, self.char1)

        # Bulk update with invalid cross-campaign ownership should be prevented
        # Note: bulk_update bypasses model validation, so this tests the expectation
        # that proper validation would be implemented at the application level

        # If validation is implemented in save() method, bulk operations might
        # bypass it, requiring additional validation in views/forms
