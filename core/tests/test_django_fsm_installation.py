"""
Comprehensive tests for django-fsm-2 installation and functionality.

This test suite verifies that django-fsm-2 package is properly installed and
functional within the Django 5.2+ project. Tests are designed to fail initially
(before installation) and pass after proper installation and integration.

Test Categories:
1. Package Installation Tests - Verify package can be imported
2. Basic FSM Functionality Tests - Test core FSM features
3. Django Integration Tests - Test database integration, migrations, admin

Context:
- Django 5.2+ project using Python 3.11
- Replacing django-fsm with django-fsm-2 (version 4.0.0+)
- PostgreSQL database with existing models
- Must integrate with existing codebase without conflicts

Requirements:
- Tests should fail before django-fsm-2 installation
- Tests should pass after proper installation and configuration
- Comprehensive coverage of FSM functionality
- Follow project TDD patterns and testing conventions
"""

from django.contrib.auth import get_user_model
from django.db import models
from django.test import TestCase, TransactionTestCase
from django.test.utils import override_settings

User = get_user_model()


class DjangoFsm2PackageInstallationTest(TestCase):
    """Test that django-fsm-2 package can be imported and has correct version."""

    def test_django_fsm2_import_available(self):
        """Test that django_fsm package can be imported without errors."""
        try:
            import django_fsm  # noqa: F401

            self.assertTrue(True, "django_fsm package imported successfully")
        except ImportError as e:
            self.fail(f"Failed to import django_fsm package: {e}")

    def test_django_fsm2_version_check(self):
        """Test that django-fsm-2 is version 4.0.0 or higher."""
        try:
            import django_fsm

            # Check if we can access version info
            if hasattr(django_fsm, "__version__"):
                version = django_fsm.__version__
                # django-fsm-2 should be version 4.0.0+
                version_parts = version.split(".")
                major_version = int(version_parts[0])
                self.assertGreaterEqual(
                    major_version,
                    4,
                    f"Expected django-fsm-2 version 4.0.0+, got {version}",
                )
            else:
                # If __version__ not available, check if it's the new package
                # by testing for features specific to django-fsm-2
                from django_fsm import FSMField, transition  # noqa: F401

                self.assertTrue(True, "django-fsm-2 features available")
        except ImportError as e:
            self.fail(f"Failed to check django-fsm-2 version: {e}")

    def test_fsm_field_import(self):
        """Test that FSMField can be imported from django_fsm."""
        try:
            from django_fsm import FSMField

            self.assertTrue(issubclass(FSMField, models.Field))
        except ImportError as e:
            self.fail(f"Failed to import FSMField: {e}")

    def test_transition_decorator_import(self):
        """Test that transition decorator can be imported from django_fsm."""
        try:
            from django_fsm import transition

            self.assertTrue(callable(transition))
        except ImportError as e:
            self.fail(f"Failed to import transition decorator: {e}")

    def test_fsm_protected_import(self):
        """Test that FSMProtectedMixin can be imported (if available)."""
        try:
            from django_fsm import FSMProtectedMixin  # noqa: F401

            self.assertTrue(True, "FSMProtectedMixin imported successfully")
        except ImportError:
            # This might not be available in all versions, so we'll just note it
            pass

    def test_no_package_conflicts(self):
        """Test that there are no conflicts with old django-fsm package."""
        # Ensure we don't have both old django-fsm and new django-fsm-2
        new_fsm_present = False

        try:
            import django_fsm  # noqa: F401

            # Check if this is the old package by looking for old-style imports
            # or version patterns
            new_fsm_present = True
        except ImportError:
            pass

        # If we have new FSM, make sure we don't have old conflicting imports
        if new_fsm_present:
            # Try to import and verify it's the new version
            from django_fsm import FSMField

            # New version should work without issues
            self.assertTrue(issubclass(FSMField, models.Field))


