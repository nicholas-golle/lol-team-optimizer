"""
Comprehensive tests for the Bulk Operations Manager.

Tests cover:
- CSV/Excel import with data mapping and validation
- Bulk edit operations for multiple players
- Export functionality in multiple formats (CSV, JSON, PDF)
- Data migration tools for existing player databases
- Backup and restore functionality
- Audit logging for all player data modifications
- Data integrity validation
"""

import csv
import json
import pytest
import tempfile
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from lol_team_optimizer.bulk_operations_manager import (
    BulkOperationsManager, AuditLogger, DataValidator, 
    ImportProcessor, ExportProcessor
)
from lol_team_optimizer.models import Player
from lol_team_optimizer.data_manager import DataManager
from lol_team_optimizer.config import Config


class TestAuditLogger:
    """Test audit logging functionality."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        config = Mock(spec=Config)
        config.data_directory = tempfile.mkdtemp()
        return config
    
    @pytest.fixture
    def audit_logger(self, config):
        """Create audit logger instance."""
        return AuditLogger(config)
    
    def test_audit_logger_initialization(self, audit_logger):
        """Test audit logger database initialization."""
        assert audit_logger.audit_db_path.exists()
        
        # Verify database structure
        import sqlite3
        with sqlite3.connect(audit_logger.audit_db_path) as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            assert 'audit_log' in tables
    
    def test_log_operation(self, audit_logger):
        """Test logging audit operations."""
        # Log an operation
        audit_logger.log_operation(
            operation="CREATE",
            entity_type="Player",
            entity_id="test_player",
            new_data={"name": "Test Player"},
            user_id="test_user",
            details="Test operation"
        )
        
        # Verify log entry
        history = audit_logger.get_audit_history(limit=1)
        assert len(history) == 1
        
        entry = history[0]
        assert entry['operation'] == "CREATE"
        assert entry['entity_type'] == "Player"
        assert entry['entity_id'] == "test_player"
        assert entry['user_id'] == "test_user"
        assert entry['details'] == "Test operation"
    
    def test_get_audit_history_with_filters(self, audit_logger):
        """Test retrieving audit history with filters."""
        # Log multiple operations
        operations = [
            ("CREATE", "Player", "player1"),
            ("UPDATE", "Player", "player1"),
            ("DELETE", "Player", "player2"),
            ("CREATE", "Team", "team1")
        ]
        
        for op, entity_type, entity_id in operations:
            audit_logger.log_operation(op, entity_type, entity_id)
        
        # Test entity type filter
        player_history = audit_logger.get_audit_history(entity_type="Player")
        assert len(player_history) == 3
        
        # Test entity ID filter
        player1_history = audit_logger.get_audit_history(entity_id="player1")
        assert len(player1_history) == 2
        
        # Test date filter
        start_date = datetime.now() - timedelta(minutes=1)
        recent_history = audit_logger.get_audit_history(start_date=start_date)
        assert len(recent_history) == 4


class TestDataValidator:
    """Test data validation functionality."""
    
    @pytest.fixture
    def validator(self):
        """Create data validator instance."""
        return DataValidator()
    
    def test_validate_valid_player_data(self, validator):
        """Test validation of valid player data."""
        valid_data = {
            'player_name': 'Test Player',
            'summoner_name': 'TestSummoner',
            'riot_tag': 'NA1',
            'top_pref': 5,
            'jungle_pref': 3,
            'middle_pref': 2,
            'bottom_pref': 1,
            'support_pref': 4
        }
        
        is_valid, errors = validator.validate_player_data(valid_data)
        assert is_valid
        assert len(errors) == 0
    
    def test_validate_invalid_player_name(self, validator):
        """Test validation of invalid player names."""
        invalid_names = [
            '',  # Empty
            'A',  # Too short
            'A' * 51,  # Too long
            'Player<Name>',  # Invalid characters
        ]
        
        for name in invalid_names:
            data = {'player_name': name, 'summoner_name': 'ValidSummoner'}
            is_valid, errors = validator.validate_player_data(data)
            assert not is_valid
            assert any('player name' in error.lower() for error in errors)
    
    def test_validate_invalid_summoner_name(self, validator):
        """Test validation of invalid summoner names."""
        invalid_summoners = [
            '',  # Empty
            'AB',  # Too short
            'A' * 17,  # Too long
            'Invalid@Name',  # Invalid characters
        ]
        
        for summoner in invalid_summoners:
            data = {'player_name': 'ValidPlayer', 'summoner_name': summoner}
            is_valid, errors = validator.validate_player_data(data)
            assert not is_valid
            assert any('summoner name' in error.lower() for error in errors)
    
    def test_validate_invalid_role_preferences(self, validator):
        """Test validation of invalid role preferences."""
        data = {
            'player_name': 'Test Player',
            'summoner_name': 'TestSummoner',
            'top_pref': 6,  # Invalid: > 5
            'jungle_pref': 0,  # Invalid: < 1
            'middle_pref': 'invalid',  # Invalid: not a number
        }
        
        is_valid, errors = validator.validate_player_data(data)
        assert not is_valid
        assert len(errors) >= 3  # At least 3 preference errors


class TestImportProcessor:
    """Test import processing functionality."""
    
    @pytest.fixture
    def mock_data_manager(self):
        """Create mock data manager."""
        data_manager = Mock(spec=DataManager)
        data_manager.load_player_data.return_value = []
        return data_manager
    
    @pytest.fixture
    def mock_audit_logger(self):
        """Create mock audit logger."""
        return Mock(spec=AuditLogger)
    
    @pytest.fixture
    def import_processor(self, mock_data_manager, mock_audit_logger):
        """Create import processor instance."""
        return ImportProcessor(mock_data_manager, mock_audit_logger)
    
    def test_process_csv_import_valid_data(self, import_processor):
        """Test CSV import with valid data."""
        # Create test CSV file
        csv_data = [
            ['player_name', 'summoner_name', 'top_pref', 'jungle_pref'],
            ['Player One', 'SummonerOne', '5', '3'],
            ['Player Two', 'SummonerTwo', '2', '4']
        ]
        
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        writer = csv.writer(temp_file)
        writer.writerows(csv_data)
        temp_file.close()
        
        try:
            field_mapping = {
                'player_name': 'player_name',
                'summoner_name': 'summoner_name',
                'top_pref': 'top_pref',
                'jungle_pref': 'jungle_pref'
            }
            
            options = {'has_header': True, 'delimiter': ','}
            
            players, errors, stats = import_processor.process_csv_import(
                temp_file.name, field_mapping, options
            )
            
            assert len(players) == 2
            assert len(errors) == 0
            assert stats['valid'] == 2
            assert stats['invalid'] == 0
            
            # Verify player data
            assert players[0].name == 'Player One'
            assert players[0].summoner_name == 'SummonerOne'
            assert players[0].role_preferences['top'] == 5
            assert players[0].role_preferences['jungle'] == 3
            
        finally:
            Path(temp_file.name).unlink()
    
    def test_process_csv_import_invalid_data(self, import_processor):
        """Test CSV import with invalid data."""
        # Create test CSV with invalid data
        csv_data = [
            ['player_name', 'summoner_name', 'top_pref'],
            ['', 'SummonerOne', '5'],  # Empty name
            ['Player Two', 'AB', '6'],  # Invalid summoner and preference
        ]
        
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        writer = csv.writer(temp_file)
        writer.writerows(csv_data)
        temp_file.close()
        
        try:
            field_mapping = {
                'player_name': 'player_name',
                'summoner_name': 'summoner_name',
                'top_pref': 'top_pref'
            }
            
            options = {'has_header': True}
            
            players, errors, stats = import_processor.process_csv_import(
                temp_file.name, field_mapping, options
            )
            
            assert len(players) == 0
            assert len(errors) == 2
            assert stats['valid'] == 0
            assert stats['invalid'] == 2
            
        finally:
            Path(temp_file.name).unlink()
    
    def test_process_json_import_valid_data(self, import_processor):
        """Test JSON import with valid data."""
        json_data = [
            {
                'player_name': 'Player One',
                'summoner_name': 'SummonerOne',
                'top_pref': 5,
                'jungle_pref': 3
            },
            {
                'player_name': 'Player Two',
                'summoner_name': 'SummonerTwo',
                'top_pref': 2,
                'jungle_pref': 4
            }
        ]
        
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(json_data, temp_file)
        temp_file.close()
        
        try:
            players, errors, stats = import_processor.process_json_import(
                temp_file.name, {}
            )
            
            assert len(players) == 2
            assert len(errors) == 0
            assert stats['valid'] == 2
            
        finally:
            Path(temp_file.name).unlink()
    
    @patch('pandas.read_excel')
    def test_process_excel_import(self, mock_read_excel, import_processor):
        """Test Excel import functionality."""
        # Mock pandas DataFrame
        import pandas as pd
        mock_df = pd.DataFrame({
            'player_name': ['Player One', 'Player Two'],
            'summoner_name': ['SummonerOne', 'SummonerTwo'],
            'top_pref': [5, 2],
            'jungle_pref': [3, 4]
        })
        mock_read_excel.return_value = mock_df
        
        field_mapping = {
            'player_name': 'player_name',
            'summoner_name': 'summoner_name',
            'top_pref': 'top_pref',
            'jungle_pref': 'jungle_pref'
        }
        
        players, errors, stats = import_processor.process_excel_import(
            'dummy_file.xlsx', field_mapping, {}
        )
        
        assert len(players) == 2
        assert len(errors) == 0
        assert stats['valid'] == 2


class TestExportProcessor:
    """Test export processing functionality."""
    
    @pytest.fixture
    def mock_data_manager(self):
        """Create mock data manager."""
        return Mock(spec=DataManager)
    
    @pytest.fixture
    def mock_audit_logger(self):
        """Create mock audit logger."""
        return Mock(spec=AuditLogger)
    
    @pytest.fixture
    def export_processor(self, mock_data_manager, mock_audit_logger):
        """Create export processor instance."""
        return ExportProcessor(mock_data_manager, mock_audit_logger)
    
    @pytest.fixture
    def sample_players(self):
        """Create sample players for testing."""
        return [
            Player(
                name="Player One",
                summoner_name="SummonerOne",
                puuid="puuid1",
                role_preferences={"top": 5, "jungle": 3, "middle": 2, "bottom": 1, "support": 4}
            ),
            Player(
                name="Player Two",
                summoner_name="SummonerTwo",
                puuid="puuid2",
                role_preferences={"top": 2, "jungle": 4, "middle": 5, "bottom": 3, "support": 1}
            )
        ]
    
    def test_export_to_csv(self, export_processor, sample_players):
        """Test CSV export functionality."""
        options = {'include_preferences': True, 'delimiter': ','}
        
        csv_file = export_processor.export_to_csv(sample_players, options)
        
        try:
            # Verify CSV content
            with open(csv_file, 'r') as f:
                reader = csv.reader(f)
                rows = list(reader)
            
            # Check header
            expected_header = ["player_name", "summoner_name", "puuid", 
                             "top_pref", "jungle_pref", "middle_pref", "bottom_pref", "support_pref"]
            assert rows[0] == expected_header
            
            # Check data rows
            assert len(rows) == 3  # Header + 2 players
            assert rows[1][0] == "Player One"
            assert rows[1][1] == "SummonerOne"
            assert rows[1][3] == "5"  # top_pref
            
        finally:
            Path(csv_file).unlink()
    
    def test_export_to_json(self, export_processor, sample_players):
        """Test JSON export functionality."""
        options = {'include_preferences': True, 'include_metadata': False}
        
        json_file = export_processor.export_to_json(sample_players, options)
        
        try:
            # Verify JSON content
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            assert len(data) == 2
            assert data[0]['player_name'] == "Player One"
            assert data[0]['summoner_name'] == "SummonerOne"
            assert 'role_preferences' in data[0]
            assert data[0]['role_preferences']['top'] == 5
            
        finally:
            Path(json_file).unlink()
    
    @patch('pandas.DataFrame.to_excel')
    @patch('pandas.ExcelWriter')
    def test_export_to_excel(self, mock_excel_writer, mock_to_excel, export_processor, sample_players):
        """Test Excel export functionality."""
        # Mock Excel writer
        mock_writer_instance = MagicMock()
        mock_excel_writer.return_value.__enter__.return_value = mock_writer_instance
        
        options = {'include_preferences': True, 'include_summary': False}
        
        excel_file = export_processor.export_to_excel(sample_players, options)
        
        # Verify Excel writer was called
        mock_excel_writer.assert_called_once()
        mock_to_excel.assert_called()
        
        # Clean up
        Path(excel_file).unlink(missing_ok=True)
    
    @patch('reportlab.platypus.SimpleDocTemplate')
    def test_export_to_pdf(self, mock_doc, export_processor, sample_players):
        """Test PDF export functionality."""
        # Mock PDF document
        mock_doc_instance = MagicMock()
        mock_doc.return_value = mock_doc_instance
        
        options = {}
        
        pdf_file = export_processor.export_to_pdf(sample_players, options)
        
        # Verify PDF document was created
        mock_doc.assert_called_once()
        mock_doc_instance.build.assert_called_once()
        
        # Clean up
        Path(pdf_file).unlink(missing_ok=True)


class TestBulkOperationsManager:
    """Test main bulk operations manager functionality."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock(spec=Config)
        config.data_directory = tempfile.mkdtemp()
        config.player_data_file = "players.json"
        return config
    
    @pytest.fixture
    def mock_data_manager(self):
        """Create mock data manager."""
        data_manager = Mock(spec=DataManager)
        data_manager.load_player_data.return_value = []
        return data_manager
    
    @pytest.fixture
    def bulk_manager(self, mock_data_manager, mock_config):
        """Create bulk operations manager instance."""
        return BulkOperationsManager(mock_data_manager, mock_config)
    
    @pytest.fixture
    def sample_players(self):
        """Create sample players for testing."""
        return [
            Player(
                name="Player One",
                summoner_name="SummonerOne",
                role_preferences={"top": 5, "jungle": 3, "middle": 2, "bottom": 1, "support": 4}
            ),
            Player(
                name="Player Two",
                summoner_name="SummonerTwo",
                role_preferences={"top": 2, "jungle": 4, "middle": 5, "bottom": 3, "support": 1}
            )
        ]
    
    def test_bulk_edit_players(self, bulk_manager, sample_players):
        """Test bulk edit operations."""
        # Mock data manager to return sample players
        bulk_manager.data_manager.load_player_data.return_value = sample_players
        
        # Define updates
        updates = {
            'role_preferences': {'top': 4, 'jungle': 4},
            'summoner_name': 'UpdatedSummoner'
        }
        
        player_names = ["Player One", "Player Two"]
        
        success_count, errors = bulk_manager.bulk_edit_players(player_names, updates)
        
        assert success_count == 2
        assert len(errors) == 0
        
        # Verify data manager save was called
        bulk_manager.data_manager.save_player_data.assert_called_once()
    
    def test_bulk_edit_nonexistent_player(self, bulk_manager, sample_players):
        """Test bulk edit with nonexistent player."""
        bulk_manager.data_manager.load_player_data.return_value = sample_players
        
        updates = {'role_preferences': {'top': 4}}
        player_names = ["Player One", "Nonexistent Player"]
        
        success_count, errors = bulk_manager.bulk_edit_players(player_names, updates)
        
        assert success_count == 1
        assert len(errors) == 1
        assert "not found" in errors[0]
    
    def test_create_backup(self, bulk_manager):
        """Test backup creation."""
        # Create dummy player data file
        player_file = Path(bulk_manager.config.data_directory) / bulk_manager.config.player_data_file
        player_file.write_text('{"test": "data"}')
        
        backup_file = bulk_manager.create_backup("test_backup")
        
        try:
            # Verify backup file exists
            assert Path(backup_file).exists()
            
            # Verify backup contents
            with zipfile.ZipFile(backup_file, 'r') as zf:
                assert "players.json" in zf.namelist()
                assert "metadata.json" in zf.namelist()
                
                # Check metadata
                metadata = json.loads(zf.read("metadata.json"))
                assert metadata['backup_name'] == "test_backup"
                assert 'backup_date' in metadata
                
        finally:
            Path(backup_file).unlink(missing_ok=True)
    
    def test_restore_backup(self, bulk_manager):
        """Test backup restoration."""
        # Create a test backup
        backup_file = bulk_manager.create_backup("test_restore")
        
        try:
            # Restore the backup
            success = bulk_manager.restore_backup(backup_file)
            assert success
            
        finally:
            Path(backup_file).unlink(missing_ok=True)
    
    def test_migrate_from_legacy_csv(self, bulk_manager):
        """Test migration from legacy CSV format."""
        # Create legacy CSV file
        legacy_data = [
            ['Name', 'Summoner', 'Top', 'Jungle', 'Mid', 'ADC', 'Support'],
            ['Player One', 'SummonerOne', '5', '3', '2', '1', '4'],
            ['Player Two', 'SummonerTwo', '2', '4', '5', '3', '1']
        ]
        
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        writer = csv.writer(temp_file)
        writer.writerows(legacy_data)
        temp_file.close()
        
        try:
            # Mock existing players
            bulk_manager.data_manager.load_player_data.return_value = []
            
            migrated_count, errors = bulk_manager.migrate_from_legacy_format(
                temp_file.name, "csv"
            )
            
            assert migrated_count == 2
            assert len(errors) == 0
            
            # Verify save was called
            bulk_manager.data_manager.save_player_data.assert_called_once()
            
        finally:
            Path(temp_file.name).unlink()
    
    def test_get_bulk_operation_templates(self, bulk_manager):
        """Test template generation."""
        templates = bulk_manager.get_bulk_operation_templates()
        
        assert 'csv' in templates
        assert 'json' in templates
        
        # Verify CSV template
        csv_file = templates['csv']
        try:
            with open(csv_file, 'r') as f:
                reader = csv.reader(f)
                rows = list(reader)
            
            # Check header
            assert 'player_name' in rows[0]
            assert 'summoner_name' in rows[0]
            assert len(rows) > 1  # Has data rows
            
        finally:
            Path(csv_file).unlink()
        
        # Verify JSON template
        json_file = templates['json']
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            assert isinstance(data, list)
            assert len(data) > 0
            assert 'player_name' in data[0]
            
        finally:
            Path(json_file).unlink()
    
    def test_get_operation_statistics(self, bulk_manager):
        """Test operation statistics retrieval."""
        # Mock audit history
        mock_history = [
            {
                'operation': 'IMPORT',
                'timestamp': datetime.now().isoformat(),
                'entity_type': 'Player'
            },
            {
                'operation': 'EXPORT',
                'timestamp': (datetime.now() - timedelta(days=1)).isoformat(),
                'entity_type': 'Player'
            }
        ]
        
        # Mock the audit logger method
        with patch.object(bulk_manager.audit_logger, 'get_audit_history', return_value=mock_history):
            stats = bulk_manager.get_operation_statistics(days=30)
            
            assert stats['total_operations'] == 2
            assert 'IMPORT' in stats['operations_by_type']
            assert 'EXPORT' in stats['operations_by_type']
            assert len(stats['recent_operations']) == 2


