from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django_fsm import FSMField, transition  # type: ignore[import-untyped]
from polymorphic.managers import PolymorphicManager  # type: ignore[import-untyped]
from polymorphic.models import PolymorphicModel  # type: ignore[import-untyped]
from polymorphic.query import PolymorphicQuerySet  # type: ignore[import-untyped]

from campaigns.models import Campaign
from core.models import DetailedAuditableMixin, NamedModelMixin, TimestampedMixin

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser


class CharacterAuditLog(models.Model):
    """Audit trail for character changes."""

    character: models.ForeignKey = models.ForeignKey(
        "Character",
        on_delete=models.CASCADE,
        related_name="audit_entries",
        help_text="The character this audit entry belongs to",
    )
    changed_by: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        help_text="User who made the change",
    )
    action: models.CharField = models.CharField(
        max_length=20,
        choices=[
            ("CREATE", "Created"),
            ("UPDATE", "Updated"),
            ("DELETE", "Deleted"),
            ("RESTORE", "Restored"),
        ],
        help_text="Type of action performed",
    )
    field_changes = models.JSONField(
        default=dict,
        help_text="Dictionary of field changes: {field_name: {old: value, new: value}}",
    )
    timestamp: models.DateTimeField = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "characters_character_audit"
        ordering = ["-timestamp"]
        verbose_name = "Character Audit Entry"
        verbose_name_plural = "Character Audit Entries"

    @property
    def user(self) -> Optional["AbstractUser"]:
        """Alias for changed_by to match test expectations."""
        return self.changed_by

    @property
    def changes(self) -> Dict[str, Any]:
        """Alias for field_changes to match test expectations."""
        return self.field_changes

    @classmethod
    def get_for_user(
        cls, character: "Character", user: Optional["AbstractUser"]
    ) -> "models.QuerySet[CharacterAuditLog]":
        """Get audit entries for a character that a user can view.

        Args:
            character: The Character instance
            user: The user requesting audit entries

        Returns:
            QuerySet of audit entries the user can view
        """
        if not user or not user.is_authenticated:
            return cls.objects.none()

        # Check if user has permission to view this character
        if not character.can_be_edited_by(user):
            # Also check if user is character owner or has read access
            permission_level = character.get_permission_level(user)
            if permission_level == "none":
                return cls.objects.none()

        return cls.objects.filter(character=character)

    def __str__(self) -> str:
        """Return string representation of audit entry."""
        # Use getattr to handle mypy's inability to recognize Django's
        # get_FOO_display methods
        action_display = getattr(self, "get_action_display", lambda: self.action)()
        return (
            f"{self.character.name} - {action_display} "
            f"by {self.changed_by} at {self.timestamp}"
        )


