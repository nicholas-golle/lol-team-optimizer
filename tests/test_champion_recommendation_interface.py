"""
Tests for Champion Recommendation Interface

This module tests the intelligent champion recommendation interface
with drag-and-drop team building, real-time updates, and analysis.
"""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch

from lol_team_optimizer.champion_recommendation_interface import (
    ChampionRecommendationInterface,
    RecommendationSession,
    RecommendationStrategy
)
from lol_team_optimizer.core_engine import CoreEngine
from lol_team_optimizer.models import Player
from lol_team_optimizer.analytics_models import ChampionRecommendation, TeamContext


class TestRecommendationSession:
    """Test RecommendationSession data class."""
    
    def test_session_initialization(self):
        """Test session initialization with default values."""
        session_id = str(uuid.uuid4())
        session = RecommendationSession(session_id=session_id)
        
        assert session.session_id == session_id
        assert len(session.team_composition) == 5
        assert all(role in session.team_composition for role in ["top", "jungle", "middle", "bottom", "support"])
        assert all(assignment is None for assignment in session.team_composition.values())
        assert session.current_strategy == "balanced"
        assert isinstance(session.recommendation_history, list)
        assert len(session.recommendation_history) == 0
    
    def test_session_with_custom_values(self):
        """Test session initialization with custom values."""
        session_id = str(uuid.uuid4())
        custom_composition = {"top": Mock(), "jungle": None, "middle": None, "bottom": None, "support": None}
        
        session = RecommendationSession(
            session_id=session_id,
            team_composition=custom_composition,
            current_strategy="aggressive"
        )
        
        assert session.session_id == session_id
        assert session.team_composition == custom_composition
        assert session.current_strategy == "aggressive"


class TestRecommendationStrategy:
    """Test RecommendationStrategy data class."""
    
    def test_default_strategies(self):
        """Test default strategy configurations."""
        strategies = RecommendationStrategy.get_default_strategies()
        
        assert len(strategies) == 4
        assert "safe" in strategies
        assert "balanced" in strategies
        assert "aggressive" in strategies
        assert "counter_pick" in strategies
        
        # Test safe strategy
        safe = strategies["safe"]
        assert safe.name == "Safe"
        assert safe.risk_tolerance == 0.2
        assert safe.weights["individual_performance"] == 0.45
        
        # Test balanced strategy
        balanced = strategies["balanced"]
        assert balanced.name == "Balanced"
        assert balanced.risk_tolerance == 0.5
        assert balanced.meta_emphasis == 1.0
        
        # Test aggressive strategy
        aggressive = strategies["aggressive"]
        assert aggressive.name == "Aggressive"
        assert aggressive.risk_tolerance == 0.8
        assert aggressive.weights["team_synergy"] == 0.35
        
        # Test counter-pick strategy
        counter_pick = strategies["counter_pick"]
        assert counter_pick.name == "Counter-Pick"
        assert counter_pick.weights["meta_relevance"] == 0.25


