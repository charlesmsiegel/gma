/**
 * Enhanced Base JavaScript for Game Master Application
 * Implements modern JavaScript standards with improved error handling,
 * accessibility, and performance optimizations.
 */

'use strict';

/**
 * Configuration and Constants
 */
const CONFIG = {
    THEME_SWITCH_TIMEOUT: 3000,
    MESSAGE_AUTO_HIDE_DELAY: 5000,
    FETCH_TIMEOUT: 10000,
    DEBOUNCE_DELAY: 300,
    API_ENDPOINTS: {
        THEME: '/api/profile/theme/',
    },
    STORAGE_KEYS: {
        AUTO_THEME_SWITCH: 'gma-auto-theme-switch',
        USER_PREFERENCES: 'gma-user-preferences',
    },
    CSS_CLASSES: {
        FOCUSED: 'focused',
        VALIDATED: 'was-validated',
        BORDER_PRIMARY: 'border-primary',
        TEXT_PRIMARY: 'text-primary',
    },
    ARIA_ATTRIBUTES: {
        EXPANDED: 'aria-expanded',
        SELECTED: 'aria-selected',
        DESCRIBEDBY: 'aria-describedby',
        LIVE: 'aria-live',
        BUSY: 'aria-busy',
    }
};

/**
 * Utility Functions
 */
const Utils = {
    /**
     * Debounce function to limit the rate of function calls
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func.apply(this, args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    /**
     * Throttle function to limit function calls to once per time period
     */
    throttle(func, limit) {
        let inThrottle;
        return function executedFunction(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },

    /**
     * Safe JSON parse with error handling
     */
    safeJSONParse(str, fallback = null) {
        try {
            return JSON.parse(str);
        } catch (error) {
            console.warn('JSON parse failed:', error);
            return fallback;
        }
    },

    /**
     * Safe localStorage operations
     */
    storage: {
        get(key, fallback = null) {
            try {
                const item = localStorage.getItem(key);
                return item ? JSON.parse(item) : fallback;
            } catch (error) {
                console.warn(`Failed to get storage item ${key}:`, error);
                return fallback;
            }
        },

        set(key, value) {
            try {
                localStorage.setItem(key, JSON.stringify(value));
                return true;
            } catch (error) {
                console.warn(`Failed to set storage item ${key}:`, error);
                return false;
            }
        },

        remove(key) {
            try {
                localStorage.removeItem(key);
                return true;
            } catch (error) {
                console.warn(`Failed to remove storage item ${key}:`, error);
                return false;
            }
        }
    },

    /**
     * Enhanced fetch with timeout and error handling
     */
    async fetchWithTimeout(url, options = {}) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), CONFIG.FETCH_TIMEOUT);

        try {
            const response = await fetch(url, {
                ...options,
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            return response;
        } catch (error) {
            clearTimeout(timeoutId);
            if (error.name === 'AbortError') {
                throw new Error('Request timeout');
            }
            throw error;
        }
    },

    /**
     * Get element with error handling
     */
    getElement(selector, context = document) {
        try {
            return context.querySelector(selector);
        } catch (error) {
            console.warn(`Invalid selector: ${selector}`, error);
            return null;
        }
    },

    /**
     * Get elements with error handling
     */
    getElements(selector, context = document) {
        try {
            return Array.from(context.querySelectorAll(selector));
        } catch (error) {
            console.warn(`Invalid selector: ${selector}`, error);
            return [];
        }
    },

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    /**
     * Sanitize theme name for CSS classes
     */
    sanitizeThemeName(name) {
        return name.replace(/[^a-zA-Z0-9-_]/g, '');
    }
};

/**
 * Enhanced Theme Manager with improved error handling and accessibility
 */
class EnhancedThemeManager {
    constructor() {
        this.currentTheme = window.GMA?.currentTheme || 'light';
        this.availableThemes = window.GMA?.availableThemes || [];
        this.csrfToken = window.GMA?.csrfToken || '';
        this.isAuthenticated = window.GMA?.isAuthenticated || false;
        this.loading = false;

        // Bind methods to maintain context
        this.switchTheme = this.switchTheme.bind(this);
        this.selectThemeOption = this.selectThemeOption.bind(this);
        this.handleSystemThemeChange = Utils.debounce(this.handleSystemThemeChange.bind(this), CONFIG.DEBOUNCE_DELAY);

        this.init();
    }

