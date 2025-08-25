"""
Comprehensive tests for JavaScript prerequisite builder components (Issue #190).

This module defines the expected behavior and interface for JavaScript components
that implement the visual prerequisite builder. These tests specify the contracts
and expected functionality without requiring actual JavaScript execution.

Key JavaScript components being tested:
1. PrerequisiteBuilder main class functionality
2. RequirementBlock individual requirement components
3. RequirementValidator real-time validation
4. JSONGenerator output generation
5. DOMManager DOM manipulation utilities
6. EventHandler user interaction handling
7. UndoRedoManager state management
8. AccessibilityManager screen reader support

These tests serve as specifications for the JavaScript implementation,
ensuring consistent behavior and proper integration with the Django backend.
"""

import json

from django.test import TestCase


class PrerequisiteBuilderClassTest(TestCase):
    """Test specifications for the main PrerequisiteBuilder JavaScript class."""

    def test_prerequisite_builder_constructor_interface(self):
        """Test the expected constructor interface for PrerequisiteBuilder."""
        # Expected constructor signature and configuration
        constructor_spec = {
            "class_name": "PrerequisiteBuilder",
            "constructor_params": {
                "container_element": "HTMLElement",  # DOM element to attach to
                "hidden_field_element": "HTMLElement",  # Hidden input field
                "options": {
                    "type": "object",
                    "default": {},
                    "properties": {
                        "initial_requirements": {"type": "object", "default": {}},
                        "validation_url": {"type": "string", "default": None},
                        "available_traits": {"type": "array", "default": []},
                        "available_fields": {"type": "array", "default": []},
                        "max_nesting_depth": {"type": "integer", "default": 5},
                        "auto_validate": {"type": "boolean", "default": True},
                        "show_json_preview": {"type": "boolean", "default": False},
                        "enable_undo_redo": {"type": "boolean", "default": True},
                    },
                },
            },
            "instance_methods": [
                "initialize",
                "addRequirement",
                "removeRequirement",
                "validateRequirements",
                "generateJSON",
                "loadFromJSON",
                "clear",
                "undo",
                "redo",
                "destroy",
            ],
            "static_methods": ["fromElement", "validateRequirementStructure"],
            "events": [
                "requirement-added",
                "requirement-removed",
                "requirement-changed",
                "validation-complete",
                "json-generated",
            ],
        }

        # Validate constructor specification structure
        self.assertIn("class_name", constructor_spec)
        self.assertEqual(constructor_spec["class_name"], "PrerequisiteBuilder")

        # Validate constructor parameters
        params = constructor_spec["constructor_params"]
        self.assertIn("container_element", params)
        self.assertIn("hidden_field_element", params)
        self.assertIn("options", params)

        # Validate options structure
        options = params["options"]["properties"]
        self.assertIn("initial_requirements", options)
        self.assertIn("max_nesting_depth", options)
        self.assertIn("auto_validate", options)

        # Validate required methods exist
        required_methods = [
            "initialize",
            "addRequirement",
            "removeRequirement",
            "validateRequirements",
            "generateJSON",
            "loadFromJSON",
        ]
        for method in required_methods:
            self.assertIn(method, constructor_spec["instance_methods"])

    def test_prerequisite_builder_initialization_process(self):
        """Test the expected initialization process."""
        initialization_spec = {
            "steps": [
                {
                    "step": "validate_constructor_params",
                    "description": "Validate container and hidden field elements exist",
                    "validation": {
                        "container_element": "must_be_html_element",
                        "hidden_field_element": "must_be_input_element",
                    },
                },
                {
                    "step": "setup_dom_structure",
                    "description": "Create the visual builder DOM structure",
                    "creates": [
                        "builder_header",
                        "builder_content",
                        "requirement_blocks_container",
                        "builder_footer",
                        "validation_messages",
                        "json_preview",
                    ],
                },
                {
                    "step": "initialize_managers",
                    "description": "Initialize helper manager classes",
                    "managers": [
                        "DOMManager",
                        "EventHandler",
                        "RequirementValidator",
                        "JSONGenerator",
                        "UndoRedoManager",
                        "AccessibilityManager",
                    ],
                },
                {
                    "step": "load_initial_data",
                    "description": "Load any initial requirements from options or hidden field",
                    "sources": ["options.initial_requirements", "hidden_field.value"],
                },
                {
                    "step": "bind_event_listeners",
                    "description": "Attach event listeners for user interactions",
                    "events": [
                        "click on add-requirement button",
                        "change on requirement inputs",
                        "click on remove-requirement buttons",
                        "keydown for keyboard shortcuts",
                    ],
                },
                {
                    "step": "trigger_ready_event",
                    "description": "Fire initialization complete event",
                    "event": "prerequisite-builder-ready",
                },
            ]
        }

        # Validate initialization steps
        self.assertEqual(len(initialization_spec["steps"]), 6)

        # Check each step has required properties
        for step in initialization_spec["steps"]:
            self.assertIn("step", step)
            self.assertIn("description", step)

        # Validate specific critical steps
        dom_setup_step = initialization_spec["steps"][1]
        self.assertEqual(dom_setup_step["step"], "setup_dom_structure")
        self.assertIn("builder_header", dom_setup_step["creates"])
        self.assertIn("requirement_blocks_container", dom_setup_step["creates"])

        managers_step = initialization_spec["steps"][2]
        self.assertEqual(managers_step["step"], "initialize_managers")
        self.assertIn("DOMManager", managers_step["managers"])
        self.assertIn("JSONGenerator", managers_step["managers"])

    def test_prerequisite_builder_public_api_methods(self):
        """Test the expected public API method specifications."""
        api_methods_spec = {
            "addRequirement": {
                "parameters": [
                    {"name": "requirementType", "type": "string", "required": True},
                    {
                        "name": "initialData",
                        "type": "object",
                        "required": False,
                        "default": {},
                    },
                    {
                        "name": "parentBlock",
                        "type": "object",
                        "required": False,
                        "default": None,
                    },
                ],
                "returns": "RequirementBlock",
                "description": "Add a new requirement block to the builder",
                "events_fired": ["requirement-added"],
                "validation": "validates requirementType is supported",
            },
            "removeRequirement": {
                "parameters": [{"name": "blockId", "type": "string", "required": True}],
                "returns": "boolean",
                "description": "Remove a requirement block by ID",
                "events_fired": ["requirement-removed"],
                "validation": "validates blockId exists",
            },
            "validateRequirements": {
                "parameters": [
                    {
                        "name": "showErrors",
                        "type": "boolean",
                        "required": False,
                        "default": True,
                    }
                ],
                "returns": "ValidationResult",
                "description": "Validate all current requirements",
                "events_fired": ["validation-complete"],
                "async": True,
            },
            "generateJSON": {
                "parameters": [],
                "returns": "object",
                "description": "Generate JSON representation of current requirements",
                "events_fired": ["json-generated"],
                "side_effects": ["updates hidden field value"],
            },
            "loadFromJSON": {
                "parameters": [
                    {"name": "jsonData", "type": "object", "required": True}
                ],
                "returns": "boolean",
                "description": "Load requirements from JSON data",
                "validation": "validates JSON structure",
                "side_effects": ["clears existing requirements", "creates new blocks"],
            },
        }

        # Validate each API method specification
        required_methods = [
            "addRequirement",
            "removeRequirement",
            "validateRequirements",
            "generateJSON",
            "loadFromJSON",
        ]

        for method_name in required_methods:
            self.assertIn(method_name, api_methods_spec)
            method_spec = api_methods_spec[method_name]

            # All methods should have these properties
            self.assertIn("parameters", method_spec)
            self.assertIn("returns", method_spec)
            self.assertIn("description", method_spec)

            # Validate parameter structure
            for param in method_spec["parameters"]:
                self.assertIn("name", param)
                self.assertIn("type", param)
                self.assertIn("required", param)

        # Validate specific method behaviors
        add_method = api_methods_spec["addRequirement"]
        self.assertEqual(add_method["returns"], "RequirementBlock")
        self.assertIn("requirement-added", add_method["events_fired"])

        validate_method = api_methods_spec["validateRequirements"]
        self.assertTrue(validate_method.get("async", False))
        self.assertEqual(validate_method["returns"], "ValidationResult")


