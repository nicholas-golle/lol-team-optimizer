"""
Base Component Library for Consistent UI Patterns

This module provides reusable Gradio components for consistent UI patterns
across the web interface, including forms, tables, progress indicators,
and validation components.
"""

import gradio as gr
from typing import List, Dict, Any, Optional, Tuple, Callable
from dataclasses import dataclass
from datetime import datetime
import logging


@dataclass
class ComponentConfig:
    """Configuration for UI components."""
    theme_color: str = "rgb(0, 123, 255)"
    success_color: str = "#155724"
    error_color: str = "#dc3545"
    warning_color: str = "#856404"
    info_color: str = "#0c5460"


class PlayerManagementComponents:
    """Reusable components for player management."""
    
    @staticmethod
    def create_player_form(config: Optional[ComponentConfig] = None) -> List[gr.Component]:
        """Create form components for player data entry."""
        if config is None:
            config = ComponentConfig()
        
        components = []
        
        # Player name input with validation
        player_name = gr.Textbox(
            label="Player Name *",
            placeholder="Enter player display name",
            info="The name that will be displayed in the interface",
            max_lines=1
        )
        components.append(player_name)
        
        # Summoner name input with validation
        summoner_name = gr.Textbox(
            label="Summoner Name *",
            placeholder="Enter in-game summoner name",
            info="The player's current in-game name (without tag)",
            max_lines=1
        )
        components.append(summoner_name)
        
        # Riot ID tag input
        riot_tag = gr.Textbox(
            label="Riot Tag",
            placeholder="NA1",
            info="Riot ID tag (e.g., NA1, EUW, KR)",
            max_lines=1,
            value="NA1"
        )
        components.append(riot_tag)
        
        # Region dropdown
        region = gr.Dropdown(
            choices=[
                ("North America", "na1"),
                ("Europe West", "euw1"),
                ("Europe Nordic & East", "eun1"),
                ("Korea", "kr"),
                ("Brazil", "br1"),
                ("Latin America North", "la1"),
                ("Latin America South", "la2"),
                ("Oceania", "oc1"),
                ("Turkey", "tr1"),
                ("Russia", "ru"),
                ("Japan", "jp1")
            ],
            label="Region",
            value="na1",
            info="The server region where the player plays"
        )
        components.append(region)
        
        # Role preferences
        gr.Markdown("### Role Preferences")
        role_prefs = {}
        for role in ["Top", "Jungle", "Middle", "Bottom", "Support"]:
            role_pref = gr.Slider(
                minimum=1,
                maximum=5,
                value=3,
                step=1,
                label=f"{role} Preference",
                info=f"How much the player prefers {role} (1=Hate, 5=Love)"
            )
            role_prefs[role.lower()] = role_pref
            components.append(role_pref)
        
        return components
    
    @staticmethod
    def create_advanced_player_form(config: Optional[ComponentConfig] = None) -> Dict[str, gr.Component]:
        """Create advanced player form with all fields."""
        if config is None:
            config = ComponentConfig()
        
        form_components = {}
        
        # Basic information
        form_components['player_name'] = gr.Textbox(
            label="Player Name *",
            placeholder="Enter display name",
            info="Display name for the player"
        )
        
        form_components['summoner_name'] = gr.Textbox(
            label="Summoner Name *", 
            placeholder="Enter summoner name",
            info="In-game summoner name"
        )
        
        form_components['riot_tag'] = gr.Textbox(
            label="Riot Tag",
            placeholder="NA1",
            value="NA1",
            info="Riot ID tag"
        )
        
        form_components['region'] = gr.Dropdown(
            choices=[
                ("North America", "na1"),
                ("Europe West", "euw1"),
                ("Europe Nordic & East", "eun1"),
                ("Korea", "kr"),
                ("Brazil", "br1"),
                ("Latin America North", "la1"),
                ("Latin America South", "la2"),
                ("Oceania", "oc1"),
                ("Turkey", "tr1"),
                ("Russia", "ru"),
                ("Japan", "jp1")
            ],
            label="Region",
            value="na1"
        )
        
        # Role preferences with star ratings
        form_components['role_preferences'] = {}
        for role in ["top", "jungle", "middle", "bottom", "support"]:
            form_components['role_preferences'][role] = gr.Slider(
                minimum=1,
                maximum=5,
                value=3,
                step=1,
                label=f"{role.title()} Preference",
                info="1=Avoid, 2=Dislike, 3=Neutral, 4=Like, 5=Main"
            )
        
        # Validation messages
        form_components['validation_message'] = gr.HTML("")
        
        # Form buttons
        form_components['submit_btn'] = gr.Button("Add Player", variant="primary")
        form_components['clear_btn'] = gr.Button("Clear Form", variant="secondary")
        form_components['validate_btn'] = gr.Button("Validate Player", variant="secondary")
        
        return form_components
    
    @staticmethod
    def create_player_table(players: List[Any], config: Optional[ComponentConfig] = None) -> gr.DataFrame:
        """Create interactive table for player display."""
        if config is None:
            config = ComponentConfig()
        
        # Prepare data for table
        table_data = []
        headers = ["Name", "Summoner Name", "Region", "Status", "Matches", "Last Updated", "Actions"]
        
        for player in players:
            # Determine status
            if hasattr(player, 'puuid') and player.puuid:
                status = "✅ Active"
            else:
                status = "⚠️ No Data"
            
            # Format last updated
            last_updated = getattr(player, 'last_updated', 'Unknown')
            if isinstance(last_updated, datetime):
                last_updated = last_updated.strftime('%Y-%m-%d %H:%M')
            
            # Get match count (placeholder for now)
            match_count = "0"  # This would be populated from match data
            
            # Create action buttons (as text for now, would be actual buttons in full implementation)
            actions = "Edit | Delete | Extract"
            
            table_data.append([
                player.name,
                player.summoner_name,
                getattr(player, 'region', 'Unknown').upper(),
                status,
                match_count,
                str(last_updated),
                actions
            ])
        
        return gr.DataFrame(
            value=table_data,
            headers=headers,
            datatype=["str", "str", "str", "str", "str", "str", "str"],
            interactive=False,
            wrap=True
        )
    
    @staticmethod
    def create_interactive_player_table(players: List[Any], config: Optional[ComponentConfig] = None) -> Dict[str, gr.Component]:
        """Create interactive player table with sorting, filtering, and pagination."""
        if config is None:
            config = ComponentConfig()
        
        components = {}
        
        # Search and filter controls
        with gr.Row():
            components['search_box'] = gr.Textbox(
                label="Search Players",
                placeholder="Search by name, summoner name, or region...",
                scale=3
            )
            components['region_filter'] = gr.Dropdown(
                label="Filter by Region",
                choices=["All", "NA1", "EUW1", "EUN1", "KR", "BR1", "LA1", "LA2", "OC1", "TR1", "RU", "JP1"],
                value="All",
                scale=1
            )
            components['status_filter'] = gr.Dropdown(
                label="Filter by Status", 
                choices=["All", "Active", "No Data"],
                value="All",
                scale=1
            )
        
        # Table controls
        with gr.Row():
            components['sort_by'] = gr.Dropdown(
                label="Sort By",
                choices=["Name", "Summoner Name", "Region", "Last Updated"],
                value="Name"
            )
            components['sort_order'] = gr.Radio(
                choices=["Ascending", "Descending"],
                value="Ascending",
                label="Sort Order"
            )
            components['page_size'] = gr.Dropdown(
                label="Items per Page",
                choices=["10", "25", "50", "100"],
                value="25"
            )
        
        # Player table
        components['player_table'] = PlayerManagementComponents.create_player_table(players, config)
        
        # Pagination controls
        with gr.Row():
            components['prev_page'] = gr.Button("← Previous", size="sm")
            components['page_info'] = gr.Markdown("Page 1 of 1")
            components['next_page'] = gr.Button("Next →", size="sm")
        
        # Bulk actions
        with gr.Row():
            components['select_all'] = gr.Checkbox(label="Select All")
            components['bulk_delete'] = gr.Button("Delete Selected", variant="stop")
            components['bulk_extract'] = gr.Button("Extract Matches for Selected", variant="secondary")
            components['bulk_export'] = gr.Button("Export Selected", variant="secondary")
        
        return components
    
    @staticmethod
    def create_bulk_import_interface(config: Optional[ComponentConfig] = None) -> Dict[str, gr.Component]:
        """Create comprehensive bulk import interface with validation."""
        if config is None:
            config = ComponentConfig()
        
        components = {}
        
        # File upload section
        components['file_upload'] = gr.File(
            label="Upload Player Data",
            file_types=[".csv", ".xlsx", ".json"],
            file_count="single"
        )
        
        # Format and options
        with gr.Row():
            components['format_selection'] = gr.Radio(
                choices=["CSV", "Excel", "JSON"],
                label="File Format",
                value="CSV",
                info="Select the format of your uploaded file"
            )
            
            components['encoding'] = gr.Dropdown(
                label="File Encoding",
                choices=["utf-8", "utf-16", "latin-1", "cp1252"],
                value="utf-8",
                info="Character encoding of the file"
            )
        
        # CSV-specific options
        with gr.Accordion("CSV Options", open=False):
            with gr.Row():
                components['csv_delimiter'] = gr.Dropdown(
                    label="Delimiter",
                    choices=[",", ";", "\t", "|"],
                    value=",",
                    info="Character used to separate fields"
                )
                components['csv_has_header'] = gr.Checkbox(
                    label="File has header row",
                    value=True,
                    info="First row contains column names"
                )
        
        # Field mapping
        with gr.Accordion("Field Mapping", open=True):
            gr.Markdown("Map your file columns to player fields:")
            
            components['field_mapping'] = {}
            required_fields = ["player_name", "summoner_name"]
            optional_fields = ["riot_tag", "region", "top_pref", "jungle_pref", "middle_pref", "bottom_pref", "support_pref"]
            
            for field in required_fields + optional_fields:
                is_required = field in required_fields
                label = field.replace("_", " ").title()
                if is_required:
                    label += " *"
                
                components['field_mapping'][field] = gr.Dropdown(
                    label=label,
                    choices=["Not Mapped"],
                    value="Not Mapped",
                    info=f"Column containing {label.lower()}"
                )
        
        # Import options
        with gr.Accordion("Import Options", open=True):
            with gr.Row():
                components['skip_duplicates'] = gr.Checkbox(
                    label="Skip Duplicate Players",
                    value=True,
                    info="Skip players that already exist in the database"
                )
                components['validate_api'] = gr.Checkbox(
                    label="Validate with Riot API",
                    value=False,
                    info="Validate player data against Riot API (slower but more accurate)"
                )
            
            with gr.Row():
                components['update_existing'] = gr.Checkbox(
                    label="Update Existing Players",
                    value=False,
                    info="Update data for players that already exist"
                )
                components['dry_run'] = gr.Checkbox(
                    label="Dry Run",
                    value=True,
                    info="Preview import without making changes"
                )
        
        # Preview section
        components['preview_btn'] = gr.Button("Preview Import", variant="secondary")
        components['preview_table'] = gr.DataFrame(
            headers=["Player Name", "Summoner Name", "Region", "Status", "Issues"],
            visible=False
        )
        
        # Import controls
        with gr.Row():
            components['import_btn'] = gr.Button("Import Players", variant="primary")
            components['cancel_btn'] = gr.Button("Cancel", variant="secondary")
        
        # Progress and results
        components['import_progress'] = gr.Progress()
        components['import_status'] = gr.Textbox(
            label="Import Status",
            value="Ready to import",
            interactive=False
        )
        components['import_results'] = gr.Markdown()
        
        # Template download
        with gr.Accordion("Download Template", open=False):
            gr.Markdown("Download a template file to see the expected format:")
            with gr.Row():
                components['download_csv_template'] = gr.Button("Download CSV Template")
                components['download_excel_template'] = gr.Button("Download Excel Template")
                components['download_json_template'] = gr.Button("Download JSON Template")
        
        return components


