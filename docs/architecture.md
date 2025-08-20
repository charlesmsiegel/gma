# GMA System Architecture Documentation

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Overview](#system-overview)
3. [Service Layer Architecture](#service-layer-architecture)
4. [API Architecture](#api-architecture)
5. [Permission System](#permission-system)
6. [Data Model Architecture](#data-model-architecture)
7. [Frontend Integration](#frontend-integration)
8. [Real-Time Architecture](#real-time-architecture)
9. [Security Architecture](#security-architecture)
10. [Performance Considerations](#performance-considerations)
11. [Deployment Architecture](#deployment-architecture)

## Executive Summary

The Game Master Application (GMA) is a web-based tabletop RPG campaign management system built with Django and React. The architecture follows domain-driven design principles with a service layer pattern for business logic separation, modular API structure for maintainability, and comprehensive security measures for user data protection.

### Key Architectural Decisions

- **Service Layer Pattern**: Business logic separated from HTTP layer for reusability
- **Modular API Design**: Focused modules instead of monolithic view files
- **Security-First Approach**: Information leakage prevention and role-based access control
- **Test-Driven Development**: Comprehensive test coverage with TDD workflow
- **Hybrid Frontend**: React components enhance Django templates for progressive enhancement

## System Overview

### Technology Stack

**Backend:**
- **Django 5.2.4+** with Django REST Framework
- **PostgreSQL 16** for data persistence
- **Redis 7.2** for caching and real-time messaging
- **Django Channels** for WebSocket support
- **django-fsm-2** for state machine management

**Frontend:**
- **React with TypeScript** for enhanced UI components
- **Progressive Web App** capabilities
- **Django Templates** as base with React enhancement

**Development:**
- **Python 3.11** with Conda environment management
- **Node.js 20** for frontend tooling
- **Test-Driven Development** with 80%+ coverage target

### System Boundaries

The GMA system manages:
- **Campaign Management**: Creation, membership, settings
- **User Authentication**: Registration, login, profile management
- **Real-Time Communication**: Chat, notifications via WebSocket
- **Game System Support**: Flexible character models for different RPG systems
- **Content Organization**: Scenes, locations, items, characters
- **State Management**: Workflow transitions for campaigns, scenes, and characters

## Service Layer Architecture

The service layer provides a clean separation between business logic and HTTP request handling.

### Service Design Principles

1. **Single Responsibility**: Each service handles one domain area
2. **Transaction Management**: Services handle complex multi-model operations
3. **Validation**: Business rule validation separate from form validation
4. **Reusability**: Same service interface for web views and API endpoints

### Core Services

#### MembershipService
Location: `campaigns/services.py:21-177`

Handles all campaign membership operations:

```python
# Example Usage
service = MembershipService(campaign)
members = service.get_campaign_members()
service.add_member(user, role="PLAYER")
results = service.bulk_operation("add", users, role="OBSERVER")
```

**Key Methods:**
- `get_available_users_for_invitation()`: Returns users eligible for invitation
- `add_member(user, role)`: Adds new member with validation
- `remove_member(user)`: Removes member from campaign
- `change_member_role(membership, new_role)`: Updates member role
- `bulk_operation(action, users, role)`: Handles bulk membership changes

**Business Rules Enforced:**
- Cannot add campaign owner as member
- Role validation against defined choices
- Prevention of duplicate memberships
- Atomic bulk operations with rollback

#### InvitationService
Location: `campaigns/services.py:179-245`

Manages campaign invitation lifecycle:

```python
# Example Usage
service = InvitationService(campaign)
invitation = service.create_invitation(user, invited_by, "PLAYER", "Welcome!")
pending = service.get_pending_invitations()
```

**Key Methods:**
- `create_invitation()`: Creates new invitation with validation
- `get_campaign_invitations(status)`: Retrieves invitations with filtering
- `get_pending_invitations()`: Shortcut for pending invitations

**Business Rules Enforced:**
- Role validation for invitations
- Duplicate invitation prevention (handled by model constraints)
- Automatic expiration handling

#### CampaignService
Location: `campaigns/services.py:247-325`

General campaign operations and utilities:

```python
# Example Usage
service = CampaignService(campaign)
updated = service.update_campaign_settings(is_public=True)
users = service.search_users_for_invitation("john")
```

**Key Methods:**
- `create_campaign(owner, **data)`: Creates new campaign
- `update_campaign_settings(**data)`: Updates campaign configuration
- `search_users_for_invitation(query)`: Finds users for invitation

### When to Use Services vs Direct Model Access

**Use Services When:**
- Operations involve multiple models
- Complex business rules need enforcement
- Transaction management required
- Same logic needed in multiple places (views + API)

**Use Direct Model Access When:**
- Simple CRUD operations
- Single model operations without business logic
- Display-only operations (queries for templates)

## API Architecture

The API architecture prioritizes modularity, security, and consistency.

### Design Principles

1. **Modular Structure**: Focused modules instead of large files
2. **Standardized Errors**: Consistent error responses across endpoints
3. **Security Focus**: Information leakage prevention
4. **Role-Based Access**: Hierarchical permission checking

### Error Handling System

#### APIError Class
Location: `api/errors.py:25-172`

Provides standardized error response builders:

```python
# Standard error responses
return APIError.not_found()
return APIError.create_validation_error_response(errors)
return APIError.permission_denied_as_not_found()  # Security-focused
```

**Security Features:**
- Generic error messages prevent information leakage
- Permission denied returns 404 to hide resource existence
- Standardized validation error formatting

#### SecurityResponseHelper
Location: `api/errors.py:239-291`

Provides security-focused response patterns:

```python
# Safe object retrieval with permission checking
campaign, error_response = SecurityResponseHelper.safe_get_or_404(
    Campaign.objects,
    request.user,
    lambda user, obj: obj.has_role(user, "OWNER", "GM"),
    id=campaign_id
)
if error_response:
    return error_response
```

### Modular View Structure

#### Campaign Views
Location: `api/views/campaigns/`

- `list_views.py`: Campaign listing and detail endpoints
- `search_views.py`: User search for invitations
- `invitation_views.py`: Invitation management

#### Membership Views
Location: `api/views/memberships/`

- `member_views.py`: Individual member management
- `bulk_views.py`: Bulk membership operations

### Serializer Architecture

The serializer system provides consistent API responses with role-based field exposure.

#### Design Patterns

1. **Nested Serializers**: Related data included in responses
2. **Role-Based Fields**: Different fields based on user permissions
3. **Bulk Operation Responses**: Structured success/error reporting

#### Key Serializers

**CampaignDetailSerializer** (lines 240-300):

- Includes memberships, members, and settings
- Settings only exposed to campaign owners
- Includes user role calculation

**Bulk Operation Serializers** (lines 407-455):

- Structured responses for bulk operations
- Separate success and error tracking
- Consistent error reporting format

## Permission System

### Role Hierarchy

The system uses a four-tier role hierarchy:

1. **OWNER** - Full campaign control
2. **GM** - Game management permissions
3. **PLAYER** - Standard participant access
4. **OBSERVER** - Read-only access

### Permission Checking Patterns

#### Template Views
Uses `CampaignManagementMixin` (campaigns/mixins.py):

```python
class CampaignManagementMixin:
    def dispatch(self, request, *args, **kwargs):
        # Check permissions before processing
        user_role = campaign.get_user_role(request.user)
        if user_role not in ["OWNER", "GM"]:
            return redirect_with_error()
```

#### API Views
Uses `SecurityResponseHelper` for consistent access control:

```python
# Permission checking in API views
campaign, error = SecurityResponseHelper.safe_get_or_404(
    queryset, user, permission_check, **filters
)
```

### Security Principles

1. **Default Deny**: No access unless explicitly granted
2. **Information Hiding**: 404 instead of 403 for private resources
3. **Role Validation**: Consistent role checking across the system
4. **Audit Trail**: Track permission-related actions

## State Management Architecture

### django-fsm-2 Integration

The GMA system uses **django-fsm-2** (version 4.0.0+) for managing complex state transitions in domain models. This provides a robust foundation for workflow management across campaigns, scenes, and characters.

#### Technology Choice Rationale

**django-fsm-2 vs django-fsm:**

- **Active Maintenance**: django-fsm-2 is actively maintained with Django 5.x support
- **Enhanced Features**: Improved transition validation and error handling
- **Better Documentation**: More comprehensive documentation and examples
- **Community Support**: Active community with regular updates and bug fixes

#### State Machine Capabilities

**Current Implementation:**
The system includes basic FSM validation and integration testing to ensure django-fsm-2 works correctly with the Django framework.

**Future State Machine Applications:**

**Campaign Lifecycle:**
```python
# Future implementation example
class Campaign(models.Model):
    state = FSMField(default='draft', max_length=50)

    @transition(field=state, source='draft', target='active')
    def activate(self):
        """Activate campaign for player access."""
        pass

    @transition(field=state, source='active', target='completed')
    def complete(self):
        """Mark campaign as completed."""
        pass
```

**Scene Management:**
```python
# Future implementation example
class Scene(models.Model):
    status = FSMField(default='planning', max_length=50)

    @transition(field=status, source='planning', target='active')
    def start_scene(self):
        """Begin scene with player participation."""
        pass

    @transition(field=status, source='active', target='concluded')
    def conclude_scene(self):
        """End scene and finalize results."""
        pass
```

**Character Development:**
```python
# Current implementation - Character Status FSM
class Character(models.Model):
    status = FSMField(default='DRAFT', max_length=20)

    @transition(field=status, source='DRAFT', target='SUBMITTED')
    def submit_for_approval(self, user):
        """Character owner submits character for approval."""
        if self.player_owner != user:
            raise PermissionError("Only character owners can submit for approval")

    @transition(field=status, source='SUBMITTED', target='APPROVED')
    def approve(self, user):
        """GM approves character for campaign play."""
        user_role = self.campaign.get_user_role(user)
        if user_role not in ["GM", "OWNER"]:
            raise PermissionError("Only GMs and campaign owners can approve characters")

    @transition(field=status, source='APPROVED', target='RETIRED')
    def retire(self, user):
        """Retire character from active play."""
        user_role = self.campaign.get_user_role(user)
        if self.player_owner != user and user_role not in ["GM", "OWNER"]:
            raise PermissionError("Only character owners, GMs, and campaign owners can retire characters")
```

#### Integration Benefits

1. **Workflow Enforcement**: Prevent invalid state transitions
2. **Business Logic**: Encapsulate state-specific behavior in transition methods
3. **Audit Trail**: Track state changes for campaign history
4. **Permission Integration**: Combine FSM transitions with role-based permissions
5. **API Consistency**: Standardize state management across REST endpoints

#### Character Status Implementation (Issue #180)

The Character model now includes a comprehensive status workflow system using django-fsm-2:

**Status Workflow:**
```
DRAFT → SUBMITTED → APPROVED → {INACTIVE, RETIRED, DECEASED}
              ↓
            DRAFT (rejection)

INACTIVE ↔ APPROVED (deactivation/reactivation)
```

**Transition Methods:**

- `submit_for_approval()`: DRAFT → SUBMITTED (character owners only)
- `approve()`: SUBMITTED → APPROVED (GMs/owners only)
- `reject()`: SUBMITTED → DRAFT (GMs/owners only)
- `deactivate()`: APPROVED → INACTIVE (GMs/owners only)
- `activate()`: INACTIVE → APPROVED (GMs/owners only)
- `retire()`: APPROVED → RETIRED (owners + GMs/owners)
- `mark_deceased()`: APPROVED → DECEASED (GMs/owners only)

**Permission Matrix:**

- **Character Owners**: Can submit characters, retire their own characters
- **GMs**: Can approve/reject/deactivate/activate/mark deceased all characters
- **Campaign Owners**: Same permissions as GMs
- **Players/Observers**: Read-only access

**Audit Integration:**

All status transitions are automatically logged via DetailedAuditableMixin, capturing:

- User who performed the transition
- Timestamp of the change
- Old and new status values
- Complete audit trail accessible via `character.audit_entries.all()`

#### Testing and Validation

The system includes comprehensive FSM testing:

**Installation Tests** (`core/tests/test_django_fsm_installation.py`):

- Package import validation
- Basic FSM functionality
- Django ORM integration

**Character Status Tests** (`characters/tests/test_fsm_basic.py` - 28 tests):

- Status field choices and defaults
- Complete transition workflow testing
- Permission validation for each transition
- Audit logging verification
- Edge cases and error conditions
- Multi-step transition flows
- Role-based access control validation

**Test Categories:**

- **Status Field Tests**: Default values, choices validation
- **Transition Flow Tests**: Basic approval workflow, rejection flow, reactivation
- **Permission Tests**: Role-based transition access control
- **Audit Tests**: Automatic logging of status changes
- **Edge Case Tests**: Invalid transitions, terminal states, direct status changes

#### Implementation Status

**Completed:**

- ✅ **Character Model FSM**: Full status workflow implementation with comprehensive testing
- ✅ **Permission Integration**: Role-based transition controls
- ✅ **Audit Trail Integration**: Automatic status change logging
- ✅ **API Integration**: Status transitions exposed via REST endpoints

**Future Phases:**

1. **Phase 2**: Apply FSM to Campaign model for lifecycle management
2. **Phase 3**: Extend to Scene model for workflow control
3. **Phase 4**: Add complex multi-model state dependencies

**Implementation Guidelines:**

- Use clear, descriptive state names (e.g., 'draft', 'active', 'completed')
- Include transition validation logic in transition methods
- Maintain backward compatibility with existing state fields
- Add comprehensive test coverage for each state machine

## Data Model Architecture

### Book Model (Source References)

**Location**: `core/models/sources.py:11-58`

The Book model provides a centralized repository for RPG source book references, enabling consistent citations and source tracking throughout the application.

```python
class Book(models.Model):
    # Core identification
    title = CharField(max_length=200, unique=True)
    abbreviation = CharField(max_length=20, unique=True)  # e.g., "M20", "V20"
    system = CharField(max_length=100)  # e.g., "Mage: The Ascension"

    # Optional metadata
    edition = CharField(max_length=50, blank=True, default="")
    publisher = CharField(max_length=100, blank=True, default="")
    isbn = CharField(max_length=17, blank=True, default="")  # ISBN-13 with hyphens
    url = URLField(blank=True, default="")

    class Meta:
        ordering = ["system", "title"]
```

**Key Features:**

- **Unique Constraints**: Both title and abbreviation must be unique across all systems
- **Flexible System Support**: Not limited to World of Darkness games
- **Citation Ready**: Designed for use in character sheets, items, and rules references
- **URL Integration**: Links to purchase pages or digital versions
- **Consistent Ordering**: System-first ordering for logical grouping

**Architectural Benefits:**

1. **Centralized Reference Management**: Single source of truth for book metadata
2. **Citation Support**: Ready for integration with character sheets and rule references
3. **Cross-System Compatibility**: Supports any RPG system, not just World of Darkness
4. **Future-Proof Design**: Extensible for additional metadata fields
5. **Performance Optimized**: Unique constraints provide implicit indexing

**Integration Patterns:**

```python
# Future integration examples
class CharacterSheet(models.Model):
    # Could reference source books
    source_books = ManyToManyField(Book, blank=True)

class Rule(models.Model):
    # Could cite specific books
    source_book = ForeignKey(Book, on_delete=CASCADE)
    page_reference = CharField(max_length=20)  # e.g., "p. 142"

class Equipment(models.Model):
    # Could track item sources
    source_book = ForeignKey(Book, on_delete=SET_NULL, null=True)
```

**Usage Philosophy:**

- **Canonical References**: Authoritative source for book information
- **Abbreviation Standards**: Consistent short references (M20, V20, etc.)
- **System Agnostic**: Works with any RPG system
- **Citation Ready**: Formatted for academic-style references

### SourceReference Model (Generic Source Attribution)

**Location**: `core/models/sources.py:150-212`

The SourceReference model provides a flexible way to link any model in the application to source books with optional page and chapter references, using Django's GenericForeignKey system for maximum flexibility.

```python
class SourceReference(TimestampedMixin, models.Model):
    # Link to source book
    book = ForeignKey(Book, on_delete=CASCADE, related_name="source_references")

    # GenericForeignKey to link to any model
    content_type = ForeignKey(ContentType, on_delete=CASCADE)
    object_id = PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    # Optional reference details
    page_number = PositiveIntegerField(null=True, blank=True)
    chapter = TextField(blank=True, null=True)

    class Meta:
        ordering = ["book__abbreviation", "page_number"]
        indexes = [
            # Optimized for object lookup
            models.Index(fields=["content_type", "object_id"]),
            # Optimized for book browsing
            models.Index(fields=["book", "page_number"]),
            # Individual field indexes
            models.Index(fields=["content_type"]),
            models.Index(fields=["object_id"]),
        ]
```

**Key Features:**

- **Universal Linking**: Can reference any model in the application via GenericForeignKey
- **Flexible References**: Supports general book references, specific pages, or chapter citations
- **Performance Optimized**: Multiple database indexes for efficient querying
- **Rich Metadata**: Optional page numbers and chapter names for precise citations
- **Cascade Safety**: Proper cleanup when books or referenced objects are deleted

**Architectural Benefits:**

1. **System-Wide Source Attribution**: Any model can be linked to source books without schema changes
2. **Flexible Citation Levels**: Supports general references, page-specific citations, or chapter-based organization
3. **Query Performance**: Optimized indexes for common access patterns
4. **Data Integrity**: Proper foreign key relationships with cascade deletion
5. **Future-Proof Design**: GenericForeignKey allows references to new models without changes

**Common Integration Patterns:**

```python
# Character source attribution
character = Character.objects.create(name="Mage Character")
SourceReference.objects.create(
    book=mage_book,
    content_object=character,
    page_number=65,
    chapter="Character Creation"
)

# Equipment with source reference
magical_item = Equipment.objects.create(name="Wand of Fireballs")
SourceReference.objects.create(
    book=magic_items_book,
    content_object=magical_item,
    page_number=127
)

# General book reference for a campaign setting
setting = CampaignSetting.objects.create(name="Technocracy")
SourceReference.objects.create(
    book=technocracy_book,
    content_object=setting
    # No page/chapter for general reference
)
```

**Query Optimization Patterns:**

```python
# Efficient object source lookup
def get_object_sources(obj):
    return SourceReference.objects.filter(
        content_type=ContentType.objects.get_for_model(obj),
        object_id=obj.id
    ).select_related('book').order_by('book__abbreviation', 'page_number')

# Book reference browsing
def get_book_references(book):
    return SourceReference.objects.filter(
        book=book
    ).select_related('content_type').order_by('page_number')

# System-wide source analysis
def get_system_references(system_name):
    return SourceReference.objects.filter(
        book__system=system_name
    ).select_related('book', 'content_type')
```

**Performance Considerations:**

- **Compound Indexes**: `(content_type, object_id)` for object lookup, `(book, page_number)` for browsing
- **Select Related**: Always use `select_related('book')` for queries involving book data
- **Prefetch Related**: Use `prefetch_related('content_object')` when accessing linked objects
- **Content Type Caching**: Cache ContentType lookups for frequently accessed models

**Future Enhancements:**

- **Quote Storage**: Text field for storing specific quotes or excerpts
- **Confidence Ratings**: Community validation of source accuracy
- **Version Tracking**: Support for different book editions with same content
- **Bulk Operations**: Management commands for importing/exporting source data

### Core Model Mixins

The system provides reusable model mixins for common functionality across multiple models, with performance optimizations and comprehensive documentation.

#### Available Mixins

**TimestampedMixin** (`core/models/mixins.py:30-56`):

- Automatic `created_at` and `updated_at` fields with database indexes
- Performance-optimized for time-based queries
- Comprehensive help text for admin interface

**DisplayableMixin** (`core/models/mixins.py:58-83`):

- `is_displayed` boolean flag for visibility control
- `display_order` integer field for custom ordering (indexed)
- Optimized for display and sorting operations

**NamedModelMixin** (`core/models/mixins.py:85-108`):

- Standard `name` field with `__str__()` method implementation
- Consistent naming across models

**DescribedModelMixin** (`core/models/mixins.py:110-130`):

- Optional `description` TextField for detailed information
- Blank-allowed with empty string default

**AuditableMixin** (`core/models/mixins.py:132-189`):

- `created_by` and `modified_by` user tracking
- **Enhanced save() method** with automatic user assignment
- Performance-optimized with foreign key relationships

**GameSystemMixin** (`core/models/mixins.py:191-235`):

- `game_system` field with predefined choices
- Supports World of Darkness focus with popular RPG systems

#### Enhanced Features

**Performance Optimizations:**
```python
# Database indexes automatically added
created_at = models.DateTimeField(auto_now_add=True, db_index=True)
updated_at = models.DateTimeField(auto_now=True, db_index=True)
display_order = models.PositiveIntegerField(default=0, db_index=True)
```

**Automatic User Tracking:**
```python
# Enhanced AuditableMixin usage
obj = MyModel(name="Example")
obj.save(user=request.user)  # Automatically sets created_by and modified_by

# On updates
obj.name = "Updated"
obj.save(user=request.user)  # Updates modified_by, preserves created_by
```

**Comprehensive Help Text:**
All mixin fields include detailed help text visible in Django admin, API documentation, and development tools.

**Usage Philosophy:**

- **Performance-First**: Database indexes on commonly queried fields
- **Developer-Friendly**: Comprehensive help text and documentation
- **Pragmatic Design**: Only provides functionality that's actually needed
- **Future-Focused**: For new models, not retrofitting existing ones
- **Simple Design**: Avoids complex inheritance hierarchies

**When to Use:**

- New models that need simple timestamp tracking
- Models without existing timestamp fields
- Situations where standardized timestamp behavior is desired

**When NOT to Use:**

- Existing models (Campaign, Character) already have their own implementations
- Models requiring custom timestamp behavior
- Models where timestamp fields aren't needed

**Example Usage:**
```python
class NewGameComponent(TimestampedMixin):
    name = models.CharField(max_length=100)
    description = models.TextField()

    # Automatically includes:
    # - created_at (set on creation)
    # - updated_at (updated on each save)
```

### Campaign Domain Models

#### Campaign Model
Location: `campaigns/models/campaign.py:83-200`

Core campaign entity with visibility controls:

```python
class Campaign(models.Model):
    name = CharField(max_length=200)
    slug = SlugField(unique=True)  # Auto-generated
    owner = ForeignKey(User)
    is_public = BooleanField(default=False)  # Visibility control
    is_active = BooleanField(default=True)   # Active campaigns only
```

**Key Features:**

- Auto-generated unique slugs
- Visibility filtering via custom manager
- Performance indexes on common queries
- Owner cascade deletion

#### CampaignMembership Model
Many-to-many relationship with role information:

```python
class CampaignMembership(models.Model):
    campaign = ForeignKey(Campaign)
    user = ForeignKey(User)
    role = CharField(choices=ROLE_CHOICES)
    joined_at = DateTimeField(auto_now_add=True)
```

**Business Rules:**

- Unique constraint on (campaign, user)
- Owner cannot be member (enforced at service layer)
- Role validation via choices

#### CampaignInvitation Model
Manages invitation lifecycle:

```python
class CampaignInvitation(models.Model):
    campaign = ForeignKey(Campaign)
    invited_user = ForeignKey(User)
    invited_by = ForeignKey(User)
    status = CharField(choices=STATUS_CHOICES)
    expires_at = DateTimeField()  # Auto-calculated
```

**Features:**

- Automatic expiration calculation
- Cleanup management via custom manager
- Constraint prevents duplicate invitations

### Character Domain Models

#### Character Model Architecture
Location: `characters/models/__init__.py:272-771`

The Character model implements a unified PC/NPC architecture using polymorphic inheritance for game system flexibility:

```python
class Character(TimestampedMixin, NamedModelMixin, DetailedAuditableMixin, PolymorphicModel):
    # Core fields
    description = TextField(blank=True, default="")
    campaign = ForeignKey(Campaign, on_delete=CASCADE)
    player_owner = ForeignKey(User, on_delete=CASCADE)
    game_system = CharField(max_length=100)

    # PC/NPC unified architecture
    npc = BooleanField(default=False, db_index=True)  # Key architectural decision

    # Soft delete support
    is_deleted = BooleanField(default=False)
    deleted_at = DateTimeField(null=True, blank=True)
    deleted_by = ForeignKey(User, on_delete=SET_NULL, null=True)
```

#### PC/NPC Unified Architecture

**Architectural Benefits:**

1. **Single Model Design**: Both Player Characters (PCs) and Non-Player Characters (NPCs) use the same base model
2. **Polymorphic Inheritance**: Game-specific features through WoDCharacter → MageCharacter inheritance
3. **Flexible Ownership**: NPCs typically owned by GMs, PCs owned by players
4. **Performance Optimization**: Database index on `npc` field for efficient filtering
5. **Consistent API**: Same endpoints, serializers, and business logic for both character types

**Business Logic Implications:**

```python
# NPC filtering in queries
npcs = Character.objects.filter(campaign=campaign, npc=True)
pcs = Character.objects.filter(campaign=campaign, npc=False)

# Permission checking considers NPC status
def can_edit_character(user, character):
    if character.player_owner == user:
        return True  # Character owner can always edit

    user_role = character.campaign.get_user_role(user)
    return user_role in ["OWNER", "GM"]  # GMs can edit all characters
```

**Character Type Management:**

- **Player Characters (npc=False)**:
  - Created by players for their own use
  - Subject to campaign character limits
  - Players have full edit control
  - Used for main story participation

- **Non-Player Characters (npc=True)**:
  - Created by GMs for story purposes
  - Not subject to player character limits
  - GMs and campaign owners have edit control
  - Used for NPCs, antagonists, supporting characters

#### Polymorphic Inheritance Chain

**Base Character → WoD Character → Game-Specific Character:**

```python
# Inheritance hierarchy
Character (Base)
├── Core fields: name, description, campaign, player_owner, npc
├── Audit trail: created_by, modified_by, timestamps
├── Soft delete: is_deleted, deleted_at, deleted_by
└── WoDCharacter
    ├── World of Darkness fields: willpower
    └── MageCharacter
        └── Mage-specific fields: arete, quintessence, paradox
```

**Polymorphic Benefits:**

- Unified queries across all character types
- Game-system-specific fields without database table explosion
- Type-safe casting and field access
- Consistent API responses with polymorphic serialization

#### Character Audit Trail Integration

**DetailedAuditableMixin Integration:**
```python
# Automatic audit trail for character changes
character.save(audit_user=request.user)  # Records user who made changes

# NPC field changes tracked in audit
audit_entry = character.audit_entries.filter(
    field_changes__has_key='npc'
).first()
# Shows: {"npc": {"old": false, "new": true}}
```

**Tracked Operations:**

- Character creation with initial PC/NPC status
- NPC status toggles (PC ↔ NPC conversions)
- Ownership transfers (important for NPCs)
- Field modifications with user attribution

#### Character Manager Architecture

The Character model uses a comprehensive manager system providing multiple access patterns for different use cases:

**Manager Instances:**

1. **`Character.objects`** (CharacterManager): Primary manager excluding soft-deleted characters
2. **`Character.all_objects`** (AllCharacterManager): Includes soft-deleted characters
3. **`Character.npcs`** (NPCManager): Only NPCs, excluding soft-deleted **[New in #175]**
4. **`Character.pcs`** (PCManager): Only PCs, excluding soft-deleted **[New in #175]**

**NPCManager and PCManager (Issue #175):**

```python
class NPCManager(PolymorphicManager):
    """Manager for NPC (Non-Player Character) filtering."""

    def get_queryset(self):
        """Return QuerySet filtered to only NPCs (npc=True) and not soft-deleted."""
        return super().get_queryset().filter(npc=True, is_deleted=False)

class PCManager(PolymorphicManager):
    """Manager for PC (Player Character) filtering."""

    def get_queryset(self):
        """Return QuerySet filtered to only PCs (npc=False) and not soft-deleted."""
        return super().get_queryset().filter(npc=False, is_deleted=False)
```

**Primary CharacterManager Methods:**

```python
class CharacterManager(PolymorphicManager):
    def npcs(self):
        """Get only NPCs (Non-Player Characters)."""
        return self.get_queryset().filter(npc=True)

    def player_characters(self):
        """Get only Player Characters (PCs)."""
        return self.get_queryset().filter(npc=False)

    def for_campaign(self, campaign):
        return self.get_queryset().filter(campaign=campaign)

    def editable_by(self, user, campaign):
        # Handles both PC and NPC permission logic
        user_role = campaign.get_user_role(user)
        if user_role in ["OWNER", "GM"]:
            return self.filter(campaign=campaign)  # All characters
        elif user_role == "PLAYER":
            return self.filter(campaign=campaign, player_owner=user)  # Own characters only
        else:
            return self.none()
```

**New Manager Usage Examples (Recommended):**

```python
# NEW: Direct manager instances (recommended approach)
Character.npcs.all()           # Only NPCs, excluding soft-deleted
Character.pcs.all()            # Only PCs, excluding soft-deleted

# NEW: Filter with additional criteria
Character.npcs.filter(campaign=campaign)         # NPCs in specific campaign
Character.pcs.filter(player_owner=user)          # PCs owned by user
Character.npcs.filter(game_system="Mage")        # NPCs of specific game system

# NEW: Complex queries using polymorphic inheritance
mage_npcs = Character.npcs.instance_of(MageCharacter)  # Only Mage NPCs
vampire_pcs = Character.pcs.instance_of(VampireCharacter)  # Only Vampire PCs

# NEW: Combining with other manager methods
Character.npcs.with_campaign_memberships()      # NPCs with prefetched data
Character.pcs.for_campaign(campaign)            # PCs filtered by campaign
```

**Backward Compatibility (Still Available):**

```python
# Existing methods on primary manager (still works)
Character.objects.npcs()                    # Same as Character.npcs.all()
Character.objects.player_characters()       # Same as Character.pcs.all()

# Traditional filtering (still works)
Character.objects.filter(npc=True)          # Manual NPC filtering
Character.objects.filter(npc=False)         # Manual PC filtering

# All active characters (default behavior)
Character.objects.all()                     # All active characters (PCs + NPCs)
Character.all_objects.all()                # Including soft-deleted characters
```

**Performance Benefits:**

- **Database Optimization**: Manager-level filtering reduces query complexity
- **Automatic Indexing**: Leverages existing database indexes on `npc` and `is_deleted` fields
- **Polymorphic Support**: Full compatibility with django-polymorphic features
- **Memory Efficiency**: QuerySet lazy evaluation with optimized filters

**Performance Optimizations:**

- Database index on `npc` field for type filtering
- Composite index on `(campaign, player_owner)` for character limits
- Prefetch related data with `with_campaign_memberships()`
- Soft delete filtering in default manager

#### Permission System Integration

**Role-Based Character Access:**

```
Character Permissions by Role:
OWNER (Campaign Creator)
├── Edit all PCs and NPCs in campaign
├── Delete any character (with campaign settings)
└── Transfer character ownership

GM (Game Master)
├── Edit all PCs and NPCs in campaign
├── Create NPCs without character limits
└── Delete characters (with campaign settings)

PLAYER (Standard Participant)
├── Edit own PCs only
├── Cannot edit NPCs
└── Subject to character creation limits

OBSERVER (Read-only Access)
├── View character lists
└── Cannot edit any characters
```

**Implementation Patterns:**
```python
# Service layer handles PC/NPC permission differences
class CharacterService:
    def create_character(self, user, campaign, **data):
        npc = data.get('npc', False)

        if npc:
            # NPCs can only be created by GMs/Owners
            if campaign.get_user_role(user) not in ["OWNER", "GM"]:
                raise PermissionError("Only GMs can create NPCs")
        else:
            # PCs subject to character limits
            self._validate_character_limit(user, campaign)
```

### Location Domain Models

#### Location Model Architecture
Location: `locations/models/__init__.py:26-479`

The Location model provides hierarchical location management for campaigns with comprehensive tree traversal capabilities and validation frameworks:

```python
class Location(TimestampedMixin, NamedModelMixin, DescribedModelMixin, AuditableMixin, PolymorphicModel):
    # Core campaign relationship
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="locations")

    # Hierarchy support
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
        help_text="Parent location in the hierarchy"
    )
```

#### Hierarchy Features

**Tree Structure Support:**
**Self-Referential Hierarchy**: Unlimited nesting depth with safety limits
- **Orphan Management**: Intelligent child location handling on parent deletion
- **Circular Reference Prevention**: Validation framework prevents invalid hierarchies
- **Performance Optimization**: Efficient tree traversal with query optimization

**New Enhanced Methods (Issue #185):**
```python
# Breadcrumb path generation
def get_full_path(self, separator: str = " > ") -> str:
    """Get full path from root to this location as breadcrumb string."""
    # Returns: "World > Continent > Country > City"

# Alias for backward compatibility
@property
def sub_locations(self) -> QuerySet["Location"]:
    """Alias for children relationship."""
    return self.children.all()
```

#### Tree Traversal Methods

**Descendant and Ancestor Navigation:**
```python
# Comprehensive tree navigation
descendants = location.get_descendants()  # All children recursively
ancestors = location.get_ancestors()      # Path to root
siblings = location.get_siblings()        # Same-level locations
root = location.get_root()               # Top-level ancestor
path = location.get_path_from_root()     # Root-to-current path
depth = location.get_depth()             # Hierarchy level (0-based)
```

**Relationship Queries:**
```python
# Check hierarchical relationships
is_child = location.is_descendant_of(parent_location)

# Generate breadcrumbs for navigation
breadcrumb = location.get_full_path(" > ")
# Result: "Azeroth > Stormwind > Stormwind City"
```

#### Validation Framework

**Business Rules Enforced:**
**Maximum Depth**: 10-level hierarchy limit (0-9)
- **Campaign Scoping**: Parent must be in same campaign
- **Circular Reference Prevention**: Comprehensive validation against cycles
- **Self-Parent Prevention**: Location cannot be its own parent

**Validation Implementation:**
```python
def clean(self) -> None:
    """Comprehensive location validation."""
    # Prevent self as parent
    if self.parent_id and self.parent_id == self.pk:
        raise ValidationError("A location cannot be its own parent.")

    # Prevent circular references
    if self.parent and self.pk:
        descendants = self.get_descendants()
        if self.parent in descendants:
            raise ValidationError("Circular reference detected...")

    # Enforce maximum depth
    if self.parent:
        future_depth = self.parent.get_depth() + 1
        if future_depth >= 10:
            raise ValidationError("Maximum depth of 10 levels exceeded...")
```

#### Permission Integration

**Role-Based Access Control:**
The Location model integrates with GMA's campaign permission system:

```python
# Permission checking methods
def can_view(self, user) -> bool:
    """Campaign members and public campaigns only."""

def can_edit(self, user) -> bool:
    """Owners/GMs edit all, Players edit their own."""

def can_delete(self, user) -> bool:
    """Owners/GMs delete all, Players delete their own."""

@classmethod
def can_create(cls, user, campaign) -> bool:
    """All campaign members can create locations."""
```

**Permission Rules:**
**View**: All campaign members + anonymous users for public campaigns
- **Create**: All campaign members (Owner, GM, Player, Observer)
- **Edit/Delete**: Owner/GM for all locations, Players for their own creations

#### Database Design

**Adjacency List Model:**
```sql
-- Core hierarchy implementation
ALTER TABLE locations_location ADD COLUMN parent_id INTEGER
    REFERENCES locations_location(id) ON DELETE SET NULL;

-- Performance indexes
CREATE INDEX locations_location_parent_id_idx ON locations_location(parent_id);
CREATE INDEX locations_location_campaign_id_idx ON locations_location(campaign_id);
```

**Performance Characteristics:**
**Descendant Queries**: O(n) where n is number of descendants
- **Ancestor Queries**: O(d) where d is depth
- **Root Finding**: O(d) where d is depth
- **Safety Limits**: Built-in protection against infinite loops

#### Use Cases

**Campaign World Building:**
```python
# Create hierarchical world structure
continent = Location.objects.create(name="Azeroth", campaign=campaign)
kingdom = Location.objects.create(name="Stormwind", parent=continent, campaign=campaign)
city = Location.objects.create(name="Stormwind City", parent=kingdom, campaign=campaign)

# Generate navigation breadcrumb
breadcrumb = city.get_full_path()
# Result: "Azeroth > Stormwind > Stormwind City"
```

**Tree Operations:**
```python
# Move entire location sub-trees
old_parent = Location.objects.get(name="Old Region")
new_parent = Location.objects.get(name="New Region")
location_to_move = Location.objects.get(name="City")

location_to_move.parent = new_parent
location_to_move.save()  # All children move automatically
```

#### Migration and Backward Compatibility

**Database Migration**: Single migration (`0005_location_parent.py`) adds hierarchy support
**Backward Compatibility**: All existing locations remain functional (parent=None)
**Zero Downtime**: Migration is additive with no data loss

### Database Optimization

#### Indexes

- Composite indexes on frequently queried combinations
- Performance indexes on is_active and is_public fields
- Foreign key indexes for relationship queries

#### Query Optimization

- `select_related()` for single foreign keys
- `prefetch_related()` for reverse foreign keys and many-to-many
- Custom managers for common query patterns

## Frontend Integration

### Hybrid Architecture

The frontend uses a hybrid approach combining Django templates with React components:

1. **Base Templates**: Django provides HTML structure and authentication
2. **React Enhancement**: Progressive enhancement for interactive features
3. **API Integration**: React components use Django REST API
4. **Fallback Support**: Django forms work if React fails to load

### Component Architecture

#### Key Components

Location: `frontend/src/components/`

- `LoginForm.tsx`: Enhanced authentication with validation
- `RegisterForm.tsx`: User registration with real-time validation
- `ProfileView.tsx` / `ProfileEditForm.tsx`: User profile management

#### Integration Pattern
React components are embedded via data attributes:

```html
<div id="react-component"
     data-react-component="login-form"
     data-react-props='{"redirectUrl": "/dashboard/"}'>
</div>
```

#### API Client

Location: `frontend/src/services/api.ts`

Provides CSRF-protected API access:

- Automatic CSRF token handling
- Consistent error handling
- TypeScript interface definitions

## Real-Time Architecture

### WebSocket Implementation

The system uses Django Channels for real-time features:

1. **Single Connection**: One WebSocket per user
2. **Dynamic Subscriptions**: Subscribe to multiple campaign channels
3. **Message Routing**: Channel-based message distribution

### Use Cases

- **Chat Systems**: Real-time scene chat
- **Notifications**: Campaign invitations and updates
- **Live Updates**: Member status changes
- **Dice Rolling**: Real-time dice roll results

### Scaling Considerations

- Redis as channel layer for horizontal scaling
- Connection pooling for database efficiency
- Message queuing for reliable delivery

## Security Architecture

### Authentication Security

1. **Secure Error Messages**: Generic responses prevent user enumeration
2. **Case-Insensitive Email**: Prevents duplicate account issues
3. **Password Validation**: Django's built-in password validators
4. **Session Management**: Secure session configuration

### API Security

1. **CSRF Protection**: Required for all state-changing operations
2. **Permission Validation**: Role-based access control
3. **Information Hiding**: 404 responses for unauthorized access
4. **Input Validation**: Comprehensive validation at multiple layers

### Recommended Production Security

```python
# Rate limiting example
@ratelimit(key='ip', rate='5/m', method='POST', block=True)
def login_view(request):
    # Authentication logic
```

**Additional Recommendations:**

- `django-ratelimit` for API endpoint protection
- `django-axes` for login attempt monitoring
- Infrastructure-level rate limiting (Cloudflare, nginx)
- Regular security audits and dependency updates

## Performance Considerations

### Database Optimization

1. **Selective Loading**: Use `only()` for limited field queries
2. **Prefetch Related**: Optimize N+1 query problems
3. **Database Indexes**: Strategic indexing on query patterns
4. **Connection Pooling**: Efficient database connection management

### Caching Strategy

1. **Redis Caching**: Session and temporary data storage
2. **QuerySet Caching**: Cache expensive database queries
3. **Template Caching**: Static content caching
4. **CDN Integration**: Static asset delivery optimization

### API Performance

1. **Pagination**: Limit result sets with configurable page sizes
2. **Field Selection**: Serializer optimization for required fields only
3. **Bulk Operations**: Reduce API calls with bulk endpoints
4. **Response Compression**: Enable gzip compression

## Deployment Architecture

### Environment Configuration

The application uses environment-based configuration for different deployment stages:

1. **Development**: Local PostgreSQL/Redis with debug enabled
2. **Staging**: Production-like environment for testing
3. **Production**: Optimized for performance and security

### Container Architecture

```dockerfile
# Multi-stage Docker build
FROM python:3.11-slim AS builder
# Build stage for dependencies

FROM python:3.11-slim AS runtime
# Runtime stage with minimal footprint
```

### Infrastructure Components

1. **Application Server**: Django with Gunicorn/daphne
2. **Database**: PostgreSQL with connection pooling
3. **Cache Layer**: Redis for sessions and channels
4. **Static Files**: CDN or nginx for static asset serving
5. **Load Balancer**: nginx or cloud load balancer
6. **Monitoring**: Application and infrastructure monitoring

### Scaling Considerations

1. **Horizontal Scaling**: Stateless application servers
2. **Database Scaling**: Read replicas for query distribution
3. **Redis Scaling**: Redis cluster for high availability
4. **CDN**: Global content distribution for static assets

### Monitoring and Observability

1. **Application Metrics**: Performance and error monitoring
2. **Infrastructure Metrics**: System resource monitoring
3. **Log Aggregation**: Centralized logging with structured formats
4. **Health Checks**: Automated health monitoring and alerting

---

*This architecture documentation should be reviewed and updated as the system evolves. Last updated: 2025-08-18*
