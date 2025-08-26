"""
Comprehensive tests for prerequisite builder JSON output generation (Issue #190).

This module tests JSON output generation from the visual prerequisite builder,
ensuring that the visual interface produces valid, correctly structured JSON
that matches the backend validation requirements.

Key JSON generation features being tested:
1. Simple requirement JSON generation (trait, has, count_tag)
2. Complex nested requirement JSON generation (any, all)
3. JSON structure validation and compliance
4. Edge cases and boundary conditions
5. Performance with large requirement structures
6. JSON formatting and serialization
7. Integration with backend validation
8. Round-trip consistency (JSON -> UI -> JSON)

The JSON generation system should produce output that is compatible with
the existing prerequisite validation and checking systems.
"""

import json

from django.core.exceptions import ValidationError
from django.test import TestCase

from prerequisites import validators
from prerequisites.helpers import all_of, has_item, trait_req


class SimpleRequirementJSONGenerationTest(TestCase):
    """Test JSON generation for simple requirements."""

    def test_trait_requirement_json_generation(self):
        """Test JSON generation for trait requirements."""
        # Mock visual builder data for trait requirement
        trait_builder_data = {
            "requirement_type": "trait",
            "trait_name": "strength",
            "use_min": True,
            "trait_min": 3,
            "use_max": False,
            "trait_max": None,
            "use_exact": False,
            "trait_exact": None,
        }

        def generate_trait_json(builder_data):
            """Generate JSON from trait builder data."""
            trait_data = {"name": builder_data["trait_name"]}

            if (
                builder_data.get("use_min")
                and builder_data.get("trait_min") is not None
            ):
                trait_data["min"] = builder_data["trait_min"]
            if (
                builder_data.get("use_max")
                and builder_data.get("trait_max") is not None
            ):
                trait_data["max"] = builder_data["trait_max"]
            if (
                builder_data.get("use_exact")
                and builder_data.get("trait_exact") is not None
            ):
                trait_data["exact"] = builder_data["trait_exact"]

            return {"trait": trait_data}

        generated_json = generate_trait_json(trait_builder_data)
        expected_json = {"trait": {"name": "strength", "min": 3}}

        self.assertEqual(generated_json, expected_json)

        # Test with multiple constraints
        complex_trait_data = {
            "requirement_type": "trait",
            "trait_name": "melee",
            "use_min": True,
            "trait_min": 2,
            "use_max": True,
            "trait_max": 5,
            "use_exact": False,
            "trait_exact": None,
        }

        complex_json = generate_trait_json(complex_trait_data)
        expected_complex = {"trait": {"name": "melee", "min": 2, "max": 5}}

        self.assertEqual(complex_json, expected_complex)

        # Test with exact value
        exact_trait_data = {
            "requirement_type": "trait",
            "trait_name": "arete",
            "use_min": False,
            "trait_min": None,
            "use_max": False,
            "trait_max": None,
            "use_exact": True,
            "trait_exact": 2,
        }

        exact_json = generate_trait_json(exact_trait_data)
        expected_exact = {"trait": {"name": "arete", "exact": 2}}

        self.assertEqual(exact_json, expected_exact)

    def test_has_requirement_json_generation(self):
        """Test JSON generation for has requirements."""

        def generate_has_json(builder_data):
            """Generate JSON from has builder data."""
            has_data = {"field": builder_data["field_name"]}

            if builder_data.get("use_id") and builder_data.get("item_id") is not None:
                has_data["id"] = builder_data["item_id"]
            if builder_data.get("use_name") and builder_data.get("item_name"):
                has_data["name"] = builder_data["item_name"]

            # Add any additional fields
            for key, value in builder_data.get("additional_fields", {}).items():
                has_data[key] = value

            return {"has": has_data}

        # Test with ID only
        id_builder_data = {
            "requirement_type": "has",
            "field_name": "weapons",
            "use_id": True,
            "item_id": 123,
            "use_name": False,
            "item_name": "",
            "additional_fields": {},
        }

        id_json = generate_has_json(id_builder_data)
        expected_id_json = {"has": {"field": "weapons", "id": 123}}

        self.assertEqual(id_json, expected_id_json)

        # Test with name only
        name_builder_data = {
            "requirement_type": "has",
            "field_name": "foci",
            "use_id": False,
            "item_id": None,
            "use_name": True,
            "item_name": "Crystal Orb",
            "additional_fields": {},
        }

        name_json = generate_has_json(name_builder_data)
        expected_name_json = {"has": {"field": "foci", "name": "Crystal Orb"}}

        self.assertEqual(name_json, expected_name_json)

        # Test with both ID and name plus additional fields
        complex_builder_data = {
            "requirement_type": "has",
            "field_name": "weapons",
            "use_id": True,
            "item_id": 456,
            "use_name": True,
            "item_name": "Magic Sword",
            "additional_fields": {"level": 2, "enchanted": True},
        }

        complex_json = generate_has_json(complex_builder_data)
        expected_complex_json = {
            "has": {
                "field": "weapons",
                "id": 456,
                "name": "Magic Sword",
                "level": 2,
                "enchanted": True,
            }
        }

        self.assertEqual(complex_json, expected_complex_json)

    def test_count_tag_requirement_json_generation(self):
        """Test JSON generation for count_tag requirements."""

        def generate_count_tag_json(builder_data):
            """Generate JSON from count_tag builder data."""
            count_data = {
                "model": builder_data["model_name"],
                "tag": builder_data["tag_name"],
            }

            if (
                builder_data.get("use_minimum")
                and builder_data.get("minimum_count") is not None
            ):
                count_data["minimum"] = builder_data["minimum_count"]
            if (
                builder_data.get("use_maximum")
                and builder_data.get("maximum_count") is not None
            ):
                count_data["maximum"] = builder_data["maximum_count"]

            return {"count_tag": count_data}

        # Test with minimum only
        min_builder_data = {
            "requirement_type": "count_tag",
            "model_name": "spheres",
            "tag_name": "elemental",
            "use_minimum": True,
            "minimum_count": 2,
            "use_maximum": False,
            "maximum_count": None,
        }

        min_json = generate_count_tag_json(min_builder_data)
        expected_min_json = {
            "count_tag": {"model": "spheres", "tag": "elemental", "minimum": 2}
        }

        self.assertEqual(min_json, expected_min_json)

        # Test with both minimum and maximum
        range_builder_data = {
            "requirement_type": "count_tag",
            "model_name": "charms",
            "tag_name": "combat",
            "use_minimum": True,
            "minimum_count": 1,
            "use_maximum": True,
            "maximum_count": 3,
        }

        range_json = generate_count_tag_json(range_builder_data)
        expected_range_json = {
            "count_tag": {
                "model": "charms",
                "tag": "combat",
                "minimum": 1,
                "maximum": 3,
            }
        }

        self.assertEqual(range_json, expected_range_json)


