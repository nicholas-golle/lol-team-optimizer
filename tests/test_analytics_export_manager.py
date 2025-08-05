"""
Tests for the Analytics Export Manager.

This module tests the comprehensive export and reporting functionality
including multiple format exports, automated report generation, and
scheduled reporting capabilities.
"""

import pytest
import json
import csv
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import threading
import time

from lol_team_optimizer.analytics_export_manager import (
    AnalyticsExportManager, ExportFormat, ReportType, ExportConfiguration,
    ReportTemplate, ReportSchedule
)
from lol_team_optimizer.analytics_models import (
    PlayerAnalytics, ChampionPerformanceMetrics, TeamComposition,
    CompositionPerformance, PerformanceMetrics, PlayerRoleAssignment,
    PerformanceDelta, AnalyticsFilters, DateRange
)


class TestAnalyticsExportManager:
    """Test suite for AnalyticsExportManager."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test exports."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def export_manager(self, temp_dir):
        """Create an AnalyticsExportManager instance for testing."""
        return AnalyticsExportManager(temp_dir)
    
    @pytest.fixture
    def sample_player_analytics(self):
        """Create sample player analytics data for testing."""
        overall_performance = PerformanceMetrics(
            win_rate=0.65,
            avg_kda=2.5,
            avg_cs_per_min=7.2,
            avg_vision_score=45.0,
            avg_damage_per_min=650.0,
            games_played=50
        )
        
        champion_performance = {
            1: ChampionPerformanceMetrics(
                champion_id=1,
                champion_name="Aatrox",
                role="top",
                games_played=10,
                win_rate=0.7,
                avg_kda=2.8,
                avg_cs_per_min=7.5,
                avg_vision_score=40.0,
                avg_damage_per_min=700.0,
                performance_vs_baseline=PerformanceDelta(
                    metric_name="win_rate",
                    baseline_value=0.65,
                    actual_value=0.7,
                    delta_absolute=0.05,
                    delta_percentage=7.69,
                    percentile_rank=75.0,
                    statistical_significance=0.05
                ),
                recent_form=None,
                synergy_scores={}
            )
        }
        
        return PlayerAnalytics(
            puuid="test_player_123",
            analysis_period=DateRange(
                start_date=datetime.now() - timedelta(days=30),
                end_date=datetime.now()
            ),
            overall_performance=overall_performance,
            role_performance={},
            champion_performance=champion_performance,
            trend_analysis=None,
            comparative_rankings=None,
            confidence_scores=None
        )
    
    @pytest.fixture
    def sample_champion_data(self):
        """Create sample champion performance data for testing."""
        return [
            ChampionPerformanceMetrics(
                champion_id=1,
                champion_name="Aatrox",
                role="top",
                games_played=15,
                win_rate=0.73,
                avg_kda=2.9,
                avg_cs_per_min=7.8,
                avg_vision_score=42.0,
                avg_damage_per_min=720.0,
                performance_vs_baseline=PerformanceDelta(
                    metric_name="win_rate",
                    baseline_value=0.65,
                    actual_value=0.73,
                    delta_absolute=0.08,
                    delta_percentage=12.31,
                    percentile_rank=80.0,
                    statistical_significance=0.03
                ),
                recent_form=None,
                synergy_scores={}
            ),
            ChampionPerformanceMetrics(
                champion_id=2,
                champion_name="Ahri",
                role="mid",
                games_played=12,
                win_rate=0.58,
                avg_kda=2.2,
                avg_cs_per_min=6.9,
                avg_vision_score=38.0,
                avg_damage_per_min=580.0,
                performance_vs_baseline=None,
                recent_form=None,
                synergy_scores={}
            )
        ]
    
    @pytest.fixture
    def sample_composition_data(self):
        """Create sample team composition data for testing."""
        composition = TeamComposition(
            players={
                "top": PlayerRoleAssignment(
                    puuid="player1",
                    player_name="Player1",
                    role="top",
                    champion_id=1,
                    champion_name="Aatrox"
                ),
                "jungle": PlayerRoleAssignment(
                    puuid="player2",
                    player_name="Player2",
                    role="jungle",
                    champion_id=2,
                    champion_name="Graves"
                )
            },
            composition_id="comp_123",
            historical_matches=["match1", "match2"]
        )
        
        return [
            CompositionPerformance(
                composition=composition,
                total_games=8,
                win_rate=0.75,
                avg_game_duration=28.5,
                performance_vs_individual_baselines={},
                synergy_effects=None,
                statistical_significance=None,
                confidence_interval=None
            )
        ]
    
    def test_initialization(self, temp_dir):
        """Test AnalyticsExportManager initialization."""
        manager = AnalyticsExportManager(temp_dir)
        
        assert manager.output_directory == temp_dir
        assert temp_dir.exists()
        assert len(manager.templates) >= 3  # Default templates
        assert "player_performance" in manager.templates
        assert "champion_analysis" in manager.templates
        assert "team_composition" in manager.templates
    
    def test_export_player_analytics_json(self, export_manager, sample_player_analytics):
        """Test exporting player analytics to JSON format."""
        filepath = export_manager.export_player_analytics(
            sample_player_analytics,
            ExportFormat.JSON
        )
        
        assert filepath.exists()
        assert filepath.suffix == ".json"
        
        # Verify JSON content
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        assert "metadata" in data
        assert "data" in data
        assert data["data"]["puuid"] == "test_player_123"
    
    def test_export_player_analytics_csv(self, export_manager, sample_player_analytics):
        """Test exporting player analytics to CSV format."""
        filepath = export_manager.export_player_analytics(
            sample_player_analytics,
            ExportFormat.CSV
        )
        
        assert filepath.exists()
        assert filepath.suffix == ".csv"
        
        # Verify CSV content
        with open(filepath, 'r') as f:
            content = f.read()
        
        assert "Player Analytics Export" in content
        assert "Overall Performance" in content
        assert "Champion Performance" in content
    
    @patch('lol_team_optimizer.analytics_export_manager.PANDAS_AVAILABLE', True)
    @patch('pandas.ExcelWriter')
    def test_export_player_analytics_excel(self, mock_excel_writer, export_manager, sample_player_analytics):
        """Test exporting player analytics to Excel format."""
        mock_writer = MagicMock()
        mock_excel_writer.return_value.__enter__.return_value = mock_writer
        
        filepath = export_manager.export_player_analytics(
            sample_player_analytics,
            ExportFormat.EXCEL
        )
        
        assert filepath.suffix == ".xlsx"
        mock_excel_writer.assert_called_once()
    
    @patch('lol_team_optimizer.analytics_export_manager.REPORTLAB_AVAILABLE', True)
    @patch('lol_team_optimizer.analytics_export_manager.SimpleDocTemplate')
    def test_export_player_analytics_pdf(self, mock_doc, export_manager, sample_player_analytics):
        """Test exporting player analytics to PDF format."""
        mock_doc_instance = MagicMock()
        mock_doc.return_value = mock_doc_instance
        
        filepath = export_manager.export_player_analytics(
            sample_player_analytics,
            ExportFormat.PDF
        )
        
        assert filepath.suffix == ".pdf"
        mock_doc.assert_called_once()
        mock_doc_instance.build.assert_called_once()
    
    def test_export_champion_analytics_json(self, export_manager, sample_champion_data):
        """Test exporting champion analytics to JSON format."""
        filepath = export_manager.export_champion_analytics(
            sample_champion_data,
            ExportFormat.JSON
        )
        
        assert filepath.exists()
        assert filepath.suffix == ".json"
        
        # Verify JSON content
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        assert "data" in data
        assert len(data["data"]) == 2
        assert data["data"][0]["champion_name"] == "Aatrox"
    
    def test_export_champion_analytics_csv(self, export_manager, sample_champion_data):
        """Test exporting champion analytics to CSV format."""
        filepath = export_manager.export_champion_analytics(
            sample_champion_data,
            ExportFormat.CSV
        )
        
        assert filepath.exists()
        assert filepath.suffix == ".csv"
        
        # Verify CSV content
        with open(filepath, 'r') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        # Find the header row
        header_found = False
        for row in rows:
            if row and "Champion" in row[0]:
                header_found = True
                break
        
        assert header_found
    
    def test_export_team_composition_analytics_json(self, export_manager, sample_composition_data):
        """Test exporting team composition analytics to JSON format."""
        filepath = export_manager.export_team_composition_analytics(
            sample_composition_data,
            ExportFormat.JSON
        )
        
        assert filepath.exists()
        assert filepath.suffix == ".json"
        
        # Verify JSON content
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        assert "data" in data
        assert len(data["data"]) == 1
        assert data["data"][0]["composition"]["composition_id"] == "comp_123"
    
    def test_export_configuration_custom_settings(self, export_manager, sample_player_analytics):
        """Test export with custom configuration settings."""
        config = ExportConfiguration(
            format=ExportFormat.JSON,
            include_metadata=False,
            decimal_places=2,
            date_format="%Y-%m-%d"
        )
        
        filepath = export_manager.export_player_analytics(
            sample_player_analytics,
            ExportFormat.JSON,
            config
        )
        
        assert filepath.exists()
        
        # Verify configuration was applied
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Should not include metadata when include_metadata=False
        assert data["metadata"] == {}
    
    def test_create_custom_template(self, export_manager):
        """Test creating a custom report template."""
        template = export_manager.create_custom_template(
            name="custom_test",
            report_type=ReportType.PLAYER_PERFORMANCE,
            title="Custom Test Report",
            description="A custom test report template",
            sections=["summary", "details"],
            metrics=["win_rate", "kda"],
            visualizations=["chart1", "chart2"]
        )
        
        assert template.name == "custom_test"
        assert template.report_type == ReportType.PLAYER_PERFORMANCE
        assert template.title == "Custom Test Report"
        assert "custom_test" in export_manager.templates
    
    def test_generate_comprehensive_report_json(self, export_manager):
        """Test generating a comprehensive report in JSON format."""
        data = {
            "player_analytics": {
                "puuid": "test_player",
                "overall_performance": {
                    "win_rate": 0.65,
                    "avg_kda": 2.5
                }
            }
        }
        
        generated_files = export_manager.generate_comprehensive_report(
            "player_performance",
            data,
            [ExportFormat.JSON]
        )
        
        assert len(generated_files) == 1
        assert generated_files[0].exists()
        assert generated_files[0].suffix == ".json"
        
        # Verify report content
        with open(generated_files[0], 'r') as f:
            report_data = json.load(f)
        
        assert "report_metadata" in report_data
        assert report_data["report_metadata"]["template_name"] == "player_performance"
        assert report_data["report_metadata"]["report_type"] == "player_performance"
    
    def test_generate_comprehensive_report_multiple_formats(self, export_manager):
        """Test generating a comprehensive report in multiple formats."""
        data = {"test": "data"}
        
        generated_files = export_manager.generate_comprehensive_report(
            "player_performance",
            data,
            [ExportFormat.JSON, ExportFormat.CSV]
        )
        
        assert len(generated_files) == 2
        
        # Check that both formats were generated
        formats_generated = {f.suffix for f in generated_files}
        assert ".json" in formats_generated
        assert ".csv" in formats_generated
    
    def test_schedule_report(self, export_manager):
        """Test scheduling automated report generation."""
        schedule_config = export_manager.schedule_report(
            name="daily_report",
            template_name="player_performance",
            frequency="daily",
            recipients=["test@example.com"],
            export_formats=[ExportFormat.JSON, ExportFormat.CSV],
            enabled=True
        )
        
        assert schedule_config.name == "daily_report"
        assert schedule_config.frequency == "daily"
        assert schedule_config.enabled
        assert "daily_report" in export_manager.schedules
    
    def test_schedule_report_invalid_template(self, export_manager):
        """Test scheduling report with invalid template name."""
        with pytest.raises(ValueError, match="Template 'nonexistent' not found"):
            export_manager.schedule_report(
                name="test_report",
                template_name="nonexistent",
                frequency="daily",
                recipients=["test@example.com"],
                export_formats=[ExportFormat.JSON]
            )
    
    def test_export_multiple_formats(self, export_manager, sample_player_analytics):
        """Test exporting data in multiple formats simultaneously."""
        formats = [ExportFormat.JSON, ExportFormat.CSV]
        
        exported_files = export_manager.export_multiple_formats(
            sample_player_analytics,
            "player",
            formats
        )
        
        assert len(exported_files) == 2
        
        # Check that both formats were exported
        formats_exported = {f.suffix for f in exported_files}
        assert ".json" in formats_exported
        assert ".csv" in formats_exported
        
        # Verify all files exist
        for filepath in exported_files:
            assert filepath.exists()
    
    def test_export_multiple_formats_with_failure(self, export_manager, sample_player_analytics):
        """Test export multiple formats with one format failing."""
        formats = [ExportFormat.JSON, ExportFormat.PDF]  # PDF might fail without ReportLab
        
        with patch('lol_team_optimizer.analytics_export_manager.REPORTLAB_AVAILABLE', False):
            exported_files = export_manager.export_multiple_formats(
                sample_player_analytics,
                "player",
                formats
            )
            
            # Should have at least JSON export even if PDF fails
            assert len(exported_files) >= 1
            json_files = [f for f in exported_files if f.suffix == ".json"]
            assert len(json_files) == 1
    
    def test_get_export_statistics_empty_directory(self, export_manager):
        """Test getting export statistics from empty directory."""
        stats = export_manager.get_export_statistics()
        
        assert stats["total_files"] == 0
        assert stats["files_by_format"] == {}
        assert stats["files_by_type"] == {}
        assert stats["total_size_mb"] == 0
        assert stats["latest_export"] is None
        assert stats["oldest_export"] is None
    
    def test_get_export_statistics_with_files(self, export_manager, sample_player_analytics):
        """Test getting export statistics with exported files."""
        # Export some files
        export_manager.export_player_analytics(sample_player_analytics, ExportFormat.JSON)
        export_manager.export_player_analytics(sample_player_analytics, ExportFormat.CSV)
        
        stats = export_manager.get_export_statistics()
        
        assert stats["total_files"] == 2
        assert "json" in stats["files_by_format"]
        assert "csv" in stats["files_by_format"]
        assert "player" in stats["files_by_type"]
        assert stats["total_size_mb"] > 0
        assert stats["latest_export"] is not None
        assert stats["oldest_export"] is not None
    
    def test_cleanup_old_exports(self, export_manager, sample_player_analytics):
        """Test cleaning up old export files."""
        # Export a file
        filepath = export_manager.export_player_analytics(sample_player_analytics, ExportFormat.JSON)
        
        # Modify file timestamp to make it appear old
        old_time = datetime.now() - timedelta(days=35)
        old_timestamp = old_time.timestamp()
        filepath.touch(times=(old_timestamp, old_timestamp))
        
        # Clean up files older than 30 days
        deleted_count = export_manager.cleanup_old_exports(days_to_keep=30)
        
        assert deleted_count == 1
        assert not filepath.exists()
    
    def test_scheduler_start_stop(self, export_manager):
        """Test starting and stopping the report scheduler."""
        # Start scheduler
        export_manager.start_scheduler()
        assert export_manager.scheduler_running
        assert export_manager.scheduler_thread is not None
        assert export_manager.scheduler_thread.is_alive()
        
        # Stop scheduler
        export_manager.stop_scheduler()
        assert not export_manager.scheduler_running
        
        # Wait a bit for thread to finish
        time.sleep(0.1)
        if export_manager.scheduler_thread:
            assert not export_manager.scheduler_thread.is_alive()
    
    def test_scheduler_already_running_warning(self, export_manager):
        """Test warning when trying to start scheduler that's already running."""
        export_manager.start_scheduler()
        
        with patch.object(export_manager.logger, 'warning') as mock_warning:
            export_manager.start_scheduler()
            mock_warning.assert_called_with("Scheduler is already running")
        
        export_manager.stop_scheduler()
    
    def test_export_unsupported_format(self, export_manager, sample_player_analytics):
        """Test exporting with unsupported format raises error."""
        # Create a mock unsupported format
        class UnsupportedFormat:
            value = "unsupported"
        
        unsupported_format = UnsupportedFormat()
        
        with pytest.raises(ValueError, match="Unsupported export format"):
            export_manager.export_player_analytics(
                sample_player_analytics,
                unsupported_format
            )
    
    def test_export_unsupported_data_type(self, export_manager, sample_player_analytics):
        """Test export_multiple_formats with unsupported data type."""
        with pytest.raises(ValueError, match="Unsupported data type"):
            export_manager.export_multiple_formats(
                sample_player_analytics,
                "unsupported_type",
                [ExportFormat.JSON]
            )
    
    def test_json_serialization_complex_objects(self, export_manager):
        """Test JSON serialization of complex objects."""
        # Test with datetime objects
        test_data = {
            "timestamp": datetime.now(),
            "nested": {
                "date": datetime.now().date(),
                "list": [1, 2, 3]
            }
        }
        
        serialized = export_manager._serialize_for_json(test_data)
        
        # Should be able to serialize without errors
        json.dumps(serialized, default=str)
    
    @patch('lol_team_optimizer.analytics_export_manager.PANDAS_AVAILABLE', False)
    def test_excel_export_without_pandas(self, export_manager, sample_player_analytics):
        """Test Excel export fails gracefully without pandas."""
        with pytest.raises(RuntimeError, match="Pandas is required for Excel export"):
            export_manager.export_player_analytics(
                sample_player_analytics,
                ExportFormat.EXCEL
            )
    
    @patch('lol_team_optimizer.analytics_export_manager.REPORTLAB_AVAILABLE', False)
    def test_pdf_export_without_reportlab(self, export_manager, sample_player_analytics):
        """Test PDF export fails gracefully without ReportLab."""
        with pytest.raises(RuntimeError, match="ReportLab is required for PDF export"):
            export_manager.export_player_analytics(
                sample_player_analytics,
                ExportFormat.PDF
            )
    
    def test_report_template_validation(self, export_manager):
        """Test report template creation and validation."""
        template = export_manager.templates["player_performance"]
        
        assert template.name == "player_performance"
        assert template.report_type == ReportType.PLAYER_PERFORMANCE
        assert template.title == "Player Performance Analysis"
        assert "summary" in template.sections
        assert "win_rate" in template.metrics
        assert "performance_chart" in template.visualizations
    
    def test_export_with_custom_fields(self, export_manager, sample_player_analytics):
        """Test export with custom field selection."""
        config = ExportConfiguration(
            format=ExportFormat.JSON,
            custom_fields=["puuid", "overall_performance"]
        )
        
        filepath = export_manager.export_player_analytics(
            sample_player_analytics,
            ExportFormat.JSON,
            config
        )
        
        assert filepath.exists()
        
        # Verify content
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        assert "data" in data
        assert "puuid" in str(data["data"])


