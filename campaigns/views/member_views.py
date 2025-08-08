"""
Views for campaign member management.
"""

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import FormView, TemplateView

from campaigns.forms import (
    BulkMemberManagementForm,
    ChangeMemberRoleForm,
    SendInvitationForm,
)
from campaigns.models import Campaign, CampaignInvitation, CampaignMembership

User = get_user_model()


class ManageMembersView(LoginRequiredMixin, TemplateView):
    """View for managing campaign members."""

    template_name = "campaigns/manage_members.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        slug = kwargs.get("slug")
        campaign = get_object_or_404(Campaign, slug=slug, is_active=True)

        # Check if user has permission to manage members
        user_role = campaign.get_user_role(self.request.user)
        if user_role not in ["OWNER", "GM"]:
            messages.error(self.request, "You don't have permission to manage members.")
            context["campaign"] = campaign
            context["can_manage"] = False
            return context

        context["campaign"] = campaign
        context["can_manage"] = True
        context["members"] = campaign.memberships.select_related("user").order_by(
            "role", "user__username"
        )

        return context


class SendInvitationView(LoginRequiredMixin, FormView):
    """View for sending campaign invitations."""

    template_name = "campaigns/send_invitation.html"
    form_class = SendInvitationForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        campaign = get_object_or_404(Campaign, slug=self.kwargs["slug"])
        kwargs["campaign"] = campaign
        return kwargs

    def post(self, request, *args, **kwargs):
        """Handle both form submission and direct user ID submission."""
        campaign = get_object_or_404(Campaign, slug=self.kwargs["slug"])

        # Check permissions
        user_role = campaign.get_user_role(request.user)
        if user_role not in ["OWNER", "GM"]:
            messages.error(request, "You don't have permission to send invitations.")
            return redirect("campaigns:detail", slug=campaign.slug)

        # Handle direct user ID submission (from tests or AJAX)
        if "invited_user_id" in request.POST:
            invited_user_id = request.POST.get("invited_user_id", "").strip()
            if not invited_user_id:
                messages.error(request, "Please select a user to invite.")
                return redirect("campaigns:send_invitation", slug=campaign.slug)

            try:
                invited_user = User.objects.get(id=invited_user_id)
                role = request.POST.get("role", "PLAYER")
                message = request.POST.get("message", "")

                # Create invitation
                invitation = CampaignInvitation.objects.create(
                    campaign=campaign,
                    invited_user=invited_user,
                    invited_by=request.user,
                    role=role,
                    message=message,
                )
                messages.success(
                    request, f"Invitation sent to {invitation.invited_user.username}!"
                )
                return redirect("campaigns:manage_members", slug=campaign.slug)
            except User.DoesNotExist:
                messages.error(request, "User not found.")
                return redirect("campaigns:send_invitation", slug=campaign.slug)

        # Otherwise, handle normal form submission
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        campaign = get_object_or_404(Campaign, slug=self.kwargs["slug"])

        # Create invitation
        invitation = form.save(invited_by=self.request.user, campaign=campaign)
        messages.success(
            self.request, f"Invitation sent to {invitation.invited_user.username}!"
        )
        return redirect("campaigns:manage_members", slug=campaign.slug)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["campaign"] = get_object_or_404(Campaign, slug=self.kwargs["slug"])
        return context


class ChangeMemberRoleView(LoginRequiredMixin, FormView):
    """View for changing member roles."""

    template_name = "campaigns/change_member_role.html"
    form_class = ChangeMemberRoleForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        campaign = get_object_or_404(Campaign, slug=self.kwargs["slug"])
        kwargs["campaign"] = campaign
        return kwargs

    def form_valid(self, form):
        campaign = get_object_or_404(Campaign, slug=self.kwargs["slug"])

        # Check permissions
        user_role = campaign.get_user_role(self.request.user)
        if user_role not in ["OWNER", "GM"]:
            messages.error(self.request, "You don't have permission to change roles.")
            return redirect("campaigns:detail", slug=campaign.slug)

        # Update role
        membership = form.save()
        messages.success(self.request, f"Role updated for {membership.user.username}!")
        return redirect("campaigns:manage_members", slug=campaign.slug)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["campaign"] = get_object_or_404(Campaign, slug=self.kwargs["slug"])
        return context


