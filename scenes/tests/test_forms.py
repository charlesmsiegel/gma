"""
Tests for scene forms.

Tests form validation, field requirements, and form save methods for Issues 37-40:
- Issue 37: Scene creation and management forms
- Issue 38: Character participation forms
- Issue 40: Scene status management forms
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from campaigns.models import Campaign, CampaignMembership
from characters.models import Character
from scenes.models import Scene

User = get_user_model()


class SceneFormTest(TestCase):
    """Test the scene creation and editing forms."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="TestPass123!"
        )
        self.gm = User.objects.create_user(
            username="gm", email="gm@test.com", password="TestPass123!"
        )

        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.user,
            game_system="Mage: The Ascension",
        )

        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm, role="GM"
        )

    def test_scene_form_valid_data(self):
        """Test scene form with valid data."""
        from scenes.forms import SceneForm

        form_data = {
            "name": "Valid Scene",
            "description": "A valid scene description",
        }

        form = SceneForm(data=form_data)

        self.assertTrue(form.is_valid())

    def test_scene_form_required_name(self):
        """Test that name field is required."""
        from scenes.forms import SceneForm

        form_data = {
            "description": "Missing name field",
        }

        form = SceneForm(data=form_data)

        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_scene_form_optional_description(self):
        """Test that description is optional."""
        from scenes.forms import SceneForm

        form_data = {
            "name": "Minimal Scene",
        }

        form = SceneForm(data=form_data)

        self.assertTrue(form.is_valid())

    def test_scene_form_name_max_length(self):
        """Test that name field enforces max length."""
        from scenes.forms import SceneForm

        form_data = {
            "name": "x" * 201,  # Scene model has max_length=200
            "description": "Testing max length",
        }

        form = SceneForm(data=form_data)

        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_scene_form_save_method(self):
        """Test that form save method creates scene with proper fields."""
        from scenes.forms import SceneForm

        form_data = {
            "name": "Form Save Test",
            "description": "Testing form save method",
        }

        form = SceneForm(data=form_data)
        self.assertTrue(form.is_valid())

        scene = form.save(campaign=self.campaign, created_by=self.gm)

        self.assertEqual(scene.name, "Form Save Test")
        self.assertEqual(scene.description, "Testing form save method")
        self.assertEqual(scene.campaign, self.campaign)
        self.assertEqual(scene.created_by, self.gm)
        self.assertEqual(scene.status, "ACTIVE")  # Default status

    def test_scene_form_save_commit_false(self):
        """Test form save with commit=False returns unsaved instance."""
        from scenes.forms import SceneForm

        form_data = {
            "name": "Uncommitted Scene",
            "description": "Testing commit=False",
        }

        form = SceneForm(data=form_data)
        self.assertTrue(form.is_valid())

        scene = form.save(commit=False)

        self.assertEqual(scene.name, "Uncommitted Scene")
        self.assertIsNone(scene.pk)  # Not saved to database

        # Manually set required fields and save
        scene.campaign = self.campaign
        scene.created_by = self.gm
        scene.save()

        self.assertIsNotNone(scene.pk)

    def test_scene_form_update_existing(self):
        """Test updating an existing scene via form."""
        from scenes.forms import SceneForm

        # Create initial scene
        scene = Scene.objects.create(
            name="Original Name",
            description="Original description",
            campaign=self.campaign,
            created_by=self.gm,
        )

        # Update via form
        form_data = {
            "name": "Updated Name",
            "description": "Updated description",
        }

        form = SceneForm(data=form_data, instance=scene)
        self.assertTrue(form.is_valid())

        updated_scene = form.save()

        self.assertEqual(updated_scene.pk, scene.pk)
        self.assertEqual(updated_scene.name, "Updated Name")
        self.assertEqual(updated_scene.description, "Updated description")
        # Should preserve original fields
        self.assertEqual(updated_scene.campaign, self.campaign)
        self.assertEqual(updated_scene.created_by, self.gm)

    def test_scene_form_clean_name_whitespace(self):
        """Test that form cleans whitespace from name."""
        from scenes.forms import SceneForm

        form_data = {
            "name": "  Whitespace Scene  ",
            "description": "Testing whitespace handling",
        }

        form = SceneForm(data=form_data)
        self.assertTrue(form.is_valid())

        cleaned_name = form.cleaned_data["name"]
        self.assertEqual(cleaned_name, "Whitespace Scene")

    def test_scene_form_widget_attributes(self):
        """Test that form widgets have proper HTML attributes."""
        from scenes.forms import SceneForm

        form = SceneForm()

        # Check that name field has proper attributes
        name_widget = form.fields["name"].widget
        self.assertIn("class", name_widget.attrs)
        self.assertIn("form-control", name_widget.attrs["class"])

        # Check that description field is textarea
        description_widget = form.fields["description"].widget
        self.assertEqual(description_widget.__class__.__name__, "Textarea")