class TestChampionRecommendationInterface:
    """Test ChampionRecommendationInterface class."""
    
    @pytest.fixture
    def mock_core_engine(self):
        """Create mock core engine."""
        engine = Mock(spec=CoreEngine)
        engine.config = Mock()
        engine.historical_analytics_engine = Mock()
        engine.champion_data_manager = Mock()
        engine.baseline_manager = Mock()
        engine.data_manager = Mock()
        
        # Mock player data
        mock_players = [
            Player(name="Player1", summoner_name="summoner1", puuid="puuid1"),
            Player(name="Player2", summoner_name="summoner2", puuid="puuid2"),
            Player(name="Player3", summoner_name="summoner3", puuid="puuid3")
        ]
        engine.data_manager.load_player_data.return_value = mock_players
        
        return engine
    
    @pytest.fixture
    def recommendation_interface(self, mock_core_engine):
        """Create recommendation interface instance."""
        return ChampionRecommendationInterface(mock_core_engine)
    
    def test_initialization(self, recommendation_interface, mock_core_engine):
        """Test interface initialization."""
        assert recommendation_interface.core_engine == mock_core_engine
        assert hasattr(recommendation_interface, 'recommendation_engine')
        assert hasattr(recommendation_interface, 'sessions')
        assert hasattr(recommendation_interface, 'strategies')
        assert len(recommendation_interface.strategies) == 4
        assert isinstance(recommendation_interface.sessions, dict)
    
    def test_create_recommendation_interface(self, recommendation_interface):
        """Test creation of recommendation interface components."""
        components = recommendation_interface.create_recommendation_interface()
        
        # Check that all required components are created
        assert 'header' in components
        assert 'strategy_selector' in components
        assert 'refresh_btn' in components
        assert 'reset_btn' in components
        
        # Check team builder components
        for role in ["top", "jungle", "middle", "bottom", "support"]:
            assert f'{role}_header' in components
            assert f'{role}_player' in components
            assert f'{role}_champion' in components
            assert f'{role}_status' in components
        
        # Check recommendation panel components
        assert 'recommendation_header' in components
        assert 'target_role' in components
        assert 'get_recommendations_btn' in components
        assert 'recommendations_display' in components
        
        # Check analysis panel components
        assert 'analysis_header' in components
        assert 'synergy_matrix' in components
        assert 'performance_chart' in components
        assert 'risk_chart' in components
        assert 'meta_chart' in components
        
        # Check history panel components
        assert 'history_header' in components
        assert 'save_composition_btn' in components
        assert 'history_display' in components
        
        # Verify a session was created
        assert len(recommendation_interface.sessions) == 1
    
    def test_handle_strategy_change(self, recommendation_interface):
        """Test strategy change handling."""
        # Create a session
        session_id = str(uuid.uuid4())
        recommendation_interface.sessions[session_id] = RecommendationSession(session_id=session_id)
        
        # Test strategy change
        result = recommendation_interface._handle_strategy_change(session_id, "aggressive")
        
        assert isinstance(result, tuple)
        assert len(result) == 2
        
        # Check that session was updated
        session = recommendation_interface.sessions[session_id]
        assert session.current_strategy == "aggressive"
        assert session.last_updated is not None
    
    def test_handle_player_assignment(self, recommendation_interface):
        """Test player assignment handling."""
        # Create a session
        session_id = str(uuid.uuid4())
        recommendation_interface.sessions[session_id] = RecommendationSession(session_id=session_id)
        
        # Test player assignment
        result = recommendation_interface._handle_player_assignment(
            session_id, "top", "Player1 (summoner1)"
        )
        
        assert isinstance(result, tuple)
        assert len(result) == 3
        
        # Check that session was updated
        session = recommendation_interface.sessions[session_id]
        assert session.team_composition["top"] is not None
        assert session.team_composition["top"].player_name == "Player1"
        assert session.team_composition["top"].role == "top"
    
    def test_handle_champion_assignment(self, recommendation_interface):
        """Test champion assignment handling."""
        # Create a session with player assigned
        session_id = str(uuid.uuid4())
        session = RecommendationSession(session_id=session_id)
        session.team_composition["top"] = Mock()
        session.team_composition["top"].player_name = "Player1"
        recommendation_interface.sessions[session_id] = session
        
        # Test champion assignment
        result = recommendation_interface._handle_champion_assignment(
            session_id, "top", "Aatrox (266)"
        )
        
        assert isinstance(result, tuple)
        assert len(result) == 3
        
        # Check that champion was assigned
        assert session.team_composition["top"].champion_id == 266
    
    @patch('lol_team_optimizer.champion_recommendation_interface.ChampionRecommendationEngine')
    def test_generate_recommendations(self, mock_engine_class, recommendation_interface):
        """Test recommendation generation."""
        # Setup mock recommendation engine
        mock_engine = Mock()
        mock_recommendations = [
            Mock(spec=ChampionRecommendation),
            Mock(spec=ChampionRecommendation)
        ]
        mock_recommendations[0].champion_name = "Aatrox"
        mock_recommendations[0].champion_id = 266
        mock_recommendations[0].confidence = 0.85
        mock_recommendations[1].champion_name = "Garen"
        mock_recommendations[1].champion_id = 86
        mock_recommendations[1].confidence = 0.75
        
        mock_engine.get_champion_recommendations.return_value = mock_recommendations
        recommendation_interface.recommendation_engine = mock_engine
        
        # Create session with player assigned
        session_id = str(uuid.uuid4())
        session = RecommendationSession(session_id=session_id)
        session.team_composition["top"] = Mock()
        session.team_composition["top"].puuid = "puuid1"
        session.team_composition["top"].player_name = "Player1"
        recommendation_interface.sessions[session_id] = session
        
        # Test recommendation generation
        result = recommendation_interface._generate_recommendations(
            session_id, "top", "balanced", 0.5, 10, False, True
        )
        
        assert isinstance(result, tuple)
        assert len(result) == 2
        
        # Check that recommendations were generated
        html_result, choices = result
        assert isinstance(html_result, str)
        assert isinstance(choices, list)
        assert len(choices) == 2
        
        # Check that session history was updated
        assert len(session.recommendation_history) == 1
        assert session.recommendation_history[0]['role'] == "top"
        assert session.recommendation_history[0]['strategy'] == "balanced"
    
    def test_save_and_load_composition(self, recommendation_interface):
        """Test composition saving and loading."""
        # Create session with composition
        session_id = str(uuid.uuid4())
        session = RecommendationSession(session_id=session_id)
        session.team_composition["top"] = Mock()
        session.team_composition["top"].player_name = "Player1"
        session.team_composition["top"].champion_id = 266
        recommendation_interface.sessions[session_id] = session
        
        # Test saving composition
        save_result = recommendation_interface._save_composition(session_id)
        assert isinstance(save_result, tuple)
        assert len(save_result) == 2
        
        choices, history_html = save_result
        assert isinstance(choices, list)
        assert len(choices) == 1
        assert isinstance(history_html, str)
        
        # Test loading composition
        composition_id = choices[0][1]  # Get the ID from the choice tuple
        load_result = recommendation_interface._load_composition(session_id, composition_id)
        
        assert isinstance(load_result, tuple)
        assert len(load_result) == 10  # 5 players + 5 champions
    
    def test_reset_team_composition(self, recommendation_interface):
        """Test team composition reset."""
        # Create session with composition
        session_id = str(uuid.uuid4())
        session = RecommendationSession(session_id=session_id)
        session.team_composition["top"] = Mock()
        recommendation_interface.sessions[session_id] = session
        
        # Test reset
        result = recommendation_interface._reset_team_composition(session_id)
        
        assert isinstance(result, tuple)
        assert len(result) == 12  # All UI components
        
        # Check that composition was reset
        assert all(assignment is None for assignment in session.team_composition.values())
    
    def test_get_available_players(self, recommendation_interface):
        """Test getting available players."""
        players = recommendation_interface._get_available_players()
        
        assert isinstance(players, list)
        assert len(players) == 3  # From mock data
        assert all(isinstance(p, Player) for p in players)
    
    def test_get_player_choices(self, recommendation_interface):
        """Test getting player choices for dropdowns."""
        choices = recommendation_interface._get_player_choices()
        
        assert isinstance(choices, list)
        assert len(choices) == 3
        assert all(isinstance(choice, str) for choice in choices)
        assert "Player1 (summoner1)" in choices
    
    def test_parse_champion_selection(self, recommendation_interface):
        """Test parsing champion selection strings."""
        # Test valid selection
        champion_id = recommendation_interface._parse_champion_selection("Aatrox (266)")
        assert champion_id == 266
        
        # Test invalid selection
        champion_id = recommendation_interface._parse_champion_selection("Invalid")
        assert champion_id is None
        
        # Test empty selection
        champion_id = recommendation_interface._parse_champion_selection("")
        assert champion_id is None
    
    def test_create_role_status_display(self, recommendation_interface):
        """Test role status display creation."""
        # Test no player assigned
        html = recommendation_interface._create_role_status_display("top", None, None)
        assert "No player assigned" in html
        
        # Test player assigned, no champion
        html = recommendation_interface._create_role_status_display("top", "Player1", None)
        assert "Player1" in html
        assert "Champion needed" in html
        
        # Test both player and champion assigned
        html = recommendation_interface._create_role_status_display("top", "Player1", "Aatrox")
        assert "Player1" in html
        assert "Aatrox" in html
    
    def test_create_team_synergy_display(self, recommendation_interface):
        """Test team synergy display creation."""
        # Create session
        session_id = str(uuid.uuid4())
        session = RecommendationSession(session_id=session_id)
        session.team_composition["top"] = Mock()
        session.team_composition["jungle"] = Mock()
        recommendation_interface.sessions[session_id] = session
        
        html = recommendation_interface._create_team_synergy_display(session_id)
        
        assert isinstance(html, str)
        assert "Team Composition Status" in html
        assert "2/5" in html  # 2 roles assigned
    
    def test_create_strategy_info_display(self, recommendation_interface):
        """Test strategy info display creation."""
        html = recommendation_interface._create_strategy_info_display("balanced")
        
        assert isinstance(html, str)
        assert "Balanced Strategy" in html
        assert "Individual Performance" in html
        assert "Team Synergy" in html
    
    def test_error_handling(self, recommendation_interface):
        """Test error handling in various methods."""
        # Test with invalid session ID
        result = recommendation_interface._handle_strategy_change("invalid_session", "balanced")
        assert "Session not found" in result[0]
        
        # Test player assignment with invalid session
        result = recommendation_interface._handle_player_assignment("invalid_session", "top", "Player1")
        assert result[1] == "Session not found"
        
        # Test champion assignment with invalid session
        result = recommendation_interface._handle_champion_assignment("invalid_session", "top", "Aatrox")
        assert "Session not found" in result[0]


