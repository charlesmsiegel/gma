"""
Comprehensive tests for requirement helper functions (Issue #188).

This test suite validates the helper functions that generate JSON requirement
structures, ensuring they create valid requirements that pass validation from
Issue #187.

Key testing areas:
1. Each helper function with valid inputs
2. Parameter validation and error handling
3. Edge cases and boundary conditions
4. Integration with the validators module
5. Generated JSON structure correctness
6. Convenience aliases functionality
7. Complex nested requirement generation

Requirements from Issue #188:
- Helper functions generate correct JSON
- Functions handle edge cases gracefully
- Generated JSON passes validation
- Functions are easy to use and understand
"""

from django.core.exceptions import ValidationError
from django.test import TestCase

# Import the helper functions
from prerequisites import helpers, validators


class TraitRequirementHelperTest(TestCase):
    """Test trait_req helper function."""

    def test_trait_req_minimum_only(self):
        """Test trait requirement with minimum constraint only."""
        result = helpers.trait_req("strength", minimum=3)

        expected = {"trait": {"name": "strength", "min": 3}}
        self.assertEqual(result, expected)

        # Should pass validation
        validators.validate_requirements(result)

    def test_trait_req_maximum_only(self):
        """Test trait requirement with maximum constraint only."""
        result = helpers.trait_req("dexterity", maximum=5)

        expected = {"trait": {"name": "dexterity", "max": 5}}
        self.assertEqual(result, expected)

        # Should pass validation
        validators.validate_requirements(result)

    def test_trait_req_exact_only(self):
        """Test trait requirement with exact constraint only."""
        result = helpers.trait_req("arete", exact=3)

        expected = {"trait": {"name": "arete", "exact": 3}}
        self.assertEqual(result, expected)

        # Should pass validation
        validators.validate_requirements(result)

    def test_trait_req_min_and_max(self):
        """Test trait requirement with both minimum and maximum."""
        result = helpers.trait_req("intelligence", minimum=2, maximum=5)

        expected = {"trait": {"name": "intelligence", "min": 2, "max": 5}}
        self.assertEqual(result, expected)

        # Should pass validation
        validators.validate_requirements(result)

    def test_trait_req_empty_name_invalid(self):
        """Test trait requirement with empty name."""
        with self.assertRaises(ValidationError) as context:
            helpers.trait_req("", minimum=3)

        error_msg = str(context.exception)
        self.assertIn("non-empty string", error_msg)

    def test_trait_req_whitespace_name_invalid(self):
        """Test trait requirement with whitespace-only name."""
        with self.assertRaises(ValidationError) as context:
            helpers.trait_req("   ", minimum=3)

        error_msg = str(context.exception)
        self.assertIn("non-empty string", error_msg)

    def test_trait_req_no_constraints_invalid(self):
        """Test trait requirement with no constraints."""
        with self.assertRaises(ValidationError) as context:
            helpers.trait_req("strength")

        error_msg = str(context.exception)
        self.assertIn("At least one constraint", error_msg)

    def test_trait_req_negative_minimum_invalid(self):
        """Test trait requirement with negative minimum."""
        with self.assertRaises(ValidationError) as context:
            helpers.trait_req("strength", minimum=-1)

        error_msg = str(context.exception)
        self.assertIn("non-negative integer", error_msg)

    def test_trait_req_invalid_minimum_type(self):
        """Test trait requirement with invalid minimum type."""
        with self.assertRaises(ValidationError) as context:
            helpers.trait_req("strength", minimum="invalid")

        error_msg = str(context.exception)
        self.assertIn("non-negative integer", error_msg)

    def test_trait_req_negative_maximum_invalid(self):
        """Test trait requirement with negative maximum."""
        with self.assertRaises(ValidationError) as context:
            helpers.trait_req("strength", maximum=-1)

        error_msg = str(context.exception)
        self.assertIn("non-negative integer", error_msg)

    def test_trait_req_invalid_exact_type(self):
        """Test trait requirement with invalid exact type."""
        with self.assertRaises(ValidationError) as context:
            helpers.trait_req("strength", exact="invalid")

        error_msg = str(context.exception)
        self.assertIn("non-negative integer", error_msg)

    def test_trait_req_trims_whitespace(self):
        """Test that trait name whitespace is trimmed."""
        result = helpers.trait_req("  strength  ", minimum=3)

        expected = {"trait": {"name": "strength", "min": 3}}
        self.assertEqual(result, expected)

    def test_trait_req_zero_values_valid(self):
        """Test trait requirement with zero values."""
        result = helpers.trait_req("trait", minimum=0, maximum=0)

        expected = {"trait": {"name": "trait", "min": 0, "max": 0}}
        self.assertEqual(result, expected)

        # Should pass validation
        validators.validate_requirements(result)


