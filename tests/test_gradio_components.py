"""
Unit tests for Gradio Components Library

Tests the reusable component library for consistent UI patterns,
including player management, analytics, progress tracking, validation,
accessibility, and export components.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
import pytest
from datetime import datetime
import sys
import os

# Add the parent directory to the path to import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lol_team_optimizer.gradio_components import (
    ComponentConfig,
    PlayerManagementComponents,
    AnalyticsComponents,
    ProgressComponents,
    ValidationComponents,
    AccessibilityComponents,
    ExportComponents,
    NotificationComponents,
    LoadingComponents,
    LayoutComponents,
    ComponentManager
)
from lol_team_optimizer.models import Player


class TestComponentConfig(unittest.TestCase):
    """Test ComponentConfig dataclass."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = ComponentConfig()
        
        self.assertEqual(config.theme_color, "rgb(0, 123, 255)")
        self.assertEqual(config.success_color, "#155724")
        self.assertEqual(config.error_color, "#dc3545")
        self.assertEqual(config.warning_color, "#856404")
        self.assertEqual(config.info_color, "#0c5460")
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = ComponentConfig(
            theme_color="rgb(255, 0, 0)",
            success_color="#00ff00",
            error_color="#ff0000"
        )
        
        self.assertEqual(config.theme_color, "rgb(255, 0, 0)")
        self.assertEqual(config.success_color, "#00ff00")
        self.assertEqual(config.error_color, "#ff0000")
        # Default values should remain
        self.assertEqual(config.warning_color, "#856404")
        self.assertEqual(config.info_color, "#0c5460")


class TestPlayerManagementComponents(unittest.TestCase):
    """Test PlayerManagementComponents class."""
    
    @patch('lol_team_optimizer.gradio_components.gr')
    def test_create_player_form(self, mock_gr):
        """Test creating player form components."""
        # Mock Gradio components
        mock_textbox = Mock()
        mock_dropdown = Mock()
        mock_gr.Textbox.return_value = mock_textbox
        mock_gr.Dropdown.return_value = mock_dropdown
        
        components = PlayerManagementComponents.create_player_form()
        
        # Should return 4 components: name, summoner_name, riot_id, region
        self.assertEqual(len(components), 4)
        
        # Verify Textbox calls for text inputs
        self.assertEqual(mock_gr.Textbox.call_count, 3)
        
        # Verify Dropdown call for region
        mock_gr.Dropdown.assert_called_once()
        
        # Check that region dropdown has proper choices
        dropdown_call = mock_gr.Dropdown.call_args
        self.assertIn('choices', dropdown_call.kwargs)
        choices = dropdown_call.kwargs['choices']
        self.assertIsInstance(choices, list)
        self.assertGreater(len(choices), 0)
        
        # Verify default region is set
        self.assertEqual(dropdown_call.kwargs['value'], 'na1')
    
    @patch('lol_team_optimizer.gradio_components.gr')
    def test_create_player_form_with_config(self, mock_gr):
        """Test creating player form with custom config."""
        config = ComponentConfig(theme_color="rgb(255, 0, 0)")
        
        mock_textbox = Mock()
        mock_dropdown = Mock()
        mock_gr.Textbox.return_value = mock_textbox
        mock_gr.Dropdown.return_value = mock_dropdown
        
        components = PlayerManagementComponents.create_player_form(config)
        
        self.assertEqual(len(components), 4)
        self.assertEqual(mock_gr.Textbox.call_count, 3)
        mock_gr.Dropdown.assert_called_once()
    
    @patch('lol_team_optimizer.gradio_components.gr')
    def test_create_player_table(self, mock_gr):
        """Test creating player table."""
        # Create mock players with proper Player model fields
        player1 = Player(name="Player1", summoner_name="Summoner1", puuid="puuid1")
        player1.riot_id = "Player1#NA1"  # Add as attribute
        player1.region = "na1"
        
        player2 = Player(name="Player2", summoner_name="Summoner2", puuid="")
        player2.riot_id = "Player2#NA1"  # Add as attribute
        player2.region = "euw1"
        
        players = [player1, player2]
        
        mock_dataframe = Mock()
        mock_gr.DataFrame.return_value = mock_dataframe
        
        result = PlayerManagementComponents.create_player_table(players)
        
        # Verify DataFrame was created
        mock_gr.DataFrame.assert_called_once()
        
        # Check call arguments
        call_args = mock_gr.DataFrame.call_args
        self.assertIn('value', call_args.kwargs)
        self.assertIn('headers', call_args.kwargs)
        self.assertIn('datatype', call_args.kwargs)
        
        # Verify table data structure
        table_data = call_args.kwargs['value']
        self.assertEqual(len(table_data), 2)  # Two players
        
        # Check first player data
        player1_row = table_data[0]
        self.assertEqual(player1_row[0], "Player1")  # Name
        self.assertEqual(player1_row[1], "Summoner1")  # Summoner name
        self.assertEqual(player1_row[2], "Player1#NA1")  # Riot ID
        self.assertEqual(player1_row[3], "NA1")  # Region (uppercase)
        self.assertIn("✅", player1_row[4])  # Status (has PUUID)
        
        # Check second player data
        player2_row = table_data[1]
        self.assertEqual(player2_row[0], "Player2")
        self.assertIn("⚠️", player2_row[4])  # Status (no PUUID)
        
        # Verify headers
        headers = call_args.kwargs['headers']
        expected_headers = ["Name", "Summoner Name", "Riot ID", "Region", "Status", "Last Updated"]
        self.assertEqual(headers, expected_headers)
    
    @patch('lol_team_optimizer.gradio_components.gr')
    def test_create_bulk_import_interface(self, mock_gr):
        """Test creating bulk import interface."""
        # Mock Gradio components
        mock_file = Mock()
        mock_radio = Mock()
        mock_checkbox = Mock()
        mock_button = Mock()
        mock_markdown = Mock()
        mock_accordion = Mock()
        
        mock_gr.File.return_value = mock_file
        mock_gr.Radio.return_value = mock_radio
        mock_gr.Checkbox.return_value = mock_checkbox
        mock_gr.Button.return_value = mock_button
        mock_gr.Markdown.return_value = mock_markdown
        mock_gr.Accordion.return_value.__enter__ = Mock(return_value=mock_accordion)
        mock_gr.Accordion.return_value.__exit__ = Mock(return_value=None)
        
        components = PlayerManagementComponents.create_bulk_import_interface()
        
        # Should return 6 components: file, format, skip_duplicates, validate_api, button, results
        self.assertEqual(len(components), 6)
        
        # Verify component creation calls
        mock_gr.File.assert_called_once()
        mock_gr.Radio.assert_called_once()
        self.assertEqual(mock_gr.Checkbox.call_count, 2)  # Two checkboxes
        mock_gr.Button.assert_called_once()
        mock_gr.Markdown.assert_called_once()
        
        # Check file upload configuration
        file_call = mock_gr.File.call_args
        self.assertIn('file_types', file_call.kwargs)
        file_types = file_call.kwargs['file_types']
        self.assertIn('.csv', file_types)
        self.assertIn('.xlsx', file_types)
        self.assertIn('.json', file_types)
        
        # Check format selection
        radio_call = mock_gr.Radio.call_args
        self.assertIn('choices', radio_call.kwargs)
        choices = radio_call.kwargs['choices']
        self.assertIn('CSV', choices)
        self.assertIn('Excel', choices)
        self.assertIn('JSON', choices)


