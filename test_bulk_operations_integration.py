"""
Integration test for bulk operations functionality.

This test demonstrates the complete bulk operations workflow including:
- CSV import with validation
- Bulk edit operations
- Export functionality
- Backup and restore
"""

import csv
import json
import tempfile
from pathlib import Path

from lol_team_optimizer.bulk_operations_manager import BulkOperationsManager
from lol_team_optimizer.data_manager import DataManager
from lol_team_optimizer.config import Config
from lol_team_optimizer.models import Player


def test_bulk_operations_integration():
    """Test complete bulk operations workflow."""
    print("🧪 Testing Bulk Operations Integration")
    
    # Create temporary config
    temp_dir = tempfile.mkdtemp()
    config = Config()
    config.data_directory = temp_dir
    config.player_data_file = "players.json"
    
    # Initialize components
    data_manager = DataManager(config)
    bulk_manager = BulkOperationsManager(data_manager, config)
    
    print("✅ Initialized bulk operations manager")
    
    # Test 1: Create sample CSV data and import
    print("\n📥 Testing CSV Import...")
    
    csv_data = [
        ['player_name', 'summoner_name', 'top_pref', 'jungle_pref', 'middle_pref', 'bottom_pref', 'support_pref'],
        ['Alice', 'AliceSummoner', '5', '2', '3', '1', '4'],
        ['Bob', 'BobSummoner', '3', '5', '2', '4', '1'],
        ['Charlie', 'CharlieSummoner', '1', '3', '5', '2', '4'],
        ['Diana', 'DianaSummoner', '2', '1', '4', '5', '3'],
        ['Eve', 'EveSummoner', '4', '4', '1', '3', '5']
    ]
    
    # Create temporary CSV file
    temp_csv = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
    writer = csv.writer(temp_csv)
    writer.writerows(csv_data)
    temp_csv.close()
    
    try:
        # Import CSV data
        field_mapping = {
            'player_name': 'player_name',
            'summoner_name': 'summoner_name',
            'top_pref': 'top_pref',
            'jungle_pref': 'jungle_pref',
            'middle_pref': 'middle_pref',
            'bottom_pref': 'bottom_pref',
            'support_pref': 'support_pref'
        }
        
        options = {'has_header': True, 'delimiter': ',', 'allow_duplicates': False}
        
        players, errors, stats = bulk_manager.import_processor.process_csv_import(
            temp_csv.name, field_mapping, options
        )
        
        print(f"   📊 Import Results: {stats['valid']} valid, {stats['invalid']} invalid, {len(errors)} errors")
        assert stats['valid'] == 5, f"Expected 5 valid players, got {stats['valid']}"
        assert len(errors) == 0, f"Expected no errors, got {errors}"
        
        # Save imported players
        data_manager.save_player_data(players)
        print("   ✅ Successfully imported 5 players")
        
    finally:
        Path(temp_csv.name).unlink()
    
    # Test 2: Bulk edit operations
    print("\n✏️ Testing Bulk Edit...")
    
    player_names = ['Alice', 'Bob', 'Charlie']
    updates = {
        'role_preferences': {'top': 4, 'jungle': 4}  # Set top and jungle to 4 for selected players
    }
    
    success_count, edit_errors = bulk_manager.bulk_edit_players(player_names, updates)
    
    print(f"   📊 Bulk Edit Results: {success_count} updated, {len(edit_errors)} errors")
    assert success_count == 3, f"Expected 3 players updated, got {success_count}"
    assert len(edit_errors) == 0, f"Expected no errors, got {edit_errors}"
    
    # Verify the changes
    updated_players = data_manager.load_player_data()
    alice = next(p for p in updated_players if p.name == 'Alice')
    assert alice.role_preferences['top'] == 4, "Alice's top preference should be updated to 4"
    assert alice.role_preferences['jungle'] == 4, "Alice's jungle preference should be updated to 4"
    
    print("   ✅ Successfully bulk edited 3 players")
    
    # Test 3: Export functionality
    print("\n📤 Testing Export...")
    
    # Test CSV export
    export_options = {'include_preferences': True, 'include_metadata': False}
    csv_export_file = bulk_manager.export_processor.export_to_csv(updated_players, export_options)
    
    # Verify CSV export
    with open(csv_export_file, 'r') as f:
        reader = csv.reader(f)
        rows = list(reader)
    
    assert len(rows) == 6, f"Expected 6 rows (header + 5 players), got {len(rows)}"  # Header + 5 players
    assert 'player_name' in rows[0], "CSV should have player_name column"
    
    print(f"   ✅ Successfully exported to CSV ({len(rows)-1} players)")
    
    # Test JSON export
    json_export_file = bulk_manager.export_processor.export_to_json(updated_players, export_options)
    
    # Verify JSON export
    with open(json_export_file, 'r') as f:
        json_data = json.load(f)
    
    assert len(json_data) == 5, f"Expected 5 players in JSON, got {len(json_data)}"
    assert 'player_name' in json_data[0], "JSON should have player_name field"
    
    print(f"   ✅ Successfully exported to JSON ({len(json_data)} players)")
    
    # Clean up export files
    Path(csv_export_file).unlink()
    Path(json_export_file).unlink()
    
    # Test 4: Backup and restore
    print("\n💾 Testing Backup & Restore...")
    
    # Create backup
    backup_file = bulk_manager.create_backup("integration_test_backup")
    assert Path(backup_file).exists(), "Backup file should exist"
    
    print("   ✅ Successfully created backup")
    
    # Modify data (add a new player)
    new_player = Player(
        name="TestPlayer",
        summoner_name="TestSummoner",
        role_preferences={"top": 3, "jungle": 3, "middle": 3, "bottom": 3, "support": 3}
    )
    
    all_players = data_manager.load_player_data()
    all_players.append(new_player)
    data_manager.save_player_data(all_players)
    
    # Verify we have 6 players now
    current_players = data_manager.load_player_data()
    assert len(current_players) == 6, f"Expected 6 players after adding one, got {len(current_players)}"
    
    # Restore backup
    success = bulk_manager.restore_backup(backup_file)
    assert success, "Backup restore should succeed"
    
    # Verify we're back to 5 players
    restored_players = data_manager.load_player_data()
    assert len(restored_players) == 5, f"Expected 5 players after restore, got {len(restored_players)}"
    
    print("   ✅ Successfully restored from backup")
    
    # Clean up backup file
    Path(backup_file).unlink()
    
    # Test 5: Template generation
    print("\n📄 Testing Template Generation...")
    
    templates = bulk_manager.get_bulk_operation_templates()
    
    assert 'csv' in templates, "Should have CSV template"
    assert 'json' in templates, "Should have JSON template"
    
    # Verify CSV template
    csv_template_file = templates['csv']
    with open(csv_template_file, 'r') as f:
        reader = csv.reader(f)
        template_rows = list(reader)
    
    assert len(template_rows) >= 2, "CSV template should have header and sample data"
    assert 'player_name' in template_rows[0], "CSV template should have player_name column"
    
    print("   ✅ Successfully generated templates")
    
    # Clean up template files
    for template_file in templates.values():
        Path(template_file).unlink()
    
    # Test 6: Audit logging
    print("\n📋 Testing Audit Logging...")
    
    # Get audit history
    audit_history = bulk_manager.audit_logger.get_audit_history(limit=100)
    
    # Should have audit entries from our operations
    assert len(audit_history) > 0, "Should have audit entries"
    
    # Check for different operation types
    operations = {entry['operation'] for entry in audit_history}
    expected_operations = {'IMPORT', 'BULK_EDIT', 'EXPORT', 'BACKUP_CREATE', 'BACKUP_RESTORE'}
    
    # We should have at least some of these operations
    assert len(operations.intersection(expected_operations)) > 0, f"Should have some expected operations, got {operations}"
    
    print(f"   ✅ Found {len(audit_history)} audit entries with operations: {operations}")
    
    # Test 7: Operation statistics
    print("\n📊 Testing Operation Statistics...")
    
    stats = bulk_manager.get_operation_statistics(days=1)
    
    assert stats['total_operations'] > 0, "Should have operation statistics"
    assert 'operations_by_type' in stats, "Should have operations by type"
    
    print(f"   ✅ Statistics: {stats['total_operations']} total operations")
    
    print("\n🎉 All bulk operations integration tests passed!")
    print(f"   📁 Test data directory: {temp_dir}")
    
    return True


if __name__ == "__main__":
    try:
        test_bulk_operations_integration()
        print("\n✅ Integration test completed successfully!")
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        raise