class HasItemHelperTest(TestCase):
    """Test has_item helper function."""

    def test_has_item_by_id_only(self):
        """Test has item requirement with ID only."""
        result = helpers.has_item("weapons", id=123)

        expected = {"has": {"field": "weapons", "id": 123}}
        self.assertEqual(result, expected)

        # Should pass validation
        validators.validate_requirements(result)

    def test_has_item_by_name_only(self):
        """Test has item requirement with name only."""
        result = helpers.has_item("foci", name="Crystal Orb")

        expected = {"has": {"field": "foci", "name": "Crystal Orb"}}
        self.assertEqual(result, expected)

        # Should pass validation
        validators.validate_requirements(result)

    def test_has_item_by_id_and_name(self):
        """Test has item requirement with both ID and name."""
        result = helpers.has_item("weapons", id=123, name="Magic Sword")

        expected = {"has": {"field": "weapons", "id": 123, "name": "Magic Sword"}}
        self.assertEqual(result, expected)

        # Should pass validation
        validators.validate_requirements(result)

    def test_has_item_with_additional_fields(self):
        """Test has item requirement with additional fields."""
        result = helpers.has_item(
            "weapons", id=123, name="Magic Sword", level=2, quality="legendary"
        )

        expected = {
            "has": {
                "field": "weapons",
                "id": 123,
                "name": "Magic Sword",
                "level": 2,
                "quality": "legendary",
            }
        }
        self.assertEqual(result, expected)

        # Should pass validation
        validators.validate_requirements(result)

    def test_has_item_empty_field_invalid(self):
        """Test has item requirement with empty field."""
        with self.assertRaises(ValidationError) as context:
            helpers.has_item("", id=123)

        error_msg = str(context.exception)
        self.assertIn("non-empty string", error_msg)

    def test_has_item_whitespace_field_invalid(self):
        """Test has item requirement with whitespace-only field."""
        with self.assertRaises(ValidationError) as context:
            helpers.has_item("   ", id=123)

        error_msg = str(context.exception)
        self.assertIn("non-empty string", error_msg)

    def test_has_item_no_identifier_invalid(self):
        """Test has item requirement with no ID or name."""
        with self.assertRaises(ValidationError) as context:
            helpers.has_item("weapons")

        error_msg = str(context.exception)
        self.assertIn("'id' or 'name'", error_msg)

    def test_has_item_invalid_id_type(self):
        """Test has item requirement with invalid ID type."""
        with self.assertRaises(ValidationError) as context:
            helpers.has_item("weapons", id="invalid")

        error_msg = str(context.exception)
        self.assertIn("positive integer", error_msg)

    def test_has_item_negative_id_invalid(self):
        """Test has item requirement with negative ID."""
        with self.assertRaises(ValidationError) as context:
            helpers.has_item("weapons", id=-1)

        error_msg = str(context.exception)
        self.assertIn("positive integer", error_msg)

    def test_has_item_zero_id_invalid(self):
        """Test has item requirement with zero ID."""
        with self.assertRaises(ValidationError) as context:
            helpers.has_item("weapons", id=0)

        error_msg = str(context.exception)
        self.assertIn("positive integer", error_msg)

    def test_has_item_invalid_name_type(self):
        """Test has item requirement with invalid name type."""
        with self.assertRaises(ValidationError) as context:
            helpers.has_item("weapons", name=123)

        error_msg = str(context.exception)
        self.assertIn("must be a string", error_msg)

    def test_has_item_trims_field_whitespace(self):
        """Test that field whitespace is trimmed."""
        result = helpers.has_item("  weapons  ", id=123)

        expected = {"has": {"field": "weapons", "id": 123}}
        self.assertEqual(result, expected)

    def test_has_item_empty_name_allowed(self):
        """Test that empty name is allowed if provided explicitly."""
        result = helpers.has_item("weapons", name="")

        expected = {"has": {"field": "weapons", "name": ""}}
        self.assertEqual(result, expected)

        # Should pass validation
        validators.validate_requirements(result)