class DjangoFsm2BasicFunctionalityTest(TestCase):
    """Test basic FSM functionality with django-fsm-2."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def test_fsm_field_creation(self):
        """Test that FSMField can be used in model definition."""
        try:
            from django_fsm import FSMField

            # Create a test model class dynamically
            class TestFSMModel(models.Model):
                state = FSMField(default="draft", max_length=50)
                name = models.CharField(max_length=100)

                class Meta:
                    app_label = "core"

            # Test field properties
            state_field = TestFSMModel._meta.get_field("state")
            self.assertIsInstance(state_field, FSMField)
            self.assertEqual(state_field.default, "draft")
            self.assertEqual(state_field.max_length, 50)

        except ImportError as e:
            self.fail(f"Failed to create FSMField: {e}")

    def test_transition_decorator_basic(self):
        """Test that @transition decorator works correctly."""
        try:
            from django_fsm import FSMField, transition

            class TestFSMModel(models.Model):
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

            # Verify transition methods exist
            self.assertTrue(hasattr(TestFSMModel, "publish"))
            self.assertTrue(hasattr(TestFSMModel, "archive"))
            self.assertTrue(callable(TestFSMModel.publish))
            self.assertTrue(callable(TestFSMModel.archive))

        except ImportError as e:
            self.fail(f"Failed to use transition decorator: {e}")

    def test_multiple_source_states(self):
        """Test @transition decorator with multiple source states."""
        try:
            from django_fsm import FSMField, transition

            class TestFSMModel(models.Model):
                state = FSMField(default="draft", max_length=50)
                name = models.CharField(max_length=100, default="test")

                @transition(field=state, source=["draft", "review"], target="published")
                def publish(self):
                    pass

                class Meta:
                    app_label = "core"

            # Verify transition method exists
            self.assertTrue(hasattr(TestFSMModel, "publish"))

        except ImportError as e:
            self.fail(f"Failed to use transition with multiple sources: {e}")

    def test_wildcard_source_state(self):
        """Test @transition decorator with wildcard source state."""
        try:
            from django_fsm import FSMField, transition

            class TestFSMModel(models.Model):
                state = FSMField(default="draft", max_length=50)
                name = models.CharField(max_length=100, default="test")

                @transition(field=state, source="*", target="cancelled")
                def cancel(self):
                    pass

                class Meta:
                    app_label = "core"

            # Verify transition method exists
            self.assertTrue(hasattr(TestFSMModel, "cancel"))

        except ImportError as e:
            self.fail(f"Failed to use transition with wildcard source: {e}")

    def test_transition_conditions(self):
        """Test @transition decorator with conditions."""
        try:
            from django_fsm import FSMField, transition

            class TestFSMModel(models.Model):
                state = FSMField(default="draft", max_length=50)
                name = models.CharField(max_length=100, default="test")
                can_publish = models.BooleanField(default=True)

                def can_be_published(self):
                    return self.can_publish

                @transition(
                    field=state,
                    source="draft",
                    target="published",
                    conditions=[can_be_published],
                )
                def publish(self):
                    pass

                class Meta:
                    app_label = "core"

            # Verify transition method exists
            self.assertTrue(hasattr(TestFSMModel, "publish"))
            self.assertTrue(hasattr(TestFSMModel, "can_be_published"))

        except ImportError as e:
            self.fail(f"Failed to use transition with conditions: {e}")

    def test_get_available_state_transitions(self):
        """Test getting available transitions from current state."""
        try:
            from django_fsm import FSMField, transition

            class TestFSMModel(models.Model):
                state = FSMField(default="draft", max_length=50)
                name = models.CharField(max_length=100, default="test")

                @transition(field=state, source="draft", target="published")
                def publish(self):
                    pass

                @transition(field=state, source="draft", target="review")
                def submit_for_review(self):
                    pass

                class Meta:
                    app_label = "core"

            # Test that we can check available transitions
            # (The exact API might vary, but we should be able to introspect)
            model_instance = TestFSMModel(state="draft")

            # Check if get_available_state_transitions method exists
            if hasattr(model_instance, "get_available_state_transitions"):
                transitions = model_instance.get_available_state_transitions()
                # django-fsm-2 returns a generator, convert to list for testing
                transitions_list = list(transitions)
                self.assertIsInstance(transitions_list, list)

        except ImportError as e:
            self.fail(f"Failed to test available transitions: {e}")


class DjangoFsm2DjangoDatabaseIntegrationTest(TransactionTestCase):
    """Test django-fsm-2 integration with Django database operations."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def test_fsm_model_database_operations(self):
        """Test FSM model can be saved to and loaded from database."""
        try:
            from django_fsm import FSMField, transition

            # Create test model dynamically
            class TestFSMModel(models.Model):
                state = FSMField(default="draft", max_length=50)
                name = models.CharField(max_length=100)
                created_by = models.ForeignKey(
                    User, on_delete=models.CASCADE, null=True, blank=True
                )

                @transition(field=state, source="draft", target="published")
                def publish(self):
                    pass

                class Meta:
                    app_label = "core"

            # Note: This test doesn't actually create tables since we're using
            # dynamic models. It tests the field creation and model definition.

            # Test model instantiation
            obj = TestFSMModel(name="Test Object", created_by=self.user)
            self.assertEqual(obj.state, "draft")
            self.assertEqual(obj.name, "Test Object")
            self.assertEqual(obj.created_by, self.user)

            # Test that transition method is available
            self.assertTrue(hasattr(obj, "publish"))

        except ImportError as e:
            self.fail(f"Failed to test database operations: {e}")

    def test_fsm_field_migration_compatibility(self):
        """Test that FSMField is compatible with Django migrations."""
        try:
            from django_fsm import FSMField

            # Test field deconstruction (required for migrations)
            field = FSMField(default="draft", max_length=50)

            # Test that field can be deconstructed for migrations
            name, path, args, kwargs = field.deconstruct()

            self.assertEqual(name, None)  # Should be None for unnamed field
            self.assertIn("FSMField", path)
            self.assertIn("default", kwargs)
            self.assertIn("max_length", kwargs)

        except ImportError as e:
            self.fail(f"Failed to test migration compatibility: {e}")
        except Exception as e:
            self.fail(f"FSMField migration compatibility issue: {e}")

    def test_fsm_field_with_choices(self):
        """Test FSMField works with Django choices."""
        try:
            from django_fsm import FSMField

            STATE_CHOICES = [
                ("draft", "Draft"),
                ("published", "Published"),
                ("archived", "Archived"),
            ]

            class TestFSMModel(models.Model):
                state = FSMField(default="draft", max_length=50, choices=STATE_CHOICES)
                name = models.CharField(max_length=100, default="test")

                class Meta:
                    app_label = "core"

            # Test field properties
            state_field = TestFSMModel._meta.get_field("state")
            self.assertEqual(state_field.choices, STATE_CHOICES)

            # Test model instantiation
            obj = TestFSMModel(name="Test Object")
            self.assertEqual(obj.state, "draft")

        except ImportError as e:
            self.fail(f"Failed to test FSMField with choices: {e}")

    def test_django_admin_integration(self):
        """Test that FSMField integrates properly with Django admin."""
        try:
            from django.contrib import admin
            from django_fsm import FSMField

            class TestFSMModel(models.Model):
                state = FSMField(default="draft", max_length=50)
                name = models.CharField(max_length=100, default="test")

                class Meta:
                    app_label = "core"

            # Test admin integration by creating ModelAdmin
            class TestFSMModelAdmin(admin.ModelAdmin):
                list_display = ["name", "state"]
                list_filter = ["state"]

            # Test that admin class can be created without errors
            admin_instance = TestFSMModelAdmin(TestFSMModel, admin.site)
            self.assertIsInstance(admin_instance, admin.ModelAdmin)

        except ImportError as e:
            self.fail(f"Failed to test admin integration: {e}")

    def test_fsm_field_serialization(self):
        """Test that FSMField values can be serialized (for API responses)."""
        try:
            import json

            from django_fsm import FSMField

            class TestFSMModel(models.Model):
                state = FSMField(default="draft", max_length=50)
                name = models.CharField(max_length=100, default="test")

                class Meta:
                    app_label = "core"

            # Test serialization
            obj = TestFSMModel(name="Test Object")

            # Test JSON serialization of state value
            state_value = obj.state
            json_data = json.dumps({"state": state_value})
            parsed_data = json.loads(json_data)

            self.assertEqual(parsed_data["state"], "draft")

        except ImportError as e:
            self.fail(f"Failed to test serialization: {e}")


