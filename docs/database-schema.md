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

### Database Technology
- **PostgreSQL 16** as the primary database
- **UTF-8 encoding** for international character support
- **Row-level security** for multi-tenant data isolation
- **JSONB fields** for flexible configuration storage
- **Full-text search** capabilities for content discovery

## Core Models

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

*This schema documentation should be updated when database changes are made. Last updated: 2025-08-17*
