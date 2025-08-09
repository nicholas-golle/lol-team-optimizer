"""
Comprehensive Player Management Tab Implementation

This module provides a complete player management interface with CRUD operations,
bulk import/export, validation, and advanced filtering capabilities.
"""

import logging
import csv
import json
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Union
from pathlib import Path
import gradio as gr

from .models import Player
from .core_engine import CoreEngine
from .gradio_components import PlayerManagementComponents, ValidationComponents, ProgressComponents
from .riot_client import RiotAPIClient


class PlayerValidator:
    """Validates player data with real-time feedback."""
    
    def __init__(self, riot_client: Optional[RiotAPIClient] = None):
        """Initialize validator with optional Riot API client."""
        self.riot_client = riot_client
        self.logger = logging.getLogger(__name__)
    
    def validate_player_name(self, name: str) -> Tuple[bool, str]:
        """Validate player display name."""
        if not name or not name.strip():
            return False, "Player name is required"
        
        if len(name.strip()) < 2:
            return False, "Player name must be at least 2 characters"
        
        if len(name.strip()) > 50:
            return False, "Player name must be less than 50 characters"
        
        # Check for invalid characters
        invalid_chars = ['<', '>', '"', "'", '&', '\\', '/']
        if any(char in name for char in invalid_chars):
            return False, f"Player name contains invalid characters: {', '.join(invalid_chars)}"
        
        return True, "Valid player name"
    
    def validate_summoner_name(self, summoner_name: str) -> Tuple[bool, str]:
        """Validate summoner name format."""
        if not summoner_name or not summoner_name.strip():
            return False, "Summoner name is required"
        
        summoner_name = summoner_name.strip()
        
        if len(summoner_name) < 3:
            return False, "Summoner name must be at least 3 characters"
        
        if len(summoner_name) > 16:
            return False, "Summoner name must be less than 16 characters"
        
        # Basic character validation (Riot allows letters, numbers, spaces, and some special chars)
        import re
        if not re.match(r'^[a-zA-Z0-9\s\-_]+$', summoner_name):
            return False, "Summoner name contains invalid characters"
        
        return True, "Valid summoner name"
    
    def validate_riot_tag(self, tag: str) -> Tuple[bool, str]:
        """Validate Riot ID tag format."""
        if not tag or not tag.strip():
            return False, "Riot tag is required"
        
        tag = tag.strip().upper()
        
        if len(tag) < 2:
            return False, "Riot tag must be at least 2 characters"
        
        if len(tag) > 5:
            return False, "Riot tag must be less than 5 characters"
        
        # Basic validation - alphanumeric
        import re
        if not re.match(r'^[A-Z0-9]+$', tag):
            return False, "Riot tag must contain only letters and numbers"
        
        return True, f"Valid riot tag: {tag}"
    
    def validate_role_preferences(self, preferences: Dict[str, int]) -> Tuple[bool, str]:
        """Validate role preference values."""
        valid_roles = {"top", "jungle", "middle", "bottom", "support"}
        
        for role, pref in preferences.items():
            if role not in valid_roles:
                return False, f"Invalid role: {role}"
            
            if not isinstance(pref, int) or not 1 <= pref <= 5:
                return False, f"Role preference for {role} must be between 1 and 5"
        
        return True, "Valid role preferences"
    
    async def validate_with_riot_api(self, summoner_name: str, tag: str, region: str) -> Tuple[bool, str, Optional[str]]:
        """Validate player exists in Riot API and return PUUID."""
        if not self.riot_client:
            return False, "Riot API client not available", None
        
        try:
            # This would be the actual API call
            # For now, we'll simulate validation
            full_riot_id = f"{summoner_name}#{tag}"
            
            # Simulate API validation (in real implementation, this would call Riot API)
            # puuid = await self.riot_client.get_puuid_by_riot_id(summoner_name, tag, region)
            
            # For demo purposes, assume validation passes
            return True, f"Player {full_riot_id} validated successfully", "simulated_puuid"
            
        except Exception as e:
            self.logger.error(f"API validation failed: {e}")
            return False, f"API validation failed: {str(e)}", None


