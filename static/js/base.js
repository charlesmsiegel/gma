// Base JavaScript for Game Master Application

// Theme Management System
class ThemeManager {
    constructor() {
        this.currentTheme = window.GMA?.currentTheme || 'light';
        this.availableThemes = window.GMA?.availableThemes || [];
        this.csrfToken = window.GMA?.csrfToken || '';
        this.isAuthenticated = window.GMA?.isAuthenticated || false;

        this.init();
    }

    init() {
        this.populateThemeSelector();
        this.initializeSystemThemeDetection();
        this.initializeThemePreviewCards();
    }

    populateThemeSelector() {
        const themeSelector = document.getElementById('theme-selector');
        if (!themeSelector || !this.availableThemes.length) return;

        themeSelector.innerHTML = '';

        // Group themes by category
        const themesByCategory = this.groupThemesByCategory();

        Object.entries(themesByCategory).forEach(([category, themes]) => {
            if (themes.length === 0) return;

            const categoryDiv = document.createElement('div');
            categoryDiv.className = 'col-12 mb-2';
            categoryDiv.innerHTML = `<small class="text-muted fw-semibold">${this.formatCategoryName(category)}</small>`;
            themeSelector.appendChild(categoryDiv);

            themes.forEach(theme => {
                const themeOption = this.createThemeOption(theme);
                themeSelector.appendChild(themeOption);
            });
        });
    }

    groupThemesByCategory() {
        const groups = {};
        this.availableThemes.forEach(theme => {
            const category = theme.category || 'standard';
            if (!groups[category]) groups[category] = [];
            groups[category].push(theme);
        });
        return groups;
    }

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

    createThemeOption(theme) {
        const div = document.createElement('div');
        div.className = 'col-12 mb-1';

        const isCurrentTheme = theme.name === this.currentTheme;

        // Calculate text color based on theme background
        const textColor = this.getContrastColor(theme.backgroundColor);
        const mutedTextColor = this.getMutedTextColor(theme.backgroundColor);

        div.innerHTML = `
            <div class="d-flex align-items-center p-2 rounded theme-option ${isCurrentTheme ? 'bg-primary bg-opacity-10 border border-primary' : ''}"
                 style="cursor: pointer; transition: all 0.2s ease;"
                 onclick="themeManager.switchTheme('${theme.name}')"
                 data-theme="${theme.name}">

                <!-- Color Preview -->
                <div class="d-flex me-3">
                    <div class="rounded-circle me-1"
                         style="width: 16px; height: 16px; background: ${theme.primaryColor}; border: 2px solid rgba(128,128,128,0.3);"></div>
                    <div class="rounded-circle"
                         style="width: 16px; height: 16px; background: ${theme.backgroundColor}; border: 2px solid rgba(128,128,128,0.3);"></div>
                </div>

                <!-- Theme Info -->
                <div class="flex-grow-1">
                    <div class="d-flex align-items-center">
                        <span class="fw-semibold me-2" style="color: ${textColor};">${theme.displayName}</span>
                        ${theme.isDark ?
                            `<i class="bi bi-moon me-1" style="font-size: 0.8rem; color: ${mutedTextColor};"></i>` :
                            `<i class="bi bi-sun me-1" style="font-size: 0.8rem; color: #ffc107;"></i>`
                        }
                        ${theme.isHighContrast ?
                            `<i class="bi bi-eye" style="font-size: 0.8rem; color: ${theme.primaryColor};" title="High Contrast"></i>` :
                            ''
                        }
                    </div>
                    <small style="color: ${mutedTextColor};">${theme.category}</small>
                </div>

                <!-- Current Indicator -->
                ${isCurrentTheme ?
                    '<i class="bi bi-check-circle-fill text-primary ms-2"></i>' :
                    `<i class="bi bi-circle ms-2" style="opacity: 0.5; color: ${mutedTextColor};"></i>`
                }
            </div>
        `;

        // Add hover effects
        const option = div.querySelector('.theme-option');
        option.addEventListener('mouseenter', () => {
            if (!isCurrentTheme) {
                option.classList.add('bg-light');
                option.style.backgroundColor = this.getLightenedColor(theme.backgroundColor, 0.1);
            }
        });

        option.addEventListener('mouseleave', () => {
            if (!isCurrentTheme) {
                option.classList.remove('bg-light');
                option.style.backgroundColor = '';
            }
        });

        return div;
    }

    // Helper function to calculate contrast color (black or white) based on background
    getContrastColor(hexColor) {
        // Convert hex to RGB
        const r = parseInt(hexColor.slice(1, 3), 16);
        const g = parseInt(hexColor.slice(3, 5), 16);
        const b = parseInt(hexColor.slice(5, 7), 16);

        // Calculate luminance using standard formula
        const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;

        // Return white for dark backgrounds, black for light backgrounds
        return luminance > 0.5 ? '#000000' : '#ffffff';
    }

