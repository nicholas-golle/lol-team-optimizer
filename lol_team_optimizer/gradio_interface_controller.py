"""
Enhanced Gradio Interface Controller with Modular Architecture

This module provides a clean, modular interface controller that separates
web interface concerns from core business logic, with comprehensive state
management and error handling.
"""

import logging
import traceback
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Callable, Union
from dataclasses import dataclass, field
from threading import Lock
import gradio as gr

from .core_engine import CoreEngine
from .models import Player
from .analytics_models import AnalyticsFilters, DateRange
from .enhanced_state_manager import EnhancedStateManager
from .web_state_models import UserPreferences, OperationState


@dataclass
class SessionState:
    """State management for individual user sessions."""
    session_id: str
    created_at: datetime
    last_activity: datetime
    current_tab: str = "player_management"
    selected_players: List[str] = field(default_factory=list)
    active_filters: Dict[str, Any] = field(default_factory=dict)
    cached_results: Dict[str, Any] = field(default_factory=dict)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    operation_states: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OperationResult:
    """Standardized result format for all operations."""
    success: bool
    message: str
    data: Optional[Any] = None
    error_details: Optional[str] = None
    operation_id: Optional[str] = None


class StateManager:
    """Manages web-specific state and session management."""
    
    def __init__(self):
        """Initialize the state manager."""
        self.sessions: Dict[str, SessionState] = {}
        self.global_cache: Dict[str, Any] = {}
        self.cache_ttl: Dict[str, datetime] = {}
        self._lock = Lock()
        self.logger = logging.getLogger(__name__)
        
        # Default cache TTL in seconds
        self.default_ttl = 3600  # 1 hour
    
    def create_session(self) -> str:
        """Create a new session and return session ID."""
        with self._lock:
            session_id = str(uuid.uuid4())
            now = datetime.now()
            
            self.sessions[session_id] = SessionState(
                session_id=session_id,
                created_at=now,
                last_activity=now
            )
            
            self.logger.info(f"Created new session: {session_id}")
            return session_id
    
    def get_session(self, session_id: str) -> Optional[SessionState]:
        """Get session state by ID."""
        with self._lock:
            session = self.sessions.get(session_id)
            if session:
                session.last_activity = datetime.now()
            return session
    
    def update_session_state(self, session_id: str, key: str, value: Any) -> bool:
        """Update session state."""
        with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                return False
            
            if key == "current_tab":
                session.current_tab = value
            elif key == "selected_players":
                session.selected_players = value
            elif key == "active_filters":
                session.active_filters = value
            elif key == "user_preferences":
                session.user_preferences.update(value)
            else:
                # Store in operation_states for custom keys
                session.operation_states[key] = value
            
            session.last_activity = datetime.now()
            return True
    
    def cache_result(self, key: str, result: Any, ttl: Optional[int] = None) -> None:
        """Cache computation results with TTL."""
        with self._lock:
            self.global_cache[key] = result
            expiry_time = datetime.now() + timedelta(seconds=ttl or self.default_ttl)
            self.cache_ttl[key] = expiry_time
            
            self.logger.debug(f"Cached result for key: {key}")
    
    def get_cached_result(self, key: str) -> Optional[Any]:
        """Retrieve cached results if not expired."""
        with self._lock:
            if key not in self.global_cache:
                return None
            
            # Check if expired
            if key in self.cache_ttl and datetime.now() > self.cache_ttl[key]:
                del self.global_cache[key]
                del self.cache_ttl[key]
                self.logger.debug(f"Cache expired for key: {key}")
                return None
            
            return self.global_cache[key]
    
    def invalidate_cache(self, pattern: Optional[str] = None) -> None:
        """Invalidate cache entries matching pattern."""
        with self._lock:
            if pattern is None:
                # Clear all cache
                self.global_cache.clear()
                self.cache_ttl.clear()
                self.logger.info("Cleared all cache")
            else:
                # Clear matching keys
                keys_to_remove = [k for k in self.global_cache.keys() if pattern in k]
                for key in keys_to_remove:
                    del self.global_cache[key]
                    if key in self.cache_ttl:
                        del self.cache_ttl[key]
                self.logger.info(f"Cleared cache for pattern: {pattern}")
    
    def cleanup_expired_sessions(self, max_age_hours: int = 24) -> None:
        """Clean up expired sessions."""
        with self._lock:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            expired_sessions = [
                sid for sid, session in self.sessions.items()
                if session.last_activity < cutoff_time
            ]
            
            for session_id in expired_sessions:
                del self.sessions[session_id]
                self.logger.info(f"Cleaned up expired session: {session_id}")


