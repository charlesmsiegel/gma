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
    - created_at: Automatically set when object is first created
    - updated_at: Automatically updated every time object is saved
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class DisplayableMixin(models.Model):
    """
    Mixin to add display control and ordering to models.

    Provides:
    - is_displayed: Boolean flag to control visibility
    - display_order: Integer for custom ordering (0 = first)
    """

    is_displayed = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        abstract = True


class NamedModelMixin(models.Model):
    """
    Mixin to add a standardized name field with __str__ method.

    Provides:
    - name: Required CharField with 100 character limit
    - __str__: Returns the name of the object
    """

    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        abstract = True


class DescribedModelMixin(models.Model):
    """
    Mixin to add an optional description field to models.

    Provides:
    - description: Optional TextField for detailed information
    """

    description = models.TextField(blank=True, default="")

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
    """

    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="%(app_label)s_%(class)s_created",
        null=True,
        blank=True,
    )
    modified_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="%(app_label)s_%(class)s_modified",
        null=True,
        blank=True,
    )

    class Meta:
        abstract = True


class GameSystemMixin(models.Model):
    """
    Mixin to add game system selection to campaign-related models.

    Provides:
    - game_system: CharField with predefined choices for popular RPG systems
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
    )

    class Meta:
        abstract = True
