/**
 * AccessibilityManager Component (Issue #191)
 *
 * Manages accessibility features for the drag-and-drop prerequisite builder,
 * including keyboard navigation, screen reader support, and ARIA attributes.
 * Ensures WCAG 2.1 AA compliance throughout the interface.
 */

class AccessibilityManager {
    constructor(dragDropBuilder) {
        this.builder = dragDropBuilder;
        this.keyboardDragMode = false;
        this.currentFocus = null;
        this.dragModeElement = null;
        this.focusHistory = [];

        this.initialize();
    }

    /**
     * Initialize accessibility features
     */
    initialize() {
        this.setupKeyboardNavigation();
        this.setupScreenReaderSupport();
        this.setupFocusManagement();
        this.setupHighContrastSupport();
        this.setupReducedMotionSupport();
    }

    /**
     * Set up keyboard navigation for drag-and-drop
     */
    setupKeyboardNavigation() {
        // Add keyboard event listener to main container
        this.builder.containerElement.addEventListener('keydown', this.handleGlobalKeydown.bind(this));

        // Add focus event listeners
        this.builder.containerElement.addEventListener('focusin', this.handleFocusIn.bind(this));
        this.builder.containerElement.addEventListener('focusout', this.handleFocusOut.bind(this));
    }

    /**
     * Set up screen reader support with ARIA attributes
     */
    setupScreenReaderSupport() {
        // Add main ARIA structure
        this.builder.containerElement.setAttribute('role', 'application');
        this.builder.containerElement.setAttribute('aria-label', 'Prerequisite builder with drag-and-drop support');

        // Create and setup live regions for announcements
        this.setupLiveRegions();

        // Add keyboard shortcut announcements
        this.announceKeyboardShortcuts();
    }

    /**
     * Set up live regions for screen reader announcements
     */
    setupLiveRegions() {
        // Polite live region for general announcements
        this.politeRegion = document.createElement('div');
        this.politeRegion.setAttribute('aria-live', 'polite');
        this.politeRegion.setAttribute('aria-atomic', 'false');
        this.politeRegion.className = 'sr-only live-region-polite';
        this.builder.containerElement.appendChild(this.politeRegion);

        // Assertive live region for urgent announcements
        this.assertiveRegion = document.createElement('div');
        this.assertiveRegion.setAttribute('aria-live', 'assertive');
        this.assertiveRegion.setAttribute('aria-atomic', 'true');
        this.assertiveRegion.className = 'sr-only live-region-assertive';
        this.builder.containerElement.appendChild(this.assertiveRegion);

        // Status region for drag-and-drop state
        this.statusRegion = document.createElement('div');
        this.statusRegion.setAttribute('role', 'status');
        this.statusRegion.setAttribute('aria-live', 'polite');
        this.statusRegion.className = 'sr-only live-region-status';
        this.builder.containerElement.appendChild(this.statusRegion);
    }

    /**
     * Set up focus management for complex interactions
     */
    setupFocusManagement() {
        // Track focus changes
        this.focusHistory = [];
        this.maxFocusHistory = 10;

        // Set up focus traps for modal dialogs (if any)
        this.focusTrap = null;
    }

    /**
     * Set up high contrast mode support
     */
    setupHighContrastSupport() {
        // Detect high contrast mode
        if (window.matchMedia) {
            const highContrastQuery = window.matchMedia('(prefers-contrast: high)');
            this.updateHighContrastMode(highContrastQuery.matches);

            highContrastQuery.addListener((query) => {
                this.updateHighContrastMode(query.matches);
            });
        }
    }

    /**
     * Set up reduced motion support
     */
    setupReducedMotionSupport() {
        // Detect reduced motion preference
        if (window.matchMedia) {
            const reducedMotionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
            this.updateReducedMotionMode(reducedMotionQuery.matches);

            reducedMotionQuery.addListener((query) => {
                this.updateReducedMotionMode(query.matches);
            });
        }
    }