class AnalyticsComponents:
    """Reusable components for analytics display."""
    
    @staticmethod
    def create_filter_panel(config: Optional[ComponentConfig] = None) -> List[gr.Component]:
        """Create analytics filter panel."""
        if config is None:
            config = ComponentConfig()
        
        components = []
        
        with gr.Accordion("Filters", open=True):
            # Player filter
            player_filter = gr.Dropdown(
                label="Player",
                multiselect=True,
                info="Select one or more players to analyze"
            )
            components.append(player_filter)
            
            # Champion filter
            champion_filter = gr.Dropdown(
                label="Champion",
                multiselect=True,
                info="Filter by specific champions"
            )
            components.append(champion_filter)
            
            # Role filter
            role_filter = gr.CheckboxGroup(
                choices=["Top", "Jungle", "Middle", "Bottom", "Support"],
                label="Roles",
                info="Filter by role positions"
            )
            components.append(role_filter)
            
            # Date range filter
            with gr.Row():
                date_start = gr.Textbox(
                    label="Start Date",
                    placeholder="YYYY-MM-DD",
                    info="Start date for analysis"
                )
                components.append(date_start)
                
                date_end = gr.Textbox(
                    label="End Date", 
                    placeholder="YYYY-MM-DD",
                    info="End date for analysis"
                )
                components.append(date_end)
            
            # Quick date presets
            date_presets = gr.Radio(
                choices=["Last 7 days", "Last 30 days", "Last 90 days", "Custom"],
                label="Date Preset",
                value="Last 30 days"
            )
            components.append(date_presets)
            
            # Minimum games filter
            min_games = gr.Slider(
                minimum=1,
                maximum=50,
                value=5,
                step=1,
                label="Minimum Games",
                info="Minimum number of games for inclusion in analysis"
            )
            components.append(min_games)
        
        return components
    
    @staticmethod
    def create_metrics_display(metrics: Dict[str, Any], config: Optional[ComponentConfig] = None) -> List[gr.Component]:
        """Create metrics display components."""
        if config is None:
            config = ComponentConfig()
        
        components = []
        
        # Key metrics cards
        with gr.Row():
            for metric_name, metric_value in metrics.items():
                with gr.Column():
                    metric_card = gr.Markdown(
                        f"""
                        <div style="text-align: center; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
                            <h3 style="margin: 0; color: {config.theme_color};">{metric_name}</h3>
                            <p style="font-size: 24px; font-weight: bold; margin: 10px 0;">{metric_value}</p>
                        </div>
                        """
                    )
                    components.append(metric_card)
        
        return components
    
    @staticmethod
    def create_export_options(config: Optional[ComponentConfig] = None) -> List[gr.Component]:
        """Create export and sharing options."""
        if config is None:
            config = ComponentConfig()
        
        components = []
        
        with gr.Accordion("Export & Share", open=False):
            # Export format selection
            export_format = gr.Radio(
                choices=["PDF Report", "CSV Data", "JSON Data", "PNG Charts"],
                label="Export Format",
                value="PDF Report"
            )
            components.append(export_format)
            
            # Export options
            with gr.Row():
                include_charts = gr.Checkbox(
                    label="Include Charts",
                    value=True
                )
                components.append(include_charts)
                
                include_raw_data = gr.Checkbox(
                    label="Include Raw Data",
                    value=False
                )
                components.append(include_raw_data)
            
            # Export button
            export_btn = gr.Button("Export Analysis", variant="secondary")
            components.append(export_btn)
            
            # Share options
            gr.Markdown("### Share Options")
            
            with gr.Row():
                generate_link_btn = gr.Button("Generate Share Link")
                components.append(generate_link_btn)
                
                copy_link_btn = gr.Button("Copy to Clipboard")
                components.append(copy_link_btn)
            
            # Share link display
            share_link = gr.Textbox(
                label="Share Link",
                interactive=False,
                placeholder="Generate a link to share this analysis"
            )
            components.append(share_link)
        
        return components