class TestIntegration:
    """Integration tests for the recommendation interface."""
    
    @pytest.fixture
    def mock_core_engine_full(self):
        """Create a more complete mock core engine for integration tests."""
        engine = Mock(spec=CoreEngine)
        engine.config = Mock()
        engine.historical_analytics_engine = Mock()
        engine.champion_data_manager = Mock()
        engine.baseline_manager = Mock()
        engine.data_manager = Mock()
        
        # Mock player data
        mock_players = [
            Player(name="TestPlayer1", summoner_name="test1", puuid="puuid1"),
            Player(name="TestPlayer2", summoner_name="test2", puuid="puuid2")
        ]
        engine.data_manager.load_player_data.return_value = mock_players
        
        # Mock champion data
        engine.champion_data_manager.get_champion_name.return_value = "TestChampion"
        
        return engine
    
    def test_full_workflow(self, mock_core_engine_full):
        """Test a complete recommendation workflow."""
        interface = ChampionRecommendationInterface(mock_core_engine_full)
        
        # Create interface
        components = interface.create_recommendation_interface()
        assert len(components) > 0
        
        # Get session ID
        session_id = list(interface.sessions.keys())[0]
        
        # Assign player to role
        result = interface._handle_player_assignment(session_id, "top", "TestPlayer1 (test1)")
        assert isinstance(result, tuple)
        
        # Assign champion to role
        result = interface._handle_champion_assignment(session_id, "top", "TestChampion (266)")
        assert isinstance(result, tuple)
        
        # Save composition
        result = interface._save_composition(session_id)
        assert isinstance(result, tuple)
        
        # Reset composition
        result = interface._reset_team_composition(session_id)
        assert isinstance(result, tuple)
    
    def test_multiple_sessions(self, mock_core_engine_full):
        """Test handling multiple concurrent sessions."""
        interface = ChampionRecommendationInterface(mock_core_engine_full)
        
        # Create multiple interfaces (simulating multiple users)
        components1 = interface.create_recommendation_interface()
        components2 = interface.create_recommendation_interface()
        
        # Should have 2 sessions
        assert len(interface.sessions) == 2
        
        session_ids = list(interface.sessions.keys())
        
        # Test that sessions are independent
        interface._handle_strategy_change(session_ids[0], "aggressive")
        interface._handle_strategy_change(session_ids[1], "safe")
        
        assert interface.sessions[session_ids[0]].current_strategy == "aggressive"
        assert interface.sessions[session_ids[1]].current_strategy == "safe"


if __name__ == "__main__":
    pytest.main([__file__])