/**
 * DragDropCanvas Component (Issue #191)
 *
 * Main canvas area where requirements are visually arranged and manipulated
 * through drag-and-drop operations. Provides drop zones, visual feedback,
 * and layout management for complex prerequisite structures.
 */

class DragDropCanvas {
    constructor(dragDropBuilder) {
        this.builder = dragDropBuilder;
        this.containerElement = null;
        this.dropZones = [];
        this.requirements = [];
        this.layoutAlgorithm = 'hierarchical';

        this.initialize();
    }

    /**
     * Initialize the canvas component
     */
    initialize() {
        this.createCanvasStructure();
        this.setupDropZones();
        this.setupEventListeners();
        this.setupAccessibility();
    }

    /**
     * Create the HTML structure for the canvas
     */
    createCanvasStructure() {
        // Find or create canvas container
        this.containerElement = this.builder.containerElement.querySelector('.drag-drop-canvas');

        if (!this.containerElement) {
            this.containerElement = document.createElement('div');
            this.containerElement.className = 'drag-drop-canvas';
            this.builder.containerElement.appendChild(this.containerElement);
        }

        // Create canvas HTML structure
        this.containerElement.innerHTML = `
            <div class="canvas-header">
                <h3>Requirement Structure</h3>
                <div class="canvas-tools">
                    <button type="button" class="layout-btn" data-layout="hierarchical" aria-pressed="true">
                        Hierarchical
                    </button>
                    <button type="button" class="layout-btn" data-layout="flow" aria-pressed="false">
                        Flow
                    </button>
                    <button type="button" class="layout-btn" data-layout="compact" aria-pressed="false">
                        Compact
                    </button>
                    <button type="button" class="auto-arrange-btn">
                        Auto Arrange
                    </button>
                </div>
            </div>
            <div class="canvas-body">
                <div class="canvas-viewport">
                    <div class="requirements-container"
                         role="region"
                         aria-label="Requirement structure canvas">
                        <!-- Requirements will be rendered here -->
                    </div>
                </div>
                <div class="canvas-sidebar">
                    <div class="sidebar-section">
                        <h4>Structure Overview</h4>
                        <div class="structure-tree" role="tree"></div>
                    </div>
                    <div class="sidebar-section">
                        <h4>Validation</h4>
                        <div class="validation-status"></div>
                    </div>
                </div>
            </div>
            <div class="canvas-footer">
                <div class="canvas-status">
                    <span class="requirement-count">0 requirements</span>
                    <span class="validation-indicator">Valid</span>
                </div>
            </div>
        `;
    }

    /**
     * Set up drop zones throughout the canvas
     */
    setupDropZones() {
        this.createRootDropZone();
        this.updateDropZones();
    }

    /**
     * Create the root drop zone for top-level requirements
     */
    createRootDropZone() {
        const requirementsContainer = this.containerElement.querySelector('.requirements-container');

        // Create root drop zone if it doesn't exist
        if (!requirementsContainer.querySelector('.drop-zone-root')) {
            const rootDropZone = document.createElement('div');
            rootDropZone.className = 'drop-zone drop-zone-root';
            rootDropZone.dataset.dropZoneType = 'root';
            rootDropZone.setAttribute('role', 'region');
            rootDropZone.setAttribute('aria-label', 'Root drop zone for top-level requirements');

            rootDropZone.innerHTML = `
                <div class="drop-zone-indicator">
                    <div class="drop-zone-icon" aria-hidden="true">⊕</div>
                    <div class="drop-zone-text">Drop requirement here</div>
                </div>
                <div class="requirements-list" role="list"></div>
            `;

            requirementsContainer.appendChild(rootDropZone);
            this.dropZones.push(rootDropZone);
        }
    }

