/**
 * Accessibility Enhancement JavaScript
 * Provides dynamic accessibility features and ARIA live regions
 */

class AccessibilityManager {
    constructor() {
        this.init();
    }

    init() {
        this.createLiveRegions();
        this.enhanceDropdowns();
        this.enhanceModals();
        this.enhanceForms();
        this.addKeyboardNavigation();
        this.announcePageChanges();
    }

    /**
     * Create ARIA live regions for dynamic content announcements
     */
    createLiveRegions() {
        // Create polite live region for non-urgent announcements
        if (!document.getElementById('aria-live-polite')) {
            const politeRegion = document.createElement('div');
            politeRegion.id = 'aria-live-polite';
            politeRegion.setAttribute('aria-live', 'polite');
            politeRegion.setAttribute('aria-atomic', 'false');
            politeRegion.className = 'sr-only';
            document.body.appendChild(politeRegion);
        }

        // Create assertive live region for urgent announcements
        if (!document.getElementById('aria-live-assertive')) {
            const assertiveRegion = document.createElement('div');
            assertiveRegion.id = 'aria-live-assertive';
            assertiveRegion.setAttribute('aria-live', 'assertive');
            assertiveRegion.setAttribute('aria-atomic', 'true');
            assertiveRegion.className = 'sr-only';
            document.body.appendChild(assertiveRegion);
        }
    }

    /**
     * Announce messages to screen readers
     */
    announce(message, priority = 'polite') {
        const regionId = priority === 'assertive' ? 'aria-live-assertive' : 'aria-live-polite';
        const region = document.getElementById(regionId);
        if (region) {
            region.textContent = message;
            // Clear after announcement to avoid repetition
            setTimeout(() => {
                region.textContent = '';
            }, 1000);
        }
    }

    /**
     * Enhance dropdown accessibility
     */
    enhanceDropdowns() {
        document.querySelectorAll('.dropdown-toggle').forEach(toggle => {
            // Add keyboard support
            toggle.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    toggle.click();
                }
            });

            // Announce state changes
            toggle.addEventListener('click', () => {
                setTimeout(() => {
                    const isExpanded = toggle.getAttribute('aria-expanded') === 'true';
                    const dropdownName = toggle.textContent.trim();
                    this.announce(`${dropdownName} menu ${isExpanded ? 'opened' : 'closed'}`);
                }, 100);
            });
        });
    }

    /**
     * Enhance modal accessibility
     */
    enhanceModals() {
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('shown.bs.modal', () => {
                const title = modal.querySelector('.modal-title');
                if (title) {
                    this.announce(`Dialog opened: ${title.textContent}`);
                }
                // Focus first focusable element or close button
                const firstFocusable = modal.querySelector('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
                if (firstFocusable) {
                    firstFocusable.focus();
                }
            });

            modal.addEventListener('hidden.bs.modal', () => {
                this.announce('Dialog closed');
            });
        });
    }

    /**
     * Enhance form accessibility
     */
    enhanceForms() {
        // Add form validation announcements
        document.querySelectorAll('form').forEach(form => {
            form.addEventListener('submit', (e) => {
                const invalidFields = form.querySelectorAll(':invalid');
                if (invalidFields.length > 0) {
                    this.announce(`Form has ${invalidFields.length} error${invalidFields.length > 1 ? 's' : ''}. Please check your input.`, 'assertive');
                }
            });
        });

        // Announce validation errors as they occur
        document.querySelectorAll('.form-control, .form-select').forEach(field => {
            field.addEventListener('invalid', () => {
                const label = this.getFieldLabel(field);
                this.announce(`Error in ${label}: ${field.validationMessage}`, 'assertive');
            });

            field.addEventListener('input', () => {
                if (field.checkValidity() && field.classList.contains('is-invalid')) {
                    const label = this.getFieldLabel(field);
                    this.announce(`${label} error resolved`);
                }
            });
        });
    }

    /**
     * Get accessible label for a form field
     */
    getFieldLabel(field) {
        const id = field.id;
        if (id) {
            const label = document.querySelector(`label[for="${id}"]`);
            if (label) return label.textContent.trim();
        }

        const ariaLabel = field.getAttribute('aria-label');
        if (ariaLabel) return ariaLabel;

        const placeholder = field.getAttribute('placeholder');
        if (placeholder) return placeholder;

        return field.name || 'field';
    }

    /**
     * Add keyboard navigation enhancements
     */
    addKeyboardNavigation() {
        // Escape key closes dropdowns and modals
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                // Close open dropdowns
                document.querySelectorAll('.dropdown-menu.show').forEach(menu => {
                    const toggle = menu.previousElementSibling;
                    if (toggle && toggle.classList.contains('dropdown-toggle')) {
                        toggle.click();
                    }
                });
            }
        });

        // Add skip navigation
        this.addSkipNavigation();
    }

    /**
     * Add skip navigation links
     */
    addSkipNavigation() {
        const skipNav = document.createElement('a');
        skipNav.href = '#main-content';
        skipNav.className = 'skip-nav';
        skipNav.textContent = 'Skip to main content';

        skipNav.addEventListener('click', (e) => {
            e.preventDefault();
            const mainContent = document.getElementById('main-content') || document.querySelector('main');
            if (mainContent) {
                mainContent.focus();
                mainContent.scrollIntoView();
            }
        });

        document.body.insertBefore(skipNav, document.body.firstChild);
    }

    /**
     * Announce page changes for SPA-like behavior
     */
    announcePageChanges() {
        // Listen for navigation changes
        const observer = new MutationObserver(() => {
            const title = document.title;
            if (title && title !== this.lastTitle) {
                this.announce(`Page changed to: ${title}`);
                this.lastTitle = title;
            }
        });

        observer.observe(document.querySelector('title'), {
            childList: true,
            subtree: true
        });
    }

    /**
     * Enhance tables with proper headers and navigation
     */
    enhanceTables() {
        document.querySelectorAll('table').forEach(table => {
            // Add table caption if missing
            if (!table.querySelector('caption')) {
                const caption = document.createElement('caption');
                caption.textContent = 'Data table';
                caption.className = 'sr-only';
                table.insertBefore(caption, table.firstChild);
            }

            // Ensure proper scope attributes
            table.querySelectorAll('th').forEach(th => {
                if (!th.hasAttribute('scope')) {
                    const isColumnHeader = th.parentElement.parentElement.tagName === 'THEAD';
                    th.setAttribute('scope', isColumnHeader ? 'col' : 'row');
                }
            });
        });
    }

    /**
     * Add loading state announcements
     */
    announceLoadingState(element, isLoading) {
        if (isLoading) {
            element.setAttribute('aria-busy', 'true');
            this.announce('Loading...');
        } else {
            element.removeAttribute('aria-busy');
            this.announce('Loading complete');
        }
    }

    /**
     * Enhance alert messages
     */
    enhanceAlerts() {
        document.querySelectorAll('.alert').forEach(alert => {
            const alertType = Array.from(alert.classList)
                .find(cls => cls.startsWith('alert-'))
                ?.replace('alert-', '') || 'info';

            if (!alert.getAttribute('role')) {
                alert.setAttribute('role', alertType === 'danger' ? 'alert' : 'status');
            }

            // Announce important alerts
            if (alertType === 'danger' || alertType === 'warning') {
                this.announce(`${alertType}: ${alert.textContent.trim()}`, 'assertive');
            }
        });
    }
}

// Initialize accessibility manager when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.accessibilityManager = new AccessibilityManager();
});

// Export for external use
window.AccessibilityManager = AccessibilityManager;
