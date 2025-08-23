# Game Master Application - Project Files

This document provides a comprehensive list of all active project files with their roles in the system.

## Root Configuration Files

- `CLAUDE.md` - Project instructions and development guidelines for Claude Code AI assistant
- `COMPREHENSIVE_PLAN.md` - Comprehensive project planning and feature implementation roadmap
- `codecov.yml` - Code coverage reporting configuration for continuous integration
- `environment.yml` - Conda environment specification with all Python dependencies
- `FILES.md` - This comprehensive project file structure documentation
- `Makefile` - Development automation commands for testing, building, and deployment
- `manage.py` - Django's main command-line utility for administrative tasks
- `package.json` - Node.js package configuration for frontend development tooling
- `PHASE_1_ISSUES_ORDER.md` - Phase 1 development issues and implementation order
- `pyproject.toml` - Python project metadata and build system configuration
- `README.md` - Project overview, installation instructions, and basic usage guide
- `.stylelintrc.json` - Stylelint configuration for CSS code quality and standards

## Django Project Configuration

### gm_app/ (Main Django Project)

- `gm_app/__init__.py` - Python package initialization for the main Django project
- `gm_app/asgi.py` - ASGI configuration for async Django applications and WebSocket support
- `gm_app/secrets.py` - Sensitive configuration values like API keys and database credentials
- `gm_app/settings.py` - Main Django settings configuration with database, middleware, and app settings
- `gm_app/test_settings.py` - Specialized Django settings optimized for testing environment
- `gm_app/urls.py` - Root URL configuration that routes requests to appropriate Django apps
- `gm_app/wsgi.py` - WSGI configuration for deploying Django with traditional web servers

## Django Applications

### api/ (REST API Layer)

- `api/__init__.py` - Python package initialization for the API application
- `api/admin.py` - Django admin interface configuration for API models (currently empty)
- `api/apps.py` - Django application configuration defining the API app settings
- `api/authentication.py` - Custom authentication backends and token handling for API security
- `api/errors.py` - Standardized error response handlers and security-focused error messages
- `api/serializers.py` - Django REST Framework serializers for converting models to JSON
- `api/migrations/__init__.py` - Database migrations package initialization for API models

#### API Models

- `api/models/__init__.py` - API-specific model definitions package (currently placeholder)

#### API Tests

- `api/tests/__init__.py` - Test package initialization for API test modules
- `api/tests/test_auth_api.py` - Authentication API endpoint tests including login and registration
- `api/tests/test_auth_integration.py` - Integration tests for authentication workflow and edge cases
- `api/tests/test_character_api_base.py` - Base character API functionality tests
- `api/tests/test_character_api_crud.py` - Character CRUD operations API tests
- `api/tests/test_character_api_list.py` - Character listing and filtering API tests
- `api/tests/test_character_api_specialized.py` - Specialized character API tests with polymorphic support
- `api/tests/test_location_api_base.py` - Base location API functionality tests
- `api/tests/test_location_api_bulk.py` - Bulk location operations API tests
- `api/tests/test_location_api_crud.py` - Location CRUD operations API tests
- `api/tests/test_location_api_filtering.py` - Location filtering and search API tests
- `api/tests/test_location_api_hierarchy.py` - Location hierarchy management API tests
- `api/tests/test_error_handling.py` - Error response format and security leak prevention tests
- `api/tests/test_frontend_integration_patterns.py` - Tests ensuring API compatibility with React frontend
- `api/tests/test_security.py` - Security vulnerability tests including XSS and injection prevention

#### API URLs

- `api/urls/__init__.py` - URL routing package initialization for modular API endpoints
- `api/urls/auth_urls.py` - Authentication-related URL patterns for login, logout, and registration
- `api/urls/campaign_urls.py` - Campaign management URL patterns for CRUD operations
- `api/urls/character_urls.py` - Character management URL patterns with polymorphic support
- `api/urls/invitation_urls.py` - Campaign invitation URL patterns for membership management
- `api/urls/location_urls.py` - Location management URL patterns for CRUD and hierarchy operations
- `api/urls/notification_urls.py` - Real-time notification URL patterns for user alerts
- `api/urls/profile_urls.py` - User profile management URL patterns for account settings

#### API Views