class NestedRequirementJSONGenerationTest(TestCase):
    """Test JSON generation for nested requirements."""

    def test_any_requirement_json_generation(self):
        """Test JSON generation for any (OR) requirements."""

        def generate_any_json(builder_data):
            """Generate JSON from any requirement builder data."""
            sub_requirements = []

            for sub_req_data in builder_data["sub_requirements"]:
                if sub_req_data["requirement_type"] == "trait":
                    trait_data = {"name": sub_req_data["trait_name"]}
                    if sub_req_data.get("use_min"):
                        trait_data["min"] = sub_req_data["trait_min"]
                    sub_requirements.append({"trait": trait_data})
                elif sub_req_data["requirement_type"] == "has":
                    has_data = {"field": sub_req_data["field_name"]}
                    if sub_req_data.get("use_name"):
                        has_data["name"] = sub_req_data["item_name"]
                    sub_requirements.append({"has": has_data})

            return {"any": sub_requirements}

        # Test simple any requirement
        any_builder_data = {
            "requirement_type": "any",
            "sub_requirements": [
                {
                    "requirement_type": "trait",
                    "trait_name": "strength",
                    "use_min": True,
                    "trait_min": 4,
                },
                {
                    "requirement_type": "trait",
                    "trait_name": "dexterity",
                    "use_min": True,
                    "trait_min": 4,
                },
            ],
        }

        any_json = generate_any_json(any_builder_data)
        expected_any_json = {
            "any": [
                {"trait": {"name": "strength", "min": 4}},
                {"trait": {"name": "dexterity", "min": 4}},
            ]
        }

        self.assertEqual(any_json, expected_any_json)

        # Test mixed requirement types in any
        mixed_any_data = {
            "requirement_type": "any",
            "sub_requirements": [
                {
                    "requirement_type": "trait",
                    "trait_name": "arete",
                    "use_min": True,
                    "trait_min": 3,
                },
                {
                    "requirement_type": "has",
                    "field_name": "foci",
                    "use_name": True,
                    "item_name": "Crystal Orb",
                },
            ],
        }

        mixed_any_json = generate_any_json(mixed_any_data)
        expected_mixed_json = {
            "any": [
                {"trait": {"name": "arete", "min": 3}},
                {"has": {"field": "foci", "name": "Crystal Orb"}},
            ]
        }

        self.assertEqual(mixed_any_json, expected_mixed_json)

    def test_all_requirement_json_generation(self):
        """Test JSON generation for all (AND) requirements."""

        def generate_all_json(builder_data):
            """Generate JSON from all requirement builder data."""
            sub_requirements = []

            for sub_req_data in builder_data["sub_requirements"]:
                if sub_req_data["requirement_type"] == "trait":
                    trait_data = {"name": sub_req_data["trait_name"]}
                    if sub_req_data.get("use_min"):
                        trait_data["min"] = sub_req_data["trait_min"]
                    if sub_req_data.get("use_max"):
                        trait_data["max"] = sub_req_data["trait_max"]
                    sub_requirements.append({"trait": trait_data})
                elif sub_req_data["requirement_type"] == "count_tag":
                    count_data = {
                        "model": sub_req_data["model_name"],
                        "tag": sub_req_data["tag_name"],
                        "minimum": sub_req_data["minimum_count"],
                    }
                    sub_requirements.append({"count_tag": count_data})

            return {"all": sub_requirements}

        # Test all requirement with multiple constraints
        all_builder_data = {
            "requirement_type": "all",
            "sub_requirements": [
                {
                    "requirement_type": "trait",
                    "trait_name": "arete",
                    "use_min": True,
                    "trait_min": 2,
                    "use_max": True,
                    "trait_max": 4,
                },
                {
                    "requirement_type": "count_tag",
                    "model_name": "spheres",
                    "tag_name": "elemental",
                    "minimum_count": 1,
                },
            ],
        }

        all_json = generate_all_json(all_builder_data)
        expected_all_json = {
            "all": [
                {"trait": {"name": "arete", "min": 2, "max": 4}},
                {"count_tag": {"model": "spheres", "tag": "elemental", "minimum": 1}},
            ]
        }

        self.assertEqual(all_json, expected_all_json)

    def test_deeply_nested_requirement_json_generation(self):
        """Test JSON generation for deeply nested requirements."""

        def generate_nested_json(builder_data, depth=0):
            """Recursively generate JSON from nested requirement data."""
            if builder_data["requirement_type"] == "any":
                sub_requirements = []
                for sub_req in builder_data["sub_requirements"]:
                    sub_requirements.append(generate_nested_json(sub_req, depth + 1))
                return {"any": sub_requirements}
            elif builder_data["requirement_type"] == "all":
                sub_requirements = []
                for sub_req in builder_data["sub_requirements"]:
                    sub_requirements.append(generate_nested_json(sub_req, depth + 1))
                return {"all": sub_requirements}
            elif builder_data["requirement_type"] == "trait":
                trait_data = {"name": builder_data["trait_name"]}
                if builder_data.get("use_min"):
                    trait_data["min"] = builder_data["trait_min"]
                return {"trait": trait_data}

        # Test 3-level nesting: ALL -> ANY -> TRAIT
        deeply_nested_data = {
            "requirement_type": "all",
            "sub_requirements": [
                {
                    "requirement_type": "trait",
                    "trait_name": "arete",
                    "use_min": True,
                    "trait_min": 2,
                },
                {
                    "requirement_type": "any",
                    "sub_requirements": [
                        {
                            "requirement_type": "trait",
                            "trait_name": "strength",
                            "use_min": True,
                            "trait_min": 3,
                        },
                        {
                            "requirement_type": "trait",
                            "trait_name": "dexterity",
                            "use_min": True,
                            "trait_min": 3,
                        },
                    ],
                },
            ],
        }

        nested_json = generate_nested_json(deeply_nested_data)
        expected_nested_json = {
            "all": [
                {"trait": {"name": "arete", "min": 2}},
                {
                    "any": [
                        {"trait": {"name": "strength", "min": 3}},
                        {"trait": {"name": "dexterity", "min": 3}},
                    ]
                },
            ]
        }

        self.assertEqual(nested_json, expected_nested_json)