class AnyOfHelperTest(TestCase):
    """Test any_of helper function."""

    def test_any_of_multiple_requirements(self):
        """Test any_of with multiple requirements."""
        req1 = helpers.trait_req("strength", minimum=3)
        req2 = helpers.trait_req("dexterity", minimum=3)

        result = helpers.any_of(req1, req2)

        expected = {
            "any": [
                {"trait": {"name": "strength", "min": 3}},
                {"trait": {"name": "dexterity", "min": 3}},
            ]
        }
        self.assertEqual(result, expected)

        # Should pass validation
        validators.validate_requirements(result)

    def test_any_of_single_requirement(self):
        """Test any_of with single requirement."""
        req1 = helpers.trait_req("strength", minimum=3)

        result = helpers.any_of(req1)

        expected = {"any": [{"trait": {"name": "strength", "min": 3}}]}
        self.assertEqual(result, expected)

        # Should pass validation
        validators.validate_requirements(result)

    def test_any_of_from_list(self):
        """Test any_of with requirements passed as a list."""
        req1 = helpers.trait_req("strength", minimum=3)
        req2 = helpers.trait_req("dexterity", minimum=3)
        req_list = [req1, req2]

        result = helpers.any_of(req_list)

        expected = {
            "any": [
                {"trait": {"name": "strength", "min": 3}},
                {"trait": {"name": "dexterity", "min": 3}},
            ]
        }
        self.assertEqual(result, expected)

        # Should pass validation
        validators.validate_requirements(result)

    def test_any_of_mixed_requirement_types(self):
        """Test any_of with mixed requirement types."""
        req1 = helpers.trait_req("strength", minimum=3)
        req2 = helpers.has_item("weapons", id=123)
        req3 = helpers.count_with_tag("spheres", "elemental", minimum=2)

        result = helpers.any_of(req1, req2, req3)

        expected = {
            "any": [
                {"trait": {"name": "strength", "min": 3}},
                {"has": {"field": "weapons", "id": 123}},
                {"count_tag": {"model": "spheres", "tag": "elemental", "minimum": 2}},
            ]
        }
        self.assertEqual(result, expected)

        # Should pass validation
        validators.validate_requirements(result)

    def test_any_of_empty_invalid(self):
        """Test any_of with no requirements."""
        with self.assertRaises(ValidationError) as context:
            helpers.any_of()

        error_msg = str(context.exception)
        self.assertIn("At least one requirement", error_msg)

    def test_any_of_empty_list_invalid(self):
        """Test any_of with empty list."""
        with self.assertRaises(ValidationError) as context:
            helpers.any_of([])

        error_msg = str(context.exception)
        self.assertIn("At least one requirement", error_msg)

    def test_any_of_non_dict_requirement_invalid(self):
        """Test any_of with non-dictionary requirement."""
        with self.assertRaises(ValidationError) as context:
            helpers.any_of("invalid_requirement")

        error_msg = str(context.exception)
        self.assertIn("must be a dictionary", error_msg)

    def test_any_of_invalid_subrequirement(self):
        """Test any_of with invalid subrequirement."""
        valid_req = helpers.trait_req("strength", minimum=3)
        invalid_req = {"invalid_type": {"field": "value"}}

        with self.assertRaises(ValidationError) as context:
            helpers.any_of(valid_req, invalid_req)

        error_msg = str(context.exception)
        self.assertIn("is invalid", error_msg)


