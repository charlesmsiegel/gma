"""
Tests for Location forms with hierarchy support.

Tests cover:
- Location creation and editing forms
- Hierarchy field validation and filtering
- Permission-based form field restrictions
- Form error handling and user feedback
- AJAX-enabled form interactions
- Bulk operation forms
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from campaigns.models import Campaign, CampaignMembership
from locations.forms import (
    BulkLocationMoveForm,
    LocationCreateForm,
    LocationEditForm,
    LocationForm,
)
from locations.models import Location

User = get_user_model()


class LocationFormTest(TestCase):
    """Test basic Location form functionality."""

    def setUp(self):
        """Set up test data for form tests."""
        self.user = User.objects.create_user(
            username="testuser", email="test@test.com", password="testpass123"
        )
        self.other_user = User.objects.create_user(
            username="otheruser", email="other@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.user,
            game_system="mage",
        )

        self.other_campaign = Campaign.objects.create(
            name="Other Campaign",
            owner=self.other_user,
            game_system="generic",
        )

    def test_location_form_valid_data(self):
        """Test LocationForm with valid data."""
        form_data = {
            "name": "Test Location",
            "description": "A test location description",
            "campaign": self.campaign.id,
            "parent": "",  # No parent
        }

        form = LocationForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())

        # Test that form saves correctly
        location = form.save(commit=False)
        location.created_by = self.user
        location.save()

        self.assertEqual(location.name, "Test Location")
        self.assertEqual(location.campaign, self.campaign)
        self.assertIsNone(location.parent)

    def test_location_form_required_fields(self):
        """Test that required fields are validated."""
        # Test missing name
        form_data = {
            "description": "Description without name",
            "campaign": self.campaign.id,
        }

        form = LocationForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

        # Test missing campaign
        form_data = {
            "name": "Name without campaign",
            "description": "Description",
        }

        form = LocationForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("campaign", form.errors)

    def test_location_form_campaign_filtering(self):
        """Test that campaign field is filtered based on user permissions."""
        # User should only see campaigns they have access to
        form = LocationForm(user=self.user)

        campaign_queryset = form.fields["campaign"].queryset
        self.assertIn(self.campaign, campaign_queryset)
        self.assertNotIn(self.other_campaign, campaign_queryset)

    def test_location_form_parent_filtering(self):
        """Test that parent field is filtered by selected campaign."""
        # Create locations in different campaigns
        location1 = Location.objects.create(
            name="Location 1",
            campaign=self.campaign,
            created_by=self.user,
        )

        location2 = Location.objects.create(
            name="Location 2",
            campaign=self.other_campaign,
            created_by=self.other_user,
        )

        # Form should filter parent options based on campaign
        form_data = {
            "name": "Child Location",
            "campaign": self.campaign.id,
            "parent": location1.id,
        }

        form = LocationForm(data=form_data, user=self.user)

        # Parent field should only show locations from same campaign
        parent_queryset = form.fields["parent"].queryset
        self.assertIn(location1, parent_queryset)
        self.assertNotIn(location2, parent_queryset)

    def test_location_form_circular_reference_validation(self):
        """Test that form prevents circular references."""
        parent = Location.objects.create(
            name="Parent Location",
            campaign=self.campaign,
            created_by=self.user,
        )

        child = Location.objects.create(
            name="Child Location",
            campaign=self.campaign,
            parent=parent,
            created_by=self.user,
        )

        # Try to make parent a child of child
        form_data = {
            "name": "Parent Location",
            "campaign": self.campaign.id,
            "parent": child.id,  # This should cause validation error
        }

        form = LocationForm(data=form_data, user=self.user, instance=parent)
        self.assertFalse(form.is_valid())
        self.assertIn("parent", form.errors)
        self.assertIn("circular", str(form.errors["parent"]).lower())

    def test_location_form_max_depth_validation(self):
        """Test that form enforces maximum depth limit."""
        # Create a chain of 9 locations (max allowed depth - 1)
        locations = []
        parent = None

        for i in range(9):
            location = Location.objects.create(
                name=f"Level {i}",
                campaign=self.campaign,
                parent=parent,
                created_by=self.user,
            )
            locations.append(location)
            parent = location

        # Try to create 10th level location
        form_data = {
            "name": "Level 9 (should work)",
            "campaign": self.campaign.id,
            "parent": locations[-1].id,
        }

        form = LocationForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())  # 10th level (depth 9) should work

        # Now create the 10th level location
        tenth_level = form.save(commit=False)
        tenth_level.created_by = self.user
        tenth_level.save()

        # Try to create 11th level location (should fail)
        form_data = {
            "name": "Level 10 (should fail)",
            "campaign": self.campaign.id,
            "parent": tenth_level.id,
        }

        form = LocationForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("parent", form.errors)
        self.assertIn("maximum depth", str(form.errors["parent"]).lower())


class LocationCreateFormTest(TestCase):
    """Test Location creation form."""

    def setUp(self):
        """Set up test data for creation form tests."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.player = User.objects.create_user(
            username="player", email="player@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Create Form Campaign",
            owner=self.owner,
            game_system="mage",
        )

        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )

    def test_create_form_initial_values(self):
        """Test that create form has appropriate initial values."""
        form = LocationCreateForm(user=self.player, campaign=self.campaign)

        # Campaign should be pre-selected if provided
        self.assertEqual(form.initial.get("campaign"), self.campaign)

        # Parent should be empty initially
        self.assertIsNone(form.initial.get("parent"))

    def test_create_form_campaign_restriction(self):
        """Test that create form restricts campaign choices."""
        form = LocationCreateForm(user=self.player)

        # Player should only see campaigns they're a member of
        campaign_queryset = form.fields["campaign"].queryset
        self.assertIn(self.campaign, campaign_queryset)

    def test_create_form_success(self):
        """Test successful location creation through form."""
        form_data = {
            "name": "New Location",
            "description": "Created through form",
            "campaign": self.campaign.id,
        }

        form = LocationCreateForm(
            data=form_data, user=self.player, campaign=self.campaign
        )
        self.assertTrue(form.is_valid())

        location = form.save()
        self.assertEqual(location.name, "New Location")
        self.assertEqual(location.campaign, self.campaign)
        self.assertEqual(location.created_by, self.player)