    /**
     * Initialize theme manager
     */
    init() {
        try {
            this.validateThemeData();
            this.populateThemeSelector();
            this.initializeSystemThemeDetection();
            this.initializeThemePreviewCards();
            this.initializeKeyboardNavigation();
        } catch (error) {
            console.error('Theme manager initialization failed:', error);
            this.showMessage('Theme system initialization failed', 'error');
        }
    }

    /**
     * Validate theme data
     */
    validateThemeData() {
        if (!Array.isArray(this.availableThemes)) {
            throw new Error('Invalid theme data: availableThemes must be an array');
        }

        this.availableThemes.forEach((theme, index) => {
            if (!theme.name || !theme.displayName) {
                console.warn(`Invalid theme at index ${index}:`, theme);
            }
        });
    }

    /**
     * Populate theme selector with enhanced accessibility
     */
    populateThemeSelector() {
        const themeSelector = Utils.getElement('#theme-selector');
        if (!themeSelector || !this.availableThemes.length) return;

        try {
            // Clear existing content
            themeSelector.innerHTML = '';
            themeSelector.setAttribute('role', 'radiogroup');
            themeSelector.setAttribute('aria-label', 'Choose theme');

            // Group themes by category
            const themesByCategory = this.groupThemesByCategory();

            Object.entries(themesByCategory).forEach(([category, themes]) => {
                if (themes.length === 0) return;

                this.createCategorySection(themeSelector, category, themes);
            });

        } catch (error) {
            console.error('Failed to populate theme selector:', error);
            themeSelector.innerHTML = '<p class="text-danger">Failed to load themes</p>';
        }
    }

    /**
     * Create category section for themes
     */
    createCategorySection(container, category, themes) {
        const categoryDiv = document.createElement('div');
        categoryDiv.className = 'col-12 mb-2';
        categoryDiv.innerHTML = `<small class="text-muted fw-semibold">${Utils.escapeHtml(this.formatCategoryName(category))}</small>`;
        container.appendChild(categoryDiv);

        themes.forEach((theme, index) => {
            const themeOption = this.createThemeOption(theme, index);
            container.appendChild(themeOption);
        });
    }

    /**
     * Group themes by category
     */
    groupThemesByCategory() {
        const groups = {};
        this.availableThemes.forEach(theme => {
            const category = theme.category || 'standard';
            if (!groups[category]) groups[category] = [];
            groups[category].push(theme);
        });
        return groups;
    }

    /**
     * Format category name with fallback
     */
    formatCategoryName(category) {
        const names = {
            'standard': 'Standard Themes',
            'dark': 'Dark Themes',
            'accessibility': 'Accessibility',
            'fantasy': 'Fantasy',
            'modern': 'Modern',
            'vintage': 'Vintage'
        };
        return names[category] || category.charAt(0).toUpperCase() + category.slice(1);
    }

    /**
     * Create theme option with enhanced accessibility
     */
    createThemeOption(theme, index) {
        const col = document.createElement('div');
        col.className = 'col-6 col-lg-4';

        const isCurrentTheme = theme.name === this.currentTheme;
        const sanitizedThemeName = Utils.sanitizeThemeName(theme.name);

        col.innerHTML = `
            <div class="card theme-card h-100 ${isCurrentTheme ? CONFIG.CSS_CLASSES.BORDER_PRIMARY : ''}"
                 role="radio"
                 aria-checked="${isCurrentTheme}"
                 aria-label="Theme: ${Utils.escapeHtml(theme.displayName)}"
                 tabindex="${isCurrentTheme ? '0' : '-1'}"
                 data-theme="${sanitizedThemeName}"
                 data-theme-name="${Utils.escapeHtml(theme.name)}">
                <div class="card-body p-2 text-center">
                    <div class="theme-preview mb-2"
                         style="height: 30px; background: linear-gradient(45deg, ${theme.backgroundColor}, ${theme.primaryColor}); border-radius: 4px;"
                         aria-hidden="true"></div>
                    <div class="d-flex align-items-center justify-content-between">
                        <small class="fw-semibold">${Utils.escapeHtml(theme.displayName)}</small>
                        <i class="bi bi-${theme.isDark ? 'moon' : 'sun'}" aria-hidden="true"></i>
                    </div>
                    ${isCurrentTheme ? `<small class="${CONFIG.CSS_CLASSES.TEXT_PRIMARY}"><i class="bi bi-check-circle" aria-hidden="true"></i> Current</small>` : ''}
                </div>
            </div>
        `;

        // Add event listeners
        const card = col.querySelector('.theme-card');
        this.addThemeCardListeners(card, theme.name);

        return col;
    }