class AllOfHelperTest(TestCase):
    """Test all_of helper function."""

    def test_all_of_multiple_requirements(self):
        """Test all_of with multiple requirements."""
        req1 = helpers.trait_req("arete", minimum=3)
        req2 = helpers.has_item("foci", name="Crystal Orb")

        result = helpers.all_of(req1, req2)

        expected = {
            "all": [
                {"trait": {"name": "arete", "min": 3}},
                {"has": {"field": "foci", "name": "Crystal Orb"}},
            ]
        }
        self.assertEqual(result, expected)

        # Should pass validation
        validators.validate_requirements(result)

    def test_all_of_single_requirement(self):
        """Test all_of with single requirement."""
        req1 = helpers.trait_req("strength", minimum=3)

        result = helpers.all_of(req1)

        expected = {"all": [{"trait": {"name": "strength", "min": 3}}]}
        self.assertEqual(result, expected)

        # Should pass validation
        validators.validate_requirements(result)

    def test_all_of_from_list(self):
        """Test all_of with requirements passed as a list."""
        req1 = helpers.trait_req("arete", minimum=3)
        req2 = helpers.has_item("foci", name="Crystal Orb")
        req_list = [req1, req2]

        result = helpers.all_of(req_list)

        expected = {
            "all": [
                {"trait": {"name": "arete", "min": 3}},
                {"has": {"field": "foci", "name": "Crystal Orb"}},
            ]
        }
        self.assertEqual(result, expected)

        # Should pass validation
        validators.validate_requirements(result)

    def test_all_of_mixed_requirement_types(self):
        """Test all_of with mixed requirement types."""
        req1 = helpers.trait_req("arete", minimum=3)
        req2 = helpers.has_item("foci", name="Crystal Orb")
        req3 = helpers.count_with_tag("spheres", "elemental", minimum=2)

        result = helpers.all_of(req1, req2, req3)

        expected = {
            "all": [
                {"trait": {"name": "arete", "min": 3}},
                {"has": {"field": "foci", "name": "Crystal Orb"}},
                {"count_tag": {"model": "spheres", "tag": "elemental", "minimum": 2}},
            ]
        }
        self.assertEqual(result, expected)

        # Should pass validation
        validators.validate_requirements(result)

    def test_all_of_empty_invalid(self):
        """Test all_of with no requirements."""
        with self.assertRaises(ValidationError) as context:
            helpers.all_of()

        error_msg = str(context.exception)
        self.assertIn("At least one requirement", error_msg)

    def test_all_of_empty_list_invalid(self):
        """Test all_of with empty list."""
        with self.assertRaises(ValidationError) as context:
            helpers.all_of([])

        error_msg = str(context.exception)
        self.assertIn("At least one requirement", error_msg)

    def test_all_of_non_dict_requirement_invalid(self):
        """Test all_of with non-dictionary requirement."""
        with self.assertRaises(ValidationError) as context:
            helpers.all_of("invalid_requirement")

        error_msg = str(context.exception)
        self.assertIn("must be a dictionary", error_msg)

    def test_all_of_invalid_subrequirement(self):
        """Test all_of with invalid subrequirement."""
        valid_req = helpers.trait_req("arete", minimum=3)
        invalid_req = {"invalid_type": {"field": "value"}}

        with self.assertRaises(ValidationError) as context:
            helpers.all_of(valid_req, invalid_req)

        error_msg = str(context.exception)
        self.assertIn("is invalid", error_msg)