- `api/views/__init__.py` - View package initialization for modular API view organization
- `api/views/auth_views.py` - Authentication view classes handling login, logout, and registration
- `api/views/character_views.py` - Character CRUD operations with polymorphic model support
- `api/views/notification_views.py` - Real-time notification management and delivery views
- `api/views/profile_views.py` - User profile editing and theme management views

##### Location Views

- `api/views/locations/__init__.py` - Location-related views package initialization
- `api/views/locations/bulk_views.py` - Bulk location operations for hierarchy management
- `api/views/locations/crud_views.py` - Location CRUD operations with hierarchy support

##### Campaign Views

- `api/views/campaigns/__init__.py` - Campaign-related views package initialization
- `api/views/campaigns/invitation_views.py` - Campaign invitation management API endpoints
- `api/views/campaigns/list_views.py` - Campaign listing and filtering API endpoints
- `api/views/campaigns/search_views.py` - User search functionality for campaign invitations

##### Membership Views

- `api/views/memberships/__init__.py` - Membership management views package initialization
- `api/views/memberships/bulk_views.py` - Bulk membership operations for campaign management
- `api/views/memberships/member_views.py` - Individual member management and role assignment

### campaigns/ (Campaign Management)

- `campaigns/__init__.py` - Python package initialization for the campaigns application
- `campaigns/admin.py` - Django admin interface configuration for campaign models
- `campaigns/apps.py` - Django application configuration for campaigns app settings
- `campaigns/forms.py` - Django forms for campaign creation, editing, and member management
- `campaigns/mixins.py` - Reusable view mixins for campaign permission checking and management
- `campaigns/permissions.py` - Campaign-specific permission classes and role-based access control
- `campaigns/services.py` - Business logic layer for complex campaign operations and workflows
- `campaigns/migrations/__init__.py` - Database migrations package for campaign model changes
- `campaigns/PERMISSIONS.md` - Documentation of campaign permission system and role hierarchy

#### Campaign Models

- `campaigns/models/__init__.py` - Campaign models package initialization
- `campaigns/models/campaign.py` - Campaign, membership, and invitation model definitions with business logic

#### Campaign Static Files

- `campaigns/static/campaigns/css/campaign_detail.css` - Styling for campaign detail page layout and components
- `campaigns/static/campaigns/css/campaign_list.css` - Styling for campaign listing page with filtering
- `campaigns/static/campaigns/css/coming_soon.css` - Placeholder styling for upcoming campaign features

#### Campaign Templates

- `campaigns/templates/campaigns/bulk_member_management.html` - Template for bulk member operations interface
- `campaigns/templates/campaigns/campaign_create.html` - Campaign creation form template with validation
- `campaigns/templates/campaigns/campaign_detail.html` - Detailed campaign view with management controls
- `campaigns/templates/campaigns/campaign_list.html` - Campaign listing with search and filter options
- `campaigns/templates/campaigns/campaign_settings.html` - Campaign configuration and privacy settings form
- `campaigns/templates/campaigns/change_member_role.html` - Member role modification interface template
- `campaigns/templates/campaigns/invitations.html` - Campaign invitation management interface template
- `campaigns/templates/campaigns/manage_members.html` - Member management dashboard template
- `campaigns/templates/campaigns/send_invitation.html` - New invitation creation form template

#### Campaign Tests

- `campaigns/tests/__init__.py` - Test package initialization for campaign test modules
- `campaigns/tests/test_admin.py` - Django admin interface tests for campaign management
- `campaigns/tests/test_api.py` - Campaign API endpoint tests with permission validation
- `campaigns/tests/test_campaign_membership.py` - Campaign membership model and business logic tests
- `campaigns/tests/test_campaign_settings.py` - Campaign configuration and settings functionality tests
- `campaigns/tests/test_edge_cases.py` - Edge case handling tests for campaign operations
- `campaigns/tests/test_edge_cases_error_handling.py` - Error handling tests for exceptional scenarios
- `campaigns/tests/test_integration.py` - Integration tests for complete campaign workflows
- `campaigns/tests/test_invitation_models.py` - Campaign invitation model and lifecycle tests
- `campaigns/tests/test_membership_api.py` - Membership management API endpoint tests
- `campaigns/tests/test_models.py` - Campaign model validation and business logic tests
- `campaigns/tests/test_permission_validation.py` - Permission system validation and security tests
- `campaigns/tests/test_permissions.py` - Role-based access control tests for campaign features
- `campaigns/tests/test_user_search_api.py` - User search functionality tests with security validation
- `campaigns/tests/test_views.py` - Campaign view tests including template rendering and permissions
- `campaigns/tests/test_web_interface_integration.py` - Web interface integration tests for campaign features

