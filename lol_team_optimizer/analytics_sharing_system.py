"""
Analytics Sharing System for comprehensive export and collaboration features.

This module extends the analytics export manager with advanced sharing capabilities,
including shareable URLs, email delivery, API endpoints, and collaborative features.
"""

import json
import uuid
import hashlib
import smtplib
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import sqlite3
import threading
from urllib.parse import urlencode
import base64

try:
    import qrcode
    from PIL import Image
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False

try:
    from jinja2 import Template, Environment, FileSystemLoader
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False

from .analytics_models import (
    PlayerAnalytics, ChampionPerformanceMetrics, TeamComposition,
    CompositionPerformance, ChampionRecommendation, AnalyticsFilters
)
from .analytics_export_manager import AnalyticsExportManager, ExportFormat, ReportTemplate


class SharePermission(Enum):
    """Permission levels for shared content."""
    PUBLIC = "public"
    PRIVATE = "private"
    TEAM_ONLY = "team_only"
    PASSWORD_PROTECTED = "password_protected"


class ShareType(Enum):
    """Types of shareable content."""
    ANALYTICS_REPORT = "analytics_report"
    PLAYER_PERFORMANCE = "player_performance"
    CHAMPION_ANALYSIS = "champion_analysis"
    TEAM_COMPOSITION = "team_composition"
    COMPARATIVE_ANALYSIS = "comparative_analysis"
    CUSTOM_DASHBOARD = "custom_dashboard"


@dataclass
class ShareConfiguration:
    """Configuration for sharing analytics content."""
    permission: SharePermission = SharePermission.PRIVATE
    expiration_hours: Optional[int] = 24
    password: Optional[str] = None
    allowed_domains: Optional[List[str]] = None
    download_enabled: bool = True
    comments_enabled: bool = False
    analytics_tracking: bool = True
    custom_branding: Optional[Dict[str, str]] = None


@dataclass
class ShareableContent:
    """Represents shareable analytics content."""
    share_id: str
    share_type: ShareType
    title: str
    description: str
    data: Dict[str, Any]
    visualizations: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    configuration: ShareConfiguration
    created_at: datetime
    created_by: str
    access_count: int = 0
    last_accessed: Optional[datetime] = None


@dataclass
class EmailTemplate:
    """Email template for sharing reports."""
    subject: str
    html_body: str
    text_body: str
    attachments: List[str] = None


@dataclass
class APIEndpoint:
    """Configuration for analytics API endpoints."""
    endpoint_id: str
    path: str
    method: str
    data_source: str
    filters: Optional[AnalyticsFilters] = None
    cache_duration: int = 300  # seconds
    rate_limit: int = 100  # requests per hour
    authentication_required: bool = True


