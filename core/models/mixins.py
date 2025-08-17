"""
Core model mixins for reusable model functionality.

These mixins provide common fields that are actually needed across multiple
models in the GMA application. They focus on real usage patterns rather than
theoretical completeness.

Available mixins:
- TimestampedMixin: Automatic created_at and updated_at fields (for future models)

Note: Most functionality like audit trails and game system fields are already
implemented in specific models where they're needed. These mixins are for
future models that need simple, common functionality.
"""

from django.db import models


class TimestampedMixin(models.Model):
    """
    Mixin to add automatic timestamp tracking to models.

    Use this for new models that need basic timestamp tracking.
    Note: Campaign and Character models already have these fields.

    Provides:
    - created_at: Automatically set when object is first created
    - updated_at: Automatically updated every time object is saved
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