class LocationEditFormTest(TestCase):
    """Test Location editing form."""

    def setUp(self):
        """Set up test data for edit form tests."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.player = User.objects.create_user(
            username="player", email="player@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Edit Form Campaign",
            owner=self.owner,
            game_system="mage",
        )

        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )

        self.location = Location.objects.create(
            name="Editable Location",
            campaign=self.campaign,
            created_by=self.player,
        )

    def test_edit_form_initial_values(self):
        """Test that edit form is populated with existing values."""
        form = LocationEditForm(instance=self.location, user=self.player)

        self.assertEqual(form.initial["name"], "Editable Location")
        self.assertEqual(form.initial["campaign"], self.campaign.id)

    def test_edit_form_permission_check(self):
        """Test that edit form checks user permissions."""
        # Player should be able to edit their own location
        form = LocationEditForm(instance=self.location, user=self.player)
        self.assertTrue(hasattr(form, "instance"))

        # Test that form validates permissions during save
        form_data = {
            "name": "Updated Location Name",
            "campaign": self.campaign.id,
        }

        form = LocationEditForm(
            data=form_data, instance=self.location, user=self.player
        )
        self.assertTrue(form.is_valid())

    def test_edit_form_campaign_change_restriction(self):
        """Test that campaign cannot be changed in edit form."""
        form = LocationEditForm(instance=self.location, user=self.player)

        # Campaign field should be disabled or not editable
        if "campaign" in form.fields:
            # If present, should be disabled
            self.assertTrue(form.fields["campaign"].disabled)
        else:
            # Or campaign field should not be present at all
            self.assertNotIn("campaign", form.fields)

    def test_edit_form_hierarchy_modification(self):
        """Test editing location hierarchy through form."""
        parent = Location.objects.create(
            name="New Parent",
            campaign=self.campaign,
            created_by=self.owner,
        )

        form_data = {
            "name": "Editable Location",
            "parent": parent.id,
        }

        form = LocationEditForm(
            data=form_data, instance=self.location, user=self.player
        )
        self.assertTrue(form.is_valid())

        updated_location = form.save()
        self.assertEqual(updated_location.parent, parent)


class BulkLocationFormTest(TestCase):
    """Test bulk operation forms for locations."""

    def setUp(self):
        """Set up test data for bulk form tests."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Bulk Form Campaign",
            owner=self.owner,
            game_system="mage",
        )

        # Create test locations
        self.locations = []
        for i in range(5):
            location = Location.objects.create(
                name=f"Bulk Location {i}",
                campaign=self.campaign,
                created_by=self.owner,
            )
            self.locations.append(location)

        self.new_parent = Location.objects.create(
            name="New Parent",
            campaign=self.campaign,
            created_by=self.owner,
        )

    def test_bulk_move_form_validation(self):
        """Test bulk move form validation."""
        form_data = {
            "new_parent": self.new_parent.id,
            "locations": [loc.id for loc in self.locations[:3]],
        }

        form = BulkLocationMoveForm(
            data=form_data, user=self.owner, campaign=self.campaign
        )
        self.assertTrue(form.is_valid())

    def test_bulk_move_form_permission_check(self):
        """Test that bulk move form checks permissions."""
        # All selected locations should be editable by user
        form_data = {
            "new_parent": self.new_parent.id,
            "locations": [loc.id for loc in self.locations],
        }

        form = BulkLocationMoveForm(
            data=form_data, user=self.owner, campaign=self.campaign
        )

        # Owner should be able to move all locations
        self.assertTrue(form.is_valid())

    def test_bulk_move_form_circular_reference_prevention(self):
        """Test that bulk move prevents circular references."""
        # Try to move new_parent under one of its future children
        form_data = {
            "new_parent": self.new_parent.id,
            "locations": [self.new_parent.id],  # Try to move parent under itself
        }

        form = BulkLocationMoveForm(
            data=form_data, user=self.owner, campaign=self.campaign
        )
        self.assertFalse(form.is_valid())
        self.assertIn("locations", form.errors)

    def test_bulk_move_form_execution(self):
        """Test successful bulk move execution."""
        selected_locations = self.locations[:3]

        form_data = {
            "new_parent": self.new_parent.id,
            "locations": [loc.id for loc in selected_locations],
        }

        form = BulkLocationMoveForm(
            data=form_data, user=self.owner, campaign=self.campaign
        )
        self.assertTrue(form.is_valid())

        # Execute the bulk move
        moved_count = form.save()
        self.assertEqual(moved_count, 3)

        # Verify locations were moved
        for location in selected_locations:
            location.refresh_from_db()
            self.assertEqual(location.parent, self.new_parent)


