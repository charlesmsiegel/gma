# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Game Master Application (GMA) - A web-based tabletop RPG campaign management system focusing on World of Darkness games, specifically Mage: the Ascension for MVP.

## Technology Stack

### Backend
- **Django 5.0** with Django REST Framework for API development
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
pytest
# or
python manage.py test

# Linting and formatting
black .
flake8
mypy .

# Create new Django app
python manage.py startapp <app_name>
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