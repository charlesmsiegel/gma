# Game Master Application - Technical Design Decisions

## Section I: Technology Stack (MVP Focus)

### Backend Services

#### Django + Django REST Framework + Django Channels
- **Usage**: Complete backend solution handling REST APIs, user management, campaign data, and real-time WebSocket chat
- **Pros**:
  - Single framework simplicity for solo development
  - Rapid MVP development leveraging existing Python expertise
  - Built-in admin interface for game system content management
  - Seamless authentication integration between REST APIs and WebSocket chat
  - Django Channels handles expected MVP load (few hundred concurrent sessions)
- **Cons**:
  - Monolithic architecture may require refactoring beyond few thousand users
  - WebSocket performance limitations compared to specialized solutions

#### PostgreSQL
- **Usage**: Primary database for all application data including users, campaigns, characters, and game rules
- **Pros**:
  - Strong consistency guarantees for critical gaming data integrity
  - Excellent performance with proper indexing for MVP scale
  - Support for complex relationships between game entities
- **Cons**:
  - Query optimization required for complex relational chains as data grows
  - Single point of failure without replication (acceptable for MVP)

#### Redis
- **Usage**: Caching layer for performance optimization and Django Channels backend for WebSocket message routing
- **Pros**:
  - Essential pub/sub capabilities for real-time chat message distribution
  - Simple single-instance setup sufficient for MVP
  - Reduces database load for repeated rule lookups during gaming sessions
- **Cons**:
  - Additional infrastructure component to monitor
  - Potential bottleneck for WebSocket scaling beyond MVP

### Frontend Application

#### React + TypeScript (Web App Only)
- **Usage**: Single Progressive Web App serving all users across desktop and mobile devices
- **Pros**:
  - Focus development effort on single, high-quality interface
  - PWA capabilities provide app-like experience without app store complexity
  - Excellent WebSocket support for seamless real-time chat integration
  - Mobile-responsive design covers tablet and phone usage adequately
- **Cons**:
  - Mobile experience may be less polished than native apps
  - Limited access to device-specific features

### Development Environment

#### Conda Environment
- **Usage**: Complete development environment management including Python, PostgreSQL, Redis, and Node.js
- **Pros**:
  - Single command setup for all dependencies and services
  - Cross-platform consistency for solo development
  - Version pinning ensures reproducible builds
- **Cons**:
  - Environment file maintenance required when adding dependencies

#### Browser Caching Strategy
- **Usage**: Service Worker and browser caching for performance optimization
- **Pros**:
  - Standard web performance patterns with minimal implementation complexity
  - Improves perceived performance during gaming sessions
- **Cons**:
  - Cache invalidation strategy needed when game data updates

---

## Section II: Architecture Decisions

### 1. System Architecture Pattern
- **Decision**: Domain-Driven Monolithic Architecture
- **Rationale**: Game mechanics require tight integration between characters, locations, items, campaigns, and rules
- **Implementation**: Single Django project with multiple Django apps organized around RPG domain concepts
- **Key Principle**: Software architecture follows tabletop RPG organizational patterns

### 2. Real-Time Architecture
- **Decision**: Character-Based Scene Architecture with Lifecycle Management
- **Core Pattern**: Scenes track characters as participants, allowing multi-character and multi-scene gameplay
- **Scene Lifecycle**: Scenes can be created by any participant, managed through active/closed states, with persistent chat history
- **WebSocket Strategy**: Single connection per player with dynamic subscriptions to multiple scene channels

### 3. Authentication & Authorization Architecture
- **Decision**: Hierarchical Role-Based Access Control with Game System Domains
- **Role Hierarchy**: Owner → GM → Player → Observer with transferable ownership
- **GM Domains**: Multiple GMs can control specific game systems within shared campaigns (e.g., Vampire GM vs. Mage GM)
- **Public Campaigns**: Optional discoverability with automatic observer access