#### Campaign URLs and Views

- `campaigns/urls/__init__.py` - URL routing package for campaign-related endpoints
- `campaigns/views/__init__.py` - View package initialization for campaign view modules
- `campaigns/views/campaign_views.py` - Campaign CRUD operations and detail views
- `campaigns/views/invitation_views.py` - Campaign invitation management views
- `campaigns/views/member_views.py` - Campaign member management and role assignment views

### characters/ (Character Management)

- `characters/__init__.py` - Python package initialization for the characters application
- `characters/admin.py` - Django admin interface configuration for character models
- `characters/apps.py` - Django application configuration for characters app settings
- `characters/forms.py` - Django forms for character creation, editing, and validation
- `characters/migrations/__init__.py` - Database migrations package for character model changes

#### Character Models

- `characters/models/__init__.py` - Character model definitions with polymorphic inheritance support

#### Character Tests

- `characters/tests/__init__.py` - Test package initialization for character test modules
- `characters/tests/test_character_create_forms.py` - Character creation form validation and submission tests
- `characters/tests/test_character_delete_forms.py` - Character deletion form and confirmation tests
- `characters/tests/test_character_edit_forms.py` - Character editing form validation tests
- `characters/tests/test_fsm_basic.py` - Character finite state machine functionality tests
- `characters/tests/test_mixin_application.py` - Character model mixin application tests
- `characters/tests/test_models.py` - Character model tests with polymorphic inheritance validation
- `characters/tests/test_owned_locations.py` - Character location ownership functionality tests
- `characters/tests/test_views.py` - Character view tests including CRUD operations and permissions

#### Character URLs and Views

- `characters/urls/__init__.py` - URL routing package for character-related endpoints
- `characters/views/__init__.py` - View package initialization for character view modules
- `characters/views/edit_delete.py` - Character editing and deletion views with permission checks

### core/ (Core Application)

- `core/__init__.py` - Python package initialization for the core application
- `core/admin.py` - Django admin interface configuration for core models
- `core/apps.py` - Django application configuration for core app settings
- `core/consumers.py` - WebSocket consumer classes for real-time communication features
- `core/mixins.py` - Reusable view mixins and utility classes for common functionality
- `core/routing.py` - WebSocket URL routing configuration for real-time features
- `core/migrations/__init__.py` - Database migrations package for core model changes

#### Core Management Commands

- `core/management/__init__.py` - Management commands package initialization
- `core/management/commands/__init__.py` - Custom Django management commands package initialization
- `core/management/commands/create_test_data.py` - Command to generate test data for development
- `core/management/commands/health_check.py` - System health monitoring command for database and Redis
- `core/management/commands/reset_dev_db.py` - Development database reset and initialization command

#### Core Models

- `core/models/__init__.py` - Core model package initialization
- `core/models/health_check.py` - Health check logging model for system monitoring
- `core/models/mixins.py` - Reusable model mixins for common functionality across all apps
- `core/models/sources.py` - Source reference models for book and supplement tracking

#### Core Tests

- `core/tests/__init__.py` - Test package initialization for core test modules
- `core/tests/README_migration_strategy.md` - Documentation for migration testing strategy
- `core/tests/test_book_model.py` - Book model functionality and validation tests
- `core/tests/test_dev_management.py` - Development management command tests
- `core/tests/test_django_fsm_installation.py` - Django FSM state machine integration tests
- `core/tests/test_health_check.py` - Health check functionality and logging tests
- `core/tests/test_migration_strategy.py` - Database migration safety and rollback tests
- `core/tests/test_mixin_cross_model_consistency.py` - Cross-model mixin consistency tests
- `core/tests/test_mixin_functionality_preservation.py` - Mixin functionality preservation tests
- `core/tests/test_mixin_migration_compatibility.py` - Mixin migration compatibility tests
- `core/tests/test_mixin_migration_simple.py` - Simple mixin migration tests
- `core/tests/test_mixins.py` - Core mixin functionality tests
- `core/tests/test_source_reference_database.py` - Source reference database integration tests
- `core/tests/test_source_reference_edge_cases.py` - Source reference edge case handling tests
- `core/tests/test_source_reference_models.py` - Source reference model validation tests
- `core/tests/test_source_reference_relationships.py` - Source reference relationship tests
- `core/tests/test_websocket.py` - WebSocket connection and real-time communication tests