class TestAnalyticsComponents(unittest.TestCase):
    """Test AnalyticsComponents class."""
    
    @patch('lol_team_optimizer.gradio_components.gr')
    def test_create_filter_panel(self, mock_gr):
        """Test creating analytics filter panel."""
        # Mock Gradio components
        mock_dropdown = Mock()
        mock_checkbox_group = Mock()
        mock_textbox = Mock()
        mock_radio = Mock()
        mock_slider = Mock()
        mock_row = Mock()
        mock_accordion = Mock()
        
        mock_gr.Dropdown.return_value = mock_dropdown
        mock_gr.CheckboxGroup.return_value = mock_checkbox_group
        mock_gr.Textbox.return_value = mock_textbox
        mock_gr.Radio.return_value = mock_radio
        mock_gr.Slider.return_value = mock_slider
        mock_gr.Row.return_value.__enter__ = Mock(return_value=mock_row)
        mock_gr.Row.return_value.__exit__ = Mock(return_value=None)
        mock_gr.Accordion.return_value.__enter__ = Mock(return_value=mock_accordion)
        mock_gr.Accordion.return_value.__exit__ = Mock(return_value=None)
        
        components = AnalyticsComponents.create_filter_panel()
        
        # Should return 8 components: player, champion, role, date_start, date_end, date_presets, min_games
        self.assertEqual(len(components), 7)
        
        # Verify component creation calls
        self.assertEqual(mock_gr.Dropdown.call_count, 2)  # Player and champion filters
        mock_gr.CheckboxGroup.assert_called_once()  # Role filter
        self.assertEqual(mock_gr.Textbox.call_count, 2)  # Date start and end
        mock_gr.Radio.assert_called_once()  # Date presets
        mock_gr.Slider.assert_called_once()  # Min games
        
        # Check role filter choices
        checkbox_call = mock_gr.CheckboxGroup.call_args
        self.assertIn('choices', checkbox_call.kwargs)
        choices = checkbox_call.kwargs['choices']
        expected_roles = ["Top", "Jungle", "Middle", "Bottom", "Support"]
        self.assertEqual(choices, expected_roles)
        
        # Check date presets
        radio_call = mock_gr.Radio.call_args
        self.assertIn('choices', radio_call.kwargs)
        preset_choices = radio_call.kwargs['choices']
        self.assertIn("Last 7 days", preset_choices)
        self.assertIn("Last 30 days", preset_choices)
        self.assertIn("Last 90 days", preset_choices)
        self.assertIn("Custom", preset_choices)
    
    @patch('lol_team_optimizer.gradio_components.gr')
    def test_create_metrics_display(self, mock_gr):
        """Test creating metrics display."""
        metrics = {
            "Win Rate": "65.2%",
            "Average KDA": "2.34",
            "Games Played": "42"
        }
        
        mock_markdown = Mock()
        mock_row = Mock()
        mock_column = Mock()
        
        mock_gr.Markdown.return_value = mock_markdown
        mock_gr.Row.return_value.__enter__ = Mock(return_value=mock_row)
        mock_gr.Row.return_value.__exit__ = Mock(return_value=None)
        mock_gr.Column.return_value.__enter__ = Mock(return_value=mock_column)
        mock_gr.Column.return_value.__exit__ = Mock(return_value=None)
        
        components = AnalyticsComponents.create_metrics_display(metrics)
        
        # Should return one component per metric
        self.assertEqual(len(components), 3)
        
        # Verify Markdown components were created
        self.assertEqual(mock_gr.Markdown.call_count, 3)
        
        # Check that metric values are included in markdown
        markdown_calls = mock_gr.Markdown.call_args_list
        for i, (metric_name, metric_value) in enumerate(metrics.items()):
            markdown_content = markdown_calls[i][0][0]  # First positional argument
            self.assertIn(metric_name, markdown_content)
            self.assertIn(metric_value, markdown_content)
    
    @patch('lol_team_optimizer.gradio_components.gr')
    def test_create_export_options(self, mock_gr):
        """Test creating export options."""
        # Mock Gradio components
        mock_radio = Mock()
        mock_checkbox = Mock()
        mock_button = Mock()
        mock_textbox = Mock()
        mock_markdown = Mock()
        mock_row = Mock()
        mock_accordion = Mock()
        
        mock_gr.Radio.return_value = mock_radio
        mock_gr.Checkbox.return_value = mock_checkbox
        mock_gr.Button.return_value = mock_button
        mock_gr.Textbox.return_value = mock_textbox
        mock_gr.Markdown.return_value = mock_markdown
        mock_gr.Row.return_value.__enter__ = Mock(return_value=mock_row)
        mock_gr.Row.return_value.__exit__ = Mock(return_value=None)
        mock_gr.Accordion.return_value.__enter__ = Mock(return_value=mock_accordion)
        mock_gr.Accordion.return_value.__exit__ = Mock(return_value=None)
        
        components = AnalyticsComponents.create_export_options()
        
        # Should return 7 components: format, include_charts, include_raw_data, export_btn, generate_link_btn, copy_link_btn, share_link
        self.assertEqual(len(components), 7)
        
        # Verify component creation calls
        mock_gr.Radio.assert_called_once()  # Export format
        self.assertEqual(mock_gr.Checkbox.call_count, 2)  # Include options
        self.assertEqual(mock_gr.Button.call_count, 3)  # Export, generate link, and copy buttons
        mock_gr.Textbox.assert_called_once()  # Share link
        
        # Check export format choices
        radio_call = mock_gr.Radio.call_args
        self.assertIn('choices', radio_call.kwargs)
        format_choices = radio_call.kwargs['choices']
        self.assertIn("PDF Report", format_choices)
        self.assertIn("CSV Data", format_choices)
        self.assertIn("JSON Data", format_choices)
        self.assertIn("PNG Charts", format_choices)


