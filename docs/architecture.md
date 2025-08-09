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
return APIError.validation_error(errors)
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

## Data Model Architecture

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

*This architecture documentation should be reviewed and updated as the system evolves. Last updated: 2025-01-08*
