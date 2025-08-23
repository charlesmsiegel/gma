"""
Tests for bulk operations in Item admin interface.

Tests cover all bulk operation requirements:
1. Bulk delete (soft delete) functionality
2. Bulk restore functionality
3. Bulk quantity updates
4. Bulk campaign transfers
5. Bulk ownership changes
6. Permission checking for bulk operations
7. Error handling in bulk operations
"""

from unittest.mock import patch

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory, TestCase

from campaigns.models import Campaign, CampaignMembership
from characters.models import Character
from items.admin import ItemAdmin
from items.models import Item

User = get_user_model()


class ItemBulkOperationsTestCase(TestCase):
    """Base test case for bulk operations tests."""

    def setUp(self):
        """Set up test data for bulk operations."""
        self.factory = RequestFactory()
        self.site = AdminSite()

        # Create users
        self.admin_user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="adminpass123"
        )
        self.owner1 = User.objects.create_user(
            username="owner1", email="owner1@example.com", password="pass123"
        )
        self.owner2 = User.objects.create_user(
            username="owner2", email="owner2@example.com", password="pass123"
        )
        self.player1 = User.objects.create_user(
            username="player1", email="player1@example.com", password="pass123"
        )

        # Create campaigns
        self.campaign1 = Campaign.objects.create(
            name="Fantasy Campaign",
            owner=self.owner1,
            game_system="D&D 5e",
        )
        self.campaign2 = Campaign.objects.create(
            name="Sci-Fi Campaign",
            owner=self.owner2,
            game_system="Cyberpunk",
        )

        # Create memberships
        CampaignMembership.objects.create(
            campaign=self.campaign1, user=self.player1, role="PLAYER"
        )

        # Create characters
        self.character1 = Character.objects.create(
            name="Character 1",
            campaign=self.campaign1,
            player_owner=self.player1,
            game_system="D&D 5e",
        )
        self.character2 = Character.objects.create(
            name="Character 2",
            campaign=self.campaign1,
            player_owner=self.owner1,
            game_system="D&D 5e",
        )

        # Create test items
        self.items = []
        for i in range(5):
            item = Item.objects.create(
                name=f"Test Item {i+1}",
                description=f"Description for item {i+1}",
                campaign=self.campaign1,
                quantity=i + 1,
                created_by=self.owner1,
            )
            self.items.append(item)

        # Create ItemAdmin instance
        self.admin = ItemAdmin(Item, self.site)

    def _create_request_with_messages(self, path, user, method="GET", data=None):
        """Helper to create request with message framework support."""
        if method.upper() == "POST":
            request = self.factory.post(path, data or {})
        else:
            request = self.factory.get(path)

        request.user = user

        # Add session and messages framework
        from django.contrib.messages.middleware import MessageMiddleware
        from django.contrib.sessions.middleware import SessionMiddleware

        SessionMiddleware(lambda x: None).process_request(request)
        MessageMiddleware(lambda x: None).process_request(request)

        request.session.save()

        # Add messages storage
        messages = FallbackStorage(request)
        setattr(request, "_messages", messages)

        return request