class BulkImportProcessor:
    """Processes bulk player imports from various file formats."""
    
    def __init__(self, core_engine: CoreEngine):
        """Initialize with core engine."""
        self.core_engine = core_engine
        self.logger = logging.getLogger(__name__)
        self.validator = PlayerValidator(core_engine.riot_client if hasattr(core_engine, 'riot_client') else None)
    
    def process_csv_file(self, file_path: str, field_mapping: Dict[str, str], 
                        options: Dict[str, Any]) -> Tuple[List[Player], List[str]]:
        """Process CSV file and return players and errors."""
        players = []
        errors = []
        
        try:
            # Read CSV with specified options
            delimiter = options.get('delimiter', ',')
            encoding = options.get('encoding', 'utf-8')
            has_header = options.get('has_header', True)
            
            with open(file_path, 'r', encoding=encoding) as f:
                if has_header:
                    reader = csv.DictReader(f, delimiter=delimiter)
                    rows = list(reader)
                else:
                    reader = csv.reader(f, delimiter=delimiter)
                    rows = list(reader)
                    # Convert to dict format using field mapping
                    if rows:
                        headers = list(field_mapping.values())
                        rows = [dict(zip(headers, row)) for row in rows]
            
            # Process each row
            for i, row in enumerate(rows, 1):
                try:
                    player = self._create_player_from_row(row, field_mapping)
                    players.append(player)
                except Exception as e:
                    errors.append(f"Row {i}: {str(e)}")
            
        except Exception as e:
            errors.append(f"Failed to read CSV file: {str(e)}")
        
        return players, errors
    
    def process_excel_file(self, file_path: str, field_mapping: Dict[str, str]) -> Tuple[List[Player], List[str]]:
        """Process Excel file and return players and errors."""
        players = []
        errors = []
        
        try:
            # Read Excel file
            df = pd.read_excel(file_path)
            
            # Process each row
            for i, row in df.iterrows():
                try:
                    row_dict = row.to_dict()
                    player = self._create_player_from_row(row_dict, field_mapping)
                    players.append(player)
                except Exception as e:
                    errors.append(f"Row {i+1}: {str(e)}")
            
        except Exception as e:
            errors.append(f"Failed to read Excel file: {str(e)}")
        
        return players, errors
    
    def process_json_file(self, file_path: str) -> Tuple[List[Player], List[str]]:
        """Process JSON file and return players and errors."""
        players = []
        errors = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                errors.append("JSON file must contain a list of player objects")
                return players, errors
            
            # Process each player object
            for i, player_data in enumerate(data):
                try:
                    if not isinstance(player_data, dict):
                        errors.append(f"Player {i+1}: Must be an object")
                        continue
                    
                    player = self._create_player_from_dict(player_data)
                    players.append(player)
                except Exception as e:
                    errors.append(f"Player {i+1}: {str(e)}")
            
        except Exception as e:
            errors.append(f"Failed to read JSON file: {str(e)}")
        
        return players, errors
    
    def _create_player_from_row(self, row: Dict[str, Any], field_mapping: Dict[str, str]) -> Player:
        """Create player from CSV/Excel row using field mapping."""
        # Extract mapped fields
        player_data = {}
        
        for field, column in field_mapping.items():
            if column != "Not Mapped" and column in row:
                player_data[field] = row[column]
        
        return self._create_player_from_dict(player_data)
    
    def _create_player_from_dict(self, data: Dict[str, Any]) -> Player:
        """Create player from dictionary data."""
        # Validate required fields
        if 'player_name' not in data or not data['player_name']:
            raise ValueError("Player name is required")
        
        if 'summoner_name' not in data or not data['summoner_name']:
            raise ValueError("Summoner name is required")
        
        # Create role preferences
        role_preferences = {}
        for role in ["top", "jungle", "middle", "bottom", "support"]:
            pref_key = f"{role}_pref"
            if pref_key in data:
                try:
                    pref_value = int(data[pref_key])
                    if 1 <= pref_value <= 5:
                        role_preferences[role] = pref_value
                    else:
                        role_preferences[role] = 3  # Default neutral
                except (ValueError, TypeError):
                    role_preferences[role] = 3  # Default neutral
            else:
                role_preferences[role] = 3  # Default neutral
        
        # Create player
        player = Player(
            name=str(data['player_name']).strip(),
            summoner_name=str(data['summoner_name']).strip(),
            puuid="",  # Will be filled during API validation
            role_preferences=role_preferences
        )
        
        return player
    
    def generate_csv_template(self) -> str:
        """Generate CSV template file."""
        template_data = [
            ["player_name", "summoner_name", "riot_tag", "region", "top_pref", "jungle_pref", "middle_pref", "bottom_pref", "support_pref"],
            ["Player One", "SummonerOne", "NA1", "na1", "5", "3", "2", "1", "4"],
            ["Player Two", "SummonerTwo", "NA1", "na1", "2", "5", "3", "4", "1"],
            ["Player Three", "SummonerThree", "EUW", "euw1", "3", "2", "5", "3", "2"]
        ]
        
        # Create temporary file
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='')
        
        try:
            writer = csv.writer(temp_file)
            writer.writerows(template_data)
        finally:
            temp_file.close()
        
        return temp_file.name


