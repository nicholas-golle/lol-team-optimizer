"""
Tests for the centralized match storage system.

This module tests match deduplication, storage, and retrieval functionality.
"""

import json
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from lol_team_optimizer.match_manager import MatchManager
from lol_team_optimizer.models import Match, MatchParticipant
from lol_team_optimizer.config import Config


class TestMatchManager:
    """Test cases for the MatchManager class."""
    
    def setup_method(self):
        """Set up test environment."""
        # Create temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        self.data_dir = Path(self.temp_dir) / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Create test config
        self.config = Config()
        self.config.data_directory = str(self.data_dir)
        
        self.match_manager = MatchManager(self.config)
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_match_data(self, match_id: str = "NA1_1234567890", 
                              puuids: list = None) -> dict:
        """Create test match data in Riot API format."""
        if puuids is None:
            puuids = ["test-puuid-1", "test-puuid-2", "test-puuid-3", 
                     "test-puuid-4", "test-puuid-5", "test-puuid-6",
                     "test-puuid-7", "test-puuid-8", "test-puuid-9", "test-puuid-10"]
        
        participants = []
        for i, puuid in enumerate(puuids):
            participant = {
                "puuid": puuid,
                "riotIdGameName": f"Player{i+1}",
                "riotIdTagline": "NA1",
                "championId": 1 + i,
                "championName": f"Champion{i+1}",
                "teamId": 100 if i < 5 else 200,
                "role": "SOLO" if i % 2 == 0 else "DUO",
                "lane": ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"][i % 5],
                "individualPosition": ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"][i % 5],
                "kills": i + 1,
                "deaths": i,
                "assists": i + 2,
                "totalDamageDealtToChampions": (i + 1) * 1000,
                "totalMinionsKilled": (i + 1) * 50,
                "neutralMinionsKilled": (i + 1) * 10,
                "visionScore": (i + 1) * 5,
                "goldEarned": (i + 1) * 500,
                "win": i < 5  # First team wins
            }
            participants.append(participant)
        
        teams = [
            {"teamId": 100, "win": True},
            {"teamId": 200, "win": False}
        ]
        
        return {
            "metadata": {
                "matchId": match_id
            },
            "info": {
                "gameCreation": int(datetime.now().timestamp() * 1000),
                "gameDuration": 1800,  # 30 minutes
                "gameEndTimestamp": int((datetime.now() + timedelta(minutes=30)).timestamp() * 1000),
                "gameMode": "CLASSIC",
                "gameType": "MATCHED_GAME",
                "mapId": 11,
                "queueId": 420,
                "gameVersion": "15.14.1",
                "participants": participants,
                "teams": teams
            }
        }
    
    def test_store_new_match(self):
        """Test storing a new match."""
        match_data = self.create_test_match_data()
        
        # Store the match
        result = self.match_manager.store_match(match_data)
        
        assert result is True  # New match stored
        
        # Verify match is stored
        stored_match = self.match_manager.get_match("NA1_1234567890")
        assert stored_match is not None
        assert stored_match.match_id == "NA1_1234567890"
        assert len(stored_match.participants) == 10
        assert stored_match.winning_team == 100
    
    def test_store_duplicate_match(self):
        """Test that duplicate matches are not stored."""
        match_data = self.create_test_match_data()
        
        # Store the match twice
        result1 = self.match_manager.store_match(match_data)
        result2 = self.match_manager.store_match(match_data)
        
        assert result1 is True   # First time stored
        assert result2 is False  # Duplicate not stored
        
        # Verify only one match exists
        stats = self.match_manager.get_match_statistics()
        assert stats['total_matches'] == 1
    
    def test_batch_store_with_deduplication(self):
        """Test batch storing with deduplication."""
        match_data1 = self.create_test_match_data("NA1_1111111111")
        match_data2 = self.create_test_match_data("NA1_2222222222")
        match_data3 = self.create_test_match_data("NA1_1111111111")  # Duplicate
        
        matches_data = [match_data1, match_data2, match_data3]
        
        # Batch store
        new_count, duplicate_count = self.match_manager.store_matches_batch(matches_data)
        
        assert new_count == 2
        assert duplicate_count == 1
        
        # Verify matches are stored
        stats = self.match_manager.get_match_statistics()
        assert stats['total_matches'] == 2
    
    def test_get_matches_for_player(self):
        """Test retrieving matches for a specific player."""
        # Create matches with overlapping players
        match_data1 = self.create_test_match_data("NA1_1111111111", 
                                                 ["player1", "player2", "player3", "player4", "player5",
                                                  "other1", "other2", "other3", "other4", "other5"])
        match_data2 = self.create_test_match_data("NA1_2222222222",
                                                 ["player1", "player6", "player7", "player8", "player9",
                                                  "other6", "other7", "other8", "other9", "other10"])
        
        # Store matches
        self.match_manager.store_match(match_data1)
        self.match_manager.store_match(match_data2)
        
        # Get matches for player1 (should be in both)
        player1_matches = self.match_manager.get_matches_for_player("player1")
        assert len(player1_matches) == 2
        
        # Get matches for player2 (should be in one)
        player2_matches = self.match_manager.get_matches_for_player("player2")
        assert len(player2_matches) == 1
        
        # Get matches for non-existent player
        no_matches = self.match_manager.get_matches_for_player("nonexistent")
        assert len(no_matches) == 0
    
    def test_get_matches_with_multiple_players(self):
        """Test retrieving matches with multiple known players."""
        # Create a match with multiple known players
        known_puuids = {"player1", "player2", "player3"}
        match_data = self.create_test_match_data("NA1_1111111111",
                                               ["player1", "player2", "unknown1", "unknown2", "unknown3",
                                                "player3", "unknown4", "unknown5", "unknown6", "unknown7"])
        
        self.match_manager.store_match(match_data)
        
        # Get matches with multiple known players
        multi_player_matches = self.match_manager.get_matches_with_multiple_players(known_puuids)
        
        assert len(multi_player_matches) == 1
        match = multi_player_matches[0]
        known_players = match.get_known_players(known_puuids)
        assert len(known_players) == 3
    
    def test_match_participant_properties(self):
        """Test MatchParticipant calculated properties."""
        participant = MatchParticipant(
            puuid="test-puuid",
            kills=5,
            deaths=2,
            assists=8,
            total_minions_killed=150,
            neutral_minions_killed=30
        )
        
        assert participant.kda == (5 + 8) / 2  # (kills + assists) / deaths
        assert participant.cs_total == 180  # minions + jungle monsters
    
    def test_match_properties(self):
        """Test Match calculated properties."""
        match_data = self.create_test_match_data()
        self.match_manager.store_match(match_data)
        
        match = self.match_manager.get_match("NA1_1234567890")
        
        # Test datetime conversion
        assert isinstance(match.game_creation_datetime, datetime)
        assert isinstance(match.game_end_datetime, datetime)
        
        # Test participant lookup
        participant = match.get_participant_by_puuid("test-puuid-1")
        assert participant is not None
        assert participant.puuid == "test-puuid-1"
        
        # Test team lookup
        team_100 = match.get_participants_by_team(100)
        team_200 = match.get_participants_by_team(200)
        assert len(team_100) == 5
        assert len(team_200) == 5
    
    def test_cleanup_old_matches(self):
        """Test cleaning up old matches."""
        # Create old and new matches
        old_timestamp = int((datetime.now() - timedelta(days=100)).timestamp() * 1000)
        new_timestamp = int(datetime.now().timestamp() * 1000)
        
        old_match_data = self.create_test_match_data("NA1_OLD_MATCH")
        old_match_data["info"]["gameCreation"] = old_timestamp
        
        new_match_data = self.create_test_match_data("NA1_NEW_MATCH")
        new_match_data["info"]["gameCreation"] = new_timestamp
        
        # Store both matches
        self.match_manager.store_match(old_match_data)
        self.match_manager.store_match(new_match_data)
        
        # Verify both are stored
        stats = self.match_manager.get_match_statistics()
        assert stats['total_matches'] == 2
        
        # Clean up matches older than 90 days
        removed_count = self.match_manager.cleanup_old_matches(90)
        
        assert removed_count == 1
        
        # Verify only new match remains
        stats = self.match_manager.get_match_statistics()
        assert stats['total_matches'] == 1
        assert self.match_manager.get_match("NA1_NEW_MATCH") is not None
        assert self.match_manager.get_match("NA1_OLD_MATCH") is None
    
    def test_match_statistics(self):
        """Test match statistics calculation."""
        # Store some test matches
        for i in range(3):
            match_data = self.create_test_match_data(f"NA1_MATCH_{i}")
            self.match_manager.store_match(match_data)
        
        stats = self.match_manager.get_match_statistics()
        
        assert stats['total_matches'] == 3
        assert stats['total_players_indexed'] == 10  # 10 unique players across matches
        assert stats['oldest_match'] is not None
        assert stats['newest_match'] is not None
        assert stats['queue_distribution'][420] == 3  # All matches are ranked solo
    
    def test_rebuild_index(self):
        """Test rebuilding the match index."""
        # Store a match
        match_data = self.create_test_match_data()
        self.match_manager.store_match(match_data)
        
        # Corrupt the index
        self.match_manager._match_index = {}
        
        # Verify index is empty
        player_matches = self.match_manager.get_matches_for_player("test-puuid-1")
        assert len(player_matches) == 0
        
        # Rebuild index
        self.match_manager.rebuild_index()
        
        # Verify index is restored
        player_matches = self.match_manager.get_matches_for_player("test-puuid-1")
        assert len(player_matches) == 1
    
    def test_persistence(self):
        """Test that matches persist across manager instances."""
        # Store a match
        match_data = self.create_test_match_data()
        self.match_manager.store_match(match_data)
        
        # Create new manager instance
        new_manager = MatchManager(self.config)
        
        # Verify match is loaded
        stored_match = new_manager.get_match("NA1_1234567890")
        assert stored_match is not None
        assert stored_match.match_id == "NA1_1234567890"
        
        # Verify index is loaded
        player_matches = new_manager.get_matches_for_player("test-puuid-1")
        assert len(player_matches) == 1


if __name__ == "__main__":
    pytest.main([__file__])