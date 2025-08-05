"""
Command-line interface for data migration operations.

This module provides easy-to-use CLI commands for checking migration status,
performing migrations, and managing backups.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from .migration import DataMigrator, run_migration_check, run_full_migration
from .config import Config


def print_status_report(status: dict) -> None:
    """Print a formatted migration status report."""
    print("\n" + "="*60)
    print("MIGRATION STATUS REPORT")
    print("="*60)
    
    print(f"Migration Needed: {'YES' if status['migration_needed'] else 'NO'}")
    print(f"Compatibility Status: {status['compatibility_status'].upper()}")
    print(f"Backup Recommended: {'YES' if status['backup_recommended'] else 'NO'}")
    
    if status['data_summary']:
        print("\nData Summary:")
        for key, value in status['data_summary'].items():
            print(f"  {key.replace('_', ' ').title()}: {value}")
    
    if status['issues_found']:
        print("\nIssues Found:")
        for issue in status['issues_found']:
            print(f"  • {issue}")
    
    print("\nRecommendations:")
    if status['migration_needed']:
        print("  • Run migration to update data format")
        print("  • Create backup before migration")
    elif status['backup_recommended']:
        print("  • Consider creating backup as precaution")
    else:
        print("  • No action needed - data is compatible")
    
    print("="*60)


def print_migration_results(results: dict) -> None:
    """Print formatted migration results."""
    print("\n" + "="*60)
    print("MIGRATION RESULTS")
    print("="*60)
    
    print(f"Overall Success: {'YES' if results['success'] else 'NO'}")
    print(f"Migration Start: {results['migration_start']}")
    print(f"Migration End: {results['migration_end']}")
    print(f"Backup Created: {results['backup_path']}")
    
    print(f"\nTotal Errors: {results['total_errors']}")
    print(f"Total Warnings: {results['total_warnings']}")
    
    # Player migration results
    player_results = results['player_migration']
    print(f"\nPlayer Migration:")
    print(f"  Players Migrated: {player_results['players_migrated']}")
    print(f"  Players Skipped: {player_results['players_skipped']}")
    if player_results['errors']:
        print("  Errors:")
        for error in player_results['errors']:
            print(f"    • {error}")
    
    # Cache migration results
    cache_results = results['cache_migration']
    print(f"\nCache Migration:")
    print(f"  Cache Files Processed: {cache_results['cache_files_processed']}")
    print(f"  Cache Entries Migrated: {cache_results['cache_entries_migrated']}")
    if cache_results['errors']:
        print("  Errors:")
        for error in cache_results['errors']:
            print(f"    • {error}")
    
    # Synergy migration results
    synergy_results = results['synergy_migration']
    print(f"\nSynergy Migration:")
    print(f"  Synergy Pairs Migrated: {synergy_results['synergy_pairs_migrated']}")
    print(f"  Synergy Pairs Skipped: {synergy_results['synergy_pairs_skipped']}")
    if synergy_results['errors']:
        print("  Errors:")
        for error in synergy_results['errors']:
            print(f"    • {error}")
    
    print("="*60)


def print_backup_list(backups: list) -> None:
    """Print formatted backup list."""
    print("\n" + "="*60)
    print("AVAILABLE BACKUPS")
    print("="*60)
    
    if not backups:
        print("No backups found.")
        print("="*60)
        return
    
    print(f"{'Name':<20} {'Created':<20} {'Files':<8} {'Size (MB)':<10}")
    print("-" * 60)
    
    for backup in backups:
        name = backup['name'][:19]  # Truncate if too long
        created = backup['created_at'][:19] if backup['created_at'] else 'Unknown'
        files = str(backup['file_count'])
        size = f"{backup['size_mb']:.1f}"
        
        print(f"{name:<20} {created:<20} {files:<8} {size:<10}")
    
    print("="*60)


def cmd_check(args) -> int:
    """Check migration status."""
    try:
        print("Checking migration status...")
        status = run_migration_check()
        print_status_report(status)
        
        # Return appropriate exit code
        if status['migration_needed']:
            return 2  # Migration needed
        elif status['issues_found']:
            return 1  # Issues found but not critical
        else:
            return 0  # All good
    
    except Exception as e:
        print(f"Error checking migration status: {e}", file=sys.stderr)
        return 1


def cmd_migrate(args) -> int:
    """Perform full migration."""
    try:
        if not args.force:
            # Check status first
            status = run_migration_check()
            if not status['migration_needed']:
                print("No migration needed. Use --force to migrate anyway.")
                return 0
            
            # Confirm with user
            print_status_report(status)
            response = input("\nProceed with migration? (y/N): ").strip().lower()
            if response not in ['y', 'yes']:
                print("Migration cancelled.")
                return 0
        
        print("Starting migration...")
        results = run_full_migration()
        print_migration_results(results)
        
        return 0 if results['success'] else 1
    
    except Exception as e:
        print(f"Error during migration: {e}", file=sys.stderr)
        return 1


def cmd_backup(args) -> int:
    """Create backup."""
    try:
        migrator = DataMigrator()
        
        backup_name = args.name
        if not backup_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"manual_backup_{timestamp}"
        
        print(f"Creating backup '{backup_name}'...")
        backup_path = migrator.create_backup(backup_name)
        
        print(f"Backup created successfully: {backup_path}")
        return 0
    
    except Exception as e:
        print(f"Error creating backup: {e}", file=sys.stderr)
        return 1


def cmd_list_backups(args) -> int:
    """List available backups."""
    try:
        migrator = DataMigrator()
        backups = migrator.list_backups()
        print_backup_list(backups)
        return 0
    
    except Exception as e:
        print(f"Error listing backups: {e}", file=sys.stderr)
        return 1


def cmd_rollback(args) -> int:
    """Rollback to a backup."""
    try:
        migrator = DataMigrator()
        
        # List available backups if no name provided
        if not args.backup_name:
            backups = migrator.list_backups()
            print_backup_list(backups)
            
            if not backups:
                print("No backups available for rollback.")
                return 1
            
            backup_name = input("Enter backup name to rollback to: ").strip()
            if not backup_name:
                print("Rollback cancelled.")
                return 0
        else:
            backup_name = args.backup_name
        
        if not args.force:
            response = input(f"Rollback to backup '{backup_name}'? This will overwrite current data. (y/N): ").strip().lower()
            if response not in ['y', 'yes']:
                print("Rollback cancelled.")
                return 0
        
        print(f"Rolling back to backup '{backup_name}'...")
        results = migrator.rollback_migration(backup_name)
        
        if results['success']:
            print(f"Rollback successful. Restored {results['files_restored']} files.")
            return 0
        else:
            print("Rollback failed:")
            for error in results['errors']:
                print(f"  • {error}")
            return 1
    
    except Exception as e:
        print(f"Error during rollback: {e}", file=sys.stderr)
        return 1


def cmd_export_status(args) -> int:
    """Export migration status to JSON file."""
    try:
        status = run_migration_check()
        
        output_file = args.output or "migration_status.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(status, f, indent=2, ensure_ascii=False)
        
        print(f"Migration status exported to: {output_file}")
        return 0
    
    except Exception as e:
        print(f"Error exporting status: {e}", file=sys.stderr)
        return 1


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="League of Legends Team Optimizer - Data Migration Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m lol_team_optimizer.migration_cli check
  python -m lol_team_optimizer.migration_cli migrate
  python -m lol_team_optimizer.migration_cli backup --name "pre_migration"
  python -m lol_team_optimizer.migration_cli rollback --backup-name "pre_migration"
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Check command
    check_parser = subparsers.add_parser('check', help='Check migration status')
    check_parser.set_defaults(func=cmd_check)
    
    # Migrate command
    migrate_parser = subparsers.add_parser('migrate', help='Perform full migration')
    migrate_parser.add_argument('--force', action='store_true', 
                               help='Force migration without confirmation')
    migrate_parser.set_defaults(func=cmd_migrate)
    
    # Backup command
    backup_parser = subparsers.add_parser('backup', help='Create data backup')
    backup_parser.add_argument('--name', help='Custom backup name')
    backup_parser.set_defaults(func=cmd_backup)
    
    # List backups command
    list_parser = subparsers.add_parser('list-backups', help='List available backups')
    list_parser.set_defaults(func=cmd_list_backups)
    
    # Rollback command
    rollback_parser = subparsers.add_parser('rollback', help='Rollback to a backup')
    rollback_parser.add_argument('--backup-name', help='Name of backup to rollback to')
    rollback_parser.add_argument('--force', action='store_true',
                                help='Force rollback without confirmation')
    rollback_parser.set_defaults(func=cmd_rollback)
    
    # Export status command
    export_parser = subparsers.add_parser('export-status', help='Export migration status to JSON')
    export_parser.add_argument('--output', help='Output file path (default: migration_status.json)')
    export_parser.set_defaults(func=cmd_export_status)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())