class TestProgressComponents(unittest.TestCase):
    """Test ProgressComponents class."""
    
    @patch('lol_team_optimizer.gradio_components.gr')
    def test_create_progress_tracker(self, mock_gr):
        """Test creating progress tracker."""
        mock_progress = Mock()
        mock_textbox = Mock()
        mock_markdown = Mock()
        
        mock_gr.Progress.return_value = mock_progress
        mock_gr.Textbox.return_value = mock_textbox
        mock_gr.Markdown.return_value = mock_markdown
        
        progress_bar, status_text, detailed_status = ProgressComponents.create_progress_tracker()
        
        # Verify components were created
        mock_gr.Progress.assert_called_once()
        mock_gr.Textbox.assert_called_once()
        mock_gr.Markdown.assert_called_once()
        
        # Check return values
        self.assertEqual(progress_bar, mock_progress)
        self.assertEqual(status_text, mock_textbox)
        self.assertEqual(detailed_status, mock_markdown)
        
        # Check textbox configuration
        textbox_call = mock_gr.Textbox.call_args
        self.assertEqual(textbox_call.kwargs['value'], "Ready")
        self.assertFalse(textbox_call.kwargs['interactive'])
    
    @patch('lol_team_optimizer.gradio_components.gr')
    def test_create_status_indicator(self, mock_gr):
        """Test creating status indicators."""
        mock_html = Mock()
        mock_gr.HTML.return_value = mock_html
        
        # Test different status types
        statuses = ["success", "error", "warning", "info", "loading"]
        
        for status in statuses:
            result = ProgressComponents.create_status_indicator(status)
            self.assertEqual(result, mock_html)
        
        # Verify HTML was called for each status
        self.assertEqual(mock_gr.HTML.call_count, len(statuses))
        
        # Check that HTML content includes appropriate icons and colors
        html_calls = mock_gr.HTML.call_args_list
        
        # Success should have green color and checkmark
        success_html = html_calls[0][0][0]
        self.assertIn("✅", success_html)
        self.assertIn("#155724", success_html)
        
        # Error should have red color and X mark
        error_html = html_calls[1][0][0]
        self.assertIn("❌", error_html)
        self.assertIn("#dc3545", error_html)
    
    @patch('lol_team_optimizer.gradio_components.gr')
    def test_create_operation_monitor(self, mock_gr):
        """Test creating operation monitor."""
        # Mock all Gradio components
        mock_markdown = Mock()
        mock_textbox = Mock()
        mock_button = Mock()
        mock_row = Mock()
        mock_accordion = Mock()
        
        mock_gr.Markdown.return_value = mock_markdown
        mock_gr.Textbox.return_value = mock_textbox
        mock_gr.Button.return_value = mock_button
        mock_gr.Row.return_value.__enter__ = Mock(return_value=mock_row)
        mock_gr.Row.return_value.__exit__ = Mock(return_value=None)
        mock_gr.Accordion.return_value.__enter__ = Mock(return_value=mock_accordion)
        mock_gr.Accordion.return_value.__exit__ = Mock(return_value=None)
        
        # Mock the status indicator creation
        with patch.object(ProgressComponents, 'create_status_indicator') as mock_status_indicator:
            mock_status_indicator.return_value = Mock()
            
            components = ProgressComponents.create_operation_monitor("Test Operation")
        
        # Should return 8 components: header, status_indicator, progress_pct, progress_details, start_btn, pause_btn, cancel_btn, log_display
        self.assertEqual(len(components), 8)
        
        # Verify component creation calls
        self.assertEqual(mock_gr.Markdown.call_count, 2)  # Header and progress details
        self.assertEqual(mock_gr.Textbox.call_count, 2)  # Progress percentage and log
        self.assertEqual(mock_gr.Button.call_count, 3)  # Start, pause, cancel buttons
        
        # Check operation name in header
        header_call = mock_gr.Markdown.call_args_list[0]
        header_content = header_call[0][0]
        self.assertIn("Test Operation", header_content)