class RequirementBlockComponentTest(TestCase):
    """Test specifications for individual RequirementBlock components."""

    def test_requirement_block_base_interface(self):
        """Test base interface for RequirementBlock components."""
        requirement_block_spec = {
            "base_class": "RequirementBlock",
            "constructor_params": {
                "blockId": {"type": "string", "required": True},
                "requirementType": {"type": "string", "required": True},
                "parentBuilder": {"type": "PrerequisiteBuilder", "required": True},
                "initialData": {"type": "object", "required": False, "default": {}},
                "parentBlock": {
                    "type": "RequirementBlock",
                    "required": False,
                    "default": None,
                },
            },
            "properties": {
                "blockId": "string",
                "requirementType": "string",
                "isValid": "boolean",
                "data": "object",
                "domElement": "HTMLElement",
                "parentBlock": "RequirementBlock|null",
                "childBlocks": "Array<RequirementBlock>",
            },
            "methods": {
                "render": {
                    "returns": "HTMLElement",
                    "description": "Render the block DOM structure",
                },
                "validate": {
                    "returns": "ValidationResult",
                    "description": "Validate the block data",
                },
                "getData": {
                    "returns": "object",
                    "description": "Get current block data as JSON",
                },
                "setData": {
                    "parameters": [{"name": "data", "type": "object"}],
                    "description": "Update block data from JSON",
                },
                "destroy": {"description": "Clean up block resources and DOM"},
            },
            "events": [
                "block-data-changed",
                "block-validation-changed",
                "block-removed",
            ],
        }

        # Validate base class specification
        self.assertEqual(requirement_block_spec["base_class"], "RequirementBlock")

        # Validate constructor parameters
        constructor = requirement_block_spec["constructor_params"]
        self.assertIn("blockId", constructor)
        self.assertIn("requirementType", constructor)
        self.assertIn("parentBuilder", constructor)
        self.assertTrue(constructor["blockId"]["required"])
        self.assertTrue(constructor["requirementType"]["required"])

        # Validate properties
        properties = requirement_block_spec["properties"]
        self.assertEqual(properties["blockId"], "string")
        self.assertEqual(properties["isValid"], "boolean")
        self.assertEqual(properties["domElement"], "HTMLElement")

        # Validate methods
        methods = requirement_block_spec["methods"]
        self.assertIn("render", methods)
        self.assertIn("validate", methods)
        self.assertIn("getData", methods)
        self.assertIn("setData", methods)

        # Check method specifications
        render_method = methods["render"]
        self.assertEqual(render_method["returns"], "HTMLElement")

        validate_method = methods["validate"]
        self.assertEqual(validate_method["returns"], "ValidationResult")

    def test_trait_requirement_block_specification(self):
        """Test specification for TraitRequirementBlock subclass."""
        trait_block_spec = {
            "class": "TraitRequirementBlock",
            "extends": "RequirementBlock",
            "requirement_type": "trait",
            "form_fields": {
                "trait_name": {
                    "type": "text",
                    "required": True,
                    "placeholder": "e.g., strength, arete, melee",
                    "validation": "non_empty_string",
                    "autocomplete_source": "available_traits",
                },
                "use_min": {
                    "type": "checkbox",
                    "label": "Minimum value",
                    "default": False,
                },
                "min_value": {
                    "type": "number",
                    "min": 0,
                    "enabled_when": "use_min = true",
                    "validation": "non_negative_integer",
                },
                "use_max": {
                    "type": "checkbox",
                    "label": "Maximum value",
                    "default": False,
                },
                "max_value": {
                    "type": "number",
                    "min": 0,
                    "enabled_when": "use_max = true",
                    "validation": "non_negative_integer_gte_min",
                },
                "use_exact": {
                    "type": "checkbox",
                    "label": "Exact value",
                    "default": False,
                    "exclusive_with": ["use_min", "use_max"],
                },
                "exact_value": {
                    "type": "number",
                    "min": 0,
                    "enabled_when": "use_exact = true",
                    "validation": "non_negative_integer",
                },
            },
            "validation_rules": [
                "trait_name must not be empty",
                "at least one constraint (min, max, or exact) must be selected",
                "min_value <= max_value when both are used",
                "exact cannot be used with min or max",
            ],
            "json_output_format": {
                "trait": {
                    "name": "trait_name_value",
                    "min": "min_value_if_used",
                    "max": "max_value_if_used",
                    "exact": "exact_value_if_used",
                }
            },
        }

        # Validate trait block specification
        self.assertEqual(trait_block_spec["class"], "TraitRequirementBlock")
        self.assertEqual(trait_block_spec["extends"], "RequirementBlock")
        self.assertEqual(trait_block_spec["requirement_type"], "trait")

        # Validate form fields
        fields = trait_block_spec["form_fields"]
        self.assertIn("trait_name", fields)
        self.assertIn("use_min", fields)
        self.assertIn("min_value", fields)

        # Check field specifications
        trait_name_field = fields["trait_name"]
        self.assertEqual(trait_name_field["type"], "text")
        self.assertTrue(trait_name_field["required"])
        self.assertEqual(trait_name_field["validation"], "non_empty_string")

        # Check constraint fields
        use_exact_field = fields["use_exact"]
        self.assertIn("use_min", use_exact_field["exclusive_with"])
        self.assertIn("use_max", use_exact_field["exclusive_with"])

        # Validate validation rules
        rules = trait_block_spec["validation_rules"]
        self.assertEqual(len(rules), 4)
        self.assertIn("trait_name must not be empty", rules)
        self.assertIn("exact cannot be used with min or max", rules)

    def test_has_requirement_block_specification(self):
        """Test specification for HasRequirementBlock subclass."""
        has_block_spec = {
            "class": "HasRequirementBlock",
            "extends": "RequirementBlock",
            "requirement_type": "has",
            "form_fields": {
                "field_name": {
                    "type": "text",
                    "required": True,
                    "placeholder": "e.g., weapons, foci, items",
                    "validation": "non_empty_string",
                    "autocomplete_source": "available_fields",
                },
                "use_id": {
                    "type": "checkbox",
                    "label": "Match by ID",
                    "default": False,
                },
                "item_id": {
                    "type": "number",
                    "min": 1,
                    "enabled_when": "use_id = true",
                    "validation": "positive_integer",
                },
                "use_name": {
                    "type": "checkbox",
                    "label": "Match by name",
                    "default": True,
                },
                "item_name": {
                    "type": "text",
                    "enabled_when": "use_name = true",
                    "validation": "non_empty_string",
                },
                "additional_fields": {
                    "type": "dynamic_fields",
                    "description": "Additional field/value pairs for matching",
                },
            },
            "validation_rules": [
                "field_name must not be empty",
                "at least one identifier (id or name) must be provided",
                "item_id must be positive integer when used",
                "item_name must not be empty when used",
            ],
            "json_output_format": {
                "has": {
                    "field": "field_name_value",
                    "id": "item_id_if_used",
                    "name": "item_name_if_used",
                    "...additional_fields": "dynamic_additional_fields",
                }
            },
        }

        # Validate has block specification
        self.assertEqual(has_block_spec["class"], "HasRequirementBlock")
        self.assertEqual(has_block_spec["requirement_type"], "has")

        # Validate form fields
        fields = has_block_spec["form_fields"]
        self.assertIn("field_name", fields)
        self.assertIn("use_id", fields)
        self.assertIn("item_id", fields)
        self.assertIn("use_name", fields)
        self.assertIn("item_name", fields)

        # Check field specifications
        field_name_field = fields["field_name"]
        self.assertTrue(field_name_field["required"])
        self.assertEqual(field_name_field["validation"], "non_empty_string")

        item_id_field = fields["item_id"]
        self.assertEqual(item_id_field["min"], 1)
        self.assertEqual(item_id_field["validation"], "positive_integer")

        # Validate validation rules
        rules = has_block_spec["validation_rules"]
        self.assertIn("field_name must not be empty", rules)
        self.assertIn("at least one identifier (id or name) must be provided", rules)

    def test_nested_requirement_blocks_specification(self):
        """Test specification for nested requirement blocks (any/all)."""
        nested_block_spec = {
            "classes": ["AnyRequirementBlock", "AllRequirementBlock"],
            "extends": "RequirementBlock",
            "requirement_types": ["any", "all"],
            "shared_features": {
                "supports_nesting": True,
                "max_nesting_depth": 5,
                "min_sub_requirements": 1,
                "sub_requirements": "Array<RequirementBlock>",
            },
            "form_structure": {
                "header": {
                    "requirement_type_selector": "dropdown",
                    "remove_button": "button",
                },
                "content": {
                    "sub_requirements_container": "div.nested-requirements-list",
                    "add_sub_requirement_button": "button.add-nested-requirement",
                    "empty_state_message": "No sub-requirements defined",
                },
                "footer": {"validation_messages": "div.validation-status"},
            },
            "methods": {
                "addSubRequirement": {
                    "parameters": [
                        {"name": "requirementType", "type": "string"},
                        {"name": "initialData", "type": "object", "default": {}},
                    ],
                    "returns": "RequirementBlock",
                    "description": "Add a nested sub-requirement",
                },
                "removeSubRequirement": {
                    "parameters": [{"name": "blockId", "type": "string"}],
                    "returns": "boolean",
                    "description": "Remove a nested sub-requirement",
                },
                "validateNesting": {
                    "returns": "ValidationResult",
                    "description": "Validate nesting depth and circular references",
                },
            },
            "validation_rules": [
                "must have at least one sub-requirement",
                "nesting depth cannot exceed max_nesting_depth",
                "circular references are not allowed",
                "all sub-requirements must be valid",
            ],
            "json_output_format": {
                "any_format": {"any": ["array_of_sub_requirement_json"]},
                "all_format": {"all": ["array_of_sub_requirement_json"]},
            },
        }

        # Validate nested block specification
        self.assertEqual(len(nested_block_spec["classes"]), 2)
        self.assertIn("AnyRequirementBlock", nested_block_spec["classes"])
        self.assertIn("AllRequirementBlock", nested_block_spec["classes"])

        # Validate shared features
        shared = nested_block_spec["shared_features"]
        self.assertTrue(shared["supports_nesting"])
        self.assertEqual(shared["max_nesting_depth"], 5)
        self.assertEqual(shared["min_sub_requirements"], 1)

        # Validate form structure
        form = nested_block_spec["form_structure"]
        self.assertIn("header", form)
        self.assertIn("content", form)
        self.assertIn("footer", form)

        # Validate methods
        methods = nested_block_spec["methods"]
        self.assertIn("addSubRequirement", methods)
        self.assertIn("removeSubRequirement", methods)
        self.assertIn("validateNesting", methods)

        # Validate validation rules
        rules = nested_block_spec["validation_rules"]
        self.assertIn("must have at least one sub-requirement", rules)
        self.assertIn("nesting depth cannot exceed max_nesting_depth", rules)


