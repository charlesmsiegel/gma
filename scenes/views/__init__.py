"""
Views for scene management.

Provides campaign-scoped scene management views with proper permission checking.
"""

import json

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.generic import CreateView, DetailView, ListView, UpdateView, View

from characters.models import Character
from core.mixins import CampaignFilterMixin, CampaignListView, CampaignManagementMixin
from scenes.forms import (
    AddParticipantForm,
    SceneForm,
    SceneSearchForm,
    SceneStatusChangeForm,
)
from scenes.models import Scene


class CampaignScenesView(CampaignListView):
    """
    List scenes in a campaign.

    - OWNER/GM: See all scenes and can manage them
    - PLAYER/OBSERVER: See all scenes (read-only access)
    """

    model = Scene
    template_name = "scenes/campaign_scenes.html"
    context_object_name = "scenes"

    def dispatch(self, request, *args, **kwargs):
        """Handle campaign_slug parameter mapping."""
        # Map campaign_slug to slug for CampaignFilterMixin
        if "campaign_slug" in kwargs:
            kwargs["slug"] = kwargs["campaign_slug"]
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        """Get filtered scenes queryset."""
        queryset = super().get_queryset()

        # Apply search filters if provided
        search_form = SceneSearchForm(self.campaign, self.request.GET)
        if search_form.is_valid():
            queryset = search_form.apply_filters(queryset)

        return queryset

    def get_context_data(self, **kwargs):
        """Add scene-specific context."""
        context = super().get_context_data(**kwargs)

        user_role = self.campaign.get_user_role(self.request.user)
        search_form = SceneSearchForm(self.campaign, self.request.GET)

        context.update(
            {
                "page_title": f"{self.campaign.name} - Scenes",
                "can_create_scene": user_role in ["OWNER", "GM"],
                "can_manage_scenes": user_role in ["OWNER", "GM"],
                "search_form": search_form,
            }
        )

        return context


class SceneCreateView(CampaignFilterMixin, CreateView):
    """
    View for creating new scenes.

    Only OWNER and GM can create scenes.
    """

    model = Scene
    form_class = SceneForm
    template_name = "scenes/scene_create.html"

    def dispatch(self, request, *args, **kwargs):
        """Handle campaign_slug parameter mapping and permission checking."""
        # Map campaign_slug to slug for CampaignFilterMixin
        if "campaign_slug" in kwargs:
            kwargs["slug"] = kwargs["campaign_slug"]

        # Call parent dispatch which handles authentication and campaign access
        # This will return early if authentication is required
        response = super().dispatch(request, *args, **kwargs)

        # If we got here, the user is authenticated and has campaign access
        # Additional permission check for scene creation
        if hasattr(self, "campaign") and self.campaign:
            # Superusers have access to all campaigns
            if not request.user.is_superuser:
                user_role = self.campaign.get_user_role(request.user)
                if user_role not in ["OWNER", "GM"]:
                    if user_role in ["PLAYER", "OBSERVER"]:
                        # User is a campaign member but lacks permission
                        raise PermissionDenied(
                            "Only campaign owners and GMs can create scenes."
                        )
                    # For non-members, parent dispatch already returned 404

        return response

    def get_context_data(self, **kwargs):
        """Add campaign context."""
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": f"Create Scene - {self.campaign.name}",
                "campaign": self.campaign,
            }
        )
        return context

    def form_valid(self, form):
        """Handle valid form submission by setting campaign and creator."""
        scene = form.save(campaign=self.campaign, created_by=self.request.user)
        messages.success(
            self.request, f'Scene "{scene.name}" was created successfully!'
        )
        return redirect("scenes:scene_detail", pk=scene.pk)

    def form_invalid(self, form):
        """Handle invalid form submission."""
        messages.error(self.request, "Please correct the errors below and try again.")
        return super().form_invalid(form)


