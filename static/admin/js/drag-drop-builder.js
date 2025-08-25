/**
 * Drag-and-Drop Prerequisite Builder (Issue #191)
 *
 * Enhanced visual prerequisite builder with drag-and-drop functionality.
 * Extends the existing PrerequisiteBuilder to provide intuitive drag-and-drop
 * interfaces for creating complex prerequisite requirements.
 */

/**
 * Main DragDropBuilder class that orchestrates drag-and-drop functionality
 * for prerequisite building. Extends the existing PrerequisiteBuilder to
 * maintain backward compatibility.
 */
class DragDropBuilder extends PrerequisiteBuilder {
    constructor(containerElement, hiddenFieldElement, options = {}) {
        super(containerElement, hiddenFieldElement, options);

        // Drag-and-drop specific options
        this.dragDropOptions = {
            enableDragDrop: true,
            enableTouch: true,
            enableKeyboardDrag: true,
            enableUndoRedo: true,
            performanceMonitoring: false,
            accessibility: {
                announcements: true,
                ariaSupport: true,
                keyboardNavigation: true
            },
            ...options.dragDrop
        };

        // Component instances
        this.palette = null;
        this.canvas = null;
        this.dropZones = [];
        this.touchHandler = null;
        this.accessibilityManager = null;
        this.undoRedoManager = null;

        // State management
        this.dragState = {
            isDragging: false,
            dragElement: null,
            dragData: null,
            sourceContainer: null,
            ghostElement: null,
            startPosition: { x: 0, y: 0 },
            currentPosition: { x: 0, y: 0 }
        };

        this.initialize();
    }

    /**
     * Initialize all drag-and-drop components and event listeners
     */
    initialize() {
        try {
            this.createComponents();
            this.setupEventListeners();
            this.setupAccessibility();

            // Announce successful initialization to screen readers
            if (this.dragDropOptions.accessibility.announcements) {
                this.announceToScreenReader(
                    "Drag-and-drop prerequisite builder initialized. Use 'd' key to activate drag mode."
                );
            }

        } catch (error) {
            console.error('DragDropBuilder initialization failed:', error);
            // Fallback to regular visual builder
            this.dragDropOptions.enableDragDrop = false;
        }
    }

    /**
     * Create all drag-and-drop component instances
     */
    createComponents() {
        // Create palette for dragging new requirement types
        this.palette = new DragDropPalette(this);

        // Create canvas for main arrangement area
        this.canvas = new DragDropCanvas(this);

        // Create touch handler for mobile support
        if (this.dragDropOptions.enableTouch) {
            this.touchHandler = new TouchHandler(this);
        }

        // Create accessibility manager for keyboard navigation
        if (this.dragDropOptions.accessibility.keyboardNavigation) {
            this.accessibilityManager = new AccessibilityManager(this);
        }

        // Create undo/redo manager for operation history
        if (this.dragDropOptions.enableUndoRedo) {
            this.undoRedoManager = new UndoRedoManager(this);
        }
    }

    /**
     * Set up all drag-and-drop event listeners
     */
    setupEventListeners() {
        // Standard drag events
        this.containerElement.addEventListener('dragstart', this.handleDragStart.bind(this));
        this.containerElement.addEventListener('dragover', this.handleDragOver.bind(this));
        this.containerElement.addEventListener('drop', this.handleDrop.bind(this));
        this.containerElement.addEventListener('dragend', this.handleDragEnd.bind(this));

        // Keyboard events for accessibility
        this.containerElement.addEventListener('keydown', this.handleKeydown.bind(this));

        // Performance monitoring
        if (this.dragDropOptions.performanceMonitoring) {
            this.setupPerformanceMonitoring();
        }
    }

    /**
     * Set up accessibility features
     */
    setupAccessibility() {
        // Add ARIA attributes
        this.containerElement.setAttribute('role', 'application');
        this.containerElement.setAttribute('aria-label', 'Drag-and-drop prerequisite builder');

        // Create live region for announcements
        this.liveRegion = document.createElement('div');
        this.liveRegion.setAttribute('aria-live', 'polite');
        this.liveRegion.setAttribute('aria-atomic', 'true');
        this.liveRegion.className = 'sr-only';
        this.containerElement.appendChild(this.liveRegion);
    }