class AnalyticsSharingSystem:
    """
    Comprehensive sharing system for analytics content.
    
    Provides functionality for creating shareable URLs, email delivery,
    API endpoints, and collaborative features.
    """
    
    def __init__(self, 
                 export_manager: AnalyticsExportManager,
                 database_path: Path,
                 base_url: str = "http://localhost:7860",
                 email_config: Optional[Dict[str, str]] = None):
        """
        Initialize the sharing system.
        
        Args:
            export_manager: Analytics export manager instance
            database_path: Path to SQLite database for sharing data
            base_url: Base URL for generating shareable links
            email_config: Email server configuration
        """
        self.export_manager = export_manager
        self.database_path = database_path
        self.base_url = base_url.rstrip('/')
        self.email_config = email_config or {}
        
        self.logger = logging.getLogger(__name__)
        self.shared_content: Dict[str, ShareableContent] = {}
        self.api_endpoints: Dict[str, APIEndpoint] = {}
        
        # Initialize database
        self._initialize_database()
        
        # Load existing shared content
        self._load_shared_content()
        
        # Initialize email templates
        self._initialize_email_templates()
        
        # Check for optional dependencies
        if not QRCODE_AVAILABLE:
            self.logger.warning("QRCode not available - QR code generation will be disabled")
        if not JINJA2_AVAILABLE:
            self.logger.warning("Jinja2 not available - advanced templating will be limited")
    
    def _initialize_database(self):
        """Initialize SQLite database for sharing data."""
        conn = sqlite3.connect(self.database_path)
        try:
            cursor = conn.cursor()
            
            # Shared content table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS shared_content (
                    share_id TEXT PRIMARY KEY,
                    share_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    data_json TEXT NOT NULL,
                    visualizations_json TEXT,
                    metadata_json TEXT,
                    configuration_json TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    created_by TEXT NOT NULL,
                    access_count INTEGER DEFAULT 0,
                    last_accessed TIMESTAMP
                )
            ''')
            
            # Access log table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS access_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    share_id TEXT NOT NULL,
                    accessed_at TIMESTAMP NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    referrer TEXT,
                    FOREIGN KEY (share_id) REFERENCES shared_content (share_id)
                )
            ''')
            
            # API endpoints table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS api_endpoints (
                    endpoint_id TEXT PRIMARY KEY,
                    path TEXT NOT NULL,
                    method TEXT NOT NULL,
                    data_source TEXT NOT NULL,
                    filters_json TEXT,
                    cache_duration INTEGER DEFAULT 300,
                    rate_limit INTEGER DEFAULT 100,
                    authentication_required BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP NOT NULL
                )
            ''')
            
            conn.commit()
        finally:
            conn.close()
    
    def _load_shared_content(self):
        """Load existing shared content from database."""
        conn = sqlite3.connect(self.database_path)
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM shared_content')
            
            for row in cursor.fetchall():
                share_id = row[0]
                content = ShareableContent(
                    share_id=share_id,
                    share_type=ShareType(row[1]),
                    title=row[2],
                    description=row[3] or "",
                    data=json.loads(row[4]),
                    visualizations=json.loads(row[5]) if row[5] else [],
                    metadata=json.loads(row[6]) if row[6] else {},
                    configuration=self._deserialize_share_config(json.loads(row[7])),
                    created_at=datetime.fromisoformat(row[8]),
                    created_by=row[9],
                    access_count=row[10],
                    last_accessed=datetime.fromisoformat(row[11]) if row[11] else None
                )
                self.shared_content[share_id] = content
        finally:
            conn.close()
    
    def _deserialize_share_config(self, config_dict: Dict[str, Any]) -> ShareConfiguration:
        """Deserialize share configuration from dictionary."""
        return ShareConfiguration(
            permission=SharePermission(config_dict.get('permission', 'private')),
            expiration_hours=config_dict.get('expiration_hours'),
            password=config_dict.get('password'),
            allowed_domains=config_dict.get('allowed_domains'),
            download_enabled=config_dict.get('download_enabled', True),
            comments_enabled=config_dict.get('comments_enabled', False),
            analytics_tracking=config_dict.get('analytics_tracking', True),
            custom_branding=config_dict.get('custom_branding')
        )
    
    def _initialize_email_templates(self):
        """Initialize default email templates."""
        self.email_templates = {
            'analytics_report': EmailTemplate(
                subject="Analytics Report: {title}",
                html_body="""
                <html>
                <body>
                    <h2>Analytics Report: {title}</h2>
                    <p>{description}</p>
                    <p>You can view the full report at: <a href="{share_url}">{share_url}</a></p>
                    <p>This report was generated on {created_at} and will expire on {expires_at}.</p>
                    <hr>
                    <p><small>Generated by LoL Team Optimizer Analytics System</small></p>
                </body>
                </html>
                """,
                text_body="""
                Analytics Report: {title}
                
                {description}
                
                View the full report at: {share_url}
                
                This report was generated on {created_at} and will expire on {expires_at}.
                
                Generated by LoL Team Optimizer Analytics System
                """
            )
        }
    
    def create_shareable_content(self,
                                title: str,
                                share_type: ShareType,
                                data: Dict[str, Any],
                                visualizations: Optional[List[Dict[str, Any]]] = None,
                                description: str = "",
                                configuration: Optional[ShareConfiguration] = None,
                                created_by: str = "system") -> str:
        """
        Create shareable content and return share ID.
        
        Args:
            title: Title of the shared content
            share_type: Type of content being shared
            data: Analytics data to share
            visualizations: List of visualization configurations
            description: Description of the content
            configuration: Sharing configuration
            created_by: User who created the share
            
        Returns:
            Share ID for accessing the content
        """
        if configuration is None:
            configuration = ShareConfiguration()
        
        # Generate unique share ID
        share_id = self._generate_share_id(title, share_type, created_by)
        
        # Create shareable content
        content = ShareableContent(
            share_id=share_id,
            share_type=share_type,
            title=title,
            description=description,
            data=data,
            visualizations=visualizations or [],
            metadata={
                'data_size': len(json.dumps(data, default=str)),
                'visualization_count': len(visualizations or []),
                'created_timestamp': datetime.now().isoformat()
            },
            configuration=configuration,
            created_at=datetime.now(),
            created_by=created_by
        )
        
        # Store in memory and database
        self.shared_content[share_id] = content
        self._save_shared_content(content)
        
        self.logger.info(f"Created shareable content: {share_id}")
        return share_id
    
    def _generate_share_id(self, title: str, share_type: ShareType, created_by: str) -> str:
        """Generate unique share ID."""
        # Create a hash based on content and timestamp
        content_hash = hashlib.sha256(
            f"{title}{share_type.value}{created_by}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]
        
        return f"{share_type.value}_{content_hash}"
    
    def _save_shared_content(self, content: ShareableContent):
        """Save shared content to database."""
        conn = sqlite3.connect(self.database_path)
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO shared_content 
                (share_id, share_type, title, description, data_json, visualizations_json,
                 metadata_json, configuration_json, created_at, created_by, access_count, last_accessed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                content.share_id,
                content.share_type.value,
                content.title,
                content.description,
                json.dumps(content.data, default=str),
                json.dumps(content.visualizations, default=str),
                json.dumps(content.metadata, default=str),
                json.dumps(self._serialize_share_config(content.configuration)),
                content.created_at.isoformat(),
                content.created_by,
                content.access_count,
                content.last_accessed.isoformat() if content.last_accessed else None
            ))
            conn.commit()
        finally:
            conn.close()
    
    def _serialize_share_config(self, config: ShareConfiguration) -> Dict[str, Any]:
        """Serialize share configuration to dictionary."""
        return {
            'permission': config.permission.value,
            'expiration_hours': config.expiration_hours,
            'password': config.password,
            'allowed_domains': config.allowed_domains,
            'download_enabled': config.download_enabled,
            'comments_enabled': config.comments_enabled,
            'analytics_tracking': config.analytics_tracking,
            'custom_branding': config.custom_branding
        }
    
    def generate_share_url(self, share_id: str, include_qr: bool = False) -> Dict[str, str]:
        """
        Generate shareable URL for content.
        
        Args:
            share_id: ID of the shared content
            include_qr: Whether to generate QR code
            
        Returns:
            Dictionary with URL and optional QR code path
        """
        if share_id not in self.shared_content:
            raise ValueError(f"Share ID not found: {share_id}")
        
        content = self.shared_content[share_id]
        
        # Generate URL
        url = f"{self.base_url}/share/{share_id}"
        
        # Add password parameter if needed
        if content.configuration.password:
            url += f"?auth=required"
        
        result = {"url": url}
        
        # Generate QR code if requested and available
        if include_qr and QRCODE_AVAILABLE:
            qr_path = self._generate_qr_code(url, share_id)
            result["qr_code"] = str(qr_path)
        
        return result
    
    def _generate_qr_code(self, url: str, share_id: str) -> Path:
        """Generate QR code for URL."""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        qr_path = self.export_manager.output_directory / f"qr_{share_id}.png"
        img.save(qr_path)
        
        return qr_path
    
    def access_shared_content(self, 
                            share_id: str, 
                            password: Optional[str] = None,
                            access_info: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Access shared content with permission checking.
        
        Args:
            share_id: ID of the shared content
            password: Password if required
            access_info: Access information (IP, user agent, etc.)
            
        Returns:
            Shared content data
        """
        if share_id not in self.shared_content:
            raise ValueError(f"Share ID not found: {share_id}")
        
        content = self.shared_content[share_id]
        
        # Check expiration
        if content.configuration.expiration_hours:
            expiry_time = content.created_at + timedelta(hours=content.configuration.expiration_hours)
            if datetime.now() > expiry_time:
                raise ValueError("Shared content has expired")
        
        # Check password
        if content.configuration.password and password != content.configuration.password:
            raise ValueError("Invalid password")
        
        # Log access
        self._log_access(share_id, access_info or {})
        
        # Update access count
        content.access_count += 1
        content.last_accessed = datetime.now()
        self._save_shared_content(content)
        
        return {
            'title': content.title,
            'description': content.description,
            'data': content.data,
            'visualizations': content.visualizations,
            'metadata': content.metadata,
            'created_at': content.created_at.isoformat(),
            'created_by': content.created_by,
            'download_enabled': content.configuration.download_enabled
        }
    
    def _log_access(self, share_id: str, access_info: Dict[str, str]):
        """Log access to shared content."""
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO access_log (share_id, accessed_at, ip_address, user_agent, referrer)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                share_id,
                datetime.now().isoformat(),
                access_info.get('ip_address'),
                access_info.get('user_agent'),
                access_info.get('referrer')
            ))
            conn.commit()
    
    def send_email_report(self,
                         share_id: str,
                         recipients: List[str],
                         template_name: str = 'analytics_report',
                         include_attachments: bool = True,
                         custom_message: Optional[str] = None) -> bool:
        """
        Send email report with shareable link.
        
        Args:
            share_id: ID of the shared content
            recipients: List of email addresses
            template_name: Email template to use
            include_attachments: Whether to include file attachments
            custom_message: Custom message to include
            
        Returns:
            True if email sent successfully
        """
        if not self.email_config:
            raise ValueError("Email configuration not provided")
        
        if share_id not in self.shared_content:
            raise ValueError(f"Share ID not found: {share_id}")
        
        content = self.shared_content[share_id]
        template = self.email_templates.get(template_name)
        
        if not template:
            raise ValueError(f"Email template not found: {template_name}")
        
        try:
            # Generate share URL
            share_url_info = self.generate_share_url(share_id)
            share_url = share_url_info['url']
            
            # Calculate expiry time
            expires_at = "Never"
            if content.configuration.expiration_hours:
                expiry_time = content.created_at + timedelta(hours=content.configuration.expiration_hours)
                expires_at = expiry_time.strftime("%Y-%m-%d %H:%M:%S")
            
            # Prepare template variables
            template_vars = {
                'title': content.title,
                'description': content.description,
                'share_url': share_url,
                'created_at': content.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                'expires_at': expires_at,
                'custom_message': custom_message or ""
            }
            
            # Create email message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = template.subject.format(**template_vars)
            msg['From'] = self.email_config['from_address']
            msg['To'] = ', '.join(recipients)
            
            # Add text and HTML parts
            text_part = MIMEText(template.text_body.format(**template_vars), 'plain')
            html_part = MIMEText(template.html_body.format(**template_vars), 'html')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Add attachments if requested
            if include_attachments:
                self._add_email_attachments(msg, content)
            
            # Send email
            with smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port']) as server:
                if self.email_config.get('use_tls'):
                    server.starttls()
                
                if self.email_config.get('username'):
                    server.login(self.email_config['username'], self.email_config['password'])
                
                server.send_message(msg)
            
            self.logger.info(f"Email report sent for share {share_id} to {len(recipients)} recipients")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send email report: {e}")
            return False
    
    def _add_email_attachments(self, msg: MIMEMultipart, content: ShareableContent):
        """Add file attachments to email message."""
        try:
            # Export content in multiple formats
            temp_data = content.data
            formats = [ExportFormat.PDF, ExportFormat.CSV]
            
            for format in formats:
                try:
                    # Determine data type for export
                    if content.share_type == ShareType.PLAYER_PERFORMANCE:
                        filepath = self.export_manager.export_player_analytics(
                            temp_data, format
                        )
                    elif content.share_type == ShareType.CHAMPION_ANALYSIS:
                        filepath = self.export_manager.export_champion_analytics(
                            temp_data, format
                        )
                    else:
                        continue  # Skip unsupported types
                    
                    # Attach file
                    with open(filepath, 'rb') as f:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(f.read())
                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename= {filepath.name}'
                        )
                        msg.attach(part)
                
                except Exception as e:
                    self.logger.warning(f"Failed to attach {format.value} file: {e}")
                    continue
        
        except Exception as e:
            self.logger.warning(f"Failed to add email attachments: {e}")
    
    def create_api_endpoint(self,
                          path: str,
                          method: str,
                          data_source: str,
                          filters: Optional[AnalyticsFilters] = None,
                          cache_duration: int = 300,
                          rate_limit: int = 100,
                          authentication_required: bool = True) -> str:
        """
        Create API endpoint for external integrations.
        
        Args:
            path: API endpoint path
            method: HTTP method (GET, POST, etc.)
            data_source: Source of data for the endpoint
            filters: Default filters to apply
            cache_duration: Cache duration in seconds
            rate_limit: Rate limit per hour
            authentication_required: Whether authentication is required
            
        Returns:
            Endpoint ID
        """
        endpoint_id = f"api_{hashlib.sha256(f'{path}{method}{data_source}'.encode()).hexdigest()[:8]}"
        
        endpoint = APIEndpoint(
            endpoint_id=endpoint_id,
            path=path,
            method=method,
            data_source=data_source,
            filters=filters,
            cache_duration=cache_duration,
            rate_limit=rate_limit,
            authentication_required=authentication_required
        )
        
        self.api_endpoints[endpoint_id] = endpoint
        self._save_api_endpoint(endpoint)
        
        self.logger.info(f"Created API endpoint: {endpoint_id} at {path}")
        return endpoint_id
    
    def _save_api_endpoint(self, endpoint: APIEndpoint):
        """Save API endpoint to database."""
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO api_endpoints 
                (endpoint_id, path, method, data_source, filters_json, cache_duration,
                 rate_limit, authentication_required, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                endpoint.endpoint_id,
                endpoint.path,
                endpoint.method,
                endpoint.data_source,
                json.dumps(asdict(endpoint.filters)) if endpoint.filters else None,
                endpoint.cache_duration,
                endpoint.rate_limit,
                endpoint.authentication_required,
                datetime.now().isoformat()
            ))
            conn.commit()
    
    def get_sharing_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive sharing statistics.
        
        Returns:
            Dictionary containing sharing statistics
        """
        stats = {
            'total_shares': len(self.shared_content),
            'shares_by_type': {},
            'shares_by_permission': {},
            'total_accesses': 0,
            'most_accessed': None,
            'recent_shares': [],
            'api_endpoints': len(self.api_endpoints),
            'expired_shares': 0
        }
        
        now = datetime.now()
        
        for content in self.shared_content.values():
            # Count by type
            type_key = content.share_type.value
            stats['shares_by_type'][type_key] = stats['shares_by_type'].get(type_key, 0) + 1
            
            # Count by permission
            perm_key = content.configuration.permission.value
            stats['shares_by_permission'][perm_key] = stats['shares_by_permission'].get(perm_key, 0) + 1
            
            # Total accesses
            stats['total_accesses'] += content.access_count
            
            # Most accessed
            if stats['most_accessed'] is None or content.access_count > stats['most_accessed']['access_count']:
                stats['most_accessed'] = {
                    'share_id': content.share_id,
                    'title': content.title,
                    'access_count': content.access_count
                }
            
            # Check if expired
            if content.configuration.expiration_hours:
                expiry_time = content.created_at + timedelta(hours=content.configuration.expiration_hours)
                if now > expiry_time:
                    stats['expired_shares'] += 1
            
            # Recent shares (last 7 days)
            if (now - content.created_at).days <= 7:
                stats['recent_shares'].append({
                    'share_id': content.share_id,
                    'title': content.title,
                    'created_at': content.created_at.isoformat(),
                    'access_count': content.access_count
                })
        
        # Sort recent shares by creation date
        stats['recent_shares'].sort(key=lambda x: x['created_at'], reverse=True)
        
        return stats
    
    def cleanup_expired_shares(self) -> int:
        """
        Clean up expired shared content.
        
        Returns:
            Number of shares cleaned up
        """
        now = datetime.now()
        expired_shares = []
        
        for share_id, content in self.shared_content.items():
            if content.configuration.expiration_hours:
                expiry_time = content.created_at + timedelta(hours=content.configuration.expiration_hours)
                if now > expiry_time:
                    expired_shares.append(share_id)
        
        # Remove expired shares
        for share_id in expired_shares:
            del self.shared_content[share_id]
            
            # Remove from database
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM shared_content WHERE share_id = ?', (share_id,))
                cursor.execute('DELETE FROM access_log WHERE share_id = ?', (share_id,))
                conn.commit()
        
        if expired_shares:
            self.logger.info(f"Cleaned up {len(expired_shares)} expired shares")
        
        return len(expired_shares)
    
    def generate_comprehensive_report(self,
                                    title: str,
                                    data_sources: List[Dict[str, Any]],
                                    template_config: Optional[Dict[str, Any]] = None,
                                    include_visualizations: bool = True) -> str:
        """
        Generate comprehensive report with multiple data sources.
        
        Args:
            title: Report title
            data_sources: List of data sources with their configurations
            template_config: Custom template configuration
            include_visualizations: Whether to include visualizations
            
        Returns:
            Share ID for the generated report
        """
        # Combine all data sources
        combined_data = {
            'title': title,
            'generated_at': datetime.now().isoformat(),
            'data_sources': data_sources,
            'summary': self._generate_report_summary(data_sources)
        }
        
        # Generate visualizations if requested
        visualizations = []
        if include_visualizations:
            visualizations = self._generate_report_visualizations(data_sources)
        
        # Create shareable content
        share_id = self.create_shareable_content(
            title=title,
            share_type=ShareType.ANALYTICS_REPORT,
            data=combined_data,
            visualizations=visualizations,
            description=f"Comprehensive analytics report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            configuration=ShareConfiguration(
                permission=SharePermission.PRIVATE,
                expiration_hours=168,  # 1 week
                download_enabled=True,
                analytics_tracking=True
            )
        )
        
        return share_id
    
    def _generate_report_summary(self, data_sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary statistics for report."""
        summary = {
            'total_data_sources': len(data_sources),
            'data_types': [],
            'key_metrics': {},
            'insights': []
        }
        
        for source in data_sources:
            data_type = source.get('type', 'unknown')
            if data_type not in summary['data_types']:
                summary['data_types'].append(data_type)
        
        return summary
    
    def _generate_report_visualizations(self, data_sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate visualizations for report."""
        visualizations = []
        
        for i, source in enumerate(data_sources):
            viz_config = {
                'id': f'viz_{i}',
                'type': 'chart',
                'title': source.get('title', f'Data Source {i+1}'),
                'data_source': source.get('type', 'unknown'),
                'config': {
                    'chart_type': 'auto',
                    'interactive': True,
                    'export_enabled': True
                }
            }
            visualizations.append(viz_config)
        
        return visualizations