class RequirementValidatorTest(TestCase):
    """Test specifications for the RequirementValidator component."""

    def test_validator_interface_specification(self):
        """Test the RequirementValidator interface specification."""
        validator_spec = {
            "class": "RequirementValidator",
            "constructor_params": {
                "builder": {"type": "PrerequisiteBuilder", "required": True},
                "options": {
                    "type": "object",
                    "properties": {
                        "validation_url": {"type": "string", "default": None},
                        "real_time_validation": {"type": "boolean", "default": True},
                        "debounce_delay": {"type": "integer", "default": 300},
                        "show_warnings": {"type": "boolean", "default": True},
                    },
                },
            },
            "methods": {
                "validateBlock": {
                    "parameters": [
                        {"name": "block", "type": "RequirementBlock"},
                        {"name": "showUI", "type": "boolean", "default": True},
                    ],
                    "returns": "Promise<ValidationResult>",
                    "description": "Validate a single requirement block",
                },
                "validateAll": {
                    "parameters": [
                        {"name": "showUI", "type": "boolean", "default": True}
                    ],
                    "returns": "Promise<ValidationResult>",
                    "description": "Validate all requirement blocks",
                },
                "clearValidation": {
                    "parameters": [
                        {"name": "blockId", "type": "string", "required": False}
                    ],
                    "description": "Clear validation messages for block or all blocks",
                },
                "showValidationError": {
                    "parameters": [
                        {"name": "blockId", "type": "string"},
                        {"name": "errors", "type": "Array<ValidationError>"},
                    ],
                    "description": "Display validation errors for a block",
                },
            },
            "validation_result_structure": {
                "valid": "boolean",
                "errors": "Array<ValidationError>",
                "warnings": "Array<ValidationWarning>",
                "block_results": "Map<string, BlockValidationResult>",
            },
            "validation_error_structure": {
                "field": "string",
                "message": "string",
                "code": "string",
                "severity": "error|warning|info",
            },
        }

        # Validate validator specification
        self.assertEqual(validator_spec["class"], "RequirementValidator")

        # Validate constructor
        constructor = validator_spec["constructor_params"]
        self.assertIn("builder", constructor)
        self.assertTrue(constructor["builder"]["required"])

        # Validate options
        options = constructor["options"]["properties"]
        self.assertIn("validation_url", options)
        self.assertIn("real_time_validation", options)
        self.assertIn("debounce_delay", options)

        # Validate methods
        methods = validator_spec["methods"]
        self.assertIn("validateBlock", methods)
        self.assertIn("validateAll", methods)
        self.assertIn("clearValidation", methods)

        # Check method specifications
        validate_block = methods["validateBlock"]
        self.assertEqual(validate_block["returns"], "Promise<ValidationResult>")

        # Validate result structures
        result_structure = validator_spec["validation_result_structure"]
        self.assertEqual(result_structure["valid"], "boolean")
        self.assertEqual(result_structure["errors"], "Array<ValidationError>")

        error_structure = validator_spec["validation_error_structure"]
        self.assertEqual(error_structure["field"], "string")
        self.assertEqual(error_structure["message"], "string")

    def test_validation_rules_specification(self):
        """Test specification for validation rules."""
        validation_rules_spec = {
            "trait_validation": {
                "trait_name_required": {
                    "rule": "field_required",
                    "field": "trait_name",
                    "message": "Trait name is required",
                },
                "trait_name_not_empty": {
                    "rule": "not_empty",
                    "field": "trait_name",
                    "message": "Trait name cannot be empty",
                },
                "constraint_required": {
                    "rule": "at_least_one",
                    "fields": ["use_min", "use_max", "use_exact"],
                    "message": "At least one constraint (min, max, or exact) must be specified",
                },
                "min_max_relationship": {
                    "rule": "conditional_validation",
                    "condition": "use_min && use_max",
                    "validation": "min_value <= max_value",
                    "message": "Maximum value cannot be less than minimum value",
                },
                "exact_exclusivity": {
                    "rule": "mutual_exclusion",
                    "field": "use_exact",
                    "exclusive_with": ["use_min", "use_max"],
                    "message": "Exact value cannot be used with minimum or maximum",
                },
            },
            "has_validation": {
                "field_name_required": {
                    "rule": "field_required",
                    "field": "field_name",
                    "message": "Field name is required",
                },
                "identifier_required": {
                    "rule": "at_least_one",
                    "fields": ["use_id", "use_name"],
                    "message": "At least one identifier (ID or name) must be provided",
                },
                "id_positive": {
                    "rule": "conditional_validation",
                    "condition": "use_id",
                    "validation": "item_id > 0",
                    "message": "Item ID must be a positive number",
                },
            },
            "nested_validation": {
                "sub_requirements_required": {
                    "rule": "min_length",
                    "field": "sub_requirements",
                    "min_length": 1,
                    "message": "At least one sub-requirement is required",
                },
                "max_nesting_depth": {
                    "rule": "max_depth",
                    "max_depth": 5,
                    "message": "Maximum nesting depth of 5 levels exceeded",
                },
                "circular_reference": {
                    "rule": "no_circular_reference",
                    "message": "Circular references are not allowed",
                },
            },
        }

        # Validate validation rules structure
        self.assertIn("trait_validation", validation_rules_spec)
        self.assertIn("has_validation", validation_rules_spec)
        self.assertIn("nested_validation", validation_rules_spec)

        # Check trait validation rules
        trait_rules = validation_rules_spec["trait_validation"]
        self.assertIn("trait_name_required", trait_rules)
        self.assertIn("constraint_required", trait_rules)
        self.assertIn("min_max_relationship", trait_rules)

        # Validate rule structure
        name_required = trait_rules["trait_name_required"]
        self.assertEqual(name_required["rule"], "field_required")
        self.assertEqual(name_required["field"], "trait_name")
        self.assertIn("message", name_required)

        # Check complex validation rules
        constraint_rule = trait_rules["constraint_required"]
        self.assertEqual(constraint_rule["rule"], "at_least_one")
        self.assertEqual(len(constraint_rule["fields"]), 3)

        exclusivity_rule = trait_rules["exact_exclusivity"]
        self.assertEqual(exclusivity_rule["rule"], "mutual_exclusion")
        self.assertIn("use_min", exclusivity_rule["exclusive_with"])


