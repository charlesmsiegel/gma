"""
Views for item management.

Provides campaign-scoped item management views with proper permission checking.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from campaigns.models import Campaign
from core.mixins import CampaignFilterMixin, CampaignListView
from items.forms import ItemForm
from items.models import Item


class CampaignItemsMixin:
    """Mixin for campaign-scoped item views with permission checking."""

    def get_campaign(self):
        """Get the campaign from URL parameter."""
        if hasattr(self, "_campaign"):
            return self._campaign

        campaign_slug = self.kwargs.get("slug") or self.kwargs.get("campaign_slug")
        if not campaign_slug:
            raise Http404("Campaign not found")

        try:
            self._campaign = get_object_or_404(Campaign, slug=campaign_slug)
            return self._campaign
        except Campaign.DoesNotExist:
            raise Http404("Campaign not found")

    def check_campaign_access(self):
        """Check if user has access to this campaign."""
        campaign = self.get_campaign()
        user_role = campaign.get_user_role(self.request.user)

        if not user_role:
            raise Http404("Campaign not found")  # Hide existence from non-members

        return user_role

    def check_item_management_permission(self):
        """Check if user can manage items (create/edit/delete)."""
        user_role = self.check_campaign_access()
        return user_role in ["OWNER", "GM"]

    def dispatch(self, request, *args, **kwargs):
        """Check permissions before dispatching."""
        if not request.user.is_authenticated:
            return redirect("users:login")

        # Check basic campaign access for authenticated users
        self.check_campaign_access()

        return super().dispatch(request, *args, **kwargs)


class CampaignItemsView(CampaignItemsMixin, ListView):
    """
    List items in a campaign with search and filtering.

    - OWNER/GM: See all items and can manage them
    - PLAYER/OBSERVER: See all items (read-only access)
    """

    model = Item
    template_name = "items/campaign_items.html"
    context_object_name = "items"
    paginate_by = 20

    def get_queryset(self):
        """Get items for this campaign with search/filtering."""
        campaign = self.get_campaign()
        queryset = (
            Item.objects.filter(campaign=campaign)
            .select_related("owner", "created_by")
            .order_by("name")
        )

        # Search functionality
        search = self.request.GET.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )

        # Filter by owner
        owner_id = self.request.GET.get("owner")
        if owner_id:
            try:
                owner_id = int(owner_id)
                if owner_id == 0:
                    # Filter for unowned items
                    queryset = queryset.filter(owner__isnull=True)
                else:
                    queryset = queryset.filter(owner_id=owner_id)
            except (ValueError, TypeError):
                pass  # Invalid owner_id, ignore filter

        return queryset

    def get_context_data(self, **kwargs):
        """Add item-specific context."""
        context = super().get_context_data(**kwargs)
        campaign = self.get_campaign()
        user_role = campaign.get_user_role(self.request.user)

        # Get characters for filter dropdown
        characters = campaign.characters.all().order_by("name")

        context.update(
            {
                "campaign": campaign,
                "page_title": f"{campaign.name} - Items",
                "can_create_item": user_role in ["OWNER", "GM"],
                "can_manage_items": user_role in ["OWNER", "GM"],
                "search_query": self.request.GET.get("search", ""),
                "owner_filter": self.request.GET.get("owner", ""),
                "characters": characters,
            }
        )

        return context


class ItemCreateView(CampaignItemsMixin, CreateView):
    """Create a new item in a campaign."""

    model = Item
    form_class = ItemForm
    template_name = "items/item_form.html"

    def dispatch(self, request, *args, **kwargs):
        """Check permissions before allowing access."""
        response = super().dispatch(request, *args, **kwargs)

        # Only OWNER/GM can create items
        if not self.check_item_management_permission():
            raise Http404("Page not found")

        return response

    def get_form_kwargs(self):
        """Add campaign context to form."""
        kwargs = super().get_form_kwargs()
        kwargs["campaign"] = self.get_campaign()
        return kwargs

    def form_valid(self, form):
        """Save item with proper audit tracking."""
        self.object = form.save(created_by=self.request.user)
        messages.success(
            self.request, f"Item '{self.object.name}' created successfully."
        )
        return redirect(self.get_success_url())

    def get_success_url(self):
        """Redirect to item detail after creation."""
        return reverse(
            "items:detail",
            kwargs={
                "slug": self.get_campaign().slug,
                "item_id": self.object.id,
            },
        )

    def get_context_data(self, **kwargs):
        """Add context for template."""
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "campaign": self.get_campaign(),
                "page_title": f"Create Item - {self.get_campaign().name}",
                "form_action": "Create",
            }
        )
        return context


class ItemDetailView(CampaignItemsMixin, DetailView):
    """View item details."""

    model = Item
    template_name = "items/item_detail.html"
    context_object_name = "item"
    pk_url_kwarg = "item_id"

    def get_object(self, queryset=None):
        """Get item ensuring it belongs to the campaign."""
        if queryset is None:
            queryset = self.get_queryset()

        campaign = self.get_campaign()
        item_id = self.kwargs.get(self.pk_url_kwarg)

        try:
            return get_object_or_404(queryset.filter(campaign=campaign), pk=item_id)
        except Item.DoesNotExist:
            raise Http404("Item not found")

    def get_context_data(self, **kwargs):
        """Add context for template."""
        context = super().get_context_data(**kwargs)
        campaign = self.get_campaign()
        user_role = campaign.get_user_role(self.request.user)

        context.update(
            {
                "campaign": campaign,
                "page_title": f"{self.object.name} - {campaign.name}",
                "can_edit": user_role in ["OWNER", "GM"]
                or (self.object.created_by == self.request.user),
                "can_delete": self.object.can_be_deleted_by(self.request.user),
            }
        )
        return context


class ItemEditView(CampaignItemsMixin, UpdateView):
    """Edit an existing item."""

    model = Item
    form_class = ItemForm
    template_name = "items/item_form.html"
    pk_url_kwarg = "item_id"

    def dispatch(self, request, *args, **kwargs):
        """Check permissions before allowing access."""
        response = super().dispatch(request, *args, **kwargs)

        # Only OWNER/GM can edit items
        if not self.check_item_management_permission():
            raise Http404("Page not found")

        return response

    def get_object(self, queryset=None):
        """Get item ensuring it belongs to the campaign."""
        if queryset is None:
            queryset = self.get_queryset()

        campaign = self.get_campaign()
        item_id = self.kwargs.get(self.pk_url_kwarg)

        try:
            return get_object_or_404(queryset.filter(campaign=campaign), pk=item_id)
        except Item.DoesNotExist:
            raise Http404("Item not found")

    def get_form_kwargs(self):
        """Add campaign context to form."""
        kwargs = super().get_form_kwargs()
        kwargs["campaign"] = self.get_campaign()
        return kwargs

    def form_valid(self, form):
        """Save item with proper audit tracking."""
        self.object = form.save(modified_by=self.request.user)
        messages.success(
            self.request, f"Item '{self.object.name}' updated successfully."
        )
        return redirect(self.get_success_url())

    def get_success_url(self):
        """Redirect to item detail after editing."""
        return reverse(
            "items:detail",
            kwargs={
                "slug": self.get_campaign().slug,
                "item_id": self.object.id,
            },
        )

    def get_context_data(self, **kwargs):
        """Add context for template."""
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "campaign": self.get_campaign(),
                "page_title": f"Edit {self.object.name} - {self.get_campaign().name}",
                "form_action": "Update",
            }
        )
        return context


class ItemDeleteView(CampaignItemsMixin, DeleteView):
    """Soft delete an item."""

    model = Item
    template_name = "items/item_confirm_delete.html"
    pk_url_kwarg = "item_id"

    def dispatch(self, request, *args, **kwargs):
        """Check basic campaign access before allowing access."""
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        """Get item ensuring it belongs to the campaign."""
        if queryset is None:
            queryset = self.get_queryset()

        campaign = self.get_campaign()
        item_id = self.kwargs.get(self.pk_url_kwarg)

        try:
            return get_object_or_404(queryset.filter(campaign=campaign), pk=item_id)
        except Item.DoesNotExist:
            raise Http404("Item not found")

    def delete(self, request, *args, **kwargs):
        """Perform soft delete instead of actual deletion."""
        self.object = self.get_object()

        try:
            self.object.soft_delete(request.user)
            messages.success(
                request, f"Item '{self.object.name}' deleted successfully."
            )
        except PermissionError:
            # Hide the resource from unauthorized users
            raise Http404("Page not found")
        except ValueError as e:
            messages.error(request, str(e))
            return redirect(self.get_success_url())

        return redirect(self.get_success_url())

    def form_valid(self, form):
        """Override to prevent Django's default deletion."""
        # Don't call super() as it would perform hard delete
        return self.delete(self.request)

    def get_success_url(self):
        """Redirect to item list after deletion."""
        return reverse(
            "campaigns:campaign_items", kwargs={"slug": self.get_campaign().slug}
        )

    def get_context_data(self, **kwargs):
        """Add context for template."""
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "campaign": self.get_campaign(),
                "page_title": f"Delete {self.object.name} - {self.get_campaign().name}",
            }
        )
        return context