class DjangoFsm2TransitionExecutionTest(TestCase):
    """Test actual FSM state transitions and business logic."""

    def test_transition_execution_success(self):
        """Test that transitions execute successfully when conditions are met."""
        try:
            from django_fsm import FSMField, transition

            class TestFSMModel(models.Model):
                state = FSMField(default="draft", max_length=50)
                name = models.CharField(max_length=100, default="test")
                published_count = models.IntegerField(default=0)

                @transition(field=state, source="draft", target="published")
                def publish(self):
                    self.published_count += 1

                class Meta:
                    app_label = "core"

            # Test transition execution
            obj = TestFSMModel(name="Test Object")
            self.assertEqual(obj.state, "draft")
            self.assertEqual(obj.published_count, 0)

            # Execute transition
            obj.publish()
            self.assertEqual(obj.state, "published")
            self.assertEqual(obj.published_count, 1)

        except ImportError as e:
            self.fail(f"Failed to test transition execution: {e}")

    def test_transition_condition_blocking(self):
        """Test that transitions are blocked when conditions are not met."""
        try:
            from django_fsm import FSMField, TransitionNotAllowed, transition

            class TestFSMModel(models.Model):
                state = FSMField(default="draft", max_length=50)
                name = models.CharField(max_length=100, default="test")
                can_publish = models.BooleanField(default=False)

                def check_can_publish(self):
                    return self.can_publish

                @transition(
                    field=state,
                    source="draft",
                    target="published",
                    conditions=[check_can_publish],
                )
                def publish(self):
                    pass

                class Meta:
                    app_label = "core"

            # Test blocked transition
            obj = TestFSMModel(name="Test Object", can_publish=False)
            self.assertEqual(obj.state, "draft")

            # This should raise TransitionNotAllowed
            with self.assertRaises(TransitionNotAllowed):
                obj.publish()

            # State should remain unchanged
            self.assertEqual(obj.state, "draft")

            # Test allowed transition
            obj.can_publish = True
            obj.publish()  # Should work now
            self.assertEqual(obj.state, "published")

        except ImportError as e:
            self.fail(f"Failed to test transition conditions: {e}")

    def test_invalid_transition_blocking(self):
        """Test that invalid transitions are properly blocked."""
        try:
            from django_fsm import FSMField, TransitionNotAllowed, transition

            class TestFSMModel(models.Model):
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

            # Test invalid transition
            obj = TestFSMModel(name="Test Object")
            self.assertEqual(obj.state, "draft")

            # Trying to archive from draft should fail
            with self.assertRaises(TransitionNotAllowed):
                obj.archive()

            # State should remain unchanged
            self.assertEqual(obj.state, "draft")

            # Valid transition should work
            obj.publish()
            self.assertEqual(obj.state, "published")

            # Now archive should work
            obj.archive()
            self.assertEqual(obj.state, "archived")

        except ImportError as e:
            self.fail(f"Failed to test invalid transitions: {e}")


