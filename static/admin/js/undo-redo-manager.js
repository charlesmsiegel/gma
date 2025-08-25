/**
 * UndoRedoManager Component (Issue #191)
 *
 * Manages undo/redo operations for drag-and-drop prerequisite builder.
 * Tracks operation history and provides undo/redo functionality with
 * proper state management and user feedback.
 */

class UndoRedoManager {
    constructor(dragDropBuilder) {
        this.builder = dragDropBuilder;
        this.history = [];
        this.currentIndex = -1;
        this.maxHistorySize = 50;

        this.initialize();
    }

    /**
     * Initialize undo/redo system
     */
    initialize() {
        this.setupKeyboardShortcuts();
        this.createUndoRedoUI();
        this.setupEventListeners();
    }

    /**
     * Set up keyboard shortcuts for undo/redo
     */
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (event) => {
            // Ctrl+Z or Cmd+Z for undo
            if ((event.ctrlKey || event.metaKey) && event.key === 'z' && !event.shiftKey) {
                event.preventDefault();
                this.undo();
            }

            // Ctrl+Y or Cmd+Shift+Z for redo
            if (((event.ctrlKey || event.metaKey) && event.key === 'y') ||
                ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key === 'Z')) {
                event.preventDefault();
                this.redo();
            }
        });
    }

    /**
     * Create undo/redo UI controls
     */
    createUndoRedoUI() {
        // Find or create toolbar container
        let toolbar = this.builder.containerElement.querySelector('.drag-drop-toolbar');

        if (!toolbar) {
            toolbar = document.createElement('div');
            toolbar.className = 'drag-drop-toolbar';
            this.builder.containerElement.insertBefore(toolbar, this.builder.containerElement.firstChild);
        }

        // Create undo/redo buttons
        const undoRedoContainer = document.createElement('div');
        undoRedoContainer.className = 'undo-redo-controls';
        undoRedoContainer.innerHTML = `
            <button type="button"
                    class="undo-btn"
                    disabled
                    aria-label="Undo last action"
                    title="Undo (Ctrl+Z)">
                <span class="icon" aria-hidden="true">↶</span>
                <span class="text">Undo</span>
            </button>
            <button type="button"
                    class="redo-btn"
                    disabled
                    aria-label="Redo last undone action"
                    title="Redo (Ctrl+Y)">
                <span class="icon" aria-hidden="true">↷</span>
                <span class="text">Redo</span>
            </button>
            <div class="history-indicator">
                <span class="history-count">0</span> operations
            </div>
        `;

        toolbar.appendChild(undoRedoContainer);

        // Store references
        this.undoButton = undoRedoContainer.querySelector('.undo-btn');
        this.redoButton = undoRedoContainer.querySelector('.redo-btn');
        this.historyIndicator = undoRedoContainer.querySelector('.history-count');
    }

    /**
     * Set up event listeners for UI controls
     */
    setupEventListeners() {
        this.undoButton.addEventListener('click', () => this.undo());
        this.redoButton.addEventListener('click', () => this.redo());
    }

    /**
     * Record a new operation in history
     */
    recordOperation(operation) {
        // Validate operation
        if (!this.isValidOperation(operation)) {
            console.warn('Invalid operation:', operation);
            return false;
        }

        // Add timestamp and ID
        const recordedOperation = {
            ...operation,
            timestamp: Date.now(),
            id: this.generateOperationId()
        };

        // Remove any redo history after current index
        if (this.currentIndex < this.history.length - 1) {
            this.history = this.history.slice(0, this.currentIndex + 1);
        }

        // Add new operation
        this.history.push(recordedOperation);
        this.currentIndex = this.history.length - 1;

        // Limit history size
        if (this.history.length > this.maxHistorySize) {
            this.history.shift();
            this.currentIndex--;
        }

        // Update UI
        this.updateUI();

        // Announce to screen readers
        this.builder.announceToScreenReader(
            `Recorded ${operation.type} operation. ${this.getUndoableCount()} operations can be undone.`
        );

        return true;
    }

    /**
     * Undo the last operation
     */
    undo() {
        if (!this.canUndo()) {
            this.builder.announceToScreenReader('Nothing to undo.', 'assertive');
            return false;
        }

        const operation = this.history[this.currentIndex];
        const success = this.revertOperation(operation);

        if (success) {
            this.currentIndex--;
            this.updateUI();

            // Announce to screen readers
            this.builder.announceToScreenReader(
                `Undid ${operation.type} operation. ${this.getUndoableCount()} operations can be undone, ${this.getRedoableCount()} can be redone.`
            );

            return true;
        } else {
            this.builder.announceToScreenReader('Undo operation failed.', 'assertive');
            return false;
        }
    }

    /**
     * Redo the next operation
     */
    redo() {
        if (!this.canRedo()) {
            this.builder.announceToScreenReader('Nothing to redo.', 'assertive');
            return false;
        }

        const operation = this.history[this.currentIndex + 1];
        const success = this.replayOperation(operation);

        if (success) {
            this.currentIndex++;
            this.updateUI();

            // Announce to screen readers
            this.builder.announceToScreenReader(
                `Redid ${operation.type} operation. ${this.getUndoableCount()} operations can be undone, ${this.getRedoableCount()} can be redone.`
            );

            return true;
        } else {
            this.builder.announceToScreenReader('Redo operation failed.', 'assertive');
            return false;
        }
    }

    /**
     * Check if undo is possible
     */
    canUndo() {
        return this.currentIndex >= 0;
    }

    /**
     * Check if redo is possible
     */
    canRedo() {
        return this.currentIndex < this.history.length - 1;
    }

    /**
     * Get number of operations that can be undone
     */
    getUndoableCount() {
        return this.currentIndex + 1;
    }

    /**
     * Get number of operations that can be redone
     */
    getRedoableCount() {
        return this.history.length - this.currentIndex - 1;
    }

    /**
     * Validate operation structure
     */
    isValidOperation(operation) {
        if (!operation || typeof operation !== 'object') {
            return false;
        }

        // Required fields
        if (!operation.type) {
            return false;
        }

        // Validate based on operation type
        switch (operation.type) {
            case 'move':
                return operation.element && operation.from && operation.to;

            case 'create':
                return operation.element && operation.parent;

            case 'delete':
                return operation.element && operation.parent;

            case 'edit':
                return operation.element && operation.oldData && operation.newData;

            default:
                return false;
        }
    }

    /**
     * Revert an operation (undo)
     */
    revertOperation(operation) {
        try {
            switch (operation.type) {
                case 'move':
                    return this.revertMove(operation);

                case 'create':
                    return this.revertCreate(operation);

                case 'delete':
                    return this.revertDelete(operation);

                case 'edit':
                    return this.revertEdit(operation);

                default:
                    console.warn('Unknown operation type:', operation.type);
                    return false;
            }
        } catch (error) {
            console.error('Failed to revert operation:', error);
            return false;
        }
    }

    /**
     * Replay an operation (redo)
     */
    replayOperation(operation) {
        try {
            switch (operation.type) {
                case 'move':
                    return this.replayMove(operation);

                case 'create':
                    return this.replayCreate(operation);

                case 'delete':
                    return this.replayDelete(operation);

                case 'edit':
                    return this.replayEdit(operation);

                default:
                    console.warn('Unknown operation type:', operation.type);
                    return false;
            }
        } catch (error) {
            console.error('Failed to replay operation:', error);
            return false;
        }
    }

    /**
     * Revert a move operation
     */
    revertMove(operation) {
        const element = operation.element;
        const fromContainer = operation.from;

        if (!element || !fromContainer) {
            return false;
        }

        // Move element back to original position
        if (element.parentNode) {
            element.parentNode.removeChild(element);
        }

        fromContainer.appendChild(element);

        // Update builder state
        this.builder.updateJSONOutput();

        return true;
    }

    /**
     * Replay a move operation
     */
    replayMove(operation) {
        const element = operation.element;
        const toContainer = operation.to;

        if (!element || !toContainer) {
            return false;
        }

        // Move element to target position
        if (element.parentNode) {
            element.parentNode.removeChild(element);
        }

        toContainer.appendChild(element);

        // Update builder state
        this.builder.updateJSONOutput();

        return true;
    }

    /**
     * Revert a create operation
     */
    revertCreate(operation) {
        const element = operation.element;

        if (!element || !element.parentNode) {
            return false;
        }

        // Remove created element
        element.parentNode.removeChild(element);

        // Update builder state
        this.builder.updateJSONOutput();

        return true;
    }

    /**
     * Replay a create operation
     */
    replayCreate(operation) {
        const parent = operation.parent;
        const elementData = operation.data;

        if (!parent || !elementData) {
            return false;
        }

        // Recreate element
        const element = this.builder.createElement(elementData);
        parent.appendChild(element);

        // Store reference for future operations
        operation.element = element;

        // Update builder state
        this.builder.updateJSONOutput();

        return true;
    }

    /**
     * Revert a delete operation
     */
    revertDelete(operation) {
        const parent = operation.parent;
        const elementData = operation.data;

        if (!parent || !elementData) {
            return false;
        }

        // Recreate deleted element
        const element = this.builder.createElement(elementData);
        parent.appendChild(element);

        // Store reference for future operations
        operation.element = element;

        // Update builder state
        this.builder.updateJSONOutput();

        return true;
    }

    /**
     * Replay a delete operation
     */
    replayDelete(operation) {
        const element = operation.element;

        if (!element || !element.parentNode) {
            return false;
        }

        // Store element data before deletion
        operation.data = this.builder.extractDragData(element);
        operation.parent = element.parentNode;

        // Remove element
        element.parentNode.removeChild(element);

        // Update builder state
        this.builder.updateJSONOutput();

        return true;
    }

    /**
     * Revert an edit operation
     */
    revertEdit(operation) {
        const element = operation.element;
        const oldData = operation.oldData;

        if (!element || !oldData) {
            return false;
        }

        // Restore old data
        this.applyDataToElement(element, oldData);

        // Update builder state
        this.builder.updateJSONOutput();

        return true;
    }

    /**
     * Replay an edit operation
     */
    replayEdit(operation) {
        const element = operation.element;
        const newData = operation.newData;

        if (!element || !newData) {
            return false;
        }

        // Apply new data
        this.applyDataToElement(element, newData);

        // Update builder state
        this.builder.updateJSONOutput();

        return true;
    }

    /**
     * Apply data to element (for edit operations)
     */
    applyDataToElement(element, data) {
        // Update element content based on data
        // This would depend on the specific requirement type
        const content = this.builder.canvas.generateRequirementContent(data);
        element.innerHTML = content;

        // Update data attributes
        if (data.type) {
            element.dataset.requirementType = data.type;
        }
    }

    /**
     * Update UI state (button states, indicators)
     */
    updateUI() {
        // Update undo button
        this.undoButton.disabled = !this.canUndo();
        if (this.canUndo()) {
            const operation = this.history[this.currentIndex];
            this.undoButton.setAttribute('aria-label', `Undo ${operation.type} operation`);
        } else {
            this.undoButton.setAttribute('aria-label', 'Undo last action');
        }

        // Update redo button
        this.redoButton.disabled = !this.canRedo();
        if (this.canRedo()) {
            const operation = this.history[this.currentIndex + 1];
            this.redoButton.setAttribute('aria-label', `Redo ${operation.type} operation`);
        } else {
            this.redoButton.setAttribute('aria-label', 'Redo last undone action');
        }

        // Update history indicator
        this.historyIndicator.textContent = this.history.length;
    }

    /**
     * Clear all history
     */
    clearHistory() {
        this.history = [];
        this.currentIndex = -1;
        this.updateUI();

        this.builder.announceToScreenReader('Undo/redo history cleared.');
    }

    /**
     * Get history summary for debugging/status
     */
    getHistorySummary() {
        return {
            totalOperations: this.history.length,
            currentIndex: this.currentIndex,
            canUndo: this.canUndo(),
            canRedo: this.canRedo(),
            undoableCount: this.getUndoableCount(),
            redoableCount: this.getRedoableCount()
        };
    }

    /**
     * Generate unique operation ID
     */
    generateOperationId() {
        return `op_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    /**
     * Export history for persistence (optional)
     */
    exportHistory() {
        return {
            history: this.history,
            currentIndex: this.currentIndex,
            timestamp: Date.now()
        };
    }

    /**
     * Import history from persistence (optional)
     */
    importHistory(data) {
        if (data && Array.isArray(data.history)) {
            this.history = data.history;
            this.currentIndex = data.currentIndex || -1;
            this.updateUI();
            return true;
        }
        return false;
    }
}
