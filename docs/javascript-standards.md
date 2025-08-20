# JavaScript Standards and Best Practices for GMA

This document outlines the JavaScript coding standards, best practices, and quality guidelines for the Game Master Application.

## Code Quality Standards

### 1. Modern JavaScript Features

#### ES6+ Syntax
```javascript
// ✅ Use const/let instead of var
const API_ENDPOINTS = {
    THEME: '/api/profile/theme/',
};

let currentTheme = 'light';

// ✅ Arrow functions for consistency
const updateTheme = (themeName) => {
    // Implementation
};

// ✅ Template literals for string interpolation
const message = `Theme changed to ${themeName}`;

// ✅ Destructuring for cleaner code
const { currentTheme, availableThemes } = window.GMA || {};

// ✅ Default parameters
function showMessage(text, type = 'info') {
    // Implementation
}
```

#### Async/Await Pattern
```javascript
// ✅ Prefer async/await over Promises
async function fetchThemeData() {
    try {
        const response = await fetch('/api/themes/');
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Failed to fetch themes:', error);
        throw error;
    }
}

// ❌ Avoid nested Promise chains
function fetchThemeDataOld() {
    return fetch('/api/themes/')
        .then(response => response.json())
        .then(data => {
            return data;
        })
        .catch(error => {
            console.error('Failed to fetch themes:', error);
            throw error;
        });
}
```

### 2. Error Handling

#### Comprehensive Error Handling
```javascript
// ✅ Wrap risky operations in try-catch
async function safeOperation() {
    try {
        const result = await riskyOperation();
        return result;
    } catch (error) {
        console.error('Operation failed:', error);

        // Show user-friendly message
        showUserMessage('Operation failed. Please try again.', 'error');

        // Announce to screen readers
        if (window.accessibilityManager) {
            window.accessibilityManager.announce('Operation failed', 'assertive');
        }

        // Re-throw if necessary
        throw error;
    }
}

// ✅ Validate inputs
function validateThemeName(name) {
    if (!name || typeof name !== 'string') {
        throw new Error('Invalid theme name: must be a non-empty string');
    }

    if (!/^[a-zA-Z0-9-_]+$/.test(name)) {
        throw new Error('Invalid theme name: contains invalid characters');
    }

    return name.trim();
}
```

#### Safe DOM Operations
```javascript
// ✅ Safe element selection with error handling
function getElement(selector, context = document) {
    try {
        const element = context.querySelector(selector);
        if (!element) {
            console.warn(`Element not found: ${selector}`);
        }
        return element;
    } catch (error) {
        console.warn(`Invalid selector: ${selector}`, error);
        return null;
    }
}

// ✅ Safe storage operations
const SafeStorage = {
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
    }
};
```

### 3. Performance Optimization

#### Debouncing and Throttling
```javascript
// ✅ Debounce expensive operations
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func.apply(this, args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// ✅ Throttle frequent events
function throttle(func, limit) {
    let inThrottle;
    return function executedFunction(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// Usage examples
const debouncedSearch = debounce(performSearch, 300);
const throttledScroll = throttle(handleScroll, 100);
```

#### Efficient DOM Manipulation
```javascript
// ✅ Batch DOM updates
function updateMultipleElements(elements, className) {
    // Use DocumentFragment for multiple insertions
    const fragment = document.createDocumentFragment();

    elements.forEach(elementData => {
        const element = createElement(elementData);
        fragment.appendChild(element);
    });

    // Single DOM insertion
    container.appendChild(fragment);
}

// ✅ Use event delegation
function setupEventDelegation() {
    document.addEventListener('click', (e) => {
        if (e.target.matches('.theme-card')) {
            handleThemeCardClick(e);
        }

        if (e.target.matches('.delete-button')) {
            handleDeleteClick(e);
        }
    });
}
```

### 4. Accessibility Integration

#### ARIA and Screen Reader Support
```javascript
// ✅ Manage ARIA states
function updateExpandedState(element, isExpanded) {
    element.setAttribute('aria-expanded', isExpanded.toString());

    // Announce state change
    if (window.accessibilityManager) {
        const elementName = element.getAttribute('aria-label') || 'menu';
        window.accessibilityManager.announce(
            `${elementName} ${isExpanded ? 'expanded' : 'collapsed'}`
        );
    }
}

// ✅ Focus management
function trapFocusInModal(modal) {
    const focusableElements = modal.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );

    const firstFocusable = focusableElements[0];
    const lastFocusable = focusableElements[focusableElements.length - 1];

    modal.addEventListener('keydown', (e) => {
        if (e.key === 'Tab') {
            if (e.shiftKey) {
                if (document.activeElement === firstFocusable) {
                    e.preventDefault();
                    lastFocusable.focus();
                }
            } else {
                if (document.activeElement === lastFocusable) {
                    e.preventDefault();
                    firstFocusable.focus();
                }
            }
        }
    });
}
```

