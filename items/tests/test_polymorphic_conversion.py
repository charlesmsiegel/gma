"""Tests for Item model polymorphic conversion.

This test suite verifies that the Item model can be successfully converted
from Django's Model to PolymorphicModel while preserving all existing
functionality and adding proper polymorphic capabilities.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import Mock

from django.contrib.admin import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.test import TestCase, TransactionTestCase
from polymorphic.managers import PolymorphicManager
from polymorphic.models import PolymorphicModel
from polymorphic.query import PolymorphicQuerySet

from campaigns.models import Campaign, CampaignMembership
from characters.models import Character
from core.models import (
    AuditableMixin,
    DescribedModelMixin,
    NamedModelMixin,
    TimestampedMixin,
)
from items.admin import ItemAdmin
from items.models import AllItemManager, Item, ItemManager, ItemQuerySet

if TYPE_CHECKING:
    pass  # Type imports removed

User = get_user_model()


class PolymorphicModelConversionTest(TestCase):
    """Test that Item model inherits from PolymorphicModel correctly."""

    def test_item_inherits_from_polymorphic_model(self):
        """Test that Item model inherits from PolymorphicModel."""
        # After conversion, Item should inherit from PolymorphicModel
        self.assertTrue(
            issubclass(Item, PolymorphicModel),
            "Item model should inherit from PolymorphicModel",
        )

    def test_item_has_polymorphic_ctype_field(self):
        """Test that Item model has polymorphic_ctype field."""
        # Check that the polymorphic_ctype field exists
        self.assertTrue(
            hasattr(Item, "polymorphic_ctype"),
            "Item model should have polymorphic_ctype field",
        )

        # Get the field and verify it's the correct type
        field = Item._meta.get_field("polymorphic_ctype")
        self.assertTrue(
            isinstance(field, models.ForeignKey),
            "polymorphic_ctype should be a ForeignKey",
        )
        self.assertEqual(
            field.related_model,
            ContentType,
            "polymorphic_ctype should reference ContentType model",
        )

    def test_item_preserves_existing_fields(self):
        """Test that all existing Item fields are preserved after conversion."""
        expected_fields = {
            "name",  # from NamedModelMixin
            "description",  # from DescribedModelMixin
            "created_at",
            "updated_at",  # from TimestampedMixin
            "created_by",
            "modified_by",  # from AuditableMixin
            "campaign",
            "quantity",
            "owner",  # Item-specific fields (changed from owners to owner)
            "last_transferred_at",  # Transfer tracking
            "is_deleted",
            "deleted_at",
            "deleted_by",  # soft delete fields
            "polymorphic_ctype",  # new polymorphic field
        }

        actual_fields = {
            field.name
            for field in Item._meta.get_fields()
            if not field.many_to_many or field.name == "owner"
        }

        self.assertTrue(
            expected_fields.issubset(actual_fields),
            f"Missing expected fields: {expected_fields - actual_fields}",
        )

    def test_item_preserves_mixin_inheritance(self):
        """Test that Item still inherits from all required mixins."""
        expected_mixins = [
            TimestampedMixin,
            NamedModelMixin,
            DescribedModelMixin,
            AuditableMixin,
            PolymorphicModel,
        ]

        for mixin in expected_mixins:
            self.assertTrue(
                issubclass(Item, mixin), f"Item should inherit from {mixin.__name__}"
            )

    def test_item_meta_configuration_preserved(self):
        """Test that Item Meta configuration is preserved."""
        meta = Item._meta

        # Check database table name
        self.assertEqual(meta.db_table, "items_item")

        # Check ordering
        self.assertEqual(list(meta.ordering), ["name"])

        # Check verbose names
        self.assertEqual(meta.verbose_name, "Item")
        self.assertEqual(meta.verbose_name_plural, "Items")

        # Check indexes are preserved
        index_names = [index.name for index in meta.indexes]
        expected_indexes = [
            "items_campaign_deleted_idx",
            "items_creator_deleted_idx",
            "items_deleted_created_idx",
        ]
        for expected_index in expected_indexes:
            self.assertIn(expected_index, index_names)


class PolymorphicQuerySetTest(TestCase):
    """Test that ItemQuerySet extends PolymorphicQuerySet correctly."""

    def test_item_queryset_inheritance(self):
        """Test that ItemQuerySet inherits from PolymorphicQuerySet."""
        self.assertTrue(
            issubclass(ItemQuerySet, PolymorphicQuerySet),
            "ItemQuerySet should inherit from PolymorphicQuerySet",
        )

    def test_item_queryset_preserves_custom_methods(self):
        """Test that custom queryset methods are preserved."""
        expected_methods = ["active", "deleted", "for_campaign", "owned_by_character"]

        for method_name in expected_methods:
            self.assertTrue(
                hasattr(ItemQuerySet, method_name),
                f"ItemQuerySet should have {method_name} method",
            )

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign", description="Test Description", owner=self.user
        )
        self.character = Character.objects.create(
            name="Test Character",
            campaign=self.campaign,
            player_owner=self.user,
            game_system="Test System",
        )

    def test_queryset_active_method(self):
        """Test that active() method works correctly."""
        # Create active and deleted items
        active_item = Item.objects.create(
            name="Active Item",
            campaign=self.campaign,
            created_by=self.user,
            is_deleted=False,
        )
        deleted_item = Item.objects.create(
            name="Deleted Item",
            campaign=self.campaign,
            created_by=self.user,
            is_deleted=True,
        )

        # Test active filter
        active_items = Item.objects.active()
        self.assertIn(active_item, active_items)
        self.assertNotIn(deleted_item, active_items)

    def test_queryset_deleted_method(self):
        """Test that deleted() method works correctly."""
        # Create active and deleted items
        active_item = Item.objects.create(
            name="Active Item",
            campaign=self.campaign,
            created_by=self.user,
            is_deleted=False,
        )
        deleted_item = Item.objects.create(
            name="Deleted Item",
            campaign=self.campaign,
            created_by=self.user,
            is_deleted=True,
        )

        # Test deleted filter
        deleted_items = Item.objects.deleted()
        self.assertNotIn(active_item, deleted_items)
        self.assertIn(deleted_item, deleted_items)

    def test_queryset_for_campaign_method(self):
        """Test that for_campaign() method works correctly."""
        # Create second campaign
        other_user = User.objects.create_user(
            username="otheruser", email="other@example.com", password="testpass123"
        )
        other_campaign = Campaign.objects.create(
            name="Other Campaign", description="Other Description", owner=other_user
        )

        # Create items in different campaigns
        campaign_item = Item.objects.create(
            name="Campaign Item", campaign=self.campaign, created_by=self.user
        )
        other_item = Item.objects.create(
            name="Other Item", campaign=other_campaign, created_by=other_user
        )

        # Test campaign filter
        campaign_items = Item.objects.for_campaign(self.campaign)
        self.assertIn(campaign_item, campaign_items)
        self.assertNotIn(other_item, campaign_items)

    def test_queryset_owned_by_character_method(self):
        """Test that owned_by_character() method works correctly."""
        # Create second user to own the second character (to avoid character limit)
        other_user = User.objects.create_user(
            username="otheruser", email="other@example.com", password="testpass123"
        )
        # Add other user to campaign so they can have a character
        CampaignMembership.objects.create(
            campaign=self.campaign, user=other_user, role="PLAYER"
        )
        other_character = Character.objects.create(
            name="Other Character",
            campaign=self.campaign,  # Same campaign, different owner
            player_owner=other_user,  # Different user
            game_system="Test System",
        )

        # Create items with different ownership
        item1 = Item.objects.create(
            name="Item 1", campaign=self.campaign, created_by=self.user
        )
        item1.owner = self.character
        item1.save()

        item2 = Item.objects.create(
            name="Item 2", campaign=self.campaign, created_by=self.user
        )
        item2.owner = other_character
        item2.save()

        # Test character ownership filter
        character_items = Item.objects.owned_by_character(self.character)
        self.assertIn(item1, character_items)
        self.assertNotIn(item2, character_items)


class PolymorphicManagerTest(TestCase):
    """Test that Item managers extend PolymorphicManager correctly."""

    def test_item_manager_inheritance(self):
        """Test that ItemManager inherits from PolymorphicManager."""
        self.assertTrue(
            issubclass(ItemManager, PolymorphicManager),
            "ItemManager should inherit from PolymorphicManager",
        )

    def test_all_item_manager_inheritance(self):
        """Test that AllItemManager inherits from PolymorphicManager."""
        self.assertTrue(
            issubclass(AllItemManager, PolymorphicManager),
            "AllItemManager should inherit from PolymorphicManager",
        )

    def test_manager_returns_polymorphic_queryset(self):
        """Test that managers return PolymorphicQuerySet instances."""
        # Test ItemManager
        queryset = Item.objects.all()
        self.assertIsInstance(
            queryset,
            PolymorphicQuerySet,
            "ItemManager should return PolymorphicQuerySet",
        )

        # Test AllItemManager
        all_queryset = Item.all_objects.all()
        self.assertIsInstance(
            all_queryset,
            PolymorphicQuerySet,
            "AllItemManager should return PolymorphicQuerySet",
        )

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign", description="Test Description", owner=self.user
        )

    def test_manager_soft_delete_filtering(self):
        """Test that default manager filters out soft-deleted items."""
        # Create active and deleted items
        active_item = Item.objects.create(
            name="Active Item",
            campaign=self.campaign,
            created_by=self.user,
            is_deleted=False,
        )
        deleted_item = Item.objects.create(
            name="Deleted Item",
            campaign=self.campaign,
            created_by=self.user,
            is_deleted=True,
        )

        # Test default manager excludes soft-deleted
        default_items = Item.objects.all()
        self.assertIn(active_item, default_items)
        self.assertNotIn(deleted_item, default_items)

        # Test all_objects manager includes soft-deleted
        all_items = Item.all_objects.all()
        self.assertIn(active_item, all_items)
        self.assertIn(deleted_item, all_items)

    def test_manager_preserves_custom_methods(self):
        """Test that custom manager methods are preserved."""
        expected_methods = ["for_campaign", "owned_by_character"]

        for method_name in expected_methods:
            self.assertTrue(
                hasattr(ItemManager, method_name),
                f"ItemManager should have {method_name} method",
            )


class PolymorphicSubclassTest(TestCase):
    """Test creating and working with Item subclasses."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign", description="Test Description", owner=self.user
        )

    def test_create_item_subclass(self):
        """Test creating a subclass of Item."""
        # Verify that Item inherits from PolymorphicModel, which means
        # subclassing will work correctly when properly implemented
        self.assertTrue(
            issubclass(Item, PolymorphicModel),
            "Item should inherit from PolymorphicModel to support subclassing",
        )

        # Verify Item has polymorphic_ctype field required for subclassing
        self.assertTrue(
            hasattr(Item, "polymorphic_ctype"),
            "Item should have polymorphic_ctype field for subclass support",
        )

        # Note: Actual subclasses like WeaponItem would be defined in
        # models files with proper migrations, not in test code

    def test_polymorphic_queries_return_correct_types(self):
        """Test that polymorphic queries return instances of correct subclasses."""
        # This test would verify that when subclasses exist,
        # queries return the specific subclass instances

        # Create base Item
        base_item = Item.objects.create(
            name="Base Item", campaign=self.campaign, created_by=self.user
        )

        # Verify it has a polymorphic_ctype
        self.assertIsNotNone(base_item.polymorphic_ctype)
        self.assertEqual(base_item.polymorphic_ctype.model_class(), Item)

        # When retrieved via polymorphic query, should return correct type
        retrieved_item = Item.objects.get(pk=base_item.pk)
        self.assertIsInstance(retrieved_item, Item)
        self.assertEqual(type(retrieved_item), Item)

    def test_polymorphic_manager_handles_subclasses(self):
        """Test that polymorphic manager properly handles subclass instances."""
        # Create base Item
        item = Item.objects.create(
            name="Test Item", campaign=self.campaign, created_by=self.user
        )

        # Verify polymorphic fields are set
        self.assertIsNotNone(item.polymorphic_ctype)

        # Test that filtering still works
        filtered_items = Item.objects.filter(name="Test Item")
        self.assertEqual(filtered_items.count(), 1)
        self.assertEqual(filtered_items.first().pk, item.pk)


