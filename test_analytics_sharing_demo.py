#!/usr/bin/env python3
"""
Analytics Sharing System Demo

This script demonstrates the comprehensive analytics sharing system functionality,
including shareable URLs, email delivery, API endpoints, and collaborative features.
"""

import sys
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import asdict

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from lol_team_optimizer.analytics_sharing_system import (
    AnalyticsSharingSystem, ShareConfiguration, SharePermission, ShareType
)
from lol_team_optimizer.analytics_export_manager import AnalyticsExportManager, ExportFormat
from lol_team_optimizer.analytics_models import (
    PlayerAnalytics, ChampionPerformanceMetrics, PerformanceMetrics, AnalyticsFilters
)


def create_sample_data():
    """Create sample analytics data for demonstration."""
    print("📊 Creating sample analytics data...")
    
    # Sample player performance
    player_performance = PerformanceMetrics(
        games_played=75,
        wins=48,
        losses=27,
        win_rate=0.64,
        total_kills=225,
        total_deaths=112,
        total_assists=300,
        avg_kda=4.69,
        total_cs=18750,
        avg_cs_per_min=7.2,
        total_vision_score=1875,
        avg_vision_score=25.0,
        total_damage_to_champions=1275000,
        avg_damage_per_min=1350,
        total_gold_earned=937500,
        avg_gold_per_min=875,
        total_game_duration=162000,
        avg_game_duration=36.0
    )
    
    from lol_team_optimizer.analytics_models import DateRange
    from datetime import datetime, timedelta
    
    analysis_period = DateRange(
        start_date=datetime.now() - timedelta(days=30),
        end_date=datetime.now()
    )
    
    player_analytics = PlayerAnalytics(
        puuid="demo_player_12345",
        player_name="DemoPlayer",
        analysis_period=analysis_period,
        overall_performance=player_performance,
        role_performance={},
        champion_performance={},
        trend_analysis=None,
        comparative_rankings=None,
        confidence_scores={}
    )
    
    # Sample champion performance
    champion_performance = PerformanceMetrics(
        games_played=30,
        wins=22,
        losses=8,
        win_rate=0.73,
        avg_kda=3.8,
        avg_cs_per_min=7.5,
        avg_vision_score=28.0,
        avg_damage_per_min=1420
    )
    
    champion_metrics = ChampionPerformanceMetrics(
        champion_id=1,
        champion_name="Annie",
        role="middle",
        performance=champion_performance
    )
    
    return player_analytics, [champion_metrics]


def demonstrate_basic_sharing(sharing_system, player_analytics, champion_metrics):
    """Demonstrate basic sharing functionality."""
    print("\n🔗 Demonstrating basic sharing functionality...")
    
    # Create shareable player report
    player_data = asdict(player_analytics)
    player_share_id = sharing_system.create_shareable_content(
        title="DemoPlayer Performance Analysis",
        share_type=ShareType.PLAYER_PERFORMANCE,
        data=player_data,
        description="Comprehensive performance analysis for DemoPlayer over the last 75 games",
        created_by="demo_user"
    )
    
    print(f"✅ Created player performance share: {player_share_id}")
    
    # Create shareable champion report
    champion_data = [asdict(metric) for metric in champion_metrics]
    champion_share_id = sharing_system.create_shareable_content(
        title="Annie Champion Analysis",
        share_type=ShareType.CHAMPION_ANALYSIS,
        data=champion_data,
        description="Detailed analysis of Annie performance in middle lane",
        created_by="demo_user"
    )
    
    print(f"✅ Created champion analysis share: {champion_share_id}")
    
    # Generate shareable URLs
    player_url = sharing_system.generate_share_url(player_share_id)
    champion_url = sharing_system.generate_share_url(champion_share_id, include_qr=True)
    
    print(f"🌐 Player report URL: {player_url['url']}")
    print(f"🌐 Champion report URL: {champion_url['url']}")
    if 'qr_code' in champion_url:
        print(f"📱 QR code generated: {champion_url['qr_code']}")
    
    return player_share_id, champion_share_id


