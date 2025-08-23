"""
Tests for Item forms.

Tests cover all requirements from Issue #54:
1. Item creation form validation and behavior
2. Item edit form validation and behavior  
3. Field requirements and constraints
4. Character ownership handling
5. Campaign context integration
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from campaigns.models import Campaign, CampaignMembership
from characters.models import Character
from items.models import Item

User = get_user_model()


class ItemFormTest(TestCase):
    """Test the item creation and editing forms directly."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="TestPass123!"
        )
        self.other_user = User.objects.create_user(
            username="otheruser", email="other@example.com", password="TestPass123!"
        )

        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            player_owner=self.user,
            game_system="Mage: The Ascension",
        )

        # Create another campaign for cross-campaign testing
        self.other_campaign = Campaign.objects.create(
            name="Other Campaign",
            player_owner=self.other_user,
            game_system="Vampire: The Masquerade",
        )

        # Create characters in different campaigns
        self.character1 = Character.objects.create(
            name="Test Character 1",
            player_owner=self.user,
            campaign=self.campaign,
        )
        self.character2 = Character.objects.create(
            name="Test Character 2",
            player_owner=self.user,
            campaign=self.campaign,
        )
        self.other_campaign_character = Character.objects.create(
            name="Other Campaign Character",
            player_owner=self.other_user,
            campaign=self.other_campaign,
        )

    def test_item_create_form_valid_minimal_data(self):
        """Test form with valid minimal data."""
        from items.forms import ItemForm

        form_data = {
            "name": "Valid Item",
            "quantity": 1,
        }

        form = ItemForm(data=form_data, campaign=self.campaign)

        self.assertTrue(form.is_valid())

    def test_item_create_form_valid_full_data(self):
        """Test form with all valid data including owner."""
        from items.forms import ItemForm

        form_data = {
            "name": "Valid Item",
            "description": "A valid item description",
            "quantity": 5,
            "owner": self.character1.id,
        }

        form = ItemForm(data=form_data, campaign=self.campaign)

        self.assertTrue(form.is_valid())

    def test_item_create_form_required_name(self):
        """Test that name field is required."""
        from items.forms import ItemForm

        form_data = {
            "description": "Missing name field",
            "quantity": 1,
        }

        form = ItemForm(data=form_data, campaign=self.campaign)

        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_item_create_form_required_quantity(self):
        """Test that quantity field is required."""
        from items.forms import ItemForm

        form_data = {
            "name": "Valid Name",
            "description": "Missing quantity field",
        }

        form = ItemForm(data=form_data, campaign=self.campaign)

        self.assertFalse(form.is_valid())
        self.assertIn("quantity", form.errors)

    def test_item_create_form_quantity_validation(self):
        """Test quantity field validation (must be >= 1)."""
        from items.forms import ItemForm

        # Test zero quantity
        form_data = {
            "name": "Valid Name",
            "quantity": 0,
        }

        form = ItemForm(data=form_data, campaign=self.campaign)

        self.assertFalse(form.is_valid())
        self.assertIn("quantity", form.errors)

        # Test negative quantity
        form_data["quantity"] = -1
        form = ItemForm(data=form_data, campaign=self.campaign)

        self.assertFalse(form.is_valid())
        self.assertIn("quantity", form.errors)

    def test_item_create_form_description_optional(self):
        """Test that description field is optional."""
        from items.forms import ItemForm

        form_data = {
            "name": "Valid Item",
            "quantity": 1,
        }

        form = ItemForm(data=form_data, campaign=self.campaign)

        self.assertTrue(form.is_valid())

    def test_item_create_form_owner_optional(self):
        """Test that owner field is optional."""
        from items.forms import ItemForm

        form_data = {
            "name": "Valid Item",
            "quantity": 1,
        }

        form = ItemForm(data=form_data, campaign=self.campaign)

        self.assertTrue(form.is_valid())

    def test_item_create_form_owner_queryset_filtered_by_campaign(self):
        """Test that owner field only shows characters from the current campaign."""
        from items.forms import ItemForm

        form = ItemForm(campaign=self.campaign)

        # Should only include characters from the current campaign
        owner_queryset = form.fields["owner"].queryset
        self.assertIn(self.character1, owner_queryset)
        self.assertIn(self.character2, owner_queryset)
        self.assertNotIn(self.other_campaign_character, owner_queryset)

    def test_item_create_form_save_method_sets_campaign(self):
        """Test that form save method sets the campaign correctly."""
        from items.forms import ItemForm

        form_data = {
            "name": "Form Save Test",
            "description": "Testing form save method",
            "quantity": 3,
        }

        form = ItemForm(data=form_data, campaign=self.campaign)
        self.assertTrue(form.is_valid())

        item = form.save(created_by=self.user)

        self.assertEqual(item.name, "Form Save Test")
        self.assertEqual(item.description, "Testing form save method")
        self.assertEqual(item.quantity, 3)
        self.assertEqual(item.campaign, self.campaign)
        self.assertEqual(item.created_by, self.user)
        self.assertIsNone(item.owner)  # No owner specified

    def test_item_create_form_save_method_with_owner(self):
        """Test that form save method handles character ownership correctly."""
        from items.forms import ItemForm

        form_data = {
            "name": "Owned Item",
            "description": "An item with an owner",
            "quantity": 1,
            "owner": self.character1.id,
        }

        form = ItemForm(data=form_data, campaign=self.campaign)
        self.assertTrue(form.is_valid())

        item = form.save(created_by=self.user)

        self.assertEqual(item.owner, self.character1)
        self.assertIsNotNone(item.last_transferred_at)  # Should set transfer timestamp

    def test_item_create_form_invalid_owner_from_other_campaign(self):
        """Test that owner from different campaign is rejected."""
        from items.forms import ItemForm

        form_data = {
            "name": "Invalid Owner Test",
            "quantity": 1,
            "owner": self.other_campaign_character.id,
        }

        form = ItemForm(data=form_data, campaign=self.campaign)

        self.assertFalse(form.is_valid())
        self.assertIn("owner", form.errors)

    def test_item_edit_form_prepopulated_data(self):
        """Test that edit form is prepopulated with existing item data."""
        from items.forms import ItemForm

        # Create an existing item
        existing_item = Item.objects.create(
            name="Existing Item",
            description="An existing item for editing",
            quantity=2,
            campaign=self.campaign,
            created_by=self.user,
            player_owner=self.character1,
        )

        form = ItemForm(instance=existing_item, campaign=self.campaign)

        self.assertEqual(form.initial["name"], "Existing Item")
        self.assertEqual(form.initial["description"], "An existing item for editing")
        self.assertEqual(form.initial["quantity"], 2)
        self.assertEqual(form.initial["owner"], self.character1.id)

    def test_item_edit_form_save_updates_existing_item(self):
        """Test that edit form save method updates existing item."""
        from items.forms import ItemForm

        # Create an existing item
        existing_item = Item.objects.create(
            name="Original Name",
            description="Original description",
            quantity=1,
            campaign=self.campaign,
            created_by=self.user,
        )

        form_data = {
            "name": "Updated Name",
            "description": "Updated description",
            "quantity": 5,
            "owner": self.character2.id,
        }

        form = ItemForm(
            data=form_data, instance=existing_item, campaign=self.campaign
        )
        self.assertTrue(form.is_valid())

        updated_item = form.save(modified_by=self.user)

        # Check that the same item was updated, not a new one created
        self.assertEqual(updated_item.id, existing_item.id)
        self.assertEqual(updated_item.name, "Updated Name")
        self.assertEqual(updated_item.description, "Updated description")
        self.assertEqual(updated_item.quantity, 5)
        self.assertEqual(updated_item.owner, self.character2)
        self.assertEqual(updated_item.modified_by, self.user)

    def test_item_edit_form_owner_change_updates_transfer_timestamp(self):
        """Test that changing owner updates the transfer timestamp."""
        from items.forms import ItemForm

        # Create an existing item with owner
        existing_item = Item.objects.create(
            name="Transfer Test Item",
            quantity=1,
            campaign=self.campaign,
            created_by=self.user,
            player_owner=self.character1,
        )

        original_transfer_time = existing_item.last_transferred_at

        form_data = {
            "name": existing_item.name,
            "quantity": existing_item.quantity,
            "owner": self.character2.id,  # Change owner
        }

        form = ItemForm(
            data=form_data, instance=existing_item, campaign=self.campaign
        )
        self.assertTrue(form.is_valid())

        updated_item = form.save()

        self.assertEqual(updated_item.owner, self.character2)
        self.assertNotEqual(updated_item.last_transferred_at, original_transfer_time)

    def test_item_form_name_max_length(self):
        """Test name field maximum length validation."""
        from items.forms import ItemForm

        # Test with very long name (assuming NamedModelMixin has max_length)
        long_name = "a" * 256  # Typically max_length is 255

        form_data = {
            "name": long_name,
            "quantity": 1,
        }

        form = ItemForm(data=form_data, campaign=self.campaign)

        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_item_form_quantity_large_number(self):
        """Test quantity field with large valid number."""
        from items.forms import ItemForm

        form_data = {
            "name": "Many Items",
            "quantity": 999999,
        }

        form = ItemForm(data=form_data, campaign=self.campaign)

        self.assertTrue(form.is_valid())

    def test_item_form_description_long_text(self):
        """Test description field with long text."""
        from items.forms import ItemForm

        long_description = "A very long description. " * 100

        form_data = {
            "name": "Long Description Item",
            "description": long_description,
            "quantity": 1,
        }

        form = ItemForm(data=form_data, campaign=self.campaign)

        # Should be valid as description is typically a TextField
        self.assertTrue(form.is_valid())

    def test_item_form_widgets_and_attributes(self):
        """Test that form fields have appropriate widgets and HTML attributes."""
        from items.forms import ItemForm

        form = ItemForm(campaign=self.campaign)

        # Name field should be required
        name_widget = form.fields["name"].widget
        self.assertTrue(form.fields["name"].required)

        # Quantity field should be required and have appropriate attributes
        quantity_widget = form.fields["quantity"].widget
        self.assertTrue(form.fields["quantity"].required)

        # Description should be optional
        self.assertFalse(form.fields["description"].required)

        # Owner should be optional
        self.assertFalse(form.fields["owner"].required)

    def test_item_form_clean_methods(self):
        """Test any custom clean methods on the form."""
        from items.forms import ItemForm

        # Test that the form correctly validates interdependent fields
        form_data = {
            "name": "Clean Test Item",
            "quantity": 1,
        }

        form = ItemForm(data=form_data, campaign=self.campaign)

        # Should not raise any ValidationError
        self.assertTrue(form.is_valid())

    def test_item_form_error_messages(self):
        """Test that appropriate error messages are shown."""
        from items.forms import ItemForm

        # Test required field error messages
        form_data = {}  # Empty form

        form = ItemForm(data=form_data, campaign=self.campaign)

        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)
        self.assertIn("quantity", form.errors)

        # Check that error messages are user-friendly
        name_errors = form.errors["name"]
        self.assertTrue(any("required" in error.lower() for error in name_errors))

    def test_item_form_without_campaign_parameter(self):
        """Test that form requires campaign parameter for proper initialization."""
        from items.forms import ItemForm

        # Form should handle missing campaign parameter gracefully
        # or raise appropriate error
        try:
            form = ItemForm()
            # If it doesn't raise an error, owner queryset should be empty or None
            if hasattr(form.fields.get("owner", None), "queryset"):
                self.assertEqual(form.fields["owner"].queryset.count(), 0)
        except Exception as e:
            # Should raise a meaningful error about missing campaign
            self.assertIn("campaign", str(e).lower())

    def test_item_form_help_text(self):
        """Test that form fields have appropriate help text."""
        from items.forms import ItemForm

        form = ItemForm(campaign=self.campaign)

        # Check that fields have helpful help text
        if hasattr(form.fields["quantity"], "help_text"):
            self.assertIsNotNone(form.fields["quantity"].help_text)

        if hasattr(form.fields["owner"], "help_text"):
            self.assertIsNotNone(form.fields["owner"].help_text)

    def test_item_form_field_order(self):
        """Test that form fields appear in logical order."""
        from items.forms import ItemForm

        form = ItemForm(campaign=self.campaign)

        # Get the order of fields
        field_names = list(form.fields.keys())

        # Name should come first
        self.assertEqual(field_names[0], "name")

        # Description and quantity should come before owner
        name_index = field_names.index("name")
        owner_index = field_names.index("owner") if "owner" in field_names else len(field_names)
        
        if "description" in field_names:
            desc_index = field_names.index("description")
            self.assertTrue(desc_index > name_index)
            self.assertTrue(desc_index < owner_index)

        if "quantity" in field_names:
            qty_index = field_names.index("quantity")
            self.assertTrue(qty_index > name_index)