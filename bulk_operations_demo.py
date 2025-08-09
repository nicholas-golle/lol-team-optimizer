"""
Demonstration of Bulk Operations functionality.

This script shows how to use the bulk operations system for:
- Importing player data from CSV/Excel/JSON
- Performing bulk edits on multiple players
- Exporting data in various formats
- Creating backups and restoring data
- Viewing audit logs
"""

import csv
import json
import tempfile
from pathlib import Path

from lol_team_optimizer.bulk_operations_manager import BulkOperationsManager
from lol_team_optimizer.bulk_operations_interface import BulkOperationsInterface
from lol_team_optimizer.data_manager import DataManager
from lol_team_optimizer.config import Config
from lol_team_optimizer.core_engine import CoreEngine


def create_sample_csv():
    """Create a sample CSV file for demonstration."""
    csv_data = [
        ['player_name', 'summoner_name', 'riot_tag', 'region', 'top_pref', 'jungle_pref', 'middle_pref', 'bottom_pref', 'support_pref'],
        ['Alice', 'AliceMain', 'NA1', 'na1', '5', '2', '3', '1', '4'],
        ['Bob', 'BobCarry', 'NA1', 'na1', '3', '5', '2', '4', '1'],
        ['Charlie', 'CharlieSupp', 'NA1', 'na1', '1', '3', '5', '2', '4'],
        ['Diana', 'DianaJungle', 'EUW', 'euw1', '2', '1', '4', '5', '3'],
        ['Eve', 'EveADC', 'EUW', 'euw1', '4', '4', '1', '3', '5'],
        ['Frank', 'FrankTop', 'KR', 'kr', '5', '1', '2', '3', '4'],
        ['Grace', 'GraceMid', 'KR', 'kr', '2', '3', '5', '1', '4']
    ]
    
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='')
    writer = csv.writer(temp_file)
    writer.writerows(csv_data)
    temp_file.close()
    
    return temp_file.name


def create_sample_json():
    """Create a sample JSON file for demonstration."""
    json_data = [
        {
            "player_name": "Helen",
            "summoner_name": "HelenSupport",
            "riot_tag": "OCE",
            "region": "oc1",
            "top_pref": 1,
            "jungle_pref": 2,
            "middle_pref": 3,
            "bottom_pref": 4,
            "support_pref": 5
        },
        {
            "player_name": "Ivan",
            "summoner_name": "IvanJungle",
            "riot_tag": "OCE",
            "region": "oc1",
            "top_pref": 3,
            "jungle_pref": 5,
            "middle_pref": 2,
            "bottom_pref": 1,
            "support_pref": 4
        }
    ]
    
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    json.dump(json_data, temp_file, indent=2)
    temp_file.close()
    
    return temp_file.name