#### Core URLs and Views

- `core/urls/__init__.py` - URL routing package for core application endpoints
- `core/views/__init__.py` - View package for core application views (home page, etc.)

### users/ (User Management)

- `users/__init__.py` - Python package initialization for the users application
- `users/admin.py` - Django admin interface configuration for user models
- `users/apps.py` - Django application configuration for users app settings
- `users/context_processors.py` - Template context processors for user-related data
- `users/forms.py` - Django forms for user registration, profile editing, and authentication
- `users/utils.py` - Utility functions for user-related operations and validations
- `users/migrations/__init__.py` - Database migrations package for user model changes

#### User Management Commands

- `users/management/__init__.py` - Management commands package initialization
- `users/management/commands/__init__.py` - User management commands package initialization
- `users/management/commands/populate_themes.py` - Command to populate theme system with default themes

#### User Models

- `users/models/__init__.py` - User models package initialization
- `users/models/theme.py` - Theme model for user interface customization system
- `users/models/user.py` - Custom user model with profile fields and theme preferences

#### User Templates

- `users/templates/users/invitations.html` - User invitation management interface template

#### User Tests

- `users/tests/__init__.py` - Test package initialization for user test modules
- `users/tests/test_admin.py` - User admin interface tests
- `users/tests/test_auth_views.py` - Authentication view tests including registration and login
- `users/tests/test_models.py` - User model validation and functionality tests
- `users/tests/test_profile_views.py` - User profile management view tests
- `users/tests/test_theme_context.py` - Theme context processor tests for user preferences
- `users/tests/test_theme_forms.py` - Theme selection form validation tests
- `users/tests/test_theme_models.py` - User theme preference model tests
- `users/tests/test_theme_views.py` - Theme selection and persistence view tests
- `users/tests/test_utils.py` - User utility function tests

#### User URLs and Views

- `users/urls/__init__.py` - URL routing package for user-related endpoints
- `users/views/__init__.py` - View package initialization for user view modules
- `users/views/auth_views.py` - User authentication views for registration and login
- `users/views/invitation_views.py` - User invitation management views
- `users/views/profile_views.py` - User profile editing and theme selection views

### items/ (Item Management)

- `items/__init__.py` - Python package initialization for the items application
- `items/admin.py` - Django admin interface with bulk operations for item management
- `items/apps.py` - Django application configuration for items app settings
- `items/forms.py` - Django forms for item creation, editing, and bulk operations
- `items/migrations/__init__.py` - Database migrations package for item model changes with polymorphic support

#### Item Models

- `items/models/__init__.py` - Polymorphic item model definitions with soft delete and character ownership

#### Item Tests

- `items/tests/__init__.py` - Test package initialization for item test modules
- `items/tests/README_ISSUE_54_TESTS.md` - Documentation for item management testing strategy
- `items/tests/test_admin.py` - Item admin interface and bulk operations tests
- `items/tests/test_bulk_operations.py` - Bulk item management operation tests
- `items/tests/test_character_ownership.py` - Single character ownership and transfer tests
- `items/tests/test_forms.py` - Item form validation and submission tests
- `items/tests/test_integration.py` - Item system integration tests
- `items/tests/test_mixin_application.py` - Item model mixin functionality tests
- `items/tests/test_models.py` - Item model validation with polymorphic inheritance
- `items/tests/test_polymorphic_conversion.py` - Polymorphic model conversion and inheritance tests
- `items/tests/test_views.py` - Item CRUD views and permission tests

#### Item URLs and Views

- `items/urls/__init__.py` - URL routing package for item-related endpoints
- `items/views/__init__.py` - View package for item CRUD operations and management

### locations/ (Location Management)

- `locations/__init__.py` - Python package initialization for the locations application
- `locations/admin.py` - Django admin interface with hierarchy management and bulk operations
- `locations/apps.py` - Django application configuration for locations app settings
- `locations/forms.py` - Django forms for location creation, editing, and hierarchy management
- `locations/services.py` - Business logic layer for location hierarchy and NPC ownership operations
- `locations/migrations/__init__.py` - Database migrations package for location model changes