    /**
     * Handle drag start events
     */
    handleDragStart(event) {
        if (!this.dragDropOptions.enableDragDrop) {
            event.preventDefault();
            return;
        }

        const dragElement = event.target.closest('.draggable');
        if (!dragElement) {
            event.preventDefault();
            return;
        }

        this.dragState.isDragging = true;
        this.dragState.dragElement = dragElement;
        this.dragState.sourceContainer = dragElement.closest('.requirement-container');
        this.dragState.startPosition = { x: event.clientX, y: event.clientY };

        // Extract drag data
        this.dragState.dragData = this.extractDragData(dragElement);

        // Set drag effect
        event.dataTransfer.effectAllowed = 'move';
        event.dataTransfer.setData('text/json', JSON.stringify(this.dragState.dragData));

        // Create ghost element for visual feedback
        this.createGhostElement(dragElement);

        // Highlight valid drop zones
        this.highlightDropZones(this.dragState.dragData);

        // Announce drag start to screen readers
        this.announceToScreenReader(
            `Started dragging ${this.dragState.dragData.type} requirement. Use arrow keys to navigate drop zones.`
        );
    }

    /**
     * Handle drag over events
     */
    handleDragOver(event) {
        if (!this.dragState.isDragging) return;

        event.preventDefault();

        const dropZone = event.target.closest('.drop-zone');
        if (!dropZone) return;

        // Update current position
        this.dragState.currentPosition = { x: event.clientX, y: event.clientY };

        // Validate drop compatibility
        if (this.isValidDrop(this.dragState.dragData, dropZone)) {
            event.dataTransfer.dropEffect = 'move';
            dropZone.classList.add('drop-zone-valid');
            dropZone.classList.remove('drop-zone-invalid');
        } else {
            event.dataTransfer.dropEffect = 'none';
            dropZone.classList.add('drop-zone-invalid');
            dropZone.classList.remove('drop-zone-valid');
        }
    }

    /**
     * Handle drop events
     */
    handleDrop(event) {
        if (!this.dragState.isDragging) return;

        event.preventDefault();

        const dropZone = event.target.closest('.drop-zone');
        if (!dropZone || !this.isValidDrop(this.dragState.dragData, dropZone)) {
            this.cancelDrag();
            return;
        }

        // Perform the drop operation
        const success = this.performDrop(this.dragState.dragData, dropZone);

        if (success) {
            // Record operation for undo/redo
            if (this.undoRedoManager) {
                this.undoRedoManager.recordOperation({
                    type: 'move',
                    element: this.dragState.dragElement,
                    from: this.dragState.sourceContainer,
                    to: dropZone,
                    data: this.dragState.dragData
                });
            }

            // Update JSON output
            this.updateJSONOutput();

            // Announce success to screen readers
            this.announceToScreenReader(
                `Successfully moved ${this.dragState.dragData.type} requirement to ${dropZone.dataset.dropZoneType}.`
            );
        }

        this.cleanupDrag();
    }

    /**
     * Handle drag end events
     */
    handleDragEnd(event) {
        this.cleanupDrag();
    }

    /**
     * Handle keyboard events for accessibility
     */
    handleKeydown(event) {
        if (!this.accessibilityManager) return;

        // Delegate to accessibility manager
        this.accessibilityManager.handleKeydown(event);
    }

    /**
     * Extract drag data from element
     */
    extractDragData(element) {
        const requirementBlock = element.closest('.requirement-block');
        if (!requirementBlock) return null;

        return {
            type: requirementBlock.dataset.requirementType || 'unknown',
            id: requirementBlock.id || `req_${Date.now()}`,
            data: this.getRequirementData(requirementBlock),
            html: requirementBlock.outerHTML
        };
    }

    /**
     * Create visual ghost element during drag
     */
    createGhostElement(element) {
        const ghost = element.cloneNode(true);
        ghost.className = 'drag-ghost';
        ghost.style.position = 'fixed';
        ghost.style.pointerEvents = 'none';
        ghost.style.zIndex = '9999';
        ghost.style.opacity = '0.5';
        document.body.appendChild(ghost);
        this.dragState.ghostElement = ghost;
    }

    /**
     * Highlight valid drop zones
     */
    highlightDropZones(dragData) {
        const dropZones = this.containerElement.querySelectorAll('.drop-zone');

        dropZones.forEach(zone => {
            if (this.isValidDrop(dragData, zone)) {
                zone.classList.add('drop-zone-available');
            } else {
                zone.classList.add('drop-zone-unavailable');
            }
        });
    }