class TestDataIntegrity:
    """Test data integrity during bulk operations."""
    
    @pytest.fixture
    def bulk_manager_with_real_data(self):
        """Create bulk manager with real data for integrity testing."""
        config = Mock(spec=Config)
        config.data_directory = tempfile.mkdtemp()
        config.player_data_file = "players.json"
        
        data_manager = Mock(spec=DataManager)
        return BulkOperationsManager(data_manager, config)
    
    def test_import_data_integrity(self, bulk_manager_with_real_data):
        """Test data integrity during import operations."""
        # Create test data with potential integrity issues
        csv_data = [
            ['player_name', 'summoner_name', 'top_pref'],
            ['Player One', 'SummonerOne', '5'],
            ['Player One', 'DuplicateName', '3'],  # Duplicate name
            ['Player Two', 'SummonerTwo', '10'],  # Invalid preference
        ]
        
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        writer = csv.writer(temp_file)
        writer.writerows(csv_data)
        temp_file.close()
        
        try:
            field_mapping = {
                'player_name': 'player_name',
                'summoner_name': 'summoner_name',
                'top_pref': 'top_pref'
            }
            
            options = {'has_header': True, 'allow_duplicates': False}
            
            # Mock existing players
            bulk_manager_with_real_data.data_manager.load_player_data.return_value = []
            
            players, errors, stats = bulk_manager_with_real_data.import_processor.process_csv_import(
                temp_file.name, field_mapping, options
            )
            
            # Should have caught integrity issues
            assert stats['duplicates'] > 0 or stats['invalid'] > 0
            assert len(errors) > 0
            
        finally:
            Path(temp_file.name).unlink()
    
    def test_backup_restore_integrity(self, bulk_manager_with_real_data):
        """Test data integrity during backup and restore operations."""
        # Create original data
        original_players = [
            Player(name="Player One", summoner_name="SummonerOne"),
            Player(name="Player Two", summoner_name="SummonerTwo")
        ]
        
        # Mock data manager
        bulk_manager_with_real_data.data_manager.load_player_data.return_value = original_players
        
        # Create player data file
        player_file = Path(bulk_manager_with_real_data.config.data_directory) / bulk_manager_with_real_data.config.player_data_file
        player_file.write_text(json.dumps([
            {"name": "Player One", "summoner_name": "SummonerOne"},
            {"name": "Player Two", "summoner_name": "SummonerTwo"}
        ]))
        
        # Create backup
        backup_file = bulk_manager_with_real_data.create_backup("integrity_test")
        
        try:
            # Modify original data
            player_file.write_text(json.dumps([
                {"name": "Modified Player", "summoner_name": "ModifiedSummoner"}
            ]))
            
            # Restore backup
            success = bulk_manager_with_real_data.restore_backup(backup_file)
            assert success
            
            # Verify data integrity
            restored_data = json.loads(player_file.read_text())
            assert len(restored_data) == 2
            assert restored_data[0]["name"] == "Player One"
            
        finally:
            Path(backup_file).unlink(missing_ok=True)


if __name__ == "__main__":
    pytest.main([__file__])