class ProgressComponents:
    """Components for progress tracking and status display."""
    
    @staticmethod
    def create_progress_tracker(config: Optional[ComponentConfig] = None) -> Tuple[gr.Progress, gr.Textbox, gr.Markdown]:
        """Create progress bar and status display."""
        if config is None:
            config = ComponentConfig()
        
        # Progress bar (handled by Gradio internally)
        progress_bar = gr.Progress()
        
        # Status text
        status_text = gr.Textbox(
            label="Current Status",
            value="Ready",
            interactive=False,
            max_lines=1
        )
        
        # Detailed status
        detailed_status = gr.Markdown(
            """
            <div style="padding: 10px; border: 1px solid #ddd; border-radius: 4px;">
                <strong>Status:</strong> Ready to begin operation
            </div>
            """
        )
        
        return progress_bar, status_text, detailed_status
    
    @staticmethod
    def create_status_indicator(status: str, config: Optional[ComponentConfig] = None) -> gr.HTML:
        """Create status indicator with appropriate styling."""
        if config is None:
            config = ComponentConfig()
        
        status_colors = {
            "success": config.success_color,
            "error": config.error_color,
            "warning": config.warning_color,
            "info": config.info_color,
            "loading": config.theme_color
        }
        
        status_icons = {
            "success": "✅",
            "error": "❌",
            "warning": "⚠️",
            "info": "ℹ️",
            "loading": "🔄"
        }
        
        color = status_colors.get(status.lower(), config.info_color)
        icon = status_icons.get(status.lower(), "•")
        
        html_content = f"""
        <div style="
            display: inline-flex;
            align-items: center;
            padding: 8px 12px;
            border-radius: 4px;
            background-color: {color}20;
            border: 1px solid {color};
            color: {color};
            font-weight: 500;
        ">
            <span style="margin-right: 8px; font-size: 16px;">{icon}</span>
            <span>{status.title()}</span>
        </div>
        """
        
        return gr.HTML(html_content)
    
    @staticmethod
    def create_operation_monitor(operation_name: str, config: Optional[ComponentConfig] = None) -> List[gr.Component]:
        """Create operation monitoring interface."""
        if config is None:
            config = ComponentConfig()
        
        components = []
        
        # Operation header
        header = gr.Markdown(f"## {operation_name} Monitor")
        components.append(header)
        
        # Status indicators
        with gr.Row():
            status_indicator = ProgressComponents.create_status_indicator("info", config)
            components.append(status_indicator)
            
            # Progress percentage
            progress_pct = gr.Textbox(
                label="Progress",
                value="0%",
                interactive=False,
                max_lines=1
            )
            components.append(progress_pct)
        
        # Progress details
        progress_details = gr.Markdown("Operation not started")
        components.append(progress_details)
        
        # Control buttons
        with gr.Row():
            start_btn = gr.Button("Start", variant="primary")
            components.append(start_btn)
            
            pause_btn = gr.Button("Pause", variant="secondary")
            components.append(pause_btn)
            
            cancel_btn = gr.Button("Cancel", variant="stop")
            components.append(cancel_btn)
        
        # Log display
        with gr.Accordion("Operation Log", open=False):
            log_display = gr.Textbox(
                label="Log",
                lines=10,
                max_lines=20,
                interactive=False
            )
            components.append(log_display)
        
        return components


