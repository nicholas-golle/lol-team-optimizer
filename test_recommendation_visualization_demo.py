#!/usr/bin/env python3
"""
Recommendation Visualization Analyzer Demo

This script demonstrates the comprehensive visualization and analysis tools for champion
recommendations, including confidence visualization, synergy analysis, comparison
matrices, trend analysis, and success rate tracking.
"""

import sys
import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lol_team_optimizer.recommendation_visualization_analyzer import (
    RecommendationVisualizationAnalyzer
)
from lol_team_optimizer.analytics_models import (
    ChampionRecommendation, TeamContext, PlayerRoleAssignment
)
from lol_team_optimizer.champion_recommendation_engine import ChampionRecommendationEngine
from lol_team_optimizer.advanced_recommendation_customizer import AdvancedRecommendationCustomizer
from lol_team_optimizer.analytics_sharing_system import AnalyticsSharingSystem
from lol_team_optimizer.core_engine import CoreEngine
from lol_team_optimizer.config import Config


def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def create_sample_recommendations() -> List[ChampionRecommendation]:
    """Create sample recommendations for demonstration."""
    return [
        ChampionRecommendation(
            champion_id=64,
            champion_name="Lee Sin",
            role="jungle",
            recommendation_score=0.92,
            confidence=0.95
        ),
        ChampionRecommendation(
            champion_id=60,
            champion_name="Elise",
            role="jungle",
            recommendation_score=0.87,
            confidence=0.89
        ),
        ChampionRecommendation(
            champion_id=104,
            champion_name="Graves",
            role="jungle",
            recommendation_score=0.84,
            confidence=0.91
        ),
        ChampionRecommendation(
            champion_id=121,
            champion_name="Kha'Zix",
            role="jungle",
            recommendation_score=0.81,
            confidence=0.86
        ),
        ChampionRecommendation(
            champion_id=76,
            champion_name="Nidalee",
            role="jungle",
            recommendation_score=0.78,
            confidence=0.82
        )
    ]


def create_sample_team_context() -> TeamContext:
    """Create sample team context for demonstration."""
    return TeamContext(
        team_composition={
            "top": PlayerRoleAssignment(
                player_id="player1",
                champion_id=86,  # Garen
                role="top",
                confidence=0.9
            ),
            "middle": PlayerRoleAssignment(
                player_id="player2",
                champion_id=238,  # Zed
                role="middle",
                confidence=0.85
            ),
            "bottom": PlayerRoleAssignment(
                player_id="player3",
                champion_id=22,  # Ashe
                role="bottom",
                confidence=0.88
            ),
            "support": PlayerRoleAssignment(
                player_id="player4",
                champion_id=412,  # Thresh
                role="support",
                confidence=0.92
            )
        },
        banned_champions=[238, 555, 777],  # Some banned champions
        enemy_team_composition={},
        game_phase="draft",
        meta_context={"patch": "13.1", "tier": "diamond"}
    )


def create_sample_scenarios() -> List[Dict[str, Any]]:
    """Create sample scenarios for comparison."""
    return [
        {
            'name': 'Early Game Focus',
            'banned_champions': [64, 76],  # Lee Sin, Nidalee
            'enemy_composition': {'jungle': 104},  # Enemy Graves
            'strategy': 'early_aggression',
            'meta_context': {'emphasis': 'early_game'}
        },
        {
            'name': 'Late Game Scaling',
            'banned_champions': [121, 60],  # Kha'Zix, Elise
            'enemy_composition': {'jungle': 64},  # Enemy Lee Sin
            'strategy': 'scaling',
            'meta_context': {'emphasis': 'late_game'}
        },
        {
            'name': 'Team Fight Oriented',
            'banned_champions': [104, 238],  # Graves, Zed
            'enemy_composition': {'middle': 103},  # Enemy Ahri
            'strategy': 'team_fight',
            'meta_context': {'emphasis': 'team_fights'}
        },
        {
            'name': 'Split Push Strategy',
            'banned_champions': [412, 111],  # Thresh, Nautilus
            'enemy_composition': {'top': 86},  # Enemy Garen
            'strategy': 'split_push',
            'meta_context': {'emphasis': 'side_lanes'}
        }
    ]


def demonstrate_confidence_visualization(analyzer: RecommendationVisualizationAnalyzer):
    """Demonstrate confidence visualization with uncertainty bands."""
    print("\n" + "="*60)
    print("CONFIDENCE VISUALIZATION DEMONSTRATION")
    print("="*60)
    
    recommendations = create_sample_recommendations()
    
    print(f"Creating confidence visualization for {len(recommendations)} recommendations...")
    
    # Create visualization with uncertainty bands
    fig = analyzer.create_confidence_visualization(
        recommendations=recommendations,
        include_uncertainty_bands=True
    )
    
    print("✓ Confidence visualization created successfully")
    print(f"  - Chart contains {len(fig.data)} data traces")
    print(f"  - Includes uncertainty bands: {analyzer.config.confidence_bands}")
    print(f"  - Color scheme: {analyzer.config.color_scheme}")
    
    # Save the chart
    output_file = "recommendation_confidence_visualization.html"
    fig.write_html(output_file)
    print(f"  - Saved to: {output_file}")
    
    # Display recommendation details
    print("\nRecommendation Details:")
    for i, rec in enumerate(recommendations, 1):
        uncertainty = 1.0 - rec.confidence
        print(f"  {i}. {rec.champion_name}")
        print(f"     Score: {rec.score:.3f} | Confidence: {rec.confidence:.3f} | Uncertainty: {uncertainty:.3f}")
        print(f"     Reasoning: {rec.reasoning}")


