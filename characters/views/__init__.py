"""
Views for character management.

Provides campaign-scoped character management views with proper permission checking.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.generic import CreateView, DetailView, ListView

from characters.forms import CharacterCreateForm
from characters.models import Character
from core.mixins import CampaignCharacterMixin, CampaignListView


class CampaignCharactersView(CampaignCharacterMixin, CampaignListView):
    """
    List characters in a campaign with role-based filtering.

    - OWNER/GM: See all characters in the campaign
    - PLAYER: See only their own characters
    - OBSERVER: See all characters (read-only)
    """

    model = Character
    template_name = "characters/campaign_characters.html"
    context_object_name = "characters"

    def get_context_data(self, **kwargs):
        """Add character-specific context."""
        context = super().get_context_data(**kwargs)

        # Use optimized role method from mixin to avoid repeated database query
        user_role = self.get_user_role()

        context.update(
            {
                "page_title": f"{self.campaign.name} - Characters",
                "can_create_character": user_role in ["OWNER", "GM", "PLAYER"],
                "can_manage_all": user_role in ["OWNER", "GM"],
                "is_player": user_role == "PLAYER",
            }
        )

        return context


class CharacterCreateView(LoginRequiredMixin, CreateView):
    """
    View for creating new characters.

    - Requires authentication
    - Filters campaigns by user membership (PLAYER, GM, OWNER roles)
    - Validates character limits before allowing creation
    - Automatically assigns player_owner and game_system
    """

    model = Character
    form_class = CharacterCreateForm
    template_name = "characters/character_create.html"

    def get_form_kwargs(self):
        """Pass the current user to the form."""
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        """Add additional context for the template."""
        context = super().get_context_data(**kwargs)

        # Get user's campaigns with character counts for display
        from django.db import models

        from campaigns.models import Campaign

        user_campaigns = (
            Campaign.objects.filter(
                models.Q(owner=self.request.user)  # Campaigns they own
                | models.Q(
                    memberships__user=self.request.user
                ),  # Campaigns they're a member of
                is_active=True,  # Only active campaigns
            )
            .distinct()
            .annotate(
                user_character_count=models.Count(
                    "characters",
                    filter=models.Q(characters__player_owner=self.request.user),
                )
            )
            .order_by("name")
        )

        # Add information about character limits
        campaigns_info = []
        for campaign in user_campaigns:
            limit = campaign.max_characters_per_player
            current_count = campaign.user_character_count

            campaigns_info.append(
                {
                    "campaign": campaign,
                    "current_count": current_count,
                    "limit": limit,
                    "at_limit": limit > 0 and current_count >= limit,
                    "can_create": limit == 0 or current_count < limit,
                }
            )

        context.update(
            {
                "page_title": "Create Character",
                "campaigns_info": campaigns_info,
                "has_available_campaigns": any(
                    info["can_create"] for info in campaigns_info
                ),
            }
        )

        return context

    def form_valid(self, form):
        """Handle successful form submission."""
        character = form.save()

        messages.success(
            self.request, f"Character '{character.name}' was successfully created!"
        )

        return redirect(self.get_success_url(character))

    def form_invalid(self, form):
        """Handle form validation errors."""
        messages.error(
            self.request,
            "There were errors in your character creation form. Please correct them below.",
        )
        return super().form_invalid(form)

    def get_success_url(self, character=None):
        """Return the URL to redirect to after successful character creation."""
        if character:
            return reverse("characters:detail", kwargs={"pk": character.pk})
        return reverse("characters:list")


class CharacterDetailView(LoginRequiredMixin, DetailView):
    """
    Display character details with proper permission checking.
    
    - Shows character information, description, and metadata
    - Provides edit/delete buttons based on user permissions
    - Shows recent scenes the character has participated in
    - Redirects to campaign detail if user lacks access
    """

    model = Character
    template_name = "characters/character_detail.html"
    context_object_name = "character"

    def get_object(self, queryset=None):
        """Get character with related data and permission checking."""
        character = super().get_object(queryset)
        
        # Check if user has permission to view this character
        user_role = character.campaign.get_user_role(self.request.user)
        
        if user_role is None:
            # Non-members cannot view characters - redirect to hide existence
            messages.error(
                self.request,
                "You don't have permission to view this character."
            )
            # This will be handled in the dispatch method
            return None
            
        return character

    def dispatch(self, request, *args, **kwargs):
        """Handle permission checking at dispatch level."""
        try:
            character = Character.objects.select_related(
                'campaign', 'player_owner'
            ).get(pk=kwargs['pk'])
            
            user_role = character.campaign.get_user_role(request.user)
            if user_role is None:
                messages.error(
                    request,
                    "You don't have permission to view this character."
                )
                return redirect('campaigns:list')
                
        except Character.DoesNotExist:
            messages.error(request, "Character not found.")
            return redirect('campaigns:list')
            
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Add additional context for the template."""
        context = super().get_context_data(**kwargs)
        character = self.object
        user = self.request.user
        
        # Get user's role for permission checking
        user_role = character.campaign.get_user_role(user)
        
        # Determine edit/delete permissions
        can_edit = character.can_be_edited_by(user, user_role)
        can_delete = character.can_be_deleted_by(user)
        
        # Get recent scenes (placeholder for future implementation)
        # This will be replaced when scene functionality is implemented
        recent_scenes = []
        
        context.update({
            'can_edit': can_edit,
            'can_delete': can_delete,
            'user_role': user_role,
            'recent_scenes': recent_scenes,
        })
        
        return context
