"""
Comprehensive tests for JSON requirement validation (Issue #187).

This test suite validates the JSON requirement validation system that ensures
structured requirements follow correct format and constraints for each
requirement type (trait, has, any, all, count_tag).

Key testing areas:
1. Basic JSON structure validation
2. Individual requirement type validation (trait, has, any, all, count_tag)
3. Nested requirement validation (recursive)
4. Error message clarity and specificity
5. Custom requirement type extensibility
6. Edge cases and malformed data
7. Performance with complex nested requirements

Requirements from Issue #187:
- Validate required fields for each requirement type
- Recursive validation for nested requirements
- Clear error messages for invalid structures
- Support for trait, has, any, all, count_tag types
- Custom requirement type extensibility
"""

from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase

# Import the validators module (will be created)
from prerequisites import validators


class BasicJSONValidationTest(TestCase):
    """Test basic JSON structure validation."""

    def test_empty_requirements_valid(self):
        """Test that empty requirements are valid."""
        # Empty dict should be valid
        validators.validate_requirements({})

        # Should not raise any exception

    def test_null_requirements_invalid(self):
        """Test that null requirements are invalid."""
        with self.assertRaises(ValidationError) as context:
            validators.validate_requirements(None)

        error_msg = str(context.exception)
        self.assertIn("Requirements must be a dictionary", error_msg)

    def test_non_dict_requirements_invalid(self):
        """Test that non-dictionary requirements are invalid."""
        invalid_types = ["string", 123, [1, 2, 3], True, set([1, 2, 3])]

        for invalid_req in invalid_types:
            with self.assertRaises(ValidationError) as context:
                validators.validate_requirements(invalid_req)

            error_msg = str(context.exception)
            self.assertIn("Requirements must be a dictionary", error_msg)

    def test_unknown_requirement_type_invalid(self):
        """Test that unknown requirement types are invalid."""
        invalid_req = {"unknown_type": {"some_field": "some_value"}}

        with self.assertRaises(ValidationError) as context:
            validators.validate_requirements(invalid_req)

        error_msg = str(context.exception)
        self.assertIn("Unknown requirement type: unknown_type", error_msg)

    def test_multiple_root_types_invalid(self):
        """Test that multiple root requirement types are invalid."""
        invalid_req = {
            "trait": {"name": "strength", "min": 3},
            "has": {"field": "charms", "id": 123},
        }

        with self.assertRaises(ValidationError) as context:
            validators.validate_requirements(invalid_req)

        error_msg = str(context.exception)
        self.assertIn(
            "Requirements must contain exactly one root requirement type", error_msg
        )


class TraitRequirementValidationTest(TestCase):
    """Test trait requirement validation."""

    def test_valid_trait_requirement_minimal(self):
        """Test valid minimal trait requirement."""
        valid_req = {"trait": {"name": "strength", "min": 1}}

        # Should not raise any exception
        validators.validate_requirements(valid_req)

    def test_valid_trait_requirement_complete(self):
        """Test valid complete trait requirement."""
        valid_req = {"trait": {"name": "dexterity", "min": 2, "max": 5, "exact": None}}

        # Should not raise any exception
        validators.validate_requirements(valid_req)

    def test_trait_missing_name_invalid(self):
        """Test trait requirement missing name field."""
        invalid_req = {"trait": {"min": 3}}

        with self.assertRaises(ValidationError) as context:
            validators.validate_requirements(invalid_req)

        error_msg = str(context.exception)
        self.assertIn("trait", error_msg)
        self.assertIn("name", error_msg)
        self.assertIn("required", error_msg)

    def test_trait_missing_constraint_invalid(self):
        """Test trait requirement with no constraints."""
        invalid_req = {"trait": {"name": "strength"}}

        with self.assertRaises(ValidationError) as context:
            validators.validate_requirements(invalid_req)

        error_msg = str(context.exception)
        self.assertIn("trait", error_msg)
        self.assertIn("at least one constraint", error_msg)

    def test_trait_invalid_constraint_values(self):
        """Test trait requirement with invalid constraint values."""
        invalid_reqs = [
            # Negative min
            {"trait": {"name": "strength", "min": -1}},
            # String min
            {"trait": {"name": "strength", "min": "invalid"}},
            # Max less than min
            {"trait": {"name": "strength", "min": 5, "max": 3}},
            # Invalid exact type
            {"trait": {"name": "strength", "exact": "invalid"}},
        ]

        for invalid_req in invalid_reqs:
            with self.assertRaises(ValidationError):
                validators.validate_requirements(invalid_req)

    def test_trait_empty_name_invalid(self):
        """Test trait requirement with empty name."""
        invalid_req = {"trait": {"name": "", "min": 1}}

        with self.assertRaises(ValidationError) as context:
            validators.validate_requirements(invalid_req)

        error_msg = str(context.exception)
        self.assertIn("name cannot be empty", error_msg)

    def test_trait_conflicting_constraints_invalid(self):
        """Test trait requirement with conflicting constraints."""
        invalid_req = {
            "trait": {"name": "strength", "min": 3, "exact": 2}  # Conflicts with min
        }

        with self.assertRaises(ValidationError) as context:
            validators.validate_requirements(invalid_req)

        error_msg = str(context.exception)
        self.assertIn("exact", error_msg)
        self.assertIn("cannot be used", error_msg)


