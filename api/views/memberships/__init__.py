"""
Campaign membership API views organized by operation type.

This package contains membership-related API views split into logical modules:
- member_views: Basic member operations (list, add, remove, change role)
- bulk_views: Bulk operations for multiple members

All views maintain backward compatibility through import re-exports.
"""

# Re-export all views to maintain backward compatibility
from .bulk_views import bulk_add_members, bulk_change_roles, bulk_remove_members
from .member_views import (
    change_member_role,
    list_campaign_members,
    remove_campaign_member,
)

__all__ = [
    # Member views
    "list_campaign_members",
    "remove_campaign_member",
    "change_member_role",
    # Bulk views
    "bulk_add_members",
    "bulk_change_roles",
    "bulk_remove_members",
]