class TestValidationComponents(unittest.TestCase):
    """Test ValidationComponents class."""
    
    @patch('lol_team_optimizer.gradio_components.gr')
    def test_create_validation_message(self, mock_gr):
        """Test creating validation messages."""
        mock_html = Mock()
        mock_gr.HTML.return_value = mock_html
        
        # Test different validation types
        message = "Test validation message"
        
        # Test error message
        result = ValidationComponents.create_validation_message(message, "error")
        self.assertEqual(result, mock_html)
        
        # Check HTML content
        html_call = mock_gr.HTML.call_args
        html_content = html_call[0][0]
        self.assertIn(message, html_content)
        self.assertIn("❌", html_content)  # Error icon
        self.assertIn("#dc3545", html_content)  # Error color
        
        # Test success message
        ValidationComponents.create_validation_message(message, "success")
        success_html_call = mock_gr.HTML.call_args
        success_html_content = success_html_call[0][0]
        self.assertIn("✅", success_html_content)  # Success icon
        self.assertIn("#155724", success_html_content)  # Success color
    
    @patch('lol_team_optimizer.gradio_components.ValidationComponents.create_validation_message')
    @patch('lol_team_optimizer.gradio_components.gr')
    def test_create_field_validator(self, mock_gr, mock_create_validation_message):
        """Test creating field validator."""
        mock_html = Mock()
        mock_gr.HTML.return_value = mock_html
        
        # Mock validation message creation to return HTML components with .value attribute
        def mock_validation_message_side_effect(message, msg_type, config):
            mock_msg = Mock()
            mock_msg.value = f"<div>{message}</div>"
            return mock_msg
        
        mock_create_validation_message.side_effect = mock_validation_message_side_effect
        
        validation_rules = {
            "required": True,
            "min_length": 3,
            "max_length": 20,
            "pattern": r"^[a-zA-Z0-9]+$",
            "pattern_message": "Only alphanumeric characters allowed"
        }
        
        validation_display, validate_func = ValidationComponents.create_field_validator(
            "Test Field", validation_rules
        )
        
        # Should return HTML component and validation function
        self.assertEqual(validation_display, mock_html)
        self.assertIsNotNone(validate_func)
        self.assertTrue(callable(validate_func))
        
        # Test validation function
        # Empty value (required field)
        result = validate_func("")
        self.assertIn("Test Field is required", result)
        
        # Too short
        result = validate_func("ab")
        self.assertIn("at least 3 characters", result)
        
        # Too long
        result = validate_func("a" * 25)
        self.assertIn("no more than 20 characters", result)
        
        # Invalid pattern
        result = validate_func("test@#$")
        self.assertIn("Only alphanumeric characters allowed", result)
        
        # Valid value
        result = validate_func("validtest123")
        self.assertIn("Test Field is valid", result)
    
    @patch('lol_team_optimizer.gradio_components.ValidationComponents.create_validation_message')
    def test_field_validator_custom_validation(self, mock_create_validation_message):
        """Test field validator with custom validation function."""
        def custom_validator(value):
            if value == "forbidden":
                return "This value is not allowed"
            return True
        
        validation_rules = {
            "custom_validator": custom_validator
        }
        
        # Mock validation message creation to return HTML components with .value attribute
        def mock_validation_message_side_effect(message, msg_type, config):
            mock_msg = Mock()
            mock_msg.value = f"<div>{message}</div>"
            return mock_msg
        
        mock_create_validation_message.side_effect = mock_validation_message_side_effect
        
        with patch('lol_team_optimizer.gradio_components.gr.HTML') as mock_html:
            mock_html.return_value = Mock()
            
            _, validate_func = ValidationComponents.create_field_validator(
                "Custom Field", validation_rules
            )
            
            # Test custom validation
            result = validate_func("forbidden")
            self.assertIn("This value is not allowed", result)
            
            result = validate_func("allowed")
            self.assertIn("Custom Field is valid", result)