class ValidationComponents:
    """Components for real-time form validation."""
    
    @staticmethod
    def create_validation_message(message: str, validation_type: str = "error", 
                                config: Optional[ComponentConfig] = None) -> gr.HTML:
        """Create validation message with appropriate styling."""
        if config is None:
            config = ComponentConfig()
        
        type_styles = {
            "error": {
                "color": config.error_color,
                "background": f"{config.error_color}20",
                "border": config.error_color,
                "icon": "❌"
            },
            "warning": {
                "color": config.warning_color,
                "background": f"{config.warning_color}20",
                "border": config.warning_color,
                "icon": "⚠️"
            },
            "success": {
                "color": config.success_color,
                "background": f"{config.success_color}20",
                "border": config.success_color,
                "icon": "✅"
            },
            "info": {
                "color": config.info_color,
                "background": f"{config.info_color}20",
                "border": config.info_color,
                "icon": "ℹ️"
            }
        }
        
        style = type_styles.get(validation_type, type_styles["info"])
        
        html_content = f"""
        <div style="
            padding: 8px 12px;
            margin: 4px 0;
            border-radius: 4px;
            background-color: {style['background']};
            border: 1px solid {style['border']};
            color: {style['color']};
            font-size: 14px;
            display: flex;
            align-items: center;
        ">
            <span style="margin-right: 8px;">{style['icon']}</span>
            <span>{message}</span>
        </div>
        """
        
        return gr.HTML(html_content)
    
    @staticmethod
    def create_field_validator(field_name: str, validation_rules: Dict[str, Any],
                             config: Optional[ComponentConfig] = None) -> Tuple[gr.Component, Callable]:
        """Create field validator with real-time validation."""
        if config is None:
            config = ComponentConfig()
        
        # Validation message display
        validation_display = gr.HTML("")
        
        def validate_field(value: str) -> str:
            """Validate field value and return validation message."""
            if not value and validation_rules.get("required", False):
                return ValidationComponents.create_validation_message(
                    f"{field_name} is required", "error", config
                ).value
            
            # Length validation
            if "min_length" in validation_rules and len(value) < validation_rules["min_length"]:
                return ValidationComponents.create_validation_message(
                    f"{field_name} must be at least {validation_rules['min_length']} characters",
                    "error", config
                ).value
            
            if "max_length" in validation_rules and len(value) > validation_rules["max_length"]:
                return ValidationComponents.create_validation_message(
                    f"{field_name} must be no more than {validation_rules['max_length']} characters",
                    "error", config
                ).value
            
            # Pattern validation
            if "pattern" in validation_rules:
                import re
                if not re.match(validation_rules["pattern"], value):
                    return ValidationComponents.create_validation_message(
                        validation_rules.get("pattern_message", f"{field_name} format is invalid"),
                        "error", config
                    ).value
            
            # Custom validation
            if "custom_validator" in validation_rules:
                custom_result = validation_rules["custom_validator"](value)
                if custom_result is not True:
                    return ValidationComponents.create_validation_message(
                        custom_result, "error", config
                    ).value
            
            # Success message
            if value:
                return ValidationComponents.create_validation_message(
                    f"{field_name} is valid", "success", config
                ).value
            
            return ""
        
        return validation_display, validate_field


