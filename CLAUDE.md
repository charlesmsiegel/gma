# CLAUDE.md

Game Master Application (GMA) - A web-based tabletop RPG campaign management system for World of Darkness games, specifically Mage: the Ascension MVP. Features character management, hierarchical locations, item tracking, and real-time chat.

## Technology Stack

**Backend**: Django 5.2.4+ w/ DRF, Django Channels (WebSocket), PostgreSQL 16, Redis 7.2, django-polymorphic, django-fsm-2
**Frontend**: Django Templates, Bootstrap 5, Vanilla JavaScript, WebSocket integration
**Environment**: Conda, Python 3.11

## Development Commands

### Essential Commands
```bash
# Environment
conda env create -f environment.yml && conda activate gma

# Database & Migrations
make migrate                    # Run migrations (auto-starts PostgreSQL)
make makemigrations            # Create migrations
make reset-dev                 # Complete reset with optional superuser

# Development
make runserver                 # Start all services (PostgreSQL + Redis + Django:8080)
make test                      # Run all tests (ALWAYS use this)
make test-coverage             # Coverage report (80% minimum)
make stop-all                  # Stop PostgreSQL and Redis

# Code Quality
black . && isort --profile black .    # Format code
flake8 && mypy .                      # Lint and type check
make lint-css                         # CSS linting
```

### Specialized Commands
```bash
# Database Management
python manage.py reset_dev_db [--force] [--no-superuser]
python manage.py health_check [--database|--redis] [--log]
python manage.py dbshell

# Test Data
python manage.py create_test_data [--users=N --campaigns=N --characters=N] [--clear] [--dry-run]

# Services
daphne -b 0.0.0.0 -p 8080 gma.asgi:application  # WebSocket support
redis-server                                      # Start Redis manually
pg_ctl start -D $CONDA_PREFIX/var/postgres      # Start PostgreSQL manually
```

## Architecture Overview

### Core Patterns
- **Service Layer**: Complex business logic in `campaigns/services.py` (MembershipService, InvitationService, CampaignService). Use for multi-model operations, transactions, and consistency across views/API.
- **Permission Hierarchy**: OWNER → GM → PLAYER → OBSERVER. Return 404 (not 403) to hide resource existence.
- **API Design**: Modular views (`api/views/`), standardized errors (`api/errors.py`), centralized messages (`api/messages.py`), 13+ DRF serializers.

### Django Apps
- **users**: Authentication, profiles, themes, campaign roles
- **campaigns**: Campaign CRUD, game systems, membership, invitations
- **scenes**: Lifecycle, participation, real-time chat (WebSocket + message history API)
- **characters**: Polymorphic models (Character → WoDCharacter → MageCharacter)
- **locations**: Hierarchical with ownership, NPC control, bulk operations
- **items**: Single character ownership, soft delete, transfer tracking, REST API
- **prerequisites**: JSON requirements, visual builder UI, drag-drop interface
- **api**: Modular REST with error handling, security, bulk operations
- **core**: Utilities, mixins, management commands, health monitoring

**Note**: Use Python modules (not files) for models, views, urls, tests in each app.

### Polymorphic Models
```
Character (base) → WoDCharacter → MageCharacter
Item (base) → [WeaponItem, ArmorItem, ConsumableItem] (future)
Location (base) → [Game-specific types] (future)
```

### Item System
**Core**: Single character ownership, soft delete, transfer tracking, polymorphic inheritance ready
**Features**: Name/description, quantity validation, audit tracking, campaign scoping
**API**: Complete CRUD (`/api/items/`) with filtering, permissions, bulk operations
**Admin**: 6 bulk operations, comprehensive filtering, transfer history
**Testing**: 227 tests (59 API, 168 model) across 7 files

### Location System
**Core**: Hierarchical tree structure, campaign isolation, NPC ownership, polymorphic inheritance ready
**Features**: Unlimited nesting, cross-campaign protection, audit tracking, soft delete
**Admin**: Tree visualization, bulk move operations, comprehensive filtering
**Testing**: 162 tests across 11 files (hierarchy, ownership, permissions, integrity)

### Real-Time Chat System
**Messages**: 4 types (PUBLIC/IC, OOC, PRIVATE, SYSTEM), 2000-char limit, Markdown support
**WebSocket**: SceneChatConsumer with authentication, role-based permissions, rate limiting (10/30/100 per minute)
**API**: `GET /api/scenes/{id}/messages/` with filtering, pagination, permission integration
**Frontend**: Auto-reconnection, character selection, accessibility (WCAG 2.1 AA)
**Infrastructure**: `/ws/scenes/{scene_id}/chat/`, Redis backend, channel groups