class TestAccessibilityComponents(unittest.TestCase):
    """Test AccessibilityComponents class."""
    
    @patch('lol_team_optimizer.gradio_components.gr')
    def test_create_accessible_button(self, mock_gr):
        """Test creating accessible button."""
        mock_button = Mock()
        mock_gr.Button.return_value = mock_button
        
        result = AccessibilityComponents.create_accessible_button(
            "Test Button", "Button description", "primary"
        )
        
        self.assertEqual(result, mock_button)
        
        # Check button configuration
        button_call = mock_gr.Button.call_args
        self.assertEqual(button_call.kwargs['value'], "Test Button")
        self.assertEqual(button_call.kwargs['variant'], "primary")
        self.assertIn('elem_id', button_call.kwargs)
        self.assertEqual(button_call.kwargs['elem_id'], "btn-test-button")
    
    @patch('lol_team_optimizer.gradio_components.gr')
    def test_create_accessible_form(self, mock_gr):
        """Test creating accessible form."""
        mock_markdown = Mock()
        mock_gr.Markdown.return_value = mock_markdown
        
        components = AccessibilityComponents.create_accessible_form(
            "Test Form", "Form description"
        )
        
        self.assertEqual(len(components), 1)
        self.assertEqual(components[0], mock_markdown)
        
        # Check markdown content
        markdown_call = mock_gr.Markdown.call_args
        markdown_content = markdown_call[0][0]
        self.assertIn("Test Form", markdown_content)
        self.assertIn("Form description", markdown_content)
        self.assertIn("Required fields are marked", markdown_content)
    
    @patch('lol_team_optimizer.gradio_components.gr')
    def test_create_skip_navigation(self, mock_gr):
        """Test creating skip navigation."""
        mock_html = Mock()
        mock_gr.HTML.return_value = mock_html
        
        result = AccessibilityComponents.create_skip_navigation()
        
        self.assertEqual(result, mock_html)
        
        # Check HTML content
        html_call = mock_gr.HTML.call_args
        html_content = html_call[0][0]
        self.assertIn("Skip to main content", html_content)
        self.assertIn("#main-content", html_content)
    
    @patch('lol_team_optimizer.gradio_components.gr')
    def test_create_screen_reader_announcement(self, mock_gr):
        """Test creating screen reader announcement."""
        mock_html = Mock()
        mock_gr.HTML.return_value = mock_html
        
        message = "Operation completed successfully"
        result = AccessibilityComponents.create_screen_reader_announcement(message)
        
        self.assertEqual(result, mock_html)
        
        # Check HTML content
        html_call = mock_gr.HTML.call_args
        html_content = html_call[0][0]
        self.assertIn(message, html_content)
        self.assertIn("aria-live", html_content)
        self.assertIn("aria-atomic", html_content)