    /**
     * Add event listeners to theme cards
     */
    addThemeCardListeners(card, themeName) {
        // Click handler
        card.addEventListener('click', (e) => {
            e.preventDefault();
            this.switchTheme(themeName);
        });

        // Keyboard handler
        card.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                this.switchTheme(themeName);
            }
        });

        // Focus management
        card.addEventListener('focus', () => {
            card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        });
    }

    /**
     * Initialize keyboard navigation for theme selector
     */
    initializeKeyboardNavigation() {
        const themeSelector = Utils.getElement('#theme-selector');
        if (!themeSelector) return;

        themeSelector.addEventListener('keydown', (e) => {
            const cards = Utils.getElements('.theme-card[role="radio"]', themeSelector);
            const currentIndex = cards.findIndex(card => card.tabIndex === 0);

            let newIndex = currentIndex;

            switch (e.key) {
                case 'ArrowLeft':
                case 'ArrowUp':
                    e.preventDefault();
                    newIndex = currentIndex > 0 ? currentIndex - 1 : cards.length - 1;
                    break;
                case 'ArrowRight':
                case 'ArrowDown':
                    e.preventDefault();
                    newIndex = currentIndex < cards.length - 1 ? currentIndex + 1 : 0;
                    break;
                case 'Home':
                    e.preventDefault();
                    newIndex = 0;
                    break;
                case 'End':
                    e.preventDefault();
                    newIndex = cards.length - 1;
                    break;
            }

            if (newIndex !== currentIndex && cards[newIndex]) {
                // Update tabindex
                cards[currentIndex].tabIndex = -1;
                cards[newIndex].tabIndex = 0;
                cards[newIndex].focus();
            }
        });
    }

    /**
     * Initialize system theme detection with enhanced error handling
     */
    initializeSystemThemeDetection() {
        if (!window.matchMedia) {
            console.warn('matchMedia not supported, system theme detection disabled');
            return;
        }

        try {
            const darkModeQuery = window.matchMedia('(prefers-color-scheme: dark)');
            const autoSwitch = Utils.getElement('#autoThemeSwitch');

            if (autoSwitch) {
                this.setupAutoThemeSwitch(autoSwitch, darkModeQuery);
            }
        } catch (error) {
            console.error('Failed to initialize system theme detection:', error);
        }
    }

    /**
     * Setup auto theme switch functionality
     */
    setupAutoThemeSwitch(autoSwitch, darkModeQuery) {
        // Load saved preference
        const autoSwitchEnabled = Utils.storage.get(CONFIG.STORAGE_KEYS.AUTO_THEME_SWITCH, false);
        autoSwitch.checked = autoSwitchEnabled;

        // Handle auto-switch toggle
        autoSwitch.addEventListener('change', (e) => {
            const enabled = e.target.checked;
            Utils.storage.set(CONFIG.STORAGE_KEYS.AUTO_THEME_SWITCH, enabled);

            if (enabled) {
                this.applySystemTheme(darkModeQuery.matches);
            }

            // Announce change to screen readers
            if (window.accessibilityManager) {
                window.accessibilityManager.announce(
                    `Auto theme switching ${enabled ? 'enabled' : 'disabled'}`
                );
            }
        });

        // Listen for system theme changes
        darkModeQuery.addEventListener('change', this.handleSystemThemeChange);

        // Apply system theme if auto-switch is enabled
        if (autoSwitchEnabled) {
            this.applySystemTheme(darkModeQuery.matches);
        }
    }

    /**
     * Handle system theme changes
     */
    handleSystemThemeChange(e) {
        const autoSwitch = Utils.getElement('#autoThemeSwitch');
        if (autoSwitch?.checked) {
            this.applySystemTheme(e.matches);
        }
    }

    /**
     * Apply system theme based on preference
     */
    applySystemTheme(isDark) {
        const appropriateTheme = this.findThemeByDarkMode(isDark);
        if (appropriateTheme) {
            this.switchTheme(appropriateTheme.name);
        }
    }

    /**
     * Find theme by dark mode preference
     */
    findThemeByDarkMode(isDark) {
        return this.availableThemes.find(theme =>
            theme.isDark === isDark && theme.name !== this.currentTheme
        ) || this.availableThemes.find(theme => theme.isDark === isDark);
    }

    /**
     * Initialize theme preview cards
     */
    initializeThemePreviewCards() {
        const themeOptions = Utils.getElements('.theme-option');
        themeOptions.forEach(option => {
            option.addEventListener('click', () => {
                const themeName = option.getAttribute('data-theme-name') ||
                                option.querySelector('input[type="radio"]')?.value;
                if (themeName) {
                    this.selectThemeOption(themeName);
                }
            });
        });
    }

    /**
     * Switch theme with enhanced error handling and loading states
     */
    async switchTheme(themeName) {
        if (!this.isAuthenticated) {
            console.warn('Theme switching requires authentication');
            this.showMessage('Please log in to change themes', 'warning');
            return;
        }

        if (this.loading) {
            console.warn('Theme switch already in progress');
            return;
        }

        if (!themeName || typeof themeName !== 'string') {
            console.error('Invalid theme name:', themeName);
            this.showMessage('Invalid theme selection', 'error');
            return;
        }

        const sanitizedThemeName = Utils.sanitizeThemeName(themeName);

        try {
            this.loading = true;
            this.setLoadingState(true);

            // Update UI immediately for better UX
            this.updateThemeUI(sanitizedThemeName);

            // Send update to server
            const response = await Utils.fetchWithTimeout(CONFIG.API_ENDPOINTS.THEME, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({ theme: themeName })
            });

            if (response.ok) {
                this.currentTheme = themeName;
                this.updateCurrentThemeIndicators();

                // Show success message
                this.showMessage('Theme updated successfully!', 'success');

                // Announce change to screen readers
                if (window.accessibilityManager) {
                    window.accessibilityManager.announce(`Theme changed to ${themeName}`);
                }
            } else {
                throw new Error(`Server responded with ${response.status}`);
            }
        } catch (error) {
            console.error('Theme switch failed:', error);

            // Revert UI changes on failure
            this.updateThemeUI(this.currentTheme);

            // Show user-friendly error message
            const errorMessage = error.message.includes('timeout')
                ? 'Theme update timed out. Please check your connection.'
                : 'Failed to update theme. Please try again.';

            this.showMessage(errorMessage, 'error');

            // Announce error to screen readers
            if (window.accessibilityManager) {
                window.accessibilityManager.announce('Theme change failed', 'assertive');
            }
        } finally {
            this.loading = false;
            this.setLoadingState(false);
        }
    }

    /**
     * Set loading state with accessibility support
     */
    setLoadingState(isLoading) {
        const themeSelector = Utils.getElement('#theme-selector');
        if (themeSelector) {
            if (isLoading) {
                themeSelector.setAttribute(CONFIG.ARIA_ATTRIBUTES.BUSY, 'true');
            } else {
                themeSelector.removeAttribute(CONFIG.ARIA_ATTRIBUTES.BUSY);
            }
        }
    }

    /**
     * Update theme UI
     */
    updateThemeUI(themeName) {
        const sanitizedThemeName = Utils.sanitizeThemeName(themeName);
        document.body.setAttribute('data-theme', sanitizedThemeName);

        // Update theme CSS link if using dynamic theme loading
        const themeLink = Utils.getElement('link[href*="themes/"]');
        if (themeLink) {
            const newHref = themeLink.href.replace(/themes\/[^\/]+\.css/, `themes/${sanitizedThemeName}.css`);
            themeLink.href = newHref;
        }
    }

    /**
     * Update current theme indicators with improved accessibility
     */
    updateCurrentThemeIndicators() {
        // Update theme cards in dropdown
        const themeCards = Utils.getElements('[data-theme]');
        themeCards.forEach(card => {
            const cardTheme = card.getAttribute('data-theme');
            const isCurrentTheme = cardTheme === Utils.sanitizeThemeName(this.currentTheme);

            card.classList.toggle(CONFIG.CSS_CLASSES.BORDER_PRIMARY, isCurrentTheme);

            if (card.hasAttribute('role') && card.getAttribute('role') === 'radio') {
                card.setAttribute('aria-checked', isCurrentTheme.toString());
                card.tabIndex = isCurrentTheme ? 0 : -1;
            }

            this.updateThemeCardIndicator(card, isCurrentTheme);
        });

        // Update theme gallery modal
        this.updateThemeGalleryIndicators();
    }

    /**
     * Update theme card indicator
     */
    updateThemeCardIndicator(card, isCurrentTheme) {
        const currentIndicator = card.querySelector(`.${CONFIG.CSS_CLASSES.TEXT_PRIMARY}`);

        if (currentIndicator && !isCurrentTheme) {
            currentIndicator.remove();
        } else if (!currentIndicator && isCurrentTheme) {
            const indicator = document.createElement('small');
            indicator.className = CONFIG.CSS_CLASSES.TEXT_PRIMARY;
            indicator.innerHTML = '<i class="bi bi-check-circle" aria-hidden="true"></i> Current';
            card.querySelector('.card-body')?.appendChild(indicator);
        }
    }

    /**
     * Update theme gallery indicators
     */
    updateThemeGalleryIndicators() {
        const galleryCards = Utils.getElements('.theme-preview-card');
        galleryCards.forEach(card => {
            const cardTheme = card.getAttribute('data-theme-name');
            const isCurrentTheme = cardTheme === this.currentTheme;

            card.classList.toggle(CONFIG.CSS_CLASSES.BORDER_PRIMARY, isCurrentTheme);

            const applyButton = card.querySelector('button[onclick*="switchTheme"]');
            const currentBadge = card.querySelector('.badge');

            if (isCurrentTheme && applyButton) {
                applyButton.outerHTML = `<span class="badge text-white" style="background-color: var(--theme-primary);"><i class="bi bi-check-circle me-1" aria-hidden="true"></i>Current</span>`;
            } else if (!isCurrentTheme && currentBadge && !applyButton) {
                const escapedTheme = Utils.escapeHtml(cardTheme);
                currentBadge.outerHTML = `<button type="button" class="btn btn-sm" onclick="themeManager.switchTheme('${escapedTheme}')" style="background-color: var(--theme-primary); color: white; border: none;"><i class="bi bi-brush me-1" aria-hidden="true"></i>Apply</button>`;
            }
        });
    }

    /**
     * Select theme option with enhanced accessibility
     */
    selectThemeOption(themeName) {
        const sanitizedThemeName = Utils.sanitizeThemeName(themeName);
        const radioButton = Utils.getElement(`input[name="theme"][value="${sanitizedThemeName}"]`);

        if (radioButton) {
            radioButton.checked = true;

            // Update visual selection
            const themeOptions = Utils.getElements('.theme-option');
            themeOptions.forEach(option => {
                option.classList.remove(CONFIG.CSS_CLASSES.BORDER_PRIMARY);
                option.setAttribute(CONFIG.ARIA_ATTRIBUTES.SELECTED, 'false');
            });

            const selectedOption = radioButton.closest('.theme-option');
            if (selectedOption) {
                selectedOption.classList.add(CONFIG.CSS_CLASSES.BORDER_PRIMARY);
                selectedOption.setAttribute(CONFIG.ARIA_ATTRIBUTES.SELECTED, 'true');
            }

            // Announce selection to screen readers
            if (window.accessibilityManager) {
                window.accessibilityManager.announce(`Selected theme: ${themeName}`);
            }
        }
    }

    /**
     * Show message with enhanced accessibility
     */
    showMessage(text, type = 'info') {
        try {
            // Create and show a toast message
            const toast = document.createElement('div');
            toast.className = `alert alert-${type} alert-dismissible fade show position-fixed top-0 end-0 m-3`;
            toast.style.zIndex = '9999';
            toast.setAttribute('role', type === 'error' ? 'alert' : 'status');
            toast.setAttribute('aria-live', type === 'error' ? 'assertive' : 'polite');

            const iconMap = {
                success: 'check-circle',
                error: 'exclamation-triangle',
                warning: 'exclamation-triangle',
                info: 'info-circle'
            };

            toast.innerHTML = `
                <div class="d-flex align-items-center">
                    <i class="bi bi-${iconMap[type] || 'info-circle'}-fill me-2" aria-hidden="true"></i>
                    ${Utils.escapeHtml(text)}
                </div>
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close notification"></button>
            `;

            document.body.appendChild(toast);

            // Auto-remove after delay
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.remove();
                }
            }, CONFIG.MESSAGE_AUTO_HIDE_DELAY);

            // Announce to screen readers
            if (window.accessibilityManager) {
                window.accessibilityManager.announce(text, type === 'error' ? 'assertive' : 'polite');
            }

        } catch (error) {
            console.error('Failed to show message:', error);
            // Fallback to console
            console.log(`${type.toUpperCase()}: ${text}`);
        }
    }
}

