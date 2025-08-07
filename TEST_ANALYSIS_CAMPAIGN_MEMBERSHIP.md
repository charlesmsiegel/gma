# CampaignMembership Test Analysis - GitHub Issue #21

## Executive Summary

I've created comprehensive tests for the CampaignMembership model based on GitHub issue #21 requirements. The tests reveal exactly what needs to be implemented to match the specification.

**Test Results: 26 tests total**
- ✅ **17 PASSING** - Current implementation working correctly
- ❌ **7 FAILING** - Core requirements missing
- 🔍 **2 ERRORS** - Model structure issues

## Test Coverage Areas

### ✅ PASSING Tests (Already Implemented)

1. **Cascade Deletion** - All 5 tests pass
   - User deletion cascades to memberships
   - Campaign deletion cascades to memberships
   - Multiple memberships handled correctly

2. **Admin Registration** - All 2 tests pass
   - Model registered in Django admin
   - Proper admin configuration (list_display, list_filter, search_fields)

3. **String Representation** - All 2 tests pass
   - Format: "user - campaign (role)"
   - Works for all role types

4. **Database Constraints** - All 2 tests pass
   - Unique constraint on user-campaign pairs
   - Meta options configured correctly

5. **Basic Model Structure** - Most tests pass
   - ForeignKey relationships correct
   - joined_at auto-populated
   - Field types correct

### ❌ FAILING Tests (Need Implementation)

#### 1. **Role Choices Structure** (3 tests failing)
```python
# CURRENT (wrong):
ROLE_CHOICES = [
    ("gm", "Game Master"),
    ("player", "Player"),
    ("observer", "Observer"),
]

# REQUIRED by issue #21:
ROLE_CHOICES = [
    ('OWNER', 'Owner'),
    ('GM', 'Game Master'),
    ('PLAYER', 'Player'),
    ('OBSERVER', 'Observer'),
]
```

#### 2. **Role Field Max Length** (1 test failing)
- **Current**: max_length=20
- **Required**: max_length=10 (to fit uppercase role names)

#### 3. **Role Validation** (1 test failing)
- Invalid roles not properly rejected during validation
- Need proper choice validation

#### 4. **Business Logic** (2 tests failing)
- **Missing**: Campaign creator doesn't automatically get OWNER role
- **Missing**: No enforcement of "exactly one OWNER per campaign" rule

### 🔍 ERROR Tests (Model Structure Issues)

1. **Model Field Structure** - Field inspection failing
2. **Role Hierarchy** - OWNER role completely missing from current choices

## Required Changes to Match Issue #21

### 1. Update CampaignMembership Model

**File**: `/home/janothar/gma/campaigns/models/campaign.py`

```python
class CampaignMembership(models.Model):
    """Membership relationship between users and campaigns."""

    # FIX: Update role choices to match issue #21 exactly
    ROLE_CHOICES = [
        ('OWNER', 'Owner'),           # ADD: Missing OWNER role
        ('GM', 'Game Master'),        # CHANGE: 'gm' → 'GM'
        ('PLAYER', 'Player'),         # CHANGE: 'player' → 'PLAYER'
        ('OBSERVER', 'Observer'),     # CHANGE: 'observer' → 'OBSERVER'
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)  # ✅ Correct
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE)  # ✅ Correct

    # FIX: Reduce max_length to 10
    role = models.CharField(
        max_length=10,  # CHANGE: 20 → 10
        choices=ROLE_CHOICES,
        help_text="The user's role in the campaign",
    )

    joined_at = models.DateTimeField(auto_now_add=True)  # ✅ Correct

    class Meta:
        db_table = "campaigns_membership"  # ✅ Correct
        unique_together = [["campaign", "user"]]  # ✅ Correct
        # ... rest of Meta options
```

### 2. Add Business Logic Methods

```python
def clean(self):
    """Validate the membership data."""
    super().clean()

    # ADD: Ensure only one OWNER per campaign
    if self.role == 'OWNER':
        existing_owner = CampaignMembership.objects.filter(
            campaign=self.campaign,
            role='OWNER'
        ).exclude(pk=self.pk)

        if existing_owner.exists():
            raise ValidationError(
                "Campaign can have only one OWNER. "
                "Transfer ownership instead of creating new OWNER."
            )

# ADD: Signal to auto-create OWNER membership when campaign is created
@receiver(post_save, sender=Campaign)
def create_owner_membership(sender, instance, created, **kwargs):
    """Automatically create OWNER membership for campaign creator."""
    if created:
        CampaignMembership.objects.create(
            user=instance.owner,
            campaign=instance,
            role='OWNER'
        )
```

### 3. Database Migration Required

The role choices change requires a database migration:

```python
# Migration will need to handle:
# 1. Change max_length: 20 → 10
# 2. Update existing data: 'gm'/'player'/'observer' → 'GM'/'PLAYER'/'OBSERVER'
# 3. Handle any existing owner relationships
```

## Test File Location

**Created**: `/home/janothar/gma/campaigns/tests/test_campaign_membership.py`

The test file contains 26 comprehensive tests covering:
- ✅ Model structure validation
- ✅ Role choice validation
- ✅ Constraint testing
- ✅ Cascade deletion behavior
- ✅ String representation
- ✅ Admin integration
- ✅ Business logic requirements
- ✅ Permission hierarchy
- ✅ Database configuration

## Next Steps

1. **Update the model** - Fix role choices and max_length
2. **Add business logic** - OWNER auto-creation and one-per-campaign constraint
3. **Create migration** - Handle existing data transformation
4. **Run tests** - Verify all 26 tests pass
5. **Test existing functionality** - Ensure no regressions

The tests provide a complete specification of the requirements and will guide the implementation to exactly match GitHub issue #21.