    /**
     * Update drop zones based on current requirements
     */
    updateDropZones() {
        // Remove old drop zones (except root)
        this.dropZones = this.dropZones.filter(zone =>
            zone.classList.contains('drop-zone-root')
        );

        // Add drop zones for logical containers (any/all)
        const logicalContainers = this.containerElement.querySelectorAll('[data-requirement-type="any"], [data-requirement-type="all"]');

        logicalContainers.forEach(container => {
            this.createLogicalContainerDropZone(container);
        });

        // Add insertion drop zones between existing requirements
        this.createInsertionDropZones();
    }

    /**
     * Create drop zones for logical containers (any/all)
     */
    createLogicalContainerDropZone(container) {
        const containerType = container.dataset.requirementType;

        if (!container.querySelector('.drop-zone-container')) {
            const dropZone = document.createElement('div');
            dropZone.className = `drop-zone drop-zone-container drop-zone-${containerType}`;
            dropZone.dataset.dropZoneType = `${containerType}_container`;
            dropZone.setAttribute('aria-label', `Drop zone for ${containerType} requirements`);

            dropZone.innerHTML = `
                <div class="drop-zone-indicator">
                    <div class="drop-zone-icon" aria-hidden="true">${containerType === 'any' ? '∨' : '∧'}</div>
                    <div class="drop-zone-text">Drop into ${containerType.toUpperCase()}</div>
                </div>
                <div class="requirements-list" role="list"></div>
            `;

            container.appendChild(dropZone);
            this.dropZones.push(dropZone);
        }
    }

    /**
     * Create insertion drop zones between requirements
     */
    createInsertionDropZones() {
        const requirementsList = this.containerElement.querySelectorAll('.requirements-list');

        requirementsList.forEach(list => {
            const requirements = list.querySelectorAll('.requirement-block');

            // Add insertion zones between requirements
            requirements.forEach((req, index) => {
                if (index > 0) {
                    const insertionZone = document.createElement('div');
                    insertionZone.className = 'drop-zone drop-zone-insertion';
                    insertionZone.dataset.dropZoneType = 'insertion';
                    insertionZone.dataset.insertionIndex = index;
                    insertionZone.setAttribute('aria-label', `Insert requirement at position ${index + 1}`);

                    insertionZone.innerHTML = `
                        <div class="insertion-indicator" aria-hidden="true">
                            <div class="insertion-line"></div>
                        </div>
                    `;

                    list.insertBefore(insertionZone, req);
                    this.dropZones.push(insertionZone);
                }
            });
        });
    }

    /**
     * Set up event listeners for canvas functionality
     */
    setupEventListeners() {
        // Layout switching
        this.containerElement.addEventListener('click', (event) => {
            const layoutBtn = event.target.closest('.layout-btn');
            if (layoutBtn) {
                this.switchLayout(layoutBtn.dataset.layout);
            }

            const autoArrangeBtn = event.target.closest('.auto-arrange-btn');
            if (autoArrangeBtn) {
                this.autoArrange();
            }
        });

        // Canvas drag and drop events
        this.containerElement.addEventListener('dragover', this.handleDragOver.bind(this));
        this.containerElement.addEventListener('drop', this.handleDrop.bind(this));

        // Requirement manipulation
        this.containerElement.addEventListener('click', this.handleRequirementClick.bind(this));
        this.containerElement.addEventListener('keydown', this.handleKeydown.bind(this));
    }

    /**
     * Set up accessibility features
     */
    setupAccessibility() {
        // Add ARIA attributes to canvas
        this.containerElement.setAttribute('role', 'main');
        this.containerElement.setAttribute('aria-label', 'Drag-and-drop canvas for requirement arrangement');

        // Add keyboard navigation instructions
        const instructions = document.createElement('div');
        instructions.className = 'sr-only canvas-instructions';
        instructions.textContent = 'Use arrow keys to navigate requirements. Press Enter to edit, Delete to remove, or D to activate drag mode.';
        this.containerElement.insertBefore(instructions, this.containerElement.firstChild);
    }