    /**
     * Validate if drop is allowed
     */
    isValidDrop(dragData, dropZone) {
        const dropType = dropZone.dataset.dropZoneType;

        // Basic compatibility rules
        switch (dropType) {
            case 'any_container':
            case 'all_container':
                return true; // All requirement types can be dropped into logical containers

            case 'root':
                return true; // All requirement types can be dropped at root level

            case 'trait_container':
                return dragData.type === 'trait';

            default:
                return false;
        }
    }

    /**
     * Perform the actual drop operation
     */
    performDrop(dragData, dropZone) {
        try {
            // Remove element from source
            if (this.dragState.dragElement && this.dragState.dragElement.parentNode) {
                this.dragState.dragElement.parentNode.removeChild(this.dragState.dragElement);
            }

            // Add element to target
            const targetContainer = dropZone.querySelector('.requirements-list') || dropZone;
            const newElement = this.createElement(dragData);
            targetContainer.appendChild(newElement);

            return true;
        } catch (error) {
            console.error('Drop operation failed:', error);
            return false;
        }
    }

    /**
     * Create element from drag data
     */
    createElement(dragData) {
        const template = document.createElement('div');
        template.innerHTML = dragData.html;
        return template.firstElementChild;
    }

    /**
     * Cancel drag operation
     */
    cancelDrag() {
        this.announceToScreenReader('Drag operation cancelled.');
        this.cleanupDrag();
    }

    /**
     * Clean up after drag operation
     */
    cleanupDrag() {
        // Reset drag state
        this.dragState.isDragging = false;
        this.dragState.dragElement = null;
        this.dragState.dragData = null;
        this.dragState.sourceContainer = null;

        // Remove ghost element
        if (this.dragState.ghostElement) {
            document.body.removeChild(this.dragState.ghostElement);
            this.dragState.ghostElement = null;
        }

        // Clear drop zone highlights
        const dropZones = this.containerElement.querySelectorAll('.drop-zone');
        dropZones.forEach(zone => {
            zone.classList.remove(
                'drop-zone-available',
                'drop-zone-unavailable',
                'drop-zone-valid',
                'drop-zone-invalid'
            );
        });
    }

    /**
     * Announce message to screen readers
     */
    announceToScreenReader(message) {
        if (!this.dragDropOptions.accessibility.announcements) return;

        if (this.liveRegion) {
            this.liveRegion.textContent = message;

            // Clear after announcement
            setTimeout(() => {
                this.liveRegion.textContent = '';
            }, 1000);
        }
    }

    /**
     * Set up performance monitoring
     */
    setupPerformanceMonitoring() {
        this.performanceMetrics = {
            dragStartTime: 0,
            dropCompleteTime: 0,
            frameCount: 0
        };

        // Monitor frame rate during drag
        const monitorFrameRate = () => {
            if (this.dragState.isDragging) {
                this.performanceMetrics.frameCount++;
                requestAnimationFrame(monitorFrameRate);
            }
        };

        this.containerElement.addEventListener('dragstart', () => {
            this.performanceMetrics.dragStartTime = performance.now();
            this.performanceMetrics.frameCount = 0;
            requestAnimationFrame(monitorFrameRate);
        });

        this.containerElement.addEventListener('drop', () => {
            this.performanceMetrics.dropCompleteTime = performance.now();
            const totalTime = this.performanceMetrics.dropCompleteTime - this.performanceMetrics.dragStartTime;
            const frameRate = this.performanceMetrics.frameCount / (totalTime / 1000);

            console.log('Drag-drop performance:', {
                totalTime: `${totalTime.toFixed(2)}ms`,
                frameRate: `${frameRate.toFixed(2)}fps`,
                frameCount: this.performanceMetrics.frameCount
            });
        });
    }

    /**
     * Public API for enabling/disabling drag-and-drop
     */
    enableDragDrop(enabled = true) {
        this.dragDropOptions.enableDragDrop = enabled;

        if (enabled) {
            this.containerElement.classList.add('drag-drop-enabled');
        } else {
            this.containerElement.classList.remove('drag-drop-enabled');
        }
    }

    /**
     * Public API for accessing current state
     */
    getState() {
        return {
            isDragging: this.dragState.isDragging,
            dragDropEnabled: this.dragDropOptions.enableDragDrop,
            components: {
                palette: !!this.palette,
                canvas: !!this.canvas,
                touchHandler: !!this.touchHandler,
                accessibilityManager: !!this.accessibilityManager,
                undoRedoManager: !!this.undoRedoManager
            }
        };
    }
}