class TestExportComponents(unittest.TestCase):
    """Test ExportComponents class."""
    
    @patch('lol_team_optimizer.gradio_components.gr')
    def test_create_export_interface(self, mock_gr):
        """Test creating export interface."""
        # Mock Gradio components
        mock_radio = Mock()
        mock_checkbox = Mock()
        mock_slider = Mock()
        mock_button = Mock()
        mock_file = Mock()
        mock_accordion = Mock()
        
        mock_gr.Radio.return_value = mock_radio
        mock_gr.Checkbox.return_value = mock_checkbox
        mock_gr.Slider.return_value = mock_slider
        mock_gr.Button.return_value = mock_button
        mock_gr.File.return_value = mock_file
        mock_gr.Accordion.return_value.__enter__ = Mock(return_value=mock_accordion)
        mock_gr.Accordion.return_value.__exit__ = Mock(return_value=None)
        
        export_types = ["PDF", "CSV", "JSON"]
        components = ExportComponents.create_export_interface(export_types)
        
        # Should return 6 components: export_type, include_metadata, include_charts, chart_quality, export_btn, download_link
        self.assertEqual(len(components), 6)
        
        # Verify component creation calls
        mock_gr.Radio.assert_called_once()
        self.assertEqual(mock_gr.Checkbox.call_count, 2)
        mock_gr.Slider.assert_called_once()
        mock_gr.Button.assert_called_once()
        mock_gr.File.assert_called_once()
        
        # Check export type choices
        radio_call = mock_gr.Radio.call_args
        self.assertEqual(radio_call.kwargs['choices'], export_types)
        self.assertEqual(radio_call.kwargs['value'], export_types[0])
    
    @patch('lol_team_optimizer.gradio_components.gr')
    def test_create_sharing_interface(self, mock_gr):
        """Test creating sharing interface."""
        # Mock Gradio components
        mock_radio = Mock()
        mock_dropdown = Mock()
        mock_button = Mock()
        mock_textbox = Mock()
        mock_row = Mock()
        mock_accordion = Mock()
        
        mock_gr.Radio.return_value = mock_radio
        mock_gr.Dropdown.return_value = mock_dropdown
        mock_gr.Button.return_value = mock_button
        mock_gr.Textbox.return_value = mock_textbox
        mock_gr.Row.return_value.__enter__ = Mock(return_value=mock_row)
        mock_gr.Row.return_value.__exit__ = Mock(return_value=None)
        mock_gr.Accordion.return_value.__enter__ = Mock(return_value=mock_accordion)
        mock_gr.Accordion.return_value.__exit__ = Mock(return_value=None)
        
        components = ExportComponents.create_sharing_interface()
        
        # Should return 5 components: privacy_level, expiration, generate_link_btn, share_link, copy_btn, email_btn
        self.assertEqual(len(components), 6)
        
        # Verify component creation calls
        mock_gr.Radio.assert_called_once()  # Privacy level
        mock_gr.Dropdown.assert_called_once()  # Expiration
        self.assertEqual(mock_gr.Button.call_count, 3)  # Generate, copy, email buttons
        mock_gr.Textbox.assert_called_once()  # Share link
        
        # Check privacy level choices
        radio_call = mock_gr.Radio.call_args
        privacy_choices = radio_call.kwargs['choices']
        self.assertIn("Public", privacy_choices)
        self.assertIn("Unlisted", privacy_choices)
        self.assertIn("Private", privacy_choices)
        
        # Check expiration choices
        dropdown_call = mock_gr.Dropdown.call_args
        expiration_choices = dropdown_call.kwargs['choices']
        self.assertIn("Never", expiration_choices)
        self.assertIn("1 hour", expiration_choices)
        self.assertIn("1 day", expiration_choices)