#### Location Models

- `locations/models/__init__.py` - Hierarchical location models with ownership and polymorphic inheritance

#### Location Tests

- `locations/tests/__init__.py` - Test package initialization for location test modules
- `locations/tests/test_admin.py` - Location admin interface tests
- `locations/tests/test_bulk_move_admin.py` - Bulk location hierarchy movement tests
- `locations/tests/test_forms.py` - Location form validation and hierarchy tests
- `locations/tests/test_hierarchy_validation.py` - Location hierarchy integrity and validation tests
- `locations/tests/test_location_interface.py` - Location interface and API tests
- `locations/tests/test_mixin_application.py` - Location model mixin functionality tests
- `locations/tests/test_models.py` - Location model validation and business logic tests
- `locations/tests/test_npc_ownership.py` - NPC ownership of locations functionality tests
- `locations/tests/test_npc_ownership_admin.py` - NPC ownership admin interface tests
- `locations/tests/test_npc_ownership_integration.py` - NPC ownership integration tests
- `locations/tests/test_permissions.py` - Location permission and access control tests
- `locations/tests/test_polymorphic_model.py` - Location polymorphic model inheritance tests

#### Location URLs and Views

- `locations/urls/__init__.py` - URL routing package for location-related endpoints
- `locations/views/__init__.py` - View package for location CRUD operations and hierarchy management

### scenes/ (Scene Management)

- `scenes/__init__.py` - Python package initialization for the scenes application
- `scenes/admin.py` - Django admin interface configuration for scene models
- `scenes/apps.py` - Django application configuration for scenes app settings
- `scenes/migrations/__init__.py` - Database migrations package for scene model changes

#### Scene Models

- `scenes/models/__init__.py` - Scene model definitions with campaign integration

#### Scene Tests

- `scenes/tests/__init__.py` - Test package initialization for scene test modules
- `scenes/tests/test_models.py` - Scene model validation and functionality tests

#### Scene URLs and Views

- `scenes/urls/__init__.py` - URL routing package for scene-related endpoints
- `scenes/views/__init__.py` - View package for scene management operations

## Frontend Development Tooling

- `package.json` - Node.js package dependencies for CSS linting and frontend development tools
- `.stylelintrc.json` - Stylelint configuration for CSS code quality and standards enforcement

## Templates (Django HTML Templates)

### Base Templates

- `templates/base.html` - Base template with navigation, theme support, and common layout elements

### Character Templates

- `templates/characters/campaign_characters.html` - Campaign-specific character listing template
- `templates/characters/character_create.html` - Character creation form template
- `templates/characters/character_delete.html` - Character deletion confirmation template
- `templates/characters/character_detail.html` - Character detail view template with game system data
- `templates/characters/character_edit.html` - Character editing form template
- `templates/characters/user_characters.html` - User's personal character listing template

### Core Templates

- `templates/core/index.html` - Home page template with welcome content and navigation

### Authentication Templates

- `templates/registration/login.html` - User login form template
- `templates/registration/logout.html` - Logout confirmation template
- `templates/registration/password_change_done.html` - Password change success template
- `templates/registration/password_change_form.html` - Password change form template
- `templates/registration/password_reset_complete.html` - Password reset completion template
- `templates/registration/password_reset_confirm.html` - Password reset confirmation template
- `templates/registration/password_reset_done.html` - Password reset email sent template
- `templates/registration/password_reset_email.html` - Password reset email HTML template
- `templates/registration/password_reset_form.html` - Password reset request form template
- `templates/registration/password_reset_subject.txt` - Password reset email subject template
- `templates/registration/register.html` - User registration form template

### Item Templates

- `templates/items/campaign_items.html` - Campaign item listing template with ownership and management features
- `templates/items/item_confirm_delete.html` - Item deletion confirmation template with soft delete support
- `templates/items/item_detail.html` - Item detail view template with ownership and transfer history
- `templates/items/item_form.html` - Item creation and editing form template

### Location Templates

- `templates/locations/campaign_locations.html` - Campaign location listing template with hierarchy display
- `templates/locations/location_detail.html` - Location detail view template with hierarchy and ownership
- `templates/locations/location_form.html` - Location creation and editing form template with parent selection

### Scene Templates

