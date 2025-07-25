"""
Command-line interface for the League of Legends Team Optimizer.

This module provides an interactive CLI for managing players, setting preferences,
and running team optimizations with formatted results display.
"""

import sys
import json
import logging
import traceback
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import asdict

from .config import Config
from .data_manager import DataManager
from .riot_client import RiotAPIClient
from .performance_calculator import PerformanceCalculator
from .optimizer import OptimizationEngine, OptimizationResult
from .champion_data import ChampionDataManager
from .models import Player, TeamAssignment


class CLI:
    """Command-line interface for the team optimizer application."""
    
    def __init__(self):
        """Initialize the CLI with all required components."""
        self.logger = logging.getLogger(__name__)
        self.roles = ["top", "jungle", "middle", "support", "bottom"]
        
        # Initialize components with error handling
        try:
            self.config = Config()
            self.logger.info("Configuration loaded successfully")
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            raise
        
        try:
            self.data_manager = DataManager(self.config)
            self.logger.info("Data manager initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize data manager: {e}")
            raise
        
        try:
            self.riot_client = RiotAPIClient(self.config)
            self.logger.info("Riot API client initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize Riot API client: {e}")
            # Continue without API client for offline mode
            self.riot_client = None
            self.logger.warning("Running in offline mode - API features disabled")
        
        try:
            self.champion_data_manager = ChampionDataManager(self.config)
            self.performance_calculator = PerformanceCalculator(self.champion_data_manager)
            self.optimizer = OptimizationEngine(self.performance_calculator, self.champion_data_manager)
            self.logger.info("Optimization engine initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize optimization components: {e}")
            raise
        
        # Track API availability
        self.api_available = self.riot_client is not None
    
    def main(self) -> None:
        """Main entry point for the CLI application."""
        print("=" * 60)
        print("    League of Legends Team Optimizer")
        print("=" * 60)
        
        # Display system status
        self._display_system_status()
        
        while True:
            try:
                self._display_main_menu()
                choice = input("\nEnter your choice (1-6): ").strip()
                
                if choice == "1":
                    self._safe_execute(self._manage_players, "player management")
                elif choice == "2":
                    self._safe_execute(self._manage_preferences, "preference management")
                elif choice == "3":
                    self._safe_execute(self._optimize_team, "team optimization")
                elif choice == "4":
                    self._safe_execute(self._view_player_data, "player data viewing")
                elif choice == "5":
                    self._safe_execute(self._system_maintenance, "system maintenance")
                elif choice == "6":
                    print("\nThank you for using League of Legends Team Optimizer!")
                    self.logger.info("Application shutdown requested by user")
                    break
                else:
                    print("\nInvalid choice. Please enter a number between 1-6.")
                
                input("\nPress Enter to continue...")
                
            except KeyboardInterrupt:
                print("\n\nExiting application...")
                self.logger.info("Application interrupted by user")
                break
            except Exception as e:
                self.logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
                print(f"\nAn unexpected error occurred: {e}")
                print("The application will continue, but please report this issue.")
                input("\nPress Enter to continue...")
    
    def _display_system_status(self) -> None:
        """Display current system status and warnings."""
        print()
        if not self.api_available:
            print("⚠️  WARNING: Riot API is not available")
            print("   - Player validation and performance data fetching disabled")
            print("   - Optimization will use cached data and preferences only")
            print()
        
        # Check for other potential issues
        try:
            players = self.data_manager.load_player_data()
            if len(players) < 5:
                print(f"ℹ️  INFO: You have {len(players)} players registered")
                print("   - Need at least 5 players for team optimization")
                print()
        except Exception as e:
            print(f"⚠️  WARNING: Could not load player data: {e}")
            print()
    
    def _safe_execute(self, func, operation_name: str) -> None:
        """
        Safely execute a function with comprehensive error handling.
        
        Args:
            func: Function to execute
            operation_name: Human-readable name for the operation
        """
        try:
            self.logger.info(f"Starting {operation_name}")
            func()
            self.logger.info(f"Completed {operation_name}")
        except KeyboardInterrupt:
            print(f"\n{operation_name.capitalize()} cancelled by user.")
            self.logger.info(f"{operation_name} cancelled by user")
        except ValueError as e:
            self.logger.error(f"Validation error in {operation_name}: {e}", exc_info=True)
            print(f"\nValidation error during {operation_name}: {e}")
            
            # Provide specific guidance for validation errors
            if "player" in str(e).lower():
                print("Suggestions:")
                print("- Check that all player names are valid")
                print("- Ensure at least 5 players are available")
                print("- Verify player preferences are set correctly")
            elif "preference" in str(e).lower():
                print("Suggestions:")
                print("- Role preferences must be between 1-5")
                print("- All roles must have valid preferences")
            else:
                print("Please check your input data and try again.")
                
        except IOError as e:
            self.logger.error(f"File system error in {operation_name}: {e}", exc_info=True)
            print(f"\nFile system error during {operation_name}: {e}")
            print("Suggestions:")
            print("- Check file permissions in the data directory")
            print("- Ensure sufficient disk space is available")
            print("- Verify the application has write access to its directories")
            
        except ConnectionError as e:
            self.logger.error(f"Network error in {operation_name}: {e}", exc_info=True)
            print(f"\nNetwork error during {operation_name}: {e}")
            print("Suggestions:")
            print("- Check your internet connection")
            print("- Verify firewall settings allow the application")
            print("- Try again in a few minutes (temporary network issues)")
            
        except Exception as e:
            self.logger.error(f"Unexpected error in {operation_name}: {e}", exc_info=True)
            print(f"\nUnexpected error during {operation_name}: {e}")
            
            # Provide specific guidance based on error type and content
            error_str = str(e).lower()
            if "api" in error_str or "riot" in error_str:
                print("This appears to be a Riot API issue.")
                print("Suggestions:")
                print("- Check your RIOT_API_KEY environment variable")
                print("- Verify your API key is valid and not expired")
                print("- Check if Riot API is experiencing downtime")
                print("- Try running in offline mode if the issue persists")
            elif "rate limit" in error_str or "429" in error_str:
                print("API rate limit exceeded.")
                print("Suggestions:")
                print("- Wait a few minutes before trying again")
                print("- The application will automatically retry with backoff")
            elif "timeout" in error_str:
                print("Request timed out.")
                print("Suggestions:")
                print("- Check your internet connection stability")
                print("- Try again - this may be a temporary issue")
            elif "memory" in error_str or "out of memory" in error_str:
                print("Memory usage issue detected.")
                print("Suggestions:")
                print("- Close other applications to free up memory")
                print("- Try with fewer players if optimizing a large group")
            elif "permission" in error_str or "access" in error_str:
                print("File access permission issue.")
                print("Suggestions:")
                print("- Run the application with appropriate permissions")
                print("- Check that data directories are writable")
            else:
                print("This might be due to system issues or corrupted data.")
                print("Suggestions:")
                print("- Try restarting the application")
                print("- Run system maintenance to clear cache")
                print("- Contact support if the problem persists")
                
            # Offer recovery options
            if "optimization" in operation_name.lower():
                print("\nRecovery options:")
                print("- Try with a smaller group of players")
                print("- Update player data and preferences")
                print("- Run system maintenance to refresh cached data")
    
    def _display_main_menu(self) -> None:
        """Display the main menu options with enhanced descriptions."""
        print("\n" + "=" * 50)
        print("MAIN MENU - League of Legends Team Optimizer")
        print("=" * 50)
        print("1. Manage Players")
        print("   └─ Add, remove, or update player information")
        print("2. Manage Role Preferences") 
        print("   └─ Set player preferences for different roles")
        print("3. Optimize Team Composition")
        print("   └─ Find optimal role assignments with champion recommendations")
        print("4. View Player Data & Champion Analysis")
        print("   └─ Detailed player stats, champion pools, and comparisons")
        print("5. System Maintenance")
        print("   └─ Cache management, diagnostics, and data validation")
        print("6. Exit")
        print()
        print("💡 New Features:")
        print("   • Champion mastery integration in optimization")
        print("   • Champion recommendations for each role assignment")
        print("   • Enhanced player analysis with champion pool depth")
        print("   • Cross-player champion analysis and comparisons")
    
    def _manage_players(self) -> None:
        """Handle player management operations."""
        while True:
            print("\n" + "-" * 30)
            print("PLAYER MANAGEMENT")
            print("-" * 30)
            print("1. Add New Player")
            print("2. Remove Player")
            print("3. Update Player Data")
            print("4. List All Players")
            print("5. Back to Main Menu")
            
            choice = input("\nEnter your choice (1-5): ").strip()
            
            if choice == "1":
                self._add_player()
            elif choice == "2":
                self._remove_player()
            elif choice == "3":
                self._update_player_data()
            elif choice == "4":
                self._list_players()
            elif choice == "5":
                break
            else:
                print("Invalid choice. Please enter a number between 1-5.")
    
    def _add_player(self) -> None:
        """Add a new player to the system."""
        print("\n" + "-" * 20)
        print("ADD NEW PLAYER")
        print("-" * 20)
        
        # Get player name
        while True:
            name = input("Enter player name: ").strip()
            if not name:
                print("Player name cannot be empty.")
                continue
            
            # Check if player already exists
            existing_player = self.data_manager.get_player_by_name(name)
            if existing_player:
                print(f"Player '{name}' already exists.")
                continue
            
            break
        
        # Get Riot ID (gameName#tagLine)
        while True:
            print("\nEnter Riot ID in format: gameName#tagLine")
            print("Example: Cheddahbeast#0w0 or PlayerName#NA1")
            riot_id = input("Riot ID: ").strip()
            
            if not riot_id:
                print("Riot ID cannot be empty.")
                continue
            
            if '#' not in riot_id:
                print("Riot ID must include the tag (e.g., PlayerName#NA1)")
                print("You can find your Riot ID in your League client profile.")
                continue
            
            # Validate Riot ID format
            game_name, tag_line = riot_id.split('#', 1)
            if not game_name or not tag_line:
                print("Invalid Riot ID format. Both game name and tag are required.")
                continue
            
            # Validate summoner exists (if API is available)
            puuid = ''
            summoner_name = riot_id  # Use Riot ID as summoner name for display
            
            if self.api_available:
                print("Validating Riot ID...")
                try:
                    summoner_data = self.riot_client.get_summoner_data(riot_id)
                    if summoner_data:
                        puuid = summoner_data.get('puuid', '')
                        game_name_from_api = summoner_data.get('gameName', game_name)
                        tag_line_from_api = summoner_data.get('tagLine', tag_line)
                        summoner_name = f"{game_name_from_api}#{tag_line_from_api}"
                        print(f"✓ Riot ID '{summoner_name}' found!")
                        break
                    else:
                        print(f"Riot ID '{riot_id}' not found. Please check the spelling and tag.")
                        print("Make sure to include the correct tag (e.g., #NA1, #EUW, etc.)")
                        retry = input("Try again? (y/n): ").strip().lower()
                        if retry != 'y':
                            return
                except Exception as e:
                    self.logger.warning(f"API validation failed for {riot_id}: {e}")
                    print(f"Warning: Could not validate Riot ID: {e}")
                    
                    if "404" in str(e) or "not found" in str(e).lower():
                        print("This Riot ID was not found. Please check:")
                        print("- Spelling of the game name")
                        print("- Correct tag (visible in your League client)")
                        print("- Make sure the account exists and has played League of Legends")
                    elif "rate limit" in str(e).lower():
                        print("API rate limit reached. Please wait a moment.")
                    elif "network" in str(e).lower() or "timeout" in str(e).lower():
                        print("Network connection issue detected.")
                    
                    use_anyway = input("Add player anyway? (y/n): ").strip().lower()
                    if use_anyway == 'y':
                        summoner_name = riot_id
                        break
                    else:
                        return
            else:
                print("⚠️  API not available - skipping Riot ID validation")
                summoner_name = riot_id
                break
        
        # Get initial role preferences (optional)
        print("\nSet initial role preferences (1-5 scale, 5 = most preferred):")
        print("Press Enter to use default (3) for any role.")
        
        preferences = {}
        for role in self.roles:
            while True:
                pref_input = input(f"{role.capitalize()}: ").strip()
                if not pref_input:
                    preferences[role] = 3  # Default neutral preference
                    break
                
                try:
                    pref_value = int(pref_input)
                    if 1 <= pref_value <= 5:
                        preferences[role] = pref_value
                        break
                    else:
                        print("Please enter a number between 1-5.")
                except ValueError:
                    print("Please enter a valid number.")
        
        # Create and save player
        player = Player(
            name=name,
            summoner_name=summoner_name,
            puuid=puuid,
            role_preferences=preferences
        )
        
        try:
            players = self.data_manager.load_player_data()
            players.append(player)
            self.data_manager.save_player_data(players)
            print(f"\n✓ Player '{name}' added successfully!")
            
            # Offer to fetch API data immediately
            if self.api_available:
                fetch_data = input("Would you like to fetch champion mastery and performance data now? (y/n): ").strip().lower()
                if fetch_data == 'y':
                    print("\nFetching player data from Riot API...")
                    success = self._fetch_player_api_data(player)
                    if success:
                        print("✓ Player data populated successfully!")
                    else:
                        print("⚠️ Some data could not be fetched, but player was added.")
        except Exception as e:
            print(f"\nError adding player: {e}")
    
    def _remove_player(self) -> None:
        """Remove a player from the system."""
        print("\n" + "-" * 15)
        print("REMOVE PLAYER")
        print("-" * 15)
        
        players = self.data_manager.load_player_data()
        if not players:
            print("No players found.")
            return
        
        # Display players
        print("\nCurrent players:")
        for i, player in enumerate(players, 1):
            print(f"{i}. {player.name} ({player.summoner_name})")
        
        # Get player selection
        while True:
            try:
                choice = input(f"\nEnter player number to remove (1-{len(players)}) or 0 to cancel: ").strip()
                choice_num = int(choice)
                
                if choice_num == 0:
                    return
                elif 1 <= choice_num <= len(players):
                    player_to_remove = players[choice_num - 1]
                    break
                else:
                    print(f"Please enter a number between 1-{len(players)} or 0 to cancel.")
            except ValueError:
                print("Please enter a valid number.")
        
        # Confirm removal
        confirm = input(f"\nAre you sure you want to remove '{player_to_remove.name}'? (y/n): ").strip().lower()
        if confirm == 'y':
            try:
                success = self.data_manager.delete_player(player_to_remove.name)
                if success:
                    print(f"✓ Player '{player_to_remove.name}' removed successfully!")
                else:
                    print(f"Error: Player '{player_to_remove.name}' not found.")
            except Exception as e:
                print(f"Error removing player: {e}")
    
    def _update_player_data(self) -> None:
        """Update existing player data."""
        print("\n" + "-" * 20)
        print("UPDATE PLAYER DATA")
        print("-" * 20)
        
        players = self.data_manager.load_player_data()
        if not players:
            print("No players found.")
            return
        
        # Select player
        player = self._select_player(players, "update")
        if not player:
            return
        
        print(f"\nUpdating data for: {player.name}")
        print("1. Update summoner name")
        print("2. Refresh performance data from API")
        print("3. Cancel")
        
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == "1":
            new_summoner = input(f"Current summoner name: {player.summoner_name}\nEnter new summoner name: ").strip()
            if new_summoner and new_summoner != player.summoner_name:
                player.summoner_name = new_summoner
                player.puuid = ""  # Reset PUUID to force re-validation
                self.data_manager.update_player(player)
                print("✓ Summoner name updated!")
        
        elif choice == "2":
            print("Refreshing performance data from Riot API...")
            try:
                success = self._fetch_player_api_data(player)
                if success:
                    print("✓ Performance data refreshed!")
                else:
                    print("⚠️ Some data could not be fetched, but available data was updated.")
            except Exception as e:
                print(f"Error refreshing data: {e}")
    
    def _list_players(self) -> None:
        """Display all players with their basic information."""
        print("\n" + "-" * 15)
        print("ALL PLAYERS")
        print("-" * 15)
        
        players = self.data_manager.load_player_data()
        if not players:
            print("No players found.")
            return
        
        for i, player in enumerate(players, 1):
            print(f"\n{i}. {player.name}")
            print(f"   Summoner: {player.summoner_name}")
            print(f"   Last Updated: {player.last_updated.strftime('%Y-%m-%d %H:%M') if player.last_updated else 'Never'}")
            
            # Show top preferred roles
            if player.role_preferences:
                sorted_prefs = sorted(player.role_preferences.items(), key=lambda x: x[1], reverse=True)
                top_roles = [f"{role}({score})" for role, score in sorted_prefs[:3]]
                print(f"   Top Preferences: {', '.join(top_roles)}")
    
    def _manage_preferences(self) -> None:
        """Handle role preference management."""
        print("\n" + "-" * 25)
        print("ROLE PREFERENCE MANAGEMENT")
        print("-" * 25)
        
        players = self.data_manager.load_player_data()
        if not players:
            print("No players found. Please add players first.")
            return
        
        # Select player
        player = self._select_player(players, "manage preferences for")
        if not player:
            return
        
        self._update_player_preferences(player)
    
    def _update_player_preferences(self, player: Player) -> None:
        """Update role preferences for a specific player."""
        print(f"\n" + "-" * 30)
        print(f"PREFERENCES FOR {player.name.upper()}")
        print("-" * 30)
        
        print("Current preferences (1=least preferred, 5=most preferred):")
        for role in self.roles:
            current_pref = player.role_preferences.get(role, 3)
            print(f"  {role.capitalize()}: {current_pref}")
        
        print("\nUpdate preferences:")
        print("Enter new values (1-5) or press Enter to keep current value.")
        
        new_preferences = {}
        for role in self.roles:
            current_pref = player.role_preferences.get(role, 3)
            
            while True:
                pref_input = input(f"{role.capitalize()} [{current_pref}]: ").strip()
                
                if not pref_input:
                    new_preferences[role] = current_pref
                    break
                
                try:
                    pref_value = int(pref_input)
                    if 1 <= pref_value <= 5:
                        new_preferences[role] = pref_value
                        break
                    else:
                        print("Please enter a number between 1-5.")
                except ValueError:
                    print("Please enter a valid number.")
        
        # Save updated preferences
        try:
            self.data_manager.update_preferences(player.name, new_preferences)
            print(f"\n✓ Preferences updated for {player.name}!")
        except Exception as e:
            print(f"\nError updating preferences: {e}")
    
    def _optimize_team(self) -> None:
        """Run team optimization and display results."""
        print("\n" + "-" * 25)
        print("TEAM COMPOSITION OPTIMIZER")
        print("-" * 25)
        
        players = self.data_manager.load_player_data()
        if len(players) < 5:
            print(f"Need at least 5 players for optimization. Currently have {len(players)} players.")
            print("Please add more players first.")
            return
        
        # Select players for optimization
        selected_players = self._select_players_for_optimization(players)
        if not selected_players:
            return
        
        print(f"\nOptimizing team composition for {len(selected_players)} players...")
        
        # Warn about limitations if API is not available
        if not self.api_available:
            print("⚠️  Running in offline mode - using cached data and preferences only")
            print("   Results may be less accurate without recent performance data")
        else:
            print("This may take a moment while we fetch performance data...")
        
        try:
            # Run optimization with progress indication
            print("Starting optimization...")
            result = self.optimizer.optimize_team(selected_players)
            print("✓ Optimization completed successfully!")
            
            # Display results
            self._display_optimization_results(result)
            
            # Offer to show alternatives
            if len(result.assignments) > 1:
                show_alternatives = input("\nWould you like to see alternative compositions? (y/n): ").strip().lower()
                if show_alternatives == 'y':
                    self._display_alternative_assignments(result)
            
            # Offer advanced alternatives
            show_advanced = input("\nWould you like to see advanced alternative strategies? (y/n): ").strip().lower()
            if show_advanced == 'y':
                self._generate_advanced_alternatives(selected_players, result)
        
        except Exception as e:
            self.logger.error(f"Optimization failed: {e}", exc_info=True)
            print(f"\nOptimization failed: {e}")
            
            # Provide specific guidance based on error type
            if "API" in str(e) or "network" in str(e).lower():
                print("\nThis appears to be an API or network issue.")
                print("Suggestions:")
                print("- Check your internet connection")
                print("- Verify your Riot API key is valid")
                print("- Try again in a few minutes (rate limiting)")
            elif "insufficient data" in str(e).lower():
                print("\nInsufficient data for optimization.")
                print("Suggestions:")
                print("- Add more players to the system")
                print("- Update player preferences")
                print("- Run system maintenance to refresh cached data")
            elif "no valid assignment" in str(e).lower():
                print("\nNo valid team assignment found.")
                print("This might be due to conflicting constraints or preferences.")
            else:
                print("This might be due to insufficient data or system issues.")
                print("Try running system maintenance or contact support.")
    
    def _select_players_for_optimization(self, players: List[Player]) -> Optional[List[Player]]:
        """Select players for team optimization."""
        if len(players) == 5:
            print("Using all 5 available players for optimization.")
            return players
        
        print(f"\nAvailable players ({len(players)}):")
        for i, player in enumerate(players, 1):
            print(f"{i}. {player.name} ({player.summoner_name})")
        
        if len(players) > 5:
            print(f"\nYou have {len(players)} players. Select players for optimization:")
            print("Enter player numbers separated by spaces (e.g., 1 3 5 7 9)")
            print("Or press Enter to use all players (will find best 5-player combinations)")
            
            selection = input("\nYour selection: ").strip()
            
            if not selection:
                return players  # Use all players
            
            try:
                indices = [int(x) - 1 for x in selection.split()]
                if any(i < 0 or i >= len(players) for i in indices):
                    print("Invalid player numbers.")
                    return None
                
                selected = [players[i] for i in indices]
                if len(selected) < 5:
                    print(f"Need at least 5 players, selected {len(selected)}.")
                    return None
                
                return selected
                
            except ValueError:
                print("Invalid input format.")
                return None
        
        return players
    
    def _display_optimization_results(self, result: OptimizationResult) -> None:
        """Display the optimization results in a formatted way."""
        best = result.best_assignment
        
        print("\n" + "=" * 50)
        print("OPTIMAL TEAM COMPOSITION")
        print("=" * 50)
        
        print(f"Total Score: {best.total_score:.2f}")
        print(f"Optimization Time: {result.optimization_time:.2f} seconds")
        print()
        
        # Role assignments with champion recommendations
        print("Role Assignments:")
        print("-" * 20)
        
        for role in self.roles:
            player_name = best.assignments.get(role, "Unassigned")
            individual_score = best.individual_scores.get(player_name, 0)
            
            print(f"{role.upper():8} | {player_name:15} | Score: {individual_score:.2f}")
            
            # Display champion recommendations for this role
            if role in best.champion_recommendations and best.champion_recommendations[role]:
                print(f"         | Recommended Champions:")
                for i, rec in enumerate(best.champion_recommendations[role][:3], 1):  # Show top 3
                    mastery_bar = "█" * rec.mastery_level + "░" * (7 - rec.mastery_level)
                    suitability_desc = self._get_suitability_description(rec.role_suitability)
                    print(f"         |   {i}. {rec.champion_name}")
                    print(f"         |      Level {rec.mastery_level} [{mastery_bar}] | {rec.mastery_points:,} pts | {suitability_desc}")
            else:
                print(f"         | No champion recommendations available")
            print()
        
        # Show synergy highlights
        if best.synergy_scores:
            print("Key Synergies:")
            print("-" * 15)
            sorted_synergies = sorted(best.synergy_scores.items(), key=lambda x: x[1], reverse=True)
            for (player1, player2), synergy in sorted_synergies[:3]:  # Top 3 synergies
                print(f"  {player1} + {player2}: {synergy:.2f}")
            print()
        # Detailed explanation
        if best.explanation:
            print("DETAILED EXPLANATION:")
            print("-" * 20)
            print(best.explanation)

    
    def _display_performance_trends(self, assignment: TeamAssignment) -> None:
        """Display performance trend analysis for the team assignment."""
        print("\n" + "=" * 50)
        print("PERFORMANCE TREND ANALYSIS")
        print("=" * 50)
        
        players = self.data_manager.load_player_data()
        player_dict = {p.name: p for p in players}
        
        for role, player_name in assignment.assignments.items():
            if player_name not in player_dict:
                continue
            
            player = player_dict[player_name]
            trend_analysis = self.performance_calculator.analyze_performance_trends(player, role)
            
            print(f"\n{player_name} ({role.upper()}):")
            print(f"  Trend: {trend_analysis['direction'].capitalize()} ({trend_analysis['trend']})")
            print(f"  Confidence: {trend_analysis['confidence']:.0%}")
            print(f"  Recent Form: {trend_analysis['recent_form']:+.2f}")
            print(f"  Matches Analyzed: {trend_analysis['matches_analyzed']}")
            print(f"  Recommendation: {trend_analysis['recommendation']}")
    
    def _display_champion_analysis(self, assignment: TeamAssignment) -> None:
        """Display detailed champion analysis for the team assignment."""
        print("\n" + "=" * 50)
        print("DETAILED CHAMPION ANALYSIS")
        print("=" * 50)
        
        players = self.data_manager.load_player_data()
        player_dict = {p.name: p for p in players}
        
        for role, player_name in assignment.assignments.items():
            if player_name not in player_dict:
                continue
            
            player = player_dict[player_name]
            print(f"\n{player_name} - {role.upper()}:")
            print("-" * 30)
            
            # Show champion pool analysis for this role
            pool_analysis = self.performance_calculator.analyze_champion_pool_depth(player, role)
            
            print(f"Champion Pool Size: {pool_analysis['pool_size']} champions")
            print(f"Average Mastery: {pool_analysis['average_mastery']:.2f}")
            print(f"Pool Depth Score: {pool_analysis['depth_score']:.2f}")
            print(f"Assessment: {pool_analysis['recommendation']}")
            
            # Show top champions for this role
            if pool_analysis['top_champions']:
                print(f"\nTop Champions for {role}:")
                for i, champ in enumerate(pool_analysis['top_champions'], 1):
                    mastery_bar = "█" * champ['mastery_level'] + "░" * (7 - champ['mastery_level'])
                    print(f"  {i}. {champ['name']} | Level {champ['mastery_level']} [{mastery_bar}] | {champ['mastery_points']:,} pts")
            
            # Show recommendations from optimization
            if role in assignment.champion_recommendations:
                recommendations = assignment.champion_recommendations[role]
                if recommendations:
                    print(f"\nOptimization Recommendations:")
                    for i, rec in enumerate(recommendations, 1):
                        confidence_desc = self._get_confidence_description(rec.confidence)
                        suitability_desc = self._get_suitability_description(rec.role_suitability)
                        print(f"  {i}. {rec.champion_name}")
                        print(f"     Mastery: Level {rec.mastery_level} ({rec.mastery_points:,} points)")
                        print(f"     Role Fit: {suitability_desc} ({rec.role_suitability:.0%})")
                        print(f"     Confidence: {confidence_desc} ({rec.confidence:.0%})")
    
    def _get_confidence_description(self, confidence: float) -> str:
        """Convert confidence score to descriptive text."""
        if confidence >= 0.8:
            return "Very High"
        elif confidence >= 0.6:
            return "High"
        elif confidence >= 0.4:
            return "Medium"
        elif confidence >= 0.2:
            return "Low"
        else:
            return "Very Low"
    
    def _get_suitability_description(self, suitability: float) -> str:
        """Convert role suitability score to descriptive text."""
        if suitability >= 0.9:
            return "Perfect"
        elif suitability >= 0.7:
            return "Excellent"
        elif suitability >= 0.5:
            return "Good"
        elif suitability >= 0.3:
            return "Fair"
        else:
            return "Poor"
    
    def _display_alternative_assignments(self, result: OptimizationResult) -> None:
        """Display alternative team assignments."""
        alternatives = self.optimizer.get_alternative_assignments(result, 3)
        
        if not alternatives:
            print("\nNo alternative compositions available.")
            return
        
        print("\n" + "=" * 50)
        print("ALTERNATIVE TEAM COMPOSITIONS")
        print("=" * 50)
        
        for i, alt in enumerate(alternatives, 1):
            print(f"\nAlternative #{i} (Score: {alt.total_score:.2f}):")
            print("-" * 30)
            
            for role in self.roles:
                player_name = alt.assignments.get(role, "Unassigned")
                individual_score = alt.individual_scores.get(player_name, 0)
                print(f"  {role.upper():8} | {player_name:15} | Score: {individual_score:.2f}")
            
            # Show comparison with primary assignment
            comparison = self.optimizer.compare_assignments(result.best_assignment, alt)
            print(f"\nComparison with primary:")
            print(comparison)
            
            if i < len(alternatives):
                input("\nPress Enter to see next alternative...")
    
    def _generate_advanced_alternatives(self, selected_players: List[Player], 
                                      primary_result: OptimizationResult) -> None:
        """Generate and display advanced alternative compositions."""
        print("\nGenerating advanced alternative compositions...")
        
        try:
            alternatives = self.optimizer.generate_alternative_compositions(
                selected_players, primary_result
            )
            
            if not alternatives:
                print("No significantly different alternatives found.")
                return
            
            print(f"\nFound {len(alternatives)} alternative strategies:")
            print("=" * 50)
            
            strategy_names = [
                "Preference-Focused",
                "Performance-Focused", 
                "Synergy-Focused",
                "Role-Balanced",
                "Hybrid Approach"
            ]
            
            for i, alt in enumerate(alternatives):
                strategy_name = strategy_names[i] if i < len(strategy_names) else f"Alternative {i+1}"
                
                print(f"\n{strategy_name} (Score: {alt.total_score:.2f}):")
                print("-" * 40)
                
                for role in self.roles:
                    player_name = alt.assignments.get(role, "Unassigned")
                    individual_score = alt.individual_scores.get(player_name, 0)
                    print(f"  {role.upper():8} | {player_name:15} | Score: {individual_score:.2f}")
                
                # Show key differences
                score_diff = alt.total_score - primary_result.best_assignment.total_score
                print(f"\nScore difference: {score_diff:+.2f}")
                
                if i < len(alternatives) - 1:
                    input("\nPress Enter to see next strategy...")
        
        except Exception as e:
            print(f"Error generating alternatives: {e}")
    
    def _display_comprehensive_player_analysis(self) -> None:
        """Display comprehensive analysis for all players."""
        print("\n" + "-" * 40)
        print("COMPREHENSIVE PLAYER ANALYSIS")
        print("-" * 40)
        
        players = self.data_manager.load_player_data()
        if not players:
            print("No players found.")
            return
        
        # Select player for analysis
        player = self._select_player(players, "analyze")
        if not player:
            return
        
        print(f"\nAnalyzing {player.name}...")
        analysis = self.performance_calculator.get_comprehensive_player_analysis(player)
        
        print(f"\n" + "=" * 50)
        print(f"ANALYSIS FOR {player.name.upper()}")
        print("=" * 50)
        
        # Role performance scores
        print("\nRole Performance Scores:")
        print("-" * 25)
        for role, score in analysis["role_scores"].items():
            trend = analysis["role_trends"][role]
            trend_indicator = "↗" if trend["direction"] == "improving" else "↘" if trend["direction"] == "declining" else "→"
            print(f"  {role.capitalize():8} | {score:.2f} {trend_indicator} | {trend['recommendation'][:50]}...")
        
        # Strengths and weaknesses
        if analysis["strengths"]:
            print(f"\nStrengths:")
            for strength in analysis["strengths"]:
                print(f"  ✓ {strength}")
        
        if analysis["weaknesses"]:
            print(f"\nAreas for Improvement:")
            for weakness in analysis["weaknesses"]:
                print(f"  ⚠ {weakness}")
        
        # Recommendations
        print(f"\nRecommendations:")
        for rec in analysis["recommendations"]:
            print(f"  • {rec}")
    
    def _system_maintenance(self) -> None:
        """Handle system maintenance operations."""
        while True:
            print("\n" + "-" * 25)
            print("SYSTEM MAINTENANCE")
            print("-" * 25)
            print("1. Clear Expired Cache")
            print("2. View Cache Statistics")
            print("3. Optimize Cache")
            print("4. Player Analysis")
            print("5. Back to Main Menu")
            
            choice = input("\nEnter your choice (1-5): ").strip()
            
            if choice == "1":
                self._clear_expired_cache()
            elif choice == "2":
                self._view_cache_statistics()
            elif choice == "3":
                self._optimize_cache()
            elif choice == "4":
                self._display_comprehensive_player_analysis()
            elif choice == "5":
                break
            else:
                print("Invalid choice. Please enter a number between 1-5.")
    
    def _clear_expired_cache(self) -> None:
        """Clear expired cache files."""
        print("\nClearing expired cache files...")
        try:
            removed_count = self.data_manager.clear_expired_cache()
            print(f"✓ Removed {removed_count} expired cache files")
        except Exception as e:
            print(f"Error clearing cache: {e}")
    
    def _view_cache_statistics(self) -> None:
        """Display cache statistics."""
        print("\n" + "-" * 30)
        print("CACHE STATISTICS")
        print("-" * 30)
        
        try:
            stats = self.data_manager.get_cache_statistics()
            
            print(f"Total Files: {stats['total_files']}")
            print(f"Total Size: {stats['total_size_mb']:.2f} MB")
            print(f"Valid Files: {stats['valid_files']}")
            print(f"Expired Files: {stats['expired_files']}")
            print(f"Corrupted Files: {stats['corrupted_files']}")
            
            if stats['oldest_entry']:
                print(f"Oldest Entry: {stats['oldest_entry']}")
            if stats['newest_entry']:
                print(f"Newest Entry: {stats['newest_entry']}")
            
            if stats['cache_keys']:
                print(f"\nCached Data Types:")
                for key in sorted(set(k.split('_')[0] for k in stats['cache_keys'])):
                    count = sum(1 for k in stats['cache_keys'] if k.startswith(key))
                    print(f"  {key}: {count} entries")
        
        except Exception as e:
            print(f"Error retrieving cache statistics: {e}")
    
    def _optimize_cache(self) -> None:
        """Optimize cache performance."""
        print("\nOptimizing cache...")
        try:
            # Clear expired files
            removed = self.data_manager.clear_expired_cache()
            
            # Clean up if needed
            self.data_manager.cleanup_cache_if_needed()
            
            # Get final statistics
            stats = self.data_manager.get_cache_statistics()
            
            print(f"✓ Cache optimization completed")
            print(f"  Removed {removed} expired files")
            print(f"  Final cache size: {stats['total_size_mb']:.2f} MB")
            print(f"  Active cache entries: {stats['valid_files']}")
        
        except Exception as e:
            print(f"Error optimizing cache: {e}")
            print()
        
        # Detailed explanation
        if best.explanation:
            print("DETAILED EXPLANATION:")
            print("-" * 20)
            print(best.explanation)
    
    def _view_player_data(self) -> None:
        """Display detailed player data and statistics with champion analysis options."""
        while True:
            print("\n" + "-" * 20)
            print("PLAYER DATA VIEWER")
            print("-" * 20)
            print("1. View Individual Player Details")
            print("2. Champion Analysis Across All Players")
            print("3. Role Suitability Analysis")
            print("4. Champion Pool Comparison")
            print("5. Back to Main Menu")
            
            choice = input("\nEnter your choice (1-5): ").strip()
            
            if choice == "1":
                self._view_individual_player_data()
            elif choice == "2":
                self._champion_analysis_all_players()
            elif choice == "3":
                self._role_suitability_analysis()
            elif choice == "4":
                self._champion_pool_comparison()
            elif choice == "5":
                break
            else:
                print("Invalid choice. Please enter a number between 1-5.")
    
    def _view_individual_player_data(self) -> None:
        """Display detailed data for a single player."""
        players = self.data_manager.load_player_data()
        if not players:
            print("No players found.")
            return
        
        player = self._select_player(players, "view data for")
        if not player:
            return
        
        self._display_detailed_player_info(player)
        
        # Offer additional analysis options
        print("\nAdditional Analysis Options:")
        print("1. Champion recommendations for specific role")
        print("2. Compare with another player")
        print("3. Performance trends (if available)")
        print("4. Return to player data menu")
        
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == "1":
            self._show_champion_recommendations_for_role(player)
        elif choice == "2":
            self._compare_players(player, players)
        elif choice == "3":
            self._show_performance_trends(player)
        elif choice == "4":
            return
    
    def _show_champion_recommendations_for_role(self, player: Player) -> None:
        """Show champion recommendations for a specific role."""
        print("\nSelect role for champion recommendations:")
        for i, role in enumerate(self.roles, 1):
            print(f"{i}. {role.capitalize()}")
        
        while True:
            try:
                choice = input(f"\nEnter role number (1-{len(self.roles)}): ").strip()
                choice_num = int(choice)
                
                if 1 <= choice_num <= len(self.roles):
                    selected_role = self.roles[choice_num - 1]
                    break
                else:
                    print(f"Please enter a number between 1-{len(self.roles)}.")
            except ValueError:
                print("Please enter a valid number.")
        
        print(f"\nChampion Recommendations for {player.name} - {selected_role.capitalize()}:")
        print("-" * 50)
        
        role_champions = player.get_top_champions_for_role(selected_role, count=10)
        
        if role_champions:
            for i, mastery in enumerate(role_champions, 1):
                mastery_bar = "█" * mastery.mastery_level + "░" * (7 - mastery.mastery_level)
                
                # Calculate recommendation strength
                if mastery.mastery_level >= 6:
                    strength = "Excellent"
                elif mastery.mastery_level >= 4:
                    strength = "Good"
                elif mastery.mastery_level >= 2:
                    strength = "Fair"
                else:
                    strength = "Learning"
                
                print(f"{i:2}. {mastery.champion_name}")
                print(f"    Level {mastery.mastery_level} [{mastery_bar}] | {mastery.mastery_points:,} points")
                print(f"    Recommendation: {strength}")
                if mastery.chest_granted:
                    print(f"    ✓ S- grade achieved")
                print()
        else:
            print(f"No champions available for {selected_role}.")
            print("This player may need to expand their champion pool for this role.")
    
    def _compare_players(self, player1: Player, all_players: List[Player]) -> None:
        """Compare two players' champion pools and preferences."""
        print(f"\nCompare {player1.name} with:")
        other_players = [p for p in all_players if p.name != player1.name]
        
        if not other_players:
            print("No other players available for comparison.")
            return
        
        player2 = self._select_player(other_players, "compare with")
        if not player2:
            return
        
        print(f"\n" + "=" * 60)
        print(f"PLAYER COMPARISON: {player1.name.upper()} vs {player2.name.upper()}")
        print("=" * 60)
        
        # Compare role preferences
        print("\nRole Preferences Comparison:")
        print("-" * 30)
        print(f"{'Role':<10} | {player1.name:<15} | {player2.name:<15} | Difference")
        print("-" * 60)
        
        for role in self.roles:
            pref1 = player1.role_preferences.get(role, 3)
            pref2 = player2.role_preferences.get(role, 3)
            diff = pref1 - pref2
            diff_str = f"{diff:+.0f}" if diff != 0 else "Same"
            
            print(f"{role.capitalize():<10} | {pref1:<15} | {pref2:<15} | {diff_str}")
        
        # Compare champion pools
        print(f"\nChampion Pool Comparison:")
        print("-" * 25)
        
        for role in self.roles:
            champs1 = player1.get_top_champions_for_role(role, count=5)
            champs2 = player2.get_top_champions_for_role(role, count=5)
            
            print(f"\n{role.capitalize()}:")
            print(f"  {player1.name}: {len(champs1)} champions")
            print(f"  {player2.name}: {len(champs2)} champions")
            
            # Find common champions
            champ_names1 = {c.champion_name for c in champs1}
            champ_names2 = {c.champion_name for c in champs2}
            common = champ_names1.intersection(champ_names2)
            
            if common:
                print(f"  Common: {', '.join(sorted(common))}")
            else:
                print(f"  No common champions in top 5")
        
        # Overall statistics
        total1 = len(player1.champion_masteries)
        total2 = len(player2.champion_masteries)
        mastery7_1 = sum(1 for m in player1.champion_masteries.values() if m.mastery_level == 7)
        mastery7_2 = sum(1 for m in player2.champion_masteries.values() if m.mastery_level == 7)
        
        print(f"\nOverall Statistics:")
        print(f"  Total Champions: {player1.name} ({total1}) vs {player2.name} ({total2})")
        print(f"  Mastery 7 Champions: {player1.name} ({mastery7_1}) vs {player2.name} ({mastery7_2})")
    
    def _show_performance_trends(self, player: Player) -> None:
        """Show performance trends for a player if available."""
        print(f"\nPerformance Trends for {player.name}:")
        print("-" * 30)
        
        if player.performance_cache:
            for role, perf_data in player.performance_cache.items():
                if isinstance(perf_data, dict) and perf_data:
                    print(f"\n{role.capitalize()}:")
                    for key, value in perf_data.items():
                        if isinstance(value, float):
                            print(f"  {key}: {value:.2f}")
                        else:
                            print(f"  {key}: {value}")
        else:
            print("No performance data available.")
            print("Run team optimization to fetch and cache performance data.")
    
    def _champion_analysis_all_players(self) -> None:
        """Analyze champion data across all players."""
        players = self.data_manager.load_player_data()
        if not players:
            print("No players found.")
            return
        
        print("\n" + "=" * 50)
        print("CHAMPION ANALYSIS - ALL PLAYERS")
        print("=" * 50)
        
        # Collect all champion data
        all_champions = {}
        role_coverage = {role: set() for role in self.roles}
        
        for player in players:
            for champion_id, mastery in player.champion_masteries.items():
                if champion_id not in all_champions:
                    all_champions[champion_id] = {
                        'name': mastery.champion_name,
                        'players': [],
                        'total_points': 0,
                        'max_level': 0,
                        'roles': set(mastery.primary_roles)
                    }
                
                all_champions[champion_id]['players'].append({
                    'player': player.name,
                    'level': mastery.mastery_level,
                    'points': mastery.mastery_points
                })
                all_champions[champion_id]['total_points'] += mastery.mastery_points
                all_champions[champion_id]['max_level'] = max(
                    all_champions[champion_id]['max_level'], 
                    mastery.mastery_level
                )
                
                # Track role coverage
                for role in mastery.primary_roles:
                    if role in role_coverage:
                        role_coverage[role].add(champion_id)
        
        # Most popular champions
        print("\nMost Popular Champions (by total mastery points):")
        print("-" * 45)
        popular_champions = sorted(
            all_champions.items(),
            key=lambda x: x[1]['total_points'],
            reverse=True
        )[:10]
        
        for i, (champ_id, data) in enumerate(popular_champions, 1):
            player_count = len(data['players'])
            print(f"{i:2}. {data['name']}")
            print(f"    {player_count} player{'s' if player_count != 1 else ''} | {data['total_points']:,} total points | Max level {data['max_level']}")
        
        # Role coverage analysis
        print(f"\nRole Coverage Analysis:")
        print("-" * 25)
        for role in self.roles:
            champion_count = len(role_coverage[role])
            coverage_desc = "Excellent" if champion_count >= 20 else "Good" if champion_count >= 10 else "Limited"
            print(f"{role.capitalize()}: {champion_count} champions ({coverage_desc})")
        
        # Team champion overlap
        print(f"\nTeam Champion Overlap:")
        print("-" * 22)
        overlap_champions = [(champ_id, data) for champ_id, data in all_champions.items() 
                           if len(data['players']) >= 2]
        overlap_champions.sort(key=lambda x: len(x[1]['players']), reverse=True)
        
        for champ_id, data in overlap_champions[:10]:
            player_names = [p['player'] for p in data['players']]
            print(f"{data['name']}: {', '.join(player_names)}")
    
    def _role_suitability_analysis(self) -> None:
        """Analyze role suitability across all players."""
        players = self.data_manager.load_player_data()
        if not players:
            print("No players found.")
            return
        
        print("\n" + "=" * 50)
        print("ROLE SUITABILITY ANALYSIS")
        print("=" * 50)
        
        # Calculate role suitability scores
        role_suitability = {}
        
        for player in players:
            role_suitability[player.name] = {}
            
            for role in self.roles:
                # Combine preference and mastery scores
                preference_score = player.role_preferences.get(role, 3) / 5.0  # Normalize to 0-1
                mastery_score = min(player.get_mastery_score_for_role(role) / 100000, 1.0)  # Normalize
                
                # Weighted combination (60% preference, 40% mastery)
                combined_score = (preference_score * 0.6) + (mastery_score * 0.4)
                role_suitability[player.name][role] = combined_score
        
        # Display role suitability matrix
        print("\nRole Suitability Matrix (0.0 - 1.0 scale):")
        print("-" * 40)
        
        # Header
        header = f"{'Player':<15}"
        for role in self.roles:
            header += f" | {role.capitalize()[:6]:<6}"
        print(header)
        print("-" * (15 + 9 * len(self.roles)))
        
        # Player rows
        for player_name in sorted(role_suitability.keys()):
            row = f"{player_name:<15}"
            for role in self.roles:
                score = role_suitability[player_name][role]
                row += f" | {score:.2f}  "
            print(row)
        
        # Best fits for each role
        print(f"\nBest Player for Each Role:")
        print("-" * 30)
        
        for role in self.roles:
            best_player = max(role_suitability.keys(), 
                            key=lambda p: role_suitability[p][role])
            best_score = role_suitability[best_player][role]
            print(f"{role.capitalize()}: {best_player} ({best_score:.2f})")
        
        # Role competition analysis
        print(f"\nRole Competition Analysis:")
        print("-" * 28)
        
        for role in self.roles:
            # Get all players sorted by suitability for this role
            sorted_players = sorted(
                role_suitability.keys(),
                key=lambda p: role_suitability[p][role],
                reverse=True
            )
            
            top_3 = sorted_players[:3]
            scores = [role_suitability[p][role] for p in top_3]
            
            print(f"\n{role.capitalize()}:")
            for i, (player, score) in enumerate(zip(top_3, scores), 1):
                print(f"  {i}. {player}: {score:.2f}")
    
    def _champion_pool_comparison(self) -> None:
        """Compare champion pools across all players."""
        players = self.data_manager.load_player_data()
        if not players:
            print("No players found.")
            return
        
        print("\n" + "=" * 50)
        print("CHAMPION POOL COMPARISON")
        print("=" * 50)
        
        # Champion pool depth by role
        print("\nChampion Pool Depth by Role:")
        print("-" * 32)
        
        # Header
        header = f"{'Player':<15}"
        for role in self.roles:
            header += f" | {role.capitalize()[:6]:<6}"
        header += f" | {'Total':<5}"
        print(header)
        print("-" * (15 + 9 * len(self.roles) + 8))
        
        # Player rows
        for player in players:
            row = f"{player.name:<15}"
            total_champions = 0
            
            for role in self.roles:
                role_champs = len(player.get_top_champions_for_role(role, count=20))
                total_champions += role_champs
                row += f" | {role_champs:<6}"
            
            row += f" | {len(player.champion_masteries):<5}"
            print(row)
        
        # Mastery level distribution
        print(f"\nMastery Level Distribution:")
        print("-" * 30)
        
        mastery_levels = {level: 0 for level in range(1, 8)}
        
        for player in players:
            for mastery in player.champion_masteries.values():
                if mastery.mastery_level in mastery_levels:
                    mastery_levels[mastery.mastery_level] += 1
        
        for level in range(7, 0, -1):  # Show from highest to lowest
            count = mastery_levels[level]
            bar = "█" * min(count // 2, 50)  # Scale bar
            print(f"Level {level}: {count:3} {bar}")
        
        # Champion overlap analysis
        print(f"\nChampion Overlap Analysis:")
        print("-" * 27)
        
        # Find champions that multiple players have
        champion_players = {}
        for player in players:
            for champion_id, mastery in player.champion_masteries.items():
                if champion_id not in champion_players:
                    champion_players[champion_id] = {
                        'name': mastery.champion_name,
                        'players': []
                    }
                champion_players[champion_id]['players'].append(player.name)
        
        # Show champions with most overlap
        overlap_champions = [(data['name'], data['players']) 
                           for data in champion_players.values() 
                           if len(data['players']) >= 2]
        overlap_champions.sort(key=lambda x: len(x[1]), reverse=True)
        
        print(f"\nMost Shared Champions:")
        for champ_name, player_list in overlap_champions[:10]:
            print(f"{champ_name}: {len(player_list)} players ({', '.join(player_list)})")
    
    def _display_detailed_player_info(self, player: Player) -> None:
        """Display comprehensive information about a player."""
        print(f"\n" + "=" * 40)
        print(f"PLAYER DETAILS: {player.name.upper()}")
        print("=" * 40)
        
        print(f"Name: {player.name}")
        print(f"Summoner: {player.summoner_name}")
        print(f"PUUID: {player.puuid[:8]}..." if player.puuid else "PUUID: Not set")
        print(f"Last Updated: {player.last_updated.strftime('%Y-%m-%d %H:%M:%S') if player.last_updated else 'Never'}")
        
        print(f"\nROLE PREFERENCES:")
        print("-" * 20)
        sorted_prefs = sorted(player.role_preferences.items(), key=lambda x: x[1], reverse=True)
        for role, pref in sorted_prefs:
            stars = "★" * pref + "☆" * (5 - pref)
            print(f"{role.capitalize():8} | {stars} ({pref}/5)")
        
        # Champion mastery information with enhanced display
        if player.champion_masteries:
            print(f"\nCHAMPION MASTERY BY ROLE:")
            print("-" * 30)
            
            for role in self.roles:
                role_champions = player.get_top_champions_for_role(role, count=5)
                role_mastery_score = player.get_mastery_score_for_role(role)
                
                print(f"\n{role.capitalize()} (Total Score: {role_mastery_score:,.0f}):")
                
                if role_champions:
                    for i, mastery in enumerate(role_champions, 1):
                        mastery_bar = "█" * mastery.mastery_level + "░" * (7 - mastery.mastery_level)
                        # Calculate days since last played if available
                        last_played = ""
                        if mastery.last_play_time:
                            days_ago = (datetime.now() - mastery.last_play_time).days
                            if days_ago == 0:
                                last_played = " (played today)"
                            elif days_ago == 1:
                                last_played = " (played yesterday)"
                            elif days_ago < 7:
                                last_played = f" ({days_ago} days ago)"
                            elif days_ago < 30:
                                weeks_ago = days_ago // 7
                                last_played = f" ({weeks_ago} week{'s' if weeks_ago > 1 else ''} ago)"
                            else:
                                last_played = f" ({days_ago // 30} month{'s' if days_ago // 30 > 1 else ''} ago)"
                        
                        print(f"  {i}. {mastery.champion_name}{last_played}")
                        print(f"     Level {mastery.mastery_level} [{mastery_bar}] | {mastery.mastery_points:,} points")
                        if mastery.chest_granted:
                            print(f"     ✓ Chest earned | Tokens: {mastery.tokens_earned}")
                        else:
                            print(f"     ☐ Chest available | Tokens: {mastery.tokens_earned}")
                else:
                    print("  No champions available for this role")
            
            # Show overall top champions with role information
            print(f"\nTOP OVERALL CHAMPIONS:")
            print("-" * 25)
            top_overall = sorted(
                player.champion_masteries.values(),
                key=lambda x: x.mastery_points,
                reverse=True
            )[:8]
            
            for i, mastery in enumerate(top_overall, 1):
                mastery_bar = "█" * mastery.mastery_level + "░" * (7 - mastery.mastery_level)
                roles_str = ", ".join(mastery.primary_roles) if mastery.primary_roles else "Flexible"
                print(f"{i}. {mastery.champion_name} ({roles_str})")
                print(f"   Level {mastery.mastery_level} [{mastery_bar}] | {mastery.mastery_points:,} points")
            
            # Champion pool analysis
            print(f"\nCHAMPION POOL ANALYSIS:")
            print("-" * 25)
            total_champions = len(player.champion_masteries)
            mastery_7_count = sum(1 for m in player.champion_masteries.values() if m.mastery_level == 7)
            mastery_6_count = sum(1 for m in player.champion_masteries.values() if m.mastery_level == 6)
            mastery_5_count = sum(1 for m in player.champion_masteries.values() if m.mastery_level == 5)
            
            print(f"Total Champions: {total_champions}")
            print(f"Mastery 7: {mastery_7_count} champions")
            print(f"Mastery 6: {mastery_6_count} champions") 
            print(f"Mastery 5: {mastery_5_count} champions")
            
            # Role depth analysis
            print(f"\nRole Depth:")
            for role in self.roles:
                role_champs = len(player.get_top_champions_for_role(role, count=20))
                depth_desc = "Excellent" if role_champs >= 10 else "Good" if role_champs >= 5 else "Limited" if role_champs >= 2 else "Minimal"
                print(f"  {role.capitalize()}: {role_champs} champions ({depth_desc})")
        else:
            print(f"\nNo champion mastery data available.")
            print("Run optimization or update player data to fetch champion information.")
        
        # Performance data (if available)
        if player.performance_cache:
            print(f"\nPERFORMANCE DATA:")
            print("-" * 20)
            for role, perf_data in player.performance_cache.items():
                if isinstance(perf_data, dict) and perf_data:
                    print(f"{role.capitalize()}:")
                    for key, value in perf_data.items():
                        if isinstance(value, float):
                            print(f"  {key}: {value:.2f}")
                        else:
                            print(f"  {key}: {value}")
        else:
            print(f"\nNo performance data cached. Run optimization to fetch data.")
    
    def _system_maintenance(self) -> None:
        """Handle system maintenance operations."""
        while True:
            print("\n" + "-" * 30)
            print("SYSTEM MAINTENANCE")
            print("-" * 30)
            print("1. Clear expired cache")
            print("2. View system statistics")
            print("3. Cleanup cache if oversized")
            print("4. Validate player data")
            print("5. Refresh API data for all players")
            print("6. Test API connectivity")
            print("7. Export player data")
            print("8. System diagnostics")
            print("9. Back to main menu")
            
            choice = input("\nEnter your choice (1-9): ").strip()
            
            if choice == "1":
                self._clear_expired_cache()
            elif choice == "2":
                self._show_system_statistics()
            elif choice == "3":
                self._cleanup_cache()
            elif choice == "4":
                self._validate_player_data()
            elif choice == "5":
                self._refresh_all_player_data()
            elif choice == "6":
                self._test_api_connectivity()
            elif choice == "7":
                self._export_player_data()
            elif choice == "8":
                self._run_system_diagnostics()
            elif choice == "9":
                break
            else:
                print("Invalid choice. Please enter a number between 1-9.")
            
            input("\nPress Enter to continue...")
    
    def _clear_expired_cache(self) -> None:
        """Clear expired cache files."""
        try:
            print("Clearing expired cache files...")
            removed = self.data_manager.clear_expired_cache()
            print(f"✓ Removed {removed} expired cache files.")
            
            if self.riot_client:
                print("Clearing API client cache...")
                self.riot_client.clear_cache()
                print("✓ API client cache cleared.")
        except Exception as e:
            print(f"Error clearing cache: {e}")
    
    def _show_system_statistics(self) -> None:
        """Display comprehensive system statistics."""
        try:
            print("\n" + "=" * 40)
            print("SYSTEM STATISTICS")
            print("=" * 40)
            
            # Player statistics
            players = self.data_manager.load_player_data()
            print(f"Total players: {len(players)}")
            
            if players:
                # Role preference distribution
                role_counts = {role: 0 for role in self.roles}
                for player in players:
                    for role, pref in player.role_preferences.items():
                        if pref >= 4:  # High preference (4-5)
                            role_counts[role] += 1
                
                print("\nHigh preference distribution:")
                for role, count in role_counts.items():
                    print(f"  {role.capitalize()}: {count} players")
            
            # Cache statistics
            cache_size = self.data_manager.get_cache_size_mb()
            max_size = self.config.max_cache_size_mb
            print(f"\nCache size: {cache_size:.2f} MB / {max_size:.2f} MB")
            print(f"Cache directory: {self.data_manager.cache_dir}")
            
            # API status
            print(f"\nAPI Status: {'Available' if self.api_available else 'Offline'}")
            if self.api_available:
                print(f"API Key: {'Set' if self.config.riot_api_key else 'Not set'}")
                print(f"Rate limit: {self.config.riot_api_rate_limit} requests per 2 minutes")
            
            # Configuration
            print(f"\nConfiguration:")
            print(f"  Data directory: {self.config.data_directory}")
            print(f"  Cache duration: {self.config.cache_duration_hours} hours")
            print(f"  Debug mode: {self.config.debug}")
            
        except Exception as e:
            print(f"Error retrieving statistics: {e}")
    
    def _cleanup_cache(self) -> None:
        """Cleanup cache if oversized."""
        try:
            print("Checking cache size...")
            initial_size = self.data_manager.get_cache_size_mb()
            
            self.data_manager.cleanup_cache_if_needed()
            
            final_size = self.data_manager.get_cache_size_mb()
            saved = initial_size - final_size
            
            print(f"✓ Cache cleanup complete.")
            print(f"  Initial size: {initial_size:.2f} MB")
            print(f"  Final size: {final_size:.2f} MB")
            print(f"  Space saved: {saved:.2f} MB")
            
        except Exception as e:
            print(f"Error during cache cleanup: {e}")
    
    def _validate_player_data(self) -> None:
        """Validate all player data for consistency."""
        try:
            print("Validating player data...")
            players = self.data_manager.load_player_data()
            
            issues = []
            
            for player in players:
                # Check required fields
                if not player.name:
                    issues.append(f"Player has empty name")
                if not player.summoner_name:
                    issues.append(f"Player '{player.name}' has empty summoner name")
                
                # Check role preferences
                if not player.role_preferences:
                    issues.append(f"Player '{player.name}' has no role preferences")
                else:
                    for role in self.roles:
                        if role not in player.role_preferences:
                            issues.append(f"Player '{player.name}' missing preference for {role}")
                        else:
                            pref = player.role_preferences[role]
                            if not isinstance(pref, int) or not 1 <= pref <= 5:
                                issues.append(f"Player '{player.name}' has invalid {role} preference: {pref}")
            
            if issues:
                print(f"Found {len(issues)} issues:")
                for issue in issues:
                    print(f"  - {issue}")
            else:
                print("✓ All player data is valid.")
                
        except Exception as e:
            print(f"Error validating player data: {e}")
    
    def _refresh_all_player_data(self) -> None:
        """Refresh API data for all players."""
        if not self.api_available:
            print("API not available - cannot refresh player data.")
            return
        
        try:
            players = self.data_manager.load_player_data()
            if not players:
                print("No players found.")
                return
            
            print(f"Refreshing data for {len(players)} players...")
            
            success_count = 0
            error_count = 0
            
            for i, player in enumerate(players, 1):
                print(f"Processing {i}/{len(players)}: {player.name}...")
                
                try:
                    # Attempt to refresh summoner data
                    if player.summoner_name:
                        summoner_data = self.riot_client.get_summoner_data(player.summoner_name)
                        if summoner_data:
                            player.puuid = summoner_data.get('puuid', player.puuid)
                            player.last_updated = datetime.now()
                            success_count += 1
                        else:
                            print(f"  Warning: No data found for {player.summoner_name}")
                            error_count += 1
                    else:
                        print(f"  Skipping {player.name} - no summoner name")
                        error_count += 1
                        
                except Exception as e:
                    print(f"  Error refreshing {player.name}: {e}")
                    error_count += 1
            
            # Save updated player data
            if success_count > 0:
                self.data_manager.save_player_data(players)
            
            print(f"\n✓ Refresh complete:")
            print(f"  Successfully updated: {success_count}")
            print(f"  Errors: {error_count}")
            
        except Exception as e:
            print(f"Error refreshing player data: {e}")
    
    def _test_api_connectivity(self) -> None:
        """Test API connectivity and functionality."""
        if not self.api_available:
            print("API client not available.")
            return
        
        print("Testing API connectivity...")
        
        try:
            # Test with a known summoner (you might want to use a test account)
            test_riot_id = "Riot Phreak#NA1"  # Riot employee, should always exist
            
            print(f"Testing with: {test_riot_id}")
            
            summoner_data = self.riot_client.get_summoner_data(test_riot_id)
            
            if summoner_data:
                print("✓ API connectivity test successful!")
                print(f"  Retrieved data for: {summoner_data.get('gameName', 'Unknown')}#{summoner_data.get('tagLine', 'Unknown')}")
                print(f"  Summoner level: {summoner_data.get('summonerLevel', 'Unknown')}")
            else:
                print("⚠️  API responded but returned no data")
                
        except Exception as e:
            print(f"✗ API connectivity test failed: {e}")
            
            # Provide specific guidance
            error_str = str(e).lower()
            if "401" in error_str or "unauthorized" in error_str:
                print("  Issue: Invalid API key")
                print("  Solution: Check your RIOT_API_KEY environment variable")
            elif "403" in error_str or "forbidden" in error_str:
                print("  Issue: API key lacks required permissions")
                print("  Solution: Verify your API key is for the correct application")
            elif "429" in error_str or "rate limit" in error_str:
                print("  Issue: Rate limit exceeded")
                print("  Solution: Wait a few minutes and try again")
            elif "timeout" in error_str or "network" in error_str:
                print("  Issue: Network connectivity problem")
                print("  Solution: Check your internet connection")
            else:
                print("  Check your API key and network connection")
    
    def _export_player_data(self) -> None:
        """Export player data to a backup file."""
        try:
            players = self.data_manager.load_player_data()
            if not players:
                print("No players found to export.")
                return
            
            # Create export filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_file = Path(self.config.data_directory) / f"player_export_{timestamp}.json"
            
            # Export data
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'player_count': len(players),
                'players': [
                    {
                        'name': player.name,
                        'summoner_name': player.summoner_name,
                        'puuid': player.puuid,
                        'role_preferences': player.role_preferences,
                        'last_updated': player.last_updated.isoformat() if player.last_updated else None
                    }
                    for player in players
                ]
            }
            
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            print(f"✓ Player data exported to: {export_file}")
            print(f"  Exported {len(players)} players")
            
        except Exception as e:
            print(f"Error exporting player data: {e}")
    
    def _run_system_diagnostics(self) -> None:
        """Run comprehensive system diagnostics."""
        print("\n" + "=" * 40)
        print("SYSTEM DIAGNOSTICS")
        print("=" * 40)
        
        # Check Python version
        print(f"Python version: {sys.version}")
        
        # Check required packages
        print("\nRequired packages:")
        packages = ['requests', 'numpy', 'scipy']
        for package in packages:
            try:
                module = __import__(package)
                version = getattr(module, '__version__', 'Unknown')
                print(f"  ✓ {package}: {version}")
            except ImportError:
                print(f"  ✗ {package}: Not installed")
        
        # Check directories
        print("\nDirectories:")
        directories = [
            ('Data', self.config.data_directory),
            ('Cache', self.config.cache_directory)
        ]
        
        for name, path in directories:
            dir_path = Path(path)
            if dir_path.exists():
                if dir_path.is_dir():
                    print(f"  ✓ {name}: {path} (exists)")
                else:
                    print(f"  ⚠️  {name}: {path} (exists but not a directory)")
            else:
                print(f"  ✗ {name}: {path} (does not exist)")
        
        # Check file permissions
        print("\nFile permissions:")
        try:
            test_file = Path(self.config.data_directory) / ".permission_test"
            test_file.write_text("test")
            test_file.unlink()
            print("  ✓ Data directory: Writable")
        except Exception as e:
            print(f"  ✗ Data directory: Not writable ({e})")
        
        # Check configuration
        print("\nConfiguration:")
        config_items = [
            ('API Key', 'Set' if self.config.riot_api_key else 'Not set'),
            ('Debug mode', self.config.debug),
            ('Cache duration', f"{self.config.cache_duration_hours} hours"),
            ('Max cache size', f"{self.config.max_cache_size_mb} MB")
        ]
        
        for name, value in config_items:
            print(f"  {name}: {value}")
        
        # Memory usage (basic check)
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            print(f"\nMemory usage: {memory_mb:.1f} MB")
        except ImportError:
            print("\nMemory usage: Cannot check (psutil not available)")
        except Exception as e:
            print(f"\nMemory usage: Error checking ({e})")
        
        print("\n" + "=" * 40)
    
    def _fetch_player_api_data(self, player: Player) -> bool:
        """
        Fetch comprehensive player data from Riot API and populate player object.
        
        Args:
            player: Player object to populate with API data
            
        Returns:
            True if data was successfully fetched and populated
        """
        if not self.riot_client:
            print("API client not available - cannot fetch data")
            return False
        
        success_count = 0
        total_operations = 0
        
        try:
            # Ensure we have a valid PUUID
            if not player.puuid:
                print("Getting player account information...")
                summoner_data = self.riot_client.get_summoner_data(player.summoner_name)
                if summoner_data:
                    player.puuid = summoner_data.get('puuid', '')
                    print(f"✓ Account data retrieved")
                    success_count += 1
                else:
                    print(f"✗ Could not find account for {player.summoner_name}")
                    return False
                total_operations += 1
            
            # Fetch champion mastery data
            print("Fetching champion mastery data...")
            total_operations += 1
            try:
                masteries = self.riot_client.get_all_champion_masteries(player.puuid)
                if masteries:
                    # Convert API response to ChampionMastery objects
                    from .models import ChampionMastery
                    player.champion_masteries = {}
                    
                    for mastery_data in masteries:
                        champion_id = mastery_data.get('championId')
                        if champion_id:
                            # Get champion name from champion data manager
                            champion_name = self.champion_data_manager.get_champion_name(champion_id)
                            if not champion_name:
                                champion_name = f"Champion {champion_id}"
                            
                            # Get champion roles
                            champion_roles = self.champion_data_manager.get_champion_roles(champion_id)
                            
                            mastery = ChampionMastery(
                                champion_id=champion_id,
                                champion_name=champion_name,
                                mastery_level=mastery_data.get('championLevel', 0),
                                mastery_points=mastery_data.get('championPoints', 0),
                                chest_granted=mastery_data.get('chestGranted', False),
                                tokens_earned=mastery_data.get('tokensEarned', 0),
                                primary_roles=champion_roles,
                                last_play_time=None  # API doesn't provide this directly
                            )
                            player.champion_masteries[champion_id] = mastery
                    
                    # Update role champion pools
                    player.role_champion_pools = {role: [] for role in self.roles}
                    for champion_id, mastery in player.champion_masteries.items():
                        for role in mastery.primary_roles:
                            if role in player.role_champion_pools:
                                player.role_champion_pools[role].append(champion_id)
                    
                    print(f"✓ Champion mastery data retrieved ({len(masteries)} champions)")
                    success_count += 1
                else:
                    print("✗ No champion mastery data found")
            except Exception as e:
                print(f"✗ Error fetching champion mastery: {e}")
            
            # Fetch match history and calculate performance data
            print("Fetching recent match history...")
            total_operations += 1
            try:
                match_ids = self.riot_client.get_match_history(player.puuid, count=20)
                if match_ids:
                    print(f"✓ Found {len(match_ids)} recent matches")
                    
                    # Fetch detailed match data
                    print("Analyzing match performance...")
                    matches = []
                    for i, match_id in enumerate(match_ids[:10], 1):  # Limit to 10 matches to avoid rate limits
                        try:
                            match_details = self.riot_client.get_match_details(match_id)
                            if match_details:
                                matches.append(match_details)
                            print(f"  Processed match {i}/10", end='\r')
                        except Exception as e:
                            print(f"  Error processing match {match_id}: {e}")
                    
                    print(f"\n✓ Analyzed {len(matches)} matches")
                    
                    # Calculate performance data for each role
                    player.performance_cache = {}
                    for role in self.roles:
                        try:
                            performance_data = self.riot_client.calculate_role_performance(matches, player.puuid, role)
                            if performance_data and performance_data.get('matches_played', 0) > 0:
                                player.performance_cache[role] = performance_data
                        except Exception as e:
                            print(f"  Error calculating {role} performance: {e}")
                    
                    if player.performance_cache:
                        roles_with_data = list(player.performance_cache.keys())
                        print(f"✓ Performance data calculated for: {', '.join(roles_with_data)}")
                        success_count += 1
                    else:
                        print("✗ No role-specific performance data could be calculated")
                else:
                    print("✗ No recent matches found")
            except Exception as e:
                print(f"✗ Error fetching match history: {e}")
            
            # Update player timestamp
            from datetime import datetime
            player.last_updated = datetime.now()
            
            # Save updated player data
            players = self.data_manager.load_player_data()
            for i, p in enumerate(players):
                if p.name == player.name:
                    players[i] = player
                    break
            self.data_manager.save_player_data(players)
            
            print(f"\nData fetch completed: {success_count}/{total_operations} operations successful")
            return success_count > 0
            
        except Exception as e:
            print(f"Error during data fetch: {e}")
            return False
    
    def _select_player(self, players: List[Player], action: str) -> Optional[Player]:
        """Helper method to select a player from a list."""
        print(f"\nSelect player to {action}:")
        for i, player in enumerate(players, 1):
            print(f"{i}. {player.name} ({player.summoner_name})")
        
        while True:
            try:
                choice = input(f"\nEnter player number (1-{len(players)}) or 0 to cancel: ").strip()
                choice_num = int(choice)
                
                if choice_num == 0:
                    return None
                elif 1 <= choice_num <= len(players):
                    return players[choice_num - 1]
                else:
                    print(f"Please enter a number between 1-{len(players)} or 0 to cancel.")
            except ValueError:
                print("Please enter a valid number.")
    
    def get_player_input(self) -> List[str]:
        """
        Collect available players for optimization.
        
        Returns:
            List of player names selected for optimization
        """
        players = self.data_manager.load_player_data()
        if not players:
            return []
        
        selected_players = self._select_players_for_optimization(players)
        return [p.name for p in selected_players] if selected_players else []
    
    def display_results(self, result: OptimizationResult) -> None:
        """
        Display optimization results with explanations.
        
        Args:
            result: Optimization result to display
        """
        self._display_optimization_results(result)
    
    def _log_user_action(self, action: str, details: Dict = None) -> None:
        """
        Log user actions for debugging and monitoring.
        
        Args:
            action: Description of the user action
            details: Additional details about the action
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'details': details or {},
            'api_available': self.api_available
        }
        
        self.logger.info(f"User action: {action}", extra={'user_action': log_entry})
        
        # Also log to a separate user actions file for analytics
        try:
            log_dir = Path(self.config.data_directory) / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            
            actions_log = log_dir / "user_actions.log"
            with open(actions_log, 'a', encoding='utf-8') as f:
                f.write(f"{json.dumps(log_entry)}\n")
        except Exception as e:
            self.logger.warning(f"Could not write to user actions log: {e}")
    
    def _log_performance_metrics(self, operation: str, duration: float, 
                               success: bool, details: Dict = None) -> None:
        """
        Log performance metrics for monitoring and optimization.
        
        Args:
            operation: Name of the operation
            duration: Time taken in seconds
            success: Whether the operation succeeded
            details: Additional performance details
        """
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'operation': operation,
            'duration_seconds': round(duration, 3),
            'success': success,
            'details': details or {}
        }
        
        self.logger.info(f"Performance: {operation} took {duration:.3f}s", 
                        extra={'performance_metrics': metrics})
        
        # Log to performance metrics file
        try:
            log_dir = Path(self.config.data_directory) / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            
            perf_log = log_dir / "performance.log"
            with open(perf_log, 'a', encoding='utf-8') as f:
                f.write(f"{json.dumps(metrics)}\n")
        except Exception as e:
            self.logger.warning(f"Could not write to performance log: {e}")
    
    def _log_error_with_context(self, error: Exception, operation: str, 
                              context: Dict = None) -> None:
        """
        Log errors with comprehensive context for debugging.
        
        Args:
            error: The exception that occurred
            operation: Operation that was being performed
            context: Additional context about the error
        """
        error_info = {
            'timestamp': datetime.now().isoformat(),
            'operation': operation,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context or {},
            'api_available': self.api_available,
            'traceback': traceback.format_exc()
        }
        
        self.logger.error(f"Error in {operation}: {error}", 
                         extra={'error_context': error_info}, exc_info=True)
        
        # Log to error log file
        try:
            log_dir = Path(self.config.data_directory) / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            
            error_log = log_dir / "errors.log"
            with open(error_log, 'a', encoding='utf-8') as f:
                f.write(f"{json.dumps(error_info)}\n")
        except Exception as e:
            # Use basic logging if file logging fails
            self.logger.critical(f"Could not write to error log: {e}")
    
    def _log_system_state(self) -> None:
        """Log current system state for debugging."""
        try:
            players = self.data_manager.load_player_data()
            cache_size = self.data_manager.get_cache_size_mb()
            
            system_state = {
                'timestamp': datetime.now().isoformat(),
                'player_count': len(players),
                'api_available': self.api_available,
                'cache_size_mb': cache_size,
                'config': {
                    'individual_weight': self.config.individual_weight,
                    'preference_weight': self.config.preference_weight,
                    'synergy_weight': self.config.synergy_weight,
                    'max_matches_to_analyze': self.config.max_matches_to_analyze
                }
            }
            
            self.logger.info("System state snapshot", extra={'system_state': system_state})
            
        except Exception as e:
            self.logger.warning(f"Could not capture system state: {e}")
    
    def _setup_debug_logging(self) -> None:
        """Set up additional debug logging if debug mode is enabled."""
        if not self.config.debug:
            return
        
        # Add debug handler for verbose logging
        debug_logger = logging.getLogger('lol_team_optimizer')
        debug_logger.setLevel(logging.DEBUG)
        
        # Create debug log file
        try:
            log_dir = Path(self.config.data_directory) / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            
            debug_handler = logging.FileHandler(log_dir / "debug.log")
            debug_handler.setLevel(logging.DEBUG)
            debug_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
            )
            debug_handler.setFormatter(debug_formatter)
            debug_logger.addHandler(debug_handler)
            
            self.logger.debug("Debug logging enabled")
            
        except Exception as e:
            self.logger.warning(f"Could not set up debug logging: {e}")


def main():
    """Entry point for the CLI application."""
    try:
        cli = CLI()
        cli.main()
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()