### Prerequisite System (Issues #188-192)
**Core**: JSON requirements with GenericForeignKey attachment to any model, complex rule validation
**Components**:
- **Helpers** (`helpers.py` 408 lines): `trait_req()`, `has_item()`, `any_of()`, `all_of()`, `count_with_tag()`
- **Checker** (`checkers.py` 696 lines): RequirementChecker with polymorphic character support, N+1 optimized
- **UI**: Visual builder widget, drag-drop interface (7 JS files, 4112 lines), WCAG 2.1 AA compliant
- **Admin** (477 lines): Bulk operations, filtering, copy/template functionality

**Integration**: Campaign scoping, polymorphic character hierarchy, audit logging, Redis caching
**Security**: JSON validation, XSS prevention, permission-based access, 5-level recursion limit
**Testing**: 417 tests across 16 files (helpers, checkers, models, admin, widgets, JS, drag-drop)

### API Design
Flat URL patterns (`/api/scenes/?campaign_id={id}`), standardized errors, bulk operations, WebSocket mirroring REST structure

## Testing & Development

### TDD Workflow
1. **Write Tests First** → Red-Green-Refactor → Commit on failure reduction
2. **Coverage**: 80%+ minimum, always use `make test` (prevents permission issues)
3. **Test Types**: Unit, integration, edge cases, security, permission validation

### Test Organization
**By App**: campaigns, api, users, characters, items, locations, scenes, prerequisites, core
**Patterns**: Service layer testing, DRF client for APIs, role-based access verification

## Development Phases

**Phase 1** ✅ **COMPLETED**: Campaign infrastructure, membership, authentication, themes, polymorphic characters, items (single ownership + REST API), locations (hierarchy + NPC ownership), scenes (REST API + workflows), prerequisites (complete system), admin interfaces, WCAG 2.1 AA compliance

**Phase 2** 🚧 **IN PROGRESS**: WoD character base + MageCharacter (arete/quintessence/paradox), scene API + chat (WebSocket + message history + rate limiting), dice rolling system, game system validation

**Phase 3** 📋 **PLANNED**: Full Mage character sheets, sphere magic, character advancement, rotes/spells
**Phase 4** 📋 **PLANNED**: Scene closure, performance optimization, production deployment

## Core Principles

1. **API-First**: All functionality via REST/WebSocket APIs
2. **Polymorphic Models**: Game system flexibility through inheritance
3. **Permission Hierarchy**: OWNER → GM → PLAYER → OBSERVER
4. **Mobile-Responsive**: Desktop-first with mobile adaptation
5. **TDD**: Tests first, then code, commit on failure reduction

## Security

**Authentication**: Secure error messages (no user existence leakage), case-insensitive email validation, 3-day password reset tokens
**Production Rate Limiting**: django-ratelimit, django-axes, infrastructure-level limiting (Cloudflare/nginx)

## Frontend

**Stack**: Django templates + Bootstrap 5 + vanilla JavaScript (no jQuery), progressive enhancement, API integration, CSRF protection

**JavaScript**:
- **Files**: `base.js` (common), `enhanced-base.js` (modern standards), `accessibility.js` (WCAG), `locations.js` (hierarchy)
- **Standards**: ES6+, fetch API, robust error handling, debouncing/throttling, XSS prevention
- **Quality**: Class-based architecture, module patterns, documented in `docs/javascript-standards.md`

**CSS**: Stylelint with `.stylelintrc.json`, BEM naming, automatic fixing, CI/CD reporting

**Accessibility**: WCAG 2.1 AA compliant - skip links, semantic HTML, focus indicators, ARIA live regions, screen reader optimization, documented in `docs/accessibility-guidelines.md`

**Workflow**: `make runserver` → `http://localhost:8080` → `make stop-all`

## Development Workflow

**Session Start**: Create branch → Define success criteria → Ask clarifying questions → @agent-test-automator writes tests → Commit tests → Implement (testing with `make test` after each unit, commit on failure reduction) → @agent-architect-review + @agent-simplify → All tests pass → Open PR

**Agent Responsibilities**:
- @agent-architect-review: Pre-PR architecture review
- @agent-django-api-developer: API endpoints
- @agent-django-backend-expert: Models, views, services
- @agent-django-orm-expert: Query optimization
- @agent-docs-architect: Documentation updates (pre-commit)
- @agent-frontend-developer: JavaScript/template enhancements
- @agent-simplify: Complexity reduction (pre-PR)
- @agent-test-automator: Test creation

## Documentation

**`/docs` Directory**: `architecture.md` (system architecture), `api-reference.md` (endpoints), `development-guide.md` (TDD workflow), `deployment.md` (production), `database-schema.md` (models/queries), `HARDCODED_VALUES.md` (environment variables)
