/**
 * DragDropPalette Component (Issue #191)
 *
 * Provides a palette of requirement types that can be dragged to create new
 * requirements. Supports search, categorization, and accessibility features.
 */

class DragDropPalette {
    constructor(dragDropBuilder) {
        this.builder = dragDropBuilder;
        this.containerElement = null;
        this.searchInput = null;
        this.categories = [];
        this.items = [];

        this.initialize();
    }

    /**
     * Initialize the palette component
     */
    initialize() {
        this.createPaletteStructure();
        this.loadRequirementTypes();
        this.setupEventListeners();
        this.setupAccessibility();
    }

    /**
     * Create the HTML structure for the palette
     */
    createPaletteStructure() {
        // Find or create palette container
        this.containerElement = this.builder.containerElement.querySelector('.drag-drop-palette');

        if (!this.containerElement) {
            this.containerElement = document.createElement('div');
            this.containerElement.className = 'drag-drop-palette';
            this.builder.containerElement.appendChild(this.containerElement);
        }

        // Create palette HTML structure
        this.containerElement.innerHTML = `
            <div class="palette-header">
                <h3>Requirement Types</h3>
                <div class="palette-search">
                    <input type="text"
                           class="palette-search-input"
                           placeholder="Search requirement types..."
                           aria-label="Search requirement types">
                    <button type="button" class="palette-search-clear" aria-label="Clear search">
                        <span aria-hidden="true">×</span>
                    </button>
                </div>
            </div>
            <div class="palette-body">
                <div class="palette-categories"></div>
            </div>
            <div class="palette-footer">
                <button type="button" class="palette-collapse-btn" aria-expanded="true">
                    Collapse Palette
                </button>
            </div>
        `;

        // Get references to key elements
        this.searchInput = this.containerElement.querySelector('.palette-search-input');
    }

    /**
     * Load requirement types into the palette
     */
    loadRequirementTypes() {
        this.categories = [
            {
                id: 'basic',
                name: 'Basic Requirements',
                description: 'Simple requirement checks',
                items: [
                    {
                        type: 'trait',
                        name: 'Trait Check',
                        description: 'Check character trait values (Strength, Dexterity, etc.)',
                        icon: '⚡',
                        template: { trait: { name: '', min: 1 } }
                    },
                    {
                        type: 'has',
                        name: 'Has Item/Feature',
                        description: 'Check if character has something',
                        icon: '🎯',
                        template: { has: { field: 'items', name: '' } }
                    },
                    {
                        type: 'count_tag',
                        name: 'Count with Tag',
                        description: 'Count items with specific tags',
                        icon: '📊',
                        template: { count_tag: { tag: '', min: 1 } }
                    }
                ]
            },
            {
                id: 'logical',
                name: 'Logical Operators',
                description: 'Combine multiple requirements',
                items: [
                    {
                        type: 'any',
                        name: 'Any Of (OR)',
                        description: 'At least one condition must be met',
                        icon: '🔀',
                        template: { any: [] }
                    },
                    {
                        type: 'all',
                        name: 'All Of (AND)',
                        description: 'All conditions must be met',
                        icon: '🔗',
                        template: { all: [] }
                    }
                ]
            }
        ];

        this.renderCategories();
    }

    /**
     * Render requirement type categories
     */
    renderCategories() {
        const categoriesContainer = this.containerElement.querySelector('.palette-categories');

        this.categories.forEach(category => {
            const categoryElement = document.createElement('div');
            categoryElement.className = 'palette-category';
            categoryElement.dataset.categoryId = category.id;

            categoryElement.innerHTML = `
                <div class="category-header">
                    <button type="button"
                            class="category-toggle"
                            aria-expanded="true"
                            aria-controls="category-${category.id}-items">
                        <span class="category-icon" aria-hidden="true">▼</span>
                        <span class="category-name">${category.name}</span>
                    </button>
                    <span class="category-description">${category.description}</span>
                </div>
                <div class="category-items" id="category-${category.id}-items">
                    ${category.items.map(item => this.renderPaletteItem(item)).join('')}
                </div>
            `;

            categoriesContainer.appendChild(categoryElement);
        });
    }

