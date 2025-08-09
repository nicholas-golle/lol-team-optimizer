"""
Tests for the Analytics Sharing System.

This module contains comprehensive tests for the analytics sharing functionality,
including shareable URLs, email delivery, API endpoints, and collaborative features.
"""

import pytest
import json
import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from dataclasses import asdict

from lol_team_optimizer.analytics_sharing_system import (
    AnalyticsSharingSystem, ShareConfiguration, SharePermission, ShareType,
    ShareableContent, EmailTemplate, APIEndpoint
)
from lol_team_optimizer.analytics_export_manager import AnalyticsExportManager, ExportFormat
from lol_team_optimizer.analytics_models import (
    PlayerAnalytics, ChampionPerformanceMetrics, PerformanceMetrics, AnalyticsFilters
)


class TestAnalyticsSharingSystem:
    """Test suite for AnalyticsSharingSystem."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def mock_export_manager(self, temp_dir):
        """Create mock export manager."""
        return Mock(spec=AnalyticsExportManager, output_directory=temp_dir)
    
    @pytest.fixture
    def sample_player_analytics(self):
        """Create sample player analytics data."""
        from lol_team_optimizer.analytics_models import DateRange
        from datetime import datetime, timedelta
        
        performance = PerformanceMetrics(
            games_played=50,
            wins=32,
            losses=18,
            win_rate=0.64,
            total_kills=150,
            total_deaths=75,
            total_assists=200,
            avg_kda=4.67,
            total_cs=12500,
            avg_cs_per_min=6.8,
            total_vision_score=1250,
            avg_vision_score=25.0,
            total_damage_to_champions=850000,
            avg_damage_per_min=1200,
            total_gold_earned=625000,
            avg_gold_per_min=850,
            total_game_duration=108000,
            avg_game_duration=36.0
        )
        
        analysis_period = DateRange(
            start_date=datetime.now() - timedelta(days=30),
            end_date=datetime.now()
        )
        
        return PlayerAnalytics(
            puuid="test_player_123",
            player_name="TestPlayer",
            analysis_period=analysis_period,
            overall_performance=performance,
            role_performance={},
            champion_performance={},
            trend_analysis=None,
            comparative_rankings=None,
            confidence_scores={}
        )
    
    @pytest.fixture
    def sample_champion_metrics(self):
        """Create sample champion performance metrics."""
        performance = PerformanceMetrics(
            games_played=25,
            wins=18,
            losses=7,
            win_rate=0.72,
            avg_kda=3.2,
            avg_cs_per_min=7.1,
            avg_vision_score=22.5,
            avg_damage_per_min=1150
        )
        
        return ChampionPerformanceMetrics(
            champion_id=1,
            champion_name="Annie",
            role="middle",
            performance=performance
        )
    
    @pytest.fixture
    def sharing_system(self, temp_dir, mock_export_manager):
        """Create sharing system instance."""
        database_path = temp_dir / "test_sharing.db"
        email_config = {
            'smtp_server': 'smtp.test.com',
            'smtp_port': 587,
            'from_address': 'test@example.com',
            'username': 'test_user',
            'password': 'test_pass',
            'use_tls': True
        }
        
        return AnalyticsSharingSystem(
            export_manager=mock_export_manager,
            database_path=database_path,
            base_url="http://localhost:7860",
            email_config=email_config
        )
    
    def test_initialization(self, sharing_system, temp_dir):
        """Test sharing system initialization."""
        assert sharing_system.base_url == "http://localhost:7860"
        assert sharing_system.database_path.exists()
        assert len(sharing_system.email_templates) > 0
        assert 'analytics_report' in sharing_system.email_templates
    
    def test_database_initialization(self, sharing_system):
        """Test database table creation."""
        with sqlite3.connect(sharing_system.database_path) as conn:
            cursor = conn.cursor()
            
            # Check if tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            assert 'shared_content' in tables
            assert 'access_log' in tables
            assert 'api_endpoints' in tables
    
    def test_create_shareable_content(self, sharing_system, sample_player_analytics):
        """Test creating shareable content."""
        data = asdict(sample_player_analytics)
        
        share_id = sharing_system.create_shareable_content(
            title="Test Player Report",
            share_type=ShareType.PLAYER_PERFORMANCE,
            data=data,
            description="Test player performance report",
            created_by="test_user"
        )
        
        assert share_id is not None
        assert share_id.startswith("player_performance_")
        assert share_id in sharing_system.shared_content
        
        content = sharing_system.shared_content[share_id]
        assert content.title == "Test Player Report"
        assert content.share_type == ShareType.PLAYER_PERFORMANCE
        assert content.created_by == "test_user"
        assert content.access_count == 0
    
    def test_create_shareable_content_with_custom_config(self, sharing_system, sample_player_analytics):
        """Test creating shareable content with custom configuration."""
        data = asdict(sample_player_analytics)
        config = ShareConfiguration(
            permission=SharePermission.PUBLIC,
            expiration_hours=48,
            password="test123",
            download_enabled=False
        )
        
        share_id = sharing_system.create_shareable_content(
            title="Public Player Report",
            share_type=ShareType.PLAYER_PERFORMANCE,
            data=data,
            configuration=config
        )
        
        content = sharing_system.shared_content[share_id]
        assert content.configuration.permission == SharePermission.PUBLIC
        assert content.configuration.expiration_hours == 48
        assert content.configuration.password == "test123"
        assert content.configuration.download_enabled is False
    
    def test_generate_share_url(self, sharing_system, sample_player_analytics):
        """Test generating shareable URLs."""
        data = asdict(sample_player_analytics)
        share_id = sharing_system.create_shareable_content(
            title="Test Report",
            share_type=ShareType.PLAYER_PERFORMANCE,
            data=data
        )
        
        url_info = sharing_system.generate_share_url(share_id)
        
        assert 'url' in url_info
        assert url_info['url'] == f"http://localhost:7860/share/{share_id}"
    
    def test_generate_share_url_with_password(self, sharing_system, sample_player_analytics):
        """Test generating shareable URLs with password protection."""
        data = asdict(sample_player_analytics)
        config = ShareConfiguration(password="secret123")
        
        share_id = sharing_system.create_shareable_content(
            title="Protected Report",
            share_type=ShareType.PLAYER_PERFORMANCE,
            data=data,
            configuration=config
        )
        
        url_info = sharing_system.generate_share_url(share_id)
        
        assert 'url' in url_info
        assert "auth=required" in url_info['url']
    
    @patch('lol_team_optimizer.analytics_sharing_system.QRCODE_AVAILABLE', True)
    @patch('qrcode.QRCode')
    def test_generate_share_url_with_qr_code(self, mock_qr_class, sharing_system, sample_player_analytics):
        """Test generating shareable URLs with QR codes."""
        # Mock QR code generation
        mock_qr = Mock()
        mock_img = Mock()
        mock_qr.make_image.return_value = mock_img
        mock_qr_class.return_value = mock_qr
        
        data = asdict(sample_player_analytics)
        share_id = sharing_system.create_shareable_content(
            title="Test Report",
            share_type=ShareType.PLAYER_PERFORMANCE,
            data=data
        )
        
        url_info = sharing_system.generate_share_url(share_id, include_qr=True)
        
        assert 'url' in url_info
        assert 'qr_code' in url_info
        mock_qr.add_data.assert_called_once()
        mock_img.save.assert_called_once()
    
    def test_access_shared_content(self, sharing_system, sample_player_analytics):
        """Test accessing shared content."""
        data = asdict(sample_player_analytics)
        share_id = sharing_system.create_shareable_content(
            title="Test Report",
            share_type=ShareType.PLAYER_PERFORMANCE,
            data=data
        )
        
        accessed_content = sharing_system.access_shared_content(share_id)
        
        assert accessed_content['title'] == "Test Report"
        assert 'data' in accessed_content
        assert 'created_at' in accessed_content
        assert accessed_content['download_enabled'] is True
        
        # Check access count updated
        content = sharing_system.shared_content[share_id]
        assert content.access_count == 1
        assert content.last_accessed is not None
    
    def test_access_shared_content_with_password(self, sharing_system, sample_player_analytics):
        """Test accessing password-protected shared content."""
        data = asdict(sample_player_analytics)
        config = ShareConfiguration(password="secret123")
        
        share_id = sharing_system.create_shareable_content(
            title="Protected Report",
            share_type=ShareType.PLAYER_PERFORMANCE,
            data=data,
            configuration=config
        )
        
        # Test access without password (should fail)
        with pytest.raises(ValueError, match="Invalid password"):
            sharing_system.access_shared_content(share_id)
        
        # Test access with wrong password (should fail)
        with pytest.raises(ValueError, match="Invalid password"):
            sharing_system.access_shared_content(share_id, password="wrong")
        
        # Test access with correct password (should succeed)
        accessed_content = sharing_system.access_shared_content(share_id, password="secret123")
        assert accessed_content['title'] == "Protected Report"
    
    def test_access_expired_content(self, sharing_system, sample_player_analytics):
        """Test accessing expired shared content."""
        data = asdict(sample_player_analytics)
        config = ShareConfiguration(expiration_hours=1)
        
        share_id = sharing_system.create_shareable_content(
            title="Expiring Report",
            share_type=ShareType.PLAYER_PERFORMANCE,
            data=data,
            configuration=config
        )
        
        # Manually set creation time to past
        content = sharing_system.shared_content[share_id]
        content.created_at = datetime.now() - timedelta(hours=2)
        
        with pytest.raises(ValueError, match="Shared content has expired"):
            sharing_system.access_shared_content(share_id)
    
    def test_access_nonexistent_content(self, sharing_system):
        """Test accessing non-existent shared content."""
        with pytest.raises(ValueError, match="Share ID not found"):
            sharing_system.access_shared_content("nonexistent_id")
    
    @patch('smtplib.SMTP')
    def test_send_email_report(self, mock_smtp_class, sharing_system, sample_player_analytics):
        """Test sending email reports."""
        # Mock SMTP server
        mock_server = Mock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server
        
        # Mock export manager
        sharing_system.export_manager.export_player_analytics.return_value = Path("test_report.pdf")
        
        data = asdict(sample_player_analytics)
        share_id = sharing_system.create_shareable_content(
            title="Email Test Report",
            share_type=ShareType.PLAYER_PERFORMANCE,
            data=data
        )
        
        recipients = ["test1@example.com", "test2@example.com"]
        result = sharing_system.send_email_report(
            share_id=share_id,
            recipients=recipients,
            custom_message="This is a test report"
        )
        
        assert result is True
        mock_server.send_message.assert_called_once()
    
    def test_send_email_report_no_config(self, temp_dir, mock_export_manager):
        """Test sending email report without email configuration."""
        sharing_system = AnalyticsSharingSystem(
            export_manager=mock_export_manager,
            database_path=temp_dir / "test.db",
            email_config=None
        )
        
        with pytest.raises(ValueError, match="Email configuration not provided"):
            sharing_system.send_email_report("test_id", ["test@example.com"])
    
    def test_create_api_endpoint(self, sharing_system):
        """Test creating API endpoints."""
        filters = AnalyticsFilters(min_games=10)
        
        endpoint_id = sharing_system.create_api_endpoint(
            path="/api/player-stats",
            method="GET",
            data_source="player_analytics",
            filters=filters,
            cache_duration=600,
            rate_limit=50
        )
        
        assert endpoint_id is not None
        assert endpoint_id.startswith("api_")
        assert endpoint_id in sharing_system.api_endpoints
        
        endpoint = sharing_system.api_endpoints[endpoint_id]
        assert endpoint.path == "/api/player-stats"
        assert endpoint.method == "GET"
        assert endpoint.data_source == "player_analytics"
        assert endpoint.cache_duration == 600
        assert endpoint.rate_limit == 50
    
    def test_get_sharing_statistics(self, sharing_system, sample_player_analytics, sample_champion_metrics):
        """Test getting sharing statistics."""
        # Create multiple shares
        player_data = asdict(sample_player_analytics)
        champion_data = [asdict(sample_champion_metrics)]
        
        share1 = sharing_system.create_shareable_content(
            title="Player Report 1",
            share_type=ShareType.PLAYER_PERFORMANCE,
            data=player_data
        )
        
        share2 = sharing_system.create_shareable_content(
            title="Champion Report 1",
            share_type=ShareType.CHAMPION_ANALYSIS,
            data=champion_data,
            configuration=ShareConfiguration(permission=SharePermission.PUBLIC)
        )
        
        # Access one share multiple times
        sharing_system.access_shared_content(share1)
        sharing_system.access_shared_content(share1)
        sharing_system.access_shared_content(share2)
        
        stats = sharing_system.get_sharing_statistics()
        
        assert stats['total_shares'] == 2
        assert stats['shares_by_type']['player_performance'] == 1
        assert stats['shares_by_type']['champion_analysis'] == 1
        assert stats['shares_by_permission']['private'] == 1
        assert stats['shares_by_permission']['public'] == 1
        assert stats['total_accesses'] == 3
        assert stats['most_accessed']['share_id'] == share1
        assert stats['most_accessed']['access_count'] == 2
        assert len(stats['recent_shares']) == 2
    
    def test_cleanup_expired_shares(self, sharing_system, sample_player_analytics):
        """Test cleaning up expired shares."""
        data = asdict(sample_player_analytics)
        
        # Create expired share
        config_expired = ShareConfiguration(expiration_hours=1)
        share1 = sharing_system.create_shareable_content(
            title="Expired Report",
            share_type=ShareType.PLAYER_PERFORMANCE,
            data=data,
            configuration=config_expired
        )
        
        # Create non-expired share
        config_valid = ShareConfiguration(expiration_hours=24)
        share2 = sharing_system.create_shareable_content(
            title="Valid Report",
            share_type=ShareType.PLAYER_PERFORMANCE,
            data=data,
            configuration=config_valid
        )
        
        # Manually set creation time for expired share
        sharing_system.shared_content[share1].created_at = datetime.now() - timedelta(hours=2)
        
        cleaned_count = sharing_system.cleanup_expired_shares()
        
        assert cleaned_count == 1
        assert share1 not in sharing_system.shared_content
        assert share2 in sharing_system.shared_content
    
    def test_generate_comprehensive_report(self, sharing_system):
        """Test generating comprehensive reports."""
        data_sources = [
            {
                'type': 'player_performance',
                'title': 'Player Analysis',
                'data': {'player_id': 'test123', 'win_rate': 0.65}
            },
            {
                'type': 'champion_analysis',
                'title': 'Champion Performance',
                'data': {'champion': 'Annie', 'win_rate': 0.72}
            }
        ]
        
        share_id = sharing_system.generate_comprehensive_report(
            title="Comprehensive Team Report",
            data_sources=data_sources,
            include_visualizations=True
        )
        
        assert share_id is not None
        assert share_id in sharing_system.shared_content
        
        content = sharing_system.shared_content[share_id]
        assert content.title == "Comprehensive Team Report"
        assert content.share_type == ShareType.ANALYTICS_REPORT
        assert len(content.visualizations) == len(data_sources)
        assert content.data['summary']['total_data_sources'] == 2
    
    def test_persistence_across_instances(self, temp_dir, mock_export_manager, sample_player_analytics):
        """Test that shared content persists across system instances."""
        database_path = temp_dir / "persistent_test.db"
        
        # Create first instance and add content
        system1 = AnalyticsSharingSystem(
            export_manager=mock_export_manager,
            database_path=database_path
        )
        
        data = asdict(sample_player_analytics)
        share_id = system1.create_shareable_content(
            title="Persistent Report",
            share_type=ShareType.PLAYER_PERFORMANCE,
            data=data
        )
        
        # Create second instance and check content exists
        system2 = AnalyticsSharingSystem(
            export_manager=mock_export_manager,
            database_path=database_path
        )
        
        assert share_id in system2.shared_content
        assert system2.shared_content[share_id].title == "Persistent Report"
    
    def test_access_logging(self, sharing_system, sample_player_analytics):
        """Test access logging functionality."""
        data = asdict(sample_player_analytics)
        share_id = sharing_system.create_shareable_content(
            title="Logged Report",
            share_type=ShareType.PLAYER_PERFORMANCE,
            data=data
        )
        
        access_info = {
            'ip_address': '192.168.1.1',
            'user_agent': 'Mozilla/5.0 Test Browser',
            'referrer': 'https://example.com'
        }
        
        sharing_system.access_shared_content(share_id, access_info=access_info)
        
        # Check access log in database
        with sqlite3.connect(sharing_system.database_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM access_log WHERE share_id = ?', (share_id,))
            log_entries = cursor.fetchall()
        
        assert len(log_entries) == 1
        log_entry = log_entries[0]
        assert log_entry[1] == share_id  # share_id
        assert log_entry[3] == '192.168.1.1'  # ip_address
        assert log_entry[4] == 'Mozilla/5.0 Test Browser'  # user_agent
        assert log_entry[5] == 'https://example.com'  # referrer


class TestShareConfiguration:
    """Test suite for ShareConfiguration."""
    
    def test_default_configuration(self):
        """Test default share configuration."""
        config = ShareConfiguration()
        
        assert config.permission == SharePermission.PRIVATE
        assert config.expiration_hours == 24
        assert config.password is None
        assert config.allowed_domains is None
        assert config.download_enabled is True
        assert config.comments_enabled is False
        assert config.analytics_tracking is True
        assert config.custom_branding is None
    
    def test_custom_configuration(self):
        """Test custom share configuration."""
        config = ShareConfiguration(
            permission=SharePermission.PUBLIC,
            expiration_hours=48,
            password="secret123",
            allowed_domains=["example.com", "test.org"],
            download_enabled=False,
            comments_enabled=True,
            analytics_tracking=False,
            custom_branding={"logo": "custom_logo.png", "color": "#FF0000"}
        )
        
        assert config.permission == SharePermission.PUBLIC
        assert config.expiration_hours == 48
        assert config.password == "secret123"
        assert config.allowed_domains == ["example.com", "test.org"]
        assert config.download_enabled is False
        assert config.comments_enabled is True
        assert config.analytics_tracking is False
        assert config.custom_branding["logo"] == "custom_logo.png"


class TestEmailTemplate:
    """Test suite for EmailTemplate."""
    
    def test_email_template_creation(self):
        """Test email template creation."""
        template = EmailTemplate(
            subject="Test Report: {title}",
            html_body="<h1>{title}</h1><p>{description}</p>",
            text_body="{title}\n{description}",
            attachments=["report.pdf", "data.csv"]
        )
        
        assert template.subject == "Test Report: {title}"
        assert "<h1>{title}</h1>" in template.html_body
        assert template.text_body == "{title}\n{description}"
        assert len(template.attachments) == 2


class TestAPIEndpoint:
    """Test suite for APIEndpoint."""
    
    def test_api_endpoint_creation(self):
        """Test API endpoint creation."""
        filters = AnalyticsFilters(min_games=5)
        
        endpoint = APIEndpoint(
            endpoint_id="test_endpoint_123",
            path="/api/test",
            method="GET",
            data_source="player_data",
            filters=filters,
            cache_duration=600,
            rate_limit=50,
            authentication_required=True
        )
        
        assert endpoint.endpoint_id == "test_endpoint_123"
        assert endpoint.path == "/api/test"
        assert endpoint.method == "GET"
        assert endpoint.data_source == "player_data"
        assert endpoint.filters.min_games == 5
        assert endpoint.cache_duration == 600
        assert endpoint.rate_limit == 50
        assert endpoint.authentication_required is True


if __name__ == "__main__":
    pytest.main([__file__])