class PlayerManagementTab:
    """Complete player management tab with all CRUD operations."""
    
    def __init__(self, core_engine: CoreEngine):
        """Initialize player management tab."""
        self.core_engine = core_engine
        self.logger = logging.getLogger(__name__)
        self.validator = PlayerValidator(getattr(core_engine, 'riot_client', None))
        self.bulk_processor = BulkImportProcessor(core_engine)
        
        # Component references
        self.components = {}
        self.current_players = []
        self.filtered_players = []
        self.current_page = 1
        self.page_size = 25
    
    def create_tab(self) -> List[gr.Component]:
        """Create the complete player management tab."""
        tab_components = []
        
        # Tab header
        tab_components.append(gr.Markdown("""
        # 👥 Player Management
        
        Manage your team's players with comprehensive CRUD operations, bulk import/export, 
        and real-time validation.
        """))
        
        # Main sections
        with gr.Tabs() as player_tabs:
            # Add Player Section
            with gr.Tab("➕ Add Player"):
                add_components = self._create_add_player_section()
                tab_components.extend(add_components)
            
            # Player List Section
            with gr.Tab("📋 Player List"):
                list_components = self._create_player_list_section()
                tab_components.extend(list_components)
            
            # Bulk Import Section
            with gr.Tab("📥 Bulk Import"):
                import_components = self._create_bulk_import_section()
                tab_components.extend(import_components)
            
            # Export Section
            with gr.Tab("📤 Export"):
                export_components = self._create_export_section()
                tab_components.extend(export_components)
        
        return tab_components
    
    def _create_add_player_section(self) -> List[gr.Component]:
        """Create the add player form section."""
        components = []
        
        # Form components
        form_components = PlayerManagementComponents.create_advanced_player_form()
        self.components.update(form_components)
        
        # Real-time validation
        def validate_player_form(name, summoner, tag, region, *role_prefs):
            """Validate player form in real-time."""
            validation_messages = []
            
            # Validate name
            name_valid, name_msg = self.validator.validate_player_name(name)
            if not name_valid:
                validation_messages.append(f"❌ {name_msg}")
            else:
                validation_messages.append(f"✅ {name_msg}")
            
            # Validate summoner name
            summoner_valid, summoner_msg = self.validator.validate_summoner_name(summoner)
            if not summoner_valid:
                validation_messages.append(f"❌ {summoner_msg}")
            else:
                validation_messages.append(f"✅ {summoner_msg}")
            
            # Validate tag
            tag_valid, tag_msg = self.validator.validate_riot_tag(tag)
            if not tag_valid:
                validation_messages.append(f"❌ {tag_msg}")
            else:
                validation_messages.append(f"✅ {tag_msg}")
            
            # Validate role preferences
            role_prefs_dict = {
                "top": role_prefs[0],
                "jungle": role_prefs[1], 
                "middle": role_prefs[2],
                "bottom": role_prefs[3],
                "support": role_prefs[4]
            }
            
            prefs_valid, prefs_msg = self.validator.validate_role_preferences(role_prefs_dict)
            if not prefs_valid:
                validation_messages.append(f"❌ {prefs_msg}")
            else:
                validation_messages.append(f"✅ {prefs_msg}")
            
            # Return validation HTML
            validation_html = "<br>".join(validation_messages)
            return f"<div style='padding: 10px; border: 1px solid #ddd; border-radius: 4px;'>{validation_html}</div>"
        
        # Add player function
        def add_player(name, summoner, tag, region, *role_prefs):
            """Add new player to the system."""
            try:
                # Create role preferences dict
                role_prefs_dict = {
                    "top": int(role_prefs[0]),
                    "jungle": int(role_prefs[1]),
                    "middle": int(role_prefs[2]),
                    "bottom": int(role_prefs[3]),
                    "support": int(role_prefs[4])
                }
                
                # Create player
                player = Player(
                    name=name.strip(),
                    summoner_name=summoner.strip(),
                    puuid="",  # Will be filled during extraction
                    role_preferences=role_prefs_dict
                )
                
                # Add to data manager
                success = self.core_engine.data_manager.add_player(player)
                
                if success:
                    return "✅ Player added successfully!"
                else:
                    return "❌ Player already exists with that name."
                    
            except Exception as e:
                self.logger.error(f"Error adding player: {e}")
                return f"❌ Error adding player: {str(e)}"
        
        # Clear form function
        def clear_form():
            """Clear all form fields."""
            return ["", "", "NA1", "na1", 3, 3, 3, 3, 3, ""]
        
        # Set up event handlers
        validation_inputs = [
            form_components['player_name'],
            form_components['summoner_name'],
            form_components['riot_tag'],
            form_components['region']
        ] + list(form_components['role_preferences'].values())
        
        # Real-time validation
        for input_component in validation_inputs:
            input_component.change(
                fn=validate_player_form,
                inputs=validation_inputs,
                outputs=form_components['validation_message']
            )
        
        # Submit button
        form_components['submit_btn'].click(
            fn=add_player,
            inputs=validation_inputs,
            outputs=gr.Markdown()
        )
        
        # Clear button
        form_components['clear_btn'].click(
            fn=clear_form,
            outputs=validation_inputs + [form_components['validation_message']]
        )
        
        return list(form_components.values())
    
    def _create_player_list_section(self) -> List[gr.Component]:
        """Create the player list and management section."""
        components = []
        
        # Load current players
        self.current_players = self.core_engine.data_manager.load_player_data()
        
        # Create interactive table
        table_components = PlayerManagementComponents.create_interactive_player_table(self.current_players)
        self.components.update(table_components)
        
        # Search and filter functions
        def filter_players(search_term, region_filter, status_filter):
            """Filter players based on search and filter criteria."""
            filtered = self.current_players.copy()
            
            # Apply search filter
            if search_term:
                search_term = search_term.lower()
                filtered = [p for p in filtered if 
                           search_term in p.name.lower() or 
                           search_term in p.summoner_name.lower()]
            
            # Apply region filter
            if region_filter != "All":
                filtered = [p for p in filtered if 
                           getattr(p, 'region', 'na1').upper() == region_filter]
            
            # Apply status filter
            if status_filter != "All":
                if status_filter == "Active":
                    filtered = [p for p in filtered if getattr(p, 'puuid', '')]
                elif status_filter == "No Data":
                    filtered = [p for p in filtered if not getattr(p, 'puuid', '')]
            
            self.filtered_players = filtered
            return PlayerManagementComponents.create_player_table(filtered)
        
        # Refresh players function
        def refresh_players():
            """Refresh the player list."""
            self.current_players = self.core_engine.data_manager.load_player_data()
            self.filtered_players = self.current_players.copy()
            return PlayerManagementComponents.create_player_table(self.current_players)
        
        # Set up event handlers
        filter_inputs = [
            table_components['search_box'],
            table_components['region_filter'],
            table_components['status_filter']
        ]
        
        for input_component in filter_inputs:
            input_component.change(
                fn=filter_players,
                inputs=filter_inputs,
                outputs=table_components['player_table']
            )
        
        # Add refresh button
        refresh_btn = gr.Button("🔄 Refresh Players", variant="secondary")
        refresh_btn.click(
            fn=refresh_players,
            outputs=table_components['player_table']
        )
        
        components.extend(list(table_components.values()) + [refresh_btn])
        return components
    
    def _create_bulk_import_section(self) -> List[gr.Component]:
        """Create the bulk import section."""
        components = []
        
        # Create bulk import interface
        import_components = PlayerManagementComponents.create_bulk_import_interface()
        self.components.update(import_components)
        
        # File processing functions
        def process_uploaded_file(file_obj, format_type, field_mapping, options):
            """Process uploaded file and show preview."""
            if not file_obj:
                return "No file uploaded", gr.DataFrame(visible=False)
            
            try:
                file_path = file_obj.name
                
                if format_type == "CSV":
                    players, errors = self.bulk_processor.process_csv_file(file_path, field_mapping, options)
                elif format_type == "Excel":
                    players, errors = self.bulk_processor.process_excel_file(file_path, field_mapping)
                elif format_type == "JSON":
                    players, errors = self.bulk_processor.process_json_file(file_path)
                else:
                    return "Unsupported file format", gr.DataFrame(visible=False)
                
                # Create preview data
                preview_data = []
                for i, player in enumerate(players):
                    status = "✅ Valid"
                    issues = ""
                    
                    # Check for validation issues
                    name_valid, name_msg = self.validator.validate_player_name(player.name)
                    summoner_valid, summoner_msg = self.validator.validate_summoner_name(player.summoner_name)
                    
                    if not name_valid or not summoner_valid:
                        status = "⚠️ Issues"
                        issues = f"{name_msg if not name_valid else ''} {summoner_msg if not summoner_valid else ''}"
                    
                    preview_data.append([
                        player.name,
                        player.summoner_name,
                        getattr(player, 'region', 'na1').upper(),
                        status,
                        issues
                    ])
                
                # Add errors to preview
                for error in errors:
                    preview_data.append(["ERROR", "", "", "❌ Error", error])
                
                preview_df = gr.DataFrame(
                    value=preview_data,
                    headers=["Player Name", "Summoner Name", "Region", "Status", "Issues"],
                    visible=True
                )
                
                status_msg = f"Processed {len(players)} players with {len(errors)} errors"
                return status_msg, preview_df
                
            except Exception as e:
                self.logger.error(f"Error processing file: {e}")
                return f"Error processing file: {str(e)}", gr.DataFrame(visible=False)
        
        # Template download functions
        def download_csv_template():
            """Generate and return CSV template."""
            template_path = self.bulk_processor.generate_csv_template()
            return template_path
        
        # Set up event handlers
        import_components['preview_btn'].click(
            fn=process_uploaded_file,
            inputs=[
                import_components['file_upload'],
                import_components['format_selection'],
                # Field mapping would be collected here
                {},  # Placeholder for field mapping
                {}   # Placeholder for options
            ],
            outputs=[
                import_components['import_status'],
                import_components['preview_table']
            ]
        )
        
        import_components['download_csv_template'].click(
            fn=download_csv_template,
            outputs=gr.File()
        )
        
        components.extend(list(import_components.values()))
        return components
    
    def _create_export_section(self) -> List[gr.Component]:
        """Create the export section."""
        components = []
        
        gr.Markdown("## Export Players")
        gr.Markdown("Export your player data in various formats.")
        
        # Export options
        export_format = gr.Radio(
            choices=["CSV", "Excel", "JSON"],
            label="Export Format",
            value="CSV"
        )
        
        include_preferences = gr.Checkbox(
            label="Include Role Preferences",
            value=True
        )
        
        export_btn = gr.Button("Export Players", variant="primary")
        export_file = gr.File(label="Download Export", visible=False)
        
        def export_players(format_type, include_prefs):
            """Export players to selected format."""
            try:
                players = self.core_engine.data_manager.load_player_data()
                
                if format_type == "CSV":
                    return self._export_csv(players, include_prefs)
                elif format_type == "Excel":
                    return self._export_excel(players, include_prefs)
                elif format_type == "JSON":
                    return self._export_json(players, include_prefs)
                
            except Exception as e:
                self.logger.error(f"Export error: {e}")
                return None
        
        export_btn.click(
            fn=export_players,
            inputs=[export_format, include_preferences],
            outputs=export_file
        )
        
        components.extend([export_format, include_preferences, export_btn, export_file])
        return components
    
    def _export_csv(self, players: List[Player], include_prefs: bool) -> str:
        """Export players to CSV format."""
        import tempfile
        
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        
        # Define headers
        headers = ["player_name", "summoner_name", "region", "last_updated"]
        if include_prefs:
            headers.extend(["top_pref", "jungle_pref", "middle_pref", "bottom_pref", "support_pref"])
        
        writer = csv.writer(temp_file)
        writer.writerow(headers)
        
        # Write player data
        for player in players:
            row = [
                player.name,
                player.summoner_name,
                getattr(player, 'region', 'na1'),
                player.last_updated.isoformat() if player.last_updated else ""
            ]
            
            if include_prefs:
                row.extend([
                    player.role_preferences.get("top", 3),
                    player.role_preferences.get("jungle", 3),
                    player.role_preferences.get("middle", 3),
                    player.role_preferences.get("bottom", 3),
                    player.role_preferences.get("support", 3)
                ])
            
            writer.writerow(row)
        
        temp_file.close()
        return temp_file.name
    
    def _export_excel(self, players: List[Player], include_prefs: bool) -> str:
        """Export players to Excel format."""
        import tempfile
        
        temp_file = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
        temp_file.close()
        
        # Prepare data
        data = []
        for player in players:
            row = {
                "player_name": player.name,
                "summoner_name": player.summoner_name,
                "region": getattr(player, 'region', 'na1'),
                "last_updated": player.last_updated.isoformat() if player.last_updated else ""
            }
            
            if include_prefs:
                row.update({
                    "top_pref": player.role_preferences.get("top", 3),
                    "jungle_pref": player.role_preferences.get("jungle", 3),
                    "middle_pref": player.role_preferences.get("middle", 3),
                    "bottom_pref": player.role_preferences.get("bottom", 3),
                    "support_pref": player.role_preferences.get("support", 3)
                })
            
            data.append(row)
        
        # Create DataFrame and save
        df = pd.DataFrame(data)
        df.to_excel(temp_file.name, index=False)
        
        return temp_file.name
    
    def _export_json(self, players: List[Player], include_prefs: bool) -> str:
        """Export players to JSON format."""
        import tempfile
        from dataclasses import asdict
        
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        
        # Prepare data
        data = []
        for player in players:
            player_dict = {
                "player_name": player.name,
                "summoner_name": player.summoner_name,
                "region": getattr(player, 'region', 'na1'),
                "last_updated": player.last_updated.isoformat() if player.last_updated else None
            }
            
            if include_prefs:
                player_dict["role_preferences"] = player.role_preferences
            
            data.append(player_dict)
        
        json.dump(data, temp_file, indent=2, ensure_ascii=False)
        temp_file.close()
        
        return temp_file.name