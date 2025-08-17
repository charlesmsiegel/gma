# GMA Migration Strategy: Mixin Field Application

This document describes the comprehensive migration strategy for applying audit mixin fields to existing Character, Item, and Location models in the GMA application.

## Overview

The migration adds `created_by` and `modified_by` audit fields to existing models while ensuring:
- **Zero data loss** during migration
- **Backwards compatibility** through rollback support
- **Performance optimization** with proper indexing
- **Comprehensive testing** for production safety

## Migration Components

### 1. Schema Migrations (Step 1)
Adds new fields with proper defaults and database constraints:

**Files:**
- `characters/migrations/0003_character_created_by_character_modified_by_and_more.py`
- `items/migrations/0003_item_modified_by_alter_item_created_at_and_more.py`
- `locations/migrations/0003_location_modified_by_alter_location_created_at_and_more.py`

**Changes:**
- Adds `created_by` and `modified_by` foreign key fields
- Updates timestamp fields with proper help text and indexing
- Maintains existing field behavior and constraints

### 2. Data Migrations (Step 2)
Populates audit fields for existing records with logical defaults:

**Files:**
- `characters/migrations/0004_populate_audit_fields.py`
- `items/migrations/0004_populate_audit_fields.py`
- `locations/migrations/0004_populate_audit_fields.py`

**Population Strategy:**
- **Characters**: Sets both `created_by` and `modified_by` to `player_owner`
- **Items/Locations**: Sets `modified_by` to existing `created_by` value
- Uses `update_fields` for minimal database impact
- Includes reverse migration functions for rollback safety

## Apply Migrations

```bash
# Apply all pending migrations
python manage.py migrate

# Apply specific app migrations
python manage.py migrate characters
python manage.py migrate items
python manage.py migrate locations

# Check migration status
python manage.py showmigrations
```

## Rollback Procedures

### Interactive Rollback (Recommended)
```bash
# Run interactive rollback script with safety confirmations
./scripts/rollback_mixin_migrations.sh
```

**Script Features:**
- Step-by-step confirmation process
- Migration state verification
- Environment detection (conda/virtualenv)
- Clear progress reporting
- Rollback of data migrations before schema migrations

### Manual Rollback
```bash
# Rollback to migration state before mixin fields
python manage.py migrate characters 0002
python manage.py migrate items 0002
python manage.py migrate locations 0002
```

**Rollback Order:**
1. Data migrations (0004) are rolled back first
2. Schema migrations (0003) are rolled back second
3. This ensures data integrity during the rollback process

## Safety Testing

### Comprehensive Test Suite
The migration includes 21 comprehensive tests in `core/tests/test_migration_strategy.py`:

```bash
# Run all migration safety tests
python manage.py test core.tests.test_migration_strategy

# Run specific test categories
python manage.py test core.tests.test_migration_strategy.ForwardMigrationDataPreservationTest
python manage.py test core.tests.test_migration_strategy.MigrationPerformanceTest
python manage.py test core.tests.test_migration_strategy.MigrationRollbackTest
```

### Test Categories

1. **Data Preservation Tests**
   - Verifies existing data survives migration unchanged
   - Tests count preservation and field integrity
   - Validates timestamp preservation

2. **Default Value Tests**
   - Ensures proper application of default values
   - Tests audit field population logic
   - Verifies save() method functionality with user parameter

3. **Data Integrity Tests**
   - Confirms foreign key relationships remain valid
   - Tests unique constraints and cascade behavior
   - Validates database constraint integrity

4. **Edge Case Tests**
   - Handles null values and empty fields
   - Tests boundary conditions (long names, old timestamps)
   - Verifies behavior when referenced users are deleted

5. **Performance Tests**
   - Validates migration performance with realistic data volumes
   - Tests index effectiveness after migration
   - Ensures acceptable query performance

6. **Rollback Tests**
   - Confirms migrations can be safely reversed
   - Tests data integrity after rollback
   - Verifies atomic migration behavior

## Enhanced Model Usage

After migration, models support enhanced audit functionality:

```python
# Automatic audit field population
character = Character.objects.create(
    name="Test Character",
    campaign=campaign,
    player_owner=user
)
character.save(user=request.user)  # Sets created_by and modified_by

# Updating with audit tracking
character.description = "Updated description"
character.save(user=request.user)  # Updates modified_by and updated_at

# Querying with audit fields
recent_characters = Character.objects.filter(
    created_at__gte=timezone.now() - timedelta(days=7)
)

characters_by_user = Character.objects.filter(
    created_by=request.user
)
```

## Performance Impact

### Database Indexes
All timestamp fields include database indexes for efficient querying:
- `created_at` indexed for chronological queries
- `updated_at` indexed for recent activity queries
- Foreign key fields automatically indexed

### Query Optimization
```python
# Efficient queries with select_related for audit fields
characters = Character.objects.select_related(
    'created_by', 'modified_by', 'player_owner'
).filter(campaign=campaign)

# Optimized ordering by timestamp fields (uses indexes)
recent_items = Item.objects.order_by('-updated_at')[:10]
```

## Production Considerations

### Pre-Migration Checklist
- [ ] Run migration safety tests: `python manage.py test core.tests.test_migration_strategy`
- [ ] Verify database backup is current
- [ ] Confirm rollback script is accessible: `./scripts/rollback_mixin_migrations.sh`
- [ ] Test migration on staging environment with production-like data
- [ ] Verify application code handles new audit fields correctly

### Post-Migration Verification
- [ ] Confirm all migrations applied: `python manage.py showmigrations`
- [ ] Verify audit fields populated correctly in database
- [ ] Test save() functionality with user parameter
- [ ] Run application smoke tests
- [ ] Monitor database performance for index effectiveness

### Monitoring
- Monitor database query performance for timestamp-based queries
- Track audit field population rates for new records
- Watch for any foreign key constraint violations
- Verify proper user tracking in audit trails

## Troubleshooting

### Common Issues

**Migration Fails with Foreign Key Error:**
```bash
# Check for orphaned records
python manage.py shell
>>> from characters.models import Character
>>> Character.objects.filter(player_owner__isnull=True).count()
```

**Performance Issues After Migration:**
```bash
# Verify indexes were created
python manage.py dbshell
\d characters_character  # Check table structure and indexes
```

**Rollback Script Permission Error:**
```bash
# Make script executable
chmod +x ./scripts/rollback_mixin_migrations.sh
```

### Emergency Rollback
If immediate rollback is needed without the interactive script:
```bash
python manage.py migrate characters 0003  # Rollback data migration only
python manage.py migrate characters 0002  # Rollback schema migration
# Repeat for items and locations
```

---

**Last Updated:** 2025-08-17
**Migration Files:** Characters/Items/Locations 0003-0004
**Test Coverage:** 21 comprehensive tests
**Rollback Support:** Full rollback capability with interactive script
