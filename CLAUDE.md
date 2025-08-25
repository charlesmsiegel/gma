# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Game Master Application (GMA) - A web-based tabletop RPG campaign management system focusing on World of Darkness games, specifically Mage: the Ascension for MVP. Features comprehensive character management, hierarchical locations, item tracking, and real-time chat communication.

## Technology Stack

### Backend

- **Django 5.2.4+** with Django REST Framework for API development
- **Django Channels** for WebSocket support (real-time scene chat with rate limiting)
- **PostgreSQL 16** as primary database
- **Redis 7.2** for caching and Channels layer
- **django-polymorphic** for game system character inheritance
- **django-fsm-2** for state machine management

### Frontend

- **Django Templates** with Bootstrap 5 for responsive UI
- **Vanilla JavaScript** for interactive features
- **WebSocket integration** for real-time scene chat with message history API

### Development Environment

- **Conda** for environment management
- **Python 3.11**

## Development Commands

### Environment Setup

```bash
# Create and activate conda environment
conda env create -f environment.yml
conda activate gma

```

### Django Commands

```bash
# Create migration files (ensures PostgreSQL is running)
make makemigrations

# Run migrations (ensures PostgreSQL is running)
make migrate

# Or run directly (requires PostgreSQL to be running)
python manage.py makemigrations
python manage.py migrate

# Reset all migrations (drops database, deletes migrations, recreates everything)
make reset-migrations

# Complete development reset (migrations + optional superuser)
make reset-dev

# Create superuser
make create-superuser
# OR
python manage.py createsuperuser

# Run development environment (PostgreSQL + Redis + Django)
make runserver
# OR
python manage.py runserver 0.0.0.0:8080

# Run with Channels/WebSocket support
daphne -b 0.0.0.0 -p 8080 gma.asgi:application

# Run tests
make test

# Run tests with coverage
make test-coverage                            # Complete coverage workflow
python -m coverage run manage.py test        # Run tests with coverage
python -m coverage combine                   # Combine coverage data files
python -m coverage report                    # Show coverage report
python -m coverage html                      # Generate HTML coverage report
python -m coverage report --fail-under=80    # Enforce 80% coverage minimum

# Code formatting and linting
isort --profile black .          # Sort imports with black profile
black .                          # Format code with black
flake8                          # Check for linting issues
mypy .                          # Type checking

# Check formatting without changes
isort --profile black --check-only --diff .  # Check import formatting
black --check --diff .                        # Check code formatting

# Additional code quality tools
mypy .                                        # Type checking
flake8 .                                      # Python linting
djlint --check templates/                     # Django template linting
djlint --reformat templates/                  # Format Django templates
bandit -r . -f json                          # Security scanning

# CSS linting and formatting
make setup-frontend                           # Install Node.js dependencies (one-time setup)
make lint-css                                # Run CSS linting with automatic fixes
make lint-css-check                          # Check CSS without making changes
npm run lint:css-report                      # Generate JSON report for CI/CD

# Create new Django app
python manage.py startapp <app_name>

# Health check commands
python manage.py health_check              # Test both database and Redis
python manage.py health_check --database   # Test database only
python manage.py health_check --redis      # Test Redis only
python manage.py health_check --log        # Log results to database

# Development database management commands
python manage.py reset_dev_db               # Reset database with confirmation
python manage.py reset_dev_db --force       # Reset database without confirmation
python manage.py reset_dev_db --no-superuser # Reset database without creating superuser

# Test data creation commands
python manage.py create_test_data           # Create default test data
python manage.py create_test_data --users=5 --campaigns=3 --characters=10  # Custom counts
python manage.py create_test_data --clear   # Clear existing test data first
python manage.py create_test_data --dry-run # Preview what would be created

# Migration safety testing commands
python manage.py test core.tests.test_migration_strategy  # Run all migration safety tests
python manage.py test core.tests.test_migration_strategy.ForwardMigrationDataPreservationTest  # Data preservation tests
python manage.py test core.tests.test_migration_strategy.MigrationPerformanceTest  # Performance tests
python manage.py test core.tests.test_migration_strategy.MigrationRollbackTest  # Rollback safety tests

# State machine testing commands
python manage.py test core.tests.test_django_fsm_installation  # Test django-fsm-2 installation and functionality

# Migration rollback support
./scripts/rollback_mixin_migrations.sh      # Interactive rollback script for mixin migrations

# Database shell access
python manage.py dbshell                   # Open PostgreSQL shell

# Admin interface
python manage.py createsuperuser           # Create admin user (if not exists)
# Then access http://localhost:8080/admin/ to view health check logs

# Stop all services
make stop-all                              # Stop PostgreSQL and Redis
```

### Database Commands

```bash
# Start PostgreSQL (if not running as service)
pg_ctl start -D $CONDA_PREFIX/var/postgres

# Start Redis
redis-server

# Access PostgreSQL
psql -U postgres
```

## Architecture Overview

### Service Layer Architecture

The project uses a **Service Layer Pattern** to separate business logic from views and forms:

