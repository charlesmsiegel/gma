# Accessibility Guidelines for GMA

This document provides comprehensive accessibility guidelines for the Game Master Application to ensure WCAG 2.1 AA compliance and inclusive design.

## Quick Reference Checklist

### ✅ Essential Elements

- [ ] All images have descriptive `alt` attributes
- [ ] Form controls have proper labels (`<label>` or `aria-label`)
- [ ] Page has proper heading hierarchy (h1 → h2 → h3)
- [ ] Skip navigation link is present
- [ ] Focus indicators are visible and high contrast
- [ ] Color is not the only way to convey information
- [ ] All interactive elements are keyboard accessible
- [ ] ARIA live regions announce dynamic content changes

### ✅ Form Accessibility

- [ ] All form fields have associated labels
- [ ] Required fields are marked with `required` attribute and asterisk
- [ ] Error messages are associated with fields using `aria-describedby`
- [ ] Validation errors are announced to screen readers
- [ ] Fieldsets are used for related form groups
- [ ] Form submission results are announced

### ✅ Navigation Accessibility

- [ ] Main navigation has `role="navigation"` or `<nav>` element
- [ ] Current page is indicated with `aria-current="page"`
- [ ] Breadcrumbs use proper `aria-label` on nav element
- [ ] Skip links allow bypassing repetitive navigation

### ✅ Interactive Elements

- [ ] Buttons have descriptive text or `aria-label`
- [ ] Links have meaningful text (not "click here")
- [ ] Dropdown menus use proper `aria-expanded` states
- [ ] Modal dialogs trap focus and have proper `role="dialog"`
- [ ] Tables have proper column/row headers with `scope` attributes

## Implementation Guide

### 1. HTML Structure

```html
<!-- Proper document structure -->
<!DOCTYPE html>
<html lang="en">
<head>
  <title>Descriptive Page Title - GMA</title>
</head>
<body>
  <!-- Skip navigation -->
  <a href="#main-content" class="skip-nav">Skip to main content</a>

  <!-- Main navigation -->
  <nav role="navigation" aria-label="Main navigation">
    <!-- Navigation items -->
  </nav>

  <!-- Main content area -->
  <main id="main-content" tabindex="-1">
    <h1>Page Title</h1>
    <!-- Page content -->
  </main>

  <!-- Footer -->
  <footer role="contentinfo">
    <!-- Footer content -->
  </footer>
</body>
</html>
```

### 2. Form Accessibility

```html
<!-- Accessible form example -->
<form novalidate>
  <fieldset>
    <legend>Character Information</legend>

    <div class="mb-3">
      <label for="char-name" class="form-label">
        Character Name <span class="required">*</span>
      </label>
      <input type="text"
             id="char-name"
             name="name"
             class="form-control"
             required
             aria-describedby="char-name-error char-name-help">
      <small id="char-name-help" class="form-text text-muted">
        Enter a unique name for your character
      </small>
      <div id="char-name-error" class="invalid-feedback" role="alert">
        <!-- Error message will be inserted here -->
      </div>
    </div>
  </fieldset>

  <button type="submit" class="btn btn-primary">
    Create Character
  </button>
</form>
```

### 3. Data Tables

```html
<table class="table">
  <caption class="sr-only">List of campaign characters</caption>
  <thead>
    <tr>
      <th scope="col">Character Name</th>
      <th scope="col">Player</th>
      <th scope="col">Status</th>
      <th scope="col">Actions</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th scope="row">Character Name</th>
      <td>Player Name</td>
      <td>
        <span class="badge bg-success" role="img" aria-label="Active character">
          Active
        </span>
      </td>
      <td>
        <button class="btn btn-sm btn-outline-primary"
                aria-label="Edit Character Name">
          <i class="bi bi-pencil" aria-hidden="true"></i>
          Edit
        </button>
      </td>
    </tr>
  </tbody>
</table>
```

### 4. Modal Dialogs

```html
<div class="modal fade"
     id="deleteModal"
     tabindex="-1"
     aria-labelledby="deleteModalLabel"
     aria-hidden="true">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title" id="deleteModalLabel">
          Confirm Character Deletion
        </h5>
        <button type="button"
                class="btn-close"
                data-bs-dismiss="modal"
                aria-label="Close dialog">
        </button>
      </div>
      <div class="modal-body">
        <p>Are you sure you want to delete this character? This action cannot be undone.</p>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
          Cancel
        </button>
        <button type="button" class="btn btn-danger">
          Delete Character
        </button>
      </div>
    </div>
  </div>
</div>
```

### 5. ARIA Live Regions

```html
<!-- Status announcements -->
<div id="aria-live-polite" aria-live="polite" aria-atomic="false" class="sr-only"></div>
<div id="aria-live-assertive" aria-live="assertive" aria-atomic="true" class="sr-only"></div>

<script>
// Announce form submission results
function announceFormResult(message, priority = 'polite') {
  const regionId = priority === 'assertive' ? 'aria-live-assertive' : 'aria-live-polite';
  const region = document.getElementById(regionId);
  region.textContent = message;
  setTimeout(() => region.textContent = '', 1000);
}
</script>
```

