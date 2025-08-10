"""
Core mixins for campaign management views.

These mixins provide common functionality for campaign-scoped views across
different apps.
"""

import logging
import re
from typing import Optional

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db import DatabaseError
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.views.generic import ListView

from campaigns.models import Campaign

logger = logging.getLogger(__name__)


class CampaignFilterMixin(LoginRequiredMixin):
    """
    Mixin to filter views by campaign and handle permissions.

    This mixin provides:
    1. Campaign retrieval from URL slug with validation
    2. Permission checking based on user role
    3. Campaign context for templates
    4. Proper error handling for missing campaigns and database errors
    5. Security logging for unauthorized access attempts
    6. Input validation to prevent injection attacks
    """

    campaign: Optional[Campaign] = None

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """Get campaign and check permissions before processing request."""
        campaign_slug = kwargs.get("slug")

        if not campaign_slug:
            logger.warning(
                f"Missing campaign slug in request from user "
                f"{request.user.pk if request.user.is_authenticated else 'anonymous'}"
            )
            raise Http404("Campaign slug is required")

        # Validate slug format to prevent injection attacks
        if not self._is_valid_slug(campaign_slug):
            logger.warning(
                f"Invalid campaign slug format '{campaign_slug[:50]}...' from user "
                f"{request.user.pk if request.user.is_authenticated else 'anonymous'}"
            )
            raise Http404("Invalid campaign identifier")

        try:
            # Optimized campaign retrieval with related data
            # Use select_related for owner to avoid additional query
            # Use prefetch_related for memberships to optimize role lookups
            campaign_queryset = Campaign.objects.select_related(
                "owner"
            ).prefetch_related("memberships__user")

            self.campaign = get_object_or_404(
                campaign_queryset, slug=campaign_slug, is_active=True
            )

            # Cache user role for the request to avoid repeated lookups
            # This optimization prevents multiple database queries per request
            user_role = self.campaign.get_user_role(request.user)
            self._cached_user_role = user_role

            if not self._has_permission(user_role):
                user_id = (
                    request.user.pk if request.user.is_authenticated else "anonymous"
                )
                logger.info(
                    f"Unauthorized access attempt to campaign '{campaign_slug}' "
                    f"by user {user_id} (role: {user_role})"
                )
                raise Http404(
                    "Campaign not found"
                )  # Hide existence from unauthorized users

        except DatabaseError as e:
            logger.error(
                f"Database error while accessing campaign '{campaign_slug}': {str(e)}"
            )
            raise Http404("Campaign temporarily unavailable")
        except Exception as e:
            logger.error(
                f"Unexpected error while accessing campaign '{campaign_slug}': {str(e)}"
            )
            raise Http404("Campaign not found")

        return super().dispatch(request, *args, **kwargs)

    def _is_valid_slug(self, slug: str) -> bool:
        """
        Validate that slug contains only safe characters.

        Allows alphanumeric characters, hyphens, and underscores.
        Prevents injection attacks through URL parameters.
        """
        if not slug or len(slug) > 100:  # Reasonable length limit
            return False

        # Only allow alphanumeric characters, hyphens, and underscores
        pattern = re.compile(r"^[a-zA-Z0-9_-]+$")
        return bool(pattern.match(slug))

    def _has_permission(self, user_role: Optional[str]) -> bool:
        """
        Check if user has permission to access this view.

        Override this method in subclasses to implement specific permission logic.
        Default: Allow OWNER, GM, PLAYER, OBSERVER
        """
        return user_role in ["OWNER", "GM", "PLAYER", "OBSERVER"]

    def get_user_role(self, user=None) -> Optional[str]:
        """
        Get user's role in this campaign, utilizing cached value when available.

        This method provides an optimized way to retrieve user roles by using
        the cached role calculated during dispatch() when possible.

        Args:
            user: User to get role for (defaults to request.user)

        Returns:
            The user's role or None if not a member
        """
        if user is None:
            user = self.request.user

        # Use cached role if it's for the same user as the request
        if (
            hasattr(self, "_cached_user_role")
            and hasattr(self, "request")
            and user == self.request.user
        ):
            return self._cached_user_role

        # Fall back to campaign method for different users
        return self.campaign.get_user_role(user)

    def get_context_data(self, **kwargs):
        """Add campaign to template context."""
        context = super().get_context_data(**kwargs)
        context["campaign"] = self.campaign
        # Use cached role to avoid repeated database query
        context["user_role"] = getattr(
            self, "_cached_user_role", None
        ) or self.campaign.get_user_role(self.request.user)
        return context

    def _model_has_field(self, model, field_name: str) -> bool:
        """
        Check if a model has a specific field using Django's field introspection.

        This is safer than using hasattr() which can trigger property evaluation.

        Args:
            model: The Django model class to check
            field_name: Name of the field to check for

        Returns:
            bool: True if the field exists, False otherwise
        """
        try:
            model._meta.get_field(field_name)
            return True
        except Exception:
            # get_field raises various exceptions for missing fields
            return False

    def get_queryset(self):
        """
        Filter queryset by campaign with optimized related data loading.

        Override this method to customize filtering logic for specific models.
        """
        if hasattr(super(), "get_queryset"):
            queryset = super().get_queryset()
            if self._model_has_field(queryset.model, "campaign"):
                try:
                    # Apply campaign filter
                    queryset = queryset.filter(campaign=self.campaign)

                    # Optimize queryset with select_related for common ForeignKey
                    # relationships
                    # This prevents N+1 queries when displaying list views
                    queryset = self._optimize_queryset(queryset)

                    return queryset
                except (DatabaseError, ValidationError) as e:
                    logger.error(
                        f"Database error in get_queryset for "
                        f"{queryset.model.__name__}: {str(e)}"
                    )
                    # Return empty queryset instead of crashing
                    return queryset.none()
        return super().get_queryset()

    def _optimize_queryset(self, queryset):
        """
        Apply select_related optimizations to common relationships.

        This method reduces database queries by pre-loading related objects
        that are commonly accessed in list views and detail views.
        """
        model = queryset.model

        # Common optimizations based on model relationships
        optimizations = []

        # Always optimize campaign relationship if it exists
        if self._model_has_field(model, "campaign"):
            optimizations.append("campaign")

        # Optimize user relationships
        if self._model_has_field(model, "player_owner"):
            optimizations.append("player_owner")
        if self._model_has_field(model, "created_by"):
            optimizations.append("created_by")
        if self._model_has_field(model, "owner"):
            optimizations.append("owner")

        # Apply optimizations if any were found
        if optimizations:
            try:
                queryset = queryset.select_related(*optimizations)
            except Exception as e:
                # Log but don't fail if optimization fails
                logger.debug(
                    f"Could not optimize queryset for {model.__name__}: {str(e)}"
                )

        return queryset