class LocationFormWidgetTest(TestCase):
    """Test custom widgets and form presentation."""

    def setUp(self):
        """Set up test data for widget tests."""
        self.user = User.objects.create_user(
            username="user", email="user@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Widget Test Campaign",
            owner=self.user,
            game_system="mage",
        )

    def test_parent_field_widget_configuration(self):
        """Test that parent field has appropriate widget."""
        form = LocationForm(user=self.user)

        parent_field = form.fields["parent"]

        # Should have empty_label for "no parent" option
        self.assertTrue(hasattr(parent_field, "empty_label"))

        # Widget should support hierarchy display
        widget = parent_field.widget
        self.assertIsNotNone(widget)

    def test_campaign_field_widget(self):
        """Test campaign field widget configuration."""
        form = LocationForm(user=self.user)

        form.fields["campaign"]

        # Should display campaign name and owner
        # Widget configuration depends on implementation

    def test_form_field_help_text(self):
        """Test that form fields have helpful help text."""
        form = LocationForm(user=self.user)

        # Name field should have help text
        self.assertIsNotNone(form.fields["name"].help_text)

        # Parent field should explain hierarchy
        self.assertIsNotNone(form.fields["parent"].help_text)
        self.assertIn("parent", form.fields["parent"].help_text.lower())

    def test_form_css_classes(self):
        """Test that form fields have appropriate CSS classes."""
        form = LocationForm(user=self.user)

        # Check that fields have Bootstrap/CSS classes for styling
        for _, field in form.fields.items():
            widget = field.widget

            # Should have CSS classes for styling
            if hasattr(widget, "attrs") and "class" in widget.attrs:
                css_classes = widget.attrs["class"]
                self.assertIsNotNone(css_classes)