    /**
     * Handle drag over events on canvas
     */
    handleDragOver(event) {
        event.preventDefault();

        const dropZone = event.target.closest('.drop-zone');
        if (!dropZone) return;

        // Visual feedback for valid/invalid drops
        const dragData = this.getDragData(event);
        if (this.isValidCanvasDrop(dragData, dropZone)) {
            dropZone.classList.add('drop-zone-hover');
            event.dataTransfer.dropEffect = 'move';
        } else {
            dropZone.classList.add('drop-zone-invalid');
            event.dataTransfer.dropEffect = 'none';
        }
    }

    /**
     * Handle drop events on canvas
     */
    handleDrop(event) {
        event.preventDefault();

        const dropZone = event.target.closest('.drop-zone');
        if (!dropZone) return;

        // Clear visual feedback
        dropZone.classList.remove('drop-zone-hover', 'drop-zone-invalid');

        const dragData = this.getDragData(event);
        if (!this.isValidCanvasDrop(dragData, dropZone)) {
            return;
        }

        // Perform drop operation
        this.performCanvasDrop(dragData, dropZone);

        // Update canvas state
        this.updateRequirementsList();
        this.updateDropZones();
        this.updateStructureTree();
        this.updateValidationStatus();

        // Announce to screen readers
        this.builder.announceToScreenReader(
            `Added ${dragData.type} requirement to ${dropZone.dataset.dropZoneType}.`
        );
    }

    /**
     * Extract drag data from drop event
     */
    getDragData(event) {
        try {
            const jsonData = event.dataTransfer.getData('text/json');
            return jsonData ? JSON.parse(jsonData) : null;
        } catch (error) {
            console.warn('Failed to parse drag data:', error);
            return null;
        }
    }

    /**
     * Validate if drop is allowed on canvas
     */
    isValidCanvasDrop(dragData, dropZone) {
        if (!dragData) return false;

        const dropType = dropZone.dataset.dropZoneType;

        switch (dropType) {
            case 'root':
                return true; // All requirements can be dropped at root

            case 'any_container':
            case 'all_container':
                return true; // All requirements can be dropped into logical containers

            case 'insertion':
                return true; // All requirements can be inserted between existing ones

            default:
                return false;
        }
    }

    /**
     * Perform drop operation on canvas
     */
    performCanvasDrop(dragData, dropZone) {
        const requirementElement = this.createRequirementElement(dragData);

        if (dropZone.dataset.dropZoneType === 'insertion') {
            // Insert at specific position
            const insertionIndex = parseInt(dropZone.dataset.insertionIndex);
            const requirementsList = dropZone.closest('.requirements-list');
            const existingRequirements = requirementsList.querySelectorAll('.requirement-block');

            if (insertionIndex < existingRequirements.length) {
                requirementsList.insertBefore(requirementElement, existingRequirements[insertionIndex]);
            } else {
                requirementsList.appendChild(requirementElement);
            }
        } else {
            // Add to container
            const requirementsList = dropZone.querySelector('.requirements-list');
            requirementsList.appendChild(requirementElement);
        }
    }

    /**
     * Create requirement element from drag data
     */
    createRequirementElement(dragData) {
        const element = document.createElement('div');
        element.className = 'requirement-block draggable';
        element.draggable = true;
        element.dataset.requirementType = dragData.type;
        element.dataset.requirementId = dragData.id;
        element.setAttribute('role', 'listitem');
        element.setAttribute('tabindex', '0');

        // Generate content based on requirement type
        const content = this.generateRequirementContent(dragData);
        element.innerHTML = content;

        return element;
    }

    /**
     * Generate HTML content for requirement element
     */
    generateRequirementContent(dragData) {
        switch (dragData.type) {
            case 'trait':
                return this.generateTraitContent(dragData.template || dragData.data);

            case 'has':
                return this.generateHasContent(dragData.template || dragData.data);

            case 'count_tag':
                return this.generateCountTagContent(dragData.template || dragData.data);

            case 'any':
                return this.generateLogicalContent(dragData.template || dragData.data, 'any');

            case 'all':
                return this.generateLogicalContent(dragData.template || dragData.data, 'all');

            default:
                return this.generateGenericContent(dragData);
        }
    }

