from django.contrib import admin

from .models import Character


@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    """Admin interface for Character model."""

    list_display = ["name", "campaign", "player_owner", "game_system", "created_at"]
    list_filter = ["campaign", "game_system", "created_at"]
    search_fields = ["name", "campaign__name", "player_owner__username"]
    readonly_fields = ["created_at", "updated_at"]
