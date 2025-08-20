# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Game Master Application (GMA) - A web-based tabletop RPG campaign management system focusing on World of Darkness games, specifically Mage: the Ascension for MVP.

## Technology Stack

### Backend

- **Django 5.2.4+** with Django REST Framework for API development
- **Django Channels** for WebSocket support (real-time chat)
- **PostgreSQL 16** as primary database
- **Redis 7.2** for caching and Channels layer
- **django-polymorphic** for game system character inheritance
- **django-fsm-2** for state machine management

### Frontend

- **Django Templates** with Bootstrap 5 for responsive UI
- **Vanilla JavaScript** for interactive features
- **WebSocket integration** for real-time features

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

- **users**: Authentication, profiles, campaign role management
- **campaigns**: Campaign creation, game system selection, membership, invitations
- **scenes**: Scene lifecycle, character participation, real-time chat, dice rolling
- **characters**: Polymorphic character models, game system logic, character sheets
- **locations**: Hierarchical campaign locations
- **items**: Equipment and treasure management
- **api**: Modular DRF views, serializers, standardized error handling
- **core**: Front page, utilities, base templates, management commands, source references (Book model)

#### Internal Structure

The models, views, urls, and tests modules in every app should be managed as python modules rather than individual files.

### Character Model Hierarchy

Uses django-polymorphic for game system inheritance:

```
Character (base)
└── WoDCharacter
    └── MageCharacter
```

### Real-Time Architecture

- Character-based scene architecture
- Single WebSocket connection per player
- Dynamic subscriptions to multiple scene channels
- Django Channels for WebSocket message routing

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

- **campaigns/tests/**: Campaign models, membership, invitations, permissions
- **api/tests/**: API endpoints, error handling, security, serializers
- **users/tests/**: Authentication, user management, profile operations
- **core/tests/**: Management commands, health checks, WebSocket connections, django-fsm-2 integration, Book model tests

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

### Phase 1: Generic Campaign Infrastructure

- Basic campaign creation and management
- Scene creation with chat (no dice)
- Base Character model setup

### Phase 2: World of Darkness Foundation

- WoD character base class
- WoD dice rolling system
- Game system selection

### Phase 3: Mage Implementation

- Full Mage: the Ascension character sheets
- Sphere magic mechanics
- Character advancement workflow

### Phase 4: Polish & Production

- Scene closure workflows
- Performance optimization
- Production deployment

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