/**
 * Enhanced Form Manager
 */
class EnhancedFormManager {
    constructor() {
        this.init();
    }

    init() {
        this.initializeFormEnhancements();
        this.initializePasswordToggles();
        this.initializeValidationEnhancements();
    }

    /**
     * Initialize enhanced form interactions
     */
    initializeFormEnhancements() {
        const formControls = Utils.getElements('.form-control, .form-select');

        formControls.forEach(input => {
            // Add focus/blur classes for enhanced styling
            input.addEventListener('focus', () => {
                input.parentElement?.classList.add(CONFIG.CSS_CLASSES.FOCUSED);
                this.announceFieldFocus(input);
            });

            input.addEventListener('blur', () => {
                input.parentElement?.classList.remove(CONFIG.CSS_CLASSES.FOCUSED);
            });

            // Enhanced validation feedback
            input.addEventListener('invalid', () => {
                this.handleFieldValidation(input, false);
            });

            input.addEventListener('input', Utils.debounce(() => {
                if (input.checkValidity() && input.classList.contains('is-invalid')) {
                    this.handleFieldValidation(input, true);
                }
            }, CONFIG.DEBOUNCE_DELAY));
        });
    }

    /**
     * Announce field focus to screen readers
     */
    announceFieldFocus(input) {
        const label = this.getFieldLabel(input);
        const isRequired = input.hasAttribute('required');

        if (isRequired && window.accessibilityManager) {
            window.accessibilityManager.announce(`${label} field, required`);
        }
    }