    /**
     * Generate content for trait requirements
     */
    generateTraitContent(data) {
        const trait = data.trait || {};
        return `
            <div class="requirement-header">
                <div class="requirement-icon" aria-hidden="true">⚡</div>
                <div class="requirement-title">Trait Check</div>
                <div class="requirement-actions">
                    <button type="button" class="edit-btn" aria-label="Edit requirement">✏️</button>
                    <button type="button" class="delete-btn" aria-label="Delete requirement">🗑️</button>
                </div>
            </div>
            <div class="requirement-content">
                <div class="trait-name">${trait.name || 'Select trait...'}</div>
                <div class="trait-constraints">
                    ${trait.min ? `Min: ${trait.min}` : ''}
                    ${trait.max ? `Max: ${trait.max}` : ''}
                </div>
            </div>
        `;
    }

    /**
     * Generate content for has requirements
     */
    generateHasContent(data) {
        const has = data.has || {};
        return `
            <div class="requirement-header">
                <div class="requirement-icon" aria-hidden="true">🎯</div>
                <div class="requirement-title">Has Item/Feature</div>
                <div class="requirement-actions">
                    <button type="button" class="edit-btn" aria-label="Edit requirement">✏️</button>
                    <button type="button" class="delete-btn" aria-label="Delete requirement">🗑️</button>
                </div>
            </div>
            <div class="requirement-content">
                <div class="has-field">${has.field || 'Select field...'}</div>
                <div class="has-name">${has.name || 'Any'}</div>
            </div>
        `;
    }

    /**
     * Generate content for count_tag requirements
     */
    generateCountTagContent(data) {
        const countTag = data.count_tag || {};
        return `
            <div class="requirement-header">
                <div class="requirement-icon" aria-hidden="true">📊</div>
                <div class="requirement-title">Count with Tag</div>
                <div class="requirement-actions">
                    <button type="button" class="edit-btn" aria-label="Edit requirement">✏️</button>
                    <button type="button" class="delete-btn" aria-label="Delete requirement">🗑️</button>
                </div>
            </div>
            <div class="requirement-content">
                <div class="count-tag">${countTag.tag || 'Select tag...'}</div>
                <div class="count-min">Min: ${countTag.min || 1}</div>
            </div>
        `;
    }

    /**
     * Generate content for logical requirements (any/all)
     */
    generateLogicalContent(data, type) {
        const icon = type === 'any' ? '🔀' : '🔗';
        const title = type === 'any' ? 'Any Of (OR)' : 'All Of (AND)';

        return `
            <div class="requirement-header">
                <div class="requirement-icon" aria-hidden="true">${icon}</div>
                <div class="requirement-title">${title}</div>
                <div class="requirement-actions">
                    <button type="button" class="edit-btn" aria-label="Edit requirement">✏️</button>
                    <button type="button" class="delete-btn" aria-label="Delete requirement">🗑️</button>
                </div>
            </div>
            <div class="requirement-content logical-container">
                <!-- Nested requirements will be added here via drop zones -->
            </div>
        `;
    }

    /**
     * Generate generic content fallback
     */
    generateGenericContent(dragData) {
        return `
            <div class="requirement-header">
                <div class="requirement-icon" aria-hidden="true">❓</div>
                <div class="requirement-title">${dragData.type || 'Unknown'}</div>
                <div class="requirement-actions">
                    <button type="button" class="edit-btn" aria-label="Edit requirement">✏️</button>
                    <button type="button" class="delete-btn" aria-label="Delete requirement">🗑️</button>
                </div>
            </div>
            <div class="requirement-content">
                <pre>${JSON.stringify(dragData.template || dragData.data, null, 2)}</pre>
            </div>
        `;
    }

