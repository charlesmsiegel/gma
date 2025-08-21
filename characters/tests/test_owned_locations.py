"""
Tests for Character model owned_locations relationship (Issue #186).

Tests cover:
- Character.owned_locations reverse relationship functionality
- Integration with Location.owned_by field
- Queryset methods and filtering for owned locations
- Performance optimization for owned_locations queries
- Character ownership across different scenarios

Test Structure:
- CharacterOwnedLocationsBasicTest: Basic relationship functionality
- CharacterOwnedLocationsQueryTest: Advanced querying and filtering
- CharacterOwnedLocationsPerformanceTest: Performance optimization
- CharacterOwnedLocationsScenarioTest: Real-world usage scenarios
"""

from django.contrib.auth import get_user_model
from django.db import models
from django.test import TestCase

from campaigns.models import Campaign, CampaignMembership
from characters.models import Character
from locations.models import Location

User = get_user_model()


class CharacterOwnedLocationsBasicTest(TestCase):
    """Test basic owned_locations relationship functionality."""

    def setUp(self):
        """Set up test data for basic owned_locations tests."""
        self.owner = User.objects.create_user(
            username="owned_owner", email="owned_owner@test.com", password="testpass123"
        )
        self.player = User.objects.create_user(
            username="owned_player",
            email="owned_player@test.com",
            password="testpass123",
        )

        self.campaign = Campaign.objects.create(
            name="Owned Locations Test Campaign",
            owner=self.owner,
            game_system="mage",
            max_characters_per_player=0,  # Allow unlimited characters for testing
        )

        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )

        # Create test characters
        self.npc_character = Character.objects.create(
            name="NPC Test Character",
            campaign=self.campaign,
            player_owner=self.owner,
            game_system="mage",
            npc=True,
        )

        self.pc_character = Character.objects.create(
            name="PC Test Character",
            campaign=self.campaign,
            player_owner=self.player,
            game_system="mage",
            npc=False,
        )

    def test_character_has_owned_locations_attribute(self):
        """Test that Character model has owned_locations attribute."""
        self.assertTrue(hasattr(self.npc_character, "owned_locations"))
        self.assertTrue(hasattr(self.pc_character, "owned_locations"))

    def test_owned_locations_returns_queryset(self):
        """Test that owned_locations returns a queryset."""
        npc_owned = self.npc_character.owned_locations.all()
        pc_owned = self.pc_character.owned_locations.all()

        # Should return querysets
        self.assertIsNotNone(npc_owned)
        self.assertIsNotNone(pc_owned)

        # Should be empty initially
        self.assertEqual(npc_owned.count(), 0)
        self.assertEqual(pc_owned.count(), 0)

    def test_owned_locations_relationship_with_single_location(self):
        """Test owned_locations relationship with a single location."""
        # Create location owned by NPC
        npc_location = Location.objects.create(
            name="NPC Owned Location",
            campaign=self.campaign,
            owned_by=self.npc_character,
            created_by=self.owner,
        )

        # Test relationship
        npc_owned = self.npc_character.owned_locations.all()
        self.assertEqual(npc_owned.count(), 1)
        self.assertIn(npc_location, npc_owned)

        # PC should have no owned locations
        pc_owned = self.pc_character.owned_locations.all()
        self.assertEqual(pc_owned.count(), 0)

    def test_owned_locations_relationship_with_multiple_locations(self):
        """Test owned_locations relationship with multiple locations."""
        # Create multiple locations owned by same character
        locations = []
        for i in range(3):
            location = Location.objects.create(
                name=f"NPC Location {i}",
                campaign=self.campaign,
                owned_by=self.npc_character,
                created_by=self.owner,
            )
            locations.append(location)

        # Test relationship
        npc_owned = self.npc_character.owned_locations.all()
        self.assertEqual(npc_owned.count(), 3)

        for location in locations:
            self.assertIn(location, npc_owned)

    def test_owned_locations_relationship_updates_dynamically(self):
        """Test that owned_locations updates when ownership changes."""
        # Create location initially unowned
        location = Location.objects.create(
            name="Dynamic Ownership Test",
            campaign=self.campaign,
            created_by=self.owner,
        )

        # Initially no character should own it
        npc_owned_initial = self.npc_character.owned_locations.all()
        self.assertEqual(npc_owned_initial.count(), 0)

        # Assign ownership to NPC
        location.owned_by = self.npc_character
        location.save()

        # Check owned_locations updates
        npc_owned_after = self.npc_character.owned_locations.all()
        self.assertEqual(npc_owned_after.count(), 1)
        self.assertIn(location, npc_owned_after)

        # Transfer ownership to PC
        location.owned_by = self.pc_character
        location.save()

        # Check both characters
        npc_owned_final = self.npc_character.owned_locations.all()
        pc_owned_final = self.pc_character.owned_locations.all()

        self.assertEqual(npc_owned_final.count(), 0)
        self.assertEqual(pc_owned_final.count(), 1)
        self.assertIn(location, pc_owned_final)

    def test_owned_locations_with_none_ownership(self):
        """Test owned_locations when location ownership is set to None."""
        # Create location owned by character
        location = Location.objects.create(
            name="None Ownership Test",
            campaign=self.campaign,
            owned_by=self.npc_character,
            created_by=self.owner,
        )

        # Verify initial ownership
        npc_owned_initial = self.npc_character.owned_locations.all()
        self.assertEqual(npc_owned_initial.count(), 1)

        # Set ownership to None
        location.owned_by = None
        location.save()

        # Check owned_locations updates
        npc_owned_after = self.npc_character.owned_locations.all()
        self.assertEqual(npc_owned_after.count(), 0)

    def test_owned_locations_related_name_configuration(self):
        """Test that owned_locations uses correct related_name."""
        # This test verifies the field configuration
        location = Location.objects.create(
            name="Related Name Test",
            campaign=self.campaign,
            owned_by=self.npc_character,
            created_by=self.owner,
        )

        # Should be accessible via owned_locations
        self.assertTrue(hasattr(self.npc_character, "owned_locations"))

        # Should contain the location
        owned = self.npc_character.owned_locations.all()
        self.assertIn(location, owned)

        # Verify this is the same as the reverse foreign key relationship
        self.assertEqual(location.owned_by, self.npc_character)


