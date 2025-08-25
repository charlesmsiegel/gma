/**
 * TouchHandler Component (Issue #191)
 *
 * Handles touch interactions for drag-and-drop prerequisite builder on
 * mobile and tablet devices. Provides gesture recognition, touch feedback,
 * and adaptive UI for touch interfaces.
 */

class TouchHandler {
    constructor(dragDropBuilder) {
        this.builder = dragDropBuilder;
        this.touchState = {
            startX: 0,
            startY: 0,
            currentX: 0,
            currentY: 0,
            startTime: 0,
            isDragging: false,
            touchId: null,
            element: null,
            initialScrollTop: 0,
            initialScrollLeft: 0
        };

        this.config = {
            tapTimeout: 300,        // Max time for tap
            longPressTimeout: 500,  // Time for long press
            dragThreshold: 10,      // Pixels to start drag
            scrollThreshold: 5,     // Pixels to detect scroll intent
            velocityThreshold: 0.5, // Minimum velocity for momentum
            dampingFactor: 0.9      // Momentum damping
        };

        this.supportedGestures = [];
        this.gestureRecognizers = {};

        this.initialize();
    }

    /**
     * Initialize touch handling system
     */
    initialize() {
        this.detectTouchCapabilities();
        this.setupTouchListeners();
        this.setupGestureRecognizers();
        this.adaptUIForTouch();
    }

    /**
     * Detect device touch capabilities
     */
    detectTouchCapabilities() {
        this.capabilities = {
            hasTouch: 'ontouchstart' in window || navigator.maxTouchPoints > 0,
            maxTouchPoints: navigator.maxTouchPoints || 1,
            isIOS: /iPad|iPhone|iPod/.test(navigator.userAgent),
            isAndroid: /Android/.test(navigator.userAgent),
            supportsPointerEvents: window.PointerEvent !== undefined,
            supportsPassiveEvents: this.detectPassiveEventSupport()
        };

        // Set supported gestures based on capabilities
        this.supportedGestures = ['tap', 'longpress', 'drag'];

        if (this.capabilities.maxTouchPoints > 1) {
            this.supportedGestures.push('pinch', 'rotate');
        }
    }

    /**
     * Detect passive event listener support
     */
    detectPassiveEventSupport() {
        let passiveSupported = false;
        try {
            const options = Object.defineProperty({}, 'passive', {
                get() {
                    passiveSupported = true;
                    return false;
                }
            });
            window.addEventListener('test', null, options);
            window.removeEventListener('test', null, options);
        } catch (err) {
            passiveSupported = false;
        }
        return passiveSupported;
    }

    /**
     * Set up touch event listeners
     */
    setupTouchListeners() {
        const container = this.builder.containerElement;
        const eventOptions = this.capabilities.supportsPassiveEvents ? { passive: false } : false;

        // Primary touch events
        container.addEventListener('touchstart', this.handleTouchStart.bind(this), eventOptions);
        container.addEventListener('touchmove', this.handleTouchMove.bind(this), eventOptions);
        container.addEventListener('touchend', this.handleTouchEnd.bind(this), eventOptions);
        container.addEventListener('touchcancel', this.handleTouchCancel.bind(this), eventOptions);

        // Pointer events (if supported)
        if (this.capabilities.supportsPointerEvents) {
            container.addEventListener('pointerdown', this.handlePointerDown.bind(this));
            container.addEventListener('pointermove', this.handlePointerMove.bind(this));
            container.addEventListener('pointerup', this.handlePointerUp.bind(this));
            container.addEventListener('pointercancel', this.handlePointerCancel.bind(this));
        }

        // Prevent default context menu on long press
        container.addEventListener('contextmenu', (event) => {
            if (this.touchState.isDragging) {
                event.preventDefault();
            }
        });
    }