class SceneParticipantFormTest(TestCase):
    """Test forms related to scene participant management."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="TestPass123!"
        )
        self.player = User.objects.create_user(
            username="player", email="player@test.com", password="TestPass123!"
        )

        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.user,
            game_system="Mage: The Ascension",
        )

        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )

        self.character1 = Character.objects.create(
            name="Test Character 1",
            campaign=self.campaign,
            player_owner=self.player,
        )
        self.character2 = Character.objects.create(
            name="Test Character 2",
            campaign=self.campaign,
            player_owner=self.user,
        )

        self.scene = Scene.objects.create(
            name="Test Scene",
            campaign=self.campaign,
            created_by=self.user,
        )

    def test_add_participant_form_valid(self):
        """Test valid participant addition form."""
        from scenes.forms import AddParticipantForm

        form_data = {
            "character": self.character1.pk,
        }

        form = AddParticipantForm(data=form_data, scene=self.scene)

        self.assertTrue(form.is_valid())

    def test_add_participant_form_requires_character(self):
        """Test that character selection is required."""
        from scenes.forms import AddParticipantForm

        form_data = {}

        form = AddParticipantForm(data=form_data, scene=self.scene)

        self.assertFalse(form.is_valid())
        self.assertIn("character", form.errors)

    def test_add_participant_form_filters_by_campaign(self):
        """Test that form only shows characters from the scene's campaign."""
        from scenes.forms import AddParticipantForm

        # Create character in different campaign
        other_campaign = Campaign.objects.create(
            name="Other Campaign",
            owner=self.user,
        )
        other_character = Character.objects.create(
            name="Other Character",
            campaign=other_campaign,
            player_owner=self.user,
        )

        form = AddParticipantForm(scene=self.scene)

        # Check queryset only includes campaign characters
        character_ids = [
            choice[0] for choice in form.fields["character"].choices if choice[0]
        ]

        self.assertIn(self.character1.pk, character_ids)
        self.assertIn(self.character2.pk, character_ids)
        self.assertNotIn(other_character.pk, character_ids)

    def test_add_participant_form_excludes_current_participants(self):
        """Test that form excludes characters already participating."""
        from scenes.forms import AddParticipantForm

        # Add character1 to scene
        self.scene.participants.add(self.character1)

        form = AddParticipantForm(scene=self.scene)

        # Check queryset excludes already participating character
        character_ids = [
            choice[0] for choice in form.fields["character"].choices if choice[0]
        ]

        self.assertNotIn(self.character1.pk, character_ids)
        self.assertIn(self.character2.pk, character_ids)

    def test_add_participant_form_save_method(self):
        """Test that form save method adds participant to scene."""
        from scenes.forms import AddParticipantForm

        form_data = {
            "character": self.character1.pk,
        }

        form = AddParticipantForm(data=form_data, scene=self.scene)
        self.assertTrue(form.is_valid())

        form.save()

        self.assertTrue(self.scene.participants.filter(pk=self.character1.pk).exists())

    def test_add_participant_form_invalid_character(self):
        """Test form validation with invalid character ID."""
        from scenes.forms import AddParticipantForm

        form_data = {
            "character": 99999,  # Non-existent character
        }

        form = AddParticipantForm(data=form_data, scene=self.scene)

        self.assertFalse(form.is_valid())
        self.assertIn("character", form.errors)

    def test_bulk_add_participants_form(self):
        """Test form for adding multiple participants at once."""
        from scenes.forms import BulkAddParticipantsForm

        form_data = {
            "characters": [self.character1.pk, self.character2.pk],
        }

        form = BulkAddParticipantsForm(data=form_data, scene=self.scene)

        self.assertTrue(form.is_valid())

    def test_bulk_add_participants_form_save(self):
        """Test bulk participant addition form save method."""
        from scenes.forms import BulkAddParticipantsForm

        form_data = {
            "characters": [self.character1.pk, self.character2.pk],
        }

        form = BulkAddParticipantsForm(data=form_data, scene=self.scene)
        self.assertTrue(form.is_valid())

        added_count = form.save()

        self.assertEqual(added_count, 2)
        self.assertTrue(self.scene.participants.filter(pk=self.character1.pk).exists())
        self.assertTrue(self.scene.participants.filter(pk=self.character2.pk).exists())