- `templates/scenes/campaign_scenes.html` - Campaign scene listing template with status and participation

### Admin Templates

- `templates/admin/locations/bulk_move_parent_form.html` - Admin bulk location move interface template

### User Templates

- `templates/users/profile.html` - User profile display template
- `templates/users/profile_edit.html` - User profile editing form template

## Static Files (CSS, JavaScript, Images)

### Campaign Static Files

- `static/campaigns/css/campaign_create.css` - Campaign creation form styling
- `static/campaigns/css/campaign_detail.css` - Campaign detail page styling with management controls
- `static/campaigns/css/campaign_detail_new.css` - Enhanced campaign detail page styling
- `static/campaigns/css/campaign_list.css` - Campaign listing page styling with filtering
- `static/campaigns/css/campaign_settings.css` - Campaign settings form styling

### Global Static Files

- `static/css/accessibility.css` - Accessibility-focused styling for WCAG 2.1 AA compliance
- `static/css/base.css` - Base styling with layout, typography, and component styles
- `static/css/email.css` - Email template styling for notifications
- `static/css/home.css` - Home page specific styling
- `static/css/locations.css` - Location-specific styling for hierarchy and management interfaces
- `static/css/theme-overrides.css` - Theme-specific style overrides and customizations
- `static/js/accessibility.js` - JavaScript for dynamic accessibility features and ARIA management
- `static/js/base.js` - Base JavaScript functionality and Django integration
- `static/js/enhanced-base.js` - Enhanced JavaScript with modern ES6+ features and error handling
- `static/js/locations.js` - Location-specific JavaScript for hierarchy management and interactions

### Theme Static Files

- `static/css/themes/cyberpunk.css` - Cyberpunk color theme with neon accents
- `static/css/themes/dark.css` - Dark theme with high contrast for readability
- `static/css/themes/forest.css` - Forest theme with green natural colors
- `static/css/themes/gothic.css` - Gothic theme with dark atmospheric colors
- `static/css/themes/high-contrast.css` - High contrast theme for accessibility
- `static/css/themes/lavender.css` - Lavender theme with soft purple colors
- `static/css/themes/light.css` - Light theme with bright, clean colors
- `static/css/themes/midnight.css` - Midnight theme with deep blue colors
- `static/css/themes/mint.css` - Mint theme with fresh green colors
- `static/css/themes/ocean.css` - Ocean theme with blue water-inspired colors
- `static/css/themes/sunset.css` - Sunset theme with warm orange and pink colors
- `static/css/themes/variables.css` - CSS custom properties for theme system
- `static/css/themes/vintage.css` - Vintage theme with retro sepia colors
- `static/css/themes/warm.css` - Warm theme with comfortable earth tones

### User Static Files

- `static/users/css/invitations.css` - User invitation interface styling

## Documentation

### Technical Documentation

- `docs/accessibility-guidelines.md` - WCAG 2.1 AA compliance guidelines and implementation patterns
- `docs/api-reference.md` - Complete API endpoint documentation with request/response examples
- `docs/architecture.md` - System architecture overview with service layer and design patterns
- `docs/database-schema.md` - Database models, relationships, and query optimization guide
- `docs/deployment.md` - Production deployment guide with security and scaling considerations
- `docs/development-guide.md` - Development workflow, TDD practices, and code standards
- `docs/HARDCODED_VALUES.md` - Environment variables and configuration values for production
- `docs/javascript-standards.md` - Modern JavaScript development standards and best practices
- `docs/location-hierarchy-system.md` - Location hierarchy system design and implementation guide
- `docs/LOCATION_MANAGEMENT_DOCUMENTATION_UPDATE.md` - Location management system documentation update
- `docs/MIGRATION_STRATEGY.md` - Database migration strategy and rollback procedures

## Scripts and Utilities

- `scripts/code_quality_config.py` - Code quality configuration and validation scripts
- `scripts/fetch_code_quality_issues.py` - Automated code quality issue detection and reporting
- `scripts/rollback_mixin_migrations.sh` - Interactive rollback script for mixin migrations
- `scripts/rollback_simple.sh` - Simple migration rollback script for development
- `scripts/test_api_keys.py` - API key testing and validation utilities

## Project Tests

- `tests/__init__.py` - Project-level test package initialization
- `tests/test_project_setup.py` - Project configuration and setup validation tests
