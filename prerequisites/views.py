"""
Views for prerequisite visual builder API (Issue #190).

This module provides JSON API endpoints that support the visual
prerequisite builder interface.
"""

import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from .helpers import all_of, any_of, count_with_tag, has_item, trait_req
from .validators import validate_requirements


class ValidateRequirementView(LoginRequiredMixin, View):
    """API endpoint for validating requirement JSON structure."""

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request):
        """Validate a requirement structure."""
        try:
            data = json.loads(request.body)

            # Use our validation system
            validate_requirements(data)

            return JsonResponse(
                {"valid": True, "message": "Requirement structure is valid."}
            )

        except json.JSONDecodeError:
            return JsonResponse(
                {"valid": False, "errors": ["Invalid JSON format."]}, status=400
            )

        except Exception as e:
            return JsonResponse({"valid": False, "errors": [str(e)]}, status=400)


class RequirementSuggestionsView(LoginRequiredMixin, View):
    """API endpoint for getting requirement suggestions."""

    def get(self, request):
        """Get suggestions based on requirement type."""
        requirement_type = request.GET.get("type", "trait")

        suggestions = []

        if requirement_type == "trait":
            # Common trait suggestions for RPG systems
            suggestions = [
                {"name": "strength", "description": "Physical strength"},
                {"name": "dexterity", "description": "Physical agility"},
                {"name": "stamina", "description": "Physical endurance"},
                {"name": "charisma", "description": "Social presence"},
                {"name": "manipulation", "description": "Social influence"},
                {"name": "appearance", "description": "Physical attractiveness"},
                {"name": "perception", "description": "Awareness and intuition"},
                {"name": "intelligence", "description": "Reasoning ability"},
                {"name": "wits", "description": "Quick thinking"},
                {"name": "willpower", "description": "Mental resilience"},
                {"name": "arete", "description": "Magical enlightenment (Mage)"},
                {"name": "quintessence", "description": "Magical energy (Mage)"},
            ]

        elif requirement_type == "has":
            suggestions = [
                {"field": "weapons", "description": "Character weapons"},
                {"field": "armor", "description": "Character armor"},
                {"field": "foci", "description": "Magical foci (Mage)"},
                {"field": "equipment", "description": "General equipment"},
                {"field": "rotes", "description": "Known rotes (Mage)"},
            ]

        return JsonResponse({"suggestions": suggestions})


class RequirementTemplatesView(LoginRequiredMixin, View):
    """API endpoint for getting predefined requirement templates."""

    def get(self, request):
        """Get common requirement templates."""
        templates = [
            {
                "name": "Basic Trait Check",
                "description": "Simple minimum trait requirement",
                "template": trait_req("strength", minimum=3),
            },
            {
                "name": "Combat Ready",
                "description": "Either high strength or dexterity",
                "template": any_of(
                    trait_req("strength", minimum=4), trait_req("dexterity", minimum=4)
                ),
            },
            {
                "name": "Mage Prerequisites",
                "description": "Basic magical requirements",
                "template": all_of(
                    trait_req("arete", minimum=2), trait_req("willpower", minimum=5)
                ),
            },
            {
                "name": "Advanced Mage",
                "description": "Advanced magical practitioner",
                "template": all_of(
                    trait_req("arete", minimum=4),
                    trait_req("quintessence", minimum=15),
                    has_item("foci", name="Primary Focus"),
                ),
            },
            {
                "name": "Social Influencer",
                "description": "High social attributes",
                "template": any_of(
                    trait_req("charisma", minimum=4),
                    trait_req("manipulation", minimum=4),
                ),
            },
        ]

        return JsonResponse({"templates": templates})