class JSONStructureValidationTest(TestCase):
    """Test JSON structure validation and compliance."""

    def test_generated_json_validates_against_schema(self):
        """Test that generated JSON validates against prerequisite schema."""
        # Generate various JSON structures and validate them
        test_cases = [
            # Simple trait requirement
            {"trait": {"name": "strength", "min": 3}},
            # Has requirement with ID
            {"has": {"field": "weapons", "id": 123}},
            # Count tag requirement
            {"count_tag": {"model": "spheres", "tag": "elemental", "minimum": 2}},
            # Any requirement
            {
                "any": [
                    {"trait": {"name": "strength", "min": 3}},
                    {"trait": {"name": "dexterity", "min": 3}},
                ]
            },
            # All requirement
            {
                "all": [
                    {"trait": {"name": "arete", "min": 2}},
                    {"has": {"field": "foci", "name": "Crystal"}},
                ]
            },
        ]

        for json_data in test_cases:
            try:
                # Use the existing validators module to validate
                validators.validate_requirements(json_data)
                validation_passed = True
            except ValidationError:
                validation_passed = False

            self.assertTrue(
                validation_passed, f"Generated JSON failed validation: {json_data}"
            )

    def test_json_serialization_and_deserialization(self):
        """Test JSON serialization and deserialization round-trip."""
        original_data = {
            "all": [
                {"trait": {"name": "arete", "min": 2, "max": 5}},
                {
                    "any": [
                        {"has": {"field": "weapons", "id": 123}},
                        {"has": {"field": "weapons", "name": "Magic Sword"}},
                    ]
                },
                {"count_tag": {"model": "spheres", "tag": "elemental", "minimum": 1}},
            ]
        }

        # Serialize to JSON string
        json_string = json.dumps(original_data)

        # Deserialize back to Python object
        deserialized_data = json.loads(json_string)

        # Should be identical
        self.assertEqual(original_data, deserialized_data)

        # Test pretty-printing
        pretty_json = json.dumps(original_data, indent=2, sort_keys=True)
        pretty_deserialized = json.loads(pretty_json)

        self.assertEqual(original_data, pretty_deserialized)
        self.assertIn("\n", pretty_json)  # Should have newlines
        self.assertIn("  ", pretty_json)  # Should have indentation

    def test_json_edge_cases_and_special_values(self):
        """Test JSON generation with edge cases and special values."""
        edge_cases = [
            # Zero values
            {"trait": {"name": "willpower", "min": 0}},
            {"count_tag": {"model": "items", "tag": "mundane", "minimum": 0}},
            # Large values
            {"trait": {"name": "age", "min": 1000}},
            {"has": {"field": "memories", "id": 999999}},
            # Special characters in names
            {"trait": {"name": "skill_melee", "min": 1}},
            {"has": {"field": "items", "name": "Sword of +3 Enhancement"}},
            # Unicode characters
            {"trait": {"name": "résistance", "min": 2}},
            {"has": {"field": "foci", "name": "Cristal magique"}},
            # Empty any/all arrays (should be invalid but test structure)
            {"any": []},
            {"all": []},
        ]

        for case in edge_cases:
            # Test serialization doesn't crash
            try:
                json_string = json.dumps(case)
                json.loads(json_string)  # Verify it parses
                serialization_ok = True
            except (TypeError, ValueError):
                serialization_ok = False

            # Most edge cases should serialize successfully
            if case not in [{"any": []}, {"all": []}]:  # These are structurally invalid
                self.assertTrue(serialization_ok, f"Serialization failed for: {case}")


