"""
Tests for visual prerequisite builder UI component (Issue #190).

This module tests the visual builder that allows users to create complex
prerequisite requirements through a user-friendly interface instead of
writing JSON manually.
"""

import json

from django.contrib.auth import get_user_model
from django.template import Context, Template
from django.test import Client, TestCase
from django.urls import reverse

from campaigns.models import Campaign
from characters.models import MageCharacter
from prerequisites.helpers import all_of, any_of, has_item, trait_req
from prerequisites.models import Prerequisite

User = get_user_model()


class VisualBuilderTemplateTests(TestCase):
    """Test template rendering and integration."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.user,
            game_system="Mage: The Ascension",
            max_characters_per_player=0,
        )

    def test_visual_builder_widget_renders(self):
        """Test that the visual builder widget renders correctly."""
        template = Template(
            """
            {% load prerequisite_tags %}
            <form>
                {% prerequisite_builder field_name="requirements" initial_value=requirements %}
            </form>
        """
        )

        context = Context({"requirements": trait_req("strength", minimum=3)})

        rendered = template.render(context)

        # Check for key elements
        self.assertIn('class="prerequisite-builder"', rendered)
        self.assertIn('data-field-name="requirements"', rendered)
        self.assertIn("Add Requirement", rendered)

    def test_visual_builder_with_complex_requirements(self):
        """Test rendering with complex nested requirements."""
        template = Template(
            """
            {% load prerequisite_tags %}
            {% prerequisite_builder field_name="test_req" initial_value=complex_req %}
        """
        )

        complex_req = all_of(
            trait_req("arete", minimum=3),
            any_of(
                has_item("foci", name="Crystal Orb"), trait_req("willpower", minimum=8)
            ),
        )

        context = Context({"complex_req": complex_req})
        rendered = template.render(context)

        # Should render nested structure
        self.assertIn("requirement-group", rendered)
        self.assertIn("requirement-block", rendered)
        self.assertIn("All:", rendered)

    def test_visual_builder_empty_state(self):
        """Test rendering with no initial requirements."""
        template = Template(
            """
            {% load prerequisite_tags %}
            {% prerequisite_builder field_name="empty_req" %}
        """
        )

        rendered = template.render(Context({}))

        # Should show empty state with add button
        self.assertIn("No requirements defined", rendered)
        self.assertIn("Add First Requirement", rendered)


class VisualBuilderJSONAPITests(TestCase):
    """Test JSON API endpoints for the visual builder."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.client = Client()
        self.client.login(username="testuser", password="testpass123")

    def test_validate_requirement_endpoint(self):
        """Test requirement validation via AJAX."""
        url = reverse("prerequisites:validate_requirement")

        valid_req = {"trait": {"name": "strength", "min": 3}}

        response = self.client.post(
            url, data=json.dumps(valid_req), content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["valid"])
        self.assertNotIn("errors", data)

    def test_validate_invalid_requirement(self):
        """Test validation of invalid requirements."""
        url = reverse("prerequisites:validate_requirement")

        invalid_req = {
            "trait": {
                "name": "",  # Invalid empty name
                "min": -1,  # Invalid negative minimum
            }
        }

        response = self.client.post(
            url, data=json.dumps(invalid_req), content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["valid"])
        self.assertIn("errors", data)

    def test_requirement_suggestions_endpoint(self):
        """Test getting suggestions for requirement building."""
        url = reverse("prerequisites:requirement_suggestions")

        response = self.client.get(url, {"type": "trait"})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("suggestions", data)
        # Should include common traits
        self.assertIn("strength", [s["name"] for s in data["suggestions"]])


class PrerequisiteBuilderFormTests(TestCase):
    """Test form integration with visual builder."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.user,
            game_system="Mage: The Ascension",
            max_characters_per_player=0,
        )

    def test_prerequisite_form_with_visual_builder(self):
        """Test Django form using visual builder widget."""
        from prerequisites.forms import PrerequisiteForm

        form = PrerequisiteForm()

        # Check that visual builder widget is used
        requirements_widget = form.fields["requirements"].widget
        self.assertEqual(
            requirements_widget.__class__.__name__, "PrerequisiteBuilderWidget"
        )

    def test_form_validation_with_visual_data(self):
        """Test form validation with data from visual builder."""
        from prerequisites.forms import PrerequisiteForm

        form_data = {
            "description": "Test Prerequisite",
            "requirements": json.dumps(trait_req("strength", minimum=3)),
        }

        form = PrerequisiteForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_form_save_creates_prerequisite(self):
        """Test that form save creates prerequisite correctly."""
        from prerequisites.forms import PrerequisiteForm

        form_data = {
            "description": "Strength Requirement",
            "requirements": json.dumps(trait_req("strength", minimum=3)),
        }

        form = PrerequisiteForm(data=form_data)
        self.assertTrue(form.is_valid())

        prerequisite = form.save()
        self.assertEqual(prerequisite.description, "Strength Requirement")
        self.assertIn("trait", prerequisite.requirements)


class VisualBuilderIntegrationTests(TestCase):
    """Integration tests for the complete visual builder system."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.user,
            game_system="Mage: The Ascension",
            max_characters_per_player=0,
        )
        self.character = MageCharacter.objects.create(
            name="Test Mage",
            campaign=self.campaign,
            player_owner=self.user,
            game_system="Mage: The Ascension",
            arete=3,
            quintessence=10,
            willpower=6,
        )

    def test_visual_builder_in_admin_interface(self):
        """Test visual builder integration in Django admin."""
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()

        self.client.login(username="testuser", password="testpass123")

        # Access prerequisite admin add page
        url = reverse("admin:prerequisites_prerequisite_add")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        # Should include visual builder JavaScript
        self.assertIn("prerequisite-builder.js", response.content.decode())

    def test_visual_builder_end_to_end_workflow(self):
        """Test complete workflow from visual building to requirement checking."""
        # Create prerequisite using visual builder (simulated)
        requirement = all_of(
            trait_req("arete", minimum=3), trait_req("willpower", minimum=8)
        )

        prerequisite = Prerequisite.objects.create(
            description="Advanced Magic Requirement", requirements=requirement
        )

        # Check requirement against character
        from prerequisites.checkers import check_requirement

        result = check_requirement(self.character, requirement)

        # Character should meet arete but not willpower requirement
        self.assertFalse(result.success)
        self.assertIn("Not all requirements satisfied", str(result))
