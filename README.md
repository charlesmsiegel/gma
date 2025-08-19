# Game Master Application (GMA)

[![Test and Coverage](https://github.com/charlesmsiegel/gma/actions/workflows/test-and-coverage.yml/badge.svg)](https://github.com/charlesmsiegel/gma/actions/workflows/test-and-coverage.yml)
[![Coverage](https://img.shields.io/badge/coverage-80%25-green.svg)](https://github.com/charlesmsiegel/gma/actions/workflows/test-and-coverage.yml)
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/cca7850a93094e0daeb176dd181e0469)](https://app.codacy.com/gh/charlesmsiegel/gma/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade)
[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](https://python.org)
[![Django](https://img.shields.io/badge/django-5.2.4-green.svg)](https://djangoproject.com)
[![Code Style](https://img.shields.io/badge/code%20style-black-black.svg)](https://github.com/psf/black)

A modern, web-based tabletop RPG campaign management system designed for World of Darkness games, with a focus on Mage: the Ascension for the MVP release.

## 🎯 Project Overview

GMA is a comprehensive campaign management platform that bridges the gap between traditional tabletop RPGs and modern digital tools. Built with a focus on World of Darkness systems, it provides game masters and players with powerful tools for character management, campaign organization, and real-time collaborative gameplay.

### Key Features

- **🏛️ Campaign Management**: Create and organize multiple campaigns with hierarchical permission systems
- **👥 Player Management**: Sophisticated invitation system with role-based access control (Owner → GM → Player → Observer)
- **🎭 Character System**: Polymorphic character models supporting multiple game systems through inheritance
- **💬 Real-time Communication**: WebSocket-powered scene chat for immersive gameplay sessions
- **🎲 Dice Rolling System**: Integrated dice mechanics specific to World of Darkness systems
- **📱 Progressive Web App**: Mobile-responsive design with offline capabilities
- **🔒 Secure Authentication**: Enterprise-grade security with comprehensive permission systems
- **🚀 API-First Design**: Complete REST API with WebSocket support for real-time features

### Technology Stack

**Backend:**

- **Django 5.2.4** with Django REST Framework for robust API development
- **Django Channels** for WebSocket support and real-time features
- **PostgreSQL 16** as the primary database for data integrity
- **Redis 7.2** for caching and Channels layer backend
- **django-polymorphic** for flexible character model inheritance

**Frontend:**

- **React with TypeScript** for enhanced user interactions
- **Progressive Web App** architecture for mobile and offline support
- **WebSocket integration** for real-time collaborative features

**Development Environment:**

- **Conda** for consistent environment management
- **Python 3.11** with comprehensive type checking
- **Node.js 20** for modern frontend development

## 🚀 Quick Start

### Prerequisites

- **Python 3.11** (managed via Conda)
- **Node.js 20**
- **PostgreSQL 16**
- **Redis 7.2**
- **Git**

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

3. **Install frontend dependencies:**

   ```bash
   cd frontend
   npm install
   cd ..
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

### Alternative Development Setup

For granular control over services:

```bash
# Start only Django backend with services
make runserver-django

# Start only React frontend (in separate terminal)
make start-frontend

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
├── api/           # REST API views, serializers, WebSocket routing
├── campaigns/     # Campaign creation, game system selection, membership
├── scenes/        # Scene lifecycle, character participation, real-time chat
├── characters/    # Polymorphic character models and game system logic
├── users/         # Authentication, profiles, campaign role management
├── locations/     # Hierarchical campaign locations
├── items/         # Equipment and treasure management
└── core/          # Front page, utilities, base templates
```

### Service Layer Pattern

Each Django app implements a clean service layer architecture:

- **Models**: Data persistence and business rules
- **Services**: Business logic and cross-app operations
- **Views**: Request handling and response formatting
- **Serializers**: API data transformation

### Character Model Hierarchy

The system uses django-polymorphic for flexible character inheritance:

```python
Character (base)
└── WoDCharacter
    └── MageCharacter
```

This design enables support for multiple game systems while maintaining type safety and query efficiency.

### Real-Time Architecture

- **Character-based scene architecture** for organized gameplay sessions
- **Single WebSocket connection per player** for efficient resource usage
- **Dynamic channel subscriptions** for multiple simultaneous scenes
- **Django Channels routing** for scalable WebSocket message handling

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
```

### Development Phases

- **✅ Phase 1**: Generic Campaign Infrastructure (Current)
  - Campaign creation and management
  - Scene creation with chat functionality
  - Base character model setup

- **🔄 Phase 2**: World of Darkness Foundation
  - WoD character base class implementation
  - WoD-specific dice rolling system
  - Game system selection framework

- **📋 Phase 3**: Mage Implementation
  - Complete Mage: the Ascension character sheets
  - Sphere magic mechanics
  - Character advancement workflows

- **🚀 Phase 4**: Polish & Production
  - Scene closure workflows
  - Performance optimization
  - Production deployment automation

## 🔌 API Features

### REST API Capabilities

- **Flat URL patterns** with query parameter filtering: `/api/scenes/?campaign_id={id}`
- **Comprehensive CRUD operations** for all major entities
- **Permission-based access control** integrated at the API level
- **Automatic API documentation** with drf-spectacular

### WebSocket Support

- **Real-time scene chat** for collaborative gameplay
- **Live character updates** across connected clients
- **Dynamic room management** based on scene participation
- **Message persistence** with full chat history

### Authentication & Security

- **Secure user registration and login** with comprehensive error handling
- **Role-based permissions** (Owner → GM → Player → Observer)
- **CSRF protection** for all form submissions
- **Rate limiting ready** for production deployment

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

- Built with [Django](https://djangoproject.com/) and [React](https://reactjs.org/)
- WebSocket support powered by [Django Channels](https://channels.readthedocs.io/)
- Character inheritance implemented with [django-polymorphic](https://django-polymorphic.readthedocs.io/)
- Development tooling includes [Black](https://black.readthedocs.io/), [mypy](https://mypy.readthedocs.io/), and [pytest](https://pytest.org/)

---

**Game Master Application** - Bringing tabletop RPGs into the digital age while preserving the magic of collaborative storytelling.
