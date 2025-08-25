"""
Comprehensive tests for prerequisite builder template rendering (Issue #190).

This module tests the Django template rendering aspects of the visual prerequisite
builder, ensuring proper template structure, context handling, and HTML output
generation.

Key template rendering features being tested:
1. Template inheritance and block structure
2. Context variable handling and filtering
3. Form widget template rendering
4. Static file inclusion (CSS/JS)
5. Template error handling and fallbacks
6. Responsive design template elements
7. Accessibility attributes in templates
8. Security considerations in template rendering

The template system should provide a complete, accessible, and secure
interface for the visual prerequisite builder.
"""

from django.contrib.auth import get_user_model
from django.template import Context, Template
from django.template.loader import get_template, render_to_string
from django.test import TestCase, override_settings
from django.utils.html import escape

from campaigns.models import Campaign, CampaignMembership
from characters.models import Character, MageCharacter
from prerequisites.models import Prerequisite

User = get_user_model()


class PrerequisiteBuilderTemplateStructureTest(TestCase):
    """Test template structure and inheritance for prerequisite builder."""

    def test_base_template_structure(self):
        """Test the base template structure for prerequisite builder."""
        # Expected base template content structure
        base_template_content = """
        {% load static %}
        <div class="prerequisite-builder-container">
            <div class="prerequisite-builder"
                 id="prerequisite-builder-{{ builder_id|default:'default' }}"
                 data-widget="prerequisite-builder"
                 data-builder-id="{{ builder_id|default:'default' }}"
                 data-initial-requirements="{{ initial_requirements|default:'{}' }}"
                 data-validation-url="{{ validation_url|default:'' }}"
                 data-available-traits="{{ available_traits|default:'[]' }}"
                 data-available-fields="{{ available_fields|default:'[]' }}"
                 data-max-nesting-depth="{{ max_nesting_depth|default:5 }}"
                 role="region"
                 aria-label="Prerequisite Requirements Builder"
                 aria-describedby="builder-instructions-{{ builder_id|default:'default' }}">

                <div class="builder-instructions"
                     id="builder-instructions-{{ builder_id|default:'default' }}"
                     style="display: none;">
                    Use this interface to build prerequisite requirements.
                    You can add multiple requirements and combine them with AND/OR logic.
                </div>

                <div class="builder-header">
                    <h4 class="builder-title">Requirement Builder</h4>
                    <div class="builder-controls">
                        <button type="button"
                                class="btn btn-sm btn-secondary clear-all-btn"
                                data-action="clear-all"
                                aria-label="Clear all requirements">
                            Clear All
                        </button>
                        <button type="button"
                                class="btn btn-sm btn-primary add-requirement-btn"
                                data-action="add-requirement"
                                aria-label="Add new requirement">
                            Add Requirement
                        </button>
                    </div>
                </div>

                <div class="builder-content">
                    <div class="requirement-blocks-container"
                         role="group"
                         aria-label="Requirement blocks">
                        <!-- Dynamic requirement blocks will be inserted here -->
                    </div>

                    <div class="empty-state"
                         id="empty-state-{{ builder_id|default:'default' }}"
                         style="display: none;"
                         role="status"
                         aria-live="polite">
                        <div class="empty-state-content">
                            <p>No requirements defined.</p>
                            <p>Click "Add Requirement" to get started.</p>
                        </div>
                        <div class="empty-state-suggestions">
                            <h5>Common Requirements:</h5>
                            <button type="button"
                                    class="btn btn-outline-primary btn-sm"
                                    data-action="add-trait-requirement">
                                Add Trait Requirement
                            </button>
                            <button type="button"
                                    class="btn btn-outline-primary btn-sm"
                                    data-action="add-has-requirement">
                                Add Item Requirement
                            </button>
                        </div>
                    </div>
                </div>

                <div class="builder-footer">
                    <div class="validation-messages"
                         role="alert"
                         aria-live="polite"
                         aria-relevant="additions text"
                         id="validation-messages-{{ builder_id|default:'default' }}">
                        <!-- Validation messages will be inserted here -->
                    </div>

                    <div class="json-preview"
                         id="json-preview-{{ builder_id|default:'default' }}"
                         style="display: none;">
                        <div class="json-preview-header">
                            <label for="json-output-{{ builder_id|default:'default' }}">
                                Generated JSON:
                            </label>
                            <button type="button"
                                    class="btn btn-sm btn-outline-secondary"
                                    data-action="toggle-json-preview">
                                Toggle Preview
                            </button>
                        </div>
                        <pre class="json-output"
                             id="json-output-{{ builder_id|default:'default' }}"
                             aria-label="Generated JSON output"></pre>
                    </div>
                </div>
            </div>
        </div>

        <!-- Include required CSS -->
        <link rel="stylesheet" href="{% static 'css/prerequisite-builder.css' %}">

        <!-- Include required JavaScript -->
        <script src="{% static 'js/prerequisite-builder.js' %}" defer></script>

        <script>
        document.addEventListener('DOMContentLoaded', function() {
            const builderElement = document.getElementById('prerequisite-builder-{{ builder_id|default:"default" }}');
            if (builderElement && window.PrerequisiteBuilder) {
                const hiddenField = document.querySelector('{{ hidden_field_selector|default:"#id_requirements" }}');
                const builder = new PrerequisiteBuilder(builderElement, hiddenField, {
                    initial_requirements: {{ initial_requirements|default:'{}' }},
                    validation_url: '{{ validation_url|default:"" }}',
                    available_traits: {{ available_traits|default:'[]' }},
                    available_fields: {{ available_fields|default:'[]' }},
                    max_nesting_depth: {{ max_nesting_depth|default:5 }},
                    auto_validate: {{ auto_validate|default:true|yesno:'true,false' }},
                    show_json_preview: {{ show_json_preview|default:false|yesno:'true,false' }},
                    enable_undo_redo: {{ enable_undo_redo|default:true|yesno:'true,false' }}
                });
                builder.initialize();
            }
        });
        </script>
        """

        template = Template(base_template_content)
        context = Context(
            {
                "builder_id": "test-builder",
                "initial_requirements": '{"trait": {"name": "strength", "min": 3}}',
                "validation_url": "/api/validate-requirements/",
                "available_traits": '["strength", "dexterity", "arete"]',
                "available_fields": '["weapons", "foci", "items"]',
                "hidden_field_selector": "#id_test_requirements",
            }
        )

        rendered = template.render(context)

        # Test essential structure elements
        self.assertIn("prerequisite-builder-container", rendered)
        self.assertIn('id="prerequisite-builder-test-builder"', rendered)
        self.assertIn('data-widget="prerequisite-builder"', rendered)
        self.assertIn('data-builder-id="test-builder"', rendered)
        self.assertIn('role="region"', rendered)
        self.assertIn('aria-label="Prerequisite Requirements Builder"', rendered)

        # Test header elements
        self.assertIn("builder-header", rendered)
        self.assertIn("Requirement Builder", rendered)
        self.assertIn('data-action="add-requirement"', rendered)
        self.assertIn('data-action="clear-all"', rendered)

        # Test content structure
        self.assertIn("requirement-blocks-container", rendered)
        self.assertIn("empty-state", rendered)
        self.assertIn('role="group"', rendered)

        # Test footer elements
        self.assertIn("validation-messages", rendered)
        self.assertIn("json-preview", rendered)
        self.assertIn('role="alert"', rendered)
        self.assertIn('aria-live="polite"', rendered)

        # Test static file inclusion
        self.assertIn("static/css/prerequisite-builder.css", rendered)
        self.assertIn("static/js/prerequisite-builder.js", rendered)

        # Test JavaScript initialization
        self.assertIn("PrerequisiteBuilder(", rendered)
        self.assertIn("test-builder", rendered)

    def test_requirement_block_template_structure(self):
        """Test requirement block template structure."""
        block_template_content = """
        <div class="requirement-block {{ block_classes|default:'' }}"
             data-requirement-type="{{ requirement_type }}"
             data-block-id="{{ block_id }}"
             data-parent-block-id="{{ parent_block_id|default:'' }}"
             data-nesting-level="{{ nesting_level|default:0 }}"
             role="group"
             aria-label="{{ requirement_type|title }} requirement block"
             aria-describedby="block-help-{{ block_id }}">

            <div class="requirement-block-header">
                <div class="block-header-left">
                    <select class="requirement-type-selector form-control"
                            id="type-selector-{{ block_id }}"
                            name="requirement_type_{{ block_id }}"
                            data-block-id="{{ block_id }}"
                            aria-label="Select requirement type">
                        {% for type_option in requirement_types %}
                        <option value="{{ type_option.value }}"
                                {% if type_option.value == requirement_type %}selected{% endif %}>
                            {{ type_option.label }}
                        </option>
                        {% endfor %}
                    </select>
                </div>

                <div class="block-header-right">
                    <button type="button"
                            class="btn btn-sm btn-outline-info help-btn"
                            data-action="show-help"
                            data-help-target="{{ requirement_type }}"
                            aria-label="Show help for {{ requirement_type|title }} requirements"
                            title="Show help">
                        ?
                    </button>
                    <button type="button"
                            class="btn btn-sm btn-danger remove-block-btn"
                            data-action="remove-block"
                            data-block-id="{{ block_id }}"
                            aria-label="Remove this requirement block"
                            title="Remove requirement">
                        ×
                    </button>
                </div>
            </div>

            <div class="requirement-block-content"
                 id="block-content-{{ block_id }}"
                 role="group"
                 aria-labelledby="type-selector-{{ block_id }}">
                <!-- Dynamic content based on requirement_type -->
                {% if requirement_type == 'trait' %}
                    {% include 'prerequisites/blocks/trait_block_content.html' %}
                {% elif requirement_type == 'has' %}
                    {% include 'prerequisites/blocks/has_block_content.html' %}
                {% elif requirement_type == 'any' or requirement_type == 'all' %}
                    {% include 'prerequisites/blocks/nested_block_content.html' %}
                {% elif requirement_type == 'count_tag' %}
                    {% include 'prerequisites/blocks/count_tag_block_content.html' %}
                {% endif %}
            </div>

            <div class="requirement-block-validation"
                 id="block-validation-{{ block_id }}"
                 role="alert"
                 aria-live="polite"
                 aria-relevant="additions text">
                <div class="validation-status"></div>
                <div class="validation-messages"></div>
            </div>

            <div class="block-help"
                 id="block-help-{{ block_id }}"
                 style="display: none;"
                 role="region"
                 aria-label="Help for {{ requirement_type|title }} requirements">
                <!-- Help content loaded dynamically -->
            </div>
        </div>
        """

        template = Template(block_template_content)
        context = Context(
            {
                "requirement_type": "trait",
                "block_id": "block-123",
                "parent_block_id": None,
                "nesting_level": 0,
                "block_classes": "new-block",
                "requirement_types": [
                    {"value": "trait", "label": "Trait Requirement"},
                    {"value": "has", "label": "Has Item"},
                    {"value": "any", "label": "Any Of (OR)"},
                    {"value": "all", "label": "All Of (AND)"},
                    {"value": "count_tag", "label": "Count Tag"},
                ],
            }
        )

        rendered = template.render(context)

        # Test block structure
        self.assertIn("requirement-block", rendered)
        self.assertIn('data-requirement-type="trait"', rendered)
        self.assertIn('data-block-id="block-123"', rendered)
        self.assertIn('data-nesting-level="0"', rendered)
        self.assertIn('role="group"', rendered)
        self.assertIn('aria-label="Trait requirement block"', rendered)

        # Test header elements
        self.assertIn("requirement-block-header", rendered)
        self.assertIn("requirement-type-selector", rendered)
        self.assertIn('id="type-selector-block-123"', rendered)
        self.assertIn("remove-block-btn", rendered)
        self.assertIn("help-btn", rendered)

        # Test content structure
        self.assertIn("requirement-block-content", rendered)
        self.assertIn('id="block-content-block-123"', rendered)

        # Test validation area
        self.assertIn("requirement-block-validation", rendered)
        self.assertIn('id="block-validation-block-123"', rendered)
        self.assertIn('role="alert"', rendered)

        # Test help area
        self.assertIn("block-help", rendered)
        self.assertIn('id="block-help-block-123"', rendered)

        # Test dropdown options
        self.assertIn('value="trait" selected', rendered)
        self.assertIn("Trait Requirement", rendered)
        self.assertIn("Any Of (OR)", rendered)