class CountWithTagHelperTest(TestCase):
    """Test count_with_tag helper function."""

    def test_count_with_tag_minimum_only(self):
        """Test count_with_tag with minimum constraint only."""
        result = helpers.count_with_tag("spheres", "elemental", minimum=2)

        expected = {"count_tag": {"model": "spheres", "tag": "elemental", "minimum": 2}}
        self.assertEqual(result, expected)

        # Should pass validation
        validators.validate_requirements(result)

    def test_count_with_tag_maximum_only(self):
        """Test count_with_tag with maximum constraint only."""
        result = helpers.count_with_tag("charms", "martial_arts", maximum=5)

        expected = {
            "count_tag": {"model": "charms", "tag": "martial_arts", "maximum": 5}
        }
        self.assertEqual(result, expected)

        # Should pass validation
        validators.validate_requirements(result)

    def test_count_with_tag_min_and_max(self):
        """Test count_with_tag with both minimum and maximum."""
        result = helpers.count_with_tag("charms", "martial_arts", minimum=1, maximum=5)

        expected = {
            "count_tag": {
                "model": "charms",
                "tag": "martial_arts",
                "minimum": 1,
                "maximum": 5,
            }
        }
        self.assertEqual(result, expected)

        # Should pass validation
        validators.validate_requirements(result)

    def test_count_with_tag_empty_model_invalid(self):
        """Test count_with_tag with empty model."""
        with self.assertRaises(ValidationError) as context:
            helpers.count_with_tag("", "elemental", minimum=2)

        error_msg = str(context.exception)
        self.assertIn("non-empty string", error_msg)

    def test_count_with_tag_whitespace_model_invalid(self):
        """Test count_with_tag with whitespace-only model."""
        with self.assertRaises(ValidationError) as context:
            helpers.count_with_tag("   ", "elemental", minimum=2)

        error_msg = str(context.exception)
        self.assertIn("non-empty string", error_msg)

    def test_count_with_tag_empty_tag_invalid(self):
        """Test count_with_tag with empty tag."""
        with self.assertRaises(ValidationError) as context:
            helpers.count_with_tag("spheres", "", minimum=2)

        error_msg = str(context.exception)
        self.assertIn("non-empty string", error_msg)

    def test_count_with_tag_whitespace_tag_invalid(self):
        """Test count_with_tag with whitespace-only tag."""
        with self.assertRaises(ValidationError) as context:
            helpers.count_with_tag("spheres", "   ", minimum=2)

        error_msg = str(context.exception)
        self.assertIn("non-empty string", error_msg)

    def test_count_with_tag_no_constraints_invalid(self):
        """Test count_with_tag with no constraints."""
        with self.assertRaises(ValidationError) as context:
            helpers.count_with_tag("spheres", "elemental")

        error_msg = str(context.exception)
        self.assertIn("At least one constraint", error_msg)

    def test_count_with_tag_negative_minimum_invalid(self):
        """Test count_with_tag with negative minimum."""
        with self.assertRaises(ValidationError) as context:
            helpers.count_with_tag("spheres", "elemental", minimum=-1)

        error_msg = str(context.exception)
        self.assertIn("non-negative integer", error_msg)

    def test_count_with_tag_invalid_minimum_type(self):
        """Test count_with_tag with invalid minimum type."""
        with self.assertRaises(ValidationError) as context:
            helpers.count_with_tag("spheres", "elemental", minimum="invalid")

        error_msg = str(context.exception)
        self.assertIn("non-negative integer", error_msg)

    def test_count_with_tag_negative_maximum_invalid(self):
        """Test count_with_tag with negative maximum."""
        with self.assertRaises(ValidationError) as context:
            helpers.count_with_tag("spheres", "elemental", maximum=-1)

        error_msg = str(context.exception)
        self.assertIn("non-negative integer", error_msg)

    def test_count_with_tag_invalid_maximum_type(self):
        """Test count_with_tag with invalid maximum type."""
        with self.assertRaises(ValidationError) as context:
            helpers.count_with_tag("spheres", "elemental", maximum="invalid")

        error_msg = str(context.exception)
        self.assertIn("non-negative integer", error_msg)

    def test_count_with_tag_trims_whitespace(self):
        """Test that model and tag whitespace is trimmed."""
        result = helpers.count_with_tag("  spheres  ", "  elemental  ", minimum=2)

        expected = {"count_tag": {"model": "spheres", "tag": "elemental", "minimum": 2}}
        self.assertEqual(result, expected)

    def test_count_with_tag_zero_values_valid(self):
        """Test count_with_tag with zero values."""
        result = helpers.count_with_tag("spheres", "elemental", minimum=0, maximum=0)

        expected = {
            "count_tag": {
                "model": "spheres",
                "tag": "elemental",
                "minimum": 0,
                "maximum": 0,
            }
        }
        self.assertEqual(result, expected)

        # Should pass validation
        validators.validate_requirements(result)


class NestedRequirementHelperTest(TestCase):
    """Test nested requirement combinations."""

    def test_complex_nested_requirements(self):
        """Test complex nested requirement combinations."""
        # Create a complex requirement:
        # (strength >= 4 OR dexterity >= 4) AND arete >= 3 AND
        # (has Crystal Orb OR elemental spheres >= 2)

        combat_req = helpers.any_of(
            helpers.trait_req("strength", minimum=4),
            helpers.trait_req("dexterity", minimum=4),
        )

        magic_req = helpers.any_of(
            helpers.has_item("foci", name="Crystal Orb"),
            helpers.count_with_tag("spheres", "elemental", minimum=2),
        )

        result = helpers.all_of(
            combat_req, helpers.trait_req("arete", minimum=3), magic_req
        )

        # Should pass validation
        validators.validate_requirements(result)

        # Check structure
        self.assertIn("all", result)
        self.assertEqual(len(result["all"]), 3)

    def test_deeply_nested_any_of_requirements(self):
        """Test deeply nested any_of requirements."""
        inner_req = helpers.any_of(
            helpers.trait_req("intelligence", minimum=3),
            helpers.has_item("backgrounds", name="mentor"),
        )

        middle_req = helpers.any_of(helpers.trait_req("arete", minimum=4), inner_req)

        result = helpers.any_of(helpers.trait_req("strength", minimum=5), middle_req)

        # Should pass validation
        validators.validate_requirements(result)

        # Check that it's properly nested
        self.assertIn("any", result)
        self.assertEqual(len(result["any"]), 2)

    def test_deeply_nested_all_of_requirements(self):
        """Test deeply nested all_of requirements."""
        inner_req = helpers.all_of(
            helpers.trait_req("intelligence", minimum=3),
            helpers.has_item("backgrounds", name="mentor"),
        )

        middle_req = helpers.all_of(helpers.trait_req("arete", minimum=3), inner_req)

        result = helpers.all_of(helpers.trait_req("strength", minimum=3), middle_req)

        # Should pass validation
        validators.validate_requirements(result)

        # Check that it's properly nested
        self.assertIn("all", result)
        self.assertEqual(len(result["all"]), 2)

    def test_mixed_nested_logical_operators(self):
        """Test mixed nested logical operators."""
        # Create requirement: all_of(trait, any_of(has_item1, has_item2), count_tag)
        result = helpers.all_of(
            helpers.trait_req("arete", minimum=3),
            helpers.any_of(
                helpers.has_item("foci", name="Crystal Orb"),
                helpers.has_item("foci", name="Silver Mirror"),
            ),
            helpers.count_with_tag("spheres", "elemental", minimum=1),
        )

        # Should pass validation
        validators.validate_requirements(result)

        # Check structure
        self.assertIn("all", result)
        self.assertEqual(len(result["all"]), 3)

        # Check that middle requirement is any_of
        middle_req = result["all"][1]
        self.assertIn("any", middle_req)