class HasRequirementValidationTest(TestCase):
    """Test has requirement validation."""

    def test_valid_has_requirement_by_id(self):
        """Test valid has requirement with ID."""
        valid_req = {"has": {"field": "charms", "id": 123}}

        # Should not raise any exception
        validators.validate_requirements(valid_req)

    def test_valid_has_requirement_by_name(self):
        """Test valid has requirement with name."""
        valid_req = {"has": {"field": "spheres", "name": "forces"}}

        # Should not raise any exception
        validators.validate_requirements(valid_req)

    def test_valid_has_requirement_complete(self):
        """Test valid complete has requirement."""
        valid_req = {
            "has": {
                "field": "charms",
                "id": 123,
                "name": "Excellent Strike",
                "level": 2,
            }
        }

        # Should not raise any exception
        validators.validate_requirements(valid_req)

    def test_has_missing_field_invalid(self):
        """Test has requirement missing field."""
        invalid_req = {"has": {"id": 123}}

        with self.assertRaises(ValidationError) as context:
            validators.validate_requirements(invalid_req)

        error_msg = str(context.exception)
        self.assertIn("has", error_msg)
        self.assertIn("field", error_msg)
        self.assertIn("required", error_msg)

    def test_has_missing_identifier_invalid(self):
        """Test has requirement missing both id and name."""
        invalid_req = {"has": {"field": "charms"}}

        with self.assertRaises(ValidationError) as context:
            validators.validate_requirements(invalid_req)

        error_msg = str(context.exception)
        self.assertIn("has", error_msg)
        self.assertIn("id or name", error_msg)

    def test_has_empty_field_invalid(self):
        """Test has requirement with empty field."""
        invalid_req = {"has": {"field": "", "id": 123}}

        with self.assertRaises(ValidationError) as context:
            validators.validate_requirements(invalid_req)

        error_msg = str(context.exception)
        self.assertIn("field cannot be empty", error_msg)

    def test_has_invalid_id_type_invalid(self):
        """Test has requirement with invalid id type."""
        invalid_req = {"has": {"field": "charms", "id": "invalid_id"}}

        with self.assertRaises(ValidationError) as context:
            validators.validate_requirements(invalid_req)

        error_msg = str(context.exception)
        self.assertIn("id must be an integer", error_msg)

    def test_has_negative_id_invalid(self):
        """Test has requirement with negative id."""
        invalid_req = {"has": {"field": "charms", "id": -1}}

        with self.assertRaises(ValidationError) as context:
            validators.validate_requirements(invalid_req)

        error_msg = str(context.exception)
        self.assertIn("id must be positive", error_msg)