class SceneStatusChangeFormTest(TestCase):
    """Test scene status change form."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="TestPass123!"
        )

        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.user,
            game_system="Mage: The Ascension",
        )

        self.scene = Scene.objects.create(
            name="Test Scene",
            campaign=self.campaign,
            created_by=self.user,
            status="ACTIVE",
        )

    def test_status_change_form_valid(self):
        """Test valid status change form."""
        from scenes.forms import SceneStatusChangeForm

        form_data = {
            "status": "CLOSED",
        }

        form = SceneStatusChangeForm(data=form_data, instance=self.scene)

        self.assertTrue(form.is_valid())

    def test_status_change_form_valid_transitions(self):
        """Test that form validates proper status transitions."""
        from scenes.forms import SceneStatusChangeForm

        # ACTIVE -> CLOSED should be valid
        form = SceneStatusChangeForm(data={"status": "CLOSED"}, instance=self.scene)
        self.assertTrue(form.is_valid())

        # Update scene status
        self.scene.status = "CLOSED"
        self.scene.save()

        # CLOSED -> ARCHIVED should be valid
        form = SceneStatusChangeForm(data={"status": "ARCHIVED"}, instance=self.scene)
        self.assertTrue(form.is_valid())

    def test_status_change_form_invalid_transitions(self):
        """Test that form rejects invalid status transitions."""
        from scenes.forms import SceneStatusChangeForm

        # ACTIVE -> ARCHIVED should be invalid (must go through CLOSED)
        form_data = {
            "status": "ARCHIVED",
        }

        form = SceneStatusChangeForm(data=form_data, instance=self.scene)

        self.assertFalse(form.is_valid())
        self.assertIn("status", form.errors)

    def test_status_change_form_no_change(self):
        """Test that form handles status not changing."""
        from scenes.forms import SceneStatusChangeForm

        form_data = {
            "status": "ACTIVE",  # Same as current status
        }

        form = SceneStatusChangeForm(data=form_data, instance=self.scene)

        # Should be valid but indicate no change needed
        self.assertTrue(form.is_valid())

        # Save should return False indicating no change
        changed = form.save()
        self.assertFalse(changed)

    def test_status_change_form_save_method(self):
        """Test that form save method properly updates status."""
        from scenes.forms import SceneStatusChangeForm

        form_data = {
            "status": "CLOSED",
        }

        form = SceneStatusChangeForm(data=form_data, instance=self.scene)
        self.assertTrue(form.is_valid())

        changed = form.save()

        self.assertTrue(changed)
        self.scene.refresh_from_db()
        self.assertEqual(self.scene.status, "CLOSED")

    def test_status_change_form_custom_validation_message(self):
        """Test that form provides helpful validation messages."""
        from scenes.forms import SceneStatusChangeForm

        form_data = {
            "status": "ARCHIVED",
        }

        form = SceneStatusChangeForm(data=form_data, instance=self.scene)

        self.assertFalse(form.is_valid())

        error_message = form.errors["status"][0].lower()
        self.assertIn("closed", error_message)
        self.assertIn("active", error_message)

    def test_status_change_form_choices_filtered(self):
        """Test that status choices are filtered based on current status."""
        from scenes.forms import SceneStatusChangeForm

        form = SceneStatusChangeForm(instance=self.scene)

        # For ACTIVE scenes, should only allow CLOSED
        status_choices = [choice[0] for choice in form.fields["status"].choices]
        self.assertIn("CLOSED", status_choices)
        self.assertNotIn("ARCHIVED", status_choices)

    def test_status_change_form_closed_scene_choices(self):
        """Test status choices for closed scenes."""
        from scenes.forms import SceneStatusChangeForm

        self.scene.status = "CLOSED"
        self.scene.save()

        form = SceneStatusChangeForm(instance=self.scene)

        # For CLOSED scenes, should allow ARCHIVED
        status_choices = [choice[0] for choice in form.fields["status"].choices]
        self.assertIn("ARCHIVED", status_choices)


class SceneSearchFormTest(TestCase):
    """Test scene search and filtering form."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="TestPass123!"
        )

        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.user,
            game_system="Mage: The Ascension",
        )

    def test_search_form_all_fields_optional(self):
        """Test that all search form fields are optional."""
        from scenes.forms import SceneSearchForm

        form = SceneSearchForm(data={}, campaign=self.campaign)

        self.assertTrue(form.is_valid())

    def test_search_form_text_search(self):
        """Test text search functionality."""
        from scenes.forms import SceneSearchForm

        form_data = {
            "search": "dragon battle",
        }

        form = SceneSearchForm(data=form_data, campaign=self.campaign)

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["search"], "dragon battle")

    def test_search_form_status_filter(self):
        """Test status filtering."""
        from scenes.forms import SceneSearchForm

        form_data = {
            "status": "ACTIVE",
        }

        form = SceneSearchForm(data=form_data, campaign=self.campaign)

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["status"], "ACTIVE")

    def test_search_form_participant_filter(self):
        """Test participant filtering."""
        from scenes.forms import SceneSearchForm

        character = Character.objects.create(
            name="Test Character",
            campaign=self.campaign,
            player_owner=self.user,
        )

        form_data = {
            "participant": character.pk,
        }

        form = SceneSearchForm(data=form_data, campaign=self.campaign)

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["participant"], character)

    def test_search_form_date_range_filter(self):
        """Test date range filtering."""
        from datetime import date

        from scenes.forms import SceneSearchForm

        form_data = {
            "date_from": "2024-01-01",
            "date_to": "2024-12-31",
        }

        form = SceneSearchForm(data=form_data, campaign=self.campaign)

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["date_from"], date(2024, 1, 1))
        self.assertEqual(form.cleaned_data["date_to"], date(2024, 12, 31))

    def test_search_form_invalid_date_range(self):
        """Test validation of invalid date range."""
        from scenes.forms import SceneSearchForm

        form_data = {
            "date_from": "2024-12-31",
            "date_to": "2024-01-01",  # End before start
        }

        form = SceneSearchForm(data=form_data, campaign=self.campaign)

        self.assertFalse(form.is_valid())
        self.assertIn("date_to", form.errors)

    def test_search_form_participant_queryset_filtered(self):
        """Test that participant choices are filtered by campaign."""
        from scenes.forms import SceneSearchForm

        # Create characters in different campaigns
        character1 = Character.objects.create(
            name="Campaign Character",
            campaign=self.campaign,
            player_owner=self.user,
        )

        other_campaign = Campaign.objects.create(
            name="Other Campaign",
            owner=self.user,
        )
        character2 = Character.objects.create(
            name="Other Character",
            campaign=other_campaign,
            player_owner=self.user,
        )

        form = SceneSearchForm(campaign=self.campaign)

        # Check that queryset only includes campaign characters
        participant_ids = [
            choice[0] for choice in form.fields["participant"].choices if choice[0]
        ]

        self.assertIn(character1.pk, participant_ids)
        self.assertNotIn(character2.pk, participant_ids)

    def test_search_form_combined_filters(self):
        """Test form with multiple filters combined."""
        from scenes.forms import SceneSearchForm

        character = Character.objects.create(
            name="Test Character",
            campaign=self.campaign,
            player_owner=self.user,
        )

        form_data = {
            "search": "epic battle",
            "status": "ACTIVE",
            "participant": character.pk,
            "date_from": "2024-01-01",
        }

        form = SceneSearchForm(data=form_data, campaign=self.campaign)

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["search"], "epic battle")
        self.assertEqual(form.cleaned_data["status"], "ACTIVE")
        self.assertEqual(form.cleaned_data["participant"], character)

    def test_search_form_apply_filters_method(self):
        """Test that form can apply filters to queryset."""
        from scenes.forms import SceneSearchForm

        # Create test scenes
        scene1 = Scene.objects.create(
            name="Active Battle Scene",
            description="Epic dragon fight",
            campaign=self.campaign,
            created_by=self.user,
            status="ACTIVE",
        )

        Scene.objects.create(
            name="Closed Investigation",
            description="Mystery solving",
            campaign=self.campaign,
            created_by=self.user,
            status="CLOSED",
        )

        form_data = {
            "search": "battle",
            "status": "ACTIVE",
        }

        form = SceneSearchForm(data=form_data, campaign=self.campaign)
        self.assertTrue(form.is_valid())

        # Apply filters to queryset
        queryset = Scene.objects.filter(campaign=self.campaign)
        filtered_queryset = form.apply_filters(queryset)

        # Should only include the active battle scene
        self.assertEqual(filtered_queryset.count(), 1)
        self.assertEqual(filtered_queryset.first(), scene1)