def demonstrate_synergy_analysis(analyzer: RecommendationVisualizationAnalyzer):
    """Demonstrate synergy analysis charts."""
    print("\n" + "="*60)
    print("SYNERGY ANALYSIS DEMONSTRATION")
    print("="*60)
    
    team_context = create_sample_team_context()
    candidate_champions = [64, 60, 104, 121, 76, 11, 79, 20]  # Various jungle champions
    
    print(f"Analyzing synergies for {len(candidate_champions)} candidate champions...")
    print("Current team composition:")
    for role, assignment in team_context.team_composition.items():
        if assignment:
            print(f"  - {role.title()}: Champion {assignment.champion_id}")
    
    # Create synergy analysis chart
    fig = analyzer.create_synergy_analysis_chart(
        team_context=team_context,
        role="jungle",
        candidate_champions=candidate_champions
    )
    
    print("✓ Synergy analysis chart created successfully")
    print(f"  - Analyzing synergies for jungle role")
    print(f"  - Heatmap size: {analyzer.config.synergy_heatmap_size}")
    print(f"  - Synergy threshold: {analyzer.config.synergy_threshold}")
    
    # Save the chart
    output_file = "recommendation_synergy_analysis.html"
    fig.write_html(output_file)
    print(f"  - Saved to: {output_file}")


def demonstrate_comparison_matrix(analyzer: RecommendationVisualizationAnalyzer):
    """Demonstrate recommendation comparison matrices."""
    print("\n" + "="*60)
    print("COMPARISON MATRIX DEMONSTRATION")
    print("="*60)
    
    scenarios = create_sample_scenarios()
    
    print(f"Comparing recommendations across {len(scenarios)} scenarios...")
    for i, scenario in enumerate(scenarios, 1):
        print(f"  {i}. {scenario['name']}")
        print(f"     Strategy: {scenario['strategy']}")
        print(f"     Banned: {len(scenario['banned_champions'])} champions")
    
    # Create comparison matrix
    fig = analyzer.create_recommendation_comparison_matrix(
        scenarios=scenarios,
        role="jungle"
    )
    
    print("✓ Comparison matrix created successfully")
    print("  - Matrix includes: Scores, Confidence, Rankings, Consistency")
    print("  - Analysis covers: Champion versatility, scenario difficulty")
    
    # Save the chart
    output_file = "recommendation_comparison_matrix.html"
    fig.write_html(output_file)
    print(f"  - Saved to: {output_file}")


def demonstrate_trend_analysis(analyzer: RecommendationVisualizationAnalyzer):
    """Demonstrate recommendation trend analysis."""
    print("\n" + "="*60)
    print("TREND ANALYSIS DEMONSTRATION")
    print("="*60)
    
    champion_id = 64  # Lee Sin
    role = "jungle"
    days_back = 60
    
    print(f"Analyzing trends for Champion {champion_id} in {role} role...")
    print(f"Time period: {days_back} days back")
    
    # Create trend analysis
    fig = analyzer.create_recommendation_trend_analysis(
        champion_id=champion_id,
        role=role,
        days_back=days_back
    )
    
    print("✓ Trend analysis created successfully")
    print("  - Includes: Score trends, confidence trends, usage rates, success rates")
    print("  - Features: Trend lines, volatility analysis, peak performance tracking")
    
    # Save the chart
    output_file = "recommendation_trend_analysis.html"
    fig.write_html(output_file)
    print(f"  - Saved to: {output_file}")


def demonstrate_success_rate_tracking(analyzer: RecommendationVisualizationAnalyzer):
    """Demonstrate success rate tracking."""
    print("\n" + "="*60)
    print("SUCCESS RATE TRACKING DEMONSTRATION")
    print("="*60)
    
    role = "jungle"
    time_period = 30
    
    print(f"Tracking success rates for {role} role over {time_period} days...")
    
    # Create success rate tracking chart
    fig = analyzer.create_success_rate_tracking_chart(
        role=role,
        time_period_days=time_period
    )
    
    print("✓ Success rate tracking chart created successfully")
    print("  - Metrics: Overall vs recent performance, confidence accuracy")
    print("  - Analysis: Recommendation volume, performance trends")
    print("  - Features: Improvement rate tracking, overconfidence detection")
    
    # Save the chart
    output_file = "recommendation_success_tracking.html"
    fig.write_html(output_file)
    print(f"  - Saved to: {output_file}")