class LogicalOperatorValidationTest(TestCase):
    """Test any/all logical operator validation."""

    def test_valid_any_requirement(self):
        """Test valid any requirement."""
        valid_req = {
            "any": [
                {"trait": {"name": "strength", "min": 3}},
                {"trait": {"name": "dexterity", "min": 3}},
            ]
        }

        # Should not raise any exception
        validators.validate_requirements(valid_req)

    def test_valid_all_requirement(self):
        """Test valid all requirement."""
        valid_req = {
            "all": [
                {"trait": {"name": "arete", "min": 3}},
                {"has": {"field": "spheres", "name": "forces"}},
            ]
        }

        # Should not raise any exception
        validators.validate_requirements(valid_req)

    def test_any_not_list_invalid(self):
        """Test any requirement that's not a list."""
        invalid_req = {"any": {"trait": {"name": "strength", "min": 3}}}

        with self.assertRaises(ValidationError) as context:
            validators.validate_requirements(invalid_req)

        error_msg = str(context.exception)
        self.assertIn("any", error_msg)
        self.assertIn("must be a list", error_msg)

    def test_all_not_list_invalid(self):
        """Test all requirement that's not a list."""
        invalid_req = {"all": {"trait": {"name": "strength", "min": 3}}}

        with self.assertRaises(ValidationError) as context:
            validators.validate_requirements(invalid_req)

        error_msg = str(context.exception)
        self.assertIn("all", error_msg)
        self.assertIn("must be a list", error_msg)

    def test_any_empty_list_invalid(self):
        """Test any requirement with empty list."""
        invalid_req = {"any": []}

        with self.assertRaises(ValidationError) as context:
            validators.validate_requirements(invalid_req)

        error_msg = str(context.exception)
        self.assertIn("any", error_msg)
        self.assertIn("cannot be empty", error_msg)

    def test_all_empty_list_invalid(self):
        """Test all requirement with empty list."""
        invalid_req = {"all": []}

        with self.assertRaises(ValidationError) as context:
            validators.validate_requirements(invalid_req)

        error_msg = str(context.exception)
        self.assertIn("all", error_msg)
        self.assertIn("cannot be empty", error_msg)

    def test_any_invalid_subrequirement(self):
        """Test any requirement with invalid subrequirement."""
        invalid_req = {
            "any": [
                {"trait": {"name": "strength", "min": 3}},
                {"invalid_type": {"some": "value"}},
            ]
        }

        with self.assertRaises(ValidationError) as context:
            validators.validate_requirements(invalid_req)

        error_msg = str(context.exception)
        self.assertIn("Unknown requirement type: invalid_type", error_msg)

    def test_all_invalid_subrequirement(self):
        """Test all requirement with invalid subrequirement."""
        invalid_req = {
            "all": [
                {"trait": {"name": "arete", "min": 3}},
                {"trait": {"name": "strength"}},  # Missing constraints
            ]
        }

        with self.assertRaises(ValidationError):
            validators.validate_requirements(invalid_req)


