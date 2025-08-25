# GMA System Architecture Documentation

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Overview](#system-overview)
3. [Service Layer Architecture](#service-layer-architecture)
4. [API Architecture](#api-architecture)
5. [Permission System](#permission-system)
6. [Data Model Architecture](#data-model-architecture)
   - [Location Domain Models](#location-domain-models)
   - [Location Management Interface Architecture](#location-management-interface-architecture)
   - [Item Domain Models](#item-domain-models)
   - [Prerequisite System Architecture](#prerequisite-system-architecture)
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
- **Hierarchical Content Management**: Tree-structured data models for locations with character ownership
- **Performance-Optimized Queries**: Strategic database indexing and query optimization patterns

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
- **Real-Time Scene Chat**: Complete WebSocket-based chat with message types, rate limiting, and history API
- **Game System Support**: Flexible character models for different RPG systems
- **Content Organization**: Scenes, locations, items, characters
- **Location Management**: Hierarchical location trees with character ownership
- **Scene Management**: Status workflow system with participant management and role-based permissions
- **Prerequisite System**: Comprehensive requirement validation for character advancement, item usage, and game mechanics
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

#### Item Views
Location: `api/views/item_views.py`

- `ItemListCreateAPIView`: Campaign-scoped item listing and creation with advanced filtering
- `ItemDetailAPIView`: Item detail, update, and soft delete operations
- `ItemPermissionMixin`: Standardized permission checking across item operations

#### Scene Views
Location: `api/views/scene_views.py`

- `SceneViewSet`: Full ViewSet for scene CRUD operations with role-based permissions
- `SceneAuthenticated`: Custom permission class for proper 401 authentication responses
- `ScenePagination`: Optimized pagination (20 items default, max 100)
- Custom actions: `add_participant`, `remove_participant`, `change_status`
- Status transition validation and participant management
- Campaign-scoped filtering with query optimization

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

**Scene Serializer Hierarchy**:

- `SceneSerializer`: Base serializer with nested campaign, participants, and creator data
- `SceneDetailSerializer`: Extended with `can_manage` and `can_participate` permission fields
- `SceneCreateUpdateSerializer`: Request validation with status transition checking and participant management
- Three-tier architecture supports different use cases (list, detail, create/update)
- Optimized participant count using prefetched data

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
# Current implementation - Scene Status Workflow (Issue #41)
class Scene(models.Model):
    STATUS_CHOICES = [
        ("ACTIVE", "Active"),
        ("CLOSED", "Closed"),
        ("ARCHIVED", "Archived"),
    ]

    status = CharField(max_length=10, choices=STATUS_CHOICES, default="ACTIVE")

    # Status transitions handled via API with validation:
    # ACTIVE → CLOSED (close scene)
    # CLOSED → ARCHIVED (archive completed scene)
    # ARCHIVED: Terminal state

    # Validation prevents:
    # - ACTIVE → ARCHIVED (must close first)
    # - CLOSED → ACTIVE (cannot reactivate)
    # - ARCHIVED → Any (terminal state)
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

### Scene Domain Models

#### Scene Model Architecture
Location: `scenes/models/__init__.py:53-118`

The Scene model provides comprehensive scene management for campaigns with status workflows, participant management, and query optimization:

```python
class Scene(models.Model):
    STATUS_CHOICES = [
        ("ACTIVE", "Active"),
        ("CLOSED", "Closed"),
        ("ARCHIVED", "Archived"),
    ]

    name = CharField(max_length=200, help_text="Scene name")
    description = TextField(blank=True, default="", help_text="Scene description")
    campaign = ForeignKey(Campaign, on_delete=CASCADE, related_name="scenes")
    created_by = ForeignKey(settings.AUTH_USER_MODEL, on_delete=CASCADE, related_name="created_scenes")
    status = CharField(max_length=10, choices=STATUS_CHOICES, default="ACTIVE")
    participants = ManyToManyField("characters.Character", related_name="participated_scenes", blank=True)

    # Timestamp fields
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

**Key Architectural Features:**

1. **Status Workflow System (Issue #41)**
   - Three-state workflow: ACTIVE → CLOSED → ARCHIVED
   - Validation prevents invalid transitions (e.g., ACTIVE → ARCHIVED, CLOSED → ACTIVE)
   - Terminal state: ARCHIVED scenes cannot be modified
   - API-enforced status transitions with role-based permissions

2. **Participant Management**
   - Many-to-many relationship with Character model
   - Supports both PC and NPC participation
   - Campaign-scoped validation ensures participants belong to the scene's campaign
   - Role-based permissions for adding/removing participants

3. **Performance Optimizations**
   - Composite database indexes for common query patterns
   - Custom manager with optimized QuerySet methods
   - Efficient prefetching of related data (campaign, participants, creator)

4. **Custom Manager Architecture**
   ```python
   class SceneQuerySet(models.QuerySet):
       def for_user(self, user):
           """Get scenes accessible to a user with optimized query."""
           return self.filter(
               Q(campaign__owner=user) | Q(campaign__memberships__user=user)
           ).distinct()

       def with_details(self):
           """Get scenes with related data optimized for serialization."""
           return self.select_related('campaign', 'created_by').prefetch_related('participants')

       def by_campaign(self, campaign_id):
           """Filter scenes by campaign ID efficiently."""
           return self.filter(campaign_id=campaign_id)
   ```

5. **Database Indexes**
   - Composite indexes: `(campaign, -created_at)`, `(campaign, status)`, `(status, -created_at)`
   - Single field indexes: `status`, `created_by`
   - Optimized for common access patterns and filtering operations

**Business Rules:**

- Scene creation limited to OWNER and GM roles
- All campaign members can view scenes and manage their own character participation
- Status changes restricted to OWNER and GM roles
- Participants must belong to the same campaign as the scene
- Archived scenes are read-only (cannot be modified)

**API Integration:**

- Full REST API with ViewSet architecture
- Three-tier serializer system (list, detail, create/update)
- Custom actions for participant management and status changes
- Role-based permission integration
- Query optimization for list and detail views

**Performance Considerations:**

- Prefetched participant data to avoid N+1 queries
- Optimized participant count calculation using cached data
- Strategic use of select_related for foreign key relationships
- Campaign-scoped filtering for security and performance

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
Location: `locations/models/__init__.py:26-521`

The Location model provides hierarchical location management for campaigns with comprehensive tree traversal capabilities, validation frameworks, and character ownership support:

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

    # Character ownership support (Issue #186)
    owned_by = models.ForeignKey(
        "characters.Character",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_locations",
        help_text="The character who owns this location (can be PC or NPC)"
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

    # Validate ownership cross-campaign constraint
    if (
        self.owned_by
        and self.campaign_id
        and self.owned_by.campaign_id != self.campaign_id
    ):
        raise ValidationError(
            "Location owner must be a character in the same campaign."
        )
```

#### Character Ownership Feature (Issue #186)

The location ownership feature enables characters (both PCs and NPCs) to own locations within their campaign, supporting typical RPG scenarios like tavern keepers owning taverns or players owning strongholds.

**Key Architectural Decisions:**

1. **Universal Character Support**: Both Player Characters (PCs) and Non-Player Characters (NPCs) can own locations
2. **Optional Ownership**: Locations can exist without an owner (owned_by = NULL)
3. **Campaign Scoping**: Validation ensures characters can only own locations within their own campaign
4. **Simplified Approach**: Direct field assignment with existing permission checks rather than complex transfer methods
5. **Admin Interface Enhancement**: Campaign-based filtering suggests NPCs for location ownership

**Business Logic Implementation:**

```python
# Character ownership validation
def clean(self) -> None:
    # ... existing validation ...

    # Validate ownership cross-campaign constraint
    if (
        self.owned_by
        and self.campaign_id
        and self.owned_by.campaign_id != self.campaign_id
    ):
        raise ValidationError(
            "Location owner must be a character in the same campaign."
        )

# Permission system integration
def can_edit(self, user) -> bool:
    # ... existing permission checks ...

    # Players can edit their character-owned locations
    if user_role == "PLAYER":
        if self.created_by == user:
            return True
        # Check if any of the user's characters own this location
        if self.owned_by and self.owned_by.player_owner == user:
            return True

    return False
```

**Reverse Relationship on Character:**

The `owned_by` field automatically creates a reverse relationship on the Character model:

```python
# Automatic reverse relationship usage
character.owned_locations.all()  # All locations owned by character
character.owned_locations.filter(name__icontains='tavern')  # Filter owned locations
character.owned_locations.count()  # Count of owned properties

# Typical usage scenarios
tavern_keeper = Character.objects.get(name="Innkeeper Bob")
tavern_properties = tavern_keeper.owned_locations.all()

# Property transfer
old_owner.owned_locations.update(owned_by=new_owner)
```

**Admin Interface Enhancements:**

```python
# Enhanced admin form with campaign-based filtering
def _setup_owner_field(self):
    if self.instance.pk and self.instance.campaign_id:
        self.fields["owned_by"].queryset = Character.objects.filter(
            campaign_id=self.instance.campaign_id
        )
        self.fields["owned_by"].help_text = (
            "The character who owns this location (can be PC or NPC). "
            "NPCs are typically used for location ownership."
        )
```

**Cross-Campaign Validation:**

```python
def clean_owned_by(self):
    owned_by = self.cleaned_data.get("owned_by")
    campaign = self.cleaned_data.get("campaign")

    if owned_by and campaign:
        if owned_by.campaign != campaign:
            raise ValidationError("Owner must be a character in the same campaign.")

    return owned_by
```

#### Permission Integration

**Role-Based Access Control:**
The Location model integrates with GMA's campaign permission system:

```python
# Permission checking methods
def can_view(self, user) -> bool:
    """Campaign members and public campaigns only."""

def can_edit(self, user) -> bool:
    """Owners/GMs edit all, Players edit their own + character-owned."""
    user_role = self.campaign.get_user_role(user)

    if user_role in ["OWNER", "GM"]:
        return True

    if user_role == "PLAYER":
        if self.created_by == user:
            return True
        # NEW: Check if any of the user's characters own this location
        if self.owned_by and self.owned_by.player_owner == user:
            return True

    return False

def can_delete(self, user) -> bool:
    """Owners/GMs delete all, Players delete their own + character-owned."""
    user_role = self.campaign.get_user_role(user)

    if user_role in ["OWNER", "GM"]:
        return True

    if user_role == "PLAYER":
        if self.created_by == user:
            return True
        # NEW: Check if any of the user's characters own this location
        if self.owned_by and self.owned_by.player_owner == user:
            return True

    return False

@classmethod
def can_create(cls, user, campaign) -> bool:
    """All campaign members can create locations."""

# NEW: Character ownership display property
@property
def owner_display(self) -> str:
    """Get a display string for the location's owner."""
    if not self.owned_by:
        return "Unowned"

    owner_type = "NPC" if self.owned_by.npc else "PC"
    return f"{self.owned_by.name} ({owner_type})"
```

**Permission Rules:**
**View**: All campaign members + anonymous users for public campaigns
- **Create**: All campaign members (Owner, GM, Player, Observer)
- **Edit/Delete**: Owner/GM for all locations, Players for their own creations + character-owned locations

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

#### Location Management Interface Architecture

The location management system provides a complete web-based interface for campaign location management following Django's class-based view pattern and responsive Bootstrap 5 design.

**Location**: `locations/views/__init__.py`, `locations/urls/__init__.py`, `templates/locations/`, `static/css/locations.css`, `static/js/locations.js`

**View Architecture:**

The system uses Django Class-Based Views with a custom campaign filtering mixin system:

```python
# Campaign parameter mapping for URL consistency
class CampaignSlugMappingMixin:
    """Maps campaign_slug URL parameter to slug for CampaignFilterMixin compatibility."""
    def dispatch(self, request, *args, **kwargs):
        if "campaign_slug" in kwargs:
            kwargs["slug"] = kwargs["campaign_slug"]
        return super().dispatch(request, *args, **kwargs)
```

**Core Views:**

1. **CampaignLocationsView** - Hierarchical location listing with search and filtering
2. **LocationDetailView** - Location detail with sub-locations and breadcrumbs
3. **LocationCreateView** - Location creation with parent selection and validation
4. **LocationEditView** - Location editing with hierarchy validation and permissions

**URL Patterns:**
```python
urlpatterns = [
    path("campaigns/<slug:campaign_slug>/", CampaignLocationsView.as_view(), name="campaign_locations"),
    path("campaigns/<slug:campaign_slug>/create/", LocationCreateView.as_view(), name="location_create"),
    path("campaigns/<slug:campaign_slug>/<int:location_id>/", LocationDetailView.as_view(), name="location_detail"),
    path("campaigns/<slug:campaign_slug>/<int:location_id>/edit/", LocationEditView.as_view(), name="location_edit"),
]
```

**Permission System Integration:**

The interface integrates with GMA's role-based permission system with performance-optimized permission checking:

```python
# Optimized permission checking to avoid N+1 queries
for location in locations:
    if user_role in ["OWNER", "GM"]:
        location.user_can_edit = True
    elif user_role == "PLAYER":
        # Check character ownership using prefetched data
        if location.owned_by:
            location.user_can_edit = (
                hasattr(location.owned_by, "player_owner")
                and location.owned_by.player_owner == user
            )
        else:
            location.user_can_edit = location.created_by == user
```

**Key Features:**

1. **Hierarchical Tree Display**: Visual tree structure with depth-based indentation and connection lines
2. **Search and Filtering**: Real-time search by name, ownership filtering by character, unowned location filtering
3. **Character Ownership Integration**: Display and management of character-owned locations
4. **Breadcrumb Navigation**: Full path navigation from campaign → location hierarchy → current location
5. **Role-Based Actions**: Context-sensitive action menus based on user permissions
6. **Responsive Design**: Mobile-friendly Bootstrap 5 interface with progressive enhancement

**Frontend Implementation:**

**Template Structure:**
- `campaign_locations.html` - Main location listing with hierarchical tree
- `location_detail.html` - Detailed location view with sub-locations and metadata
- `location_form.html` - Unified create/edit form with hierarchy preview

**CSS Architecture** (`static/css/locations.css`):
```css
/* Visual hierarchy with depth-based indentation */
.location-tree .location-item.depth-1 { padding-left: 1.5rem; border-left: 2px solid #e9ecef; }
.location-tree .location-item.depth-2 { padding-left: 3rem; border-left: 2px solid #e9ecef; }
.location-tree .location-item.depth-3 { padding-left: 4.5rem; border-left: 2px solid #e9ecef; }

/* Interactive elements */
.location-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
```

**JavaScript Enhancements** (`static/js/locations.js`):
- Auto-submit filter forms on selection change
- Mutual exclusion between owner and unowned filters
- Real-time hierarchy preview during location creation/editing
- Client-side form validation with error feedback
- URL parameter handling for pre-selecting parent locations

**Form Architecture:**

**Location Form Hierarchy** (`locations/forms.py`):

```python
LocationForm (Base)
├── LocationCreateForm - Sets created_by, campaign filtering
├── LocationEditForm - Disables campaign field, prevents modification
└── BulkLocationMoveForm - Bulk operations with validation
```

**Key Form Features:**

1. **Dynamic Parent Filtering**: Parent dropdown populated based on campaign selection
2. **Hierarchy Validation**: Prevents circular references and enforces depth limits
3. **Campaign Scoping**: Ensures all parent options belong to the same campaign
4. **Real-time Preview**: JavaScript shows full path preview as user selects parent
5. **Bulk Operations**: Form supports moving multiple locations simultaneously

**Performance Optimizations:**

1. **Query Optimization**:
   - `select_related()` for foreign keys (parent, owned_by, created_by, campaign)
   - `prefetch_related()` for reverse relationships (children)
   - Strategic use of `only()` for field-limited queries

2. **Database Indexes**: Leverages existing indexes on campaign_id, parent_id, and created_by

3. **Template Efficiency**: Minimal database queries in templates through prefetched data

4. **JavaScript Performance**: Debounced form submissions and efficient DOM manipulation

**Security Implementation:**

1. **Campaign Isolation**: All operations scoped to user's accessible campaigns
2. **Permission Validation**: Multi-layer permission checking (URL, view, model)
3. **CSRF Protection**: All forms include Django CSRF tokens
4. **Input Sanitization**: XSS prevention through Django's template auto-escaping
5. **Information Hiding**: 404 responses for unauthorized access instead of 403

**Testing Coverage:**

**Comprehensive Test Suite** (`locations/tests/test_location_interface.py`):

- **1,624 lines** of comprehensive test coverage
- **16 test classes** covering all interface components
- **Integration tests** for complete user workflows
- **Permission matrix testing** for all role combinations
- **Template rendering verification** with context validation
- **URL routing and navigation testing**
- **Search and filtering functionality validation**
- **Error handling and edge case coverage**

**Test Categories:**
- Location list view with hierarchical display
- Location detail view with sub-locations and breadcrumbs
- Location create view with parent selection and validation
- Location edit view with hierarchy validation and permissions
- Search and filtering maintaining tree structure
- URL routing and navigation patterns
- Template rendering with proper context
- Complete integration workflows

**Accessibility Features:**

1. **Semantic HTML**: Proper heading hierarchy and landmark roles
2. **ARIA Support**: Screen reader announcements for dynamic content
3. **Keyboard Navigation**: All interactive elements keyboard accessible
4. **Focus Management**: Proper focus indicators and tab order
5. **Alternative Text**: Descriptive text for all visual elements

### Database Optimization

#### Indexes

- Composite indexes on frequently queried combinations
- Performance indexes on is_active and is_public fields
- Foreign key indexes for relationship queries

#### Query Optimization

- `select_related()` for single foreign keys
- `prefetch_related()` for reverse foreign keys and many-to-many
- Custom managers for common query patterns

### Item Domain Models

#### Item Model Architecture

**Location**: `items/models/__init__.py:107-284`

The Item model provides comprehensive equipment and treasure management for campaigns with soft delete functionality, single character ownership, advanced admin capabilities, and polymorphic inheritance support for future extensibility:

```python
class Item(TimestampedMixin, NamedModelMixin, DescribedModelMixin, AuditableMixin, PolymorphicModel):
    # Core item information
    name = CharField(max_length=200, help_text="Name of the item")
    campaign = ForeignKey(Campaign, on_delete=models.CASCADE, related_name="items")
    quantity = PositiveIntegerField(default=1, validators=[MinValueValidator(1)])

    # User audit tracking
    created_by = ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="created_items")

    # Single character ownership (Issue #183)
    owner = ForeignKey("characters.Character", on_delete=models.SET_NULL, null=True, blank=True, related_name="possessions")
    last_transferred_at = DateTimeField(null=True, blank=True, help_text="When this item was last transferred")

    # Soft delete functionality
    is_deleted = BooleanField(default=False)
    deleted_at = DateTimeField(null=True, blank=True)
    deleted_by = ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="deleted_items")
```

**Key Architectural Features:**

1. **Single Character Ownership Architecture (Issue #183)**
   - Converted from many-to-many `owners` field to single `owner` ForeignKey
   - One item can be owned by exactly one character (PC or NPC) or remain unowned
   - Transfer tracking with `last_transferred_at` timestamp field
   - Related name changed from "owned_items" to "possessions" for semantic clarity
   - Character relationship: `character.possessions.all()` for all items owned by character

2. **Transfer Functionality**
   ```python
   def transfer_to(self, new_owner: Optional["Character"]) -> "Item":
       """Transfer item to new owner with timestamp tracking."""
       self.owner = new_owner
       self.last_transferred_at = timezone.now()
       self.save(update_fields=["owner", "last_transferred_at"])
       return self  # Method chaining support
   ```

3. **Soft Delete Pattern Implementation**
   - Items are marked as deleted rather than physically removed
   - Maintains data integrity for campaign history
   - Allows for restoration of accidentally deleted items
   - Tracks who deleted items and when

4. **Polymorphic Manager Architecture**
   ```python
   class ItemQuerySet(PolymorphicQuerySet):
       """Custom QuerySet extending PolymorphicQuerySet with filtering methods."""
       def active(self):
           return self.filter(is_deleted=False)
       def deleted(self):
           return self.filter(is_deleted=True)
       def owned_by_character(self, character):
           return self.filter(owner=character)

   class ItemManager(PolymorphicManager):
       def get_queryset(self):
           return ItemQuerySet(self.model, using=self._db).filter(is_deleted=False)

   class AllItemManager(PolymorphicManager):
       def get_queryset(self):
           return ItemQuerySet(self.model, using=self._db)  # Includes deleted items
   ```

5. **Custom QuerySet Methods**
   - `active()`: Filter to non-deleted items
   - `deleted()`: Filter to soft-deleted items
   - `for_campaign()`: Campaign-specific filtering
   - `owned_by_character(character)`: Single character ownership filtering

6. **Permission System Integration**
   - Role-based access control using campaign hierarchy
   - Creator privileges for item management
   - Superuser override capabilities
   - `can_be_deleted_by(user)` method for centralized permission checking

7. **Business Logic Methods**
   - `transfer_to(new_owner)`: Transfer item ownership with timestamp tracking and method chaining
   - `soft_delete(user)`: Performs soft deletion with permission validation
   - `restore(user)`: Restores soft-deleted items with permission validation
   - `clean()`: Model-level validation for name and quantity

**Admin Interface Architecture:**

The ItemAdmin class provides comprehensive management capabilities with single ownership support:

```python
@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    # 6 bulk operations adapted for single ownership
    actions = [
        "soft_delete_selected",
        "restore_selected",
        "update_quantity",
        "assign_ownership",      # Now assigns single owner
        "clear_ownership",       # Sets owner to None
        "transfer_campaign",
    ]

    # Organized fieldsets for single ownership
    fieldsets = [
        ("Basic Information", {"fields": ("name", "description", "campaign", "quantity")}),
        ("Ownership", {"fields": ("owner", "last_transferred_at"), "classes": ("collapse",)}),
        ("Audit Information", {"fields": ("created_by", "created_at", "updated_at"), "classes": ("collapse",)}),
        ("Deletion Status", {"fields": ("is_deleted", "deleted_at", "deleted_by"), "classes": ("collapse",)}),
    ]
```

**Bulk Operations:**
- Soft delete with permission checking and transaction safety
- Bulk restoration of deleted items
- Quantity updates across multiple items
- Single ownership assignment/clearing for multiple items
- Campaign transfer capabilities
- Comprehensive error handling and user feedback

**Testing Architecture:**

The Item model includes 168 comprehensive tests across 6 test files:

1. **Model Tests** (`test_models.py`): Core validation, soft delete functionality, permission system
2. **Admin Tests** (`test_admin.py`): Admin interface capabilities, bulk operations, permission checks
3. **Bulk Operations Tests** (`test_bulk_operations.py`): Transaction safety, error handling, edge cases
4. **Mixin Application Tests** (`test_mixin_application.py`): Inheritance validation, field compatibility
5. **Polymorphic Conversion Tests** (`test_polymorphic_conversion.py`): Polymorphic behavior, manager compatibility, inheritance validation
6. **Character Ownership Tests** (`test_character_ownership.py`): Single ownership functionality, transfer methods, possessions relationship (33 tests)

**Database Performance Considerations:**

- Indexes on `campaign` foreign key for filtering
- Index on `is_deleted` for manager query optimization
- Single `owner` ForeignKey relationship optimized for character ownership queries
- `last_transferred_at` field for transfer history tracking
- Soft delete pattern maintains referential integrity
- Polymorphic field (`polymorphic_ctype`) supports inheritance chains
- Character.possessions reverse relationship provides efficient access to owned items

#### Polymorphic Inheritance Architecture (Issue #182)

The Item model has been converted from Django's standard Model to PolymorphicModel, enabling future game system-specific item types while maintaining full backward compatibility.

**Polymorphic Implementation:**

```python
# Base Item class (now polymorphic)
class Item(TimestampedMixin, NamedModelMixin, DescribedModelMixin, AuditableMixin, PolymorphicModel):
    # Core item functionality applies to all item types
    campaign = ForeignKey(Campaign, on_delete=CASCADE)
    quantity = PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    owners = ManyToManyField("characters.Character", blank=True)
    # Soft delete pattern
    # Audit tracking via AuditableMixin
    # Polymorphic inheritance support
```

**Architectural Benefits:**

1. **Future Extensibility**: Ready for game-specific item subclasses (WeaponItem, ArmorItem, ConsumableItem)
2. **Type-Safe Queries**: Polymorphic queries automatically return correct subclass instances
3. **Unified API**: Same endpoints, serializers, and business logic for all item types
4. **Database Efficiency**: Single table with polymorphic_ctype field for type identification
5. **Full Backward Compatibility**: All existing Item functionality preserved

**Future Subclassing Pattern:**

Following the same inheritance pattern as the Character model hierarchy:

```python
# Future implementation examples
class WeaponItem(Item):
    """Weapon-specific item properties."""
    damage_dice = CharField(max_length=20)  # e.g., "2d6+1"
    weapon_type = CharField(max_length=50)  # e.g., "Sword", "Bow"

class ArmorItem(Item):
    """Armor-specific item properties."""
    armor_class = PositiveIntegerField()
    armor_type = CharField(max_length=50)  # e.g., "Light", "Heavy"

class ConsumableItem(Item):
    """Consumable item with usage tracking."""
    uses_remaining = PositiveIntegerField()
    max_uses = PositiveIntegerField()
```

**Polymorphic Query Capabilities:**

```python
# Unified queries across all item types
all_items = Item.objects.for_campaign(campaign)  # Returns all item types

# Type-specific queries (future functionality)
weapons = Item.objects.instance_of(WeaponItem)
armor = Item.objects.instance_of(ArmorItem)

# Polymorphic filtering with type safety
magical_weapons = WeaponItem.objects.filter(magical=True)
```

**Testing Coverage:**

The polymorphic conversion includes comprehensive test coverage:
- **33 polymorphic-specific tests** in `test_polymorphic_conversion.py`
- **Inheritance validation** ensuring proper polymorphic behavior
- **Manager compatibility** with PolymorphicManager/PolymorphicQuerySet
- **Database field verification** for polymorphic_ctype field
- **Backward compatibility** ensuring existing functionality works unchanged

**Implementation Status:**

- ✅ **Base Item Model**: Converted to PolymorphicModel with full functionality
- ✅ **Manager Architecture**: Updated to PolymorphicManager/PolymorphicQuerySet
- ✅ **Database Migration**: Added polymorphic_ctype field with data population
- ✅ **Test Coverage**: Comprehensive validation of polymorphic behavior
- ✅ **Backward Compatibility**: All 135 existing tests passing unchanged
- 🔄 **Future Development**: Ready for Item subclass implementation per game system requirements

#### Item API Architecture

**Location**: `api/views/item_views.py`, `api/serializers.py`, `api/urls/item_urls.py`

The Item API provides comprehensive REST endpoints for equipment and treasure management with campaign-scoped access control:

**API Implementation Status:**

- ✅ **REST Endpoints**: Complete CRUD operations implemented
  - `ItemListCreateAPIView`: GET /api/items/ (list + filter) and POST /api/items/ (create)
  - `ItemDetailAPIView`: GET/PUT/DELETE /api/items/{id}/ (detail, update, soft delete)
- ✅ **Serializers**: Two-tier serialization architecture
  - `ItemSerializer`: Full response serialization with nested relationships
  - `ItemCreateUpdateSerializer`: Request validation and model updates
- ✅ **Permission Integration**: Campaign role-based access control
  - OWNER/GM: Full access to all campaign items
  - PLAYER: View all, create/edit/delete own items
  - OBSERVER: View only access
- ✅ **Advanced Filtering**: Campaign-scoped with multiple filter parameters
  - Owner filtering (character-based or unowned items)
  - Creator filtering (user-based)
  - Quantity range filtering with validation
  - Full-text search across name and description
  - Soft-deleted item inclusion for restoration workflows
- ✅ **Single Character Ownership**: API support for ownership transfer
  - Transfer tracking with `last_transferred_at` timestamp
  - Campaign validation ensuring owner belongs to same campaign
  - Unowned item support with `owner=null` filtering
- ✅ **Polymorphic Support**: API ready for future item subclasses
  - `polymorphic_ctype` field in responses for type identification
  - Serializer architecture supports inheritance
- ✅ **Security Features**: Information leakage prevention
  - 404 responses for non-members instead of 403
  - Campaign membership validation on all endpoints
  - Character ownership cross-campaign validation
- ✅ **Soft Delete Integration**: Safe deletion with restoration capabilities
  - Soft delete via DELETE endpoint
  - `include_deleted` parameter for restoration workflows
  - Permission-based visibility of deleted items

**Test Coverage:**

- ✅ **59 Comprehensive API Tests**: Full endpoint validation with edge cases
- ✅ **Permission Testing**: Role-based access control validation
- ✅ **Security Testing**: Information leakage and boundary condition testing
- ✅ **Filter Testing**: All query parameter combinations and validation

### Prerequisite System Architecture

**Location**: `prerequisites/` - Complete prerequisite validation system (Issues #188-192)

The prerequisite system provides comprehensive requirement validation for character advancement, item usage, spell casting, and other game mechanics. It combines structured JSON requirements with intuitive helper functions, a powerful checking engine, and advanced visual building tools.

#### System Components

**1. Requirement Helpers (Issue #188)**
Location: `prerequisites/helpers.py` - 408 lines

Provides developer-friendly functions for building JSON requirement structures:

```python
from prerequisites.helpers import trait_req, has_item, any_of, all_of, count_with_tag

# Simple requirements
strength_req = trait_req("strength", minimum=3)
sword_req = has_item("weapons", name="Magic Sword")

# Complex logical combinations
combat_mastery = all_of(
    any_of(
        trait_req("strength", minimum=4),
        trait_req("dexterity", minimum=4)
    ),
    has_item("weapons", name="Master's Blade"),
    count_with_tag("achievements", "combat", minimum=5)
)
```

**Key Helper Functions:**
- `trait_req(name, minimum, maximum, exact)`: Character trait requirements
- `has_item(field, id, name, **kwargs)`: Item possession requirements
- `any_of(*requirements)`: Logical OR combinations (at least one must pass)
- `all_of(*requirements)`: Logical AND combinations (all must pass)
- `count_with_tag(model, tag, minimum, maximum)`: Counting requirements for tagged objects

**2. Checking Engine (Issue #189)**
Location: `prerequisites/checkers.py` - 696 lines

Comprehensive validation engine with recursive checking and detailed result reporting:

```python
from prerequisites.checkers import RequirementChecker

checker = RequirementChecker()

# Simple requirement checking
result = checker.check_requirement(character, strength_req)
print(f"Result: {result.passed} - {result.message}")

# Complex requirement checking with detailed breakdown
result = checker.check_requirement(character, combat_mastery)
for detail in result.details:
    print(f"  {detail.requirement_type}: {detail.passed} - {detail.message}")
```

**RequirementChecker Features:**
- **Polymorphic Character Support**: Works with Character → WoDCharacter → MageCharacter hierarchy
- **Recursive Logic**: Handles nested any/all combinations up to 5 levels deep
- **Performance Optimized**: Efficient queries with minimal database hits
- **Extensible Registry**: Plugin system for custom requirement types
- **Detailed Results**: Complete success/failure breakdown with human-readable messages

**Supported Requirement Types:**
- `trait`: Character attributes, abilities, skills, and custom traits
- `has`: Object possession (items, relationships, achievements)
- `any`: Logical OR - at least one sub-requirement must pass
- `all`: Logical AND - all sub-requirements must pass
- `count_tag`: Count objects with specific tags (minimum/maximum constraints)

**3. Visual Builder UI (Issue #190)**
Location: `prerequisites/widgets.py` - Django form widget integration

Seamless Django form integration for requirement building:

```python
from prerequisites.widgets import PrerequisiteBuilderWidget

class MyModelForm(forms.ModelForm):
    requirements = forms.JSONField(widget=PrerequisiteBuilderWidget)

    class Meta:
        model = MyModel
        fields = ['name', 'requirements']
```

**Widget Features:**
- **Django Integration**: Drop-in widget for JSONField forms
- **Visual Interface**: User-friendly requirement building UI
- **Real-time Validation**: Live JSON structure validation
- **Bootstrap Styling**: Consistent with GMA design system
- **Template Rendering**: Custom template with proper CSRF handling

**4. Advanced Drag-Drop Interface (Issue #191)**
Location: 7 JavaScript files (4,112 lines total)

Professional drag-and-drop interface for complex requirement building:

**JavaScript Architecture:**
- **`prerequisite-builder.js`** (330 lines): Main coordination and API integration
- **`drag-drop-builder.js`** (478 lines): Core drag-drop engine with event handling
- **`drag-drop-canvas.js`** (794 lines): Canvas management, rendering, and validation
- **`drag-drop-palette.js`** (477 lines): Component palette and toolbox management
- **`accessibility-manager.js`** (735 lines): WCAG 2.1 AA compliance and screen reader support
- **`touch-handler.js`** (707 lines): Mobile touch interactions and gesture recognition
- **`undo-redo-manager.js`** (591 lines): Action history and state management

**Advanced Features:**
- **Visual Building**: Drag-and-drop requirement composition with component palette
- **Touch Support**: Full mobile compatibility with touch gestures and haptic feedback
- **Accessibility**: Complete WCAG 2.1 AA compliance with keyboard navigation and screen readers
- **Undo/Redo System**: Full action history with unlimited undo levels
- **Real-time Preview**: Live JSON generation with syntax highlighting and validation
- **Component Library**: Pre-built requirement components with smart defaults
- **Auto-Layout**: Intelligent requirement tree visualization and layout optimization

**5. Admin Interface (Issue #192)**
Location: `prerequisites/admin.py` - 477 lines

Comprehensive Django admin integration with visual tools and bulk operations:

**Admin Features:**
- **Visual Builder Integration**: PrerequisiteBuilderWidget embedded in admin forms
- **List Display**: Requirement summaries with complexity indicators and type badges
- **Advanced Filtering**: By content type, requirement complexity, description keywords
- **Search Functionality**: Full-text search across descriptions and JSON requirements
- **Permission System**: Role-based access with campaign scoping
- **Bulk Operations**: Copy requirements, template application, validation reporting

**Bulk Operations:**
- **Copy Prerequisites**: Duplicate requirement structures across objects
- **Bulk Validation**: Test multiple characters against requirement sets
- **Template Application**: Apply common requirements to multiple objects
- **Export/Import**: JSON export for backup, migration, and sharing
- **Validation Reports**: Campaign-wide requirement analysis and reporting

#### Data Models

**Prerequisite Model**
Location: `prerequisites/models/__init__.py`

Core model supporting universal attachment via GenericForeignKey:

```python
class Prerequisite(TimestampedMixin, models.Model):
    description = CharField(max_length=500, validators=[validate_description])
    requirements = JSONField(default=dict, blank=True)

    # GenericForeignKey for universal attachment
    content_type = ForeignKey(ContentType, on_delete=SET_NULL, null=True, blank=True)
    object_id = PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey("content_type", "object_id")

    class Meta:
        indexes = [
            Index(fields=["content_type", "object_id"], name="prereq_content_idx"),
            Index(fields=["content_type"], name="prereq_content_type_idx"),
        ]
```

**Key Features:**
- **Universal Attachment**: Works with characters, items, locations, or any Django model
- **JSON Requirements**: Structured requirement storage with comprehensive validation
- **Audit Tracking**: TimestampedMixin provides creation/modification history
- **Database Optimization**: Strategic indexing for GenericForeignKey performance
- **Validation Pipeline**: Multi-layer validation from form to database level

**PrerequisiteCheckResult Model**
Audit trail for requirement checking operations:

```python
class PrerequisiteCheckResult(TimestampedMixin, models.Model):
    content_object = GenericForeignKey("content_type", "object_id")  # Object checked
    character = ForeignKey("characters.Character", on_delete=CASCADE)  # Character tested
    requirements = JSONField()  # Requirements that were evaluated
    result = BooleanField()  # Pass/fail result
    failure_reasons = JSONField(default=list, blank=True)  # Detailed failure information
    checked_at = DateTimeField(auto_now_add=True)  # Timestamp
```

#### Integration Architecture

**Character System Integration**
Seamless integration with polymorphic character hierarchy:

```python
# Works with all character types transparently
base_character = Character.objects.get(id=1)
wod_character = WoDCharacter.objects.get(id=2)
mage_character = MageCharacter.objects.get(id=3)

# Same checking API for all character types
checker = RequirementChecker()
results = [
    checker.check_requirement(base_character, requirement),
    checker.check_requirement(wod_character, requirement),
    checker.check_requirement(mage_character, requirement)
]
```

**Campaign Scoping**
Prerequisites respect campaign boundaries and permissions:

```python
# Campaign-specific requirements
campaign_specific_req = Prerequisite.objects.create(
    description="Chronicle mastery required",
    requirements=all_of(
        trait_req("chronicle_reputation", minimum=3),
        count_with_tag("story_beats", "completed", minimum=10)
    ),
    content_object=campaign_specific_item
)
```

**API Integration**
RESTful endpoints for requirement management (future implementation):

```python
# Planned API endpoints
GET    /api/prerequisites/                    # List prerequisites with filtering
POST   /api/prerequisites/                   # Create new requirement
GET    /api/prerequisites/{id}/              # Retrieve specific requirement
PUT    /api/prerequisites/{id}/              # Update requirement
DELETE /api/prerequisites/{id}/              # Delete requirement
POST   /api/prerequisites/{id}/check/        # Check requirement against character
POST   /api/prerequisites/bulk-check/        # Batch requirement checking
GET    /api/prerequisites/templates/         # Common requirement templates
```

#### Performance Architecture

**Query Optimization Strategies:**
- **N+1 Prevention**: Efficient checking with minimal database operations
- **Bulk Operations**: Batch processing for multiple character/requirement combinations
- **Strategic Indexing**: GenericForeignKey optimization with composite indexes
- **Caching Layer**: Redis caching for frequently-accessed requirements
- **Lazy Evaluation**: Deferred requirement resolution where appropriate

**Scalability Patterns:**
- **Registry Design**: Extensible requirement type system for custom game mechanics
- **Depth Limits**: Maximum 5 levels of nested requirements for performance control
- **JSON Optimization**: Efficient PostgreSQL JSON field operations
- **Query Batching**: Grouped database operations for complex requirement trees

#### Security Model

**JSON Structure Validation**
Location: `prerequisites/validators.py`

Comprehensive validation pipeline preventing malicious or malformed requirements:

```python
from prerequisites.validators import validate_requirements

# Multi-layer validation
try:
    validate_requirements(requirement_json)
except ValidationError as e:
    # Handle validation failure
    return JsonResponse({"error": str(e)}, status=400)
```

**Protection Features:**
- **Structure Validation**: Prevents malformed JSON and infinite recursion
- **Type Safety**: Validates requirement types and parameter constraints
- **XSS Prevention**: Safe JSON rendering in admin widgets
- **Input Sanitization**: Comprehensive cleaning of user-provided data
- **Recursion Limits**: Prevents stack overflow attacks through nested requirements

**Access Control Architecture:**
- **Campaign Isolation**: Requirements scoped to campaign membership
- **Role-Based Permissions**: Admin-only access to bulk operations
- **Content Security**: GenericForeignKey respects source model permissions
- **Audit Trail**: Complete tracking of requirement creation and modifications

#### Testing Coverage

Comprehensive test suite with **417 test methods across 16 test files**:

**Test Organization:**
- **`test_helpers.py`**: Requirement building function validation (48 tests)
- **`test_checkers.py`**: Requirement checking engine logic (73 tests)
- **`test_models.py`**: Prerequisite model validation and constraints (52 tests)
- **`test_admin.py`**: Admin interface functionality and bulk operations (41 tests)
- **`test_visual_builder.py`**: Widget integration and form rendering (29 tests)
- **`test_admin_widgets.py`**: Admin widget customization (22 tests)
- **`test_javascript_components.py`**: Frontend component functionality (38 tests)
- **`test_drag_drop_*`**: Drag-drop interface testing (114 tests across 4 files)

**Coverage Areas:**
- **Requirement Building**: All helper functions with edge cases and error conditions
- **Character Integration**: Full polymorphic character hierarchy testing
- **Complex Logic**: Nested any/all combinations with deep recursion validation
- **Performance**: Database query count validation and optimization verification
- **Security**: XSS prevention, input sanitization, and permission boundary testing
- **Accessibility**: WCAG 2.1 AA compliance verification with automated testing
- **Mobile Support**: Touch interaction testing and responsive design validation
- **Admin Integration**: Bulk operations, filtering, and permission enforcement

#### Usage Patterns

**Character Advancement Requirements**
```python
# Multi-tier advancement system
advancement_req = all_of(
    trait_req("experience_points", minimum=50),
    trait_req("current_level", maximum=4),
    any_of(
        has_item("training", name="Combat Training Certificate"),
        count_with_tag("achievements", "combat", minimum=3),
        all_of(
            trait_req("mentor_approval", exact=1),
            has_item("recommendations", name="Master's Endorsement")
        )
    )
)
```

**Spell/Power Prerequisites**
```python
# Complex magical requirements
fireball_mastery_req = all_of(
    trait_req("arete", minimum=3),
    trait_req("forces", minimum=2),
    trait_req("prime", minimum=1),
    any_of(
        has_item("foci", name="Fire Focus"),
        trait_req("avatar_resonance", exact=1)  # Fire resonance
    ),
    count_with_tag("spells", "forces", minimum=5)
)
```

**Item Usage Requirements**
```python
# Artifact attunement system
legendary_artifact_req = all_of(
    trait_req("willpower", minimum=6),
    any_of(
        trait_req("arete", minimum=4),
        count_with_tag("backgrounds", "avatar", minimum=3)
    ),
    trait_req("artifact_compatibility", exact=1),
    has_item("attunement_ritual", name="Legendary Binding")
)
```

#### Extensibility Framework

**Custom Requirement Types**
Registry pattern supports game-specific requirement checkers:

```python
from prerequisites.checkers import RequirementChecker

@RequirementChecker.register("resonance_match")
def check_resonance_requirement(character, requirement_data):
    """Custom resonance matching for Mage characters."""
    required_resonance = requirement_data.get("resonance")
    character_resonance = getattr(character, "resonance", None)

    passed = character_resonance == required_resonance
    message = f"Resonance {'matches' if passed else 'does not match'} requirement"

    return RequirementCheckResult(passed=passed, message=message)
```

**Future Game System Support**
Ready for expansion to additional RPG systems:

```python
# D&D 5e integration (future)
dnd_requirements = all_of(
    trait_req("level", minimum=5),
    trait_req("strength", minimum=13),
    has_item("class_features", name="Extra Attack"),
    count_with_tag("feats", "combat", minimum=2)
)

# World of Darkness expansion
werewolf_requirements = all_of(
    trait_req("gnosis", minimum=3),
    trait_req("rage", minimum=4),
    has_item("totems", name="Spirit Guide"),
    count_with_tag("gifts", "tribal", minimum=5)
)
```

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

### Location Management Frontend Integration

The location management system demonstrates the hybrid frontend architecture through its comprehensive web interface implementation:

#### Template-Based Foundation

**Base Templates**: Django templates provide the structural HTML and server-side rendering for location management:

```html
<!-- campaign_locations.html - Hierarchical location listing -->
<ul class="location-tree list-unstyled">
  {% for location in locations %}
    <li class="location-item depth-{{ location.get_depth }}">
      <!-- Location card with role-based actions -->
    </li>
  {% endfor %}
</ul>
```

#### Progressive Enhancement with JavaScript

**JavaScript Enhancement** (`static/js/locations.js`): Adds interactive features without breaking functionality if JavaScript fails:

- **Auto-submit filters**: Form submissions without page refresh
- **Real-time preview**: Dynamic hierarchy path generation
- **Mutual filter exclusion**: Smart filter interaction logic
- **Client-side validation**: Enhanced form validation feedback

```javascript
// Progressive enhancement example
document.addEventListener('DOMContentLoaded', function() {
    // Enhance filter forms for better UX
    const ownerSelect = document.getElementById('owner');
    if (ownerSelect) {
        ownerSelect.addEventListener('change', function() {
            filterForm.submit(); // Enhanced: auto-submit
        });
    }

    // Fallback: forms still work without JavaScript
});
```

#### CSS-Based Visual Hierarchy

**Responsive CSS** (`static/css/locations.css`): Creates visual tree structure using pure CSS:

```css
/* Depth-based visual hierarchy */
.location-item.depth-1 { padding-left: 1.5rem; border-left: 2px solid #e9ecef; }
.location-item.depth-2 { padding-left: 3rem; border-left: 2px solid #e9ecef; }

/* Interactive enhancements */
.location-card:hover { transform: translateY(-2px); }
```

#### Accessibility Integration

Following GMA's accessibility-first approach:

- **Semantic HTML**: Proper breadcrumb navigation with `nav` and `ol` elements
- **ARIA Labels**: Screen reader support for hierarchical relationships
- **Keyboard Navigation**: All actions accessible via keyboard
- **Focus Management**: Clear focus indicators for interactive elements

#### Performance Patterns

**Template Optimization**: Minimizes database queries through strategic prefetching:

```python
# View-level optimization
queryset = Location.objects.filter(campaign=campaign).select_related(
    'parent', 'owned_by', 'created_by', 'campaign', 'owned_by__player_owner'
).prefetch_related('children')

# Template efficiency through prefetched data
# No additional queries for related data access
```

**Frontend Asset Optimization**:
- **CSS**: Single location-specific stylesheet loaded only when needed
- **JavaScript**: Progressive enhancement with graceful degradation
- **Images**: Bootstrap icons via CDN for performance

## Real-Time Architecture

### WebSocket Implementation

The GMA implements a comprehensive real-time chat system using Django Channels for scene-based communication.

#### Architecture Overview

```
WebSocket Client (JavaScript)
        ↓
Django Channels Routing (/ws/scenes/{scene_id}/chat/)
        ↓
SceneChatConsumer (WebSocket Consumer)
        ↓
Channel Groups (scene_chat_{scene_id})
        ↓
Message Broadcasting to All Scene Participants
```

#### Core Components

**1. SceneChatConsumer (`scenes/consumers.py`)**

The main WebSocket consumer handling real-time chat functionality:

```python
class SceneChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Authenticate user and validate scene access
        # Join scene-specific channel group

    async def receive(self, text_data):
        # Handle incoming messages with rate limiting
        # Validate message content and permissions
        # Broadcast to channel group
```

**Key Features:**
- **Authentication Required**: Only authenticated users with scene access can connect
- **Permission Validation**: Role-based access control (OWNER → GM → PLAYER → OBSERVER)
- **Rate Limiting**: Configurable limits based on user role and message type
- **Content Filtering**: Basic inappropriate content detection
- **Error Handling**: Comprehensive error responses with security considerations

**2. Message Model (`scenes/models/Message`)**

Persistent storage for chat messages with rich metadata:

```python
class Message(models.Model):
    scene = models.ForeignKey(Scene)
    character = models.ForeignKey(Character, null=True)  # For IC messages
    sender = models.ForeignKey(User)
    content = models.TextField()  # Supports Markdown
    message_type = models.CharField(choices=TYPE_CHOICES)
    recipients = models.ManyToManyField(User)  # For private messages
    created_at = models.DateTimeField(auto_now_add=True)
```

**Message Types:**
- **PUBLIC**: In-character messages requiring character attribution
- **OOC**: Out-of-character messages from players (no character required)
- **PRIVATE**: Private messages between specific users
- **SYSTEM**: GM/Owner-only system messages

**3. Rate Limiting System (`core/rate_limiting.py`)**

Multi-tier rate limiting with Redis backend support:

```python
class ChatRateLimiter:
    limits = {
        "default": {"max_requests": 10, "time_window": 60},   # 10/min
        "staff": {"max_requests": 30, "time_window": 60},     # 30/min
        "system": {"max_requests": 100, "time_window": 60},   # 100/min
    }
```

**Features:**
- **Sliding Window**: Memory-efficient rate limiting implementation
- **Role-Based Limits**: Different limits for users, staff, and system messages
- **Redis Backend**: Distributed rate limiting with fallback to memory
- **Graceful Degradation**: Automatic fallback when Redis unavailable

**4. Message History API (`api/views/scene_views.py:messages`)**

REST API endpoint for message history with advanced filtering:

```bash
GET /api/scenes/{id}/messages/?message_type=PUBLIC,OOC&since=2024-01-15T10:00:00Z
```

**Filtering Capabilities:**
- **Message Type**: Single or comma-separated list (PUBLIC, OOC, PRIVATE, SYSTEM)
- **Character/Sender**: Filter by character or user
- **Date Range**: Since/until timestamp filtering
- **Full-Text Search**: Case-insensitive content search
- **Pagination**: Efficient pagination for large histories

**Permission Integration:**
- **Campaign Owners/GMs**: Can see all message types including private messages
- **Players/Observers**: Can see PUBLIC, OOC, SYSTEM messages, and private messages where they are sender/recipient

#### JavaScript Chat Interface (`static/js/scene-chat.js`)

Full-featured chat UI with WebSocket integration:

**Key Features:**
- **Real-time Updates**: Live message display with automatic scrolling
- **Character Selection**: Dynamic dropdown for in-character messages
- **Message Type Switching**: Toggle between IC, OOC, and Private modes
- **Rate Limit Feedback**: Real-time rate limit status display
- **Connection Management**: Auto-reconnection with connection status indicators
- **Accessibility**: ARIA live regions, keyboard navigation, screen reader support

**Message Handling:**
```javascript
// Send message
websocket.send(JSON.stringify({
    type: 'chat_message',
    message: {
        content: messageText,
        message_type: selectedType,
        character: selectedCharacter,
        recipients: privateRecipients
    }
}));

// Receive message
websocket.onmessage = function(event) {
    const data = JSON.parse(event.data);
    if (data.type === 'chat.message') {
        displayMessage(data);
    }
};
```

#### WebSocket Routing (`scenes/routing.py`)

Channel routing configuration:

```python
websocket_urlpatterns = [
    re_path(r"ws/scenes/(?P<scene_id>\d+)/chat/$", SceneChatConsumer.as_asgi()),
]
```

#### Security Features

**1. Authentication & Authorization**
- WebSocket connections require authenticated users
- Scene access validation based on campaign membership
- Role-based message visibility and sending permissions

**2. Rate Limiting & Abuse Prevention**
- Configurable per-user message limits
- Content length validation (2000 character limit)
- Inappropriate content filtering hooks

**3. Data Validation**
- Message type validation with character requirements
- Cross-campaign character validation
- Recipient validation for private messages

#### Performance Optimizations

**1. Database Queries**
- Optimized message queries with select_related/prefetch_related
- Strategic database indexing for common query patterns
- Efficient pagination for message history

**2. WebSocket Management**
- Channel groups for efficient broadcasting
- Connection cleanup on disconnect
- Heartbeat mechanism for connection health

**3. Caching Strategy**
- Redis caching for rate limiting data
- Memory fallback for high availability
- Periodic cleanup of stale data

#### Scaling Considerations

**Horizontal Scaling:**
- Redis as channel layer backend for multi-server deployments
- Stateless WebSocket consumers for load balancing
- Database connection pooling for efficiency

**Future Enhancements:**
- Message persistence optimization with archiving
- Advanced content filtering with machine learning
- File attachment support for images and documents
- Voice message integration
- Typing indicators for enhanced user experience

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

#### Location-Specific Optimizations

**Hierarchical Query Optimization**:

The location management system implements several performance optimizations for hierarchical data:

```python
# Optimized location list query
queryset = Location.objects.filter(campaign=campaign).select_related(
    'parent', 'owned_by', 'created_by', 'campaign', 'owned_by__player_owner'
).prefetch_related('children')

# Tree traversal with safety limits
def get_descendants(self):
    # Breadth-first search with cycle detection
    queue = list(self.children.select_related("campaign"))
    visited = set()

    while queue and len(visited) < 1000:  # Safety limit
        current = queue.pop(0)
        if current.pk not in visited:
            visited.add(current.pk)
            queue.extend(current.children.all())
```

**Database Index Strategy**:

- **Primary Indexes**: `campaign_id`, `parent_id` for hierarchy navigation
- **Composite Indexes**: `(campaign_id, parent_id)` for tree operations
- **Character Ownership Index**: `owned_by_id` for ownership filtering

**Query Complexity Management**:

- **Safety Limits**: Maximum depth (10 levels) and traversal limits (1000 nodes)
- **Lazy Loading**: Tree methods return QuerySets for efficient filtering
- **Cycle Prevention**: Validation prevents infinite loops in traversal

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

*This architecture documentation should be reviewed and updated as the system evolves. Last updated: 2025-08-24*
