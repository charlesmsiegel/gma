"""
Core model mixins for reusable model functionality.

These mixins provide common fields and behaviors that can be shared across
multiple models in the application. Each mixin is designed to be composable
and can be used individually or in combination with other mixins.

Available mixins:
- TimestampedMixin: Automatic created_at and updated_at fields
- DisplayableMixin: Fields for controlling display and ordering
- NamedModelMixin: Standard name field with __str__ method
- DescribedModelMixin: Optional description field
- AuditableMixin: User tracking for creation and modification
- GameSystemMixin: Game system choices for campaign-related models

Usage:
    class MyModel(TimestampedMixin, NamedModelMixin):
        extra_field = models.CharField(max_length=100)

        class Meta:
            app_label = 'myapp'
"""

from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class TimestampedMixin(models.Model):
    """
    Mixin to add automatic timestamp tracking to models.

    Provides:
    - created_at: Automatically set when object is first created (indexed)
    - updated_at: Automatically updated every time object is saved (indexed)

    Performance Notes:
    - Both fields are indexed for efficient date-based queries
    - Use select_related() when querying models with timestamp-based ordering
    """

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="Timestamp when the object was created",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        db_index=True,
        help_text="Timestamp when the object was last modified",
    )

    class Meta:
        abstract = True


class DisplayableMixin(models.Model):
    """
    Mixin to add display control and ordering to models.

    Provides:
    - is_displayed: Boolean flag to control visibility
    - display_order: Integer for custom ordering (0 = first, indexed)

    Performance Notes:
    - display_order is indexed for efficient ordering queries
    - Consider composite indexes (is_displayed, display_order) for heavy-use models
    """

    is_displayed = models.BooleanField(
        default=True,
        help_text="Whether this item should be displayed in lists and views",
    )
    display_order = models.PositiveIntegerField(
        default=0,
        db_index=True,
        help_text="Order for displaying items (0 = first, higher numbers = later)",
    )

    class Meta:
        abstract = True


class NamedModelMixin(models.Model):
    """
    Mixin to add a standardized name field with __str__ method.

    Provides:
    - name: Required CharField with 100 character limit
    - __str__: Returns the name of the object

    Performance Notes:
    - Consider adding db_index=True if you frequently search by name
    - Use name__icontains for case-insensitive search
    """

    name = models.CharField(max_length=100, help_text="Name of the object")

    def __str__(self):
        return self.name

    class Meta:
        abstract = True


class DescribedModelMixin(models.Model):
    """
    Mixin to add an optional description field to models.

    Provides:
    - description: Optional TextField for detailed information

    Performance Notes:
    - TextField is not indexed by default (appropriate for large text)
    - Use description__icontains for text search, consider full-text for large data
    """

    description = models.TextField(
        blank=True, default="", help_text="Optional detailed description"
    )

    class Meta:
        abstract = True


class AuditableMixin(models.Model):
    """
    Mixin to add user audit tracking to models.

    Provides:
    - created_by: Optional ForeignKey to User who created the object
    - modified_by: Optional ForeignKey to User who last modified the object
    - save(): Enhanced save method that accepts 'user' parameter for automatic tracking

    Usage:
        obj.save(user=request.user)  # Automatically sets modified_by

    Performance Notes:
    - Use select_related('created_by', 'modified_by') for efficient user queries
    - Foreign key relationships add query overhead if not properly managed
    - Consider using prefetch_related() for reverse lookups
    """

    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="%(app_label)s_%(class)s_created",
        null=True,
        blank=True,
        help_text="User who created this object",
    )
    modified_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="%(app_label)s_%(class)s_modified",
        null=True,
        blank=True,
        help_text="User who last modified this object",
    )

    def save(self, *args, **kwargs):
        """
        Enhanced save method with automatic user tracking.

        Args:
            user: User instance to set as modified_by (and created_by for new objects)
            *args, **kwargs: Standard save arguments
        """
        user = kwargs.pop("user", None)

        if user and hasattr(user, "pk") and user.pk:
            # Set modified_by for all saves
            self.modified_by = user

            # Set created_by only for new objects
            if self.pk is None and not self.created_by:
                self.created_by = user

        super().save(*args, **kwargs)

    class Meta:
        abstract = True


class GameSystemMixin(models.Model):
    """
    Mixin to add game system selection to campaign-related models.

    Provides:
    - game_system: CharField with predefined choices for popular RPG systems

    Performance Notes:
    - game_system field uses choices which are efficient for filtering
    - Consider adding db_index=True if you frequently filter by game_system
    - Choices are optimized for World of Darkness focus while supporting other systems
    """

    GAME_SYSTEM_CHOICES = [
        ("generic", "Generic/Universal"),
        ("wod", "World of Darkness"),
        ("mage", "Mage: The Ascension"),
        ("vampire", "Vampire: The Masquerade"),
        ("werewolf", "Werewolf: The Apocalypse"),
        ("changeling", "Changeling: The Dreaming"),
        ("wraith", "Wraith: The Oblivion"),
        ("hunter", "Hunter: The Reckoning"),
        ("mummy", "Mummy: The Resurrection"),
        ("demon", "Demon: The Fallen"),
        ("nwod", "Chronicles of Darkness"),
        ("dnd5e", "Dungeons & Dragons 5th Edition"),
        ("pathfinder", "Pathfinder"),
        ("shadowrun", "Shadowrun"),
        ("call_of_cthulhu", "Call of Cthulhu"),
        ("savage_worlds", "Savage Worlds"),
        ("fate", "Fate Core"),
        ("pbta", "Powered by the Apocalypse"),
        ("other", "Other"),
    ]

    game_system = models.CharField(
        max_length=50,
        choices=GAME_SYSTEM_CHOICES,
        default="generic",
        help_text="The game system this object is designed for",
    )

    class Meta:
        abstract = True