    // Helper function to get muted text color
    getMutedTextColor(hexColor) {
        const r = parseInt(hexColor.slice(1, 3), 16);
        const g = parseInt(hexColor.slice(3, 5), 16);
        const b = parseInt(hexColor.slice(5, 7), 16);

        const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;

        // Return lighter gray for dark backgrounds, darker gray for light backgrounds
        return luminance > 0.5 ? '#666666' : '#cccccc';
    }

    // Helper function to lighten/darken a color for hover effects
    getLightenedColor(hexColor, factor) {
        const r = parseInt(hexColor.slice(1, 3), 16);
        const g = parseInt(hexColor.slice(3, 5), 16);
        const b = parseInt(hexColor.slice(5, 7), 16);

        const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;

        // Lighten dark colors, darken light colors
        const adjustment = luminance > 0.5 ? -20 : 20;

        const newR = Math.max(0, Math.min(255, r + adjustment));
        const newG = Math.max(0, Math.min(255, g + adjustment));
        const newB = Math.max(0, Math.min(255, b + adjustment));

        return `rgb(${newR}, ${newG}, ${newB})`;
    }

    initializeSystemThemeDetection() {
        if (!window.matchMedia) return;

        const darkModeQuery = window.matchMedia('(prefers-color-scheme: dark)');
        const autoSwitch = document.getElementById('autoThemeSwitch');

        if (autoSwitch) {
            // Load saved preference
            const autoSwitchEnabled = localStorage.getItem('gma-auto-theme-switch') === 'true';
            autoSwitch.checked = autoSwitchEnabled;

            // Handle auto-switch toggle
            autoSwitch.addEventListener('change', (e) => {
                localStorage.setItem('gma-auto-theme-switch', e.target.checked);
                if (e.target.checked) {
                    this.applySystemTheme(darkModeQuery.matches);
                }
            });

            // Listen for system theme changes
            darkModeQuery.addEventListener('change', (e) => {
                if (autoSwitch.checked) {
                    this.applySystemTheme(e.matches);
                }
            });

            // Only apply system theme on page load if user is NOT authenticated
            // or if they haven't explicitly chosen a theme
            // This prevents overriding explicit user theme choices
            if (autoSwitchEnabled && !this.isAuthenticated) {
                this.applySystemTheme(darkModeQuery.matches);
            }
        }
    }

    applySystemTheme(isDark) {
        // Check if current theme already matches the desired mode
        const currentThemeObj = this.availableThemes.find(theme => theme.name === this.currentTheme);
        if (currentThemeObj && currentThemeObj.isDark === isDark) {
            // Current theme already matches system preference, no need to change
            return;
        }

        const appropriateTheme = this.findThemeByDarkMode(isDark);
        if (appropriateTheme) {
            this.switchTheme(appropriateTheme.name);
        }
    }

    findThemeByDarkMode(isDark) {
        // Find any theme that matches the dark/light mode preference
        return this.availableThemes.find(theme => theme.isDark === isDark);
    }