    /**
     * Handle field validation with accessibility
     */
    handleFieldValidation(input, isValid) {
        const label = this.getFieldLabel(input);

        if (window.accessibilityManager) {
            if (isValid) {
                window.accessibilityManager.announce(`${label} error resolved`);
            } else {
                window.accessibilityManager.announce(
                    `Error in ${label}: ${input.validationMessage}`,
                    'assertive'
                );
            }
        }
    }

    /**
     * Get accessible label for a form field
     */
    getFieldLabel(field) {
        const id = field.id;
        if (id) {
            const label = Utils.getElement(`label[for="${id}"]`);
            if (label) return label.textContent.trim();
        }

        const ariaLabel = field.getAttribute('aria-label');
        if (ariaLabel) return ariaLabel;

        const placeholder = field.getAttribute('placeholder');
        if (placeholder) return placeholder;

        return field.name || 'field';
    }

    /**
     * Initialize enhanced validation
     */
    initializeValidationEnhancements() {
        const forms = Utils.getElements('form[novalidate]');

        forms.forEach(form => {
            form.addEventListener('submit', (event) => {
                if (!form.checkValidity()) {
                    event.preventDefault();
                    event.stopPropagation();

                    // Focus on first invalid field
                    const firstInvalid = form.querySelector(':invalid');
                    if (firstInvalid) {
                        firstInvalid.focus();

                        // Scroll into view smoothly
                        firstInvalid.scrollIntoView({
                            behavior: 'smooth',
                            block: 'center'
                        });
                    }

                    // Announce form errors
                    const invalidFields = form.querySelectorAll(':invalid');
                    if (window.accessibilityManager) {
                        window.accessibilityManager.announce(
                            `Form has ${invalidFields.length} error${invalidFields.length > 1 ? 's' : ''}. Please check your input.`,
                            'assertive'
                        );
                    }
                }

                form.classList.add(CONFIG.CSS_CLASSES.VALIDATED);
            });
        });
    }