class AccessibilityComponents:
    """Components for WCAG compliance and accessibility."""
    
    @staticmethod
    def create_accessible_button(text: str, description: str, variant: str = "primary",
                               config: Optional[ComponentConfig] = None) -> gr.Button:
        """Create accessible button with proper ARIA labels."""
        if config is None:
            config = ComponentConfig()
        
        return gr.Button(
            value=text,
            variant=variant,
            elem_id=f"btn-{text.lower().replace(' ', '-')}",
            # Note: Gradio doesn't directly support ARIA attributes,
            # but we can add them via custom CSS/JS if needed
        )
    
    @staticmethod
    def create_accessible_form(form_title: str, form_description: str,
                             config: Optional[ComponentConfig] = None) -> List[gr.Component]:
        """Create accessible form with proper structure."""
        if config is None:
            config = ComponentConfig()
        
        components = []
        
        # Form header with description
        form_header = gr.Markdown(f"""
        # {form_title}
        
        {form_description}
        
        *Required fields are marked with an asterisk (*)*
        """)
        components.append(form_header)
        
        return components
    
    @staticmethod
    def create_skip_navigation() -> gr.HTML:
        """Create skip navigation links for keyboard users."""
        html_content = """
        <div style="position: absolute; left: -9999px; width: 1px; height: 1px;">
            <a href="#main-content" style="position: absolute; left: 6px; top: 7px; z-index: 999; 
               text-decoration: none; background: #000; color: #fff; padding: 8px 16px;">
                Skip to main content
            </a>
        </div>
        """
        return gr.HTML(html_content)
    
    @staticmethod
    def create_screen_reader_announcement(message: str) -> gr.HTML:
        """Create screen reader announcement."""
        html_content = f"""
        <div aria-live="polite" aria-atomic="true" style="
            position: absolute; 
            left: -10000px; 
            width: 1px; 
            height: 1px; 
            overflow: hidden;
        ">
            {message}
        </div>
        """
        return gr.HTML(html_content)


