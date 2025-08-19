# GMA Database Schema Documentation

## Table of Contents

1. [Schema Overview](#schema-overview)
2. [Core Models](#core-models)
3. [Campaign Domain](#campaign-domain)
4. [User Domain](#user-domain)
5. [Authentication and Sessions](#authentication-and-sessions)
6. [Real-time Features](#real-time-features)
7. [Relationship Diagrams](#relationship-diagrams)
8. [Indexes and Performance](#indexes-and-performance)
9. [Data Migration Patterns](#data-migration-patterns)
10. [Query Optimization](#query-optimization)

## Schema Overview

The GMA database schema is designed around domain-driven principles with clear separation of concerns:

- **User Management**: Authentication, profiles, preferences
- **Campaign Management**: Campaigns, memberships, invitations
- **Content Management**: Characters, scenes, items, locations
- **Real-time Features**: Health checks, notifications
- **System Management**: Migrations, admin logs
- **State Management**: Workflow transitions using django-fsm-2

### Database Technology

- **PostgreSQL 16** as the primary database
- **UTF-8 encoding** for international character support
- **Row-level security** for multi-tenant data isolation
- **JSONB fields** for flexible configuration storage
- **Full-text search** capabilities for content discovery
- **State management** with django-fsm-2 for workflow transitions

## Core Models

### Book Model

**Table**: `core_book`

Stores canonical RPG source books with metadata for citations and references throughout the application.

```sql
CREATE TABLE core_book (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) UNIQUE NOT NULL,
    abbreviation VARCHAR(20) UNIQUE NOT NULL,
    system VARCHAR(100) NOT NULL,
    edition VARCHAR(50) DEFAULT '' NOT NULL,
    publisher VARCHAR(100) DEFAULT '' NOT NULL,
    isbn VARCHAR(17) DEFAULT '' NOT NULL,  -- ISBN-13 with hyphens: 978-0-123456-78-9
    url VARCHAR(200) DEFAULT '' NOT NULL
);

-- Performance indexes
CREATE INDEX core_book_system_idx ON core_book (system);
CREATE INDEX core_book_title_idx ON core_book (title);
```

**Field Specifications:**

**Core Fields:**
- `title`: Full book title (VARCHAR 200, UNIQUE, required)
- `abbreviation`: Short book abbreviation (VARCHAR 20, UNIQUE, required)
  - Examples: "M20" for Mage 20th Anniversary, "V20" for Vampire 20th Anniversary
- `system`: Game system this book belongs to (VARCHAR 100, required)
  - Examples: "Mage: The Ascension", "Vampire: The Masquerade", "Werewolf: The Apocalypse"

**Optional Metadata:**
- `edition`: Edition information (VARCHAR 50, optional)
  - Examples: "Revised", "20th Anniversary", "2nd Edition"
- `publisher`: Book publisher (VARCHAR 100, optional)
  - Examples: "Onyx Path Publishing", "White Wolf Publishing", "Modiphius Entertainment"
- `isbn`: ISBN-10 or ISBN-13 identifier (VARCHAR 17, optional)
  - Supports both formats with or without hyphens
- `url`: Purchase or information URL (URLField, optional)
  - DriveThruRPG links, publisher websites, etc.

**Business Rules:**
- Book titles must be unique across all systems
- Abbreviations must be unique across all systems
- System field is required for proper categorization
- All optional fields default to empty string (not NULL)
- Ordering by system, then title for consistent display

**Usage Patterns:**
```sql
-- Find books by game system
SELECT * FROM core_book
WHERE system = 'Mage: The Ascension'
ORDER BY title;

-- Search books by title or abbreviation
SELECT * FROM core_book
WHERE title ILIKE '%players guide%'
   OR abbreviation ILIKE '%pg%';

-- Get book by abbreviation (common usage)
SELECT * FROM core_book
WHERE abbreviation = 'M20';

-- Find books by publisher
SELECT * FROM core_book
WHERE publisher = 'Onyx Path Publishing'
ORDER BY system, title;
```

**Performance Considerations:**
- Index on `system` field for game system filtering
- Index on `title` field for search operations
- Unique constraints on `title` and `abbreviation` provide implicit indexes
- Consider full-text search index for complex title searches

**Future Enhancements:**
- Foreign key relationships to character sheets, items, or other content
- Book ratings or review system
- Publication date tracking
- Multi-language support for international editions

### SourceReference Model

**Table**: `core_sourcereference`

Links any model in the application to source books with optional page and chapter references using Django's GenericForeignKey system.

```sql
CREATE TABLE core_sourcereference (
    id SERIAL PRIMARY KEY,
    book_id INTEGER NOT NULL REFERENCES core_book(id) ON DELETE CASCADE,
    content_type_id INTEGER NOT NULL REFERENCES django_content_type(id) ON DELETE CASCADE,
    object_id INTEGER NOT NULL,
    page_number INTEGER CHECK (page_number > 0),
    chapter TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
);

-- Performance indexes
CREATE INDEX core_sourcereference_content_type_idx ON core_sourcereference (content_type_id);
CREATE INDEX core_sourcereference_object_id_idx ON core_sourcereference (object_id);
CREATE INDEX core_sourcereference_content_type_object_id_idx ON core_sourcereference (content_type_id, object_id);
CREATE INDEX core_sourcereference_book_page_number_idx ON core_sourcereference (book_id, page_number);
```

**Field Specifications:**

**Required Fields:**
- `book`: ForeignKey to Book model (CASCADE delete, required)
- `content_type`: ForeignKey to Django's ContentType (CASCADE delete, required)
- `object_id`: PositiveIntegerField for the linked object's ID (required)
- `content_object`: GenericForeignKey combining content_type and object_id

**Optional Reference Details:**
- `page_number`: PositiveIntegerField for specific page references (optional)
  - Must be positive integer if provided
  - Null allowed for general book references
- `chapter`: TextField for chapter or section names (optional)
  - Supports full chapter titles or section identifiers
  - Null allowed for page-only or general references

**Inherited Fields (from TimestampedMixin):**
- `created_at`: Automatic creation timestamp (indexed)
- `updated_at`: Automatic modification timestamp (indexed)

**Business Rules:**
- Each source reference must link to exactly one Book
- Each source reference must link to exactly one content object via GenericForeignKey
- Page numbers must be positive integers when provided
- References are ordered by book abbreviation, then page number
- Cascade deletion when referenced book or content object is deleted

**Usage Patterns:**
```sql
-- Find all source references for a specific object
SELECT sr.*, b.title, b.abbreviation
FROM core_sourcereference sr
JOIN core_book b ON sr.book_id = b.id
JOIN django_content_type ct ON sr.content_type_id = ct.id
WHERE ct.app_label = 'characters'
  AND ct.model = 'character'
  AND sr.object_id = 123;

-- Find all references to a specific book
SELECT sr.*, ct.app_label, ct.model, sr.object_id
FROM core_sourcereference sr
JOIN django_content_type ct ON sr.content_type_id = ct.id
WHERE sr.book_id = 1
ORDER BY sr.page_number;

-- Find references with specific page numbers
SELECT sr.*, b.abbreviation, sr.page_number
FROM core_sourcereference sr
JOIN core_book b ON sr.book_id = b.id
WHERE sr.page_number BETWEEN 100 AND 200
ORDER BY b.abbreviation, sr.page_number;

-- Find references by chapter
SELECT sr.*, b.title, sr.chapter
FROM core_sourcereference sr
JOIN core_book b ON sr.book_id = b.id
WHERE sr.chapter ILIKE '%magic%'
ORDER BY b.system, sr.chapter;
```

**Performance Considerations:**
- Compound index on `(content_type_id, object_id)` for efficient object lookup
- Compound index on `(book_id, page_number)` for book browsing
- Individual indexes on `content_type_id` and `object_id` for general queries
- Consider adding `book_id` index if frequently filtering by book alone

**Common Query Patterns:**
```python
# Django ORM patterns for efficient querying

# Get all source references for an object
references = SourceReference.objects.filter(
    content_type=ContentType.objects.get_for_model(obj),
    object_id=obj.id
).select_related('book').order_by('book__abbreviation', 'page_number')

# Get references with specific details
detailed_refs = SourceReference.objects.filter(
    book__system='Mage: The Ascension',
    page_number__isnull=False
).select_related('book').prefetch_related('content_object')

# Reverse lookup from Book to all references
book_references = SourceReference.objects.filter(
    book=book
).select_related('content_type').order_by('page_number')
```

**Integration Examples:**

This model enables source attribution across the entire application:

```python
# Character with source reference
character = Character.objects.create(name="Mage Character")
SourceReference.objects.create(
    book=mage_book,
    content_object=character,
    page_number=65,
    chapter="Character Creation"
)

# Spell with multiple source references
spell = Spell.objects.create(name="Mind Reading")
SourceReference.objects.create(
    book=mage_core_book,
    content_object=spell,
    page_number=205
)
SourceReference.objects.create(
    book=mind_sphere_guide,
    content_object=spell,
    chapter="Advanced Mind Magic"
)

# Campaign setting with general reference
setting = CampaignSetting.objects.create(name="Technocracy")
SourceReference.objects.create(
    book=technocracy_book,
    content_object=setting
    # No page or chapter - general reference to entire book
)
```

**Future Enhancements:**
- Quote or excerpt field for storing specific text references
- Confidence or accuracy rating for community-contributed references
- Version tracking for references that change between book editions
- Bulk import tools for existing source attribution data

### Core Model Mixins

The GMA system provides reusable model mixins that encapsulate common functionality needed across multiple models. These mixins include performance optimizations such as database indexing and comprehensive help text.

#### TimestampedMixin

**Location**: `core/models/mixins.py:30-56`
**Purpose**: Automatic timestamp tracking for model creation and updates with performance optimization

```sql
-- Fields added by TimestampedMixin (with performance indexes)
created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,

-- Automatic indexes for performance
CREATE INDEX <table>_created_at_idx ON <table> (created_at);
CREATE INDEX <table>_updated_at_idx ON <table> (updated_at);
```

**Field Specifications:**

- `created_at`: Automatically set on model creation (`auto_now_add=True`, indexed)
- `updated_at`: Automatically updated on every model save (`auto_now=True`, indexed)
- Both fields use timezone-aware timestamps
- Both fields are non-nullable with automatic defaults
- Both fields include comprehensive help text for admin interface
- **Performance**: Both fields are indexed (`db_index=True`) for efficient date-based queries

#### DisplayableMixin

**Location**: `core/models/mixins.py:58-83`
**Purpose**: Control display visibility and ordering with performance optimization

```sql
-- Fields added by DisplayableMixin
is_displayed BOOLEAN DEFAULT true NOT NULL,
display_order INTEGER DEFAULT 0 NOT NULL,

-- Performance index for ordering
CREATE INDEX <table>_display_order_idx ON <table> (display_order);
```

**Field Specifications:**

- `is_displayed`: Boolean flag controlling visibility (default: `True`)
- `display_order`: Integer for custom ordering (default: `0`, indexed for performance)
- **Performance**: `display_order` field is indexed for efficient ordering queries
- Consider composite indexes like `(is_displayed, display_order)` for heavy-use models

#### NamedModelMixin

**Location**: `core/models/mixins.py:85-108`
**Purpose**: Standardized name field with string representation

```sql
-- Fields added by NamedModelMixin
name VARCHAR(100) NOT NULL
```

**Field Specifications:**

- `name`: Required CharField with 100 character limit
- Provides `__str__()` method returning the name
- **Performance**: Consider adding `db_index=True` if frequently searching by name

#### DescribedModelMixin

**Location**: `core/models/mixins.py:110-130`
**Purpose**: Optional description field for detailed information

```sql
-- Fields added by DescribedModelMixin
description TEXT DEFAULT '' NOT NULL
```

**Field Specifications:**

- `description`: Optional TextField with blank=True and default empty string
- **Performance**: Not indexed by default (appropriate for large text fields)
- Use `description__icontains` for text search, consider full-text search for large datasets

#### AuditableMixin

**Location**: `core/models/mixins.py:132-189`
**Purpose**: User audit tracking with automatic user management

```sql
-- Fields added by AuditableMixin
created_by_id INTEGER REFERENCES users_user(id) ON DELETE CASCADE,
modified_by_id INTEGER REFERENCES users_user(id) ON DELETE CASCADE
```

**Field Specifications:**

- `created_by`: Optional ForeignKey to User who created the object
- `modified_by`: Optional ForeignKey to User who last modified the object
- **Enhanced save() method**: Accepts `user` parameter for automatic tracking
- **Performance**: Use `select_related('created_by', 'modified_by')` for efficient queries

**Automatic User Tracking:**

```python
# Automatic user tracking
obj.save(user=request.user)  # Sets modified_by and created_by for new objects

# Manual tracking still works
obj.created_by = user
obj.save()
```

#### GameSystemMixin

**Location**: `core/models/mixins.py:191-235`
**Purpose**: Game system selection for campaign-related models

```sql
-- Fields added by GameSystemMixin
game_system VARCHAR(50) DEFAULT 'generic' NOT NULL
    CHECK (game_system IN ('generic', 'wod', 'mage', 'vampire', ...))
```

**Field Specifications:**

- `game_system`: CharField with predefined choices for popular RPG systems
- Default value: `'generic'`
- **Performance**: Choices are efficient for filtering, consider `db_index=True` for frequent filtering

### Mixin Performance Optimizations

**Database Indexes:**
All mixins include strategic database indexing for commonly queried fields:

- `TimestampedMixin`: Indexes on `created_at` and `updated_at` for time-based queries
- `DisplayableMixin`: Index on `display_order` for efficient sorting
- `AuditableMixin`: Foreign key indexes automatically created by Django
- `GameSystemMixin`: Consider adding index if filtering by game_system frequently

**Help Text Documentation:**
All mixin fields include comprehensive help text visible in:

- Django admin interface
- API documentation
- Development tools
- Database schema documentation

**Usage Guidelines:**

- Use `select_related()` when querying models with audit tracking
- Consider composite indexes for models using multiple mixins
- Monitor query performance and add additional indexes as needed

**Use TimestampedMixin when:**

- Creating new models that need basic timestamp tracking
- Standardized timestamp behavior is desired
- No custom timestamp logic is required

**Don't use TimestampedMixin when:**

- Model already has timestamp fields (e.g., Campaign, Character)
- Custom timestamp behavior is needed
- Timestamp tracking isn't required for the model

**Implementation Example:**

```python
from core.models.mixins import TimestampedMixin

class GameSession(TimestampedMixin):
    """Example model using TimestampedMixin."""
    name = models.CharField(max_length=200)
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE)

    # TimestampedMixin automatically provides:
    # created_at and updated_at fields
```

### State Machine Fields

The GMA system uses **django-fsm-2** for managing model state transitions. State machine fields provide workflow management for campaigns, scenes, and characters.

#### FSMField Database Schema

**Basic State Field:**

```sql
-- State field with choices constraint
status VARCHAR(50) DEFAULT 'draft' NOT NULL
    CHECK (status IN ('draft', 'active', 'completed', 'cancelled'))
```

**State Field with Index:**

```sql
-- State field optimized for filtering
state VARCHAR(50) DEFAULT 'pending' NOT NULL,

-- Index for efficient state-based queries
CREATE INDEX <table>_state_idx ON <table> (state);
```

#### State Machine Integration Patterns

**Campaign State Management:**

```python
# Future implementation example
from django_fsm import FSMField, transition

class Campaign(models.Model):
    # Existing fields...
    state = FSMField(default='draft', max_length=50)

    @transition(field=state, source='draft', target='active')
    def activate(self):
        """Activate campaign for player participation."""
        pass
```

**Database Impact:**

```sql
-- Additional field for Campaign table
ALTER TABLE campaigns_campaign
ADD COLUMN state VARCHAR(50) DEFAULT 'draft' NOT NULL;

-- Index for efficient state filtering
CREATE INDEX campaigns_campaign_state_idx
ON campaigns_campaign (state);

-- Constraint for valid states
ALTER TABLE campaigns_campaign
ADD CONSTRAINT campaigns_campaign_state_check
CHECK (state IN ('draft', 'active', 'completed', 'archived'));
```

#### State Transition Audit Trail

**Future Enhancement - State History:**

```sql
-- State transition log table
CREATE TABLE core_statetransitionlog (
    id SERIAL PRIMARY KEY,
    content_type_id INTEGER NOT NULL REFERENCES django_content_type(id),
    object_id INTEGER NOT NULL,

    -- Transition details
    from_state VARCHAR(50) NOT NULL,
    to_state VARCHAR(50) NOT NULL,
    transition_method VARCHAR(100) NOT NULL,

    -- Audit information
    user_id INTEGER REFERENCES users_user(id) ON DELETE SET NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    notes TEXT DEFAULT ''
);

-- Indexes for efficient querying
CREATE INDEX statetransition_content_object_idx
ON core_statetransitionlog (content_type_id, object_id);

CREATE INDEX statetransition_timestamp_idx
ON core_statetransitionlog (timestamp DESC);
```

#### Character Status Query Patterns

**Filtering by Character Status:**

```sql
-- Get all approved characters in a campaign
SELECT * FROM characters_character
WHERE campaign_id = ? AND status = 'APPROVED' AND is_deleted = false;

-- Get characters pending approval
SELECT * FROM characters_character
WHERE campaign_id = ? AND status = 'SUBMITTED' AND is_deleted = false;

-- Get all draft characters owned by a player
SELECT * FROM characters_character
WHERE player_owner_id = ? AND status = 'DRAFT' AND is_deleted = false;

-- Character status distribution for a campaign
SELECT
    status,
    npc,
    COUNT(*) as count
FROM characters_character
WHERE campaign_id = ? AND is_deleted = false
GROUP BY status, npc
ORDER BY status, npc;

-- Characters by status priority (for GM dashboard)
SELECT * FROM characters_character
WHERE campaign_id = ? AND is_deleted = false
ORDER BY
    CASE status
        WHEN 'SUBMITTED' THEN 1  -- Needs attention
        WHEN 'APPROVED' THEN 2   -- Active characters
        WHEN 'DRAFT' THEN 3      -- In progress
        WHEN 'INACTIVE' THEN 4   -- Temporarily out
        WHEN 'RETIRED' THEN 5    -- Historical
        WHEN 'DECEASED' THEN 6   -- Historical
        ELSE 7
    END,
    updated_at DESC;
```

#### State-Based Query Patterns (Campaigns)

**Filtering by State:**

```sql
-- Active campaigns only
SELECT * FROM campaigns_campaign
WHERE state = 'active' AND is_public = true;

-- Campaigns by state priority
SELECT * FROM campaigns_campaign
ORDER BY
    CASE state
        WHEN 'active' THEN 1
        WHEN 'draft' THEN 2
        WHEN 'completed' THEN 3
        ELSE 4
    END,
    updated_at DESC;
```

**Character Status Transition Analytics:**

```sql
-- Character status distribution analysis
SELECT
    status,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
FROM characters_character
WHERE is_deleted = false
GROUP BY status
ORDER BY count DESC;

-- Recent character status changes
SELECT
    c.name as character_name,
    camp.name as campaign_name,
    (audit.field_changes->'status'->>'old') as from_status,
    (audit.field_changes->'status'->>'new') as to_status,
    audit.timestamp,
    u.username as changed_by
FROM characters_character_audit audit
JOIN characters_character c ON audit.character_id = c.id
JOIN campaigns_campaign camp ON c.campaign_id = camp.id
JOIN users_user u ON audit.changed_by_id = u.id
WHERE audit.field_changes ? 'status'
ORDER BY audit.timestamp DESC
LIMIT 10;

-- Character approval workflow metrics
SELECT
    camp.name as campaign_name,
    COUNT(*) FILTER (WHERE c.status = 'DRAFT') as draft_count,
    COUNT(*) FILTER (WHERE c.status = 'SUBMITTED') as submitted_count,
    COUNT(*) FILTER (WHERE c.status = 'APPROVED') as approved_count,
    COUNT(*) FILTER (WHERE c.status = 'INACTIVE') as inactive_count,
    COUNT(*) FILTER (WHERE c.status = 'RETIRED') as retired_count,
    COUNT(*) FILTER (WHERE c.status = 'DECEASED') as deceased_count
FROM characters_character c
JOIN campaigns_campaign camp ON c.campaign_id = camp.id
WHERE c.is_deleted = false
GROUP BY camp.id, camp.name
ORDER BY camp.name;
```

**State Transition Analytics (Campaigns):**

```sql
-- State distribution analysis
SELECT
    state,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
FROM campaigns_campaign
GROUP BY state
ORDER BY count DESC;

-- Recent state changes (with future audit table)
SELECT
    c.name as campaign_name,
    stl.from_state,
    stl.to_state,
    stl.timestamp,
    u.username as changed_by
FROM core_statetransitionlog stl
JOIN campaigns_campaign c ON stl.object_id = c.id
JOIN users_user u ON stl.user_id = u.id
WHERE stl.content_type_id = (
    SELECT id FROM django_content_type
    WHERE app_label = 'campaigns' AND model = 'campaign'
)
ORDER BY stl.timestamp DESC
LIMIT 10;
```

#### Performance Considerations

**Character Status Field Indexing:**

- Status field is indexed for efficient filtering
- Composite index on (campaign_id, status) for common query patterns
- Database CHECK constraint ensures data integrity
- Consider partial indexes for specific status combinations

**Query Optimization:**

```sql
-- Efficient status-based filtering with composite index
CREATE INDEX characters_campaign_status_approved_idx
ON characters_character (campaign_id, updated_at DESC)
WHERE status = 'APPROVED' AND is_deleted = false;

-- Efficient owner + status queries
CREATE INDEX characters_owner_status_idx
ON characters_character (player_owner_id, status)
WHERE is_deleted = false;

-- Audit trail optimization for status changes
CREATE INDEX characters_audit_status_timeline_idx
ON characters_character_audit (character_id, timestamp DESC)
WHERE field_changes ? 'status';
```

**State Field Indexing (General):**

- Always index state fields for efficient filtering
- Consider composite indexes for state + other frequently queried fields
- Use partial indexes for specific state combinations

**Query Optimization (General):**

```sql
-- Efficient state-based filtering with composite index
CREATE INDEX campaigns_active_updated_idx
ON campaigns_campaign (state, updated_at DESC)
WHERE state = 'active';

-- Efficient owner + state queries
CREATE INDEX campaigns_owner_state_idx
ON campaigns_campaign (owner_id, state);
```

**State Validation:**

- Use database constraints to enforce valid state values
- Consider using ENUMs for better type safety (PostgreSQL)
- Document state transition rules in application code

**Database Schema Impact:**

```sql
-- Generated table with TimestampedMixin
CREATE TABLE example_gamesession (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    campaign_id INTEGER NOT NULL REFERENCES campaigns_campaign(id),

    -- From TimestampedMixin
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
);
```

**Indexing Considerations:**

- Consider adding indexes on `created_at` for time-based queries
- Consider adding indexes on `updated_at` for "recently modified" queries
- Composite indexes may be useful for filtering by status + timestamp

```sql
-- Example indexes for timestamp fields
CREATE INDEX idx_gamesession_created ON example_gamesession (created_at);
CREATE INDEX idx_gamesession_updated ON example_gamesession (updated_at DESC);
```

### Campaign Model

**Table**: `campaigns_campaign`

The central entity around which all game content is organized.

```sql
CREATE TABLE campaigns_campaign (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    slug VARCHAR(200) UNIQUE NOT NULL,
    description TEXT DEFAULT '',

    -- Ownership and access control
    owner_id INTEGER NOT NULL REFERENCES users_user(id) ON DELETE CASCADE,
    is_active BOOLEAN DEFAULT true NOT NULL,
    is_public BOOLEAN DEFAULT false NOT NULL,

    -- Self-service join options
    allow_observer_join BOOLEAN DEFAULT false NOT NULL,
    allow_player_join BOOLEAN DEFAULT false NOT NULL,

    -- Game system
    game_system VARCHAR(100) DEFAULT '',

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
);
```

**Key Features:**

- **Auto-generated slug**: URL-friendly unique identifier
- **Visibility control**: Public/private campaign access
- **Owner cascade deletion**: When owner is deleted, campaign is removed
- **Join permissions**: Configurable self-service joining

**Relationships:**

- **Owner**: Many campaigns → One user (owner)
- **Members**: Many-to-many through CampaignMembership
- **Invitations**: One campaign → Many invitations

### CampaignMembership Model

**Table**: `campaigns_campaignmembership`

Manages user participation in campaigns with role-based access.

```sql
CREATE TABLE campaigns_campaignmembership (
    id SERIAL PRIMARY KEY,
    campaign_id INTEGER NOT NULL REFERENCES campaigns_campaign(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users_user(id) ON DELETE CASCADE,

    -- Role hierarchy: OWNER > GM > PLAYER > OBSERVER
    role VARCHAR(20) NOT NULL CHECK (role IN ('OWNER', 'GM', 'PLAYER', 'OBSERVER')),

    joined_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,

    -- Prevent duplicate memberships
    UNIQUE(campaign_id, user_id)
);
```

**Business Rules:**

- **Unique membership**: One membership per user per campaign
- **Role hierarchy**: Defines permission levels
- **Cascade deletion**: Remove membership when campaign or user deleted
- **Owner exclusion**: Campaign owner cannot be a member (enforced at service layer)

### CampaignInvitation Model

**Table**: `campaigns_campaigninvitation`

Manages invitation lifecycle for campaign membership.

```sql
CREATE TABLE campaigns_campaigninvitation (
    id SERIAL PRIMARY KEY,
    campaign_id INTEGER NOT NULL REFERENCES campaigns_campaign(id) ON DELETE CASCADE,
    invited_user_id INTEGER NOT NULL REFERENCES users_user(id) ON DELETE CASCADE,
    invited_by_id INTEGER NOT NULL REFERENCES users_user(id) ON DELETE CASCADE,

    -- Invitation details
    role VARCHAR(20) NOT NULL CHECK (role IN ('GM', 'PLAYER', 'OBSERVER')),
    message TEXT DEFAULT '',

    -- Status tracking
    status VARCHAR(20) DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'ACCEPTED', 'DECLINED', 'EXPIRED')),

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT (now() + INTERVAL '7 days') NOT NULL,

    -- Prevent duplicate invitations
    UNIQUE(campaign_id, invited_user_id, status)
    DEFERRABLE INITIALLY DEFERRED
);
```

**Invitation Lifecycle:**

1. **PENDING**: Invitation created, awaiting response
2. **ACCEPTED**: User accepted and became member
3. **DECLINED**: User declined invitation
4. **EXPIRED**: Invitation expired without response

**Business Rules:**

- **7-day expiration**: Default invitation lifetime
- **No duplicate pending**: One pending invitation per user per campaign
- **Automatic cleanup**: Expired invitations cleaned up periodically

## Campaign Domain

### Character Model

**Table**: `characters_character`

The core character model supporting polymorphic inheritance for different game systems, with unified PC/NPC architecture.

```sql
-- Character base table
CREATE TABLE characters_character (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT DEFAULT '',
    game_system VARCHAR(100) NOT NULL,
    npc BOOLEAN DEFAULT false NOT NULL,  -- PC/NPC unified architecture

    -- Relationships
    campaign_id INTEGER NOT NULL REFERENCES campaigns_campaign(id) ON DELETE CASCADE,
    player_owner_id INTEGER NOT NULL REFERENCES users_user(id) ON DELETE CASCADE,

    -- Polymorphic type tracking
    polymorphic_ctype_id INTEGER NOT NULL REFERENCES django_content_type(id),

    -- Character status workflow (Issue #180)
    status VARCHAR(20) DEFAULT 'DRAFT' NOT NULL
        CHECK (status IN ('DRAFT', 'SUBMITTED', 'APPROVED', 'INACTIVE', 'RETIRED', 'DECEASED')),

    -- Audit trail fields (via DetailedAuditableMixin)
    created_by_id INTEGER REFERENCES users_user(id) ON DELETE SET NULL,
    modified_by_id INTEGER REFERENCES users_user(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,

    -- Soft delete fields
    is_deleted BOOLEAN DEFAULT false NOT NULL,
    deleted_at TIMESTAMP WITH TIME ZONE,
    deleted_by_id INTEGER REFERENCES users_user(id) ON DELETE SET NULL,

    -- Constraints
    CONSTRAINT unique_character_name_per_campaign UNIQUE (campaign_id, name)
);

-- Performance indexes
CREATE INDEX characters_character_npc_idx ON characters_character (npc);  -- NPC filtering
CREATE INDEX characters_character_status_idx ON characters_character (status);  -- Status filtering
CREATE INDEX characters_character_count_idx ON characters_character (campaign_id, player_owner_id);  -- Character limits
CREATE INDEX characters_character_campaign_idx ON characters_character (campaign_id);  -- Campaign queries
CREATE INDEX characters_character_created_at_idx ON characters_character (created_at);  -- Audit queries
CREATE INDEX characters_character_updated_at_idx ON characters_character (updated_at);  -- Audit queries

-- Composite index for common queries
CREATE INDEX characters_character_campaign_status_idx ON characters_character (campaign_id, status);  -- Campaign + status queries
```

**Field Specifications:**

**Core Identity:**

- `name`: Character name, must be unique within campaign (VARCHAR 100, indexed via constraint)
- `description`: Optional character background and description (TEXT, blank allowed)
- `game_system`: Game system identifier (VARCHAR 100, matches campaign system)

**PC/NPC Architecture:**

- `npc`: Boolean flag distinguishing NPCs from PCs (BOOLEAN, default: false, indexed)
  - `false`: Player Character (PC) - controlled by players
  - `true`: Non-Player Character (NPC) - controlled by GMs
  - **Performance**: Indexed for efficient filtering queries
  - **Unified Model**: Same Character model serves both PCs and NPCs

**Character Status Workflow (Issue #180):**

- `status`: Character lifecycle status (VARCHAR 20, default: 'DRAFT', indexed)
  - `DRAFT`: Initial character creation state
  - `SUBMITTED`: Character submitted for GM approval
  - `APPROVED`: Character approved for campaign play
  - `INACTIVE`: Character temporarily inactive
  - `RETIRED`: Character permanently retired (terminal state)
  - `DECEASED`: Character marked as deceased (terminal state)
  - **Constraints**: Database CHECK constraint enforces valid status values
  - **Performance**: Indexed for efficient status-based filtering
  - **Workflow**: Managed by django-fsm-2 state transitions

**Relationships:**

- `campaign_id`: Campaign this character belongs to (CASCADE delete)
- `player_owner_id`: User who owns/controls this character (CASCADE delete)
  - For PCs: The actual player
  - For NPCs: Usually the GM who created them

**Polymorphic Support:**

- `polymorphic_ctype_id`: Django content type for polymorphic inheritance
- Supports inheritance: Character → WoDCharacter → MageCharacter
- Enables game-system-specific fields while maintaining unified queries

**Audit Trail (via DetailedAuditableMixin):**

- `created_by_id`: User who created the character (SET NULL on user deletion)
- `modified_by_id`: User who last modified the character (SET NULL on user deletion)
- `created_at`: Character creation timestamp (indexed for audit queries)
- `updated_at`: Last modification timestamp (indexed for audit queries)

**Soft Delete Support:**

- `is_deleted`: Soft delete flag (default: false)
- `deleted_at`: Deletion timestamp (null for active characters)
- `deleted_by_id`: User who deleted the character (SET NULL on user deletion)

**Business Rules:**

- Character names must be unique within a campaign
- Player must be a campaign member to own characters
- Campaign owners and GMs can edit all campaign characters
- Players can only edit their own characters
- Character limit per player enforced at campaign level
- NPC/PC status can be toggled (useful for character ownership transfers)
- **Status Workflow Rules:**
  - Characters start in DRAFT status
  - Only character owners can submit for approval (DRAFT → SUBMITTED)
  - Only GMs/owners can approve characters (SUBMITTED → APPROVED)
  - Only GMs/owners can reject characters (SUBMITTED → DRAFT)
  - Only GMs/owners can deactivate/activate characters (APPROVED ⇄ INACTIVE)
  - Character owners can retire their own characters (APPROVED → RETIRED)
  - GMs/owners can retire any character (APPROVED → RETIRED)
  - Only GMs/owners can mark characters deceased (APPROVED → DECEASED)
  - RETIRED and DECEASED are terminal states (no further transitions)

#### Polymorphic Character Inheritance

**WoD Character Extension:**

```sql
-- World of Darkness character extension
CREATE TABLE characters_wodcharacter (
    character_ptr_id INTEGER PRIMARY KEY REFERENCES characters_character(id) ON DELETE CASCADE,
    willpower SMALLINT DEFAULT 3 NOT NULL CHECK (willpower >= 1 AND willpower <= 10)
);
```

**Mage Character Extension:**

```sql
-- Mage: The Ascension character extension
CREATE TABLE characters_magecharacter (
    wodcharacter_ptr_id INTEGER PRIMARY KEY REFERENCES characters_wodcharacter(character_ptr_id) ON DELETE CASCADE,
    arete SMALLINT DEFAULT 1 NOT NULL CHECK (arete >= 1 AND arete <= 10),
    quintessence SMALLINT DEFAULT 0 NOT NULL CHECK (quintessence >= 0),
    paradox SMALLINT DEFAULT 0 NOT NULL CHECK (paradox >= 0)
);
```

#### Character Audit Trail

**Audit Log Table:**

```sql
-- Character-specific audit trail
CREATE TABLE characters_character_audit (
    id SERIAL PRIMARY KEY,
    character_id INTEGER NOT NULL REFERENCES characters_character(id) ON DELETE CASCADE,
    changed_by_id INTEGER REFERENCES users_user(id) ON DELETE SET NULL,
    action VARCHAR(20) NOT NULL CHECK (action IN ('CREATE', 'UPDATE', 'DELETE', 'RESTORE')),
    field_changes JSONB DEFAULT '{}' NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
);

-- Audit indexes
CREATE INDEX characters_audit_character_idx ON characters_character_audit (character_id);
CREATE INDEX characters_audit_timestamp_idx ON characters_character_audit (timestamp DESC);
CREATE INDEX characters_audit_action_idx ON characters_character_audit (action);
CREATE INDEX characters_audit_status_changes_idx ON characters_character_audit USING gin (field_changes) WHERE field_changes ? 'status';
```

**Tracked Field Changes:**

- `name`: Character name changes
- `description`: Background updates
- `npc`: PC/NPC status changes
- `status`: Character status transitions (NEW in #180)
- `campaign_id`: Campaign transfers (rare)
- `player_owner_id`: Ownership changes
- `game_system`: System changes (rare)

**Status Transition Audit Examples:**

```json
{
  "status": {
    "old": "DRAFT",
    "new": "SUBMITTED"
  }
}

{
  "status": {
    "old": "SUBMITTED",
    "new": "APPROVED"
  }
}

{
  "status": {
    "old": "APPROVED",
    "new": "RETIRED"
  }
}
```

#### Character Manager System (Issue #175)

The Character model provides multiple manager instances for efficient character querying and filtering:

**Manager Architecture:**

```python
# Manager instances on Character model
objects = CharacterManager()        # Primary manager (excludes soft-deleted)
all_objects = AllCharacterManager() # Includes soft-deleted characters
npcs = NPCManager()                 # Only NPCs, excludes soft-deleted
pcs = PCManager()                   # Only PCs, excludes soft-deleted
```

**NPCManager and PCManager Implementation:**

```python
class NPCManager(PolymorphicManager):
    """Manager for NPC (Non-Player Character) filtering."""

    def get_queryset(self):
        return super().get_queryset().filter(npc=True, is_deleted=False)

class PCManager(PolymorphicManager):
    """Manager for PC (Player Character) filtering."""

    def get_queryset(self):
        return super().get_queryset().filter(npc=False, is_deleted=False)
```

**Database Query Translation:**

```sql
-- Character.npcs.all() translates to:
SELECT * FROM characters_character
WHERE npc = true AND is_deleted = false;

-- Character.pcs.all() translates to:
SELECT * FROM characters_character
WHERE npc = false AND is_deleted = false;

-- Character.npcs.filter(campaign_id=1) translates to:
SELECT * FROM characters_character
WHERE campaign_id = 1 AND npc = true AND is_deleted = false;

-- Character.pcs.filter(player_owner_id=123) translates to:
SELECT * FROM characters_character
WHERE player_owner_id = 123 AND npc = false AND is_deleted = false;
```

**Manager Usage Patterns:**

```python
# Recommended: Use dedicated managers
campaign_npcs = Character.npcs.filter(campaign=campaign)
user_pcs = Character.pcs.filter(player_owner=user)

# Polymorphic inheritance support
mage_npcs = Character.npcs.instance_of(MageCharacter)
all_vampire_pcs = Character.pcs.instance_of(VampireCharacter)

# Combining with other filters
active_campaign_npcs = Character.npcs.filter(
    campaign=campaign,
    game_system="Mage: The Ascension"
)

# Performance-optimized queries with prefetch
npcs_with_campaign_data = Character.npcs.with_campaign_memberships()

# Backward compatibility (still works)
legacy_npcs = Character.objects.npcs()  # Same as Character.npcs.all()
legacy_pcs = Character.objects.player_characters()  # Same as Character.pcs.all()
```

**NPC Field Usage Patterns**

**Query by Character Type:**

```sql
-- Get all NPCs in a campaign
SELECT * FROM characters_character
WHERE campaign_id = ? AND npc = true AND is_deleted = false;

-- Get all PCs owned by a player
SELECT * FROM characters_character
WHERE player_owner_id = ? AND npc = false AND is_deleted = false;

-- Get character counts by type for a campaign
SELECT
    npc,
    COUNT(*) as count
FROM characters_character
WHERE campaign_id = ? AND is_deleted = false
GROUP BY npc;
```

**Performance Considerations:**

- `npc` field is indexed for efficient filtering
- `is_deleted` field is also indexed for soft-delete filtering
- Manager-level filtering reduces query complexity and improves performance
- Combined filters leverage composite indexes for optimal query performance
- Polymorphic queries benefit from select_related() on content types

**Manager Performance Benefits:**

- **Automatic Filtering**: Manager-level filters applied automatically to all queries
- **Index Utilization**: Both `npc` and `is_deleted` fields are individually indexed
- **Query Optimization**: Reduces need for manual WHERE clauses in application code
- **Polymorphic Compatibility**: Full support for django-polymorphic inheritance chains

**Migration History:**

- **Issue #174**: Added `npc` field with database index
- **Issue #175**: Added NPCManager and PCManager for intuitive character filtering
- **Default Behavior**: New field defaults to `false` (PC) for backward compatibility
- **Existing Data**: All existing characters treated as PCs (npc=false)
- **Backward Compatibility**: Existing `Character.objects` methods preserved

### Permission System

The campaign permission system uses a hierarchical role model:

```
OWNER (Campaign Creator)
├── Full campaign control
├── Member management
├── Campaign settings
└── Delete campaign

GM (Game Master)
├── Member management
├── Content creation
├── Scene management
└── Cannot delete campaign

PLAYER (Standard Participant)
├── Character management
├── Scene participation
└── Read campaign content

OBSERVER (Read-only Access)
├── View campaign content
├── View public scenes
└── Cannot modify content
```

### Visibility and Access Control

Campaigns support two visibility modes:

**Public Campaigns:**

- Visible to all authenticated users
- Can be browsed in campaign directory
- Join permissions controlled by allow_*_join flags

**Private Campaigns:**

- Visible only to owner and members
- Invitation-only access
- Hidden from public campaign lists

### Campaign Query Patterns

**Visibility Filtering:**

```sql
-- Campaigns visible to authenticated user
SELECT c.* FROM campaigns_campaign c
WHERE c.is_public = true
   OR c.owner_id = :user_id
   OR EXISTS (
       SELECT 1 FROM campaigns_campaignmembership m
       WHERE m.campaign_id = c.id AND m.user_id = :user_id
   );
```

**Role-based Access:**

```sql
-- User's role in campaign
SELECT
    CASE
        WHEN c.owner_id = :user_id THEN 'OWNER'
        ELSE m.role
    END as user_role
FROM campaigns_campaign c
LEFT JOIN campaigns_campaignmembership m
    ON c.id = m.campaign_id AND m.user_id = :user_id
WHERE c.id = :campaign_id;
```

## User Domain

### User Model

**Table**: `users_user`

Extended Django user model with GMA-specific features.

```sql
-- Inherits from Django AbstractUser
CREATE TABLE users_user (
    id SERIAL PRIMARY KEY,

    -- Django built-in fields
    username VARCHAR(150) UNIQUE NOT NULL,
    email VARCHAR(254) UNIQUE NOT NULL,
    first_name VARCHAR(150) DEFAULT '',
    last_name VARCHAR(150) DEFAULT '',
    is_active BOOLEAN DEFAULT true NOT NULL,
    is_staff BOOLEAN DEFAULT false NOT NULL,
    is_superuser BOOLEAN DEFAULT false NOT NULL,
    date_joined TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    last_login TIMESTAMP WITH TIME ZONE,
    password VARCHAR(128) NOT NULL,

    -- GMA custom fields
    display_name VARCHAR(100) DEFAULT '',
    timezone VARCHAR(50) DEFAULT 'UTC',

    -- Notification preferences
    notification_preferences JSONB DEFAULT '{}' NOT NULL
);
```

**Custom Fields:**

- **display_name**: Optional display name for UI
- **timezone**: User's preferred timezone
- **notification_preferences**: Flexible notification settings

### User Query Patterns

**Search for Invitations:**

```sql
-- Find users available for campaign invitation
SELECT u.id, u.username, u.email
FROM users_user u
WHERE u.is_active = true
  AND (u.username ILIKE '%:query%' OR u.email ILIKE '%:query%')
  AND u.id NOT IN (
      -- Exclude campaign owner
      SELECT :owner_id
      UNION
      -- Exclude existing members
      SELECT m.user_id FROM campaigns_campaignmembership m
      WHERE m.campaign_id = :campaign_id
      UNION
      -- Exclude users with pending invitations
      SELECT i.invited_user_id FROM campaigns_campaigninvitation i
      WHERE i.campaign_id = :campaign_id AND i.status = 'PENDING'
  )
ORDER BY u.username
LIMIT 10;
```

## Authentication and Sessions

### Session Management

Django's session framework with Redis backend:

**Session Storage:**

```python
# Session in Redis
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'  # Redis cache
SESSION_COOKIE_AGE = 86400  # 24 hours
```

**Session Data Structure:**

```json
{
  "_auth_user_id": "123",
  "_auth_user_backend": "django.contrib.auth.backends.ModelBackend",
  "_auth_user_hash": "...",
  "csrf_token": "...",
  "last_activity": "2024-01-15T10:30:00Z"
}
```

### CSRF Protection

CSRF tokens are managed through Django's built-in middleware:

- Token stored in session and cookie
- Required for all state-changing operations
- Validated on each POST/PUT/DELETE request

## Real-time Features

### Health Check System

**Table**: `core_healthchecklog`

Tracks system health monitoring results.

```sql
CREATE TABLE core_healthchecklog (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,

    -- Component status
    database_status BOOLEAN NOT NULL,
    redis_status BOOLEAN NOT NULL,
    overall_status BOOLEAN NOT NULL,

    -- Performance metrics
    database_response_time DECIMAL(10,3),
    redis_response_time DECIMAL(10,3),

    -- Error details
    error_details TEXT DEFAULT ''
);
```

**Usage:**

- Automated health checks every 5 minutes
- API endpoint for external monitoring
- Performance trend analysis

### WebSocket Architecture

Real-time features use Django Channels with Redis channel layer:

**Channel Groups:**

- `campaign_{id}`: Campaign-wide notifications
- `user_{id}`: User-specific notifications
- `scene_{id}`: Scene-specific chat and updates

**Message Types:**

```json
{
  "type": "campaign.membership.added",
  "campaign_id": 123,
  "user": {"id": 456, "username": "newplayer"},
  "role": "PLAYER"
}

{
  "type": "invitation.received",
  "invitation_id": 789,
  "campaign": {"id": 123, "name": "Vampire Chronicle"},
  "invited_by": {"username": "storyteller"}
}
```

## Relationship Diagrams

### Campaign Domain ERD

```
users_user
├── id (PK)
├── username
├── email
└── ...

campaigns_campaign
├── id (PK)
├── name
├── slug (UNIQUE)
├── owner_id (FK → users_user.id)
├── is_public
├── is_active
└── ...

campaigns_campaignmembership
├── id (PK)
├── campaign_id (FK → campaigns_campaign.id)
├── user_id (FK → users_user.id)
├── role
└── joined_at
└── UNIQUE(campaign_id, user_id)

campaigns_campaigninvitation
├── id (PK)
├── campaign_id (FK → campaigns_campaign.id)
├── invited_user_id (FK → users_user.id)
├── invited_by_id (FK → users_user.id)
├── role
├── status
├── created_at
├── expires_at
└── UNIQUE(campaign_id, invited_user_id, status)
```

### User Relationships

```sql
-- One user can:
-- Own many campaigns (1:N)
-- Be member of many campaigns (M:N through membership)
-- Send many invitations (1:N as inviter)
-- Receive many invitations (1:N as invitee)

SELECT
    u.username,
    COUNT(DISTINCT owned.id) as owned_campaigns,
    COUNT(DISTINCT member.campaign_id) as member_campaigns,
    COUNT(DISTINCT sent_inv.id) as sent_invitations,
    COUNT(DISTINCT recv_inv.id) as received_invitations
FROM users_user u
LEFT JOIN campaigns_campaign owned ON u.id = owned.owner_id
LEFT JOIN campaigns_campaignmembership member ON u.id = member.user_id
LEFT JOIN campaigns_campaigninvitation sent_inv ON u.id = sent_inv.invited_by_id
LEFT JOIN campaigns_campaigninvitation recv_inv ON u.id = recv_inv.invited_user_id
GROUP BY u.id, u.username;
```

## Indexes and Performance

### Strategic Indexes

```sql
-- Campaign visibility and access patterns
CREATE INDEX campaigns_campaign_visibility_idx
    ON campaigns_campaign (is_active, is_public);

CREATE INDEX campaigns_campaign_owner_active_idx
    ON campaigns_campaign (owner_id, is_active);

-- Membership lookup patterns
CREATE INDEX campaigns_membership_user_lookup_idx
    ON campaigns_campaignmembership (user_id, campaign_id);

CREATE INDEX campaigns_membership_campaign_lookup_idx
    ON campaigns_campaignmembership (campaign_id, user_id);

-- Invitation management
CREATE INDEX campaigns_invitation_status_idx
    ON campaigns_campaigninvitation (status, expires_at);

CREATE INDEX campaigns_invitation_user_pending_idx
    ON campaigns_campaigninvitation (invited_user_id, status)
    WHERE status = 'PENDING';

-- Search optimization
CREATE INDEX users_user_search_idx
    ON users_user USING gin(to_tsvector('english', username || ' ' || email))
    WHERE is_active = true;
```

### Query Performance Analysis

**Campaign List with User Role:**

```sql
EXPLAIN ANALYZE
SELECT
    c.id,
    c.name,
    c.game_system,
    c.member_count,
    CASE
        WHEN c.owner_id = :user_id THEN 'OWNER'
        ELSE m.role
    END as user_role
FROM (
    SELECT
        c.*,
        1 + COUNT(m.id) as member_count
    FROM campaigns_campaign c
    LEFT JOIN campaigns_campaignmembership m ON c.id = m.campaign_id
    WHERE c.is_active = true
      AND (c.is_public = true OR c.owner_id = :user_id OR c.id IN (
          SELECT campaign_id FROM campaigns_campaignmembership
          WHERE user_id = :user_id
      ))
    GROUP BY c.id
) c
LEFT JOIN campaigns_campaignmembership m
    ON c.id = m.campaign_id AND m.user_id = :user_id
ORDER BY c.updated_at DESC
LIMIT 25;
```

**Expected Performance:**

- **Small datasets (< 1000 campaigns)**: < 10ms
- **Medium datasets (< 10000 campaigns)**: < 50ms
- **Large datasets (< 100000 campaigns)**: < 200ms

## Data Migration Patterns

### Applying Model Mixins to Existing Models

The GMA project includes a comprehensive migration strategy for safely applying model mixins to existing models without data loss. This approach is used for adding audit fields (`created_by`, `modified_by`) to Character, Item, and Location models.

#### Migration Strategy Implementation

**Current Implementation (Characters, Items, Locations):**

- **Schema Migration**: Adds new mixin fields with proper defaults and indexes
- **Data Migration**: Populates audit fields for existing records using logical defaults
- **Safety Testing**: Comprehensive test suite validates migration safety
- **Rollback Support**: Interactive script for safe migration rollback

**Migration Files:**

- `characters/migrations/0003_character_created_by_character_modified_by_and_more.py` - Schema changes
- `characters/migrations/0004_populate_audit_fields.py` - Data population
- `items/migrations/0003_item_modified_by_alter_item_created_at_and_more.py` - Schema changes
- `items/migrations/0004_populate_audit_fields.py` - Data population
- `locations/migrations/0003_location_modified_by_alter_location_created_at_and_more.py` - Schema changes
- `locations/migrations/0004_populate_audit_fields.py` - Data population

#### Migration Safety Testing

The project includes 21 comprehensive tests in `core/tests/test_migration_strategy.py`:

**Test Categories:**

- **Data Preservation Tests**: Verify existing data survives migration
- **Default Value Tests**: Ensure proper application of default values
- **Data Integrity Tests**: Confirm foreign keys and constraints remain valid
- **Edge Case Tests**: Handle null values, boundary conditions, user deletion
- **Performance Tests**: Validate migration performance with realistic data volumes
- **Concurrency Tests**: Test concurrent access patterns after migration
- **Rollback Tests**: Ensure migrations can be safely reversed
- **Audit Integrity Tests**: Verify audit trail functionality remains intact

```bash
# Run migration safety tests
python manage.py test core.tests.test_migration_strategy

# Run specific test categories
python manage.py test core.tests.test_migration_strategy.ForwardMigrationDataPreservationTest
python manage.py test core.tests.test_migration_strategy.MigrationPerformanceTest
python manage.py test core.tests.test_migration_strategy.MigrationRollbackTest
```

#### Rollback Procedures

If migration rollback is needed, use the provided interactive script:

```bash
# Interactive rollback with safety confirmations
./scripts/rollback_mixin_migrations.sh

# Manual rollback commands (if needed)
python manage.py migrate characters 0002
python manage.py migrate items 0002
python manage.py migrate locations 0002
```

**Rollback Features:**

- Step-by-step rollback of data migrations before schema migrations
- Interactive confirmation to prevent accidental rollbacks
- Migration state verification before and after rollback
- Environment detection (conda/virtualenv support)
- Clear status reporting throughout the process

#### Data Population Strategy

For existing models, the data migrations use logical defaults:

**Characters:**

- `created_by` → Set to `player_owner` (most logical default)
- `modified_by` → Set to `player_owner` (assumes owner last modified)

**Items and Locations:**

- `created_by` → Preserved from existing field
- `modified_by` → Set to `created_by` (assumes creator last modified)

**Safety Considerations:**

- Uses `update_fields` to minimize database impact
- Preserves existing timestamp values
- Maintains foreign key integrity
- Handles edge cases (null values, deleted users)

### Schema Evolution Examples

**Adding New Fields:**

```python
# Migration: Add notification preferences
class Migration(migrations.Migration):
    operations = [
        migrations.AddField(
            model_name='user',
            name='notification_preferences',
            field=models.JSONField(default=dict),
        ),
    ]
```

**Complex Data Migrations:**

```python
# Migration: Populate display names from first/last name
def populate_display_names(apps, schema_editor):
    User = apps.get_model('users', 'User')

    for user in User.objects.filter(display_name=''):
        if user.first_name or user.last_name:
            user.display_name = f"{user.first_name} {user.last_name}".strip()
            user.save(update_fields=['display_name'])

class Migration(migrations.Migration):
    operations = [
        migrations.RunPython(
            populate_display_names,
            reverse_code=migrations.RunPython.noop
        ),
    ]
```

**Index Creation:**

```python
# Migration: Add performance indexes
class Migration(migrations.Migration):
    operations = [
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY campaigns_active_public_idx "
            "ON campaigns_campaign (is_active, is_public) "
            "WHERE is_active = true;",
            reverse_sql="DROP INDEX campaigns_active_public_idx;"
        ),
    ]
```

## Query Optimization

### Common Query Patterns

**Efficient Campaign Loading:**

```python
# Good: Use select_related for foreign keys
campaigns = (
    Campaign.objects
    .filter(is_active=True)
    .select_related('owner')  # Single query join
    .prefetch_related('memberships__user')  # Optimized N+1 resolution
)

# Bad: N+1 query problem
campaigns = Campaign.objects.filter(is_active=True)
for campaign in campaigns:
    print(campaign.owner.username)  # Additional query per campaign
    for membership in campaign.memberships.all():  # Additional queries
        print(membership.user.username)
```

**Efficient Permission Checking:**

```python
# Good: Single query with EXISTS
def user_can_access_campaign(user_id, campaign_id):
    return Campaign.objects.filter(
        id=campaign_id,
        models.Q(is_public=True) |
        models.Q(owner_id=user_id) |
        models.Q(memberships__user_id=user_id)
    ).exists()

# Bad: Multiple queries
def user_can_access_campaign_bad(user_id, campaign_id):
    campaign = Campaign.objects.get(id=campaign_id)
    if campaign.is_public:
        return True
    if campaign.owner_id == user_id:
        return True
    return campaign.memberships.filter(user_id=user_id).exists()
```

**Bulk Operations:**

```python
# Good: Bulk operations
def add_multiple_members(campaign_id, user_role_pairs):
    memberships = [
        CampaignMembership(
            campaign_id=campaign_id,
            user_id=user_id,
            role=role
        )
        for user_id, role in user_role_pairs
    ]
    return CampaignMembership.objects.bulk_create(
        memberships,
        ignore_conflicts=True
    )

# Bad: Individual saves
def add_multiple_members_bad(campaign_id, user_role_pairs):
    for user_id, role in user_role_pairs:
        membership = CampaignMembership(
            campaign_id=campaign_id,
            user_id=user_id,
            role=role
        )
        membership.save()  # Individual database hit
```

### Database Maintenance

**Regular Maintenance Tasks:**

```sql
-- Update table statistics (weekly)
ANALYZE campaigns_campaign;
ANALYZE campaigns_campaignmembership;
ANALYZE campaigns_campaigninvitation;

-- Cleanup expired invitations (daily)
DELETE FROM campaigns_campaigninvitation
WHERE status = 'PENDING'
  AND expires_at < now() - INTERVAL '30 days';

-- Vacuum dead tuples (weekly)
VACUUM ANALYZE campaigns_campaign;

-- Reindex if necessary (monthly)
REINDEX TABLE campaigns_campaign;
```

**Monitoring Queries:**

```sql
-- Slow query detection
SELECT query, mean_time, calls, total_time
FROM pg_stat_statements
WHERE mean_time > 100  -- queries taking >100ms average
ORDER BY mean_time DESC
LIMIT 10;

-- Index usage analysis
SELECT
    schemaname,
    tablename,
    indexname,
    idx_tup_read,
    idx_tup_fetch,
    idx_tup_read / idx_tup_fetch as ratio
FROM pg_stat_user_indexes
ORDER BY idx_tup_read DESC;
```

---

*This schema documentation should be updated when database changes are made. Last updated: 2025-08-18*