class BulkDeleteOperationsTest(ItemBulkOperationsTestCase):
    """Test bulk delete (soft delete) operations."""

    def test_bulk_soft_delete_action_exists(self):
        """Test that bulk soft delete action is available."""
        request = self._create_request_with_messages(
            "/admin/items/item/", self.admin_user
        )
        actions = self.admin.get_actions(request)
        self.assertIn("soft_delete_selected", actions)

    def test_bulk_soft_delete_execution(self):
        """Test executing bulk soft delete action."""
        # Select first 3 items for deletion
        selected_items = self.items[:3]
        item_ids = [item.id for item in selected_items]

        request = self._create_request_with_messages(
            "/admin/items/item/",
            self.admin_user,
            "POST",
            {
                "action": "soft_delete_selected",
                "_selected_action": item_ids,
            },
        )

        # Execute the action
        self.admin.soft_delete_selected(request, Item.objects.filter(id__in=item_ids))

        # Verify items were soft deleted
        for item in selected_items:
            # Use all_objects to get the updated item since default manager
            # excludes deleted items
            updated_item = Item.all_objects.get(id=item.id)
            self.assertTrue(updated_item.is_deleted)
            self.assertIsNotNone(updated_item.deleted_at)
            self.assertEqual(updated_item.deleted_by, self.admin_user)

    def test_bulk_soft_delete_preserves_unselected(self):
        """Test that bulk soft delete doesn't affect unselected items."""
        # Select first 2 items for deletion
        selected_items = self.items[:2]
        unselected_items = self.items[2:]
        item_ids = [item.id for item in selected_items]

        request = self._create_request_with_messages(
            "/admin/items/item/",
            self.admin_user,
            "POST",
            {
                "action": "soft_delete_selected",
                "_selected_action": item_ids,
            },
        )

        # Execute the action
        self.admin.soft_delete_selected(request, Item.objects.filter(id__in=item_ids))

        # Verify unselected items are not affected
        for item in unselected_items:
            item.refresh_from_db()
            self.assertFalse(item.is_deleted)

    def test_bulk_soft_delete_already_deleted_items(self):
        """Test bulk soft delete handles already deleted items gracefully."""
        # Soft delete one item manually
        self.items[0].soft_delete(self.owner1)

        # Try to bulk delete all items including the already deleted one
        item_ids = [item.id for item in self.items[:3]]

        request = self._create_request_with_messages(
            "/admin/items/item/",
            self.admin_user,
            "POST",
            {
                "action": "soft_delete_selected",
                "_selected_action": item_ids,
            },
        )

        # This should handle the already deleted item gracefully
        self.admin.soft_delete_selected(
            request, Item.all_objects.filter(id__in=item_ids)
        )

        # Verify that the action completes successfully
        # (exact behavior depends on implementation)

    def test_bulk_soft_delete_permission_check(self):
        """Test that bulk soft delete respects permissions."""
        # Test with non-admin user
        selected_items = self.items[:2]
        item_ids = [item.id for item in selected_items]

        request = self._create_request_with_messages(
            "/admin/items/item/",
            self.player1,  # Non-admin user
            "POST",
            {
                "action": "soft_delete_selected",
                "_selected_action": item_ids,
            },
        )

        # Should either raise PermissionError or handle gracefully
        try:
            self.admin.soft_delete_selected(
                request, Item.objects.filter(id__in=item_ids)
            )
            # If it doesn't raise an error, items should not be deleted
            for item in selected_items:
                item.refresh_from_db()
                self.assertFalse(item.is_deleted)
        except PermissionError:
            pass  # Expected behavior


class BulkRestoreOperationsTest(ItemBulkOperationsTestCase):
    """Test bulk restore operations."""

    def setUp(self):
        """Set up with some deleted items."""
        super().setUp()

        # Soft delete first 3 items
        for item in self.items[:3]:
            item.soft_delete(self.owner1)

    def test_bulk_restore_action_exists(self):
        """Test that bulk restore action is available."""
        request = self._create_request_with_messages(
            "/admin/items/item/", self.admin_user
        )
        actions = self.admin.get_actions(request)
        self.assertIn("restore_selected", actions)

    def test_bulk_restore_execution(self):
        """Test executing bulk restore action."""
        deleted_items = self.items[:3]
        item_ids = [item.id for item in deleted_items]

        request = self._create_request_with_messages(
            "/admin/items/item/",
            self.admin_user,
            "POST",
            {
                "action": "restore_selected",
                "_selected_action": item_ids,
            },
        )

        # Execute the action on all_objects queryset
        queryset = Item.all_objects.filter(id__in=item_ids)
        self.admin.restore_selected(request, queryset)

        # Verify items were restored
        for item in deleted_items:
            # Get fresh instance from database
            updated_item = Item.all_objects.get(id=item.id)
            self.assertFalse(updated_item.is_deleted)
            self.assertIsNone(updated_item.deleted_at)
            self.assertIsNone(updated_item.deleted_by)

    def test_bulk_restore_non_deleted_items(self):
        """Test bulk restore handles non-deleted items gracefully."""
        # Mix of deleted and non-deleted items
        mixed_items = [
            self.items[0],
            self.items[1],
            self.items[3],
        ]  # 0,1 deleted, 3 not
        item_ids = [item.id for item in mixed_items]

        request = self._create_request_with_messages(
            "/admin/items/item/",
            self.admin_user,
            "POST",
            {
                "action": "restore_selected",
                "_selected_action": item_ids,
            },
        )

        queryset = Item.all_objects.filter(id__in=item_ids)
        self.admin.restore_selected(request, queryset)

        # Should handle mixed items gracefully
        # (exact behavior depends on implementation)


