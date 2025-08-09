# GMA Development Guide

## Table of Contents

1. [Development Environment Setup](#development-environment-setup)
2. [Test-Driven Development Workflow](#test-driven-development-workflow)
3. [Code Standards and Best Practices](#code-standards-and-best-practices)
4. [Service Layer Development](#service-layer-development)
5. [API Development Patterns](#api-development-patterns)
6. [Frontend Development](#frontend-development)
7. [Database Development](#database-development)
8. [Testing Practices](#testing-practices)
9. [Git Workflow](#git-workflow)
10. [Debugging and Troubleshooting](#debugging-and-troubleshooting)

## Development Environment Setup

### Prerequisites

- **Python 3.11**: Required for Django 5.2.4+
- **Node.js 20**: For React frontend development
- **Conda**: For Python environment management
- **PostgreSQL**: Primary database (included in conda environment)
- **Redis**: For caching and real-time features

### Initial Setup

```bash
# Clone repository
git clone <repository-url>
cd gma

# Create conda environment
conda env create -f environment.yml
conda activate gma

# Install frontend dependencies
cd frontend
npm install
cd ..

# Set up database
make reset-dev

# Create superuser
make create-superuser

# Start development environment
make runserver
```

### Development URLs

- **Django Application**: http://localhost:8080
- **Django Admin**: http://localhost:8080/admin/
- **React Development Server**: http://localhost:3000 (started with Django)
- **API Base**: http://localhost:8080/api/

### Environment Variables

Create `.env` file for local development:

```bash
# Database
DB_NAME=gm_app_db
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_HOST=127.0.0.1
REDIS_PORT=6379

# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Frontend
REACT_APP_API_URL=http://localhost:8080/api
```

## Test-Driven Development Workflow

### TDD Philosophy

The GMA project follows strict Test-Driven Development principles:

1. **Red**: Write a failing test first
2. **Green**: Write minimal code to make the test pass
3. **Refactor**: Improve code quality while keeping tests green
4. **Commit**: Frequent commits at each successful step

### Feature Development Workflow

```bash
# 1. Create feature branch
git checkout -b feature/user-profile-enhancement

# 2. Write failing tests first
python manage.py test users.tests.test_profile_api

# 3. Implement minimal code to pass tests
# Edit models/views/serializers as needed

# 4. Run tests frequently
make test

# 5. Commit when tests pass or failure count decreases
git add .
git commit -m "Add user profile update validation tests"

# 6. Continue TDD cycle until feature complete
# 7. Run full test suite
make test-coverage

# 8. Code review and cleanup
# 9. Create pull request
```

### Test Categories

#### Unit Tests
Test individual components in isolation:

```python
# Example: campaigns/tests/test_services.py
class TestMembershipService(TestCase):
    def setUp(self):
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.user
        )
        self.service = MembershipService(self.campaign)

    def test_add_member_valid_role(self):
        """Test adding member with valid role."""
        new_user = User.objects.create_user("newuser", "new@example.com")

        membership = self.service.add_member(new_user, "PLAYER")

        self.assertEqual(membership.user, new_user)
        self.assertEqual(membership.role, "PLAYER")
        self.assertEqual(membership.campaign, self.campaign)
```

#### Integration Tests
Test component interactions:

```python
# Example: api/tests/test_campaign_integration.py
class TestCampaignAPIIntegration(APITestCase):
    def test_create_campaign_and_add_member(self):
        """Test full campaign creation and membership flow."""
        # Create campaign
        response = self.client.post('/api/campaigns/', {
            'name': 'Integration Test Campaign',
            'game_system': 'Test System'
        })
        self.assertEqual(response.status_code, 201)
        campaign_id = response.data['id']

        # Add member via API
        response = self.client.post(f'/api/campaigns/{campaign_id}/members/', {
            'user_id': self.other_user.id,
            'role': 'PLAYER'
        })
        self.assertEqual(response.status_code, 201)
```

#### Security Tests
Test permission boundaries:

```python
# Example: api/tests/test_security.py
class TestCampaignSecurity(APITestCase):
    def test_private_campaign_hidden_from_non_members(self):
        """Test that private campaigns return 404 for non-members."""
        private_campaign = Campaign.objects.create(
            name="Private Campaign",
            owner=self.other_user,
            is_public=False
        )

        response = self.client.get(f'/api/campaigns/{private_campaign.id}/')
        self.assertEqual(response.status_code, 404)
        self.assertIn("not found", response.data['detail'].lower())
```

### Running Tests

```bash
# Run all tests
make test

# Run specific app tests
python manage.py test campaigns

# Run specific test class
python manage.py test campaigns.tests.test_services.TestMembershipService

# Run with coverage
make test-coverage
python -m coverage report
python -m coverage html  # Generate HTML report

# Run specific test with verbose output
python manage.py test campaigns.tests.test_api.TestCampaignAPI.test_create_campaign -v 2
```

### Test Database Management

```bash
# Reset test database (if needed)
python manage.py flush --settings=gm_app.test_settings

# Create test data for manual testing
python manage.py create_test_data
python manage.py create_test_data --users=10 --campaigns=5
```

## Code Standards and Best Practices

### Python Code Style

The project follows Black and isort formatting with flake8 linting:

```bash
# Format code
isort --profile black .
black .

# Check linting
flake8 .

# Type checking
mypy .

# Check without making changes
isort --profile black --check-only --diff .
black --check --diff .
```

### Django Patterns

#### Model Design

```python
# Good: Clear, focused model with proper validation
class Campaign(models.Model):
    name = models.CharField(max_length=200, help_text="Campaign name")
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="owned_campaigns"
    )

    class Meta:
        db_table = "campaigns_campaign"
        ordering = ["-updated_at", "name"]
        indexes = [
            models.Index(fields=["is_active", "is_public"]),
        ]

    def clean(self):
        """Validate model data."""
        if not self.name.strip():
            raise ValidationError("Campaign name is required.")

    def save(self, *args, **kwargs):
        """Auto-generate slug on save."""
        if not self.slug:
            self.slug = self._generate_unique_slug()
        super().save(*args, **kwargs)
```

#### Service Layer Patterns

```python
# Good: Service class with clear responsibilities
class MembershipService:
    """Service for campaign membership operations."""

    def __init__(self, campaign: Campaign):
        self.campaign = campaign

    @transaction.atomic
    def add_member(self, user: User, role: str) -> CampaignMembership:
        """Add member with validation and business rules."""
        # Validate role
        if role not in dict(CampaignMembership.ROLE_CHOICES):
            raise ValidationError(f"Invalid role: {role}")

        # Business rule: no duplicate memberships
        if self.campaign.memberships.filter(user=user).exists():
            raise ValidationError("User is already a member")

        return CampaignMembership.objects.create(
            campaign=self.campaign,
            user=user,
            role=role
        )
```

#### API View Patterns

```python
# Good: Clean API view with standardized error handling
class CampaignDetailAPIView(generics.RetrieveAPIView):
    serializer_class = CampaignDetailSerializer

    def get_queryset(self):
        return Campaign.objects.visible_to_user(self.request.user)

    def get_object(self):
        """Get campaign with permission checking."""
        campaign, error_response = SecurityResponseHelper.safe_get_or_404(
            self.get_queryset(),
            self.request.user,
            permission_check=None,  # Visibility handled by queryset
            pk=self.kwargs['pk']
        )
        if error_response:
            raise NotFound("Campaign not found.")
        return campaign
```

### Error Handling Patterns

```python
# Good: Use standardized error responses
from api.errors import APIError, SecurityResponseHelper

def my_api_view(request):
    try:
        # Business logic here
        result = service.do_something()
        return Response({"data": result})
    except ValidationError as e:
        return APIError.validation_error(e)
    except SomeModel.DoesNotExist:
        return APIError.not_found()
    except PermissionDenied:
        return APIError.permission_denied_as_not_found()
```

### Security Best Practices

1. **Information Hiding**: Always return 404 for permission denied
2. **Input Validation**: Validate at multiple layers (serializer, service, model)
3. **CSRF Protection**: Required for all state-changing operations
4. **Generic Error Messages**: Don't leak system information

```python
# Good: Security-focused permission checking
def check_campaign_access(user, campaign):
    """Check if user can access campaign."""
    if not user.is_authenticated:
        return False

    # Public campaigns are accessible to all authenticated users
    if campaign.is_public:
        return True

    # Private campaigns only accessible to members
    return (
        campaign.owner == user or
        campaign.memberships.filter(user=user).exists()
    )
```

## Service Layer Development

### When to Create Services

Create service classes for:

- **Complex Business Logic**: Operations involving multiple models
- **Transaction Management**: Operations requiring atomicity
- **Reusable Operations**: Logic used in both web views and API
- **External Integrations**: API calls, email sending, file processing

### Service Structure

```python
# campaigns/services.py
class CampaignService:
    """Service for campaign-related operations."""

    def __init__(self, campaign: Optional[Campaign] = None):
        """Initialize service, optionally for specific campaign."""
        self.campaign = campaign

    @transaction.atomic
    def create_campaign_with_initial_setup(
        self,
        owner: User,
        **campaign_data
    ) -> Campaign:
        """Create campaign with initial configuration."""
        # Create campaign
        campaign = Campaign(owner=owner, **campaign_data)
        campaign.full_clean()
        campaign.save()

        # Create initial game session
        initial_session = GameSession.objects.create(
            campaign=campaign,
            name="Campaign Setup",
            created_by=owner
        )

        # Send welcome notification
        NotificationService.send_campaign_created(campaign)

        return campaign

    def get_campaign_statistics(self) -> Dict[str, Any]:
        """Get comprehensive campaign statistics."""
        if not self.campaign:
            raise ValueError("No campaign associated with service")

        return {
            'member_count': self.campaign.memberships.count() + 1,  # +1 for owner
            'active_sessions': self.campaign.sessions.filter(is_active=True).count(),
            'total_characters': self.campaign.characters.count(),
            'recent_activity': self._get_recent_activity()
        }
```

### Service Testing

```python
class TestCampaignService(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("testuser", "test@example.com")
        self.service = CampaignService()

    def test_create_campaign_with_initial_setup(self):
        """Test complete campaign creation workflow."""
        campaign_data = {
            'name': 'Test Campaign',
            'game_system': 'D&D 5e',
            'description': 'Test description'
        }

        campaign = self.service.create_campaign_with_initial_setup(
            self.user,
            **campaign_data
        )

        # Verify campaign created
        self.assertEqual(campaign.name, 'Test Campaign')
        self.assertEqual(campaign.owner, self.user)

        # Verify initial session created
        self.assertTrue(
            campaign.sessions.filter(name="Campaign Setup").exists()
        )
```

## API Development Patterns

### URL Patterns

Use consistent, RESTful URL patterns:

```python
# api/urls/campaign_urls.py
urlpatterns = [
    # Resource collections
    path('campaigns/', CampaignListAPIView.as_view(), name='campaign-list'),
    path('campaigns/', CampaignCreateAPIView.as_view(), name='campaign-create'),

    # Resource details
    path('campaigns/<int:pk>/', CampaignDetailAPIView.as_view(), name='campaign-detail'),

    # Nested resources
    path('campaigns/<int:campaign_pk>/members/', MemberListAPIView.as_view()),
    path('campaigns/<int:campaign_pk>/invitations/', InvitationListAPIView.as_view()),

    # Actions on resources
    path('campaigns/<int:pk>/search-users/', UserSearchAPIView.as_view()),
    path('invitations/<int:pk>/accept/', AcceptInvitationAPIView.as_view()),
]
```

### Serializer Patterns

#### Base Serializer Design

```python
# Good: Clean serializer with proper validation
class CampaignSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    user_role = serializers.SerializerMethodField()

    class Meta:
        model = Campaign
        fields = ['id', 'name', 'description', 'owner', 'user_role']
        read_only_fields = ['id', 'owner', 'user_role']

    def get_user_role(self, obj):
        """Get current user's role in campaign."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.get_user_role(request.user)
        return None

    def validate_name(self, value):
        """Validate campaign name."""
        if not value.strip():
            raise serializers.ValidationError("Name cannot be blank.")
        return value.strip()
```

#### Nested Serializers

```python
# Good: Efficient nested serializer
class CampaignDetailSerializer(CampaignSerializer):
    memberships = CampaignMembershipSerializer(many=True, read_only=True)

    class Meta(CampaignSerializer.Meta):
        fields = CampaignSerializer.Meta.fields + ['memberships']

    def to_representation(self, instance):
        """Customize representation based on user role."""
        data = super().to_representation(instance)

        # Only include sensitive data for owners/GMs
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            user_role = instance.get_user_role(request.user)
            if user_role not in ['OWNER', 'GM']:
                # Remove sensitive fields for regular players
                data.pop('member_emails', None)

        return data
```

### View Patterns

#### Generic Views

```python
# Good: Clean generic view with proper filtering
class CampaignListAPIView(generics.ListAPIView):
    serializer_class = CampaignSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['game_system', 'is_public']
    search_fields = ['name', 'description']

    def get_queryset(self):
        """Return campaigns visible to user."""
        return (
            Campaign.objects
            .visible_to_user(self.request.user)
            .select_related('owner')
            .prefetch_related('memberships__user')
        )
```

#### Custom Action Views

```python
# Good: Clean action view with proper validation
class AcceptInvitationAPIView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        """Accept campaign invitation."""
        # Get invitation with security check
        invitation, error = SecurityResponseHelper.safe_get_or_404(
            CampaignInvitation.objects,
            request.user,
            lambda user, inv: inv.invited_user == user and inv.status == 'PENDING',
            pk=pk
        )
        if error:
            return error

        try:
            # Use service for business logic
            service = InvitationService(invitation.campaign)
            membership = service.accept_invitation(invitation)

            serializer = InvitationAcceptResponseSerializer({
                'detail': 'Invitation accepted successfully.',
                'membership': membership
            })
            return Response(serializer.data)

        except ValidationError as e:
            return APIError.validation_error(e)
```

## Frontend Development

### React Component Structure

```typescript
// components/CampaignList.tsx
interface Campaign {
  id: number;
  name: string;
  game_system: string;
  user_role: string | null;
  member_count: number;
}

interface CampaignListProps {
  campaigns: Campaign[];
  onCampaignSelect: (campaign: Campaign) => void;
}

export const CampaignList: React.FC<CampaignListProps> = ({
  campaigns,
  onCampaignSelect
}) => {
  return (
    <div className="campaign-list">
      {campaigns.map(campaign => (
        <div
          key={campaign.id}
          className="campaign-card"
          onClick={() => onCampaignSelect(campaign)}
        >
          <h3>{campaign.name}</h3>
          <p>{campaign.game_system}</p>
          <div className="campaign-meta">
            <span className="member-count">{campaign.member_count} members</span>
            {campaign.user_role && (
              <span className="user-role">{campaign.user_role}</span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
};
```

### API Integration

```typescript
// services/campaignApi.ts
import { apiClient } from './api';

export interface CreateCampaignData {
  name: string;
  description?: string;
  game_system: string;
  is_public?: boolean;
}

export const campaignApi = {
  async getCampaigns(params?: { q?: string; role?: string }) {
    const response = await apiClient.get('/campaigns/', { params });
    return response.data;
  },

  async createCampaign(data: CreateCampaignData) {
    const response = await apiClient.post('/campaigns/', data);
    return response.data;
  },

  async getCampaignDetail(id: number) {
    const response = await apiClient.get(`/campaigns/${id}/`);
    return response.data;
  }
};
```

## Database Development

### Migration Best Practices

```python
# Good migration with proper field definitions
class Migration(migrations.Migration):
    dependencies = [
        ('campaigns', '0010_add_campaign_invitation_model'),
    ]

    operations = [
        migrations.AddField(
            model_name='campaign',
            name='allow_observer_join',
            field=models.BooleanField(
                default=False,
                help_text='Allow anyone to join as observer without invitation'
            ),
        ),
        migrations.AddIndex(
            model_name='campaign',
            index=models.Index(
                fields=['is_public', 'is_active'],
                name='campaigns_public_active_idx'
            ),
        ),
    ]
```

### Query Optimization

```python
# Good: Optimized query with select_related and prefetch_related
def get_campaigns_with_members(user):
    """Get campaigns with optimized member loading."""
    return (
        Campaign.objects
        .visible_to_user(user)
        .select_related('owner')  # Single foreign key
        .prefetch_related(
            'memberships__user',     # Reverse foreign key with related
            'invitations__invited_user'
        )
        .annotate(
            member_count=models.Count('memberships') + 1  # +1 for owner
        )
    )
```

### Database Indexes

```python
# models.py - Strategic index placement
class Campaign(models.Model):
    # ... fields ...

    class Meta:
        indexes = [
            # Compound index for common query patterns
            models.Index(fields=['is_active', 'is_public']),
            models.Index(fields=['owner', 'is_active']),

            # Single field indexes for filtering
            models.Index(fields=['created_at']),
            models.Index(fields=['game_system']),
        ]
```

## Testing Practices

### Test Organization

```
app/tests/
├── __init__.py
├── test_models.py          # Model validation, methods
├── test_services.py        # Service layer logic
├── test_api.py            # API endpoint functionality
├── test_permissions.py    # Permission/security tests
├── test_integration.py    # Cross-component tests
└── test_edge_cases.py     # Error conditions, boundaries
```

### Test Fixtures and Factories

```python
# tests/factories.py
import factory
from django.contrib.auth import get_user_model

User = get_user_model()

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')

class CampaignFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Campaign

    name = factory.Faker('sentence', nb_words=3)
    description = factory.Faker('text', max_nb_chars=200)
    owner = factory.SubFactory(UserFactory)
    game_system = factory.Faker('word')
```

### Comprehensive Test Coverage

```python
class TestCampaignMembershipAPI(APITestCase):
    def setUp(self):
        self.owner = UserFactory()
        self.campaign = CampaignFactory(owner=self.owner)
        self.member = UserFactory()
        self.non_member = UserFactory()

    def test_add_member_success(self):
        """Test successful member addition."""
        self.client.force_authenticate(self.owner)

        response = self.client.post(
            f'/api/campaigns/{self.campaign.id}/members/',
            {'user_id': self.member.id, 'role': 'PLAYER'}
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['role'], 'PLAYER')
        self.assertTrue(
            self.campaign.memberships.filter(user=self.member).exists()
        )

    def test_add_member_permission_denied(self):
        """Test member addition by non-owner fails."""
        self.client.force_authenticate(self.non_member)

        response = self.client.post(
            f'/api/campaigns/{self.campaign.id}/members/',
            {'user_id': self.member.id, 'role': 'PLAYER'}
        )

        self.assertEqual(response.status_code, 404)  # Security: 404 not 403

    def test_add_member_invalid_role(self):
        """Test adding member with invalid role."""
        self.client.force_authenticate(self.owner)

        response = self.client.post(
            f'/api/campaigns/{self.campaign.id}/members/',
            {'user_id': self.member.id, 'role': 'INVALID_ROLE'}
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('role', response.data)
```

## Git Workflow

### Branch Naming

```bash
# Feature development
feature/user-authentication-enhancement
feature/campaign-invitation-system

# Bug fixes
bugfix/campaign-membership-validation
hotfix/security-permission-check

# Refactoring
refactor/service-layer-extraction
refactor/api-error-standardization

# Testing
test/campaign-membership-edge-cases
```

### Commit Messages

Follow conventional commit format:

```bash
# Feature commits
git commit -m "feat: Add campaign invitation acceptance API endpoint

- Implement invitation acceptance with validation
- Add service layer method for business logic
- Include comprehensive test coverage
- Update API documentation"

# Bug fix commits
git commit -m "fix: Prevent duplicate campaign memberships

- Add unique constraint validation in service layer
- Handle duplicate membership attempts gracefully
- Return appropriate error message to user
- Add regression tests"

# Test commits
git commit -m "test: Add edge case tests for membership service

- Test adding owner as member (should fail)
- Test invalid role assignments
- Test bulk operations with mixed success/failure
- Improve test coverage to 95%"
```

### Pull Request Process

```bash
# 1. Create feature branch from main
git checkout main
git pull origin main
git checkout -b feature/new-feature

# 2. Develop with TDD
# Write tests -> Implement -> Commit frequently

# 3. Run quality checks before PR
make test-coverage
isort --profile black --check-only .
black --check .
flake8 .

# 4. Push and create PR
git push origin feature/new-feature
# Create PR via GitHub/GitLab interface

# 5. Address review feedback
# Make changes, commit, push

# 6. Merge after approval
# Squash and merge for clean history
```

## Debugging and Troubleshooting

### Django Debug Settings

```python
# settings.py - Development debugging
DEBUG = True
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'DEBUG',  # Show SQL queries
        },
        'campaigns.services': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
```

### Debugging API Issues

```python
# Use Django shell for API debugging
python manage.py shell

from campaigns.models import Campaign
from campaigns.services import MembershipService
from django.contrib.auth import get_user_model

User = get_user_model()

# Test service logic directly
campaign = Campaign.objects.get(id=1)
user = User.objects.get(id=2)
service = MembershipService(campaign)

# Debug membership addition
try:
    membership = service.add_member(user, "PLAYER")
    print(f"Success: {membership}")
except Exception as e:
    print(f"Error: {e}")
```

### Common Issues and Solutions

#### Database Issues

```bash
# Reset database completely
make reset-dev

# Apply specific migration
python manage.py migrate campaigns 0010

# Check migration status
python manage.py showmigrations
```

#### Test Issues

```bash
# Run single failing test with verbose output
python manage.py test campaigns.tests.test_api.TestCampaignAPI.test_create_campaign -v 2

# Run with pdb debugging
python manage.py test --debug-mode campaigns.tests.test_api

# Check test database
python manage.py dbshell --settings=gm_app.test_settings
```

#### Frontend Issues

```bash
# Clear React build cache
cd frontend
npm run build:clean
npm run build

# Check API connectivity
curl -H "Content-Type: application/json" http://localhost:8080/api/campaigns/
```

### Performance Debugging

```python
# Add to views for query debugging
from django.db import connection

def my_view(request):
    # Your view logic here

    # Debug queries (development only)
    if settings.DEBUG:
        print(f"Queries: {len(connection.queries)}")
        for query in connection.queries[-5:]:  # Last 5 queries
            print(f"Time: {query['time']}s")
            print(f"SQL: {query['sql']}")
```

### Health Check Commands

```bash
# Check system health
python manage.py health_check

# Check specific components
python manage.py health_check --database
python manage.py health_check --redis

# Generate test data for debugging
python manage.py create_test_data --users=5 --campaigns=3
```

---

*This development guide should be updated as new patterns and practices are established. Last updated: 2025-01-08*
