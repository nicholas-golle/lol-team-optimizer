"""
Synergy management system for League of Legends team optimization.

This module handles the collection, analysis, and storage of player synergy data
based on match history and performance metrics.
"""

import logging
import json
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

from .models import Player, SynergyDatabase, PlayerSynergyData
from .riot_client import RiotAPIClient


class SynergyManager:
    """
    Manager for collecting and analyzing player synergy data.
    
    Handles fetching match history, analyzing player combinations,
    and maintaining the synergy database.
    """
    
    def __init__(self, riot_client: Optional[RiotAPIClient] = None, 
                 cache_directory: str = "cache"):
        """
        Initialize the synergy manager.
        
        Args:
            riot_client: Riot API client for fetching match data
            cache_directory: Directory for caching synergy data
        """
        self.logger = logging.getLogger(__name__)
        self.riot_client = riot_client
        self.cache_directory = cache_directory
        self.synergy_db = SynergyDatabase()
        
        # Ensure cache directory exists
        os.makedirs(cache_directory, exist_ok=True)
        self.synergy_cache_file = os.path.join(cache_directory, "synergy_data.json")
        
        # Load existing synergy data
        self._load_synergy_data()
        
        self.logger.info("Synergy manager initialized")
    
    def _load_synergy_data(self):
        """Load synergy data from cache file."""
        try:
            if os.path.exists(self.synergy_cache_file):
                with open(self.synergy_cache_file, 'r') as f:
                    data = json.load(f)
                
                # Reconstruct synergy database
                self.synergy_db = SynergyDatabase()
                
                for key_str, synergy_data in data.get('synergies', {}).items():
                    # Parse key
                    player1, player2 = key_str.split('|')
                    key = (player1, player2)
                    
                    # Reconstruct PlayerSynergyData
                    synergy = PlayerSynergyData(
                        player1_name=player1,
                        player2_name=player2,
                        games_together=synergy_data.get('games_together', 0),
                        wins_together=synergy_data.get('wins_together', 0),
                        losses_together=synergy_data.get('losses_together', 0),
                        avg_combined_kda=synergy_data.get('avg_combined_kda', 0.0),
                        avg_game_duration=synergy_data.get('avg_game_duration', 0.0),
                        avg_vision_score_combined=synergy_data.get('avg_vision_score_combined', 0.0),
                        recent_games_together=synergy_data.get('recent_games_together', 0)
                    )
                    
                    # Reconstruct role combinations
                    for role_key_str, role_data in synergy_data.get('role_combinations', {}).items():
                        role1, role2 = role_key_str.split('|')
                        role_key = (role1, role2)
                        synergy.role_combinations[role_key] = role_data
                    
                    # Reconstruct champion combinations
                    for champ_key_str, champ_data in synergy_data.get('champion_combinations', {}).items():
                        champ1, champ2 = map(int, champ_key_str.split('|'))
                        champ_key = (champ1, champ2)
                        synergy.champion_combinations[champ_key] = champ_data
                    
                    # Parse datetime fields
                    if synergy_data.get('last_played_together'):
                        synergy.last_played_together = datetime.fromisoformat(
                            synergy_data['last_played_together']
                        )
                    
                    self.synergy_db.synergies[key] = synergy
                
                # Parse last updated
                if data.get('last_updated'):
                    self.synergy_db.last_updated = datetime.fromisoformat(data['last_updated'])
                
                self.logger.info(f"Loaded synergy data for {len(self.synergy_db.synergies)} player pairs")
            
        except Exception as e:
            self.logger.warning(f"Failed to load synergy data: {e}")
            self.synergy_db = SynergyDatabase()
    
    def _save_synergy_data(self):
        """Save synergy data to cache file."""
        try:
            data = {
                'synergies': {},
                'last_updated': self.synergy_db.last_updated.isoformat() if self.synergy_db.last_updated else None
            }
            
            for key, synergy in self.synergy_db.synergies.items():
                key_str = f"{key[0]}|{key[1]}"
                
                synergy_data = {
                    'games_together': synergy.games_together,
                    'wins_together': synergy.wins_together,
                    'losses_together': synergy.losses_together,
                    'avg_combined_kda': synergy.avg_combined_kda,
                    'avg_game_duration': synergy.avg_game_duration,
                    'avg_vision_score_combined': synergy.avg_vision_score_combined,
                    'recent_games_together': synergy.recent_games_together,
                    'last_played_together': synergy.last_played_together.isoformat() if synergy.last_played_together else None,
                    'role_combinations': {},
                    'champion_combinations': {}
                }
                
                # Serialize role combinations
                for role_key, role_data in synergy.role_combinations.items():
                    role_key_str = f"{role_key[0]}|{role_key[1]}"
                    synergy_data['role_combinations'][role_key_str] = role_data
                
                # Serialize champion combinations
                for champ_key, champ_data in synergy.champion_combinations.items():
                    champ_key_str = f"{champ_key[0]}|{champ_key[1]}"
                    synergy_data['champion_combinations'][champ_key_str] = champ_data
                
                data['synergies'][key_str] = synergy_data
            
            with open(self.synergy_cache_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            self.logger.info(f"Saved synergy data for {len(self.synergy_db.synergies)} player pairs")
            
        except Exception as e:
            self.logger.error(f"Failed to save synergy data: {e}")
    
    def update_synergy_data_for_players(self, players: List[Player], 
                                      match_count: int = 20, 
                                      comprehensive: bool = False) -> bool:
        """
        Update synergy data by analyzing recent matches for all players.
        
        Args:
            players: List of players to analyze
            match_count: Number of recent matches to analyze per player
            comprehensive: If True, collect extensive match history (up to 100 games)
            
        Returns:
            True if update was successful
        """
        if not self.riot_client:
            self.logger.warning("No Riot API client available for synergy updates")
            return False
        
        self.logger.info(f"Updating synergy data for {len(players)} players")
        
        try:
            if comprehensive:
                return self._comprehensive_match_history_collection(players)
            else:
                return self._standard_match_history_collection(players, match_count)
            
        except Exception as e:
            self.logger.error(f"Failed to update synergy data: {e}")
            return False
    
    def _standard_match_history_collection(self, players: List[Player], match_count: int) -> bool:
        """
        Standard match history collection (20-30 games per player).
        
        Args:
            players: List of players to analyze
            match_count: Number of recent matches to analyze per player
            
        Returns:
            True if collection was successful
        """
        # Collect all match IDs from all players
        all_match_ids = set()
        player_match_map = {}  # match_id -> list of players in that match
        
        for player in players:
            if not player.puuid:
                self.logger.warning(f"Player {player.name} has no PUUID, skipping")
                continue
            
            # Get recent match history
            match_ids = self.riot_client.get_match_history(player.puuid, count=match_count)
            
            for match_id in match_ids:
                all_match_ids.add(match_id)
                if match_id not in player_match_map:
                    player_match_map[match_id] = []
                player_match_map[match_id].append(player)
        
        return self._process_collected_matches(all_match_ids, player_match_map)
    
    def _comprehensive_match_history_collection(self, players: List[Player]) -> bool:
        """
        Comprehensive match history collection with rate limiting (up to 100 games per player).
        
        Args:
            players: List of players to analyze
            
        Returns:
            True if collection was successful
        """
        import time
        
        self.logger.info("Starting comprehensive match history collection (up to 100 games per player)")
        self.logger.info("This process respects API rate limits and may take several minutes...")
        
        # Track all unique matches and which players were in them
        all_match_ids = set()
        player_match_map = {}  # match_id -> list of players in that match
        player_match_counts = {}  # player_name -> number of matches collected
        
        # Rate limiting parameters
        requests_made = 0
        last_request_time = time.time()
        rate_limit_delay = 1.2  # Seconds between requests to stay under rate limits
        
        for player in players:
            if not player.puuid:
                self.logger.warning(f"Player {player.name} has no PUUID, skipping")
                continue
            
            self.logger.info(f"Collecting extensive match history for {player.name}...")
            player_match_counts[player.name] = 0
            
            # Collect matches in batches to get up to 100 games
            start_index = 0
            batch_size = 20
            total_collected = 0
            
            while total_collected < 100:
                # Rate limiting
                current_time = time.time()
                time_since_last = current_time - last_request_time
                if time_since_last < rate_limit_delay:
                    sleep_time = rate_limit_delay - time_since_last
                    self.logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
                    time.sleep(sleep_time)
                
                try:
                    # Get batch of matches
                    match_ids = self.riot_client.get_match_history(
                        player.puuid, 
                        count=min(batch_size, 100 - total_collected),
                        start=start_index
                    )
                    
                    requests_made += 1
                    last_request_time = time.time()
                    
                    if not match_ids:
                        self.logger.info(f"No more matches available for {player.name} (collected {total_collected})")
                        break
                    
                    # Add matches to our collection
                    for match_id in match_ids:
                        all_match_ids.add(match_id)
                        if match_id not in player_match_map:
                            player_match_map[match_id] = []
                        player_match_map[match_id].append(player)
                    
                    total_collected += len(match_ids)
                    player_match_counts[player.name] = total_collected
                    start_index += len(match_ids)
                    
                    self.logger.info(f"  Collected {total_collected} matches for {player.name}")
                    
                    # If we got fewer matches than requested, we've reached the end
                    if len(match_ids) < batch_size:
                        break
                
                except Exception as e:
                    self.logger.warning(f"Error collecting matches for {player.name}: {e}")
                    break
        
        # Log collection summary
        total_matches = len(all_match_ids)
        self.logger.info(f"Comprehensive collection complete:")
        self.logger.info(f"  Total unique matches: {total_matches}")
        self.logger.info(f"  API requests made: {requests_made}")
        for player_name, count in player_match_counts.items():
            self.logger.info(f"  {player_name}: {count} matches")
        
        # Find matches with multiple tracked players (these are the ones we care about for synergy)
        shared_matches = {match_id: players_list for match_id, players_list in player_match_map.items() 
                         if len(players_list) > 1}
        
        self.logger.info(f"Found {len(shared_matches)} matches with multiple tracked players")
        
        return self._process_collected_matches(shared_matches.keys(), player_match_map, comprehensive=True)
    
    def _process_collected_matches(self, match_ids, player_match_map: Dict, comprehensive: bool = False) -> bool:
        """
        Process collected matches to extract synergy data.
        
        Args:
            match_ids: Iterable of match IDs to process
            player_match_map: Mapping of match_id -> list of players
            comprehensive: Whether this is comprehensive collection (affects logging)
            
        Returns:
            True if processing was successful
        """
        import time
        
        match_ids_list = list(match_ids)
        self.logger.info(f"Processing {len(match_ids_list)} matches for synergy analysis")
        
        # Rate limiting for match details requests
        requests_made = 0
        last_request_time = time.time()
        rate_limit_delay = 1.2 if comprehensive else 0.5  # More conservative for comprehensive
        
        processed_matches = 0
        failed_matches = 0
        
        for i, match_id in enumerate(match_ids_list):
            try:
                # Only process matches with multiple tracked players
                players_in_match = player_match_map[match_id]
                if len(players_in_match) < 2:
                    continue
                
                # Rate limiting
                current_time = time.time()
                time_since_last = current_time - last_request_time
                if time_since_last < rate_limit_delay:
                    sleep_time = rate_limit_delay - time_since_last
                    time.sleep(sleep_time)
                
                # Get match details
                match_details = self.riot_client.get_match_details(match_id)
                requests_made += 1
                last_request_time = time.time()
                
                if not match_details:
                    failed_matches += 1
                    continue
                
                # Process match for synergy data
                self._process_match_for_synergy(match_details, players_in_match)
                processed_matches += 1
                
                # Progress logging
                if comprehensive:
                    if processed_matches % 25 == 0:
                        progress = (i + 1) / len(match_ids_list) * 100
                        self.logger.info(f"Progress: {progress:.1f}% ({processed_matches} matches processed)")
                else:
                    if processed_matches % 10 == 0:
                        self.logger.info(f"Processed {processed_matches} matches...")
            
            except Exception as e:
                self.logger.warning(f"Failed to process match {match_id}: {e}")
                failed_matches += 1
                continue
        
        # Final summary
        self.logger.info(f"Match processing complete:")
        self.logger.info(f"  Successfully processed: {processed_matches} matches")
        self.logger.info(f"  Failed to process: {failed_matches} matches")
        self.logger.info(f"  API requests made: {requests_made}")
        
        if processed_matches > 0:
            # Save updated synergy data
            self._save_synergy_data()
            self.logger.info("Synergy data saved successfully")
            return True
        else:
            self.logger.warning("No matches were successfully processed")
            return False
    
    def collect_comprehensive_match_history(self, players: List[Player]) -> Dict[str, any]:
        """
        Public method to collect comprehensive match history with detailed reporting.
        
        Args:
            players: List of players to analyze
            
        Returns:
            Dictionary with collection results and statistics
        """
        if not self.riot_client:
            return {
                'success': False,
                'error': 'No Riot API client available',
                'stats': {}
            }
        
        start_time = time.time()
        initial_synergy_count = len(self.synergy_db.synergies)
        
        success = self.update_synergy_data_for_players(players, comprehensive=True)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Generate detailed statistics
        final_synergy_count = len(self.synergy_db.synergies)
        new_synergies = final_synergy_count - initial_synergy_count
        
        # Calculate synergy data quality
        synergies_with_data = sum(1 for s in self.synergy_db.synergies.values() if s.games_together > 0)
        high_confidence_synergies = sum(1 for s in self.synergy_db.synergies.values() if s.games_together >= 10)
        
        # Calculate average games together
        total_games = sum(s.games_together for s in self.synergy_db.synergies.values())
        avg_games_together = total_games / synergies_with_data if synergies_with_data > 0 else 0
        
        stats = {
            'duration_minutes': duration / 60,
            'initial_synergy_pairs': initial_synergy_count,
            'final_synergy_pairs': final_synergy_count,
            'new_synergy_pairs': new_synergies,
            'synergies_with_data': synergies_with_data,
            'high_confidence_synergies': high_confidence_synergies,
            'average_games_together': avg_games_together,
            'data_coverage_percent': (synergies_with_data / final_synergy_count * 100) if final_synergy_count > 0 else 0
        }
        
        return {
            'success': success,
            'stats': stats,
            'recommendations': self._generate_collection_recommendations(stats)
        }
    
    def _generate_collection_recommendations(self, stats: Dict[str, any]) -> List[str]:
        """Generate recommendations based on collection statistics."""
        recommendations = []
        
        if stats['data_coverage_percent'] < 50:
            recommendations.append("Low data coverage - consider running comprehensive collection again in a few days")
        elif stats['data_coverage_percent'] < 80:
            recommendations.append("Good data coverage - periodic updates should maintain synergy accuracy")
        else:
            recommendations.append("Excellent data coverage - synergy analysis should be highly accurate")
        
        if stats['high_confidence_synergies'] < stats['synergies_with_data'] * 0.3:
            recommendations.append("Many synergy pairs have low confidence - encourage more team play")
        
        if stats['average_games_together'] < 5:
            recommendations.append("Low average games together - team synergy will improve with more shared matches")
        elif stats['average_games_together'] > 15:
            recommendations.append("High average games together - synergy data should be very reliable")
        
        if stats['duration_minutes'] > 10:
            recommendations.append("Collection took significant time - consider running during off-peak hours")
        
        return recommendations
    
    def _process_match_for_synergy(self, match_details: Dict, tracked_players: List[Player]):
        """
        Process a single match to extract synergy data.
        
        Args:
            match_details: Match details from Riot API
            tracked_players: List of players we're tracking in this match
        """
        try:
            participants = match_details.get('info', {}).get('participants', [])
            game_creation = match_details.get('info', {}).get('gameCreation', 0)
            game_duration = match_details.get('info', {}).get('gameDuration', 0)
            
            # Map PUUIDs to our tracked players
            puuid_to_player = {player.puuid: player for player in tracked_players}
            
            # Find participant data for our tracked players
            tracked_participants = []
            for participant in participants:
                puuid = participant.get('puuid')
                if puuid in puuid_to_player:
                    player = puuid_to_player[puuid]
                    
                    # Extract role information
                    role = self._normalize_role(
                        participant.get('teamPosition', ''),
                        participant.get('individualPosition', '')
                    )
                    
                    tracked_participants.append({
                        'player_name': player.name,
                        'puuid': puuid,
                        'role': role,
                        'champion_id': participant.get('championId', 0),
                        'win': participant.get('win', False),
                        'kills': participant.get('kills', 0),
                        'deaths': participant.get('deaths', 0),
                        'assists': participant.get('assists', 0),
                        'vision_score': participant.get('visionScore', 0),
                        'team_id': participant.get('teamId', 0)
                    })
            
            # Only process if we have at least 2 tracked players
            if len(tracked_participants) < 2:
                return
            
            # Group by team (only analyze synergy within same team)
            teams = {}
            for participant in tracked_participants:
                team_id = participant['team_id']
                if team_id not in teams:
                    teams[team_id] = []
                teams[team_id].append(participant)
            
            # Process synergy for each team
            for team_participants in teams.values():
                if len(team_participants) < 2:
                    continue
                
                # Create match data structure
                match_data = {
                    'participants': team_participants,
                    'game_creation': game_creation,
                    'game_duration': game_duration
                }
                
                # Add to synergy database
                self.synergy_db.add_match_data(match_data)
        
        except Exception as e:
            self.logger.warning(f"Failed to process match for synergy: {e}")
    
    def _normalize_role(self, team_position: str, individual_position: str) -> str:
        """
        Normalize role information from Riot API.
        
        Args:
            team_position: Team position from API
            individual_position: Individual position from API
            
        Returns:
            Normalized role string
        """
        # Use team position first, fall back to individual position
        position = team_position or individual_position
        
        role_mapping = {
            'TOP': 'top',
            'JUNGLE': 'jungle',
            'MIDDLE': 'middle',
            'MID': 'middle',
            'BOTTOM': 'bottom',
            'BOT': 'bottom',
            'UTILITY': 'support',
            'SUPPORT': 'support'
        }
        
        return role_mapping.get(position.upper(), 'unknown')
    
    def get_synergy_database(self) -> SynergyDatabase:
        """Get the synergy database."""
        return self.synergy_db
    
    def analyze_player_synergies(self, player_name: str) -> Dict[str, any]:
        """
        Analyze synergies for a specific player.
        
        Args:
            player_name: Name of the player to analyze
            
        Returns:
            Dictionary containing synergy analysis
        """
        synergies = self.synergy_db.get_all_synergies_for_player(player_name)
        
        if not synergies:
            return {
                'player': player_name,
                'total_teammates': 0,
                'best_teammates': [],
                'worst_teammates': [],
                'role_synergies': {},
                'recommendations': ['No synergy data available - play more games with teammates']
            }
        
        # Calculate teammate scores
        teammate_scores = []
        role_synergies = {}
        
        for synergy in synergies:
            teammate = synergy.player2_name if synergy.player1_name == player_name else synergy.player1_name
            
            if synergy.games_together >= 3:  # Minimum games for reliable data
                score = synergy.calculate_overall_synergy_score()
                teammate_scores.append((teammate, score, synergy.games_together, synergy.win_rate_together))
                
                # Analyze role synergies
                for role_key, role_data in synergy.role_combinations.items():
                    if role_data['games'] >= 2:  # Minimum for role synergy
                        role_synergy_score = role_data['wins'] / role_data['games']
                        role_str = f"{role_key[0]}-{role_key[1]}"
                        
                        if role_str not in role_synergies:
                            role_synergies[role_str] = []
                        
                        role_synergies[role_str].append({
                            'teammate': teammate,
                            'games': role_data['games'],
                            'win_rate': role_synergy_score,
                            'synergy_score': (role_synergy_score - 0.5) * 0.4  # Convert to synergy scale
                        })
        
        # Sort teammates by synergy score
        teammate_scores.sort(key=lambda x: x[1], reverse=True)
        
        best_teammates = teammate_scores[:5]
        worst_teammates = teammate_scores[-3:] if len(teammate_scores) > 3 else []
        
        # Generate recommendations
        recommendations = []
        if len(best_teammates) > 0:
            best_teammate, best_score, games, win_rate = best_teammates[0]
            recommendations.append(f"Best synergy with {best_teammate} ({games} games, {win_rate:.1%} WR)")
        
        if len(worst_teammates) > 0:
            worst_teammate, worst_score, games, win_rate = worst_teammates[-1]
            if worst_score < -0.05:
                recommendations.append(f"Work on synergy with {worst_teammate} ({games} games, {win_rate:.1%} WR)")
        
        if len(teammate_scores) < 3:
            recommendations.append("Play more games with teammates to build synergy data")
        
        return {
            'player': player_name,
            'total_teammates': len(synergies),
            'teammates_with_data': len(teammate_scores),
            'best_teammates': [
                {
                    'name': name,
                    'synergy_score': score,
                    'games': games,
                    'win_rate': win_rate
                }
                for name, score, games, win_rate in best_teammates
            ],
            'worst_teammates': [
                {
                    'name': name,
                    'synergy_score': score,
                    'games': games,
                    'win_rate': win_rate
                }
                for name, score, games, win_rate in worst_teammates
            ],
            'role_synergies': role_synergies,
            'recommendations': recommendations
        }
    
    def get_team_synergy_report(self, player_names: List[str]) -> Dict[str, any]:
        """
        Generate a comprehensive synergy report for a team.
        
        Args:
            player_names: List of player names in the team
            
        Returns:
            Dictionary containing team synergy report
        """
        if len(player_names) < 2:
            return {
                'team_size': len(player_names),
                'synergy_matrix': {},
                'overall_score': 0.0,
                'recommendations': ['Need at least 2 players for synergy analysis']
            }
        
        synergy_matrix = self.synergy_db.calculate_team_synergy_matrix(player_names)
        
        # Calculate overall team synergy
        if synergy_matrix:
            overall_score = sum(synergy_matrix.values()) / len(synergy_matrix)
        else:
            overall_score = 0.0
        
        # Identify best and worst pairs
        sorted_pairs = sorted(synergy_matrix.items(), key=lambda x: x[1], reverse=True)
        
        best_pairs = sorted_pairs[:3]
        worst_pairs = sorted_pairs[-3:] if len(sorted_pairs) > 3 else []
        
        # Generate recommendations
        recommendations = []
        
        if overall_score > 0.05:
            recommendations.append("Team has good overall synergy")
        elif overall_score < -0.05:
            recommendations.append("Team synergy needs improvement - consider more practice together")
        else:
            recommendations.append("Team synergy is neutral - room for improvement")
        
        if best_pairs:
            best_pair, best_score = best_pairs[0]
            recommendations.append(f"Strongest synergy: {best_pair[0]} + {best_pair[1]} ({best_score:+.2f})")
        
        if worst_pairs and worst_pairs[-1][1] < -0.05:
            worst_pair, worst_score = worst_pairs[-1]
            recommendations.append(f"Weakest synergy: {worst_pair[0]} + {worst_pair[1]} ({worst_score:+.2f}) - needs attention")
        
        # Calculate data coverage
        total_possible_pairs = len(player_names) * (len(player_names) - 1) // 2
        pairs_with_data = sum(1 for (p1, p2), score in synergy_matrix.items() 
                             if self.synergy_db.get_synergy(p1, p2).games_together > 0)
        
        data_coverage = pairs_with_data / total_possible_pairs if total_possible_pairs > 0 else 0.0
        
        if data_coverage < 0.5:
            recommendations.append(f"Limited synergy data ({data_coverage:.1%} coverage) - play more games together")
        
        return {
            'team_size': len(player_names),
            'synergy_matrix': {
                f"{pair[0]} + {pair[1]}": {
                    'synergy_score': score,
                    'games_together': self.synergy_db.get_synergy(pair[0], pair[1]).games_together,
                    'win_rate_together': self.synergy_db.get_synergy(pair[0], pair[1]).win_rate_together
                }
                for pair, score in synergy_matrix.items()
            },
            'overall_score': overall_score,
            'best_pairs': [
                {
                    'players': list(pair),
                    'synergy_score': score,
                    'games_together': self.synergy_db.get_synergy(pair[0], pair[1]).games_together
                }
                for pair, score in best_pairs
            ],
            'worst_pairs': [
                {
                    'players': list(pair),
                    'synergy_score': score,
                    'games_together': self.synergy_db.get_synergy(pair[0], pair[1]).games_together
                }
                for pair, score in worst_pairs
            ],
            'data_coverage': data_coverage,
            'recommendations': recommendations
        }
    
    def get_shared_matches_analysis(self, players: List[Player]) -> Dict[str, any]:
        """
        Analyze shared matches between players to understand synergy data quality.
        
        Args:
            players: List of players to analyze
            
        Returns:
            Dictionary with shared match analysis
        """
        if not self.riot_client:
            return {'error': 'No Riot API client available'}
        
        # Get match history for each player
        player_matches = {}
        for player in players:
            if not player.puuid:
                continue
            
            try:
                matches = self.riot_client.get_match_history(player.puuid, count=50)
                player_matches[player.name] = set(matches)
            except Exception as e:
                self.logger.warning(f"Failed to get matches for {player.name}: {e}")
                player_matches[player.name] = set()
        
        # Find shared matches between all pairs
        shared_analysis = {}
        total_shared_matches = set()
        
        player_names = list(player_matches.keys())
        for i, player1 in enumerate(player_names):
            for player2 in player_names[i+1:]:
                shared_matches = player_matches[player1] & player_matches[player2]
                pair_key = f"{player1} + {player2}"
                shared_analysis[pair_key] = {
                    'shared_matches': len(shared_matches),
                    'player1_total': len(player_matches[player1]),
                    'player2_total': len(player_matches[player2]),
                    'overlap_percentage': len(shared_matches) / min(len(player_matches[player1]), len(player_matches[player2])) * 100 if min(len(player_matches[player1]), len(player_matches[player2])) > 0 else 0
                }
                total_shared_matches.update(shared_matches)
        
        # Overall statistics
        total_unique_matches = set()
        for matches in player_matches.values():
            total_unique_matches.update(matches)
        
        return {
            'player_match_counts': {name: len(matches) for name, matches in player_matches.items()},
            'shared_analysis': shared_analysis,
            'total_unique_matches': len(total_unique_matches),
            'total_shared_matches': len(total_shared_matches),
            'shared_match_percentage': len(total_shared_matches) / len(total_unique_matches) * 100 if total_unique_matches else 0,
            'recommendations': self._generate_shared_match_recommendations(shared_analysis)
        }
    
    def _generate_shared_match_recommendations(self, shared_analysis: Dict) -> List[str]:
        """Generate recommendations based on shared match analysis."""
        recommendations = []
        
        if not shared_analysis:
            recommendations.append("No shared matches found - players may not play together regularly")
            return recommendations
        
        # Find pairs with good shared match counts
        high_synergy_pairs = [pair for pair, data in shared_analysis.items() if data['shared_matches'] >= 10]
        medium_synergy_pairs = [pair for pair, data in shared_analysis.items() if 5 <= data['shared_matches'] < 10]
        low_synergy_pairs = [pair for pair, data in shared_analysis.items() if data['shared_matches'] < 5]
        
        if high_synergy_pairs:
            recommendations.append(f"Excellent synergy data for {len(high_synergy_pairs)} pairs (10+ shared matches)")
        
        if medium_synergy_pairs:
            recommendations.append(f"Good synergy data for {len(medium_synergy_pairs)} pairs (5-9 shared matches)")
        
        if low_synergy_pairs:
            recommendations.append(f"Limited synergy data for {len(low_synergy_pairs)} pairs (<5 shared matches)")
            recommendations.append("Consider playing more games together to improve synergy accuracy")
        
        # Check for very high overlap (might indicate duo queue)
        high_overlap_pairs = [pair for pair, data in shared_analysis.items() if data['overlap_percentage'] > 80]
        if high_overlap_pairs:
            recommendations.append(f"High overlap detected for {len(high_overlap_pairs)} pairs - likely frequent duo partners")
        
        return recommendations
    
    def optimize_synergy_data_collection(self, players: List[Player]) -> Dict[str, any]:
        """
        Optimize synergy data collection by focusing on shared matches.
        
        Args:
            players: List of players to optimize collection for
            
        Returns:
            Dictionary with optimization results
        """
        if not self.riot_client:
            return {'error': 'No Riot API client available'}
        
        self.logger.info("Optimizing synergy data collection by analyzing shared matches...")
        
        # First, analyze current shared matches
        shared_analysis = self.get_shared_matches_analysis(players)
        
        if 'error' in shared_analysis:
            return shared_analysis
        
        # Identify player pairs that need more data
        pairs_needing_data = []
        for pair, data in shared_analysis['shared_analysis'].items():
            if data['shared_matches'] < 10:  # Threshold for reliable synergy
                pairs_needing_data.append((pair, data['shared_matches']))
        
        # Sort by current shared match count (prioritize pairs with some data)
        pairs_needing_data.sort(key=lambda x: x[1], reverse=True)
        
        self.logger.info(f"Found {len(pairs_needing_data)} player pairs needing more synergy data")
        
        # Collect additional match history for players in pairs needing data
        players_needing_more_data = set()
        for pair, _ in pairs_needing_data:
            player1, player2 = pair.split(' + ')
            players_needing_more_data.add(player1)
            players_needing_more_data.add(player2)
        
        # Filter to actual player objects
        players_to_update = [p for p in players if p.name in players_needing_more_data]
        
        if players_to_update:
            self.logger.info(f"Collecting additional match history for {len(players_to_update)} players")
            success = self.update_synergy_data_for_players(players_to_update, match_count=75, comprehensive=True)
            
            if success:
                # Re-analyze after collection
                updated_analysis = self.get_shared_matches_analysis(players)
                
                return {
                    'success': True,
                    'initial_analysis': shared_analysis,
                    'updated_analysis': updated_analysis,
                    'players_updated': len(players_to_update),
                    'pairs_improved': self._count_improved_pairs(shared_analysis, updated_analysis)
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to collect additional match history',
                    'initial_analysis': shared_analysis
                }
        else:
            return {
                'success': True,
                'message': 'No additional data collection needed',
                'analysis': shared_analysis
            }
    
    def _count_improved_pairs(self, initial_analysis: Dict, updated_analysis: Dict) -> int:
        """Count how many pairs improved their shared match count."""
        improved = 0
        
        initial_shared = initial_analysis.get('shared_analysis', {})
        updated_shared = updated_analysis.get('shared_analysis', {})
        
        for pair in initial_shared:
            if pair in updated_shared:
                if updated_shared[pair]['shared_matches'] > initial_shared[pair]['shared_matches']:
                    improved += 1
        
        return improved