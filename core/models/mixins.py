"""
Django model mixins providing common functionality across the application.

These mixins provide reusable functionality that can be combined on any Django model:

1. TimestampedMixin - Automatic created_at and updated_at timestamps
2. DisplayableMixin - Display control with is_displayed flag and ordering
3. NamedModelMixin - Standardized name field with __str__ method
4. DescribedModelMixin - Optional description field for detailed information
5. AuditableMixin - User tracking with created_by and modified_by fields
6. GameSystemMixin - Game system selection for campaign-related models

All mixins are designed to be combined safely without field conflicts.
They follow Django best practices for abstract base classes and migrations.
"""

from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class TimestampedMixin(models.Model):
    """
    Mixin to add automatic timestamp tracking to models.

    Provides:
    - created_at: Automatically set when object is first created
    - updated_at: Automatically updated every time object is saved

    Usage:
        class MyModel(TimestampedMixin):
            name = models.CharField(max_length=100)

            class Meta:
                app_label = 'myapp'
    """

    created_at = models.DateTimeField(
        auto_now_add=True, help_text="Timestamp when the object was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True, help_text="Timestamp when the object was last modified"
    )

    class Meta:
        abstract = True


class DisplayableMixin(models.Model):
    """
    Mixin to add display control and ordering to models.

    Provides:
    - is_displayed: Boolean flag to control visibility
    - display_order: Integer for custom ordering (0 = first)

    Usage:
        class MyModel(DisplayableMixin):
            name = models.CharField(max_length=100)

            class Meta:
                app_label = 'myapp'
                ordering = ['display_order', 'id']
    """

    is_displayed = models.BooleanField(
        default=True,
        help_text="Whether this item should be displayed in lists and views",
    )
    display_order = models.PositiveIntegerField(
        default=0,
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

    Usage:
        class MyModel(NamedModelMixin):
            extra_field = models.CharField(max_length=50)

            class Meta:
                app_label = 'myapp'
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

    Usage:
        class MyModel(DescribedModelMixin):
            name = models.CharField(max_length=100)

            class Meta:
                app_label = 'myapp'
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

    Note: These fields must be set manually in your views/forms.
    They are not automatically populated like timestamps.

    Usage:
        class MyModel(AuditableMixin):
            name = models.CharField(max_length=100)

            class Meta:
                app_label = 'myapp'
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

    class Meta:
        abstract = True


class GameSystemMixin(models.Model):
    """
    Mixin to add game system selection to campaign-related models.

    Provides:
    - game_system: CharField with predefined choices for popular RPG systems

    Supports:
    - World of Darkness games (WoD, Mage, Vampire, etc.)
    - D&D 5th Edition
    - Pathfinder
    - Modern systems (Shadowrun, Call of Cthulhu)
    - Indie systems (Fate, PbtA, Savage Worlds)
    - Generic/Universal systems

    Usage:
        class MyModel(GameSystemMixin):
            name = models.CharField(max_length=100)

            class Meta:
                app_label = 'myapp'
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