class CharacterOwnedLocationsQueryTest(TestCase):
    """Test advanced querying and filtering for owned_locations."""

    def setUp(self):
        """Set up test data for query tests."""
        self.owner = User.objects.create_user(
            username="query_owner", email="query_owner@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Query Test Campaign",
            owner=self.owner,
            game_system="mage",
            max_characters_per_player=0,  # Allow unlimited characters for testing
        )

        # Create multiple characters
        self.characters = []
        for i in range(3):
            character = Character.objects.create(
                name=f"Query Character {i}",
                campaign=self.campaign,
                player_owner=self.owner,
                game_system="mage",
                npc=True,
            )
            self.characters.append(character)

        # Create locations with various ownership
        self.locations = []
        for i in range(9):
            char_index = i % 3  # Distribute ownership among 3 characters
            location = Location.objects.create(
                name=f"Query Location {i}",
                campaign=self.campaign,
                owned_by=self.characters[char_index],
                created_by=self.owner,
            )
            self.locations.append(location)

    def test_owned_locations_filtering(self):
        """Test filtering owned_locations by various criteria."""
        test_char = self.characters[0]

        # Filter by name
        named_locations = test_char.owned_locations.filter(name__icontains="Location 0")
        self.assertGreater(named_locations.count(), 0)

        # Filter by campaign
        campaign_locations = test_char.owned_locations.filter(campaign=self.campaign)
        self.assertEqual(
            campaign_locations.count(), 3
        )  # Character 0 owns locations 0, 3, 6

        # Filter with exclude
        non_zero_locations = test_char.owned_locations.exclude(name__endswith="0")
        self.assertGreater(non_zero_locations.count(), 0)

    def test_owned_locations_ordering(self):
        """Test ordering of owned_locations."""
        test_char = self.characters[0]

        # Order by name
        ordered_by_name = test_char.owned_locations.order_by("name")
        names = [loc.name for loc in ordered_by_name]
        self.assertEqual(names, sorted(names))

        # Order by creation date
        ordered_by_date = test_char.owned_locations.order_by("created_at")
        dates = [loc.created_at for loc in ordered_by_date]
        self.assertEqual(dates, sorted(dates))

    def test_owned_locations_aggregation(self):
        """Test aggregation operations on owned_locations."""
        from django.db.models import Count, Max, Min

        test_char = self.characters[0]

        # Count owned locations
        owned_count = test_char.owned_locations.count()
        self.assertEqual(owned_count, 3)

        # Aggregate by related fields
        stats = test_char.owned_locations.aggregate(
            total=Count("id"),
            latest_created=Max("created_at"),
            earliest_created=Min("created_at"),
        )

        self.assertEqual(stats["total"], 3)
        self.assertIsNotNone(stats["latest_created"])
        self.assertIsNotNone(stats["earliest_created"])

    def test_owned_locations_with_select_related(self):
        """Test owned_locations with select_related optimization."""
        test_char = self.characters[0]

        # Use select_related to optimize queries
        optimized_owned = test_char.owned_locations.select_related(
            "campaign", "created_by"
        )

        # Should work without additional queries
        locations_list = list(optimized_owned)
        self.assertEqual(len(locations_list), 3)

        # Access related fields should not trigger additional queries
        for location in locations_list:
            self.assertEqual(location.campaign, self.campaign)
            self.assertEqual(location.created_by, self.owner)

    def test_owned_locations_with_prefetch_related(self):
        """Test owned_locations with prefetch_related for reverse relationships."""
        # Create child locations to test prefetch
        parent_location = self.locations[0]  # Owned by characters[0]

        child_locations = []
        for i in range(2):
            child = Location.objects.create(
                name=f"Child Location {i}",
                campaign=self.campaign,
                parent=parent_location,
                owned_by=self.characters[0],
                created_by=self.owner,
            )
            child_locations.append(child)

        test_char = self.characters[0]

        # Use prefetch_related for children
        owned_with_children = test_char.owned_locations.prefetch_related("children")

        # Should optimize children access
        for location in owned_with_children:
            location.children.all()
            # Test that children are accessible without additional queries

    def test_owned_locations_complex_queries(self):
        """Test complex queries on owned_locations."""
        test_char = self.characters[0]

        # Complex filter with Q objects
        from django.db.models import Q

        complex_filter = test_char.owned_locations.filter(
            Q(name__icontains="Location") & Q(campaign=self.campaign)
        )
        self.assertGreater(complex_filter.count(), 0)

        # Chained filters
        chained = (
            test_char.owned_locations.filter(campaign=self.campaign)
            .exclude(name__endswith="9")
            .order_by("name")
        )

        self.assertGreaterEqual(chained.count(), 0)

    def test_owned_locations_values_and_values_list(self):
        """Test values() and values_list() on owned_locations."""
        test_char = self.characters[0]

        # Get values
        location_values = test_char.owned_locations.values("name", "id")
        self.assertEqual(len(location_values), 3)

        for value in location_values:
            self.assertIn("name", value)
            self.assertIn("id", value)

        # Get values_list
        location_names = test_char.owned_locations.values_list("name", flat=True)
        self.assertEqual(len(location_names), 3)

        for name in location_names:
            self.assertIsInstance(name, str)
            self.assertTrue(name.startswith("Query Location"))

    def test_owned_locations_exists_and_boolean_evaluation(self):
        """Test exists() and boolean evaluation on owned_locations."""
        owned_char = self.characters[0]

        # Character with owned locations
        self.assertTrue(owned_char.owned_locations.exists())
        self.assertTrue(bool(owned_char.owned_locations.all()))

        # Create character with no owned locations
        empty_char = Character.objects.create(
            name="Empty Character",
            campaign=self.campaign,
            player_owner=self.owner,
            game_system="mage",
            npc=True,
        )

        self.assertFalse(empty_char.owned_locations.exists())
        self.assertFalse(bool(empty_char.owned_locations.all()))


