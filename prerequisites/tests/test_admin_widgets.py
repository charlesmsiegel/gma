"""
Tests for Django admin widgets for prerequisite visual builder (Issue #190).

This module tests the admin interface integration and custom widgets
for the prerequisite visual builder system.
"""

import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from prerequisites.helpers import all_of, trait_req
from prerequisites.models import Prerequisite

User = get_user_model()


class PrerequisiteBuilderWidgetTests(TestCase):
    """Test the custom admin widget for prerequisite building."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="admin", email="admin@example.com", password="adminpass123"
        )
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()

    def test_widget_initialization(self):
        """Test that the widget initializes correctly."""
        from prerequisites.widgets import PrerequisiteBuilderWidget

        widget = PrerequisiteBuilderWidget()
        self.assertIsNotNone(widget)
        self.assertEqual(
            widget.template_name, "admin/widgets/prerequisite_builder.html"
        )

    def test_widget_render_empty(self):
        """Test widget rendering with no initial value."""
        from prerequisites.widgets import PrerequisiteBuilderWidget

        widget = PrerequisiteBuilderWidget()
        html = widget.render("requirements", None, attrs={"id": "id_requirements"})

        # Should contain the widget container
        self.assertIn('class="prerequisite-builder-widget"', html)
        self.assertIn('id="id_requirements"', html)
        self.assertIn('data-widget-type="prerequisite-builder"', html)

    def test_widget_render_with_value(self):
        """Test widget rendering with initial requirement value."""
        from prerequisites.widgets import PrerequisiteBuilderWidget

        widget = PrerequisiteBuilderWidget()
        requirement = trait_req("strength", minimum=3)
        html = widget.render(
            "requirements", json.dumps(requirement), attrs={"id": "id_requirements"}
        )

        # Should contain the requirement data
        self.assertIn("data-initial-requirements", html)
        self.assertIn("&quot;trait&quot;:", html)
        self.assertIn("&quot;name&quot;: &quot;strength&quot;", html)

    def test_widget_media(self):
        """Test that widget includes required CSS and JS files."""
        from prerequisites.widgets import PrerequisiteBuilderWidget

        widget = PrerequisiteBuilderWidget()
        media = widget.media

        # Should include JavaScript files
        self.assertIn("admin/js/prerequisite-builder.js", media._js)
        # Should include CSS files
        self.assertIn("admin/css/prerequisite-builder.css", media._css["all"])

    def test_widget_value_from_datadict(self):
        """Test extracting value from form data."""
        from prerequisites.widgets import PrerequisiteBuilderWidget

        widget = PrerequisiteBuilderWidget()
        data = {"requirements": json.dumps(trait_req("arete", minimum=2))}
        files = {}

        value = widget.value_from_datadict(data, files, "requirements")
        requirement = json.loads(value)

        self.assertIn("trait", requirement)
        self.assertEqual(requirement["trait"]["name"], "arete")
        self.assertEqual(requirement["trait"]["min"], 2)


class AdminInterfaceTests(TestCase):
    """Test admin interface integration for prerequisites."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="admin", email="admin@example.com", password="adminpass123"
        )
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()

        self.client = Client()
        self.client.login(username="admin", password="adminpass123")

    def test_prerequisite_admin_add_page(self):
        """Test that the prerequisite admin add page renders correctly."""
        url = reverse("admin:prerequisites_prerequisite_add")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        # Should contain visual builder widget
        content = response.content.decode()
        self.assertIn("prerequisite-builder-widget", content)
        self.assertIn('data-widget-type="prerequisite-builder"', content)

    def test_prerequisite_admin_change_page(self):
        """Test that the prerequisite admin change page renders correctly."""
        # Create a prerequisite first
        prerequisite = Prerequisite.objects.create(
            description="Test Prerequisite",
            requirements=trait_req("strength", minimum=4),
        )

        url = reverse("admin:prerequisites_prerequisite_change", args=[prerequisite.pk])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        # Should contain visual builder with existing data
        content = response.content.decode()
        self.assertIn("prerequisite-builder-widget", content)
        self.assertIn("&quot;name&quot;: &quot;strength&quot;", content)

    def test_prerequisite_admin_save(self):
        """Test saving a prerequisite through admin with visual builder data."""
        url = reverse("admin:prerequisites_prerequisite_add")

        requirement_data = json.dumps(
            all_of(trait_req("arete", minimum=3), trait_req("willpower", minimum=5))
        )

        form_data = {
            "description": "Complex Magic Requirement",
            "requirements": requirement_data,
            "_save": "Save",
        }

        response = self.client.post(url, form_data)

        # Should redirect after successful save
        self.assertEqual(response.status_code, 302)

        # Verify prerequisite was created
        prerequisite = Prerequisite.objects.get(description="Complex Magic Requirement")
        self.assertIn("all", prerequisite.requirements)
        self.assertEqual(len(prerequisite.requirements["all"]), 2)

    def test_admin_widget_javascript_included(self):
        """Test that admin pages include required JavaScript."""
        url = reverse("admin:prerequisites_prerequisite_add")
        response = self.client.get(url)

        content = response.content.decode()
        # Should include admin JavaScript for prerequisite builder
        self.assertIn("prerequisite-builder.js", content)


