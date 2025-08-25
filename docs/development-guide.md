# GMA Development Guide

## Table of Contents

1. [Development Environment Setup](#development-environment-setup)
2. [Test-Driven Development Workflow](#test-driven-development-workflow)
3. [Code Standards and Best Practices](#code-standards-and-best-practices)
4. [Service Layer Development](#service-layer-development)
5. [Prerequisite System Development](#prerequisite-system-development)
6. [Source Reference Development](#source-reference-development)
7. [API Development Patterns](#api-development-patterns)
8. [Frontend Development](#frontend-development)
9. [Database Development](#database-development)
10. [Testing Practices](#testing-practices)
11. [Git Workflow](#git-workflow)
12. [Debugging and Troubleshooting](#debugging-and-troubleshooting)

## Development Environment Setup

### Prerequisites

- **Python 3.11**: Required for Django 5.2.4+
- **Node.js 20**: For React frontend development
- **Conda**: For Python environment management
- **PostgreSQL**: Primary database (included in conda environment)
- **Redis**: For caching and real-time features
- **django-fsm-2**: For state machine management (installed via pip)

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

#### Migration Safety Tests
Test database migration safety and data integrity:

```python
# Example: core/tests/test_migration_strategy.py
class TestMigrationSafety(TransactionTestCase):
    """Test migration safety for mixin field application."""

    def test_character_data_preservation(self):
        """Test character data preservation during migration."""
        # Create test data
        original_data = self.create_sample_data(20)

        # Verify count preserved
        self.assertEqual(Character.objects.count(), 20)

        # Verify each character's data preserved
        for char in original_data["characters"]:
            char.refresh_from_db()
            self.assertIsNotNone(char.name)
            self.assertIsNotNone(char.campaign)
            self.assertIsNotNone(char.created_at)
            self.assertIsNotNone(char.updated_at)

    def test_migration_rollback_safety(self):
        """Test that migrations can be safely rolled back."""
        # Test data integrity after hypothetical rollback
        original_data = self.create_sample_data(10)

        # Verify core data would survive rollback
        for char in original_data["characters"]:
            self.assertIsNotNone(char.name)
            self.assertIsNotNone(char.campaign_id)
            self.assertIsNotNone(char.player_owner_id)
```

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
python manage.py test items

# Run specific test class
python manage.py test campaigns.tests.test_services.TestMembershipService
python manage.py test items.tests.test_admin.ItemAdminTest

# Run migration safety tests
python manage.py test core.tests.test_migration_strategy

# Run with coverage
make test-coverage
python -m coverage report
python -m coverage html  # Generate HTML report

# Run specific test with verbose output
python manage.py test campaigns.tests.test_api.TestCampaignAPI.test_create_campaign -v 2

# Run performance tests for migrations
python manage.py test core.tests.test_migration_strategy.MigrationPerformanceTest -v 2

# Test django-fsm-2 installation and functionality
python manage.py test core.tests.test_django_fsm_installation
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

**Using Core Model Mixins:**

```python
# Good: Using TimestampedMixin for new models
from core.models.mixins import TimestampedMixin

class GameSession(TimestampedMixin):
    """Game session model with automatic timestamp tracking."""
    name = models.CharField(max_length=200, help_text="Session name")
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name="sessions"
    )
    status = models.CharField(
        max_length=20,
        choices=[('ACTIVE', 'Active'), ('COMPLETED', 'Completed')],
        default='ACTIVE'
    )

    class Meta:
        db_table = "campaigns_gamesession"
        ordering = ["-updated_at", "name"]
        indexes = [
            models.Index(fields=["campaign", "status"]),
            models.Index(fields=["updated_at"]),  # For recent activity queries
        ]

    def __str__(self):
        return f"{self.campaign.name}: {self.name}"
```

**Mixin Usage Guidelines:**

- **Use TimestampedMixin** for new models needing timestamp tracking
- **Don't retrofit existing models** that already have timestamp fields
- **Keep it simple** - mixins should provide focused functionality
- **Test mixin behavior** as part of model tests

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
        return APIError.create_validation_error_response(e)
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

### State Machine Development

The GMA project uses django-fsm-2 for managing state transitions in domain models. This provides workflow management for campaigns, scenes, and characters.

#### Character Status Implementation (Current)

The Character model includes a fully implemented status workflow:

```python
from django_fsm import FSMField, transition

class Character(models.Model):
    """Character model with status workflow."""
    status = FSMField(default='DRAFT', max_length=20)

    @transition(field=status, source='DRAFT', target='SUBMITTED')
    def submit_for_approval(self, user):
        """Character owner submits for approval."""
        if self.player_owner != user:
            raise PermissionError("Only character owners can submit for approval")

    @transition(field=status, source='SUBMITTED', target='APPROVED')
    def approve(self, user):
        """GM approves character for campaign."""
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

#### State Machine Patterns

**Basic FSM Model (Example for Future Development):**
```python
from django_fsm import FSMField, transition

class GameSession(models.Model):
    """Example model with state machine."""
    name = models.CharField(max_length=200)
    status = FSMField(default='planning', max_length=50)

    @transition(field=status, source='planning', target='active')
    def start_session(self):
        """Begin the game session."""
        self.started_at = timezone.now()

    @transition(field=status, source='active', target='completed')
    def complete_session(self):
        """End the game session."""
        self.completed_at = timezone.now()

    @transition(field=status, source=['planning', 'active'], target='cancelled')
    def cancel_session(self):
        """Cancel the game session."""
        self.cancelled_at = timezone.now()
```

**State Machine with Validation:**
```python
from django_fsm import FSMField, transition
from django.core.exceptions import ValidationError

class Campaign(models.Model):
    state = FSMField(default='draft', max_length=50)

    @transition(field=state, source='draft', target='active')
    def activate(self):
        """Activate campaign for players."""
        # Validation before transition
        if not self.has_minimum_players():
            raise ValidationError("Campaign needs at least one player")

        # Business logic after transition
        self.send_activation_notifications()

    def has_minimum_players(self):
        """Check if campaign has minimum required players."""
        return self.memberships.filter(role='PLAYER').exists()
```

**Testing Character Status Transitions:**
```python
class TestCharacterStatusFSM(TestCase):
    def setUp(self):
        # Set up users and campaign
        self.owner = User.objects.create_user("owner", "owner@test.com")
        self.gm = User.objects.create_user("gm", "gm@test.com")
        self.player = User.objects.create_user("player", "player@test.com")

        self.campaign = Campaign.objects.create(
            name="Test Campaign", owner=self.owner, game_system="Test"
        )

        # Add memberships
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm, role="GM"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )

        self.character = Character.objects.create(
            name="Test Character",
            campaign=self.campaign,
            player_owner=self.player,
            game_system="Test"
        )

    def test_character_lifecycle(self):
        """Test complete character status lifecycle."""
        # Initial state
        self.assertEqual(self.character.status, 'DRAFT')

        # Submit for approval
        self.character.submit_for_approval(user=self.player)
        self.character.save(audit_user=self.player)
        self.assertEqual(self.character.status, 'SUBMITTED')

        # Approve character
        self.character.approve(user=self.gm)
        self.character.save(audit_user=self.gm)
        self.assertEqual(self.character.status, 'APPROVED')

        # Retire character
        self.character.retire(user=self.player)
        self.character.save(audit_user=self.player)
        self.assertEqual(self.character.status, 'RETIRED')

    def test_permission_validation(self):
        """Test that transitions validate permissions."""
        self.character.submit_for_approval(user=self.player)
        self.character.save(audit_user=self.player)

        # Player cannot approve their own character
        with self.assertRaises(PermissionError):
            self.character.approve(user=self.player)

        # GM can approve
        self.character.approve(user=self.gm)
        self.character.save(audit_user=self.gm)
        self.assertEqual(self.character.status, 'APPROVED')

    def test_invalid_transitions(self):
        """Test that invalid transitions are blocked."""
        # Cannot approve from DRAFT (must submit first)
        with self.assertRaises(TransitionNotAllowed):
            self.character.approve(user=self.gm)

        # Cannot retire from DRAFT (must be APPROVED)
        with self.assertRaises(TransitionNotAllowed):
            self.character.retire(user=self.player)

    def test_audit_trail_integration(self):
        """Test that status transitions create audit entries."""
        initial_count = self.character.audit_entries.count()

        # Perform transition
        self.character.submit_for_approval(user=self.player)
        self.character.save(audit_user=self.player)

        # Check audit entry was created
        new_count = self.character.audit_entries.count()
        self.assertEqual(new_count, initial_count + 1)

        # Verify audit content
        audit_entry = self.character.audit_entries.latest('timestamp')
        self.assertEqual(audit_entry.changed_by, self.player)
        self.assertIn('status', audit_entry.field_changes)
        self.assertEqual(audit_entry.field_changes['status']['old'], 'DRAFT')
        self.assertEqual(audit_entry.field_changes['status']['new'], 'SUBMITTED')
```

**Testing State Machines (General Pattern):**
```python
class TestGameSessionFSM(TestCase):
    def setUp(self):
        self.session = GameSession.objects.create(name="Test Session")

    def test_session_lifecycle(self):
        """Test complete session state transitions."""
        # Initial state
        self.assertEqual(self.session.status, 'planning')

        # Start session
        self.session.start_session()
        self.assertEqual(self.session.status, 'active')
        self.assertIsNotNone(self.session.started_at)

        # Complete session
        self.session.complete_session()
        self.assertEqual(self.session.status, 'completed')
        self.assertIsNotNone(self.session.completed_at)

    def test_invalid_transition(self):
        """Test that invalid transitions raise errors."""
        self.session.status = 'completed'

        with self.assertRaises(TransitionNotAllowed):
            self.session.start_session()
```

#### FSM Integration Guidelines

**When to Use State Machines:**
- Models with clear lifecycle stages (campaigns, scenes, characters)
- Complex business rules around state transitions
- Need for audit trail of state changes
- API endpoints that modify model state

**Best Practices:**
- Use descriptive state names ('DRAFT', 'SUBMITTED', 'APPROVED')
- Include validation logic in transition methods
- Test all valid and invalid transition paths
- Consider permission checks in transition methods
- Document state diagrams for complex workflows
- Integrate with audit trail systems (DetailedAuditableMixin)
- Use consistent naming patterns for transition methods

**Character Status Implementation Best Practices:**
- Always validate user permissions in transition methods
- Use save(audit_user=user) after transitions for audit trail
- Test both successful transitions and permission errors
- Verify audit entries are created for each transition
- Test edge cases like terminal states (RETIRED, DECEASED)
- Use descriptive error messages for permission failures

**State Machine Testing:**
```python
# Test all valid transitions
def test_all_valid_transitions(self):
    """Test each valid state transition."""
    transitions = [
        ('planning', 'start_session', 'active'),
        ('active', 'complete_session', 'completed'),
        ('planning', 'cancel_session', 'cancelled'),
    ]

    for source, method, target in transitions:
        session = GameSession.objects.create(name="Test")
        session.status = source

        getattr(session, method)()
        self.assertEqual(session.status, target)

# Test invalid transitions
def test_invalid_transitions(self):
    """Test that invalid transitions are blocked."""
    session = GameSession.objects.create(name="Test")
    session.status = 'completed'

    with self.assertRaises(TransitionNotAllowed):
        session.start_session()
```

## Prerequisite System Development

### Overview

The prerequisite system provides comprehensive requirement validation for character advancement, item usage, spell casting, and other game mechanics. It combines structured JSON requirements, intuitive helper functions, a powerful checking engine, and advanced visual building tools across Issues #188-192.

### Architecture Components

The prerequisite system consists of five main components:

1. **Requirement Helpers (Issue #188)**: `prerequisites/helpers.py` - Helper functions for building JSON requirements
2. **Checking Engine (Issue #189)**: `prerequisites/checkers.py` - Validation engine with recursive checking
3. **Visual Builder UI (Issue #190)**: `prerequisites/widgets.py` - Django form widget integration
4. **Drag-Drop Interface (Issue #191)**: 7 JavaScript files - Advanced visual requirement building
5. **Admin Interface (Issue #192)**: `prerequisites/admin.py` - Full Django admin integration

### Development Workflow

#### Setting Up Prerequisite Development

```bash
# All prerequisite components are included in the main GMA environment
conda activate gma

# Run prerequisite-specific tests
python manage.py test prerequisites.tests

# Test specific components
python manage.py test prerequisites.tests.test_helpers
python manage.py test prerequisites.tests.test_checkers
python manage.py test prerequisites.tests.test_visual_builder
python manage.py test prerequisites.tests.test_drag_drop_builder

# Run all drag-drop related tests
python manage.py test prerequisites.tests.test_drag_drop*
```

#### Creating Helper Functions

When adding new requirement types, follow this pattern:

```python
# In prerequisites/helpers.py

def new_requirement_type(param1, param2=None, **kwargs):
    """
    Generate a new requirement type JSON structure.

    Args:
        param1: Required parameter description
        param2: Optional parameter description
        **kwargs: Additional fields for the requirement

    Returns:
        Dictionary containing the requirement in JSON format

    Raises:
        ValidationError: If parameters are invalid

    Examples:
        >>> new_requirement = new_requirement_type("value", minimum=3)
        {"new_type": {"param1": "value", "minimum": 3}}
    """
    # Validate required parameters
    if not isinstance(param1, str) or not param1.strip():
        raise ValidationError("param1 must be a non-empty string")

    # Build requirement data
    req_data = {"param1": param1.strip()}

    if param2 is not None:
        if not isinstance(param2, int) or param2 < 0:
            raise ValidationError("param2 must be a non-negative integer")
        req_data["param2"] = param2

    # Add additional fields
    for key, value in kwargs.items():
        req_data[key] = value

    # Create requirement structure
    requirement = {"new_type": req_data}

    # Validate generated structure
    try:
        validators.validate_requirements(requirement)
    except ValidationError as e:
        raise ValidationError(f"Generated requirement is invalid: {e}")

    return requirement
```

#### Implementing Requirement Checkers

Add new requirement types to the checking engine:

```python
# In prerequisites/checkers.py

@RequirementChecker.register("new_type")
def check_new_requirement(character, requirement_data):
    """
    Check a new requirement type against a character.

    Args:
        character: Character instance to check against
        requirement_data: Dictionary containing requirement parameters

    Returns:
        RequirementCheckResult with success/failure information
    """
    param1 = requirement_data.get("param1")
    param2 = requirement_data.get("param2")

    # Implement checking logic
    character_value = getattr(character, param1, None)

    if character_value is None:
        return RequirementCheckResult(
            passed=False,
            message=f"Character does not have {param1}",
            requirement_type="new_type"
        )

    if param2 is not None and character_value < param2:
        return RequirementCheckResult(
            passed=False,
            message=f"{param1} requirement not met ({character_value} < {param2})",
            requirement_type="new_type"
        )

    return RequirementCheckResult(
        passed=True,
        message=f"{param1} requirement met ({character_value} >= {param2})",
        requirement_type="new_type"
    )
```

#### Adding Visual Builder Components

For new requirement types, add JavaScript components to the drag-drop interface:

```javascript
// In static/admin/js/drag-drop-palette.js

class NewTypeComponent extends RequirementComponent {
    constructor() {
        super();
        this.type = 'new_type';
        this.displayName = 'New Requirement';
        this.description = 'Description of new requirement type';
        this.icon = 'fas fa-new-icon';
    }

    getDefaultData() {
        return {
            param1: '',
            param2: 1
        };
    }

    renderForm(data) {
        return `
            <div class="form-group">
                <label>Parameter 1:</label>
                <input type="text" class="form-control param1-input"
                       value="${data.param1 || ''}" placeholder="Enter value">
            </div>
            <div class="form-group">
                <label>Parameter 2:</label>
                <input type="number" class="form-control param2-input"
                       value="${data.param2 || 1}" min="0">
            </div>
        `;
    }

    validate(data) {
        if (!data.param1 || data.param1.trim() === '') {
            return { valid: false, message: 'Parameter 1 is required' };
        }
        if (data.param2 !== undefined && (data.param2 < 0 || !Number.isInteger(data.param2))) {
            return { valid: false, message: 'Parameter 2 must be a non-negative integer' };
        }
        return { valid: true };
    }

    getDisplayText(data) {
        let text = `${data.param1}`;
        if (data.param2 !== undefined) {
            text += ` (min: ${data.param2})`;
        }
        return text;
    }
}

// Register the component
RequirementPalette.registerComponent(NewTypeComponent);
```

#### Testing Workflow

The prerequisite system has comprehensive test coverage. Follow TDD principles:

```python
# In prerequisites/tests/test_new_feature.py

from django.test import TestCase
from django.core.exceptions import ValidationError

from prerequisites.helpers import new_requirement_type
from prerequisites.checkers import RequirementChecker
from prerequisites.validators import validate_requirements

class NewRequirementTypeTest(TestCase):
    """Test the new requirement type helper function."""

    def test_valid_requirement_creation(self):
        """Test creating a valid new requirement."""
        req = new_requirement_type("test_param", param2=3)

        expected = {
            "new_type": {
                "param1": "test_param",
                "param2": 3
            }
        }
        self.assertEqual(req, expected)

    def test_validation_error_empty_param1(self):
        """Test validation error for empty param1."""
        with self.assertRaises(ValidationError) as cm:
            new_requirement_type("")

        self.assertIn("param1 must be a non-empty string", str(cm.exception))

    def test_generated_requirement_validation(self):
        """Test that generated requirements pass validation."""
        req = new_requirement_type("valid_param", param2=5)

        # Should not raise ValidationError
        validate_requirements(req)

class NewRequirementCheckerTest(TestCase):
    """Test the new requirement checking logic."""

    def setUp(self):
        self.checker = RequirementChecker()
        self.character = create_test_character()  # Helper function

    def test_requirement_passes(self):
        """Test requirement checking when character meets requirements."""
        # Set up character with required attribute
        setattr(self.character, 'test_param', 5)

        req = new_requirement_type("test_param", param2=3)
        result = self.checker.check_requirement(self.character, req)

        self.assertTrue(result.passed)
        self.assertIn("requirement met", result.message.lower())

    def test_requirement_fails(self):
        """Test requirement checking when character doesn't meet requirements."""
        # Set up character with insufficient attribute
        setattr(self.character, 'test_param', 1)

        req = new_requirement_type("test_param", param2=3)
        result = self.checker.check_requirement(self.character, req)

        self.assertFalse(result.passed)
        self.assertIn("not met", result.message.lower())
```

#### JavaScript Testing

For drag-drop interface components, add JavaScript tests:

```javascript
// In prerequisites/tests/test_javascript_components.py

from django.test import TestCase
from django.template.loader import render_to_string
from django.contrib.auth import get_user_model

class NewTypeComponentTest(TestCase):
    """Test the new type JavaScript component."""

    def test_component_rendering(self):
        """Test that the component renders correctly."""
        context = {
            'component_type': 'new_type',
            'initial_data': {'param1': 'test', 'param2': 5}
        }

        # Render template that includes JavaScript component
        html = render_to_string('prerequisites/test_component.html', context)

        self.assertIn('new_type', html)
        self.assertIn('test', html)
        self.assertIn('5', html)

    def test_component_validation(self):
        """Test client-side validation."""
        # This would typically use Selenium or similar for full JavaScript testing
        pass
```

#### Admin Integration

Add admin interface support for new requirement types:

```python
# In prerequisites/admin.py

class PrerequisiteAdmin(admin.ModelAdmin):
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        # Customize form based on requirement type
        if obj and obj.requirements:
            req_type = self.get_requirement_type(obj.requirements)
            if req_type == 'new_type':
                # Add specific help text or field customizations
                form.base_fields['requirements'].help_text += (
                    " This prerequisite uses the new requirement type."
                )

        return form

    def get_requirement_type(self, requirements):
        """Extract the main requirement type from JSON structure."""
        if isinstance(requirements, dict):
            for key in ['new_type', 'trait', 'has', 'any', 'all', 'count_tag']:
                if key in requirements:
                    return key
        return 'unknown'
```

### Performance Considerations

When developing prerequisite features:

#### Query Optimization

```python
# Efficient character checking with minimal database queries
def check_multiple_requirements(character, requirements_list):
    """Check multiple requirements efficiently."""
    # Prefetch related data once
    character = Character.objects.select_related('campaign').prefetch_related(
        'possessions',
        'achievements'
    ).get(id=character.id)

    checker = RequirementChecker()
    results = []

    for requirement in requirements_list:
        result = checker.check_requirement(character, requirement)
        results.append(result)

    return results
```

#### Caching Strategy

```python
from django.core.cache import cache

def get_cached_requirement_result(character_id, requirement_hash):
    """Get cached requirement check result."""
    cache_key = f"prereq_{character_id}_{requirement_hash}"
    return cache.get(cache_key)

def cache_requirement_result(character_id, requirement_hash, result, timeout=300):
    """Cache requirement check result for 5 minutes."""
    cache_key = f"prereq_{character_id}_{requirement_hash}"
    cache.set(cache_key, result, timeout)
```

### Debugging and Troubleshooting

#### Common Issues

1. **Validation Errors**: Always validate JSON structure before saving
2. **Circular Dependencies**: Avoid self-referencing requirements
3. **Performance**: Monitor database queries in complex requirement trees
4. **JavaScript Errors**: Use browser developer tools for drag-drop debugging

#### Debug Utilities

```python
# In prerequisites/utils.py (create if needed)

def debug_requirement_structure(requirement, indent=0):
    """Print requirement structure for debugging."""
    prefix = "  " * indent

    if isinstance(requirement, dict):
        for key, value in requirement.items():
            print(f"{prefix}{key}:")
            if isinstance(value, (list, dict)):
                debug_requirement_structure(value, indent + 1)
            else:
                print(f"{prefix}  {value}")
    elif isinstance(requirement, list):
        for i, item in enumerate(requirement):
            print(f"{prefix}[{i}]:")
            debug_requirement_structure(item, indent + 1)

def validate_requirement_depth(requirement, max_depth=5, current_depth=0):
    """Validate requirement nesting doesn't exceed maximum depth."""
    if current_depth > max_depth:
        raise ValidationError(f"Requirement nesting exceeds maximum depth of {max_depth}")

    if isinstance(requirement, dict):
        for key, value in requirement.items():
            if key in ['any', 'all'] and isinstance(value, list):
                for sub_req in value:
                    validate_requirement_depth(sub_req, max_depth, current_depth + 1)
```

### Integration with Existing Systems

#### Character System Integration

```python
# Example of integrating prerequisites with character advancement
def can_character_advance(character, advancement_type):
    """Check if character can perform specific advancement."""
    prereqs = Prerequisite.objects.filter(
        content_type=ContentType.objects.get_for_model(advancement_type),
        object_id=advancement_type.id
    )

    checker = RequirementChecker()
    for prereq in prereqs:
        result = checker.check_requirement(character, prereq.requirements)
        if not result.passed:
            return False, result.message

    return True, "All prerequisites met"
```

## Source Reference Development

### Overview

The source reference system provides a flexible way to link any model in the application to RPG source books with optional page and chapter references. This system consists of two models: `Book` and `SourceReference`.

### Model Usage Patterns

#### Basic Source Reference Creation

```python
from core.models import Book, SourceReference
from django.contrib.contenttypes.models import ContentType

# Create or get a book
book = Book.objects.get_or_create(
    title="Mage: The Ascension 20th Anniversary Edition",
    abbreviation="M20",
    defaults={
        'system': "Mage: The Ascension",
        'edition': "20th Anniversary",
        'publisher': "Onyx Path Publishing"
    }
)[0]

# Link a character to a source with page reference
character = Character.objects.get(id=42)
source_ref = SourceReference.objects.create(
    book=book,
    content_object=character,
    page_number=65,
    chapter="Character Creation"
)
```

#### Query Patterns for Source References

```python
# Get all source references for an object
def get_object_sources(obj):
    content_type = ContentType.objects.get_for_model(obj)
    return SourceReference.objects.filter(
        content_type=content_type,
        object_id=obj.id
    ).select_related('book').order_by('book__abbreviation', 'page_number')

# Get all objects referencing a specific book
def get_book_references(book):
    return SourceReference.objects.filter(
        book=book
    ).select_related('content_type').order_by('page_number')

# Find references by page range
def get_references_by_page_range(book, start_page, end_page):
    return SourceReference.objects.filter(
        book=book,
        page_number__gte=start_page,
        page_number__lte=end_page
    ).select_related('content_type')

# Search references by chapter
def search_by_chapter(chapter_text):
    return SourceReference.objects.filter(
        chapter__icontains=chapter_text
    ).select_related('book', 'content_type')
```

#### Adding Source References to Models

For models that frequently need source references, consider adding helper methods:

```python
class Character(models.Model):
    name = models.CharField(max_length=100)
    # ... other fields

    def add_source_reference(self, book, page_number=None, chapter=None):
        """Add a source reference to this character."""
        return SourceReference.objects.create(
            book=book,
            content_object=self,
            page_number=page_number,
            chapter=chapter
        )

    def get_source_references(self):
        """Get all source references for this character."""
        content_type = ContentType.objects.get_for_model(self)
        return SourceReference.objects.filter(
            content_type=content_type,
            object_id=self.id
        ).select_related('book').order_by('book__abbreviation', 'page_number')

    @property
    def primary_source(self):
        """Get the primary (first) source reference."""
        sources = self.get_source_references()
        return sources.first() if sources.exists() else None
```

#### Bulk Operations

```python
# Bulk create source references for multiple objects
def bulk_add_sources(objects, book, page_number=None, chapter=None):
    """Add the same source reference to multiple objects."""
    source_refs = []
    for obj in objects:
        content_type = ContentType.objects.get_for_model(obj)
        source_refs.append(SourceReference(
            book=book,
            content_type=content_type,
            object_id=obj.id,
            page_number=page_number,
            chapter=chapter
        ))

    return SourceReference.objects.bulk_create(source_refs)

# Bulk update page numbers
def update_page_numbers(source_refs, new_page):
    """Update page numbers for multiple source references."""
    for ref in source_refs:
        ref.page_number = new_page

    SourceReference.objects.bulk_update(source_refs, ['page_number'])
```

#### Performance Optimization

```python
# Efficient querying with related data
def get_characters_with_sources(campaign):
    """Get characters with their source references efficiently."""
    return Character.objects.filter(
        campaign=campaign
    ).prefetch_related(
        Prefetch(
            'sourcereference_set',
            queryset=SourceReference.objects.select_related('book')
        )
    )

# Cache frequently accessed books
from django.core.cache import cache

def get_book_by_abbreviation(abbreviation):
    """Get book with caching for frequently accessed books."""
    cache_key = f"book_abbrev_{abbreviation}"
    book = cache.get(cache_key)

    if book is None:
        try:
            book = Book.objects.get(abbreviation=abbreviation)
            cache.set(cache_key, book, 3600)  # Cache for 1 hour
        except Book.DoesNotExist:
            return None

    return book
```

#### Template Integration

```python
# Custom template tag for displaying source references
# core/templatetags/source_tags.py
from django import template
from core.models import SourceReference
from django.contrib.contenttypes.models import ContentType

register = template.Library()

@register.inclusion_tag('core/source_references.html')
def show_sources(obj):
    """Display source references for any object."""
    content_type = ContentType.objects.get_for_model(obj)
    sources = SourceReference.objects.filter(
        content_type=content_type,
        object_id=obj.id
    ).select_related('book')

    return {'sources': sources}

@register.simple_tag
def source_citation(source_ref):
    """Format a source reference as a citation."""
    citation = str(source_ref.book)
    if source_ref.chapter:
        citation += f", {source_ref.chapter}"
    if source_ref.page_number:
        citation += f", p. {source_ref.page_number}"
    return citation
```

#### API Integration Patterns

```python
# Serializer for models with source references
class CharacterSerializer(serializers.ModelSerializer):
    source_references = serializers.SerializerMethodField()

    class Meta:
        model = Character
        fields = ['id', 'name', 'description', 'source_references']

    def get_source_references(self, obj):
        sources = obj.get_source_references()
        return [{
            'book': source.book.abbreviation,
            'title': source.book.title,
            'page_number': source.page_number,
            'chapter': source.chapter
        } for source in sources]

# API view for adding source references
class AddSourceReferenceView(APIView):
    def post(self, request):
        book_id = request.data.get('book_id')
        content_type_id = request.data.get('content_type_id')
        object_id = request.data.get('object_id')
        page_number = request.data.get('page_number')
        chapter = request.data.get('chapter')

        try:
            book = Book.objects.get(id=book_id)
            content_type = ContentType.objects.get(id=content_type_id)

            source_ref = SourceReference.objects.create(
                book=book,
                content_type=content_type,
                object_id=object_id,
                page_number=page_number,
                chapter=chapter
            )

            return Response({
                'id': source_ref.id,
                'book': source_ref.book.abbreviation,
                'page_number': source_ref.page_number,
                'chapter': source_ref.chapter
            })

        except (Book.DoesNotExist, ContentType.DoesNotExist) as e:
            return Response({'error': str(e)}, status=400)
```

### Testing Patterns

```python
# Test source reference functionality
class SourceReferenceTestCase(TestCase):
    def setUp(self):
        self.book = Book.objects.create(
            title="Test Book",
            abbreviation="TB",
            system="Test System"
        )
        self.character = Character.objects.create(name="Test Character")

    def test_create_source_reference(self):
        """Test creating a source reference."""
        source_ref = SourceReference.objects.create(
            book=self.book,
            content_object=self.character,
            page_number=100,
            chapter="Test Chapter"
        )

        self.assertEqual(source_ref.content_object, self.character)
        self.assertEqual(source_ref.book, self.book)
        self.assertEqual(source_ref.page_number, 100)

    def test_query_object_sources(self):
        """Test querying sources for an object."""
        SourceReference.objects.create(
            book=self.book,
            content_object=self.character,
            page_number=50
        )

        sources = self.character.get_source_references()
        self.assertEqual(sources.count(), 1)
        self.assertEqual(sources.first().page_number, 50)
```

### Best Practices

1. **Always use select_related()**: When querying SourceReference, always include `select_related('book')` to avoid N+1 queries.

2. **Cache frequently accessed books**: Use Django's caching framework for commonly referenced books.

3. **Validate page numbers**: Ensure page numbers are positive when provided.

4. **Use bulk operations**: For creating multiple source references, use `bulk_create()` for better performance.

5. **Consider data migration**: When adding source references to existing data, create data migrations for bulk operations.

6. **Template integration**: Create template tags for consistent source reference display across the application.

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
            return APIError.create_validation_error_response(e)
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

#### Schema Migrations

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

#### Data Migrations

For migrations that need to populate data, create separate data migration files:

```python
# Good data migration with rollback support
from django.db import migrations

def populate_audit_fields(apps, schema_editor):
    """Populate audit fields for existing records."""
    Model = apps.get_model("app_name", "ModelName")

    for obj in Model.objects.all():
        if obj.created_by_id is None and hasattr(obj, 'owner'):
            obj.created_by_id = obj.owner_id
            obj.save(update_fields=["created_by_id"])

def reverse_audit_fields(apps, schema_editor):
    """Reverse data migration for rollback safety."""
    Model = apps.get_model("app_name", "ModelName")
    Model.objects.update(created_by=None, modified_by=None)

class Migration(migrations.Migration):
    dependencies = [
        ('app_name', '0003_add_audit_fields'),
    ]

    operations = [
        migrations.RunPython(
            populate_audit_fields,
            reverse_audit_fields,
            elidable=True,  # Can be optimized during squashing
        ),
    ]
```

#### Migration Safety Testing

The project includes comprehensive migration safety tests in `core/tests/test_migration_strategy.py`:

```bash
# Run migration safety tests before deploying
python manage.py test core.tests.test_migration_strategy

# Test specific migration scenarios
python manage.py test core.tests.test_migration_strategy.ForwardMigrationDataPreservationTest
python manage.py test core.tests.test_migration_strategy.MigrationRollbackTest

# Performance testing with larger datasets
python manage.py test core.tests.test_migration_strategy.MigrationPerformanceTest
```

**Migration Testing Categories:**
- **Data Preservation**: Ensures existing data survives migration
- **Default Values**: Verifies proper application of default values
- **Data Integrity**: Confirms foreign keys and constraints remain valid
- **Edge Cases**: Tests null values, boundary conditions, and user deletion
- **Performance**: Validates migration performance with realistic data volumes
- **Rollback Safety**: Ensures migrations can be safely reversed

#### Migration Rollback Procedures

If a migration needs to be rolled back, use the provided rollback script:

```bash
# Interactive rollback with confirmation
./scripts/rollback_mixin_migrations.sh

# Manual rollback commands
python manage.py migrate characters 0002  # Rollback to before mixin fields
python manage.py migrate items 0002
python manage.py migrate locations 0002
```

**Rollback Safety Features:**
- Interactive confirmation to prevent accidental rollbacks
- Step-by-step rollback of data migrations before schema migrations
- Verification of migration state before and after rollback
- Automatic environment detection (conda/virtualenv)
- Clear status reporting throughout the process

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

### Polymorphic Model Development

#### Polymorphic Inheritance Pattern

The GMA system uses django-polymorphic for flexible inheritance hierarchies, enabling type-specific behavior while maintaining unified base functionality.

**Current Polymorphic Models:**
- **Character Model**: Character → WoDCharacter → MageCharacter
- **Item Model**: Item → [Future subclasses: WeaponItem, ArmorItem, ConsumableItem] *(Issue #182)*
- **Location Model**: Location → [Future subclasses for location types]

#### Item Model Polymorphic Conversion (Issue #182)

The Item model was successfully converted from Django's standard Model to PolymorphicModel, enabling future game system-specific item types.

**Implementation Pattern:**

```python
# items/models/__init__.py
from polymorphic.models import PolymorphicModel
from polymorphic.managers import PolymorphicManager
from polymorphic.query import PolymorphicQuerySet

class ItemQuerySet(PolymorphicQuerySet):
    """Custom QuerySet extending PolymorphicQuerySet."""
    def active(self):
        return self.filter(is_deleted=False)

    def for_campaign(self, campaign):
        return self.filter(campaign=campaign)

class ItemManager(PolymorphicManager):
    """Manager excluding soft-deleted items by default."""
    def get_queryset(self):
        return ItemQuerySet(self.model, using=self._db).filter(is_deleted=False)

class Item(TimestampedMixin, NamedModelMixin, DescribedModelMixin, AuditableMixin, PolymorphicModel):
    """Base item class with polymorphic support."""
    campaign = ForeignKey(Campaign, on_delete=CASCADE)
    quantity = PositiveIntegerField(default=1)
    # ... other base fields

    objects = ItemManager()
    all_objects = AllItemManager()  # Includes soft-deleted
```

**Key Migration Steps:**

```python
# Migration 0007: Add polymorphic_ctype field
operations = [
    migrations.AddField(
        model_name='item',
        name='polymorphic_ctype',
        field=models.ForeignKey(
            default=None,
            on_delete=models.CASCADE,
            related_name='polymorphic_items',
            to='contenttypes.contenttype'
        ),
    ),
]

# Migration 0008: Populate polymorphic_ctype data
def populate_polymorphic_ctype(apps, schema_editor):
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Item = apps.get_model('items', 'Item')

    item_content_type = ContentType.objects.get_for_model(Item)
    Item.objects.filter(polymorphic_ctype_id__isnull=True).update(
        polymorphic_ctype_id=item_content_type.id
    )
```

#### Creating Item Subclasses

**Future Development Pattern:**

```python
# items/models/weapon.py
class WeaponItem(Item):
    """Weapon-specific item with combat properties."""
    damage_dice = CharField(max_length=20)  # e.g., "2d6+1"
    weapon_type = CharField(max_length=50, choices=WEAPON_TYPE_CHOICES)
    range_increment = PositiveIntegerField(null=True, blank=True)
    is_magical = BooleanField(default=False)

    class Meta:
        verbose_name = "Weapon"
        verbose_name_plural = "Weapons"

# items/models/armor.py
class ArmorItem(Item):
    """Armor-specific item with protection properties."""
    armor_class = PositiveIntegerField()
    armor_type = CharField(max_length=50, choices=ARMOR_TYPE_CHOICES)
    max_dex_bonus = PositiveIntegerField(null=True, blank=True)
    armor_check_penalty = IntegerField(default=0)
```

**Polymorphic Query Patterns:**

```python
# Get all items (returns appropriate subclass instances)
all_items = Item.objects.for_campaign(campaign)

# Type-specific filtering
weapons = Item.objects.instance_of(WeaponItem)
magical_weapons = WeaponItem.objects.filter(is_magical=True)

# Mixed queries with type safety
items_with_high_value = Item.objects.filter(
    Q(weaponitem__is_magical=True) |
    Q(armoritem__armor_class__gte=5)
)
```

#### Testing Polymorphic Models

**Required Test Coverage:**

```python
class PolymorphicModelTests(TestCase):
    def test_inheritance_chain(self):
        """Test that polymorphic inheritance works correctly."""
        item = Item.objects.create(name="Basic Item", campaign=campaign)
        weapon = WeaponItem.objects.create(
            name="Magic Sword",
            campaign=campaign,
            damage_dice="1d8+1",
            weapon_type="sword"
        )

        # Verify polymorphic queries return correct types
        all_items = Item.objects.all()
        self.assertIsInstance(all_items[0], Item)
        self.assertIsInstance(all_items[1], WeaponItem)

    def test_manager_polymorphic_support(self):
        """Test managers work with polymorphic inheritance."""
        # Create mixed item types
        Item.objects.create(name="Generic", campaign=campaign)
        WeaponItem.objects.create(name="Sword", campaign=campaign, damage_dice="1d8")

        # Test polymorphic queries with managers
        active_items = Item.objects.active()
        self.assertEqual(active_items.count(), 2)

        # Verify correct types returned
        for item in active_items:
            self.assertTrue(hasattr(item, 'polymorphic_ctype'))
```

**Test Categories:**
1. **Inheritance Validation**: Verify polymorphic relationships work correctly
2. **Manager Compatibility**: Ensure custom managers work with inheritance
3. **Query Behavior**: Test that queries return appropriate types
4. **Test Polymorphic Support**: Ensure managers work with inheritance chains
5. **Migration Safety**: Test polymorphic field addition and data population

#### Development Guidelines

**When to Use Polymorphic Models:**

✅ **Use when:**
- Need type-specific behavior with shared base functionality
- Future extensibility requires multiple related model types
- Want unified API/admin interface across types
- Complex inheritance hierarchies benefit from single table storage

❌ **Don't use when:**
- Simple models don't need inheritance
- Performance is critical (polymorphic queries have overhead)
- Types are fundamentally different (prefer separate models)

**Performance Considerations:**
- Polymorphic queries include JOIN with ContentType table
- Use `select_related('polymorphic_ctype')` for optimization
- Consider caching ContentType lookups for frequently accessed models
- Index polymorphic_ctype_id for efficient type filtering

**Migration Best Practices:**
- Add polymorphic_ctype field with migration
- Create data migration to populate existing records
- Test migration with realistic data volumes
- Provide rollback procedures for safety

#### Item Character Ownership Patterns (Issue #183)

The Item model supports single character ownership with transfer functionality and timestamp tracking. This section covers development patterns for working with the ownership system.

**Ownership Architecture:**

```python
# Single character ownership (converted from many-to-many)
class Item(PolymorphicModel):
    owner = ForeignKey("characters.Character", on_delete=SET_NULL, null=True, blank=True, related_name="possessions")
    last_transferred_at = DateTimeField(null=True, blank=True)

    def transfer_to(self, new_owner: Optional["Character"]) -> "Item":
        """Transfer item to new owner with timestamp tracking."""
        self.owner = new_owner
        self.last_transferred_at = timezone.now()
        self.save(update_fields=["owner", "last_transferred_at"])
        return self  # Method chaining support

# Character reverse relationship
class Character(PolymorphicModel):
    # Automatic reverse relationship via related_name="possessions"
    # character.possessions.all() returns all items owned by character
```

**Common Usage Patterns:**

```python
# Direct ownership assignment
item.owner = character
item.save()

# Transfer with timestamp tracking (preferred method)
item.transfer_to(character)  # Updates owner and last_transferred_at
item.transfer_to(None)       # Makes item unowned

# Query patterns
character_items = Item.objects.owned_by_character(character)
unowned_items = Item.objects.filter(owner=None)
character_possessions = character.possessions.all()  # New relationship name

# Bulk operations
character.possessions.update(owner=new_character)  # Transfer all possessions
Item.objects.filter(owner=old_character).update(owner=None)  # Clear ownership
```

**Testing Patterns:**

```python
class TestItemOwnership(TestCase):
    def setUp(self):
        self.campaign = Campaign.objects.create(name="Test", owner=self.user)
        self.character = Character.objects.create(name="Hero", campaign=self.campaign)
        self.item = Item.objects.create(name="Sword", campaign=self.campaign)

    def test_item_transfer_functionality(self):
        """Test transfer_to method with timestamp tracking."""
        # Initial state
        self.assertIsNone(self.item.owner)
        self.assertIsNone(self.item.last_transferred_at)

        # Transfer to character
        result = self.item.transfer_to(self.character)

        # Verify transfer
        self.assertEqual(self.item.owner, self.character)
        self.assertIsNotNone(self.item.last_transferred_at)
        self.assertEqual(result, self.item)  # Method chaining

    def test_character_possessions_relationship(self):
        """Test character.possessions reverse relationship."""
        self.item.transfer_to(self.character)

        # Test relationship
        possessions = self.character.possessions.all()
        self.assertIn(self.item, possessions)
        self.assertEqual(self.character.possessions.count(), 1)

    def test_ownership_queries(self):
        """Test manager methods for ownership filtering."""
        self.item.transfer_to(self.character)

        # Test filtering methods
        owned_items = Item.objects.owned_by_character(self.character)
        self.assertIn(self.item, owned_items)

        unowned_items = Item.objects.filter(owner=None)
        self.assertNotIn(self.item, unowned_items)
```

**Migration Strategy (Issue #183):**

The ownership conversion used a 3-step migration process:

1. **Add new fields**: Add `owner` ForeignKey and `last_transferred_at` fields
2. **Migrate data**: Convert many-to-many ownership to single ownership
3. **Remove old field**: Remove the `owners` many-to-many field

```python
# Migration data conversion logic
def migrate_ownership_data(apps, schema_editor):
    Item = apps.get_model('items', 'Item')

    for item in Item.objects.prefetch_related('owners').all():
        owners = list(item.owners.all())
        if owners:
            # Use first owner for single ownership
            item.owner = owners[0]
            item.last_transferred_at = timezone.now()
            item.save(update_fields=['owner', 'last_transferred_at'])
```

**Best Practices:**

1. **Use transfer_to() method**: Provides timestamp tracking and method chaining
2. **Handle unowned items**: Items can be unowned (owner=None) - design for this case
3. **Character deletion safety**: Uses SET_NULL so items become unowned when character deleted
4. **Test ownership edge cases**: Unowned items, character deletion, bulk transfers
5. **Use possessions relationship**: More semantic than generic "owned_items"

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
├── test_websocket.py      # WebSocket consumer tests
├── test_chat.py          # Real-time chat functionality
├── test_rate_limiting.py  # Rate limiting system tests
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

### Testing Model Mixins

When testing models that use mixins, focus on the essential functionality and integration:

```python
# core/tests/test_mixins.py
class TimestampedTestModel(TimestampedMixin):
    """Test model for mixin functionality."""
    title = models.CharField(max_length=100)

    class Meta:
        app_label = "core"

class TestTimestampedMixin(TestCase):
    """Test TimestampedMixin functionality."""

    def test_has_timestamp_fields(self):
        """Test that mixin provides required fields."""
        fields = {f.name: f for f in TimestampedTestModel._meta.get_fields()}

        self.assertIn("created_at", fields)
        self.assertIn("updated_at", fields)
        self.assertIsInstance(fields["created_at"], models.DateTimeField)
        self.assertIsInstance(fields["updated_at"], models.DateTimeField)

    def test_timestamps_set_on_create(self):
        """Test automatic timestamp setting on creation."""
        before_create = timezone.now()
        obj = TimestampedTestModel.objects.create(title="Test")
        after_create = timezone.now()

        self.assertIsNotNone(obj.created_at)
        self.assertIsNotNone(obj.updated_at)
        self.assertGreaterEqual(obj.created_at, before_create)
        self.assertLessEqual(obj.created_at, after_create)

    def test_updated_at_changes_on_save(self):
        """Test that updated_at changes when object is saved."""
        obj = TimestampedTestModel.objects.create(title="Test")
        original_updated_at = obj.updated_at

        time.sleep(0.1)  # Ensure time difference
        obj.title = "Updated"
        obj.save()
        obj.refresh_from_db()

        self.assertGreater(obj.updated_at, original_updated_at)
```

**Mixin Testing Philosophy:**

- **Focus on Essential Behavior**: Test the core functionality the mixin provides
- **Test Integration**: Verify mixin works correctly with actual models
- **Keep Tests Simple**: Avoid over-testing implementation details
- **Test Edge Cases**: But only the ones that matter in practice
- **Test Performance Features**: Verify indexes exist and help text is present
- **Test Enhanced Functionality**: For AuditableMixin, test automatic user tracking

**When Testing Models with Mixins:**

```python
class TestGameSessionModel(TestCase):
    """Test GameSession model (includes TimestampedMixin)."""

    def setUp(self):
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=User.objects.create_user("owner", "owner@example.com")
        )

    def test_session_creation_includes_timestamps(self):
        """Test that session creation includes automatic timestamps."""
        session = GameSession.objects.create(
            name="Session 1",
            campaign=self.campaign
        )

        # Test mixin functionality
        self.assertIsNotNone(session.created_at)
        self.assertIsNotNone(session.updated_at)

        # Test model-specific functionality
        self.assertEqual(session.name, "Session 1")
        self.assertEqual(session.campaign, self.campaign)

    def test_session_update_changes_timestamp(self):
        """Test that session updates change the updated_at timestamp."""
        session = GameSession.objects.create(
            name="Session 1",
            campaign=self.campaign
        )
        original_updated = session.updated_at

        time.sleep(0.1)
        session.status = 'COMPLETED'
        session.save()
        session.refresh_from_db()

        self.assertGreater(session.updated_at, original_updated)
        self.assertEqual(session.status, 'COMPLETED')

    def test_session_with_user_tracking(self):
        """Test that session with AuditableMixin tracks users automatically."""
        user = User.objects.create_user("creator", "creator@example.com")

        # Create session with user tracking
        session = GameSession(
            name="Session with Tracking",
            campaign=self.campaign
        )
        session.save(user=user)

        # Verify automatic user tracking
        self.assertEqual(session.created_by, user)
        self.assertEqual(session.modified_by, user)

        # Update with different user
        modifier = User.objects.create_user("modifier", "modifier@example.com")
        session.status = 'COMPLETED'
        session.save(user=modifier)

        # Verify created_by unchanged, modified_by updated
        session.refresh_from_db()
        self.assertEqual(session.created_by, user)  # Unchanged
        self.assertEqual(session.modified_by, modifier)  # Updated
```

### Character Status Transition Testing Patterns (Issue #180)

The Character model now includes a comprehensive status workflow system using django-fsm-2. Test patterns for character status transitions:

#### Status Transition Testing

```python
class CharacterStatusTransitionTest(TestCase):
    """Test Character status transition functionality."""

    def test_submit_for_approval_workflow(self):
        """Test character submission workflow."""
        character = Character.objects.create(
            name="Test Character",
            campaign=self.campaign,
            player_owner=self.player,
            game_system="Test System"
        )

        # Character starts in DRAFT
        self.assertEqual(character.status, "DRAFT")

        # Player can submit for approval
        character.submit_for_approval(user=self.player)
        character.save(audit_user=self.player)
        self.assertEqual(character.status, "SUBMITTED")

        # GM can approve
        character.approve(user=self.gm)
        character.save(audit_user=self.gm)
        self.assertEqual(character.status, "APPROVED")

    def test_permission_based_transitions(self):
        """Test that transitions respect permission rules."""
        character = self._create_submitted_character()

        # Only GMs/owners can approve
        with self.assertRaises(PermissionError):
            character.approve(user=self.player)

        # GMs can approve
        character.approve(user=self.gm)
        character.save(audit_user=self.gm)
        self.assertEqual(character.status, "APPROVED")

    def test_audit_trail_for_status_changes(self):
        """Test that status changes create audit entries."""
        character = self._create_character()

        initial_count = character.audit_entries.count()

        character.submit_for_approval(user=self.player)
        character.save(audit_user=self.player)

        # Should create audit entry for status change
        new_count = character.audit_entries.count()
        self.assertEqual(new_count, initial_count + 1)

        # Verify audit entry content
        audit_entry = character.audit_entries.latest('timestamp')
        self.assertEqual(audit_entry.action, 'UPDATE')
        self.assertIn('status', audit_entry.field_changes)
        self.assertEqual(audit_entry.field_changes['status']['old'], 'DRAFT')
        self.assertEqual(audit_entry.field_changes['status']['new'], 'SUBMITTED')
```

### Character Manager Testing Patterns (Issue #175)

The Character model includes multiple manager instances for efficient filtering. Test these new manager capabilities:

#### Manager Instance Testing

```python
class CharacterManagerTest(TestCase):
    """Test Character manager instances and functionality."""

    def test_manager_instances_exist(self):
        """Test that all manager instances are available."""
        self.assertTrue(hasattr(Character, 'objects'))      # Primary manager
        self.assertTrue(hasattr(Character, 'all_objects'))  # Includes soft-deleted
        self.assertTrue(hasattr(Character, 'npcs'))         # NPCs only
        self.assertTrue(hasattr(Character, 'pcs'))          # PCs only

    def test_npc_manager_filtering(self):
        """Test NPCManager returns only NPCs, excluding soft-deleted."""
        # Create test data
        pc = Character.objects.create(name="PC", campaign=self.campaign,
                                    player_owner=self.player, npc=False)
        npc = Character.objects.create(name="NPC", campaign=self.campaign,
                                     player_owner=self.gm, npc=True)
        deleted_npc = Character.objects.create(name="Deleted NPC", campaign=self.campaign,
                                             player_owner=self.gm, npc=True)
        deleted_npc.soft_delete(self.gm)

        # Test NPCManager
        npcs = Character.npcs.all()
        self.assertIn(npc, npcs)
        self.assertNotIn(pc, npcs)
        self.assertNotIn(deleted_npc, npcs)
        self.assertEqual(npcs.count(), 1)

    def test_pc_manager_filtering(self):
        """Test PCManager returns only PCs, excluding soft-deleted."""
        # Similar test structure for PCs
        pcs = Character.pcs.all()
        # Verify only active PCs are returned

    def test_manager_polymorphic_support(self):
        """Test managers work with polymorphic inheritance."""
        mage_pc = MageCharacter.objects.create(
            name="Mage PC", campaign=self.campaign, player_owner=self.player,
            npc=False, willpower=3, arete=1
        )
        mage_npc = MageCharacter.objects.create(
            name="Mage NPC", campaign=self.campaign, player_owner=self.gm,
            npc=True, willpower=5, arete=3
        )

        # Test polymorphic queries with managers
        mage_pcs = Character.pcs.instance_of(MageCharacter)
        mage_npcs = Character.npcs.instance_of(MageCharacter)

        self.assertIn(mage_pc, mage_pcs)
        self.assertNotIn(mage_npc, mage_pcs)
        self.assertIn(mage_npc, mage_npcs)
        self.assertNotIn(mage_pc, mage_npcs)

    def test_manager_chaining_and_filtering(self):
        """Test manager method chaining with additional filters."""
        # Test combining manager filters with additional criteria
        campaign_npcs = Character.npcs.filter(campaign=self.campaign)
        user_pcs = Character.pcs.filter(player_owner=self.player)

        # Verify chaining works correctly
        self.assertTrue(hasattr(campaign_npcs, 'count'))
        self.assertTrue(hasattr(user_pcs, 'order_by'))

    def test_backward_compatibility(self):
        """Test existing manager methods still work."""
        # Verify existing methods on objects manager still work
        legacy_npcs = Character.objects.npcs()
        legacy_pcs = Character.objects.player_characters()

        # Compare with new manager instances
        new_npcs = Character.npcs.all()
        new_pcs = Character.pcs.all()

        self.assertEqual(list(legacy_npcs), list(new_npcs))
        self.assertEqual(list(legacy_pcs), list(new_pcs))
```

**Testing Best Practices for Character Managers:**

1. **Test Manager Existence**: Verify all manager instances are accessible
2. **Test Filtering Logic**: Ensure managers return correct character types
3. **Test Soft Delete Exclusion**: Verify soft-deleted characters are excluded
4. **Test Polymorphic Support**: Ensure managers work with inheritance chains
5. **Test Method Chaining**: Verify additional filtering works correctly
6. **Test Performance**: Verify database queries are optimized
7. **Test Backward Compatibility**: Ensure existing code still works
8. **Test Edge Cases**: Empty querysets, mixed character types, etc.

### Character NPC Field Testing Patterns

The NPC field implementation (issue #174) introduced unified PC/NPC architecture. Here are essential testing patterns for Character functionality:

#### Model Field Testing

```python
class CharacterNPCFieldTest(TestCase):
    """Test Character model NPC field functionality."""

    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.gm = User.objects.create_user(
            username="gm", email="gm@test.com", password="testpass123"
        )
        self.player = User.objects.create_user(
            username="player", email="player@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            game_system="Mage: The Ascension",
        )

        # Create memberships
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm, role="GM"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )

    def test_character_npc_field_defaults_to_false(self):
        """Test that NPC field defaults to False (PC)."""
        character = Character.objects.create(
            name="Test Character",
            campaign=self.campaign,
            player_owner=self.player,
            game_system="Mage: The Ascension",
        )

        self.assertFalse(character.npc)

        # Verify persistence
        character.refresh_from_db()
        self.assertFalse(character.npc)

    def test_character_npc_field_explicit_true(self):
        """Test creating NPC with explicit npc=True."""
        npc = Character.objects.create(
            name="Test NPC",
            campaign=self.campaign,
            player_owner=self.gm,
            game_system="Mage: The Ascension",
            npc=True,
        )

        self.assertTrue(npc.npc)

        # Verify persistence
        npc.refresh_from_db()
        self.assertTrue(npc.npc)

    def test_npc_field_toggle(self):
        """Test toggling NPC status."""
        character = Character.objects.create(
            name="Toggle Character",
            campaign=self.campaign,
            player_owner=self.player,
            game_system="Mage: The Ascension",
            npc=False,
        )

        # Convert PC to NPC
        character.npc = True
        character.save()
        character.refresh_from_db()
        self.assertTrue(character.npc)

        # Convert NPC back to PC
        character.npc = False
        character.save()
        character.refresh_from_db()
        self.assertFalse(character.npc)

    def test_npc_field_database_index(self):
        """Test that NPC field has database index for performance."""
        from django.db import connection

        table_name = Character._meta.db_table

        with connection.cursor() as cursor:
            if connection.vendor == "postgresql":
                cursor.execute(
                    """
                    SELECT indexname, indexdef
                    FROM pg_indexes
                    WHERE tablename = %s AND indexdef LIKE '%%npc%%'
                    """,
                    [table_name],
                )
                indexes = cursor.fetchall()
                npc_indexes = [idx for idx in indexes if "npc" in idx[1].lower()]

                self.assertGreater(
                    len(npc_indexes),
                    0,
                    f"No database index found for npc field on {table_name}",
                )
```

#### Query Pattern Testing

```python
def test_npc_filtering_queries(self):
    """Test efficient filtering by NPC status."""
    # Create mixed character types
    pc1 = Character.objects.create(
        name="Player Character 1",
        campaign=self.campaign,
        player_owner=self.player,
        game_system="Mage: The Ascension",
        npc=False,
    )

    npc1 = Character.objects.create(
        name="Non-Player Character 1",
        campaign=self.campaign,
        player_owner=self.gm,
        game_system="Mage: The Ascension",
        npc=True,
    )

    # Test filtering queries
    npcs = Character.objects.filter(campaign=self.campaign, npc=True)
    pcs = Character.objects.filter(campaign=self.campaign, npc=False)

    self.assertEqual(npcs.count(), 1)
    self.assertIn(npc1, npcs)
    self.assertNotIn(pc1, npcs)

    self.assertEqual(pcs.count(), 1)
    self.assertIn(pc1, pcs)
    self.assertNotIn(npc1, pcs)

def test_polymorphic_inheritance_with_npc_field(self):
    """Test NPC field works with polymorphic inheritance."""
    from characters.models import MageCharacter

    mage_pc = MageCharacter.objects.create(
        name="Mage PC",
        campaign=self.campaign,
        player_owner=self.player,
        game_system="Mage: The Ascension",
        npc=False,
        willpower=4,
        arete=2,
    )

    mage_npc = MageCharacter.objects.create(
        name="Mage NPC",
        campaign=self.campaign,
        player_owner=self.gm,
        game_system="Mage: The Ascension",
        npc=True,
        willpower=6,
        arete=4,
    )

    # Test polymorphic queries with NPC filtering
    all_npcs = Character.objects.filter(npc=True)
    mage_npcs = MageCharacter.objects.filter(npc=True)

    self.assertIn(mage_npc, all_npcs)
    self.assertIn(mage_npc, mage_npcs)
    self.assertNotIn(mage_pc, all_npcs)
    self.assertNotIn(mage_pc, mage_npcs)
```

#### Audit Trail Testing

```python
def test_npc_field_audit_trail(self):
    """Test that NPC field changes are tracked in audit trail."""
    character = Character.objects.create(
        name="Audit Test Character",
        campaign=self.campaign,
        player_owner=self.player,
        game_system="Mage: The Ascension",
        npc=False,
    )

    # Change NPC status with audit user
    character.npc = True
    character.save(audit_user=self.gm)

    # Verify audit entry exists
    audit_entries = character.audit_entries.all()
    self.assertGreater(audit_entries.count(), 0)

    # Look for NPC field change in audit trail
    npc_change_entries = audit_entries.filter(
        field_changes__has_key='npc'
    )

    if npc_change_entries.exists():
        audit_entry = npc_change_entries.first()
        field_changes = audit_entry.field_changes
        self.assertIn('npc', field_changes)
        self.assertEqual(field_changes['npc']['old'], False)
        self.assertEqual(field_changes['npc']['new'], True)
```

#### API Testing with NPC Field

```python
class CharacterAPITest(APITestCase):
    """Test Character API with NPC field support."""

    def test_create_pc_via_api(self):
        """Test creating PC via API."""
        self.client.force_authenticate(self.player)

        data = {
            "name": "API Test PC",
            "description": "Created via API",
            "npc": False,
            "campaign": self.campaign.id,
            "character_type": "Character",
        }

        response = self.client.post("/api/characters/", data)
        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.data["npc"])
        self.assertEqual(response.data["name"], "API Test PC")

    def test_create_npc_requires_gm_permission(self):
        """Test that creating NPCs requires GM/Owner permissions."""
        self.client.force_authenticate(self.player)

        data = {
            "name": "API Test NPC",
            "description": "NPC created via API",
            "npc": True,
            "campaign": self.campaign.id,
            "character_type": "Character",
        }

        # Players shouldn't be able to create NPCs
        response = self.client.post("/api/characters/", data)
        self.assertEqual(response.status_code, 403)

        # GMs should be able to create NPCs
        self.client.force_authenticate(self.gm)
        response = self.client.post("/api/characters/", data)
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["npc"])

    def test_npc_filtering_in_api(self):
        """Test filtering characters by NPC status via API."""
        # Create test characters
        Character.objects.create(
            name="Test PC", campaign=self.campaign,
            player_owner=self.player, game_system="Test", npc=False
        )
        Character.objects.create(
            name="Test NPC", campaign=self.campaign,
            player_owner=self.gm, game_system="Test", npc=True
        )

        self.client.force_authenticate(self.player)

        # Test filtering for NPCs only
        response = self.client.get(f"/api/characters/?campaign_id={self.campaign.id}&npc=true")
        self.assertEqual(response.status_code, 200)
        results = response.data["results"]
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0]["npc"])

        # Test filtering for PCs only
        response = self.client.get(f"/api/characters/?campaign_id={self.campaign.id}&npc=false")
        self.assertEqual(response.status_code, 200)
        results = response.data["results"]
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0]["npc"])
```

**Testing Best Practices for NPC Field:**

1. **Test Default Behavior**: Verify new characters default to PC (npc=False)
2. **Test Database Performance**: Verify index exists and queries are efficient
3. **Test Polymorphic Integration**: Ensure NPC field works with inheritance
4. **Test Audit Trail**: Verify NPC status changes are tracked
5. **Test API Integration**: Verify serializers include NPC field
6. **Test Permission Logic**: Verify NPC creation restrictions
7. **Test Query Patterns**: Verify filtering by NPC status works correctly
8. **Test Migration Safety**: Verify existing data handles new field correctly

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

### Real-Time Chat System Testing

The real-time chat system requires comprehensive testing across multiple components: WebSocket consumers, message models, rate limiting, and API endpoints.

#### WebSocket Consumer Testing

```python
# scenes/tests/test_scene_chat_consumer.py
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import TestCase

class SceneChatConsumerTest(TestCase):
    """Test WebSocket chat consumer functionality."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass'
        )
        self.campaign = Campaign.objects.create(
            name='Test Campaign',
            owner=self.user
        )
        self.scene = Scene.objects.create(
            name='Test Scene',
            campaign=self.campaign,
            created_by=self.user
        )

    async def test_websocket_connection_requires_auth(self):
        """Test that WebSocket connection requires authentication."""
        communicator = WebsocketCommunicator(
            SceneChatConsumer.as_asgi(),
            f"ws/scenes/{self.scene.id}/chat/"
        )

        connected, subprotocol = await communicator.connect()
        self.assertFalse(connected)  # Should reject unauthenticated users

    async def test_chat_message_sending(self):
        """Test sending chat messages through WebSocket."""
        # Authenticate user for WebSocket
        communicator = WebsocketCommunicator(
            SceneChatConsumer.as_asgi(),
            f"ws/scenes/{self.scene.id}/chat/",
            headers=[(b"cookie", f"sessionid={self.client.session.session_key}".encode())]
        )

        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)

        # Create character for IC message
        character = Character.objects.create(
            name='Test Character',
            campaign=self.campaign,
            player_owner=self.user
        )

        # Send message
        message_data = {
            "type": "chat_message",
            "message": {
                "content": "Hello, world!",
                "message_type": "PUBLIC",
                "character": character.id
            }
        }

        await communicator.send_json_to(message_data)

        # Receive broadcasted message
        response = await communicator.receive_json_from()

        self.assertEqual(response["type"], "chat.message")
        self.assertEqual(response["content"], "Hello, world!")
        self.assertEqual(response["message_type"], "PUBLIC")
        self.assertEqual(response["character"]["id"], character.id)

        await communicator.disconnect()

    async def test_rate_limiting(self):
        """Test rate limiting prevents message spam."""
        communicator = WebsocketCommunicator(
            SceneChatConsumer.as_asgi(),
            f"ws/scenes/{self.scene.id}/chat/"
        )

        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)

        # Send messages rapidly to trigger rate limit
        for i in range(15):  # Exceed 10/minute limit
            await communicator.send_json_to({
                "type": "chat_message",
                "message": {
                    "content": f"Message {i}",
                    "message_type": "OOC"
                }
            })

        # Should receive rate limit error
        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "error")
        self.assertIn("Rate limit exceeded", response["error"])

        await communicator.disconnect()
```

#### Message Model Testing

```python
# scenes/tests/test_message_model.py
class MessageModelTest(TestCase):
    """Test Message model validation and business logic."""

    def test_public_message_requires_character(self):
        """Test that PUBLIC messages require character attribution."""
        with self.assertRaises(ValidationError) as context:
            message = Message(
                scene=self.scene,
                sender=self.user,
                content="Test message",
                message_type="PUBLIC"
                # No character - should fail validation
            )
            message.full_clean()

        self.assertIn("character", str(context.exception))

    def test_ooc_message_cannot_have_character(self):
        """Test that OOC messages cannot have character attribution."""
        character = Character.objects.create(
            name='Test Character',
            campaign=self.campaign,
            player_owner=self.user
        )

        with self.assertRaises(ValidationError) as context:
            message = Message(
                scene=self.scene,
                sender=self.user,
                character=character,  # Should not be allowed for OOC
                content="Test OOC message",
                message_type="OOC"
            )
            message.full_clean()

        self.assertIn("OOC messages cannot have character attribution", str(context.exception))

    def test_system_message_requires_gm_permissions(self):
        """Test that only GMs can send system messages."""
        player = get_user_model().objects.create_user(
            username='player',
            email='player@example.com'
        )

        # Add player to campaign
        Membership.objects.create(
            campaign=self.campaign,
            user=player,
            role='PLAYER'
        )

        with self.assertRaises(ValidationError) as context:
            message = Message(
                scene=self.scene,
                sender=player,  # Player cannot send system messages
                content="System announcement",
                message_type="SYSTEM"
            )
            message.full_clean()

        self.assertIn("Only GMs can send system messages", str(context.exception))
```

#### Rate Limiting Testing

```python
# core/tests/test_rate_limiting.py
from core.rate_limiting import ChatRateLimiter

class ChatRateLimiterTest(TestCase):
    """Test chat rate limiting functionality."""

    def setUp(self):
        self.limiter = ChatRateLimiter()
        self.user = get_user_model().objects.create_user(
            username='testuser',
            email='test@example.com'
        )

    def test_default_user_rate_limit(self):
        """Test default user rate limiting (10 messages/minute)."""
        # Should allow 10 messages
        for i in range(10):
            allowed, info = self.limiter.check_message_rate_limit(self.user, "PUBLIC")
            self.assertTrue(allowed)
            self.assertEqual(info["remaining"], 9 - i)

        # 11th message should be blocked
        allowed, info = self.limiter.check_message_rate_limit(self.user, "PUBLIC")
        self.assertFalse(allowed)
        self.assertEqual(info["remaining"], 0)
        self.assertGreater(info["retry_after"], 0)

    def test_staff_user_higher_limits(self):
        """Test that staff users have higher rate limits (30/minute)."""
        self.user.is_staff = True
        self.user.save()

        # Should allow 30 messages for staff
        for i in range(30):
            allowed, info = self.limiter.check_message_rate_limit(self.user, "PUBLIC")
            self.assertTrue(allowed, f"Message {i+1} should be allowed")

        # 31st message should be blocked
        allowed, info = self.limiter.check_message_rate_limit(self.user, "PUBLIC")
        self.assertFalse(allowed)

    def test_system_messages_bypass_limits(self):
        """Test that system messages have very high limits."""
        # System messages should have 100/minute limit
        for i in range(100):
            allowed, info = self.limiter.check_message_rate_limit(self.user, "SYSTEM")
            self.assertTrue(allowed, f"System message {i+1} should be allowed")
```

#### Message History API Testing

```python
# api/tests/test_message_history_api.py
class MessageHistoryAPITest(APITestCase):
    """Test message history API endpoint."""

    def test_message_filtering_by_type(self):
        """Test filtering messages by message type."""
        # Create messages of different types
        Message.objects.create(
            scene=self.scene,
            sender=self.user,
            character=self.character,
            content="IC message",
            message_type="PUBLIC"
        )

        Message.objects.create(
            scene=self.scene,
            sender=self.user,
            content="OOC message",
            message_type="OOC"
        )

        # Filter for only PUBLIC messages
        response = self.client.get(
            f'/api/scenes/{self.scene.id}/messages/?message_type=PUBLIC'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['message_type'], 'PUBLIC')

    def test_permission_based_message_visibility(self):
        """Test that users only see messages they have permission for."""
        player = get_user_model().objects.create_user(
            username='player',
            email='player@example.com'
        )

        # Create private message not intended for player
        private_message = Message.objects.create(
            scene=self.scene,
            sender=self.user,
            content="Private message",
            message_type="PRIVATE"
        )
        # Don't add player as recipient

        # Player should not see private message
        self.client.force_authenticate(user=player)
        response = self.client.get(f'/api/scenes/{self.scene.id}/messages/')

        self.assertEqual(response.status_code, 200)
        message_ids = [msg['id'] for msg in response.data['results']]
        self.assertNotIn(private_message.id, message_ids)

    def test_date_range_filtering(self):
        """Test filtering messages by date range."""
        from datetime import datetime, timedelta

        # Create message in the past
        past_message = Message.objects.create(
            scene=self.scene,
            sender=self.user,
            content="Old message",
            message_type="OOC"
        )
        past_message.created_at = datetime.now() - timedelta(hours=2)
        past_message.save()

        # Create recent message
        recent_message = Message.objects.create(
            scene=self.scene,
            sender=self.user,
            content="Recent message",
            message_type="OOC"
        )

        # Filter for messages since 1 hour ago
        since_time = (datetime.now() - timedelta(hours=1)).isoformat()
        response = self.client.get(
            f'/api/scenes/{self.scene.id}/messages/?since={since_time}'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], recent_message.id)
```

#### Integration Testing

```python
# scenes/tests/test_chat_integration.py
class ChatIntegrationTest(TransactionTestCase):
    """Integration tests for complete chat workflow."""

    def test_end_to_end_chat_workflow(self):
        """Test complete chat workflow from WebSocket to API."""
        # 1. Send message via WebSocket
        # 2. Verify message stored in database
        # 3. Retrieve message via API
        # 4. Verify all data consistent across interfaces

        # This would use both WebSocket communicator and API client
        # to test the full integration
        pass
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
python manage.py test items.tests.test_models.ItemModelTest.test_soft_delete_functionality -v 2

# Run with pdb debugging
python manage.py test --debug-mode campaigns.tests.test_api
python manage.py test --debug-mode items.tests.test_admin

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

*This development guide should be updated as new patterns and practices are established. Last updated: 2025-08-17*
