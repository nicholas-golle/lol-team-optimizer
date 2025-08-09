"""
Gradio Interface for Bulk Operations and Data Import/Export

This module provides a comprehensive Gradio interface for:
- CSV/Excel import with data mapping and validation
- Bulk edit operations for multiple players
- Export functionality in multiple formats
- Data migration and backup/restore operations
- Audit logging visualization
"""

import csv
import json
import logging
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union

import gradio as gr
import pandas as pd

from .bulk_operations_manager import BulkOperationsManager
from .models import Player
from .core_engine import CoreEngine


class BulkOperationsInterface:
    """Gradio interface for bulk operations."""
    
    def __init__(self, core_engine: CoreEngine):
        """Initialize bulk operations interface."""
        self.core_engine = core_engine
        self.bulk_manager = BulkOperationsManager(
            core_engine.data_manager, 
            core_engine.config
        )
        self.logger = logging.getLogger(__name__)
        
        # State management
        self.current_import_data = []
        self.current_field_mapping = {}
        self.selected_players = []
    
    def create_bulk_operations_tab(self) -> List[gr.Component]:
        """Create the complete bulk operations tab."""
        components = []
        
        # Tab header
        components.append(gr.Markdown("""
        # 📦 Bulk Operations & Data Management
        
        Comprehensive tools for importing, exporting, and managing player data in bulk.
        """))
        
        # Create sub-tabs for different operations
        with gr.Tabs() as bulk_tabs:
            # Import Tab
            with gr.Tab("📥 Import Data"):
                import_components = self._create_import_section()
                components.extend(import_components)
            
            # Export Tab
            with gr.Tab("📤 Export Data"):
                export_components = self._create_export_section()
                components.extend(export_components)
            
            # Bulk Edit Tab
            with gr.Tab("✏️ Bulk Edit"):
                edit_components = self._create_bulk_edit_section()
                components.extend(edit_components)
            
            # Backup & Restore Tab
            with gr.Tab("💾 Backup & Restore"):
                backup_components = self._create_backup_section()
                components.extend(backup_components)
            
            # Migration Tab
            with gr.Tab("🔄 Data Migration"):
                migration_components = self._create_migration_section()
                components.extend(migration_components)
            
            # Audit Log Tab
            with gr.Tab("📋 Audit Log"):
                audit_components = self._create_audit_section()
                components.extend(audit_components)
        
        return components
    
    def _create_import_section(self) -> List[gr.Component]:
        """Create the data import section."""
        components = []
        
        # Import header
        components.append(gr.Markdown("## Import Player Data"))
        components.append(gr.Markdown(
            "Import players from CSV, Excel, or JSON files with validation and field mapping."
        ))
        
        # File upload
        file_upload = gr.File(
            label="Upload Data File",
            file_types=[".csv", ".xlsx", ".xls", ".json"],
            type="filepath"
        )
        components.append(file_upload)
        
        # Format selection
        format_selection = gr.Radio(
            choices=["CSV", "Excel", "JSON"],
            label="File Format",
            value="CSV"
        )
        components.append(format_selection)
        
        # Import options
        with gr.Row():
            has_header = gr.Checkbox(label="File has header row", value=True)
            allow_duplicates = gr.Checkbox(label="Allow duplicate player names", value=False)
            skip_rows = gr.Number(label="Skip rows", value=0, precision=0)
        
        components.extend([has_header, allow_duplicates, skip_rows])
        
        # CSV-specific options
        with gr.Group(visible=True) as csv_options:
            with gr.Row():
                delimiter = gr.Textbox(label="Delimiter", value=",", max_lines=1)
                encoding = gr.Dropdown(
                    choices=["utf-8", "latin-1", "cp1252"],
                    label="Encoding",
                    value="utf-8"
                )
        
        components.extend([csv_options, delimiter, encoding])
        
        # Field mapping section
        components.append(gr.Markdown("### Field Mapping"))
        components.append(gr.Markdown(
            "Map columns from your file to player data fields:"
        ))
        
        # Field mapping controls
        mapping_controls = {}
        field_options = ["Not Mapped", "player_name", "summoner_name", "riot_tag", "region",
                        "top_pref", "jungle_pref", "middle_pref", "bottom_pref", "support_pref"]
        
        with gr.Row():
            with gr.Column():
                mapping_controls['player_name'] = gr.Dropdown(
                    choices=field_options,
                    label="Player Name",
                    value="player_name"
                )
                mapping_controls['summoner_name'] = gr.Dropdown(
                    choices=field_options,
                    label="Summoner Name",
                    value="summoner_name"
                )
                mapping_controls['riot_tag'] = gr.Dropdown(
                    choices=field_options,
                    label="Riot Tag",
                    value="Not Mapped"
                )
            
            with gr.Column():
                mapping_controls['top_pref'] = gr.Dropdown(
                    choices=field_options,
                    label="Top Preference",
                    value="Not Mapped"
                )
                mapping_controls['jungle_pref'] = gr.Dropdown(
                    choices=field_options,
                    label="Jungle Preference",
                    value="Not Mapped"
                )
                mapping_controls['middle_pref'] = gr.Dropdown(
                    choices=field_options,
                    label="Middle Preference",
                    value="Not Mapped"
                )
            
            with gr.Column():
                mapping_controls['bottom_pref'] = gr.Dropdown(
                    choices=field_options,
                    label="Bottom Preference",
                    value="Not Mapped"
                )
                mapping_controls['support_pref'] = gr.Dropdown(
                    choices=field_options,
                    label="Support Preference",
                    value="Not Mapped"
                )
        
        components.extend(list(mapping_controls.values()))
        
        # Preview and import buttons
        with gr.Row():
            preview_btn = gr.Button("🔍 Preview Import", variant="secondary")
            import_btn = gr.Button("📥 Import Data", variant="primary")
            download_template_btn = gr.Button("📄 Download Template", variant="secondary")
        
        components.extend([preview_btn, import_btn, download_template_btn])
        
        # Preview table
        preview_table = gr.DataFrame(
            label="Import Preview",
            visible=False,
            interactive=False
        )
        components.append(preview_table)
        
        # Import status
        import_status = gr.Markdown(visible=False)
        components.append(import_status)
        
        # Template download
        template_file = gr.File(label="Template Download", visible=False)
        components.append(template_file)
        
        # Event handlers
        def update_csv_options_visibility(format_type):
            """Show/hide CSV options based on format selection."""
            return gr.Group(visible=(format_type == "CSV"))
        
        format_selection.change(
            fn=update_csv_options_visibility,
            inputs=[format_selection],
            outputs=[csv_options]
        )
        
        def preview_import_data(file_path, format_type, has_header_val, skip_rows_val,
                               delimiter_val, encoding_val, *mapping_values):
            """Preview imported data before actual import."""
            if not file_path:
                return gr.DataFrame(visible=False), gr.Markdown("No file uploaded", visible=True)
            
            try:
                # Build field mapping
                field_mapping = {}
                mapping_fields = ['player_name', 'summoner_name', 'riot_tag', 'region',
                                'top_pref', 'jungle_pref', 'middle_pref', 'bottom_pref', 'support_pref']
                
                for i, field in enumerate(mapping_fields):
                    if i < len(mapping_values) and mapping_values[i] != "Not Mapped":
                        field_mapping[field] = mapping_values[i]
                
                # Import options
                options = {
                    'has_header': has_header_val,
                    'skip_rows': int(skip_rows_val) if skip_rows_val else 0,
                    'delimiter': delimiter_val,
                    'encoding': encoding_val,
                    'allow_duplicates': False  # For preview only
                }
                
                # Process file based on format
                if format_type == "CSV":
                    players, errors, stats = self.bulk_manager.import_processor.process_csv_import(
                        file_path, field_mapping, options
                    )
                elif format_type == "Excel":
                    players, errors, stats = self.bulk_manager.import_processor.process_excel_import(
                        file_path, field_mapping, options
                    )
                elif format_type == "JSON":
                    players, errors, stats = self.bulk_manager.import_processor.process_json_import(
                        file_path, options
                    )
                else:
                    return gr.DataFrame(visible=False), gr.Markdown("Unsupported format", visible=True)
                
                # Store for actual import
                self.current_import_data = players
                self.current_field_mapping = field_mapping
                
                # Create preview data
                preview_data = []
                for i, player in enumerate(players[:50]):  # Limit preview to 50 rows
                    status = "✅ Valid"
                    issues = ""
                    
                    # Basic validation
                    if not player.name or len(player.name) < 2:
                        status = "⚠️ Issues"
                        issues += "Invalid name; "
                    
                    if not player.summoner_name or len(player.summoner_name) < 3:
                        status = "⚠️ Issues"
                        issues += "Invalid summoner name; "
                    
                    preview_data.append([
                        player.name,
                        player.summoner_name,
                        player.puuid or "Not set",
                        f"{player.role_preferences.get('top', 3)}/{player.role_preferences.get('jungle', 3)}/{player.role_preferences.get('middle', 3)}/{player.role_preferences.get('bottom', 3)}/{player.role_preferences.get('support', 3)}",
                        status,
                        issues.rstrip("; ")
                    ])
                
                # Add error rows
                for error in errors[:10]:  # Limit error display
                    preview_data.append([
                        "ERROR",
                        "",
                        "",
                        "",
                        "❌ Error",
                        error
                    ])
                
                preview_df = gr.DataFrame(
                    value=preview_data,
                    headers=["Player Name", "Summoner Name", "PUUID", "Role Prefs (T/J/M/B/S)", "Status", "Issues"],
                    visible=True
                )
                
                status_msg = f"""
                ### Import Preview Results
                
                - **Total Processed**: {stats['processed']}
                - **Valid Players**: {stats['valid']}
                - **Invalid Players**: {stats['invalid']}
                - **Duplicates**: {stats['duplicates']}
                - **Errors**: {len(errors)}
                
                {f"**First 50 players shown**" if len(players) > 50 else ""}
                """
                
                return preview_df, gr.Markdown(status_msg, visible=True)
                
            except Exception as e:
                self.logger.error(f"Preview failed: {e}")
                return gr.DataFrame(visible=False), gr.Markdown(f"Preview failed: {str(e)}", visible=True)
        
        preview_btn.click(
            fn=preview_import_data,
            inputs=[file_upload, format_selection, has_header, skip_rows, delimiter, encoding] + list(mapping_controls.values()),
            outputs=[preview_table, import_status]
        )
        
        def perform_import(allow_duplicates_val):
            """Perform the actual import operation."""
            if not self.current_import_data:
                return gr.Markdown("No data to import. Please preview first.", visible=True)
            
            try:
                # Get existing players
                existing_players = self.core_engine.data_manager.load_player_data()
                
                # Filter duplicates if not allowed
                if not allow_duplicates_val:
                    existing_names = {p.name.lower() for p in existing_players}
                    filtered_players = [p for p in self.current_import_data 
                                      if p.name.lower() not in existing_names]
                else:
                    filtered_players = self.current_import_data
                
                # Add new players
                all_players = existing_players + filtered_players
                self.core_engine.data_manager.save_player_data(all_players)
                
                # Clear import data
                self.current_import_data = []
                
                status_msg = f"""
                ### Import Completed Successfully! ✅
                
                - **Players Imported**: {len(filtered_players)}
                - **Total Players**: {len(all_players)}
                
                The players have been added to your database and are ready for use.
                """
                
                return gr.Markdown(status_msg, visible=True)
                
            except Exception as e:
                self.logger.error(f"Import failed: {e}")
                return gr.Markdown(f"Import failed: {str(e)}", visible=True)
        
        import_btn.click(
            fn=perform_import,
            inputs=[allow_duplicates],
            outputs=[import_status]
        )
        
        def download_template(format_type):
            """Generate and download template file."""
            try:
                templates = self.bulk_manager.get_bulk_operation_templates()
                
                if format_type.lower() == "csv":
                    return gr.File(value=templates['csv'], visible=True)
                elif format_type.lower() == "json":
                    return gr.File(value=templates['json'], visible=True)
                else:
                    # Create Excel template
                    temp_file = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
                    temp_file.close()
                    
                    template_data = [
                        {
                            "player_name": "Player One",
                            "summoner_name": "SummonerOne",
                            "riot_tag": "NA1",
                            "region": "na1",
                            "top_pref": 5,
                            "jungle_pref": 3,
                            "middle_pref": 2,
                            "bottom_pref": 1,
                            "support_pref": 4
                        }
                    ]
                    
                    df = pd.DataFrame(template_data)
                    df.to_excel(temp_file.name, index=False)
                    
                    return gr.File(value=temp_file.name, visible=True)
                    
            except Exception as e:
                self.logger.error(f"Template generation failed: {e}")
                return gr.File(visible=False)
        
        download_template_btn.click(
            fn=download_template,
            inputs=[format_selection],
            outputs=[template_file]
        )
        
        return components
    
    def _create_export_section(self) -> List[gr.Component]:
        """Create the data export section."""
        components = []
        
        # Export header
        components.append(gr.Markdown("## Export Player Data"))
        components.append(gr.Markdown(
            "Export your player data in various formats for backup or external use."
        ))
        
        # Export format selection
        export_format = gr.Radio(
            choices=["CSV", "Excel", "JSON", "PDF"],
            label="Export Format",
            value="CSV"
        )
        components.append(export_format)
        
        # Export options
        with gr.Row():
            include_preferences = gr.Checkbox(label="Include Role Preferences", value=True)
            include_metadata = gr.Checkbox(label="Include Metadata", value=False)
            include_masteries = gr.Checkbox(label="Include Champion Masteries", value=False)
        
        components.extend([include_preferences, include_metadata, include_masteries])
        
        # Player selection
        components.append(gr.Markdown("### Player Selection"))
        
        player_selection = gr.Radio(
            choices=["All Players", "Selected Players"],
            label="Export Scope",
            value="All Players"
        )
        components.append(player_selection)
        
        # Player checklist (visible when "Selected Players" is chosen)
        player_checklist = gr.CheckboxGroup(
            choices=[],
            label="Select Players to Export",
            visible=False
        )
        components.append(player_checklist)
        
        # Export button
        export_btn = gr.Button("📤 Export Data", variant="primary")
        components.append(export_btn)
        
        # Export file download
        export_file = gr.File(label="Download Export", visible=False)
        components.append(export_file)
        
        # Export status
        export_status = gr.Markdown(visible=False)
        components.append(export_status)
        
        # Event handlers
        def update_player_selection_visibility(selection_type):
            """Show/hide player selection based on export scope."""
            if selection_type == "Selected Players":
                # Load current players
                players = self.core_engine.data_manager.load_player_data()
                player_names = [p.name for p in players]
                return gr.CheckboxGroup(choices=player_names, visible=True)
            else:
                return gr.CheckboxGroup(visible=False)
        
        player_selection.change(
            fn=update_player_selection_visibility,
            inputs=[player_selection],
            outputs=[player_checklist]
        )
        
        def perform_export(format_type, include_prefs, include_meta, include_mast,
                          selection_type, selected_players):
            """Perform the export operation."""
            try:
                # Load players
                all_players = self.core_engine.data_manager.load_player_data()
                
                # Filter players based on selection
                if selection_type == "Selected Players" and selected_players:
                    players_to_export = [p for p in all_players if p.name in selected_players]
                else:
                    players_to_export = all_players
                
                if not players_to_export:
                    return gr.File(visible=False), gr.Markdown("No players to export", visible=True)
                
                # Export options
                options = {
                    'include_preferences': include_prefs,
                    'include_metadata': include_meta,
                    'include_masteries': include_mast
                }
                
                # Perform export based on format
                if format_type == "CSV":
                    export_file_path = self.bulk_manager.export_processor.export_to_csv(
                        players_to_export, options
                    )
                elif format_type == "Excel":
                    options['include_summary'] = True
                    export_file_path = self.bulk_manager.export_processor.export_to_excel(
                        players_to_export, options
                    )
                elif format_type == "JSON":
                    export_file_path = self.bulk_manager.export_processor.export_to_json(
                        players_to_export, options
                    )
                elif format_type == "PDF":
                    export_file_path = self.bulk_manager.export_processor.export_to_pdf(
                        players_to_export, options
                    )
                else:
                    return gr.File(visible=False), gr.Markdown("Unsupported format", visible=True)
                
                status_msg = f"""
                ### Export Completed Successfully! ✅
                
                - **Format**: {format_type}
                - **Players Exported**: {len(players_to_export)}
                - **File Size**: {Path(export_file_path).stat().st_size / 1024:.1f} KB
                
                Your export is ready for download.
                """
                
                return gr.File(value=export_file_path, visible=True), gr.Markdown(status_msg, visible=True)
                
            except Exception as e:
                self.logger.error(f"Export failed: {e}")
                return gr.File(visible=False), gr.Markdown(f"Export failed: {str(e)}", visible=True)
        
        export_btn.click(
            fn=perform_export,
            inputs=[export_format, include_preferences, include_metadata, include_masteries,
                   player_selection, player_checklist],
            outputs=[export_file, export_status]
        )
        
        return components
    
    def _create_bulk_edit_section(self) -> List[gr.Component]:
        """Create the bulk edit section."""
        components = []
        
        # Bulk edit header
        components.append(gr.Markdown("## Bulk Edit Players"))
        components.append(gr.Markdown(
            "Edit multiple players simultaneously with bulk operations."
        ))
        
        # Player selection
        player_checklist = gr.CheckboxGroup(
            choices=[],
            label="Select Players to Edit"
        )
        components.append(player_checklist)
        
        # Load players button
        load_players_btn = gr.Button("🔄 Load Players", variant="secondary")
        components.append(load_players_btn)
        
        # Bulk edit options
        components.append(gr.Markdown("### Edit Operations"))
        
        # Role preferences bulk edit
        with gr.Group():
            components.append(gr.Markdown("**Role Preferences**"))
            
            with gr.Row():
                bulk_top_pref = gr.Slider(1, 5, value=3, step=1, label="Top Preference")
                bulk_jungle_pref = gr.Slider(1, 5, value=3, step=1, label="Jungle Preference")
                bulk_middle_pref = gr.Slider(1, 5, value=3, step=1, label="Middle Preference")
            
            with gr.Row():
                bulk_bottom_pref = gr.Slider(1, 5, value=3, step=1, label="Bottom Preference")
                bulk_support_pref = gr.Slider(1, 5, value=3, step=1, label="Support Preference")
            
            update_preferences = gr.Checkbox(label="Update Role Preferences", value=False)
        
        components.extend([bulk_top_pref, bulk_jungle_pref, bulk_middle_pref,
                          bulk_bottom_pref, bulk_support_pref, update_preferences])
        
        # Other bulk operations
        with gr.Group():
            components.append(gr.Markdown("**Other Operations**"))
            
            # Summoner name prefix/suffix
            summoner_prefix = gr.Textbox(label="Add Prefix to Summoner Names", placeholder="e.g., Team_")
            summoner_suffix = gr.Textbox(label="Add Suffix to Summoner Names", placeholder="e.g., _Main")
            update_summoner = gr.Checkbox(label="Update Summoner Names", value=False)
        
        components.extend([summoner_prefix, summoner_suffix, update_summoner])
        
        # Bulk edit button
        bulk_edit_btn = gr.Button("✏️ Apply Bulk Edit", variant="primary")
        components.append(bulk_edit_btn)
        
        # Bulk edit status
        bulk_edit_status = gr.Markdown(visible=False)
        components.append(bulk_edit_status)
        
        # Event handlers
        def load_players():
            """Load current players for selection."""
            players = self.core_engine.data_manager.load_player_data()
            player_names = [p.name for p in players]
            return gr.CheckboxGroup(choices=player_names)
        
        load_players_btn.click(
            fn=load_players,
            outputs=[player_checklist]
        )
        
        def perform_bulk_edit(selected_players, update_prefs, top_pref, jungle_pref, middle_pref,
                             bottom_pref, support_pref, update_summ, prefix, suffix):
            """Perform bulk edit operations."""
            if not selected_players:
                return gr.Markdown("No players selected for editing", visible=True)
            
            try:
                updates = {}
                
                # Role preferences update
                if update_prefs:
                    updates['role_preferences'] = {
                        'top': int(top_pref),
                        'jungle': int(jungle_pref),
                        'middle': int(middle_pref),
                        'bottom': int(bottom_pref),
                        'support': int(support_pref)
                    }
                
                # Summoner name update
                if update_summ and (prefix or suffix):
                    # This would need special handling in the bulk manager
                    # For now, we'll just note it in the updates
                    updates['summoner_name_transform'] = {
                        'prefix': prefix,
                        'suffix': suffix
                    }
                
                if not updates:
                    return gr.Markdown("No updates specified", visible=True)
                
                # Perform bulk edit
                success_count, errors = self.bulk_manager.bulk_edit_players(
                    selected_players, updates
                )
                
                if errors:
                    error_msg = "\n".join([f"- {error}" for error in errors])
                    status_msg = f"""
                    ### Bulk Edit Completed with Errors ⚠️
                    
                    - **Successfully Updated**: {success_count} players
                    - **Errors**: {len(errors)}
                    
                    **Error Details:**
                    {error_msg}
                    """
                else:
                    status_msg = f"""
                    ### Bulk Edit Completed Successfully! ✅
                    
                    - **Players Updated**: {success_count}
                    
                    All selected players have been updated with the specified changes.
                    """
                
                return gr.Markdown(status_msg, visible=True)
                
            except Exception as e:
                self.logger.error(f"Bulk edit failed: {e}")
                return gr.Markdown(f"Bulk edit failed: {str(e)}", visible=True)
        
        bulk_edit_btn.click(
            fn=perform_bulk_edit,
            inputs=[player_checklist, update_preferences, bulk_top_pref, bulk_jungle_pref,
                   bulk_middle_pref, bulk_bottom_pref, bulk_support_pref,
                   update_summoner, summoner_prefix, summoner_suffix],
            outputs=[bulk_edit_status]
        )
        
        return components
    
    def _create_backup_section(self) -> List[gr.Component]:
        """Create the backup and restore section."""
        components = []
        
        # Backup section
        components.append(gr.Markdown("## Backup & Restore"))
        components.append(gr.Markdown(
            "Create backups of your player data and restore from previous backups."
        ))
        
        # Create backup
        with gr.Group():
            components.append(gr.Markdown("### Create Backup"))
            
            backup_name = gr.Textbox(
                label="Backup Name (optional)",
                placeholder="Leave empty for automatic naming"
            )
            
            create_backup_btn = gr.Button("💾 Create Backup", variant="primary")
            backup_file = gr.File(label="Backup Download", visible=False)
            backup_status = gr.Markdown(visible=False)
        
        components.extend([backup_name, create_backup_btn, backup_file, backup_status])
        
        # Restore backup
        with gr.Group():
            components.append(gr.Markdown("### Restore Backup"))
            
            restore_file = gr.File(
                label="Upload Backup File",
                file_types=[".zip"]
            )
            
            restore_btn = gr.Button("🔄 Restore Backup", variant="secondary")
            restore_status = gr.Markdown(visible=False)
        
        components.extend([restore_file, restore_btn, restore_status])
        
        # Event handlers
        def create_backup(backup_name_val):
            """Create a backup of player data."""
            try:
                backup_file_path = self.bulk_manager.create_backup(backup_name_val or None)
                
                status_msg = f"""
                ### Backup Created Successfully! ✅
                
                Your player data has been backed up and is ready for download.
                
                **Backup includes:**
                - Player data
                - Audit logs
                - Metadata
                """
                
                return gr.File(value=backup_file_path, visible=True), gr.Markdown(status_msg, visible=True)
                
            except Exception as e:
                self.logger.error(f"Backup creation failed: {e}")
                return gr.File(visible=False), gr.Markdown(f"Backup creation failed: {str(e)}", visible=True)
        
        create_backup_btn.click(
            fn=create_backup,
            inputs=[backup_name],
            outputs=[backup_file, backup_status]
        )
        
        def restore_backup(restore_file_path):
            """Restore from backup file."""
            if not restore_file_path:
                return gr.Markdown("No backup file uploaded", visible=True)
            
            try:
                success = self.bulk_manager.restore_backup(restore_file_path)
                
                if success:
                    status_msg = """
                    ### Backup Restored Successfully! ✅
                    
                    Your player data has been restored from the backup.
                    
                    **Note:** A backup of your current data was created before restoration.
                    """
                else:
                    status_msg = "### Backup Restoration Failed ❌"
                
                return gr.Markdown(status_msg, visible=True)
                
            except Exception as e:
                self.logger.error(f"Backup restoration failed: {e}")
                return gr.Markdown(f"Backup restoration failed: {str(e)}", visible=True)
        
        restore_btn.click(
            fn=restore_backup,
            inputs=[restore_file],
            outputs=[restore_status]
        )
        
        return components
    
    def _create_migration_section(self) -> List[gr.Component]:
        """Create the data migration section."""
        components = []
        
        # Migration header
        components.append(gr.Markdown("## Data Migration"))
        components.append(gr.Markdown(
            "Migrate player data from legacy formats or other systems."
        ))
        
        # Legacy file upload
        legacy_file = gr.File(
            label="Upload Legacy Data File",
            file_types=[".csv", ".xlsx", ".json", ".txt"]
        )
        components.append(legacy_file)
        
        # Legacy format selection
        legacy_format = gr.Radio(
            choices=["CSV", "Excel", "JSON", "Custom"],
            label="Legacy Format",
            value="CSV"
        )
        components.append(legacy_format)
        
        # Migration options
        with gr.Row():
            merge_duplicates = gr.Checkbox(label="Merge with existing players", value=True)
            validate_data = gr.Checkbox(label="Validate migrated data", value=True)
        
        components.extend([merge_duplicates, validate_data])
        
        # Migration button
        migrate_btn = gr.Button("🔄 Migrate Data", variant="primary")
        components.append(migrate_btn)
        
        # Migration status
        migration_status = gr.Markdown(visible=False)
        components.append(migration_status)
        
        # Event handler
        def perform_migration(file_path, format_type, merge_dupes, validate):
            """Perform data migration."""
            if not file_path:
                return gr.Markdown("No file uploaded for migration", visible=True)
            
            try:
                migrated_count, errors = self.bulk_manager.migrate_from_legacy_format(
                    file_path, format_type.lower()
                )
                
                if errors:
                    error_msg = "\n".join([f"- {error}" for error in errors[:10]])  # Show first 10 errors
                    status_msg = f"""
                    ### Migration Completed with Issues ⚠️
                    
                    - **Players Migrated**: {migrated_count}
                    - **Errors**: {len(errors)}
                    
                    **Error Details:**
                    {error_msg}
                    {f"... and {len(errors) - 10} more errors" if len(errors) > 10 else ""}
                    """
                else:
                    status_msg = f"""
                    ### Migration Completed Successfully! ✅
                    
                    - **Players Migrated**: {migrated_count}
                    
                    All legacy data has been successfully migrated to the current format.
                    """
                
                return gr.Markdown(status_msg, visible=True)
                
            except Exception as e:
                self.logger.error(f"Migration failed: {e}")
                return gr.Markdown(f"Migration failed: {str(e)}", visible=True)
        
        migrate_btn.click(
            fn=perform_migration,
            inputs=[legacy_file, legacy_format, merge_duplicates, validate_data],
            outputs=[migration_status]
        )
        
        return components
    
    def _create_audit_section(self) -> List[gr.Component]:
        """Create the audit log section."""
        components = []
        
        # Audit header
        components.append(gr.Markdown("## Audit Log"))
        components.append(gr.Markdown(
            "View and analyze all player data modifications and bulk operations."
        ))
        
        # Audit filters
        with gr.Row():
            audit_days = gr.Number(label="Days to Show", value=30, precision=0)
            audit_operation = gr.Dropdown(
                choices=["All", "IMPORT", "EXPORT", "BULK_EDIT", "CREATE", "UPDATE", "DELETE"],
                label="Operation Type",
                value="All"
            )
            audit_entity = gr.Textbox(label="Entity ID (optional)", placeholder="e.g., player name")
        
        components.extend([audit_days, audit_operation, audit_entity])
        
        # Load audit log button
        load_audit_btn = gr.Button("📋 Load Audit Log", variant="secondary")
        components.append(load_audit_btn)
        
        # Audit log table
        audit_table = gr.DataFrame(
            label="Audit Log",
            visible=False,
            interactive=False
        )
        components.append(audit_table)
        
        # Statistics
        audit_stats = gr.Markdown(visible=False)
        components.append(audit_stats)
        
        # Event handler
        def load_audit_log(days, operation_type, entity_id):
            """Load and display audit log."""
            try:
                # Get audit history
                start_date = datetime.now() - timedelta(days=int(days)) if days else None
                
                history = self.bulk_manager.audit_logger.get_audit_history(
                    entity_type="Player" if operation_type != "All" else None,
                    entity_id=entity_id if entity_id else None,
                    start_date=start_date,
                    limit=1000
                )
                
                # Filter by operation type
                if operation_type != "All":
                    history = [h for h in history if h['operation'] == operation_type]
                
                if not history:
                    return gr.DataFrame(visible=False), gr.Markdown("No audit entries found", visible=True)
                
                # Create table data
                table_data = []
                for entry in history:
                    timestamp = datetime.fromisoformat(entry['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
                    table_data.append([
                        timestamp,
                        entry['operation'],
                        entry['entity_type'],
                        entry['entity_id'],
                        entry.get('user_id', 'System'),
                        entry.get('details', '')[:100] + ('...' if len(entry.get('details', '')) > 100 else '')
                    ])
                
                audit_df = gr.DataFrame(
                    value=table_data,
                    headers=["Timestamp", "Operation", "Entity Type", "Entity ID", "User", "Details"],
                    visible=True
                )
                
                # Generate statistics
                stats = self.bulk_manager.get_operation_statistics(days=int(days) if days else 30)
                
                stats_msg = f"""
                ### Audit Statistics
                
                - **Total Operations**: {stats['total_operations']}
                - **Operations by Type**: {', '.join([f"{k}: {v}" for k, v in stats['operations_by_type'].items()])}
                - **Showing**: {len(history)} entries
                """
                
                return audit_df, gr.Markdown(stats_msg, visible=True)
                
            except Exception as e:
                self.logger.error(f"Failed to load audit log: {e}")
                return gr.DataFrame(visible=False), gr.Markdown(f"Failed to load audit log: {str(e)}", visible=True)
        
        load_audit_btn.click(
            fn=load_audit_log,
            inputs=[audit_days, audit_operation, audit_entity],
            outputs=[audit_table, audit_stats]
        )
        
        return components