class DetailedAuditableMixin(AuditableMixin):
    """
    Enhanced auditable mixin that provides detailed audit trail functionality.

    Extends AuditableMixin with:
    - Detailed change tracking with field-level changes
    - Configurable audit log model creation
    - Support for action types (CREATE, UPDATE, DELETE, RESTORE)
    - Permission-based audit access control

    Usage:
        class MyModel(DetailedAuditableMixin, models.Model):
            # Your model fields

            def _get_audit_log_model(self):
                return MyModelAuditLog

        obj.save(user=request.user)  # Creates detailed audit entry

    Performance Notes:
    - Creates audit entries on every save operation
    - Use bulk operations carefully as they bypass audit logging
    - Consider audit log retention policies for high-volume models
    """

    def __init__(self, *args, **kwargs):
        """Initialize the model and store original field values for change tracking."""
        super().__init__(*args, **kwargs)
        self._store_original_values()

    def _store_original_values(self):
        """Store original field values for change tracking."""
        self._original_values = {}
        if self.pk is not None:
            # Only store values for existing objects, but only use __dict__
            # to avoid recursion during Django's object loading and deletion
            for field in self._meta.concrete_fields:
                # Only access fields already loaded in __dict__ to avoid
                # deferred field loading
                if field.name in self.__dict__:
                    self._original_values[field.name] = self.__dict__[field.name]

    def _should_create_audit_entry(self):
        """Determine if an audit entry should be created."""
        # Override this method in subclasses to customize audit entry creation
        return True

    def _get_tracked_fields(self):
        """Get list of field names to track for changes."""
        # Override this method in subclasses to customize tracked fields
        # By default, track all concrete fields except auto fields and audit fields
        tracked_fields = []
        for field in self._meta.concrete_fields:
            # Skip auto fields, primary keys, and audit tracking fields
            if not field.auto_created and field.name not in [
                "id",
                "created_by",
                "modified_by",
                "created_at",
                "updated_at",
            ]:
                tracked_fields.append(field.name)
        return tracked_fields

    def _get_field_changes(self, original_values):
        """Compare current values with original to detect changes."""
        changes = {}
        tracked_fields = self._get_tracked_fields()

        for field_name in tracked_fields:
            old_value = original_values.get(field_name)
            new_value = getattr(self, field_name, None)

            # Handle ForeignKey fields by comparing IDs
            try:
                field = self._meta.get_field(field_name)
                if hasattr(field, "related_model"):
                    if hasattr(new_value, "pk"):
                        new_value = new_value.pk
                    if hasattr(old_value, "pk"):
                        old_value = old_value.pk
            except (AttributeError, ValueError):
                pass

            if old_value != new_value:
                changes[field_name] = {"old": old_value, "new": new_value}

        return changes

    def get_field_changes(self, original_values):
        """Public method to get field changes for external usage."""
        return self._get_field_changes(original_values)

    def _create_audit_entry(self, user, action, field_changes=None):
        """Create an audit entry for this model instance."""
        if not self._should_create_audit_entry():
            return

        audit_model = self._get_audit_log_model()
        if audit_model is None:
            return

        field_changes = field_changes or {}

        audit_entry = audit_model(
            **self._get_audit_entry_fields(user, action, field_changes)
        )
        audit_entry.save()
        return audit_entry

    def _get_audit_log_model(self):
        """Get the audit log model class for this model."""
        # Override this method in subclasses to return the appropriate audit model
        # Return None to disable audit logging
        return None

    def _get_audit_entry_fields(self, user, action, field_changes):
        """Get the fields for creating an audit entry."""
        # Override this method in subclasses to customize audit entry fields
        # This is a base implementation that subclasses should override
        return {
            "changed_by": user,
            "action": action,
            "field_changes": field_changes,
        }

    def save(self, *args, **kwargs):
        """Enhanced save method with detailed audit trail creation."""
        # Check if this is a new object
        is_new = self.pk is None

        # Store original values before save for change tracking
        original_values = getattr(self, "_original_values", {})

        # Get audit user from kwargs
        audit_user = kwargs.pop("audit_user", None) or kwargs.pop("user", None)

        # Call parent save method (which includes AuditableMixin logic)
        super().save(*args, **kwargs)

        # Create detailed audit entry if user is provided
        if audit_user and self._should_create_audit_entry():
            if is_new:
                # For new objects, track initial field values
                initial_changes = {}
                for field_name in self._get_tracked_fields():
                    value = getattr(self, field_name, None)
                    try:
                        field = self._meta.get_field(field_name)
                        if hasattr(field, "related_model"):
                            if hasattr(value, "pk"):
                                value = value.pk
                    except (AttributeError, ValueError):
                        pass
                    initial_changes[field_name] = {"old": None, "new": value}

                self._create_audit_entry(audit_user, "CREATE", initial_changes)
            else:
                # For updates, track what changed
                changes = self._get_field_changes(original_values)
                if changes:
                    self._create_audit_entry(audit_user, "UPDATE", changes)

        # Update stored values after save for future change tracking
        self._store_original_values()

    def refresh_from_db(self, using=None, fields=None):
        """Refresh the instance from the database and reset change tracking."""
        super().refresh_from_db(using=using, fields=fields)
        self._store_original_values()

    class Meta:
        abstract = True