class ConvenienceAliasTest(TestCase):
    """Test convenience aliases for the helper functions."""

    def test_trait_alias(self):
        """Test trait alias for trait_req."""
        result1 = helpers.trait("strength", minimum=3)
        result2 = helpers.trait_req("strength", minimum=3)

        self.assertEqual(result1, result2)

    def test_has_alias(self):
        """Test has alias for has_item."""
        result1 = helpers.has("weapons", id=123)
        result2 = helpers.has_item("weapons", id=123)

        self.assertEqual(result1, result2)

    def test_any_requirement_alias(self):
        """Test any_requirement alias for any_of."""
        req1 = helpers.trait_req("strength", minimum=3)
        req2 = helpers.trait_req("dexterity", minimum=3)

        result1 = helpers.any_requirement(req1, req2)
        result2 = helpers.any_of(req1, req2)

        self.assertEqual(result1, result2)

    def test_all_requirement_alias(self):
        """Test all_requirement alias for all_of."""
        req1 = helpers.trait_req("arete", minimum=3)
        req2 = helpers.has_item("foci", name="Crystal Orb")

        result1 = helpers.all_requirement(req1, req2)
        result2 = helpers.all_of(req1, req2)

        self.assertEqual(result1, result2)

    def test_count_tag_alias(self):
        """Test count_tag alias for count_with_tag."""
        result1 = helpers.count_tag("spheres", "elemental", minimum=2)
        result2 = helpers.count_with_tag("spheres", "elemental", minimum=2)

        self.assertEqual(result1, result2)


class IntegrationWithValidatorsTest(TestCase):
    """Test integration with validators module."""

    def test_all_helper_outputs_pass_validation(self):
        """Test that all helper function outputs pass validation."""
        # Test various helper function outputs
        test_requirements = [
            helpers.trait_req("strength", minimum=3),
            helpers.trait_req("dexterity", minimum=2, maximum=5),
            helpers.trait_req("arete", exact=3),
            helpers.has_item("weapons", id=123),
            helpers.has_item("foci", name="Crystal Orb"),
            helpers.has_item("weapons", id=123, name="Magic Sword", level=2),
            helpers.count_with_tag("spheres", "elemental", minimum=2),
            helpers.count_with_tag("charms", "martial_arts", minimum=1, maximum=5),
            helpers.any_of(
                helpers.trait_req("strength", minimum=3),
                helpers.trait_req("dexterity", minimum=3),
            ),
            helpers.all_of(
                helpers.trait_req("arete", minimum=3),
                helpers.has_item("foci", name="Crystal Orb"),
            ),
        ]

        # All should pass validation
        for requirement in test_requirements:
            with self.subTest(requirement=requirement):
                try:
                    validators.validate_requirements(requirement)
                except ValidationError as e:
                    self.fail(
                        f"Helper generated invalid requirement: "
                        f"{requirement} - Error: {e}"
                    )

    def test_helper_validation_matches_validators_module(self):
        """Test that helper validation matches validators module validation."""
        # Test a requirement that should fail validation
        invalid_trait_data = {"name": "", "min": -1}  # Empty name, negative min

        # Both should raise ValidationError for the same reasons
        with self.assertRaises(ValidationError):
            helpers.trait_req("", minimum=-1)

        # Direct validator should also fail
        with self.assertRaises(ValidationError):
            validators.validate_trait_requirement(invalid_trait_data)

    def test_complex_requirement_validation_integration(self):
        """Test complex requirements pass full validation."""
        # Create the complex requirement from the issue example
        advanced_req = helpers.all_of(
            helpers.trait_req("arete", minimum=3),
            helpers.has_item("foci", name="Crystal Orb"),
            helpers.count_with_tag("spheres", "elemental", minimum=2),
        )

        # Should pass full validation
        validators.validate_requirements(advanced_req)

        # Test the structure is correct
        self.assertIn("all", advanced_req)
        self.assertEqual(len(advanced_req["all"]), 3)

        # Verify each sub-requirement
        sub_reqs = advanced_req["all"]
        self.assertIn("trait", sub_reqs[0])
        self.assertIn("has", sub_reqs[1])
        self.assertIn("count_tag", sub_reqs[2])