def demonstrate_advanced_sharing(sharing_system, player_analytics):
    """Demonstrate advanced sharing features."""
    print("\n🔒 Demonstrating advanced sharing features...")
    
    # Create password-protected share
    protected_config = ShareConfiguration(
        permission=SharePermission.PASSWORD_PROTECTED,
        password="demo123",
        expiration_hours=48,
        download_enabled=True,
        analytics_tracking=True
    )
    
    player_data = asdict(player_analytics)
    protected_share_id = sharing_system.create_shareable_content(
        title="Protected Player Analysis",
        share_type=ShareType.PLAYER_PERFORMANCE,
        data=player_data,
        description="Password-protected player analysis report",
        configuration=protected_config,
        created_by="demo_user"
    )
    
    print(f"🔐 Created password-protected share: {protected_share_id}")
    
    # Create public share with custom expiration
    public_config = ShareConfiguration(
        permission=SharePermission.PUBLIC,
        expiration_hours=168,  # 1 week
        download_enabled=True,
        comments_enabled=True,
        custom_branding={
            "logo": "team_logo.png",
            "primary_color": "#1E88E5",
            "secondary_color": "#FFC107"
        }
    )
    
    public_share_id = sharing_system.create_shareable_content(
        title="Public Team Performance Dashboard",
        share_type=ShareType.PLAYER_PERFORMANCE,
        data=player_data,
        description="Public dashboard showing team performance metrics",
        configuration=public_config,
        created_by="demo_user"
    )
    
    print(f"🌍 Created public share: {public_share_id}")
    
    # Generate URLs
    protected_url = sharing_system.generate_share_url(protected_share_id)
    public_url = sharing_system.generate_share_url(public_share_id)
    
    print(f"🔐 Protected URL: {protected_url['url']}")
    print(f"🌍 Public URL: {public_url['url']}")
    
    return protected_share_id, public_share_id


def demonstrate_content_access(sharing_system, share_ids):
    """Demonstrate content access and logging."""
    print("\n👀 Demonstrating content access...")
    
    player_share_id, champion_share_id, protected_share_id, public_share_id = share_ids
    
    # Access public content
    try:
        public_content = sharing_system.access_shared_content(
            public_share_id,
            access_info={
                'ip_address': '192.168.1.100',
                'user_agent': 'Mozilla/5.0 (Demo Browser)',
                'referrer': 'https://demo.example.com'
            }
        )
        print(f"✅ Accessed public content: {public_content['title']}")
    except Exception as e:
        print(f"❌ Failed to access public content: {e}")
    
    # Try to access protected content without password
    try:
        sharing_system.access_shared_content(protected_share_id)
        print("❌ Should not have accessed protected content without password")
    except ValueError as e:
        print(f"✅ Correctly blocked access without password: {e}")
    
    # Access protected content with correct password
    try:
        protected_content = sharing_system.access_shared_content(
            protected_share_id,
            password="demo123",
            access_info={'ip_address': '192.168.1.101'}
        )
        print(f"✅ Accessed protected content: {protected_content['title']}")
    except Exception as e:
        print(f"❌ Failed to access protected content: {e}")
    
    # Access content multiple times to test counting
    for i in range(3):
        try:
            sharing_system.access_shared_content(player_share_id)
        except Exception as e:
            print(f"❌ Failed to access player content (attempt {i+1}): {e}")
    
    print("✅ Completed access demonstrations")


def demonstrate_email_sharing(sharing_system, share_id):
    """Demonstrate email sharing functionality."""
    print("\n📧 Demonstrating email sharing...")
    
    # Note: This is a demonstration - actual email sending would require real SMTP config
    try:
        # This would normally send an email, but we'll catch the exception
        # since we're using mock email configuration
        result = sharing_system.send_email_report(
            share_id=share_id,
            recipients=["demo1@example.com", "demo2@example.com"],
            template_name='analytics_report',
            include_attachments=True,
            custom_message="This is a demonstration of the email sharing feature."
        )
        
        if result:
            print("✅ Email report sent successfully")
        else:
            print("⚠️ Email sending failed (expected with demo configuration)")
    
    except Exception as e:
        print(f"⚠️ Email demonstration completed (expected error with demo config): {e}")


def demonstrate_api_endpoints(sharing_system):
    """Demonstrate API endpoint creation."""
    print("\n🔌 Demonstrating API endpoint creation...")
    
    # Create API endpoints for different data types
    filters = AnalyticsFilters(min_games=10, win_only=False)
    
    player_endpoint = sharing_system.create_api_endpoint(
        path="/api/v1/player-analytics",
        method="GET",
        data_source="player_performance",
        filters=filters,
        cache_duration=600,
        rate_limit=100,
        authentication_required=True
    )
    
    print(f"✅ Created player analytics endpoint: {player_endpoint}")
    
    champion_endpoint = sharing_system.create_api_endpoint(
        path="/api/v1/champion-stats",
        method="GET",
        data_source="champion_performance",
        cache_duration=300,
        rate_limit=200,
        authentication_required=False
    )
    
    print(f"✅ Created champion stats endpoint: {champion_endpoint}")
    
    team_endpoint = sharing_system.create_api_endpoint(
        path="/api/v1/team-composition",
        method="POST",
        data_source="team_analysis",
        cache_duration=900,
        rate_limit=50,
        authentication_required=True
    )
    
    print(f"✅ Created team composition endpoint: {team_endpoint}")
    
    return [player_endpoint, champion_endpoint, team_endpoint]


