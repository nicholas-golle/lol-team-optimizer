"""
Bulk Operations and Data Import/Export Manager

This module provides comprehensive bulk operations for player data including:
- CSV/Excel import with data mapping and validation
- Bulk edit operations for multiple players
- Export functionality in multiple formats (CSV, JSON, PDF)
- Data migration tools for existing player databases
- Backup and restore functionality
- Audit logging for all player data modifications
"""

import csv
import json
import logging
import pandas as pd
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import asdict
from io import StringIO, BytesIO

from .models import Player, ChampionMastery
from .data_manager import DataManager
from .config import Config


class AuditLogger:
    """Handles audit logging for all player data modifications."""
    
    def __init__(self, config: Config):
        """Initialize audit logger with database connection."""
        self.config = config
        self.audit_db_path = Path(config.data_directory) / "audit_log.db"
        self.logger = logging.getLogger(__name__)
        self._init_audit_database()
    
    def _init_audit_database(self) -> None:
        """Initialize audit log database."""
        try:
            with sqlite3.connect(self.audit_db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS audit_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        operation TEXT NOT NULL,
                        entity_type TEXT NOT NULL,
                        entity_id TEXT NOT NULL,
                        old_data TEXT,
                        new_data TEXT,
                        user_id TEXT,
                        session_id TEXT,
                        ip_address TEXT,
                        details TEXT
                    )
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_audit_timestamp 
                    ON audit_log(timestamp)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_audit_entity 
                    ON audit_log(entity_type, entity_id)
                """)
                
                conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to initialize audit database: {e}")
    
    def log_operation(self, operation: str, entity_type: str, entity_id: str,
                     old_data: Optional[Dict] = None, new_data: Optional[Dict] = None,
                     user_id: Optional[str] = None, session_id: Optional[str] = None,
                     ip_address: Optional[str] = None, details: Optional[str] = None) -> None:
        """Log an audit event."""
        try:
            with sqlite3.connect(self.audit_db_path) as conn:
                conn.execute("""
                    INSERT INTO audit_log 
                    (timestamp, operation, entity_type, entity_id, old_data, new_data, 
                     user_id, session_id, ip_address, details)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    datetime.now().isoformat(),
                    operation,
                    entity_type,
                    entity_id,
                    json.dumps(old_data, default=str) if old_data else None,
                    json.dumps(new_data, default=str) if new_data else None,
                    user_id,
                    session_id,
                    ip_address,
                    details
                ))
                conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to log audit event: {e}")
    
    def get_audit_history(self, entity_type: Optional[str] = None, 
                         entity_id: Optional[str] = None,
                         start_date: Optional[datetime] = None,
                         end_date: Optional[datetime] = None,
                         limit: int = 1000) -> List[Dict[str, Any]]:
        """Retrieve audit history with optional filters."""
        try:
            with sqlite3.connect(self.audit_db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                query = "SELECT * FROM audit_log WHERE 1=1"
                params = []
                
                if entity_type:
                    query += " AND entity_type = ?"
                    params.append(entity_type)
                
                if entity_id:
                    query += " AND entity_id = ?"
                    params.append(entity_id)
                
                if start_date:
                    query += " AND timestamp >= ?"
                    params.append(start_date.isoformat())
                
                if end_date:
                    query += " AND timestamp <= ?"
                    params.append(end_date.isoformat())
                
                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)
                
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            self.logger.error(f"Failed to retrieve audit history: {e}")
            return []


