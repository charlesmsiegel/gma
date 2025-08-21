/* Location Management JavaScript */

document.addEventListener('DOMContentLoaded', function() {
    // Location List Page - Auto-submit form on filter changes
    const filterForm = document.querySelector('.search-filters form');
    const ownerSelect = document.getElementById('owner');
    const unownedCheckbox = document.getElementById('unowned');

    if (ownerSelect) {
        ownerSelect.addEventListener('change', function() {
            filterForm.submit();
        });
    }

    if (unownedCheckbox) {
        unownedCheckbox.addEventListener('change', function() {
            filterForm.submit();
        });
    }

    // Clear other filters when unowned is checked
    if (unownedCheckbox && ownerSelect) {
        unownedCheckbox.addEventListener('change', function() {
            if (this.checked) {
                ownerSelect.value = '';
            }
        });

        ownerSelect.addEventListener('change', function() {
            if (this.value) {
                unownedCheckbox.checked = false;
            }
        });
    }

    // Location Form Page - Hierarchy Preview
    const parentSelect = document.getElementById('id_parent');
    const hierarchyPreview = document.getElementById('hierarchy-preview');
    const hierarchyPath = document.getElementById('hierarchy-path');
    const nameInput = document.getElementById('id_name');

    if (parentSelect && hierarchyPreview && hierarchyPath && nameInput) {
        // Location hierarchy data (populated from Django context)
        const locationHierarchy = window.locationHierarchy || {};

        function updateHierarchyPreview() {
            const selectedParentId = parentSelect.value;
            const locationName = nameInput.value || '[New Location]';

            if (selectedParentId && locationHierarchy[selectedParentId]) {
                const parentPath = locationHierarchy[selectedParentId];
                hierarchyPath.textContent = parentPath + ' > ' + locationName;
                hierarchyPreview.style.display = 'block';
            } else if (selectedParentId === '') {
                hierarchyPath.textContent = locationName + ' (Root Level)';
                hierarchyPreview.style.display = 'block';
            } else {
                hierarchyPreview.style.display = 'none';
            }
        }

        // Update preview when parent or name changes
        parentSelect.addEventListener('change', updateHierarchyPreview);
        nameInput.addEventListener('input', updateHierarchyPreview);

        // Initial preview update
        updateHierarchyPreview();

        // Handle URL parent parameter for pre-selecting parent
        const urlParams = new URLSearchParams(window.location.search);
        const parentParam = urlParams.get('parent');
        if (parentParam) {
            parentSelect.value = parentParam;
            updateHierarchyPreview();
        }
    }

    // Form validation for location forms
    const form = document.querySelector('form');
    if (form && nameInput) {
        form.addEventListener('submit', function(event) {
            const nameValue = nameInput.value.trim();
            if (!nameValue) {
                event.preventDefault();
                nameInput.focus();
                nameInput.classList.add('is-invalid');

                // Show error message
                let errorDiv = nameInput.parentNode.querySelector('.invalid-feedback');
                if (!errorDiv) {
                    errorDiv = document.createElement('div');
                    errorDiv.className = 'invalid-feedback d-block';
                    nameInput.parentNode.appendChild(errorDiv);
                }
                errorDiv.textContent = 'Location name is required.';
            } else {
                nameInput.classList.remove('is-invalid');
            }
        });

        // Remove error styling when user starts typing
        nameInput.addEventListener('input', function() {
            this.classList.remove('is-invalid');
            const errorDiv = this.parentNode.querySelector('.invalid-feedback');
            if (errorDiv && !errorDiv.textContent.includes('This field is required')) {
                errorDiv.remove();
            }
        });
    }
});