def demonstrate_comprehensive_reports(sharing_system, player_analytics, champion_metrics):
    """Demonstrate comprehensive report generation."""
    print("\n📋 Demonstrating comprehensive report generation...")
    
    # Prepare multiple data sources
    data_sources = [
        {
            'type': 'player_performance',
            'title': 'Player Performance Analysis',
            'data': asdict(player_analytics),
            'description': 'Individual player performance metrics and trends'
        },
        {
            'type': 'champion_analysis',
            'title': 'Champion Performance Breakdown',
            'data': [asdict(metric) for metric in champion_metrics],
            'description': 'Champion-specific performance analysis'
        },
        {
            'type': 'team_synergy',
            'title': 'Team Synergy Analysis',
            'data': {
                'synergy_matrix': [[0.8, 0.6], [0.7, 0.9]],
                'optimal_compositions': ['Comp A', 'Comp B'],
                'performance_predictions': [0.72, 0.68]
            },
            'description': 'Team composition and synergy analysis'
        }
    ]
    
    # Generate comprehensive report
    comprehensive_share_id = sharing_system.generate_comprehensive_report(
        title="Complete Team Performance Analysis",
        data_sources=data_sources,
        include_visualizations=True
    )
    
    print(f"✅ Generated comprehensive report: {comprehensive_share_id}")
    
    # Generate URL for the comprehensive report
    comprehensive_url = sharing_system.generate_share_url(comprehensive_share_id)
    print(f"🌐 Comprehensive report URL: {comprehensive_url['url']}")
    
    return comprehensive_share_id


def demonstrate_statistics_and_cleanup(sharing_system):
    """Demonstrate statistics and cleanup functionality."""
    print("\n📊 Demonstrating statistics and cleanup...")
    
    # Get sharing statistics
    stats = sharing_system.get_sharing_statistics()
    
    print(f"📈 Sharing Statistics:")
    print(f"   Total shares: {stats['total_shares']}")
    print(f"   Total accesses: {stats['total_accesses']}")
    print(f"   API endpoints: {stats['api_endpoints']}")
    print(f"   Expired shares: {stats['expired_shares']}")
    
    if stats['most_accessed']:
        print(f"   Most accessed: {stats['most_accessed']['title']} ({stats['most_accessed']['access_count']} accesses)")
    
    print(f"   Shares by type: {stats['shares_by_type']}")
    print(f"   Shares by permission: {stats['shares_by_permission']}")
    print(f"   Recent shares: {len(stats['recent_shares'])}")
    
    # Demonstrate cleanup (won't actually clean anything in this demo)
    cleaned_count = sharing_system.cleanup_expired_shares()
    print(f"🧹 Cleaned up {cleaned_count} expired shares")


def main():
    """Main demonstration function."""
    print("🚀 Analytics Sharing System Demo")
    print("=" * 50)
    
    # Create temporary directory for demo
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Initialize export manager
        export_manager = AnalyticsExportManager(temp_path / "exports")
        
        # Initialize sharing system with demo email config
        email_config = {
            'smtp_server': 'smtp.demo.com',
            'smtp_port': 587,
            'from_address': 'demo@example.com',
            'username': 'demo_user',
            'password': 'demo_pass',
            'use_tls': True
        }
        
        sharing_system = AnalyticsSharingSystem(
            export_manager=export_manager,
            database_path=temp_path / "sharing_demo.db",
            base_url="https://demo.lol-optimizer.com",
            email_config=email_config
        )
        
        # Create sample data
        player_analytics, champion_metrics = create_sample_data()
        
        # Demonstrate basic sharing
        player_share_id, champion_share_id = demonstrate_basic_sharing(
            sharing_system, player_analytics, champion_metrics
        )
        
        # Demonstrate advanced sharing
        protected_share_id, public_share_id = demonstrate_advanced_sharing(
            sharing_system, player_analytics
        )
        
        # Demonstrate content access
        share_ids = (player_share_id, champion_share_id, protected_share_id, public_share_id)
        demonstrate_content_access(sharing_system, share_ids)
        
        # Demonstrate email sharing
        demonstrate_email_sharing(sharing_system, player_share_id)
        
        # Demonstrate API endpoints
        api_endpoints = demonstrate_api_endpoints(sharing_system)
        
        # Demonstrate comprehensive reports
        comprehensive_share_id = demonstrate_comprehensive_reports(
            sharing_system, player_analytics, champion_metrics
        )
        
        # Demonstrate statistics and cleanup
        demonstrate_statistics_and_cleanup(sharing_system)
        
        print("\n✨ Demo completed successfully!")
        print(f"📁 Demo files created in: {temp_path}")
        print(f"🗄️ Database file: {temp_path / 'sharing_demo.db'}")
        
        # Show final summary
        final_stats = sharing_system.get_sharing_statistics()
        print(f"\n📊 Final Statistics:")
        print(f"   Created {final_stats['total_shares']} shareable items")
        print(f"   Generated {final_stats['total_accesses']} total accesses")
        print(f"   Set up {len(api_endpoints)} API endpoints")
        print(f"   Demonstrated all major sharing features")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️ Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()