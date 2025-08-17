# Mixin Migration Strategy

## Overview

This document outlines the safe migration strategy for applying mixin-based fields to existing Django models in the Game Master Application (GMA). The migration adds standardized audit and timestamp fields to the Character, Item, and Location models through Django mixins.

## Table of Contents

1. [Migration Scope](#migration-scope)
2. [Pre-Migration Checklist](#pre-migration-checklist)
3. [Migration Process](#migration-process)
4. [Rollback Procedures](#rollback-procedures)
5. [Testing Strategy](#testing-strategy)
6. [Production Deployment](#production-deployment)
7. [Post-Migration Validation](#post-migration-validation)
8. [Troubleshooting](#troubleshooting)

## Migration Scope

### Affected Models
- **Character** (`characters.models.Character`)
- **Item** (`items.models.Item`)
- **Location** (`locations.models.Location`)

### Fields Being Added
Each model receives the following fields through mixins:

| Field | Type | Mixin | Description |
|-------|------|-------|-------------|
| `created_at` | DateTimeField | TimestampedMixin | Auto-set on creation |
| `updated_at` | DateTimeField | TimestampedMixin | Auto-updated on save |
| `created_by` | ForeignKey(User) | AuditableMixin | User who created the record |
| `modified_by` | ForeignKey(User) | AuditableMixin | User who last modified |
| `name` | CharField(100) | NamedModelMixin | Standardized name field |
| `description` | TextField | DescribedModelMixin | Optional description |

### Migration Files

#### Schema Migrations (Step 1)
- `characters/migrations/0003_character_created_by_character_modified_by_and_more.py`
- `items/migrations/0003_item_modified_by_alter_item_created_at_and_more.py`
- `locations/migrations/0003_location_modified_by_alter_location_created_at_and_more.py`

#### Data Migrations (Step 2)
- `characters/migrations/0004_populate_audit_fields.py`
- `items/migrations/0004_populate_audit_fields.py`
- `locations/migrations/0004_populate_audit_fields.py`

## Pre-Migration Checklist

### 1. Backup Database
```bash
# PostgreSQL backup
pg_dump -U postgres -d gm_app_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Verify backup
ls -lh backup_*.sql
```

### 2. Test Environment Validation
```bash
# Run migration tests
python manage.py test core.tests.test_migration_strategy -v 2

# Expected output: 21 tests passed
```

### 3. Check Current Migration Status
```bash
python manage.py showmigrations characters items locations

# Should show 0003 and 0004 as [ ] (not applied)
```

### 4. Verify Database Connectivity
```bash
python manage.py dbshell --command "SELECT 1;"
```

## Migration Process

### Step 1: Apply Schema Migrations

Apply the structural changes that add new fields:

```bash
# Apply schema migrations for all apps
python manage.py migrate characters 0003
python manage.py migrate items 0003
python manage.py migrate locations 0003
```

At this point:
- New fields exist in the database
- `created_by` and `modified_by` are NULL for existing records
- Timestamps are set to current time for existing records

### Step 2: Apply Data Migrations

Populate the audit fields with sensible defaults:

```bash
# Apply data migrations to populate audit fields
python manage.py migrate characters 0004
python manage.py migrate items 0004
python manage.py migrate locations 0004
```

Default value strategy:
- **Characters**: `created_by` and `modified_by` set to `player_owner`
- **Items**: `created_by` and `modified_by` set to `campaign.owner`
- **Locations**: `created_by` and `modified_by` set to `campaign.owner`

### Step 3: Verify Migration Success

```bash
# Check migration status
python manage.py showmigrations characters items locations

# All migrations should show [X] (applied)

# Run validation tests
python manage.py test core.tests.test_migration_strategy
```

## Rollback Procedures

### Automated Rollback Script

Use the provided rollback script for safe reversal:

```bash
# Execute rollback script
./scripts/rollback_mixin_migrations.sh
```

### Manual Rollback Steps

If automated rollback fails:

```bash
# Step 1: Rollback data migrations
python manage.py migrate characters 0003
python manage.py migrate items 0003
python manage.py migrate locations 0003

# Step 2: Rollback schema migrations
python manage.py migrate characters 0002
python manage.py migrate items 0002
python manage.py migrate locations 0002
```

### Post-Rollback Validation

```bash
# Verify rollback
python manage.py showmigrations characters items locations

# 0003 and 0004 should show [ ] (not applied)
```

## Testing Strategy

### Unit Tests

The migration safety test suite (`core/tests/test_migration_strategy.py`) includes:

1. **Data Preservation Tests**
   - Existing data remains intact
   - Foreign key relationships maintained
   - No data loss during migration

2. **Default Value Tests**
   - Audit fields populated correctly
   - Timestamps set appropriately
   - NULL handling for edge cases

3. **Performance Tests**
   - Migration completes within acceptable time
   - No database locks or deadlocks
   - Handles datasets up to 100 records per model

4. **Rollback Tests**
   - Forward and backward migration work
   - Data integrity after rollback
   - No orphaned constraints

### Integration Tests

```bash
# Run full test suite to verify no regressions
make test

# Expected: All tests pass
```

## Production Deployment

### Deployment Steps

1. **Announce Maintenance Window**
   - Notify users of 15-minute downtime
   - Schedule during low-traffic period

2. **Pre-Deployment**
   ```bash
   # Take full backup
   pg_dump -U postgres -d production_db > pre_migration_backup.sql

   # Put application in maintenance mode
   python manage.py maintenance_mode on
   ```

3. **Execute Migration**
   ```bash
   # Apply migrations in transaction
   python manage.py migrate --database production

   # Verify immediately
   python manage.py dbshell --database production \
     --command "SELECT COUNT(*) FROM characters_character WHERE created_by_id IS NULL;"
   # Should return 0
   ```

4. **Post-Deployment**
   ```bash
   # Run health checks
   python manage.py health_check --database --log

   # Disable maintenance mode
   python manage.py maintenance_mode off
   ```

### Monitoring

Monitor these metrics post-migration:
- Database query performance
- Application response times
- Error rates in logs
- Audit trail creation

## Post-Migration Validation

### Data Integrity Checks

```sql
-- Check Characters have audit fields
SELECT COUNT(*) FROM characters_character
WHERE created_by_id IS NULL OR modified_by_id IS NULL;
-- Expected: 0

-- Check Items have audit fields
SELECT COUNT(*) FROM items_item
WHERE created_by_id IS NULL OR modified_by_id IS NULL;
-- Expected: 0

-- Check Locations have audit fields
SELECT COUNT(*) FROM locations_location
WHERE created_by_id IS NULL OR modified_by_id IS NULL;
-- Expected: 0

-- Verify timestamp fields
SELECT COUNT(*) FROM characters_character
WHERE created_at IS NULL OR updated_at IS NULL;
-- Expected: 0
```

### Application Functionality

1. Create new Character/Item/Location
2. Edit existing records
3. Verify audit trails update correctly
4. Check admin interface displays new fields

## Troubleshooting

### Common Issues and Solutions

#### Issue: Migration Timeout
**Symptom**: Migration hangs or times out
**Solution**:
```bash
# Increase statement timeout
psql -c "SET statement_timeout = '10min';"
python manage.py migrate
```

#### Issue: Foreign Key Constraint Violation
**Symptom**: Error about missing user references
**Solution**:
```bash
# Check for deleted users referenced in data
python manage.py shell
>>> from django.contrib.auth import get_user_model
>>> User = get_user_model()
>>> User.objects.filter(id__in=[...]).exists()
```

#### Issue: Duplicate Migration Numbers
**Symptom**: Migration number conflict
**Solution**:
```bash
# Rename migration file to next available number
mv 0004_populate_audit_fields.py 0005_populate_audit_fields.py
# Update dependencies in the file
```

#### Issue: Rollback Fails
**Symptom**: Cannot reverse migration
**Solution**:
```bash
# Force reset to specific migration
python manage.py migrate characters 0002 --fake
python manage.py migrate characters 0002  # Actually apply

# Manually clean up if needed
psql -c "ALTER TABLE characters_character DROP COLUMN created_by_id CASCADE;"
```

## Performance Considerations

### Expected Performance

| Dataset Size | Migration Time | Rollback Time |
|-------------|---------------|---------------|
| < 100 records | < 1 second | < 1 second |
| 1,000 records | < 5 seconds | < 3 seconds |
| 10,000 records | < 30 seconds | < 20 seconds |
| 100,000 records | < 5 minutes | < 3 minutes |

### Optimization Tips

1. **Run during low traffic**: Minimize concurrent database access
2. **Disable triggers temporarily**: If safe to do so
3. **Batch updates**: Data migration uses single-record updates for safety but can be batched for large datasets
4. **Index considerations**: New fields are indexed, which may slow initial migration but improves query performance

## Security Considerations

1. **Audit Trail**: All migrations are logged with user performing them
2. **Permission Checks**: Only database superusers can run migrations
3. **Data Privacy**: No sensitive data exposed during migration
4. **Rollback Safety**: All migrations are reversible without data loss

## Conclusion

This migration strategy provides a safe, tested approach to adding mixin-based fields to existing models. The combination of:
- Comprehensive testing (21 test cases)
- Staged migration approach (schema then data)
- Automated rollback procedures
- Detailed documentation

Ensures that the migration can be applied safely in production with minimal risk and quick recovery options if issues arise.

For questions or issues, contact the development team or refer to the troubleshooting section above.