class TestNotificationComponents(unittest.TestCase):
    """Test NotificationComponents class."""
    
    @patch('lol_team_optimizer.gradio_components.gr')
    def test_create_toast_notification(self, mock_gr):
        """Test creating toast notifications."""
        mock_html = Mock()
        mock_gr.HTML.return_value = mock_html
        
        # Test success notification
        result = NotificationComponents.create_toast_notification(
            "Operation completed successfully", "success"
        )
        
        self.assertEqual(result, mock_html)
        
        # Check HTML content
        html_call = mock_gr.HTML.call_args
        html_content = html_call[0][0]
        
        self.assertIn("Operation completed successfully", html_content)
        self.assertIn("✅", html_content)  # Success icon
        self.assertIn("#155724", html_content)  # Success color
        self.assertIn("position: fixed", html_content)  # Toast positioning
        self.assertIn("slideIn", html_content)  # Animation
    
    @patch('lol_team_optimizer.gradio_components.gr')
    def test_create_alert_banner(self, mock_gr):
        """Test creating alert banners."""
        mock_html = Mock()
        mock_gr.HTML.return_value = mock_html
        
        # Test dismissible error banner
        result = NotificationComponents.create_alert_banner(
            "An error occurred", "error", dismissible=True
        )
        
        self.assertEqual(result, mock_html)
        
        # Check HTML content
        html_call = mock_gr.HTML.call_args
        html_content = html_call[0][0]
        
        self.assertIn("An error occurred", html_content)
        self.assertIn("❌", html_content)  # Error icon
        self.assertIn("#dc3545", html_content)  # Error color
        self.assertIn("×", html_content)  # Dismiss button
        self.assertIn("onclick", html_content)  # Dismiss functionality


class TestLoadingComponents(unittest.TestCase):
    """Test LoadingComponents class."""
    
    @patch('lol_team_optimizer.gradio_components.gr')
    def test_create_loading_spinner(self, mock_gr):
        """Test creating loading spinners."""
        mock_html = Mock()
        mock_gr.HTML.return_value = mock_html
        
        # Test medium spinner
        result = LoadingComponents.create_loading_spinner(
            "Processing data...", "medium"
        )
        
        self.assertEqual(result, mock_html)
        
        # Check HTML content
        html_call = mock_gr.HTML.call_args
        html_content = html_call[0][0]
        
        self.assertIn("Processing data...", html_content)
        self.assertIn("32px", html_content)  # Medium size
        self.assertIn("border-radius: 50%", html_content)  # Circular spinner
        self.assertIn("animation: spin", html_content)  # Spin animation
        self.assertIn("@keyframes spin", html_content)  # CSS animation
    
    @patch('lol_team_optimizer.gradio_components.gr')
    def test_create_skeleton_loader(self, mock_gr):
        """Test creating skeleton loaders."""
        mock_html = Mock()
        mock_gr.HTML.return_value = mock_html
        
        # Test 3-line skeleton
        result = LoadingComponents.create_skeleton_loader(lines=3)
        
        self.assertEqual(result, mock_html)
        
        # Check HTML content
        html_call = mock_gr.HTML.call_args
        html_content = html_call[0][0]
        
        # Should have 3 skeleton lines
        self.assertEqual(html_content.count('<div style="'), 4)  # 3 lines + container
        self.assertIn("background: linear-gradient", html_content)  # Shimmer effect
        self.assertIn("@keyframes loading", html_content)  # Loading animation
        self.assertIn("75%", html_content)  # Last line shorter