## CSS Accessibility Features

### Focus Management

```css
/* Enhanced focus indicators */
*:focus {
  outline: 2px solid var(--bs-primary);
  outline-offset: 2px;
}

.btn:focus {
  outline: 3px solid var(--bs-warning);
  box-shadow: 0 0 0 4px rgba(255, 193, 7, 0.25);
}
```

### High Contrast Support

```css
@media (prefers-contrast: high) {
  .btn {
    border-width: 2px;
  }
  .form-control {
    border-width: 2px;
  }
}
```

### Reduced Motion Support

```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

## JavaScript Accessibility

### Dynamic Content Updates

```javascript
// Announce dynamic content changes
function updateContent(element, newContent) {
  element.innerHTML = newContent;

  // Announce the change
  window.accessibilityManager.announce('Content updated');
}

// Loading states
function setLoadingState(element, isLoading) {
  if (isLoading) {
    element.setAttribute('aria-busy', 'true');
    window.accessibilityManager.announce('Loading...');
  } else {
    element.removeAttribute('aria-busy');
    window.accessibilityManager.announce('Loading complete');
  }
}
```

### Keyboard Navigation

```javascript
// Custom keyboard handlers
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    // Close open dropdowns/modals
    closeAllDropdowns();
  }

  if (e.key === 'Enter' || e.key === ' ') {
    // Handle custom button activation
    handleCustomButtonActivation(e);
  }
});
```

## Testing Checklist

### Automated Testing

- [ ] Run axe-core accessibility scanner
- [ ] Validate HTML markup
- [ ] Test color contrast ratios (4.5:1 for normal text, 3:1 for large text)
- [ ] Verify focus order with tab navigation

### Manual Testing

- [ ] Navigate entire site using only keyboard
- [ ] Test with screen reader (NVDA, JAWS, VoiceOver)
- [ ] Verify at 200% zoom level
- [ ] Test with Windows High Contrast mode
- [ ] Verify with JavaScript disabled

### Screen Reader Testing Commands

#### NVDA (Windows)
- `NVDA + Space`: Toggle between browse and focus mode
- `H`: Navigate by headings
- `F`: Navigate by form fields
- `B`: Navigate by buttons
- `L`: Navigate by links

#### VoiceOver (macOS)
- `Control + Option + →`: Navigate forward
- `Control + Option + ←`: Navigate backward
- `Control + Option + U`: Open rotor (navigation menu)

## Common Accessibility Issues to Avoid

### ❌ Don't Do This

```html
<!-- Missing alt text -->
<img src="character.jpg">

<!-- Meaningless link text -->
<a href="/character/1">Click here</a>

<!-- Missing label -->
<input type="text" placeholder="Character name">

<!-- Color-only indication -->
<span style="color: red;">Error</span>

<!-- Inaccessible dropdown -->
<div class="dropdown" onclick="toggleDropdown()">Menu</div>
```

### ✅ Do This Instead

```html
<!-- Descriptive alt text -->
<img src="character.jpg" alt="Gandalf the Grey, wizard character">

<!-- Meaningful link text -->
<a href="/character/1">View Gandalf character details</a>

<!-- Proper label -->
<label for="char-name">Character Name</label>
<input type="text" id="char-name" placeholder="e.g., Gandalf">

<!-- Multiple indicators -->
<span class="text-danger" role="alert">
  <i class="bi bi-exclamation-triangle" aria-hidden="true"></i>
  Error: Invalid character name
</span>

<!-- Accessible dropdown -->
<button class="dropdown-toggle"
        aria-expanded="false"
        aria-haspopup="true">
  Menu
</button>
```

## Integration with GMA

### Template Updates Required

1. **base.html**: Add skip navigation and main content landmark
2. **forms**: Add proper labels and error announcements
3. **tables**: Add caption and scope attributes
4. **modals**: Ensure focus management and ARIA attributes
5. **navigation**: Add current page indicators

### CSS Integration

```html
<!-- Add to base.html -->
<link rel="stylesheet" href="{% static 'css/accessibility.css' %}">
```

### JavaScript Integration

```html
<!-- Add to base.html -->
<script src="{% static 'js/accessibility.js' %}"></script>
```

## Accessibility Statement Template

```html
<!-- Add to footer or dedicated page -->
<p>
  We are committed to ensuring digital accessibility for all users.
  If you encounter any accessibility barriers, please contact us at
  <a href="mailto:accessibility@gma.com">accessibility@gma.com</a>.
</p>
```

## Resources

- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [WebAIM Screen Reader Testing](https://webaim.org/articles/screenreader_testing/)
- [axe-core Accessibility Testing](https://github.com/dequelabs/axe-core)
- [Bootstrap Accessibility](https://getbootstrap.com/docs/5.3/getting-started/accessibility/)
- [ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/)