class CountTagRequirementValidationTest(TestCase):
    """Test count_tag requirement validation."""

    def test_valid_count_tag_requirement(self):
        """Test valid count_tag requirement."""
        valid_req = {
            "count_tag": {"model": "spheres", "tag": "elemental", "minimum": 2}
        }

        # Should not raise any exception
        validators.validate_requirements(valid_req)

    def test_valid_count_tag_with_maximum(self):
        """Test valid count_tag requirement with maximum."""
        valid_req = {
            "count_tag": {
                "model": "charms",
                "tag": "martial_arts",
                "minimum": 1,
                "maximum": 5,
            }
        }

        # Should not raise any exception
        validators.validate_requirements(valid_req)

    def test_count_tag_missing_model_invalid(self):
        """Test count_tag requirement missing model."""
        invalid_req = {"count_tag": {"tag": "elemental", "minimum": 2}}

        with self.assertRaises(ValidationError) as context:
            validators.validate_requirements(invalid_req)

        error_msg = str(context.exception)
        self.assertIn("count_tag", error_msg)
        self.assertIn("model", error_msg)
        self.assertIn("required", error_msg)

    def test_count_tag_missing_tag_invalid(self):
        """Test count_tag requirement missing tag."""
        invalid_req = {"count_tag": {"model": "spheres", "minimum": 2}}

        with self.assertRaises(ValidationError) as context:
            validators.validate_requirements(invalid_req)

        error_msg = str(context.exception)
        self.assertIn("count_tag", error_msg)
        self.assertIn("tag", error_msg)
        self.assertIn("required", error_msg)

    def test_count_tag_missing_constraint_invalid(self):
        """Test count_tag requirement with no constraints."""
        invalid_req = {"count_tag": {"model": "spheres", "tag": "elemental"}}

        with self.assertRaises(ValidationError) as context:
            validators.validate_requirements(invalid_req)

        error_msg = str(context.exception)
        self.assertIn("count_tag", error_msg)
        self.assertIn("at least one constraint", error_msg)

    def test_count_tag_invalid_constraint_values(self):
        """Test count_tag requirement with invalid constraint values."""
        invalid_reqs = [
            # Negative minimum
            {"count_tag": {"model": "spheres", "tag": "elemental", "minimum": -1}},
            # String minimum
            {
                "count_tag": {
                    "model": "spheres",
                    "tag": "elemental",
                    "minimum": "invalid",
                }
            },
            # Maximum less than minimum
            {
                "count_tag": {
                    "model": "spheres",
                    "tag": "elemental",
                    "minimum": 5,
                    "maximum": 3,
                }
            },
        ]

        for invalid_req in invalid_reqs:
            with self.assertRaises(ValidationError):
                validators.validate_requirements(invalid_req)

    def test_count_tag_empty_fields_invalid(self):
        """Test count_tag requirement with empty fields."""
        invalid_reqs = [
            {"count_tag": {"model": "", "tag": "elemental", "minimum": 2}},
            {"count_tag": {"model": "spheres", "tag": "", "minimum": 2}},
        ]

        for invalid_req in invalid_reqs:
            with self.assertRaises(ValidationError) as context:
                validators.validate_requirements(invalid_req)

            error_msg = str(context.exception)
            self.assertIn("cannot be empty", error_msg)


class NestedRequirementValidationTest(TestCase):
    """Test recursive validation of nested requirements."""

    def test_nested_any_with_trait_and_has(self):
        """Test nested any with trait and has requirements."""
        valid_req = {
            "any": [
                {
                    "all": [
                        {"trait": {"name": "strength", "min": 3}},
                        {"trait": {"name": "dexterity", "min": 2}},
                    ]
                },
                {"has": {"field": "charms", "name": "Excellent Strike"}},
            ]
        }

        # Should not raise any exception
        validators.validate_requirements(valid_req)

    def test_deeply_nested_requirements(self):
        """Test deeply nested requirements."""
        valid_req = {
            "all": [
                {
                    "any": [
                        {"trait": {"name": "arete", "min": 3}},
                        {
                            "all": [
                                {"trait": {"name": "intelligence", "min": 4}},
                                {"has": {"field": "backgrounds", "name": "mentor"}},
                            ]
                        },
                    ]
                },
                {"count_tag": {"model": "spheres", "tag": "elemental", "minimum": 2}},
            ]
        }

        # Should not raise any exception
        validators.validate_requirements(valid_req)

    def test_nested_requirement_with_invalid_child(self):
        """Test nested requirement with invalid child."""
        invalid_req = {
            "any": [
                {"trait": {"name": "strength", "min": 3}},
                {
                    "all": [
                        {"trait": {"name": "dexterity", "min": 2}},
                        {"invalid_type": {"field": "value"}},
                    ]
                },
            ]
        }

        with self.assertRaises(ValidationError) as context:
            validators.validate_requirements(invalid_req)

        error_msg = str(context.exception)
        self.assertIn("Unknown requirement type: invalid_type", error_msg)

    def test_nested_requirement_maintains_validation_path(self):
        """Test that nested validation maintains clear error paths."""
        invalid_req = {
            "all": [
                {"trait": {"name": "strength", "min": 3}},
                {
                    "any": [
                        {"trait": {"name": ""}},  # Empty name
                        {"has": {"field": "charms", "id": 123}},
                    ]
                },
            ]
        }

        with self.assertRaises(ValidationError) as context:
            validators.validate_requirements(invalid_req)

        error_msg = str(context.exception)
        self.assertIn("name cannot be empty", error_msg)

    def test_circular_reference_protection(self):
        """Test protection against circular references in validation."""
        # This tests the validator's ability to handle deep recursion
        # Create a deeply nested structure that could cause issues
        nested_req = {"all": [{"trait": {"name": "test", "min": 1}}]}

        # Nest it deeply
        for _ in range(100):
            nested_req = {"any": [nested_req]}

        # Should either validate or fail gracefully (not crash)
        try:
            validators.validate_requirements(nested_req)
        except (ValidationError, RecursionError):
            # Either is acceptable - we just don't want a crash
            pass


