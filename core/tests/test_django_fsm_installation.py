"""
Tests for django-fsm-2 installation and basic functionality.

This module provides minimal validation that django-fsm-2 is properly
installed and working with Django for the GM Application project.
"""

from django.db import models
from django.test import TestCase


class DjangoFsm2InstallationTest(TestCase):
    """Test django-fsm-2 package installation and basic functionality."""

    def test_package_import(self):
        """Test that django-fsm-2 can be imported without errors."""
        from django_fsm import FSMField, TransitionNotAllowed, transition

        # Verify core components are available
        self.assertTrue(callable(transition))
        self.assertTrue(issubclass(FSMField, models.Field))
        self.assertTrue(issubclass(TransitionNotAllowed, Exception))

    def test_basic_fsm_functionality(self):
        """Test that basic FSM functionality works correctly."""
        from django_fsm import FSMField, transition

        class BasicTestFSMModel(models.Model):
            state = FSMField(default="draft", max_length=50)
            name = models.CharField(max_length=100, default="test")

            @transition(field=state, source="draft", target="published")
            def publish(self):
                pass

            @transition(field=state, source="published", target="archived")
            def archive(self):
                pass

            class Meta:
                app_label = "core"

        # Test model creation and initial state
        obj = BasicTestFSMModel(name="Test Object")
        self.assertEqual(obj.state, "draft")
        self.assertEqual(obj.name, "Test Object")

        # Test state transition
        obj.publish()
        self.assertEqual(obj.state, "published")

        # Test chained transitions
        obj.archive()
        self.assertEqual(obj.state, "archived")

    def test_django_integration(self):
        """Test that django-fsm-2 integrates properly with Django."""
        from django_fsm import FSMField, transition

        class IntegrationTestFSMModel(models.Model):
            state = FSMField(default="active", max_length=50)

            @transition(field=state, source="active", target="inactive")
            def deactivate(self):
                pass

            class Meta:
                app_label = "core"

        # Test that the field has Django field properties
        field = IntegrationTestFSMModel._meta.get_field("state")
        self.assertIsInstance(field, FSMField)
        self.assertEqual(field.default, "active")
        self.assertEqual(field.max_length, 50)

        # Test that Django can create the model
        obj = IntegrationTestFSMModel()
        self.assertEqual(obj.state, "active")

        # Test transition method exists and works
        self.assertTrue(hasattr(obj, "deactivate"))
        obj.deactivate()
        self.assertEqual(obj.state, "inactive")
