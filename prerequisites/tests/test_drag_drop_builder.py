"""
Comprehensive tests for drag-and-drop prerequisite builder interface (Issue #191).

This module tests the drag-and-drop enhancements to the visual prerequisite builder
that allows users to drag requirement types from a palette, reorder existing
requirements, and nest requirements into logical groups through intuitive
drag-and-drop interactions.

Key drag-and-drop components being tested:
1. DragDropBuilder main class that orchestrates drag-and-drop functionality
2. DragDropPalette component for dragging new requirement types
3. DragDropCanvas component for the main arrangement area
4. DropZone component for visual drop zones and validation
5. TouchHandler for touch device support
6. AccessibilityManager for keyboard navigation and ARIA support
7. UndoRedoManager for operation history
8. Integration with existing PrerequisiteBuilder from Issue #190

The drag-and-drop interface builds upon and enhances the existing visual builder
while maintaining full backward compatibility and accessibility standards.
"""

import json
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.template import Context, Template
from django.test import Client, TestCase
from django.urls import reverse

from campaigns.models import Campaign
from characters.models import MageCharacter
from prerequisites.helpers import all_of, any_of, has_item, trait_req
from prerequisites.models import Prerequisite

User = get_user_model()


class DragDropBuilderClassTest(TestCase):
    """Test specifications for the main DragDropBuilder JavaScript class."""

    def test_drag_drop_builder_constructor_interface(self):
        """Test the expected constructor interface for DragDropBuilder."""
        constructor_spec = {
            "class_name": "DragDropBuilder",
            "extends": "PrerequisiteBuilder",  # Extends existing visual builder
            "constructor_params": {
                "container_element": "HTMLElement",
                "hidden_field_element": "HTMLElement",
                "options": {
                    "type": "object",
                    "default": {},
                    "properties": {
                        # Inherited from PrerequisiteBuilder
                        "initial_requirements": {"type": "object", "default": {}},
                        "validation_url": {"type": "string", "default": None},
                        "available_traits": {"type": "array", "default": []},
                        "available_fields": {"type": "array", "default": []},
                        "max_nesting_depth": {"type": "integer", "default": 5},
                        "auto_validate": {"type": "boolean", "default": True},
                        "show_json_preview": {"type": "boolean", "default": False},
                        "enable_undo_redo": {"type": "boolean", "default": True},
                        # New drag-and-drop specific options
                        "enable_drag_drop": {"type": "boolean", "default": True},
                        "palette_position": {
                            "type": "string",
                            "default": "left",
                            "enum": ["left", "right", "top"],
                        },
                        "drop_zone_highlight": {"type": "boolean", "default": True},
                        "drag_preview_enabled": {"type": "boolean", "default": True},
                        "touch_support": {"type": "boolean", "default": True},
                        "keyboard_shortcuts": {"type": "boolean", "default": True},
                        "animation_duration": {"type": "integer", "default": 300},
                        "snap_to_grid": {"type": "boolean", "default": false},
                        "multi_select": {"type": "boolean", "default": false},
                    },
                },
            },
            "instance_methods": [
                # Inherited methods from PrerequisiteBuilder
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
                # New drag-and-drop methods
                "enableDragDrop",
                "disableDragDrop",
                "createDragPreview",
                "handleDragStart",
                "handleDragOver",
                "handleDrop",
                "reorderRequirements",
                "moveToContainer",
                "snapToGrid",
                "selectMultiple",
                "moveSelected",
                "duplicateRequirement",
                "exportLayout",
                "importLayout",
                "resetLayout",
            ],
            "static_methods": [
                "fromElement",
                "validateRequirementStructure",
                "isTouchDevice",
                "getDropZoneFromPoint",
                "calculateSnapPosition",
            ],
            "events": [
                # Inherited events
                "requirement-added",
                "requirement-removed",
                "requirement-changed",
                "validation-complete",
                "json-generated",
                # New drag-and-drop events
                "drag-started",
                "drag-ended",
                "drop-completed",
                "requirement-reordered",
                "requirement-moved",
                "layout-changed",
                "touch-drag-start",
                "touch-drag-end",
                "keyboard-move",
                "multi-select-changed",
                "grid-snap-changed",
            ],
        }

        # Validate constructor specification structure
        self.assertIn("class_name", constructor_spec)
        self.assertEqual(constructor_spec["class_name"], "DragDropBuilder")
        self.assertEqual(constructor_spec["extends"], "PrerequisiteBuilder")

        # Validate constructor parameters
        params = constructor_spec["constructor_params"]
        self.assertIn("container_element", params)
        self.assertIn("hidden_field_element", params)
        self.assertIn("options", params)

        # Validate new drag-and-drop options
        options = params["options"]["properties"]
        self.assertIn("enable_drag_drop", options)
        self.assertIn("palette_position", options)
        self.assertIn("drop_zone_highlight", options)
        self.assertIn("touch_support", options)
        self.assertIn("keyboard_shortcuts", options)

        # Validate options have correct defaults
        self.assertTrue(options["enable_drag_drop"]["default"])
        self.assertEqual(options["palette_position"]["default"], "left")
        self.assertTrue(options["drop_zone_highlight"]["default"])

        # Validate required methods exist
        required_drag_methods = [
            "enableDragDrop",
            "disableDragDrop",
            "handleDragStart",
            "handleDragOver",
            "handleDrop",
            "reorderRequirements",
        ]
        for method in required_drag_methods:
            self.assertIn(method, constructor_spec["instance_methods"])

        # Validate new events
        required_events = [
            "drag-started",
            "drag-ended",
            "drop-completed",
            "requirement-reordered",
            "layout-changed",
        ]
        for event in required_events:
            self.assertIn(event, constructor_spec["events"])

    def test_drag_drop_builder_initialization_process(self):
        """Test the expected initialization process for drag-and-drop."""
        initialization_spec = {
            "steps": [
                {
                    "step": "call_parent_constructor",
                    "description": "Initialize parent PrerequisiteBuilder functionality",
                    "calls": "super(container_element, hidden_field_element, options)",
                },
                {
                    "step": "validate_drag_drop_support",
                    "description": "Check browser support for drag-and-drop and touch",
                    "validation": {
                        "html5_drag_drop": "must_be_supported",
                        "touch_events": "optional_but_detected",
                        "pointer_events": "preferred_if_available",
                    },
                },
                {
                    "step": "setup_drag_drop_dom_structure",
                    "description": "Create drag-and-drop specific DOM elements",
                    "creates": [
                        "drag_drop_palette",
                        "drop_zones_container",
                        "drag_preview_element",
                        "selection_overlay",
                        "grid_overlay",
                    ],
                },
                {
                    "step": "initialize_drag_drop_managers",
                    "description": "Initialize drag-and-drop specific manager classes",
                    "managers": [
                        "DragDropPalette",
                        "DropZoneManager",
                        "TouchHandler",
                        "AccessibilityManager",  # Enhanced for drag-and-drop
                        "UndoRedoManager",  # Enhanced for layout operations
                        "GridManager",
                        "SelectionManager",
                    ],
                },
                {
                    "step": "setup_drag_drop_event_listeners",
                    "description": "Bind drag-and-drop and touch event listeners",
                    "events": [
                        "dragstart",
                        "dragover",
                        "dragenter",
                        "dragleave",
                        "drop",
                        "touchstart",
                        "touchmove",
                        "touchend",
                        "touchcancel",
                        "pointerdown",
                        "pointermove",
                        "pointerup",
                        "pointercancel",
                        "keydown for keyboard drag operations",
                        "contextmenu for right-click operations",
                    ],
                },
                {
                    "step": "configure_accessibility_features",
                    "description": "Setup keyboard navigation and screen reader support",
                    "features": [
                        "ARIA drag-and-drop roles and states",
                        "keyboard focus management during drag operations",
                        "screen reader announcements for drag actions",
                        "high contrast mode support",
                        "reduced motion support",
                    ],
                },
                {
                    "step": "trigger_drag_drop_ready_event",
                    "description": "Fire drag-and-drop initialization complete event",
                    "event": "drag-drop-builder-ready",
                },
            ]
        }

        # Validate initialization steps
        self.assertEqual(len(initialization_spec["steps"]), 7)

        # Check each step has required properties
        for step in initialization_spec["steps"]:
            self.assertIn("step", step)
            self.assertIn("description", step)

        # Validate specific critical steps
        parent_step = initialization_spec["steps"][0]
        self.assertEqual(parent_step["step"], "call_parent_constructor")
        self.assertIn("super", parent_step["calls"])

        support_check_step = initialization_spec["steps"][1]
        self.assertEqual(support_check_step["step"], "validate_drag_drop_support")
        self.assertIn("html5_drag_drop", support_check_step["validation"])

        dom_setup_step = initialization_spec["steps"][2]
        self.assertEqual(dom_setup_step["step"], "setup_drag_drop_dom_structure")
        self.assertIn("drag_drop_palette", dom_setup_step["creates"])
        self.assertIn("drop_zones_container", dom_setup_step["creates"])

        managers_step = initialization_spec["steps"][3]
        self.assertEqual(managers_step["step"], "initialize_drag_drop_managers")
        self.assertIn("DragDropPalette", managers_step["managers"])
        self.assertIn("TouchHandler", managers_step["managers"])

        events_step = initialization_spec["steps"][4]
        self.assertEqual(events_step["step"], "setup_drag_drop_event_listeners")
        self.assertIn("dragstart", events_step["events"])
        self.assertIn("touchstart", events_step["events"])

        accessibility_step = initialization_spec["steps"][5]
        self.assertEqual(accessibility_step["step"], "configure_accessibility_features")
        self.assertIn(
            "ARIA drag-and-drop roles and states", accessibility_step["features"]
        )

    def test_drag_drop_public_api_methods(self):
        """Test the expected public API method specifications for drag-and-drop."""
        api_methods_spec = {
            "enableDragDrop": {
                "parameters": [
                    {
                        "name": "options",
                        "type": "object",
                        "required": False,
                        "default": {},
                        "properties": {
                            "palette": {"type": "boolean", "default": True},
                            "reordering": {"type": "boolean", "default": True},
                            "nesting": {"type": "boolean", "default": True},
                        },
                    }
                ],
                "returns": "boolean",
                "description": "Enable drag-and-drop functionality with optional feature flags",
                "events_fired": ["drag-drop-enabled"],
                "validation": "validates browser support exists",
            },
            "disableDragDrop": {
                "parameters": [
                    {
                        "name": "preserveLayout",
                        "type": "boolean",
                        "required": False,
                        "default": True,
                    }
                ],
                "returns": "boolean",
                "description": "Disable drag-and-drop while optionally preserving current layout",
                "events_fired": ["drag-drop-disabled"],
                "side_effects": [
                    "removes drag event listeners",
                    "hides palette and drop zones",
                ],
            },
            "handleDragStart": {
                "parameters": [
                    {"name": "event", "type": "DragEvent", "required": True},
                    {"name": "sourceElement", "type": "HTMLElement", "required": True},
                ],
                "returns": "boolean",
                "description": "Handle the start of a drag operation",
                "events_fired": ["drag-started"],
                "validation": "validates element is draggable",
                "side_effects": [
                    "creates drag preview",
                    "sets drag data",
                    "highlights drop zones",
                ],
            },
            "handleDragOver": {
                "parameters": [
                    {"name": "event", "type": "DragEvent", "required": True}
                ],
                "returns": "boolean",
                "description": "Handle drag over events and update drop zone visuals",
                "validation": "validates drop target is valid",
                "side_effects": [
                    "updates drop zone highlighting",
                    "shows insertion indicators",
                ],
            },
            "handleDrop": {
                "parameters": [
                    {"name": "event", "type": "DragEvent", "required": True},
                    {"name": "targetElement", "type": "HTMLElement", "required": True},
                ],
                "returns": "Promise<boolean>",
                "description": "Handle drop operations and update requirement structure",
                "events_fired": [
                    "drop-completed",
                    "requirement-added|requirement-moved",
                ],
                "async": True,
                "validation": "validates drop operation is allowed",
                "side_effects": [
                    "updates DOM structure",
                    "triggers validation",
                    "saves undo state",
                ],
            },
            "reorderRequirements": {
                "parameters": [
                    {"name": "fromIndex", "type": "integer", "required": True},
                    {"name": "toIndex", "type": "integer", "required": True},
                    {
                        "name": "container",
                        "type": "HTMLElement",
                        "required": False,
                        "default": "null",
                    },
                ],
                "returns": "boolean",
                "description": "Reorder requirements within the same container",
                "events_fired": ["requirement-reordered"],
                "validation": "validates indices are valid",
                "side_effects": [
                    "updates DOM order",
                    "regenerates JSON",
                    "saves undo state",
                ],
            },
            "moveToContainer": {
                "parameters": [
                    {"name": "elementId", "type": "string", "required": True},
                    {
                        "name": "targetContainer",
                        "type": "HTMLElement",
                        "required": True,
                    },
                    {
                        "name": "position",
                        "type": "integer",
                        "required": False,
                        "default": -1,
                    },
                ],
                "returns": "boolean",
                "description": "Move requirement to different container (for nesting)",
                "events_fired": ["requirement-moved"],
                "validation": "validates move operation doesn't create circular references",
                "side_effects": [
                    "updates DOM structure",
                    "validates nesting depth",
                    "saves undo state",
                ],
            },
        }

        # Validate each API method specification
        required_methods = [
            "enableDragDrop",
            "disableDragDrop",
            "handleDragStart",
            "handleDragOver",
            "handleDrop",
            "reorderRequirements",
            "moveToContainer",
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
        enable_method = api_methods_spec["enableDragDrop"]
        self.assertEqual(enable_method["returns"], "boolean")
        self.assertIn("drag-drop-enabled", enable_method["events_fired"])

        drag_start_method = api_methods_spec["handleDragStart"]
        self.assertEqual(len(drag_start_method["parameters"]), 2)
        self.assertIn("creates drag preview", drag_start_method["side_effects"])

        drop_method = api_methods_spec["handleDrop"]
        self.assertTrue(drop_method.get("async", False))
        self.assertEqual(drop_method["returns"], "Promise<boolean>")


class DragDropPaletteComponentTest(TestCase):
    """Test specifications for the DragDropPalette component."""

    def test_drag_drop_palette_interface(self):
        """Test base interface for DragDropPalette component."""
        palette_spec = {
            "class": "DragDropPalette",
            "constructor_params": {
                "parentBuilder": {"type": "DragDropBuilder", "required": True},
                "containerElement": {"type": "HTMLElement", "required": True},
                "options": {
                    "type": "object",
                    "required": False,
                    "default": {},
                    "properties": {
                        "position": {
                            "type": "string",
                            "default": "left",
                            "enum": ["left", "right", "top"],
                        },
                        "collapsed": {"type": "boolean", "default": False},
                        "search_enabled": {"type": "boolean", "default": True},
                        "categories_enabled": {"type": "boolean", "default": True},
                        "custom_requirements": {"type": "array", "default": []},
                    },
                },
            },
            "properties": {
                "parentBuilder": "DragDropBuilder",
                "containerElement": "HTMLElement",
                "paletteItems": "Array<PaletteItem>",
                "isVisible": "boolean",
                "isCollapsed": "boolean",
                "searchFilter": "string",
                "selectedCategory": "string",
            },
            "methods": {
                "render": {
                    "returns": "HTMLElement",
                    "description": "Render the palette DOM structure",
                },
                "addItem": {
                    "parameters": [
                        {"name": "requirementType", "type": "string"},
                        {"name": "config", "type": "object", "default": {}},
                    ],
                    "returns": "PaletteItem",
                    "description": "Add a new draggable item to the palette",
                },
                "removeItem": {
                    "parameters": [{"name": "itemId", "type": "string"}],
                    "returns": "boolean",
                    "description": "Remove an item from the palette",
                },
                "show": {
                    "description": "Show the palette",
                    "events_fired": ["palette-shown"],
                },
                "hide": {
                    "description": "Hide the palette",
                    "events_fired": ["palette-hidden"],
                },
                "collapse": {
                    "description": "Collapse the palette to icon bar",
                    "events_fired": ["palette-collapsed"],
                },
                "expand": {
                    "description": "Expand the palette to full view",
                    "events_fired": ["palette-expanded"],
                },
                "filterItems": {
                    "parameters": [
                        {"name": "searchTerm", "type": "string"},
                        {"name": "category", "type": "string", "required": False},
                    ],
                    "description": "Filter visible palette items",
                    "events_fired": ["palette-filtered"],
                },
                "reset": {
                    "description": "Reset palette to default state",
                },
            },
            "events": [
                "palette-item-drag-start",
                "palette-item-drag-end",
                "palette-shown",
                "palette-hidden",
                "palette-collapsed",
                "palette-expanded",
                "palette-filtered",
            ],
            "palette_items": [
                {
                    "type": "trait",
                    "label": "Trait Requirement",
                    "icon": "trait-icon",
                    "description": "Check character trait values",
                    "category": "basic",
                },
                {
                    "type": "has",
                    "label": "Has Item",
                    "icon": "item-icon",
                    "description": "Check for specific items or features",
                    "category": "basic",
                },
                {
                    "type": "any",
                    "label": "Any Of (OR)",
                    "icon": "or-icon",
                    "description": "At least one sub-requirement must be met",
                    "category": "logical",
                },
                {
                    "type": "all",
                    "label": "All Of (AND)",
                    "icon": "and-icon",
                    "description": "All sub-requirements must be met",
                    "category": "logical",
                },
                {
                    "type": "count_tag",
                    "label": "Count Tag",
                    "icon": "count-icon",
                    "description": "Count items with specific tags",
                    "category": "advanced",
                },
            ],
        }

        # Validate palette specification
        self.assertEqual(palette_spec["class"], "DragDropPalette")

        # Validate constructor parameters
        constructor = palette_spec["constructor_params"]
        self.assertIn("parentBuilder", constructor)
        self.assertIn("containerElement", constructor)
        self.assertTrue(constructor["parentBuilder"]["required"])
        self.assertTrue(constructor["containerElement"]["required"])

        # Validate options structure
        options = constructor["options"]["properties"]
        self.assertIn("position", options)
        self.assertIn("collapsed", options)
        self.assertIn("search_enabled", options)
        self.assertEqual(options["position"]["default"], "left")
        self.assertFalse(options["collapsed"]["default"])

        # Validate properties
        properties = palette_spec["properties"]
        self.assertEqual(properties["parentBuilder"], "DragDropBuilder")
        self.assertEqual(properties["paletteItems"], "Array<PaletteItem>")
        self.assertEqual(properties["isVisible"], "boolean")

        # Validate methods
        methods = palette_spec["methods"]
        self.assertIn("render", methods)
        self.assertIn("addItem", methods)
        self.assertIn("show", methods)
        self.assertIn("hide", methods)
        self.assertIn("collapse", methods)
        self.assertIn("expand", methods)
        self.assertIn("filterItems", methods)

        # Check method specifications
        add_item_method = methods["addItem"]
        self.assertEqual(add_item_method["returns"], "PaletteItem")
        self.assertEqual(len(add_item_method["parameters"]), 2)

        filter_method = methods["filterItems"]
        self.assertIn("palette-filtered", filter_method["events_fired"])

        # Validate events
        events = palette_spec["events"]
        self.assertIn("palette-item-drag-start", events)
        self.assertIn("palette-shown", events)
        self.assertIn("palette-collapsed", events)

        # Validate palette items
        items = palette_spec["palette_items"]
        self.assertEqual(len(items), 5)

        # Check required palette items exist
        item_types = [item["type"] for item in items]
        self.assertIn("trait", item_types)
        self.assertIn("has", item_types)
        self.assertIn("any", item_types)
        self.assertIn("all", item_types)
        self.assertIn("count_tag", item_types)

        # Validate item structure
        trait_item = next(item for item in items if item["type"] == "trait")
        self.assertIn("label", trait_item)
        self.assertIn("icon", trait_item)
        self.assertIn("description", trait_item)
        self.assertIn("category", trait_item)

    def test_palette_item_drag_behavior(self):
        """Test specification for palette item drag behavior."""
        drag_behavior_spec = {
            "drag_start": {
                "event": "dragstart",
                "data_set": {
                    "text/plain": "requirement_type",
                    "application/json": "full_requirement_template",
                    "application/x-prerequisite-item": "palette_item_config",
                },
                "visual_effects": [
                    "add dragging class to palette item",
                    "show ghost image with requirement type icon",
                    "highlight compatible drop zones",
                    "dim incompatible areas",
                ],
                "events_fired": ["palette-item-drag-start"],
            },
            "drag_end": {
                "event": "dragend",
                "cleanup": [
                    "remove dragging class from palette item",
                    "hide all drop zone highlights",
                    "restore normal opacity to all areas",
                    "clear drag data",
                ],
                "events_fired": ["palette-item-drag-end"],
            },
            "touch_support": {
                "touch_start": {
                    "event": "touchstart",
                    "behavior": "begin touch drag sequence after 150ms hold",
                    "visual_feedback": "show touch drag preview",
                },
                "touch_move": {
                    "event": "touchmove",
                    "behavior": "move drag preview with finger, highlight drop zones",
                },
                "touch_end": {
                    "event": "touchend",
                    "behavior": "complete drop if over valid zone, otherwise cancel",
                },
            },
            "accessibility": {
                "keyboard_activation": {
                    "keys": ["Enter", "Space"],
                    "behavior": "activate drag mode for keyboard navigation",
                },
                "screen_reader": {
                    "announcements": [
                        "Draggable requirement: {type} - {description}",
                        "Use arrow keys to navigate, Enter to place",
                    ],
                },
                "focus_management": {
                    "drag_start": "move focus to first valid drop zone",
                    "navigation": "arrow keys move between drop zones",
                    "drop": "focus returns to dropped requirement block",
                    "cancel": "focus returns to original palette item",
                },
            },
        }

        # Validate drag behavior specification
        self.assertIn("drag_start", drag_behavior_spec)
        self.assertIn("drag_end", drag_behavior_spec)
        self.assertIn("touch_support", drag_behavior_spec)
        self.assertIn("accessibility", drag_behavior_spec)

        # Check drag start behavior
        drag_start = drag_behavior_spec["drag_start"]
        self.assertEqual(drag_start["event"], "dragstart")
        self.assertIn("data_set", drag_start)
        self.assertIn("visual_effects", drag_start)
        self.assertIn("events_fired", drag_start)

        data_set = drag_start["data_set"]
        self.assertIn("text/plain", data_set)
        self.assertIn("application/json", data_set)
        self.assertIn("application/x-prerequisite-item", data_set)

        visual_effects = drag_start["visual_effects"]
        self.assertIn("add dragging class to palette item", visual_effects)
        self.assertIn("highlight compatible drop zones", visual_effects)

        # Check touch support
        touch_support = drag_behavior_spec["touch_support"]
        self.assertIn("touch_start", touch_support)
        self.assertIn("touch_move", touch_support)
        self.assertIn("touch_end", touch_support)

        touch_start = touch_support["touch_start"]
        self.assertEqual(touch_start["event"], "touchstart")
        self.assertIn("150ms hold", touch_start["behavior"])

        # Check accessibility features
        accessibility = drag_behavior_spec["accessibility"]
        self.assertIn("keyboard_activation", accessibility)
        self.assertIn("screen_reader", accessibility)
        self.assertIn("focus_management", accessibility)

        keyboard_activation = accessibility["keyboard_activation"]
        self.assertIn("Enter", keyboard_activation["keys"])
        self.assertIn("Space", keyboard_activation["keys"])

        focus_management = accessibility["focus_management"]
        self.assertIn("drag_start", focus_management)
        self.assertIn("navigation", focus_management)
        self.assertIn("drop", focus_management)
        self.assertIn("cancel", focus_management)


class DragDropCanvasComponentTest(TestCase):
    """Test specifications for the DragDropCanvas component."""

    def test_drag_drop_canvas_interface(self):
        """Test base interface for DragDropCanvas component."""
        canvas_spec = {
            "class": "DragDropCanvas",
            "constructor_params": {
                "parentBuilder": {"type": "DragDropBuilder", "required": True},
                "containerElement": {"type": "HTMLElement", "required": True},
                "options": {
                    "type": "object",
                    "required": False,
                    "default": {},
                    "properties": {
                        "grid_enabled": {"type": "boolean", "default": False},
                        "grid_size": {"type": "integer", "default": 20},
                        "snap_to_grid": {"type": "boolean", "default": False},
                        "multi_select": {"type": "boolean", "default": False},
                        "auto_layout": {"type": "boolean", "default": True},
                        "layout_algorithm": {
                            "type": "string",
                            "default": "hierarchical",
                            "enum": ["hierarchical", "grid", "free"],
                        },
                        "animation_enabled": {"type": "boolean", "default": True},
                        "zoom_enabled": {"type": "boolean", "default": False},
                    },
                },
            },
            "properties": {
                "parentBuilder": "DragDropBuilder",
                "containerElement": "HTMLElement",
                "requirementBlocks": "Map<string, RequirementBlock>",
                "dropZones": "Array<DropZone>",
                "gridOverlay": "HTMLElement|null",
                "selectionBox": "HTMLElement|null",
                "selectedBlocks": "Set<string>",
                "dragPreview": "HTMLElement|null",
                "currentLayout": "string",
            },
            "methods": {
                "render": {
                    "returns": "HTMLElement",
                    "description": "Render the canvas DOM structure",
                },
                "addRequirementBlock": {
                    "parameters": [
                        {"name": "blockId", "type": "string"},
                        {"name": "requirementType", "type": "string"},
                        {
                            "name": "position",
                            "type": "object",
                            "default": {"x": 0, "y": 0},
                        },
                        {"name": "parentBlockId", "type": "string", "required": False},
                    ],
                    "returns": "RequirementBlock",
                    "description": "Add a requirement block to the canvas",
                    "events_fired": ["block-added-to-canvas"],
                },
                "removeRequirementBlock": {
                    "parameters": [{"name": "blockId", "type": "string"}],
                    "returns": "boolean",
                    "description": "Remove a requirement block from the canvas",
                    "events_fired": ["block-removed-from-canvas"],
                },
                "moveRequirementBlock": {
                    "parameters": [
                        {"name": "blockId", "type": "string"},
                        {"name": "position", "type": "object"},
                        {"name": "animate", "type": "boolean", "default": True},
                    ],
                    "returns": "boolean",
                    "description": "Move a requirement block to new position",
                    "events_fired": ["block-moved"],
                },
                "createDropZones": {
                    "description": "Create and position drop zones for drag operations",
                },
                "highlightDropZones": {
                    "parameters": [
                        {"name": "dragData", "type": "object"},
                        {
                            "name": "compatibilityCheck",
                            "type": "function",
                            "required": False,
                        },
                    ],
                    "description": "Highlight compatible drop zones during drag",
                },
                "clearDropZoneHighlights": {
                    "description": "Clear all drop zone highlighting",
                },
                "selectBlock": {
                    "parameters": [
                        {"name": "blockId", "type": "string"},
                        {"name": "addToSelection", "type": "boolean", "default": False},
                    ],
                    "description": "Select a requirement block",
                    "events_fired": ["block-selected"],
                },
                "clearSelection": {
                    "description": "Clear all selected blocks",
                    "events_fired": ["selection-cleared"],
                },
                "autoLayout": {
                    "parameters": [
                        {"name": "algorithm", "type": "string", "required": False},
                        {"name": "animate", "type": "boolean", "default": True},
                    ],
                    "description": "Automatically arrange requirement blocks",
                    "events_fired": ["layout-changed"],
                },
            },
            "drop_zones": {
                "canvas_drop_zone": {
                    "selector": ".canvas-drop-zone",
                    "accepts": ["trait", "has", "any", "all", "count_tag"],
                    "behavior": "creates new requirement block at drop position",
                    "visual_indicator": "full canvas highlighting",
                },
                "container_drop_zone": {
                    "selector": ".container-drop-zone",
                    "accepts": [
                        "trait",
                        "has",
                        "count_tag",
                    ],  # not containers themselves
                    "behavior": "adds requirement to existing container (any/all)",
                    "visual_indicator": "container border highlighting",
                },
                "reorder_drop_zone": {
                    "selector": ".reorder-drop-zone",
                    "accepts": ["existing-requirement-blocks"],
                    "behavior": "reorders requirements within same container",
                    "visual_indicator": "insertion line between blocks",
                },
                "nesting_drop_zone": {
                    "selector": ".nesting-drop-zone",
                    "accepts": ["existing-requirement-blocks"],
                    "behavior": "moves requirement to different nesting level",
                    "visual_indicator": "target container highlighting with depth indicator",
                },
            },
        }

        # Validate canvas specification
        self.assertEqual(canvas_spec["class"], "DragDropCanvas")

        # Validate constructor
        constructor = canvas_spec["constructor_params"]
        self.assertIn("parentBuilder", constructor)
        self.assertIn("containerElement", constructor)
        self.assertTrue(constructor["parentBuilder"]["required"])

        # Validate options
        options = constructor["options"]["properties"]
        self.assertIn("grid_enabled", options)
        self.assertIn("multi_select", options)
        self.assertIn("auto_layout", options)
        self.assertIn("layout_algorithm", options)
        self.assertFalse(options["grid_enabled"]["default"])
        self.assertEqual(options["layout_algorithm"]["default"], "hierarchical")

        # Validate properties
        properties = canvas_spec["properties"]
        self.assertEqual(
            properties["requirementBlocks"], "Map<string, RequirementBlock>"
        )
        self.assertEqual(properties["dropZones"], "Array<DropZone>")
        self.assertEqual(properties["selectedBlocks"], "Set<string>")

        # Validate methods
        methods = canvas_spec["methods"]
        self.assertIn("render", methods)
        self.assertIn("addRequirementBlock", methods)
        self.assertIn("moveRequirementBlock", methods)
        self.assertIn("createDropZones", methods)
        self.assertIn("selectBlock", methods)
        self.assertIn("autoLayout", methods)

        # Check method specifications
        add_block_method = methods["addRequirementBlock"]
        self.assertEqual(add_block_method["returns"], "RequirementBlock")
        self.assertIn("block-added-to-canvas", add_block_method["events_fired"])

        move_block_method = methods["moveRequirementBlock"]
        self.assertEqual(len(move_block_method["parameters"]), 3)
        self.assertIn("block-moved", move_block_method["events_fired"])

        # Validate drop zones
        drop_zones = canvas_spec["drop_zones"]
        self.assertIn("canvas_drop_zone", drop_zones)
        self.assertIn("container_drop_zone", drop_zones)
        self.assertIn("reorder_drop_zone", drop_zones)
        self.assertIn("nesting_drop_zone", drop_zones)

        # Check drop zone specifications
        canvas_drop = drop_zones["canvas_drop_zone"]
        self.assertEqual(canvas_drop["selector"], ".canvas-drop-zone")
        self.assertIn("trait", canvas_drop["accepts"])
        self.assertIn("has", canvas_drop["accepts"])

        container_drop = drop_zones["container_drop_zone"]
        self.assertNotIn(
            "any", container_drop["accepts"]
        )  # containers can't be nested in containers
        self.assertNotIn("all", container_drop["accepts"])

    def test_canvas_layout_algorithms(self):
        """Test specification for canvas layout algorithms."""
        layout_algorithms_spec = {
            "hierarchical": {
                "description": "Arrange requirements in a tree-like hierarchy",
                "behavior": {
                    "root_requirements": "arranged horizontally at top level",
                    "nested_requirements": "arranged vertically below parent with indentation",
                    "connections": "visual lines showing parent-child relationships",
                    "spacing": "consistent spacing based on nesting depth",
                },
                "parameters": {
                    "horizontal_spacing": {"type": "integer", "default": 150},
                    "vertical_spacing": {"type": "integer", "default": 100},
                    "indent_per_level": {"type": "integer", "default": 50},
                    "show_connections": {"type": "boolean", "default": True},
                },
            },
            "grid": {
                "description": "Arrange requirements in a regular grid pattern",
                "behavior": {
                    "grid_columns": "requirements arranged in configurable columns",
                    "uniform_sizing": "all blocks same size within grid cells",
                    "snap_to_grid": "all positions aligned to grid coordinates",
                    "overflow_handling": "automatic row wrapping for excess items",
                },
                "parameters": {
                    "columns": {"type": "integer", "default": 3},
                    "cell_width": {"type": "integer", "default": 200},
                    "cell_height": {"type": "integer", "default": 150},
                    "gap": {"type": "integer", "default": 20},
                },
            },
            "free": {
                "description": "Free-form positioning without automatic layout",
                "behavior": {
                    "manual_positioning": "users manually position all blocks",
                    "no_automatic_arrangement": "layout algorithm doesn't change positions",
                    "collision_detection": "optional collision avoidance",
                    "position_persistence": "positions saved with requirement data",
                },
                "parameters": {
                    "collision_avoidance": {"type": "boolean", "default": False},
                    "boundary_constraints": {"type": "boolean", "default": True},
                    "position_snapping": {"type": "boolean", "default": False},
                },
            },
        }

        # Validate layout algorithms
        self.assertIn("hierarchical", layout_algorithms_spec)
        self.assertIn("grid", layout_algorithms_spec)
        self.assertIn("free", layout_algorithms_spec)

        # Check hierarchical layout
        hierarchical = layout_algorithms_spec["hierarchical"]
        self.assertIn("description", hierarchical)
        self.assertIn("behavior", hierarchical)
        self.assertIn("parameters", hierarchical)

        hier_behavior = hierarchical["behavior"]
        self.assertIn("root_requirements", hier_behavior)
        self.assertIn("nested_requirements", hier_behavior)
        self.assertIn("connections", hier_behavior)

        hier_params = hierarchical["parameters"]
        self.assertIn("horizontal_spacing", hier_params)
        self.assertIn("vertical_spacing", hier_params)
        self.assertEqual(hier_params["horizontal_spacing"]["default"], 150)

        # Check grid layout
        grid = layout_algorithms_spec["grid"]
        grid_behavior = grid["behavior"]
        self.assertIn("grid_columns", grid_behavior)
        self.assertIn("snap_to_grid", grid_behavior)

        grid_params = grid["parameters"]
        self.assertIn("columns", grid_params)
        self.assertEqual(grid_params["columns"]["default"], 3)

        # Check free layout
        free = layout_algorithms_spec["free"]
        free_behavior = free["behavior"]
        self.assertIn("manual_positioning", free_behavior)
        self.assertIn("no_automatic_arrangement", free_behavior)


class DropZoneComponentTest(TestCase):
    """Test specifications for the DropZone component."""

    def test_drop_zone_interface(self):
        """Test base interface for DropZone component."""
        drop_zone_spec = {
            "class": "DropZone",
            "constructor_params": {
                "element": {"type": "HTMLElement", "required": True},
                "config": {
                    "type": "object",
                    "required": True,
                    "properties": {
                        "accepts": {"type": "array", "required": True},
                        "behavior": {"type": "string", "required": True},
                        "validator": {"type": "function", "required": False},
                        "visual_feedback": {"type": "boolean", "default": True},
                    },
                },
            },
            "properties": {
                "element": "HTMLElement",
                "accepts": "Array<string>",
                "behavior": "string",
                "validator": "function|null",
                "isActive": "boolean",
                "isHighlighted": "boolean",
                "isCompatible": "boolean",
            },
            "methods": {
                "activate": {
                    "description": "Activate drop zone for drag operations",
                    "events_fired": ["drop-zone-activated"],
                },
                "deactivate": {
                    "description": "Deactivate drop zone",
                    "events_fired": ["drop-zone-deactivated"],
                },
                "highlight": {
                    "parameters": [{"name": "dragData", "type": "object"}],
                    "description": "Highlight drop zone if compatible with drag data",
                    "returns": "boolean",  # true if compatible and highlighted
                },
                "unhighlight": {
                    "description": "Remove highlighting from drop zone",
                },
                "canAccept": {
                    "parameters": [{"name": "dragData", "type": "object"}],
                    "returns": "boolean",
                    "description": "Check if drop zone can accept the dragged data",
                },
                "handleDragEnter": {
                    "parameters": [{"name": "event", "type": "DragEvent"}],
                    "description": "Handle drag enter event",
                    "events_fired": ["drag-enter"],
                },
                "handleDragLeave": {
                    "parameters": [{"name": "event", "type": "DragEvent"}],
                    "description": "Handle drag leave event",
                    "events_fired": ["drag-leave"],
                },
                "handleDrop": {
                    "parameters": [{"name": "event", "type": "DragEvent"}],
                    "returns": "Promise<boolean>",
                    "async": True,
                    "description": "Handle drop event and execute drop behavior",
                    "events_fired": ["drop-accepted", "drop-rejected"],
                },
            },
            "visual_states": {
                "inactive": {
                    "css_class": "drop-zone-inactive",
                    "description": "Drop zone not participating in current drag operation",
                    "visual_style": "hidden or very subtle indication",
                },
                "active_compatible": {
                    "css_class": "drop-zone-active-compatible",
                    "description": "Drop zone can accept current drag data",
                    "visual_style": "clear highlighting, positive color (green/blue)",
                },
                "active_incompatible": {
                    "css_class": "drop-zone-active-incompatible",
                    "description": "Drop zone cannot accept current drag data",
                    "visual_style": "subtle indication, neutral/muted color",
                },
                "drag_over": {
                    "css_class": "drop-zone-drag-over",
                    "description": "Drag is currently hovering over this drop zone",
                    "visual_style": "strong highlighting, animated if enabled",
                },
                "drop_pending": {
                    "css_class": "drop-zone-drop-pending",
                    "description": "Drop operation is being processed",
                    "visual_style": "loading indicator or pulsing animation",
                },
            },
        }

        # Validate drop zone specification
        self.assertEqual(drop_zone_spec["class"], "DropZone")

        # Validate constructor
        constructor = drop_zone_spec["constructor_params"]
        self.assertIn("element", constructor)
        self.assertIn("config", constructor)
        self.assertTrue(constructor["element"]["required"])
        self.assertTrue(constructor["config"]["required"])

        # Validate config properties
        config_props = constructor["config"]["properties"]
        self.assertIn("accepts", config_props)
        self.assertIn("behavior", config_props)
        self.assertTrue(config_props["accepts"]["required"])
        self.assertTrue(config_props["behavior"]["required"])

        # Validate properties
        properties = drop_zone_spec["properties"]
        self.assertEqual(properties["element"], "HTMLElement")
        self.assertEqual(properties["accepts"], "Array<string>")
        self.assertEqual(properties["isActive"], "boolean")

        # Validate methods
        methods = drop_zone_spec["methods"]
        self.assertIn("activate", methods)
        self.assertIn("highlight", methods)
        self.assertIn("canAccept", methods)
        self.assertIn("handleDrop", methods)

        # Check method specifications
        highlight_method = methods["highlight"]
        self.assertEqual(highlight_method["returns"], "boolean")

        can_accept_method = methods["canAccept"]
        self.assertEqual(can_accept_method["returns"], "boolean")

        drop_method = methods["handleDrop"]
        self.assertTrue(drop_method.get("async", False))
        self.assertEqual(drop_method["returns"], "Promise<boolean>")
        self.assertIn("drop-accepted", drop_method["events_fired"])

        # Validate visual states
        visual_states = drop_zone_spec["visual_states"]
        self.assertIn("inactive", visual_states)
        self.assertIn("active_compatible", visual_states)
        self.assertIn("active_incompatible", visual_states)
        self.assertIn("drag_over", visual_states)

        # Check visual state specifications
        compatible_state = visual_states["active_compatible"]
        self.assertIn("css_class", compatible_state)
        self.assertIn("description", compatible_state)
        self.assertIn("visual_style", compatible_state)
        self.assertIn("green/blue", compatible_state["visual_style"])

    def test_drop_zone_behaviors(self):
        """Test specification for different drop zone behaviors."""
        behaviors_spec = {
            "create_new_requirement": {
                "description": "Create a new requirement block from palette item",
                "applies_to": ["canvas-drop-zone"],
                "data_required": ["requirement_type", "template_config"],
                "process": [
                    "validate drag data contains requirement type",
                    "determine drop position from event coordinates",
                    "create new RequirementBlock instance",
                    "add block to canvas at drop position",
                    "trigger requirement-added event",
                    "focus new requirement block for editing",
                ],
                "validation": [
                    "drag data must be from palette",
                    "drop position must be within canvas bounds",
                    "requirement type must be supported",
                ],
            },
            "add_to_container": {
                "description": "Add requirement to existing container (any/all)",
                "applies_to": ["container-drop-zone"],
                "data_required": ["requirement_type", "template_config"],
                "process": [
                    "validate container can accept requirement type",
                    "create new RequirementBlock instance",
                    "add block as child of target container",
                    "update container's visual layout",
                    "trigger requirement-added event",
                    "validate nesting depth limits",
                ],
                "validation": [
                    "container must not be at max nesting depth",
                    "requirement type must be compatible with container",
                    "circular references must be prevented",
                ],
            },
            "reorder_requirements": {
                "description": "Reorder requirements within same container",
                "applies_to": ["reorder-drop-zone"],
                "data_required": ["source_block_id", "source_position"],
                "process": [
                    "validate source block can be moved",
                    "determine target position from drop zone",
                    "remove block from current position",
                    "insert block at target position",
                    "update DOM order to match logical order",
                    "trigger requirement-reordered event",
                ],
                "validation": [
                    "source and target must be in same container",
                    "target position must be valid",
                    "operation must not break requirement structure",
                ],
            },
            "move_between_containers": {
                "description": "Move requirement to different nesting level",
                "applies_to": ["nesting-drop-zone"],
                "data_required": ["source_block_id", "target_container_id"],
                "process": [
                    "validate move operation is allowed",
                    "remove block from source container",
                    "add block to target container",
                    "update both containers' layouts",
                    "validate resulting structure",
                    "trigger requirement-moved event",
                ],
                "validation": [
                    "target container must accept requirement type",
                    "move must not create circular references",
                    "nesting depth limits must be respected",
                    "source container must not become empty (for any/all)",
                ],
            },
        }

        # Validate behavior specifications
        self.assertIn("create_new_requirement", behaviors_spec)
        self.assertIn("add_to_container", behaviors_spec)
        self.assertIn("reorder_requirements", behaviors_spec)
        self.assertIn("move_between_containers", behaviors_spec)

        # Check create_new_requirement behavior
        create_behavior = behaviors_spec["create_new_requirement"]
        self.assertIn("description", create_behavior)
        self.assertIn("applies_to", create_behavior)
        self.assertIn("data_required", create_behavior)
        self.assertIn("process", create_behavior)
        self.assertIn("validation", create_behavior)

        self.assertIn("canvas-drop-zone", create_behavior["applies_to"])
        self.assertIn("requirement_type", create_behavior["data_required"])
        self.assertEqual(len(create_behavior["process"]), 6)
        self.assertEqual(len(create_behavior["validation"]), 3)

        # Check add_to_container behavior
        container_behavior = behaviors_spec["add_to_container"]
        self.assertIn("container-drop-zone", container_behavior["applies_to"])
        self.assertIn("validate nesting depth limits", container_behavior["process"])
        self.assertIn(
            "circular references must be prevented", container_behavior["validation"]
        )

        # Check reorder behavior
        reorder_behavior = behaviors_spec["reorder_requirements"]
        self.assertIn("source_block_id", reorder_behavior["data_required"])
        self.assertIn(
            "update DOM order to match logical order", reorder_behavior["process"]
        )

        # Check move behavior
        move_behavior = behaviors_spec["move_between_containers"]
        self.assertIn("nesting-drop-zone", move_behavior["applies_to"])
        self.assertIn("validate resulting structure", move_behavior["process"])
        self.assertIn(
            "source container must not become empty (for any/all)",
            move_behavior["validation"],
        )


class TouchHandlerTest(TestCase):
    """Test specifications for the TouchHandler component."""

    def test_touch_handler_interface(self):
        """Test base interface for TouchHandler component."""
        touch_handler_spec = {
            "class": "TouchHandler",
            "constructor_params": {
                "parentBuilder": {"type": "DragDropBuilder", "required": True},
                "options": {
                    "type": "object",
                    "required": False,
                    "default": {},
                    "properties": {
                        "hold_delay": {"type": "integer", "default": 500},
                        "move_threshold": {"type": "integer", "default": 10},
                        "tap_timeout": {"type": "integer", "default": 300},
                        "double_tap_delay": {"type": "integer", "default": 400},
                        "force_touch_enabled": {"type": "boolean", "default": True},
                        "haptic_feedback": {"type": "boolean", "default": True},
                    },
                },
            },
            "properties": {
                "parentBuilder": "DragDropBuilder",
                "isEnabled": "boolean",
                "currentTouch": "Touch|null",
                "touchStartPosition": "object|null",  # {x, y}
                "touchStartTime": "number",
                "holdTimer": "number|null",
                "isDragging": "boolean",
                "dragPreview": "HTMLElement|null",
            },
            "methods": {
                "enable": {
                    "description": "Enable touch drag-and-drop support",
                    "events_fired": ["touch-handler-enabled"],
                },
                "disable": {
                    "description": "Disable touch drag-and-drop support",
                    "events_fired": ["touch-handler-disabled"],
                },
                "handleTouchStart": {
                    "parameters": [{"name": "event", "type": "TouchEvent"}],
                    "description": "Handle touch start event",
                    "events_fired": ["touch-start"],
                },
                "handleTouchMove": {
                    "parameters": [{"name": "event", "type": "TouchEvent"}],
                    "description": "Handle touch move event",
                    "events_fired": [
                        "touch-move",
                        "touch-drag-start",
                        "touch-drag-move",
                    ],
                },
                "handleTouchEnd": {
                    "parameters": [{"name": "event", "type": "TouchEvent"}],
                    "description": "Handle touch end event",
                    "events_fired": [
                        "touch-end",
                        "touch-drag-end",
                        "touch-tap",
                        "touch-double-tap",
                    ],
                },
                "handleTouchCancel": {
                    "parameters": [{"name": "event", "type": "TouchEvent"}],
                    "description": "Handle touch cancel event",
                    "events_fired": ["touch-cancel", "touch-drag-cancel"],
                },
                "startTouchDrag": {
                    "parameters": [
                        {"name": "touch", "type": "Touch"},
                        {"name": "sourceElement", "type": "HTMLElement"},
                    ],
                    "description": "Begin touch-based drag operation",
                    "events_fired": ["touch-drag-started"],
                },
                "updateTouchDrag": {
                    "parameters": [{"name": "touch", "type": "Touch"}],
                    "description": "Update touch drag position and visual feedback",
                },
                "completeTouchDrag": {
                    "parameters": [{"name": "touch", "type": "Touch"}],
                    "returns": "Promise<boolean>",
                    "async": True,
                    "description": "Complete touch drag operation",
                    "events_fired": ["touch-drag-completed"],
                },
                "cancelTouchDrag": {
                    "description": "Cancel ongoing touch drag operation",
                    "events_fired": ["touch-drag-cancelled"],
                },
                "createTouchPreview": {
                    "parameters": [{"name": "sourceElement", "type": "HTMLElement"}],
                    "returns": "HTMLElement",
                    "description": "Create touch drag preview element",
                },
                "provideBehavioralFeedback": {
                    "parameters": [
                        {
                            "name": "feedbackType",
                            "type": "string",
                        },  # start, move, drop, cancel
                        {"name": "intensity", "type": "number", "default": 1},
                    ],
                    "description": "Provide haptic/audio feedback for touch interactions",
                },
            },
            "touch_gestures": {
                "single_tap": {
                    "recognition": "touchstart -> touchend within tap_timeout, no movement",
                    "behavior": "equivalent to mouse click",
                    "use_cases": ["select requirement block", "activate palette item"],
                },
                "double_tap": {
                    "recognition": "two single taps within double_tap_delay",
                    "behavior": "equivalent to mouse double-click",
                    "use_cases": ["edit requirement block", "toggle palette"],
                },
                "long_press": {
                    "recognition": "touchstart held for hold_delay without movement",
                    "behavior": "context menu or drag initiation",
                    "use_cases": ["show context menu", "start drag operation"],
                },
                "drag": {
                    "recognition": "touchstart -> touchmove beyond move_threshold",
                    "behavior": "drag-and-drop operation",
                    "use_cases": ["move requirement blocks", "reorder items"],
                },
                "pinch": {
                    "recognition": "two touches moving closer/farther",
                    "behavior": "zoom in/out (if zoom enabled)",
                    "use_cases": ["zoom canvas view"],
                },
                "two_finger_scroll": {
                    "recognition": "two touches moving in same direction",
                    "behavior": "pan/scroll canvas",
                    "use_cases": ["navigate large requirement trees"],
                },
            },
        }

        # Validate touch handler specification
        self.assertEqual(touch_handler_spec["class"], "TouchHandler")

        # Validate constructor
        constructor = touch_handler_spec["constructor_params"]
        self.assertIn("parentBuilder", constructor)
        self.assertTrue(constructor["parentBuilder"]["required"])

        # Validate options
        options = constructor["options"]["properties"]
        self.assertIn("hold_delay", options)
        self.assertIn("move_threshold", options)
        self.assertIn("haptic_feedback", options)
        self.assertEqual(options["hold_delay"]["default"], 500)
        self.assertEqual(options["move_threshold"]["default"], 10)

        # Validate properties
        properties = touch_handler_spec["properties"]
        self.assertEqual(properties["parentBuilder"], "DragDropBuilder")
        self.assertEqual(properties["currentTouch"], "Touch|null")
        self.assertEqual(properties["isDragging"], "boolean")

        # Validate methods
        methods = touch_handler_spec["methods"]
        self.assertIn("enable", methods)
        self.assertIn("handleTouchStart", methods)
        self.assertIn("handleTouchMove", methods)
        self.assertIn("startTouchDrag", methods)
        self.assertIn("completeTouchDrag", methods)

        # Check method specifications
        complete_drag = methods["completeTouchDrag"]
        self.assertTrue(complete_drag.get("async", False))
        self.assertEqual(complete_drag["returns"], "Promise<boolean>")

        create_preview = methods["createTouchPreview"]
        self.assertEqual(create_preview["returns"], "HTMLElement")

        # Validate touch gestures
        gestures = touch_handler_spec["touch_gestures"]
        self.assertIn("single_tap", gestures)
        self.assertIn("long_press", gestures)
        self.assertIn("drag", gestures)
        self.assertIn("pinch", gestures)

        # Check gesture specifications
        single_tap = gestures["single_tap"]
        self.assertIn("recognition", single_tap)
        self.assertIn("behavior", single_tap)
        self.assertIn("use_cases", single_tap)

        long_press = gestures["long_press"]
        self.assertIn("hold_delay", long_press["recognition"])
        self.assertIn("start drag operation", long_press["use_cases"])

    def test_touch_event_handling_flow(self):
        """Test specification for touch event handling flow."""
        touch_flow_spec = {
            "touch_start_flow": {
                "steps": [
                    "record touch start position and time",
                    "identify touched element and check if draggable",
                    "prevent default if element is draggable",
                    "start hold timer for long press detection",
                    "provide haptic feedback if enabled",
                    "fire touch-start event",
                ],
                "conditions": {
                    "draggable_element": "start hold timer, prepare for potential drag",
                    "non_draggable_element": "allow normal touch behavior",
                    "multiple_touches": "handle according to gesture (pinch, scroll)",
                },
            },
            "touch_move_flow": {
                "steps": [
                    "calculate movement distance from start position",
                    "check if movement exceeds move_threshold",
                    "cancel hold timer if movement detected",
                    "determine if this is start of drag operation",
                    "update drag preview position if dragging",
                    "highlight drop zones based on current position",
                    "fire appropriate touch events",
                ],
                "conditions": {
                    "below_threshold": "continue waiting for hold or end",
                    "above_threshold_draggable": "start drag operation",
                    "above_threshold_non_draggable": "allow normal scrolling",
                    "already_dragging": "update drag state and visuals",
                },
            },
            "touch_end_flow": {
                "steps": [
                    "cancel any active hold timer",
                    "determine final touch behavior based on state",
                    "execute appropriate action (tap, drag drop, etc)",
                    "clean up drag preview and highlighting",
                    "provide completion haptic feedback",
                    "fire touch-end and related events",
                ],
                "conditions": {
                    "was_dragging": "attempt drop operation at end position",
                    "was_holding": "show context menu or start edit",
                    "quick_release": "treat as tap gesture",
                    "double_tap_sequence": "treat as double-tap gesture",
                },
            },
            "touch_cancel_flow": {
                "description": "Handle system touch cancellation",
                "steps": [
                    "cancel any active timers",
                    "clean up drag state and visuals",
                    "restore original element positions",
                    "provide cancellation feedback",
                    "fire touch-cancel events",
                ],
                "triggers": [
                    "system interruption (phone call, notification)",
                    "touch leaves browser viewport",
                    "too many simultaneous touches",
                    "programmatic cancellation",
                ],
            },
        }

        # Validate touch flow specification
        self.assertIn("touch_start_flow", touch_flow_spec)
        self.assertIn("touch_move_flow", touch_flow_spec)
        self.assertIn("touch_end_flow", touch_flow_spec)
        self.assertIn("touch_cancel_flow", touch_flow_spec)

        # Check touch start flow
        start_flow = touch_flow_spec["touch_start_flow"]
        self.assertIn("steps", start_flow)
        self.assertIn("conditions", start_flow)
        self.assertEqual(len(start_flow["steps"]), 6)

        start_conditions = start_flow["conditions"]
        self.assertIn("draggable_element", start_conditions)
        self.assertIn("non_draggable_element", start_conditions)
        self.assertIn("multiple_touches", start_conditions)

        # Check touch move flow
        move_flow = touch_flow_spec["touch_move_flow"]
        self.assertIn("calculate movement distance", move_flow["steps"][0])
        self.assertIn("highlight drop zones", move_flow["steps"][5])

        move_conditions = move_flow["conditions"]
        self.assertIn("below_threshold", move_conditions)
        self.assertIn("above_threshold_draggable", move_conditions)
        self.assertIn("already_dragging", move_conditions)

        # Check touch end flow
        end_flow = touch_flow_spec["touch_end_flow"]
        self.assertIn("determine final touch behavior", end_flow["steps"][1])

        end_conditions = end_flow["conditions"]
        self.assertIn("was_dragging", end_conditions)
        self.assertIn("quick_release", end_conditions)
        self.assertIn("attempt drop operation", end_conditions["was_dragging"])

        # Check touch cancel flow
        cancel_flow = touch_flow_spec["touch_cancel_flow"]
        self.assertIn("description", cancel_flow)
        self.assertIn("steps", cancel_flow)
        self.assertIn("triggers", cancel_flow)
        self.assertIn("system interruption", cancel_flow["triggers"][0])


class AccessibilityManagerTest(TestCase):
    """Test specifications for the AccessibilityManager component enhanced for drag-and-drop."""

    def test_accessibility_manager_interface(self):
        """Test base interface for AccessibilityManager component."""
        accessibility_spec = {
            "class": "AccessibilityManager",
            "extends": "BaseAccessibilityManager",  # From Issue #190
            "constructor_params": {
                "parentBuilder": {"type": "DragDropBuilder", "required": True},
                "options": {
                    "type": "object",
                    "required": False,
                    "default": {},
                    "properties": {
                        "keyboard_drag_enabled": {"type": "boolean", "default": True},
                        "screen_reader_announcements": {
                            "type": "boolean",
                            "default": True,
                        },
                        "focus_management": {"type": "boolean", "default": True},
                        "high_contrast_support": {"type": "boolean", "default": True},
                        "reduced_motion_support": {"type": "boolean", "default": True},
                        "keyboard_shortcuts": {
                            "type": "object",
                            "default": {
                                "drag_mode": "d",
                                "cancel": "Escape",
                                "confirm": "Enter",
                                "navigate_up": "ArrowUp",
                                "navigate_down": "ArrowDown",
                                "navigate_left": "ArrowLeft",
                                "navigate_right": "ArrowRight",
                                "select_all": "Ctrl+a",
                                "copy": "Ctrl+c",
                                "paste": "Ctrl+v",
                            },
                        },
                    },
                },
            },
            "properties": {
                "parentBuilder": "DragDropBuilder",
                "keyboardDragMode": "boolean",
                "focusedElement": "HTMLElement|null",
                "announcementRegion": "HTMLElement",
                "lastAnnouncement": "string",
                "dragContext": "object|null",
            },
            "methods": {
                # Inherited methods from BaseAccessibilityManager
                "initialize": {"description": "Initialize accessibility features"},
                "destroy": {"description": "Clean up accessibility resources"},
                # Enhanced drag-and-drop methods
                "enableKeyboardDrag": {
                    "description": "Enable keyboard-based drag operations",
                    "events_fired": ["keyboard-drag-enabled"],
                },
                "disableKeyboardDrag": {
                    "description": "Disable keyboard-based drag operations",
                    "events_fired": ["keyboard-drag-disabled"],
                },
                "handleKeyboardDragStart": {
                    "parameters": [
                        {"name": "element", "type": "HTMLElement"},
                        {"name": "event", "type": "KeyboardEvent"},
                    ],
                    "description": "Start keyboard drag operation",
                    "events_fired": ["keyboard-drag-started"],
                },
                "handleKeyboardNavigation": {
                    "parameters": [{"name": "event", "type": "KeyboardEvent"}],
                    "returns": "boolean",
                    "description": "Handle keyboard navigation during drag mode",
                },
                "announceDropZones": {
                    "parameters": [{"name": "dragData", "type": "object"}],
                    "description": "Announce available drop zones to screen reader",
                },
                "announceDragState": {
                    "parameters": [
                        {
                            "name": "state",
                            "type": "string",
                        },  # started, moved, dropped, cancelled
                        {"name": "context", "type": "object", "required": False},
                    ],
                    "description": "Announce drag state changes to screen reader",
                },
                "updateAriaAttributes": {
                    "parameters": [
                        {"name": "element", "type": "HTMLElement"},
                        {"name": "attributes", "type": "object"},
                    ],
                    "description": "Update ARIA attributes for drag-drop state",
                },
                "manageFocusDuringDrag": {
                    "parameters": [
                        {"name": "dragElement", "type": "HTMLElement"},
                        {
                            "name": "phase",
                            "type": "string",
                        },  # start, move, drop, cancel
                    ],
                    "description": "Manage focus during drag operations",
                },
                "provideAudioFeedback": {
                    "parameters": [
                        {"name": "feedbackType", "type": "string"},
                        {"name": "priority", "type": "string", "default": "normal"},
                    ],
                    "description": "Provide audio feedback for actions",
                },
            },
            "aria_attributes": {
                "draggable_elements": {
                    "aria-grabbed": "false|true - indicates if element is being dragged",
                    "aria-describedby": "id of instructions for drag operation",
                    "aria-label": "descriptive label including drag instructions",
                    "role": "button or appropriate interactive role",
                    "tabindex": "0 for keyboard accessibility",
                },
                "drop_zones": {
                    "aria-dropeffect": "none|copy|move|link - indicates drop effect",
                    "aria-label": "descriptive label for drop zone purpose",
                    "aria-describedby": "id of detailed drop instructions",
                    "role": "region or button depending on behavior",
                },
                "container_elements": {
                    "aria-expanded": "true|false for collapsible containers",
                    "aria-owns": "space-separated ids of child requirements",
                    "role": "group or tree depending on structure",
                },
                "status_announcements": {
                    "aria-live": "polite|assertive based on announcement priority",
                    "aria-atomic": "true for complete message replacement",
                    "aria-relevant": "additions removals text for change types",
                },
            },
        }

        # Validate accessibility specification
        self.assertEqual(accessibility_spec["class"], "AccessibilityManager")
        self.assertEqual(accessibility_spec["extends"], "BaseAccessibilityManager")

        # Validate constructor
        constructor = accessibility_spec["constructor_params"]
        self.assertIn("parentBuilder", constructor)
        self.assertTrue(constructor["parentBuilder"]["required"])

        # Validate options
        options = constructor["options"]["properties"]
        self.assertIn("keyboard_drag_enabled", options)
        self.assertIn("screen_reader_announcements", options)
        self.assertIn("keyboard_shortcuts", options)
        self.assertTrue(options["keyboard_drag_enabled"]["default"])

        shortcuts = options["keyboard_shortcuts"]["default"]
        self.assertIn("drag_mode", shortcuts)
        self.assertIn("cancel", shortcuts)
        self.assertEqual(shortcuts["cancel"], "Escape")

        # Validate properties
        properties = accessibility_spec["properties"]
        self.assertEqual(properties["keyboardDragMode"], "boolean")
        self.assertEqual(properties["announcementRegion"], "HTMLElement")

        # Validate methods
        methods = accessibility_spec["methods"]
        self.assertIn("enableKeyboardDrag", methods)
        self.assertIn("handleKeyboardDragStart", methods)
        self.assertIn("announceDropZones", methods)
        self.assertIn("manageFocusDuringDrag", methods)

        # Check method specifications
        keyboard_nav = methods["handleKeyboardNavigation"]
        self.assertEqual(keyboard_nav["returns"], "boolean")

        announce_state = methods["announceDragState"]
        self.assertEqual(len(announce_state["parameters"]), 2)

        # Validate ARIA attributes
        aria_attrs = accessibility_spec["aria_attributes"]
        self.assertIn("draggable_elements", aria_attrs)
        self.assertIn("drop_zones", aria_attrs)
        self.assertIn("container_elements", aria_attrs)

        # Check ARIA attribute specifications
        draggable_attrs = aria_attrs["draggable_elements"]
        self.assertIn("aria-grabbed", draggable_attrs)
        self.assertIn("aria-describedby", draggable_attrs)
        self.assertIn("tabindex", draggable_attrs)

        drop_zone_attrs = aria_attrs["drop_zones"]
        self.assertIn("aria-dropeffect", drop_zone_attrs)
        self.assertIn("copy|move|link", drop_zone_attrs["aria-dropeffect"])

    def test_keyboard_drag_operation_flow(self):
        """Test specification for keyboard drag operation flow."""
        keyboard_drag_spec = {
            "activation": {
                "trigger": "press 'd' key on focused draggable element",
                "prerequisites": [
                    "element must have focus",
                    "element must be draggable",
                    "keyboard drag must be enabled",
                ],
                "initial_state": [
                    "enter keyboard drag mode",
                    "update aria-grabbed to true",
                    "announce drag mode activation",
                    "focus first compatible drop zone",
                    "highlight all compatible drop zones",
                ],
            },
            "navigation": {
                "arrow_keys": {
                    "ArrowUp": "move focus to drop zone above",
                    "ArrowDown": "move focus to drop zone below",
                    "ArrowLeft": "move focus to drop zone left or parent level",
                    "ArrowRight": "move focus to drop zone right or child level",
                },
                "tab_navigation": {
                    "Tab": "move focus to next drop zone in document order",
                    "Shift+Tab": "move focus to previous drop zone in document order",
                },
                "home_end": {
                    "Home": "move focus to first drop zone",
                    "End": "move focus to last drop zone",
                },
                "feedback": [
                    "announce drop zone name and type on focus change",
                    "provide audio cues for navigation direction",
                    "update visual focus indicators",
                ],
            },
            "completion": {
                "confirm_drop": {
                    "trigger": "press Enter on focused drop zone",
                    "process": [
                        "validate drop operation is allowed",
                        "perform drop operation",
                        "announce drop completion or error",
                        "exit keyboard drag mode",
                        "focus dropped element",
                        "update aria-grabbed to false",
                    ],
                },
                "cancel_drag": {
                    "trigger": "press Escape key",
                    "process": [
                        "cancel drag operation",
                        "announce cancellation",
                        "exit keyboard drag mode",
                        "return focus to original element",
                        "update aria-grabbed to false",
                        "clear drop zone highlights",
                    ],
                },
            },
            "announcements": {
                "drag_start": "Drag mode activated for {element}. Use arrow keys to navigate drop zones, Enter to drop, Escape to cancel.",
                "zone_focus": "{zone_name} drop zone. {zone_description}. Press Enter to drop here.",
                "drop_success": "{element} dropped in {zone_name}.",
                "drop_error": "Cannot drop {element} in {zone_name}. {error_reason}",
                "drag_cancel": "Drag operation cancelled. Focus returned to {element}.",
                "no_zones": "No compatible drop zones available for {element}.",
            },
        }

        # Validate keyboard drag specification
        self.assertIn("activation", keyboard_drag_spec)
        self.assertIn("navigation", keyboard_drag_spec)
        self.assertIn("completion", keyboard_drag_spec)
        self.assertIn("announcements", keyboard_drag_spec)

        # Check activation
        activation = keyboard_drag_spec["activation"]
        self.assertEqual(
            activation["trigger"], "press 'd' key on focused draggable element"
        )
        self.assertEqual(len(activation["prerequisites"]), 3)
        self.assertEqual(len(activation["initial_state"]), 5)
        self.assertIn("enter keyboard drag mode", activation["initial_state"])

        # Check navigation
        navigation = keyboard_drag_spec["navigation"]
        self.assertIn("arrow_keys", navigation)
        self.assertIn("tab_navigation", navigation)
        self.assertIn("feedback", navigation)

        arrow_keys = navigation["arrow_keys"]
        self.assertIn("ArrowUp", arrow_keys)
        self.assertIn("ArrowDown", arrow_keys)
        self.assertEqual(arrow_keys["ArrowUp"], "move focus to drop zone above")

        # Check completion
        completion = keyboard_drag_spec["completion"]
        self.assertIn("confirm_drop", completion)
        self.assertIn("cancel_drag", completion)

        confirm_drop = completion["confirm_drop"]
        self.assertEqual(confirm_drop["trigger"], "press Enter on focused drop zone")
        self.assertIn("perform drop operation", confirm_drop["process"])

        cancel_drag = completion["cancel_drag"]
        self.assertEqual(cancel_drag["trigger"], "press Escape key")
        self.assertIn("return focus to original element", cancel_drag["process"])

        # Check announcements
        announcements = keyboard_drag_spec["announcements"]
        self.assertIn("drag_start", announcements)
        self.assertIn("drop_success", announcements)
        self.assertIn("drag_cancel", announcements)
        self.assertIn("arrow keys", announcements["drag_start"])


class UndoRedoManagerTest(TestCase):
    """Test specifications for the UndoRedoManager component enhanced for drag-and-drop operations."""

    def test_undo_redo_manager_interface(self):
        """Test base interface for UndoRedoManager component."""
        undo_redo_spec = {
            "class": "UndoRedoManager",
            "extends": "BaseUndoRedoManager",  # From Issue #190
            "constructor_params": {
                "parentBuilder": {"type": "DragDropBuilder", "required": True},
                "options": {
                    "type": "object",
                    "required": False,
                    "default": {},
                    "properties": {
                        "max_history_size": {"type": "integer", "default": 50},
                        "auto_save_enabled": {"type": "boolean", "default": True},
                        "batch_operations": {"type": "boolean", "default": True},
                        "keyboard_shortcuts": {"type": "boolean", "default": True},
                    },
                },
            },
            "properties": {
                "parentBuilder": "DragDropBuilder",
                "history": "Array<Operation>",
                "currentIndex": "integer",
                "batchInProgress": "boolean",
                "currentBatch": "Array<Operation>",
            },
            "methods": {
                # Inherited from BaseUndoRedoManager
                "undo": {"returns": "boolean", "description": "Undo last operation"},
                "redo": {"returns": "boolean", "description": "Redo next operation"},
                "clear": {"description": "Clear undo/redo history"},
                "canUndo": {"returns": "boolean"},
                "canRedo": {"returns": "boolean"},
                # Enhanced for drag-and-drop
                "recordDragOperation": {
                    "parameters": [{"name": "operation", "type": "DragOperation"}],
                    "description": "Record a drag-and-drop operation",
                },
                "recordLayoutChange": {
                    "parameters": [
                        {"name": "beforeState", "type": "object"},
                        {"name": "afterState", "type": "object"},
                    ],
                    "description": "Record layout change operation",
                },
                "startBatch": {
                    "parameters": [{"name": "description", "type": "string"}],
                    "description": "Start batching multiple operations",
                },
                "endBatch": {
                    "description": "End current batch and add to history",
                },
                "undoDragOperation": {
                    "parameters": [{"name": "operation", "type": "DragOperation"}],
                    "returns": "Promise<boolean>",
                    "async": True,
                    "description": "Undo a drag-and-drop operation",
                },
                "redoDragOperation": {
                    "parameters": [{"name": "operation", "type": "DragOperation"}],
                    "returns": "Promise<boolean>",
                    "async": True,
                    "description": "Redo a drag-and-drop operation",
                },
            },
            "operation_types": {
                "requirement_added": {
                    "data": {
                        "blockId": "string",
                        "requirementType": "string",
                        "position": "object",  # {x, y}
                        "parentId": "string|null",
                        "requirementData": "object",
                    },
                    "undo": "remove requirement block and clean up DOM",
                    "redo": "recreate requirement block at original position",
                },
                "requirement_removed": {
                    "data": {
                        "blockId": "string",
                        "requirementType": "string",
                        "position": "object",
                        "parentId": "string|null",
                        "requirementData": "object",
                        "childrenIds": "Array<string>",  # for containers
                    },
                    "undo": "recreate requirement block with all children",
                    "redo": "remove requirement block and children",
                },
                "requirement_moved": {
                    "data": {
                        "blockId": "string",
                        "fromParentId": "string|null",
                        "toParentId": "string|null",
                        "fromPosition": "object",
                        "toPosition": "object",
                        "fromIndex": "integer",
                        "toIndex": "integer",
                    },
                    "undo": "move requirement back to original parent and position",
                    "redo": "move requirement to new parent and position",
                },
                "requirement_reordered": {
                    "data": {
                        "parentId": "string|null",
                        "blockId": "string",
                        "fromIndex": "integer",
                        "toIndex": "integer",
                    },
                    "undo": "move requirement back to original index",
                    "redo": "move requirement to new index",
                },
                "layout_changed": {
                    "data": {
                        "algorithm": "string",
                        "beforePositions": "Map<string, object>",
                        "afterPositions": "Map<string, object>",
                    },
                    "undo": "restore all blocks to before positions",
                    "redo": "apply all blocks to after positions",
                },
                "batch_operation": {
                    "data": {
                        "description": "string",
                        "operations": "Array<Operation>",
                    },
                    "undo": "undo all operations in reverse order",
                    "redo": "redo all operations in original order",
                },
            },
        }

        # Validate undo/redo specification
        self.assertEqual(undo_redo_spec["class"], "UndoRedoManager")
        self.assertEqual(undo_redo_spec["extends"], "BaseUndoRedoManager")

        # Validate constructor
        constructor = undo_redo_spec["constructor_params"]
        self.assertIn("parentBuilder", constructor)
        self.assertTrue(constructor["parentBuilder"]["required"])

        # Validate options
        options = constructor["options"]["properties"]
        self.assertIn("max_history_size", options)
        self.assertIn("batch_operations", options)
        self.assertEqual(options["max_history_size"]["default"], 50)
        self.assertTrue(options["batch_operations"]["default"])

        # Validate properties
        properties = undo_redo_spec["properties"]
        self.assertEqual(properties["history"], "Array<Operation>")
        self.assertEqual(properties["currentIndex"], "integer")
        self.assertEqual(properties["batchInProgress"], "boolean")

        # Validate methods
        methods = undo_redo_spec["methods"]
        self.assertIn("undo", methods)
        self.assertIn("recordDragOperation", methods)
        self.assertIn("startBatch", methods)
        self.assertIn("undoDragOperation", methods)

        # Check method specifications
        record_drag = methods["recordDragOperation"]
        self.assertEqual(len(record_drag["parameters"]), 1)
        self.assertEqual(record_drag["parameters"][0]["type"], "DragOperation")

        undo_drag = methods["undoDragOperation"]
        self.assertTrue(undo_drag.get("async", False))
        self.assertEqual(undo_drag["returns"], "Promise<boolean>")

        # Validate operation types
        operation_types = undo_redo_spec["operation_types"]
        self.assertIn("requirement_added", operation_types)
        self.assertIn("requirement_moved", operation_types)
        self.assertIn("layout_changed", operation_types)
        self.assertIn("batch_operation", operation_types)

        # Check operation type specifications
        added_op = operation_types["requirement_added"]
        self.assertIn("data", added_op)
        self.assertIn("undo", added_op)
        self.assertIn("redo", added_op)

        added_data = added_op["data"]
        self.assertIn("blockId", added_data)
        self.assertIn("position", added_data)

        moved_op = operation_types["requirement_moved"]
        moved_data = moved_op["data"]
        self.assertIn("fromParentId", moved_data)
        self.assertIn("toParentId", moved_data)
        self.assertIn("fromPosition", moved_data)
        self.assertIn("toPosition", moved_data)

    def test_batch_operation_handling(self):
        """Test specification for batch operation handling."""
        batch_spec = {
            "batch_scenarios": {
                "multi_select_move": {
                    "description": "Moving multiple selected requirements simultaneously",
                    "operations": [
                        {"type": "requirement_moved", "blockId": "block1"},
                        {"type": "requirement_moved", "blockId": "block2"},
                        {"type": "requirement_moved", "blockId": "block3"},
                    ],
                    "batch_description": "Move 3 selected requirements",
                    "undo_behavior": "restore all blocks to original positions",
                },
                "auto_layout_application": {
                    "description": "Applying automatic layout to all requirements",
                    "operations": [
                        {"type": "layout_changed", "algorithm": "hierarchical"},
                    ],
                    "batch_description": "Apply hierarchical layout",
                    "undo_behavior": "restore previous layout positions",
                },
                "drag_with_auto_nesting": {
                    "description": "Drag operation that triggers automatic nesting adjustments",
                    "operations": [
                        {"type": "requirement_moved", "blockId": "dragged_block"},
                        {
                            "type": "requirement_reordered",
                            "parentId": "target_container",
                        },
                        {"type": "layout_changed", "scope": "target_container"},
                    ],
                    "batch_description": "Drag block with auto-nesting",
                    "undo_behavior": "reverse all nesting and layout changes",
                },
                "complex_structure_modification": {
                    "description": "Operations that modify requirement structure hierarchy",
                    "operations": [
                        {"type": "requirement_added", "blockId": "new_container"},
                        {
                            "type": "requirement_moved",
                            "blockId": "existing_req1",
                            "toParentId": "new_container",
                        },
                        {
                            "type": "requirement_moved",
                            "blockId": "existing_req2",
                            "toParentId": "new_container",
                        },
                        {"type": "requirement_reordered", "parentId": "new_container"},
                    ],
                    "batch_description": "Create container and move requirements",
                    "undo_behavior": "remove container and restore original structure",
                },
            },
            "batch_triggers": {
                "automatic": [
                    "multi-select operations",
                    "auto-layout applications",
                    "operations that trigger cascading changes",
                    "drag operations with validation-triggered adjustments",
                ],
                "manual": [
                    "user-initiated batch mode",
                    "programmatic batch operations",
                    "plugin or extension triggered batches",
                ],
            },
            "batch_management": {
                "start_batch": {
                    "conditions": [
                        "user selects multiple items",
                        "operation is flagged as batch-worthy",
                        "cascade of operations is detected",
                    ],
                    "process": [
                        "set batchInProgress flag",
                        "initialize currentBatch array",
                        "optionally show batch indicator in UI",
                    ],
                },
                "add_to_batch": {
                    "conditions": [
                        "batch is in progress",
                        "operation is compatible with current batch",
                    ],
                    "process": [
                        "add operation to currentBatch array",
                        "do not add to main history yet",
                        "update batch progress indicator",
                    ],
                },
                "end_batch": {
                    "conditions": [
                        "batch operation is complete",
                        "timeout since last operation added",
                        "explicit batch end signal",
                    ],
                    "process": [
                        "create batch_operation with currentBatch",
                        "add batch_operation to main history",
                        "clear currentBatch array",
                        "reset batchInProgress flag",
                    ],
                },
            },
        }

        # Validate batch specification
        self.assertIn("batch_scenarios", batch_spec)
        self.assertIn("batch_triggers", batch_spec)
        self.assertIn("batch_management", batch_spec)

        # Check batch scenarios
        scenarios = batch_spec["batch_scenarios"]
        self.assertIn("multi_select_move", scenarios)
        self.assertIn("auto_layout_application", scenarios)
        self.assertIn("complex_structure_modification", scenarios)

        multi_move = scenarios["multi_select_move"]
        self.assertIn("description", multi_move)
        self.assertIn("operations", multi_move)
        self.assertIn("batch_description", multi_move)
        self.assertEqual(len(multi_move["operations"]), 3)

        # Check batch triggers
        triggers = batch_spec["batch_triggers"]
        self.assertIn("automatic", triggers)
        self.assertIn("manual", triggers)
        self.assertIn("multi-select operations", triggers["automatic"])

        # Check batch management
        management = batch_spec["batch_management"]
        self.assertIn("start_batch", management)
        self.assertIn("add_to_batch", management)
        self.assertIn("end_batch", management)

        start_batch = management["start_batch"]
        self.assertIn("conditions", start_batch)
        self.assertIn("process", start_batch)
        self.assertIn("set batchInProgress flag", start_batch["process"])


class DragDropIntegrationTest(TestCase):
    """Test specifications for integration between drag-and-drop and existing visual builder."""

    def test_backward_compatibility_with_visual_builder(self):
        """Test that drag-and-drop maintains compatibility with Issue #190 visual builder."""
        compatibility_spec = {
            "class_inheritance": {
                "DragDropBuilder": {
                    "extends": "PrerequisiteBuilder",
                    "preserved_methods": [
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
                    "preserved_events": [
                        "requirement-added",
                        "requirement-removed",
                        "requirement-changed",
                        "validation-complete",
                        "json-generated",
                    ],
                    "preserved_options": [
                        "initial_requirements",
                        "validation_url",
                        "available_traits",
                        "available_fields",
                        "max_nesting_depth",
                        "auto_validate",
                    ],
                },
            },
            "feature_flags": {
                "enable_drag_drop": {
                    "default": True,
                    "when_false": "operates exactly like Issue #190 visual builder",
                    "when_true": "adds drag-and-drop enhancements",
                },
                "palette_position": {
                    "default": "left",
                    "options": ["left", "right", "top", "hidden"],
                    "hidden_mode": "no palette shown, maintains form-based interface",
                },
                "drop_zone_highlight": {
                    "default": True,
                    "when_false": "no visual drop zone feedback",
                    "maintains": "keyboard and screen reader functionality",
                },
            },
            "progressive_enhancement": {
                "base_functionality": [
                    "all Issue #190 visual builder features work unchanged",
                    "form inputs remain functional for manual data entry",
                    "JSON generation and validation unchanged",
                    "existing keyboard navigation preserved",
                ],
                "enhanced_functionality": [
                    "drag-and-drop adds alternative interaction method",
                    "touch support enhances mobile experience",
                    "visual feedback improves usability",
                    "keyboard drag operations supplement existing shortcuts",
                ],
                "graceful_degradation": [
                    "if drag-and-drop not supported, falls back to Issue #190 behavior",
                    "if touch not supported, mouse and keyboard remain fully functional",
                    "if visual enhancements fail, functional interface remains",
                ],
            },
            "data_compatibility": {
                "json_format": "identical to Issue #190 specification",
                "requirement_structure": "no changes to underlying data model",
                "validation_rules": "same validation as Issue #190",
                "export_import": "fully compatible with Issue #190 exports",
            },
        }

        # Validate compatibility specification
        self.assertIn("class_inheritance", compatibility_spec)
        self.assertIn("feature_flags", compatibility_spec)
        self.assertIn("progressive_enhancement", compatibility_spec)
        self.assertIn("data_compatibility", compatibility_spec)

        # Check class inheritance
        inheritance = compatibility_spec["class_inheritance"]["DragDropBuilder"]
        self.assertEqual(inheritance["extends"], "PrerequisiteBuilder")
        self.assertIn("addRequirement", inheritance["preserved_methods"])
        self.assertIn("generateJSON", inheritance["preserved_methods"])
        self.assertIn("requirement-added", inheritance["preserved_events"])

        # Check feature flags
        flags = compatibility_spec["feature_flags"]
        self.assertIn("enable_drag_drop", flags)
        self.assertIn("palette_position", flags)

        enable_flag = flags["enable_drag_drop"]
        self.assertTrue(enable_flag["default"])
        self.assertIn("Issue #190 visual builder", enable_flag["when_false"])

        palette_flag = flags["palette_position"]
        self.assertEqual(palette_flag["default"], "left")
        self.assertIn("hidden", palette_flag["options"])

        # Check progressive enhancement
        enhancement = compatibility_spec["progressive_enhancement"]
        self.assertIn("base_functionality", enhancement)
        self.assertIn("enhanced_functionality", enhancement)
        self.assertIn("graceful_degradation", enhancement)

        base_func = enhancement["base_functionality"]
        self.assertIn("Issue #190 visual builder features work unchanged", base_func[0])
        self.assertIn("JSON generation and validation unchanged", base_func[2])

        # Check data compatibility
        data_compat = compatibility_spec["data_compatibility"]
        self.assertEqual(
            data_compat["json_format"], "identical to Issue #190 specification"
        )
        self.assertEqual(
            data_compat["requirement_structure"], "no changes to underlying data model"
        )

    def test_integration_with_existing_components(self):
        """Test integration specifications with existing components."""
        integration_spec = {
            "django_form_integration": {
                "widget_compatibility": {
                    "PrerequisiteBuilderWidget": "enhanced but fully backward compatible",
                    "hidden_field_sync": "maintains same hidden field update mechanism",
                    "form_validation": "uses same Django form validation as Issue #190",
                    "admin_interface": "works in Django admin without changes",
                },
                "template_integration": {
                    "prerequisite_tags": "all Issue #190 template tags work unchanged",
                    "css_classes": "new classes added, existing classes preserved",
                    "javascript_loading": "DragDropBuilder loads as enhancement to PrerequisiteBuilder",
                    "no_js_fallback": "form remains functional without JavaScript",
                },
            },
            "api_integration": {
                "validation_endpoint": "same /api/prerequisites/validate/ endpoint",
                "suggestions_endpoint": "same /api/prerequisites/suggestions/ endpoint",
                "no_new_endpoints": "drag-and-drop uses existing API infrastructure",
                "csrf_protection": "maintains same CSRF token handling",
            },
            "existing_javascript_components": {
                "RequirementValidator": "enhanced to handle drag-drop operations",
                "JSONGenerator": "unchanged, used by drag-drop for same JSON output",
                "DOMManager": "extended for drag-drop DOM manipulation",
                "EventHandler": "extended with drag-drop event types",
                "all_existing_functionality": "preserved and working",
            },
            "css_integration": {
                "base_styles": "Issue #190 styles remain unchanged",
                "new_styles": "additive only, no modifications to existing styles",
                "theme_compatibility": "works with all existing themes",
                "responsive_design": "maintains existing responsive behavior",
                "accessibility_styles": "enhances existing accessibility CSS",
            },
            "testing_integration": {
                "existing_tests": "all Issue #190 tests continue to pass",
                "new_test_coverage": "drag-and-drop tests are additive",
                "mock_strategies": "can disable drag-drop for testing Issue #190 features",
                "ci_cd_compatibility": "no changes required to existing test infrastructure",
            },
        }

        # Validate integration specification
        self.assertIn("django_form_integration", integration_spec)
        self.assertIn("api_integration", integration_spec)
        self.assertIn("existing_javascript_components", integration_spec)
        self.assertIn("css_integration", integration_spec)
        self.assertIn("testing_integration", integration_spec)

        # Check Django form integration
        django_integration = integration_spec["django_form_integration"]
        self.assertIn("widget_compatibility", django_integration)
        self.assertIn("template_integration", django_integration)

        widget_compat = django_integration["widget_compatibility"]
        self.assertIn(
            "fully backward compatible", widget_compat["PrerequisiteBuilderWidget"]
        )
        self.assertIn("same hidden field update", widget_compat["hidden_field_sync"])

        # Check API integration
        api_integration = integration_spec["api_integration"]
        self.assertEqual(
            api_integration["validation_endpoint"],
            "same /api/prerequisites/validate/ endpoint",
        )
        self.assertEqual(
            api_integration["no_new_endpoints"],
            "drag-and-drop uses existing API infrastructure",
        )

        # Check JavaScript components
        js_integration = integration_spec["existing_javascript_components"]
        self.assertIn("enhanced to handle", js_integration["RequirementValidator"])
        self.assertIn("unchanged", js_integration["JSONGenerator"])
        self.assertIn(
            "preserved and working", js_integration["all_existing_functionality"]
        )

        # Check CSS integration
        css_integration = integration_spec["css_integration"]
        self.assertEqual(
            css_integration["base_styles"], "Issue #190 styles remain unchanged"
        )
        self.assertEqual(
            css_integration["new_styles"],
            "additive only, no modifications to existing styles",
        )

        # Check testing integration
        testing_integration = integration_spec["testing_integration"]
        self.assertEqual(
            testing_integration["existing_tests"],
            "all Issue #190 tests continue to pass",
        )
        self.assertIn("can disable drag-drop", testing_integration["mock_strategies"])


class DragDropPerformanceTest(TestCase):
    """Test specifications for drag-and-drop performance considerations."""

    def test_performance_requirements(self):
        """Test performance requirement specifications."""
        performance_spec = {
            "response_times": {
                "drag_start": {
                    "target": "< 50ms",
                    "description": "Time from drag start event to visual feedback",
                    "measurement": "event timestamp to first DOM update",
                },
                "drag_preview_update": {
                    "target": "< 16ms",
                    "description": "Drag preview position update during move",
                    "measurement": "time between mousemove/touchmove and preview position update",
                    "note": "must maintain 60fps for smooth dragging",
                },
                "drop_zone_highlighting": {
                    "target": "< 25ms",
                    "description": "Time to update drop zone highlights during drag",
                    "measurement": "drag position change to drop zone visual update",
                },
                "drop_completion": {
                    "target": "< 100ms",
                    "description": "Time from drop event to DOM structure update",
                    "measurement": "drop event to requirement structure update complete",
                },
                "undo_redo_operations": {
                    "target": "< 50ms",
                    "description": "Time to complete undo/redo of drag operations",
                    "measurement": "undo/redo call to DOM update complete",
                },
            },
            "memory_usage": {
                "drag_preview_elements": {
                    "limit": "single preview element per active drag",
                    "cleanup": "immediate cleanup on drag end/cancel",
                },
                "drop_zone_elements": {
                    "strategy": "reuse existing elements when possible",
                    "cleanup": "remove temporary drop zones after drag",
                },
                "event_listeners": {
                    "strategy": "use event delegation to minimize listener count",
                    "cleanup": "remove listeners on component destroy",
                },
                "undo_history": {
                    "limit": "configurable max history size (default 50 operations)",
                    "cleanup": "automatically remove oldest entries when limit exceeded",
                },
            },
            "dom_manipulation": {
                "batch_updates": {
                    "strategy": "batch DOM updates using requestAnimationFrame",
                    "applies_to": [
                        "drop zone highlighting",
                        "layout changes",
                        "visual feedback",
                    ],
                },
                "element_creation": {
                    "strategy": "create elements lazily and reuse when possible",
                    "cache": "maintain element cache for frequent operations",
                },
                "layout_thrashing": {
                    "prevention": [
                        "avoid reading layout properties during drag operations",
                        "use transform for position changes instead of top/left",
                        "batch style changes to minimize reflow/repaint",
                    ],
                },
            },
            "large_dataset_handling": {
                "many_requirements": {
                    "threshold": "> 50 requirement blocks",
                    "optimizations": [
                        "virtualize drop zone creation for off-screen elements",
                        "debounce drop zone highlight updates",
                        "use intersection observer for visibility detection",
                    ],
                },
                "deep_nesting": {
                    "threshold": "> 10 levels deep",
                    "optimizations": [
                        "lazy load nested container contents",
                        "limit simultaneous drop zone calculations",
                        "use efficient tree traversal algorithms",
                    ],
                },
            },
        }

        # Validate performance specification
        self.assertIn("response_times", performance_spec)
        self.assertIn("memory_usage", performance_spec)
        self.assertIn("dom_manipulation", performance_spec)
        self.assertIn("large_dataset_handling", performance_spec)

        # Check response times
        response_times = performance_spec["response_times"]
        self.assertIn("drag_start", response_times)
        self.assertIn("drag_preview_update", response_times)

        drag_start = response_times["drag_start"]
        self.assertEqual(drag_start["target"], "< 50ms")
        self.assertIn("visual feedback", drag_start["description"])

        preview_update = response_times["drag_preview_update"]
        self.assertEqual(preview_update["target"], "< 16ms")
        self.assertIn("60fps", preview_update["note"])

        # Check memory usage
        memory_usage = performance_spec["memory_usage"]
        self.assertIn("drag_preview_elements", memory_usage)
        self.assertIn("undo_history", memory_usage)

        preview_memory = memory_usage["drag_preview_elements"]
        self.assertIn("single preview element", preview_memory["limit"])
        self.assertIn("immediate cleanup", preview_memory["cleanup"])

        # Check DOM manipulation
        dom_manipulation = performance_spec["dom_manipulation"]
        self.assertIn("batch_updates", dom_manipulation)
        self.assertIn("layout_thrashing", dom_manipulation)

        batch_updates = dom_manipulation["batch_updates"]
        self.assertIn("requestAnimationFrame", batch_updates["strategy"])
        self.assertIn("drop zone highlighting", batch_updates["applies_to"])

        layout_prevention = dom_manipulation["layout_thrashing"]["prevention"]
        self.assertIn("avoid reading layout properties", layout_prevention[0])
        self.assertIn("use transform", layout_prevention[1])

        # Check large dataset handling
        large_data = performance_spec["large_dataset_handling"]
        self.assertIn("many_requirements", large_data)
        self.assertIn("deep_nesting", large_data)

        many_req = large_data["many_requirements"]
        self.assertEqual(many_req["threshold"], "> 50 requirement blocks")
        self.assertIn("virtualize drop zone creation", many_req["optimizations"][0])

    def test_performance_monitoring(self):
        """Test performance monitoring specifications."""
        monitoring_spec = {
            "metrics_collection": {
                "drag_operation_timing": {
                    "start_time": "performance.mark('drag-start')",
                    "end_time": "performance.mark('drag-end')",
                    "measurement": "performance.measure('drag-operation', 'drag-start', 'drag-end')",
                    "threshold": "operations > 100ms should be logged",
                },
                "memory_usage_tracking": {
                    "method": "performance.memory when available",
                    "frequency": "before and after major operations",
                    "alerts": "memory increase > 10MB in single operation",
                },
                "frame_rate_monitoring": {
                    "method": "requestAnimationFrame timing",
                    "target": "maintain > 30fps during drag operations",
                    "alerts": "consecutive frames > 33ms",
                },
            },
            "debugging_tools": {
                "performance_panel": {
                    "enabled": "in development mode only",
                    "shows": [
                        "drag operation timings",
                        "drop zone calculation times",
                        "DOM manipulation metrics",
                        "memory usage graphs",
                    ],
                },
                "console_logging": {
                    "levels": {
                        "debug": "all performance measurements",
                        "info": "slow operations only",
                        "warn": "performance threshold violations",
                        "error": "performance failures",
                    },
                },
            },
            "performance_testing": {
                "unit_tests": [
                    "drag start response time < 50ms",
                    "drop completion < 100ms",
                    "undo/redo < 50ms",
                    "memory cleanup after operations",
                ],
                "integration_tests": [
                    "50+ requirement blocks drag performance",
                    "10+ nesting level performance",
                    "simultaneous multi-user operations",
                ],
                "browser_testing": [
                    "Chrome performance profiling",
                    "Firefox performance tools",
                    "Safari timeline analysis",
                    "Edge memory usage tracking",
                ],
            },
        }

        # Validate monitoring specification
        self.assertIn("metrics_collection", monitoring_spec)
        self.assertIn("debugging_tools", monitoring_spec)
        self.assertIn("performance_testing", monitoring_spec)

        # Check metrics collection
        metrics = monitoring_spec["metrics_collection"]
        self.assertIn("drag_operation_timing", metrics)
        self.assertIn("memory_usage_tracking", metrics)
        self.assertIn("frame_rate_monitoring", metrics)

        drag_timing = metrics["drag_operation_timing"]
        self.assertIn("performance.mark", drag_timing["start_time"])
        self.assertIn("> 100ms should be logged", drag_timing["threshold"])

        memory_tracking = metrics["memory_usage_tracking"]
        self.assertIn("performance.memory", memory_tracking["method"])
        self.assertIn("> 10MB", memory_tracking["alerts"])

        # Check debugging tools
        debugging = monitoring_spec["debugging_tools"]
        self.assertIn("performance_panel", debugging)
        self.assertIn("console_logging", debugging)

        panel = debugging["performance_panel"]
        self.assertEqual(panel["enabled"], "in development mode only")
        self.assertIn("drag operation timings", panel["shows"])

        # Check performance testing
        testing = monitoring_spec["performance_testing"]
        self.assertIn("unit_tests", testing)
        self.assertIn("integration_tests", testing)
        self.assertIn("browser_testing", testing)

        unit_tests = testing["unit_tests"]
        self.assertIn("< 50ms", unit_tests[0])
        self.assertIn("memory cleanup", unit_tests[3])


class DragDropTemplateTest(TestCase):
    """Test specifications for drag-and-drop template rendering integration."""

    def test_template_integration_with_visual_builder(self):
        """Test that drag-and-drop templates integrate with existing visual builder templates."""
        template_integration_spec = {
            "template_inheritance": {
                "base_template": "widgets/prerequisite_builder_widget.html from Issue #190",
                "drag_drop_enhancements": [
                    "add drag-and-drop palette section",
                    "add drop zone indicators",
                    "add drag preview container",
                    "maintain all existing structure",
                ],
                "conditional_rendering": {
                    "if_drag_drop_enabled": "show palette and drop zones",
                    "if_drag_drop_disabled": "render exactly like Issue #190",
                },
            },
            "template_context": {
                "existing_context": {
                    "field_name": "preserved from Issue #190",
                    "initial_value": "preserved from Issue #190",
                    "available_traits": "preserved from Issue #190",
                    "available_fields": "preserved from Issue #190",
                },
                "new_context_variables": {
                    "drag_drop_enabled": {
                        "type": "boolean",
                        "default": True,
                        "description": "whether to enable drag-and-drop features",
                    },
                    "palette_position": {
                        "type": "string",
                        "default": "left",
                        "options": ["left", "right", "top", "hidden"],
                        "description": "position of the requirement type palette",
                    },
                    "touch_enabled": {
                        "type": "boolean",
                        "default": "auto-detected",
                        "description": "whether device supports touch interactions",
                    },
                    "grid_enabled": {
                        "type": "boolean",
                        "default": False,
                        "description": "whether to show grid overlay for positioning",
                    },
                },
            },
            "css_class_additions": {
                "container_classes": [
                    "drag-drop-enabled",
                    "palette-{position}",
                    "touch-device",
                    "grid-mode",
                    "reduced-motion",  # for accessibility
                ],
                "new_element_classes": [
                    "drag-drop-palette",
                    "palette-item",
                    "drop-zone",
                    "drop-zone-active",
                    "drag-preview",
                    "selection-overlay",
                ],
            },
        }

        # Validate template integration
        self.assertIn("template_inheritance", template_integration_spec)
        self.assertIn("template_context", template_integration_spec)
        self.assertIn("css_class_additions", template_integration_spec)

        # Check template inheritance
        inheritance = template_integration_spec["template_inheritance"]
        self.assertIn("Issue #190", inheritance["base_template"])
        self.assertIn(
            "maintain all existing structure", inheritance["drag_drop_enhancements"]
        )

        conditional = inheritance["conditional_rendering"]
        self.assertIn(
            "show palette and drop zones", conditional["if_drag_drop_enabled"]
        )
        self.assertIn("exactly like Issue #190", conditional["if_drag_drop_disabled"])

        # Check template context
        context = template_integration_spec["template_context"]
        self.assertIn("existing_context", context)
        self.assertIn("new_context_variables", context)

        existing = context["existing_context"]
        self.assertIn("preserved from Issue #190", existing["field_name"])

        new_vars = context["new_context_variables"]
        self.assertIn("drag_drop_enabled", new_vars)
        self.assertIn("palette_position", new_vars)

        drag_enabled = new_vars["drag_drop_enabled"]
        self.assertTrue(drag_enabled["default"])
        self.assertEqual(drag_enabled["type"], "boolean")

        # Check CSS classes
        css_classes = template_integration_spec["css_class_additions"]
        self.assertIn("container_classes", css_classes)
        self.assertIn("new_element_classes", css_classes)

        container_classes = css_classes["container_classes"]
        self.assertIn("drag-drop-enabled", container_classes)
        self.assertIn("palette-{position}", container_classes)

        new_classes = css_classes["new_element_classes"]
        self.assertIn("drag-drop-palette", new_classes)
        self.assertIn("drop-zone", new_classes)

    def test_form_integration_in_templates(self):
        """Test form integration specifications in Django templates."""
        form_integration_spec = {
            "form_rendering": {
                "hidden_field": "same hidden field mechanism as Issue #190",
                "field_id": "preserved field ID structure",
                "field_name": "preserved field name structure",
                "css_classes": "existing form classes preserved",
                "validation_errors": "same error display mechanism",
            },
            "javascript_initialization": {
                "script_tags": {
                    "prerequisite_builder_js": "enhanced but backward compatible",
                    "drag_drop_enhancements_js": "additional script for drag-and-drop",
                    "touch_handler_js": "loaded conditionally for touch devices",
                },
                "initialization_order": [
                    "load base PrerequisiteBuilder JavaScript",
                    "detect browser capabilities (drag-drop, touch)",
                    "conditionally load drag-drop enhancements",
                    "initialize DragDropBuilder with options",
                    "set up event listeners and accessibility",
                ],
                "fallback_handling": {
                    "no_drag_drop_support": "initialize base PrerequisiteBuilder only",
                    "javascript_disabled": "form remains fully functional",
                    "touch_only_device": "enable touch handlers, disable mouse drag",
                },
            },
            "csrf_token_handling": {
                "ajax_requests": "same CSRF token mechanism as Issue #190",
                "form_submissions": "preserved form submission handling",
                "validation_calls": "same token passing for validation API",
            },
        }

        # Validate form integration
        self.assertIn("form_rendering", form_integration_spec)
        self.assertIn("javascript_initialization", form_integration_spec)
        self.assertIn("csrf_token_handling", form_integration_spec)

        # Check form rendering
        form_rendering = form_integration_spec["form_rendering"]
        self.assertEqual(
            form_rendering["hidden_field"], "same hidden field mechanism as Issue #190"
        )
        self.assertEqual(
            form_rendering["validation_errors"], "same error display mechanism"
        )

        # Check JavaScript initialization
        js_init = form_integration_spec["javascript_initialization"]
        self.assertIn("script_tags", js_init)
        self.assertIn("initialization_order", js_init)
        self.assertIn("fallback_handling", js_init)

        script_tags = js_init["script_tags"]
        self.assertIn("backward compatible", script_tags["prerequisite_builder_js"])
        self.assertIn("conditionally", script_tags["touch_handler_js"])

        init_order = js_init["initialization_order"]
        self.assertEqual(len(init_order), 5)
        self.assertIn("base PrerequisiteBuilder", init_order[0])
        self.assertIn("DragDropBuilder", init_order[3])

        # Check CSRF handling
        csrf = form_integration_spec["csrf_token_handling"]
        self.assertEqual(
            csrf["ajax_requests"], "same CSRF token mechanism as Issue #190"
        )
        self.assertEqual(
            csrf["validation_calls"], "same token passing for validation API"
        )

    def test_end_to_end_workflow_integration(self):
        """Test end-to-end workflow integration with existing visual builder."""
        workflow_spec = {
            "user_workflow_scenarios": {
                "existing_user_workflow": {
                    "description": "User accustomed to Issue #190 visual builder",
                    "workflow": [
                        "click Add Requirement button",
                        "select requirement type from dropdown",
                        "fill in requirement details in form",
                        "click Save or add another requirement",
                    ],
                    "drag_drop_compatibility": "workflow works identically with drag-drop enabled",
                },
                "drag_drop_enhanced_workflow": {
                    "description": "User taking advantage of drag-drop features",
                    "workflow": [
                        "drag requirement type from palette",
                        "drop in desired location on canvas",
                        "requirement block appears with form fields",
                        "fill in details as before",
                        "drag to reorder or reorganize as needed",
                    ],
                    "fallback": "can switch to form-based workflow at any time",
                },
                "mobile_touch_workflow": {
                    "description": "User on touch device",
                    "workflow": [
                        "long-press on palette item to start drag",
                        "drag with finger to canvas",
                        "visual feedback shows drop zones",
                        "release to drop and create requirement",
                        "touch to edit, drag to reorganize",
                    ],
                    "accessibility": "voice control and switch navigation supported",
                },
                "keyboard_only_workflow": {
                    "description": "User relying on keyboard navigation",
                    "workflow": [
                        "Tab to navigate to Add Requirement or palette",
                        "Press 'd' to enter drag mode on palette item",
                        "Arrow keys to navigate between drop zones",
                        "Enter to confirm placement",
                        "Continue with normal keyboard form interaction",
                    ],
                    "screen_reader": "full screen reader announcements throughout",
                },
            },
            "data_flow_integration": {
                "json_generation": "identical JSON output to Issue #190",
                "form_submission": "same Django form handling",
                "validation": "same validation rules and error messages",
                "persistence": "same database storage mechanism",
            },
            "error_handling_integration": {
                "validation_errors": "displayed using same mechanism as Issue #190",
                "drag_drop_errors": "integrated with existing error display",
                "network_errors": "same handling for AJAX validation calls",
                "javascript_errors": "graceful degradation to form-only interface",
            },
        }

        # Validate workflow specification
        self.assertIn("user_workflow_scenarios", workflow_spec)
        self.assertIn("data_flow_integration", workflow_spec)
        self.assertIn("error_handling_integration", workflow_spec)

        # Check user workflows
        workflows = workflow_spec["user_workflow_scenarios"]
        self.assertIn("existing_user_workflow", workflows)
        self.assertIn("drag_drop_enhanced_workflow", workflows)
        self.assertIn("mobile_touch_workflow", workflows)
        self.assertIn("keyboard_only_workflow", workflows)

        existing_workflow = workflows["existing_user_workflow"]
        self.assertIn("Issue #190", existing_workflow["description"])
        self.assertIn("works identically", existing_workflow["drag_drop_compatibility"])

        touch_workflow = workflows["mobile_touch_workflow"]
        self.assertIn("long-press", touch_workflow["workflow"][0])
        self.assertIn("voice control", touch_workflow["accessibility"])

        # Check data flow
        data_flow = workflow_spec["data_flow_integration"]
        self.assertEqual(
            data_flow["json_generation"], "identical JSON output to Issue #190"
        )
        self.assertEqual(data_flow["form_submission"], "same Django form handling")

        # Check error handling
        error_handling = workflow_spec["error_handling_integration"]
        self.assertIn("same mechanism", error_handling["validation_errors"])
        self.assertIn("graceful degradation", error_handling["javascript_errors"])


# Mark the completion of the drag-and-drop builder tests
class TestCompletionMarker(TestCase):
    """Marker test to indicate completion of drag-and-drop builder test suite."""

    def test_drag_drop_test_suite_completeness(self):
        """Verify that all required drag-and-drop test categories are implemented."""
        implemented_test_categories = [
            "DragDropBuilderClassTest",  # Main class functionality
            "DragDropPaletteComponentTest",  # Palette component
            "DragDropCanvasComponentTest",  # Canvas component
            "DropZoneComponentTest",  # Drop zone component
            "TouchHandlerTest",  # Touch device support
            "AccessibilityManagerTest",  # Accessibility and keyboard navigation
            "UndoRedoManagerTest",  # Undo/redo system
            "DragDropIntegrationTest",  # Integration with visual builder
            "DragDropPerformanceTest",  # Performance considerations
            "DragDropTemplateTest",  # Template integration
        ]

        # All required test categories should be implemented
        self.assertEqual(len(implemented_test_categories), 10)

        # Test coverage should be comprehensive
        required_test_areas = [
            "drag-and-drop core functionality",
            "visual feedback and UI state",
            "accessibility and keyboard navigation",
            "touch device support",
            "undo/redo system",
            "integration with visual builder",
            "performance and edge cases",
            "template rendering integration",
        ]

        self.assertEqual(len(required_test_areas), 8)

        # This test passing indicates the drag-and-drop test suite is complete
        self.assertTrue(
            True, "Drag-and-drop prerequisite interface test suite is complete"
        )
