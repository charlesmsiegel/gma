from django.contrib import admin
from django.db.models import Count, Q
from django.utils.html import format_html

from .models import Campaign, CampaignMembership


class MemberCountFilter(admin.SimpleListFilter):
    """Custom filter for member count ranges."""

    title = "member count"
    parameter_name = "member_count"

    def lookups(self, request, model_admin):
        return [
            ("small", "1-2 members"),
            ("medium", "3-5 members"),
            ("large", "6+ members"),
        ]

    def queryset(self, request, queryset):
        # Annotate with total member count
        queryset = queryset.annotate(
            total_members=Count("memberships") + 1  # +1 for owner
        )

        if self.value() == "small":
            return queryset.filter(total_members__lte=2)
        elif self.value() == "medium":
            return queryset.filter(total_members__range=(3, 5))
        elif self.value() == "large":
            return queryset.filter(total_members__gte=6)
        return queryset


class CampaignMembershipInline(admin.TabularInline):
    """Inline admin for campaign memberships."""

    model = CampaignMembership
    extra = 0
    fields = ["user", "role", "joined_at"]
    readonly_fields = ["joined_at"]
    raw_id_fields = ["user"]

    def get_queryset(self, request):
        """Optimize inline queryset."""
        return super().get_queryset(request).select_related("user")


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    """Admin configuration for Campaign model."""

    list_display = ["name", "owner", "created_at", "member_count_display"]
    list_filter = ["game_system", "is_active", "created_at", MemberCountFilter]
    search_fields = ["name", "slug", "description", "owner__username", "owner__email"]
    readonly_fields = ["created_at", "updated_at"]
    date_hierarchy = "created_at"
    raw_id_fields = ["owner"]  # Better UX with many users
    inlines = [CampaignMembershipInline]

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
        """Optimize queryset with select_related and annotations for member counts."""
        return (
            super()
            .get_queryset(request)
            .select_related("owner")
            .annotate(
                total_members=Count("memberships") + 1,  # +1 for owner
                gm_count=Count("memberships", filter=Q(memberships__role="GM")),
                player_count=Count("memberships", filter=Q(memberships__role="PLAYER")),
                observer_count=Count(
                    "memberships", filter=Q(memberships__role="OBSERVER")
                ),
            )
        )

    def member_count_display(self, obj):
        """Display member count breakdown by role."""
        owner_count = 1  # Always 1 owner
        gm_count = getattr(obj, "gm_count", 0)
        player_count = getattr(obj, "player_count", 0)
        observer_count = getattr(obj, "observer_count", 0)
        total = getattr(obj, "total_members", 1)

        return format_html(
            "<strong>Owner:</strong> {} | <strong>GM:</strong> {} | "
            "<strong>Player:</strong> {} | <strong>Observer:</strong> {} | "
            "<strong>Total:</strong> {}",
            owner_count,
            gm_count,
            player_count,
            observer_count,
            total,
        )

    member_count_display.short_description = "Member Count"
    member_count_display.admin_order_field = "total_members"


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
                "description": "Users can have one membership per campaign. Campaign "
                "owners are handled automatically and cannot have membership roles.",
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