class TestLayoutComponents(unittest.TestCase):
    """Test LayoutComponents class."""
    
    @patch('lol_team_optimizer.gradio_components.gr')
    def test_create_card_container(self, mock_gr):
        """Test creating card containers."""
        # Mock Gradio components
        mock_html = Mock()
        mock_group = Mock()
        
        mock_gr.HTML.return_value = mock_html
        mock_gr.Group.return_value.__enter__ = Mock(return_value=mock_group)
        mock_gr.Group.return_value.__exit__ = Mock(return_value=None)
        
        # Test card creation
        content_components = [Mock(), Mock()]  # Mock content
        result = LayoutComponents.create_card_container(
            "Test Card", content_components
        )
        
        # Should return header + content wrapper + content + close wrapper
        expected_length = 3 + len(content_components)  # header, wrapper, close + content
        self.assertEqual(len(result), expected_length)
        
        # Check HTML calls for header and wrappers
        self.assertEqual(mock_gr.HTML.call_count, 3)  # Header, content wrapper, close wrapper
        
        # Check that title is in header
        header_call = mock_gr.HTML.call_args_list[0]
        header_content = header_call[0][0]
        self.assertIn("Test Card", header_content)
        self.assertIn("border-radius: 8px", header_content)  # Card styling
    
    @patch('lol_team_optimizer.gradio_components.gr')
    def test_create_section_divider(self, mock_gr):
        """Test creating section dividers."""
        mock_html = Mock()
        mock_gr.HTML.return_value = mock_html
        
        # Test divider with title
        result = LayoutComponents.create_section_divider("Section Title")
        
        self.assertEqual(result, mock_html)
        
        # Check HTML content
        html_call = mock_gr.HTML.call_args
        html_content = html_call[0][0]
        
        self.assertIn("Section Title", html_content)
        self.assertIn("<hr", html_content)  # Divider lines
        self.assertIn("text-transform: uppercase", html_content)  # Title styling
        
        # Test divider without title
        LayoutComponents.create_section_divider()
        
        # Check second call (without title)
        html_call_2 = mock_gr.HTML.call_args
        html_content_2 = html_call_2[0][0]
        
        self.assertIn("<hr", html_content_2)  # Should still have divider
        self.assertNotIn("span", html_content_2)  # No title span


class TestComponentManager(unittest.TestCase):
    """Test ComponentManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.component_manager = ComponentManager()
    
    def test_register_component(self):
        """Test registering components."""
        mock_component = Mock()
        
        self.component_manager.register_component("test_component", mock_component)
        
        self.assertIn("test_component", self.component_manager.component_registry)
        self.assertEqual(
            self.component_manager.component_registry["test_component"],
            mock_component
        )
    
    def test_get_component(self):
        """Test getting registered components."""
        mock_component = Mock()
        self.component_manager.register_component("test_component", mock_component)
        
        # Get existing component
        result = self.component_manager.get_component("test_component")
        self.assertEqual(result, mock_component)
        
        # Get non-existent component
        result = self.component_manager.get_component("nonexistent")
        self.assertIsNone(result)
    
    def test_setup_component_interactions(self):
        """Test setting up component interactions."""
        # Create mock components
        source_component = Mock()
        target_component = Mock()
        handler_function = Mock()
        
        # Register components
        self.component_manager.register_component("source", source_component)
        self.component_manager.register_component("target", target_component)
        
        # Set up interaction
        interactions = [{
            "source": "source",
            "target": "target",
            "event": "click",
            "handler": handler_function
        }]
        
        self.component_manager.setup_component_interactions(interactions)
        
        # Verify click handler was set up
        source_component.click.assert_called_once_with(
            fn=handler_function,
            outputs=target_component
        )
    
    def test_setup_component_interactions_change_event(self):
        """Test setting up change event interactions."""
        # Create mock components
        source_component = Mock()
        target_component = Mock()
        handler_function = Mock()
        
        # Register components
        self.component_manager.register_component("source", source_component)
        self.component_manager.register_component("target", target_component)
        
        # Set up change interaction
        interactions = [{
            "source": "source",
            "target": "target",
            "event": "change",
            "handler": handler_function
        }]
        
        self.component_manager.setup_component_interactions(interactions)
        
        # Verify change handler was set up
        source_component.change.assert_called_once_with(
            fn=handler_function,
            outputs=target_component
        )
    
    def test_setup_component_interactions_missing_component(self):
        """Test setting up interactions with missing components."""
        handler_function = Mock()
        
        # Set up interaction with non-existent components
        interactions = [{
            "source": "nonexistent_source",
            "target": "nonexistent_target",
            "event": "click",
            "handler": handler_function
        }]
        
        # Should not raise exception
        self.component_manager.setup_component_interactions(interactions)
    
    def test_create_component_group(self):
        """Test creating component groups."""
        components = [Mock(), Mock(), Mock()]
        
        self.component_manager.create_component_group("test_group", components)
        
        # Verify all components were registered
        for i, component in enumerate(components):
            component_name = f"test_group_{i}"
            self.assertIn(component_name, self.component_manager.component_registry)
            self.assertEqual(
                self.component_manager.component_registry[component_name],
                component
            )


if __name__ == '__main__':
    # Set up logging for tests
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Run tests
    unittest.main(verbosity=2)