"""
Tests for core model mixins.

These tests focus on simple, pragmatic functionality that's actually needed
rather than comprehensive theoretical coverage.
"""

import time

from django.db import models
from django.test import TestCase
from django.utils import timezone as django_timezone

from core.models.mixins import TimestampedMixin


class TimestampedTestModel(TimestampedMixin):
    """Test model using TimestampedMixin."""

    title = models.CharField(max_length=100)

    class Meta:
        app_label = "core"


class TimestampedMixinTest(TestCase):
    """Test TimestampedMixin functionality."""

    def test_has_timestamp_fields(self):
        """Test that TimestampedMixin provides created_at and updated_at fields."""
        fields = {f.name: f for f in TimestampedTestModel._meta.get_fields()}

        self.assertIn("created_at", fields)
        self.assertIn("updated_at", fields)
        self.assertIsInstance(fields["created_at"], models.DateTimeField)
        self.assertIsInstance(fields["updated_at"], models.DateTimeField)

    def test_timestamps_set_on_create(self):
        """Test that timestamps are automatically set when creating an object."""
        before_create = django_timezone.now()
        obj = TimestampedTestModel.objects.create(title="Test Object")
        after_create = django_timezone.now()

        self.assertIsNotNone(obj.created_at)
        self.assertIsNotNone(obj.updated_at)
        self.assertGreaterEqual(obj.created_at, before_create)
        self.assertLessEqual(obj.created_at, after_create)

    def test_updated_at_changes_on_save(self):
        """Test that updated_at changes when object is saved."""
        obj = TimestampedTestModel.objects.create(title="Test Object")
        original_created_at = obj.created_at
        original_updated_at = obj.updated_at

        time.sleep(0.1)
        obj.title = "Updated Title"
        obj.save()
        obj.refresh_from_db()

        self.assertEqual(obj.created_at, original_created_at)
        self.assertGreater(obj.updated_at, original_updated_at)

    def test_abstract_base_class(self):
        """Test that TimestampedMixin is an abstract base class."""
        self.assertTrue(TimestampedMixin._meta.abstract)