    /**
     * Handle global keyboard events
     */
    handleGlobalKeydown(event) {
        // Handle keyboard drag activation
        if (event.key === 'd' || event.key === 'D') {
            if (!this.keyboardDragMode) {
                const focusedElement = document.activeElement;
                const draggableElement = focusedElement.closest('.draggable');

                if (draggableElement) {
                    event.preventDefault();
                    this.activateKeyboardDrag(draggableElement);
                    return;
                }
            }
        }

        // Handle keyboard drag navigation
        if (this.keyboardDragMode) {
            this.handleKeyboardDragNavigation(event);
            return;
        }

        // Handle general navigation
        this.handleGeneralNavigation(event);
    }

    /**
     * Handle keyboard drag navigation when in drag mode
     */
    handleKeyboardDragNavigation(event) {
        switch (event.key) {
            case 'Escape':
                event.preventDefault();
                this.cancelKeyboardDrag();
                break;

            case 'Enter':
            case ' ':
                event.preventDefault();
                this.completeKeyboardDrag();
                break;

            case 'ArrowUp':
                event.preventDefault();
                this.navigateDropZones('up');
                break;

            case 'ArrowDown':
                event.preventDefault();
                this.navigateDropZones('down');
                break;

            case 'ArrowLeft':
                event.preventDefault();
                this.navigateDropZones('left');
                break;

            case 'ArrowRight':
                event.preventDefault();
                this.navigateDropZones('right');
                break;

            case 'Home':
                event.preventDefault();
                this.navigateDropZones('first');
                break;

            case 'End':
                event.preventDefault();
                this.navigateDropZones('last');
                break;
        }
    }

    /**
     * Handle general keyboard navigation
     */
    handleGeneralNavigation(event) {
        const focusedElement = document.activeElement;

        switch (event.key) {
            case 'F1':
                event.preventDefault();
                this.showKeyboardHelp();
                break;

            case 'Tab':
                // Let default tab behavior work, but track focus
                this.trackFocus(focusedElement);
                break;

            case 'ArrowUp':
            case 'ArrowDown':
                // Navigate within lists and trees
                if (focusedElement.closest('.palette-category') || focusedElement.closest('.structure-tree')) {
                    event.preventDefault();
                    this.navigateList(event.key === 'ArrowUp' ? 'up' : 'down');
                }
                break;
        }
    }

    /**
     * Activate keyboard drag mode for an element
     */
    activateKeyboardDrag(element) {
        this.keyboardDragMode = true;
        this.dragModeElement = element;

        // Visual feedback
        element.classList.add('keyboard-dragging');
        this.builder.containerElement.classList.add('keyboard-drag-active');

        // Highlight available drop zones
        this.highlightDropZones();

        // Focus first available drop zone
        const firstDropZone = this.getAvailableDropZones()[0];
        if (firstDropZone) {
            firstDropZone.focus();
            firstDropZone.classList.add('drop-zone-focused');
        }

        // Announce drag mode activation
        this.announceToScreenReader(
            `Keyboard drag mode activated for ${this.getElementDescription(element)}. ` +
            `Use arrow keys to navigate drop zones, Enter to drop, or Escape to cancel.`,
            'assertive'
        );

        // Update status
        this.updateDragStatus(`Dragging: ${this.getElementDescription(element)}`);
    }

    /**
     * Navigate between drop zones during keyboard drag
     */
    navigateDropZones(direction) {
        const dropZones = this.getAvailableDropZones();
        const currentFocused = document.activeElement;
        const currentIndex = dropZones.indexOf(currentFocused);

        let nextIndex;

        switch (direction) {
            case 'up':
                nextIndex = Math.max(0, currentIndex - 1);
                break;
            case 'down':
                nextIndex = Math.min(dropZones.length - 1, currentIndex + 1);
                break;
            case 'left':
                nextIndex = Math.max(0, currentIndex - 1);
                break;
            case 'right':
                nextIndex = Math.min(dropZones.length - 1, currentIndex + 1);
                break;
            case 'first':
                nextIndex = 0;
                break;
            case 'last':
                nextIndex = dropZones.length - 1;
                break;
            default:
                return;
        }

        // Clear current focus styling
        dropZones.forEach(zone => zone.classList.remove('drop-zone-focused'));

        // Focus new drop zone
        if (dropZones[nextIndex]) {
            dropZones[nextIndex].focus();
            dropZones[nextIndex].classList.add('drop-zone-focused');

            // Announce new position
            this.announceToScreenReader(
                `Drop zone ${nextIndex + 1} of ${dropZones.length}: ${this.getDropZoneDescription(dropZones[nextIndex])}`
            );
        }
    }

