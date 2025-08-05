# Data Migration Guide

This guide explains how to migrate existing League of Legends Team Optimizer data to the new streamlined format.

## Overview

The streamlined interface consolidates functionality and may require migration of existing data to ensure compatibility. The migration system handles:

- Player data format updates
- Cache file restructuring  
- Synergy data format standardization
- Backward compatibility preservation

## Quick Start

### Check Migration Status

```bash
python -m lol_team_optimizer.migration_cli check
```

This will show:
- Whether migration is needed
- What data will be affected
- Recommendations for next steps

### Perform Migration

```bash
# Create backup first (recommended)
python -m lol_team_optimizer.migration_cli backup --name "pre_streamlined"

# Run migration
python -m lol_team_optimizer.migration_cli migrate
```

### Rollback if Needed

```bash
# List available backups
python -m lol_team_optimizer.migration_cli list-backups

# Rollback to specific backup
python -m lol_team_optimizer.migration_cli rollback --backup-name "pre_streamlined"
```

## Migration Details

### What Gets Migrated

#### Player Data
- **Missing Fields**: Adds default values for missing role preferences, champion pools
- **Datetime Format**: Converts old datetime strings to ISO format
- **Champion Masteries**: Ensures all required fields are present
- **Role Preferences**: Fills in missing roles with default values (3)

#### Cache Data
- **Monolithic Files**: Splits large cache files into individual entries
- **Format Standardization**: Ensures consistent cache entry format
- **TTL Handling**: Preserves time-to-live information

#### Synergy Data
- **Field Completion**: Adds missing synergy calculation fields
- **Format Consistency**: Standardizes synergy data structure

### Backup System

The migration system automatically creates backups before any changes:

- **Location**: `data/backups/`
- **Format**: Complete copy of data and cache directories
- **Manifest**: JSON file tracking what was backed up
- **Retention**: Manual cleanup (backups are not auto-deleted)

### Safety Features

- **Automatic Backup**: Every migration creates a backup
- **Validation**: Data is validated before and after migration
- **Rollback**: Complete rollback capability to any backup
- **Error Handling**: Graceful handling of corrupted data
- **Dry Run**: Check what would be migrated without changes

## Command Reference

### Check Migration Status
```bash
python -m lol_team_optimizer.migration_cli check
```
- Shows migration requirements
- Lists issues found
- Provides recommendations

### Create Backup
```bash
python -m lol_team_optimizer.migration_cli backup [--name BACKUP_NAME]
```
- Creates backup of current data
- Optional custom name (auto-generated if not provided)

### Perform Migration
```bash
python -m lol_team_optimizer.migration_cli migrate [--force]
```
- Migrates all data to new format
- `--force`: Skip confirmation prompts

### List Backups
```bash
python -m lol_team_optimizer.migration_cli list-backups
```
- Shows all available backups
- Displays creation date, file count, size

### Rollback
```bash
python -m lol_team_optimizer.migration_cli rollback [--backup-name NAME] [--force]
```
- Restores data from backup
- Interactive backup selection if name not provided
- `--force`: Skip confirmation prompts

### Export Status
```bash
python -m lol_team_optimizer.migration_cli export-status [--output FILE]
```
- Exports migration status to JSON file
- Useful for automation or detailed analysis

## Integration with Core System

The core engine automatically detects when migration is needed:

```python
from lol_team_optimizer.core_engine import CoreEngine

engine = CoreEngine()
migration_status = engine.get_migration_status()

if migration_status:
    print("Migration needed:", migration_status['migration_needed'])
```

## Troubleshooting

### Common Issues

#### "Migration needed but no issues found"
- Usually indicates minor format differences
- Safe to migrate
- Consider creating backup first

#### "Cache file corruption detected"
- Some cache files may be corrupted
- Migration will skip corrupted files
- Lost cache data will be regenerated on next API call

#### "Player data validation failed"
- Player data has unexpected format
- Check `data/players.json` manually
- May need manual cleanup before migration

#### "Backup creation failed"
- Check disk space
- Verify write permissions to data directory
- Ensure backup directory is accessible

### Recovery Procedures

#### If Migration Fails
1. Check error messages in output
2. Restore from automatic backup created before migration
3. Fix underlying issues (disk space, permissions, data corruption)
4. Retry migration

#### If Data is Lost
1. List available backups: `migration_cli list-backups`
2. Rollback to most recent backup: `migration_cli rollback`
3. If no backups available, check `data/backups/` directory manually

#### If System Won't Start
1. Check migration log: `data/migration_log.json`
2. Try rollback to known good backup
3. Delete corrupted cache files (will be regenerated)
4. Restore player data from backup manually

### Manual Migration

If automatic migration fails, you can migrate manually:

1. **Backup Data**:
   ```bash
   cp -r data data_backup
   cp -r cache cache_backup
   ```

2. **Fix Player Data**:
   - Open `data/players.json`
   - Ensure all players have required fields
   - Convert datetime strings to ISO format

3. **Fix Cache Data**:
   - Split large cache files into individual entries
   - Ensure each entry has `data`, `timestamp`, `ttl_hours`

4. **Validate**:
   ```bash
   python -m lol_team_optimizer.migration_cli check
   ```

## Best Practices

### Before Migration
- Create backup with descriptive name
- Check available disk space (migration may temporarily double storage)
- Close other applications using the data
- Note current system state

### During Migration
- Don't interrupt the process
- Monitor for error messages
- Keep terminal/command prompt open

### After Migration
- Verify migration success with status check
- Test core functionality
- Keep backup until confident system works
- Document any issues encountered

### Regular Maintenance
- Periodically clean old backups
- Monitor backup disk usage
- Test rollback procedure occasionally

## API Reference

### Python API

```python
from lol_team_optimizer.migration import DataMigrator, run_migration_check, run_full_migration

# Check if migration needed
status = run_migration_check()
print(status['migration_needed'])

# Perform full migration
results = run_full_migration()
print(results['success'])

# Advanced usage
migrator = DataMigrator()
backup_path = migrator.create_backup("my_backup")
migration_results = migrator.perform_full_migration()
rollback_results = migrator.rollback_migration("my_backup")
```

### Status Dictionary Format

```python
{
    'migration_needed': bool,
    'backup_recommended': bool,
    'issues_found': [str],
    'data_summary': {
        'player_count': int,
        'cache_files': int,
        'synergy_pairs': int
    },
    'compatibility_status': 'compatible' | 'migration_required' | 'issues_detected'
}
```

### Migration Results Format

```python
{
    'success': bool,
    'migration_start': str,  # ISO datetime
    'migration_end': str,    # ISO datetime
    'backup_path': str,
    'total_errors': int,
    'total_warnings': int,
    'player_migration': {
        'players_migrated': int,
        'players_skipped': int,
        'errors': [str],
        'warnings': [str]
    },
    'cache_migration': {...},
    'synergy_migration': {...}
}
```

## Support

If you encounter issues not covered in this guide:

1. Check the migration log: `data/migration_log.json`
2. Run status check with verbose output
3. Create an issue with:
   - Migration status output
   - Error messages
   - System information
   - Steps to reproduce

The migration system is designed to be safe and reversible. When in doubt, create a backup and test the migration process.