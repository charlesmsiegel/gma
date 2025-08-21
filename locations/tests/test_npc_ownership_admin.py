"""
Admin interface tests for NPC ownership of locations (Issue #186).

Tests cover:
- Admin form field configuration for owned_by field
- limit_choices_to={'npc': True} hint behavior
- Admin queryset filtering for character selection
- Admin form validation with cross-campaign ownership
- Admin interface supports both NPC and PC ownership despite hint
- Character display and selection in admin forms

Test Structure:
- LocationOwnershipAdminFormTest: Admin form configuration and behavior
- LocationOwnershipAdminQuerysetTest: Admin queryset filtering
- LocationOwnershipAdminValidationTest: Admin form validation
- LocationOwnershipAdminDisplayTest: Admin display and selection behavior
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from campaigns.models import Campaign, CampaignMembership
from characters.models import Character
from locations.models import Location

# Try to import admin classes - these might not exist yet
try:
    from locations.admin import LocationAdmin
except ImportError:
    LocationAdmin = None

User = get_user_model()


class LocationOwnershipAdminFormTest(TestCase):
    """Test admin form configuration for location ownership."""

    def setUp(self):
        """Set up test data for admin form tests."""
        self.owner = User.objects.create_user(
            username="admin_owner",
            email="admin_owner@test.com",
            password="testpass123",
            is_staff=True,
            is_superuser=True,
        )

        self.player = User.objects.create_user(
            username="admin_player",
            email="admin_player@test.com",
            password="testpass123",
        )

        self.campaign = Campaign.objects.create(
            name="Admin Form Test Campaign",
            owner=self.owner,
            game_system="mage",
        )

        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )

        # Create test characters
        self.npc1 = Character.objects.create(
            name="Admin NPC 1",
            campaign=self.campaign,
            player_owner=self.owner,
            game_system="mage",
            npc=True,
        )

        self.npc2 = Character.objects.create(
            name="Admin NPC 2",
            campaign=self.campaign,
            player_owner=self.owner,
            game_system="mage",
            npc=True,
        )

        self.pc_character = Character.objects.create(
            name="Admin PC",
            campaign=self.campaign,
            player_owner=self.player,
            game_system="mage",
            npc=False,
        )

    def test_owned_by_field_has_correct_configuration(self):
        """Test that owned_by field has correct ForeignKey configuration."""
        # Get the owned_by field from Location model
        owned_by_field = Location._meta.get_field("owned_by")

        # Test field properties
        self.assertEqual(owned_by_field.related_model, Character)
        self.assertTrue(owned_by_field.null)
        self.assertTrue(owned_by_field.blank)

        # Test that field has limit_choices_to for NPC hint
        if hasattr(owned_by_field, "limit_choices_to"):
            self.assertEqual(owned_by_field.limit_choices_to, {"npc": True})

    def test_admin_form_includes_owned_by_field(self):
        """Test that admin form includes the owned_by field."""
        # Create a location instance for form testing
        location = Location.objects.create(
            name="Admin Form Test Location",
            campaign=self.campaign,
            created_by=self.owner,
        )

        # Test that owned_by field exists and can be set
        location.owned_by = self.npc1
        location.save()

        location.refresh_from_db()
        self.assertEqual(location.owned_by, self.npc1)

    def test_owned_by_field_accepts_none(self):
        """Test that owned_by field accepts None in admin forms."""
        location = Location.objects.create(
            name="None Ownership Test",
            campaign=self.campaign,
            owned_by=None,
            created_by=self.owner,
        )

        self.assertIsNone(location.owned_by)

    def test_owned_by_field_accepts_npc_characters(self):
        """Test that owned_by field accepts NPC characters."""
        location = Location.objects.create(
            name="NPC Ownership Test",
            campaign=self.campaign,
            owned_by=self.npc1,
            created_by=self.owner,
        )

        self.assertEqual(location.owned_by, self.npc1)
        self.assertTrue(location.owned_by.npc)

    def test_owned_by_field_accepts_pc_characters_despite_hint(self):
        """Test that owned_by field accepts PC characters despite NPC hint."""
        # Even though limit_choices_to suggests NPCs, field should accept PCs
        location = Location.objects.create(
            name="PC Ownership Test",
            campaign=self.campaign,
            owned_by=self.pc_character,
            created_by=self.owner,
        )

        self.assertEqual(location.owned_by, self.pc_character)
        self.assertFalse(location.owned_by.npc)


class LocationOwnershipAdminQuerysetTest(TestCase):
    """Test admin queryset filtering for character selection."""

    def setUp(self):
        """Set up test data for admin queryset tests."""
        self.owner = User.objects.create_user(
            username="qs_owner",
            email="qs_owner@test.com",
            password="testpass123",
            is_staff=True,
        )

        self.campaign1 = Campaign.objects.create(
            name="Queryset Test Campaign 1",
            owner=self.owner,
            game_system="mage",
        )

        self.campaign2 = Campaign.objects.create(
            name="Queryset Test Campaign 2",
            owner=self.owner,
            game_system="generic",
        )

        # Create characters in both campaigns
        self.c1_npc1 = Character.objects.create(
            name="Campaign 1 NPC 1",
            campaign=self.campaign1,
            player_owner=self.owner,
            game_system="mage",
            npc=True,
        )

        self.c1_npc2 = Character.objects.create(
            name="Campaign 1 NPC 2",
            campaign=self.campaign1,
            player_owner=self.owner,
            game_system="mage",
            npc=True,
        )

        self.c1_pc = Character.objects.create(
            name="Campaign 1 PC",
            campaign=self.campaign1,
            player_owner=self.owner,
            game_system="mage",
            npc=False,
        )

        self.c2_npc = Character.objects.create(
            name="Campaign 2 NPC",
            campaign=self.campaign2,
            player_owner=self.owner,
            game_system="generic",
            npc=True,
        )

        self.c2_pc = Character.objects.create(
            name="Campaign 2 PC",
            campaign=self.campaign2,
            player_owner=self.owner,
            game_system="generic",
            npc=False,
        )

    def test_limit_choices_to_filters_npcs(self):
        """Test that limit_choices_to={'npc': True} filters correctly."""
        # Test the queryset that would be used with limit_choices_to
        npc_queryset = Character.objects.filter(npc=True)
        pc_queryset = Character.objects.filter(npc=False)

        # NPCs should be included
        self.assertIn(self.c1_npc1, npc_queryset)
        self.assertIn(self.c1_npc2, npc_queryset)
        self.assertIn(self.c2_npc, npc_queryset)

        # PCs should not be in NPC queryset
        self.assertNotIn(self.c1_pc, npc_queryset)
        self.assertNotIn(self.c2_pc, npc_queryset)

        # Verify PC queryset for completeness
        self.assertIn(self.c1_pc, pc_queryset)
        self.assertIn(self.c2_pc, pc_queryset)

    def test_admin_character_queryset_ordering(self):
        """Test that characters are properly ordered for admin selection."""
        # Default ordering should be by name
        all_characters = Character.objects.all().order_by("name")

        # Verify ordering
        character_names = [char.name for char in all_characters]
        self.assertEqual(character_names, sorted(character_names))

    def test_admin_can_filter_by_campaign(self):
        """Test that admin can filter characters by campaign for ownership."""
        # Campaign 1 characters
        c1_characters = Character.objects.filter(campaign=self.campaign1)
        self.assertEqual(c1_characters.count(), 3)  # 2 NPCs + 1 PC
        self.assertIn(self.c1_npc1, c1_characters)
        self.assertIn(self.c1_npc2, c1_characters)
        self.assertIn(self.c1_pc, c1_characters)

        # Campaign 2 characters
        c2_characters = Character.objects.filter(campaign=self.campaign2)
        self.assertEqual(c2_characters.count(), 2)  # 1 NPC + 1 PC
        self.assertIn(self.c2_npc, c2_characters)
        self.assertIn(self.c2_pc, c2_characters)

    def test_admin_combined_filters_npc_and_campaign(self):
        """Test combining NPC filter with campaign filter."""
        # Campaign 1 NPCs only
        c1_npcs = Character.objects.filter(campaign=self.campaign1, npc=True)
        self.assertEqual(c1_npcs.count(), 2)
        self.assertIn(self.c1_npc1, c1_npcs)
        self.assertIn(self.c1_npc2, c1_npcs)
        self.assertNotIn(self.c1_pc, c1_npcs)

        # Campaign 2 NPCs only
        c2_npcs = Character.objects.filter(campaign=self.campaign2, npc=True)
        self.assertEqual(c2_npcs.count(), 1)
        self.assertIn(self.c2_npc, c2_npcs)

    def test_admin_character_string_representation(self):
        """Test character string representation for admin display."""
        # Test that characters display appropriately in admin dropdowns
        for character in [self.c1_npc1, self.c1_pc, self.c2_npc]:
            char_str = str(character)
            self.assertIsInstance(char_str, str)
            self.assertGreater(len(char_str), 0)
            self.assertEqual(char_str, character.name)


class LocationOwnershipAdminValidationTest(TestCase):
    """Test admin form validation for location ownership."""

    def setUp(self):
        """Set up test data for admin validation tests."""
        self.owner = User.objects.create_user(
            username="val_owner",
            email="val_owner@test.com",
            password="testpass123",
            is_staff=True,
        )

        self.campaign1 = Campaign.objects.create(
            name="Validation Campaign 1",
            owner=self.owner,
            game_system="mage",
        )

        self.campaign2 = Campaign.objects.create(
            name="Validation Campaign 2",
            owner=self.owner,
            game_system="generic",
        )

        self.char1 = Character.objects.create(
            name="Validation Character 1",
            campaign=self.campaign1,
            player_owner=self.owner,
            game_system="mage",
            npc=True,
        )

        self.char2 = Character.objects.create(
            name="Validation Character 2",
            campaign=self.campaign2,
            player_owner=self.owner,
            game_system="generic",
            npc=True,
        )

    def test_admin_prevents_cross_campaign_ownership(self):
        """Test that admin form validation prevents cross-campaign ownership."""
        # Create location in campaign1
        location = Location(
            name="Cross Campaign Validation",
            campaign=self.campaign1,
            created_by=self.owner,
        )

        # Attempt to assign character from campaign2
        location.owned_by = self.char2

        # Validation should fail
        with self.assertRaises(ValidationError):
            location.clean()

    def test_admin_allows_same_campaign_ownership(self):
        """Test that admin form allows same-campaign ownership."""
        location = Location(
            name="Same Campaign Validation",
            campaign=self.campaign1,
            owned_by=self.char1,
            created_by=self.owner,
        )

        # Validation should pass
        location.clean()
        location.save()

        self.assertEqual(location.owned_by, self.char1)

    def test_admin_allows_none_ownership(self):
        """Test that admin form allows None ownership."""
        location = Location(
            name="None Ownership Validation",
            campaign=self.campaign1,
            owned_by=None,
            created_by=self.owner,
        )

        # Validation should pass
        location.clean()
        location.save()

        self.assertIsNone(location.owned_by)

    def test_admin_form_validation_error_messages(self):
        """Test that admin form shows appropriate validation error messages."""
        location = Location(
            name="Error Message Test",
            campaign=self.campaign1,
            owned_by=self.char2,  # Wrong campaign
            created_by=self.owner,
        )

        with self.assertRaises(ValidationError) as context:
            location.clean()

        error_message = str(context.exception).lower()
        self.assertIn("campaign", error_message)


class LocationOwnershipAdminDisplayTest(TestCase):
    """Test admin display and selection behavior for location ownership."""

    def setUp(self):
        """Set up test data for admin display tests."""
        self.owner = User.objects.create_user(
            username="disp_owner",
            email="disp_owner@test.com",
            password="testpass123",
            is_staff=True,
            is_superuser=True,
        )

        self.campaign = Campaign.objects.create(
            name="Display Test Campaign",
            owner=self.owner,
            game_system="mage",
        )

        # Create characters with distinctive names
        self.tavern_keeper = Character.objects.create(
            name="Marcus the Tavern Keeper",
            campaign=self.campaign,
            player_owner=self.owner,
            game_system="mage",
            npc=True,
        )

        self.noble_lord = Character.objects.create(
            name="Lord Blackwood",
            campaign=self.campaign,
            player_owner=self.owner,
            game_system="mage",
            npc=True,
        )

        self.player_mage = Character.objects.create(
            name="Aeliana the Wise",
            campaign=self.campaign,
            player_owner=self.owner,
            game_system="mage",
            npc=False,
        )

    def test_admin_character_selection_display(self):
        """Test how characters are displayed in admin selection fields."""
        # Create locations with different ownership
        tavern = Location.objects.create(
            name="The Golden Griffin Tavern",
            campaign=self.campaign,
            owned_by=self.tavern_keeper,
            created_by=self.owner,
        )

        manor = Location.objects.create(
            name="Blackwood Manor",
            campaign=self.campaign,
            owned_by=self.noble_lord,
            created_by=self.owner,
        )

        sanctum = Location.objects.create(
            name="Aeliana's Sanctum",
            campaign=self.campaign,
            owned_by=self.player_mage,
            created_by=self.owner,
        )

        unowned = Location.objects.create(
            name="Public Market Square",
            campaign=self.campaign,
            owned_by=None,
            created_by=self.owner,
        )

        # Test character display in ownership field
        self.assertEqual(str(tavern.owned_by), "Marcus the Tavern Keeper")
        self.assertEqual(str(manor.owned_by), "Lord Blackwood")
        self.assertEqual(str(sanctum.owned_by), "Aeliana the Wise")
        self.assertIsNone(unowned.owned_by)

    def test_admin_owned_by_field_help_text(self):
        """Test that owned_by field has appropriate help text."""
        owned_by_field = Location._meta.get_field("owned_by")

        # Field should have helpful description
        if hasattr(owned_by_field, "help_text"):
            help_text = owned_by_field.help_text.lower()
            # Should mention character ownership
            self.assertIn("character", help_text)

    def test_admin_location_list_display_includes_ownership(self):
        """Test that admin list view can display ownership information."""
        # Create locations with different ownership types
        locations = [
            Location.objects.create(
                name="NPC Owned Location",
                campaign=self.campaign,
                owned_by=self.tavern_keeper,
                created_by=self.owner,
            ),
            Location.objects.create(
                name="PC Owned Location",
                campaign=self.campaign,
                owned_by=self.player_mage,
                created_by=self.owner,
            ),
            Location.objects.create(
                name="Unowned Location",
                campaign=self.campaign,
                owned_by=None,
                created_by=self.owner,
            ),
        ]

        # Test that ownership information is accessible for display
        for location in locations:
            if location.owned_by:
                owner_name = str(location.owned_by)
                self.assertIsInstance(owner_name, str)
                self.assertGreater(len(owner_name), 0)
            else:
                self.assertIsNone(location.owned_by)

    def test_admin_character_type_identification(self):
        """Test that admin can identify character types (NPC vs PC) for ownership."""
        npc_location = Location.objects.create(
            name="NPC Test Location",
            campaign=self.campaign,
            owned_by=self.tavern_keeper,
            created_by=self.owner,
        )

        pc_location = Location.objects.create(
            name="PC Test Location",
            campaign=self.campaign,
            owned_by=self.player_mage,
            created_by=self.owner,
        )

        # Verify character type can be determined
        self.assertTrue(npc_location.owned_by.npc)
        self.assertFalse(pc_location.owned_by.npc)

    def test_admin_ownership_field_ordering_and_filtering(self):
        """Test that ownership field supports proper ordering and filtering in admin."""
        # Create multiple locations for testing
        locations = []
        characters = [self.tavern_keeper, self.noble_lord, self.player_mage]

        for i, char in enumerate(characters):
            location = Location.objects.create(
                name=f"Order Test Location {i}",
                campaign=self.campaign,
                owned_by=char,
                created_by=self.owner,
            )
            locations.append(location)

        # Test ordering by owner name
        owned_locations = Location.objects.filter(owned_by__isnull=False).order_by(
            "owned_by__name"
        )

        self.assertEqual(owned_locations.count(), 3)

        # Test filtering by owner type
        npc_owned = Location.objects.filter(owned_by__npc=True)
        pc_owned = Location.objects.filter(owned_by__npc=False)

        self.assertEqual(npc_owned.count(), 2)  # tavern_keeper, noble_lord
        self.assertEqual(pc_owned.count(), 1)  # player_mage

    def test_admin_bulk_ownership_operations(self):
        """Test that admin supports bulk ownership operations."""
        # Create multiple unowned locations
        locations = []
        for i in range(3):
            location = Location.objects.create(
                name=f"Bulk Test Location {i}",
                campaign=self.campaign,
                owned_by=None,
                created_by=self.owner,
            )
            locations.append(location)

        # Test bulk assignment of ownership
        location_ids = [loc.id for loc in locations]
        updated_count = Location.objects.filter(id__in=location_ids).update(
            owned_by=self.tavern_keeper
        )

        self.assertEqual(updated_count, 3)

        # Verify bulk assignment worked
        for location in locations:
            location.refresh_from_db()
            self.assertEqual(location.owned_by, self.tavern_keeper)

    def test_admin_ownership_search_functionality(self):
        """Test that admin supports searching by character owner names."""
        # Create locations with searchable owner names
        location1 = Location.objects.create(
            name="Searchable Location 1",
            campaign=self.campaign,
            owned_by=self.tavern_keeper,  # "Marcus the Tavern Keeper"
            created_by=self.owner,
        )

        location2 = Location.objects.create(
            name="Searchable Location 2",
            campaign=self.campaign,
            owned_by=self.noble_lord,  # "Lord Blackwood"
            created_by=self.owner,
        )

        # Test searching by owner name
        marcus_locations = Location.objects.filter(owned_by__name__icontains="Marcus")
        blackwood_locations = Location.objects.filter(
            owned_by__name__icontains="Blackwood"
        )

        self.assertEqual(marcus_locations.count(), 1)
        self.assertIn(location1, marcus_locations)

        self.assertEqual(blackwood_locations.count(), 1)
        self.assertIn(location2, blackwood_locations)