    /**
     * Initialize password visibility toggles
     */
    initializePasswordToggles() {
        const passwordToggles = Utils.getElements('.password-toggle');

        passwordToggles.forEach(toggle => {
            toggle.addEventListener('click', () => {
                this.togglePasswordVisibility(toggle);
            });

            toggle.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    this.togglePasswordVisibility(toggle);
                }
            });
        });
    }

    /**
     * Toggle password visibility with accessibility
     */
    togglePasswordVisibility(toggle) {
        const input = toggle.previousElementSibling;
        const icon = toggle.querySelector('i');

        if (!input || !icon) return;

        const isPassword = input.type === 'password';
        const newType = isPassword ? 'text' : 'password';
        const newIconClass = isPassword ? 'bi-eye-slash' : 'bi-eye';
        const oldIconClass = isPassword ? 'bi-eye' : 'bi-eye-slash';

        input.type = newType;
        icon.classList.replace(oldIconClass, newIconClass);

        // Update accessibility attributes
        toggle.setAttribute('aria-label', `${isPassword ? 'Hide' : 'Show'} password`);

        // Announce change to screen readers
        if (window.accessibilityManager) {
            window.accessibilityManager.announce(
                `Password ${isPassword ? 'shown' : 'hidden'}`
            );
        }
    }
}