class DataValidator:
    """Validates player data during import operations."""
    
    def __init__(self):
        """Initialize validator."""
        self.logger = logging.getLogger(__name__)
        self.validation_rules = self._load_validation_rules()
    
    def _load_validation_rules(self) -> Dict[str, Dict]:
        """Load validation rules for player data."""
        return {
            'player_name': {
                'required': True,
                'min_length': 2,
                'max_length': 50,
                'invalid_chars': ['<', '>', '"', "'", '&', '\\', '/']
            },
            'summoner_name': {
                'required': True,
                'min_length': 3,
                'max_length': 16,
                'pattern': r'^[a-zA-Z0-9\s\-_]+$'
            },
            'riot_tag': {
                'required': False,
                'min_length': 2,
                'max_length': 5,
                'pattern': r'^[A-Z0-9]+$'
            },
            'role_preferences': {
                'required': False,
                'min_value': 1,
                'max_value': 5,
                'valid_roles': ['top', 'jungle', 'middle', 'bottom', 'support']
            }
        }
    
    def validate_player_data(self, player_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate player data against rules."""
        errors = []
        
        # Validate player name
        if not self._validate_field(player_data.get('player_name', ''), 'player_name'):
            errors.append("Invalid player name")
        
        # Validate summoner name
        if not self._validate_field(player_data.get('summoner_name', ''), 'summoner_name'):
            errors.append("Invalid summoner name")
        
        # Validate riot tag if provided
        riot_tag = player_data.get('riot_tag', '')
        if riot_tag and not self._validate_field(riot_tag, 'riot_tag'):
            errors.append("Invalid riot tag")
        
        # Validate role preferences
        for role in self.validation_rules['role_preferences']['valid_roles']:
            pref_key = f"{role}_pref"
            if pref_key in player_data:
                try:
                    pref_value = int(player_data[pref_key])
                    if not (1 <= pref_value <= 5):
                        errors.append(f"Invalid {role} preference: must be 1-5")
                except (ValueError, TypeError):
                    errors.append(f"Invalid {role} preference: must be a number")
        
        return len(errors) == 0, errors
    
    def _validate_field(self, value: str, field_name: str) -> bool:
        """Validate individual field against rules."""
        rules = self.validation_rules.get(field_name, {})
        
        if not value and rules.get('required', False):
            return False
        
        if not value:
            return True  # Optional field
        
        # Length validation
        if 'min_length' in rules and len(value) < rules['min_length']:
            return False
        
        if 'max_length' in rules and len(value) > rules['max_length']:
            return False
        
        # Pattern validation
        if 'pattern' in rules:
            import re
            if not re.match(rules['pattern'], value):
                return False
        
        # Invalid characters
        if 'invalid_chars' in rules:
            if any(char in value for char in rules['invalid_chars']):
                return False
        
        return True


class ImportProcessor:
    """Processes data imports from various file formats."""
    
    def __init__(self, data_manager: DataManager, audit_logger: AuditLogger):
        """Initialize import processor."""
        self.data_manager = data_manager
        self.audit_logger = audit_logger
        self.validator = DataValidator()
        self.logger = logging.getLogger(__name__)
    
    def process_csv_import(self, file_path: str, field_mapping: Dict[str, str],
                          options: Dict[str, Any]) -> Tuple[List[Player], List[str], Dict[str, Any]]:
        """Process CSV file import with validation and mapping."""
        players = []
        errors = []
        stats = {'processed': 0, 'valid': 0, 'invalid': 0, 'duplicates': 0}
        
        try:
            # Read CSV with specified options
            delimiter = options.get('delimiter', ',')
            encoding = options.get('encoding', 'utf-8')
            has_header = options.get('has_header', True)
            skip_rows = options.get('skip_rows', 0)
            
            with open(file_path, 'r', encoding=encoding) as f:
                # Skip specified rows
                for _ in range(skip_rows):
                    next(f, None)
                
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
            
            # Get existing players to check for duplicates
            existing_players = {p.name.lower(): p for p in self.data_manager.load_player_data()}
            
            # Process each row
            for i, row in enumerate(rows, 1):
                stats['processed'] += 1
                
                try:
                    # Map fields
                    mapped_data = self._map_row_data(row, field_mapping)
                    
                    # Validate data
                    is_valid, validation_errors = self.validator.validate_player_data(mapped_data)
                    
                    if not is_valid:
                        stats['invalid'] += 1
                        errors.append(f"Row {i}: {'; '.join(validation_errors)}")
                        continue
                    
                    # Check for duplicates
                    player_name = mapped_data['player_name'].lower()
                    if player_name in existing_players:
                        stats['duplicates'] += 1
                        if not options.get('allow_duplicates', False):
                            errors.append(f"Row {i}: Duplicate player name '{mapped_data['player_name']}'")
                            continue
                    
                    # Create player
                    player = self._create_player_from_data(mapped_data)
                    players.append(player)
                    stats['valid'] += 1
                    
                    # Log import
                    self.audit_logger.log_operation(
                        operation="IMPORT",
                        entity_type="Player",
                        entity_id=player.name,
                        new_data=asdict(player),
                        details=f"Imported from CSV row {i}"
                    )
                    
                except Exception as e:
                    stats['invalid'] += 1
                    errors.append(f"Row {i}: {str(e)}")
            
        except Exception as e:
            errors.append(f"Failed to read CSV file: {str(e)}")
        
        return players, errors, stats
    
    def process_excel_import(self, file_path: str, field_mapping: Dict[str, str],
                           options: Dict[str, Any]) -> Tuple[List[Player], List[str], Dict[str, Any]]:
        """Process Excel file import with validation and mapping."""
        players = []
        errors = []
        stats = {'processed': 0, 'valid': 0, 'invalid': 0, 'duplicates': 0}
        
        try:
            # Read Excel file
            sheet_name = options.get('sheet_name', 0)
            skip_rows = options.get('skip_rows', 0)
            
            df = pd.read_excel(file_path, sheet_name=sheet_name, skiprows=skip_rows)
            
            # Get existing players to check for duplicates
            existing_players = {p.name.lower(): p for p in self.data_manager.load_player_data()}
            
            # Process each row
            for i, row in df.iterrows():
                stats['processed'] += 1
                
                try:
                    # Convert row to dict
                    row_dict = row.to_dict()
                    
                    # Map fields
                    mapped_data = self._map_row_data(row_dict, field_mapping)
                    
                    # Validate data
                    is_valid, validation_errors = self.validator.validate_player_data(mapped_data)
                    
                    if not is_valid:
                        stats['invalid'] += 1
                        errors.append(f"Row {i+1}: {'; '.join(validation_errors)}")
                        continue
                    
                    # Check for duplicates
                    player_name = mapped_data['player_name'].lower()
                    if player_name in existing_players:
                        stats['duplicates'] += 1
                        if not options.get('allow_duplicates', False):
                            errors.append(f"Row {i+1}: Duplicate player name '{mapped_data['player_name']}'")
                            continue
                    
                    # Create player
                    player = self._create_player_from_data(mapped_data)
                    players.append(player)
                    stats['valid'] += 1
                    
                    # Log import
                    self.audit_logger.log_operation(
                        operation="IMPORT",
                        entity_type="Player",
                        entity_id=player.name,
                        new_data=asdict(player),
                        details=f"Imported from Excel row {i+1}"
                    )
                    
                except Exception as e:
                    stats['invalid'] += 1
                    errors.append(f"Row {i+1}: {str(e)}")
            
        except Exception as e:
            errors.append(f"Failed to read Excel file: {str(e)}")
        
        return players, errors, stats
    
    def process_json_import(self, file_path: str, options: Dict[str, Any]) -> Tuple[List[Player], List[str], Dict[str, Any]]:
        """Process JSON file import with validation."""
        players = []
        errors = []
        stats = {'processed': 0, 'valid': 0, 'invalid': 0, 'duplicates': 0}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                errors.append("JSON file must contain a list of player objects")
                return players, errors, stats
            
            # Get existing players to check for duplicates
            existing_players = {p.name.lower(): p for p in self.data_manager.load_player_data()}
            
            # Process each player object
            for i, player_data in enumerate(data):
                stats['processed'] += 1
                
                try:
                    if not isinstance(player_data, dict):
                        stats['invalid'] += 1
                        errors.append(f"Player {i+1}: Must be an object")
                        continue
                    
                    # Validate data
                    is_valid, validation_errors = self.validator.validate_player_data(player_data)
                    
                    if not is_valid:
                        stats['invalid'] += 1
                        errors.append(f"Player {i+1}: {'; '.join(validation_errors)}")
                        continue
                    
                    # Check for duplicates
                    player_name = player_data['player_name'].lower()
                    if player_name in existing_players:
                        stats['duplicates'] += 1
                        if not options.get('allow_duplicates', False):
                            errors.append(f"Player {i+1}: Duplicate player name '{player_data['player_name']}'")
                            continue
                    
                    # Create player
                    player = self._create_player_from_data(player_data)
                    players.append(player)
                    stats['valid'] += 1
                    
                    # Log import
                    self.audit_logger.log_operation(
                        operation="IMPORT",
                        entity_type="Player",
                        entity_id=player.name,
                        new_data=asdict(player),
                        details=f"Imported from JSON entry {i+1}"
                    )
                    
                except Exception as e:
                    stats['invalid'] += 1
                    errors.append(f"Player {i+1}: {str(e)}")
            
        except Exception as e:
            errors.append(f"Failed to read JSON file: {str(e)}")
        
        return players, errors, stats
    
    def _map_row_data(self, row: Dict[str, Any], field_mapping: Dict[str, str]) -> Dict[str, Any]:
        """Map row data using field mapping."""
        mapped_data = {}
        
        for field, column in field_mapping.items():
            if column != "Not Mapped" and column in row:
                value = row[column]
                # Clean and convert value
                if isinstance(value, str):
                    value = value.strip()
                elif pd.isna(value):
                    value = ""
                mapped_data[field] = value
        
        return mapped_data
    
    def _create_player_from_data(self, data: Dict[str, Any]) -> Player:
        """Create player from mapped data."""
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


class ExportProcessor:
    """Processes data exports to various formats."""
    
    def __init__(self, data_manager: DataManager, audit_logger: AuditLogger):
        """Initialize export processor."""
        self.data_manager = data_manager
        self.audit_logger = audit_logger
        self.logger = logging.getLogger(__name__)
    
    def export_to_csv(self, players: List[Player], options: Dict[str, Any]) -> str:
        """Export players to CSV format."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='')
        
        try:
            # Define headers based on options
            headers = ["player_name", "summoner_name", "puuid"]
            
            if options.get('include_preferences', True):
                headers.extend(["top_pref", "jungle_pref", "middle_pref", "bottom_pref", "support_pref"])
            
            if options.get('include_metadata', False):
                headers.extend(["last_updated", "champion_count", "total_mastery_points"])
            
            writer = csv.writer(temp_file, delimiter=options.get('delimiter', ','))
            writer.writerow(headers)
            
            # Write player data
            for player in players:
                row = [player.name, player.summoner_name, player.puuid]
                
                if options.get('include_preferences', True):
                    row.extend([
                        player.role_preferences.get("top", 3),
                        player.role_preferences.get("jungle", 3),
                        player.role_preferences.get("middle", 3),
                        player.role_preferences.get("bottom", 3),
                        player.role_preferences.get("support", 3)
                    ])
                
                if options.get('include_metadata', False):
                    row.extend([
                        player.last_updated.isoformat() if player.last_updated else "",
                        len(player.champion_masteries),
                        sum(m.mastery_points for m in player.champion_masteries.values())
                    ])
                
                writer.writerow(row)
            
            # Log export
            self.audit_logger.log_operation(
                operation="EXPORT",
                entity_type="Player",
                entity_id="bulk",
                details=f"Exported {len(players)} players to CSV"
            )
            
        finally:
            temp_file.close()
        
        return temp_file.name
    
    def export_to_excel(self, players: List[Player], options: Dict[str, Any]) -> str:
        """Export players to Excel format."""
        temp_file = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
        temp_file.close()
        
        try:
            # Prepare data
            data = []
            for player in players:
                row = {
                    "player_name": player.name,
                    "summoner_name": player.summoner_name,
                    "puuid": player.puuid
                }
                
                if options.get('include_preferences', True):
                    row.update({
                        "top_pref": player.role_preferences.get("top", 3),
                        "jungle_pref": player.role_preferences.get("jungle", 3),
                        "middle_pref": player.role_preferences.get("middle", 3),
                        "bottom_pref": player.role_preferences.get("bottom", 3),
                        "support_pref": player.role_preferences.get("support", 3)
                    })
                
                if options.get('include_metadata', False):
                    row.update({
                        "last_updated": player.last_updated.isoformat() if player.last_updated else "",
                        "champion_count": len(player.champion_masteries),
                        "total_mastery_points": sum(m.mastery_points for m in player.champion_masteries.values())
                    })
                
                data.append(row)
            
            # Create DataFrame and save
            df = pd.DataFrame(data)
            
            with pd.ExcelWriter(temp_file.name, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Players', index=False)
                
                # Add summary sheet if requested
                if options.get('include_summary', False):
                    summary_data = self._generate_summary_data(players)
                    summary_df = pd.DataFrame(summary_data)
                    summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Log export
            self.audit_logger.log_operation(
                operation="EXPORT",
                entity_type="Player",
                entity_id="bulk",
                details=f"Exported {len(players)} players to Excel"
            )
            
        except Exception as e:
            self.logger.error(f"Excel export failed: {e}")
            raise
        
        return temp_file.name
    
    def export_to_json(self, players: List[Player], options: Dict[str, Any]) -> str:
        """Export players to JSON format."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        
        try:
            # Prepare data
            data = []
            for player in players:
                player_data = {
                    "player_name": player.name,
                    "summoner_name": player.summoner_name,
                    "puuid": player.puuid
                }
                
                if options.get('include_preferences', True):
                    player_data["role_preferences"] = player.role_preferences
                
                if options.get('include_masteries', False):
                    masteries = {}
                    for champ_id, mastery in player.champion_masteries.items():
                        masteries[str(champ_id)] = {
                            "champion_name": mastery.champion_name,
                            "mastery_level": mastery.mastery_level,
                            "mastery_points": mastery.mastery_points,
                            "chest_granted": mastery.chest_granted
                        }
                    player_data["champion_masteries"] = masteries
                
                if options.get('include_metadata', False):
                    player_data.update({
                        "last_updated": player.last_updated.isoformat() if player.last_updated else None,
                        "champion_count": len(player.champion_masteries),
                        "total_mastery_points": sum(m.mastery_points for m in player.champion_masteries.values())
                    })
                
                data.append(player_data)
            
            # Write JSON
            json.dump(data, temp_file, indent=2, ensure_ascii=False)
            
            # Log export
            self.audit_logger.log_operation(
                operation="EXPORT",
                entity_type="Player",
                entity_id="bulk",
                details=f"Exported {len(players)} players to JSON"
            )
            
        finally:
            temp_file.close()
        
        return temp_file.name
    
    def export_to_pdf(self, players: List[Player], options: Dict[str, Any]) -> str:
        """Export players to PDF format."""
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
        except ImportError:
            raise ImportError("reportlab is required for PDF export. Install with: pip install reportlab")
        
        temp_file = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        temp_file.close()
        
        try:
            # Create PDF document
            doc = SimpleDocTemplate(temp_file.name, pagesize=A4)
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
            story.append(Paragraph("Player Data Export", title_style))
            story.append(Spacer(1, 12))
            
            # Summary information
            summary_style = styles['Normal']
            story.append(Paragraph(f"Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", summary_style))
            story.append(Paragraph(f"Total Players: {len(players)}", summary_style))
            story.append(Spacer(1, 20))
            
            # Player table
            table_data = [["Player Name", "Summoner Name", "Top", "Jungle", "Mid", "ADC", "Support"]]
            
            for player in players:
                row = [
                    player.name,
                    player.summoner_name,
                    str(player.role_preferences.get("top", 3)),
                    str(player.role_preferences.get("jungle", 3)),
                    str(player.role_preferences.get("middle", 3)),
                    str(player.role_preferences.get("bottom", 3)),
                    str(player.role_preferences.get("support", 3))
                ]
                table_data.append(row)
            
            # Create table
            table = Table(table_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 14),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(table)
            
            # Build PDF
            doc.build(story)
            
            # Log export
            self.audit_logger.log_operation(
                operation="EXPORT",
                entity_type="Player",
                entity_id="bulk",
                details=f"Exported {len(players)} players to PDF"
            )
            
        except Exception as e:
            self.logger.error(f"PDF export failed: {e}")
            raise
        
        return temp_file.name
    
    def _generate_summary_data(self, players: List[Player]) -> List[Dict[str, Any]]:
        """Generate summary data for export."""
        summary = []
        
        # Overall statistics
        total_players = len(players)
        total_masteries = sum(len(p.champion_masteries) for p in players)
        avg_masteries = total_masteries / total_players if total_players > 0 else 0
        
        summary.append({
            "Metric": "Total Players",
            "Value": total_players
        })
        
        summary.append({
            "Metric": "Total Champion Masteries",
            "Value": total_masteries
        })
        
        summary.append({
            "Metric": "Average Masteries per Player",
            "Value": round(avg_masteries, 2)
        })
        
        # Role preference distribution
        role_totals = {"top": 0, "jungle": 0, "middle": 0, "bottom": 0, "support": 0}
        for player in players:
            for role, pref in player.role_preferences.items():
                role_totals[role] += pref
        
        for role, total in role_totals.items():
            avg_pref = total / total_players if total_players > 0 else 0
            summary.append({
                "Metric": f"Average {role.title()} Preference",
                "Value": round(avg_pref, 2)
            })
        
        return summary


class BulkOperationsManager:
    """Main manager for bulk operations and data import/export."""
    
    def __init__(self, data_manager: DataManager, config: Config):
        """Initialize bulk operations manager."""
        self.data_manager = data_manager
        self.config = config
        self.audit_logger = AuditLogger(config)
        self.import_processor = ImportProcessor(data_manager, self.audit_logger)
        self.export_processor = ExportProcessor(data_manager, self.audit_logger)
        self.logger = logging.getLogger(__name__)
    
    def bulk_edit_players(self, player_names: List[str], updates: Dict[str, Any],
                         user_id: Optional[str] = None) -> Tuple[int, List[str]]:
        """Perform bulk edit operations on multiple players."""
        success_count = 0
        errors = []
        
        try:
            players = self.data_manager.load_player_data()
            player_dict = {p.name: p for p in players}
            
            for player_name in player_names:
                if player_name not in player_dict:
                    errors.append(f"Player '{player_name}' not found")
                    continue
                
                try:
                    player = player_dict[player_name]
                    old_data = asdict(player)
                    
                    # Apply updates
                    if 'role_preferences' in updates:
                        player.role_preferences.update(updates['role_preferences'])
                    
                    if 'summoner_name' in updates:
                        player.summoner_name = updates['summoner_name']
                    
                    # Update timestamp
                    player.last_updated = datetime.now()
                    
                    # Log the change
                    self.audit_logger.log_operation(
                        operation="BULK_EDIT",
                        entity_type="Player",
                        entity_id=player.name,
                        old_data=old_data,
                        new_data=asdict(player),
                        user_id=user_id,
                        details="Bulk edit operation"
                    )
                    
                    success_count += 1
                    
                except Exception as e:
                    errors.append(f"Failed to update '{player_name}': {str(e)}")
            
            # Save updated players
            if success_count > 0:
                self.data_manager.save_player_data(list(player_dict.values()))
            
        except Exception as e:
            errors.append(f"Bulk edit operation failed: {str(e)}")
        
        return success_count, errors
    
    def create_backup(self, backup_name: Optional[str] = None) -> str:
        """Create a backup of all player data."""
        if not backup_name:
            backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        backup_dir = Path(self.config.data_directory) / "backups"
        backup_dir.mkdir(exist_ok=True)
        
        backup_file = backup_dir / f"{backup_name}.zip"
        
        try:
            with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED) as zf:
                # Add player data
                player_file = Path(self.config.data_directory) / self.config.player_data_file
                if player_file.exists():
                    zf.write(player_file, "players.json")
                
                # Add audit log
                if self.audit_logger.audit_db_path.exists():
                    zf.write(self.audit_logger.audit_db_path, "audit_log.db")
                
                # Add metadata
                metadata = {
                    "backup_date": datetime.now().isoformat(),
                    "backup_name": backup_name,
                    "version": "1.0"
                }
                
                metadata_json = json.dumps(metadata, indent=2)
                zf.writestr("metadata.json", metadata_json)
            
            # Log backup creation
            self.audit_logger.log_operation(
                operation="BACKUP_CREATE",
                entity_type="System",
                entity_id=backup_name,
                details=f"Created backup: {backup_file}"
            )
            
            return str(backup_file)
            
        except Exception as e:
            self.logger.error(f"Backup creation failed: {e}")
            raise
    
    def restore_backup(self, backup_file: str, user_id: Optional[str] = None) -> bool:
        """Restore player data from backup."""
        try:
            backup_path = Path(backup_file)
            if not backup_path.exists():
                raise FileNotFoundError(f"Backup file not found: {backup_file}")
            
            # Create current backup before restore
            current_backup = self.create_backup("pre_restore_backup")
            
            with zipfile.ZipFile(backup_path, 'r') as zf:
                # Extract player data
                if "players.json" in zf.namelist():
                    player_data = zf.read("players.json")
                    player_file = Path(self.config.data_directory) / self.config.player_data_file
                    with open(player_file, 'wb') as f:
                        f.write(player_data)
                    
                    # Clear the data manager cache to force reload
                    self.data_manager._players_cache = {}
                    self.data_manager._cache_last_loaded = None
                
                # Extract audit log if present
                if "audit_log.db" in zf.namelist():
                    audit_data = zf.read("audit_log.db")
                    with open(self.audit_logger.audit_db_path, 'wb') as f:
                        f.write(audit_data)
            
            # Log restore operation
            self.audit_logger.log_operation(
                operation="BACKUP_RESTORE",
                entity_type="System",
                entity_id=backup_path.name,
                user_id=user_id,
                details=f"Restored from backup: {backup_file}. Current backup saved as: {current_backup}"
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Backup restore failed: {e}")
            raise
    
    def migrate_from_legacy_format(self, legacy_file: str, format_type: str) -> Tuple[int, List[str]]:
        """Migrate player data from legacy formats."""
        migrated_count = 0
        errors = []
        
        try:
            if format_type.lower() == "csv":
                # Define legacy CSV mapping
                legacy_mapping = {
                    'player_name': 'Name',
                    'summoner_name': 'Summoner',
                    'top_pref': 'Top',
                    'jungle_pref': 'Jungle',
                    'middle_pref': 'Mid',
                    'bottom_pref': 'ADC',
                    'support_pref': 'Support'
                }
                
                players, import_errors, stats = self.import_processor.process_csv_import(
                    legacy_file, legacy_mapping, {'has_header': True}
                )
                
                if players:
                    # Save migrated players
                    existing_players = self.data_manager.load_player_data()
                    all_players = existing_players + players
                    self.data_manager.save_player_data(all_players)
                    migrated_count = len(players)
                
                errors.extend(import_errors)
                
            else:
                errors.append(f"Unsupported legacy format: {format_type}")
            
            # Log migration
            self.audit_logger.log_operation(
                operation="MIGRATE",
                entity_type="System",
                entity_id="legacy_data",
                details=f"Migrated {migrated_count} players from {format_type} format"
            )
            
        except Exception as e:
            errors.append(f"Migration failed: {str(e)}")
        
        return migrated_count, errors
    
    def get_bulk_operation_templates(self) -> Dict[str, str]:
        """Generate template files for bulk operations."""
        templates = {}
        
        # CSV template
        csv_template = StringIO()
        writer = csv.writer(csv_template)
        writer.writerow(["player_name", "summoner_name", "riot_tag", "region", 
                        "top_pref", "jungle_pref", "middle_pref", "bottom_pref", "support_pref"])
        writer.writerow(["Player One", "SummonerOne", "NA1", "na1", "5", "3", "2", "1", "4"])
        writer.writerow(["Player Two", "SummonerTwo", "EUW", "euw1", "2", "5", "3", "4", "1"])
        
        # Save to temporary file
        temp_csv = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        temp_csv.write(csv_template.getvalue())
        temp_csv.close()
        templates['csv'] = temp_csv.name
        
        # JSON template
        json_template = [
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
            },
            {
                "player_name": "Player Two",
                "summoner_name": "SummonerTwo",
                "riot_tag": "EUW",
                "region": "euw1",
                "top_pref": 2,
                "jungle_pref": 5,
                "middle_pref": 3,
                "bottom_pref": 4,
                "support_pref": 1
            }
        ]
        
        temp_json = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(json_template, temp_json, indent=2)
        temp_json.close()
        templates['json'] = temp_json.name
        
        return templates
    
    def get_operation_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get statistics for bulk operations over specified period."""
        start_date = datetime.now() - timedelta(days=days)
        
        audit_history = self.audit_logger.get_audit_history(
            start_date=start_date,
            limit=10000
        )
        
        stats = {
            'total_operations': len(audit_history),
            'operations_by_type': {},
            'operations_by_day': {},
            'recent_operations': audit_history[:10]  # Last 10 operations
        }
        
        # Count operations by type
        for entry in audit_history:
            op_type = entry['operation']
            stats['operations_by_type'][op_type] = stats['operations_by_type'].get(op_type, 0) + 1
            
            # Count by day
            op_date = datetime.fromisoformat(entry['timestamp']).date().isoformat()
            stats['operations_by_day'][op_date] = stats['operations_by_day'].get(op_date, 0) + 1
        
        return stats