class CharacterQuerySet(PolymorphicQuerySet):
    """Custom QuerySet for Character with filtering methods."""

    def active(self) -> "CharacterQuerySet":
        """Filter to only active (non-deleted) characters."""
        return self.filter(is_deleted=False)

    def deleted(self) -> "CharacterQuerySet":
        """Filter to only soft-deleted characters."""
        return self.filter(is_deleted=True)

    def for_campaign(self, campaign: Campaign) -> "CharacterQuerySet":
        """Filter characters belonging to a specific campaign.

        Args:
            campaign: The campaign to filter by

        Returns:
            QuerySet of characters in the campaign
        """
        if campaign is None:
            raise ValueError("Campaign parameter cannot be None")
        return self.filter(campaign=campaign)

    def owned_by(self, user: Optional["AbstractUser"]) -> "CharacterQuerySet":
        """Filter characters owned by a specific user.

        Args:
            user: The user to filter by, or None for no characters

        Returns:
            QuerySet of characters owned by the user
        """
        if user is None:
            return self.none()
        return self.filter(player_owner=user)

    def with_campaign_memberships(self) -> "CharacterQuerySet":
        """Prefetch campaign memberships to optimize permission checks.

        Use this method when you need to check permissions for multiple characters
        to avoid N+1 queries.

        Returns:
            QuerySet with prefetched campaign memberships
        """
        return self.select_related("campaign", "campaign__owner").prefetch_related(
            "campaign__memberships__user"
        )

    def npcs(self) -> "CharacterQuerySet":
        """Filter to only NPCs (Non-Player Characters).

        Returns:
            QuerySet of only NPC characters
        """
        return self.filter(npc=True)

    def player_characters(self) -> "CharacterQuerySet":
        """Filter to only Player Characters (PCs).

        Returns:
            QuerySet of only PC characters
        """
        return self.filter(npc=False)

    def editable_by(
        self, user: Optional["AbstractUser"], campaign: Campaign
    ) -> "CharacterQuerySet":
        """Filter characters that can be edited by a user in a campaign.

        Args:
            user: The user to check edit permissions for
            campaign: The campaign to check within

        Returns:
            QuerySet of characters the user can edit
        """
        if user is None:
            return self.none()

        if campaign is None:
            raise ValueError("Campaign parameter cannot be None")

        # Get user's role in the campaign (this is a single query, not N+1 issue)
        user_role = campaign.get_user_role(user)

        if user_role is None:
            # Non-members cannot edit any characters
            return self.none()
        elif user_role in ["OWNER", "GM"]:
            # Campaign owners and GMs can edit all characters in their campaign
            return self.filter(campaign=campaign)
        elif user_role in ["PLAYER"]:
            # Players can only edit their own characters
            return self.filter(campaign=campaign, player_owner=user)
        else:
            # Observers and others cannot edit any characters
            return self.none()


class CharacterManager(PolymorphicManager):
    """Custom manager for Character with query methods."""

    def get_queryset(self):
        """Return the custom CharacterQuerySet, excluding soft-deleted by default."""
        return CharacterQuerySet(self.model, using=self._db).filter(is_deleted=False)

    def for_campaign(self, campaign: Campaign):
        """Get characters for a specific campaign.

        Args:
            campaign: The campaign to get characters for

        Returns:
            QuerySet of characters in the campaign
        """
        if campaign is None:
            raise ValueError("Campaign parameter cannot be None")
        return self.get_queryset().filter(campaign=campaign)

    def owned_by(self, user: Optional["AbstractUser"]):
        """Get characters owned by a specific user.

        Args:
            user: The user to get characters for

        Returns:
            QuerySet of characters owned by the user
        """
        if user is None:
            return self.none()
        return self.get_queryset().filter(player_owner=user)

    def editable_by(self, user: Optional["AbstractUser"], campaign: Campaign):
        """Get characters that can be edited by a user in a campaign.

        Args:
            user: The user to check edit permissions for
            campaign: The campaign to check within

        Returns:
            QuerySet of characters the user can edit
        """
        if user is None:
            return self.none()

        if campaign is None:
            raise ValueError("Campaign parameter cannot be None")

        # Get user's role in the campaign
        user_role = campaign.get_user_role(user)

        if user_role is None:
            # Non-members cannot edit any characters
            return self.none()
        elif user_role in ["OWNER", "GM"]:
            # Campaign owners and GMs can edit all characters in their campaign
            return self.get_queryset().filter(campaign=campaign)
        elif user_role in ["PLAYER"]:
            # Players can only edit their own characters
            return self.get_queryset().filter(campaign=campaign, player_owner=user)
        else:
            # Observers and others cannot edit any characters
            return self.none()

    def npcs(self):
        """Get only NPCs (Non-Player Characters).

        Returns:
            QuerySet of only NPC characters
        """
        return self.get_queryset().filter(npc=True)

    def player_characters(self):
        """Get only Player Characters (PCs).

        Returns:
            QuerySet of only PC characters
        """
        return self.get_queryset().filter(npc=False)

    def with_campaign_memberships(self):
        """Get characters with prefetched campaign memberships.

        Returns:
            QuerySet with prefetched campaign memberships for optimization
        """
        return (
            self.get_queryset()
            .select_related("campaign", "campaign__owner")
            .prefetch_related("campaign__memberships__user")
        )