    /**
     * Handle requirement click events (edit/delete)
     */
    handleRequirementClick(event) {
        const editBtn = event.target.closest('.edit-btn');
        if (editBtn) {
            this.editRequirement(editBtn.closest('.requirement-block'));
            return;
        }

        const deleteBtn = event.target.closest('.delete-btn');
        if (deleteBtn) {
            this.deleteRequirement(deleteBtn.closest('.requirement-block'));
            return;
        }
    }

    /**
     * Handle keyboard navigation on canvas
     */
    handleKeydown(event) {
        const requirement = event.target.closest('.requirement-block');
        if (!requirement) return;

        switch (event.key) {
            case 'Delete':
            case 'Backspace':
                event.preventDefault();
                this.deleteRequirement(requirement);
                break;

            case 'Enter':
                event.preventDefault();
                this.editRequirement(requirement);
                break;

            case 'd':
            case 'D':
                if (this.builder.accessibilityManager) {
                    event.preventDefault();
                    this.builder.accessibilityManager.activateKeyboardDrag(requirement);
                }
                break;
        }
    }

    /**
     * Switch canvas layout algorithm
     */
    switchLayout(layout) {
        // Update button states
        this.containerElement.querySelectorAll('.layout-btn').forEach(btn => {
            btn.setAttribute('aria-pressed', 'false');
        });

        const activeBtn = this.containerElement.querySelector(`[data-layout="${layout}"]`);
        if (activeBtn) {
            activeBtn.setAttribute('aria-pressed', 'true');
        }

        // Apply layout
        this.layoutAlgorithm = layout;
        this.containerElement.className = `drag-drop-canvas layout-${layout}`;

        this.arrangeRequirements();
    }

    /**
     * Auto-arrange requirements using current layout algorithm
     */
    autoArrange() {
        this.arrangeRequirements();
        this.builder.announceToScreenReader('Requirements auto-arranged using ' + this.layoutAlgorithm + ' layout.');
    }

    /**
     * Arrange requirements based on current layout algorithm
     */
    arrangeRequirements() {
        switch (this.layoutAlgorithm) {
            case 'hierarchical':
                this.arrangeHierarchical();
                break;
            case 'flow':
                this.arrangeFlow();
                break;
            case 'compact':
                this.arrangeCompact();
                break;
        }
    }

    /**
     * Arrange requirements in hierarchical layout
     */
    arrangeHierarchical() {
        // Implementation for hierarchical arrangement
        const requirements = this.containerElement.querySelectorAll('.requirement-block');
        requirements.forEach((req, index) => {
            req.style.transform = `translateY(${index * 120}px)`;
        });
    }

    /**
     * Arrange requirements in flow layout
     */
    arrangeFlow() {
        // Implementation for flow arrangement
        const requirements = this.containerElement.querySelectorAll('.requirement-block');
        let x = 0, y = 0;
        const rowHeight = 120;
        const columnWidth = 300;
        const maxColumns = 3;

        requirements.forEach((req, index) => {
            const col = index % maxColumns;
            const row = Math.floor(index / maxColumns);
            req.style.transform = `translate(${col * columnWidth}px, ${row * rowHeight}px)`;
        });
    }

    /**
     * Arrange requirements in compact layout
     */
    arrangeCompact() {
        // Implementation for compact arrangement
        const requirements = this.containerElement.querySelectorAll('.requirement-block');
        requirements.forEach((req, index) => {
            req.style.transform = `translateY(${index * 80}px)`;
        });
    }

    /**
     * Update the requirements list
     */
    updateRequirementsList() {
        const requirements = this.containerElement.querySelectorAll('.requirement-block');
        this.requirements = Array.from(requirements).map(req => ({
            id: req.dataset.requirementId,
            type: req.dataset.requirementType,
            element: req
        }));

        // Update requirement count
        const countElement = this.containerElement.querySelector('.requirement-count');
        if (countElement) {
            countElement.textContent = `${this.requirements.length} requirements`;
        }
    }

