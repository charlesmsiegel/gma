/**
 * Prerequisite Visual Builder JavaScript (Issue #190)
 *
 * This script provides the interactive visual builder for creating
 * complex prerequisite requirements in the Django admin interface.
 */

class PrerequisiteBuilder {
    constructor(fieldName, initialValue = null) {
        this.fieldName = fieldName;
        this.container = document.querySelector(`[data-field-name="${fieldName}"]`);
        this.hiddenInput = document.getElementById(`${fieldName}_input`);
        this.requirementBlocks = document.getElementById('requirement-blocks');

        if (!this.container || !this.hiddenInput) {
            console.error('PrerequisiteBuilder: Required DOM elements not found');
            return;
        }

        this.requirements = initialValue || {};
        this.setupEventListeners();
        this.render();
    }

    setupEventListeners() {
        // Add requirement button
        const addBtn = this.container.querySelector('#add-requirement-btn');
        if (addBtn) {
            addBtn.addEventListener('click', () => this.addRequirement());
        }

        // Clear requirements button
        const clearBtn = this.container.querySelector('#clear-requirements-btn');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.clearRequirements());
        }

        // Add first requirement button
        const addFirstBtn = this.container.querySelector('.add-first-requirement');
        if (addFirstBtn) {
            addFirstBtn.addEventListener('click', () => this.addRequirement());
        }
    }

    addRequirement(type = 'trait') {
        // Hide empty state
        const emptyState = this.container.querySelector('.empty-state');
        if (emptyState) {
            emptyState.style.display = 'none';
        }

        // Create new requirement block
        const blockId = `req_${Date.now()}`;
        const blockHTML = this.createRequirementBlockHTML(blockId, type);

        if (this.requirementBlocks) {
            this.requirementBlocks.insertAdjacentHTML('beforeend', blockHTML);

            // Setup event listeners for the new block
            this.setupBlockEventListeners(blockId);
        }

        this.updateHiddenInput();
    }

    createRequirementBlockHTML(blockId, type) {
        return `
            <div class="requirement-block" data-block-id="${blockId}">
                <button type="button" class="remove-requirement" onclick="this.parentElement.remove(); window.prerequisiteBuilder.updateHiddenInput();">×</button>

                <div class="requirement-type-selector">
                    <label>Type:</label>
                    <select name="req_type" onchange="window.prerequisiteBuilder.changeRequirementType('${blockId}', this.value)">
                        <option value="trait" ${type === 'trait' ? 'selected' : ''}>Trait Check</option>
                        <option value="has" ${type === 'has' ? 'selected' : ''}>Has Item/Feature</option>
                        <option value="any" ${type === 'any' ? 'selected' : ''}>Any Of</option>
                        <option value="all" ${type === 'all' ? 'selected' : ''}>All Of</option>
                        <option value="count_tag" ${type === 'count_tag' ? 'selected' : ''}>Count with Tag</option>
                    </select>
                </div>

                <div class="requirement-details" data-type="${type}">
                    ${this.createRequirementDetailsHTML(type, blockId)}
                </div>
            </div>
        `;
    }

    createRequirementDetailsHTML(type, blockId) {
        switch (type) {
            case 'trait':
                return `
                    <label>Trait Name:</label>
                    <input type="text" name="trait_name" placeholder="e.g., strength, arete" onchange="window.prerequisiteBuilder.updateHiddenInput()">

                    <label>Minimum:</label>
                    <input type="number" name="minimum" min="0" onchange="window.prerequisiteBuilder.updateHiddenInput()">

                    <label>Maximum:</label>
                    <input type="number" name="maximum" min="0" onchange="window.prerequisiteBuilder.updateHiddenInput()">
                `;

            case 'has':
                return `
                    <label>Field:</label>
                    <input type="text" name="field" placeholder="e.g., weapons, foci" onchange="window.prerequisiteBuilder.updateHiddenInput()">

                    <label>Name (optional):</label>
                    <input type="text" name="item_name" placeholder="e.g., Magic Sword" onchange="window.prerequisiteBuilder.updateHiddenInput()">

                    <label>ID (optional):</label>
                    <input type="number" name="item_id" onchange="window.prerequisiteBuilder.updateHiddenInput()">
                `;

            case 'any':
            case 'all':
                return `
                    <div class="nested-requirements">
                        <p>Nested requirements:</p>
                        <button type="button" onclick="window.prerequisiteBuilder.addNestedRequirement('${blockId}')">Add Nested Requirement</button>
                        <div class="nested-blocks"></div>
                    </div>
                `;

            case 'count_tag':
                return `
                    <label>Model:</label>
                    <input type="text" name="model" placeholder="e.g., spheres" onchange="window.prerequisiteBuilder.updateHiddenInput()">

                    <label>Tag:</label>
                    <input type="text" name="tag" placeholder="e.g., elemental" onchange="window.prerequisiteBuilder.updateHiddenInput()">

                    <label>Minimum Count:</label>
                    <input type="number" name="minimum" min="0" onchange="window.prerequisiteBuilder.updateHiddenInput()">
                `;

            default:
                return '<p>Select a requirement type</p>';
        }
    }

    changeRequirementType(blockId, newType) {
        const block = this.container.querySelector(`[data-block-id="${blockId}"]`);
        if (block) {
            const detailsContainer = block.querySelector('.requirement-details');
            detailsContainer.setAttribute('data-type', newType);
            detailsContainer.innerHTML = this.createRequirementDetailsHTML(newType, blockId);
            this.updateHiddenInput();
        }
    }

    addNestedRequirement(parentBlockId) {
        const parentBlock = this.container.querySelector(`[data-block-id="${parentBlockId}"]`);
        const nestedContainer = parentBlock.querySelector('.nested-blocks');

        const nestedId = `nested_${Date.now()}`;
        const nestedHTML = this.createRequirementBlockHTML(nestedId, 'trait');

        nestedContainer.insertAdjacentHTML('beforeend', `<div class="nested-requirement">${nestedHTML}</div>`);
        this.updateHiddenInput();
    }

    setupBlockEventListeners(blockId) {
        // Event listeners are set up inline in the HTML for simplicity
        // This could be refactored to use proper event delegation
    }

    clearRequirements() {
        if (this.requirementBlocks) {
            this.requirementBlocks.innerHTML = '';
        }

        // Show empty state
        const emptyState = this.container.querySelector('.empty-state');
        if (emptyState) {
            emptyState.style.display = 'block';
        }

        this.requirements = {};
        this.updateHiddenInput();
    }

    updateHiddenInput() {
        const requirements = this.buildRequirementsFromDOM();
        this.hiddenInput.value = JSON.stringify(requirements);
    }

    buildRequirementsFromDOM() {
        const blocks = this.container.querySelectorAll('.requirement-block');
        if (blocks.length === 0) {
            return {};
        }

        if (blocks.length === 1) {
            return this.buildRequirementFromBlock(blocks[0]);
        }

        // Multiple blocks - wrap in 'all'
        const requirements = [];
        blocks.forEach(block => {
            requirements.push(this.buildRequirementFromBlock(block));
        });

        return {
            type: 'all',
            requirements: requirements
        };
    }

    buildRequirementFromBlock(block) {
        const typeSelect = block.querySelector('select[name="req_type"]');
        const type = typeSelect ? typeSelect.value : 'trait';

        const requirement = { type: type };

        switch (type) {
            case 'trait':
                const traitName = block.querySelector('input[name="trait_name"]');
                const minimum = block.querySelector('input[name="minimum"]');
                const maximum = block.querySelector('input[name="maximum"]');

                if (traitName) requirement.name = traitName.value;
                if (minimum && minimum.value) requirement.minimum = parseInt(minimum.value);
                if (maximum && maximum.value) requirement.maximum = parseInt(maximum.value);
                break;

            case 'has':
                const field = block.querySelector('input[name="field"]');
                const itemName = block.querySelector('input[name="item_name"]');
                const itemId = block.querySelector('input[name="item_id"]');

                if (field) requirement.field = field.value;
                if (itemName && itemName.value) requirement.name = itemName.value;
                if (itemId && itemId.value) requirement.id = parseInt(itemId.value);
                break;

            case 'count_tag':
                const model = block.querySelector('input[name="model"]');
                const tag = block.querySelector('input[name="tag"]');
                const minCount = block.querySelector('input[name="minimum"]');

                if (model) requirement.model = model.value;
                if (tag) requirement.tag = tag.value;
                if (minCount && minCount.value) requirement.minimum = parseInt(minCount.value);
                break;
        }

        return requirement;
    }

    render() {
        if (this.requirements && Object.keys(this.requirements).length > 0) {
            // Hide empty state and render existing requirements
            const emptyState = this.container.querySelector('.empty-state');
            if (emptyState) {
                emptyState.style.display = 'none';
            }

            this.renderRequirement(this.requirements);
        }
    }

    renderRequirement(requirement) {
        if (!requirement || !requirement.type) return;

        const blockId = `existing_${Date.now()}`;
        const blockHTML = this.createRequirementBlockHTML(blockId, requirement.type);

        if (this.requirementBlocks) {
            this.requirementBlocks.insertAdjacentHTML('beforeend', blockHTML);

            // Populate with existing data
            this.populateBlock(blockId, requirement);
        }
    }

    populateBlock(blockId, requirement) {
        const block = this.container.querySelector(`[data-block-id="${blockId}"]`);
        if (!block) return;

        switch (requirement.type) {
            case 'trait':
                const traitName = block.querySelector('input[name="trait_name"]');
                const minimum = block.querySelector('input[name="minimum"]');
                const maximum = block.querySelector('input[name="maximum"]');

                if (traitName) traitName.value = requirement.name || '';
                if (minimum) minimum.value = requirement.minimum || '';
                if (maximum) maximum.value = requirement.maximum || '';
                break;

            case 'has':
                const field = block.querySelector('input[name="field"]');
                const itemName = block.querySelector('input[name="item_name"]');
                const itemId = block.querySelector('input[name="item_id"]');

                if (field) field.value = requirement.field || '';
                if (itemName) itemName.value = requirement.name || '';
                if (itemId) itemId.value = requirement.id || '';
                break;
        }
    }
}

// Make available globally for inline event handlers
window.prerequisiteBuilder = null;

// Initialize on DOM content loaded
document.addEventListener('DOMContentLoaded', function() {
    // Look for prerequisite builder widgets on the page
    const widgets = document.querySelectorAll('.prerequisite-builder-widget');

    widgets.forEach(widget => {
        const fieldName = widget.dataset.fieldName;
        const hiddenInput = widget.querySelector('input[type="hidden"]');
        const initialValue = hiddenInput ? hiddenInput.value : null;

        let parsedValue = null;
        if (initialValue) {
            try {
                parsedValue = JSON.parse(initialValue);
            } catch (e) {
                console.warn('Failed to parse initial value:', initialValue);
            }
        }

        // Create builder instance
        window.prerequisiteBuilder = new PrerequisiteBuilder(fieldName, parsedValue);
    });
});