class TestReportScheduling:
    """Test suite for report scheduling functionality."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test exports."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def export_manager(self, temp_dir):
        """Create an AnalyticsExportManager instance for testing."""
        return AnalyticsExportManager(temp_dir)
    
    def test_schedule_daily_report(self, export_manager):
        """Test scheduling a daily report."""
        schedule_config = export_manager.schedule_report(
            name="daily_test",
            template_name="player_performance",
            frequency="daily",
            recipients=["test@example.com"],
            export_formats=[ExportFormat.JSON]
        )
        
        assert schedule_config.frequency == "daily"
        assert schedule_config.enabled
    
    def test_schedule_weekly_report(self, export_manager):
        """Test scheduling a weekly report."""
        schedule_config = export_manager.schedule_report(
            name="weekly_test",
            template_name="champion_analysis",
            frequency="weekly",
            recipients=["test@example.com"],
            export_formats=[ExportFormat.CSV, ExportFormat.PDF]
        )
        
        assert schedule_config.frequency == "weekly"
        assert len(schedule_config.export_formats) == 2
    
    def test_schedule_monthly_report(self, export_manager):
        """Test scheduling a monthly report."""
        schedule_config = export_manager.schedule_report(
            name="monthly_test",
            template_name="team_composition",
            frequency="monthly",
            recipients=["manager@example.com", "coach@example.com"],
            export_formats=[ExportFormat.EXCEL]
        )
        
        assert schedule_config.frequency == "monthly"
        assert len(schedule_config.recipients) == 2
    
    def test_schedule_unsupported_frequency(self, export_manager):
        """Test scheduling with unsupported frequency."""
        with pytest.raises(ValueError, match="Unsupported frequency"):
            export_manager.schedule_report(
                name="invalid_test",
                template_name="player_performance",
                frequency="hourly",  # Unsupported
                recipients=["test@example.com"],
                export_formats=[ExportFormat.JSON]
            )
    
    def test_disabled_schedule(self, export_manager):
        """Test creating a disabled schedule."""
        schedule_config = export_manager.schedule_report(
            name="disabled_test",
            template_name="player_performance",
            frequency="daily",
            recipients=["test@example.com"],
            export_formats=[ExportFormat.JSON],
            enabled=False
        )
        
        assert not schedule_config.enabled
    
    @patch('schedule.every')
    def test_schedule_setup_daily(self, mock_schedule, export_manager):
        """Test setting up daily schedule."""
        mock_day = MagicMock()
        mock_schedule.return_value.day = mock_day
        mock_at = MagicMock()
        mock_day.at.return_value = mock_at
        
        schedule_config = ReportSchedule(
            name="test",
            template=export_manager.templates["player_performance"],
            frequency="daily",
            recipients=["test@example.com"],
            export_formats=[ExportFormat.JSON]
        )
        
        export_manager._setup_schedule(schedule_config)
        
        mock_schedule.assert_called_once()
        mock_day.at.assert_called_with("09:00")
        mock_at.do.assert_called_once()
    
    @patch('schedule.every')
    def test_schedule_setup_weekly(self, mock_schedule, export_manager):
        """Test setting up weekly schedule."""
        mock_monday = MagicMock()
        mock_schedule.return_value.monday = mock_monday
        mock_at = MagicMock()
        mock_monday.at.return_value = mock_at
        
        schedule_config = ReportSchedule(
            name="test",
            template=export_manager.templates["player_performance"],
            frequency="weekly",
            recipients=["test@example.com"],
            export_formats=[ExportFormat.JSON]
        )
        
        export_manager._setup_schedule(schedule_config)
        
        mock_schedule.assert_called_once()
        mock_monday.at.assert_called_with("09:00")
        mock_at.do.assert_called_once()
    
    @patch('schedule.every')
    def test_schedule_setup_monthly(self, mock_schedule, export_manager):
        """Test setting up monthly schedule."""
        mock_month = MagicMock()
        mock_schedule.return_value.month = mock_month
        
        schedule_config = ReportSchedule(
            name="test",
            template=export_manager.templates["player_performance"],
            frequency="monthly",
            recipients=["test@example.com"],
            export_formats=[ExportFormat.JSON]
        )
        
        export_manager._setup_schedule(schedule_config)
        
        mock_schedule.assert_called_once()
        mock_month.do.assert_called_once()


class TestReportGeneration:
    """Test suite for comprehensive report generation."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test exports."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def export_manager(self, temp_dir):
        """Create an AnalyticsExportManager instance for testing."""
        return AnalyticsExportManager(temp_dir)
    
    def test_generate_player_performance_report(self, export_manager):
        """Test generating a player performance report."""
        data = {
            "player_analytics": Mock(
                puuid="test_player",
                overall_performance=Mock(
                    win_rate=0.65,
                    avg_kda=2.5,
                    avg_cs_per_min=7.2
                )
            )
        }
        
        generated_files = export_manager.generate_comprehensive_report(
            "player_performance",
            data,
            [ExportFormat.JSON, ExportFormat.CSV]
        )
        
        assert len(generated_files) == 2
        for filepath in generated_files:
            assert filepath.exists()
    
    def test_generate_champion_analysis_report(self, export_manager):
        """Test generating a champion analysis report."""
        data = {
            "champion_data": [
                Mock(
                    champion_name="Aatrox",
                    role="top",
                    games_played=10,
                    win_rate=0.7
                )
            ]
        }
        
        generated_files = export_manager.generate_comprehensive_report(
            "champion_analysis",
            data,
            [ExportFormat.JSON]
        )
        
        assert len(generated_files) == 1
        assert generated_files[0].exists()
    
    def test_generate_team_composition_report(self, export_manager):
        """Test generating a team composition report."""
        data = {
            "composition_data": [
                Mock(
                    composition=Mock(composition_id="comp_123"),
                    total_games=5,
                    win_rate=0.8
                )
            ]
        }
        
        generated_files = export_manager.generate_comprehensive_report(
            "team_composition",
            data,
            [ExportFormat.CSV]
        )
        
        assert len(generated_files) == 1
        assert generated_files[0].exists()
    
    def test_generate_report_with_custom_config(self, export_manager):
        """Test generating report with custom configuration."""
        data = {"test": "data"}
        custom_config = {
            "decimal_places": 4,
            "include_metadata": False
        }
        
        generated_files = export_manager.generate_comprehensive_report(
            "player_performance",
            data,
            [ExportFormat.JSON],
            custom_config
        )
        
        assert len(generated_files) == 1
        assert generated_files[0].exists()
    
    def test_generate_report_invalid_template(self, export_manager):
        """Test generating report with invalid template."""
        with pytest.raises(ValueError, match="Template 'invalid' not found"):
            export_manager.generate_comprehensive_report(
                "invalid",
                {},
                [ExportFormat.JSON]
            )


if __name__ == "__main__":
    pytest.main([__file__])