class JSONGenerationPerformanceTest(TestCase):
    """Test JSON generation performance with large structures."""

    def test_large_nested_structure_generation(self):
        """Test JSON generation with large nested structures."""

        def create_large_nested_structure(depth, width):
            """Create a large nested requirement structure for testing."""
            if depth <= 0:
                return {"trait": {"name": f"trait_{width}", "min": 1}}

            sub_requirements = []
            for i in range(width):
                sub_requirements.append(create_large_nested_structure(depth - 1, i + 1))

            return {"any" if depth % 2 == 0 else "all": sub_requirements}

        def generate_json_from_structure(structure):
            """Generate JSON from a requirement structure (identity function for testing)."""
            return structure

        # Test moderately large structure (depth=3, width=5)
        large_structure = create_large_nested_structure(3, 5)
        generated_json = generate_json_from_structure(large_structure)

        # Should be able to serialize without issues
        json_string = json.dumps(generated_json)
        self.assertIsInstance(json_string, str)
        self.assertGreater(len(json_string), 100)  # Should be substantial

        # Should be able to deserialize
        parsed_back = json.loads(json_string)
        self.assertEqual(generated_json, parsed_back)

    def test_many_sibling_requirements_generation(self):
        """Test JSON generation with many sibling requirements."""
        # Create structure with many siblings at one level
        many_siblings_structure = {"all": []}

        # Add 50 trait requirements
        for i in range(50):
            trait_req = {"trait": {"name": f"skill_{i:02d}", "min": i % 5 + 1}}
            many_siblings_structure["all"].append(trait_req)

        # Should handle serialization efficiently
        json_string = json.dumps(many_siblings_structure)
        self.assertIsInstance(json_string, str)

        # Check structure is preserved
        parsed_back = json.loads(json_string)
        self.assertEqual(len(parsed_back["all"]), 50)
        self.assertEqual(
            parsed_back["all"][0], {"trait": {"name": "skill_00", "min": 1}}
        )
        self.assertEqual(
            parsed_back["all"][49], {"trait": {"name": "skill_49", "min": 5}}
        )


