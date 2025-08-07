"""
Campaign views for web interface.

This module provides Django views for campaign creation, editing, and management
through the web interface, including proper authentication and permission checks.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import CreateView, DetailView, ListView

from ..forms import CampaignForm
from ..models import Campaign


class CampaignListView(ListView):
    """View for listing campaigns."""

    model = Campaign
    template_name = "campaigns/campaign_list.html"
    context_object_name = "campaigns"
    paginate_by = 20

    def get_queryset(self):
        """Return campaigns visible to the user."""
        # For now, return all active campaigns
        # Later this can be filtered by membership, permissions, etc.
        return Campaign.objects.filter(is_active=True).select_related("owner")


class CampaignDetailView(DetailView):
    """View for displaying campaign details."""

    model = Campaign
    template_name = "campaigns/campaign_detail.html"
    context_object_name = "campaign"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        """Return campaigns visible to the user."""
        # For now, return all campaigns
        # Later this can be filtered by permissions
        return Campaign.objects.select_related("owner")

    def get_context_data(self, **kwargs):
        """Add additional context for the template."""
        context = super().get_context_data(**kwargs)
        campaign = self.get_object()
        user = self.request.user

        # Add user permissions for this campaign
        if user.is_authenticated:
            context["user_role"] = campaign.get_user_role(user)
            context["is_owner"] = campaign.is_owner(user)
            context["is_member"] = campaign.is_member(user)
        else:
            context["user_role"] = None
            context["is_owner"] = False
            context["is_member"] = False

        return context


class CampaignCreateView(LoginRequiredMixin, CreateView):
    """View for creating new campaigns."""

    model = Campaign
    form_class = CampaignForm
    template_name = "campaigns/campaign_create.html"

    def form_valid(self, form):
        """Handle valid form submission by setting the owner."""
        campaign = form.save(owner=self.request.user)
        messages.success(
            self.request, f'Campaign "{campaign.name}" was created successfully!'
        )
        return redirect("campaigns:detail", slug=campaign.slug)

    def form_invalid(self, form):
        """Handle invalid form submission."""
        messages.error(self.request, "Please correct the errors below and try again.")
        return super().form_invalid(form)


@login_required
def campaign_create_function_view(request):
    """
    Function-based view for campaign creation.

    This provides an alternative to the class-based view for scenarios
    where more control over the request handling is needed.
    """
    if request.method == "POST":
        form = CampaignForm(request.POST)
        if form.is_valid():
            campaign = form.save(owner=request.user)
            messages.success(
                request, f'Campaign "{campaign.name}" was created successfully!'
            )
            return redirect("campaigns:detail", slug=campaign.slug)
        else:
            messages.error(request, "Please correct the errors below and try again.")
    else:
        form = CampaignForm()

    return render(
        request,
        "campaigns/campaign_create.html",
        {"form": form, "title": "Create New Campaign"},
    )


def campaign_detail_function_view(request, slug):
    """
    Function-based view for campaign detail.

    This provides an alternative to the class-based view for scenarios
    where more control over the request handling is needed.
    """
    campaign = get_object_or_404(Campaign, slug=slug)

    # Get user role and permissions
    user_role = None
    is_owner = False
    is_member = False

    if request.user.is_authenticated:
        user_role = campaign.get_user_role(request.user)
        is_owner = campaign.is_owner(request.user)
        is_member = campaign.is_member(request.user)

    context = {
        "campaign": campaign,
        "user_role": user_role,
        "is_owner": is_owner,
        "is_member": is_member,
    }

    return render(request, "campaigns/campaign_detail.html", context)