    /**
     * Set up gesture recognizers
     */
    setupGestureRecognizers() {
        // Tap recognizer
        this.gestureRecognizers.tap = {
            recognize: (touches, event) => {
                const touch = touches[0];
                const duration = Date.now() - this.touchState.startTime;
                const distance = this.calculateDistance(
                    this.touchState.startX, this.touchState.startY,
                    touch.clientX, touch.clientY
                );

                return duration < this.config.tapTimeout && distance < this.config.dragThreshold;
            },
            handle: (element, event) => {
                this.handleTap(element, event);
            }
        };

        // Long press recognizer
        this.gestureRecognizers.longpress = {
            timeout: null,
            recognize: (touches, event) => {
                // Set up timeout for long press
                if (this.gestureRecognizers.longpress.timeout) {
                    clearTimeout(this.gestureRecognizers.longpress.timeout);
                }

                this.gestureRecognizers.longpress.timeout = setTimeout(() => {
                    if (!this.touchState.isDragging) {
                        this.handleLongPress(this.touchState.element, event);
                    }
                }, this.config.longPressTimeout);
            },
            cancel: () => {
                if (this.gestureRecognizers.longpress.timeout) {
                    clearTimeout(this.gestureRecognizers.longpress.timeout);
                    this.gestureRecognizers.longpress.timeout = null;
                }
            }
        };

        // Drag recognizer
        this.gestureRecognizers.drag = {
            recognize: (touches, event) => {
                const touch = touches[0];
                const distance = this.calculateDistance(
                    this.touchState.startX, this.touchState.startY,
                    touch.clientX, touch.clientY
                );

                return distance > this.config.dragThreshold;
            },
            handle: (element, event) => {
                this.handleDragStart(element, event);
            }
        };
    }

    /**
     * Adapt UI for touch interactions
     */
    adaptUIForTouch() {
        if (this.capabilities.hasTouch) {
            this.builder.containerElement.classList.add('touch-enabled');

            // Increase touch target sizes
            const style = document.createElement('style');
            style.textContent = `
                .touch-enabled .palette-item,
                .touch-enabled .requirement-block,
                .touch-enabled .drop-zone {
                    min-height: 44px;
                    min-width: 44px;
                    padding: 8px;
                }

                .touch-enabled .requirement-actions button {
                    min-height: 44px;
                    min-width: 44px;
                    padding: 12px;
                }

                .touch-enabled .drop-zone-indicator {
                    font-size: 1.2em;
                    padding: 16px;
                }

                .touch-enabled .draggable {
                    cursor: grab;
                }

                .touch-enabled .draggable.touch-dragging {
                    cursor: grabbing;
                    opacity: 0.7;
                    transform: scale(1.05);
                    transition: transform 0.2s ease;
                    z-index: 1000;
                }
            `;
            document.head.appendChild(style);
        }
    }

    /**
     * Handle touch start events
     */
    handleTouchStart(event) {
        // Only handle single touch for now
        if (event.touches.length !== 1) {
            return;
        }

        const touch = event.touches[0];
        const element = touch.target.closest('.draggable');

        if (!element) return;

        // Initialize touch state
        this.touchState = {
            startX: touch.clientX,
            startY: touch.clientY,
            currentX: touch.clientX,
            currentY: touch.clientY,
            startTime: Date.now(),
            isDragging: false,
            touchId: touch.identifier,
            element: element,
            initialScrollTop: this.builder.containerElement.scrollTop,
            initialScrollLeft: this.builder.containerElement.scrollLeft
        };

        // Add touch feedback
        element.classList.add('touch-active');

        // Start gesture recognition
        this.gestureRecognizers.longpress.recognize([touch], event);

        // Prevent default to avoid scrolling during potential drag
        // but allow if this looks like a scroll gesture
        const scrollIntent = this.detectScrollIntent(touch);
        if (!scrollIntent) {
            event.preventDefault();
        }
    }