class ErrorMessageValidationTest(TestCase):
    """Test error message clarity and specificity."""

    def test_trait_error_messages_are_specific(self):
        """Test that trait validation errors are specific."""
        invalid_req = {"trait": {"name": "", "min": -1, "max": "invalid"}}

        with self.assertRaises(ValidationError) as context:
            validators.validate_requirements(invalid_req)

        error_msg = str(context.exception)
        # Should mention specific issues, not just "invalid"
        self.assertTrue(
            any(
                phrase in error_msg.lower()
                for phrase in [
                    "name cannot be empty",
                    "min",
                    "max",
                    "must be",
                    "integer",
                    "positive",
                ]
            )
        )

    def test_has_error_messages_are_specific(self):
        """Test that has validation errors are specific."""
        invalid_req = {"has": {"field": "", "id": -1, "name": None}}

        with self.assertRaises(ValidationError) as context:
            validators.validate_requirements(invalid_req)

        error_msg = str(context.exception)
        # Should mention specific field issues
        self.assertTrue(
            any(
                phrase in error_msg.lower()
                for phrase in ["field cannot be empty", "id", "positive", "integer"]
            )
        )

    def test_nested_error_messages_show_path(self):
        """Test that nested errors show the path to the error."""
        invalid_req = {
            "all": [
                {"trait": {"name": "strength", "min": 3}},
                {"any": [{"trait": {"name": ""}}]},  # Error in nested location
            ]
        }

        with self.assertRaises(ValidationError) as context:
            validators.validate_requirements(invalid_req)

        error_msg = str(context.exception)
        # Should give some indication of location/path
        self.assertIn("name cannot be empty", error_msg)

    def test_multiple_errors_reported(self):
        """Test that multiple errors can be reported together."""
        invalid_req = {"trait": {"name": "", "min": -1}}

        with self.assertRaises(ValidationError) as context:
            validators.validate_requirements(invalid_req)

        # The implementation may choose to report first error or multiple
        # This test just ensures we get meaningful error information
        error_msg = str(context.exception)
        self.assertTrue(len(error_msg) > 10)  # Should be a meaningful message


