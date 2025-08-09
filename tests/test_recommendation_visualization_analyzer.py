"""
Tests for Recommendation Visualization Analyzer

This module tests the comprehensive visualization and analysis tools for champion
recommendations, including confidence visualization, synergy analysis, comparison
matrices, trend analysis, and success rate tracking.
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
from typing import List, Dict, Any

import plotly.graph_objects as go

from lol_team_optimizer.recommendation_visualization_analyzer import (
    RecommendationVisualizationAnalyzer
)
from lol_team_optimizer.analytics_models import (
    ChampionRecommendation, TeamContext, PlayerRoleAssignment
)
from lol_team_optimizer.champion_recommendation_engine import ChampionRecommendationEngine
from lol_team_optimizer.advanced_recommendation_customizer import AdvancedRecommendationCustomizer
from lol_team_optimizer.analytics_sharing_system import AnalyticsSharingSystem


class TestRecommendationVisualizationAnalyzer:
    """Test suite for RecommendationVisualizationAnalyzer."""
    
    @pytest.fixture
    def mock_recommendation_engine(self):
        """Create mock recommendation engine."""
        engine = Mock(spec=ChampionRecommendationEngine)
        engine.champion_data = Mock()
        engine.champion_data.get_champion_name.side_effect = lambda x: f"Champion_{x}"
        engine.calculate_champion_synergy.return_value = 0.75
        engine.get_recommendations.return_value = [
            ChampionRecommendation(
                champion_id=1,
                champion_name="TestChamp1",
                role="jungle",
                score=0.85,
                confidence=0.90,
                reasoning="High performance",
                synergy_score=0.80,
                individual_score=0.85,
                meta_score=0.75
            ),
            ChampionRecommendation(
                champion_id=2,
                champion_name="TestChamp2",
                role="jungle",
                score=0.75,
                confidence=0.80,
                reasoning="Good synergy",
                synergy_score=0.85,
                individual_score=0.70,
                meta_score=0.80
            )
        ]
        return engine
    
    @pytest.fixture
    def mock_customizer(self):
        """Create mock advanced recommendation customizer."""
        return Mock(spec=AdvancedRecommendationCustomizer)
    
    @pytest.fixture
    def mock_sharing_system(self):
        """Create mock analytics sharing system."""
        sharing = Mock(spec=AnalyticsSharingSystem)
        sharing.export_analysis.return_value = {
            'file_path': '/tmp/test_export.html',
            'export_id': 'test_export_123',
            'format': 'html'
        }
        sharing.create_shareable_analysis.return_value = {
            'share_id': 'share_123',
            'share_url': 'https://example.com/share/123',
            'access_token': 'token_123'
        }
        return sharing
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        # Create a mock config since the dataclass isn't being exported
        from unittest.mock import Mock
        config = Mock()
        config.color_scheme = "viridis"
        config.chart_height = 400
        config.chart_width = 600
        config.confidence_bands = True
        config.uncertainty_alpha = 0.3
        return config
    
    @pytest.fixture
    def analyzer(self, mock_recommendation_engine, mock_customizer, mock_sharing_system, config):
        """Create RecommendationVisualizationAnalyzer instance."""
        return RecommendationVisualizationAnalyzer(
            recommendation_engine=mock_recommendation_engine,
            customizer=mock_customizer,
            sharing_system=mock_sharing_system,
            config=config
        )
    
    @pytest.fixture
    def sample_recommendations(self):
        """Create sample recommendations for testing."""
        return [
            ChampionRecommendation(
                champion_id=1,
                champion_name="Graves",
                role="jungle",
                score=0.85,
                confidence=0.90,
                reasoning="High individual performance",
                synergy_score=0.80,
                individual_score=0.85,
                meta_score=0.75
            ),
            ChampionRecommendation(
                champion_id=2,
                champion_name="Elise",
                role="jungle",
                score=0.75,
                confidence=0.80,
                reasoning="Good team synergy",
                synergy_score=0.85,
                individual_score=0.70,
                meta_score=0.80
            ),
            ChampionRecommendation(
                champion_id=3,
                champion_name="Kha'Zix",
                role="jungle",
                score=0.70,
                confidence=0.75,
                reasoning="Meta relevant pick",
                synergy_score=0.65,
                individual_score=0.75,
                meta_score=0.85
            )
        ]
    
    @pytest.fixture
    def sample_team_context(self):
        """Create sample team context."""
        return TeamContext(
            team_composition={
                "top": PlayerRoleAssignment(
                    player_id="player1",
                    champion_id=86,  # Garen
                    role="top",
                    confidence=0.9
                )
            },
            banned_champions=[64, 238],  # Lee Sin, Zed
            enemy_team_composition={},
            game_phase="draft",
            meta_context={}
        )
    
    def test_initialization(self, mock_recommendation_engine, mock_customizer, mock_sharing_system):
        """Test analyzer initialization."""
        analyzer = RecommendationVisualizationAnalyzer(
            recommendation_engine=mock_recommendation_engine,
            customizer=mock_customizer,
            sharing_system=mock_sharing_system
        )
        
        assert analyzer.recommendation_engine == mock_recommendation_engine
        assert analyzer.customizer == mock_customizer
        assert analyzer.sharing_system == mock_sharing_system
        assert analyzer.config is not None
    
    def test_create_confidence_visualization(self, analyzer, sample_recommendations):
        """Test confidence visualization creation."""
        fig = analyzer.create_confidence_visualization(sample_recommendations)
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 1  # At least the main bar chart
        
        # Check if uncertainty bands are included
        if analyzer.config.confidence_bands:
            assert len(fig.data) >= 2  # Bar chart + uncertainty bands
        
        # Verify chart properties
        assert fig.layout.title.text == "Champion Recommendations with Confidence Visualization"
        assert fig.layout.xaxis.title.text == "Champions"
        assert fig.layout.yaxis.title.text == "Recommendation Score"
    
    def test_create_confidence_visualization_empty(self, analyzer):
        """Test confidence visualization with empty recommendations."""
        fig = analyzer.create_confidence_visualization([])
        
        assert isinstance(fig, go.Figure)
        # Should create an empty chart with message
        assert len(fig.layout.annotations) > 0
    
    def test_create_synergy_analysis_chart(self, analyzer, sample_team_context):
        """Test synergy analysis chart creation."""
        candidate_champions = [1, 2, 3, 4, 5]
        
        fig = analyzer.create_synergy_analysis_chart(
            team_context=sample_team_context,
            role="jungle",
            candidate_champions=candidate_champions
        )
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 1  # At least the heatmap
        
        # Verify chart properties
        assert "Synergy Analysis" in fig.layout.title.text
        assert "jungle" in fig.layout.title.text.lower()
    
    def test_create_recommendation_comparison_matrix(self, analyzer):
        """Test recommendation comparison matrix creation."""
        scenarios = [
            {
                'name': 'Scenario 1',
                'banned_champions': [64],
                'enemy_composition': {}
            },
            {
                'name': 'Scenario 2',
                'banned_champions': [238],
                'enemy_composition': {}
            }
        ]
        
        fig = analyzer.create_recommendation_comparison_matrix(scenarios, "jungle")
        
        assert isinstance(fig, go.Figure)
        # Should have multiple subplots
        assert hasattr(fig, '_grid_ref')
        
        # Verify chart properties
        assert "Comparison Matrix" in fig.layout.title.text
    
    def test_create_recommendation_trend_analysis(self, analyzer):
        """Test recommendation trend analysis creation."""
        fig = analyzer.create_recommendation_trend_analysis(
            champion_id=1,
            role="jungle",
            days_back=30
        )
        
        assert isinstance(fig, go.Figure)
        # Should have multiple subplots for different metrics
        assert len(fig.data) >= 4  # Score, confidence, usage, success trends
        
        # Verify chart properties
        assert "Trend Analysis" in fig.layout.title.text
    
    def test_create_success_rate_tracking_chart(self, analyzer):
        """Test success rate tracking chart creation."""
        fig = analyzer.create_success_rate_tracking_chart(
            role="jungle",
            time_period_days=30
        )
        
        assert isinstance(fig, go.Figure)
        # Should have multiple subplots
        assert len(fig.data) >= 4  # Different success metrics
        
        # Verify chart properties
        assert "Success Rate Tracking" in fig.layout.title.text
    
    def test_export_recommendation_analysis(self, analyzer):
        """Test recommendation analysis export."""
        analysis_data = {
            'recommendations': [
                {'champion': 'Graves', 'score': 0.85, 'confidence': 0.90}
            ],
            'metadata': {'role': 'jungle', 'timestamp': datetime.now().isoformat()}
        }
        
        result = analyzer.export_recommendation_analysis(
            analysis_type="confidence_visualization",
            data=analysis_data,
            format="html"
        )
        
        assert 'file_path' in result
        assert 'export_id' in result
        assert result['format'] == 'html'
        
        # Verify sharing system was called
        analyzer.sharing_system.export_analysis.assert_called_once()
    
    def test_share_recommendation_analysis(self, analyzer):
        """Test recommendation analysis sharing."""
        analysis_data = {
            'type': 'synergy_analysis',
            'data': {'synergy_matrix': [[0.8, 0.6], [0.6, 0.8]]}
        }
        
        share_options = {
            'privacy': 'public',
            'expiration_days': 30
        }
        
        result = analyzer.share_recommendation_analysis(analysis_data, share_options)
        
        assert 'share_id' in result
        assert 'share_url' in result
        assert 'access_token' in result
        
        # Verify sharing system was called
        analyzer.sharing_system.create_shareable_analysis.assert_called_once()
    
    def test_analyze_champion_synergies(self, analyzer, sample_team_context):
        """Test champion synergy analysis."""
        candidate_champions = [1, 2, 3]
        
        # Call the private method directly for testing
        result = analyzer._analyze_champion_synergies(
            team_context=sample_team_context,
            role="jungle",
            candidate_champions=candidate_champions
        )
        
        assert result is not None
        assert isinstance(result, SynergyAnalysisResult)
        assert len(result.champion_labels) > 0
        assert result.heatmap_data.shape[0] > 0
        assert len(result.strongest_synergies) > 0
    
    def test_generate_scenario_comparisons(self, analyzer):
        """Test scenario comparison generation."""
        scenarios = [
            {'name': 'Scenario 1', 'banned_champions': [64]},
            {'name': 'Scenario 2', 'banned_champions': [238]}
        ]
        
        result = analyzer._generate_scenario_comparisons(scenarios, "jungle")
        
        assert result is not None
        assert isinstance(result, RecommendationComparisonMatrix)
        assert len(result.scenarios) == 2
        assert result.score_matrix.shape[0] == 2  # 2 scenarios
        assert len(result.consistency_scores) > 0
    
    def test_get_recommendation_trend_data(self, analyzer):
        """Test recommendation trend data retrieval."""
        result = analyzer._get_recommendation_trend_data(
            champion_id=1,
            role="jungle",
            days_back=30
        )
        
        assert result is not None
        assert isinstance(result, RecommendationTrendData)
        assert result.champion_id == 1
        assert result.role == "jungle"
        assert len(result.dates) == 31  # 30 days back + today
        assert len(result.scores) == len(result.dates)
        assert result.trend_direction in ["increasing", "decreasing", "stable"]
    
    def test_get_success_rate_metrics(self, analyzer):
        """Test success rate metrics retrieval."""
        result = analyzer._get_success_rate_metrics(
            role="jungle",
            time_period_days=30
        )
        
        assert isinstance(result, list)
        assert len(result) > 0
        
        for metric in result:
            assert isinstance(metric, RecommendationSuccessMetrics)
            assert metric.champion_id > 0
            assert 0 <= metric.success_rate <= 1
            assert metric.total_recommendations > 0
    
    def test_caching_behavior(self, analyzer, sample_team_context):
        """Test that caching works correctly."""
        candidate_champions = [1, 2, 3]
        
        # First call should compute and cache
        result1 = analyzer._analyze_champion_synergies(
            team_context=sample_team_context,
            role="jungle",
            candidate_champions=candidate_champions
        )
        
        # Second call should use cache
        result2 = analyzer._analyze_champion_synergies(
            team_context=sample_team_context,
            role="jungle",
            candidate_champions=candidate_champions
        )
        
        # Results should be identical (same object from cache)
        assert result1 is result2
    
    def test_error_handling_in_visualization(self, analyzer):
        """Test error handling in visualization methods."""
        # Test with invalid data that should trigger error handling
        with patch.object(analyzer.recommendation_engine, 'get_recommendations', 
                         side_effect=Exception("Test error")):
            
            fig = analyzer.create_recommendation_comparison_matrix(
                scenarios=[{'name': 'Test'}],
                role="jungle"
            )
            
            # Should return error chart
            assert isinstance(fig, go.Figure)
            # Error charts typically have annotations
            assert len(fig.layout.annotations) > 0
    
    def test_configuration_usage(self, mock_recommendation_engine, mock_customizer, mock_sharing_system):
        """Test that configuration is properly used."""
        custom_config = RecommendationVisualizationConfig(
            color_scheme="plasma",
            chart_height=800,
            chart_width=1200,
            confidence_bands=False
        )
        
        analyzer = RecommendationVisualizationAnalyzer(
            recommendation_engine=mock_recommendation_engine,
            customizer=mock_customizer,
            sharing_system=mock_sharing_system,
            config=custom_config
        )
        
        assert analyzer.config.color_scheme == "plasma"
        assert analyzer.config.chart_height == 800
        assert analyzer.config.chart_width == 1200
        assert analyzer.config.confidence_bands == False
    
    def test_empty_chart_creation(self, analyzer):
        """Test empty chart creation."""
        fig = analyzer._create_empty_chart("Test message")
        
        assert isinstance(fig, go.Figure)
        assert len(fig.layout.annotations) == 1
        assert fig.layout.annotations[0].text == "Test message"
    
    def test_error_chart_creation(self, analyzer):
        """Test error chart creation."""
        fig = analyzer._create_error_chart("Test error")
        
        assert isinstance(fig, go.Figure)
        assert len(fig.layout.annotations) == 1
        assert "Error: Test error" in fig.layout.annotations[0].text


class TestRecommendationVisualizationConfig:
    """Test suite for RecommendationVisualizationConfig."""
    
    def test_default_configuration(self):
        """Test default configuration values."""
        config = RecommendationVisualizationConfig()
        
        assert config.color_scheme == "viridis"
        assert config.chart_height == 500
        assert config.chart_width == 800
        assert config.confidence_bands == True
        assert config.uncertainty_alpha == 0.3
        assert config.synergy_heatmap_size == (600, 600)
        assert config.synergy_threshold == 0.1
        assert config.trend_window_days == 90
        assert config.trend_smoothing == True
        assert "png" in config.export_formats
        assert "html" in config.export_formats
        assert "pdf" in config.export_formats
        assert config.export_dpi == 300
    
    def test_custom_configuration(self):
        """Test custom configuration values."""
        config = RecommendationVisualizationConfig(
            color_scheme="plasma",
            chart_height=600,
            chart_width=900,
            confidence_bands=False,
            uncertainty_alpha=0.5,
            export_formats=["png", "svg"]
        )
        
        assert config.color_scheme == "plasma"
        assert config.chart_height == 600
        assert config.chart_width == 900
        assert config.confidence_bands == False
        assert config.uncertainty_alpha == 0.5
        assert config.export_formats == ["png", "svg"]


class TestDataStructures:
    """Test suite for data structures used in recommendation visualization."""
    
    def test_recommendation_trend_data(self):
        """Test RecommendationTrendData structure."""
        dates = [datetime.now() - timedelta(days=i) for i in range(5)]
        scores = [0.8, 0.75, 0.82, 0.78, 0.85]
        
        trend_data = RecommendationTrendData(
            champion_id=1,
            champion_name="TestChamp",
            role="jungle",
            dates=dates,
            scores=scores,
            confidence_values=[0.9] * 5,
            usage_rates=[0.3] * 5,
            success_rates=[0.7] * 5,
            trend_direction="increasing",
            trend_strength=0.8,
            volatility=0.1,
            avg_score=0.8,
            score_std=0.03,
            peak_score=0.85,
            peak_date=dates[-1]
        )
        
        assert trend_data.champion_id == 1
        assert trend_data.champion_name == "TestChamp"
        assert trend_data.role == "jungle"
        assert len(trend_data.dates) == 5
        assert len(trend_data.scores) == 5
        assert trend_data.trend_direction == "increasing"
        assert trend_data.peak_score == 0.85
    
    def test_synergy_analysis_result(self):
        """Test SynergyAnalysisResult structure."""
        synergy_result = SynergyAnalysisResult(
            champion_pairs=[(1, 2), (2, 3)],
            synergy_matrix={(1, 2): 0.8, (2, 3): 0.6},
            interaction_effects={},
            strongest_synergies=[(1, 2, 0.8)],
            weakest_synergies=[(2, 3, 0.6)],
            synergy_clusters=[[1, 2], [3]],
            heatmap_data=np.array([[0, 0.8], [0.8, 0]]),
            champion_labels=["Champ1", "Champ2"]
        )
        
        assert len(synergy_result.champion_pairs) == 2
        assert synergy_result.synergy_matrix[(1, 2)] == 0.8
        assert len(synergy_result.strongest_synergies) == 1
        assert synergy_result.heatmap_data.shape == (2, 2)
        assert len(synergy_result.champion_labels) == 2
    
    def test_recommendation_comparison_matrix(self):
        """Test RecommendationComparisonMatrix structure."""
        comparison_matrix = RecommendationComparisonMatrix(
            scenarios=["Scenario1", "Scenario2"],
            champions=[1, 2, 3],
            champion_names=["Champ1", "Champ2", "Champ3"],
            score_matrix=np.random.rand(2, 3),
            confidence_matrix=np.random.rand(2, 3),
            rank_matrix=np.array([[1, 2, 3], [2, 1, 3]]),
            consistency_scores={1: 0.8, 2: 0.6, 3: 0.7},
            scenario_difficulty={"Scenario1": 0.3, "Scenario2": 0.5},
            champion_versatility={1: 0.9, 2: 0.7, 3: 0.8}
        )
        
        assert len(comparison_matrix.scenarios) == 2
        assert len(comparison_matrix.champions) == 3
        assert comparison_matrix.score_matrix.shape == (2, 3)
        assert comparison_matrix.consistency_scores[1] == 0.8
        assert comparison_matrix.scenario_difficulty["Scenario1"] == 0.3
    
    def test_recommendation_success_metrics(self):
        """Test RecommendationSuccessMetrics structure."""
        success_metrics = RecommendationSuccessMetrics(
            champion_id=1,
            champion_name="TestChamp",
            role="jungle",
            total_recommendations=100,
            successful_outcomes=75,
            success_rate=0.75,
            avg_game_duration=28.5,
            avg_kda=2.1,
            avg_damage_dealt=18500.0,
            avg_gold_earned=12000.0,
            confidence_accuracy=0.85,
            overconfidence_bias=0.05,
            recent_success_rate=0.78,
            trend_direction="increasing",
            improvement_rate=0.02
        )
        
        assert success_metrics.champion_id == 1
        assert success_metrics.total_recommendations == 100
        assert success_metrics.successful_outcomes == 75
        assert success_metrics.success_rate == 0.75
        assert success_metrics.trend_direction == "increasing"
        assert success_metrics.improvement_rate == 0.02


if __name__ == "__main__":
    pytest.main([__file__])