- **Services** (`campaigns/services.py`): Business logic for complex operations
  - `MembershipService`: Handles campaign membership operations (add/remove/change roles)
  - `InvitationService`: Manages invitation creation and lifecycle
  - `CampaignService`: General campaign operations, settings, and user search
- **When to use services vs direct model access**:
  - Use services for operations involving multiple models or complex business rules
  - Use services when operations require transaction management (@transaction.atomic)
  - Direct model access is fine for simple CRUD operations
  - Services provide a consistent interface for both web views and API endpoints

### API Architecture

The API has been refactored for modularity and standardization:

- **Error Handling** (`api/errors.py`): Standardized error responses with security focus
  - `APIError`: Consistent error response builders (not_found, validation_error, etc.)
  - `FieldValidator`: Field validation helpers with standardized messages
  - `SecurityResponseHelper`: Security-focused responses that prevent information leakage
- **Centralized Messages** (`api/messages.py`): Single source of truth for error messages
  - `ErrorMessages`: Centralized error messages for consistent API responses
  - `FieldErrorMessages`: Field-specific error message builders
  - Prevents duplicate error strings and ensures consistency across all API endpoints
- **Modular View Structure** (`api/views/`):
  - `campaigns/`: Campaign-related API views (list, search, invitations)
  - `memberships/`: Membership management views (bulk operations, member management)
  - Focused modules replacing large monolithic view files
- **Serializers** (`api/serializers.py`): 13+ DRF serializers for consistent API responses
  - Nested serializers for related data
  - Role-based field exposure (settings only for owners)
  - Bulk operation response formats with success/error tracking

### Permission System Simplification

Consolidated permission checking with consistent patterns:

- **CampaignManagementMixin**: Template view permission checking
- **Role Hierarchy**: OWNER → GM → PLAYER → OBSERVER
- **Security Principle**: Return 404 instead of 403 to hide resource existence
- **Consistent Access Control**: `campaign.get_user_role(user)` for role checking

### Django App Structure

The project follows a domain-driven monolithic architecture with these Django apps:

- **users**: Authentication, profiles, theme management, campaign role management
- **campaigns**: Campaign creation, game system selection, membership, invitations, settings
- **scenes**: Scene lifecycle, character participation, comprehensive real-time chat system with WebSocket consumer, message history API, and rate limiting
- **characters**: Polymorphic character models (Character → WoDCharacter → MageCharacter), game system logic
- **locations**: Hierarchical location management with ownership, NPC control, bulk operations
- **items**: Polymorphic item management with single character ownership, soft delete, transfer tracking, complete REST API
- **prerequisites**: Comprehensive prerequisite system with JSON requirements, visual builder UI, drag-drop interface, and admin integration
- **api**: Modular REST API with comprehensive error handling, security features, bulk operations, including campaigns, characters, locations, and items
- **core**: Home page, utilities, mixins, management commands, health monitoring, source references

#### Internal Structure

The models, views, urls, and tests modules in every app should be managed as python modules rather than individual files.

### Polymorphic Model Hierarchy

Uses django-polymorphic for flexible game system inheritance:

#### Character Model Hierarchy
```
Character (base, polymorphic)
└── WoDCharacter
    └── MageCharacter
```

#### Item Model Hierarchy
```
Item (base, polymorphic) - Active with full CRUD operations
├── WeaponItem (future expansion)
├── ArmorItem (future expansion)
├── ConsumableItem (future expansion)
└── [Game-specific item types]
```

#### Location Model Hierarchy
```
Location (base, polymorphic) - Hierarchical with ownership
├── [Game-specific location types - future]
└── NPC ownership and control features
```

### Item Model Architecture

The Item model provides comprehensive equipment and treasure management with polymorphic inheritance support for future extensibility. Key features include:

#### Core Features
- **Basic Information**: Name (via NamedModelMixin), description, campaign association
- **Quantity Tracking**: Positive integer validation with minimum value of 1
- **Single Character Ownership**: ForeignKey relationship with Character model (Issue #183)
- **Transfer Tracking**: last_transferred_at timestamp field with transfer_to() method
- **Character Relationship**: Character.possessions reverse relationship for owned items
- **Audit Tracking**: created_by and modified_by via AuditableMixin for full user accountability
- **Soft Delete Pattern**: is_deleted, deleted_at, deleted_by fields for safe data management
- **Polymorphic Inheritance**: PolymorphicModel base enables future Item subclasses (Issue #182)

#### Single Character Ownership (Issue #183)
- **One Owner Per Item**: Each item can be owned by exactly one character (PC or NPC) or remain unowned
- **Transfer Method**: transfer_to(new_owner) with timestamp tracking and method chaining
- **Related Name**: Changed from "owned_items" to "possessions" for semantic clarity
- **Safe Deletion**: Items become unowned (owner=NULL) when character is deleted
- **Migration Strategy**: 3-step process preserving data during conversion from many-to-many

#### Polymorphic Manager Architecture
- **ItemManager (PolymorphicManager)**: Default manager excluding soft-deleted items with polymorphic support
- **AllItemManager (PolymorphicManager)**: Manager including all items (for restoration operations)
- **ItemQuerySet (PolymorphicQuerySet)**: Custom queryset with filtering methods (active, deleted, for_campaign, owned_by_character)

#### Permission System
- **Role-based Access**: Uses campaign role hierarchy (OWNER → GM → PLAYER → OBSERVER)
- **Creator Rights**: Item creators can always delete their items
- **Superuser Access**: Superusers have full item management permissions
- **can_be_deleted_by()**: Centralized permission checking method

#### Admin Interface Capabilities
- **6 Bulk Operations**: Soft delete, restore, quantity update, single ownership assignment/clearing, campaign transfer
- **Comprehensive Filtering**: By campaign, creator, quantity, creation date, deletion status, ownership
- **Organized Layout**: Fieldsets for basic info, single ownership with transfer timestamp, audit trail, and deletion status
- **Permission Checking**: Staff-only access with proper error handling
- **Transfer History**: Displays last_transferred_at timestamp in ownership fieldset

#### Polymorphic Inheritance (Issue #182)
- **Future Extensibility**: Ready for game-specific item subclasses (WeaponItem, ArmorItem, ConsumableItem)
- **Unified API**: Same endpoints, serializers, and business logic for all item types
- **Type-Safe Queries**: Polymorphic queries automatically return correct subclass instances
- **Database Efficiency**: Single table with polymorphic_ctype field for type identification
- **Full Backward Compatibility**: All existing Item functionality preserved

#### API Implementation
- **REST Endpoints**: Complete CRUD operations implemented (Issue #55)
  - `GET /api/items/`: List campaign items with advanced filtering, search, and pagination
  - `POST /api/items/`: Create new items with campaign and character validation
  - `GET /api/items/{id}/`: Retrieve item details with permission checking
  - `PUT /api/items/{id}/`: Update items with ownership transfer support
  - `DELETE /api/items/{id}/`: Soft delete items with audit tracking
- **Serializers**: Two-tier architecture for comprehensive API responses
  - `ItemSerializer`: Full response serialization with nested campaign, character, and user relationships
  - `ItemCreateUpdateSerializer`: Request validation and model updates with campaign scoping
- **Advanced Filtering**: Campaign-scoped filtering with multiple parameters
  - Owner filtering (character-based or unowned items with `owner=null`)
  - Creator filtering, quantity range validation, full-text search
  - Soft-deleted item inclusion for restoration workflows
- **Permission Integration**: Role-based access control with security features
  - Campaign membership validation, creator privileges, and superuser access
  - 404 responses instead of 403 to prevent information leakage
  - Character ownership validation ensuring same-campaign requirements
- **Polymorphic API Support**: Ready for future item subclasses
  - `polymorphic_ctype` field in responses for type identification
  - Serializer architecture supports inheritance without breaking changes

#### Testing Coverage
- **227 comprehensive tests** across 7 test files covering:
  - **59 API tests**: Endpoint validation, permissions, filtering, and security
  - **168 model tests**: Model validation, soft delete, admin operations, and business logic
  - Permission system edge cases and boundary condition testing
  - Admin interface bulk operations with transaction safety
  - Mixin application and database field compatibility
  - **Polymorphic conversion validation** (33 tests in test_polymorphic_conversion.py)
  - **Single character ownership** (33 tests in test_character_ownership.py covering transfer functionality, possessions relationship, and migration compatibility)

### Location Management System

The Location system provides hierarchical organization of campaign areas with comprehensive ownership and permission controls:

#### Core Features
- **Hierarchical Structure**: Tree-based parent/child relationships with unlimited nesting depth
- **Campaign Isolation**: Locations belong to specific campaigns with cross-campaign protection
- **Polymorphic Inheritance**: PolymorphicModel base enables future location subclasses
- **NPC Ownership**: Characters (including NPCs) can own and control locations
- **Permission System**: Role-based access control with campaign hierarchy integration
- **Audit Tracking**: Full creation/modification history via AuditableMixin
- **Soft Delete Support**: Safe deletion with restoration capabilities

#### Ownership and Control
- **Character Ownership**: Any character can own locations (owned_by field)
- **NPC Control**: NPCs can own locations within campaigns they participate in
- **Permission Hierarchy**: Campaign owners and GMs have management permissions
- **Ownership Validation**: Prevents cross-campaign ownership violations

#### Admin Interface
- **Hierarchy Visualization**: Tree-like display with parent/child relationships
- **Bulk Operations**: Move multiple locations to new parent with validation
- **Filtering**: By campaign, owner, parent location, creation date
- **Validation**: Prevents circular references and maintains data integrity

#### Testing Coverage
- **162 comprehensive tests** across 11 test files covering:
  - Hierarchical model validation and constraints
  - NPC ownership functionality and edge cases
  - Admin interface bulk operations
  - Permission system validation
  - Polymorphic model inheritance
  - Cross-campaign isolation
  - Circular reference prevention
  - Database integrity and performance

### Real-Time Chat Architecture

The GMA implements a comprehensive real-time chat system for scene communication with the following key features:

#### Message Model
- **Message Types**: PUBLIC (IC with character), OOC (out-of-character), PRIVATE (with recipients), SYSTEM (GM-only)
- **Character Attribution**: IC messages require character selection; OOC messages are player-based
- **Recipient Management**: Private messages support multiple recipients with permission checking
- **Content Validation**: 2000-character limit, Markdown support, inappropriate content filtering

#### WebSocket Consumer (SceneChatConsumer)
- **Authentication**: Secure WebSocket connections with user authentication required
- **Permission Checking**: Role-based access control (OWNER → GM → PLAYER → OBSERVER)
- **Rate Limiting**: Configurable limits (10/minute default, 30/minute staff, 100/minute system)
- **Connection Management**: Auto-reconnection, heartbeat monitoring, graceful error handling

#### Message History API
- **REST Endpoint**: `GET /api/scenes/{id}/messages/` with comprehensive filtering
- **Advanced Filtering**: Message type, sender, character, date range, search functionality
- **Permission Integration**: Messages filtered by user role and visibility rules
- **Pagination**: Efficient pagination for large message histories

#### JavaScript Chat Interface
- **Real-time Updates**: WebSocket message handling with automatic reconnection
- **Character Selection**: Dynamic character dropdown for IC messages
- **Message Formatting**: Timestamp display, message type indicators, character attribution
- **Rate Limit Feedback**: Real-time rate limit status with user-friendly messaging
- **Accessibility**: Screen reader support, keyboard navigation, ARIA live regions

#### Rate Limiting System
- **Multi-tier Limits**: Different rate limits based on user roles and message types
- **Sliding Window**: Memory-efficient rate limiting with Redis backend support
- **Security Features**: Content filtering, spam prevention, abuse protection

#### WebSocket Infrastructure
- **Routing**: `/ws/scenes/{scene_id}/chat/` endpoint pattern
- **Channel Groups**: Scene-based message broadcasting
- **Message Broadcasting**: Real-time delivery to all connected scene participants
- **Error Handling**: Comprehensive error messages with security considerations

### Prerequisite System Architecture

The GMA implements a comprehensive prerequisite system (Issues #188-192) for managing structured requirements across the entire RPG system. This system enables complex rule validation for character advancement, item usage, spell casting, and other game mechanics.

#### Core Components (Issues #188-192)

##### Requirement Helpers (Issue #188)
Location: `prerequisites/helpers.py` - 408 lines

Provides intuitive helper functions for building JSON requirement structures:

```python
from prerequisites.helpers import trait_req, has_item, any_of, all_of, count_with_tag

# Simple requirements
strength_req = trait_req("strength", minimum=3)
sword_req = has_item("weapons", name="Magic Sword")

# Complex logical combinations
combat_req = any_of(
    trait_req("strength", minimum=4),
    trait_req("dexterity", minimum=4)
)

advanced_req = all_of(
    trait_req("arete", minimum=3),
    has_item("foci", name="Crystal Orb"),
    count_with_tag("spheres", "elemental", minimum=2)
)
```

**Key Helper Functions:**
- `trait_req(name, minimum, maximum, exact)`: Character trait requirements
- `has_item(field, id, name, **kwargs)`: Item possession requirements
- `any_of(*requirements)`: Logical OR combinations
- `all_of(*requirements)`: Logical AND combinations
- `count_with_tag(model, tag, minimum, maximum)`: Tagged object counting

##### Checking Engine (Issue #189)
Location: `prerequisites/checkers.py` - 696 lines

Comprehensive validation engine that evaluates requirements against characters:

```python
from prerequisites.checkers import RequirementChecker

# Initialize checker
checker = RequirementChecker()

# Check simple requirement
result = checker.check_requirement(character, strength_req)
print(f"Passed: {result.passed}, Message: {result.message}")

# Check complex requirement with detailed results
result = checker.check_requirement(character, complex_req)
for detail in result.details:
    print(f"  {detail.requirement_type}: {detail.passed}")
```

**RequirementChecker Features:**
- **Character Integration**: Works with polymorphic Character models (Character → WoDCharacter → MageCharacter)
- **Recursive Checking**: Handles nested logical requirements (any/all combinations)
- **Performance Optimized**: Efficient database queries with minimal N+1 issues
- **Extensible Design**: Registry pattern for custom requirement types
- **Detailed Results**: RequirementCheckResult with success/failure details

**Supported Requirement Types:**
- `trait`: Character attributes, skills, and abilities
- `has`: Item possession and object relationships
- `any`: Logical OR operations with multiple sub-requirements
- `all`: Logical AND operations with multiple sub-requirements
- `count_tag`: Counting objects with specific tags

##### Visual Builder UI (Issue #190)
Location: `prerequisites/widgets.py` - Django form widget integration

Django widget system integration for requirement building in admin forms:

```python
# Form integration
class MyModelForm(forms.ModelForm):
    requirements = forms.JSONField(widget=PrerequisiteBuilderWidget)

    class Meta:
        model = MyModel
        fields = ['name', 'requirements']
```

**Widget Features:**
- **Form Integration**: Seamless Django form widget for JSONField
- **Visual Interface**: User-friendly requirement building interface
- **Real-time Validation**: Client-side and server-side requirement validation
- **Template Integration**: Custom template rendering with Bootstrap styling

##### Drag-Drop Interface (Issue #191)
Location: 7 JavaScript files (4,112 lines total)

Advanced drag-and-drop interface for complex requirement building:

**JavaScript Architecture:**
- **`prerequisite-builder.js`** (330 lines): Main builder coordination
- **`drag-drop-builder.js`** (478 lines): Core drag-drop functionality
- **`drag-drop-canvas.js`** (794 lines): Canvas management and rendering
- **`drag-drop-palette.js`** (477 lines): Component palette and toolbox
- **`accessibility-manager.js`** (735 lines): WCAG 2.1 AA compliance features
- **`touch-handler.js`** (707 lines): Mobile touch interaction support
- **`undo-redo-manager.js`** (591 lines): Action history and state management

**Key Features:**
- **Drag-Drop Interface**: Visual requirement building with component palette
- **Touch Support**: Mobile-friendly touch interactions for tablets
- **Accessibility**: Full WCAG 2.1 AA compliance with screen reader support
- **Undo/Redo**: Complete action history with state management
- **Real-time Preview**: JSON output generation with live validation
- **Component Library**: Pre-built requirement components (trait, has, any, all, count_tag)

##### Admin Interface (Issue #192)
Location: `prerequisites/admin.py` - 477 lines

Comprehensive Django admin integration with bulk operations:

**Admin Features:**
- **Visual Builder**: Integrated PrerequisiteBuilderWidget for JSONField editing
- **List Display**: Prerequisite summary columns with requirement type indicators
- **Advanced Filtering**: By content type, description, requirement complexity
- **Bulk Operations**: Copy requirements, apply to multiple objects, validation
- **Permission System**: Role-based access control with campaign isolation
- **Search Functionality**: Full-text search across descriptions and requirement data

**Bulk Operations:**
- **Copy Prerequisites**: Duplicate requirement sets across objects
- **Bulk Validation**: Validate multiple prerequisites against character sets
- **Template Application**: Apply requirement templates to new objects
- **Export/Import**: JSON export for requirement backup and migration

#### Data Models and Integration

##### Prerequisite Model
Location: `prerequisites/models/__init__.py`

Core model with GenericForeignKey for universal attachment:

```python
# Attach to any model
character_prereq = Prerequisite.objects.create(
    description="Combat mastery required",
    requirements=all_of(
        trait_req("strength", minimum=3),
        trait_req("melee", minimum=2)
    ),
    content_object=character
)

# Standalone requirements for templates
template_prereq = Prerequisite.objects.create(
    description="Mage sphere mastery",
    requirements=count_with_tag("spheres", "elemental", minimum=3)
)
```

**Model Features:**
- **GenericForeignKey**: Attach to characters, items, locations, or any model
- **JSON Requirements**: Structured requirement storage with validation
- **Audit Tracking**: TimestampedMixin for creation/modification history
- **Database Indexes**: Optimized queries for GenericForeignKey operations
- **Validation**: Comprehensive requirement structure validation

##### PrerequisiteCheckResult Model
Audit trail for requirement checking operations:

```python
# Automatic result logging
result = checker.check_requirement(character, requirement)
if log_results:
    PrerequisiteCheckResult.objects.create(
        content_object=spell,
        character=character,
        requirements=requirement,
        result=result.passed,
        failure_reasons=result.get_failure_reasons()
    )
```

#### Integration Points

##### Character System Integration
Works seamlessly with polymorphic character hierarchy:

```python
# Works with all character types
base_character = Character.objects.get(id=1)
wod_character = WoDCharacter.objects.get(id=2)
mage_character = MageCharacter.objects.get(id=3)

# All work with requirement checking
results = [
    checker.check_requirement(base_character, req),
    checker.check_requirement(wod_character, req),
    checker.check_requirement(mage_character, req)
]
```

##### Campaign Scoping
Prerequisites respect campaign boundaries:

```python
# Campaign-specific requirements
campaign_req = Prerequisite.objects.create(
    description="Campaign-specific mastery",
    requirements=trait_req("custom_skill", minimum=2),
    content_object=campaign_specific_item
)
```

##### API Integration
RESTful endpoints for requirement management:

```python
# API endpoints (future implementation)
GET /api/prerequisites/                    # List prerequisites
POST /api/prerequisites/                   # Create requirement
GET /api/prerequisites/{id}/               # Retrieve requirement
PUT /api/prerequisites/{id}/               # Update requirement
DELETE /api/prerequisites/{id}/            # Delete requirement
POST /api/prerequisites/{id}/check/        # Check requirement against character
```

#### Performance Considerations

Based on architectural reviews, the prerequisite system addresses several performance concerns:

##### Query Optimization
- **N+1 Query Prevention**: Efficient checking with minimal database hits
- **Bulk Operations**: Batch checking for multiple characters/requirements
- **Database Indexes**: Strategic indexing for GenericForeignKey queries
- **Caching Strategy**: Redis caching for frequently-accessed requirements

##### Scalability Patterns
- **Registry Design**: Extensible requirement type system
- **Recursive Depth Limits**: Maximum 5 levels of nested requirements
- **JSON Field Optimization**: Efficient PostgreSQL JSON operations
- **Lazy Loading**: Deferred requirement evaluation where possible

#### Security Model

##### JSON Structure Validation
Location: `prerequisites/validators.py`

Comprehensive validation prevents malicious JSON:

```python
# Structure validation
validators.validate_requirements(requirement_json)

# Prevents:
# - Malformed JSON structures
# - Infinite recursion in nested requirements
# - Invalid requirement types
# - XSS attacks through requirement data
```

##### Access Control
- **Campaign Isolation**: Requirements scoped to campaign membership
- **Admin Permissions**: Staff-only access to bulk operations
- **Content Object Security**: GenericForeignKey respects model permissions
- **XSS Protection**: Safe JSON rendering in admin widgets (note: security review findings)

#### Testing Coverage

Comprehensive test suite with 417 test methods across 16 test files:

**Test Categories:**
- **Helper Function Tests**: `test_helpers.py` - Requirement building validation
- **Checking Engine Tests**: `test_checkers.py` - Requirement evaluation logic
- **Model Tests**: `test_models.py` - Prerequisite model validation
- **Admin Tests**: `test_admin.py` - Admin interface and bulk operations
- **Widget Tests**: `test_visual_builder.py`, `test_admin_widgets.py` - UI component testing
- **JavaScript Tests**: `test_javascript_components.py`, `test_drag_drop_*` - Frontend functionality
- **Integration Tests**: Cross-system requirement checking and validation

**Test Coverage Areas:**
- **Requirement Building**: All helper functions with edge cases
- **Character Integration**: All polymorphic character types
- **Complex Logic**: Nested any/all combinations with deep recursion
- **Performance**: Query count validation and optimization verification
- **Security**: XSS prevention, input sanitization, permission checking
- **Accessibility**: WCAG 2.1 AA compliance verification
- **Mobile Support**: Touch interaction and responsive design testing

#### Usage Patterns and Examples

##### Character Advancement Requirements
```python
# Level up requirements
advancement_req = all_of(
    trait_req("experience_points", minimum=50),
    trait_req("current_level", maximum=4),
    any_of(
        has_item("training", name="Combat Training"),
        count_with_tag("achievements", "combat", minimum=3)
    )
)

# Check advancement eligibility
result = checker.check_requirement(character, advancement_req)
```

##### Spell/Power Prerequisites
```python
# High-level spell requirements
fireball_req = all_of(
    trait_req("arete", minimum=3),
    trait_req("forces", minimum=2),
    trait_req("prime", minimum=1),
    has_item("foci", name="Fire Focus")
)

# Batch check multiple spells
spell_eligibility = checker.batch_check(character, spell_requirements)
```

##### Item Usage Requirements
```python
# Magic item attunement
artifact_req = all_of(
    trait_req("willpower", minimum=6),
    any_of(
        trait_req("arete", minimum=4),
        count_with_tag("backgrounds", "avatar", minimum=3)
    ),
    trait_req("resonance_match", exact=1)  # Custom game logic
)
```

##### Campaign-Specific Rules
```python
# Chronicle-specific advancement
chronicle_mastery = all_of(
    count_with_tag("story_points", "completed", minimum=5),
    has_item("relationships", name="Mentor"),
    trait_req("chronicle_reputation", minimum=3)
)
```

#### Extensibility and Future Development

##### Custom Requirement Types
The registry pattern supports custom requirement checkers:

```python
# Register new requirement type
@RequirementChecker.register("custom_type")
def check_custom_requirement(character, requirement_data):
    # Custom logic implementation
    return RequirementCheckResult(passed=True, message="Custom check passed")
```

##### Game System Integration
Ready for expansion to additional RPG systems:

```python
# D&D 5e requirements (future)
dnd_req = all_of(
    trait_req("level", minimum=5),
    trait_req("strength", minimum=13),
    has_item("class_features", name="Extra Attack")
)

# Exalted requirements (future)
exalted_req = all_of(
    trait_req("essence", minimum=3),
    count_with_tag("charms", "solar", minimum=10),
    has_item("artifacts", name="Grand Daiklave")
)
```

##### API Expansion
Future API endpoints for advanced functionality:

```python
# Planned API endpoints
POST /api/prerequisites/bulk-check/         # Batch requirement checking
GET /api/prerequisites/templates/           # Requirement templates
POST /api/prerequisites/validate/          # Structure validation
GET /api/characters/{id}/eligible-for/     # Find eligible content
```

### API Design

- Flat URL patterns with query parameter filtering
- Example: `/api/scenes/?campaign_id={id}`
- WebSocket messages mirror REST API data structures
- Standardized error responses with security considerations
- Bulk operation endpoints for efficiency

## Test-Driven Development Workflow

### Testing Philosophy

The project follows strict **Test-Driven Development (TDD)** principles:

1. **Write Tests First**: All features start with comprehensive test coverage
2. **Red-Green-Refactor**: Write failing test → Make it pass → Improve code quality
3. **Frequent Commits**: Commit after each test passes or failure count decreases
4. **Comprehensive Coverage**: Aim for 80%+ test coverage with quality over quantity

### Test Structure

Tests are organized by functionality and complexity:

- **Unit Tests**: Individual model methods, service functions, utility functions
- **Integration Tests**: API endpoints, service layer interactions, database operations
- **Edge Cases**: Error handling, permission boundaries, validation failures
- **Security Tests**: Authentication, authorization, data leakage prevention

### Test Categories by App

- **campaigns/tests/**: Campaign models, membership, invitations, permissions, settings, API integration
- **api/tests/**: API endpoints, error handling, security, serializers, character/location APIs
- **users/tests/**: Authentication, user management, profile operations, theme system
- **characters/tests/**: Polymorphic character models, forms, views, ownership, FSM integration
- **items/tests/**: Item management, single ownership, polymorphic conversion, bulk operations
- **locations/tests/**: Hierarchical locations, NPC ownership, admin bulk operations, permissions
- **scenes/tests/**: Scene models, WebSocket consumer functionality, message model validation, chat integration, rate limiting, and real-time communication
- **prerequisites/tests/**: Requirement system testing with 417 test methods across 16 test files (helpers, checkers, models, admin, widgets, JavaScript, drag-drop functionality)
- **core/tests/**: Management commands, health checks, WebSocket connections, mixins, source references

### Running Tests

```bash
make test                   # Run all tests
make test-coverage          # Run with coverage report
python -m coverage report   # View coverage summary
python -m coverage html     # Generate detailed HTML report
```

ALWAYS use `make test` it will check all tests to avoid regressions and you will always have permission

### Test Patterns

- **Service Testing**: Test business logic separately from HTTP layer
- **API Testing**: Use DRF test client for endpoint validation
- **Permission Testing**: Verify role-based access controls
- **Error Handling**: Test both success and failure scenarios

## Development Phases

### Phase 1: ✅ Generic Campaign Infrastructure (COMPLETED)

- ✅ Basic campaign creation and management
- ✅ Campaign membership and invitation system
- ✅ User authentication and profile management
- ✅ Theme system with 13+ themes
- ✅ Base Character model with polymorphic inheritance
- ✅ Item management with single character ownership and complete REST API
- ✅ Location hierarchy with NPC ownership
- ✅ Scene management with complete REST API and status workflows
- ✅ Comprehensive prerequisite system with JSON requirements, visual builder UI, drag-drop interface, and admin integration
- ✅ Comprehensive admin interfaces
- ✅ REST API with security features
- ✅ WCAG 2.1 AA accessibility compliance

### Phase 2: 🚧 World of Darkness Foundation (IN PROGRESS)

- ✅ WoD character base class implementation
- ✅ MageCharacter with arete, quintessence, and paradox
- ✅ Scene API with participant management and status workflows
- ✅ Comprehensive real-time chat system with WebSocket consumer and message history API
- ✅ Rate limiting system for chat messages with role-based limits
- ✅ JavaScript chat interface with character selection and accessibility features
- 🚧 WoD dice rolling system
- 🚧 Game system selection validation

### Phase 3: Mage Implementation (PLANNED)

- Full Mage: the Ascension character sheets
- Sphere magic mechanics
- Character advancement workflow
- Rotes and spell management

### Phase 4: Polish & Production (PLANNED)

- Scene closure workflows
- Performance optimization
- Production deployment
- Advanced real-time features

## Key Development Principles

1. **API-First**: All functionality exposed through REST/WebSocket APIs
2. **Polymorphic Models**: Game system flexibility through inheritance
3. **Permission-Based**: Hierarchical roles (Owner → GM → Player → Observer)
4. **Mobile-Responsive**: Desktop-first with mobile adaptation
5. **Test Driven Design**: All code will be created after tests are. Any subjob will consist of writing tests, then writing code, on a feature branch, and committing at each functional improvement.

## Security Considerations

### Authentication Security

- Authentication views implement secure error messages that don't reveal user existence
- Case-insensitive email validation prevents duplicate accounts
- Password reset tokens expire in 3 days (Django default)

### Rate Limiting (Production Recommendation)

For production deployment, implement rate limiting to prevent brute force attacks:

- **django-ratelimit**: Decorator-based rate limiting for views
- **django-axes**: Comprehensive login attempt tracking and blocking
- **Infrastructure**: Cloudflare, nginx, or load balancer rate limiting

Example django-ratelimit implementation:

```python
from django_ratelimit.decorators import ratelimit

@ratelimit(key='ip', rate='5/m', method='POST', block=True)
def login_view(request):
    # Login logic
```

## Frontend Integration

The project uses Django templates with Bootstrap 5 and vanilla JavaScript for interactive features:

### Architecture

- **Template-based**: Django templates with Bootstrap 5 for responsive UI
- **Progressive enhancement**: JavaScript enhances forms and provides AJAX functionality
- **API integration**: JavaScript uses Django REST API endpoints for dynamic features
- **CSRF protection**: Manual CSRF token handling for secure AJAX requests

### JavaScript Structure

- **Base JavaScript**: `static/js/base.js` for common functionality (theme switching, AJAX helpers)
- **Enhanced JavaScript**: `static/js/enhanced-base.js` with modern standards and improved error handling
- **Accessibility JavaScript**: `static/js/accessibility.js` for WCAG 2.1 AA compliance features
- **Location Management**: `static/js/locations.js` for hierarchy management and interactions
- **Page-specific scripts**: Additional JavaScript files for complex interactions
- **Fetch API**: Modern JavaScript for API communication instead of jQuery
- **Bootstrap 5**: For responsive components and interactions

### JavaScript Quality Standards

- **Modern ES6+ Features**: Comprehensive use of const/let, arrow functions, async/await, and template literals
- **Error Handling**: Robust try-catch blocks, timeout handling, and graceful degradation
- **Performance Optimization**: Debouncing, throttling, and efficient DOM manipulation
- **Security Implementation**: XSS prevention, input sanitization, and CSRF token handling
- **Accessibility Integration**: Screen reader announcements, keyboard navigation, and ARIA state management
- **Code Organization**: Class-based architecture, module patterns, and centralized configuration
- **Standards Documentation**: Complete guide in `docs/javascript-standards.md` with examples and anti-patterns

### CSS Quality and Linting

- **Stylelint Configuration**: Comprehensive CSS linting with `.stylelintrc.json`
  - Modern CSS standards (short hex colors, percentage alpha values, context media queries)
  - Property ordering and consistency rules
  - BEM naming convention support with flexible patterns
  - SCSS and modern CSS features support
  - Automatic fixing of common issues
- **Node.js Dependencies**: Frontend tooling managed via `package.json`
  - Stylelint plugins for enhanced checking
  - JSON reporting for CI/CD integration
  - Makefile integration for easy usage

### Accessibility Implementation

- **WCAG 2.1 AA Compliance**: Comprehensive accessibility features
  - Skip navigation links for keyboard users
  - Proper semantic HTML structure with landmarks (`role="banner"`, `role="contentinfo"`, `<main>`)
  - Enhanced focus indicators with high contrast and clear visibility
  - ARIA live regions for dynamic content announcements
  - Screen reader optimizations with proper labeling and descriptions
- **Accessibility CSS** (`static/css/accessibility.css`): Focused styling for accessibility
  - High contrast focus indicators
  - Reduced motion support for users with vestibular disorders
  - Screen reader only content helpers
  - Enhanced form validation visual feedback
- **Accessibility JavaScript** (`static/js/accessibility.js`): Dynamic accessibility features
  - ARIA live region management for announcements
  - Form validation error announcements
  - Modal focus trapping and management
  - Keyboard navigation enhancements
  - Loading state announcements
- **Guidelines Documentation** (`docs/accessibility-guidelines.md`): Complete implementation guide
  - Template patterns for accessible HTML
  - Testing procedures and checklists
  - Screen reader testing instructions
  - Common issues and solutions

### Development Workflow

1. **Start development**: `make runserver` - Starts PostgreSQL, Redis, and Django (port 8080)
2. **Access application**: Visit `http://localhost:8080` for the complete application
3. **Stop services**: `make stop-all` - Stops PostgreSQL and Redis

# Workflow

Whenever we start a session, unless resuming a previous workflow, we use the following:

1) Create a branch for the work we're doing
2) Determine our success criteria.
3) Ask the user clarifying questions about our goals
4) Use @agent-test-automator to write tests that will be satisfied if and only if we are successful.
5) Commit the tests to the branch
6) Implement features/fixes/etc testing after each unit of work with `make test`. Commit whenever the number of test failures decreases. favor frequent small commits over single larger ones
7) Run @agent-architect-review and @agent-simplify to ensure the code is clean and ready for deployment. Commit after each runs and all tests pass.
8) Once all tests pass, we open a pull request

## Responsibilities

Use the following agents for specific tasks:

- @agent-architect-review before creating pull request to review all changes for consistent architecture
- @agent-django-api-developer when creating API endpoints
- @agent-django-backend-expert for building models, views, ervices, etc. in django
- @agent-django-orm-expert for optimizing queries
- @agent-docs-architect should run before commits to update documents
- @agent-frontend-developer for building JavaScript and template enhancements
- @agent-simplify should run before PR to ensure the design doesn't get too complex
- @agent-test-automator builds tests

# Documentation Structure

Comprehensive technical documentation is available in the `/docs` directory:

- **`docs/architecture.md`**: System architecture, service layer, API structure, security patterns
- **`docs/api-reference.md`**: Complete API endpoint documentation with examples
- **`docs/development-guide.md`**: TDD workflow, code standards, testing practices
- **`docs/deployment.md`**: Production deployment, security, monitoring, scaling
- **`docs/database-schema.md`**: Database models, relationships, query optimization
- **`docs/HARDCODED_VALUES.md`**: Environment variables to configure for production

The documentation is designed for both new developers joining the project and as a reference for the existing team. Each document includes practical examples and follows the project's architectural decisions.