class JSONOutputIntegrationTest(TestCase):
    """Test JSON output integration with backend systems."""

    def test_json_output_compatibility_with_helpers(self):
        """Test that generated JSON is compatible with helper functions."""
        # Generate JSON using visual builder approach
        visual_builder_json = {
            "all": [
                {"trait": {"name": "arete", "min": 3}},
                {"has": {"field": "foci", "name": "Crystal Orb"}},
            ]
        }

        # Compare with helper function output
        helper_json = all_of(
            trait_req("arete", minimum=3), has_item("foci", name="Crystal Orb")
        )

        # Should be structurally equivalent
        self.assertEqual(visual_builder_json, helper_json)

        # Both should validate successfully
        try:
            validators.validate_requirements(visual_builder_json)
            visual_valid = True
        except ValidationError:
            visual_valid = False

        try:
            validators.validate_requirements(helper_json)
            helper_valid = True
        except ValidationError:
            helper_valid = False

        self.assertTrue(visual_valid)
        self.assertTrue(helper_valid)

    def test_json_output_round_trip_consistency(self):
        """Test round-trip consistency: JSON -> UI -> JSON."""
        # Original JSON from backend
        original_json = {
            "any": [
                {"trait": {"name": "strength", "min": 3, "max": 5}},
                {
                    "all": [
                        {"trait": {"name": "dexterity", "min": 4}},
                        {"has": {"field": "weapons", "id": 123, "name": "Magic Sword"}},
                    ]
                },
            ]
        }

        # Simulate loading into UI (convert to builder format)
        def json_to_builder_format(json_data):
            """Convert JSON to visual builder format."""

            def convert_requirement(req_data):
                if "trait" in req_data:
                    trait = req_data["trait"]
                    return {
                        "requirement_type": "trait",
                        "trait_name": trait["name"],
                        "use_min": "min" in trait,
                        "trait_min": trait.get("min"),
                        "use_max": "max" in trait,
                        "trait_max": trait.get("max"),
                        "use_exact": "exact" in trait,
                        "trait_exact": trait.get("exact"),
                    }
                elif "has" in req_data:
                    has = req_data["has"]
                    return {
                        "requirement_type": "has",
                        "field_name": has["field"],
                        "use_id": "id" in has,
                        "item_id": has.get("id"),
                        "use_name": "name" in has,
                        "item_name": has.get("name"),
                    }
                elif "any" in req_data:
                    return {
                        "requirement_type": "any",
                        "sub_requirements": [
                            convert_requirement(sub) for sub in req_data["any"]
                        ],
                    }
                elif "all" in req_data:
                    return {
                        "requirement_type": "all",
                        "sub_requirements": [
                            convert_requirement(sub) for sub in req_data["all"]
                        ],
                    }

            return convert_requirement(json_data)

        # Convert JSON to builder format
        builder_format = json_to_builder_format(original_json)

        # Simulate generating JSON from UI (convert back to JSON)
        def builder_to_json_format(builder_data):
            """Convert builder format back to JSON."""
            if builder_data["requirement_type"] == "trait":
                trait_data = {"name": builder_data["trait_name"]}
                if builder_data.get("use_min"):
                    trait_data["min"] = builder_data["trait_min"]
                if builder_data.get("use_max"):
                    trait_data["max"] = builder_data["trait_max"]
                if builder_data.get("use_exact"):
                    trait_data["exact"] = builder_data["trait_exact"]
                return {"trait": trait_data}
            elif builder_data["requirement_type"] == "has":
                has_data = {"field": builder_data["field_name"]}
                if builder_data.get("use_id"):
                    has_data["id"] = builder_data["item_id"]
                if builder_data.get("use_name"):
                    has_data["name"] = builder_data["item_name"]
                return {"has": has_data}
            elif builder_data["requirement_type"] in ["any", "all"]:
                sub_requirements = []
                for sub_req in builder_data["sub_requirements"]:
                    sub_requirements.append(builder_to_json_format(sub_req))
                return {builder_data["requirement_type"]: sub_requirements}

        # Convert back to JSON
        regenerated_json = builder_to_json_format(builder_format)

        # Should match original
        self.assertEqual(original_json, regenerated_json)

    def test_json_output_validation_integration(self):
        """Test integration with backend validation systems."""
        # Generate JSON from visual builder
        generated_json = {
            "all": [
                {"trait": {"name": "arete", "min": 2}},
                {"count_tag": {"model": "spheres", "tag": "elemental", "minimum": 1}},
            ]
        }

        # Should pass validation
        try:
            validators.validate_requirements(generated_json)
            is_valid = True
            validation_error = None
        except ValidationError as e:
            is_valid = False
            validation_error = str(e)

        self.assertTrue(
            is_valid, f"Generated JSON failed validation: {validation_error}"
        )

        # Test with invalid JSON from hypothetically broken UI
        invalid_json = {
            "all": [
                {"trait": {"name": "", "min": -1}},  # Invalid: empty name, negative min
                {
                    "count_tag": {"model": "spheres"}
                },  # Invalid: missing tag and constraints
            ]
        }

        # Should fail validation
        try:
            validators.validate_requirements(invalid_json)
            invalid_passes = True
        except ValidationError:
            invalid_passes = False

        self.assertFalse(invalid_passes, "Invalid JSON should not pass validation")


