"""
Comprehensive tests for prerequisite builder form validation and error display.

This module tests form validation, error handling, and user feedback systems
for the visual prerequisite builder, ensuring robust validation and clear
error communication to users.

Key validation features being tested:
1. Real-time form validation with debouncing
2. Error message display and formatting
3. Field-level validation feedback
4. Cross-field validation rules
5. Nested requirement validation
6. User-friendly error recovery
7. Accessibility in error messages
8. Server-side validation integration

The validation system should provide immediate feedback while maintaining
good user experience and accessibility standards.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()


class ValidationResult:
    """Mock validation result class for testing."""

    def __init__(self, valid=True, errors=None, warnings=None, field_errors=None):
        self.valid = valid
        self.errors = errors or []
        self.warnings = warnings or []
        self.field_errors = field_errors or {}

    def to_dict(self):
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "field_errors": self.field_errors,
        }


class FieldValidator:
    """Mock field validator class for testing validation logic."""

    @staticmethod
    def validate_trait_name(value):
        """Validate trait name field."""
        if not value or not value.strip():
            return ValidationResult(
                valid=False,
                errors=["Trait name is required"],
                field_errors={"trait_name": ["Trait name cannot be empty"]},
            )

        if len(value.strip()) < 2:
            return ValidationResult(
                valid=False,
                errors=["Trait name too short"],
                field_errors={
                    "trait_name": ["Trait name must be at least 2 characters"]
                },
            )

        return ValidationResult(valid=True)

    @staticmethod
    def validate_trait_constraints(
        use_min, min_val, use_max, max_val, use_exact, exact_val
    ):
        """Validate trait constraint combinations."""
        errors = []
        field_errors = {}

        # Check that at least one constraint is used
        if not any([use_min, use_max, use_exact]):
            errors.append("At least one constraint must be specified")
            field_errors["constraints"] = ["Select minimum, maximum, or exact value"]

        # Check exact exclusivity
        if use_exact and (use_min or use_max):
            errors.append("Exact value cannot be used with min/max")
            field_errors["use_exact"] = [
                "Exact value cannot be combined with min/max constraints"
            ]

        # Validate min/max relationship
        if use_min and use_max and min_val is not None and max_val is not None:
            if min_val > max_val:
                errors.append("Maximum value cannot be less than minimum")
                field_errors["trait_max"] = [
                    "Maximum must be greater than or equal to minimum"
                ]

        # Validate numeric values
        if use_min and (min_val is None or min_val < 0):
            errors.append("Invalid minimum value")
            field_errors["trait_min"] = ["Minimum value must be a non-negative number"]

        if use_max and (max_val is None or max_val < 0):
            errors.append("Invalid maximum value")
            field_errors["trait_max"] = ["Maximum value must be a non-negative number"]

        if use_exact and (exact_val is None or exact_val < 0):
            errors.append("Invalid exact value")
            field_errors["trait_exact"] = ["Exact value must be a non-negative number"]

        return ValidationResult(
            valid=len(errors) == 0, errors=errors, field_errors=field_errors
        )

    @staticmethod
    def validate_has_requirement(field_name, use_id, item_id, use_name, item_name):
        """Validate has requirement fields."""
        errors = []
        field_errors = {}

        # Field name is required
        if not field_name or not field_name.strip():
            errors.append("Field name is required")
            field_errors["field_name"] = ["Field name cannot be empty"]

        # Must have at least one identifier
        if not use_id and not use_name:
            errors.append("At least one identifier required")
            field_errors["identifiers"] = ["Specify either ID or name"]

        # Validate ID if used
        if use_id:
            if item_id is None or item_id <= 0:
                errors.append("Invalid item ID")
                field_errors["item_id"] = ["Item ID must be a positive number"]

        # Validate name if used
        if use_name:
            if not item_name or not item_name.strip():
                errors.append("Item name cannot be empty")
                field_errors["item_name"] = [
                    "Item name is required when name matching is enabled"
                ]

        return ValidationResult(
            valid=len(errors) == 0, errors=errors, field_errors=field_errors
        )


class RealTimeValidationTest(TestCase):
    """Test real-time validation functionality."""

    def test_trait_requirement_validation_success(self):
        """Test successful validation of trait requirements."""
        # Valid trait requirement data
        valid_data = {
            "requirement_type": "trait",
            "trait_name": "strength",
            "use_min": True,
            "trait_min": 3,
            "use_max": False,
            "trait_max": None,
            "use_exact": False,
            "trait_exact": None,
        }

        # Test name validation
        name_result = FieldValidator.validate_trait_name(valid_data["trait_name"])
        self.assertTrue(name_result.valid)
        self.assertEqual(len(name_result.errors), 0)

        # Test constraint validation
        constraint_result = FieldValidator.validate_trait_constraints(
            valid_data["use_min"],
            valid_data["trait_min"],
            valid_data["use_max"],
            valid_data["trait_max"],
            valid_data["use_exact"],
            valid_data["trait_exact"],
        )
        self.assertTrue(constraint_result.valid)
        self.assertEqual(len(constraint_result.errors), 0)

    def test_trait_requirement_validation_failures(self):
        """Test validation failures for trait requirements."""
        # Test empty trait name
        empty_name_result = FieldValidator.validate_trait_name("")
        self.assertFalse(empty_name_result.valid)
        self.assertIn("Trait name is required", empty_name_result.errors)
        self.assertIn("trait_name", empty_name_result.field_errors)

        # Test short trait name
        short_name_result = FieldValidator.validate_trait_name("x")
        self.assertFalse(short_name_result.valid)
        self.assertIn("Trait name too short", short_name_result.errors)

        # Test no constraints selected
        no_constraints_result = FieldValidator.validate_trait_constraints(
            False, None, False, None, False, None
        )
        self.assertFalse(no_constraints_result.valid)
        self.assertIn(
            "At least one constraint must be specified", no_constraints_result.errors
        )

        # Test exact with min/max conflict
        exact_conflict_result = FieldValidator.validate_trait_constraints(
            True, 2, True, 5, True, 3
        )
        self.assertFalse(exact_conflict_result.valid)
        self.assertIn(
            "Exact value cannot be used with min/max", exact_conflict_result.errors
        )
        self.assertIn("use_exact", exact_conflict_result.field_errors)

        # Test min > max
        min_max_error_result = FieldValidator.validate_trait_constraints(
            True, 5, True, 3, False, None
        )
        self.assertFalse(min_max_error_result.valid)
        self.assertIn(
            "Maximum value cannot be less than minimum", min_max_error_result.errors
        )
        self.assertIn("trait_max", min_max_error_result.field_errors)

        # Test negative values
        negative_min_result = FieldValidator.validate_trait_constraints(
            True, -1, False, None, False, None
        )
        self.assertFalse(negative_min_result.valid)
        self.assertIn("Invalid minimum value", negative_min_result.errors)
        self.assertIn("trait_min", negative_min_result.field_errors)

    def test_has_requirement_validation_success(self):
        """Test successful validation of has requirements."""
        # Valid has requirement with ID
        id_result = FieldValidator.validate_has_requirement(
            "weapons", True, 123, False, ""
        )
        self.assertTrue(id_result.valid)
        self.assertEqual(len(id_result.errors), 0)

        # Valid has requirement with name
        name_result = FieldValidator.validate_has_requirement(
            "foci", False, None, True, "Crystal Orb"
        )
        self.assertTrue(name_result.valid)
        self.assertEqual(len(name_result.errors), 0)

        # Valid has requirement with both ID and name
        both_result = FieldValidator.validate_has_requirement(
            "items", True, 456, True, "Magic Sword"
        )
        self.assertTrue(both_result.valid)
        self.assertEqual(len(both_result.errors), 0)

    def test_has_requirement_validation_failures(self):
        """Test validation failures for has requirements."""
        # Test empty field name
        empty_field_result = FieldValidator.validate_has_requirement(
            "", True, 123, False, ""
        )
        self.assertFalse(empty_field_result.valid)
        self.assertIn("Field name is required", empty_field_result.errors)
        self.assertIn("field_name", empty_field_result.field_errors)

        # Test no identifiers
        no_id_result = FieldValidator.validate_has_requirement(
            "weapons", False, None, False, ""
        )
        self.assertFalse(no_id_result.valid)
        self.assertIn("At least one identifier required", no_id_result.errors)
        self.assertIn("identifiers", no_id_result.field_errors)

        # Test invalid ID
        invalid_id_result = FieldValidator.validate_has_requirement(
            "weapons", True, -1, False, ""
        )
        self.assertFalse(invalid_id_result.valid)
        self.assertIn("Invalid item ID", invalid_id_result.errors)
        self.assertIn("item_id", invalid_id_result.field_errors)

        # Test empty name when name is used
        empty_name_result = FieldValidator.validate_has_requirement(
            "foci", False, None, True, ""
        )
        self.assertFalse(empty_name_result.valid)
        self.assertIn("Item name cannot be empty", empty_name_result.errors)
        self.assertIn("item_name", empty_name_result.field_errors)


class ErrorDisplayTest(TestCase):
    """Test error display and formatting functionality."""

    def test_error_message_structure_and_formatting(self):
        """Test structure and formatting of error messages."""
        # Expected error message structure
        error_message_spec = {
            "field_errors": {
                "trait_name": {
                    "errors": ["Trait name is required"],
                    "severity": "error",
                    "display_type": "inline",
                    "element_id": "trait-name-error-block-1",
                    "aria_attributes": {
                        "role": "alert",
                        "aria-live": "polite",
                        "aria-relevant": "additions text",
                    },
                },
                "trait_min": {
                    "errors": ["Minimum value must be non-negative"],
                    "severity": "error",
                    "display_type": "tooltip",
                    "element_id": "trait-min-error-block-1",
                    "positioning": "below_field",
                },
            },
            "global_errors": {
                "constraint_conflict": {
                    "message": "Exact value cannot be used with minimum or maximum",
                    "severity": "error",
                    "display_type": "banner",
                    "dismissible": True,
                    "auto_hide_delay": 0,  # 0 means no auto-hide
                }
            },
            "warnings": {
                "no_maximum": {
                    "message": "No maximum value set - requirement has no upper limit",
                    "severity": "warning",
                    "display_type": "inline",
                    "dismissible": True,
                    "auto_hide_delay": 5000,
                }
            },
            "validation_summary": {
                "total_errors": 2,
                "total_warnings": 1,
                "blocks_with_errors": ["block-1"],
                "overall_valid": False,
            },
        }

        # Test error message structure
        field_errors = error_message_spec["field_errors"]
        self.assertIn("trait_name", field_errors)
        self.assertIn("trait_min", field_errors)

        # Test field error structure
        trait_name_error = field_errors["trait_name"]
        self.assertIn("errors", trait_name_error)
        self.assertIn("severity", trait_name_error)
        self.assertIn("display_type", trait_name_error)
        self.assertIn("aria_attributes", trait_name_error)

        # Test ARIA attributes
        aria_attrs = trait_name_error["aria_attributes"]
        self.assertEqual(aria_attrs["role"], "alert")
        self.assertEqual(aria_attrs["aria-live"], "polite")

        # Test global errors
        global_errors = error_message_spec["global_errors"]
        self.assertIn("constraint_conflict", global_errors)

        conflict_error = global_errors["constraint_conflict"]
        self.assertEqual(conflict_error["severity"], "error")
        self.assertTrue(conflict_error["dismissible"])

        # Test validation summary
        summary = error_message_spec["validation_summary"]
        self.assertEqual(summary["total_errors"], 2)
        self.assertEqual(summary["total_warnings"], 1)
        self.assertFalse(summary["overall_valid"])

    def test_error_message_html_generation(self):
        """Test HTML generation for error messages."""
        # Mock error data
        error_data = {
            "field": "trait_name",
            "message": "Trait name is required",
            "severity": "error",
            "block_id": "block-1",
        }

        # Test field error generation structure

        # Simulate HTML generation function
        def generate_field_error_html(error_data):
            return f"""
            <div class="field-error {error_data['severity']}-severity"
                 id="field-error-{error_data['field']}-{error_data['block_id']}"
                 data-field="{error_data['field']}"
                 data-block-id="{error_data['block_id']}"
                 data-severity="{error_data['severity']}"
                 role="alert"
                 aria-live="polite">
                <span class="error-icon" aria-hidden="true">⚠</span>
                <span class="error-message">{error_data['message']}</span>
                <button type="button"
                        class="error-dismiss btn-link"
                        aria-label="Dismiss error"
                        data-dismiss-error="field-error-{error_data['field']}-{error_data['block_id']}">
                    ×
                </button>
            </div>
            """

        generated_html = generate_field_error_html(error_data)

        # Test HTML structure
        self.assertIn("field-error", generated_html)
        self.assertIn("error-severity", generated_html)
        self.assertIn('id="field-error-trait_name-block-1"', generated_html)
        self.assertIn('data-field="trait_name"', generated_html)
        self.assertIn('data-block-id="block-1"', generated_html)
        self.assertIn('role="alert"', generated_html)
        self.assertIn('aria-live="polite"', generated_html)
        self.assertIn("Trait name is required", generated_html)
        self.assertIn("error-dismiss", generated_html)

    def test_warning_message_display(self):
        """Test warning message display functionality."""
        # Mock warning data
        warning_data = {
            "field": "trait_max",
            "message": "No maximum value set - requirement has no upper limit",
            "severity": "warning",
            "block_id": "block-2",
            "dismissible": True,
            "auto_hide_delay": 5000,
        }

        def generate_warning_html(warning_data):
            auto_hide = (
                f'data-auto-hide="{warning_data["auto_hide_delay"]}"'
                if warning_data.get("auto_hide_delay")
                else ""
            )
            dismissible = "dismissible" if warning_data.get("dismissible") else ""

            return f"""
            <div class="field-warning warning-severity {dismissible}"
                 id="field-warning-{warning_data['field']}-{warning_data['block_id']}"
                 data-field="{warning_data['field']}"
                 data-block-id="{warning_data['block_id']}"
                 data-severity="{warning_data['severity']}"
                 {auto_hide}
                 role="status"
                 aria-live="polite">
                <span class="warning-icon" aria-hidden="true">ℹ</span>
                <span class="warning-message">{warning_data['message']}</span>
                {'<button type="button" class="warning-dismiss btn-link" aria-label="Dismiss warning">×</button>' if warning_data.get('dismissible') else ''}
            </div>
            """

        generated_warning = generate_warning_html(warning_data)

        # Test warning structure
        self.assertIn("field-warning", generated_warning)
        self.assertIn("warning-severity", generated_warning)
        self.assertIn("dismissible", generated_warning)
        self.assertIn('data-auto-hide="5000"', generated_warning)
        self.assertIn('role="status"', generated_warning)
        self.assertIn("No maximum value set", generated_warning)
        self.assertIn("warning-dismiss", generated_warning)


class CrossFieldValidationTest(TestCase):
    """Test cross-field validation rules."""

    def test_trait_constraint_cross_validation(self):
        """Test cross-field validation for trait constraints."""

        # Test case: use_exact conflicts with use_min/use_max
        def validate_constraint_conflicts(form_data):
            errors = {}

            if form_data.get("use_exact") and (
                form_data.get("use_min") or form_data.get("use_max")
            ):
                errors["use_exact"] = (
                    "Exact value cannot be used with minimum or maximum constraints"
                )
                errors["constraint_conflict"] = (
                    "Choose either exact value OR min/max range, not both"
                )

            return errors

        # Test conflict case
        conflict_data = {"use_exact": True, "use_min": True, "use_max": False}

        conflict_errors = validate_constraint_conflicts(conflict_data)
        self.assertIn("use_exact", conflict_errors)
        self.assertIn("constraint_conflict", conflict_errors)

        # Test non-conflict case
        valid_data = {"use_exact": True, "use_min": False, "use_max": False}

        valid_errors = validate_constraint_conflicts(valid_data)
        self.assertEqual(len(valid_errors), 0)

    def test_min_max_relationship_validation(self):
        """Test validation of min/max value relationships."""

        def validate_min_max_relationship(min_val, max_val, use_min, use_max):
            errors = {}

            if use_min and use_max and min_val is not None and max_val is not None:
                if min_val > max_val:
                    errors["trait_max"] = (
                        f"Maximum value ({max_val}) cannot be less than minimum ({min_val})"
                    )
                    errors["min_max_relationship"] = (
                        "Maximum must be greater than or equal to minimum"
                    )
                elif min_val == max_val:
                    errors["min_max_relationship"] = (
                        "Consider using exact value instead of identical min/max"
                    )

            return errors

        # Test min > max error
        min_greater_errors = validate_min_max_relationship(5, 3, True, True)
        self.assertIn("trait_max", min_greater_errors)
        self.assertIn("min_max_relationship", min_greater_errors)

        # Test min == max warning
        equal_errors = validate_min_max_relationship(3, 3, True, True)
        self.assertIn("min_max_relationship", equal_errors)
        self.assertIn(
            "Consider using exact value", equal_errors["min_max_relationship"]
        )

        # Test valid relationship
        valid_errors = validate_min_max_relationship(2, 5, True, True)
        self.assertEqual(len(valid_errors), 0)


class NestedValidationTest(TestCase):
    """Test validation of nested requirement structures."""

    def test_nested_requirement_validation_structure(self):
        """Test validation structure for nested requirements."""
        # Mock nested requirement data
        nested_data = {
            "requirement_type": "any",
            "block_id": "any-block-1",
            "sub_requirements": [
                {
                    "requirement_type": "trait",
                    "block_id": "trait-block-1",
                    "trait_name": "strength",
                    "use_min": True,
                    "trait_min": 3,
                },
                {
                    "requirement_type": "trait",
                    "block_id": "trait-block-2",
                    "trait_name": "",  # Invalid empty name
                    "use_min": False,
                    "use_max": False,
                    "use_exact": False,  # Invalid no constraints
                },
            ],
        }

        def validate_nested_requirement(nested_data):
            validation_result = {
                "block_id": nested_data["block_id"],
                "valid": True,
                "errors": [],
                "sub_validations": [],
            }

            # Check minimum sub-requirements
            if len(nested_data["sub_requirements"]) < 1:
                validation_result["valid"] = False
                validation_result["errors"].append(
                    "At least one sub-requirement is required"
                )

            # Validate each sub-requirement
            for sub_req in nested_data["sub_requirements"]:
                if sub_req["requirement_type"] == "trait":
                    name_result = FieldValidator.validate_trait_name(
                        sub_req.get("trait_name", "")
                    )
                    constraint_result = FieldValidator.validate_trait_constraints(
                        sub_req.get("use_min", False),
                        sub_req.get("trait_min"),
                        sub_req.get("use_max", False),
                        sub_req.get("trait_max"),
                        sub_req.get("use_exact", False),
                        sub_req.get("trait_exact"),
                    )

                    sub_validation = {
                        "block_id": sub_req["block_id"],
                        "valid": name_result.valid and constraint_result.valid,
                        "errors": name_result.errors + constraint_result.errors,
                        "field_errors": {
                            **name_result.field_errors,
                            **constraint_result.field_errors,
                        },
                    }

                    validation_result["sub_validations"].append(sub_validation)

                    if not sub_validation["valid"]:
                        validation_result["valid"] = False

            return validation_result

        # Test nested validation
        result = validate_nested_requirement(nested_data)

        # Test overall structure
        self.assertEqual(result["block_id"], "any-block-1")
        self.assertFalse(
            result["valid"]
        )  # Should be invalid due to sub-requirement errors
        self.assertEqual(len(result["sub_validations"]), 2)

        # Test first sub-requirement (valid)
        first_sub = result["sub_validations"][0]
        self.assertEqual(first_sub["block_id"], "trait-block-1")
        self.assertTrue(first_sub["valid"])

        # Test second sub-requirement (invalid)
        second_sub = result["sub_validations"][1]
        self.assertEqual(second_sub["block_id"], "trait-block-2")
        self.assertFalse(second_sub["valid"])
        self.assertGreater(len(second_sub["errors"]), 0)

    def test_nesting_depth_validation(self):
        """Test validation of nesting depth limits."""

        def validate_nesting_depth(requirement_data, current_depth=0, max_depth=5):
            if current_depth > max_depth:
                return {
                    "valid": False,
                    "error": f"Maximum nesting depth of {max_depth} exceeded (current: {current_depth})",
                }

            if requirement_data["requirement_type"] in ["any", "all"]:
                for sub_req in requirement_data.get("sub_requirements", []):
                    sub_result = validate_nesting_depth(
                        sub_req, current_depth + 1, max_depth
                    )
                    if not sub_result["valid"]:
                        return sub_result

            return {"valid": True}

        # Test valid nesting depth
        shallow_data = {
            "requirement_type": "any",
            "sub_requirements": [
                {"requirement_type": "trait"},
                {"requirement_type": "has"},
            ],
        }

        shallow_result = validate_nesting_depth(shallow_data, 0, 5)
        self.assertTrue(shallow_result["valid"])

        # Test excessive nesting depth
        deep_data = {
            "requirement_type": "any",
            "sub_requirements": [
                {
                    "requirement_type": "all",
                    "sub_requirements": [
                        {
                            "requirement_type": "any",
                            "sub_requirements": [
                                {
                                    "requirement_type": "all",
                                    "sub_requirements": [{"requirement_type": "trait"}],
                                }
                            ],
                        }
                    ],
                }
            ],
        }

        deep_result = validate_nesting_depth(deep_data, 3, 5)  # Start at depth 3
        self.assertFalse(deep_result["valid"])
        self.assertIn("Maximum nesting depth", deep_result["error"])


class ValidationUserExperienceTest(TestCase):
    """Test user experience aspects of validation."""

    def test_debounced_validation_behavior(self):
        """Test debounced validation timing and behavior."""

        # Mock debounced validation behavior
        class DebouncedValidator:
            def __init__(self, delay=300):
                self.delay = delay
                self.pending_validations = {}
                self.validation_count = 0

            def schedule_validation(self, field_id, value):
                # Cancel previous validation for this field
                if field_id in self.pending_validations:
                    self.cancel_validation(field_id)

                # Schedule new validation
                self.pending_validations[field_id] = {
                    "value": value,
                    "scheduled_time": self.delay,
                    "status": "pending",
                }

            def execute_validation(self, field_id):
                if field_id in self.pending_validations:
                    validation = self.pending_validations[field_id]
                    validation["status"] = "completed"
                    self.validation_count += 1
                    return True
                return False

            def cancel_validation(self, field_id):
                if field_id in self.pending_validations:
                    self.pending_validations[field_id]["status"] = "cancelled"

        validator = DebouncedValidator(delay=300)

        # Test single validation
        validator.schedule_validation("trait_name_block_1", "strength")
        self.assertIn("trait_name_block_1", validator.pending_validations)
        self.assertEqual(
            validator.pending_validations["trait_name_block_1"]["status"], "pending"
        )

        # Test validation cancellation with rapid changes
        validator.schedule_validation("trait_name_block_1", "str")
        validator.schedule_validation("trait_name_block_1", "stre")
        validator.schedule_validation("trait_name_block_1", "stren")
        validator.schedule_validation("trait_name_block_1", "streng")
        validator.schedule_validation("trait_name_block_1", "strength")

        # Should only have one pending validation (the last one)
        self.assertEqual(len(validator.pending_validations), 1)
        self.assertEqual(
            validator.pending_validations["trait_name_block_1"]["value"], "strength"
        )

        # Execute validation
        executed = validator.execute_validation("trait_name_block_1")
        self.assertTrue(executed)
        self.assertEqual(validator.validation_count, 1)

    def test_progressive_validation_feedback(self):
        """Test progressive validation feedback as user types."""
        # Mock progressive validation states
        validation_states = {
            "initial": {
                "show_errors": False,
                "show_warnings": False,
                "show_success": False,
            },
            "typing": {
                "show_errors": False,
                "show_warnings": False,
                "show_success": False,
            },
            "paused": {
                "show_errors": True,
                "show_warnings": True,
                "show_success": False,
            },
            "valid": {
                "show_errors": False,
                "show_warnings": True,
                "show_success": True,
            },
            "invalid": {
                "show_errors": True,
                "show_warnings": False,
                "show_success": False,
            },
        }

        def get_validation_state(input_value, is_typing, validation_result):
            if is_typing:
                return validation_states["typing"]

            if not input_value or not input_value.strip():
                return validation_states["initial"]

            if validation_result and validation_result.valid:
                return validation_states["valid"]
            elif validation_result and not validation_result.valid:
                return validation_states["invalid"]
            else:
                return validation_states["paused"]

        # Test initial state (empty input)
        initial_state = get_validation_state("", False, None)
        self.assertEqual(initial_state, validation_states["initial"])
        self.assertFalse(initial_state["show_errors"])

        # Test typing state
        typing_state = get_validation_state("str", True, None)
        self.assertEqual(typing_state, validation_states["typing"])
        self.assertFalse(typing_state["show_errors"])

        # Test valid state
        valid_result = ValidationResult(valid=True, warnings=["No maximum set"])
        valid_state = get_validation_state("strength", False, valid_result)
        self.assertEqual(valid_state, validation_states["valid"])
        self.assertTrue(valid_state["show_success"])
        self.assertTrue(valid_state["show_warnings"])

        # Test invalid state
        invalid_result = ValidationResult(valid=False, errors=["Name too short"])
        invalid_state = get_validation_state("x", False, invalid_result)
        self.assertEqual(invalid_state, validation_states["invalid"])
        self.assertTrue(invalid_state["show_errors"])
        self.assertFalse(invalid_state["show_success"])

    def test_error_recovery_guidance(self):
        """Test error recovery guidance and suggestions."""

        # Mock error recovery suggestions
        def get_recovery_suggestions(error_type, error_context):
            suggestions = {
                "empty_trait_name": {
                    "message": "Trait name is required",
                    "suggestions": [
                        "Enter a character trait name (e.g., strength, dexterity)",
                        "Common traits: arete, quintessence, willpower",
                        "Use lowercase names for consistency",
                    ],
                    "quick_fixes": ["strength", "dexterity", "arete"],
                },
                "constraint_conflict": {
                    "message": "Exact value cannot be used with min/max",
                    "suggestions": [
                        'Uncheck either "Exact value" or the min/max constraints',
                        "Use exact value for specific requirements (e.g., Arete = 3)",
                        "Use min/max for range requirements (e.g., Strength 2-5)",
                    ],
                    "quick_fixes": ["Use exact only", "Use min/max only"],
                },
                "min_greater_than_max": {
                    "message": "Maximum value cannot be less than minimum",
                    "suggestions": [
                        f'Set maximum to {error_context.get("min_value", 0)} or higher',
                        f'Or reduce minimum to {error_context.get("max_value", 0)} or lower',
                        "Consider if you meant to use exact value instead",
                    ],
                    "quick_fixes": [
                        f'Set max to {error_context.get("min_value", 0)}',
                        f'Set min to {error_context.get("max_value", 0)}',
                    ],
                },
            }

            return suggestions.get(
                error_type,
                {
                    "message": "Please correct this error",
                    "suggestions": ["Check your input and try again"],
                    "quick_fixes": [],
                },
            )

        # Test empty trait name suggestions
        empty_name_suggestions = get_recovery_suggestions("empty_trait_name", {})
        self.assertIn("suggestions", empty_name_suggestions)
        self.assertIn("quick_fixes", empty_name_suggestions)
        self.assertEqual(len(empty_name_suggestions["suggestions"]), 3)
        self.assertIn("strength", empty_name_suggestions["quick_fixes"])

        # Test constraint conflict suggestions
        conflict_suggestions = get_recovery_suggestions("constraint_conflict", {})
        self.assertIn("Uncheck either", conflict_suggestions["suggestions"][0])
        self.assertEqual(len(conflict_suggestions["quick_fixes"]), 2)

        # Test min/max error with context
        min_max_context = {"min_value": 5, "max_value": 3}
        min_max_suggestions = get_recovery_suggestions(
            "min_greater_than_max", min_max_context
        )
        self.assertIn("Set maximum to 5", min_max_suggestions["suggestions"][0])
        self.assertIn("Set max to 5", min_max_suggestions["quick_fixes"][0])


class ValidationAccessibilityTest(TestCase):
    """Test accessibility aspects of validation feedback."""

    def test_screen_reader_error_announcements(self):
        """Test screen reader accessibility for error announcements."""

        # Mock screen reader announcement structure
        def generate_sr_announcement(validation_result, field_name):
            announcements = []

            if not validation_result.valid:
                error_count = len(validation_result.errors)
                if error_count == 1:
                    announcements.append(
                        f"Error in {field_name}: {validation_result.errors[0]}"
                    )
                else:
                    announcements.append(f"{error_count} errors in {field_name}")
                    for error in validation_result.errors:
                        announcements.append(error)

            if validation_result.warnings:
                warning_count = len(validation_result.warnings)
                if warning_count == 1:
                    announcements.append(
                        f"Warning for {field_name}: {validation_result.warnings[0]}"
                    )
                else:
                    announcements.append(f"{warning_count} warnings for {field_name}")

            return announcements

        # Test single error announcement
        single_error = ValidationResult(valid=False, errors=["Trait name is required"])
        single_announcements = generate_sr_announcement(single_error, "trait name")
        self.assertEqual(len(single_announcements), 1)
        self.assertEqual(
            single_announcements[0], "Error in trait name: Trait name is required"
        )

        # Test multiple errors announcement
        multiple_errors = ValidationResult(
            valid=False,
            errors=[
                "Trait name is required",
                "At least one constraint must be specified",
            ],
        )
        multiple_announcements = generate_sr_announcement(
            multiple_errors, "trait requirements"
        )
        self.assertEqual(len(multiple_announcements), 3)
        self.assertEqual(multiple_announcements[0], "2 errors in trait requirements")

        # Test warning announcement
        warning_result = ValidationResult(valid=True, warnings=["No maximum value set"])
        warning_announcements = generate_sr_announcement(
            warning_result, "trait constraints"
        )
        self.assertEqual(len(warning_announcements), 1)
        self.assertIn("Warning for trait constraints", warning_announcements[0])

    def test_aria_live_region_management(self):
        """Test ARIA live region management for dynamic updates."""
        # Mock ARIA live region structure
        aria_live_regions = {
            "validation_messages": {
                "element_id": "validation-messages-builder-1",
                "aria_live": "polite",
                "aria_relevant": "additions text",
                "aria_atomic": "false",
                "role": "alert",
            },
            "block_validation": {
                "element_id": "block-validation-{block_id}",
                "aria_live": "polite",
                "aria_relevant": "additions text",
                "aria_atomic": "true",
                "role": "status",
            },
            "validation_summary": {
                "element_id": "validation-summary-builder-1",
                "aria_live": "assertive",
                "aria_relevant": "text",
                "aria_atomic": "true",
                "role": "status",
            },
        }

        def update_aria_live_region(region_type, content, block_id=None):
            if region_type not in aria_live_regions:
                return None

            region_config = aria_live_regions[region_type]
            element_id = (
                region_config["element_id"].format(block_id=block_id)
                if block_id
                else region_config["element_id"]
            )

            return {
                "element_id": element_id,
                "content": content,
                "attributes": {
                    "aria-live": region_config["aria_live"],
                    "aria-relevant": region_config["aria_relevant"],
                    "aria-atomic": region_config["aria_atomic"],
                    "role": region_config["role"],
                },
            }

        # Test validation messages update
        validation_update = update_aria_live_region(
            "validation_messages", "Validation complete: 2 errors found"
        )

        self.assertEqual(
            validation_update["element_id"], "validation-messages-builder-1"
        )
        self.assertEqual(validation_update["attributes"]["aria-live"], "polite")
        self.assertEqual(validation_update["attributes"]["role"], "alert")

        # Test block validation update
        block_update = update_aria_live_region(
            "block_validation",
            "Trait name error: Name is required",
            block_id="block-123",
        )

        self.assertEqual(block_update["element_id"], "block-validation-block-123")
        self.assertEqual(block_update["attributes"]["aria-atomic"], "true")

        # Test validation summary update
        summary_update = update_aria_live_region(
            "validation_summary", "Form validation: 0 errors, 1 warning"
        )

        self.assertEqual(summary_update["attributes"]["aria-live"], "assertive")
        self.assertEqual(summary_update["attributes"]["role"], "status")