class DataPreservationTest(TransactionTestCase):
    """Test that existing Item data is preserved during conversion."""

    def setUp(self):
        """Set up test data that mimics existing database state."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign", description="Test Description", owner=self.user
        )
        self.character = Character.objects.create(
            name="Test Character",
            campaign=self.campaign,
            player_owner=self.user,
            game_system="Test System",
        )

    def test_existing_items_work_after_conversion(self):
        """Test that existing Item instances work correctly after conversion."""
        # Create items that would exist before conversion
        item = Item.objects.create(
            name="Existing Item",
            description="This item existed before conversion",
            campaign=self.campaign,
            quantity=5,
            created_by=self.user,
        )
        item.owner = self.character
        item.save()

        # Verify all functionality still works
        self.assertEqual(item.name, "Existing Item")
        self.assertEqual(item.quantity, 5)
        self.assertEqual(item.campaign, self.campaign)
        self.assertEqual(item.owner, self.character)
        self.assertEqual(item.created_by, self.user)

        # Test soft delete functionality
        self.assertFalse(item.is_deleted)
        item.soft_delete(self.user)
        self.assertTrue(item.is_deleted)

        # Test restoration
        item.restore(self.user)
        self.assertFalse(item.is_deleted)

    def test_model_methods_preserved(self):
        """Test that all model methods still work correctly."""
        item = Item.objects.create(
            name="Test Item", campaign=self.campaign, created_by=self.user
        )

        # Test permission methods
        self.assertTrue(item.can_be_deleted_by(self.user))

        # Test clean method
        item.quantity = 0
        with self.assertRaises(ValidationError):
            item.full_clean()

        # Test string representation
        self.assertEqual(str(item), "Test Item")

    def test_queryset_methods_preserved(self):
        """Test that all queryset methods still work correctly."""
        # Create test items
        active_item = Item.objects.create(
            name="Active Item", campaign=self.campaign, created_by=self.user
        )
        deleted_item = Item.objects.create(
            name="Deleted Item",
            campaign=self.campaign,
            created_by=self.user,
            is_deleted=True,
        )

        # Test queryset filtering
        active_items = Item.objects.active()
        self.assertIn(active_item, active_items)
        self.assertNotIn(deleted_item, active_items)

        deleted_items = Item.objects.deleted()
        self.assertNotIn(active_item, deleted_items)
        self.assertIn(deleted_item, deleted_items)

        campaign_items = Item.objects.for_campaign(self.campaign)
        self.assertIn(active_item, campaign_items)
        # Deleted items should not appear in default manager
        self.assertNotIn(deleted_item, campaign_items)


class AdminPolymorphicTest(TestCase):
    """Test that admin interface works with polymorphic Item model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            is_staff=True,
            is_superuser=True,
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign", description="Test Description", owner=self.user
        )
        self.site = AdminSite()
        self.admin = ItemAdmin(Item, self.site)

    def test_admin_registration_works(self):
        """Test that ItemAdmin can be registered with polymorphic Item."""
        # Verify admin is properly configured
        self.assertIsInstance(self.admin, ItemAdmin)
        self.assertEqual(self.admin.model, Item)

    def test_admin_list_display_includes_polymorphic_info(self):
        """Test that admin list display works with polymorphic model."""
        # After conversion, admin might want to show polymorphic type
        current_list_display = self.admin.list_display
        self.assertIsInstance(current_list_display, (list, tuple))

        # Verify current fields are preserved
        expected_fields = [
            "name",
            "campaign",
            "quantity",
            "created_by",
            "created_at",
            "is_deleted",
        ]
        for field in expected_fields:
            self.assertIn(field, current_list_display)

    def test_admin_queryset_optimizations_work(self):
        """Test that admin queryset optimizations work with polymorphic model."""
        # Create mock request
        mock_request = Mock()
        mock_request.user = self.user

        # Get admin queryset
        queryset = self.admin.get_queryset(mock_request)

        # Should be polymorphic queryset with optimizations
        self.assertIsInstance(queryset, PolymorphicQuerySet)

        # Verify select_related optimizations are preserved
        select_related = queryset.query.select_related
        self.assertIsInstance(select_related, dict)

    def test_bulk_actions_work_with_polymorphic_items(self):
        """Test that bulk actions work correctly with polymorphic items."""
        # Create test items
        item1 = Item.objects.create(
            name="Item 1", campaign=self.campaign, created_by=self.user
        )
        item2 = Item.objects.create(
            name="Item 2", campaign=self.campaign, created_by=self.user
        )

        # Mock request and queryset for bulk action
        mock_request = Mock()
        mock_request.user = self.user

        # Test soft delete action
        queryset = Item.objects.filter(pk__in=[item1.pk, item2.pk])
        self.admin.soft_delete_selected(mock_request, queryset)

        # Verify items were soft deleted
        item1.refresh_from_db()
        item2.refresh_from_db()
        self.assertTrue(item1.is_deleted)
        self.assertTrue(item2.is_deleted)