### 4. Data Architecture
- **Decision**: Polymorphic Character Model with Template System
- **Approach**: Structured database columns over JSONB for query performance
- **Character Inheritance**: Base Character model with game-specific subclasses (WoDCharacter, DnDCharacter, etc.)
- **Template Library**: Separate character templates for importing official NPCs and reusable characters

---

## Section III: Database Design

### Character Model Hierarchy
```python
# Base model with shared fields
Character (name, player, campaign, created_date, status)
├── WoDCharacter (attributes, willpower, health_levels)
│   ├── VampireCharacter (blood_pool, generation, clan)
│   ├── MageCharacter (arete, paradox, sphere_ratings)
│   └── WerewolfCharacter (rage, gnosis, crinos_form)
├── DnDCharacter (level, hit_points, armor_class)
│   ├── DnD5eCharacter (proficiency_bonus, spell_slots)
│   └── PathfinderCharacter (base_attack_bonus, saves)
└── CustomCharacter (for homebrew systems)
```

### Core Entity Relationships
```python
# Campaign-specific active characters
CampaignCharacter (belongs to one campaign)
├── Inherits from game-specific types (VampireCharacter, MageCharacter, etc.)
├── ForeignKey to Campaign (one-to-many)
├── ForeignKey to Player/GM (ownership)
└── ManyToMany to Scenes (participation)

# Template characters for importing
TemplateCharacter (no campaign association)
├── Same inheritance hierarchy as CampaignCharacter
├── Tagged with source (official, homebrew, user-created)
├── Public/private visibility settings
└── Version/edition information for game system compatibility

# Character creation workflow
CharacterImport (tracks copy relationships)
├── Source template or character
├── Destination campaign character
└── Import metadata (date, modifications made)
```

### Scene and Message Data Model
```python
Campaign
├── Campaign Settings (multi-scene rules, permissions)
├── Scenes
│   ├── Scene Metadata (name, description, creator, status, timestamps)
│   ├── Scene Status (active, closed, archived)
│   ├── Character Participants (many-to-many relationship)
│   ├── Scene Closure Data (XP awards, loot distribution, GM notes)
│   └── Messages (persistent, immutable after scene closure)
│       ├── Speaking Character (which character said this)
│       ├── Message Content
│       ├── Message Type (public, GM private, whisper, system)
│       ├── Timestamps (created, edited)
│       └── Visibility Rules
└── Characters
    ├── Player Owner
    └── Scene Memberships (potentially multiple)
```

### Character Ownership & Modification Control
- **Creation Phase**: Players have complete control during initial character creation
- **Advancement Workflow**: Player-initiated character advancement requires GM approval before taking effect
- **GM Authority**: GMs can make direct character modifications (damage, equipment, status effects) without approval
- **System Automation**: Automated changes (dice roll results, spell effects) apply immediately but may be subject to GM override

### Template Character Features
- **Template Library**: Searchable database of official NPCs, sample characters, and community-created templates
- **Cross-Campaign Copying**: Players can copy their characters to new campaigns
- **Stat Preservation**: All mechanical stats, equipment, and progression copied exactly
- **Official Character Library**: Template database includes signature NPCs from official game materials (e.g., Porthos Fitz-Empress, Senex for Mage games)

### Data Consistency Strategy
- **Decision**: Defer until real-world usage data is available
- **Initial Approach**: Rely on Django's default database behavior and PostgreSQL's ACID properties
- **Philosophy**: Avoid over-engineering for theoretical problems until evidence shows they're real problems

---

## Section IV: API Design

### 1. Endpoint Organization Strategy
- **Decision**: Flat URL patterns with rich query parameter filtering
- **Rationale**: Provides maximum flexibility for partial resource access and complex filtering without requiring full hierarchical URL construction