class CampaignManagementMixin(CampaignFilterMixin):
    """
    Mixin for campaign management views that require OWNER or GM permissions.
    """

    def _has_permission(self, user_role: Optional[str]) -> bool:
        """Only allow OWNER and GM to access management views."""
        return user_role in ["OWNER", "GM"]


class CampaignCharacterMixin(CampaignFilterMixin):
    """
    Mixin for views with player-specific filtering (characters, items, etc.).

    This mixin automatically detects the appropriate ownership field:
    - Uses 'player_owner' field for Character models
    - Uses 'created_by' field for Location and Item models
    - Logs warnings if no ownership field is found
    - Provides robust error handling for database operations
    """

    def _has_permission(self, user_role: Optional[str]) -> bool:
        """Allow all campaign members to view characters."""
        return user_role in ["OWNER", "GM", "PLAYER", "OBSERVER"]

    def get_queryset(self):
        """Filter characters by campaign and user permissions."""
        if not hasattr(super(), "get_queryset"):
            raise NotImplementedError("get_queryset must be implemented")

        queryset = super().get_queryset()

        try:
            # Filter by campaign
            if self._model_has_field(queryset.model, "campaign"):
                queryset = queryset.filter(campaign=self.campaign)
            else:
                logger.warning(
                    f"Model {queryset.model.__name__} does not have 'campaign' field "
                    f"but is using CampaignCharacterMixin"
                )
                return queryset.none()

            # For players, only show their own characters/items
            # Use cached role to avoid repeated database query
            user_role = getattr(
                self, "_cached_user_role", None
            ) or self.campaign.get_user_role(self.request.user)
            if user_role == "PLAYER":
                # Check which ownership field exists on the model
                if self._model_has_field(queryset.model, "player_owner"):
                    queryset = queryset.filter(player_owner=self.request.user)
                elif self._model_has_field(queryset.model, "created_by"):
                    queryset = queryset.filter(created_by=self.request.user)
                else:
                    # No ownership field found - players can't filter their own items
                    logger.warning(
                        f"Model {queryset.model.__name__} has neither 'player_owner' "
                        f"nor 'created_by' field for player filtering. "
                        f"Player role users will see all items."
                    )
                    # Continue without filtering - let campaign filtering handle it

        except (DatabaseError, ValidationError) as e:
            logger.error(
                f"Database error in CampaignCharacterMixin.get_queryset for "
                f"{queryset.model.__name__}: {str(e)}"
            )
            # Return empty queryset instead of crashing
            return queryset.none()
        except Exception as e:
            logger.error(
                f"Unexpected error in CampaignCharacterMixin.get_queryset for "
                f"{queryset.model.__name__}: {str(e)}"
            )
            return queryset.none()

        return queryset


class CampaignListView(CampaignFilterMixin, ListView):
    """
    Base ListView for campaign-scoped content.

    Provides common functionality for listing campaign content like
    characters, scenes, locations, and items.
    """

    template_name_suffix = "_campaign_list"
    context_object_name = "objects"
    paginate_by = 20

    def get_context_data(self, **kwargs):
        """Add campaign-specific context."""
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "campaign": self.campaign,
                # Use cached role to avoid repeated database query
                "user_role": getattr(self, "_cached_user_role", None)
                or self.campaign.get_user_role(self.request.user),
                "page_title": f"{self.campaign.name} - {self.get_content_type_name()}",
            }
        )
        return context

    def get_content_type_name(self) -> str:
        """Get human-readable name for the content type being listed."""
        if hasattr(self, "model") and self.model:
            return self.model._meta.verbose_name_plural.title()
        return "Items"