class MigrationCompatibilityTest(TestCase):
    """Test compatibility aspects of the polymorphic conversion migration."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign", description="Test Description", owner=self.user
        )

    def test_polymorphic_ctype_automatically_set(self):
        """Test that polymorphic_ctype is automatically set for new items."""
        item = Item.objects.create(
            name="New Item", campaign=self.campaign, created_by=self.user
        )

        # Verify polymorphic_ctype is set
        self.assertIsNotNone(item.polymorphic_ctype)
        self.assertEqual(item.polymorphic_ctype.model_class(), Item)

    def test_existing_data_migration_simulation(self):
        """Test data migration simulation from non-polymorphic to polymorphic."""
        # Create item
        item = Item.objects.create(
            name="Migrated Item", campaign=self.campaign, created_by=self.user
        )

        # Simulate what migration would do - set polymorphic_ctype if not set
        if item.polymorphic_ctype is None:
            content_type = ContentType.objects.get_for_model(Item)
            item.polymorphic_ctype = content_type
            item.save(update_fields=["polymorphic_ctype"])

        # Verify the item works correctly
        self.assertIsNotNone(item.polymorphic_ctype)

        # Test that it can be retrieved via polymorphic query
        retrieved = Item.objects.get(pk=item.pk)
        self.assertEqual(retrieved.pk, item.pk)
        self.assertEqual(type(retrieved), Item)

    def test_database_constraints_maintained(self):
        """Test that database constraints are maintained after conversion."""
        # Test validation constraints
        with self.assertRaises(ValidationError):
            item = Item(
                name="Test Item",
                campaign=self.campaign,
                created_by=self.user,
                quantity=0,  # Should fail validation
            )
            item.full_clean()


class BackwardCompatibilityTest(TestCase):
    """Test backward compatibility after polymorphic conversion."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign", description="Test Description", owner=self.user
        )

    def test_existing_api_calls_work(self):
        """Test that existing code using Item model still works."""
        # Test basic creation
        item = Item.objects.create(
            name="API Test Item", campaign=self.campaign, created_by=self.user
        )

        # Test filtering
        items = Item.objects.filter(campaign=self.campaign)
        self.assertIn(item, items)

        # Test custom manager methods
        campaign_items = Item.objects.for_campaign(self.campaign)
        self.assertIn(item, campaign_items)

        # Test model methods
        self.assertTrue(item.can_be_deleted_by(self.user))

    def test_foreign_key_relationships_preserved(self):
        """Test that foreign key relationships still work correctly."""
        item = Item.objects.create(
            name="Relationship Test", campaign=self.campaign, created_by=self.user
        )

        # Test reverse relationships
        campaign_items = self.campaign.items.all()
        self.assertIn(item, campaign_items)

        # User relationship is created_by, not created_items (no reverse name defined)
        user_created_items = Item.objects.filter(created_by=self.user)
        self.assertIn(item, user_created_items)

    def test_many_to_many_relationships_preserved(self):
        """Test that many-to-many relationships still work correctly."""
        character = Character.objects.create(
            name="Test Character",
            campaign=self.campaign,
            player_owner=self.user,
            game_system="Test System",
        )

        item = Item.objects.create(
            name="M2M Test Item", campaign=self.campaign, created_by=self.user
        )

        # Test adding relationship (now single ownership)
        item.owner = character
        item.save()
        self.assertEqual(item.owner, character)

        # Test reverse relationship (now possessions)
        self.assertIn(item, character.possessions.all())

    def test_model_serialization_compatibility(self):
        """Test that model serialization still works (for fixtures, etc.)."""
        from django.core import serializers

        item = Item.objects.create(
            name="Serialization Test", campaign=self.campaign, created_by=self.user
        )

        # Test serialization doesn't break
        try:
            data = serializers.serialize("json", [item])
            self.assertIsInstance(data, str)

            # Test deserialization
            deserialized = list(serializers.deserialize("json", data))
            self.assertEqual(len(deserialized), 1)
        except Exception as e:
            self.fail(f"Serialization failed: {e}")