#### Keyboard Navigation
```javascript
// ✅ Implement arrow key navigation
function setupArrowKeyNavigation(container, itemSelector) {
    container.addEventListener('keydown', (e) => {
        const items = Array.from(container.querySelectorAll(itemSelector));
        const currentIndex = items.findIndex(item => item === document.activeElement);

        let newIndex = currentIndex;

        switch (e.key) {
            case 'ArrowLeft':
            case 'ArrowUp':
                e.preventDefault();
                newIndex = currentIndex > 0 ? currentIndex - 1 : items.length - 1;
                break;
            case 'ArrowRight':
            case 'ArrowDown':
                e.preventDefault();
                newIndex = currentIndex < items.length - 1 ? currentIndex + 1 : 0;
                break;
            case 'Home':
                e.preventDefault();
                newIndex = 0;
                break;
            case 'End':
                e.preventDefault();
                newIndex = items.length - 1;
                break;
        }

        if (newIndex !== currentIndex && items[newIndex]) {
            items[newIndex].focus();
        }
    });
}
```

### 5. Security Best Practices

#### XSS Prevention
```javascript
// ✅ Escape HTML content
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ✅ Sanitize user input
function sanitizeInput(input) {
    return input.replace(/[<>]/g, '').trim();
}

// ✅ Safe innerHTML usage
function safeSetInnerHTML(element, htmlString) {
    // Only use with trusted content
    if (typeof htmlString !== 'string') {
        console.error('HTML content must be a string');
        return;
    }

    element.innerHTML = htmlString;
}

// ✅ Prefer textContent for user data
function displayUserName(element, userName) {
    element.textContent = userName; // Safe from XSS
}
```

#### CSRF Protection
```javascript
// ✅ Include CSRF token in AJAX requests
function makeSecureRequest(url, data) {
    return fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken(),
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify(data)
    });
}

function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
           window.GMA?.csrfToken ||
           '';
}
```

### 6. Code Organization

#### Class-Based Architecture
```javascript
// ✅ Use classes for complex functionality
class FeatureManager {
    constructor(options = {}) {
        this.options = { ...this.defaultOptions, ...options };
        this.initialized = false;

        // Bind methods to maintain context
        this.handleEvent = this.handleEvent.bind(this);
    }

    get defaultOptions() {
        return {
            autoInit: true,
            debug: false
        };
    }

    async init() {
        if (this.initialized) {
            console.warn('Feature already initialized');
            return;
        }

        try {
            await this.setup();
            this.attachEventListeners();
            this.initialized = true;

            if (this.options.debug) {
                console.log('Feature initialized successfully');
            }
        } catch (error) {
            console.error('Feature initialization failed:', error);
            throw error;
        }
    }

    async setup() {
        // Override in subclasses
    }

    attachEventListeners() {
        // Override in subclasses
    }

    handleEvent(event) {
        // Common event handling logic
    }

    destroy() {
        this.removeEventListeners();
        this.initialized = false;
    }
}
```

#### Module Pattern
```javascript
// ✅ Use modules for utilities
const Utils = {
    dom: {
        getElement(selector, context = document) {
            try {
                return context.querySelector(selector);
            } catch (error) {
                console.warn(`Invalid selector: ${selector}`, error);
                return null;
            }
        },

        getElements(selector, context = document) {
            try {
                return Array.from(context.querySelectorAll(selector));
            } catch (error) {
                console.warn(`Invalid selector: ${selector}`, error);
                return [];
            }
        }
    },

    async: {
        delay(ms) {
            return new Promise(resolve => setTimeout(resolve, ms));
        },

        timeout(promise, ms) {
            return Promise.race([
                promise,
                new Promise((_, reject) =>
                    setTimeout(() => reject(new Error('Timeout')), ms)
                )
            ]);
        }
    }
};
```

### 7. Testing Considerations

#### Testable Code Structure
```javascript
// ✅ Write testable functions
function calculateTotal(items) {
    if (!Array.isArray(items)) {
        throw new Error('Items must be an array');
    }

    return items.reduce((total, item) => {
        if (typeof item.price !== 'number' || item.price < 0) {
            throw new Error('Invalid item price');
        }
        return total + item.price;
    }, 0);
}

// ✅ Dependency injection for testing
class ApiClient {
    constructor(fetcher = fetch) {
        this.fetch = fetcher;
    }

    async getData(url) {
        const response = await this.fetch(url);
        return response.json();
    }
}
```

#### Environment Detection
```javascript
// ✅ Environment-aware code
const Environment = {
    isDevelopment() {
        return window.location.hostname === 'localhost' ||
               window.location.hostname.includes('dev');
    },

    isProduction() {
        return !this.isDevelopment();
    },

    enableDebugMode() {
        return this.isDevelopment() || window.GMA?.debug;
    }
};

function log(...args) {
    if (Environment.enableDebugMode()) {
        console.log(...args);
    }
}
```

## Configuration Management