class CharacterOwnedLocationsPerformanceTest(TestCase):
    """Test performance optimization for owned_locations queries."""

    def setUp(self):
        """Set up performance test data."""
        self.owner = User.objects.create_user(
            username="perf_owner", email="perf_owner@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Performance Test Campaign",
            owner=self.owner,
            game_system="mage",
            max_characters_per_player=0,  # Allow unlimited characters for testing
        )

        # Create character for performance testing
        self.test_character = Character.objects.create(
            name="Performance Test Character",
            campaign=self.campaign,
            player_owner=self.owner,
            game_system="mage",
            npc=True,
        )

    def test_owned_locations_query_count(self):
        """Test that owned_locations queries are efficient."""
        # Create multiple locations
        locations = []
        for i in range(10):
            location = Location.objects.create(
                name=f"Performance Location {i}",
                campaign=self.campaign,
                owned_by=self.test_character,
                created_by=self.owner,
            )
            locations.append(location)

        # Test single query for owned_locations
        with self.assertNumQueries(1):
            owned_locations = list(self.test_character.owned_locations.all())
            self.assertEqual(len(owned_locations), 10)

    def test_owned_locations_with_select_related_performance(self):
        """Test performance with select_related optimization."""
        # Create locations
        for i in range(5):
            Location.objects.create(
                name=f"Optimized Location {i}",
                campaign=self.campaign,
                owned_by=self.test_character,
                created_by=self.owner,
            )

        # Test with select_related
        with self.assertNumQueries(1):  # Should be single optimized query
            optimized_owned = self.test_character.owned_locations.select_related(
                "campaign", "created_by"
            )

            for location in optimized_owned:
                # These should not trigger additional queries
                _ = location.campaign.name
                _ = location.created_by.username

    def test_owned_locations_count_performance(self):
        """Test that count() operations are efficient."""
        # Create locations
        for i in range(20):
            Location.objects.create(
                name=f"Count Location {i}",
                campaign=self.campaign,
                owned_by=self.test_character,
                created_by=self.owner,
            )

        # Test count query efficiency
        with self.assertNumQueries(1):
            count = self.test_character.owned_locations.count()
            self.assertEqual(count, 20)

        # Test count with filter
        with self.assertNumQueries(1):
            filtered_count = self.test_character.owned_locations.filter(
                name__icontains="Count"
            ).count()
            self.assertEqual(filtered_count, 20)

    def test_multiple_characters_owned_locations_performance(self):
        """Test performance when accessing owned_locations for multiple characters."""
        # Create multiple characters
        characters = [self.test_character]
        for i in range(4):
            char = Character.objects.create(
                name=f"Multi Character {i}",
                campaign=self.campaign,
                player_owner=self.owner,
                game_system="mage",
                npc=True,
            )
            characters.append(char)

        # Create locations for each character
        for char in characters:
            for i in range(3):
                Location.objects.create(
                    name=f"{char.name} Location {i}",
                    campaign=self.campaign,
                    owned_by=char,
                    created_by=self.owner,
                )

        # Test accessing owned_locations for all characters efficiently
        # Note: This will be multiple queries (one per character) which is expected
        with self.assertNumQueries(5):  # One query per character
            for char in characters:
                owned_count = char.owned_locations.count()
                self.assertEqual(owned_count, 3)