class ExportComponents:
    """Components for data export and sharing."""
    
    @staticmethod
    def create_export_interface(export_types: List[str], config: Optional[ComponentConfig] = None) -> List[gr.Component]:
        """Create comprehensive export interface."""
        if config is None:
            config = ComponentConfig()
        
        components = []
        
        # Export type selection
        export_type = gr.Radio(
            choices=export_types,
            label="Export Format",
            value=export_types[0] if export_types else "PDF"
        )
        components.append(export_type)
        
        # Export options
        with gr.Accordion("Export Options", open=False):
            # Include options
            include_metadata = gr.Checkbox(
                label="Include Metadata",
                value=True,
                info="Include analysis parameters and timestamps"
            )
            components.append(include_metadata)
            
            include_charts = gr.Checkbox(
                label="Include Visualizations",
                value=True,
                info="Include charts and graphs in export"
            )
            components.append(include_charts)
            
            # Quality settings
            chart_quality = gr.Slider(
                minimum=1,
                maximum=5,
                value=3,
                step=1,
                label="Chart Quality",
                info="Higher quality = larger file size"
            )
            components.append(chart_quality)
        
        # Export button
        export_btn = gr.Button("Generate Export", variant="primary")
        components.append(export_btn)
        
        # Download link
        download_link = gr.File(
            label="Download Export",
            visible=False
        )
        components.append(download_link)
        
        return components
    
    @staticmethod
    def create_sharing_interface(config: Optional[ComponentConfig] = None) -> List[gr.Component]:
        """Create sharing and collaboration interface."""
        if config is None:
            config = ComponentConfig()
        
        components = []
        
        # Sharing options
        with gr.Accordion("Share Analysis", open=False):
            # Privacy settings
            privacy_level = gr.Radio(
                choices=["Public", "Unlisted", "Private"],
                label="Privacy Level",
                value="Unlisted",
                info="Control who can access the shared analysis"
            )
            components.append(privacy_level)
            
            # Expiration settings
            expiration = gr.Dropdown(
                choices=["Never", "1 hour", "1 day", "1 week", "1 month"],
                label="Link Expiration",
                value="1 week",
                info="When the share link should expire"
            )
            components.append(expiration)
            
            # Generate share link
            generate_link_btn = gr.Button("Generate Share Link", variant="secondary")
            components.append(generate_link_btn)
            
            # Share link display
            share_link = gr.Textbox(
                label="Share Link",
                interactive=False,
                placeholder="Click 'Generate Share Link' to create a shareable URL"
            )
            components.append(share_link)
            
            # Quick share buttons
            with gr.Row():
                copy_btn = gr.Button("Copy Link", size="sm")
                components.append(copy_btn)
                
                email_btn = gr.Button("Email Link", size="sm")
                components.append(email_btn)
        
        return components