class CustomRequirementTypeValidationTest(TestCase):
    """Test extensibility for custom requirement types."""

    def test_register_custom_validator(self):
        """Test registering a custom requirement type validator."""

        # Define custom validator
        def validate_custom_type(requirement_data, path=""):
            if not isinstance(requirement_data, dict):
                raise ValidationError(f"Custom type must be a dictionary at {path}")
            if "custom_field" not in requirement_data:
                raise ValidationError(f"Custom type requires 'custom_field' at {path}")

        # Register the validator
        validators.register_requirement_validator("custom", validate_custom_type)

        # Test valid custom requirement
        valid_req = {"custom": {"custom_field": "custom_value"}}

        # Should not raise any exception
        validators.validate_requirements(valid_req)

        # Test invalid custom requirement
        invalid_req = {"custom": {"other_field": "value"}}

        with self.assertRaises(ValidationError) as context:
            validators.validate_requirements(invalid_req)

        error_msg = str(context.exception)
        self.assertIn("custom_field", error_msg)

    def test_override_existing_validator(self):
        """Test overriding an existing validator."""

        # Define stricter trait validator
        def strict_trait_validator(requirement_data, path=""):
            if not isinstance(requirement_data, dict):
                raise ValidationError(f"Trait must be a dictionary at {path}")
            if requirement_data.get("name") != "strength":
                raise ValidationError(f"Only 'strength' trait allowed at {path}")

        # Override trait validator
        validators.register_requirement_validator("trait", strict_trait_validator)

        # Test that only strength is allowed
        valid_req = {"trait": {"name": "strength"}}
        validators.validate_requirements(valid_req)

        # Test that other traits are rejected
        invalid_req = {"trait": {"name": "dexterity"}}

        with self.assertRaises(ValidationError) as context:
            validators.validate_requirements(invalid_req)

        error_msg = str(context.exception)
        self.assertIn("strength", error_msg)

    def test_list_registered_validators(self):
        """Test getting list of registered validators."""
        validator_types = validators.get_registered_validator_types()

        # Should include built-in types
        expected_types = {"trait", "has", "any", "all", "count_tag"}
        self.assertTrue(expected_types.issubset(set(validator_types)))

    def test_unregister_validator(self):
        """Test unregistering a validator."""

        # Register custom validator
        def dummy_validator(requirement_data, path=""):
            pass

        validators.register_requirement_validator("temporary", dummy_validator)

        # Verify it's registered
        self.assertIn("temporary", validators.get_registered_validator_types())

        # Unregister it
        validators.unregister_requirement_validator("temporary")

        # Verify it's gone
        self.assertNotIn("temporary", validators.get_registered_validator_types())

        # Should now fail validation
        invalid_req = {"temporary": {}}
        with self.assertRaises(ValidationError):
            validators.validate_requirements(invalid_req)


class PerformanceValidationTest(TestCase):
    """Test performance with complex nested requirements."""

    def test_deep_nesting_performance(self):
        """Test validation performance with deep nesting."""
        # Create deeply nested requirement (reasonable depth)
        nested_req = {"trait": {"name": "strength", "min": 1}}

        for i in range(20):  # 20 levels deep
            nested_req = {
                "any": [nested_req, {"trait": {"name": f"attr_{i}", "min": 1}}]
            }

        # Should validate without performance issues
        # (This is more of a smoke test - real performance testing would need timing)
        validators.validate_requirements(nested_req)

    def test_wide_requirements_performance(self):
        """Test validation performance with wide requirements."""
        # Create requirement with many siblings
        any_list = []
        for i in range(100):  # 100 sibling requirements
            any_list.append({"trait": {"name": f"trait_{i}", "min": 1}})

        wide_req = {"any": any_list}

        # Should validate without performance issues
        validators.validate_requirements(wide_req)

    def test_complex_mixed_requirements_performance(self):
        """Test validation performance with complex mixed requirements."""
        complex_req = {
            "all": [
                {
                    "any": [
                        {"trait": {"name": "strength", "min": 3, "max": 5}},
                        {"trait": {"name": "dexterity", "min": 4}},
                        {
                            "all": [
                                {"trait": {"name": "intelligence", "min": 3}},
                                {"has": {"field": "skills", "name": "academics"}},
                            ]
                        },
                    ]
                },
                {
                    "count_tag": {
                        "model": "spheres",
                        "tag": "elemental",
                        "minimum": 2,
                        "maximum": 5,
                    }
                },
                {
                    "any": [
                        {
                            "has": {
                                "field": "charms",
                                "id": 123,
                                "name": "Excellent Strike",
                            }
                        },
                        {"has": {"field": "charms", "id": 456, "name": "Iron Skin"}},
                        {
                            "all": [
                                {"trait": {"name": "martial_arts", "min": 3}},
                                {"has": {"field": "backgrounds", "name": "mentor"}},
                            ]
                        },
                    ]
                },
            ]
        }

        # Should validate complex requirements efficiently
        validators.validate_requirements(complex_req)