class DataFlowManager:
    """Manages data flow between interface components."""
    
    def __init__(self, core_engine: CoreEngine, state_manager: StateManager):
        """Initialize the data flow manager."""
        self.core_engine = core_engine
        self.state_manager = state_manager
        self.logger = logging.getLogger(__name__)
        self.event_handlers: Dict[str, List[Callable]] = {}
    
    def register_event_handler(self, event_type: str, handler: Callable) -> None:
        """Register an event handler for specific event types."""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
    
    def emit_event(self, event_type: str, data: Any) -> None:
        """Emit an event to all registered handlers."""
        handlers = self.event_handlers.get(event_type, [])
        for handler in handlers:
            try:
                handler(data)
            except Exception as e:
                self.logger.error(f"Error in event handler for {event_type}: {e}")
    
    def handle_player_update(self, session_id: str, player_data: Dict[str, Any]) -> OperationResult:
        """Handle player data updates and propagate changes."""
        try:
            # Validate player data
            required_fields = ['name', 'summoner_name']
            if not all(field in player_data for field in required_fields):
                return OperationResult(
                    success=False,
                    message="Missing required player fields",
                    error_details=f"Required fields: {required_fields}"
                )
            
            # Create player object (Player model only has name, summoner_name, puuid)
            player = Player(
                name=player_data['name'],
                summoner_name=player_data['summoner_name'],
                puuid=""  # Will be filled during extraction
            )
            
            # Add to core engine
            self.core_engine.data_manager.add_player(player)
            
            # Invalidate related cache
            self.state_manager.invalidate_cache("player_")
            
            # Emit event
            self.emit_event("player_added", {"player": player, "session_id": session_id})
            
            return OperationResult(
                success=True,
                message=f"Successfully added player: {player.name}",
                data={"player": player}
            )
            
        except Exception as e:
            self.logger.error(f"Error handling player update: {e}")
            return OperationResult(
                success=False,
                message="Failed to add player",
                error_details=str(e)
            )
    
    def handle_match_extraction(self, session_id: str, extraction_params: Dict[str, Any]) -> OperationResult:
        """Handle match extraction requests with progress tracking."""
        try:
            operation_id = str(uuid.uuid4())
            
            # Validate parameters
            if 'player_selection' not in extraction_params:
                return OperationResult(
                    success=False,
                    message="No player selected for extraction"
                )
            
            # Get player data
            players = self.core_engine.data_manager.load_player_data()
            player_choices = [f"{p.name} ({p.summoner_name})" for p in players]
            
            if extraction_params['player_selection'] not in player_choices:
                return OperationResult(
                    success=False,
                    message="Selected player not found"
                )
            
            # Find selected player
            player_idx = player_choices.index(extraction_params['player_selection'])
            player = players[player_idx]
            
            # Store operation state
            self.state_manager.update_session_state(
                session_id, 
                f"extraction_{operation_id}", 
                {
                    "status": "starting",
                    "player": player.name,
                    "progress": 0.0
                }
            )
            
            # Perform extraction using historical_match_scraping
            max_matches = extraction_params.get('max_matches', 300)
            result = self.core_engine.historical_match_scraping(
                player_names=[player.name],
                max_matches_per_player=max_matches,
                force_restart=False
            )
            
            # Update operation state based on result
            if 'error' not in result:
                # Get extraction stats for the player
                player_stats = result.get('player_stats', {}).get(player.name, {})
                matches_extracted = player_stats.get('new_matches_stored', 0)
                
                self.state_manager.update_session_state(
                    session_id,
                    f"extraction_{operation_id}",
                    {
                        "status": "completed",
                        "player": player.name,
                        "progress": 1.0,
                        "matches_extracted": matches_extracted
                    }
                )
                
                # Invalidate analytics cache
                self.state_manager.invalidate_cache("analytics_")
                
                return OperationResult(
                    success=True,
                    message=f"Extracted {matches_extracted} matches for {player.name}",
                    data=result,
                    operation_id=operation_id
                )
            else:
                self.state_manager.update_session_state(
                    session_id,
                    f"extraction_{operation_id}",
                    {
                        "status": "failed",
                        "player": player.name,
                        "progress": 0.0,
                        "error": result.get('error', 'Unknown error')
                    }
                )
                
                return OperationResult(
                    success=False,
                    message=f"Extraction failed: {result.get('error', 'Unknown error')}",
                    operation_id=operation_id
                )
                
        except Exception as e:
            self.logger.error(f"Error handling match extraction: {e}")
            return OperationResult(
                success=False,
                message="Match extraction failed",
                error_details=str(e)
            )
    
    def handle_analytics_request(self, session_id: str, analytics_params: Dict[str, Any]) -> OperationResult:
        """Handle analytics requests with caching."""
        try:
            # Create cache key
            cache_key = f"analytics_{hash(str(sorted(analytics_params.items())))}"
            
            # Check cache first
            cached_result = self.state_manager.get_cached_result(cache_key)
            if cached_result:
                self.logger.debug("Returning cached analytics result")
                return OperationResult(
                    success=True,
                    message="Analytics retrieved from cache",
                    data=cached_result
                )
            
            # Validate parameters
            if 'player_selection' not in analytics_params:
                return OperationResult(
                    success=False,
                    message="No player selected for analytics"
                )
            
            if not self.core_engine.analytics_available:
                return OperationResult(
                    success=False,
                    message="Analytics engine not available"
                )
            
            # Get player data
            players = self.core_engine.data_manager.load_player_data()
            player_choices = [f"{p.name} ({p.summoner_name})" for p in players]
            
            if analytics_params['player_selection'] not in player_choices:
                return OperationResult(
                    success=False,
                    message="Selected player not found"
                )
            
            # Find selected player
            player_idx = player_choices.index(analytics_params['player_selection'])
            player = players[player_idx]
            
            # Create analytics filters
            days = analytics_params.get('days', 60)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            filters = AnalyticsFilters(
                date_range=DateRange(start_date=start_date, end_date=end_date),
                min_games=1
            )
            
            # Get analytics
            analytics = self.core_engine.historical_analytics_engine.analyze_player_performance(
                player.puuid, filters
            )
            
            # Cache result
            self.state_manager.cache_result(cache_key, analytics, ttl=1800)  # 30 minutes
            
            return OperationResult(
                success=True,
                message="Analytics generated successfully",
                data=analytics
            )
            
        except Exception as e:
            self.logger.error(f"Error handling analytics request: {e}")
            return OperationResult(
                success=False,
                message="Analytics generation failed",
                error_details=str(e)
            )