    /**
     * Render individual palette item
     */
    renderPaletteItem(item) {
        return `
            <div class="palette-item draggable"
                 draggable="true"
                 data-requirement-type="${item.type}"
                 data-template='${JSON.stringify(item.template)}'
                 tabindex="0"
                 role="button"
                 aria-label="Drag ${item.name} requirement type">
                <div class="item-icon" aria-hidden="true">${item.icon}</div>
                <div class="item-content">
                    <div class="item-name">${item.name}</div>
                    <div class="item-description">${item.description}</div>
                </div>
                <div class="item-drag-handle" aria-hidden="true">⋮⋮</div>
            </div>
        `;
    }

    /**
     * Set up event listeners for palette functionality
     */
    setupEventListeners() {
        // Search functionality
        this.searchInput.addEventListener('input', this.handleSearch.bind(this));

        // Clear search button
        const clearBtn = this.containerElement.querySelector('.palette-search-clear');
        clearBtn.addEventListener('click', this.clearSearch.bind(this));

        // Category toggles
        this.containerElement.addEventListener('click', (event) => {
            const toggle = event.target.closest('.category-toggle');
            if (toggle) {
                this.toggleCategory(toggle);
            }
        });

        // Palette item interactions
        this.containerElement.addEventListener('dragstart', this.handleItemDragStart.bind(this));
        this.containerElement.addEventListener('keydown', this.handleItemKeydown.bind(this));

        // Palette collapse/expand
        const collapseBtn = this.containerElement.querySelector('.palette-collapse-btn');
        collapseBtn.addEventListener('click', this.togglePalette.bind(this));
    }

    /**
     * Set up accessibility features
     */
    setupAccessibility() {
        // Add ARIA attributes
        this.containerElement.setAttribute('role', 'toolbar');
        this.containerElement.setAttribute('aria-label', 'Requirement types palette');

        // Add keyboard navigation instructions
        const instructions = document.createElement('div');
        instructions.className = 'sr-only palette-instructions';
        instructions.textContent = 'Use arrow keys to navigate requirement types. Press Enter or Space to activate drag mode, or drag with mouse.';
        this.containerElement.insertBefore(instructions, this.containerElement.firstChild);
    }

    /**
     * Handle search input
     */
    handleSearch(event) {
        const query = event.target.value.toLowerCase().trim();

        if (query === '') {
            this.showAllItems();
        } else {
            this.filterItems(query);
        }

        // Announce search results to screen readers
        const visibleItems = this.containerElement.querySelectorAll('.palette-item:not(.hidden)').length;
        this.builder.announceToScreenReader(
            `Search results: ${visibleItems} requirement types found.`
        );
    }

    /**
     * Clear search input
     */
    clearSearch() {
        this.searchInput.value = '';
        this.showAllItems();
        this.searchInput.focus();

        this.builder.announceToScreenReader('Search cleared. All requirement types shown.');
    }

    /**
     * Show all palette items
     */
    showAllItems() {
        const items = this.containerElement.querySelectorAll('.palette-item');
        items.forEach(item => {
            item.classList.remove('hidden');
        });
    }

    /**
     * Filter items based on search query
     */
    filterItems(query) {
        const items = this.containerElement.querySelectorAll('.palette-item');

        items.forEach(item => {
            const name = item.querySelector('.item-name').textContent.toLowerCase();
            const description = item.querySelector('.item-description').textContent.toLowerCase();

            if (name.includes(query) || description.includes(query)) {
                item.classList.remove('hidden');
            } else {
                item.classList.add('hidden');
            }
        });
    }

    /**
     * Toggle category expand/collapse
     */
    toggleCategory(toggleButton) {
        const categoryElement = toggleButton.closest('.palette-category');
        const itemsContainer = categoryElement.querySelector('.category-items');
        const icon = toggleButton.querySelector('.category-icon');

        const isExpanded = toggleButton.getAttribute('aria-expanded') === 'true';

        if (isExpanded) {
            // Collapse
            toggleButton.setAttribute('aria-expanded', 'false');
            itemsContainer.style.display = 'none';
            icon.textContent = '▶';
        } else {
            // Expand
            toggleButton.setAttribute('aria-expanded', 'true');
            itemsContainer.style.display = 'block';
            icon.textContent = '▼';
        }
    }

