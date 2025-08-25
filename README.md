# Game Master Application (GMA)

[![Test and Coverage](https://github.com/charlesmsiegel/gma/actions/workflows/test-and-coverage.yml/badge.svg)](https://github.com/charlesmsiegel/gma/actions/workflows/test-and-coverage.yml)
[![Coverage](https://img.shields.io/badge/coverage-80%25-green.svg)](https://github.com/charlesmsiegel/gma/actions/workflows/test-and-coverage.yml)
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/cca7850a93094e0daeb176dd181e0469)](https://app.codacy.com/gh/charlesmsiegel/gma/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade)
[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](https://python.org)
[![Django](https://img.shields.io/badge/django-5.2.4-green.svg)](https://djangoproject.com)
[![Code Style](https://img.shields.io/badge/code%20style-black-black.svg)](https://github.com/psf/black)

A modern, web-based tabletop RPG campaign management system designed for World of Darkness games. Features comprehensive character management, hierarchical locations, item tracking, real-time scene chat communication, and campaign organization with accessibility-first design.

## 🎯 Project Overview

GMA is a comprehensive campaign management platform that bridges the gap between traditional tabletop RPGs and modern digital tools. Built with a focus on World of Darkness systems, it provides game masters and players with powerful tools for character management, campaign organization, and real-time collaborative gameplay.

### Key Features

- **🏛️ Campaign Management**: Full campaign lifecycle with settings, membership, and invitation system
- **👥 Player Management**: Role-based permissions (Owner → GM → Player → Observer) with secure invitation workflow
- **🎭 Character System**: Polymorphic models supporting World of Darkness inheritance (Character → WoDCharacter → MageCharacter)
- **📦 Item Management**: Single character ownership with transfer tracking and soft delete functionality
- **🏘️ Location Hierarchy**: Tree-based campaign locations with NPC ownership and bulk admin operations
- **🎨 Theme System**: 13+ themes including accessibility options with WCAG 2.1 AA compliance
- **💬 Real-time Scene Chat**: Complete WebSocket-based chat system with message types (IC/OOC/Private/System), character attribution, rate limiting, and message history API
- **🔒 Enterprise Security**: Secure authentication, CSRF protection, permission-based API access
- **🚀 API-First Design**: Complete REST API with modular views and comprehensive error handling

### Technology Stack

**Backend:**

- **Django 5.2.4** with Django REST Framework for robust API development
- **Django Channels** for WebSocket support and real-time features
- **PostgreSQL 16** as the primary database for data integrity
- **Redis 7.2** for caching and Channels layer backend
- **django-polymorphic** for flexible character model inheritance

**Frontend:**

- **Django Templates** with Bootstrap 5 for responsive design
- **Modern JavaScript ES6+** with accessibility features and enhanced error handling
- **CSS Linting** with Stylelint for code quality
- **WCAG 2.1 AA Compliance** with screen reader support and keyboard navigation

**Development Environment:**

- **Conda** for consistent environment management
- **Python 3.11** with comprehensive type checking
- **Node.js tooling** for CSS linting and frontend development tools

## 🚀 Quick Start

### Prerequisites

- **Python 3.11** (managed via Conda)
- **PostgreSQL 16**
- **Redis 7.2**
- **Git**
- **Node.js** (optional, for CSS linting tools)

### Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/charlesmsiegel/gma.git
   cd gma
   ```

2. **Set up the development environment:**

   ```bash
   # Create and activate conda environment
   conda env create -f environment.yml
   conda activate gma
   ```

3. **Install development tooling (optional):**

   ```bash
   # Install CSS linting tools
   npm install
   ```

4. **Initialize the database:**

   ```bash
   # Set up the database and create a superuser
   make reset-dev
   ```

5. **Start all services:**

   ```bash
   # Start PostgreSQL, Redis, and Django (port 8080)
   make runserver
   ```

6. **Access the application:**
   - **Main Application**: <http://localhost:8080>
   - **Admin Interface**: <http://localhost:8080/admin/>
   - **API Documentation**: <http://localhost:8080/api/schema/swagger-ui/>

### Development Commands

```bash
# Run all tests
make test

# Run tests with coverage
make test-coverage

# Code formatting and linting
make lint-css              # CSS linting with automatic fixes
isort --profile black .    # Sort imports
black .                    # Format Python code
flake8 .                   # Python linting
mypy .                     # Type checking

# Stop all services
make stop-all
```

## 📚 Documentation

Comprehensive documentation is available in the `docs/` directory:

- **[Architecture Guide](docs/architecture.md)** - System design and component interactions
- **[Development Guide](docs/development-guide.md)** - Setup, workflow, and best practices
- **[API Reference](docs/api-reference.md)** - Complete REST API and WebSocket documentation
- **[Database Schema](docs/database-schema.md)** - Data models and relationships
- **[Deployment Guide](docs/deployment.md)** - Production deployment instructions
- **[CLAUDE.md](CLAUDE.md)** - AI assistant development instructions and project context

## 🏗️ Architecture Overview

### Domain-Driven Design

The application follows a domain-driven monolithic architecture with clear separation of concerns:

```
├── api/           # Modular REST API with security features and bulk operations
├── campaigns/     # Campaign management with settings, membership, invitations
├── scenes/        # Scene management with comprehensive real-time chat system
├── characters/    # Polymorphic WoD character models with inheritance
├── users/         # Authentication, profiles, theme system
├── locations/     # Hierarchical locations with NPC ownership
├── items/         # Item management with single character ownership
└── core/          # Utilities, mixins, health monitoring, source references
```

### Service Layer Pattern

Each Django app implements a clean service layer architecture:

- **Models**: Data persistence and business rules
- **Services**: Business logic and cross-app operations
- **Views**: Request handling and response formatting
- **Serializers**: API data transformation

### Polymorphic Model Architecture

The system uses django-polymorphic for flexible inheritance across multiple domains:

**Character Hierarchy:**
```python
Character (base, polymorphic)
└── WoDCharacter (willpower)
    └── MageCharacter (arete, quintessence, paradox)
```

**Item System:**
```python
Item (base, polymorphic) - Ready for future game-specific items
├── WeaponItem (future)
├── ArmorItem (future)
└── ConsumableItem (future)
```

**Location System:**
```python
Location (base, polymorphic) - Hierarchical with NPC ownership
└── [Game-specific location types - future]
```

This design enables support for multiple game systems while maintaining type safety and query efficiency.

### Current Implementation Status

**✅ Completed Core Features:**
- Full campaign management with membership and settings
- Polymorphic character system (Character → WoD → Mage)
- Item management with single character ownership and transfer tracking
- Hierarchical location system with NPC ownership
- Theme system with 13+ themes and accessibility compliance
- Comprehensive admin interfaces with bulk operations
- REST API with security features and standardized error handling
- WCAG 2.1 AA accessibility implementation

**🚧 In Progress:**
- Advanced scene workflow management
- WoD-specific dice rolling system
- Advanced character sheet functionality

## 🧪 Development Workflow

GMA follows a **Test-Driven Development (TDD)** approach with comprehensive quality assurance:

### Testing Strategy

```bash
# Run complete test suite
make test

# Run tests with coverage reporting
make test-coverage

# Enforce minimum 80% coverage
python -m coverage report --fail-under=80
```

### Code Quality Standards

```bash
# Format code (run automatically in pre-commit)
isort --profile black .
black .

# Type checking
mypy .

# Linting and security
flake8 .
bandit -r . -f json

# Template formatting
djlint --reformat templates/

# CSS linting
make lint-css
```

### Development Phases

- **✅ Phase 1**: Generic Campaign Infrastructure (COMPLETED)
  - ✅ Campaign creation, management, and settings
  - ✅ User authentication with theme system
  - ✅ Polymorphic character model foundation
  - ✅ Item and location management systems
  - ✅ Admin interfaces and bulk operations
  - ✅ Comprehensive REST API
  - ✅ Accessibility compliance (WCAG 2.1 AA)

- **🚧 Phase 2**: World of Darkness Foundation (IN PROGRESS)
  - ✅ WoD character base class with willpower
  - ✅ MageCharacter with arete, quintessence, paradox
  - ✅ Comprehensive real-time scene chat system
  - ✅ WebSocket consumer with rate limiting and permission checking
  - ✅ Message history API with advanced filtering
  - ✅ JavaScript chat interface with accessibility features
  - 🚧 WoD-specific dice rolling system
  - 🚧 Game system validation framework

- **📋 Phase 3**: Mage Implementation (PLANNED)
  - Complete Mage: the Ascension character sheets
  - Sphere magic mechanics and rote management
  - Character advancement workflows
  - Advanced scene management

- **🚀 Phase 4**: Polish & Production (PLANNED)
  - Scene closure workflows
  - Performance optimization
  - Production deployment automation
  - Advanced real-time collaborative features

## 🔌 API Features

### REST API Capabilities

- **Modular API Structure**: Organized views by domain (campaigns, characters, locations, items)
- **Comprehensive CRUD Operations**: Full lifecycle management for all entities
- **Bulk Operations**: Efficient batch processing for admin tasks
- **Advanced Filtering**: Query parameter filtering with security validation
- **Standardized Responses**: Consistent error handling and success messages
- **Permission Integration**: Role-based access control at API level

### Security Features

- **Authentication Protection**: Secure login/logout with error message standardization
- **CSRF Token Handling**: Automatic token management for all form submissions
- **Permission Hierarchy**: Owner → GM → Player → Observer role enforcement
- **Input Validation**: Comprehensive field validation with sanitization
- **Error Information Control**: Security-focused error responses prevent data leakage
- **Rate Limiting Ready**: Production-ready rate limiting infrastructure

### Real-Time Chat System

- **WebSocket Consumer**: Complete SceneChatConsumer with authentication and rate limiting
- **Message Types**: PUBLIC (IC), OOC, PRIVATE (with recipients), SYSTEM (GM-only)
- **Permission System**: Role-based message visibility and sending permissions
- **Rate Limiting**: Configurable limits (10/min default, 30/min staff, 100/min system)
- **Message History API**: REST endpoint with filtering, pagination, and search
- **JavaScript Interface**: Full-featured chat UI with character selection and accessibility
- **Security Features**: Content validation, spam protection, error handling

## 🤝 Contributing

1. **Fork the repository** and create a feature branch
2. **Write tests first** following TDD principles
3. **Implement features** with frequent, small commits
4. **Ensure all tests pass** and maintain 80%+ coverage
5. **Run code quality checks** before submitting
6. **Open a pull request** with clear description

### Git Workflow

```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Run tests after each change
make test

# Commit frequently with descriptive messages
git commit -m "Add user search API endpoint"

# Ensure final code quality
make test-coverage
black .
flake8 .

# Push and create pull request
git push origin feature/your-feature-name
```

## 📝 License

This project is currently in active development. Please contact the maintainers for licensing information.

## 🙏 Acknowledgments

- Built with [Django](https://djangoproject.com/) and [Bootstrap](https://getbootstrap.com/)
- WebSocket support powered by [Django Channels](https://channels.readthedocs.io/)
- Polymorphic models implemented with [django-polymorphic](https://django-polymorphic.readthedocs.io/)
- State management with [django-fsm-2](https://github.com/viewflow/django-fsm)
- Development tooling includes [Black](https://black.readthedocs.io/), [mypy](https://mypy.readthedocs.io/), [flake8](https://flake8.pycqa.org/), and [Stylelint](https://stylelint.io/)
- Accessibility compliance following [WCAG 2.1 AA](https://www.w3.org/WAI/WCAG21/Understanding/) guidelines

---

**Game Master Application** - Bringing tabletop RPGs into the digital age while preserving the magic of collaborative storytelling.
