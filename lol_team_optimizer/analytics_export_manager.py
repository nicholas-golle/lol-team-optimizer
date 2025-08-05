"""
Analytics Export Manager for comprehensive data export and reporting.

This module provides functionality to export analytics data in multiple formats
and generate comprehensive reports with customizable templates.
"""

import json
import csv
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import schedule
import time

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

from .analytics_models import (
    PlayerAnalytics, ChampionPerformanceMetrics, TeamComposition,
    CompositionPerformance, ChampionRecommendation, PerformanceDelta,
    AnalyticsFilters, TrendAnalysis, SynergyAnalysis
)


class ExportFormat(Enum):
    """Supported export formats."""
    CSV = "csv"
    JSON = "json"
    EXCEL = "xlsx"
    PDF = "pdf"


class ReportType(Enum):
    """Types of reports that can be generated."""
    PLAYER_PERFORMANCE = "player_performance"
    CHAMPION_ANALYSIS = "champion_analysis"
    TEAM_COMPOSITION = "team_composition"
    COMPARATIVE_ANALYSIS = "comparative_analysis"
    TREND_ANALYSIS = "trend_analysis"
    COMPREHENSIVE = "comprehensive"


@dataclass
class ExportConfiguration:
    """Configuration for data export operations."""
    format: ExportFormat
    include_metadata: bool = True
    include_raw_data: bool = False
    date_format: str = "%Y-%m-%d %H:%M:%S"
    decimal_places: int = 3
    custom_fields: Optional[List[str]] = None


@dataclass
class ReportTemplate:
    """Template configuration for report generation."""
    name: str
    report_type: ReportType
    title: str
    description: str
    sections: List[str]
    metrics: List[str]
    visualizations: List[str]
    custom_styling: Optional[Dict[str, Any]] = None


@dataclass
class ReportSchedule:
    """Configuration for scheduled report generation."""
    name: str
    template: ReportTemplate
    frequency: str  # daily, weekly, monthly
    recipients: List[str]
    export_formats: List[ExportFormat]
    filters: Optional[AnalyticsFilters] = None
    enabled: bool = True