class EdgeCaseTest(TestCase):
    """Test edge cases and boundary conditions."""

    def test_unicode_in_helper_functions(self):
        """Test unicode characters in helper function parameters."""
        # Test unicode trait names
        result = helpers.trait_req("力量", minimum=3)  # Chinese characters
        validators.validate_requirements(result)

        # Test unicode field names
        result = helpers.has_item("武器", name="魔法剑")  # Chinese characters
        validators.validate_requirements(result)

        # Test unicode tags
        result = helpers.count_with_tag("球体", "元素", minimum=2)  # Chinese characters
        validators.validate_requirements(result)

    def test_very_long_strings_in_helpers(self):
        """Test very long strings in helper functions."""
        long_name = "a" * 1000

        # Should handle long strings gracefully
        try:
            result = helpers.trait_req(long_name, minimum=1)
            validators.validate_requirements(result)
        except ValidationError:
            # If there are length limits, that's acceptable
            pass

    def test_special_characters_in_helpers(self):
        """Test special characters in helper function parameters."""
        # Test special characters in names
        result = helpers.trait_req("strength-modified_v2.1", minimum=1)
        validators.validate_requirements(result)

        # Test special characters in field names
        result = helpers.has_item("weapons-and-armor", name="sword+1")
        validators.validate_requirements(result)

    def test_extreme_numeric_values_in_helpers(self):
        """Test extreme numeric values in helper functions."""
        # Test large numbers
        result = helpers.trait_req("test", minimum=1000000)
        validators.validate_requirements(result)

        # Test zero values
        result = helpers.count_with_tag("spheres", "elemental", minimum=0)
        validators.validate_requirements(result)

    def test_large_nested_structures(self):
        """Test large nested requirement structures."""
        # Create a wide any_of requirement
        req_list = []
        for i in range(50):
            req_list.append(helpers.trait_req(f"trait_{i}", minimum=1))

        result = helpers.any_of(req_list)
        validators.validate_requirements(result)

        # Should have 50 sub-requirements
        self.assertEqual(len(result["any"]), 50)

    def test_empty_string_handling(self):
        """Test empty string handling in helper functions."""
        # Empty strings should be handled gracefully in has_item name
        result = helpers.has_item("weapons", name="")
        validators.validate_requirements(result)

        # But empty field should fail
        with self.assertRaises(ValidationError):
            helpers.has_item("", id=123)