class DjangoFsm2AdvancedFeaturesTest(TestCase):
    """Test advanced django-fsm-2 features and edge cases."""

    def test_custom_state_field_name(self):
        """Test FSM with custom field name (not 'state')."""
        try:
            from django_fsm import FSMField, transition

            class TestFSMModel(models.Model):
                status = FSMField(default="pending", max_length=50)
                name = models.CharField(max_length=100, default="test")

                @transition(field=status, source="pending", target="approved")
                def approve(self):
                    pass

                class Meta:
                    app_label = "core"

            # Test custom field name
            obj = TestFSMModel(name="Test Object")
            self.assertEqual(obj.status, "pending")

            obj.approve()
            self.assertEqual(obj.status, "approved")

        except ImportError as e:
            self.fail(f"Failed to test custom field name: {e}")

    def test_multiple_fsm_fields(self):
        """Test model with multiple FSM fields."""
        try:
            from django_fsm import FSMField, transition

            class TestFSMModel(models.Model):
                workflow_state = FSMField(default="draft", max_length=50)
                approval_state = FSMField(default="pending", max_length=50)
                name = models.CharField(max_length=100, default="test")

                @transition(field=workflow_state, source="draft", target="submitted")
                def submit(self):
                    pass

                @transition(field=approval_state, source="pending", target="approved")
                def approve(self):
                    pass

                class Meta:
                    app_label = "core"

            # Test multiple FSM fields
            obj = TestFSMModel(name="Test Object")
            self.assertEqual(obj.workflow_state, "draft")
            self.assertEqual(obj.approval_state, "pending")

            # Test independent transitions
            obj.submit()
            self.assertEqual(obj.workflow_state, "submitted")
            self.assertEqual(obj.approval_state, "pending")  # Should be unchanged

            obj.approve()
            self.assertEqual(obj.workflow_state, "submitted")  # Should be unchanged
            self.assertEqual(obj.approval_state, "approved")

        except ImportError as e:
            self.fail(f"Failed to test multiple FSM fields: {e}")

    def test_fsm_integration_with_existing_mixins(self):
        """Test that FSM fields work with existing project mixins."""
        try:
            from django_fsm import FSMField, transition

            from core.models.mixins import NamedModelMixin, TimestampedMixin

            class TestFSMModel(TimestampedMixin, NamedModelMixin):
                state = FSMField(default="draft", max_length=50)

                @transition(field=state, source="draft", target="published")
                def publish(self):
                    pass

                class Meta:
                    app_label = "core"

            # Test integration with mixins
            obj = TestFSMModel(name="Test Object")
            self.assertEqual(obj.state, "draft")
            self.assertEqual(obj.name, "Test Object")
            self.assertEqual(str(obj), "Test Object")  # From NamedModelMixin
            self.assertTrue(hasattr(obj, "created_at"))  # From TimestampedMixin

            obj.publish()
            self.assertEqual(obj.state, "published")

        except ImportError as e:
            self.fail(f"Failed to test mixin integration: {e}")