    initializeThemePreviewCards() {
        // Initialize theme option selection in profile edit
        const themeOptions = document.querySelectorAll('.theme-option');
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

    async switchTheme(themeName) {
        if (!this.isAuthenticated) {
            console.warn('Theme switching requires authentication');
            return;
        }

        try {
            // Update UI immediately for better UX
            this.updateThemeUI(themeName);

            // Send update to server
            const response = await fetch('/api/profile/theme/', {
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
            } else {
                // Revert UI changes on failure
                this.updateThemeUI(this.currentTheme);
                throw new Error('Failed to update theme');
            }
        } catch (error) {
            console.error('Theme switch failed:', error);
            this.showMessage('Failed to update theme. Please try again.', 'error');
        }
    }

    updateThemeUI(themeName) {
        document.body.setAttribute('data-theme', themeName);

        // Update theme CSS link if using dynamic theme loading
        const themeLink = document.querySelector('link[href*="themes/"]');
        if (themeLink) {
            const newHref = themeLink.href.replace(/themes\/[^\/]+\.css/, `themes/${themeName}.css`);
            themeLink.href = newHref;
        }
    }

    updateCurrentThemeIndicators() {
        // Update theme cards in dropdown
        const themeCards = document.querySelectorAll('[data-theme]');
        themeCards.forEach(card => {
            const cardTheme = card.getAttribute('data-theme');
            const isCurrentTheme = cardTheme === this.currentTheme;

            card.classList.toggle('border-primary', isCurrentTheme);

            const currentIndicator = card.querySelector('.text-primary');
            if (currentIndicator && !isCurrentTheme) {
                currentIndicator.remove();
            } else if (!currentIndicator && isCurrentTheme) {
                const indicator = document.createElement('small');
                indicator.className = 'text-primary';
                indicator.innerHTML = '<i class="bi bi-check-circle"></i> Current';
                card.querySelector('.card-body').appendChild(indicator);
            }
        });

        // Update theme gallery modal
        const galleryCards = document.querySelectorAll('.theme-preview-card');
        galleryCards.forEach(card => {
            const cardTheme = card.getAttribute('data-theme-name');
            const isCurrentTheme = cardTheme === this.currentTheme;

            card.classList.toggle('border-primary', isCurrentTheme);

            const applyButton = card.querySelector('button[onclick*="switchTheme"]');
            const currentBadge = card.querySelector('.badge');

            if (isCurrentTheme) {
                if (applyButton) {
                    applyButton.outerHTML = `<span class="badge text-white" style="background-color: var(--theme-primary);"><i class="bi bi-check-circle me-1"></i>Current</span>`;
                }
            } else if (currentBadge && !applyButton) {
                currentBadge.outerHTML = `<button type="button" class="btn btn-sm" onclick="switchTheme('${cardTheme}')" style="background-color: var(--theme-primary); color: white; border: none;"><i class="bi bi-brush me-1"></i>Apply</button>`;
            }
        });
    }

    selectThemeOption(themeName) {
        const radioButton = document.querySelector(`input[name="theme"][value="${themeName}"]`);
        if (radioButton) {
            radioButton.checked = true;

            // Update visual selection
            const themeOptions = document.querySelectorAll('.theme-option');
            themeOptions.forEach(option => {
                option.classList.remove('border-primary');
            });

            const selectedOption = radioButton.closest('.theme-option');
            if (selectedOption) {
                selectedOption.classList.add('border-primary');
            }
        }
    }

    showMessage(text, type = 'info') {
        // Create and show a toast message
        const toast = document.createElement('div');
        toast.className = `alert alert-${type} alert-dismissible fade show position-fixed top-0 end-0 m-3`;
        toast.style.zIndex = '9999';
        toast.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="bi bi-${type === 'success' ? 'check-circle' : 'exclamation-triangle'}-fill me-2"></i>
                ${text}
            </div>
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;

        document.body.appendChild(toast);

        // Auto-remove after 3 seconds
        setTimeout(() => {
            if (toast.parentNode) {
                toast.remove();
            }
        }, 3000);
    }
}

// Global theme manager instance
let themeManager;

// Global functions for template usage
function switchTheme(themeName) {
    if (themeManager) {
        themeManager.switchTheme(themeName);
    }
}

function selectThemeOption(themeName) {
    if (themeManager) {
        themeManager.selectThemeOption(themeName);
    }
}

document.addEventListener('DOMContentLoaded', function() {
    // Initialize theme manager
    themeManager = new ThemeManager();

    // Auto-hide messages after 5 seconds
    const messages = document.querySelectorAll('.alert[role="alert"]');
    messages.forEach(function(message) {
        if (!message.querySelector('.btn-close')) return; // Skip if no close button

        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(message);
            bsAlert.close();
        }, 5000);
    });

    // Add active class to current page nav links
    const currentPath = window.location.pathname;
    const navLinkElements = document.querySelectorAll('.navbar-nav .nav-link');

    navLinkElements.forEach(function(link) {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });

    // Initialize enhanced form interactions
    initializeFormEnhancements();
});

// Enhanced form interactions
function initializeFormEnhancements() {
    // Add floating label effects
    const formControls = document.querySelectorAll('.form-control, .form-select');
    formControls.forEach(input => {
        // Add focus/blur classes for enhanced styling
        input.addEventListener('focus', () => {
            input.parentElement?.classList.add('focused');
        });

        input.addEventListener('blur', () => {
            input.parentElement?.classList.remove('focused');
        });
    });

    // Enhanced validation feedback
    const forms = document.querySelectorAll('form[novalidate]');
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();

                // Focus on first invalid field
                const firstInvalid = form.querySelector(':invalid');
                if (firstInvalid) {
                    firstInvalid.focus();
                }
            }
            form.classList.add('was-validated');
        });
    });

    // Password visibility toggle
    const passwordToggles = document.querySelectorAll('.password-toggle');
    passwordToggles.forEach(toggle => {
        toggle.addEventListener('click', function() {
            const input = this.previousElementSibling;
            const icon = this.querySelector('i');

            if (input.type === 'password') {
                input.type = 'text';
                icon.classList.replace('bi-eye', 'bi-eye-slash');
            } else {
                input.type = 'password';
                icon.classList.replace('bi-eye-slash', 'bi-eye');
            }
        });
    });
}