#### Example Endpoint Patterns
```
# Flat resource patterns
/api/campaigns/
/api/scenes/?campaign_id={id}
/api/characters/?campaign_id={id}
/api/messages/?scene_id={id}&character_id={id}&date_from={date}
/api/templates/?game_system=vampire&category=npc
```

### 2. WebSocket Message Format
- **Decision**: Mirror REST API data structures for consistency
- **Implementation**: Same structure as REST API response with additional WebSocket metadata

#### Message Structure Pattern
```json
{
  "type": "message",
  "action": "create|update|delete",
  "data": {
    // Same structure as REST API response
    "scene_id": 123,
    "character_id": 456,
    "content": "Hello everyone!",
    "message_type": "public",
    "timestamp": "2025-01-15T10:30:00Z"
  },
  "metadata": {
    "sequence": 12345,
    "channel": "campaign_1_scene_123"
  }
}
```

### 3. Authentication Strategy
- **Decision**: Django's built-in session-based authentication
- **Implementation**: Standard Django sessions with database-backed permission checking
- **Permission Checking**: View-level decorators, model-level filtered querysets, and WebSocket per-message validation

### 4. Rate Limiting Strategy
- **Decision**: Conservative rate limits based on tabletop gaming pace
- **Standard Users**: 10 requests per minute, 5 chat messages per minute per scene
- **GMs**: 2x standard limits for managing more game elements
- **Rationale**: RPG sessions are conversational and turn-based, requiring few API calls per user per minute

---

## Section V: Frontend Architecture

### 1. State Management Strategy
- **Decision**: Start with React's built-in state management (useState, useContext)
- **Rationale**: Simpler learning curve for developer with Django templates experience
- **Evolution Path**: Can migrate to Redux or other solutions later if state complexity grows

### 2. Responsive Design Strategy
- **Decision**: Desktop-first responsive design with mobile adaptation
- **Primary Use Case**: Active gaming sessions require desktop experience for optimal functionality
- **Secondary Use Case**: Mobile provides character sheet reference and light campaign access

### 3. Real-time Chat Integration
- **Decision**: Chat integrated directly into scene views
- **Implementation**: Each scene view contains its own integrated chat interface
- **Benefits**: Chat context always matches current game scene, aligns with scene-based data model

### 4. Navigation Pattern
- **Decision**: Tab-based navigation within campaigns
- **Implementation**: Campaign selector leads to tabbed interface for all campaign-related activities
- **Campaign Tabs**: Scenes, Characters, Rules, Templates, Management (role-based visibility)

---

## Section VI: Development Phases

### Django App Structure & MVP Definition

#### Target MVP: Functional Mage: the Ascension Game Management System

**Core Django Apps:**
- **users**: Authentication, profiles, campaign role management
- **campaigns**: Campaign creation, game system selection (World of Darkness + edition), membership, analytics
- **scenes**: Scene lifecycle management, character participation, real-time chat, dice rolling
- **characters**: Character models, game system logic, character sheets
- **locations**: Campaign locations with hierarchical organization
- **items**: Equipment and treasure management
- **api**: DRF views, serializers, WebSocket routing for all functionality
- **core**: Front page, global utilities, base templates

### MVP Requirements by App

#### users (Largely Complete)
- User authentication and registration
- Campaign role management (Owner/GM/Player/Observer)
- User profiles and preferences
- Permission system integration

#### campaigns (Game System Foundation)
- Campaign creation and basic management
- Game system selection: World of Darkness with edition specification
- Campaign membership and role assignment
- Basic campaign settings and configuration

#### scenes (Full Lifecycle Implementation)
- Complete scene lifecycle: active → closing → closed → archived
- Character participation management (add/remove characters from scenes)
- Real-time chat integration with WebSocket support
- Dice rolling system with World of Darkness mechanics
- Scene closure workflow (XP distribution, loot allocation)

#### characters (Full Mage Character Management)
- Complete Mage: the Ascension character sheet implementation
- Polymorphic character models (WoDCharacter → MageCharacter)
- Full game mechanics: Arete, Sphere ratings, Paradox, Willpower, Health
- Character advancement system with GM approval workflow
- Character creation and progression tracking