class AnalyticsExportManager:
    """
    Comprehensive export and reporting manager for analytics data.
    
    Provides functionality to export analytics data in multiple formats,
    generate customizable reports, and manage scheduled reporting.
    """
    
    def __init__(self, output_directory: Path):
        """
        Initialize the export manager.
        
        Args:
            output_directory: Directory for storing exported files and reports
        """
        self.output_directory = Path(output_directory)
        self.output_directory.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger(__name__)
        self.templates: Dict[str, ReportTemplate] = {}
        self.schedules: Dict[str, ReportSchedule] = {}
        self.scheduler_thread: Optional[threading.Thread] = None
        self.scheduler_running = False
        
        # Initialize default templates
        self._initialize_default_templates()
        
        # Check for optional dependencies
        if not PANDAS_AVAILABLE:
            self.logger.warning("Pandas not available - Excel export will be limited")
        if not REPORTLAB_AVAILABLE:
            self.logger.warning("ReportLab not available - PDF export will be disabled")
    
    def _initialize_default_templates(self):
        """Initialize default report templates."""
        # Player Performance Template
        self.templates["player_performance"] = ReportTemplate(
            name="player_performance",
            report_type=ReportType.PLAYER_PERFORMANCE,
            title="Player Performance Analysis",
            description="Comprehensive analysis of individual player performance",
            sections=["summary", "performance_metrics", "champion_analysis", "trends"],
            metrics=["win_rate", "kda", "cs_per_min", "vision_score", "damage_per_min"],
            visualizations=["performance_chart", "trend_graph", "champion_breakdown"]
        )
        
        # Champion Analysis Template
        self.templates["champion_analysis"] = ReportTemplate(
            name="champion_analysis",
            report_type=ReportType.CHAMPION_ANALYSIS,
            title="Champion Performance Analysis",
            description="Detailed analysis of champion performance and recommendations",
            sections=["champion_overview", "performance_comparison", "recommendations"],
            metrics=["win_rate", "pick_rate", "performance_delta", "synergy_score"],
            visualizations=["champion_comparison", "recommendation_chart"]
        )
        
        # Team Composition Template
        self.templates["team_composition"] = ReportTemplate(
            name="team_composition",
            report_type=ReportType.TEAM_COMPOSITION,
            title="Team Composition Analysis",
            description="Analysis of team compositions and synergy effects",
            sections=["composition_overview", "synergy_analysis", "optimal_compositions"],
            metrics=["composition_win_rate", "synergy_effects", "performance_deltas"],
            visualizations=["synergy_matrix", "composition_comparison"]
        ) 
   
    def export_player_analytics(
        self,
        analytics: PlayerAnalytics,
        format: ExportFormat,
        config: Optional[ExportConfiguration] = None
    ) -> Path:
        """
        Export player analytics data in the specified format.
        
        Args:
            analytics: Player analytics data to export
            format: Export format
            config: Export configuration options
            
        Returns:
            Path to the exported file
        """
        if config is None:
            config = ExportConfiguration(format=format)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"player_analytics_{analytics.puuid}_{timestamp}.{format.value}"
        filepath = self.output_directory / filename
        
        try:
            if format == ExportFormat.JSON:
                self._export_to_json(analytics, filepath, config)
            elif format == ExportFormat.CSV:
                self._export_player_to_csv(analytics, filepath, config)
            elif format == ExportFormat.EXCEL:
                self._export_player_to_excel(analytics, filepath, config)
            elif format == ExportFormat.PDF:
                self._export_player_to_pdf(analytics, filepath, config)
            else:
                raise ValueError(f"Unsupported export format: {format}")
            
            self.logger.info(f"Exported player analytics to {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Failed to export player analytics: {e}")
            raise
    
    def export_champion_analytics(
        self,
        champion_data: List[ChampionPerformanceMetrics],
        format: ExportFormat,
        config: Optional[ExportConfiguration] = None
    ) -> Path:
        """
        Export champion analytics data in the specified format.
        
        Args:
            champion_data: Champion performance data to export
            format: Export format
            config: Export configuration options
            
        Returns:
            Path to the exported file
        """
        if config is None:
            config = ExportConfiguration(format=format)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"champion_analytics_{timestamp}.{format.value}"
        filepath = self.output_directory / filename
        
        try:
            if format == ExportFormat.JSON:
                self._export_to_json(champion_data, filepath, config)
            elif format == ExportFormat.CSV:
                self._export_champion_to_csv(champion_data, filepath, config)
            elif format == ExportFormat.EXCEL:
                self._export_champion_to_excel(champion_data, filepath, config)
            elif format == ExportFormat.PDF:
                self._export_champion_to_pdf(champion_data, filepath, config)
            else:
                raise ValueError(f"Unsupported export format: {format}")
            
            self.logger.info(f"Exported champion analytics to {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Failed to export champion analytics: {e}")
            raise
    
    def _export_to_json(self, data: Any, filepath: Path, config: ExportConfiguration):
        """Export data to JSON format."""
        export_data = {
            "metadata": {
                "export_timestamp": datetime.now().strftime(config.date_format),
                "format": "json",
                "version": "1.0"
            } if config.include_metadata else {},
            "data": self._serialize_for_json(data)
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
    
    def _serialize_for_json(self, obj: Any) -> Any:
        """Serialize objects for JSON export."""
        if hasattr(obj, '__dict__'):
            return asdict(obj) if hasattr(obj, '__dataclass_fields__') else obj.__dict__
        elif isinstance(obj, list):
            return [self._serialize_for_json(item) for item in obj]
        elif isinstance(obj, dict):
            return {k: self._serialize_for_json(v) for k, v in obj.items()}
        else:
            return obj
    
    def _export_player_to_csv(self, analytics: PlayerAnalytics, filepath: Path, config: ExportConfiguration):
        """Export player analytics to CSV format."""
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write metadata if requested
            if config.include_metadata:
                writer.writerow(["# Player Analytics Export"])
                writer.writerow(["# Export Date:", datetime.now().strftime(config.date_format)])
                writer.writerow(["# Player PUUID:", analytics.puuid])
                writer.writerow([])
            
            # Write overall performance
            writer.writerow(["Overall Performance"])
            writer.writerow(["Metric", "Value"])
            if analytics.overall_performance:
                perf = analytics.overall_performance
                writer.writerow(["Win Rate", f"{perf.win_rate:.{config.decimal_places}f}"])
                writer.writerow(["Average KDA", f"{perf.avg_kda:.{config.decimal_places}f}"])
                writer.writerow(["CS per Minute", f"{perf.avg_cs_per_min:.{config.decimal_places}f}"])
                writer.writerow(["Vision Score", f"{perf.avg_vision_score:.{config.decimal_places}f}"])
                writer.writerow(["Damage per Minute", f"{perf.avg_damage_per_min:.{config.decimal_places}f}"])
    
    def _export_champion_to_csv(self, champion_data: List[ChampionPerformanceMetrics], filepath: Path, config: ExportConfiguration):
        """Export champion analytics to CSV format."""
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write metadata if requested
            if config.include_metadata:
                writer.writerow(["# Champion Analytics Export"])
                writer.writerow(["# Export Date:", datetime.now().strftime(config.date_format)])
                writer.writerow([])
            
            # Write champion data
            writer.writerow([
                "Champion", "Role", "Games Played", "Win Rate", "Average KDA",
                "CS per Minute", "Vision Score", "Damage per Minute"
            ])
            
            for champion in champion_data:
                writer.writerow([
                    champion.champion_name,
                    champion.role,
                    champion.games_played,
                    f"{champion.win_rate:.{config.decimal_places}f}",
                    f"{champion.avg_kda:.{config.decimal_places}f}",
                    f"{champion.avg_cs_per_min:.{config.decimal_places}f}",
                    f"{champion.avg_vision_score:.{config.decimal_places}f}",
                    f"{champion.avg_damage_per_min:.{config.decimal_places}f}"
                ])
    
    def _export_player_to_excel(self, analytics: PlayerAnalytics, filepath: Path, config: ExportConfiguration):
        """Export player analytics to Excel format."""
        if not PANDAS_AVAILABLE:
            raise RuntimeError("Pandas is required for Excel export")
        
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # Overall performance sheet
            if analytics.overall_performance:
                perf = analytics.overall_performance
                overall_data = {
                    'Metric': ['Win Rate', 'Average KDA', 'CS per Minute', 'Vision Score', 'Damage per Minute'],
                    'Value': [
                        round(perf.win_rate, config.decimal_places),
                        round(perf.avg_kda, config.decimal_places),
                        round(perf.avg_cs_per_min, config.decimal_places),
                        round(perf.avg_vision_score, config.decimal_places),
                        round(perf.avg_damage_per_min, config.decimal_places)
                    ]
                }
                overall_df = pd.DataFrame(overall_data)
                overall_df.to_excel(writer, sheet_name='Overall Performance', index=False)
    
    def _export_champion_to_excel(self, champion_data: List[ChampionPerformanceMetrics], filepath: Path, config: ExportConfiguration):
        """Export champion analytics to Excel format."""
        if not PANDAS_AVAILABLE:
            raise RuntimeError("Pandas is required for Excel export")
        
        data = []
        for champion in champion_data:
            data.append({
                'Champion': champion.champion_name,
                'Role': champion.role,
                'Games': champion.games_played,
                'Win Rate': round(champion.win_rate, config.decimal_places),
                'KDA': round(champion.avg_kda, config.decimal_places),
                'CS/min': round(champion.avg_cs_per_min, config.decimal_places),
                'Vision Score': round(champion.avg_vision_score, config.decimal_places),
                'Damage/min': round(champion.avg_damage_per_min, config.decimal_places)
            })
        
        df = pd.DataFrame(data)
        df.to_excel(filepath, index=False)
    
    def _export_player_to_pdf(self, analytics: PlayerAnalytics, filepath: Path, config: ExportConfiguration):
        """Export player analytics to PDF format."""
        if not REPORTLAB_AVAILABLE:
            raise RuntimeError("ReportLab is required for PDF export")
        
        doc = SimpleDocTemplate(str(filepath), pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1  # Center alignment
        )
        story.append(Paragraph("Player Performance Analytics Report", title_style))
        story.append(Spacer(1, 12))
        
        # Player info
        story.append(Paragraph(f"<b>Player PUUID:</b> {analytics.puuid}", styles['Normal']))
        story.append(Paragraph(f"<b>Report Generated:</b> {datetime.now().strftime(config.date_format)}", styles['Normal']))
        story.append(Spacer(1, 12))
        
        doc.build(story)
    
    def _export_champion_to_pdf(self, champion_data: List[ChampionPerformanceMetrics], filepath: Path, config: ExportConfiguration):
        """Export champion analytics to PDF format."""
        if not REPORTLAB_AVAILABLE:
            raise RuntimeError("ReportLab is required for PDF export")
        
        doc = SimpleDocTemplate(str(filepath), pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1
        )
        story.append(Paragraph("Champion Performance Analytics Report", title_style))
        story.append(Spacer(1, 12))
        
        doc.build(story)
    
    def get_export_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about export operations.
        
        Returns:
            Dictionary containing export statistics
        """
        output_files = list(self.output_directory.glob("*"))
        
        stats = {
            "total_files": len(output_files),
            "files_by_format": {},
            "files_by_type": {},
            "total_size_mb": 0,
            "latest_export": None,
            "oldest_export": None
        }
        
        if output_files:
            # Calculate file statistics
            for file_path in output_files:
                if file_path.is_file():
                    # File format
                    format_ext = file_path.suffix.lower().lstrip('.')
                    stats["files_by_format"][format_ext] = stats["files_by_format"].get(format_ext, 0) + 1
                    
                    # File type (based on filename)
                    if "player" in file_path.name:
                        stats["files_by_type"]["player"] = stats["files_by_type"].get("player", 0) + 1
                    elif "champion" in file_path.name:
                        stats["files_by_type"]["champion"] = stats["files_by_type"].get("champion", 0) + 1
                    
                    # File size
                    stats["total_size_mb"] += file_path.stat().st_size / (1024 * 1024)
                    
                    # File dates
                    file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if stats["latest_export"] is None or file_time > stats["latest_export"]:
                        stats["latest_export"] = file_time
                    if stats["oldest_export"] is None or file_time < stats["oldest_export"]:
                        stats["oldest_export"] = file_time
        
        stats["total_size_mb"] = round(stats["total_size_mb"], 2)
        return stats
    
    def export_multiple_formats(
        self,
        data: Any,
        data_type: str,
        formats: List[ExportFormat],
        custom_config: Optional[Dict[str, Any]] = None
    ) -> List[Path]:
        """
        Export data in multiple formats simultaneously.
        
        Args:
            data: Data to export
            data_type: Type of data (player, champion, composition)
            formats: List of formats to export in
            custom_config: Custom configuration options
            
        Returns:
            List of paths to exported files
        """
        exported_files = []
        
        for format in formats:
            config = ExportConfiguration(format=format)
            if custom_config:
                for key, value in custom_config.items():
                    if hasattr(config, key):
                        setattr(config, key, value)
            
            try:
                if data_type == "player":
                    filepath = self.export_player_analytics(data, format, config)
                elif data_type == "champion":
                    filepath = self.export_champion_analytics(data, format, config)
                else:
                    raise ValueError(f"Unsupported data type: {data_type}")
                
                exported_files.append(filepath)
                
            except Exception as e:
                self.logger.error(f"Failed to export in format {format.value}: {e}")
                continue
        
        return exported_files