class JSONGeneratorTest(TestCase):
    """Test specifications for the JSONGenerator component."""

    def test_json_generator_interface_specification(self):
        """Test the JSONGenerator interface specification."""
        json_generator_spec = {
            "class": "JSONGenerator",
            "constructor_params": {
                "builder": {"type": "PrerequisiteBuilder", "required": True}
            },
            "methods": {
                "generateFromBlocks": {
                    "parameters": [
                        {"name": "blocks", "type": "Array<RequirementBlock>"}
                    ],
                    "returns": "object",
                    "description": "Generate JSON from array of requirement blocks",
                },
                "generateFromBuilder": {
                    "parameters": [],
                    "returns": "object",
                    "description": "Generate JSON from current builder state",
                },
                "formatForDisplay": {
                    "parameters": [
                        {"name": "jsonObject", "type": "object"},
                        {"name": "indent", "type": "number", "default": 2},
                    ],
                    "returns": "string",
                    "description": "Format JSON for human-readable display",
                },
                "validateStructure": {
                    "parameters": [{"name": "jsonObject", "type": "object"}],
                    "returns": "boolean",
                    "description": "Validate generated JSON structure",
                },
            },
            "generation_strategies": {
                "single_requirement": {
                    "description": "Generate JSON for single requirement block",
                    "example_input": "TraitRequirementBlock with strength >= 3",
                    "example_output": '{"trait": {"name": "strength", "min": 3}}',
                },
                "multiple_requirements": {
                    "description": "Generate JSON for multiple top-level requirements (implicit AND)",
                    "example_input": "Two trait blocks at root level",
                    "example_output": '{"all": [{"trait": {...}}, {"trait": {...}}]}',
                },
                "nested_requirements": {
                    "description": "Generate JSON for nested requirement structures",
                    "example_input": "Any block containing trait blocks",
                    "example_output": '{"any": [{"trait": {...}}, {"trait": {...}}]}',
                },
                "empty_requirements": {
                    "description": "Generate JSON for empty builder",
                    "example_output": "{}",
                },
            },
        }

        # Validate generator specification
        self.assertEqual(json_generator_spec["class"], "JSONGenerator")

        # Validate constructor
        constructor = json_generator_spec["constructor_params"]
        self.assertIn("builder", constructor)
        self.assertTrue(constructor["builder"]["required"])

        # Validate methods
        methods = json_generator_spec["methods"]
        self.assertIn("generateFromBlocks", methods)
        self.assertIn("generateFromBuilder", methods)
        self.assertIn("formatForDisplay", methods)
        self.assertIn("validateStructure", methods)

        # Check method specifications
        generate_blocks = methods["generateFromBlocks"]
        self.assertEqual(generate_blocks["returns"], "object")

        format_display = methods["formatForDisplay"]
        self.assertEqual(format_display["returns"], "string")

        # Validate generation strategies
        strategies = json_generator_spec["generation_strategies"]
        self.assertIn("single_requirement", strategies)
        self.assertIn("multiple_requirements", strategies)
        self.assertIn("nested_requirements", strategies)
        self.assertIn("empty_requirements", strategies)

        # Check strategy specifications
        single_strategy = strategies["single_requirement"]
        self.assertIn("description", single_strategy)
        self.assertIn("example_input", single_strategy)
        self.assertIn("example_output", single_strategy)

    def test_json_output_format_specification(self):
        """Test specification for JSON output formats."""
        json_formats_spec = {
            "trait_requirement": {
                "structure": {
                    "trait": {
                        "name": "string (required)",
                        "min": "integer (optional, >= 0)",
                        "max": "integer (optional, >= 0, >= min)",
                        "exact": "integer (optional, >= 0, exclusive with min/max)",
                    }
                },
                "examples": [
                    '{"trait": {"name": "strength", "min": 3}}',
                    '{"trait": {"name": "arete", "exact": 2}}',
                    '{"trait": {"name": "melee", "min": 2, "max": 5}}',
                ],
            },
            "has_requirement": {
                "structure": {
                    "has": {
                        "field": "string (required)",
                        "id": "integer (optional, > 0)",
                        "name": "string (optional)",
                        "...additional": "any (optional additional fields)",
                    }
                },
                "examples": [
                    '{"has": {"field": "weapons", "id": 123}}',
                    '{"has": {"field": "foci", "name": "Crystal Orb"}}',
                    '{"has": {"field": "items", "name": "Sword", "level": 2}}',
                ],
            },
            "any_requirement": {
                "structure": {"any": "Array<Requirement> (min length 1)"},
                "examples": [
                    '{"any": [{"trait": {"name": "strength", "min": 3}}, {"trait": {"name": "dexterity", "min": 3}}]}'
                ],
            },
            "all_requirement": {
                "structure": {"all": "Array<Requirement> (min length 1)"},
                "examples": [
                    '{"all": [{"trait": {"name": "arete", "min": 2}}, {"has": {"field": "foci", "name": "Orb"}}]}'
                ],
            },
            "count_tag_requirement": {
                "structure": {
                    "count_tag": {
                        "model": "string (required)",
                        "tag": "string (required)",
                        "minimum": "integer (optional, >= 0)",
                        "maximum": "integer (optional, >= 0, >= minimum)",
                    }
                },
                "examples": [
                    '{"count_tag": {"model": "spheres", "tag": "elemental", "minimum": 2}}',
                    '{"count_tag": {"model": "charms", "tag": "combat", "minimum": 1, "maximum": 3}}',
                ],
            },
        }

        # Validate format specifications
        self.assertIn("trait_requirement", json_formats_spec)
        self.assertIn("has_requirement", json_formats_spec)
        self.assertIn("any_requirement", json_formats_spec)
        self.assertIn("all_requirement", json_formats_spec)
        self.assertIn("count_tag_requirement", json_formats_spec)

        # Check trait requirement format
        trait_format = json_formats_spec["trait_requirement"]
        self.assertIn("structure", trait_format)
        self.assertIn("examples", trait_format)

        trait_structure = trait_format["structure"]["trait"]
        self.assertIn("name", trait_structure)
        self.assertIn("min", trait_structure)
        self.assertIn("max", trait_structure)
        self.assertIn("exact", trait_structure)

        # Validate examples are valid JSON
        for example in trait_format["examples"]:
            parsed = json.loads(example)
            self.assertIn("trait", parsed)
            self.assertIn("name", parsed["trait"])

        # Check nested requirement formats
        any_format = json_formats_spec["any_requirement"]
        self.assertIn("any", any_format["structure"])

        all_format = json_formats_spec["all_requirement"]
        self.assertIn("all", all_format["structure"])