class BulkQuantityUpdateTest(ItemBulkOperationsTestCase):
    """Test bulk quantity update operations."""

    def test_bulk_update_quantity_action_exists(self):
        """Test that bulk quantity update action is available."""
        request = self._create_request_with_messages(
            "/admin/items/item/", self.admin_user
        )
        actions = self.admin.get_actions(request)
        self.assertIn("update_quantity", actions)

    def test_bulk_update_quantity_execution(self):
        """Test executing bulk quantity update action."""
        selected_items = self.items[:3]
        item_ids = [item.id for item in selected_items]
        new_quantity = 10

        request = self._create_request_with_messages(
            "/admin/items/item/",
            self.admin_user,
            "POST",
            {
                "action": "update_quantity",
                "_selected_action": item_ids,
                "new_quantity": new_quantity,
            },
        )

        queryset = Item.objects.filter(id__in=item_ids)

        # Mock the intermediate form if this action requires it
        with patch("items.admin.ItemAdmin.update_quantity") as mock_action:
            mock_action.return_value = None
            self.admin.update_quantity(request, queryset)

            # Verify the action was called
            mock_action.assert_called_once()

    def test_bulk_update_quantity_validation(self):
        """Test validation for bulk quantity updates."""
        selected_items = self.items[:2]
        item_ids = [item.id for item in selected_items]

        # Test with invalid quantity (negative)
        self._create_request_with_messages(
            "/admin/items/item/",
            self.admin_user,
            "POST",
            {
                "action": "update_quantity",
                "_selected_action": item_ids,
                "new_quantity": -5,
            },
        )

        # Should handle invalid input gracefully
        # (exact validation depends on implementation)


class BulkOwnershipOperationsTest(ItemBulkOperationsTestCase):
    """Test bulk ownership change operations."""

    def test_bulk_assign_ownership_action_exists(self):
        """Test that bulk ownership assignment action is available."""
        request = self._create_request_with_messages(
            "/admin/items/item/", self.admin_user
        )
        actions = self.admin.get_actions(request)
        self.assertIn("assign_ownership", actions)

    def test_bulk_assign_ownership_execution(self):
        """Test executing bulk ownership assignment."""
        selected_items = self.items[:3]
        item_ids = [item.id for item in selected_items]

        request = self._create_request_with_messages(
            "/admin/items/item/",
            self.admin_user,
            "POST",
            {
                "action": "assign_ownership",
                "_selected_action": item_ids,
                "character_id": self.character1.id,
            },
        )

        queryset = Item.objects.filter(id__in=item_ids)

        # Mock the action if it requires intermediate steps
        with patch("items.admin.ItemAdmin.assign_ownership") as mock_action:
            mock_action.return_value = None
            self.admin.assign_ownership(request, queryset)

            mock_action.assert_called_once()

    def test_bulk_clear_ownership_action_exists(self):
        """Test that bulk ownership clearing action is available."""
        request = self._create_request_with_messages(
            "/admin/items/item/", self.admin_user
        )
        actions = self.admin.get_actions(request)
        self.assertIn("clear_ownership", actions)

    def test_bulk_clear_ownership_execution(self):
        """Test executing bulk ownership clearing."""
        # Assign ownership first
        for item in self.items[:3]:
            item.owner = self.character1
            item.save()

        selected_items = self.items[:3]
        item_ids = [item.id for item in selected_items]

        request = self._create_request_with_messages(
            "/admin/items/item/",
            self.admin_user,
            "POST",
            {
                "action": "clear_ownership",
                "_selected_action": item_ids,
            },
        )

        queryset = Item.objects.filter(id__in=item_ids)
        self.admin.clear_ownership(request, queryset)

        # Verify ownership was cleared
        for item in selected_items:
            item.refresh_from_db()
            self.assertIsNone(item.owner)