    /**
     * Update the structure tree in sidebar
     */
    updateStructureTree() {
        const treeContainer = this.containerElement.querySelector('.structure-tree');
        if (!treeContainer) return;

        const treeHTML = this.generateStructureTree();
        treeContainer.innerHTML = treeHTML;
    }

    /**
     * Generate structure tree HTML
     */
    generateStructureTree() {
        const rootRequirements = this.containerElement.querySelectorAll('.drop-zone-root > .requirements-list > .requirement-block');

        if (rootRequirements.length === 0) {
            return '<div class="tree-empty">No requirements</div>';
        }

        return Array.from(rootRequirements).map(req =>
            this.generateTreeNode(req)
        ).join('');
    }

    /**
     * Generate tree node HTML
     */
    generateTreeNode(requirement) {
        const type = requirement.dataset.requirementType;
        const id = requirement.dataset.requirementId;

        const nested = requirement.querySelectorAll('.requirement-block');
        const hasNested = nested.length > 0;

        return `
            <div class="tree-node" data-requirement-id="${id}">
                <div class="tree-node-content">
                    <span class="tree-node-icon">${this.getTypeIcon(type)}</span>
                    <span class="tree-node-type">${type}</span>
                    ${hasNested ? `<span class="tree-node-count">(${nested.length})</span>` : ''}
                </div>
                ${hasNested ? `
                    <div class="tree-node-children">
                        ${Array.from(nested).map(child => this.generateTreeNode(child)).join('')}
                    </div>
                ` : ''}
            </div>
        `;
    }

    /**
     * Get icon for requirement type
     */
    getTypeIcon(type) {
        const icons = {
            trait: '⚡',
            has: '🎯',
            count_tag: '📊',
            any: '🔀',
            all: '🔗'
        };
        return icons[type] || '❓';
    }

    /**
     * Update validation status
     */
    updateValidationStatus() {
        const statusElement = this.containerElement.querySelector('.validation-status');
        const indicatorElement = this.containerElement.querySelector('.validation-indicator');

        if (!statusElement || !indicatorElement) return;

        // Perform validation
        const validation = this.validateCurrentStructure();

        statusElement.innerHTML = validation.errors.length > 0 ?
            `<div class="validation-errors">${validation.errors.join('<br>')}</div>` :
            '<div class="validation-success">Structure is valid</div>';

        indicatorElement.textContent = validation.errors.length > 0 ? 'Invalid' : 'Valid';
        indicatorElement.className = `validation-indicator ${validation.errors.length > 0 ? 'invalid' : 'valid'}`;
    }

    /**
     * Validate current requirement structure
     */
    validateCurrentStructure() {
        const errors = [];

        // Check for empty logical containers
        const logicalContainers = this.containerElement.querySelectorAll('[data-requirement-type="any"], [data-requirement-type="all"]');
        logicalContainers.forEach(container => {
            const nested = container.querySelectorAll('.requirement-block');
            if (nested.length === 0) {
                errors.push(`${container.dataset.requirementType.toUpperCase()} container is empty`);
            }
        });

        return { errors };
    }

    /**
     * Edit requirement (open edit dialog)
     */
    editRequirement(requirement) {
        // Implementation would open edit dialog
        console.log('Edit requirement:', requirement);
    }

    /**
     * Delete requirement with confirmation
     */
    deleteRequirement(requirement) {
        if (confirm('Are you sure you want to delete this requirement?')) {
            requirement.remove();
            this.updateRequirementsList();
            this.updateDropZones();
            this.updateStructureTree();
            this.updateValidationStatus();

            this.builder.announceToScreenReader('Requirement deleted.');
        }
    }

    /**
     * Public API for getting current canvas state
     */
    getState() {
        return {
            layoutAlgorithm: this.layoutAlgorithm,
            requirementCount: this.requirements.length,
            dropZoneCount: this.dropZones.length,
            validationStatus: this.validateCurrentStructure()
        };
    }
}
