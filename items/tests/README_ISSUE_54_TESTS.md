# Issue #54: Item Management Interface Tests

This document outlines the comprehensive test suite created for Issue #54: Implement Item Management Interface. These tests follow TDD principles and will validate the implementation when the features are built.

## Test Files Created

### 1. test_views.py - Web Interface View Testing
**Location**: `/home/janothar/gma/items/tests/test_views.py`

**Coverage**: 5 main test classes with 55+ individual test methods

#### ItemCreateViewTest (13 test methods)
- Authentication requirement testing
- Permission-based access control (OWNER/GM can create, PLAYER/OBSERVER cannot)
- Form display validation
- Successful item creation with minimal and full data
- Form validation error handling
- Campaign context validation
- Cross-role permission testing

#### ItemDetailViewTest (14 test methods)
- Authentication requirement testing
- Permission-based viewing (all campaign members can view)
- Complete item information display
- Edit/Delete button visibility based on permissions
- Character ownership integration
- Unowned item handling

#### ItemEditViewTest (13 test methods)
- Authentication and permission testing
- Pre-populated form validation
- Successful item updates
- Ownership transfer functionality with timestamp tracking
- Form validation on edit
- Permission matrix validation across all roles

#### ItemListViewTest (14 test methods)
- Complete item listing
- Search functionality (by name and description)
- Filtering by character owner
- Unowned item filtering
- Pagination support
- Permission-based action button visibility
- Combined search and filter operations
- Empty results handling
- Case-insensitive search

#### ItemDeleteViewTest (8 test methods)
- Permission-based deletion (OWNER/GM/creator can delete)
- Soft delete validation
- HTTP method requirements (POST only)
- Confirmation messaging
- Permission matrix validation

### 2. test_forms.py - Form Validation Testing
**Location**: `/home/janothar/gma/items/tests/test_forms.py`

**Coverage**: 1 main test class with 20+ test methods

#### ItemFormTest (20 test methods)
- Valid form data testing (minimal and complete)
- Required field validation
- Field constraint validation (quantity >= 1)
- Optional field handling
- Campaign-scoped character owner filtering
- Form save method behavior
- Character ownership assignment
- Cross-campaign security validation
- Field length and type validation
- Widget and HTML attribute testing
- Custom clean method validation
- Error message appropriateness
- Form initialization requirements
- Field ordering and help text

### 3. test_integration.py - Cross-App Integration Testing
**Location**: `/home/janothar/gma/items/tests/test_integration.py`

**Coverage**: 4 main test classes with 25+ integration scenarios

#### ItemCampaignIntegrationTest (4 test methods)
- Campaign detail page item management links
- Item count display in campaign overview
- Navigation flow from campaign to items
- Breadcrumb navigation back to campaign

#### ItemCharacterIntegrationTest (6 test methods)
- Character detail page possession display
- Item quantity display in character context
- Character-to-item detail page linking
- Character-based item filtering
- Character deletion impact on item ownership

#### ItemURLPatternsTest (6 test methods)
- URL pattern correctness and routing
- Invalid parameter handling (404 responses)
- URL namespace verification
- Campaign slug and item ID validation

#### ItemWorkflowIntegrationTest (4 test methods)
- Complete end-to-end workflows (create → view → edit → transfer → delete)
- GM-specific workflow testing
- Player read-only workflow validation
- Cross-campaign isolation verification

## Test Design Principles

### 1. Test-Driven Development (TDD)
- All tests are written **before** implementation
- Tests will initially **fail** until features are implemented
- Red-Green-Refactor cycle support

### 2. Permission Matrix Coverage
Every test validates the complete permission hierarchy:
- **OWNER**: Full CRUD access to all campaign items
- **GM**: Full CRUD access to all campaign items  
- **PLAYER**: Read-only access to all items, can view details
- **OBSERVER**: Read-only access to all items, can view details
- **NON-MEMBER**: No access (404 responses)
- **ITEM CREATOR**: Can always delete their own items

### 3. Security-First Testing
- All unauthorized access returns 404 (not 403) to hide resource existence
- Cross-campaign isolation validation
- CSRF protection verification
- Input validation and sanitization

### 4. Edge Case Coverage
- Empty search results
- Unowned items handling
- Character deletion impact
- Form validation edge cases
- URL parameter validation
- Database constraint validation

## Expected URL Patterns (To Be Implemented)

Based on the test structure, the following URL patterns are expected:

```python
# items/urls/__init__.py
urlpatterns = [
    # Existing
    path("campaigns/<slug:campaign_slug>/", CampaignItemsView.as_view(), name="campaign_items"),
    
    # New patterns needed
    path("campaigns/<slug:campaign_slug>/create/", ItemCreateView.as_view(), name="create"),
    path("campaigns/<slug:campaign_slug>/<int:item_id>/", ItemDetailView.as_view(), name="detail"),
    path("campaigns/<slug:campaign_slug>/<int:item_id>/edit/", ItemEditView.as_view(), name="edit"),
    path("campaigns/<slug:campaign_slug>/<int:item_id>/delete/", ItemDeleteView.as_view(), name="delete"),
]
```

## Expected Form Structure (To Be Implemented)

The tests expect an `ItemForm` class with:
- Campaign parameter for character owner filtering
- Support for both create and edit modes
- Proper field validation and widgets
- Transfer timestamp handling on ownership changes

## Template Requirements

Based on test assertions, templates should include:
- Form fields with proper names and attributes
- Permission-based button visibility
- Comprehensive item information display
- Search and filter interfaces
- Pagination controls
- Breadcrumb navigation

## Database Requirements

All tests use the existing Item model with:
- Single character ownership (owner field)
- Transfer timestamp tracking (last_transferred_at)
- Soft delete functionality
- Campaign association
- Audit trails (created_by, modified_by)

## Running the Tests

The tests are integrated into the existing test suite:

```bash
# Run all item tests
make test

# Run specific test files
python manage.py test items.tests.test_views
python manage.py test items.tests.test_forms  
python manage.py test items.tests.test_integration

# Run with coverage
make test-coverage
```

## Test Status

- ✅ **test_views.py**: 55+ tests created, syntax validated
- ✅ **test_forms.py**: 20+ tests created, syntax validated  
- ✅ **test_integration.py**: 25+ tests created, syntax validated
- ✅ **Test discovery**: Integrated with existing test suite
- ❌ **Implementation**: Views, forms, templates, and URLs need to be created

## Next Steps

1. **Create Forms**: Implement `items/forms.py` with `ItemForm` class
2. **Create Views**: Implement view classes in `items/views/`
3. **Create Templates**: Build HTML templates for all views
4. **Update URLs**: Add new URL patterns to `items/urls/__init__.py`
5. **Integration**: Ensure campaign and character integration works
6. **Test Validation**: Run tests to ensure they pass with implementation

The comprehensive test suite provides a clear specification for the Item Management Interface implementation and ensures all requirements from Issue #54 are thoroughly validated.