/**
 * Enhanced Navigation Manager
 */
class EnhancedNavigationManager {
    constructor() {
        this.init();
    }

    init() {
        this.highlightCurrentPage();
        this.initializeMessageAutoHide();
    }

    /**
     * Highlight current page in navigation
     */
    highlightCurrentPage() {
        const currentPath = window.location.pathname;
        const navLinks = Utils.getElements('.navbar-nav .nav-link, .navbar-nav .btn');

        navLinks.forEach(link => {
            const linkPath = link.getAttribute('href');
            if (linkPath === currentPath) {
                link.classList.add('active');
                link.setAttribute('aria-current', 'page');
            }
        });
    }

    /**
     * Initialize message auto-hide with accessibility
     */
    initializeMessageAutoHide() {
        const messages = Utils.getElements('.alert[role="alert"], .alert[role="status"]');

        messages.forEach(message => {
            if (!message.querySelector('.btn-close')) return;

            // Announce message to screen readers
            if (window.accessibilityManager) {
                const messageText = message.textContent.trim();
                const messageType = message.classList.contains('alert-danger') ? 'error' : 'info';
                window.accessibilityManager.announce(messageText, messageType === 'error' ? 'assertive' : 'polite');
            }

            setTimeout(() => {
                if (message.parentNode && typeof bootstrap !== 'undefined') {
                    const bsAlert = new bootstrap.Alert(message);
                    bsAlert.close();
                }
            }, CONFIG.MESSAGE_AUTO_HIDE_DELAY);
        });
    }
}

/**
 * Application Initialization
 */
class EnhancedGMAApplication {
    constructor() {
        this.themeManager = null;
        this.formManager = null;
        this.navigationManager = null;
        this.initialized = false;
    }

    async init() {
        if (this.initialized) {
            console.warn('Application already initialized');
            return;
        }

        try {
            // Initialize managers
            this.themeManager = new EnhancedThemeManager();
            this.formManager = new EnhancedFormManager();
            this.navigationManager = new EnhancedNavigationManager();

            // Set global references for template compatibility
            window.themeManager = this.themeManager;
            window.switchTheme = this.themeManager.switchTheme;
            window.selectThemeOption = this.themeManager.selectThemeOption;

            this.initialized = true;
            console.log('GMA Application initialized successfully');

        } catch (error) {
            console.error('Failed to initialize GMA Application:', error);

            // Show fallback error message
            if (document.body) {
                const errorDiv = document.createElement('div');
                errorDiv.className = 'alert alert-danger position-fixed top-0 start-50 translate-middle-x mt-3';
                errorDiv.style.zIndex = '9999';
                errorDiv.textContent = 'Application initialization failed. Some features may not work correctly.';
                document.body.appendChild(errorDiv);

                setTimeout(() => errorDiv.remove(), 5000);
            }
        }
    }
}

// Initialize application when DOM is ready
let gmaApp;

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', async () => {
        gmaApp = new EnhancedGMAApplication();
        await gmaApp.init();
    });
} else {
    // DOM already loaded
    gmaApp = new EnhancedGMAApplication();
    gmaApp.init();
}

// Export for external access
window.GMAApplication = EnhancedGMAApplication;