class AddParticipantView(View):
    """
    AJAX view for adding participants to scenes.

    Only OWNER, GM, and character owners can add participants.
    """

    def post(self, request, *args, **kwargs):
        """Handle AJAX request to add participant."""
        # Check authentication
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required"}, status=401)

        # Get the scene
        scene = get_object_or_404(Scene, pk=kwargs["pk"])

        # Check if user has access to this scene's campaign
        user_role = scene.campaign.get_user_role(request.user)
        if user_role not in ["OWNER", "GM", "PLAYER", "OBSERVER"]:
            return JsonResponse({"error": "Scene not found"}, status=404)

        # Get character ID from request (handle both JSON and form data)
        if request.content_type == "application/json":
            try:
                data = json.loads(request.body)
                character_id = data.get("character_id")
            except json.JSONDecodeError:
                return JsonResponse({"error": "Invalid JSON"}, status=400)
        else:
            character_id = request.POST.get("character_id")

        if not character_id:
            return JsonResponse({"error": "Character ID required"}, status=400)

        try:
            character = Character.objects.get(pk=character_id)
        except Character.DoesNotExist:
            return JsonResponse({"error": "Character not found"}, status=404)

        # Check if character belongs to the same campaign
        if character.campaign != scene.campaign:
            return JsonResponse({"error": "Character not in this campaign"}, status=400)

        # Check permissions
        can_add = False
        if user_role in ["OWNER", "GM"]:
            can_add = True
        elif (
            user_role in ["PLAYER", "OBSERVER"]
            and character.player_owner == request.user
        ):
            can_add = True

        if not can_add:
            return JsonResponse({"error": "Permission denied"}, status=403)

        # Check if character is already participating
        if scene.participants.filter(pk=character.pk).exists():
            return JsonResponse(
                {
                    "success": True,
                    "message": (
                        f"{character.name} is already participating in this scene."
                    ),
                },
                status=200,
            )

        # Add participant
        scene.participants.add(character)

        return JsonResponse(
            {
                "success": True,
                "message": f"{character.name} added to scene",
                "character": {
                    "id": character.pk,
                    "name": character.name,
                    "owner": character.player_owner.display_name
                    or character.player_owner.username,
                },
            }
        )


class RemoveParticipantView(View):
    """
    AJAX view for removing participants from scenes.

    Only OWNER, GM, and character owners can remove participants.
    """

    def delete(self, request, *args, **kwargs):
        """Handle AJAX DELETE request to remove participant."""
        # Check authentication
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required"}, status=401)

        # Get the scene
        scene = get_object_or_404(Scene, pk=kwargs["pk"])

        # Check if user has access to this scene's campaign
        user_role = scene.campaign.get_user_role(request.user)
        if user_role not in ["OWNER", "GM", "PLAYER", "OBSERVER"]:
            return JsonResponse({"error": "Scene not found"}, status=404)

        # Get character ID from URL parameter
        character_id = kwargs.get("character_id")

        try:
            character = Character.objects.get(pk=character_id)
        except Character.DoesNotExist:
            return JsonResponse({"error": "Character not found"}, status=404)

        # Check if character is actually participating
        if not scene.participants.filter(pk=character.pk).exists():
            return JsonResponse(
                {"error": "Character not participating in this scene"}, status=400
            )

        # Check permissions
        can_remove = False
        if user_role in ["OWNER", "GM"]:
            can_remove = True
        elif (
            user_role in ["PLAYER", "OBSERVER"]
            and character.player_owner == request.user
        ):
            can_remove = True

        if not can_remove:
            return JsonResponse({"error": "Permission denied"}, status=403)

        # Remove participant
        scene.participants.remove(character)

        return JsonResponse(
            {
                "success": True,
                "message": f"{character.name} removed from scene",
                "character_id": character.pk,
            }
        )