    /**
     * Complete keyboard drag operation
     */
    completeKeyboardDrag() {
        if (!this.keyboardDragMode || !this.dragModeElement) return;

        const focusedDropZone = document.activeElement;
        if (!focusedDropZone.classList.contains('drop-zone')) return;

        // Extract drag data from element
        const dragData = this.builder.extractDragData(this.dragModeElement);

        // Validate drop
        if (!this.builder.isValidDrop(dragData, focusedDropZone)) {
            this.announceToScreenReader('Invalid drop location. Please choose a different drop zone.', 'assertive');
            return;
        }

        // Perform drop
        const success = this.builder.performDrop(dragData, focusedDropZone);

        if (success) {
            this.announceToScreenReader(
                `Successfully dropped ${this.getElementDescription(this.dragModeElement)} into ${this.getDropZoneDescription(focusedDropZone)}.`
            );
        } else {
            this.announceToScreenReader('Drop operation failed. Please try again.', 'assertive');
        }

        this.cancelKeyboardDrag();
    }

    /**
     * Cancel keyboard drag operation
     */
    cancelKeyboardDrag() {
        if (!this.keyboardDragMode) return;

        // Clear drag mode
        this.keyboardDragMode = false;

        // Clear visual feedback
        if (this.dragModeElement) {
            this.dragModeElement.classList.remove('keyboard-dragging');
            this.dragModeElement.focus(); // Return focus to original element
        }

        this.builder.containerElement.classList.remove('keyboard-drag-active');

        // Clear drop zone highlighting
        this.clearDropZoneHighlights();

        // Clear status
        this.updateDragStatus('');

        // Announce cancellation
        this.announceToScreenReader('Keyboard drag mode cancelled.');

        // Reset state
        this.dragModeElement = null;
    }

    /**
     * Get available drop zones for current drag operation
     */
    getAvailableDropZones() {
        const allDropZones = Array.from(this.builder.containerElement.querySelectorAll('.drop-zone'));

        // Filter based on drag data if available
        if (this.dragModeElement) {
            const dragData = this.builder.extractDragData(this.dragModeElement);
            return allDropZones.filter(zone => this.builder.isValidDrop(dragData, zone));
        }

        return allDropZones;
    }

    /**
     * Highlight available drop zones
     */
    highlightDropZones() {
        const dropZones = this.getAvailableDropZones();
        dropZones.forEach(zone => {
            zone.classList.add('drop-zone-keyboard-available');
            zone.setAttribute('tabindex', '0');
        });
    }

    /**
     * Clear drop zone highlights
     */
    clearDropZoneHighlights() {
        const dropZones = this.builder.containerElement.querySelectorAll('.drop-zone');
        dropZones.forEach(zone => {
            zone.classList.remove('drop-zone-keyboard-available', 'drop-zone-focused');
            zone.removeAttribute('tabindex');
        });
    }

    /**
     * Navigate within lists (palette items, tree nodes, etc.)
     */
    navigateList(direction) {
        const focusedElement = document.activeElement;
        const list = focusedElement.closest('.palette-category, .structure-tree, .requirements-list');

        if (!list) return;

        const items = Array.from(list.querySelectorAll('[tabindex="0"], button, input, .palette-item, .tree-node, .requirement-block'));
        const currentIndex = items.indexOf(focusedElement);

        if (currentIndex === -1) return;

        let nextIndex;
        if (direction === 'up') {
            nextIndex = (currentIndex - 1 + items.length) % items.length;
        } else {
            nextIndex = (currentIndex + 1) % items.length;
        }

        items[nextIndex].focus();
    }

