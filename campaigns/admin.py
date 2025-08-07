from django.contrib import admin

from .models import Campaign, CampaignMembership


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    """Admin configuration for Campaign model."""

    list_display = ["name", "owner", "game_system", "is_active", "created_at"]
    list_filter = ["game_system", "is_active", "created_at"]
    search_fields = ["name", "description", "owner__username", "owner__email"]
    readonly_fields = ["created_at", "updated_at"]
    date_hierarchy = "created_at"
    raw_id_fields = ["owner"]  # Better UX with many users

    fieldsets = [
        (
            "Basic Information",
            {"fields": ["name", "slug", "description", "game_system"]},
        ),
        (
            "Ownership",
            {
                "fields": ["owner"],
                "description": "Campaign owner has full access to the campaign. "
                "Campaigns are deleted if the owner is deleted.",
            },
        ),
        (
            "Status",
            {"fields": ["is_active"]},
        ),
        (
            "Timestamps",
            {"fields": ["created_at", "updated_at"], "classes": ["collapse"]},
        ),
    ]

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related("owner")


@admin.register(CampaignMembership)
class CampaignMembershipAdmin(admin.ModelAdmin):
    """Admin configuration for CampaignMembership model."""

    list_display = ["user", "campaign", "role", "joined_at"]
    list_filter = ["role", "joined_at", "campaign__game_system"]
    search_fields = [
        "user__username",
        "user__email",
        "campaign__name",
        "campaign__owner__username",
    ]
    readonly_fields = ["joined_at"]
    date_hierarchy = "joined_at"
    raw_id_fields = ["user", "campaign"]  # Better UX with many records

    fieldsets = [
        (
            "Membership",
            {
                "fields": ["campaign", "user", "role"],
                "description": "Users can have one membership per campaign. "
                "Campaign owners can also be members with any role.",
            },
        ),
        (
            "Status",
            {"fields": ["joined_at"]},
        ),
    ]

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return (
            super()
            .get_queryset(request)
            .select_related("user", "campaign", "campaign__owner")
        )