class AllCharacterManager(PolymorphicManager):
    """Manager that includes soft-deleted characters."""

    def get_queryset(self):
        """Return the polymorphic QuerySet including all characters."""
        return super().get_queryset()


class NPCManager(PolymorphicManager):
    """Manager for NPC (Non-Player Character) filtering."""

    def get_queryset(self):
        """Return QuerySet filtered to only NPCs (npc=True) and not soft-deleted."""
        return super().get_queryset().filter(npc=True, is_deleted=False)


class PCManager(PolymorphicManager):
    """Manager for PC (Player Character) filtering."""

    def get_queryset(self):
        """Return QuerySet filtered to only PCs (npc=False) and not soft-deleted."""
        return super().get_queryset().filter(npc=False, is_deleted=False)


class Character(
    TimestampedMixin, NamedModelMixin, DetailedAuditableMixin, PolymorphicModel
):
    """Base Character model for all game systems with mixin-based functionality.

    Provides standardized fields through mixins:
    - TimestampedMixin: created_at, updated_at fields with indexing
    - NamedModelMixin: name field with __str__ method
    - DetailedAuditableMixin: created_by, modified_by tracking with detailed audit trail
    """

    description: models.TextField = models.TextField(
        blank=True, default="", help_text="Character description and background"
    )
    campaign: models.ForeignKey = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name="characters",
        help_text="The campaign this character belongs to",
    )
    player_owner: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_characters",
        help_text="The player who owns this character",
    )
    game_system: models.CharField = models.CharField(
        max_length=100, help_text="The game system this character uses"
    )
    npc: models.BooleanField = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether this character is an NPC (Non-Player Character)",
    )

    # Character status FSM field
    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("SUBMITTED", "Submitted"),
        ("ACTIVE", "Active"),
        ("INACTIVE", "Inactive"),
        ("RETIRED", "Retired"),
        ("DECEASED", "Deceased"),
    ]

    status: FSMField = FSMField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="DRAFT",
        protected=False,  # Allow direct setting during creation
        db_index=True,
        help_text="Current status of the character in the campaign",
    )

    # Soft delete fields
    is_deleted: models.BooleanField = models.BooleanField(
        default=False, help_text="Whether this character has been soft deleted"
    )
    deleted_at: models.DateTimeField = models.DateTimeField(
        null=True, blank=True, help_text="When this character was deleted"
    )
    deleted_by: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deleted_characters",
        help_text="User who deleted this character",
    )

    objects = CharacterManager()
    all_objects = AllCharacterManager()
    npcs = NPCManager()
    pcs = PCManager()

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the model and store original field values for change tracking."""
        super().__init__(*args, **kwargs)
        # Additional Character-specific original values for legacy compatibility
        # The parent DetailedAuditableMixin already stores _original_values
        self._original_campaign_id = self.__dict__.get("campaign_id")
        self._original_player_owner_id = self.__dict__.get("player_owner_id")
        self._original_name = self.__dict__.get("name", "")
        self._original_description = self.__dict__.get("description", "")
        self._original_game_system = self.__dict__.get("game_system", "")
        self._original_npc = self.__dict__.get("npc", False)
        self._original_status = self.__dict__.get("status", "DRAFT")

    class Meta:
        db_table = "characters_character"
        constraints = [
            models.UniqueConstraint(
                fields=["campaign", "name"], name="unique_character_name_per_campaign"
            ),
        ]
        indexes = [
            models.Index(
                fields=["campaign", "player_owner"],
                name="characters_character_count_idx",
            ),
        ]
        ordering = ["name"]
        verbose_name = "Character"
        verbose_name_plural = "Characters"

    def __str__(self) -> str:
        """Return the character name."""
        return self.name

    # DetailedAuditableMixin integration methods
    def _get_audit_log_model(self):
        """Return the CharacterAuditLog model for detailed audit trail."""
        return CharacterAuditLog

    def _get_audit_entry_fields(self, user, action, field_changes):
        """Get fields for creating a CharacterAuditLog entry."""
        return {
            "character": self,
            "changed_by": user,
            "action": action,
            "field_changes": field_changes,
        }

    def _get_tracked_fields(self):
        """Get list of fields to track for Character audit trail."""
        return [
            "name",
            "description",
            "game_system",
            "campaign_id",
            "player_owner_id",
            "npc",
            "status",
        ]

    def _has_campaign_changed(self) -> bool:
        """Check if the campaign field has changed since the instance was loaded."""
        return self.campaign_id != self._original_campaign_id

    def _has_player_owner_changed(self) -> bool:
        """Check if the player_owner field has changed since the instance was loaded."""
        return self.player_owner_id != self._original_player_owner_id

    def _should_validate_membership(self) -> bool:
        """
        Determine if membership validation should be performed.

        Returns True if:
        1. This is a new character (pk is None), OR
        2. The campaign or player_owner has changed
        """
        if self.pk is None:
            # Always validate for new characters
            return True

        # For existing characters, only validate if key fields changed
        return self._has_campaign_changed() or self._has_player_owner_changed()

    def clean(self) -> None:
        """Validate the character data."""
        super().clean()

        # Validate character name is not empty/blank
        if not self.name or not self.name.strip():
            raise ValidationError("Character name cannot be empty.")

        # Validate character name length
        if len(self.name) > 100:
            raise ValidationError("Character name cannot exceed 100 characters.")

        # Validate that player is a member of the campaign
        # Check membership for new characters or when campaign/player_owner changes
        if self.campaign and self.player_owner and self._should_validate_membership():
            if not self.campaign.is_member(self.player_owner):
                raise ValidationError(
                    "Only campaign members (players, GMs, owners) can own "
                    "characters in this campaign."
                )

        # Validate max characters per player limit
        if self.campaign and self.player_owner:
            max_chars = self.campaign.max_characters_per_player
            if max_chars > 0:  # 0 means unlimited
                self._validate_character_limit(max_chars)

    @transaction.atomic
    def _validate_character_limit(self, max_chars: int) -> None:
        """
        Validate character limit with atomic protection.

        Args:
            max_chars: Maximum characters allowed per player

        Raises:
            ValidationError: If character limit would be exceeded
        """
        from campaigns.models import Campaign

        # Lock the campaign to prevent concurrent character creation
        Campaign.objects.select_for_update().get(pk=self.campaign.pk)

        # Count existing characters for this player in this campaign
        existing_count = (
            Character.objects.filter(
                campaign=self.campaign, player_owner=self.player_owner
            )
            .exclude(pk=self.pk or 0)
            .count()
        )

        if existing_count >= max_chars:
            raise ValidationError(
                f"You cannot have more than {max_chars} "
                f"character{'s' if max_chars != 1 else ''} in this campaign. "
                "Please delete an existing character before creating a new one."
            )

    def save(self, *args: Any, **kwargs: Any) -> None:
        """
        Save the character with validation and audit trail.

        Uses DetailedAuditableMixin for audit functionality while preserving
        Character-specific validation logic.
        """
        # Run validation for new characters or when explicitly requested
        validate = kwargs.pop("validate", self.pk is None)
        if validate:
            self.full_clean()

        # Get audit user from kwargs (support legacy names for compatibility)
        audit_user = kwargs.pop("audit_user", None) or kwargs.pop("update_user", None)

        # Default to player_owner for automatic auditing if no user provided
        if audit_user is None and hasattr(self, "player_owner") and self.player_owner:
            audit_user = self.player_owner

        # Set audit_user back in kwargs for DetailedAuditableMixin to use
        if audit_user:
            kwargs["audit_user"] = audit_user

        # Call parent save method which includes DetailedAuditableMixin logic
        super().save(*args, **kwargs)

        # Update legacy original values for backward compatibility
        self._original_campaign_id = self.campaign_id
        self._original_player_owner_id = self.player_owner_id
        self._original_name = self.name
        self._original_description = self.description
        self._original_game_system = self.game_system
        self._original_npc = self.npc
        self._original_status = self.status

    def refresh_from_db(
        self, using: Optional[str] = None, fields: Optional[List[str]] = None
    ) -> None:
        """Refresh the instance from the database and reset change tracking."""
        # For soft-deleted characters, we need to use all_objects manager
        # But to avoid recursion issues with polymorphic queries during Django's
        # deletion cascades, we'll use a simpler approach

        if hasattr(self, "_state") and self._state.db is None:
            # Object not yet saved, use default behavior
            super().refresh_from_db(using=using, fields=fields)
            return

        # Try with all_objects first (includes soft-deleted)
        try:
            # Use all_objects but be careful with polymorphic fields
            fresh_instance = self.__class__.all_objects.using(using).get(pk=self.pk)

            # Update only the requested fields or all fields
            if fields is None:
                fields = [field.name for field in self._meta.concrete_fields]

            # Clear the related object cache to force fresh retrieval
            if hasattr(self, "_state"):
                self._state.fields_cache.clear()

            for field_name in fields:
                if hasattr(fresh_instance, field_name):
                    setattr(self, field_name, getattr(fresh_instance, field_name))

        except self.__class__.DoesNotExist:
            # Fallback to default behavior for hard-deleted objects
            super().refresh_from_db(using=using, fields=fields)

    def can_be_edited_by(
        self, user: Optional["AbstractUser"], user_role: Optional[str] = None
    ) -> bool:
        """Check if a user can edit this character.

        Args:
            user: The user to check edit permissions for
            user_role: Optional cached user role to avoid database query

        Returns:
            True if the user can edit this character, False otherwise
        """
        if user is None:
            return False

        # Character owners can always edit their characters
        if self.player_owner == user:
            return True

        # Use cached role if provided, otherwise fetch from campaign
        if user_role is None:
            user_role = self._get_cached_user_role(user)

        # Campaign owners and GMs can edit all characters in their campaign
        return user_role in ["OWNER", "GM"]

    def can_be_deleted_by(self, user: Optional["AbstractUser"]) -> bool:
        """Check if a user can delete this character.

        Args:
            user: The user to check delete permissions for

        Returns:
            True if the user can delete this character, False otherwise
        """
        if user is None:
            return False

        # Character owners can always delete their own characters
        if self.player_owner == user:
            return True

        # Get user's role in the campaign
        user_role = self._get_cached_user_role(user)

        if user_role is None:
            return False

        # Check campaign settings for GM/Owner deletion permissions
        if user_role == "OWNER":
            return getattr(self.campaign, "allow_owner_character_deletion", True)
        elif user_role == "GM":
            return getattr(self.campaign, "allow_gm_character_deletion", False)

        # Players, observers, and others cannot delete characters they don't own
        return False

    def get_permission_level(
        self, user: Optional["AbstractUser"], user_role: Optional[str] = None
    ) -> str:
        """Get the permission level a user has for this character.

        Args:
            user: The user to check permissions for
            user_role: Optional cached user role to avoid database query

        Returns:
            Permission level: 'owner', 'campaign_owner', 'gm', 'read', or 'none'
        """
        if user is None:
            return "none"

        # Character owners get highest permission
        if self.player_owner == user:
            return "owner"

        # Use cached role if provided, otherwise fetch from campaign
        if user_role is None:
            user_role = self._get_cached_user_role(user)

        if user_role is None:
            return "none"
        elif user_role == "OWNER":
            return "campaign_owner"
        elif user_role == "GM":
            return "gm"
        elif user_role in ["PLAYER", "OBSERVER"]:
            return "read"
        else:
            return "none"

    def _get_cached_user_role(self, user: "AbstractUser") -> Optional[str]:
        """Get user's role in the campaign.

        Args:
            user: The user to check role for

        Returns:
            User's role in the campaign or None if not a member
        """
        if not user or not user.is_authenticated:
            return None

        return self.campaign.get_user_role(user)

    def soft_delete(
        self, user: "AbstractUser", confirmation_name: Optional[str] = None
    ) -> Union["Character", bool]:
        """Soft delete this character.

        Args:
            user: The user performing the deletion
            confirmation_name: Optional character name confirmation for validation

        Returns:
            Character instance if successful, False if no permission

        Raises:
            ValueError: If character deleted or confirmation name doesn't match
        """
        from django.utils import timezone

        if not self.can_be_deleted_by(user):
            return False

        if self.is_deleted:
            # Return self to indicate success - idempotent operation
            return self

        # Validate confirmation name if provided
        if confirmation_name is not None:
            if not confirmation_name:
                raise ValueError("Confirmation name cannot be empty")
            if confirmation_name != self.name:
                raise ValueError(
                    "Confirmation name must match character name "
                    f"exactly: '{self.name}'"
                )

        # Store original status before soft deletion
        original_status = self.status

        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])

        # Create audit entry using DetailedAuditableMixin method
        self._create_audit_entry(
            user,
            "DELETE",
            {
                "is_deleted": {"old": False, "new": True},
                "status_at_deletion": {"old": None, "new": original_status},
            },
        )

        return self

    def restore(self, user: "AbstractUser") -> "Character":
        """Restore a soft-deleted character.

        Args:
            user: The user performing the restoration

        Raises:
            PermissionError: If user doesn't have permission to restore
            ValueError: If character is not deleted
        """
        if not self.can_be_deleted_by(user):
            raise PermissionError("You don't have permission to restore this character")

        if not self.is_deleted:
            raise ValueError("Character is not deleted")

        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        # Use direct SQL update since default manager excludes soft-deleted chars
        self.__class__.all_objects.filter(pk=self.pk).update(
            is_deleted=False, deleted_at=None, deleted_by=None
        )

        # Create audit entry using DetailedAuditableMixin method
        self._create_audit_entry(
            user, "RESTORE", {"is_deleted": {"old": True, "new": False}}
        )

        return self

    def hard_delete(self, user: "AbstractUser") -> "Character":
        """Permanently delete this character (admin only).

        Args:
            user: The user performing the deletion

        Raises:
            PermissionError: If user is not an admin
        """
        if not user.is_staff:
            raise PermissionError(
                "Only administrators can permanently delete characters"
            )

        # Create final audit entry before deletion using DetailedAuditableMixin method
        self._create_audit_entry(
            user,
            "DELETE",
            {"permanently_deleted": {"old": False, "new": True}},
        )

        self.delete()
        return self

    # FSM Status Transition Methods

    @transition(field=status, source="DRAFT", target="SUBMITTED")
    def submit_for_approval(self, user: "AbstractUser") -> None:
        """Transition from DRAFT to SUBMITTED status.

        Args:
            user: The user performing the transition (must be character owner)

        Raises:
            PermissionError: If user doesn't have permission
        """
        if self.player_owner != user:
            raise PermissionError(
                "Only character owners can submit characters for approval"
            )
        self.save(audit_user=user)

    @transition(field=status, source="SUBMITTED", target="ACTIVE")
    def approve(self, user: "AbstractUser") -> None:
        """Transition from SUBMITTED to ACTIVE status.

        Args:
            user: The user performing the transition (must be GM or campaign owner)

        Raises:
            PermissionError: If user doesn't have permission
        """
        user_role = self.campaign.get_user_role(user)
        if user_role not in ["GM", "OWNER"]:
            raise PermissionError("Only GMs and campaign owners can approve characters")
        self.save(audit_user=user)

    @transition(field=status, source="SUBMITTED", target="DRAFT")
    def reject(self, user: "AbstractUser") -> None:
        """Transition from SUBMITTED to DRAFT status (rejection).

        Args:
            user: The user performing the transition (must be GM or campaign owner)

        Raises:
            PermissionError: If user doesn't have permission
        """
        user_role = self.campaign.get_user_role(user)
        if user_role not in ["GM", "OWNER"]:
            raise PermissionError("Only GMs and campaign owners can reject characters")
        self.save(audit_user=user)

    @transition(field=status, source="ACTIVE", target="INACTIVE")
    def deactivate(self, user: "AbstractUser") -> None:
        """Transition from ACTIVE to INACTIVE status.

        Args:
            user: The user performing the transition (must be GM or campaign owner)

        Raises:
            PermissionError: If user doesn't have permission
        """
        user_role = self.campaign.get_user_role(user)
        if user_role not in ["GM", "OWNER"]:
            raise PermissionError(
                "Only GMs and campaign owners can deactivate characters"
            )
        self.save(audit_user=user)

    @transition(field=status, source="INACTIVE", target="ACTIVE")
    def activate(self, user: "AbstractUser") -> None:
        """Transition from INACTIVE to ACTIVE status.

        Args:
            user: The user performing the transition (must be GM or campaign owner)

        Raises:
            PermissionError: If user doesn't have permission
        """
        user_role = self.campaign.get_user_role(user)
        if user_role not in ["GM", "OWNER"]:
            raise PermissionError(
                "Only GMs and campaign owners can activate characters"
            )
        self.save(audit_user=user)

    @transition(field=status, source="ACTIVE", target="RETIRED")
    def retire(self, user: "AbstractUser") -> None:
        """Transition from ACTIVE to RETIRED status.

        Args:
            user: The user performing the transition

        Raises:
            PermissionError: If user doesn't have permission
        """
        user_role = self.campaign.get_user_role(user)
        if self.player_owner != user and user_role not in ["GM", "OWNER"]:
            raise PermissionError(
                "Only character owners, GMs, and campaign owners can retire characters"
            )
        self.save(audit_user=user)

    @transition(field=status, source="ACTIVE", target="DECEASED")
    def mark_deceased(self, user: "AbstractUser") -> None:
        """Transition from ACTIVE to DECEASED status.

        Args:
            user: The user performing the transition (must be GM or campaign owner)

        Raises:
            PermissionError: If user doesn't have permission
        """
        user_role = self.campaign.get_user_role(user)
        if user_role not in ["GM", "OWNER"]:
            raise PermissionError(
                "Only GMs and campaign owners can mark characters as deceased"
            )
        self.save(audit_user=user)


class WoDCharacter(Character):
    """Base World of Darkness character model."""

    # WoD-specific fields that are common to all WoD games
    willpower: models.PositiveSmallIntegerField = models.PositiveSmallIntegerField(
        default=3, help_text="Character's willpower rating (1-10)"
    )

    class Meta:
        verbose_name = "World of Darkness Character"
        verbose_name_plural = "World of Darkness Characters"


class MageCharacter(WoDCharacter):
    """Mage: The Ascension character model."""

    # Mage-specific fields
    arete: models.PositiveSmallIntegerField = models.PositiveSmallIntegerField(
        default=1, help_text="Mage's Arete rating (1-10)"
    )
    quintessence: models.PositiveSmallIntegerField = models.PositiveSmallIntegerField(
        default=0, help_text="Current quintessence points"
    )
    paradox: models.PositiveSmallIntegerField = models.PositiveSmallIntegerField(
        default=0, help_text="Current paradox points"
    )

    class Meta:
        verbose_name = "Mage Character"
        verbose_name_plural = "Mage Characters"
