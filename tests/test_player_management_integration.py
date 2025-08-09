"""
Integration tests for the comprehensive player management functionality.

Tests all CRUD operations, bulk import/export, validation, and UI interactions.
"""

import pytest
import tempfile
import csv
import json
import pandas as pd
import gradio as gr
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from lol_team_optimizer.models import Player
from lol_team_optimizer.core_engine import CoreEngine
from lol_team_optimizer.data_manager import DataManager
from lol_team_optimizer.player_management_tab import (
    PlayerManagementTab, 
    PlayerValidator, 
    BulkImportProcessor
)
from lol_team_optimizer.gradio_components import PlayerManagementComponents


class TestPlayerValidator:
    """Test player validation functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = PlayerValidator()
    
    def test_validate_player_name_valid(self):
        """Test valid player name validation."""
        valid, message = self.validator.validate_player_name("TestPlayer")
        assert valid is True
        assert "Valid player name" in message
    
    def test_validate_player_name_empty(self):
        """Test empty player name validation."""
        valid, message = self.validator.validate_player_name("")
        assert valid is False
        assert "required" in message
    
    def test_validate_player_name_too_short(self):
        """Test too short player name validation."""
        valid, message = self.validator.validate_player_name("A")
        assert valid is False
        assert "at least 2 characters" in message
    
    def test_validate_player_name_too_long(self):
        """Test too long player name validation."""
        long_name = "A" * 51
        valid, message = self.validator.validate_player_name(long_name)
        assert valid is False
        assert "less than 50 characters" in message
    
    def test_validate_player_name_invalid_chars(self):
        """Test player name with invalid characters."""
        valid, message = self.validator.validate_player_name("Test<Player>")
        assert valid is False
        assert "invalid characters" in message
    
    def test_validate_summoner_name_valid(self):
        """Test valid summoner name validation."""
        valid, message = self.validator.validate_summoner_name("TestSummoner")
        assert valid is True
        assert "Valid summoner name" in message
    
    def test_validate_summoner_name_empty(self):
        """Test empty summoner name validation."""
        valid, message = self.validator.validate_summoner_name("")
        assert valid is False
        assert "required" in message
    
    def test_validate_summoner_name_too_short(self):
        """Test too short summoner name validation."""
        valid, message = self.validator.validate_summoner_name("AB")
        assert valid is False
        assert "at least 3 characters" in message
    
    def test_validate_summoner_name_too_long(self):
        """Test too long summoner name validation."""
        long_name = "A" * 17
        valid, message = self.validator.validate_summoner_name(long_name)
        assert valid is False
        assert "less than 16 characters" in message
    
    def test_validate_riot_tag_valid(self):
        """Test valid Riot tag validation."""
        valid, message = self.validator.validate_riot_tag("NA1")
        assert valid is True
        assert "Valid riot tag" in message
    
    def test_validate_riot_tag_empty(self):
        """Test empty Riot tag validation."""
        valid, message = self.validator.validate_riot_tag("")
        assert valid is False
        assert "required" in message
    
    def test_validate_riot_tag_invalid_chars(self):
        """Test Riot tag with invalid characters."""
        valid, message = self.validator.validate_riot_tag("NA-1")
        assert valid is False
        assert "letters and numbers" in message
    
    def test_validate_role_preferences_valid(self):
        """Test valid role preferences validation."""
        prefs = {"top": 5, "jungle": 3, "middle": 2, "bottom": 1, "support": 4}
        valid, message = self.validator.validate_role_preferences(prefs)
        assert valid is True
        assert "Valid role preferences" in message
    
    def test_validate_role_preferences_invalid_role(self):
        """Test role preferences with invalid role."""
        prefs = {"invalid_role": 3}
        valid, message = self.validator.validate_role_preferences(prefs)
        assert valid is False
        assert "Invalid role" in message
    
    def test_validate_role_preferences_invalid_value(self):
        """Test role preferences with invalid value."""
        prefs = {"top": 6}
        valid, message = self.validator.validate_role_preferences(prefs)
        assert valid is False
        assert "between 1 and 5" in message


class TestBulkImportProcessor:
    """Test bulk import processing functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_core_engine = Mock(spec=CoreEngine)
        self.processor = BulkImportProcessor(self.mock_core_engine)
    
    def test_process_csv_file_valid(self):
        """Test processing valid CSV file."""
        # Create temporary CSV file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.writer(f)
            writer.writerow(["player_name", "summoner_name", "riot_tag", "region"])
            writer.writerow(["Player1", "Summoner1", "NA1", "na1"])
            writer.writerow(["Player2", "Summoner2", "EUW", "euw1"])
            temp_path = f.name
        
        try:
            field_mapping = {
                "player_name": "player_name",
                "summoner_name": "summoner_name",
                "riot_tag": "riot_tag",
                "region": "region"
            }
            
            options = {"delimiter": ",", "encoding": "utf-8", "has_header": True}
            
            players, errors = self.processor.process_csv_file(temp_path, field_mapping, options)
            
            assert len(players) == 2
            assert len(errors) == 0
            assert players[0].name == "Player1"
            assert players[0].summoner_name == "Summoner1"
            assert players[1].name == "Player2"
            assert players[1].summoner_name == "Summoner2"
            
        finally:
            Path(temp_path).unlink()
    
    def test_process_csv_file_missing_required_field(self):
        """Test processing CSV file with missing required field."""
        # Create temporary CSV file without summoner_name
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.writer(f)
            writer.writerow(["player_name", "region"])
            writer.writerow(["Player1", "na1"])
            temp_path = f.name
        
        try:
            field_mapping = {
                "player_name": "player_name",
                "summoner_name": "Not Mapped"
            }
            
            options = {"delimiter": ",", "encoding": "utf-8", "has_header": True}
            
            players, errors = self.processor.process_csv_file(temp_path, field_mapping, options)
            
            assert len(players) == 0
            assert len(errors) == 1
            assert "Summoner name is required" in errors[0]
            
        finally:
            Path(temp_path).unlink()
    
    def test_process_json_file_valid(self):
        """Test processing valid JSON file."""
        # Create temporary JSON file
        data = [
            {
                "player_name": "Player1",
                "summoner_name": "Summoner1",
                "riot_tag": "NA1",
                "region": "na1",
                "top_pref": 5,
                "jungle_pref": 3
            },
            {
                "player_name": "Player2", 
                "summoner_name": "Summoner2",
                "riot_tag": "EUW",
                "region": "euw1"
            }
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data, f)
            temp_path = f.name
        
        try:
            players, errors = self.processor.process_json_file(temp_path)
            
            assert len(players) == 2
            assert len(errors) == 0
            assert players[0].name == "Player1"
            assert players[0].role_preferences["top"] == 5
            assert players[0].role_preferences["jungle"] == 3
            assert players[1].name == "Player2"
            assert players[1].role_preferences["top"] == 3  # Default
            
        finally:
            Path(temp_path).unlink()
    
    def test_process_json_file_invalid_format(self):
        """Test processing JSON file with invalid format."""
        # Create temporary JSON file with invalid format (not a list)
        data = {"player_name": "Player1", "summoner_name": "Summoner1"}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data, f)
            temp_path = f.name
        
        try:
            players, errors = self.processor.process_json_file(temp_path)
            
            assert len(players) == 0
            assert len(errors) == 1
            assert "must contain a list" in errors[0]
            
        finally:
            Path(temp_path).unlink()
    
    def test_generate_csv_template(self):
        """Test CSV template generation."""
        template_path = self.processor.generate_csv_template()
        
        try:
            assert Path(template_path).exists()
            
            # Verify template content
            with open(template_path, 'r') as f:
                reader = csv.reader(f)
                headers = next(reader)
                
                expected_headers = [
                    "player_name", "summoner_name", "riot_tag", "region",
                    "top_pref", "jungle_pref", "middle_pref", "bottom_pref", "support_pref"
                ]
                
                assert headers == expected_headers
                
                # Check sample data
                sample_row = next(reader)
                assert len(sample_row) == len(expected_headers)
                assert sample_row[0] == "Player One"
                
        finally:
            Path(template_path).unlink()