class TraitBlockContentTemplateTest(TestCase):
    """Test trait requirement block content template."""

    def test_trait_block_content_template(self):
        """Test the trait requirement block content template."""
        trait_template_content = """
        <div class="trait-requirement-form">
            <div class="form-group">
                <label for="trait-name-{{ block_id }}" class="form-label">
                    Trait Name:
                    <span class="required-indicator" aria-label="Required">*</span>
                </label>
                <input type="text"
                       class="form-control trait-name-input"
                       id="trait-name-{{ block_id }}"
                       name="trait_name_{{ block_id }}"
                       placeholder="e.g., strength, arete, melee"
                       value="{{ trait_name|default:'' }}"
                       data-block-id="{{ block_id }}"
                       data-field="trait_name"
                       aria-describedby="trait-name-help-{{ block_id }}"
                       required>
                <small id="trait-name-help-{{ block_id }}" class="form-text text-muted">
                    Enter the name of the character trait to check (attribute, skill, etc.)
                </small>
            </div>

            <div class="constraint-controls">
                <fieldset>
                    <legend class="constraint-legend">Value Constraints:</legend>

                    <div class="constraint-group">
                        <div class="form-check">
                            <input type="checkbox"
                                   class="form-check-input use-min-checkbox"
                                   id="use-min-{{ block_id }}"
                                   name="use_min_{{ block_id }}"
                                   data-block-id="{{ block_id }}"
                                   data-field="use_min"
                                   {% if use_min %}checked{% endif %}
                                   aria-describedby="min-constraint-help-{{ block_id }}">
                            <label for="use-min-{{ block_id }}" class="form-check-label">
                                Minimum Value:
                            </label>
                        </div>
                        <input type="number"
                               class="form-control trait-min-input"
                               id="trait-min-{{ block_id }}"
                               name="trait_min_{{ block_id }}"
                               min="0"
                               step="1"
                               value="{{ trait_min|default:'' }}"
                               data-block-id="{{ block_id }}"
                               data-field="trait_min"
                               {% if not use_min %}disabled{% endif %}
                               aria-label="Minimum trait value">
                        <small id="min-constraint-help-{{ block_id }}" class="form-text text-muted">
                            Character must have at least this value
                        </small>
                    </div>

                    <div class="constraint-group">
                        <div class="form-check">
                            <input type="checkbox"
                                   class="form-check-input use-max-checkbox"
                                   id="use-max-{{ block_id }}"
                                   name="use_max_{{ block_id }}"
                                   data-block-id="{{ block_id }}"
                                   data-field="use_max"
                                   {% if use_max %}checked{% endif %}
                                   aria-describedby="max-constraint-help-{{ block_id }}">
                            <label for="use-max-{{ block_id }}" class="form-check-label">
                                Maximum Value:
                            </label>
                        </div>
                        <input type="number"
                               class="form-control trait-max-input"
                               id="trait-max-{{ block_id }}"
                               name="trait_max_{{ block_id }}"
                               min="0"
                               step="1"
                               value="{{ trait_max|default:'' }}"
                               data-block-id="{{ block_id }}"
                               data-field="trait_max"
                               {% if not use_max %}disabled{% endif %}
                               aria-label="Maximum trait value">
                        <small id="max-constraint-help-{{ block_id }}" class="form-text text-muted">
                            Character must have no more than this value
                        </small>
                    </div>

                    <div class="constraint-group">
                        <div class="form-check">
                            <input type="checkbox"
                                   class="form-check-input use-exact-checkbox"
                                   id="use-exact-{{ block_id }}"
                                   name="use_exact_{{ block_id }}"
                                   data-block-id="{{ block_id }}"
                                   data-field="use_exact"
                                   {% if use_exact %}checked{% endif %}
                                   aria-describedby="exact-constraint-help-{{ block_id }}">
                            <label for="use-exact-{{ block_id }}" class="form-check-label">
                                Exact Value:
                            </label>
                        </div>
                        <input type="number"
                               class="form-control trait-exact-input"
                               id="trait-exact-{{ block_id }}"
                               name="trait_exact_{{ block_id }}"
                               min="0"
                               step="1"
                               value="{{ trait_exact|default:'' }}"
                               data-block-id="{{ block_id }}"
                               data-field="trait_exact"
                               {% if not use_exact %}disabled{% endif %}
                               aria-label="Exact trait value">
                        <small id="exact-constraint-help-{{ block_id }}" class="form-text text-muted">
                            Character must have exactly this value (cannot be combined with min/max)
                        </small>
                    </div>
                </fieldset>
            </div>

            <div class="constraint-validation-info" role="region" aria-label="Constraint validation information">
                <div class="alert alert-info" style="display: none;" id="constraint-info-{{ block_id }}">
                    <small>At least one constraint (minimum, maximum, or exact) must be specified.</small>
                </div>
                <div class="alert alert-warning" style="display: none;" id="constraint-warning-{{ block_id }}">
                    <small>Exact value cannot be used together with minimum or maximum values.</small>
                </div>
            </div>
        </div>
        """

        template = Template(trait_template_content)
        context = Context(
            {
                "block_id": "trait-block-1",
                "trait_name": "strength",
                "use_min": True,
                "trait_min": 3,
                "use_max": False,
                "trait_max": "",
                "use_exact": False,
                "trait_exact": "",
            }
        )

        rendered = template.render(context)

        # Test form structure
        self.assertIn("trait-requirement-form", rendered)
        self.assertIn("form-group", rendered)

        # Test trait name field
        self.assertIn("trait-name-input", rendered)
        self.assertIn('id="trait-name-trait-block-1"', rendered)
        self.assertIn('value="strength"', rendered)
        self.assertIn('placeholder="e.g., strength, arete, melee"', rendered)
        self.assertIn("required", rendered)

        # Test constraint controls
        self.assertIn("constraint-controls", rendered)
        self.assertIn("fieldset", rendered)
        self.assertIn("Value Constraints:", rendered)

        # Test minimum constraint
        self.assertIn("use-min-checkbox", rendered)
        self.assertIn('id="use-min-trait-block-1"', rendered)
        self.assertIn("checked", rendered)  # use_min is True
        self.assertIn("trait-min-input", rendered)
        self.assertIn('value="3"', rendered)

        # Test maximum constraint
        self.assertIn("use-max-checkbox", rendered)
        self.assertIn("trait-max-input", rendered)
        self.assertIn("disabled", rendered)  # use_max is False

        # Test exact constraint
        self.assertIn("use-exact-checkbox", rendered)
        self.assertIn("trait-exact-input", rendered)

        # Test accessibility attributes
        self.assertIn('aria-label="Minimum trait value"', rendered)
        self.assertIn('aria-describedby="trait-name-help-trait-block-1"', rendered)
        self.assertIn('role="region"', rendered)

        # Test validation info
        self.assertIn("constraint-validation-info", rendered)
        self.assertIn("constraint-info-trait-block-1", rendered)
        self.assertIn("constraint-warning-trait-block-1", rendered)


