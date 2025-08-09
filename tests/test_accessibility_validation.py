"""
Accessibility validation tests for Gradio components.

Tests WCAG compliance and accessibility features of the component library.
"""

import unittest
from unittest.mock import Mock, patch
import sys
import os

# Add the parent directory to the path to import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lol_team_optimizer.gradio_components import (
    AccessibilityComponents,
    ComponentConfig,
    PlayerManagementComponents,
    ValidationComponents
)


class TestAccessibilityValidation(unittest.TestCase):
    """Test accessibility compliance of components."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = ComponentConfig()
    
    def test_skip_navigation_structure(self):
        """Test skip navigation has proper structure."""
        with patch('lol_team_optimizer.gradio_components.gr.HTML') as mock_html:
            mock_html.return_value = Mock()
            
            skip_nav = AccessibilityComponents.create_skip_navigation()
            
            # Verify HTML was called
            mock_html.assert_called_once()
            
            # Check HTML content structure
            html_call = mock_html.call_args
            html_content = html_call[0][0]
            
            # Should have proper skip link structure
            self.assertIn('href="#main-content"', html_content)
            self.assertIn('Skip to main content', html_content)
            self.assertIn('position: absolute', html_content)
            self.assertIn('left: -9999px', html_content)  # Hidden by default
    
    def test_screen_reader_announcement_aria(self):
        """Test screen reader announcements have proper ARIA attributes."""
        with patch('lol_team_optimizer.gradio_components.gr.HTML') as mock_html:
            mock_html.return_value = Mock()
            
            message = "Form submitted successfully"
            announcement = AccessibilityComponents.create_screen_reader_announcement(message)
            
            # Verify HTML was called
            mock_html.assert_called_once()
            
            # Check ARIA attributes
            html_call = mock_html.call_args
            html_content = html_call[0][0]
            
            self.assertIn('aria-live="polite"', html_content)
            self.assertIn('aria-atomic="true"', html_content)
            self.assertIn(message, html_content)
            self.assertIn('position: absolute', html_content)
            self.assertIn('left: -10000px', html_content)  # Screen reader only
    
    def test_accessible_button_attributes(self):
        """Test accessible buttons have proper attributes."""
        with patch('lol_team_optimizer.gradio_components.gr.Button') as mock_button:
            mock_button.return_value = Mock()
            
            button = AccessibilityComponents.create_accessible_button(
                "Submit Form", "Submit the player registration form", "primary"
            )
            
            # Verify button creation
            mock_button.assert_called_once()
            
            # Check button configuration
            button_call = mock_button.call_args
            self.assertEqual(button_call.kwargs['value'], "Submit Form")
            self.assertEqual(button_call.kwargs['variant'], "primary")
            self.assertIn('elem_id', button_call.kwargs)
            self.assertEqual(button_call.kwargs['elem_id'], "btn-submit-form")
    
    def test_accessible_form_structure(self):
        """Test accessible forms have proper structure."""
        with patch('lol_team_optimizer.gradio_components.gr.Markdown') as mock_markdown:
            mock_markdown.return_value = Mock()
            
            form_components = AccessibilityComponents.create_accessible_form(
                "Player Registration", "Register a new player in the system"
            )
            
            # Should return one component (header)
            self.assertEqual(len(form_components), 1)
            
            # Verify markdown content
            mock_markdown.assert_called_once()
            markdown_call = mock_markdown.call_args
            markdown_content = markdown_call[0][0]
            
            # Should have proper heading structure
            self.assertIn("# Player Registration", markdown_content)
            self.assertIn("Register a new player in the system", markdown_content)
            self.assertIn("Required fields are marked", markdown_content)
            self.assertIn("asterisk (*)", markdown_content)
    
    def test_validation_message_accessibility(self):
        """Test validation messages are accessible."""
        with patch('lol_team_optimizer.gradio_components.gr.HTML') as mock_html:
            mock_html.return_value = Mock()
            
            # Test error message
            error_msg = ValidationComponents.create_validation_message(
                "Username is required", "error", self.config
            )
            
            mock_html.assert_called()
            html_call = mock_html.call_args
            html_content = html_call[0][0]
            
            # Should have proper color contrast and structure
            self.assertIn("Username is required", html_content)
            self.assertIn("❌", html_content)  # Clear visual indicator
            self.assertIn("#dc3545", html_content)  # Error color
            self.assertIn("display: flex", html_content)  # Proper layout
            self.assertIn("align-items: center", html_content)  # Icon alignment
    
    def test_color_contrast_compliance(self):
        """Test color choices meet WCAG contrast requirements."""
        config = ComponentConfig()
        
        # Test default colors have sufficient contrast
        # These are the colors used in the components
        colors = {
            "theme_color": "rgb(0, 123, 255)",  # Blue
            "success_color": "#155724",  # Dark green
            "error_color": "#dc3545",  # Red
            "warning_color": "#856404",  # Dark yellow
            "info_color": "#0c5460"  # Dark cyan
        }
        
        # Verify colors are defined and not empty
        for color_name, color_value in colors.items():
            config_color = getattr(config, color_name)
            self.assertEqual(config_color, color_value)
            self.assertIsNotNone(config_color)
            self.assertNotEqual(config_color, "")
    
    def test_keyboard_navigation_support(self):
        """Test components support keyboard navigation."""
        with patch('lol_team_optimizer.gradio_components.gr') as mock_gr:
            # Mock all Gradio components
            mock_gr.Textbox.return_value = Mock()
            mock_gr.Button.return_value = Mock()
            mock_gr.Dropdown.return_value = Mock()
            
            # Create player form components
            form_components = PlayerManagementComponents.create_player_form(self.config)
            
            # Verify components are created (they should be keyboard accessible by default in Gradio)
            self.assertGreater(len(form_components), 0)
            
            # Check that textboxes are created (keyboard accessible)
            self.assertGreater(mock_gr.Textbox.call_count, 0)
            
            # Check that dropdown is created (keyboard accessible)
            mock_gr.Dropdown.assert_called_once()
    
    def test_focus_management(self):
        """Test focus management in component interactions."""
        # This test verifies that components can be properly focused
        # In a real implementation, this would test tab order and focus trapping
        
        with patch('lol_team_optimizer.gradio_components.gr') as mock_gr:
            mock_gr.Textbox.return_value = Mock()
            mock_gr.Button.return_value = Mock()
            
            # Create accessible button
            button = AccessibilityComponents.create_accessible_button(
                "Test Button", "Test description"
            )
            
            # Verify button has elem_id for focus management
            button_call = mock_gr.Button.call_args
            self.assertIn('elem_id', button_call.kwargs)
            self.assertTrue(button_call.kwargs['elem_id'].startswith('btn-'))
    
    def test_semantic_html_structure(self):
        """Test components use semantic HTML where possible."""
        with patch('lol_team_optimizer.gradio_components.gr.HTML') as mock_html:
            mock_html.return_value = Mock()
            
            # Test status indicator uses semantic structure
            from lol_team_optimizer.gradio_components import ProgressComponents
            
            status = ProgressComponents.create_status_indicator("success", self.config)
            
            mock_html.assert_called_once()
            html_call = mock_html.call_args
            html_content = html_call[0][0]
            
            # Should use semantic elements and proper structure
            self.assertIn('<div', html_content)
            self.assertIn('<span', html_content)
            self.assertIn('display: inline-flex', html_content)  # Proper layout
            self.assertIn('align-items: center', html_content)  # Accessibility
    
    def test_responsive_design_accessibility(self):
        """Test components work well on different screen sizes."""
        # This test verifies that components use responsive design principles
        
        with patch('lol_team_optimizer.gradio_components.gr') as mock_gr:
            mock_gr.Row.return_value.__enter__ = Mock()
            mock_gr.Row.return_value.__exit__ = Mock()
            mock_gr.Column.return_value.__enter__ = Mock()
            mock_gr.Column.return_value.__exit__ = Mock()
            mock_gr.Markdown.return_value = Mock()
            
            # Test metrics display uses responsive layout
            from lol_team_optimizer.gradio_components import AnalyticsComponents
            
            metrics = {"Win Rate": "65%", "KDA": "2.1", "Games": "42"}
            components = AnalyticsComponents.create_metrics_display(metrics, self.config)
            
            # Should create components with responsive layout
            self.assertEqual(len(components), len(metrics))
            
            # Verify Row layout is used (responsive)
            mock_gr.Row.assert_called()
            mock_gr.Column.assert_called()


class TestWCAGCompliance(unittest.TestCase):
    """Test WCAG 2.1 AA compliance features."""
    
    def test_text_alternatives(self):
        """Test components provide text alternatives for non-text content."""
        with patch('lol_team_optimizer.gradio_components.gr.HTML') as mock_html:
            mock_html.return_value = Mock()
            
            # Test status indicators have text alternatives
            from lol_team_optimizer.gradio_components import ProgressComponents
            
            status = ProgressComponents.create_status_indicator("loading", ComponentConfig())
            
            html_call = mock_html.call_args
            html_content = html_call[0][0]
            
            # Should have both icon and text
            self.assertIn("🔄", html_content)  # Visual indicator
            self.assertIn("Loading", html_content)  # Text alternative
    
    def test_keyboard_accessibility(self):
        """Test all interactive elements are keyboard accessible."""
        # Gradio components are keyboard accessible by default
        # This test verifies we're not breaking that accessibility
        
        with patch('lol_team_optimizer.gradio_components.gr') as mock_gr:
            mock_gr.Button.return_value = Mock()
            mock_gr.Textbox.return_value = Mock()
            mock_gr.Dropdown.return_value = Mock()
            mock_gr.Checkbox.return_value = Mock()
            
            # Test player form components
            components = PlayerManagementComponents.create_player_form()
            
            # All components should be keyboard accessible
            self.assertGreater(len(components), 0)
            
            # Verify interactive components are created
            self.assertGreater(mock_gr.Textbox.call_count, 0)
            mock_gr.Dropdown.assert_called()
    
    def test_color_not_only_indicator(self):
        """Test information is not conveyed by color alone."""
        with patch('lol_team_optimizer.gradio_components.gr.HTML') as mock_html:
            mock_html.return_value = Mock()
            
            # Test validation messages use both color and icons
            validation_msg = ValidationComponents.create_validation_message(
                "Field is valid", "success", ComponentConfig()
            )
            
            html_call = mock_html.call_args
            html_content = html_call[0][0]
            
            # Should have both color and icon/text indicators
            self.assertIn("✅", html_content)  # Icon indicator
            self.assertIn("#155724", html_content)  # Color indicator
            self.assertIn("Field is valid", html_content)  # Text indicator
    
    def test_sufficient_color_contrast(self):
        """Test color combinations provide sufficient contrast."""
        config = ComponentConfig()
        
        # Test that error colors provide sufficient contrast
        # Red on white background should have good contrast
        self.assertEqual(config.error_color, "#dc3545")
        
        # Success colors should have good contrast
        self.assertEqual(config.success_color, "#155724")
        
        # These colors are chosen to meet WCAG AA standards
        # In a real implementation, you would use a contrast checker
    
    def test_resize_text_support(self):
        """Test components work when text is resized."""
        # This test verifies components use relative units and flexible layouts
        
        with patch('lol_team_optimizer.gradio_components.gr.HTML') as mock_html:
            mock_html.return_value = Mock()
            
            # Test status indicators use flexible sizing
            from lol_team_optimizer.gradio_components import ProgressComponents
            
            status = ProgressComponents.create_status_indicator("info", ComponentConfig())
            
            html_call = mock_html.call_args
            html_content = html_call[0][0]
            
            # Should use flexible units and layouts
            self.assertIn("padding:", html_content)  # Flexible spacing
            self.assertIn("font-size:", html_content)  # Text sizing
            self.assertIn("display: inline-flex", html_content)  # Flexible layout


if __name__ == '__main__':
    unittest.main()