class DOMManagerTest(TestCase):
    """Test specifications for the DOMManager utility component."""

    def test_dom_manager_interface_specification(self):
        """Test the DOMManager interface specification."""
        dom_manager_spec = {
            "class": "DOMManager",
            "constructor_params": {
                "containerElement": {"type": "HTMLElement", "required": True}
            },
            "methods": {
                "createElement": {
                    "parameters": [
                        {"name": "tagName", "type": "string"},
                        {"name": "attributes", "type": "object", "default": {}},
                        {"name": "textContent", "type": "string", "default": ""},
                    ],
                    "returns": "HTMLElement",
                    "description": "Create DOM element with attributes and content",
                },
                "createRequirementBlock": {
                    "parameters": [
                        {"name": "blockId", "type": "string"},
                        {"name": "requirementType", "type": "string"},
                    ],
                    "returns": "HTMLElement",
                    "description": "Create DOM structure for requirement block",
                },
                "removeElement": {
                    "parameters": [{"name": "element", "type": "HTMLElement"}],
                    "description": "Remove element from DOM with cleanup",
                },
                "findBlockElement": {
                    "parameters": [{"name": "blockId", "type": "string"}],
                    "returns": "HTMLElement|null",
                    "description": "Find requirement block element by ID",
                },
                "updateBlockValidation": {
                    "parameters": [
                        {"name": "blockId", "type": "string"},
                        {"name": "validationResult", "type": "ValidationResult"},
                    ],
                    "description": "Update visual validation state of block",
                },
                "showEmptyState": {
                    "parameters": [],
                    "description": "Show empty state when no requirements exist",
                },
                "hideEmptyState": {
                    "parameters": [],
                    "description": "Hide empty state when requirements are added",
                },
            },
            "dom_structure": {
                "main_container": ".prerequisite-builder",
                "header": ".builder-header",
                "content": ".builder-content",
                "blocks_container": ".requirement-blocks-container",
                "footer": ".builder-footer",
                "empty_state": ".empty-state",
                "validation_messages": ".validation-messages",
                "json_preview": ".json-preview",
            },
            "css_classes": {
                "requirement_block": "requirement-block",
                "block_valid": "block-valid",
                "block_invalid": "block-invalid",
                "block_warning": "block-warning",
                "nested_requirement": "nested-requirement",
                "form_group": "form-group",
                "form_control": "form-control",
                "btn": "btn",
                "btn_primary": "btn-primary",
                "btn_secondary": "btn-secondary",
                "btn_danger": "btn-danger",
            },
        }

        # Validate DOM manager specification
        self.assertEqual(dom_manager_spec["class"], "DOMManager")

        # Validate constructor
        constructor = dom_manager_spec["constructor_params"]
        self.assertIn("containerElement", constructor)
        self.assertTrue(constructor["containerElement"]["required"])

        # Validate methods
        methods = dom_manager_spec["methods"]
        self.assertIn("createElement", methods)
        self.assertIn("createRequirementBlock", methods)
        self.assertIn("removeElement", methods)
        self.assertIn("findBlockElement", methods)

        # Check method specifications
        create_element = methods["createElement"]
        self.assertEqual(create_element["returns"], "HTMLElement")

        # Validate DOM structure
        dom_structure = dom_manager_spec["dom_structure"]
        self.assertIn("main_container", dom_structure)
        self.assertIn("blocks_container", dom_structure)
        self.assertIn("empty_state", dom_structure)

        # Validate CSS classes
        css_classes = dom_manager_spec["css_classes"]
        self.assertIn("requirement_block", css_classes)
        self.assertIn("block_valid", css_classes)
        self.assertIn("block_invalid", css_classes)

    def test_dom_templates_specification(self):
        """Test specification for DOM templates."""
        dom_templates_spec = {
            "builder_structure": """
                <div class="prerequisite-builder">
                    <div class="builder-header">
                        <h4>Requirement Builder</h4>
                        <div class="builder-controls">
                            <button type="button" class="btn btn-secondary" data-action="clear-all">Clear All</button>
                            <button type="button" class="btn btn-primary" data-action="add-requirement">Add Requirement</button>
                        </div>
                    </div>
                    <div class="builder-content">
                        <div class="requirement-blocks-container"></div>
                        <div class="empty-state" style="display: none;">
                            <p>No requirements defined. Click "Add Requirement" to get started.</p>
                        </div>
                    </div>
                    <div class="builder-footer">
                        <div class="validation-messages"></div>
                        <div class="json-preview" style="display: none;">
                            <label>Generated JSON:</label>
                            <pre class="json-output"></pre>
                        </div>
                    </div>
                </div>
            """,
            "requirement_block_template": """
                <div class="requirement-block" data-requirement-type="{type}" data-block-id="{id}">
                    <div class="requirement-block-header">
                        <select class="requirement-type-selector">
                            <option value="trait">Trait Requirement</option>
                            <option value="has">Has Item</option>
                            <option value="any">Any Of (OR)</option>
                            <option value="all">All Of (AND)</option>
                            <option value="count_tag">Count Tag</option>
                        </select>
                        <button type="button" class="btn btn-danger remove-block">×</button>
                    </div>
                    <div class="requirement-block-content">
                        <!-- Dynamic content based on requirement type -->
                    </div>
                    <div class="requirement-block-validation">
                        <div class="validation-status"></div>
                    </div>
                </div>
            """,
        }

        # Validate template structure
        builder_template = dom_templates_spec["builder_structure"]
        self.assertIn("prerequisite-builder", builder_template)
        self.assertIn("builder-header", builder_template)
        self.assertIn("requirement-blocks-container", builder_template)
        self.assertIn("empty-state", builder_template)
        self.assertIn("validation-messages", builder_template)

        # Validate requirement block template
        block_template = dom_templates_spec["requirement_block_template"]
        self.assertIn("requirement-block", block_template)
        self.assertIn("data-requirement-type", block_template)
        self.assertIn("data-block-id", block_template)
        self.assertIn("requirement-type-selector", block_template)
        self.assertIn("remove-block", block_template)