class SceneDetailView(DetailView):
    """
    View for displaying scene details.

    All campaign members can view scenes.
    """

    model = Scene
    template_name = "scenes/scene_detail.html"
    context_object_name = "scene"

    def dispatch(self, request, *args, **kwargs):
        """Handle authentication and campaign access checking."""
        # Check authentication first
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login

            return redirect_to_login(request.get_full_path())

        # Get the scene to check campaign access
        scene = get_object_or_404(Scene, pk=kwargs["pk"])

        # Check if user has access to this scene's campaign
        # Superusers have access to all scenes
        if not request.user.is_superuser:
            user_role = scene.campaign.get_user_role(request.user)
            if user_role not in ["OWNER", "GM", "PLAYER", "OBSERVER"]:
                raise Http404("Scene not found")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Add scene-specific context."""
        context = super().get_context_data(**kwargs)
        scene = self.get_object()
        user_role = scene.campaign.get_user_role(self.request.user)

        # Superusers get OWNER-level permissions
        if self.request.user.is_superuser and user_role is None:
            user_role = "OWNER"

        context.update(
            {
                "page_title": f"{scene.name} - {scene.campaign.name}",
                "campaign": scene.campaign,
                "can_manage_scene": user_role in ["OWNER", "GM"],
                "participants": scene.participants.select_related(
                    "player_owner"
                ).order_by("name"),
            }
        )

        return context


class SceneEditView(UpdateView):
    """
    View for editing existing scenes.

    Only OWNER and GM can edit scenes.
    """

    model = Scene
    form_class = SceneForm
    template_name = "scenes/scene_edit.html"
    context_object_name = "scene"

    def dispatch(self, request, *args, **kwargs):
        """Handle authentication and permission checking."""
        # Check authentication first
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login

            return redirect_to_login(request.get_full_path())

        # Get the scene to check campaign access
        scene = get_object_or_404(Scene, pk=kwargs["pk"])

        # Check if user has access to this scene's campaign
        # Superusers have access to all scenes
        if not request.user.is_superuser:
            user_role = scene.campaign.get_user_role(request.user)
            if user_role not in ["OWNER", "GM"]:
                if user_role in ["PLAYER", "OBSERVER"]:
                    raise PermissionDenied(
                        "Only campaign owners and GMs can edit scenes."
                    )
                else:
                    raise Http404("Scene not found")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Add scene-specific context."""
        context = super().get_context_data(**kwargs)
        scene = self.get_object()

        context.update(
            {
                "page_title": f"Edit {scene.name} - {scene.campaign.name}",
                "campaign": scene.campaign,
            }
        )

        return context

    def get_success_url(self):
        """Redirect to scene detail after successful update."""
        return reverse("scenes:scene_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        """Handle successful form submission."""
        messages.success(
            self.request, f'Scene "{self.object.name}" was updated successfully!'
        )
        return super().form_valid(form)

    def form_invalid(self, form):
        """Handle invalid form submission."""
        messages.error(self.request, "Please correct the errors below and try again.")
        return super().form_invalid(form)


class SceneStatusChangeView(View):
    """
    AJAX view for changing scene status.

    Only OWNER and GM can change scene status.
    """

    def post(self, request, *args, **kwargs):
        """Handle AJAX request to change scene status."""
        # Check authentication
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login

            return redirect_to_login(request.get_full_path())

        # Get the scene
        scene = get_object_or_404(Scene, pk=kwargs["pk"])

        # Check if user has access to this scene's campaign
        # Superusers have access to all scenes
        if not request.user.is_superuser:
            user_role = scene.campaign.get_user_role(request.user)
            if user_role not in ["OWNER", "GM"]:
                if user_role in ["PLAYER", "OBSERVER"]:
                    return JsonResponse({"error": "Permission denied"}, status=403)
                else:
                    return JsonResponse({"error": "Scene not found"}, status=404)

        # Get new status from request (handle both JSON and form data)
        if request.content_type == "application/json":
            try:
                data = json.loads(request.body)
                new_status = data.get("status")
            except json.JSONDecodeError:
                return JsonResponse({"error": "Invalid JSON"}, status=400)
        else:
            new_status = request.POST.get("status")

        if not new_status:
            return JsonResponse({"error": "Status required"}, status=400)

        # Create form with the scene instance and new status
        form = SceneStatusChangeForm({"status": new_status}, instance=scene)

        if form.is_valid():
            status_changed = form.save()

            # Check if this is an AJAX request
            if (
                request.headers.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest"
                or request.content_type == "application/json"
            ):
                if status_changed:
                    return JsonResponse(
                        {
                            "success": True,
                            "message": f"Scene status changed to "
                            f"{scene.get_status_display()}",
                            "new_status": scene.status,
                            "new_status_display": scene.get_status_display(),
                        }
                    )
                else:
                    return JsonResponse(
                        {
                            "success": True,
                            "message": "Status unchanged",
                            "new_status": scene.status,
                            "new_status_display": scene.get_status_display(),
                        }
                    )
            else:
                # Regular form submission - redirect to scene detail
                if status_changed:
                    messages.success(
                        request, f"Scene status changed to {scene.get_status_display()}"
                    )
                return redirect("scenes:scene_detail", pk=scene.pk)
        else:
            # Check if this is an AJAX request for errors
            if (
                request.headers.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest"
                or request.content_type == "application/json"
            ):
                errors = []
                for field, field_errors in form.errors.items():
                    for error in field_errors:
                        errors.append(f"{field}: {error}")

                return JsonResponse(
                    {"error": "Validation failed", "details": errors}, status=400
                )
            else:
                # Regular form submission with errors - redirect back with error message
                for field, field_errors in form.errors.items():
                    for error in field_errors:
                        messages.error(request, f"{field}: {error}")
                return redirect("scenes:scene_detail", pk=scene.pk)