class AdminFormTests(TestCase):
    """Test custom admin forms for prerequisites."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="admin", email="admin@example.com", password="adminpass123"
        )

    def test_prerequisite_admin_form(self):
        """Test that admin form uses visual builder widget."""
        from django.contrib.admin.sites import AdminSite

        from prerequisites.admin import PrerequisiteAdmin

        admin_site = AdminSite()
        admin_instance = PrerequisiteAdmin(Prerequisite, admin_site)
        form_class = admin_instance.get_form(None)

        form = form_class()

        # Check that requirements field uses visual builder widget
        requirements_widget = form.fields["requirements"].widget
        self.assertEqual(
            requirements_widget.__class__.__name__, "PrerequisiteBuilderWidget"
        )

    def test_admin_form_validation(self):
        """Test admin form validation with visual builder data."""
        from django.contrib.admin.sites import AdminSite

        from prerequisites.admin import PrerequisiteAdmin

        admin_site = AdminSite()
        admin_instance = PrerequisiteAdmin(Prerequisite, admin_site)
        form_class = admin_instance.get_form(None)

        # Valid form data
        form_data = {
            "description": "Admin Test Requirement",
            "requirements": json.dumps(trait_req("dexterity", minimum=3)),
        }

        form = form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_admin_form_invalid_json(self):
        """Test admin form validation with invalid JSON."""
        from django.contrib.admin.sites import AdminSite

        from prerequisites.admin import PrerequisiteAdmin

        admin_site = AdminSite()
        admin_instance = PrerequisiteAdmin(Prerequisite, admin_site)
        form_class = admin_instance.get_form(None)

        # Invalid JSON data
        form_data = {
            "description": "Invalid JSON Test",
            "requirements": '{"invalid": json}',
        }

        form = form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("requirements", form.errors)


class VisualBuilderAPIViewTests(TestCase):
    """Test API views supporting the visual builder."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.client = Client()
        self.client.login(username="testuser", password="testpass123")

    def test_validate_requirement_api(self):
        """Test the requirement validation API endpoint."""
        url = reverse("prerequisites:validate_requirement")

        # Test valid requirement
        valid_req = {"trait": {"name": "strength", "min": 3}}

        response = self.client.post(
            url, data=json.dumps(valid_req), content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["valid"])

    def test_requirement_suggestions_api(self):
        """Test the requirement suggestions API endpoint."""
        url = reverse("prerequisites:requirement_suggestions")

        # Test trait suggestions
        response = self.client.get(url, {"type": "trait"})
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("suggestions", data)
        # Should have common trait suggestions
        trait_names = [s["name"] for s in data["suggestions"]]
        self.assertIn("strength", trait_names)
        self.assertIn("arete", trait_names)

    def test_requirement_templates_api(self):
        """Test the requirement templates API endpoint."""
        url = reverse("prerequisites:requirement_templates")

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("templates", data)
        # Should have predefined template examples
        self.assertTrue(len(data["templates"]) > 0)