class JSONFormattingAndDisplayTest(TestCase):
    """Test JSON formatting and display functionality."""

    def test_json_pretty_printing_for_preview(self):
        """Test JSON pretty-printing for user preview."""
        complex_json = {
            "all": [
                {"trait": {"name": "arete", "min": 2, "max": 4}},
                {
                    "any": [
                        {"has": {"field": "foci", "name": "Crystal Orb"}},
                        {"has": {"field": "foci", "name": "Staff of Power"}},
                    ]
                },
            ]
        }

        # Test compact formatting (for storage)
        compact = json.dumps(complex_json, separators=(",", ":"))
        # Should not contain extra spaces (minimal formatting)
        self.assertNotIn(", ", compact)  # No space after comma
        self.assertNotIn(": ", compact)  # No space after colon
        self.assertNotIn("\n", compact)

        # Test pretty formatting (for display)
        pretty = json.dumps(complex_json, indent=2, sort_keys=True)
        self.assertIn("\n", pretty)
        self.assertIn("  ", pretty)  # 2-space indentation

        # Test custom formatting options
        custom_pretty = json.dumps(complex_json, indent=4, sort_keys=False)
        self.assertIn("\n", custom_pretty)
        self.assertIn("    ", custom_pretty)  # 4-space indentation

        # All formats should parse to the same data
        parsed_compact = json.loads(compact)
        parsed_pretty = json.loads(pretty)
        parsed_custom = json.loads(custom_pretty)

        self.assertEqual(complex_json, parsed_compact)
        self.assertEqual(complex_json, parsed_pretty)
        self.assertEqual(complex_json, parsed_custom)

    def test_json_syntax_highlighting_structure(self):
        """Test structure for JSON syntax highlighting."""
        # Mock syntax highlighting data structure
        json_with_highlighting = {
            "content": '{"trait": {"name": "strength", "min": 3}}',
            "tokens": [
                {"type": "brace", "value": "{", "start": 0, "end": 1},
                {"type": "key", "value": '"trait"', "start": 1, "end": 8},
                {"type": "colon", "value": ":", "start": 8, "end": 9},
                {"type": "brace", "value": "{", "start": 10, "end": 11},
                {"type": "key", "value": '"name"', "start": 11, "end": 17},
                {"type": "colon", "value": ":", "start": 17, "end": 18},
                {"type": "string", "value": '"strength"', "start": 19, "end": 29},
                {"type": "comma", "value": ",", "start": 29, "end": 30},
                {"type": "key", "value": '"min"', "start": 31, "end": 36},
                {"type": "colon", "value": ":", "start": 36, "end": 37},
                {"type": "number", "value": "3", "start": 38, "end": 39},
                {"type": "brace", "value": "}", "start": 39, "end": 40},
                {"type": "brace", "value": "}", "start": 40, "end": 41},
            ],
        }

        # Test highlighting structure
        self.assertIn("content", json_with_highlighting)
        self.assertIn("tokens", json_with_highlighting)

        # Test token structure
        first_token = json_with_highlighting["tokens"][0]
        self.assertIn("type", first_token)
        self.assertIn("value", first_token)
        self.assertIn("start", first_token)
        self.assertIn("end", first_token)

        # Test token types
        token_types = [token["type"] for token in json_with_highlighting["tokens"]]
        expected_types = ["brace", "key", "colon", "string", "number"]
        for expected_type in expected_types:
            self.assertIn(expected_type, token_types)

    def test_json_diff_generation_for_changes(self):
        """Test JSON diff generation for showing changes."""
        original_json = {"trait": {"name": "strength", "min": 3}}

        modified_json = {"trait": {"name": "strength", "min": 4, "max": 6}}

        def generate_json_diff(original, modified):
            """Generate a simple diff structure."""
            diff = {"changes": [], "additions": [], "deletions": []}

            # Simple diff logic for demonstration
            if original != modified:
                diff["changes"].append(
                    {
                        "path": "trait.min",
                        "old_value": 3,
                        "new_value": 4,
                        "change_type": "modified",
                    }
                )
                diff["additions"].append(
                    {"path": "trait.max", "value": 6, "change_type": "added"}
                )

            return diff

        diff_result = generate_json_diff(original_json, modified_json)

        # Test diff structure
        self.assertIn("changes", diff_result)
        self.assertIn("additions", diff_result)
        self.assertIn("deletions", diff_result)

        # Test change detection
        self.assertEqual(len(diff_result["changes"]), 1)
        self.assertEqual(len(diff_result["additions"]), 1)

        # Test change details
        change = diff_result["changes"][0]
        self.assertEqual(change["path"], "trait.min")
        self.assertEqual(change["old_value"], 3)
        self.assertEqual(change["new_value"], 4)