    /**
     * Handle touch move events
     */
    handleTouchMove(event) {
        if (event.touches.length !== 1) return;

        const touch = event.touches[0];

        // Only handle if this is our tracked touch
        if (touch.identifier !== this.touchState.touchId) return;

        // Update current position
        this.touchState.currentX = touch.clientX;
        this.touchState.currentY = touch.clientY;

        const distance = this.calculateDistance(
            this.touchState.startX, this.touchState.startY,
            this.touchState.currentX, this.touchState.currentY
        );

        // Check if drag should start
        if (!this.touchState.isDragging && distance > this.config.dragThreshold) {
            // Cancel other gestures
            this.gestureRecognizers.longpress.cancel();

            // Start drag
            this.startTouchDrag(event);
        }

        // Continue drag if active
        if (this.touchState.isDragging) {
            this.updateTouchDrag(event);
            event.preventDefault();
        }
    }

    /**
     * Handle touch end events
     */
    handleTouchEnd(event) {
        const touch = Array.from(event.changedTouches).find(t => t.identifier === this.touchState.touchId);
        if (!touch) return;

        // Remove touch feedback
        if (this.touchState.element) {
            this.touchState.element.classList.remove('touch-active');
        }

        if (this.touchState.isDragging) {
            this.endTouchDrag(event);
        } else {
            // Check for tap gesture
            if (this.gestureRecognizers.tap.recognize([touch], event)) {
                this.gestureRecognizers.tap.handle(this.touchState.element, event);
            }
        }

        // Cancel any remaining gesture timeouts
        this.gestureRecognizers.longpress.cancel();

        // Reset touch state
        this.resetTouchState();
    }

    /**
     * Handle touch cancel events
     */
    handleTouchCancel(event) {
        if (this.touchState.isDragging) {
            this.cancelTouchDrag();
        }

        // Cancel all gestures
        this.gestureRecognizers.longpress.cancel();

        // Remove touch feedback
        if (this.touchState.element) {
            this.touchState.element.classList.remove('touch-active', 'touch-dragging');
        }

        this.resetTouchState();
    }

    /**
     * Handle pointer events (unified touch/mouse/pen)
     */
    handlePointerDown(event) {
        // For now, delegate to touch handlers for pointer events that are touch-based
        if (event.pointerType === 'touch') {
            // Convert pointer event to touch event format
            const touchEvent = {
                touches: [{
                    identifier: event.pointerId,
                    clientX: event.clientX,
                    clientY: event.clientY,
                    target: event.target
                }],
                preventDefault: () => event.preventDefault()
            };
            this.handleTouchStart(touchEvent);
        }
    }

    handlePointerMove(event) {
        if (event.pointerType === 'touch' && this.touchState.touchId === event.pointerId) {
            const touchEvent = {
                touches: [{
                    identifier: event.pointerId,
                    clientX: event.clientX,
                    clientY: event.clientY
                }],
                preventDefault: () => event.preventDefault()
            };
            this.handleTouchMove(touchEvent);
        }
    }

    handlePointerUp(event) {
        if (event.pointerType === 'touch' && this.touchState.touchId === event.pointerId) {
            const touchEvent = {
                changedTouches: [{
                    identifier: event.pointerId,
                    clientX: event.clientX,
                    clientY: event.clientY
                }]
            };
            this.handleTouchEnd(touchEvent);
        }
    }

    handlePointerCancel(event) {
        if (event.pointerType === 'touch' && this.touchState.touchId === event.pointerId) {
            this.handleTouchCancel(event);
        }
    }

    /**
     * Start touch drag operation
     */
    startTouchDrag(event) {
        this.touchState.isDragging = true;

        const element = this.touchState.element;
        if (!element) return;

        // Add dragging visual feedback
        element.classList.add('touch-dragging');

        // Extract drag data
        const dragData = this.builder.extractDragData(element);

        // Highlight drop zones
        this.builder.highlightDropZones(dragData);

        // Create drag preview (optional)
        this.createTouchDragPreview(element);

        // Announce to screen readers
        this.builder.announceToScreenReader(
            `Started touch drag of ${dragData.type} requirement. Move to drop zone and lift finger to drop.`
        );

        // Haptic feedback (if supported)
        this.provideHapticFeedback('start');
    }