class BulkMemberManagementView(LoginRequiredMixin, FormView):
    """View for bulk member operations."""

    template_name = "campaigns/bulk_member_management.html"
    form_class = BulkMemberManagementForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        campaign = get_object_or_404(Campaign, slug=self.kwargs["slug"])
        kwargs["campaign"] = campaign
        return kwargs

    def form_valid(self, form):
        campaign = get_object_or_404(Campaign, slug=self.kwargs["slug"])

        # Check permissions
        user_role = campaign.get_user_role(self.request.user)
        if user_role not in ["OWNER", "GM"]:
            messages.error(
                self.request, "You don't have permission for bulk operations."
            )
            return redirect("campaigns:detail", slug=campaign.slug)

        # Process bulk operation
        result = form.process_bulk_operation()
        messages.success(self.request, f"Bulk operation completed: {result}")
        return redirect("campaigns:manage_members", slug=campaign.slug)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["campaign"] = get_object_or_404(Campaign, slug=self.kwargs["slug"])
        return context


# AJAX Views
class AjaxUserSearchView(LoginRequiredMixin, View):
    """AJAX endpoint for user search."""

    def get(self, request, *args, **kwargs):
        campaign = get_object_or_404(Campaign, slug=kwargs["slug"])

        # Check permissions
        user_role = campaign.get_user_role(request.user)
        if user_role not in ["OWNER", "GM"]:
            return JsonResponse({"error": "Permission denied"}, status=403)

        query = request.GET.get("q", "").strip()
        if len(query) < 2:
            return JsonResponse({"users": []})

        # Search users
        users = (
            User.objects.filter(username__icontains=query)
            .exclude(id=campaign.owner.id)
            .exclude(campaign_memberships__campaign=campaign)[:10]
        )

        results = [
            {"id": user.id, "username": user.username, "email": user.email}
            for user in users
        ]

        return JsonResponse({"users": results})


class AjaxChangeMemberRoleView(LoginRequiredMixin, View):
    """AJAX endpoint for changing member roles."""

    def post(self, request, *args, **kwargs):
        campaign = get_object_or_404(Campaign, slug=kwargs["slug"])

        # Check permissions
        user_role = campaign.get_user_role(request.user)
        if user_role not in ["OWNER", "GM"]:
            return JsonResponse({"error": "Permission denied"}, status=403)

        user_id = request.POST.get("user_id")
        new_role = request.POST.get("role")

        if not user_id or not new_role:
            return JsonResponse({"error": "Missing parameters"}, status=400)

        if new_role not in ["GM", "PLAYER", "OBSERVER"]:
            return JsonResponse({"error": "Invalid role"}, status=400)

        # Update membership
        try:
            membership = CampaignMembership.objects.get(
                campaign=campaign, user_id=user_id
            )
            membership.role = new_role
            membership.save()

            return JsonResponse(
                {"success": True, "message": f"Role updated to {new_role}"}
            )
        except CampaignMembership.DoesNotExist:
            return JsonResponse({"error": "Member not found"}, status=404)


class AjaxRemoveMemberView(LoginRequiredMixin, View):
    """AJAX endpoint for removing members."""

    def post(self, request, *args, **kwargs):
        campaign = get_object_or_404(Campaign, slug=kwargs["slug"])

        # Check permissions
        user_role = campaign.get_user_role(request.user)
        if user_role not in ["OWNER", "GM"]:
            return JsonResponse({"error": "Permission denied"}, status=403)

        user_id = request.POST.get("user_id")

        if not user_id:
            return JsonResponse({"error": "Missing user_id"}, status=400)

        # Cannot remove owner
        if int(user_id) == campaign.owner.id:
            return JsonResponse({"error": "Cannot remove campaign owner"}, status=400)

        # Remove member
        try:
            membership = CampaignMembership.objects.get(
                campaign=campaign, user_id=user_id
            )

            # GM can't remove other GMs
            if user_role == "GM" and membership.role == "GM":
                return JsonResponse(
                    {"error": "GMs cannot remove other GMs"}, status=403
                )

            membership.delete()

            return JsonResponse(
                {"success": True, "message": "Member removed successfully"}
            )
        except CampaignMembership.DoesNotExist:
            return JsonResponse({"error": "Member not found"}, status=404)