### Constants and Configuration
```javascript
// ✅ Centralized configuration
const CONFIG = {
    // Timeouts
    FETCH_TIMEOUT: 10000,
    MESSAGE_AUTO_HIDE_DELAY: 5000,
    DEBOUNCE_DELAY: 300,

    // API Endpoints
    API_ENDPOINTS: {
        THEME: '/api/profile/theme/',
        CAMPAIGNS: '/api/campaigns/',
    },

    // Storage Keys
    STORAGE_KEYS: {
        AUTO_THEME_SWITCH: 'gma-auto-theme-switch',
        USER_PREFERENCES: 'gma-user-preferences',
    },

    // CSS Classes
    CSS_CLASSES: {
        FOCUSED: 'focused',
        VALIDATED: 'was-validated',
        BORDER_PRIMARY: 'border-primary',
    },

    // ARIA Attributes
    ARIA_ATTRIBUTES: {
        EXPANDED: 'aria-expanded',
        SELECTED: 'aria-selected',
        DESCRIBEDBY: 'aria-describedby',
    }
};
```

## Linting and Code Quality

### ESLint Configuration
```javascript
// .eslintrc.js
module.exports = {
    env: {
        browser: true,
        es2021: true
    },
    extends: [
        'eslint:recommended'
    ],
    parserOptions: {
        ecmaVersion: 12,
        sourceType: 'module'
    },
    rules: {
        'no-console': 'warn',
        'no-unused-vars': 'error',
        'prefer-const': 'error',
        'no-var': 'error',
        'prefer-arrow-callback': 'error',
        'prefer-template': 'error',
        'no-eval': 'error',
        'no-implied-eval': 'error',
        'no-new-func': 'error',
        'strict': ['error', 'function']
    }
};
```

### Code Quality Checklist

#### ✅ Required Standards
- [ ] Use `const`/`let` instead of `var`
- [ ] Implement proper error handling with try-catch
- [ ] Use async/await instead of Promise chains
- [ ] Escape user input to prevent XSS
- [ ] Include CSRF tokens in AJAX requests
- [ ] Implement debouncing for expensive operations
- [ ] Add accessibility attributes and screen reader support
- [ ] Use semantic function and variable names
- [ ] Include JSDoc comments for complex functions
- [ ] Validate function parameters
- [ ] Handle edge cases and null/undefined values

#### ✅ Performance Standards
- [ ] Debounce user input handlers
- [ ] Throttle scroll and resize handlers
- [ ] Use event delegation for dynamic content
- [ ] Batch DOM updates
- [ ] Cache DOM queries
- [ ] Implement request timeouts
- [ ] Use appropriate data structures
- [ ] Avoid memory leaks by removing event listeners

#### ✅ Accessibility Standards
- [ ] Support keyboard navigation
- [ ] Announce dynamic changes to screen readers
- [ ] Manage focus appropriately
- [ ] Use ARIA attributes correctly
- [ ] Provide alternative text for dynamic content
- [ ] Ensure minimum contrast ratios
- [ ] Support reduced motion preferences

## Common Anti-Patterns to Avoid

### ❌ Don't Do This
```javascript
// ❌ Using var
var theme = 'light';

// ❌ Not handling errors
function switchTheme(name) {
    fetch('/api/theme/', { method: 'POST' });
}

// ❌ Inline event handlers
<button onclick="doSomething()">Click me</button>

// ❌ Global pollution
window.myFunction = function() {};

// ❌ Not escaping user input
element.innerHTML = userInput;

// ❌ Blocking the main thread
for (let i = 0; i < 1000000; i++) {
    // Heavy computation
}
```

### ✅ Do This Instead
```javascript
// ✅ Use const/let
const theme = 'light';

// ✅ Handle errors properly
async function switchTheme(name) {
    try {
        const response = await fetch('/api/theme/', {
            method: 'POST',
            body: JSON.stringify({ theme: name })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('Theme switch failed:', error);
        showMessage('Failed to change theme', 'error');
        throw error;
    }
}

// ✅ Use event listeners
button.addEventListener('click', handleClick);

// ✅ Use modules/classes
class ThemeManager {
    switchTheme(name) {
        // Implementation
    }
}

// ✅ Escape user input
element.textContent = userInput;

// ✅ Use Web Workers for heavy computation
const worker = new Worker('heavy-computation.js');
worker.postMessage(data);
```

## Integration with Django

### CSRF Token Handling
```javascript
// Get CSRF token from various sources
function getCSRFToken() {
    // Try meta tag first
    const metaToken = document.querySelector('meta[name="csrf-token"]')?.content;
    if (metaToken) return metaToken;

    // Try form input
    const formToken = document.querySelector('[name="csrfmiddlewaretoken"]')?.value;
    if (formToken) return formToken;

    // Try global variable
    return window.GMA?.csrfToken || '';
}

// Include in all AJAX requests
function makeRequest(url, data) {
    return fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken(),
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify(data)
    });
}
```

### Template Integration
```html
<!-- Pass data safely to JavaScript -->
<script>
window.GMA = {
    currentTheme: '{{ user_theme|escapejs }}',
    isAuthenticated: {{ user.is_authenticated|yesno:"true,false" }},
    csrfToken: '{{ csrf_token|escapejs }}',
    apiEndpoints: {
        theme: '{% url "api:profile:theme" %}'
    }
};
</script>
```

This document serves as a comprehensive guide for maintaining high-quality, secure, and accessible JavaScript code in the GMA project.