class UsabilityTest(TestCase):
    """Test usability and intuitive API design."""

    def test_helper_function_examples_from_docstrings(self):
        """Test that examples from docstrings work correctly."""
        # Examples from trait_req docstring
        result = helpers.trait_req("strength", minimum=3)
        expected = {"trait": {"name": "strength", "min": 3}}
        self.assertEqual(result, expected)

        result = helpers.trait_req("dexterity", minimum=2, maximum=5)
        expected = {"trait": {"name": "dexterity", "min": 2, "max": 5}}
        self.assertEqual(result, expected)

        result = helpers.trait_req("arete", exact=3)
        expected = {"trait": {"name": "arete", "exact": 3}}
        self.assertEqual(result, expected)

        # Examples from has_item docstring
        result = helpers.has_item("weapons", id=123)
        expected = {"has": {"field": "weapons", "id": 123}}
        self.assertEqual(result, expected)

        result = helpers.has_item("foci", name="Crystal Orb")
        expected = {"has": {"field": "foci", "name": "Crystal Orb"}}
        self.assertEqual(result, expected)

        # Examples from count_with_tag docstring
        result = helpers.count_with_tag("spheres", "elemental", minimum=2)
        expected = {"count_tag": {"model": "spheres", "tag": "elemental", "minimum": 2}}
        self.assertEqual(result, expected)

    def test_issue_example_requirements(self):
        """Test the examples from Issue #188."""
        # Simple trait requirement
        strength_req = helpers.trait_req("strength", minimum=3)
        self.assertEqual(strength_req, {"trait": {"name": "strength", "min": 3}})

        # Has item requirement
        sword_req = helpers.has_item("weapons", id=123, name="Magic Sword")
        expected_sword = {"has": {"field": "weapons", "id": 123, "name": "Magic Sword"}}
        self.assertEqual(sword_req, expected_sword)

        # Logical combinations
        combat_req = helpers.any_of(
            helpers.trait_req("strength", minimum=4),
            helpers.trait_req("dexterity", minimum=4),
        )
        self.assertIn("any", combat_req)
        self.assertEqual(len(combat_req["any"]), 2)

        # Complex requirements
        advanced_req = helpers.all_of(
            helpers.trait_req("arete", minimum=3),
            helpers.has_item("foci", name="Crystal Orb"),
            helpers.count_with_tag("spheres", "elemental", minimum=2),
        )
        self.assertIn("all", advanced_req)
        self.assertEqual(len(advanced_req["all"]), 3)

        # All should pass validation
        for req in [strength_req, sword_req, combat_req, advanced_req]:
            validators.validate_requirements(req)

    def test_parameter_names_are_intuitive(self):
        """Test that parameter names are intuitive and clear."""
        # trait_req uses 'minimum' and 'maximum' instead of 'min' and 'max'
        result = helpers.trait_req("strength", minimum=3, maximum=5)
        # But generates 'min' and 'max' in JSON for compatibility
        expected = {"trait": {"name": "strength", "min": 3, "max": 5}}
        self.assertEqual(result, expected)

        # count_with_tag uses 'minimum' and 'maximum' consistently
        result = helpers.count_with_tag("spheres", "elemental", minimum=2, maximum=5)
        expected = {
            "count_tag": {
                "model": "spheres",
                "tag": "elemental",
                "minimum": 2,
                "maximum": 5,
            }
        }
        self.assertEqual(result, expected)

    def test_error_messages_are_helpful(self):
        """Test that error messages are helpful and specific."""
        # Test trait_req error messages
        with self.assertRaises(ValidationError) as context:
            helpers.trait_req("")

        error_msg = str(context.exception)
        self.assertIn("non-empty string", error_msg)

        # Test has_item error messages
        with self.assertRaises(ValidationError) as context:
            helpers.has_item("weapons")

        error_msg = str(context.exception)
        self.assertIn("'id' or 'name'", error_msg)

        # Test any_of error messages
        with self.assertRaises(ValidationError) as context:
            helpers.any_of()

        error_msg = str(context.exception)
        self.assertIn("At least one requirement", error_msg)


class PerformanceTest(TestCase):
    """Test performance characteristics of helper functions."""

    def test_helper_function_performance_with_large_inputs(self):
        """Test helper functions with large inputs don't cause performance issues."""
        # Create a large any_of requirement (this is more of a smoke test)
        large_req_list = []
        for i in range(1000):
            large_req_list.append(helpers.trait_req(f"trait_{i}", minimum=1))

        # Should complete without timeout
        result = helpers.any_of(large_req_list)

        # Should have 1000 sub-requirements
        self.assertEqual(len(result["any"]), 1000)

        # Should pass validation (though this might be slow)
        validators.validate_requirements(result)

    def test_nested_requirement_performance(self):
        """Test performance with deeply nested requirements."""
        # Create a moderately deep nesting
        current_req = helpers.trait_req("base", minimum=1)

        for i in range(20):  # 20 levels deep
            current_req = helpers.any_of(
                current_req, helpers.trait_req(f"alt_{i}", minimum=1)
            )

        # Should complete and validate without performance issues
        validators.validate_requirements(current_req)

        # Should be properly nested
        self.assertIn("any", current_req)