class WebErrorHandler:
    """Handles errors in the web interface gracefully."""
    
    def __init__(self):
        """Initialize the error handler."""
        self.logger = logging.getLogger(__name__)
        self.error_log: List[Dict[str, Any]] = []
        
        # User-friendly error messages
        self.error_messages = {
            'api_error': "Unable to connect to Riot API. Please check your internet connection and API key.",
            'validation_error': "Please check your input and try again.",
            'timeout_error': "The operation took too long to complete. Please try again.",
            'not_found_error': "The requested data was not found.",
            'permission_error': "You don't have permission to perform this action.",
            'server_error': "An internal server error occurred. Please try again later."
        }
    
    def handle_error(self, error: Exception, context: str = "") -> OperationResult:
        """Handle any error and return user-friendly result."""
        error_id = str(uuid.uuid4())
        error_info = {
            'error_id': error_id,
            'timestamp': datetime.now().isoformat(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context,
            'traceback': traceback.format_exc()
        }
        
        # Log error
        self.error_log.append(error_info)
        self.logger.error(f"Error {error_id} in {context}: {error}")
        
        # Determine user-friendly message
        error_type = type(error).__name__.lower()
        if 'api' in error_type or 'connection' in error_type:
            user_message = self.error_messages['api_error']
        elif 'validation' in error_type or 'value' in error_type:
            user_message = self.error_messages['validation_error']
        elif 'timeout' in error_type:
            user_message = self.error_messages['timeout_error']
        elif 'notfound' in error_type or 'keyerror' in error_type:
            user_message = self.error_messages['not_found_error']
        elif 'permission' in error_type:
            user_message = self.error_messages['permission_error']
        else:
            user_message = self.error_messages['server_error']
        
        return OperationResult(
            success=False,
            message=user_message,
            error_details=f"Error ID: {error_id}"
        )
    
    def get_error_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent error log entries."""
        return self.error_log[-limit:]


class GradioInterface:
    """Main Gradio interface controller with clean separation from core engine."""
    
    def __init__(self, core_engine: Optional[CoreEngine] = None):
        """Initialize the Gradio interface controller."""
        self.logger = logging.getLogger(__name__)
        
        # Initialize core engine
        if core_engine is None:
            try:
                self.core_engine = CoreEngine()
            except Exception as e:
                self.logger.error(f"Failed to initialize core engine: {e}")
                raise RuntimeError(f"Core engine initialization failed: {e}")
        else:
            self.core_engine = core_engine
        
        # Initialize enhanced state manager
        self.enhanced_state_manager = EnhancedStateManager(
            cache_size_mb=100,
            max_sessions=1000
        )
        
        # Legacy managers for backward compatibility
        self.state_manager = StateManager()
        self.data_flow_manager = DataFlowManager(self.core_engine, self.state_manager)
        self.error_handler = WebErrorHandler()
        
        # Interface state
        self.demo: Optional[gr.Blocks] = None
        self.current_session_id: Optional[str] = None
        
        self.logger.info("Gradio interface controller initialized successfully")
    
    def create_interface(self) -> gr.Blocks:
        """Create the main Gradio interface with all components."""
        try:
            # Create new session with enhanced state manager
            self.current_session_id = self.enhanced_state_manager.create_session()
            
            # Create interface
            self.demo = self._build_interface()
            
            self.logger.info("Gradio interface created successfully")
            return self.demo
            
        except Exception as e:
            self.logger.error(f"Failed to create interface: {e}")
            raise RuntimeError(f"Interface creation failed: {e}")
    
    def _build_interface(self) -> gr.Blocks:
        """Build the actual Gradio interface."""
        # Custom CSS for better styling
        css = """
        .gradio-container {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        .tab-nav {
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        }
        .tab-nav button {
            color: white !important;
        }
        .tab-nav button.selected {
            background: rgba(255, 255, 255, 0.2) !important;
        }
        .error-message {
            color: #dc3545;
            background-color: #f8d7da;
            border: 1px solid #f5c6cb;
            padding: 10px;
            border-radius: 4px;
            margin: 10px 0;
        }
        .success-message {
            color: #155724;
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
            padding: 10px;
            border-radius: 4px;
            margin: 10px 0;
        }
        """
        
        with gr.Blocks(
            css=css, 
            title="LoL Team Optimizer - Enhanced Interface", 
            theme=gr.themes.Soft()
        ) as interface:
            
            # Header
            gr.Markdown("""
            # 🎮 League of Legends Team Optimizer
            
            **Enhanced Web Interface with Advanced Analytics**
            
            Welcome to the next-generation LoL Team Optimizer! This enhanced interface provides
            comprehensive team analytics, player management, and optimization features with
            improved performance and user experience.
            """)
            
            # System status
            with gr.Row():
                system_status = gr.Markdown(self._get_system_status_display())
            
            # Main interface tabs
            with gr.Tabs() as main_tabs:
                
                # Player Management Tab
                with gr.Tab("👥 Player Management", id="player_management"):
                    self._create_player_management_tab()
                
                # Match Extraction Tab  
                with gr.Tab("📥 Match Extraction", id="match_extraction"):
                    self._create_match_extraction_tab()
                
                # Analytics Dashboard Tab
                with gr.Tab("📊 Analytics Dashboard", id="analytics"):
                    self._create_analytics_tab()
                
                # Champion Recommendations Tab
                with gr.Tab("🎯 Champion Recommendations", id="recommendations"):
                    self._create_recommendations_tab()
                
                # Team Composition Tab
                with gr.Tab("👥 Team Composition", id="team_composition"):
                    self._create_team_composition_tab()
            
            # Footer
            gr.Markdown("""
            ---
            
            **LoL Team Optimizer Enhanced Interface** - Version 2.0
            
            Built with modular architecture for improved performance and maintainability.
            Session ID: """ + (self.current_session_id or "Unknown"))
        
        return interface
    
    def _get_system_status_display(self) -> str:
        """Get system status display."""
        status_items = []
        
        # Core engine status
        status_items.append("✅ Core Engine: Ready")
        
        # API status
        if self.core_engine.api_available:
            status_items.append("✅ Riot API: Connected")
        else:
            status_items.append("⚠️ Riot API: Not Available")
        
        # Analytics status
        if self.core_engine.analytics_available:
            status_items.append("✅ Analytics: Available")
        else:
            status_items.append("⚠️ Analytics: Limited")
        
        # Migration status
        migration_status = self.core_engine.get_migration_status()
        if migration_status and migration_status.get('migration_needed'):
            status_items.append("⚠️ Migration: Required")
        else:
            status_items.append("✅ Data: Up to Date")
        
        return "**System Status:** " + " | ".join(status_items)
    
    def _create_player_management_tab(self) -> None:
        """Create the comprehensive player management tab."""
        from .player_management_tab import PlayerManagementTab
        
        try:
            # Create player management tab instance
            player_tab = PlayerManagementTab(self.core_engine)
            
            # Create the tab components
            tab_components = player_tab.create_tab()
            
            # The components are already added to the interface by create_tab()
            # Store reference for potential future use
            self.player_management_tab = player_tab
            
        except Exception as e:
            self.logger.error(f"Error creating player management tab: {e}")
            
            # Fallback to simple interface
            gr.Markdown("## ⚠️ Player Management")
            gr.Markdown(f"**Error loading advanced player management:** {str(e)}")
            
            # Simple add player form as fallback
            with gr.Row():
                player_name = gr.Textbox(label="Player Name", placeholder="Enter player name")
                summoner_name = gr.Textbox(label="Summoner Name", placeholder="Enter summoner name")
            
            add_btn = gr.Button("Add Player", variant="primary")
            result_display = gr.Markdown()
            
            def simple_add_player(name: str, summoner: str) -> str:
                try:
                    if not name or not summoner:
                        return "❌ Both player name and summoner name are required"
                    
                    player = Player(name=name.strip(), summoner_name=summoner.strip(), puuid="")
                    success = self.core_engine.data_manager.add_player(player)
                    
                    if success:
                        return f"✅ Successfully added player: {name}"
                    else:
                        return f"❌ Player '{name}' already exists"
                        
                except Exception as e:
                    return f"❌ Error adding player: {str(e)}"
            
            add_btn.click(
                fn=simple_add_player,
                inputs=[player_name, summoner_name],
                outputs=result_display
            )
    
    def _create_match_extraction_tab(self) -> None:
        """Create the comprehensive match extraction tab with progress tracking."""
        from .match_extraction_interface import MatchExtractionInterface
        
        try:
            # Create match extraction interface instance
            extraction_interface = MatchExtractionInterface(self.core_engine)
            
            # Create the extraction interface components
            extraction_components = extraction_interface.create_extraction_interface()
            
            # Store reference for potential future use
            self.match_extraction_interface = extraction_interface
            
        except Exception as e:
            self.logger.error(f"Error creating match extraction interface: {e}")
            
            # Fallback to simple interface
            gr.Markdown("## ⚠️ Match Extraction")
            gr.Markdown(f"**Error loading advanced match extraction interface:** {str(e)}")
            
            # Simple extraction form as fallback
            gr.Markdown("### Simple Match Extraction")
            
            with gr.Row():
                extract_player = gr.Dropdown(
                    label="Select Player",
                    info="Choose a player to extract matches for",
                    interactive=True
                )
                extract_max_matches = gr.Slider(
                    minimum=50,
                    maximum=1000,
                    value=300,
                    step=50,
                    label="Max Matches to Extract",
                    info="Maximum number of matches to extract"
                )
            
            extract_btn = gr.Button("Extract Matches", variant="primary")
            extract_result = gr.Markdown()
            
            # Event handler for match extraction
            def handle_extract_matches(player_selection: str, max_matches: int) -> str:
                try:
                    result = self.data_flow_manager.handle_match_extraction(
                        self.current_session_id,
                        {
                            'player_selection': player_selection,
                            'max_matches': max_matches
                        }
                    )
                    
                    if result.success:
                        return f'<div class="success-message">✅ {result.message}</div>'
                    else:
                        return f'<div class="error-message">❌ {result.message}</div>'
                        
                except Exception as e:
                    error_result = self.error_handler.handle_error(e, "extract_matches")
                    return f'<div class="error-message">❌ {error_result.message}</div>'
            
            extract_btn.click(
                fn=handle_extract_matches,
                inputs=[extract_player, extract_max_matches],
                outputs=extract_result
            )
            
            # Function to update player choices
            def update_player_choices() -> gr.Dropdown:
                try:
                    players = self.core_engine.data_manager.load_player_data()
                    choices = [f"{p.name} ({p.summoner_name})" for p in players]
                    return gr.Dropdown.update(choices=choices)
                except Exception as e:
                    self.logger.error(f"Error updating player choices: {e}")
                    return gr.Dropdown.update(choices=[])
            
            # Initialize player choices on load
            try:
                players = self.core_engine.data_manager.load_player_data()
                choices = [f"{p.name} ({p.summoner_name})" for p in players]
                extract_player.choices = choices
            except Exception as e:
                self.logger.error(f"Error initializing player choices: {e}")erface_load_handlers.append((update_player_choices, [], [extract_player]))
        self._interface_load_handlers = interface_load_handlers
    
    def _create_analytics_tab(self) -> None:
        """Create the comprehensive analytics dashboard tab with real-time filtering."""
        from .analytics_dashboard import AnalyticsDashboard
        from .visualization_manager import VisualizationManager
        
        try:
            # Initialize visualization manager if not already available
            if not hasattr(self, 'visualization_manager'):
                self.visualization_manager = VisualizationManager()
            
            # Create analytics dashboard
            analytics_dashboard = AnalyticsDashboard(
                analytics_engine=self.core_engine.historical_analytics_engine,
                visualization_manager=self.visualization_manager,
                state_manager=self.enhanced_state_manager,
                data_manager=self.core_engine.data_manager
            )
            
            # Create dashboard interface components
            dashboard_components = analytics_dashboard.create_dashboard_interface()
            
            # Setup event handlers for real-time filtering
            analytics_dashboard.setup_event_handlers()
            
            # Store dashboard reference for potential future use
            self.analytics_dashboard = analytics_dashboard
            
        except Exception as e:
            self.logger.error(f"Error creating analytics dashboard: {e}")
            
            # Fallback to simple analytics interface
            gr.Markdown("## ⚠️ Analytics Dashboard")
            gr.Markdown(f"**Error loading advanced analytics dashboard:** {str(e)}")
            
            # Simple analytics interface as fallback
            gr.Markdown("### Simple Analytics")
            
            analytics_player = gr.Dropdown(
                label="Select Player",
                info="Choose a player to analyze",
                interactive=True
            )
            
            analytics_days = gr.Slider(
                minimum=7,
                maximum=180,
                value=60,
                step=7,
                label="Analysis Period (Days)",
                info="Time period for analysis"
            )
            
            analyze_btn = gr.Button("Analyze Performance", variant="primary")
            
            # Results display
            with gr.Row():
                with gr.Column():
                    analytics_summary = gr.Markdown()
                with gr.Column():
                    performance_chart = gr.Plot()
            
            champion_chart = gr.Plot()
            
            # Simple event handler
            def handle_simple_analytics(player_selection: str, days: int) -> Tuple[str, Any, Any]:
                try:
                    result = self.data_flow_manager.handle_analytics_request(
                        self.current_session_id,
                        {
                            'player_selection': player_selection,
                            'days': days
                        }
                    )
                    
                    if result.success:
                        analytics = result.data
                        summary = self._format_analytics_summary(analytics, player_selection)
                        perf_chart = self._create_performance_chart(analytics)
                        champ_chart = self._create_champion_chart(analytics)
                        
                        return summary, perf_chart, champ_chart
                    else:
                        error_msg = f'<div class="error-message">❌ {result.message}</div>'
                        return error_msg, None, None
                        
                except Exception as e:
                    error_result = self.error_handler.handle_error(e, "analytics_request")
                    error_msg = f'<div class="error-message">❌ {error_result.message}</div>'
                    return error_msg, None, None
            
            analyze_btn.click(
                fn=handle_simple_analytics,
                inputs=[analytics_player, analytics_days],
                outputs=[analytics_summary, performance_chart, champion_chart]
            )
            
            # Function to update player choices
            def update_analytics_player_choices() -> gr.Dropdown:
                try:
                    players = self.core_engine.data_manager.load_player_data()
                    choices = [f"{p.name} ({p.summoner_name})" for p in players]
                    return gr.Dropdown.update(choices=choices)
                except Exception as e:
                    self.logger.error(f"Error updating analytics player choices: {e}")
                    return gr.Dropdown.update(choices=[])
            
            # Add to load handlers
            interface_load_handlers = getattr(self, '_interface_load_handlers', [])
            interface_load_handlers.append((update_analytics_player_choices, [], [analytics_player]))
            self._interface_load_handlers = interface_load_handlers
    
    def _create_recommendations_tab(self) -> None:
        """Create the comprehensive champion recommendations tab with intelligent interface."""
        try:
            from .champion_recommendation_interface import ChampionRecommendationInterface
            
            # Create champion recommendation interface instance
            recommendation_interface = ChampionRecommendationInterface(self.core_engine)
            
            # Create the recommendation interface within the current Gradio context
            recommendation_interface.create_recommendation_interface()
            
            # Store reference for potential future use
            self.champion_recommendation_interface = recommendation_interface
            
            self.logger.info("Advanced champion recommendation interface loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Error creating advanced champion recommendation interface: {e}")
            
            # Fallback to simple interface
            gr.Markdown("## ⚠️ Champion Recommendations")
            gr.Markdown(f"**Error loading advanced recommendation interface:** {str(e)}")
            gr.Markdown("Using simplified recommendation interface.")
            
            # Simple recommendation form as fallback
            with gr.Row():
                rec_player = gr.Dropdown(
                    label="Select Player",
                    info="Choose a player for recommendations",
                    interactive=True
                )
                rec_role = gr.Dropdown(
                    choices=["top", "jungle", "middle", "bottom", "support"],
                    label="Select Role",
                    value="middle",
                    info="Role to get recommendations for"
                )
            
            recommend_btn = gr.Button("Get Recommendations", variant="primary")
            recommendations_result = gr.Markdown()
            
            # Event handler for recommendations
            def handle_recommendations(player_selection: str, role: str) -> str:
                try:
                    if not player_selection:
                        return '<div class="error-message">❌ Please select a player</div>'
                    
                    # Simple recommendation logic (placeholder)
                    sample_recommendations = [
                        f"1. Champion A - High synergy with team composition",
                        f"2. Champion B - Strong individual performance history",
                        f"3. Champion C - Meta relevant pick for current patch",
                        f"4. Champion D - Good counter-pick potential",
                        f"5. Champion E - Comfort pick with high mastery"
                    ]
                    
                    result_html = f"""
                    <div style="padding: 15px; border: 1px solid #28a745; border-radius: 8px; background: #d4edda;">
                        <h4>🎯 Recommendations for {player_selection} ({role.title()})</h4>
                        <ul style="margin: 10px 0;">
                            {''.join([f'<li style="margin: 5px 0;">{rec}</li>' for rec in sample_recommendations])}
                        </ul>
                        <p style="margin: 10px 0 0 0; font-size: 0.9em; color: #666;">
                            <em>Note: This is a simplified interface. The full intelligent recommendation system 
                            provides detailed analysis, confidence scoring, and real-time team composition building.</em>
                        </p>
                    </div>
                    """
                    
                    return result_html
                    
                except Exception as e:
                    return f'<div class="error-message">❌ Error: {str(e)}</div>'
            
            recommend_btn.click(
                fn=handle_recommendations,
                inputs=[rec_player, rec_role],
                outputs=recommendations_result
            )
            
            # Function to update player choices
            def update_rec_player_choices() -> gr.Dropdown:
                try:
                    players = self.core_engine.data_manager.load_player_data()
                    choices = [f"{p.name} ({p.summoner_name})" for p in players]
                    return gr.Dropdown.update(choices=choices)
                except Exception as e:
                    self.logger.error(f"Error updating recommendation player choices: {e}")
                    return gr.Dropdown.update(choices=[])
            
            # Add to load handlers
            interface_load_handlers = getattr(self, '_interface_load_handlers', [])
            interface_load_handlers.append((update_rec_player_choices, [], [rec_player]))
            self._interface_load_handlers = interface_load_handlers
    
    def _create_team_composition_tab(self) -> None:
        """Create the team composition analysis tab."""
        gr.Markdown("## Team Composition Analysis")
        gr.Markdown("Analyze team synergy and find optimal compositions.")
        
        with gr.Row():
            with gr.Column():
                team_player1 = gr.Dropdown(label="Player 1 (Top)")
                team_player2 = gr.Dropdown(label="Player 2 (Jungle)")
                team_player3 = gr.Dropdown(label="Player 3 (Mid)")
            with gr.Column():
                team_player4 = gr.Dropdown(label="Player 4 (ADC)")
                team_player5 = gr.Dropdown(label="Player 5 (Support)")
        
        analyze_team_btn = gr.Button("Analyze Team Composition", variant="primary")
        team_analysis_result = gr.Markdown()
        
        # Event handler for team analysis
        def handle_team_analysis(*player_selections) -> str:
            try:
                if not self.core_engine.analytics_available:
                    return '<div class="error-message">❌ Analytics engine not available</div>'
                
                # Filter out empty selections
                selected_players = [p for p in player_selections if p and p != "None"]
                
                if len(selected_players) < 2:
                    return '<div class="error-message">❌ Please select at least 2 players</div>'
                
                # Get player data
                players = self.core_engine.data_manager.load_player_data()
                player_choices = [f"{p.name} ({p.summoner_name})" for p in players]
                
                # Get player PUUIDs and names
                puuids = []
                player_names = []
                
                for selection in selected_players:
                    if selection in player_choices:
                        player_idx = player_choices.index(selection)
                        player = players[player_idx]
                        puuids.append(player.puuid)
                        player_names.append(player.name)
                
                if len(puuids) < 2:
                    return '<div class="error-message">❌ Could not find selected players</div>'
                
                # Analyze team composition
                result = f"# 👥 Team Composition Analysis\n\n"
                result += f"**Players:** {', '.join(player_names)}\n\n"
                
                # Get individual analytics for each player
                end_date = datetime.now()
                start_date = end_date - timedelta(days=60)
                filters = AnalyticsFilters(
                    date_range=DateRange(start_date=start_date, end_date=end_date),
                    min_games=1
                )
                
                total_games = 0
                total_wins = 0
                
                result += "## Individual Performance\n"
                for puuid, name in zip(puuids, player_names):
                    try:
                        analytics = self.core_engine.historical_analytics_engine.analyze_player_performance(
                            puuid, filters
                        )
                        
                        if analytics and analytics.overall_performance:
                            perf = analytics.overall_performance
                            result += f"- **{name}:** {perf.win_rate:.1%} WR ({perf.games_played} games)\n"
                            total_games += perf.games_played
                            total_wins += perf.wins
                    except:
                        result += f"- **{name}:** No data available\n"
                
                if total_games > 0:
                    team_wr = total_wins / total_games
                    result += f"\n**Combined Win Rate:** {team_wr:.1%} ({total_games} total games)\n"
                
                return result
                
            except Exception as e:
                error_result = self.error_handler.handle_error(e, "team_analysis")
                return f'<div class="error-message">❌ {error_result.message}</div>'
        
        analyze_team_btn.click(
            fn=handle_team_analysis,
            inputs=[team_player1, team_player2, team_player3, team_player4, team_player5],
            outputs=team_analysis_result
        )
        
        # Function to update all team player dropdowns
        def update_team_player_choices() -> List[gr.Dropdown]:
            try:
                players = self.core_engine.data_manager.load_player_data()
                choices = [f"{p.name} ({p.summoner_name})" for p in players]
                return [gr.Dropdown.update(choices=choices) for _ in range(5)]
            except Exception as e:
                self.logger.error(f"Error updating team player choices: {e}")
                return [gr.Dropdown.update(choices=[]) for _ in range(5)]
        
        # Add to load handlers
        interface_load_handlers = getattr(self, '_interface_load_handlers', [])
        interface_load_handlers.append((
            update_team_player_choices, 
            [], 
            [team_player1, team_player2, team_player3, team_player4, team_player5]
        ))
        self._interface_load_handlers = interface_load_handlers
    
    def _format_analytics_summary(self, analytics, player_name: str) -> str:
        """Format analytics into a readable summary."""
        try:
            summary = f"# 📊 Analytics Report - {player_name}\n\n"
            
            if hasattr(analytics, 'analysis_period') and analytics.analysis_period:
                start = analytics.analysis_period.start_date.strftime('%Y-%m-%d')
                end = analytics.analysis_period.end_date.strftime('%Y-%m-%d')
                summary += f"**Analysis Period:** {start} to {end}\n\n"
            
            # Overall performance
            if hasattr(analytics, 'overall_performance') and analytics.overall_performance:
                perf = analytics.overall_performance
                summary += f"## 🎮 Overall Performance\n"
                summary += f"- **Games Played:** {perf.games_played}\n"
                summary += f"- **Win Rate:** {perf.win_rate:.1%}\n"
                summary += f"- **Average KDA:** {perf.avg_kda:.2f}\n"
                summary += f"- **CS/Min:** {perf.avg_cs_per_min:.1f}\n"
                summary += f"- **Vision Score:** {perf.avg_vision_score:.1f}\n\n"
            
            # Champion performance
            if hasattr(analytics, 'champion_performance') and analytics.champion_performance:
                summary += f"## 🏆 Top Champions\n"
                sorted_champs = sorted(
                    analytics.champion_performance.items(),
                    key=lambda x: x[1].performance.win_rate,
                    reverse=True
                )[:5]
                
                for i, (champ_id, champ_perf) in enumerate(sorted_champs, 1):
                    perf = champ_perf.performance
                    summary += f"{i}. **{champ_perf.champion_name}** ({champ_perf.role})\n"
                    summary += f"   - Win Rate: {perf.win_rate:.1%} ({perf.games_played} games)\n"
                    summary += f"   - KDA: {perf.avg_kda:.2f}\n\n"
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error formatting analytics summary: {e}")
            return f'<div class="error-message">❌ Error formatting analytics summary</div>'
    
    def _create_performance_chart(self, analytics) -> Any:
        """Create a performance metrics chart."""
        try:
            if not hasattr(analytics, 'overall_performance') or not analytics.overall_performance:
                return None
            
            import plotly.graph_objects as go
            
            perf = analytics.overall_performance
            
            # Create radar chart for performance metrics
            categories = ['Win Rate', 'KDA', 'CS/Min', 'Vision Score', 'Damage/Min']
            values = [
                perf.win_rate * 100,
                min(perf.avg_kda * 10, 100),  # Scale KDA to 0-100
                min(perf.avg_cs_per_min * 10, 100),  # Scale CS to 0-100
                min(perf.avg_vision_score * 2, 100),  # Scale vision to 0-100
                min(perf.avg_damage_per_min / 10, 100) if hasattr(perf, 'avg_damage_per_min') else 50
            ]
            
            fig = go.Figure()
            
            fig.add_trace(go.Scatterpolar(
                r=values,
                theta=categories,
                fill='toself',
                name='Performance',
                line_color='rgb(0, 123, 255)'
            ))
            
            fig.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, 100]
                    )),
                showlegend=False,
                title="Performance Metrics Overview"
            )
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Error creating performance chart: {e}")
            return None
    
    def _create_champion_chart(self, analytics) -> Any:
        """Create a champion performance chart."""
        try:
            if not hasattr(analytics, 'champion_performance') or not analytics.champion_performance:
                return None
            
            import plotly.graph_objects as go
            
            # Prepare data for chart
            champions = []
            win_rates = []
            games_played = []
            
            for champ_id, champ_perf in analytics.champion_performance.items():
                if champ_perf.performance.games_played >= 3:  # Only show champions with 3+ games
                    champions.append(champ_perf.champion_name)
                    win_rates.append(champ_perf.performance.win_rate * 100)
                    games_played.append(champ_perf.performance.games_played)
            
            if not champions:
                return None
            
            # Create bar chart
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                x=champions,
                y=win_rates,
                text=[f"{wr:.1f}% ({gp} games)" for wr, gp in zip(win_rates, games_played)],
                textposition='auto',
                marker_color='rgb(0, 123, 255)'
            ))
            
            fig.update_layout(
                title="Champion Win Rates",
                xaxis_title="Champion",
                yaxis_title="Win Rate (%)",
                yaxis=dict(range=[0, 100])
            )
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Error creating champion chart: {e}")
            return None
    
    def launch(self, share: bool = False, server_name: str = "127.0.0.1", 
               server_port: int = 7860, **kwargs) -> None:
        """Launch the Gradio interface."""
        try:
            if self.demo is None:
                self.create_interface()
            
            # Set up interface load handlers
            if hasattr(self, '_interface_load_handlers'):
                for handler_func, inputs, outputs in self._interface_load_handlers:
                    self.demo.load(fn=handler_func, inputs=inputs, outputs=outputs)
            
            self.logger.info(f"Launching Gradio interface on {server_name}:{server_port}")
            
            self.demo.launch(
                share=share,
                server_name=server_name,
                server_port=server_port,
                show_error=True,
                **kwargs
            )
            
        except Exception as e:
            self.logger.error(f"Failed to launch interface: {e}")
            raise RuntimeError(f"Interface launch failed: {e}")
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get current session information."""
        if not self.current_session_id:
            return {"error": "No active session"}
        
        session = self.state_manager.get_session(self.current_session_id)
        if not session:
            return {"error": "Session not found"}
        
        return {
            "session_id": session.session_id,
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat(),
            "current_tab": session.current_tab,
            "selected_players": session.selected_players,
            "cache_size": len(self.state_manager.global_cache)
        }