#### locations (Basic Hierarchy)
- Location creation with name and description
- Hierarchical organization (locations within locations)
- Campaign-specific locations
- Basic location management interface

#### items (Minimal Implementation)
- Item creation with name and description
- Basic item management
- Campaign-specific items

#### api (Complete API Coverage)
- RESTful APIs for all app functionality
- WebSocket integration for real-time features
- Authentication and permission enforcement
- Internal system operations routed through API

#### core (Essential Infrastructure)
- Application front page and landing
- Global utilities and helper functions
- Base template system
- Application-wide configuration

### MVP Development Phases

#### Phase 1: Generic Campaign Infrastructure
**Goal**: "Could run a campaign with no mechanical stuff" functionality
- **users**: Complete authentication, profiles, basic campaign roles
- **campaigns**: Campaign creation, membership management, basic settings
- **scenes**: Scene creation, character participation, basic chat (no dice yet)
- **characters**: Base Character model with django-polymorphic setup
  - Metadata only: name, description, player_owner, campaign, created_date
  - No statistics or game mechanics in base class
  - Polymorphic foundation ready for game-specific subclasses
- **locations**: Generic locations with name, description, hierarchy
- **items**: Generic items with name, description
- **api**: RESTful APIs for all basic CRUD operations
- **core**: Front page, navigation, basic UI framework

**Milestone**: Users can create campaigns, add generic characters, create scenes, and chat

#### Phase 2: World of Darkness Foundation
**Goal**: Implement WoD base classes and game system selection
- **campaigns**: Game system selection (World of Darkness + edition) with inheritance enforcement
- **characters**: WoDCharacter subclass with Attributes, Abilities, Willpower, Health
  - Inherits from base Character using django-polymorphic
  - Campaign validation ensures only WoD characters in WoD campaigns
- **items**: WoDItem base class for game-specific items
- **locations**: WoDLocation base class if needed for game-specific location types
- **scenes**: WoD dice rolling system (difficulty, successes, botches)
- **api**: Game system-aware serializers and polymorphic model handling

**Milestone**: Campaign creation locked to WoD, basic WoD dice mechanics work, character sheets have WoD structure

#### Phase 3: Mage Character Implementation  
**Goal**: Full Mage: the Ascension character creation and play mechanics
- **characters**: MageCharacter subclass inheriting from WoDCharacter
  - Spheres, Arete, Paradox, Resonance, Avatar
  - Mage-specific character sheet interface
- **scenes**: Mage-specific dice mechanics (Arete + Sphere rolls, Paradox accumulation)
- **characters**: Character advancement system with sphere progression, Arete increases
- **characters**: GM approval workflow for character advancement
- **api**: Mage-specific character operations and polymorphic validation

**Milestone**: Complete Mage character sheets, sphere magic mechanics, character progression

#### Phase 4: Polish & Production Readiness
**Goal**: Production deployment and user experience refinement
- **scenes**: Scene closure workflow with XP distribution
- **campaigns**: Campaign analytics and progression tracking  
- **all apps**: Error handling, validation, performance optimization
- **core**: Production deployment configuration
- **api**: Rate limiting, security hardening

#### Django-Polymorphic Implementation Strategy
- **Phase 1**: Base models with polymorphic setup, no subclasses yet
- **Phase 2**: First level of inheritance (WoDCharacter, WoDItem, etc.)
- **Phase 3**: Second level inheritance (MageCharacter from WoDCharacter)
- **API Design**: Polymorphic serializers handle type-specific fields automatically

**Benefits of This Approach**:
- Clean separation between generic campaign management and game mechanics
- Game system abstraction prevents cross-contamination from day one
- Django-polymorphic foundation supports easy addition of new game systems later
- Can validate core workflows before implementing complex character mechanics