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

### Frontend
- **React with TypeScript** (Progressive Web App)
- **WebSocket integration** for real-time features

### Development Environment
- **Conda** for environment management
- **Python 3.11**
- **Node.js 20** for frontend development

## Development Commands

### Environment Setup
```bash
# Create and activate conda environment
conda env create -f environment.yml
conda activate gma

# Install frontend dependencies (after initial React setup)
cd frontend
npm install
```

### Django Commands
```bash
# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver

# Run with Channels/WebSocket support
daphne -b 0.0.0.0 -p 8000 gma.asgi:application

# Run tests
python manage.py test
# or use Makefile
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

# Database shell access
python manage.py dbshell                   # Open PostgreSQL shell

# Admin interface
python manage.py createsuperuser           # Create admin user (if not exists)
# Then access http://localhost:8080/admin/ to view health check logs
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

### Django App Structure
The project follows a domain-driven monolithic architecture with these Django apps:

- **users**: Authentication, profiles, campaign role management
- **campaigns**: Campaign creation, game system selection, membership
- **scenes**: Scene lifecycle, character participation, real-time chat, dice rolling
- **characters**: Polymorphic character models, game system logic, character sheets
- **locations**: Hierarchical campaign locations
- **items**: Equipment and treasure management
- **api**: DRF views, serializers, WebSocket routing
- **core**: Front page, utilities, base templates

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
