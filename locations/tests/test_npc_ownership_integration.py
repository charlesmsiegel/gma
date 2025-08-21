"""
Integration tests for NPC ownership of locations (Issue #186).

Tests cover the complete feature integration including:
- Character model integration with owned_locations relationship
- Location model integration with owned_by field
- Database integrity and performance with ownership relationships
- Real-world scenarios and use cases
- Migration compatibility and data consistency

Test Structure:
- LocationOwnershipIntegrationTest: Complete feature integration
- LocationOwnershipPerformanceTest: Performance and scalability
- LocationOwnershipScenarioTest: Real-world use case scenarios
- LocationOwnershipDataConsistencyTest: Data integrity and consistency
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase, TransactionTestCase

from campaigns.models import Campaign, CampaignMembership
from characters.models import Character
from locations.models import Location

User = get_user_model()


class LocationOwnershipIntegrationTest(TestCase):
    """Test complete integration of location ownership feature."""

    def setUp(self):
        """Set up comprehensive test data for integration tests."""
        # Create users with different roles
        self.campaign_owner = User.objects.create_user(
            username="campaign_owner",
            email="campaign_owner@test.com",
            password="testpass123",
        )
        self.gm_user = User.objects.create_user(
            username="gm_user", email="gm_user@test.com", password="testpass123"
        )
        self.player1 = User.objects.create_user(
            username="player1", email="player1@test.com", password="testpass123"
        )
        self.player2 = User.objects.create_user(
            username="player2", email="player2@test.com", password="testpass123"
        )

        # Create campaign
        self.campaign = Campaign.objects.create(
            name="Integration Test Campaign",
            owner=self.campaign_owner,
            game_system="mage",
        )

        # Create memberships
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm_user, role="GM"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player1, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player2, role="PLAYER"
        )

        # Create diverse character portfolio
        self.npcs = [
            Character.objects.create(
                name="Innkeeper Margaret",
                campaign=self.campaign,
                player_owner=self.gm_user,
                game_system="mage",
                npc=True,
                description="Friendly innkeeper who runs the local tavern",
            ),
            Character.objects.create(
                name="Lord Aldric Blackstone",
                campaign=self.campaign,
                player_owner=self.campaign_owner,
                game_system="mage",
                npc=True,
                description="Noble lord who owns vast estates",
            ),
            Character.objects.create(
                name="Merchant Tobias",
                campaign=self.campaign,
                player_owner=self.gm_user,
                game_system="mage",
                npc=True,
                description="Traveling merchant with several shops",
            ),
        ]

        self.pcs = [
            Character.objects.create(
                name="Lyra Moonwhisper",
                campaign=self.campaign,
                player_owner=self.player1,
                game_system="mage",
                npc=False,
                description="Player character mage with a secret sanctum",
            ),
            Character.objects.create(
                name="Gareth Ironforge",
                campaign=self.campaign,
                player_owner=self.player2,
                game_system="mage",
                npc=False,
                description="Player character who owns a blacksmith shop",
            ),
        ]

    def test_complete_ownership_workflow(self):
        """Test complete ownership workflow from creation to transfer."""
        # Step 1: Create unowned location
        tavern = Location.objects.create(
            name="The Prancing Pony",
            description="A cozy tavern in the town center",
            campaign=self.campaign,
            created_by=self.gm_user,
        )
        self.assertIsNone(tavern.owned_by)

        # Step 2: Assign ownership to NPC
        tavern.owned_by = self.npcs[0]  # Innkeeper Margaret
        tavern.save()

        tavern.refresh_from_db()
        self.assertEqual(tavern.owned_by, self.npcs[0])
        self.assertIn(tavern, self.npcs[0].owned_locations.all())

        # Step 3: Create related locations with same owner
        rooms = []
        for i in range(3):
            room = Location.objects.create(
                name=f"Room {i+1}",
                description=f"Guest room {i+1} in the tavern",
                campaign=self.campaign,
                parent=tavern,
                owned_by=self.npcs[0],
                created_by=self.gm_user,
            )
            rooms.append(room)

        # Verify ownership propagation
        margaret_locations = self.npcs[0].owned_locations.all()
        self.assertEqual(margaret_locations.count(), 4)  # Tavern + 3 rooms
        self.assertIn(tavern, margaret_locations)
        for room in rooms:
            self.assertIn(room, margaret_locations)

        # Step 4: Transfer ownership to different NPC
        new_owner = self.npcs[1]  # Lord Aldric
        tavern.owned_by = new_owner
        tavern.save()

        # Verify transfer
        tavern.refresh_from_db()
        self.assertEqual(tavern.owned_by, new_owner)
        self.assertIn(tavern, new_owner.owned_locations.all())
        self.assertNotIn(tavern, self.npcs[0].owned_locations.all())

        # Step 5: Partial transfer (some rooms to different owner)
        rooms[0].owned_by = self.pcs[0]  # Lyra gets one room
        rooms[0].save()

        # Verify partial transfer
        rooms[0].refresh_from_db()
        self.assertEqual(rooms[0].owned_by, self.pcs[0])
        self.assertIn(rooms[0], self.pcs[0].owned_locations.all())
        self.assertNotIn(rooms[0], new_owner.owned_locations.all())

    def test_owned_locations_relationship_functionality(self):
        """Test owned_locations reverse relationship functionality."""
        # Create locations for different characters
        locations_data = [
            ("Blackstone Manor", self.npcs[1]),  # Lord Aldric
            ("Manor Gardens", self.npcs[1]),  # Lord Aldric
            ("Lyra's Sanctum", self.pcs[0]),  # Lyra
            ("Merchant's Warehouse", self.npcs[2]),  # Tobias
            ("Gareth's Smithy", self.pcs[1]),  # Gareth
        ]

        created_locations = []
        for name, owner in locations_data:
            location = Location.objects.create(
                name=name,
                campaign=self.campaign,
                owned_by=owner,
                created_by=self.campaign_owner,
            )
            created_locations.append(location)

        # Test owned_locations for Lord Aldric (should have 2)
        aldric_locations = self.npcs[1].owned_locations.all()
        self.assertEqual(aldric_locations.count(), 2)
        self.assertIn(created_locations[0], aldric_locations)  # Manor
        self.assertIn(created_locations[1], aldric_locations)  # Gardens

        # Test owned_locations for Lyra (should have 1)
        lyra_locations = self.pcs[0].owned_locations.all()
        self.assertEqual(lyra_locations.count(), 1)
        self.assertIn(created_locations[2], lyra_locations)  # Sanctum

        # Test owned_locations for characters with no ownership
        for char in [self.npcs[0]]:  # Margaret has no locations in this test
            char_locations = char.owned_locations.all()
            self.assertEqual(char_locations.count(), 0)

    def test_ownership_with_character_lifecycle(self):
        """Test ownership behavior throughout character lifecycle."""
        # Create location owned by character
        shop = Location.objects.create(
            name="Tobias Trading Post",
            campaign=self.campaign,
            owned_by=self.npcs[2],  # Merchant Tobias
            created_by=self.gm_user,
        )

        # Verify initial ownership
        self.assertEqual(shop.owned_by, self.npcs[2])
        self.assertEqual(self.npcs[2].owned_locations.count(), 1)

        # Soft delete character
        tobias_id = self.npcs[2].id
        self.npcs[2].soft_delete(self.gm_user)

        # Check ownership after soft delete
        shop.refresh_from_db()
        # Ownership should remain with soft-deleted character
        self.assertEqual(shop.owned_by.id, tobias_id)
        self.assertTrue(shop.owned_by.is_deleted)

        # Restore character
        deleted_tobias = Character.all_objects.get(id=tobias_id)
        deleted_tobias.restore(self.gm_user)

        # Verify ownership after restore
        shop.refresh_from_db()
        restored_tobias = Character.objects.get(id=tobias_id)
        self.assertEqual(shop.owned_by, restored_tobias)
        self.assertFalse(shop.owned_by.is_deleted)

    def test_cross_campaign_ownership_prevention_integration(self):
        """Test cross-campaign ownership prevention in full integration."""
        # Create second campaign
        other_campaign = Campaign.objects.create(
            name="Other Campaign",
            owner=self.campaign_owner,
            game_system="generic",
        )

        other_character = Character.objects.create(
            name="Foreign Character",
            campaign=other_campaign,
            player_owner=self.campaign_owner,
            game_system="generic",
            npc=True,
        )

        # Create location in original campaign
        location = Location.objects.create(
            name="Cross Campaign Test Location",
            campaign=self.campaign,
            created_by=self.campaign_owner,
        )

        # Attempt cross-campaign ownership assignment
        location.owned_by = other_character

        # Should fail validation
        with self.assertRaises(ValidationError):
            location.clean()

        # Should also prevent saving
        with self.assertRaises(ValidationError):
            location.save()

    def test_ownership_hierarchy_integration(self):
        """Test ownership in hierarchical location structures."""
        # Create hierarchical location structure
        estate = Location.objects.create(
            name="Blackstone Estate",
            campaign=self.campaign,
            owned_by=self.npcs[1],  # Lord Aldric
            created_by=self.campaign_owner,
        )

        mansion = Location.objects.create(
            name="Main Mansion",
            campaign=self.campaign,
            parent=estate,
            owned_by=self.npcs[1],  # Same owner
            created_by=self.campaign_owner,
        )

        library = Location.objects.create(
            name="Private Library",
            campaign=self.campaign,
            parent=mansion,
            owned_by=self.npcs[1],  # Same owner
            created_by=self.campaign_owner,
        )

        guest_wing = Location.objects.create(
            name="Guest Wing",
            campaign=self.campaign,
            parent=mansion,
            owned_by=self.pcs[0],  # Different owner (guest)
            created_by=self.campaign_owner,
        )

        servants_quarters = Location.objects.create(
            name="Servants' Quarters",
            campaign=self.campaign,
            parent=estate,
            owned_by=None,  # Unowned
            created_by=self.campaign_owner,
        )

        # Verify hierarchy and ownership
        aldric_locations = self.npcs[1].owned_locations.all()
        self.assertEqual(aldric_locations.count(), 3)  # Estate, mansion, library
        self.assertIn(estate, aldric_locations)
        self.assertIn(mansion, aldric_locations)
        self.assertIn(library, aldric_locations)

        lyra_locations = self.pcs[0].owned_locations.all()
        self.assertEqual(lyra_locations.count(), 1)  # Guest wing only
        self.assertIn(guest_wing, lyra_locations)

        # Test hierarchy preservation with ownership
        self.assertEqual(guest_wing.parent, mansion)
        self.assertEqual(library.parent, mansion)
        self.assertEqual(servants_quarters.parent, estate)


class LocationOwnershipPerformanceTest(TestCase):
    """Test performance and scalability of ownership relationships."""

    def setUp(self):
        """Set up performance test data."""
        self.owner = User.objects.create_user(
            username="perf_owner", email="perf_owner@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Performance Test Campaign",
            owner=self.owner,
            game_system="mage",
        )

    def test_ownership_query_performance(self):
        """Test query performance with ownership relationships."""
        # Create characters
        characters = []
        for i in range(10):
            char = Character.objects.create(
                name=f"Performance Character {i}",
                campaign=self.campaign,
                player_owner=self.owner,
                game_system="mage",
                npc=True,
            )
            characters.append(char)

        # Create locations with ownership
        locations = []
        for i in range(50):
            char = characters[i % len(characters)]  # Distribute ownership
            location = Location.objects.create(
                name=f"Performance Location {i}",
                campaign=self.campaign,
                owned_by=char,
                created_by=self.owner,
            )
            locations.append(location)

        # Test efficient querying
        with self.assertNumQueries(1):  # Should be one efficient query
            owned_locations = Location.objects.filter(
                owned_by__isnull=False
            ).select_related("owned_by")
            list(owned_locations)  # Force evaluation

        # Test character owned_locations performance
        test_char = characters[0]
        with self.assertNumQueries(1):  # Should be one query
            char_locations = test_char.owned_locations.all()
            list(char_locations)  # Force evaluation

    def test_bulk_ownership_operations_performance(self):
        """Test performance of bulk ownership operations."""
        # Create characters
        old_owner = Character.objects.create(
            name="Old Bulk Owner",
            campaign=self.campaign,
            player_owner=self.owner,
            game_system="mage",
            npc=True,
        )

        new_owner = Character.objects.create(
            name="New Bulk Owner",
            campaign=self.campaign,
            player_owner=self.owner,
            game_system="mage",
            npc=True,
        )

        # Create many locations with same owner
        locations = []
        for i in range(100):
            location = Location.objects.create(
                name=f"Bulk Location {i}",
                campaign=self.campaign,
                owned_by=old_owner,
                created_by=self.owner,
            )
            locations.append(location)

        # Test bulk transfer performance
        with self.assertNumQueries(1):  # Should be single UPDATE query
            updated_count = Location.objects.filter(owned_by=old_owner).update(
                owned_by=new_owner
            )

        self.assertEqual(updated_count, 100)

        # Verify transfer
        new_owner_count = new_owner.owned_locations.count()
        old_owner_count = old_owner.owned_locations.count()
        self.assertEqual(new_owner_count, 100)
        self.assertEqual(old_owner_count, 0)

    def test_ownership_with_large_hierarchy_performance(self):
        """Test ownership performance with large hierarchical structures."""
        # Create character owner
        noble = Character.objects.create(
            name="Noble with Large Estate",
            campaign=self.campaign,
            player_owner=self.owner,
            game_system="mage",
            npc=True,
        )

        # Create large hierarchical structure
        root = Location.objects.create(
            name="Estate Root",
            campaign=self.campaign,
            owned_by=noble,
            created_by=self.owner,
        )

        # Create tree structure: 1 root -> 5 buildings -> 10 rooms each
        buildings = []
        for i in range(5):
            building = Location.objects.create(
                name=f"Building {i}",
                campaign=self.campaign,
                parent=root,
                owned_by=noble,
                created_by=self.owner,
            )
            buildings.append(building)

            # Create rooms in each building
            for j in range(10):
                Location.objects.create(
                    name=f"Room {i}-{j}",
                    campaign=self.campaign,
                    parent=building,
                    owned_by=noble,
                    created_by=self.owner,
                )

        # Test querying all owned locations efficiently
        with self.assertNumQueries(1):
            owned_locations = noble.owned_locations.all()
            owned_count = owned_locations.count()

        self.assertEqual(owned_count, 56)  # 1 root + 5 buildings + 50 rooms


class LocationOwnershipScenarioTest(TestCase):
    """Test real-world scenarios and use cases for location ownership."""

    def setUp(self):
        """Set up scenario test data."""
        self.gm = User.objects.create_user(
            username="scenario_gm", email="scenario_gm@test.com", password="testpass123"
        )

        self.player1 = User.objects.create_user(
            username="scenario_player1",
            email="scenario_player1@test.com",
            password="testpass123",
        )

        self.player2 = User.objects.create_user(
            username="scenario_player2",
            email="scenario_player2@test.com",
            password="testpass123",
        )

        self.campaign = Campaign.objects.create(
            name="Scenario Test Campaign",
            owner=self.gm,
            game_system="mage",
        )

        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player1, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player2, role="PLAYER"
        )

    def test_tavern_ownership_scenario(self):
        """Test typical tavern ownership scenario."""
        # Create tavern keeper NPC
        innkeeper = Character.objects.create(
            name="Goodwife Martha",
            campaign=self.campaign,
            player_owner=self.gm,
            game_system="mage",
            npc=True,
            description="Friendly innkeeper who owns the Silver Stag",
        )

        # Create tavern and rooms
        tavern = Location.objects.create(
            name="The Silver Stag Tavern",
            description="A popular tavern frequented by adventurers",
            campaign=self.campaign,
            owned_by=innkeeper,
            created_by=self.gm,
        )

        common_room = Location.objects.create(
            name="Common Room",
            description="The main tavern area with tables and a large fireplace",
            campaign=self.campaign,
            parent=tavern,
            owned_by=innkeeper,
            created_by=self.gm,
        )

        # Player rents a room
        player_char = Character.objects.create(
            name="Adventurer Kael",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="mage",
            npc=False,
        )

        rented_room = Location.objects.create(
            name="Room 3 (Rented)",
            description="A small room rented by Kael",
            campaign=self.campaign,
            parent=tavern,
            owned_by=player_char,  # Player temporarily owns rented room
            created_by=self.gm,
        )

        # Verify scenario setup
        self.assertEqual(tavern.owned_by, innkeeper)
        self.assertEqual(common_room.owned_by, innkeeper)
        self.assertEqual(rented_room.owned_by, player_char)

        # Innkeeper owns tavern and common room
        innkeeper_properties = innkeeper.owned_locations.all()
        self.assertEqual(innkeeper_properties.count(), 2)
        self.assertIn(tavern, innkeeper_properties)
        self.assertIn(common_room, innkeeper_properties)

        # Player owns rented room
        player_properties = player_char.owned_locations.all()
        self.assertEqual(player_properties.count(), 1)
        self.assertIn(rented_room, player_properties)

    def test_noble_estate_scenario(self):
        """Test complex noble estate ownership scenario."""
        # Create noble family NPCs
        lord = Character.objects.create(
            name="Lord Aldric Ravencrest",
            campaign=self.campaign,
            player_owner=self.gm,
            game_system="mage",
            npc=True,
        )

        lady = Character.objects.create(
            name="Lady Elara Ravencrest",
            campaign=self.campaign,
            player_owner=self.gm,
            game_system="mage",
            npc=True,
        )

        steward = Character.objects.create(
            name="Steward Henrick",
            campaign=self.campaign,
            player_owner=self.gm,
            game_system="mage",
            npc=True,
        )

        # Create estate structure
        estate = Location.objects.create(
            name="Ravencrest Estate",
            campaign=self.campaign,
            owned_by=lord,
            created_by=self.gm,
        )

        manor = Location.objects.create(
            name="Ravencrest Manor",
            campaign=self.campaign,
            parent=estate,
            owned_by=lord,
            created_by=self.gm,
        )

        # Lord's private areas
        Location.objects.create(
            name="Lord's Study",
            campaign=self.campaign,
            parent=manor,
            owned_by=lord,
            created_by=self.gm,
        )

        # Lady's private areas
        Location.objects.create(
            name="Lady's Chambers",
            campaign=self.campaign,
            parent=manor,
            owned_by=lady,
            created_by=self.gm,
        )

        # Steward's domain
        Location.objects.create(
            name="Steward's Office",
            campaign=self.campaign,
            parent=manor,
            owned_by=steward,
            created_by=self.gm,
        )

        # Shared/unowned areas
        Location.objects.create(
            name="Great Hall",
            campaign=self.campaign,
            parent=manor,
            owned_by=None,  # Shared family space
            created_by=self.gm,
        )

        # Verify complex ownership
        lord_properties = lord.owned_locations.all()
        self.assertEqual(lord_properties.count(), 3)  # Estate, manor, study

        lady_properties = lady.owned_locations.all()
        self.assertEqual(lady_properties.count(), 1)  # Chambers

        steward_properties = steward.owned_locations.all()
        self.assertEqual(steward_properties.count(), 1)  # Office

    def test_merchant_multiple_properties_scenario(self):
        """Test merchant with multiple properties across town."""
        # Create merchant NPC
        merchant = Character.objects.create(
            name="Master Goldhand",
            campaign=self.campaign,
            player_owner=self.gm,
            game_system="mage",
            npc=True,
            description="Wealthy merchant with interests across the city",
        )

        # Create merchant's properties
        main_shop = Location.objects.create(
            name="Goldhand's Fine Goods",
            description="Upscale shop in the merchant quarter",
            campaign=self.campaign,
            owned_by=merchant,
            created_by=self.gm,
        )

        warehouse = Location.objects.create(
            name="Goldhand's Warehouse",
            description="Storage facility near the docks",
            campaign=self.campaign,
            owned_by=merchant,
            created_by=self.gm,
        )

        residence = Location.objects.create(
            name="Goldhand Manor",
            description="Merchant's luxurious home",
            campaign=self.campaign,
            owned_by=merchant,
            created_by=self.gm,
        )

        # Create branch shops managed by employees
        branch_manager = Character.objects.create(
            name="Apprentice Finn",
            campaign=self.campaign,
            player_owner=self.gm,
            game_system="mage",
            npc=True,
        )

        branch_shop = Location.objects.create(
            name="Goldhand's Branch Shop",
            description="Smaller shop run by Finn",
            campaign=self.campaign,
            owned_by=branch_manager,  # Managed by employee
            created_by=self.gm,
        )

        # Verify merchant empire
        merchant_properties = merchant.owned_locations.all()
        self.assertEqual(merchant_properties.count(), 3)
        expected_properties = [main_shop, warehouse, residence]
        for prop in expected_properties:
            self.assertIn(prop, merchant_properties)

        # Verify branch management
        finn_properties = branch_manager.owned_locations.all()
        self.assertEqual(finn_properties.count(), 1)
        self.assertIn(branch_shop, finn_properties)

    def test_player_character_property_acquisition_scenario(self):
        """Test player character acquiring and losing property."""
        # Create player character
        player_char = Character.objects.create(
            name="Mage Lyralei",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="mage",
            npc=False,
        )

        # Create previous owner NPC
        old_owner = Character.objects.create(
            name="Former Owner Willem",
            campaign=self.campaign,
            player_owner=self.gm,
            game_system="mage",
            npc=True,
        )

        # Create property initially owned by NPC
        tower = Location.objects.create(
            name="Abandoned Tower",
            description="An old wizard's tower",
            campaign=self.campaign,
            owned_by=old_owner,
            created_by=self.gm,
        )

        # Player acquires property
        tower.owned_by = player_char
        tower.save()

        # Player establishes sanctum
        sanctum = Location.objects.create(
            name="Lyralei's Sanctum",
            description="Personal magical workspace",
            campaign=self.campaign,
            parent=tower,
            owned_by=player_char,
            created_by=self.player1,
        )

        # Verify acquisition
        player_properties = player_char.owned_locations.all()
        self.assertEqual(player_properties.count(), 2)
        self.assertIn(tower, player_properties)
        self.assertIn(sanctum, player_properties)

        # Old owner loses property
        old_owner_properties = old_owner.owned_locations.all()
        self.assertEqual(old_owner_properties.count(), 0)

        # Later: Player loses property back to authorities (NPC)
        authorities = Character.objects.create(
            name="Town Authorities",
            campaign=self.campaign,
            player_owner=self.gm,
            game_system="mage",
            npc=True,
        )

        # Property confiscated
        tower.owned_by = authorities
        sanctum.owned_by = authorities
        tower.save()
        sanctum.save()

        # Verify loss
        player_properties_after = player_char.owned_locations.all()
        self.assertEqual(player_properties_after.count(), 0)

        authorities_properties = authorities.owned_locations.all()
        self.assertEqual(authorities_properties.count(), 2)


class LocationOwnershipDataConsistencyTest(TransactionTestCase):
    """Test data integrity and consistency of ownership relationships."""

    def setUp(self):
        """Set up data consistency test environment."""
        self.owner = User.objects.create_user(
            username="consistency_owner",
            email="consistency_owner@test.com",
            password="testpass123",
        )

        self.campaign = Campaign.objects.create(
            name="Consistency Test Campaign",
            owner=self.owner,
            game_system="mage",
        )

    def test_ownership_transaction_integrity(self):
        """Test that ownership changes maintain transaction integrity."""
        # Create character and location
        character = Character.objects.create(
            name="Transaction Test Character",
            campaign=self.campaign,
            player_owner=self.owner,
            game_system="mage",
            npc=True,
        )

        location = Location.objects.create(
            name="Transaction Test Location",
            campaign=self.campaign,
            created_by=self.owner,
        )

        # Test successful transaction
        with transaction.atomic():
            location.owned_by = character
            location.save()
            # Add other related changes that should all succeed together
            location.description = "Updated during ownership assignment"
            location.save()

        # Verify changes persisted
        location.refresh_from_db()
        self.assertEqual(location.owned_by, character)
        self.assertEqual(location.description, "Updated during ownership assignment")

        # Test failed transaction rollback
        try:
            with transaction.atomic():
                location.owned_by = None
                location.save()
                # Simulate error that causes rollback
                raise IntegrityError("Simulated error")
        except IntegrityError:
            pass

        # Verify rollback - ownership should remain unchanged
        location.refresh_from_db()
        self.assertEqual(location.owned_by, character)  # Should not be None

    def test_concurrent_ownership_modifications(self):
        """Test handling of concurrent ownership modifications."""
        # Create test data
        character1 = Character.objects.create(
            name="Concurrent Character 1",
            campaign=self.campaign,
            player_owner=self.owner,
            game_system="mage",
            npc=True,
        )

        character2 = Character.objects.create(
            name="Concurrent Character 2",
            campaign=self.campaign,
            player_owner=self.owner,
            game_system="mage",
            npc=True,
        )

        location = Location.objects.create(
            name="Concurrent Test Location",
            campaign=self.campaign,
            owned_by=character1,
            created_by=self.owner,
        )

        # Simulate concurrent modification
        location_copy1 = Location.objects.get(pk=location.pk)
        location_copy2 = Location.objects.get(pk=location.pk)

        # First modification
        location_copy1.owned_by = character2
        location_copy1.save()

        # Second modification (should overwrite first)
        location_copy2.owned_by = None
        location_copy2.save()

        # Verify final state
        location.refresh_from_db()
        self.assertIsNone(location.owned_by)

    def test_ownership_referential_integrity(self):
        """Test referential integrity of ownership relationships."""
        character = Character.objects.create(
            name="Integrity Test Character",
            campaign=self.campaign,
            player_owner=self.owner,
            game_system="mage",
            npc=True,
        )

        location = Location.objects.create(
            name="Integrity Test Location",
            campaign=self.campaign,
            owned_by=character,
            created_by=self.owner,
        )

        # Verify initial relationship
        self.assertEqual(location.owned_by, character)
        self.assertIn(location, character.owned_locations.all())

        # Delete character (should set location.owned_by to None due to SET_NULL)
        character_id = character.id
        character.delete()

        # Verify referential integrity maintained
        location.refresh_from_db()
        self.assertIsNone(location.owned_by)

        # Verify character no longer exists
        with self.assertRaises(Character.DoesNotExist):
            Character.objects.get(id=character_id)

    def test_ownership_data_migration_compatibility(self):
        """Test that ownership feature is compatible with data migrations."""
        # Create locations without ownership (pre-feature state)
        locations_without_ownership = []
        for i in range(5):
            location = Location.objects.create(
                name=f"Migration Test Location {i}",
                campaign=self.campaign,
                created_by=self.owner,
            )
            locations_without_ownership.append(location)

        # Verify all locations have None ownership (default)
        for location in locations_without_ownership:
            self.assertIsNone(location.owned_by)

        # Create characters for ownership assignment
        characters = []
        for i in range(3):
            character = Character.objects.create(
                name=f"Migration Character {i}",
                campaign=self.campaign,
                player_owner=self.owner,
                game_system="mage",
                npc=True,
            )
            characters.append(character)

        # Simulate post-migration ownership assignment
        for i, location in enumerate(locations_without_ownership):
            if i < len(characters):
                location.owned_by = characters[i % len(characters)]
                location.save()

        # Verify migration-like assignment worked
        for i, location in enumerate(locations_without_ownership):
            if i < len(characters):
                expected_character = characters[i % len(characters)]
                self.assertEqual(location.owned_by, expected_character)
            else:
                self.assertIsNone(location.owned_by)

    def test_ownership_bulk_operations_consistency(self):
        """Test consistency during bulk ownership operations."""
        # Create multiple characters
        characters = []
        for i in range(3):
            character = Character.objects.create(
                name=f"Bulk Character {i}",
                campaign=self.campaign,
                player_owner=self.owner,
                game_system="mage",
                npc=True,
            )
            characters.append(character)

        # Create locations owned by first character
        locations = []
        for i in range(10):
            location = Location.objects.create(
                name=f"Bulk Location {i}",
                campaign=self.campaign,
                owned_by=characters[0],
                created_by=self.owner,
            )
            locations.append(location)

        # Verify initial ownership
        char0_count = characters[0].owned_locations.count()
        self.assertEqual(char0_count, 10)

        # Bulk transfer to second character
        with transaction.atomic():
            updated_count = Location.objects.filter(owned_by=characters[0]).update(
                owned_by=characters[1]
            )
            self.assertEqual(updated_count, 10)

        # Verify bulk transfer consistency
        char0_count_after = characters[0].owned_locations.count()
        char1_count_after = characters[1].owned_locations.count()

        self.assertEqual(char0_count_after, 0)
        self.assertEqual(char1_count_after, 10)

        # Verify all locations correctly transferred
        for location in locations:
            location.refresh_from_db()
            self.assertEqual(location.owned_by, characters[1])