    /**
     * Handle focus in events
     */
    handleFocusIn(event) {
        this.currentFocus = event.target;
        this.trackFocus(event.target);

        // Add focus styling for custom elements
        if (event.target.closest('.requirement-block, .palette-item')) {
            event.target.closest('.requirement-block, .palette-item').classList.add('focused');
        }
    }

    /**
     * Handle focus out events
     */
    handleFocusOut(event) {
        // Remove focus styling
        if (event.target.closest('.requirement-block, .palette-item')) {
            event.target.closest('.requirement-block, .palette-item').classList.remove('focused');
        }
    }

    /**
     * Track focus history for navigation
     */
    trackFocus(element) {
        if (element && element !== document.body) {
            this.focusHistory.push(element);

            // Limit history size
            if (this.focusHistory.length > this.maxFocusHistory) {
                this.focusHistory.shift();
            }
        }
    }

    /**
     * Show keyboard help dialog
     */
    showKeyboardHelp() {
        // Create modal dialog with keyboard shortcuts
        const modal = document.createElement('div');
        modal.className = 'keyboard-help-modal';
        modal.setAttribute('role', 'dialog');
        modal.setAttribute('aria-labelledby', 'keyboard-help-title');
        modal.setAttribute('aria-modal', 'true');

        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h2 id="keyboard-help-title">Keyboard Shortcuts</h2>
                    <button type="button" class="modal-close" aria-label="Close help dialog">×</button>
                </div>
                <div class="modal-body">
                    <div class="shortcut-section">
                        <h3>Navigation</h3>
                        <dl>
                            <dt>Tab / Shift+Tab</dt>
                            <dd>Navigate between interactive elements</dd>
                            <dt>Arrow Keys</dt>
                            <dd>Navigate within lists and categories</dd>
                            <dt>Home / End</dt>
                            <dd>Move to first / last item in list</dd>
                        </dl>
                    </div>
                    <div class="shortcut-section">
                        <h3>Drag and Drop</h3>
                        <dl>
                            <dt>D</dt>
                            <dd>Activate keyboard drag mode for focused element</dd>
                            <dt>Arrow Keys (in drag mode)</dt>
                            <dd>Navigate between drop zones</dd>
                            <dt>Enter / Space (in drag mode)</dt>
                            <dd>Complete drop operation</dd>
                            <dt>Escape (in drag mode)</dt>
                            <dd>Cancel drag operation</dd>
                        </dl>
                    </div>
                    <div class="shortcut-section">
                        <h3>Actions</h3>
                        <dl>
                            <dt>Enter</dt>
                            <dd>Edit focused requirement</dd>
                            <dt>Delete / Backspace</dt>
                            <dd>Delete focused requirement</dd>
                            <dt>F1</dt>
                            <dd>Show this help dialog</dd>
                        </dl>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn-close">Close</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Set up focus trap
        this.setupFocusTrap(modal);

        // Focus first element
        const firstButton = modal.querySelector('button');
        if (firstButton) firstButton.focus();

        // Event listeners
        modal.addEventListener('click', (event) => {
            if (event.target.classList.contains('modal-close') ||
                event.target.classList.contains('btn-close') ||
                event.target === modal) {
                this.closeKeyboardHelp(modal);
            }
        });

        modal.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') {
                this.closeKeyboardHelp(modal);
            }
        });
    }

    /**
     * Close keyboard help dialog
     */
    closeKeyboardHelp(modal) {
        // Remove focus trap
        this.removeFocusTrap();

        // Remove modal
        document.body.removeChild(modal);

        // Restore focus
        if (this.currentFocus) {
            this.currentFocus.focus();
        }
    }

    /**
     * Set up focus trap for modal dialogs
     */
    setupFocusTrap(modal) {
        const focusableElements = modal.querySelectorAll(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );

        if (focusableElements.length === 0) return;

        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];

        this.focusTrap = (event) => {
            if (event.key === 'Tab') {
                if (event.shiftKey) {
                    if (document.activeElement === firstElement) {
                        event.preventDefault();
                        lastElement.focus();
                    }
                } else {
                    if (document.activeElement === lastElement) {
                        event.preventDefault();
                        firstElement.focus();
                    }
                }
            }
        };

        modal.addEventListener('keydown', this.focusTrap);
    }

    /**
     * Remove focus trap
     */
    removeFocusTrap() {
        if (this.focusTrap) {
            // Remove from all modals (if any)
            const modals = document.querySelectorAll('.keyboard-help-modal');
            modals.forEach(modal => {
                modal.removeEventListener('keydown', this.focusTrap);
            });
            this.focusTrap = null;
        }
    }

    /**
     * Update high contrast mode
     */
    updateHighContrastMode(enabled) {
        if (enabled) {
            this.builder.containerElement.classList.add('high-contrast');
        } else {
            this.builder.containerElement.classList.remove('high-contrast');
        }
    }

    /**
     * Update reduced motion mode
     */
    updateReducedMotionMode(enabled) {
        if (enabled) {
            this.builder.containerElement.classList.add('reduced-motion');
        } else {
            this.builder.containerElement.classList.remove('reduced-motion');
        }
    }

    /**
     * Announce keyboard shortcuts on initialization
     */
    announceKeyboardShortcuts() {
        setTimeout(() => {
            this.announceToScreenReader(
                'Drag-and-drop prerequisite builder loaded. Press F1 for keyboard shortcuts or D to activate drag mode on focused elements.'
            );
        }, 1000);
    }

    /**
     * Announce message to appropriate live region
     */
    announceToScreenReader(message, priority = 'polite') {
        let liveRegion;

        switch (priority) {
            case 'assertive':
                liveRegion = this.assertiveRegion;
                break;
            case 'status':
                liveRegion = this.statusRegion;
                break;
            default:
                liveRegion = this.politeRegion;
                break;
        }

        if (liveRegion) {
            liveRegion.textContent = message;

            // Clear after announcement
            setTimeout(() => {
                liveRegion.textContent = '';
            }, priority === 'assertive' ? 2000 : 1000);
        }
    }

    /**
     * Update drag status in status region
     */
    updateDragStatus(status) {
        if (this.statusRegion) {
            this.statusRegion.textContent = status;
        }
    }

    /**
     * Get human-readable description of element
     */
    getElementDescription(element) {
        const type = element.dataset.requirementType;
        const title = element.querySelector('.requirement-title, .item-name');

        if (title) {
            return `${type}: ${title.textContent}`;
        }

        return type || 'Unknown requirement';
    }

    /**
     * Get human-readable description of drop zone
     */
    getDropZoneDescription(dropZone) {
        const type = dropZone.dataset.dropZoneType;

        switch (type) {
            case 'root':
                return 'Root level';
            case 'any_container':
                return 'Any of (OR) container';
            case 'all_container':
                return 'All of (AND) container';
            case 'insertion':
                const index = dropZone.dataset.insertionIndex;
                return `Insert at position ${parseInt(index) + 1}`;
            default:
                return type || 'Unknown drop zone';
        }
    }

    /**
     * Public API for accessibility status
     */
    getAccessibilityStatus() {
        return {
            keyboardDragMode: this.keyboardDragMode,
            currentFocus: this.currentFocus ? this.currentFocus.tagName : null,
            focusHistoryLength: this.focusHistory.length,
            liveRegionsPresent: !!(this.politeRegion && this.assertiveRegion && this.statusRegion),
            highContrastMode: this.builder.containerElement.classList.contains('high-contrast'),
            reducedMotionMode: this.builder.containerElement.classList.contains('reduced-motion')
        };
    }
}