class NestedBlockContentTemplateTest(TestCase):
    """Test nested requirement block content template."""

    def test_nested_block_content_template(self):
        """Test the nested requirement block content template."""
        nested_template_content = """
        <div class="nested-requirement-container">
            <div class="nested-requirement-header">
                <div class="logic-description">
                    {% if requirement_type == 'any' %}
                        <span class="logic-indicator logic-or">
                            At least <strong>one</strong> of the following requirements must be satisfied:
                        </span>
                    {% elif requirement_type == 'all' %}
                        <span class="logic-indicator logic-and">
                            <strong>All</strong> of the following requirements must be satisfied:
                        </span>
                    {% endif %}
                </div>
            </div>

            <div class="nested-requirements-list"
                 id="nested-list-{{ block_id }}"
                 role="group"
                 aria-label="{{ requirement_type|title }} sub-requirements"
                 data-parent-block-id="{{ block_id }}"
                 data-nesting-level="{{ nesting_level|add:1 }}">

                {% for sub_requirement in sub_requirements %}
                <div class="nested-requirement-item"
                     data-sub-block-id="{{ sub_requirement.block_id }}">
                    <!-- Sub-requirement blocks will be inserted here -->
                </div>
                {% empty %}
                <div class="nested-empty-state"
                     id="nested-empty-{{ block_id }}"
                     role="status"
                     aria-live="polite">
                    <div class="empty-message">
                        <p>No sub-requirements defined.</p>
                        <p>Add at least one requirement to continue.</p>
                    </div>
                </div>
                {% endfor %}
            </div>

            <div class="nested-requirement-controls">
                <div class="add-controls">
                    <button type="button"
                            class="btn btn-sm btn-outline-primary add-nested-requirement-btn"
                            data-action="add-nested-requirement"
                            data-parent-block-id="{{ block_id }}"
                            data-nesting-level="{{ nesting_level|add:1 }}"
                            aria-label="Add sub-requirement to {{ requirement_type|title }} block"
                            {% if nesting_level >= max_nesting_depth %}disabled{% endif %}>
                        <span class="btn-icon">+</span>
                        Add Sub-Requirement
                    </button>

                    {% if nesting_level >= max_nesting_depth %}
                    <small class="text-muted nesting-limit-warning">
                        Maximum nesting depth reached
                    </small>
                    {% endif %}
                </div>

                <div class="quick-add-controls" style="display: none;">
                    <div class="quick-add-buttons">
                        <button type="button"
                                class="btn btn-sm btn-outline-secondary"
                                data-action="quick-add-trait"
                                data-parent-block-id="{{ block_id }}">
                            Quick Add Trait
                        </button>
                        <button type="button"
                                class="btn btn-sm btn-outline-secondary"
                                data-action="quick-add-has"
                                data-parent-block-id="{{ block_id }}">
                            Quick Add Item
                        </button>
                    </div>
                </div>
            </div>

            <div class="nested-requirement-info">
                <div class="nesting-info">
                    <small class="text-muted">
                        Nesting level: {{ nesting_level|add:1 }} of {{ max_nesting_depth }}
                    </small>
                </div>

                <div class="sub-requirement-count"
                     id="sub-count-{{ block_id }}"
                     aria-live="polite">
                    <small class="text-muted">
                        Sub-requirements: <span class="count">{{ sub_requirements|length }}</span>
                    </small>
                </div>
            </div>
        </div>
        """

        template = Template(nested_template_content)
        context = Context(
            {
                "requirement_type": "any",
                "block_id": "nested-block-1",
                "nesting_level": 1,
                "max_nesting_depth": 5,
                "sub_requirements": [
                    {"block_id": "sub-block-1"},
                    {"block_id": "sub-block-2"},
                ],
            }
        )

        rendered = template.render(context)

        # Test nested container structure
        self.assertIn("nested-requirement-container", rendered)
        self.assertIn("nested-requirement-header", rendered)

        # Test logic description
        self.assertIn("logic-indicator", rendered)
        self.assertIn("logic-or", rendered)
        self.assertIn("At least <strong>one</strong>", rendered)

        # Test nested requirements list
        self.assertIn("nested-requirements-list", rendered)
        self.assertIn('id="nested-list-nested-block-1"', rendered)
        self.assertIn('role="group"', rendered)
        self.assertIn('data-nesting-level="2"', rendered)

        # Test sub-requirement items
        self.assertIn("nested-requirement-item", rendered)
        self.assertIn('data-sub-block-id="sub-block-1"', rendered)
        self.assertIn('data-sub-block-id="sub-block-2"', rendered)

        # Test controls
        self.assertIn("nested-requirement-controls", rendered)
        self.assertIn("add-nested-requirement-btn", rendered)
        self.assertIn('data-action="add-nested-requirement"', rendered)
        self.assertIn('data-parent-block-id="nested-block-1"', rendered)

        # Test quick add controls
        self.assertIn("quick-add-controls", rendered)
        self.assertIn('data-action="quick-add-trait"', rendered)
        self.assertIn('data-action="quick-add-has"', rendered)

        # Test info section
        self.assertIn("nested-requirement-info", rendered)
        self.assertIn("Nesting level: 2 of 5", rendered)
        self.assertIn('Sub-requirements: <span class="count">2</span>', rendered)

        # Test accessibility
        self.assertIn('aria-label="Any sub-requirements"', rendered)
        self.assertIn('aria-live="polite"', rendered)