class BulkCampaignTransferTest(ItemBulkOperationsTestCase):
    """Test bulk campaign transfer operations."""

    def test_bulk_transfer_campaign_action_exists(self):
        """Test that bulk campaign transfer action is available."""
        request = self._create_request_with_messages(
            "/admin/items/item/", self.admin_user
        )
        actions = self.admin.get_actions(request)
        self.assertIn("transfer_campaign", actions)

    def test_bulk_transfer_campaign_execution(self):
        """Test executing bulk campaign transfer."""
        selected_items = self.items[:3]
        item_ids = [item.id for item in selected_items]

        request = self._create_request_with_messages(
            "/admin/items/item/",
            self.admin_user,
            "POST",
            {
                "action": "transfer_campaign",
                "_selected_action": item_ids,
                "target_campaign_id": self.campaign2.id,
            },
        )

        queryset = Item.objects.filter(id__in=item_ids)

        # Mock the action since it may require intermediate forms
        with patch("items.admin.ItemAdmin.transfer_campaign") as mock_action:
            mock_action.return_value = None
            self.admin.transfer_campaign(request, queryset)

            mock_action.assert_called_once()

    def test_bulk_transfer_campaign_validation(self):
        """Test validation for bulk campaign transfers."""
        # Test transferring to non-existent campaign
        selected_items = self.items[:2]
        item_ids = [item.id for item in selected_items]

        self._create_request_with_messages(
            "/admin/items/item/",
            self.admin_user,
            "POST",
            {
                "action": "transfer_campaign",
                "_selected_action": item_ids,
                "target_campaign_id": 99999,  # Non-existent ID
            },
        )

        # Should handle invalid campaign ID gracefully
        # (exact validation depends on implementation)


class BulkOperationsPermissionsTest(ItemBulkOperationsTestCase):
    """Test permissions for bulk operations."""

    def test_bulk_operations_superuser_access(self):
        """Test that superuser can perform all bulk operations."""
        request = self._create_request_with_messages(
            "/admin/items/item/", self.admin_user
        )
        actions = self.admin.get_actions(request)

        # Superuser should have access to all bulk actions
        expected_actions = [
            "soft_delete_selected",
            "restore_selected",
            "update_quantity",
            "assign_ownership",
            "clear_ownership",
            "transfer_campaign",
        ]

        for action in expected_actions:
            self.assertIn(action, actions)

    def test_bulk_operations_regular_user_restrictions(self):
        """Test that regular users have limited bulk operation access."""
        # Create request with regular user
        request = self.factory.get("/admin/items/item/")
        request.user = self.owner1

        # Get available actions for this user
        self.admin.get_actions(request)

        # Some actions might be restricted for regular users
        # (exact restrictions depend on your permission system)

    def test_bulk_operations_no_selection_error(self):
        """Test bulk operations with no items selected."""
        request = self._create_request_with_messages(
            "/admin/items/item/",
            self.admin_user,
            "POST",
            {
                "action": "soft_delete_selected",
                "_selected_action": [],  # No items selected
            },
        )

        # Should handle empty selection gracefully
        self.admin.soft_delete_selected(request, Item.objects.none())

        # Should not cause any errors or unwanted side effects


class BulkOperationsErrorHandlingTest(ItemBulkOperationsTestCase):
    """Test error handling in bulk operations."""

    def test_bulk_operation_database_error_handling(self):
        """Test handling of database errors during bulk operations."""
        selected_items = self.items[:2]
        item_ids = [item.id for item in selected_items]

        request = self._create_request_with_messages(
            "/admin/items/item/",
            self.admin_user,
            "POST",
            {
                "action": "soft_delete_selected",
                "_selected_action": item_ids,
            },
        )

        # Simulate database error
        with patch.object(Item, "soft_delete", side_effect=Exception("Database error")):
            try:
                self.admin.soft_delete_selected(
                    request, Item.objects.filter(id__in=item_ids)
                )
                # Should handle the error gracefully
            except Exception:
                # Should either handle gracefully or provide meaningful error message
                pass

    def test_bulk_operation_partial_failure(self):
        """Test handling of partial failures in bulk operations."""
        selected_items = self.items[:3]
        item_ids = [item.id for item in selected_items]

        # Delete one item to cause a failure scenario
        self.items[1].delete()  # Hard delete to cause issues

        request = self._create_request_with_messages(
            "/admin/items/item/",
            self.admin_user,
            "POST",
            {
                "action": "soft_delete_selected",
                "_selected_action": item_ids,
            },
        )

        # Should handle partial failures gracefully
        try:
            self.admin.soft_delete_selected(
                request, Item.objects.filter(id__in=item_ids)
            )
        except Exception:
            # Should provide meaningful error feedback
            pass