class TestPlayerManagementTab:
    """Test player management tab functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_core_engine = Mock(spec=CoreEngine)
        self.mock_data_manager = Mock(spec=DataManager)
        self.mock_core_engine.data_manager = self.mock_data_manager
        
        self.tab = PlayerManagementTab(self.mock_core_engine)
    
    def test_initialization(self):
        """Test player management tab initialization."""
        assert self.tab.core_engine == self.mock_core_engine
        assert isinstance(self.tab.validator, PlayerValidator)
        assert isinstance(self.tab.bulk_processor, BulkImportProcessor)
        assert self.tab.current_players == []
        assert self.tab.current_page == 1
        assert self.tab.page_size == 25
    
    def test_export_csv(self):
        """Test CSV export functionality."""
        # Create test players
        players = [
            Player(
                name="Player1",
                summoner_name="Summoner1",
                puuid="test_puuid_1",
                role_preferences={"top": 5, "jungle": 3, "middle": 2, "bottom": 1, "support": 4}
            ),
            Player(
                name="Player2",
                summoner_name="Summoner2", 
                puuid="test_puuid_2",
                role_preferences={"top": 2, "jungle": 4, "middle": 5, "bottom": 3, "support": 1}
            )
        ]
        
        # Test export with preferences
        csv_path = self.tab._export_csv(players, include_prefs=True)
        
        try:
            assert Path(csv_path).exists()
            
            # Verify CSV content
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                
                assert len(rows) == 2
                assert rows[0]["player_name"] == "Player1"
                assert rows[0]["summoner_name"] == "Summoner1"
                assert rows[0]["top_pref"] == "5"
                assert rows[1]["player_name"] == "Player2"
                assert rows[1]["jungle_pref"] == "4"
                
        finally:
            Path(csv_path).unlink()
    
    def test_export_json(self):
        """Test JSON export functionality."""
        # Create test players
        players = [
            Player(
                name="Player1",
                summoner_name="Summoner1",
                puuid="test_puuid_1",
                role_preferences={"top": 5, "jungle": 3, "middle": 2, "bottom": 1, "support": 4}
            )
        ]
        
        # Test export with preferences
        json_path = self.tab._export_json(players, include_prefs=True)
        
        try:
            assert Path(json_path).exists()
            
            # Verify JSON content
            with open(json_path, 'r') as f:
                data = json.load(f)
                
                assert len(data) == 1
                assert data[0]["player_name"] == "Player1"
                assert data[0]["summoner_name"] == "Summoner1"
                assert "role_preferences" in data[0]
                assert data[0]["role_preferences"]["top"] == 5
                
        finally:
            Path(json_path).unlink()


class TestPlayerManagementComponents:
    """Test player management UI components."""
    
    def test_create_advanced_player_form(self):
        """Test advanced player form creation."""
        form_components = PlayerManagementComponents.create_advanced_player_form()
        
        # Check required components exist
        assert "player_name" in form_components
        assert "summoner_name" in form_components
        assert "riot_tag" in form_components
        assert "region" in form_components
        assert "role_preferences" in form_components
        assert "validation_message" in form_components
        assert "submit_btn" in form_components
        
        # Check role preferences
        role_prefs = form_components["role_preferences"]
        expected_roles = ["top", "jungle", "middle", "bottom", "support"]
        
        for role in expected_roles:
            assert role in role_prefs
    
    def test_create_interactive_player_table(self):
        """Test interactive player table creation."""
        # Create test players
        players = [
            Player(name="Player1", summoner_name="Summoner1", puuid="test1"),
            Player(name="Player2", summoner_name="Summoner2", puuid="test2")
        ]
        
        # Create components within Gradio context
        with gr.Blocks() as demo:
            table_components = PlayerManagementComponents.create_interactive_player_table(players)
        
        # Check required components exist
        assert "search_box" in table_components
        assert "region_filter" in table_components
        assert "status_filter" in table_components
        assert "sort_by" in table_components
        assert "sort_order" in table_components
        assert "page_size" in table_components
        assert "player_table" in table_components
        assert "prev_page" in table_components
        assert "next_page" in table_components
        assert "bulk_delete" in table_components
    
    def test_create_bulk_import_interface(self):
        """Test bulk import interface creation."""
        # Create components within Gradio context
        with gr.Blocks() as demo:
            import_components = PlayerManagementComponents.create_bulk_import_interface()
        
        # Check required components exist
        assert "file_upload" in import_components
        assert "format_selection" in import_components
        assert "encoding" in import_components
        assert "field_mapping" in import_components
        assert "skip_duplicates" in import_components
        assert "validate_api" in import_components
        assert "preview_btn" in import_components
        assert "import_btn" in import_components
        assert "import_progress" in import_components
        assert "import_results" in import_components
        
        # Check field mapping contains required fields
        field_mapping = import_components["field_mapping"]
        assert "player_name" in field_mapping
        assert "summoner_name" in field_mapping


class TestPlayerManagementIntegration:
    """Integration tests for complete player management workflow."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary directory for test data
        self.temp_dir = tempfile.mkdtemp()
        
        # Mock configuration
        self.mock_config = Mock()
        self.mock_config.data_directory = self.temp_dir
        self.mock_config.cache_directory = self.temp_dir
        self.mock_config.player_data_file = "players.json"
        self.mock_config.player_data_cache_hours = 1
        
        # Create data manager with temp directory
        self.data_manager = DataManager(self.mock_config)
        
        # Mock core engine
        self.mock_core_engine = Mock(spec=CoreEngine)
        self.mock_core_engine.data_manager = self.data_manager
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_complete_player_crud_workflow(self):
        """Test complete CRUD workflow for players."""
        # Test adding players
        player1 = Player(
            name="TestPlayer1",
            summoner_name="TestSummoner1",
            puuid="",
            role_preferences={"top": 5, "jungle": 3, "middle": 2, "bottom": 1, "support": 4}
        )
        
        player2 = Player(
            name="TestPlayer2",
            summoner_name="TestSummoner2",
            puuid="",
            role_preferences={"top": 2, "jungle": 4, "middle": 5, "bottom": 3, "support": 1}
        )
        
        # Add players
        success1 = self.data_manager.add_player(player1)
        success2 = self.data_manager.add_player(player2)
        
        assert success1 is True
        assert success2 is True
        
        # Test duplicate prevention
        duplicate_success = self.data_manager.add_player(player1)
        assert duplicate_success is False
        
        # Test loading players
        loaded_players = self.data_manager.load_player_data()
        assert len(loaded_players) == 2
        
        player_names = [p.name for p in loaded_players]
        assert "TestPlayer1" in player_names
        assert "TestPlayer2" in player_names
        
        # Test getting specific player
        retrieved_player = self.data_manager.get_player_by_name("TestPlayer1")
        assert retrieved_player is not None
        assert retrieved_player.name == "TestPlayer1"
        assert retrieved_player.summoner_name == "TestSummoner1"
        assert retrieved_player.role_preferences["top"] == 5
        
        # Test updating player
        retrieved_player.role_preferences["top"] = 4
        self.data_manager.update_player(retrieved_player)
        
        updated_player = self.data_manager.get_player_by_name("TestPlayer1")
        assert updated_player.role_preferences["top"] == 4
        
        # Test deleting player
        delete_success = self.data_manager.delete_player("TestPlayer1")
        assert delete_success is True
        
        remaining_players = self.data_manager.load_player_data()
        assert len(remaining_players) == 1
        assert remaining_players[0].name == "TestPlayer2"
        
        # Test deleting non-existent player
        delete_fail = self.data_manager.delete_player("NonExistentPlayer")
        assert delete_fail is False
    
    def test_bulk_import_export_workflow(self):
        """Test complete bulk import/export workflow."""
        # Create test data
        test_players = [
            {
                "player_name": "BulkPlayer1",
                "summoner_name": "BulkSummoner1",
                "riot_tag": "NA1",
                "region": "na1",
                "top_pref": 5,
                "jungle_pref": 3,
                "middle_pref": 2,
                "bottom_pref": 1,
                "support_pref": 4
            },
            {
                "player_name": "BulkPlayer2",
                "summoner_name": "BulkSummoner2",
                "riot_tag": "EUW",
                "region": "euw1",
                "top_pref": 2,
                "jungle_pref": 4,
                "middle_pref": 5,
                "bottom_pref": 3,
                "support_pref": 1
            }
        ]
        
        # Create temporary JSON file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_players, f)
            json_path = f.name
        
        try:
            # Test bulk import
            processor = BulkImportProcessor(self.mock_core_engine)
            players, errors = processor.process_json_file(json_path)
            
            assert len(players) == 2
            assert len(errors) == 0
            
            # Add players to data manager
            for player in players:
                self.data_manager.add_player(player)
            
            # Verify players were added
            loaded_players = self.data_manager.load_player_data()
            assert len(loaded_players) == 2
            
            # Test export
            tab = PlayerManagementTab(self.mock_core_engine)
            
            # Test CSV export
            csv_path = tab._export_csv(loaded_players, include_prefs=True)
            assert Path(csv_path).exists()
            
            # Verify CSV content
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                csv_rows = list(reader)
                
                assert len(csv_rows) == 2
                assert csv_rows[0]["player_name"] == "BulkPlayer1"
                assert csv_rows[0]["top_pref"] == "5"
                assert csv_rows[1]["player_name"] == "BulkPlayer2"
                assert csv_rows[1]["middle_pref"] == "5"
            
            Path(csv_path).unlink()
            
            # Test JSON export
            json_export_path = tab._export_json(loaded_players, include_prefs=True)
            assert Path(json_export_path).exists()
            
            # Verify JSON content
            with open(json_export_path, 'r') as f:
                exported_data = json.load(f)
                
                assert len(exported_data) == 2
                assert exported_data[0]["player_name"] == "BulkPlayer1"
                assert exported_data[0]["role_preferences"]["top"] == 5
                assert exported_data[1]["player_name"] == "BulkPlayer2"
                assert exported_data[1]["role_preferences"]["middle"] == 5
            
            Path(json_export_path).unlink()
            
        finally:
            Path(json_path).unlink()
    
    def test_validation_workflow(self):
        """Test validation workflow for player data."""
        validator = PlayerValidator()
        
        # Test valid player data
        valid_name, name_msg = validator.validate_player_name("ValidPlayer")
        valid_summoner, summoner_msg = validator.validate_summoner_name("ValidSummoner")
        valid_tag, tag_msg = validator.validate_riot_tag("NA1")
        valid_prefs, prefs_msg = validator.validate_role_preferences({
            "top": 5, "jungle": 3, "middle": 2, "bottom": 1, "support": 4
        })
        
        assert all([valid_name, valid_summoner, valid_tag, valid_prefs])
        
        # Test invalid player data
        invalid_name, _ = validator.validate_player_name("")
        invalid_summoner, _ = validator.validate_summoner_name("AB")
        invalid_tag, _ = validator.validate_riot_tag("INVALID-TAG")
        invalid_prefs, _ = validator.validate_role_preferences({"invalid_role": 3})
        
        assert not any([invalid_name, invalid_summoner, invalid_tag, invalid_prefs])


if __name__ == "__main__":
    pytest.main([__file__])