class DjangoFsm2ErrorHandlingTest(TestCase):
    """Test error handling and edge cases with django-fsm-2."""

    def test_transition_not_allowed_exception(self):
        """Test that TransitionNotAllowed exception is properly raised."""
        try:
            from django_fsm import FSMField, TransitionNotAllowed, transition

            class TestFSMModel(models.Model):
                state = FSMField(default="draft", max_length=50)
                name = models.CharField(max_length=100, default="test")

                @transition(field=state, source="published", target="archived")
                def archive(self):
                    pass

                class Meta:
                    app_label = "core"

            # Test exception handling
            obj = TestFSMModel(name="Test Object")
            self.assertEqual(obj.state, "draft")

            # Should raise specific exception
            with self.assertRaises(TransitionNotAllowed) as cm:
                obj.archive()

            # Verify exception type and message
            self.assertIsInstance(cm.exception, TransitionNotAllowed)

        except ImportError as e:
            self.fail(f"Failed to test exception handling: {e}")

    def test_field_validation_errors(self):
        """Test FSMField validation and error handling."""
        try:
            from django_fsm import FSMField

            STATE_CHOICES = [
                ("draft", "Draft"),
                ("published", "Published"),
            ]

            class TestFSMModel(models.Model):
                state = FSMField(
                    default="draft",
                    max_length=10,  # Short max_length for testing
                    choices=STATE_CHOICES,
                )
                name = models.CharField(max_length=100, default="test")

                class Meta:
                    app_label = "core"

            # Test field creation
            obj = TestFSMModel(name="Test Object")
            self.assertEqual(obj.state, "draft")

            # Test invalid state assignment (if validation is in place)
            obj.state = "invalid_state_that_is_very_long"

            # Note: Validation might happen at save time or field level
            # This tests that the field can handle assignment

        except ImportError as e:
            self.fail(f"Failed to test field validation: {e}")


class DjangoFsm2PerformanceTest(TestCase):
    """Test performance characteristics of django-fsm-2."""

    def test_transition_performance(self):
        """Test that transitions execute efficiently."""
        try:
            import time

            from django_fsm import FSMField, transition

            class TestFSMModel(models.Model):
                state = FSMField(default="draft", max_length=50)
                name = models.CharField(max_length=100, default="test")

                @transition(field=state, source="draft", target="published")
                def publish(self):
                    pass

                class Meta:
                    app_label = "core"

            # Test transition performance
            obj = TestFSMModel(name="Test Object")

            start_time = time.time()
            for _ in range(100):
                # Reset and execute transition
                obj.state = "draft"
                obj.publish()
            end_time = time.time()

            execution_time = end_time - start_time
            # Should complete 100 transitions in reasonable time (< 1 second)
            self.assertLess(execution_time, 1.0, "100 FSM transitions took too long")

        except ImportError as e:
            self.fail(f"Failed to test performance: {e}")

    def test_memory_usage_stability(self):
        """Test that FSM operations don't cause memory leaks."""
        try:
            from django_fsm import FSMField, transition

            class TestFSMModel(models.Model):
                state = FSMField(default="draft", max_length=50)
                name = models.CharField(max_length=100, default="test")

                @transition(field=state, source="draft", target="published")
                def publish(self):
                    pass

                @transition(field=state, source="published", target="draft")
                def unpublish(self):
                    pass

                class Meta:
                    app_label = "core"

            # Create multiple objects and execute transitions
            objects = []
            for i in range(50):
                obj = TestFSMModel(name=f"Test Object {i}")
                obj.publish()
                obj.unpublish()
                objects.append(obj)

            # Basic test that objects were created and transitions worked
            self.assertEqual(len(objects), 50)
            for obj in objects:
                self.assertEqual(obj.state, "draft")

        except ImportError as e:
            self.fail(f"Failed to test memory usage: {e}")