    /**
     * Update touch drag operation
     */
    updateTouchDrag(event) {
        // Update drag preview position if it exists
        if (this.dragPreview) {
            this.dragPreview.style.left = `${this.touchState.currentX - 50}px`;
            this.dragPreview.style.top = `${this.touchState.currentY - 25}px`;
        }

        // Check for drop zone under finger
        const dropZone = this.getDropZoneUnderTouch(this.touchState.currentX, this.touchState.currentY);

        if (dropZone !== this.currentDropZone) {
            // Remove highlight from previous drop zone
            if (this.currentDropZone) {
                this.currentDropZone.classList.remove('drop-zone-touch-hover');
            }

            // Add highlight to new drop zone
            if (dropZone) {
                dropZone.classList.add('drop-zone-touch-hover');
                this.provideHapticFeedback('over');
            }

            this.currentDropZone = dropZone;
        }
    }

    /**
     * End touch drag operation
     */
    endTouchDrag(event) {
        const element = this.touchState.element;
        if (!element) return;

        // Remove dragging visual feedback
        element.classList.remove('touch-dragging');

        // Find drop zone under final touch position
        const dropZone = this.getDropZoneUnderTouch(this.touchState.currentX, this.touchState.currentY);

        if (dropZone) {
            // Attempt drop
            const dragData = this.builder.extractDragData(element);

            if (this.builder.isValidDrop(dragData, dropZone)) {
                const success = this.builder.performDrop(dragData, dropZone);

                if (success) {
                    this.builder.announceToScreenReader(
                        `Successfully dropped ${dragData.type} requirement.`
                    );
                    this.provideHapticFeedback('success');
                } else {
                    this.provideHapticFeedback('error');
                }
            } else {
                this.builder.announceToScreenReader('Invalid drop location.');
                this.provideHapticFeedback('error');
            }
        } else {
            this.builder.announceToScreenReader('Drag cancelled - no drop zone found.');
        }

        this.cleanupTouchDrag();
    }

    /**
     * Cancel touch drag operation
     */
    cancelTouchDrag() {
        if (this.touchState.element) {
            this.touchState.element.classList.remove('touch-dragging');
        }

        this.builder.announceToScreenReader('Touch drag cancelled.');
        this.cleanupTouchDrag();
    }

    /**
     * Clean up after touch drag
     */
    cleanupTouchDrag() {
        // Remove drag preview
        if (this.dragPreview) {
            document.body.removeChild(this.dragPreview);
            this.dragPreview = null;
        }

        // Clear drop zone highlights
        const dropZones = this.builder.containerElement.querySelectorAll('.drop-zone');
        dropZones.forEach(zone => {
            zone.classList.remove('drop-zone-touch-hover', 'drop-zone-available', 'drop-zone-unavailable');
        });

        this.currentDropZone = null;
    }

    /**
     * Handle tap gesture
     */
    handleTap(element, event) {
        // Check if element has special tap behavior
        const paletteItem = element.closest('.palette-item');
        const requirementBlock = element.closest('.requirement-block');

        if (paletteItem) {
            // Tap on palette item - show details or start drag
            this.showItemDetails(paletteItem);
        } else if (requirementBlock) {
            // Tap on requirement - select or edit
            this.selectRequirement(requirementBlock);
        }
    }

    /**
     * Handle long press gesture
     */
    handleLongPress(element, event) {
        // Long press should start drag mode or show context menu
        if (element.classList.contains('draggable')) {
            // Start drag mode similar to keyboard 'd' key
            if (this.builder.accessibilityManager) {
                this.builder.accessibilityManager.activateKeyboardDrag(element);
            }

            this.provideHapticFeedback('longpress');
        }
    }