# Utility functions for component management
class NotificationComponents:
    """Components for user notifications and alerts."""
    
    @staticmethod
    def create_toast_notification(message: str, notification_type: str = "info",
                                config: Optional[ComponentConfig] = None) -> gr.HTML:
        """Create toast notification component."""
        if config is None:
            config = ComponentConfig()
        
        type_styles = {
            "success": {
                "color": config.success_color,
                "background": f"{config.success_color}15",
                "border": config.success_color,
                "icon": "✅"
            },
            "error": {
                "color": config.error_color,
                "background": f"{config.error_color}15",
                "border": config.error_color,
                "icon": "❌"
            },
            "warning": {
                "color": config.warning_color,
                "background": f"{config.warning_color}15",
                "border": config.warning_color,
                "icon": "⚠️"
            },
            "info": {
                "color": config.info_color,
                "background": f"{config.info_color}15",
                "border": config.info_color,
                "icon": "ℹ️"
            }
        }
        
        style = type_styles.get(notification_type, type_styles["info"])
        
        html_content = f"""
        <div style="
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 1000;
            padding: 12px 16px;
            border-radius: 6px;
            background-color: {style['background']};
            border: 1px solid {style['border']};
            color: {style['color']};
            font-weight: 500;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            display: flex;
            align-items: center;
            max-width: 400px;
            animation: slideIn 0.3s ease-out;
        ">
            <span style="margin-right: 10px; font-size: 18px;">{style['icon']}</span>
            <span>{message}</span>
        </div>
        <style>
            @keyframes slideIn {{
                from {{ transform: translateX(100%); opacity: 0; }}
                to {{ transform: translateX(0); opacity: 1; }}
            }}
        </style>
        """
        
        return gr.HTML(html_content)
    
    @staticmethod
    def create_alert_banner(message: str, alert_type: str = "info", dismissible: bool = True,
                          config: Optional[ComponentConfig] = None) -> gr.HTML:
        """Create alert banner component."""
        if config is None:
            config = ComponentConfig()
        
        type_styles = {
            "success": {"color": config.success_color, "icon": "✅"},
            "error": {"color": config.error_color, "icon": "❌"},
            "warning": {"color": config.warning_color, "icon": "⚠️"},
            "info": {"color": config.info_color, "icon": "ℹ️"}
        }
        
        style = type_styles.get(alert_type, type_styles["info"])
        dismiss_button = """
        <button onclick="this.parentElement.style.display='none'" style="
            background: none;
            border: none;
            color: inherit;
            font-size: 18px;
            cursor: pointer;
            margin-left: auto;
            padding: 0 4px;
        ">×</button>
        """ if dismissible else ""
        
        html_content = f"""
        <div style="
            padding: 12px 16px;
            margin: 8px 0;
            border-radius: 4px;
            background-color: {style['color']}15;
            border: 1px solid {style['color']};
            color: {style['color']};
            display: flex;
            align-items: center;
        ">
            <span style="margin-right: 10px; font-size: 16px;">{style['icon']}</span>
            <span style="flex: 1;">{message}</span>
            {dismiss_button}
        </div>
        """
        
        return gr.HTML(html_content)


class LoadingComponents:
    """Components for loading states and spinners."""
    
    @staticmethod
    def create_loading_spinner(message: str = "Loading...", size: str = "medium",
                             config: Optional[ComponentConfig] = None) -> gr.HTML:
        """Create loading spinner component."""
        if config is None:
            config = ComponentConfig()
        
        sizes = {
            "small": {"size": "20px", "font": "14px"},
            "medium": {"size": "32px", "font": "16px"},
            "large": {"size": "48px", "font": "18px"}
        }
        
        size_config = sizes.get(size, sizes["medium"])
        
        html_content = f"""
        <div style="
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 20px;
            text-align: center;
        ">
            <div style="
                width: {size_config['size']};
                height: {size_config['size']};
                border: 3px solid #f3f3f3;
                border-top: 3px solid {config.theme_color};
                border-radius: 50%;
                animation: spin 1s linear infinite;
                margin-bottom: 12px;
            "></div>
            <span style="
                color: #666;
                font-size: {size_config['font']};
                font-weight: 500;
            ">{message}</span>
        </div>
        <style>
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
        </style>
        """
        
        return gr.HTML(html_content)
    
    @staticmethod
    def create_skeleton_loader(lines: int = 3, config: Optional[ComponentConfig] = None) -> gr.HTML:
        """Create skeleton loading placeholder."""
        if config is None:
            config = ComponentConfig()
        
        skeleton_lines = ""
        for i in range(lines):
            width = "100%" if i < lines - 1 else "75%"  # Last line shorter
            skeleton_lines += f"""
            <div style="
                height: 16px;
                background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
                background-size: 200% 100%;
                animation: loading 1.5s infinite;
                border-radius: 4px;
                margin-bottom: 8px;
                width: {width};
            "></div>
            """
        
        html_content = f"""
        <div style="padding: 16px;">
            {skeleton_lines}
        </div>
        <style>
            @keyframes loading {{
                0% {{ background-position: 200% 0; }}
                100% {{ background-position: -200% 0; }}
            }}
        </style>
        """
        
        return gr.HTML(html_content)