    /**
     * Handle drag start for palette items
     */
    handleItemDragStart(event) {
        const paletteItem = event.target.closest('.palette-item');
        if (!paletteItem) return;

        const requirementType = paletteItem.dataset.requirementType;
        const template = JSON.parse(paletteItem.dataset.template);

        // Set drag data
        const dragData = {
            type: requirementType,
            source: 'palette',
            template: template,
            id: `new_${requirementType}_${Date.now()}`
        };

        event.dataTransfer.setData('text/json', JSON.stringify(dragData));
        event.dataTransfer.effectAllowed = 'copy';

        // Visual feedback
        paletteItem.classList.add('dragging');

        // Announce to screen readers
        this.builder.announceToScreenReader(
            `Started dragging ${paletteItem.querySelector('.item-name').textContent} from palette.`
        );

        // Remove dragging class after drag ends
        setTimeout(() => {
            paletteItem.classList.remove('dragging');
        }, 100);
    }

    /**
     * Handle keyboard navigation and activation
     */
    handleItemKeydown(event) {
        const paletteItem = event.target.closest('.palette-item');
        if (!paletteItem) return;

        switch (event.key) {
            case 'Enter':
            case ' ':
                event.preventDefault();
                this.activateItemDrag(paletteItem);
                break;

            case 'ArrowDown':
                event.preventDefault();
                this.focusNextItem(paletteItem);
                break;

            case 'ArrowUp':
                event.preventDefault();
                this.focusPreviousItem(paletteItem);
                break;

            case 'Home':
                event.preventDefault();
                this.focusFirstItem();
                break;

            case 'End':
                event.preventDefault();
                this.focusLastItem();
                break;
        }
    }

    /**
     * Activate drag mode for keyboard users
     */
    activateItemDrag(paletteItem) {
        // Delegate to accessibility manager if available
        if (this.builder.accessibilityManager) {
            this.builder.accessibilityManager.activateKeyboardDrag(paletteItem);
        } else {
            // Fallback: simulate drag start
            const dragEvent = new DragEvent('dragstart', {
                bubbles: true,
                cancelable: true,
                dataTransfer: new DataTransfer()
            });

            paletteItem.dispatchEvent(dragEvent);
        }
    }

    /**
     * Focus navigation helpers
     */
    focusNextItem(currentItem) {
        const items = Array.from(this.containerElement.querySelectorAll('.palette-item:not(.hidden)'));
        const currentIndex = items.indexOf(currentItem);
        const nextIndex = (currentIndex + 1) % items.length;
        items[nextIndex].focus();
    }

    focusPreviousItem(currentItem) {
        const items = Array.from(this.containerElement.querySelectorAll('.palette-item:not(.hidden)'));
        const currentIndex = items.indexOf(currentItem);
        const prevIndex = (currentIndex - 1 + items.length) % items.length;
        items[prevIndex].focus();
    }

    focusFirstItem() {
        const firstItem = this.containerElement.querySelector('.palette-item:not(.hidden)');
        if (firstItem) firstItem.focus();
    }

    focusLastItem() {
        const items = this.containerElement.querySelectorAll('.palette-item:not(.hidden)');
        const lastItem = items[items.length - 1];
        if (lastItem) lastItem.focus();
    }

    /**
     * Toggle entire palette visibility
     */
    togglePalette() {
        const body = this.containerElement.querySelector('.palette-body');
        const button = this.containerElement.querySelector('.palette-collapse-btn');

        const isCollapsed = this.containerElement.classList.contains('collapsed');

        if (isCollapsed) {
            // Expand
            this.containerElement.classList.remove('collapsed');
            body.style.display = 'block';
            button.textContent = 'Collapse Palette';
            button.setAttribute('aria-expanded', 'true');
        } else {
            // Collapse
            this.containerElement.classList.add('collapsed');
            body.style.display = 'none';
            button.textContent = 'Expand Palette';
            button.setAttribute('aria-expanded', 'false');
        }
    }

    /**
     * Public API for adding custom requirement types
     */
    addRequirementType(categoryId, requirementType) {
        const category = this.categories.find(cat => cat.id === categoryId);
        if (!category) {
            console.warn(`Category '${categoryId}' not found`);
            return;
        }

        category.items.push(requirementType);
        this.renderCategories(); // Re-render to show new type
    }

    /**
     * Public API for getting current state
     */
    getState() {
        return {
            searchQuery: this.searchInput.value,
            collapsed: this.containerElement.classList.contains('collapsed'),
            categories: this.categories.map(cat => ({
                id: cat.id,
                name: cat.name,
                expanded: this.containerElement.querySelector(`#category-${cat.id}-items`).style.display !== 'none',
                itemCount: cat.items.length
            }))
        };
    }
}