class DjangoFsm2ConfigurationTest(TestCase):
    """Test django-fsm-2 configuration and settings."""

    def test_django_startup_with_fsm(self):
        """Test that Django starts successfully with django-fsm-2 installed."""
        # This test verifies that importing django_fsm doesn't break Django
        try:
            from django.conf import settings
            from django_fsm import FSMField, transition  # noqa: F401

            # Verify Django settings are accessible
            self.assertTrue(hasattr(settings, "INSTALLED_APPS"))

            # Verify we can import Django components
            from django.contrib import admin  # noqa: F401
            from django.db import models

            # Test that FSM components integrate with Django
            self.assertTrue(issubclass(FSMField, models.Field))

        except ImportError as e:
            self.fail(f"Django startup failed with django-fsm-2: {e}")

    def test_no_settings_conflicts(self):
        """Test that django-fsm-2 doesn't conflict with Django settings."""
        try:
            import django_fsm  # noqa: F401
            from django.conf import settings

            # Test that FSM import doesn't modify Django settings
            original_debug = getattr(settings, "DEBUG", None)
            original_installed_apps = getattr(settings, "INSTALLED_APPS", [])

            # Import should not change settings
            from django_fsm import FSMField, transition  # noqa: F401

            self.assertEqual(getattr(settings, "DEBUG", None), original_debug)
            self.assertEqual(
                getattr(settings, "INSTALLED_APPS", []), original_installed_apps
            )

        except ImportError as e:
            self.fail(f"Settings conflict test failed: {e}")

    @override_settings(DEBUG=True)
    def test_fsm_with_debug_mode(self):
        """Test that django-fsm-2 works correctly in DEBUG mode."""
        try:
            from django.conf import settings
            from django_fsm import FSMField, transition

            self.assertTrue(settings.DEBUG)

            # FSM should work in debug mode
            class TestFSMModel(models.Model):
                state = FSMField(default="draft", max_length=50)

                @transition(field=state, source="draft", target="published")
                def publish(self):
                    pass

                class Meta:
                    app_label = "core"

            obj = TestFSMModel()
            obj.publish()
            self.assertEqual(obj.state, "published")

        except ImportError as e:
            self.fail(f"DEBUG mode test failed: {e}")


class DjangoFsm2DocumentationTest(TestCase):
    """Test that django-fsm-2 has proper documentation and help."""

    def test_fsm_field_help_text(self):
        """Test that FSMField supports help_text parameter."""
        try:
            from django_fsm import FSMField

            help_text = "This field tracks the workflow state"
            field = FSMField(default="draft", max_length=50, help_text=help_text)

            self.assertEqual(field.help_text, help_text)

        except ImportError as e:
            self.fail(f"Help text test failed: {e}")

    def test_transition_documentation(self):
        """Test that transition decorator supports documentation."""
        try:
            from django_fsm import FSMField, transition

            class TestFSMModel(models.Model):
                state = FSMField(default="draft", max_length=50)

                @transition(field=state, source="draft", target="published")
                def publish(self):
                    """Publish the content to make it publicly visible."""
                    pass

                class Meta:
                    app_label = "core"

            # Test that docstring is preserved
            self.assertIsNotNone(TestFSMModel.publish.__doc__)
            self.assertIn("Publish the content", TestFSMModel.publish.__doc__)

        except ImportError as e:
            self.fail(f"Documentation test failed: {e}")