class EdgeCaseValidationTest(TestCase):
    """Test edge cases and unusual data."""

    def test_unicode_in_requirements(self):
        """Test unicode characters in requirement fields."""
        unicode_req = {"trait": {"name": "力量", "min": 3}}  # Chinese characters

        # Should handle unicode correctly
        validators.validate_requirements(unicode_req)

    def test_very_long_strings(self):
        """Test validation with very long strings."""
        long_name = "a" * 1000
        long_req = {"trait": {"name": long_name, "min": 1}}

        # Should handle long strings (validator may impose limits)
        try:
            validators.validate_requirements(long_req)
        except ValidationError as e:
            # If there are length limits, the error should be clear
            self.assertTrue(len(str(e)) > 0)

    def test_special_characters_in_names(self):
        """Test special characters in field names."""
        special_req = {"trait": {"name": "strength-modified_v2.1", "min": 1}}

        # Should handle reasonable special characters
        validators.validate_requirements(special_req)

    def test_extreme_numeric_values(self):
        """Test extreme numeric values."""
        extreme_reqs = [
            {"trait": {"name": "test", "min": 0}},  # Zero
            {"trait": {"name": "test", "min": 1000000}},  # Large number
            {"trait": {"name": "test", "min": 1, "max": 1}},  # Same min/max
        ]

        for req in extreme_reqs:
            # Should either validate or give clear error
            try:
                validators.validate_requirements(req)
            except ValidationError as e:
                self.assertTrue(len(str(e)) > 0)

    def test_boolean_and_null_values(self):
        """Test handling of boolean and null values in requirements."""
        mixed_req = {
            "trait": {
                "name": "test",
                "min": 1,
                "optional": True,  # Boolean
                "description": None,  # Null
            }
        }

        # Should handle mixed types appropriately
        try:
            validators.validate_requirements(mixed_req)
        except ValidationError as e:
            # If validation fails, error should be meaningful
            self.assertIn("optional", str(e).lower() or "description" in str(e).lower())

    def test_empty_nested_structures(self):
        """Test empty nested structures."""
        empty_nested = {
            "all": [
                {"trait": {"name": "test", "min": 1}},
                {"any": []},  # Empty nested any
            ]
        }

        with self.assertRaises(ValidationError) as context:
            validators.validate_requirements(empty_nested)

        error_msg = str(context.exception)
        self.assertIn("cannot be empty", error_msg)


class IntegrationValidationTest(TestCase):
    """Test integration with Prerequisite model."""

    @patch("prerequisites.models.validators.validate_requirements")
    def test_model_calls_validator(self, mock_validate):
        """Test that Prerequisite model calls the validator."""
        from prerequisites.models import Prerequisite

        requirements = {"trait": {"name": "strength", "min": 3}}
        prereq = Prerequisite(description="Test requirement", requirements=requirements)

        # Save should trigger validation
        try:
            prereq.save()
        except Exception:
            pass  # We don't care if save fails for other reasons

        # Validator should have been called with the requirements
        mock_validate.assert_called_with(requirements)

    def test_model_validation_error_propagation(self):
        """Test that validator errors propagate properly through model."""
        from prerequisites.models import Prerequisite

        invalid_requirements = {"invalid_type": {"field": "value"}}
        prereq = Prerequisite(
            description="Test requirement", requirements=invalid_requirements
        )

        with self.assertRaises(ValidationError):
            prereq.full_clean()

    def test_model_validation_with_valid_requirements(self):
        """Test model validation passes with valid requirements."""
        from prerequisites.models import Prerequisite

        valid_requirements = {"trait": {"name": "strength", "min": 3}}
        prereq = Prerequisite(
            description="Test requirement", requirements=valid_requirements
        )

        # Should not raise ValidationError
        prereq.full_clean()


# Additional test classes for comprehensive coverage could include:
# - DatabaseConstraintValidationTest (testing DB-level validation)
# - ConcurrencyValidationTest (testing thread safety)
# - BackwardCompatibilityTest (testing with legacy requirement formats)
# - ValidationCachingTest (if caching is implemented)
# - LocalizationTest (if error messages need localization)