def demonstrate_bulk_operations():
    """Demonstrate the bulk operations functionality."""
    print("🚀 Bulk Operations Demonstration")
    print("=" * 50)
    
    # Setup
    temp_dir = tempfile.mkdtemp()
    config = Config()
    config.data_directory = temp_dir
    config.player_data_file = "players.json"
    
    data_manager = DataManager(config)
    bulk_manager = BulkOperationsManager(data_manager, config)
    
    print(f"📁 Working directory: {temp_dir}")
    print()
    
    # 1. Import from CSV
    print("1️⃣ CSV Import Demonstration")
    print("-" * 30)
    
    csv_file = create_sample_csv()
    print(f"📄 Created sample CSV: {Path(csv_file).name}")
    
    field_mapping = {
        'player_name': 'player_name',
        'summoner_name': 'summoner_name',
        'riot_tag': 'riot_tag',
        'region': 'region',
        'top_pref': 'top_pref',
        'jungle_pref': 'jungle_pref',
        'middle_pref': 'middle_pref',
        'bottom_pref': 'bottom_pref',
        'support_pref': 'support_pref'
    }
    
    options = {
        'has_header': True,
        'delimiter': ',',
        'encoding': 'utf-8',
        'allow_duplicates': False
    }
    
    players, errors, stats = bulk_manager.import_processor.process_csv_import(
        csv_file, field_mapping, options
    )
    
    print(f"📊 Import Results:")
    print(f"   ✅ Valid players: {stats['valid']}")
    print(f"   ❌ Invalid players: {stats['invalid']}")
    print(f"   🔄 Duplicates: {stats['duplicates']}")
    print(f"   📝 Errors: {len(errors)}")
    
    if players:
        data_manager.save_player_data(players)
        print(f"💾 Saved {len(players)} players to database")
    
    Path(csv_file).unlink()  # Clean up
    print()
    
    # 2. Import from JSON
    print("2️⃣ JSON Import Demonstration")
    print("-" * 30)
    
    json_file = create_sample_json()
    print(f"📄 Created sample JSON: {Path(json_file).name}")
    
    json_players, json_errors, json_stats = bulk_manager.import_processor.process_json_import(
        json_file, {'allow_duplicates': False}
    )
    
    print(f"📊 JSON Import Results:")
    print(f"   ✅ Valid players: {json_stats['valid']}")
    print(f"   ❌ Invalid players: {json_stats['invalid']}")
    print(f"   📝 Errors: {len(json_errors)}")
    
    if json_players:
        all_players = data_manager.load_player_data()
        all_players.extend(json_players)
        data_manager.save_player_data(all_players)
        print(f"💾 Added {len(json_players)} more players to database")
    
    Path(json_file).unlink()  # Clean up
    print()
    
    # 3. Bulk Edit Operations
    print("3️⃣ Bulk Edit Demonstration")
    print("-" * 30)
    
    all_players = data_manager.load_player_data()
    print(f"👥 Total players in database: {len(all_players)}")
    
    # Select players from NA region for bulk edit
    na_players = [p.name for p in all_players if 'NA1' in str(getattr(p, 'riot_tag', ''))]
    print(f"🇺🇸 NA players selected for bulk edit: {na_players}")
    
    # Bulk edit: Increase jungle preference for NA players
    updates = {
        'role_preferences': {
            'jungle': 4,  # Set jungle preference to 4
            'support': 2  # Set support preference to 2
        }
    }
    
    success_count, edit_errors = bulk_manager.bulk_edit_players(na_players, updates)
    
    print(f"📊 Bulk Edit Results:")
    print(f"   ✅ Successfully updated: {success_count} players")
    print(f"   ❌ Errors: {len(edit_errors)}")
    
    if edit_errors:
        for error in edit_errors:
            print(f"      - {error}")
    print()
    
    # 4. Export Operations
    print("4️⃣ Export Demonstration")
    print("-" * 30)
    
    updated_players = data_manager.load_player_data()
    
    # CSV Export
    csv_export_options = {
        'include_preferences': True,
        'include_metadata': True,
        'delimiter': ','
    }
    
    csv_export_file = bulk_manager.export_processor.export_to_csv(
        updated_players, csv_export_options
    )
    
    csv_size = Path(csv_export_file).stat().st_size
    print(f"📄 CSV Export: {Path(csv_export_file).name} ({csv_size} bytes)")
    
    # JSON Export
    json_export_options = {
        'include_preferences': True,
        'include_metadata': True,
        'include_masteries': False
    }
    
    json_export_file = bulk_manager.export_processor.export_to_json(
        updated_players, json_export_options
    )
    
    json_size = Path(json_export_file).stat().st_size
    print(f"📄 JSON Export: {Path(json_export_file).name} ({json_size} bytes)")
    
    # Clean up export files
    Path(csv_export_file).unlink()
    Path(json_export_file).unlink()
    print()
    
    # 5. Backup and Restore
    print("5️⃣ Backup & Restore Demonstration")
    print("-" * 30)
    
    # Create backup
    backup_file = bulk_manager.create_backup("demo_backup")
    backup_size = Path(backup_file).stat().st_size
    print(f"💾 Created backup: {Path(backup_file).name} ({backup_size} bytes)")
    
    # Simulate data loss by removing a player
    current_players = data_manager.load_player_data()
    print(f"👥 Players before 'data loss': {len(current_players)}")
    
    # Remove last player
    reduced_players = current_players[:-1]
    data_manager.save_player_data(reduced_players)
    
    after_loss = data_manager.load_player_data()
    print(f"👥 Players after 'data loss': {len(after_loss)}")
    
    # Restore from backup
    success = bulk_manager.restore_backup(backup_file)
    print(f"🔄 Backup restore: {'✅ Success' if success else '❌ Failed'}")
    
    restored_players = data_manager.load_player_data()
    print(f"👥 Players after restore: {len(restored_players)}")
    
    Path(backup_file).unlink()  # Clean up
    print()
    
    # 6. Template Generation
    print("6️⃣ Template Generation Demonstration")
    print("-" * 30)
    
    templates = bulk_manager.get_bulk_operation_templates()
    
    for format_type, template_file in templates.items():
        template_size = Path(template_file).stat().st_size
        print(f"📄 {format_type.upper()} Template: {Path(template_file).name} ({template_size} bytes)")
        
        # Show first few lines of CSV template
        if format_type == 'csv':
            with open(template_file, 'r') as f:
                lines = f.readlines()[:3]
            print(f"   Preview: {lines[0].strip()}")
            print(f"            {lines[1].strip()}")
        
        Path(template_file).unlink()  # Clean up
    print()
    
    # 7. Audit Log
    print("7️⃣ Audit Log Demonstration")
    print("-" * 30)
    
    audit_history = bulk_manager.audit_logger.get_audit_history(limit=20)
    print(f"📋 Total audit entries: {len(audit_history)}")
    
    # Group by operation type
    operations = {}
    for entry in audit_history:
        op_type = entry['operation']
        operations[op_type] = operations.get(op_type, 0) + 1
    
    print("📊 Operations breakdown:")
    for op_type, count in operations.items():
        print(f"   {op_type}: {count}")
    
    # Show recent operations
    print("\n🕒 Recent operations:")
    for entry in audit_history[:5]:
        timestamp = entry['timestamp'][:19]  # Remove microseconds
        print(f"   {timestamp} - {entry['operation']} - {entry['entity_id']}")
    print()
    
    # 8. Statistics
    print("8️⃣ Operation Statistics")
    print("-" * 30)
    
    stats = bulk_manager.get_operation_statistics(days=1)
    
    print(f"📊 Statistics (last 24 hours):")
    print(f"   Total operations: {stats['total_operations']}")
    print(f"   Operations by type:")
    for op_type, count in stats['operations_by_type'].items():
        print(f"      {op_type}: {count}")
    
    print(f"   Operations by day: {len(stats['operations_by_day'])} days with activity")
    print()
    
    print("✅ Bulk Operations Demonstration Complete!")
    print(f"📁 All files created in: {temp_dir}")
    print("\nKey Features Demonstrated:")
    print("  ✅ CSV/JSON import with validation")
    print("  ✅ Bulk edit operations")
    print("  ✅ Multi-format export (CSV, JSON)")
    print("  ✅ Backup and restore functionality")
    print("  ✅ Template generation")
    print("  ✅ Comprehensive audit logging")
    print("  ✅ Operation statistics and reporting")


if __name__ == "__main__":
    try:
        demonstrate_bulk_operations()
    except Exception as e:
        print(f"\n❌ Demonstration failed: {e}")
        import traceback
        traceback.print_exc()