    /**
     * Create touch drag preview element
     */
    createTouchDragPreview(element) {
        this.dragPreview = element.cloneNode(true);
        this.dragPreview.className = 'touch-drag-preview';
        this.dragPreview.style.position = 'fixed';
        this.dragPreview.style.pointerEvents = 'none';
        this.dragPreview.style.zIndex = '9999';
        this.dragPreview.style.opacity = '0.8';
        this.dragPreview.style.transform = 'scale(0.9)';

        document.body.appendChild(this.dragPreview);
    }

    /**
     * Get drop zone under touch coordinates
     */
    getDropZoneUnderTouch(x, y) {
        // Temporarily hide drag preview to get element underneath
        const originalDisplay = this.dragPreview ? this.dragPreview.style.display : null;
        if (this.dragPreview) {
            this.dragPreview.style.display = 'none';
        }

        const element = document.elementFromPoint(x, y);
        const dropZone = element ? element.closest('.drop-zone') : null;

        // Restore drag preview
        if (this.dragPreview && originalDisplay !== null) {
            this.dragPreview.style.display = originalDisplay;
        }

        return dropZone;
    }

    /**
     * Detect if touch gesture is intended for scrolling
     */
    detectScrollIntent(touch) {
        // Simple heuristic: if touch is near edge of scrollable area
        const container = this.builder.containerElement;
        const rect = container.getBoundingClientRect();

        const nearEdge = touch.clientY < rect.top + 50 ||
                        touch.clientY > rect.bottom - 50 ||
                        touch.clientX < rect.left + 50 ||
                        touch.clientX > rect.right - 50;

        return nearEdge && (container.scrollHeight > container.clientHeight ||
                           container.scrollWidth > container.clientWidth);
    }

    /**
     * Calculate distance between two points
     */
    calculateDistance(x1, y1, x2, y2) {
        return Math.sqrt(Math.pow(x2 - x1, 2) + Math.pow(y2 - y1, 2));
    }

    /**
     * Provide haptic feedback (if supported)
     */
    provideHapticFeedback(type) {
        if (navigator.vibrate) {
            switch (type) {
                case 'start':
                    navigator.vibrate(50);
                    break;
                case 'over':
                    navigator.vibrate(25);
                    break;
                case 'success':
                    navigator.vibrate([100, 50, 100]);
                    break;
                case 'error':
                    navigator.vibrate([200, 100, 200]);
                    break;
                case 'longpress':
                    navigator.vibrate(75);
                    break;
            }
        }
    }

    /**
     * Show details for palette item
     */
    showItemDetails(paletteItem) {
        // Implementation would show item details tooltip or modal
        console.log('Show details for palette item:', paletteItem);
    }

    /**
     * Select requirement block
     */
    selectRequirement(requirementBlock) {
        // Remove previous selections
        this.builder.containerElement.querySelectorAll('.requirement-selected').forEach(el => {
            el.classList.remove('requirement-selected');
        });

        // Select this requirement
        requirementBlock.classList.add('requirement-selected');
        requirementBlock.focus();
    }

    /**
     * Reset touch state
     */
    resetTouchState() {
        this.touchState = {
            startX: 0,
            startY: 0,
            currentX: 0,
            currentY: 0,
            startTime: 0,
            isDragging: false,
            touchId: null,
            element: null,
            initialScrollTop: 0,
            initialScrollLeft: 0
        };
    }

    /**
     * Public API for touch capabilities
     */
    getTouchCapabilities() {
        return { ...this.capabilities };
    }

    /**
     * Public API for current touch state
     */
    getTouchState() {
        return {
            isDragging: this.touchState.isDragging,
            hasActiveTouch: this.touchState.touchId !== null,
            supportedGestures: [...this.supportedGestures]
        };
    }
}