class LayoutComponents:
    """Components for layout and structure."""
    
    @staticmethod
    def create_card_container(title: str, content: List[gr.Component],
                            config: Optional[ComponentConfig] = None) -> List[gr.Component]:
        """Create card container with title and content."""
        if config is None:
            config = ComponentConfig()
        
        components = []
        
        # Card header
        header = gr.HTML(f"""
        <div style="
            background: linear-gradient(135deg, {config.theme_color}10, {config.theme_color}05);
            border: 1px solid {config.theme_color}30;
            border-radius: 8px 8px 0 0;
            padding: 16px 20px;
            margin: 0;
        ">
            <h3 style="
                margin: 0;
                color: {config.theme_color};
                font-size: 18px;
                font-weight: 600;
            ">{title}</h3>
        </div>
        """)
        components.append(header)
        
        # Card content wrapper
        with gr.Group():
            content_wrapper = gr.HTML("""
            <div style="
                border: 1px solid #e0e0e0;
                border-top: none;
                border-radius: 0 0 8px 8px;
                padding: 20px;
                background: white;
            ">
            """)
            components.append(content_wrapper)
            
            # Add content components
            components.extend(content)
            
            # Close wrapper
            close_wrapper = gr.HTML("</div>")
            components.append(close_wrapper)
        
        return components
    
    @staticmethod
    def create_section_divider(title: str = "", config: Optional[ComponentConfig] = None) -> gr.HTML:
        """Create section divider with optional title."""
        if config is None:
            config = ComponentConfig()
        
        if title:
            html_content = f"""
            <div style="
                display: flex;
                align-items: center;
                margin: 24px 0 16px 0;
            ">
                <hr style="
                    flex: 1;
                    border: none;
                    height: 1px;
                    background: linear-gradient(to right, transparent, #ddd, transparent);
                ">
                <span style="
                    padding: 0 16px;
                    color: #666;
                    font-weight: 500;
                    font-size: 14px;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                ">{title}</span>
                <hr style="
                    flex: 1;
                    border: none;
                    height: 1px;
                    background: linear-gradient(to right, transparent, #ddd, transparent);
                ">
            </div>
            """
        else:
            html_content = """
            <hr style="
                border: none;
                height: 1px;
                background: linear-gradient(to right, transparent, #ddd, transparent);
                margin: 24px 0;
            ">
            """
        
        return gr.HTML(html_content)


class ComponentManager:
    """Manages component lifecycle and interactions."""
    
    def __init__(self, config: Optional[ComponentConfig] = None):
        """Initialize component manager."""
        self.config = config or ComponentConfig()
        self.logger = logging.getLogger(__name__)
        self.component_registry: Dict[str, gr.Component] = {}
    
    def register_component(self, name: str, component: gr.Component) -> None:
        """Register a component for later reference."""
        self.component_registry[name] = component
        self.logger.debug(f"Registered component: {name}")
    
    def get_component(self, name: str) -> Optional[gr.Component]:
        """Get a registered component by name."""
        return self.component_registry.get(name)
    
    def setup_component_interactions(self, interactions: List[Dict[str, Any]]) -> None:
        """Set up interactions between components."""
        for interaction in interactions:
            try:
                source = self.get_component(interaction["source"])
                target = self.get_component(interaction["target"])
                event_type = interaction.get("event", "click")
                handler = interaction["handler"]
                
                if source and target:
                    if event_type == "click" and hasattr(source, "click"):
                        source.click(fn=handler, outputs=target)
                    elif event_type == "change" and hasattr(source, "change"):
                        source.change(fn=handler, outputs=target)
                    # Add more event types as needed
                    
                    self.logger.debug(f"Set up interaction: {interaction['source']} -> {interaction['target']}")
                
            except Exception as e:
                self.logger.error(f"Failed to set up interaction: {e}")
    
    def create_component_group(self, group_name: str, components: List[gr.Component]) -> None:
        """Create a group of related components."""
        for i, component in enumerate(components):
            self.register_component(f"{group_name}_{i}", component)
        
        self.logger.info(f"Created component group: {group_name} with {len(components)} components")
    
    def create_themed_interface(self, title: str, components: List[gr.Component]) -> gr.Blocks:
        """Create a themed Gradio interface with consistent styling."""
        css = f"""
        .gradio-container {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }}
        
        .main-header {{
            background: linear-gradient(135deg, {self.config.theme_color}, {self.config.theme_color}dd);
            color: white;
            padding: 20px;
            text-align: center;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        
        .component-card {{
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 16px;
            margin: 8px 0;
            background: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}
        
        .status-success {{ color: {self.config.success_color}; }}
        .status-error {{ color: {self.config.error_color}; }}
        .status-warning {{ color: {self.config.warning_color}; }}
        .status-info {{ color: {self.config.info_color}; }}
        """
        
        with gr.Blocks(css=css, title=title, theme=gr.themes.Soft()) as interface:
            # Add header
            gr.HTML(f"""
            <div class="main-header">
                <h1 style="margin: 0; font-size: 28px; font-weight: 700;">{title}</h1>
                <p style="margin: 8px 0 0 0; opacity: 0.9;">League of Legends Team Optimization Platform</p>
            </div>
            """)
            
            # Add components
            for component in components:
                component.render()
        
        return interface