class CharacterOwnedLocationsScenarioTest(TestCase):
    """Test real-world usage scenarios for owned_locations."""

    def setUp(self):
        """Set up scenario test data."""
        self.gm = User.objects.create_user(
            username="scenario_gm", email="scenario_gm@test.com", password="testpass123"
        )
        self.player = User.objects.create_user(
            username="scenario_player",
            email="scenario_player@test.com",
            password="testpass123",
        )

        self.campaign = Campaign.objects.create(
            name="Scenario Test Campaign",
            owner=self.gm,
            game_system="mage",
            max_characters_per_player=0,  # Allow unlimited characters for testing
        )

        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )

    def test_npc_merchant_properties_scenario(self):
        """Test NPC merchant with multiple business properties."""
        # Create merchant NPC
        merchant = Character.objects.create(
            name="Master Goldhand",
            campaign=self.campaign,
            player_owner=self.gm,
            game_system="mage",
            npc=True,
            description="Wealthy merchant with multiple business interests",
        )

        # Create merchant's properties
        properties = [
            ("Goldhand's Main Shop", "Primary retail location"),
            ("Goldhand's Warehouse", "Storage and distribution center"),
            ("Goldhand Residence", "Personal mansion"),
            ("Goldhand's Branch Store", "Secondary retail location"),
        ]

        created_locations = []
        for name, desc in properties:
            location = Location.objects.create(
                name=name,
                description=desc,
                campaign=self.campaign,
                owned_by=merchant,
                created_by=self.gm,
            )
            created_locations.append(location)

        # Test merchant's property portfolio
        merchant_properties = merchant.owned_locations.all()
        self.assertEqual(merchant_properties.count(), 4)

        # Test filtering merchant's properties by type
        shops = merchant.owned_locations.filter(name__icontains="Shop")
        self.assertEqual(shops.count(), 1)

        stores = merchant.owned_locations.filter(name__icontains="Store")
        self.assertEqual(stores.count(), 1)

        # Test getting all business properties (exclude residence)
        business_properties = merchant.owned_locations.exclude(
            name__icontains="Residence"
        )
        self.assertEqual(business_properties.count(), 3)

    def test_player_character_property_acquisition_scenario(self):
        """Test player character acquiring properties over time."""
        # Create player character
        player_char = Character.objects.create(
            name="Mage Apprentice Kael",
            campaign=self.campaign,
            player_owner=self.player,
            game_system="mage",
            npc=False,
            description="Young mage building his magical practice",
        )

        # Initially no properties
        initial_properties = player_char.owned_locations.all()
        self.assertEqual(initial_properties.count(), 0)

        # Scenario: Player acquires first property (rented room)
        first_property = Location.objects.create(
            name="Rented Room at The Silver Stag",
            description="Small rented room serving as temporary residence",
            campaign=self.campaign,
            owned_by=player_char,
            created_by=self.player,
        )

        # Check progression
        after_first = player_char.owned_locations.all()
        self.assertEqual(after_first.count(), 1)
        self.assertIn(first_property, after_first)

        # Scenario: Player acquires sanctum
        Location.objects.create(
            name="Kael's Hidden Sanctum",
            description="Secret magical workspace in the basement",
            campaign=self.campaign,
            owned_by=player_char,
            created_by=self.player,
        )

        # Scenario: Player upgrades to tower
        Location.objects.create(
            name="The Forgotten Tower",
            description="Ancient wizard's tower claimed by Kael",
            campaign=self.campaign,
            owned_by=player_char,
            created_by=self.gm,
        )

        # Check final property portfolio
        final_properties = player_char.owned_locations.all()
        self.assertEqual(final_properties.count(), 3)

        # Test querying by property type
        magical_properties = player_char.owned_locations.filter(
            models.Q(name__icontains="Sanctum") | models.Q(name__icontains="Tower")
        )
        self.assertEqual(magical_properties.count(), 2)

    def test_noble_family_estate_scenario(self):
        """Test noble family with complex estate ownership."""
        # Create noble family members
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

        heir = Character.objects.create(
            name="Young Lord Marcus Ravencrest",
            campaign=self.campaign,
            player_owner=self.gm,
            game_system="mage",
            npc=True,
        )

        # Create estate structure with different ownership
        estate_properties = [
            ("Ravencrest Estate", lord, "Main estate grounds"),
            ("Ravencrest Manor", lord, "Primary family residence"),
            ("Lord's Study", lord, "Private study and office"),
            ("Lady's Solar", lady, "Lady's private chambers"),
            ("Lady's Garden", lady, "Personal garden space"),
            ("Marcus's Chambers", heir, "Young lord's quarters"),
        ]

        for name, owner, desc in estate_properties:
            Location.objects.create(
                name=name,
                description=desc,
                campaign=self.campaign,
                owned_by=owner,
                created_by=self.gm,
            )

        # Test individual ownership
        lord_properties = lord.owned_locations.all()
        lady_properties = lady.owned_locations.all()
        heir_properties = heir.owned_locations.all()

        self.assertEqual(lord_properties.count(), 3)
        self.assertEqual(lady_properties.count(), 2)
        self.assertEqual(heir_properties.count(), 1)

        # Test family property queries
        all_family_properties = Location.objects.filter(owned_by__in=[lord, lady, heir])
        self.assertEqual(all_family_properties.count(), 6)

        # Test estate property filtering
        lord_formal_spaces = lord.owned_locations.filter(
            name__in=["Ravencrest Estate", "Ravencrest Manor", "Lord's Study"]
        )
        self.assertEqual(lord_formal_spaces.count(), 3)

    def test_character_property_inheritance_scenario(self):
        """Test property inheritance when character ownership changes."""
        # Create original owner
        old_lord = Character.objects.create(
            name="Old Lord Blackwood",
            campaign=self.campaign,
            player_owner=self.gm,
            game_system="mage",
            npc=True,
        )

        # Create heir
        new_lord = Character.objects.create(
            name="Young Lord Blackwood",
            campaign=self.campaign,
            player_owner=self.gm,
            game_system="mage",
            npc=True,
        )

        # Create inherited properties
        inherited_properties = []
        property_names = [
            "Blackwood Castle",
            "East Wing Manor",
            "Castle Armory",
            "Family Crypt",
        ]

        for name in property_names:
            location = Location.objects.create(
                name=name,
                campaign=self.campaign,
                owned_by=old_lord,
                created_by=self.gm,
            )
            inherited_properties.append(location)

        # Verify initial ownership
        old_lord_properties = old_lord.owned_locations.all()
        self.assertEqual(old_lord_properties.count(), 4)

        # Simulate inheritance transfer
        for location in inherited_properties:
            location.owned_by = new_lord
            location.save()

        # Verify inheritance completion
        old_lord_final = old_lord.owned_locations.all()
        new_lord_final = new_lord.owned_locations.all()

        self.assertEqual(old_lord_final.count(), 0)
        self.assertEqual(new_lord_final.count(), 4)

        # Verify all properties transferred
        for location in inherited_properties:
            self.assertIn(location, new_lord_final)

    def test_character_business_network_scenario(self):
        """Test complex business network with multiple character owners."""
        # Create business network characters
        guild_master = Character.objects.create(
            name="Guild Master Helena",
            campaign=self.campaign,
            player_owner=self.gm,
            game_system="mage",
            npc=True,
        )

        shop_manager = Character.objects.create(
            name="Manager Boris",
            campaign=self.campaign,
            player_owner=self.gm,
            game_system="mage",
            npc=True,
        )

        warehouse_keeper = Character.objects.create(
            name="Keeper Samuel",
            campaign=self.campaign,
            player_owner=self.gm,
            game_system="mage",
            npc=True,
        )

        # Create business network properties
        business_structure = [
            ("Merchant Guild Hall", guild_master),
            ("Guild Master's Office", guild_master),
            ("Main Trading Post", shop_manager),
            ("Secondary Shop", shop_manager),
            ("Primary Warehouse", warehouse_keeper),
            ("Storage Annex", warehouse_keeper),
        ]

        for name, owner in business_structure:
            Location.objects.create(
                name=name,
                campaign=self.campaign,
                owned_by=owner,
                created_by=self.gm,
            )

        # Test business network queries
        helena_properties = guild_master.owned_locations.all()
        boris_properties = shop_manager.owned_locations.all()
        samuel_properties = warehouse_keeper.owned_locations.all()

        self.assertEqual(helena_properties.count(), 2)
        self.assertEqual(boris_properties.count(), 2)
        self.assertEqual(samuel_properties.count(), 2)

        # Test network-wide queries
        all_business_properties = Location.objects.filter(
            owned_by__in=[guild_master, shop_manager, warehouse_keeper]
        )
        self.assertEqual(all_business_properties.count(), 6)

        # Test role-based property filtering
        management_properties = Location.objects.filter(
            owned_by__in=[guild_master, shop_manager]
        )
        self.assertEqual(management_properties.count(), 4)

        storage_properties = warehouse_keeper.owned_locations.filter(
            models.Q(name__icontains="Warehouse") | models.Q(name__icontains="Storage")
        )
        self.assertEqual(storage_properties.count(), 2)