def demonstrate_export_and_sharing(analyzer: RecommendationVisualizationAnalyzer):
    """Demonstrate export and sharing functionality."""
    print("\n" + "="*60)
    print("EXPORT AND SHARING DEMONSTRATION")
    print("="*60)
    
    # Prepare sample analysis data
    analysis_data = {
        'type': 'comprehensive_analysis',
        'recommendations': [rec.__dict__ for rec in create_sample_recommendations()],
        'team_context': create_sample_team_context().__dict__,
        'scenarios': create_sample_scenarios(),
        'timestamp': datetime.now().isoformat(),
        'metadata': {
            'role': 'jungle',
            'analysis_version': '1.0',
            'config': analyzer.config.__dict__
        }
    }
    
    print("Demonstrating export functionality...")
    
    # Test different export formats
    export_formats = ['html', 'json']
    
    for format_type in export_formats:
        try:
            result = analyzer.export_recommendation_analysis(
                analysis_type="comprehensive_visualization",
                data=analysis_data,
                format=format_type
            )
            
            print(f"✓ Export to {format_type.upper()} successful")
            print(f"  - Export ID: {result.get('export_id', 'N/A')}")
            print(f"  - File path: {result.get('file_path', 'N/A')}")
            
        except Exception as e:
            print(f"✗ Export to {format_type.upper()} failed: {e}")
    
    print("\nDemonstrating sharing functionality...")
    
    # Test sharing
    share_options = {
        'privacy': 'public',
        'expiration_days': 30,
        'allow_comments': True,
        'include_raw_data': False
    }
    
    try:
        result = analyzer.share_recommendation_analysis(
            analysis_data=analysis_data,
            share_options=share_options
        )
        
        print("✓ Sharing successful")
        print(f"  - Share ID: {result.get('share_id', 'N/A')}")
        print(f"  - Share URL: {result.get('share_url', 'N/A')}")
        print(f"  - Access token: {result.get('access_token', 'N/A')}")
        
    except Exception as e:
        print(f"✗ Sharing failed: {e}")


def demonstrate_configuration_options():
    """Demonstrate different configuration options."""
    print("\n" + "="*60)
    print("CONFIGURATION OPTIONS DEMONSTRATION")
    print("="*60)
    
    print("Configuration options are handled internally by the analyzer.")
    print("The analyzer uses default settings that can be customized through the config parameter.")
    print("Available options include:")
    print("  - Color schemes: viridis, plasma, blues, reds, custom")
    print("  - Chart dimensions: customizable width and height")
    print("  - Confidence bands: enable/disable uncertainty visualization")
    print("  - Export formats: png, html, pdf, svg")
    print("  - Trend analysis: customizable time windows and smoothing")


def main():
    """Main demonstration function."""
    print("RECOMMENDATION VISUALIZATION ANALYZER DEMO")
    print("=" * 80)
    print("This demo showcases the comprehensive visualization and analysis tools")
    print("for champion recommendations in the LoL Team Optimizer.")
    print("=" * 80)
    
    setup_logging()
    
    try:
        # Initialize components (using mocks for demo)
        print("\nInitializing components...")
        
        # Create mock components for demonstration
        config = Config()
        core_engine = CoreEngine()
        
        # Initialize the analyzer with mock components
        from unittest.mock import Mock
        
        mock_recommendation_engine = Mock()
        mock_recommendation_engine.champion_data.get_champion_name.side_effect = lambda x: f"Champion_{x}"
        mock_recommendation_engine.calculate_champion_synergy.return_value = 0.75
        mock_recommendation_engine.get_recommendations.return_value = create_sample_recommendations()
        
        mock_customizer = Mock()
        mock_sharing_system = Mock()
        mock_sharing_system.export_analysis.return_value = {
            'file_path': '/tmp/demo_export.html',
            'export_id': 'demo_export_123',
            'format': 'html'
        }
        mock_sharing_system.create_shareable_analysis.return_value = {
            'share_id': 'demo_share_123',
            'share_url': 'https://example.com/share/demo_123',
            'access_token': 'demo_token_123'
        }
        
        # Create analyzer
        analyzer = RecommendationVisualizationAnalyzer(
            recommendation_engine=mock_recommendation_engine,
            customizer=mock_customizer,
            sharing_system=mock_sharing_system
        )
        
        print("✓ Components initialized successfully")
        
        # Run demonstrations
        demonstrate_confidence_visualization(analyzer)
        demonstrate_synergy_analysis(analyzer)
        demonstrate_comparison_matrix(analyzer)
        demonstrate_trend_analysis(analyzer)
        demonstrate_success_rate_tracking(analyzer)
        demonstrate_export_and_sharing(analyzer)
        demonstrate_configuration_options()
        
        print("\n" + "="*80)
        print("DEMONSTRATION COMPLETE")
        print("="*80)
        print("All visualization features have been demonstrated successfully!")
        print("\nGenerated files:")
        print("  - recommendation_confidence_visualization.html")
        print("  - recommendation_synergy_analysis.html")
        print("  - recommendation_comparison_matrix.html")
        print("  - recommendation_trend_analysis.html")
        print("  - recommendation_success_tracking.html")
        print("\nThese files can be opened in a web browser to view the interactive visualizations.")
        
    except Exception as e:
        print(f"\n✗ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)