class LocationFormAjaxTest(TestCase):
    """Test AJAX-enabled form functionality."""

    def setUp(self):
        """Set up test data for AJAX form tests."""
        self.user = User.objects.create_user(
            username="ajaxuser", email="ajax@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="AJAX Test Campaign",
            owner=self.user,
            game_system="mage",
        )

    def test_parent_field_ajax_filtering(self):
        """Test AJAX filtering of parent field based on campaign selection."""
        # This test verifies that the form supports AJAX updates
        # when campaign selection changes

        other_campaign = Campaign.objects.create(
            name="Other AJAX Campaign",
            owner=self.user,
            game_system="generic",
        )

        # Create locations in different campaigns
        location1 = Location.objects.create(
            name="Campaign 1 Location",
            campaign=self.campaign,
            created_by=self.user,
        )

        location2 = Location.objects.create(
            name="Campaign 2 Location",
            campaign=other_campaign,
            created_by=self.user,
        )

        # Test form with first campaign
        form1 = LocationForm(user=self.user, initial={"campaign": self.campaign})
        parent_queryset1 = form1.fields["parent"].queryset

        self.assertIn(location1, parent_queryset1)
        self.assertNotIn(location2, parent_queryset1)

        # Test form with second campaign
        form2 = LocationForm(user=self.user, initial={"campaign": other_campaign})
        parent_queryset2 = form2.fields["parent"].queryset

        self.assertNotIn(location1, parent_queryset2)
        self.assertIn(location2, parent_queryset2)

    def test_form_validation_ajax_response(self):
        """Test that form validation works with AJAX requests."""
        # Test invalid data submission via AJAX
        form_data = {
            "name": "",  # Invalid: empty name
            "campaign": self.campaign.id,
        }

        form = LocationForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())

        # Form should return JSON-serializable errors for AJAX
        errors = form.errors
        self.assertIn("name", errors)

        # Errors should be convertible to JSON for AJAX responses
        import json

        try:
            json.dumps(dict(errors))
        except TypeError:
            self.fail("Form errors should be JSON-serializable for AJAX")

    def test_dynamic_hierarchy_display(self):
        """Test dynamic hierarchy display in form."""
        # Create hierarchy for testing dynamic display
        parent = Location.objects.create(
            name="A Parent Location",
            campaign=self.campaign,
            created_by=self.user,
        )

        child = Location.objects.create(
            name="B Child Location",
            campaign=self.campaign,
            parent=parent,
            created_by=self.user,
        )

        # Form should support dynamic hierarchy display
        form = LocationForm(user=self.user, initial={"campaign": self.campaign})

        # Parent field should display hierarchy information
        parent_choices = form.fields["parent"].queryset

        # Choices should be ordered to show hierarchy
        choices_list = list(parent_choices)
        parent_index = choices_list.index(parent)
        child_index = choices_list.index(child)

        # Parent should come before child in hierarchy display
        self.assertLess(parent_index, child_index)