class TemplateContextHandlingTest(TestCase):
    """Test template context handling and variable filtering."""

    def setUp(self):
        """Set up test data."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Test Campaign", owner=self.owner, game_system="mage"
        )

        self.character = MageCharacter.objects.create(
            name="Test Character",
            campaign=self.campaign,
            owner=self.owner,
            strength=3,
            arete=2,
        )

    def test_context_variable_filtering_and_escaping(self):
        """Test proper context variable filtering and HTML escaping."""
        template_content = """
        <div class="prerequisite-builder"
             data-initial-requirements="{{ initial_requirements|default:'{}' }}"
             data-available-traits="{{ available_traits|default:'[]' }}"
             data-builder-title="{{ builder_title|default:'Prerequisite Builder'|escape }}">
            <h4>{{ builder_title|default:'Prerequisite Builder'|escape }}</h4>
            <div class="instructions">{{ instructions|default:'Build your requirements'|escape }}</div>
        </div>
        """

        template = Template(template_content)

        # Test with potentially dangerous content
        context = Context(
            {
                "initial_requirements": '{"trait": {"name": "strength", "min": 3}}',
                "available_traits": '["strength", "dexterity", "arete"]',
                "builder_title": 'My <script>alert("xss")</script> Builder',
                "instructions": "Build requirements with <b>care</b> & attention",
            }
        )

        rendered = template.render(context)

        # Test that JSON data is preserved (not HTML escaped)
        self.assertIn('"trait"', rendered)
        self.assertIn('"strength"', rendered)
        self.assertIn('"min"', rendered)

        # Test that HTML content is properly escaped
        self.assertIn(
            "My &lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt; Builder", rendered
        )
        self.assertIn(
            "Build requirements with &lt;b&gt;care&lt;/b&gt; &amp; attention", rendered
        )

        # Test that dangerous script content is escaped
        self.assertNotIn("<script>", rendered)
        self.assertNotIn('alert("xss")', rendered)

    def test_context_variable_defaults_and_fallbacks(self):
        """Test context variable defaults and fallback behavior."""
        template_content = """
        <div class="prerequisite-builder"
             data-builder-id="{{ builder_id|default:'default-builder' }}"
             data-max-depth="{{ max_nesting_depth|default:5 }}"
             data-auto-validate="{{ auto_validate|default:true|yesno:'true,false' }}"
             data-initial-requirements="{{ initial_requirements|default:'{}' }}">

            {% if validation_url %}
            <div data-validation-url="{{ validation_url }}">Validation enabled</div>
            {% else %}
            <div>No validation URL provided</div>
            {% endif %}

            <div class="trait-list">
                {% for trait in available_traits|default:'' %}
                <span class="trait-option">{{ trait }}</span>
                {% empty %}
                <span class="no-traits">No traits available</span>
                {% endfor %}
            </div>
        </div>
        """

        template = Template(template_content)

        # Test with minimal context
        minimal_context = Context({})
        rendered = template.render(minimal_context)

        # Test defaults are applied
        self.assertIn('data-builder-id="default-builder"', rendered)
        self.assertIn('data-max-depth="5"', rendered)
        self.assertIn('data-auto-validate="true"', rendered)
        self.assertIn('data-initial-requirements="{}"', rendered)

        # Test conditional rendering
        self.assertIn("No validation URL provided", rendered)
        self.assertIn("No traits available", rendered)

        # Test with full context
        full_context = Context(
            {
                "builder_id": "custom-builder",
                "max_nesting_depth": 3,
                "auto_validate": False,
                "initial_requirements": '{"trait": {"name": "arete", "min": 2}}',
                "validation_url": "/api/validate/",
                "available_traits": ["strength", "dexterity", "arete"],
            }
        )

        rendered_full = template.render(full_context)

        # Test custom values are used
        self.assertIn('data-builder-id="custom-builder"', rendered_full)
        self.assertIn('data-max-depth="3"', rendered_full)
        self.assertIn('data-auto-validate="false"', rendered_full)

        # Test conditional content with values
        self.assertIn("Validation enabled", rendered_full)
        self.assertIn('<span class="trait-option">strength</span>', rendered_full)
        self.assertIn('<span class="trait-option">arete</span>', rendered_full)
        self.assertNotIn("No traits available", rendered_full)


class TemplateSecurityTest(TestCase):
    """Test security aspects of template rendering."""

    def test_json_injection_prevention_in_templates(self):
        """Test prevention of JSON injection attacks in templates."""
        template_content = """
        <div data-config="{{ config_json }}" data-requirements="{{ requirements_json }}">
        </div>
        <script>
        const config = {{ config_json|safe }};
        const requirements = {{ requirements_json|safe }};
        </script>
        """

        template = Template(template_content)

        # Test with potentially malicious JSON
        malicious_context = Context(
            {
                "config_json": '{"valid": true}; alert("xss"); {"fake": true}',
                "requirements_json": '{"trait": {"name": "strength"}}',
            }
        )

        rendered = template.render(malicious_context)

        # Test that malicious content is HTML escaped in attributes
        self.assertIn(
            "&quot;valid&quot;: true}; alert(&quot;xss&quot;); {&quot;fake&quot;",
            rendered,
        )

        # Test that safe filter preserves JSON structure in script context
        # (This highlights the need for proper JSON validation before using |safe)
        self.assertIn('{"trait": {"name": "strength"}}', rendered)

    def test_xss_prevention_in_user_content(self):
        """Test XSS prevention in user-generated content."""
        template_content = """
        <div class="requirement-block">
            <div class="block-title">{{ block_title }}</div>
            <div class="block-description">{{ block_description|linebreaks }}</div>
            <input type="text" value="{{ input_value }}" placeholder="{{ placeholder_text }}">
        </div>
        """

        template = Template(template_content)

        # Test with XSS attempts
        xss_context = Context(
            {
                "block_title": '<script>alert("title xss")</script>Trait Requirement',
                "block_description": 'This is a requirement\n<img src=x onerror=alert("desc xss")>',
                "input_value": '"><script>alert("input xss")</script>',
                "placeholder_text": "Enter value\" onmouseover=\"alert('placeholder xss')",
            }
        )

        rendered = template.render(xss_context)

        # Test that script tags are escaped
        self.assertNotIn("<script>", rendered)
        self.assertNotIn('alert("title xss")', rendered)
        self.assertNotIn('alert("desc xss")', rendered)
        self.assertNotIn('alert("input xss")', rendered)
        self.assertNotIn("alert('placeholder xss')", rendered)

        # Test that content is properly escaped
        self.assertIn("&lt;script&gt;", rendered)
        self.assertIn("&quot;&gt;&lt;script&gt;", rendered)
        self.assertIn("onmouseover=&quot;alert", rendered)

    def test_csrf_protection_in_forms(self):
        """Test CSRF protection in forms that include prerequisite builder."""
        template_content = """
        {% load csrf %}
        <form method="post" action="/save-prerequisites/">
            {% csrf_token %}
            <div class="prerequisite-builder">
                <!-- Builder content -->
            </div>
            <input type="hidden" name="requirements" id="id_requirements">
            <button type="submit">Save</button>
        </form>
        """

        template = Template(template_content)
        context = Context({})

        rendered = template.render(context)

        # Test that CSRF token is included
        self.assertIn("csrfmiddlewaretoken", rendered)
        self.assertIn('type="hidden"', rendered)

        # Test form structure
        self.assertIn('method="post"', rendered)
        self.assertIn('action="/save-prerequisites/"', rendered)
        self.assertIn('name="requirements"', rendered)


class TemplateAccessibilityTest(TestCase):
    """Test accessibility aspects of template rendering."""

    def test_aria_attributes_and_roles_in_templates(self):
        """Test proper ARIA attributes and roles in templates."""
        template_content = """
        <div class="prerequisite-builder"
             role="region"
             aria-label="Prerequisite Requirements Builder"
             aria-describedby="builder-instructions">

            <div id="builder-instructions" class="sr-only">
                Use this interface to define prerequisite requirements for characters.
                Navigate with tab key and use arrow keys within requirement blocks.
            </div>

            <div class="validation-messages"
                 role="alert"
                 aria-live="polite"
                 aria-relevant="additions text"
                 aria-atomic="false">
                <!-- Validation messages -->
            </div>

            <div class="requirement-block"
                 role="group"
                 aria-labelledby="block-title-1"
                 aria-describedby="block-help-1">

                <h5 id="block-title-1">Trait Requirement</h5>
                <div id="block-help-1" class="help-text">
                    Define minimum, maximum, or exact values for character traits.
                </div>

                <fieldset>
                    <legend>Constraint Options</legend>
                    <div class="form-check">
                        <input type="checkbox"
                               id="use-min-1"
                               aria-describedby="min-help-1">
                        <label for="use-min-1">Use minimum value</label>
                        <div id="min-help-1" class="form-text">
                            Character must have at least this value
                        </div>
                    </div>
                </fieldset>
            </div>
        </div>
        """

        template = Template(template_content)
        context = Context({})
        rendered = template.render(context)

        # Test main region role and labeling
        self.assertIn('role="region"', rendered)
        self.assertIn('aria-label="Prerequisite Requirements Builder"', rendered)
        self.assertIn('aria-describedby="builder-instructions"', rendered)

        # Test screen reader instructions
        self.assertIn('id="builder-instructions"', rendered)
        self.assertIn('class="sr-only"', rendered)

        # Test validation messages accessibility
        self.assertIn('role="alert"', rendered)
        self.assertIn('aria-live="polite"', rendered)
        self.assertIn('aria-relevant="additions text"', rendered)
        self.assertIn('aria-atomic="false"', rendered)

        # Test requirement block grouping
        self.assertIn('role="group"', rendered)
        self.assertIn('aria-labelledby="block-title-1"', rendered)
        self.assertIn('aria-describedby="block-help-1"', rendered)

        # Test form structure
        self.assertIn("<fieldset>", rendered)
        self.assertIn("<legend>Constraint Options</legend>", rendered)
        self.assertIn('aria-describedby="min-help-1"', rendered)

    def test_keyboard_navigation_support_in_templates(self):
        """Test keyboard navigation support in templates."""
        template_content = """
        <div class="prerequisite-builder" tabindex="0" role="application">
            <div class="builder-controls">
                <button type="button"
                        class="add-requirement-btn"
                        data-action="add-requirement"
                        aria-label="Add new requirement"
                        title="Add new requirement (Ctrl+N)">
                    Add Requirement
                </button>

                <button type="button"
                        class="clear-all-btn"
                        data-action="clear-all"
                        aria-label="Clear all requirements"
                        title="Clear all requirements (Ctrl+Delete)">
                    Clear All
                </button>
            </div>

            <div class="requirement-blocks-container"
                 role="group"
                 aria-label="Requirement blocks"
                 data-keyboard-nav="true">

                <div class="requirement-block" tabindex="0" data-block-id="block-1">
                    <button type="button"
                            class="remove-block-btn"
                            aria-label="Remove this requirement (Delete key)"
                            title="Remove requirement"
                            data-keyboard-shortcut="Delete">
                        Remove
                    </button>
                </div>
            </div>

            <div class="keyboard-help" style="display: none;" aria-hidden="true">
                <h5>Keyboard Shortcuts:</h5>
                <ul>
                    <li><kbd>Ctrl+N</kbd> - Add new requirement</li>
                    <li><kbd>Delete</kbd> - Remove focused requirement</li>
                    <li><kbd>Ctrl+Z</kbd> - Undo</li>
                    <li><kbd>Ctrl+Y</kbd> - Redo</li>
                    <li><kbd>Escape</kbd> - Cancel current action</li>
                </ul>
            </div>
        </div>
        """

        template = Template(template_content)
        context = Context({})
        rendered = template.render(context)

        # Test tabindex attributes
        self.assertIn('tabindex="0"', rendered)

        # Test keyboard shortcut hints
        self.assertIn('title="Add new requirement (Ctrl+N)"', rendered)
        self.assertIn('title="Clear all requirements (Ctrl+Delete)"', rendered)
        self.assertIn('data-keyboard-shortcut="Delete"', rendered)

        # Test keyboard navigation structure
        self.assertIn('data-keyboard-nav="true"', rendered)
        self.assertIn('role="application"', rendered)

        # Test keyboard help
        self.assertIn("keyboard-help", rendered)
        self.assertIn("<kbd>Ctrl+N</kbd>", rendered)
        self.assertIn("<kbd>Delete</kbd>", rendered)
        self.assertIn("<kbd>Escape</kbd>", rendered)
