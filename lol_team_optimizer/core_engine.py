"""
Core Engine for League of Legends Team Optimizer.

This module consolidates business logic from CLI, notebook, and setup scripts
into a unified interface with intelligent defaults and comprehensive error handling.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import asdict

from .config import Config
from .data_manager import DataManager
from .riot_client import RiotAPIClient
from .synergy_manager import SynergyManager
from .performance_calculator import PerformanceCalculator
from .optimizer import OptimizationEngine, OptimizationResult
from .champion_data import ChampionDataManager
from .models import Player, TeamAssignment
from .migration import DataMigrator
from .match_manager import MatchManager
from .historical_analytics_engine import HistoricalAnalyticsEngine
from .champion_recommendation_engine import ChampionRecommendationEngine
from .baseline_manager import BaselineManager
from .analytics_cache_manager import AnalyticsCacheManager
from .statistical_analyzer import StatisticalAnalyzer
from .champion_synergy_analyzer import ChampionSynergyAnalyzer


class CoreEngine:
    """
    Centralized business logic engine for the team optimizer.
    
    Provides unified methods for player management, optimization, and analysis
    with intelligent defaults and comprehensive error handling.
    """
    
    def __init__(self):
        """Initialize the core engine with all required components."""
        self.logger = logging.getLogger(__name__)
        self.roles = ["top", "jungle", "middle", "support", "bottom"]
        
        # Check for migration needs before initializing
        self._check_and_handle_migration()
        
        # Initialize components with comprehensive error handling
        self._initialize_components()
        
        # Track system status
        self.system_status = self._get_system_status()
    
    def _initialize_components(self) -> None:
        """Initialize all system components with error handling."""
        try:
            self.config = Config()
            self.logger.info("Configuration loaded successfully")
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            raise RuntimeError(f"Configuration initialization failed: {e}")
        
        try:
            self.data_manager = DataManager(self.config)
            self.match_manager = MatchManager(self.config)
            self.logger.info("Data manager and match manager initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize data managers: {e}")
            raise RuntimeError(f"Data manager initialization failed: {e}")
        
        # Initialize API client with graceful degradation
        try:
            self.riot_client = RiotAPIClient(self.config)
            self.api_available = True
            self.logger.info("Riot API client initialized")
        except Exception as e:
            self.logger.warning(f"Riot API client initialization failed: {e}")
            self.riot_client = None
            self.api_available = False
        
        try:
            self.champion_data_manager = ChampionDataManager(self.config)
            self.performance_calculator = PerformanceCalculator(self.champion_data_manager)
            
            # Initialize synergy manager with match manager
            self.synergy_manager = SynergyManager(self.riot_client, self.config.cache_directory, self.match_manager)
            synergy_db = self.synergy_manager.get_synergy_database()
            
            self.optimizer = OptimizationEngine(self.performance_calculator, self.champion_data_manager, synergy_db)
            self.logger.info("Optimization engine initialized with synergy support")
        except Exception as e:
            self.logger.error(f"Failed to initialize optimization components: {e}")
            raise RuntimeError(f"Optimization engine initialization failed: {e}")
        
        # Initialize analytics engines
        try:
            self.analytics_cache_manager = AnalyticsCacheManager(self.config)
            self.baseline_manager = BaselineManager(self.config, self.match_manager)
            self.statistical_analyzer = StatisticalAnalyzer()
            self.champion_synergy_analyzer = ChampionSynergyAnalyzer(
                self.config, self.match_manager, self.baseline_manager, self.statistical_analyzer
            )
            self.historical_analytics_engine = HistoricalAnalyticsEngine(
                self.config, self.match_manager, self.baseline_manager, self.analytics_cache_manager
            )
            self.champion_recommendation_engine = ChampionRecommendationEngine(
                self.config, self.historical_analytics_engine, self.champion_data_manager, self.baseline_manager
            )
            self.analytics_available = True
            self.logger.info("Analytics engines initialized successfully")
        except Exception as e:
            self.logger.warning(f"Failed to initialize analytics engines: {e}")
            # Set to None for graceful degradation
            self.analytics_cache_manager = None
            self.baseline_manager = None
            self.statistical_analyzer = None
            self.champion_synergy_analyzer = None
            self.historical_analytics_engine = None
            self.champion_recommendation_engine = None
            self.analytics_available = False
    
    def _check_and_handle_migration(self) -> None:
        """Check if migration is needed and handle it automatically."""
        try:
            # Initialize config first for migration check
            config = Config()
            migrator = DataMigrator(config)
            
            # Check migration status
            migration_status = migrator.check_migration_needed()
            
            if migration_status['migration_needed']:
                self.logger.warning("Data migration needed for compatibility with streamlined interface")
                
                # For now, just log the need for migration
                # In a production system, you might want to:
                # 1. Automatically migrate if safe
                # 2. Prompt user for migration
                # 3. Provide clear instructions
                
                self.logger.info("Run 'python -m lol_team_optimizer.migration_cli check' for details")
                self.logger.info("Run 'python -m lol_team_optimizer.migration_cli migrate' to migrate")
                
                # Store migration status for later reference
                self._migration_status = migration_status
            else:
                self._migration_status = None
                
        except Exception as e:
            self.logger.warning(f"Could not check migration status: {e}")
            self._migration_status = None
    
    def get_migration_status(self) -> Optional[Dict[str, Any]]:
        """Get the current migration status."""
        return getattr(self, '_migration_status', None)
    
    def get_match_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics about stored match data.
        
        Returns:
            Dictionary with match statistics and insights
        """
        return self.match_manager.get_match_statistics()
    
    def get_matches_with_team_members(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get matches that contain multiple players from our database.
        
        Args:
            limit: Maximum number of matches to return
            
        Returns:
            List of match summaries with team member information
        """
        # Get all player PUUIDs
        players = self.data_manager.load_player_data()
        puuids = {p.puuid for p in players if p.puuid}
        
        if not puuids:
            return []
        
        # Get matches with multiple team members
        matches = self.match_manager.get_matches_with_multiple_players(puuids, limit)
        
        # Create summaries
        match_summaries = []
        for match in matches:
            known_players = match.get_known_players(puuids)
            
            # Get player names
            puuid_to_name = {p.puuid: p.name for p in players}
            player_names = [puuid_to_name.get(p.puuid, p.summoner_name) for p in known_players]
            
            summary = {
                'match_id': match.match_id,
                'game_creation': match.game_creation_datetime.isoformat(),
                'game_duration_minutes': match.game_duration // 60,
                'queue_id': match.queue_id,
                'known_players': player_names,
                'known_player_count': len(known_players),
                'winning_team': match.winning_team,
                'team_members_won': any(p.win for p in known_players)
            }
            match_summaries.append(summary)
        
        return match_summaries
    
    def cleanup_old_match_data(self, days: int = 90) -> Dict[str, int]:
        """
        Clean up old match data to save storage space.
        
        Args:
            days: Number of days of match history to keep
            
        Returns:
            Dictionary with cleanup statistics
        """
        matches_removed = self.match_manager.cleanup_old_matches(days)
        
        return {
            'matches_removed': matches_removed,
            'days_kept': days,
            'cleanup_date': datetime.now().isoformat()
        }
    
    def rebuild_match_index(self) -> Dict[str, Any]:
        """
        Rebuild the match index for better performance.
        
        Returns:
            Dictionary with rebuild statistics
        """
        self.match_manager.rebuild_index()
        stats = self.match_manager.get_match_statistics()
        
        return {
            'total_matches': stats['total_matches'],
            'players_indexed': stats['total_players_indexed'],
            'rebuild_date': datetime.now().isoformat()
        }
    
    def historical_match_scraping(self, player_names: Optional[List[str]] = None, 
                                max_matches_per_player: int = 500,
                                force_restart: bool = False) -> Dict[str, Any]:
        """
        Perform historical match scraping with extraction tracking.
        
        Args:
            player_names: List of player names to scrape (None for all players)
            max_matches_per_player: Maximum matches to fetch per player
            force_restart: If True, restart extraction from beginning
            
        Returns:
            Dictionary with scraping results and statistics
        """
        if not self.api_available:
            return {"error": "API unavailable - cannot perform historical scraping"}
        
        # Get players to scrape
        if player_names:
            players_to_scrape = []
            for name in player_names:
                player = self.data_manager.get_player_by_name(name)
                if player and player.puuid:
                    players_to_scrape.append(player)
        else:
            all_players = self.data_manager.load_player_data()
            players_to_scrape = [p for p in all_players if p.puuid]
        
        if not players_to_scrape:
            return {"error": "No players with valid PUUIDs found"}
        
        results = {
            'players_processed': 0,
            'total_new_matches': 0,
            'total_duplicates_skipped': 0,
            'player_results': {},
            'extraction_progress': {},
            'errors': [],
            'start_time': datetime.now().isoformat()
        }
        
        self.logger.info(f"Starting historical match scraping for {len(players_to_scrape)} players")
        
        for player in players_to_scrape:
            try:
                self.logger.info(f"Historical scraping for {player.name}")
                
                # Reset extraction if requested
                if force_restart:
                    self.match_manager.reset_player_extraction(player.puuid)
                
                # Get current extraction info
                extraction_info = self.match_manager.get_player_extraction_info(player.puuid)
                
                if extraction_info['extraction_complete']:
                    self.logger.info(f"Extraction already complete for {player.name}")
                    results['player_results'][player.name] = {
                        'status': 'already_complete',
                        'matches_extracted': extraction_info['matches_extracted'],
                        'total_available': extraction_info['total_matches_available']
                    }
                    results['players_processed'] += 1
                    continue
                
                # Perform incremental extraction
                total_new_matches = 0
                batch_size = 20
                
                while not extraction_info['extraction_complete'] and total_new_matches < max_matches_per_player:
                    # Get next batch to extract
                    start_index, count = self.match_manager.get_next_extraction_batch(player.puuid, batch_size)
                    
                    if count == 0:
                        break
                    
                    try:
                        # Fetch match IDs for this batch
                        batch_match_ids = self.riot_client.get_match_history(
                            player.puuid, 
                            count=count, 
                            start=start_index
                        )
                        
                        if not batch_match_ids:
                            # No more matches available
                            self.match_manager.mark_extraction_complete(player.puuid)
                            break
                        
                        # Filter out matches we already have
                        new_match_ids = [mid for mid in batch_match_ids if not self.match_manager.get_match(mid)]
                        
                        # Fetch detailed match data
                        new_matches = []
                        for match_id in new_match_ids:
                            try:
                                match_detail = self.riot_client.get_match_details(match_id)
                                if match_detail:
                                    new_matches.append(match_detail)
                            except Exception as e:
                                self.logger.warning(f"Failed to fetch match {match_id}: {e}")
                                continue
                        
                        # Store new matches
                        if new_matches:
                            new_count, duplicate_count = self.match_manager.store_matches_batch(new_matches)
                            total_new_matches += new_count
                            results['total_new_matches'] += new_count
                            results['total_duplicates_skipped'] += duplicate_count
                        
                        # Update extraction progress
                        self.match_manager.update_player_extraction_progress(
                            player.puuid, 
                            len(batch_match_ids),
                            None  # We don't know total available yet
                        )
                        
                        # Get updated extraction info
                        extraction_info = self.match_manager.get_player_extraction_info(player.puuid)
                        
                        # Rate limiting
                        time.sleep(1)
                        
                        self.logger.info(f"Extracted batch for {player.name}: {len(batch_match_ids)} IDs, {len(new_matches)} new matches")
                        
                    except Exception as e:
                        self.logger.warning(f"Failed to fetch batch for {player.name} at index {start_index}: {e}")
                        break
                
                # Update player performance with new data if we got matches
                if total_new_matches > 0:
                    updated_matches = self.match_manager.get_matches_for_player(player.puuid, limit=100)
                    performance_cache = self._calculate_performance_from_stored_matches(player, updated_matches)
                    if performance_cache:
                        player.performance_cache = performance_cache
                        self.data_manager.update_player(player)
                
                # Get final extraction info
                final_extraction_info = self.match_manager.get_player_extraction_info(player.puuid)
                
                results['player_results'][player.name] = {
                    'status': 'completed' if final_extraction_info['extraction_complete'] else 'partial',
                    'new_matches_stored': total_new_matches,
                    'total_matches_extracted': final_extraction_info['matches_extracted'],
                    'extraction_progress': final_extraction_info['extraction_progress'],
                    'extraction_complete': final_extraction_info['extraction_complete']
                }
                
                results['extraction_progress'][player.name] = final_extraction_info
                results['players_processed'] += 1
                
            except Exception as e:
                error_msg = f"Error in historical scraping for {player.name}: {e}"
                self.logger.error(error_msg)
                results['errors'].append(error_msg)
        
        results['end_time'] = datetime.now().isoformat()
        results['duration_minutes'] = (datetime.fromisoformat(results['end_time']) - 
                                     datetime.fromisoformat(results['start_time'])).total_seconds() / 60
        
        # Update system status
        self.system_status = self._get_system_status()
        
        self.logger.info(f"Historical scraping completed: {results['total_new_matches']} new matches stored")
        return results
    
    def comprehensive_match_scraping(self, player_names: Optional[List[str]] = None, 
                                   max_matches_per_player: int = 200) -> Dict[str, Any]:
        """
        Perform comprehensive match scraping for better analysis data.
        
        Args:
            player_names: List of player names to scrape (None for all players)
            max_matches_per_player: Maximum matches to fetch per player
            
        Returns:
            Dictionary with scraping results and statistics
        """
        if not self.api_available:
            return {"error": "API unavailable - cannot perform comprehensive scraping"}
        
        # Get players to scrape
        if player_names:
            players_to_scrape = []
            for name in player_names:
                player = self.data_manager.get_player_by_name(name)
                if player and player.puuid:
                    players_to_scrape.append(player)
        else:
            all_players = self.data_manager.load_player_data()
            players_to_scrape = [p for p in all_players if p.puuid]
        
        if not players_to_scrape:
            return {"error": "No players with valid PUUIDs found"}
        
        results = {
            'players_processed': 0,
            'total_new_matches': 0,
            'total_duplicates_skipped': 0,
            'player_results': {},
            'errors': [],
            'start_time': datetime.now().isoformat()
        }
        
        self.logger.info(f"Starting comprehensive match scraping for {len(players_to_scrape)} players")
        
        for player in players_to_scrape:
            try:
                self.logger.info(f"Scraping comprehensive match history for {player.name}")
                
                # Get existing match count
                existing_matches = self.match_manager.get_matches_for_player(player.puuid)
                existing_count = len(existing_matches)
                
                # Fetch comprehensive match history
                all_match_ids = []
                batch_size = 20
                
                for start_index in range(0, max_matches_per_player, batch_size):
                    try:
                        batch_match_ids = self.riot_client.get_match_history(
                            player.puuid, 
                            count=batch_size, 
                            start=start_index
                        )
                        
                        if not batch_match_ids:
                            break  # No more matches available
                        
                        all_match_ids.extend(batch_match_ids)
                        
                        # Rate limiting between batches
                        if start_index > 0:
                            time.sleep(1)
                            
                    except Exception as e:
                        self.logger.warning(f"Failed to fetch match batch for {player.name} at index {start_index}: {e}")
                        break
                
                self.logger.info(f"Found {len(all_match_ids)} total match IDs for {player.name}")
                
                # Filter out matches we already have
                new_match_ids = [mid for mid in all_match_ids if not self.match_manager.get_match(mid)]
                
                if new_match_ids:
                    self.logger.info(f"Fetching {len(new_match_ids)} new matches for {player.name}")
                    
                    # Fetch detailed match data with careful rate limiting
                    new_matches = []
                    for i, match_id in enumerate(new_match_ids):
                        try:
                            match_detail = self.riot_client.get_match_details(match_id)
                            if match_detail:
                                new_matches.append(match_detail)
                            
                            # Progressive rate limiting (slower for larger batches)
                            if (i + 1) % 5 == 0:
                                time.sleep(0.5)
                            if (i + 1) % 20 == 0:
                                time.sleep(2)
                                
                        except Exception as e:
                            self.logger.warning(f"Failed to fetch match {match_id} for {player.name}: {e}")
                            continue
                    
                    # Store new matches
                    if new_matches:
                        new_count, duplicate_count = self.match_manager.store_matches_batch(new_matches)
                        
                        results['total_new_matches'] += new_count
                        results['total_duplicates_skipped'] += duplicate_count
                        
                        # Update player performance with new data
                        updated_matches = self.match_manager.get_matches_for_player(player.puuid, limit=100)
                        performance_cache = self._calculate_performance_from_stored_matches(player, updated_matches)
                        if performance_cache:
                            player.performance_cache = performance_cache
                            self.data_manager.update_player(player)
                        
                        results['player_results'][player.name] = {
                            'existing_matches': existing_count,
                            'new_matches_found': len(new_match_ids),
                            'new_matches_stored': new_count,
                            'duplicates_skipped': duplicate_count,
                            'total_matches_after': len(updated_matches)
                        }
                    else:
                        results['player_results'][player.name] = {
                            'existing_matches': existing_count,
                            'new_matches_found': 0,
                            'new_matches_stored': 0,
                            'duplicates_skipped': 0,
                            'total_matches_after': existing_count
                        }
                else:
                    results['player_results'][player.name] = {
                        'existing_matches': existing_count,
                        'new_matches_found': 0,
                        'new_matches_stored': 0,
                        'duplicates_skipped': 0,
                        'total_matches_after': existing_count,
                        'note': 'All matches already stored'
                    }
                
                results['players_processed'] += 1
                
            except Exception as e:
                error_msg = f"Error scraping {player.name}: {e}"
                self.logger.error(error_msg)
                results['errors'].append(error_msg)
        
        results['end_time'] = datetime.now().isoformat()
        results['duration_minutes'] = (datetime.fromisoformat(results['end_time']) - 
                                     datetime.fromisoformat(results['start_time'])).total_seconds() / 60
        
        # Update system status
        self.system_status = self._get_system_status()
        
        self.logger.info(f"Comprehensive scraping completed: {results['total_new_matches']} new matches stored")
        return results
    
    def update_synergies_from_stored_matches(self) -> Dict[str, Any]:
        """
        Update player synergies based on stored match data.
        
        Returns:
            Dictionary with synergy update results
        """
        try:
            players = self.data_manager.load_player_data()
            players_with_puuid = [p for p in players if p.puuid]
            
            if len(players_with_puuid) < 2:
                return {"error": "Need at least 2 players with PUUIDs to calculate synergies"}
            
            # Calculate synergies from stored matches
            self.synergy_manager.calculate_synergies_from_stored_matches(players_with_puuid)
            
            # Get updated synergy statistics
            synergy_db = self.synergy_manager.get_synergy_database()
            synergy_count = len(synergy_db.synergies)
            
            return {
                'success': True,
                'players_analyzed': len(players_with_puuid),
                'synergy_pairs_updated': synergy_count,
                'last_updated': synergy_db.last_updated.isoformat() if synergy_db.last_updated else None,
                'update_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error updating synergies from stored matches: {e}")
            return {"error": f"Failed to update synergies: {e}"}
    
    def comprehensive_analysis_from_stored_data(self) -> Dict[str, Any]:
        """
        Perform comprehensive analysis using only stored match data.
        
        Returns:
            Dictionary with comprehensive analysis results
        """
        try:
            analysis_start = datetime.now()
            
            # Load players
            players = self.data_manager.load_player_data()
            players_with_data = [p for p in players if p.puuid]
            
            if not players_with_data:
                return {"error": "No players with match data found"}
            
            results = {
                'analysis_start': analysis_start.isoformat(),
                'players_analyzed': len(players_with_data),
                'match_statistics': {},
                'performance_updates': {},
                'synergy_updates': {},
                'team_analysis': {}
            }
            
            # Get match statistics
            match_stats = self.match_manager.get_match_statistics()
            results['match_statistics'] = match_stats
            
            # Update performance data for all players using stored matches
            performance_updates = 0
            for player in players_with_data:
                stored_matches = self.match_manager.get_matches_for_player(player.puuid, limit=100)
                if stored_matches:
                    old_cache_size = len(player.performance_cache)
                    performance_cache = self._calculate_performance_from_stored_matches(player, stored_matches)
                    if performance_cache:
                        player.performance_cache = performance_cache
                        self.data_manager.update_player(player)
                        performance_updates += 1
                        
                        results['performance_updates'][player.name] = {
                            'matches_analyzed': len(stored_matches),
                            'roles_with_data': len(performance_cache),
                            'previous_roles': old_cache_size
                        }
            
            # Update synergies from stored matches
            synergy_result = self.update_synergies_from_stored_matches()
            results['synergy_updates'] = synergy_result
            
            # Analyze team matches
            puuids = {p.puuid for p in players_with_data}
            team_matches = self.match_manager.get_matches_with_multiple_players(puuids, limit=50)
            
            # Team match analysis
            team_wins = sum(1 for match in team_matches 
                          if any(p.win for p in match.get_known_players(puuids)))
            team_games = len(team_matches)
            
            results['team_analysis'] = {
                'total_team_matches': team_games,
                'team_wins': team_wins,
                'team_win_rate': team_wins / team_games if team_games > 0 else 0,
                'players_in_team_matches': len(puuids)
            }
            
            # Calculate analysis duration
            analysis_end = datetime.now()
            results['analysis_end'] = analysis_end.isoformat()
            results['analysis_duration_seconds'] = (analysis_end - analysis_start).total_seconds()
            
            # Update system status
            self.system_status = self._get_system_status()
            
            self.logger.info(f"Comprehensive analysis completed in {results['analysis_duration_seconds']:.2f} seconds")
            self.logger.info(f"Updated performance for {performance_updates} players using stored match data")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error in comprehensive analysis: {e}")
            return {"error": f"Analysis failed: {e}"}
    
    def get_extraction_status(self) -> Dict[str, Any]:
        """
        Get comprehensive extraction status for all players.
        
        Returns:
            Dictionary with extraction status and progress information
        """
        try:
            # Get extraction info from match manager
            extraction_info = self.match_manager.get_all_extraction_info()
            
            # Add player names to the extraction info
            players = self.data_manager.load_player_data()
            puuid_to_name = {p.puuid: p.name for p in players if p.puuid}
            
            # Enhance player details with names
            enhanced_players = {}
            for puuid, details in extraction_info['players'].items():
                player_name = puuid_to_name.get(puuid, f"Unknown ({puuid[:8]}...)")
                enhanced_players[player_name] = {
                    **details,
                    'player_name': player_name
                }
            
            return {
                'summary': extraction_info['summary'],
                'players': enhanced_players,
                'status_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting extraction status: {e}")
            return {"error": f"Failed to get extraction status: {e}"}
    
    def reset_player_extraction(self, player_name: str) -> Dict[str, Any]:
        """
        Reset extraction progress for a specific player.
        
        Args:
            player_name: Name of the player to reset
            
        Returns:
            Dictionary with reset results
        """
        try:
            player = self.data_manager.get_player_by_name(player_name)
            if not player or not player.puuid:
                return {"error": f"Player {player_name} not found or has no PUUID"}
            
            self.match_manager.reset_player_extraction(player.puuid)
            
            return {
                'success': True,
                'player_name': player_name,
                'puuid': player.puuid,
                'reset_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error resetting extraction for {player_name}: {e}")
            return {"error": f"Failed to reset extraction: {e}"}
    
    def _get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status information."""
        try:
            players = self.data_manager.load_player_data()
            player_count = len(players)
            
            # Check data completeness
            players_with_api_data = sum(1 for p in players if p.performance_cache or p.champion_masteries)
            players_with_preferences = sum(1 for p in players if any(pref != 3 for pref in p.role_preferences.values()))
            
            # Get match statistics
            match_stats = self.match_manager.get_match_statistics()
            
            # Get analytics status
            analytics_status = {
                'available': self.analytics_available,
                'components_online': 0,
                'total_components': 6
            }
            
            if self.analytics_available:
                components = [
                    self.historical_analytics_engine,
                    self.champion_recommendation_engine,
                    self.baseline_manager,
                    self.analytics_cache_manager,
                    self.statistical_analyzer,
                    self.champion_synergy_analyzer
                ]
                analytics_status['components_online'] = sum(1 for c in components if c is not None)
            
            return {
                'api_available': self.api_available,
                'analytics_available': self.analytics_available,
                'player_count': player_count,
                'players_with_api_data': players_with_api_data,
                'players_with_preferences': players_with_preferences,
                'ready_for_optimization': player_count >= 5,
                'ready_for_analytics': player_count >= 2 and match_stats['total_matches'] > 0,
                'champion_data_loaded': len(self.champion_data_manager.champions) > 0,
                'match_data': {
                    'total_matches': match_stats['total_matches'],
                    'players_with_matches': match_stats['total_players_indexed'],
                    'oldest_match': match_stats['oldest_match'],
                    'newest_match': match_stats['newest_match'],
                    'storage_size_mb': match_stats['storage_file_size_mb']
                },
                'analytics_status': analytics_status,
                'last_updated': datetime.now()
            }
        except Exception as e:
            self.logger.error(f"Error getting system status: {e}")
            return {
                'api_available': self.api_available,
                'analytics_available': getattr(self, 'analytics_available', False),
                'error': str(e),
                'last_updated': datetime.now()
            }
    
    def add_player_with_data(self, name: str, riot_id: str, auto_fetch: bool = True) -> Tuple[bool, str, Optional[Player]]:
        """
        Add a player with automatic data fetching and intelligent defaults.
        
        Args:
            name: Player display name
            riot_id: Riot ID in format gameName#tagLine
            auto_fetch: Whether to automatically fetch API data
            
        Returns:
            Tuple of (success, message, player_object)
        """
        try:
            # Validate input
            if not name or not riot_id:
                return False, "Player name and Riot ID are required", None
            
            if '#' not in riot_id:
                return False, "Riot ID must include tag (e.g., PlayerName#NA1)", None
            
            # Check if player already exists
            existing_player = self.data_manager.get_player_by_name(name)
            if existing_player:
                return False, f"Player '{name}' already exists", None
            
            # Validate Riot ID if API is available
            puuid = ''
            summoner_name = riot_id
            
            if self.api_available and auto_fetch:
                try:
                    summoner_data = self.riot_client.get_summoner_data(riot_id)
                    if summoner_data:
                        puuid = summoner_data.get('puuid', '')
                        game_name = summoner_data.get('gameName', riot_id.split('#')[0])
                        tag_line = summoner_data.get('tagLine', riot_id.split('#')[1])
                        summoner_name = f"{game_name}#{tag_line}"
                    else:
                        return False, f"Riot ID '{riot_id}' not found", None
                except Exception as e:
                    self.logger.warning(f"API validation failed for {riot_id}: {e}")
                    if "404" in str(e) or "not found" in str(e).lower():
                        return False, f"Riot ID '{riot_id}' not found", None
                    # Continue with offline mode for other errors
            
            # Create player with intelligent default preferences
            default_preferences = self._generate_intelligent_default_preferences()
            
            player = Player(
                name=name,
                summoner_name=summoner_name,
                puuid=puuid,
                role_preferences=default_preferences
            )
            
            # Fetch API data first if available and requested
            api_data_fetched = False
            if self.api_available and auto_fetch and puuid:
                try:
                    api_data_fetched = self._fetch_player_api_data_with_caching(player)
                    
                    # If we got performance data, calculate intelligent preferences
                    if api_data_fetched and player.performance_cache:
                        intelligent_prefs = self._calculate_preferences_from_performance(player)
                        if intelligent_prefs:
                            player.role_preferences = intelligent_prefs
                            self.logger.info(f"Applied intelligent preferences for {name} based on performance data")
                        
                except Exception as e:
                    self.logger.warning(f"Failed to fetch API data for {name}: {e}")
            
            # Save player
            players = self.data_manager.load_player_data()
            players.append(player)
            self.data_manager.save_player_data(players)
            
            # Update system status
            self.system_status = self._get_system_status()
            
            success_msg = f"Player '{name}' added successfully"
            if api_data_fetched:
                success_msg += " with API data and intelligent preferences"
            elif not self.api_available:
                success_msg += " (offline mode - using default preferences)"
            else:
                success_msg += " (API data unavailable - using default preferences)"
            
            return True, success_msg, player
            
        except Exception as e:
            self.logger.error(f"Error adding player {name}: {e}")
            return False, f"Error adding player: {e}", None
    
    def _generate_intelligent_default_preferences(self) -> Dict[str, int]:
        """
        Generate intelligent default preferences based on role popularity and balance.
        
        Returns:
            Dictionary of role preferences with slight variations from neutral
        """
        # Start with neutral preferences
        default_prefs = {role: 3 for role in self.roles}
        
        # Add slight variations to encourage role diversity
        # These are based on general role popularity and learning curve
        role_adjustments = {
            "support": 1,    # Slightly higher - often needed role
            "jungle": -1,    # Slightly lower - complex role for beginners
            "middle": 0,     # Neutral - popular but competitive
            "top": 0,        # Neutral - good for beginners
            "bottom": 0      # Neutral - popular role
        }
        
        for role, adjustment in role_adjustments.items():
            default_prefs[role] = max(1, min(5, default_prefs[role] + adjustment))
        
        return default_prefs
    
    def _fetch_player_api_data_with_caching(self, player: Player) -> bool:
        """
        Fetch API data for a player with intelligent caching strategies.
        
        Args:
            player: Player object to update
            
        Returns:
            True if data was successfully fetched or retrieved from cache
        """
        if not self.api_available or not player.puuid:
            return False
        
        try:
            success = False
            
            # Check cache first for champion mastery data
            mastery_cache_key = f"mastery_{player.puuid}"
            cached_masteries = self.data_manager.get_cached_data(mastery_cache_key)
            
            if cached_masteries:
                self.logger.info(f"Using cached champion mastery data for {player.name}")
                player.champion_masteries = self._process_champion_masteries(cached_masteries)
                success = True
            else:
                # Fetch fresh champion mastery data
                try:
                    masteries = self.riot_client.get_all_champion_masteries(player.puuid)
                    if masteries:
                        # Cache the raw data for future use
                        self.data_manager.cache_api_data(masteries, mastery_cache_key, ttl_hours=24)
                        player.champion_masteries = self._process_champion_masteries(masteries)
                        success = True
                        self.logger.info(f"Fetched and cached champion mastery data for {player.name}")
                except Exception as e:
                    self.logger.warning(f"Failed to fetch champion mastery for {player.name}: {e}")
            
            # Check for existing match data in centralized storage
            existing_matches = self.match_manager.get_matches_for_player(player.puuid, limit=20)
            
            # Determine if we need to fetch fresh data
            needs_fresh_data = True
            if existing_matches:
                # Check if we have recent matches (within last 6 hours)
                latest_match = existing_matches[0]  # Already sorted by newest first
                six_hours_ago = datetime.now() - timedelta(hours=6)
                if latest_match.stored_at and latest_match.stored_at > six_hours_ago:
                    needs_fresh_data = False
                    self.logger.info(f"Using existing match data for {player.name} ({len(existing_matches)} matches)")
            
            if needs_fresh_data:
                # Fetch more comprehensive match data
                try:
                    # Fetch more matches for better analysis (up to 100 total)
                    all_match_ids = []
                    
                    # Fetch in batches to respect API limits
                    for start_index in range(0, 100, 20):  # Fetch 100 matches in batches of 20
                        batch_match_ids = self.riot_client.get_match_history(
                            player.puuid, 
                            count=20, 
                            start=start_index
                        )
                        if not batch_match_ids:
                            break  # No more matches available
                        
                        all_match_ids.extend(batch_match_ids)
                        
                        # Small delay between batches to respect rate limits
                        if start_index > 0:
                            time.sleep(0.5)
                    
                    self.logger.info(f"Found {len(all_match_ids)} total matches for {player.name}")
                    
                    if all_match_ids:
                        # Filter out matches we already have
                        new_match_ids = [mid for mid in all_match_ids if not self.match_manager.get_match(mid)]
                        self.logger.info(f"Need to fetch {len(new_match_ids)} new matches for {player.name}")
                        
                        # Fetch detailed match data with rate limiting
                        new_matches = []
                        for i, match_id in enumerate(new_match_ids):
                            try:
                                match_detail = self.riot_client.get_match_details(match_id)
                                if match_detail:
                                    new_matches.append(match_detail)
                                
                                # Rate limiting: pause every 10 requests
                                if (i + 1) % 10 == 0:
                                    time.sleep(1)
                                    
                            except Exception as e:
                                self.logger.warning(f"Failed to fetch match {match_id}: {e}")
                                continue
                        
                        if new_matches:
                            # Store matches in centralized storage with deduplication
                            new_count, duplicate_count = self.match_manager.store_matches_batch(new_matches)
                            self.logger.info(f"Stored {new_count} new matches for {player.name}, skipped {duplicate_count} duplicates")
                            
                            # Get updated match list (more matches for better analysis)
                            existing_matches = self.match_manager.get_matches_for_player(player.puuid, limit=50)
                        
                except Exception as e:
                    self.logger.warning(f"Failed to fetch match data for {player.name}: {e}")
            
            # Calculate performance from stored matches (use more matches for better analysis)
            all_stored_matches = self.match_manager.get_matches_for_player(player.puuid, limit=100)
            if all_stored_matches:
                performance_cache = self._calculate_performance_from_stored_matches(player, all_stored_matches)
                if performance_cache:
                    player.performance_cache = performance_cache
                    success = True
                    self.logger.info(f"Calculated performance from {len(all_stored_matches)} stored matches for {player.name}")
            
            # Update last updated timestamp if we got any data
            if success:
                player.last_updated = datetime.now()
                self.data_manager.update_player(player)
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error fetching API data for {player.name}: {e}")
            return False
    
    def _process_champion_masteries(self, raw_masteries: List[Dict]) -> Dict[int, Any]:
        """
        Process raw champion mastery data into ChampionMastery objects.
        
        Args:
            raw_masteries: Raw mastery data from API
            
        Returns:
            Dictionary of champion_id -> ChampionMastery objects
        """
        from .models import ChampionMastery
        
        processed_masteries = {}
        
        for mastery_data in raw_masteries:
            try:
                champion_id = mastery_data.get('championId')
                if not champion_id:
                    continue
                
                # Get champion name from champion data manager
                champion_name = ""
                champion_info = None
                if self.champion_data_manager:
                    champion_info = self.champion_data_manager.get_champion_info(champion_id)
                    if champion_info:
                        champion_name = champion_info.name
                
                # Determine primary roles for this champion
                primary_roles = []
                if champion_info and champion_info.tags:
                    # Map champion tags to roles
                    tag_to_role = {
                        'Tank': ['top', 'support'],
                        'Fighter': ['top', 'jungle'],
                        'Assassin': ['middle', 'jungle'],
                        'Mage': ['middle', 'support'],
                        'Marksman': ['bottom'],
                        'Support': ['support']
                    }
                    
                    for tag in champion_info.tags:
                        if tag in tag_to_role:
                            primary_roles.extend(tag_to_role[tag])
                    
                    # Remove duplicates and ensure we have at least one role
                    primary_roles = list(set(primary_roles))
                
                if not primary_roles:
                    primary_roles = ['middle']  # Default fallback
                
                mastery = ChampionMastery(
                    champion_id=champion_id,
                    champion_name=champion_name,
                    mastery_level=mastery_data.get('championLevel', 0),
                    mastery_points=mastery_data.get('championPoints', 0),
                    chest_granted=mastery_data.get('chestGranted', False),
                    tokens_earned=mastery_data.get('tokensEarned', 0),
                    primary_roles=primary_roles,
                    last_play_time=datetime.fromtimestamp(mastery_data.get('lastPlayTime', 0) / 1000) if mastery_data.get('lastPlayTime') else None
                )
                
                processed_masteries[champion_id] = mastery
                
            except Exception as e:
                self.logger.warning(f"Failed to process mastery data for champion {mastery_data.get('championId', 'unknown')}: {e}")
                continue
        
        return processed_masteries
    
    def _calculate_performance_from_stored_matches(self, player: Player, matches: List['Match']) -> Dict[str, Dict]:
        """
        Calculate performance metrics from stored Match objects.
        
        Args:
            player: Player object
            matches: List of Match objects from centralized storage
            
        Returns:
            Dictionary of role -> performance data
        """
        from .models import Match
        
        performance_cache = {}
        
        for role in self.roles:
            try:
                role_performance = self._calculate_role_performance_from_matches(matches, player.puuid, role)
                if role_performance and role_performance.get('matches_played', 0) > 0:
                    performance_cache[role] = role_performance
            except Exception as e:
                self.logger.warning(f"Failed to calculate {role} performance for {player.name}: {e}")
                continue
        
        return performance_cache
    
    def _calculate_role_performance_from_matches(self, matches: List['Match'], puuid: str, role: str) -> Optional[Dict[str, Any]]:
        """
        Calculate performance metrics for a specific role from Match objects.
        
        Args:
            matches: List of Match objects
            puuid: Player's PUUID
            role: Role to calculate performance for
            
        Returns:
            Dictionary with performance metrics or None
        """
        from .models import Match
        
        # Map our role names to Riot's position names
        role_mapping = {
            'top': ['TOP', 'SOLO'],
            'jungle': ['JUNGLE', 'NONE'],  # Jungle often shows as NONE
            'middle': ['MIDDLE', 'SOLO'],
            'support': ['UTILITY', 'SUPPORT'],
            'bottom': ['BOTTOM', 'DUO_CARRY']
        }
        
        expected_positions = role_mapping.get(role, [])
        if not expected_positions:
            return None
        
        # Filter matches where player played this role
        role_matches = []
        for match in matches:
            participant = match.get_participant_by_puuid(puuid)
            if participant and (
                participant.individual_position in expected_positions or
                participant.lane in expected_positions or
                (role == 'jungle' and participant.neutral_minions_killed > participant.total_minions_killed)
            ):
                role_matches.append((match, participant))
        
        if not role_matches:
            return None
        
        # Calculate aggregated statistics
        total_games = len(role_matches)
        wins = sum(1 for _, participant in role_matches if participant.win)
        total_kills = sum(participant.kills for _, participant in role_matches)
        total_deaths = sum(participant.deaths for _, participant in role_matches)
        total_assists = sum(participant.assists for _, participant in role_matches)
        total_cs = sum(participant.cs_total for _, participant in role_matches)
        total_vision = sum(participant.vision_score for _, participant in role_matches)
        total_damage = sum(participant.total_damage_dealt_to_champions for _, participant in role_matches)
        total_duration = sum(match.game_duration for match, _ in role_matches)
        
        # Calculate averages and ratios
        win_rate = wins / total_games if total_games > 0 else 0.0
        avg_kda = (total_kills + total_assists) / max(total_deaths, 1)
        avg_cs_per_min = (total_cs / (total_duration / 60)) if total_duration > 0 else 0.0
        avg_vision_score = total_vision / total_games if total_games > 0 else 0.0
        avg_damage_per_min = (total_damage / (total_duration / 60)) if total_duration > 0 else 0.0
        
        # Calculate recent form (last 10 games vs previous games)
        recent_form = 0.0
        if total_games >= 6:  # Need at least 6 games to calculate form
            recent_matches = role_matches[:min(10, total_games // 2)]
            older_matches = role_matches[len(recent_matches):]
            
            if recent_matches and older_matches:
                recent_wr = sum(1 for _, p in recent_matches if p.win) / len(recent_matches)
                older_wr = sum(1 for _, p in older_matches if p.win) / len(older_matches)
                recent_form = recent_wr - older_wr  # -1 to 1 scale
        
        return {
            'matches_played': total_games,
            'win_rate': win_rate,
            'avg_kda': avg_kda,
            'avg_cs_per_min': avg_cs_per_min,
            'avg_vision_score': avg_vision_score,
            'avg_damage_per_min': avg_damage_per_min,
            'recent_form': max(-1.0, min(1.0, recent_form)),
            'total_kills': total_kills,
            'total_deaths': total_deaths,
            'total_assists': total_assists,
            'last_updated': datetime.now().isoformat()
        }
    
    def _calculate_performance_from_matches(self, player: Player, matches: List[Dict]) -> Dict[str, Dict]:
        """
        Calculate performance data from match history.
        
        Args:
            player: Player object
            matches: List of match detail objects
            
        Returns:
            Dictionary of role -> performance data
        """
        if not matches or not player.puuid:
            return {}
        
        performance_cache = {}
        
        for role in self.roles:
            try:
                role_performance = self.riot_client.calculate_role_performance(matches, player.puuid, role)
                if role_performance and role_performance.get('matches_played', 0) > 0:
                    performance_cache[role] = role_performance
            except Exception as e:
                self.logger.warning(f"Failed to calculate performance for {player.name} in {role}: {e}")
                continue
        
        return performance_cache
    
    def _fetch_player_api_data(self, player: Player) -> bool:
        """
        Legacy method - redirects to new caching method.
        
        Args:
            player: Player object to update
            
        Returns:
            True if data was successfully fetched
        """
        return self._fetch_player_api_data_with_caching(player)
    
    def optimize_team_smart(self, player_selection: Optional[List[str]] = None, 
                           auto_select: bool = True) -> Tuple[bool, str, Optional[OptimizationResult]]:
        """
        Smart team optimization with automatic player selection and graceful degradation.
        
        Args:
            player_selection: List of player names to include (None for auto-selection)
            auto_select: Whether to automatically select best players if not specified
            
        Returns:
            Tuple of (success, message, optimization_result)
        """
        try:
            players = self.data_manager.load_player_data()
            
            if len(players) < 2:
                return False, f"Need at least 2 players for optimization. Currently have {len(players)} players.", None
            
            # Handle player selection with intelligent defaults
            if player_selection:
                # Use specified players
                selected_players = []
                for name in player_selection:
                    player = self.data_manager.get_player_by_name(name)
                    if player:
                        selected_players.append(player)
                    else:
                        return False, f"Player '{name}' not found", None
            elif auto_select:
                # Auto-select best players based on data completeness and quality
                selected_players = self._auto_select_players_with_fallback(players)
            else:
                # Use all players
                selected_players = players
            
            if len(selected_players) < 2:
                return False, "Need at least 2 players for optimization", None
            
            # Ensure data completeness with graceful degradation
            self._ensure_player_data_completeness_with_fallback(selected_players)
            
            # Run optimization with error handling
            start_time = time.time()
            result = self.optimizer.optimize_team(selected_players)
            optimization_time = time.time() - start_time
            
            # Update result with timing and system information
            result.optimization_time = optimization_time
            
            # Generate success message with system status
            success_msg = self._generate_optimization_success_message(
                selected_players, optimization_time, result
            )
            
            return True, success_msg, result
            
        except Exception as e:
            self.logger.error(f"Optimization failed: {e}")
            # Try fallback optimization with minimal data
            fallback_result = self._attempt_fallback_optimization(players, player_selection)
            if fallback_result[0]:
                return fallback_result
            return False, f"Optimization failed: {e}", None
    
    def _auto_select_players_with_fallback(self, players: List[Player], max_players: int = 10) -> List[Player]:
        """
        Auto-select players with intelligent fallback when data is limited.
        
        Args:
            players: List of all available players
            max_players: Maximum number of players to select
            
        Returns:
            List of selected players
        """
        if not players:
            return []
        
        # First try the standard auto-selection
        selected = self._auto_select_players(players, max_players)
        
        # If we don't have enough players with good data, expand selection
        if len(selected) < min(5, len(players)):
            # Score all players with more lenient criteria
            player_scores = []
            
            for player in players:
                score = 1  # Base score for existing
                
                # Bonus for any API data
                if player.performance_cache or player.champion_masteries:
                    score += 2
                
                # Bonus for non-default preferences
                if any(pref != 3 for pref in player.role_preferences.values()):
                    score += 1
                
                # Bonus for recent activity (less strict)
                if player.last_updated and (datetime.now() - player.last_updated).days < 60:
                    score += 1
                
                player_scores.append((player, score))
            
            # Sort and select top players
            player_scores.sort(key=lambda x: x[1], reverse=True)
            selected = [player for player, score in player_scores[:max_players]]
        
        return selected
    
    def refresh_player_data(self, player_name: str, force_api_fetch: bool = False) -> Tuple[bool, str]:
        """
        Refresh data for a specific player with intelligent caching.
        
        Args:
            player_name: Name of player to refresh
            force_api_fetch: Whether to force fresh API data fetch
            
        Returns:
            Tuple of (success, message)
        """
        try:
            player = self.data_manager.get_player_by_name(player_name)
            if not player:
                return False, f"Player '{player_name}' not found"
            
            if not self.api_available:
                return False, "API unavailable - cannot refresh player data"
            
            if not player.puuid:
                return False, f"No PUUID available for {player_name} - cannot fetch API data"
            
            # Clear cache if forcing fresh fetch
            if force_api_fetch:
                mastery_cache_key = f"mastery_{player.puuid}"
                matches_cache_key = f"matches_{player.puuid}"
                
                # Remove cached data to force fresh fetch
                cache_file_mastery = self.data_manager.cache_dir / f"{mastery_cache_key}.json"
                cache_file_matches = self.data_manager.cache_dir / f"{matches_cache_key}.json"
                
                if cache_file_mastery.exists():
                    cache_file_mastery.unlink()
                if cache_file_matches.exists():
                    cache_file_matches.unlink()
            
            # Fetch fresh data
            success = self._fetch_player_api_data_with_caching(player)
            
            if success:
                # Recalculate preferences with new data
                new_prefs = self._calculate_preferences_from_performance(player)
                if new_prefs:
                    player.role_preferences = new_prefs
                
                # Update player in database
                self.data_manager.update_player(player)
                
                # Update system status
                self.system_status = self._get_system_status()
                
                return True, f"Successfully refreshed data for {player_name}"
            else:
                return False, f"Failed to fetch fresh data for {player_name}"
                
        except Exception as e:
            self.logger.error(f"Error refreshing data for {player_name}: {e}")
            return False, f"Error refreshing player data: {e}"
    
    def bulk_refresh_player_data(self, player_names: Optional[List[str]] = None, 
                               max_concurrent: int = 3) -> Dict[str, Tuple[bool, str]]:
        """
        Refresh data for multiple players with rate limiting and caching.
        
        Args:
            player_names: List of player names to refresh (None for all players)
            max_concurrent: Maximum concurrent API requests
            
        Returns:
            Dictionary of player_name -> (success, message)
        """
        if not self.api_available:
            return {"error": (False, "API unavailable - cannot refresh player data")}
        
        # Get players to refresh
        if player_names:
            players_to_refresh = []
            for name in player_names:
                player = self.data_manager.get_player_by_name(name)
                if player:
                    players_to_refresh.append(player)
        else:
            players_to_refresh = self.data_manager.load_player_data()
        
        if not players_to_refresh:
            return {"error": (False, "No players found")}
        
        results = {}
        
        # First, populate missing PUUIDs
        players_needing_puuid = [p for p in players_to_refresh if not p.puuid]
        if players_needing_puuid:
            self.logger.info(f"Populating PUUIDs for {len(players_needing_puuid)} players")
            for player in players_needing_puuid:
                try:
                    # Extract game name and tag line from summoner_name
                    if '#' in player.summoner_name:
                        game_name, tag_line = player.summoner_name.split('#', 1)
                        summoner_data = self.riot_client.get_summoner_data(player.summoner_name)
                        if summoner_data and summoner_data.get('puuid'):
                            player.puuid = summoner_data['puuid']
                            self.data_manager.update_player(player)
                            self.logger.info(f"Populated PUUID for {player.name}")
                        else:
                            results[player.name] = (False, f"Could not find PUUID for {player.summoner_name}")
                            continue
                    else:
                        results[player.name] = (False, f"Invalid summoner name format: {player.summoner_name}")
                        continue
                except Exception as e:
                    self.logger.error(f"Error populating PUUID for {player.name}: {e}")
                    results[player.name] = (False, f"Error getting PUUID: {e}")
                    continue
        
        # Filter to players with PUUIDs (after populating missing ones)
        players_with_puuid = [p for p in players_to_refresh if p.puuid]
        
        if not players_with_puuid:
            return results if results else {"error": (False, "No players with valid PUUIDs found")}
        
        # Process players in batches to respect rate limits
        import time
        batch_size = max_concurrent
        
        for i in range(0, len(players_with_puuid), batch_size):
            batch = players_with_puuid[i:i + batch_size]
            
            for player in batch:
                # Skip if we already have an error result for this player
                if player.name in results:
                    continue
                    
                try:
                    success = self._fetch_player_api_data_with_caching(player)
                    
                    if success:
                        # Recalculate preferences
                        new_prefs = self._calculate_preferences_from_performance(player)
                        if new_prefs:
                            player.role_preferences = new_prefs
                        
                        # Update player
                        self.data_manager.update_player(player)
                        results[player.name] = (True, "Data refreshed successfully")
                    else:
                        results[player.name] = (False, "Failed to fetch API data")
                        
                except Exception as e:
                    self.logger.error(f"Error refreshing {player.name}: {e}")
                    results[player.name] = (False, f"Error: {e}")
            
            # Rate limiting delay between batches
            if i + batch_size < len(players_with_puuid):
                time.sleep(2)  # 2 second delay between batches
        
        # Update system status
        self.system_status = self._get_system_status()
        
        return results
    
    def populate_missing_puuids(self) -> Dict[str, Tuple[bool, str]]:
        """
        Populate missing PUUIDs for all players.
        
        Returns:
            Dictionary of player_name -> (success, message)
        """
        if not self.api_available:
            return {"error": (False, "API unavailable - cannot populate PUUIDs")}
        
        players = self.data_manager.load_player_data()
        players_needing_puuid = [p for p in players if not p.puuid]
        
        if not players_needing_puuid:
            return {"info": (True, "All players already have PUUIDs")}
        
        results = {}
        self.logger.info(f"Populating PUUIDs for {len(players_needing_puuid)} players")
        
        for player in players_needing_puuid:
            try:
                # Extract game name and tag line from summoner_name
                if '#' in player.summoner_name:
                    game_name, tag_line = player.summoner_name.split('#', 1)
                    summoner_data = self.riot_client.get_summoner_data(player.summoner_name)
                    if summoner_data and summoner_data.get('puuid'):
                        player.puuid = summoner_data['puuid']
                        self.data_manager.update_player(player)
                        results[player.name] = (True, f"PUUID populated successfully")
                        self.logger.info(f"Populated PUUID for {player.name}")
                    else:
                        results[player.name] = (False, f"Could not find PUUID for {player.summoner_name}")
                else:
                    results[player.name] = (False, f"Invalid summoner name format: {player.summoner_name}")
            except Exception as e:
                self.logger.error(f"Error populating PUUID for {player.name}: {e}")
                results[player.name] = (False, f"Error getting PUUID: {e}")
        
        # Update system status
        self.system_status = self._get_system_status()
        
        return results
    
    def get_player_data_freshness(self, player_name: str) -> Dict[str, Any]:
        """
        Get information about the freshness and completeness of player data.
        
        Args:
            player_name: Name of player to check
            
        Returns:
            Dictionary with data freshness information
        """
        player = self.data_manager.get_player_by_name(player_name)
        if not player:
            return {"error": f"Player '{player_name}' not found"}
        
        freshness_info = {
            "player_name": player_name,
            "last_updated": player.last_updated.isoformat() if player.last_updated else None,
            "data_age_days": (datetime.now() - player.last_updated).days if player.last_updated else None,
            "has_performance_data": bool(player.performance_cache),
            "has_champion_masteries": bool(player.champion_masteries),
            "has_custom_preferences": any(pref != 3 for pref in player.role_preferences.values()),
            "api_available": self.api_available,
            "has_puuid": bool(player.puuid),
            "recommendations": []
        }
        
        # Generate recommendations
        if not player.puuid:
            freshness_info["recommendations"].append("Add valid Riot ID to enable API data fetching")
        elif not self.api_available:
            freshness_info["recommendations"].append("API currently unavailable - using cached/default data")
        elif freshness_info["data_age_days"] and freshness_info["data_age_days"] > 7:
            freshness_info["recommendations"].append("Data is over 7 days old - consider refreshing")
        elif not freshness_info["has_performance_data"] and not freshness_info["has_champion_masteries"]:
            freshness_info["recommendations"].append("No API data available - refresh to get performance data")
        
        # Data quality score
        quality_score = 0
        if freshness_info["has_performance_data"]:
            quality_score += 40
        if freshness_info["has_champion_masteries"]:
            quality_score += 40
        if freshness_info["has_custom_preferences"]:
            quality_score += 20
        
        # Age penalty
        if freshness_info["data_age_days"]:
            if freshness_info["data_age_days"] <= 7:
                pass  # No penalty
            elif freshness_info["data_age_days"] <= 30:
                quality_score -= 10
            else:
                quality_score -= 20
        
        freshness_info["data_quality_score"] = max(0, quality_score)
        
        return freshness_info
    
    def _ensure_player_data_completeness_with_fallback(self, players: List[Player]) -> None:
        """
        Ensure data completeness with graceful fallback when API is unavailable.
        
        Args:
            players: List of players to ensure data completeness for
        """
        try:
            # Try the standard data completeness check
            self._ensure_player_data_completeness(players)
        except Exception as e:
            self.logger.warning(f"Standard data completeness check failed: {e}")
            
            # Fallback: ensure minimum viable data for each player
            for player in players:
                try:
                    # Ensure basic preferences exist
                    if not player.role_preferences:
                        player.role_preferences = self._generate_intelligent_default_preferences()
                    
                    # Fill in missing role preferences
                    for role in self.roles:
                        if role not in player.role_preferences:
                            player.role_preferences[role] = 3
                    
                    # Ensure role champion pools exist (even if empty)
                    if not player.role_champion_pools:
                        player.role_champion_pools = {role: [] for role in self.roles}
                    
                    # Update timestamp
                    player.last_updated = datetime.now()
                    
                except Exception as player_error:
                    self.logger.error(f"Failed to ensure minimum data for {player.name}: {player_error}")
                    continue
    
    def _generate_optimization_success_message(self, players: List[Player], 
                                             optimization_time: float, 
                                             result: Any) -> str:
        """
        Generate a comprehensive success message for optimization results.
        
        Args:
            players: List of players used in optimization
            optimization_time: Time taken for optimization
            result: Optimization result object
            
        Returns:
            Formatted success message
        """
        base_msg = f"Optimization completed successfully in {optimization_time:.2f} seconds"
        
        # Add player count information
        if len(players) < 5:
            base_msg += f" (using {len(players)} players - some roles may be suboptimal)"
        
        # Add data quality information
        players_with_api_data = sum(1 for p in players if p.performance_cache or p.champion_masteries)
        if players_with_api_data < len(players):
            missing_data = len(players) - players_with_api_data
            base_msg += f" ({missing_data} player(s) using default preferences)"
        
        # Add API status information
        if not self.api_available:
            base_msg += " (offline mode - using cached/default data)"
        
        return base_msg
    
    def _attempt_fallback_optimization(self, players: List[Player], 
                                     player_selection: Optional[List[str]]) -> Tuple[bool, str, Optional[Any]]:
        """
        Attempt a fallback optimization with minimal data requirements.
        
        Args:
            players: List of all players
            player_selection: Optional specific player selection
            
        Returns:
            Tuple of (success, message, result)
        """
        try:
            self.logger.info("Attempting fallback optimization with minimal data")
            
            # Select players for fallback
            if player_selection:
                selected_players = [self.data_manager.get_player_by_name(name) 
                                  for name in player_selection]
                selected_players = [p for p in selected_players if p]  # Remove None values
            else:
                # Use all available players
                selected_players = players
            
            if len(selected_players) < 2:
                return False, "Insufficient players for fallback optimization", None
            
            # Ensure absolute minimum data
            for player in selected_players:
                if not player.role_preferences:
                    player.role_preferences = {role: 3 for role in self.roles}
                
                # Fill missing preferences
                for role in self.roles:
                    if role not in player.role_preferences:
                        player.role_preferences[role] = 3
            
            # Try optimization with minimal data
            start_time = time.time()
            result = self.optimizer.optimize_team(selected_players)
            optimization_time = time.time() - start_time
            
            result.optimization_time = optimization_time
            
            success_msg = (f"Fallback optimization completed in {optimization_time:.2f} seconds "
                          f"(using minimal data for {len(selected_players)} players)")
            
            return True, success_msg, result
            
        except Exception as e:
            self.logger.error(f"Fallback optimization also failed: {e}")
            return False, f"All optimization attempts failed: {e}", None
    
    def _auto_select_players(self, players: List[Player], max_players: int = 10) -> List[Player]:
        """
        Automatically select the best players for optimization based on data completeness.
        
        Args:
            players: List of all available players
            max_players: Maximum number of players to select
            
        Returns:
            List of selected players
        """
        # Score players based on data completeness and recency
        player_scores = []
        
        for player in players:
            score = 0
            
            # Base score for having the player
            score += 1
            
            # Bonus for having API data
            if player.performance_cache:
                score += 3  # Increased weight for performance data
            if player.champion_masteries:
                score += 3  # Increased weight for champion data
            
            # Bonus for having custom preferences
            if any(pref != 3 for pref in player.role_preferences.values()):
                score += 2  # Increased weight for custom preferences
            
            # Bonus for recent updates
            if player.last_updated:
                days_old = (datetime.now() - player.last_updated).days
                if days_old < 7:
                    score += 2
                elif days_old < 30:
                    score += 1
            
            # Bonus for role diversity (players with strong preferences in different roles)
            strong_roles = [role for role, pref in player.role_preferences.items() if pref >= 4]
            if len(strong_roles) == 1:
                score += 1  # Specialist bonus
            elif len(strong_roles) >= 2:
                score += 2  # Flexibility bonus
            
            # Penalty for very old or missing data
            if not player.last_updated:
                score -= 1
            elif (datetime.now() - player.last_updated).days > 90:
                score -= 2
            
            player_scores.append((player, score))
        
        # Sort by score and select top players
        player_scores.sort(key=lambda x: x[1], reverse=True)
        selected = [player for player, score in player_scores[:max_players]]
        
        # Log selection reasoning for debugging
        self.logger.info(f"Auto-selected {len(selected)} players based on data quality scores")
        for player, score in player_scores[:len(selected)]:
            self.logger.debug(f"Selected {player.name} with score {score}")
        
        return selected
    
    def _ensure_player_data_completeness(self, players: List[Player]) -> None:
        """
        Ensure players have complete data for optimization, using intelligent defaults and caching.
        
        Args:
            players: List of players to check and update
        """
        players_to_update = []
        
        for player in players:
            player_updated = False
            
            # Check if preferences need updating
            needs_preference_update = (
                not player.role_preferences or 
                all(pref == 3 for pref in player.role_preferences.values()) or
                self._should_refresh_preferences(player)
            )
            
            if needs_preference_update:
                # Try to calculate preferences from available data
                calculated_prefs = None
                
                if player.performance_cache or player.champion_masteries:
                    calculated_prefs = self._calculate_preferences_from_performance(player)
                
                if calculated_prefs:
                    player.role_preferences = calculated_prefs
                    player_updated = True
                    self.logger.info(f"Updated preferences for {player.name} based on available data")
                else:
                    # Apply intelligent defaults if no data available
                    player.role_preferences = self._generate_intelligent_default_preferences()
                    player_updated = True
                    self.logger.info(f"Applied intelligent default preferences for {player.name}")
            
            # Check if API data needs refreshing
            if self._should_refresh_api_data(player):
                if self.api_available and player.puuid:
                    try:
                        api_updated = self._fetch_player_api_data_with_caching(player)
                        if api_updated:
                            player_updated = True
                            self.logger.info(f"Refreshed API data for {player.name}")
                            
                            # Recalculate preferences with new data
                            new_prefs = self._calculate_preferences_from_performance(player)
                            if new_prefs:
                                player.role_preferences = new_prefs
                                self.logger.info(f"Updated preferences for {player.name} with fresh API data")
                    except Exception as e:
                        self.logger.warning(f"Failed to refresh API data for {player.name}: {e}")
                else:
                    self.logger.debug(f"API unavailable or no PUUID for {player.name}, using existing data")
            
            # Ensure role champion pools are populated
            if not player.role_champion_pools or not any(player.role_champion_pools.values()):
                if player.champion_masteries:
                    self._populate_role_champion_pools(player)
                    player_updated = True
            
            if player_updated:
                players_to_update.append(player)
        
        # Batch update players to minimize I/O
        if players_to_update:
            for player in players_to_update:
                self.data_manager.update_player(player)
    
    def _should_refresh_preferences(self, player: Player) -> bool:
        """
        Determine if player preferences should be refreshed based on data age and quality.
        
        Args:
            player: Player to check
            
        Returns:
            True if preferences should be refreshed
        """
        # If no last updated timestamp, refresh
        if not player.last_updated:
            return True
        
        # If data is very old (>30 days), refresh
        days_old = (datetime.now() - player.last_updated).days
        if days_old > 30:
            return True
        
        # If we have new API data but old preferences, refresh
        if (player.performance_cache or player.champion_masteries) and days_old > 7:
            return True
        
        return False
    
    def _should_refresh_api_data(self, player: Player) -> bool:
        """
        Determine if API data should be refreshed based on age and availability.
        
        Args:
            player: Player to check
            
        Returns:
            True if API data should be refreshed
        """
        if not self.api_available or not player.puuid:
            return False
        
        # If no data at all, definitely refresh
        if not player.performance_cache and not player.champion_masteries:
            return True
        
        # If no last updated timestamp, refresh
        if not player.last_updated:
            return True
        
        # Check age of data
        days_old = (datetime.now() - player.last_updated).days
        
        # Refresh if data is older than 7 days
        if days_old > 7:
            return True
        
        # Refresh if we only have partial data and it's older than 1 day
        has_performance = bool(player.performance_cache)
        has_masteries = bool(player.champion_masteries)
        
        if (not has_performance or not has_masteries) and days_old > 1:
            return True
        
        return False
    
    def _populate_role_champion_pools(self, player: Player) -> None:
        """
        Populate role champion pools based on champion masteries.
        
        Args:
            player: Player to populate champion pools for
        """
        if not player.champion_masteries:
            return
        
        # Initialize empty pools
        player.role_champion_pools = {role: [] for role in self.roles}
        
        # Populate pools based on champion primary roles
        for champion_id, mastery in player.champion_masteries.items():
            for role in mastery.primary_roles:
                if role in player.role_champion_pools:
                    player.role_champion_pools[role].append(champion_id)
        
        # Sort each pool by mastery points (descending)
        for role in player.role_champion_pools:
            player.role_champion_pools[role].sort(
                key=lambda champ_id: player.champion_masteries.get(champ_id, type('obj', (object,), {'mastery_points': 0})).mastery_points,
                reverse=True
            )
    
    def _calculate_preferences_from_performance(self, player: Player) -> Optional[Dict[str, int]]:
        """
        Calculate intelligent role preferences based on performance data and champion mastery.
        
        Args:
            player: Player with performance data
            
        Returns:
            Dictionary of role preferences or None if calculation fails
        """
        if not player.performance_cache and not player.champion_masteries:
            return None
        
        try:
            preferences = {}
            role_scores = {}
            
            # Calculate scores for each role
            for role in self.roles:
                role_score = self._calculate_role_suitability_score(player, role)
                role_scores[role] = role_score
            
            if not role_scores:
                return None
            
            # Convert scores to 1-5 preference scale with intelligent distribution
            sorted_roles = sorted(role_scores.items(), key=lambda x: x[1], reverse=True)
            
            # Assign preferences based on relative performance
            for i, (role, score) in enumerate(sorted_roles):
                if i == 0 and score > 0.7:
                    # Best role with high score
                    preferences[role] = 5
                elif i == 0 and score > 0.5:
                    # Best role with decent score
                    preferences[role] = 4
                elif i <= 1 and score > 0.4:
                    # Top 2 roles with reasonable scores
                    preferences[role] = 4 if i == 0 else 3
                elif score > 0.3:
                    # Decent performance
                    preferences[role] = 3
                elif score > 0.2:
                    # Below average but playable
                    preferences[role] = 2
                else:
                    # Poor performance
                    preferences[role] = 1
            
            # Ensure all roles have preferences
            for role in self.roles:
                if role not in preferences:
                    preferences[role] = 2  # Default low preference
            
            # Apply some smoothing to avoid extreme distributions
            self._smooth_preferences(preferences)
            
            return preferences
            
        except Exception as e:
            self.logger.error(f"Error calculating preferences for {player.name}: {e}")
            return None
    
    def _calculate_role_suitability_score(self, player: Player, role: str) -> float:
        """
        Calculate comprehensive role suitability score combining performance and mastery.
        
        Args:
            player: Player object
            role: Role to calculate suitability for
            
        Returns:
            Suitability score (0.0 to 1.0)
        """
        score_components = []
        weights = []
        
        # Performance-based score
        if player.performance_cache and role in player.performance_cache:
            perf_data = player.performance_cache[role]
            if isinstance(perf_data, dict):
                win_rate = perf_data.get('win_rate', 0.5)
                kda = min(perf_data.get('avg_kda', 1.0), 5.0) / 5.0  # Normalize to 0-1
                matches = perf_data.get('matches_played', 0)
                recent_form = (perf_data.get('recent_form', 0.0) + 1) / 2  # Convert -1,1 to 0,1
                
                # Weight by confidence (number of matches)
                confidence = min(matches / 15.0, 1.0)  # Full confidence at 15+ matches
                
                # Composite performance score
                perf_score = (win_rate * 0.5 + kda * 0.3 + recent_form * 0.2) * confidence
                score_components.append(perf_score)
                weights.append(0.6)  # High weight for performance data
        
        # Champion mastery-based score
        if player.champion_masteries:
            mastery_score = self._calculate_mastery_score_for_role(player, role)
            score_components.append(mastery_score)
            weights.append(0.4)  # Moderate weight for mastery data
        
        # If no data available, return neutral score
        if not score_components:
            return 0.5
        
        # Calculate weighted average
        total_score = sum(score * weight for score, weight in zip(score_components, weights))
        total_weight = sum(weights)
        
        return total_score / total_weight if total_weight > 0 else 0.5
    
    def _calculate_mastery_score_for_role(self, player: Player, role: str) -> float:
        """
        Calculate mastery-based suitability score for a role.
        
        Args:
            player: Player object
            role: Role to calculate mastery score for
            
        Returns:
            Mastery score (0.0 to 1.0)
        """
        if not player.champion_masteries:
            return 0.5
        
        role_champions = []
        total_mastery_points = 0
        high_mastery_count = 0
        
        for champion_id, mastery in player.champion_masteries.items():
            if role in mastery.primary_roles:
                role_champions.append(mastery)
                total_mastery_points += mastery.mastery_points
                
                # Count high mastery champions (level 6+)
                if mastery.mastery_level >= 6:
                    high_mastery_count += 1
        
        if not role_champions:
            return 0.3  # Below average if no champions for this role
        
        # Calculate score based on multiple factors
        champion_count_score = min(len(role_champions) / 10.0, 1.0)  # Up to 10 champions
        mastery_points_score = min(total_mastery_points / 500000.0, 1.0)  # Up to 500k points
        high_mastery_score = min(high_mastery_count / 3.0, 1.0)  # Up to 3 high mastery champions
        
        # Recent play bonus
        recent_play_bonus = 0.0
        recent_champions = [m for m in role_champions if m.last_play_time and 
                          (datetime.now() - m.last_play_time).days <= 30]
        if recent_champions:
            recent_play_bonus = min(len(recent_champions) / 5.0, 0.2)  # Up to 20% bonus
        
        # Combine scores
        mastery_score = (
            champion_count_score * 0.3 +
            mastery_points_score * 0.3 +
            high_mastery_score * 0.4 +
            recent_play_bonus
        )
        
        return min(mastery_score, 1.0)
    
    def _smooth_preferences(self, preferences: Dict[str, int]) -> None:
        """
        Apply smoothing to preferences to avoid extreme distributions.
        
        Args:
            preferences: Dictionary of role preferences to smooth (modified in place)
        """
        # Count extreme preferences
        high_prefs = sum(1 for pref in preferences.values() if pref >= 4)
        low_prefs = sum(1 for pref in preferences.values() if pref <= 2)
        
        # If too many high preferences, reduce some
        if high_prefs > 2:
            sorted_prefs = sorted(preferences.items(), key=lambda x: x[1], reverse=True)
            for i, (role, pref) in enumerate(sorted_prefs):
                if i >= 2 and pref >= 4:
                    preferences[role] = 3
        
        # If too many low preferences, boost some
        if low_prefs > 3:
            sorted_prefs = sorted(preferences.items(), key=lambda x: x[1])
            for i, (role, pref) in enumerate(sorted_prefs):
                if i < 2 and pref <= 2:
                    preferences[role] = 3
        
        # Ensure at least one role has preference 3 or higher
        if all(pref < 3 for pref in preferences.values()):
            best_role = max(preferences.items(), key=lambda x: x[1])[0]
            preferences[best_role] = 3
    
    def get_comprehensive_analysis(self, players: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Get comprehensive analysis of players and team dynamics.
        
        Args:
            players: List of player names to analyze (None for all players)
            
        Returns:
            Dictionary containing comprehensive analysis data
        """
        try:
            all_players = self.data_manager.load_player_data()
            
            if players:
                # Filter to specified players
                analyzed_players = []
                for name in players:
                    player = self.data_manager.get_player_by_name(name)
                    if player:
                        analyzed_players.append(player)
            else:
                analyzed_players = all_players
            
            if not analyzed_players:
                return {'error': 'No players found for analysis'}
            
            analysis = {
                'system_status': self.system_status,
                'player_count': len(analyzed_players),
                'players': [],
                'team_analysis': {},
                'recommendations': []
            }
            
            # Individual player analysis
            for player in analyzed_players:
                player_analysis = self._analyze_individual_player(player)
                analysis['players'].append(player_analysis)
            
            # Team-level analysis
            if len(analyzed_players) >= 2:
                team_analysis = self._analyze_team_dynamics(analyzed_players)
                analysis['team_analysis'] = team_analysis
            
            # Generate recommendations
            recommendations = self._generate_recommendations(analyzed_players)
            analysis['recommendations'] = recommendations
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error in comprehensive analysis: {e}")
            return {'error': f'Analysis failed: {e}'}
    
    def _analyze_individual_player(self, player: Player) -> Dict[str, Any]:
        """Analyze an individual player's data and capabilities."""
        analysis = {
            'name': player.name,
            'summoner_name': player.summoner_name,
            'last_updated': player.last_updated.isoformat() if player.last_updated else None,
            'data_completeness': {},
            'role_analysis': {},
            'champion_analysis': {},
            'strengths': [],
            'weaknesses': []
        }
        
        # Data completeness
        analysis['data_completeness'] = {
            'has_preferences': any(pref != 3 for pref in player.role_preferences.values()),
            'has_performance_data': bool(player.performance_cache),
            'has_champion_data': bool(player.champion_masteries),
            'completeness_score': 0
        }
        
        completeness = 0
        if analysis['data_completeness']['has_preferences']:
            completeness += 1
        if analysis['data_completeness']['has_performance_data']:
            completeness += 2
        if analysis['data_completeness']['has_champion_data']:
            completeness += 2
        
        analysis['data_completeness']['completeness_score'] = completeness / 5.0
        
        # Role analysis
        for role in self.roles:
            role_data = {
                'preference': player.role_preferences.get(role, 3),
                'performance_score': 0,
                'champion_pool_size': 0,
                'suitability': 'Unknown'
            }
            
            # Performance data
            if player.performance_cache and role in player.performance_cache:
                perf = player.performance_cache[role]
                if isinstance(perf, dict):
                    role_data['performance_score'] = perf.get('win_rate', 0) * 100
                    role_data['matches_played'] = perf.get('matches_played', 0)
                    role_data['avg_kda'] = perf.get('avg_kda', 0)
            
            # Champion pool analysis
            if player.champion_masteries:
                role_champions = [
                    champ for champ in player.champion_masteries.values()
                    if role in champ.primary_roles
                ]
                role_data['champion_pool_size'] = len(role_champions)
                role_data['top_champions'] = [
                    {
                        'name': champ.champion_name,
                        'mastery_level': champ.mastery_level,
                        'mastery_points': champ.mastery_points
                    }
                    for champ in sorted(role_champions, key=lambda x: x.mastery_points, reverse=True)[:3]
                ]
            
            # Calculate overall suitability
            suitability_score = (
                role_data['preference'] * 0.3 +
                (role_data['performance_score'] / 20) * 0.4 +  # Scale performance to 0-5
                min(role_data['champion_pool_size'] / 5, 1) * 5 * 0.3  # Scale champion pool to 0-5
            )
            
            if suitability_score >= 4:
                role_data['suitability'] = 'Excellent'
            elif suitability_score >= 3:
                role_data['suitability'] = 'Good'
            elif suitability_score >= 2:
                role_data['suitability'] = 'Fair'
            else:
                role_data['suitability'] = 'Poor'
            
            analysis['role_analysis'][role] = role_data
        
        # Overall champion analysis
        if player.champion_masteries:
            total_champions = len(player.champion_masteries)
            total_mastery_points = sum(champ.mastery_points for champ in player.champion_masteries.values())
            mastery_7_count = sum(1 for champ in player.champion_masteries.values() if champ.mastery_level == 7)
            
            analysis['champion_analysis'] = {
                'total_champions': total_champions,
                'total_mastery_points': total_mastery_points,
                'mastery_7_champions': mastery_7_count,
                'champion_diversity': min(total_champions / 50, 1.0)  # Normalize to 0-1
            }
        
        # Generate strengths and weaknesses
        analysis['strengths'], analysis['weaknesses'] = self._identify_player_strengths_weaknesses(player, analysis)
        
        return analysis
    
    def _analyze_team_dynamics(self, players: List[Player]) -> Dict[str, Any]:
        """Analyze team-level dynamics and synergies."""
        team_analysis = {
            'player_count': len(players),
            'role_coverage': {},
            'synergy_potential': 0,
            'data_quality': 0,
            'optimization_readiness': 'Unknown'
        }
        
        # Role coverage analysis
        for role in self.roles:
            suitable_players = []
            for player in players:
                role_pref = player.role_preferences.get(role, 3)
                has_champions = bool(player.champion_masteries and any(
                    role in champ.primary_roles for champ in player.champion_masteries.values()
                ))
                has_performance = bool(player.performance_cache and role in player.performance_cache)
                
                suitability_score = role_pref
                if has_champions:
                    suitability_score += 1
                if has_performance:
                    suitability_score += 1
                
                if suitability_score >= 4:
                    suitable_players.append(player.name)
            
            team_analysis['role_coverage'][role] = {
                'suitable_players': suitable_players,
                'coverage_quality': 'Good' if len(suitable_players) >= 2 else 'Limited' if suitable_players else 'Poor'
            }
        
        # Calculate overall team readiness
        total_coverage = sum(1 for role_data in team_analysis['role_coverage'].values() 
                           if role_data['coverage_quality'] in ['Good', 'Limited'])
        
        if total_coverage >= 5 and len(players) >= 5:
            team_analysis['optimization_readiness'] = 'Ready'
        elif total_coverage >= 3:
            team_analysis['optimization_readiness'] = 'Partial'
        else:
            team_analysis['optimization_readiness'] = 'Insufficient'
        
        return team_analysis
    
    def _identify_player_strengths_weaknesses(self, player: Player, analysis: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """Identify player strengths and weaknesses based on analysis."""
        strengths = []
        weaknesses = []
        
        # Check role preferences
        high_pref_roles = [role for role, pref in player.role_preferences.items() if pref >= 4]
        if len(high_pref_roles) >= 2:
            strengths.append(f"Flexible - comfortable in {len(high_pref_roles)} roles")
        elif len(high_pref_roles) == 1:
            strengths.append(f"Specialized in {high_pref_roles[0]} role")
        
        # Check champion mastery
        if player.champion_masteries:
            mastery_7_count = sum(1 for champ in player.champion_masteries.values() if champ.mastery_level == 7)
            if mastery_7_count >= 5:
                strengths.append(f"High champion mastery ({mastery_7_count} level 7 champions)")
            elif mastery_7_count == 0:
                weaknesses.append("No level 7 champion masteries")
        else:
            weaknesses.append("No champion mastery data available")
        
        # Check performance data
        if player.performance_cache:
            high_performance_roles = [
                role for role, perf in player.performance_cache.items()
                if isinstance(perf, dict) and perf.get('win_rate', 0) > 0.6
            ]
            if high_performance_roles:
                strengths.append(f"Strong performance in {', '.join(high_performance_roles)}")
        else:
            weaknesses.append("No recent performance data")
        
        # Check data completeness
        completeness = analysis['data_completeness']['completeness_score']
        if completeness < 0.5:
            weaknesses.append("Incomplete player data - consider updating")
        
        return strengths, weaknesses
    
    def _generate_recommendations(self, players: List[Player]) -> List[str]:
        """Generate recommendations for improving team optimization."""
        recommendations = []
        
        # Check player count
        if len(players) < 5:
            recommendations.append(f"Add {5 - len(players)} more players for full team optimization")
        
        # Check data completeness
        players_without_api_data = [
            p for p in players 
            if not (p.performance_cache or p.champion_masteries)
        ]
        if players_without_api_data and self.api_available:
            recommendations.append(f"Fetch API data for {len(players_without_api_data)} players to improve accuracy")
        
        # Check preferences
        players_with_default_prefs = [
            p for p in players
            if all(pref == 3 for pref in p.role_preferences.values())
        ]
        if players_with_default_prefs:
            recommendations.append(f"Set role preferences for {len(players_with_default_prefs)} players")
        
        # Check role coverage
        role_gaps = []
        for role in self.roles:
            suitable_count = sum(
                1 for p in players
                if p.role_preferences.get(role, 3) >= 4
            )
            if suitable_count == 0:
                role_gaps.append(role)
        
        if role_gaps:
            recommendations.append(f"Consider adding players who prefer: {', '.join(role_gaps)}")
        
        return recommendations
    
    def bulk_player_operations(self, operations: List[Dict[str, Any]]) -> List[Tuple[bool, str]]:
        """
        Perform bulk operations on players.
        
        Args:
            operations: List of operation dictionaries with 'action' and parameters
            
        Returns:
            List of (success, message) tuples for each operation
        """
        results = []
        
        for operation in operations:
            try:
                action = operation.get('action')
                
                if action == 'add':
                    success, message, _ = self.add_player_with_data(
                        operation.get('name', ''),
                        operation.get('riot_id', ''),
                        operation.get('auto_fetch', True)
                    )
                    results.append((success, message))
                
                elif action == 'remove':
                    name = operation.get('name', '')
                    success = self.data_manager.delete_player(name)
                    message = f"Player '{name}' removed" if success else f"Player '{name}' not found"
                    results.append((success, message))
                
                elif action == 'update_preferences':
                    name = operation.get('name', '')
                    preferences = operation.get('preferences', {})
                    try:
                        self.data_manager.update_preferences(name, preferences)
                        results.append((True, f"Preferences updated for '{name}'"))
                    except Exception as e:
                        results.append((False, f"Failed to update preferences for '{name}': {e}"))
                
                elif action == 'refresh_data':
                    name = operation.get('name', '')
                    player = self.data_manager.get_player_by_name(name)
                    if player:
                        success = self._fetch_player_api_data(player)
                        message = f"Data refreshed for '{name}'" if success else f"Failed to refresh data for '{name}'"
                        results.append((success, message))
                    else:
                        results.append((False, f"Player '{name}' not found"))
                
                else:
                    results.append((False, f"Unknown operation: {action}"))
                    
            except Exception as e:
                results.append((False, f"Operation failed: {e}"))
        
        # Update system status after bulk operations
        self.system_status = self._get_system_status()
        
        return results
    
    def get_system_diagnostics(self) -> Dict[str, Any]:
        """Get comprehensive system diagnostics and health information."""
        diagnostics = {
            'timestamp': datetime.now().isoformat(),
            'system_status': self.system_status,
            'component_status': {},
            'performance_metrics': {},
            'analytics_status': {},
            'recommendations': []
        }
        
        # Component status
        diagnostics['component_status'] = {
            'config': 'OK' if self.config else 'ERROR',
            'data_manager': 'OK' if self.data_manager else 'ERROR',
            'riot_client': 'OK' if self.api_available else 'OFFLINE',
            'champion_data': 'OK' if len(self.champion_data_manager.champions) > 0 else 'ERROR',
            'optimizer': 'OK' if self.optimizer else 'ERROR',
            'analytics': 'OK' if self.analytics_available else 'ERROR'
        }
        
        # Analytics status
        diagnostics['analytics_status'] = self._get_analytics_health_status()
        
        # Performance metrics
        try:
            players = self.data_manager.load_player_data()
            diagnostics['performance_metrics'] = {
                'total_players': len(players),
                'players_with_complete_data': sum(
                    1 for p in players 
                    if p.performance_cache and p.champion_masteries
                ),
                'cache_size': len(self.champion_data_manager.champions),
                'last_optimization': 'N/A'  # Could track this in future
            }
        except Exception as e:
            diagnostics['performance_metrics'] = {'error': str(e)}
        
        # System recommendations
        if not self.api_available:
            diagnostics['recommendations'].append("API client offline - check RIOT_API_KEY environment variable")
        
        if not self.analytics_available:
            diagnostics['recommendations'].append("Analytics system offline - some features may be unavailable")
        
        if diagnostics['performance_metrics'].get('total_players', 0) < 5:
            diagnostics['recommendations'].append("Add more players for optimal team optimization")
        
        return diagnostics
    
    # Analytics System Integration Methods
    
    def analyze_player_performance(self, puuid: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Analyze player performance using historical analytics engine.
        
        Args:
            puuid: Player's PUUID
            filters: Optional analytics filters
            
        Returns:
            Dictionary with player performance analysis
        """
        if not self.analytics_available:
            return {"error": "Analytics system unavailable"}
        
        try:
            from .analytics_models import AnalyticsFilters
            
            # Convert filters if provided
            analytics_filters = None
            if filters:
                analytics_filters = AnalyticsFilters(**filters)
            
            # Perform analysis
            result = self.historical_analytics_engine.analyze_player_performance(puuid, analytics_filters)
            
            # Convert to dictionary for JSON serialization
            return {
                'puuid': result.puuid,
                'analysis_period': {
                    'start_date': result.analysis_period.start_date.isoformat(),
                    'end_date': result.analysis_period.end_date.isoformat()
                } if result.analysis_period else None,
                'overall_performance': result.overall_performance.__dict__,
                'role_performance': {role: perf.__dict__ for role, perf in result.role_performance.items()},
                'champion_performance': {
                    str(champ_id): perf.__dict__ 
                    for champ_id, perf in result.champion_performance.items()
                },
                'trend_analysis': result.trend_analysis.__dict__ if result.trend_analysis else None,
                'comparative_rankings': result.comparative_rankings.__dict__ if result.comparative_rankings else None,
                'confidence_scores': result.confidence_scores.__dict__ if result.confidence_scores else None
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing player performance: {e}")
            return {"error": f"Failed to analyze player performance: {e}"}
    
    def get_champion_recommendations(self, puuid: str, role: str, 
                                   team_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get champion recommendations for a player and role.
        
        Args:
            puuid: Player's PUUID
            role: Role to get recommendations for
            team_context: Optional team context information
            
        Returns:
            Dictionary with champion recommendations
        """
        if not self.analytics_available:
            return {"error": "Analytics system unavailable"}
        
        try:
            from .analytics_models import TeamContext
            
            # Convert team context if provided
            context = None
            if team_context:
                context = TeamContext(**team_context)
            
            # Get recommendations
            recommendations = self.champion_recommendation_engine.get_champion_recommendations(
                puuid, role, context
            )
            
            # Convert to dictionary format
            return {
                'puuid': puuid,
                'role': role,
                'recommendations': [
                    {
                        'champion_id': rec.champion_id,
                        'champion_name': rec.champion_name,
                        'recommendation_score': rec.recommendation_score,
                        'confidence': rec.confidence,
                        'historical_performance': rec.historical_performance.__dict__ if rec.historical_performance else None,
                        'expected_performance': rec.expected_performance.__dict__ if rec.expected_performance else None,
                        'synergy_analysis': rec.synergy_analysis.__dict__ if rec.synergy_analysis else None,
                        'reasoning': rec.reasoning.__dict__ if rec.reasoning else None
                    }
                    for rec in recommendations
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Error getting champion recommendations: {e}")
            return {"error": f"Failed to get champion recommendations: {e}"}
    
    def calculate_performance_trends(self, puuid: str, time_window_days: int = 30) -> Dict[str, Any]:
        """
        Calculate performance trends for a player.
        
        Args:
            puuid: Player's PUUID
            time_window_days: Time window for trend analysis
            
        Returns:
            Dictionary with trend analysis results
        """
        if not self.analytics_available:
            return {"error": "Analytics system unavailable"}
        
        try:
            result = self.historical_analytics_engine.calculate_performance_trends(puuid, time_window_days)
            
            return {
                'puuid': result.puuid,
                'time_window_days': result.time_window_days,
                'trend_data': [
                    {
                        'timestamp': point.timestamp.isoformat(),
                        'value': point.value,
                        'metadata': point.metadata
                    }
                    for point in result.trend_data
                ],
                'trend_direction': result.trend_direction,
                'trend_strength': result.trend_strength,
                'statistical_significance': result.statistical_significance,
                'confidence_interval': {
                    'lower': result.confidence_interval.lower,
                    'upper': result.confidence_interval.upper,
                    'confidence_level': result.confidence_interval.confidence_level
                } if result.confidence_interval else None
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating performance trends: {e}")
            return {"error": f"Failed to calculate performance trends: {e}"}
    
    def generate_comparative_analysis(self, puuids: List[str], metric: str) -> Dict[str, Any]:
        """
        Generate comparative analysis between multiple players.
        
        Args:
            puuids: List of player PUUIDs to compare
            metric: Metric to compare (e.g., 'win_rate', 'kda', 'cs_per_min')
            
        Returns:
            Dictionary with comparative analysis results
        """
        if not self.analytics_available:
            return {"error": "Analytics system unavailable"}
        
        try:
            result = self.historical_analytics_engine.generate_comparative_analysis(puuids, metric)
            
            return {
                'players': result.players,
                'comparison_metric': result.comparison_metric,
                'player_values': result.player_values,
                'rankings': result.rankings,
                'percentiles': result.percentiles,
                'statistical_significance': {
                    f"{pair[0]}_{pair[1]}": p_value 
                    for pair, p_value in (result.statistical_significance or {}).items()
                },
                'analysis_period': {
                    'start_date': result.analysis_period.start_date.isoformat(),
                    'end_date': result.analysis_period.end_date.isoformat()
                } if result.analysis_period else None,
                'sample_sizes': result.sample_sizes
            }
            
        except Exception as e:
            self.logger.error(f"Error generating comparative analysis: {e}")
            return {"error": f"Failed to generate comparative analysis: {e}"}
    
    def get_analytics_cache_statistics(self) -> Dict[str, Any]:
        """
        Get analytics cache performance statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        if not self.analytics_available or not self.analytics_cache_manager:
            return {"error": "Analytics cache unavailable"}
        
        try:
            return self.analytics_cache_manager.get_cache_statistics()
        except Exception as e:
            self.logger.error(f"Error getting cache statistics: {e}")
            return {"error": f"Failed to get cache statistics: {e}"}
    
    def invalidate_analytics_cache(self, pattern: Optional[str] = None) -> Dict[str, Any]:
        """
        Invalidate analytics cache entries.
        
        Args:
            pattern: Optional pattern to match cache keys (None for all)
            
        Returns:
            Dictionary with invalidation results
        """
        if not self.analytics_available or not self.analytics_cache_manager:
            return {"error": "Analytics cache unavailable"}
        
        try:
            if pattern:
                self.analytics_cache_manager.invalidate_cache(pattern)
                return {"success": True, "message": f"Invalidated cache entries matching '{pattern}'"}
            else:
                # Clear all cache
                self.analytics_cache_manager.clear_cache()
                return {"success": True, "message": "All cache entries cleared"}
        except Exception as e:
            self.logger.error(f"Error invalidating cache: {e}")
            return {"error": f"Failed to invalidate cache: {e}"}
    
    def update_player_baselines(self, puuid: str) -> Dict[str, Any]:
        """
        Update performance baselines for a specific player.
        
        Args:
            puuid: Player's PUUID
            
        Returns:
            Dictionary with update results
        """
        if not self.analytics_available or not self.baseline_manager:
            return {"error": "Baseline manager unavailable"}
        
        try:
            # Get player matches for baseline calculation
            matches = self.match_manager.get_matches_for_player(puuid)
            
            if not matches:
                return {"error": "No matches found for player"}
            
            # Update baselines
            from .analytics_models import BaselineContext
            context = BaselineContext()
            baseline = self.baseline_manager.calculate_player_baseline(puuid, context)
            
            return {
                "success": True,
                "puuid": puuid,
                "baseline_updated": True,
                "matches_analyzed": len(matches),
                "baseline_metrics": baseline.__dict__ if baseline else None
            }
            
        except Exception as e:
            self.logger.error(f"Error updating player baselines: {e}")
            return {"error": f"Failed to update baselines: {e}"}
    
    def migrate_analytics_data(self, migration_type: str = "full") -> Dict[str, Any]:
        """
        Migrate analytics data for compatibility with new versions.
        
        Args:
            migration_type: Type of migration ('full', 'incremental', 'cache_only')
            
        Returns:
            Dictionary with migration results
        """
        if not self.analytics_available:
            return {"error": "Analytics system unavailable"}
        
        try:
            migration_start = datetime.now()
            results = {
                "migration_type": migration_type,
                "start_time": migration_start.isoformat(),
                "operations_performed": [],
                "errors": []
            }
            
            # Clear analytics cache
            if migration_type in ["full", "cache_only"]:
                try:
                    if self.analytics_cache_manager:
                        self.analytics_cache_manager.clear_cache()
                        results["operations_performed"].append("Analytics cache cleared")
                except Exception as e:
                    results["errors"].append(f"Failed to clear cache: {e}")
            
            # Rebuild baselines
            if migration_type == "full":
                try:
                    players = self.data_manager.load_player_data()
                    players_with_puuid = [p for p in players if p.puuid]
                    
                    for player in players_with_puuid:
                        self.update_player_baselines(player.puuid)
                    
                    results["operations_performed"].append(f"Baselines rebuilt for {len(players_with_puuid)} players")
                except Exception as e:
                    results["errors"].append(f"Failed to rebuild baselines: {e}")
            
            # Update system status
            self.system_status = self._get_system_status()
            
            migration_end = datetime.now()
            results["end_time"] = migration_end.isoformat()
            results["duration_seconds"] = (migration_end - migration_start).total_seconds()
            results["success"] = len(results["errors"]) == 0
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error during analytics migration: {e}")
            return {"error": f"Analytics migration failed: {e}"}
    
    def _get_analytics_health_status(self) -> Dict[str, Any]:
        """
        Get detailed health status of analytics components.
        
        Returns:
            Dictionary with analytics health information
        """
        if not self.analytics_available:
            return {
                "overall_status": "OFFLINE",
                "components": {
                    "historical_analytics_engine": "OFFLINE",
                    "champion_recommendation_engine": "OFFLINE",
                    "baseline_manager": "OFFLINE",
                    "analytics_cache_manager": "OFFLINE",
                    "statistical_analyzer": "OFFLINE",
                    "champion_synergy_analyzer": "OFFLINE"
                },
                "error": "Analytics system not initialized"
            }
        
        health_status = {
            "overall_status": "OK",
            "components": {},
            "performance_metrics": {},
            "recommendations": []
        }
        
        # Check individual components
        components = {
            "historical_analytics_engine": self.historical_analytics_engine,
            "champion_recommendation_engine": self.champion_recommendation_engine,
            "baseline_manager": self.baseline_manager,
            "analytics_cache_manager": self.analytics_cache_manager,
            "statistical_analyzer": self.statistical_analyzer,
            "champion_synergy_analyzer": self.champion_synergy_analyzer
        }
        
        for component_name, component in components.items():
            if component is None:
                health_status["components"][component_name] = "OFFLINE"
                health_status["overall_status"] = "DEGRADED"
            else:
                health_status["components"][component_name] = "OK"
        
        # Get performance metrics
        try:
            if self.analytics_cache_manager:
                cache_stats = self.analytics_cache_manager.get_cache_statistics()
                health_status["performance_metrics"]["cache"] = cache_stats
        except Exception as e:
            health_status["performance_metrics"]["cache_error"] = str(e)
        
        try:
            if self.historical_analytics_engine:
                optimization_stats = self.historical_analytics_engine.get_optimization_statistics()
                health_status["performance_metrics"]["optimization"] = optimization_stats
        except Exception as e:
            health_status["performance_metrics"]["optimization_error"] = str(e)
        
        # Generate recommendations
        if health_status["overall_status"] == "DEGRADED":
            health_status["recommendations"].append("Some analytics components are offline - restart may be required")
        
        try:
            cache_hit_rate = health_status["performance_metrics"].get("cache", {}).get("hit_rate", 0)
            if isinstance(cache_hit_rate, (int, float)) and cache_hit_rate < 0.5:
                health_status["recommendations"].append("Low cache hit rate - consider increasing cache size")
        except (TypeError, AttributeError):
            # Handle cases where cache stats might be Mock objects or invalid
            pass
        
        return health_status