"""
Edit and delete views for character management.

Provides character edit and delete views with proper permission checking,
audit trail, and confirmation requirements.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.generic import UpdateView, View

from characters.forms import CharacterDeleteForm, CharacterEditForm
from characters.models import Character


class CharacterEditView(LoginRequiredMixin, UpdateView):
    """
    Edit character view with proper permission checking.

    - Allows character owners, campaign owners, and GMs to edit characters
    - Provides form with validation and audit trail
    - Shows character details and edit form
    """

    model = Character
    form_class = CharacterEditForm
    template_name = "characters/character_edit.html"
    context_object_name = "character"

    def get_object(self, queryset=None):
        """Get character with permission checking."""
        character = get_object_or_404(Character, pk=self.kwargs["pk"])

        # Check if user has permission to edit this character
        if not character.can_be_edited_by(self.request.user):
            raise PermissionDenied("You don't have permission to edit this character.")

        return character

    def get_form_kwargs(self):
        """Pass the current user and character to the form."""
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        kwargs["character"] = self.object
        return kwargs

    def get_context_data(self, **kwargs):
        """Add additional context for the template."""
        context = super().get_context_data(**kwargs)
        character = self.object

        # Get user's role for template rendering
        user_role = character.campaign.get_user_role(self.request.user)

        context.update(
            {
                "page_title": f"Edit {character.name}",
                "user_role": user_role,
                "campaign": character.campaign,
            }
        )

        return context

    def form_valid(self, form):
        """Handle successful form submission."""
        character = form.save()

        messages.success(
            self.request, f"Character '{character.name}' was successfully updated!"
        )

        return redirect(self.get_success_url())

    def form_invalid(self, form):
        """Handle form validation errors."""
        messages.error(
            self.request,
            "There were errors in your character edit form. "
            "Please correct them below.",
        )
        return super().form_invalid(form)

    def get_success_url(self):
        """Return the URL to redirect to after successful character edit."""
        return reverse("characters:detail", kwargs={"pk": self.object.pk})


class CharacterDeleteView(LoginRequiredMixin, View):
    """
    Delete character view with confirmation and permission checking.

    - Supports both soft delete (default) and hard delete (admin only)
    - Requires character name confirmation
    - Creates audit trail entries
    """

    def get(self, request, pk):
        """Display the delete confirmation form."""
        character = get_object_or_404(Character, pk=pk)

        # Check if user has permission to delete this character
        if not character.can_be_deleted_by(request.user):
            messages.error(
                request, "You don't have permission to delete this character."
            )
            return redirect("characters:detail", pk=character.pk)

        form = CharacterDeleteForm(character=character, user=request.user)

        context = {
            "character": character,
            "form": form,
            "page_title": f"Delete {character.name}",
            "user_role": character.campaign.get_user_role(request.user),
            "campaign": character.campaign,
            "can_hard_delete": request.user.is_staff,
        }

        return render(request, "characters/character_delete.html", context)

    def post(self, request, pk):
        """Handle the delete confirmation form submission."""
        character = get_object_or_404(Character, pk=pk)

        # Check if user has permission to delete this character
        if not character.can_be_deleted_by(request.user):
            messages.error(
                request, "You don't have permission to delete this character."
            )
            return redirect("characters:detail", pk=character.pk)

        form = CharacterDeleteForm(request.POST, character=character, user=request.user)

        if form.is_valid():
            try:
                # Check if hard delete was requested (admin only)
                hard_delete = request.POST.get("hard_delete") == "true"

                deleted_character = form.delete_character(hard_delete=hard_delete)

                if hard_delete:
                    messages.success(
                        request,
                        f"Character '{deleted_character.name}' was "
                        "permanently and successfully deleted.",
                    )
                else:
                    messages.success(
                        request,
                        f"Character '{deleted_character.name}' was successfully "
                        f"deleted "
                        f"and can be restored by campaign staff.",
                    )

                # Redirect to campaign characters list
                return redirect(
                    "characters:campaign_characters",
                    campaign_slug=character.campaign.slug,
                )

            except PermissionError as e:
                messages.error(request, str(e))
                return redirect("characters:detail", pk=character.pk)

        # Form is invalid, redisplay with errors
        context = {
            "character": character,
            "form": form,
            "page_title": f"Delete {character.name}",
            "user_role": character.campaign.get_user_role(request.user),
            "campaign": character.campaign,
            "can_hard_delete": request.user.is_staff,
        }

        return render(request, "characters/character_delete.html", context)
