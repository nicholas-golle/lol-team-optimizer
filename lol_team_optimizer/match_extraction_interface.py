"""
Interactive Match Extraction Interface with Progress Tracking

This module provides a comprehensive match extraction interface with real-time
progress tracking, parameter customization, pause/resume functionality, and
detailed logging for the Gradio web interface.
"""

import logging
import json
import uuid
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from pathlib import Path
import gradio as gr

from .core_engine import CoreEngine
from .models import Player
from .gradio_components import ProgressComponents, ValidationComponents, ComponentConfig


@dataclass
class ExtractionConfig:
    """Configuration for match extraction operations."""
    player_selection: str
    queue_types: List[str] = field(default_factory=lambda: ["420", "440"])  # Ranked Solo/Duo, Ranked Flex
    max_matches_per_player: int = 300
    date_range_days: int = 365
    batch_size: int = 20
    rate_limit_delay: float = 1.0
    enable_validation: bool = True
    auto_retry: bool = True
    max_retries: int = 3


@dataclass
class ExtractionProgress:
    """Progress tracking for extraction operations."""
    operation_id: str
    player_name: str
    status: str = "not_started"  # not_started, running, paused, completed, failed, cancelled
    progress_percentage: float = 0.0
    current_step: str = ""
    matches_extracted: int = 0
    total_matches_available: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    detailed_log: List[str] = field(default_factory=list)
    can_pause: bool = True
    can_resume: bool = False
    can_cancel: bool = True


@dataclass
class ExtractionHistory:
    """Historical record of extraction operations."""
    operation_id: str
    player_name: str
    config: ExtractionConfig
    progress: ExtractionProgress
    timestamp: datetime
    duration_seconds: Optional[float] = None
    success: bool = False


class ExtractionScheduler:
    """Handles scheduling and automation of extraction operations."""
    
    def __init__(self):
        """Initialize the extraction scheduler."""
        self.logger = logging.getLogger(__name__)
        self.scheduled_operations: Dict[str, Dict[str, Any]] = {}
        self.recurring_schedules: Dict[str, Dict[str, Any]] = {}
    
    def schedule_extraction(self, config: ExtractionConfig, schedule_time: datetime) -> str:
        """Schedule an extraction operation for a specific time."""
        schedule_id = str(uuid.uuid4())
        
        self.scheduled_operations[schedule_id] = {
            'config': config,
            'schedule_time': schedule_time,
            'status': 'scheduled',
            'created_at': datetime.now()
        }
        
        self.logger.info(f"Scheduled extraction {schedule_id} for {schedule_time}")
        return schedule_id
    
    def create_recurring_schedule(self, config: ExtractionConfig, interval_hours: int) -> str:
        """Create a recurring extraction schedule."""
        schedule_id = str(uuid.uuid4())
        
        self.recurring_schedules[schedule_id] = {
            'config': config,
            'interval_hours': interval_hours,
            'last_run': None,
            'next_run': datetime.now() + timedelta(hours=interval_hours),
            'status': 'active',
            'created_at': datetime.now()
        }
        
        self.logger.info(f"Created recurring schedule {schedule_id} with {interval_hours}h interval")
        return schedule_id
    
    def get_pending_operations(self) -> List[Dict[str, Any]]:
        """Get operations that are ready to run."""
        now = datetime.now()
        pending = []
        
        # Check scheduled operations
        for schedule_id, operation in self.scheduled_operations.items():
            if operation['status'] == 'scheduled' and operation['schedule_time'] <= now:
                pending.append({
                    'type': 'scheduled',
                    'id': schedule_id,
                    'config': operation['config']
                })
        
        # Check recurring schedules
        for schedule_id, schedule in self.recurring_schedules.items():
            if schedule['status'] == 'active' and schedule['next_run'] <= now:
                pending.append({
                    'type': 'recurring',
                    'id': schedule_id,
                    'config': schedule['config']
                })
        
        return pending


class MatchExtractionInterface:
    """Interactive match extraction interface with comprehensive features."""
    
    def __init__(self, core_engine: CoreEngine):
        """Initialize the match extraction interface."""
        self.core_engine = core_engine
        self.logger = logging.getLogger(__name__)
        self.config = ComponentConfig()
        
        # State management
        self.active_operations: Dict[str, ExtractionProgress] = {}
        self.extraction_history: List[ExtractionHistory] = []
        self.scheduler = ExtractionScheduler()
        
        # Threading for background operations
        self.operation_threads: Dict[str, threading.Thread] = {}
        self.stop_events: Dict[str, threading.Event] = {}
        self.pause_events: Dict[str, threading.Event] = {}
        
        # Load extraction history
        self._load_extraction_history()
    
    def _load_extraction_history(self) -> None:
        """Load extraction history from storage."""
        try:
            history_file = Path(self.core_engine.config.data_directory) / "extraction_history.json"
            if history_file.exists():
                with open(history_file, 'r') as f:
                    history_data = json.load(f)
                
                for item in history_data:
                    # Reconstruct objects from JSON
                    config = ExtractionConfig(**item['config'])
                    progress = ExtractionProgress(**item['progress'])
                    
                    # Convert datetime strings back to datetime objects
                    if item['timestamp']:
                        timestamp = datetime.fromisoformat(item['timestamp'])
                    else:
                        timestamp = datetime.now()
                    
                    history_entry = ExtractionHistory(
                        operation_id=item['operation_id'],
                        player_name=item['player_name'],
                        config=config,
                        progress=progress,
                        timestamp=timestamp,
                        duration_seconds=item.get('duration_seconds'),
                        success=item.get('success', False)
                    )
                    
                    self.extraction_history.append(history_entry)
                
                self.logger.info(f"Loaded {len(self.extraction_history)} extraction history entries")
        
        except Exception as e:
            self.logger.warning(f"Failed to load extraction history: {e}")
            self.extraction_history = []
    
    def _save_extraction_history(self) -> None:
        """Save extraction history to storage."""
        try:
            history_file = Path(self.core_engine.config.data_directory) / "extraction_history.json"
            
            # Convert to JSON-serializable format
            history_data = []
            for entry in self.extraction_history:
                history_data.append({
                    'operation_id': entry.operation_id,
                    'player_name': entry.player_name,
                    'config': entry.config.__dict__,
                    'progress': entry.progress.__dict__,
                    'timestamp': entry.timestamp.isoformat(),
                    'duration_seconds': entry.duration_seconds,
                    'success': entry.success
                })
            
            with open(history_file, 'w') as f:
                json.dump(history_data, f, indent=2, default=str)
            
            self.logger.debug("Saved extraction history")
        
        except Exception as e:
            self.logger.error(f"Failed to save extraction history: {e}")
    
    def create_extraction_interface(self) -> Dict[str, gr.Component]:
        """Create the complete match extraction interface."""
        components = {}
        
        # Header
        gr.Markdown("## 📥 Interactive Match Extraction")
        gr.Markdown("""
        Extract historical match data with real-time progress tracking, advanced configuration options,
        and comprehensive logging. Configure extraction parameters, monitor progress, and manage
        extraction operations with pause/resume functionality.
        """)
        
        # Configuration Panel
        with gr.Accordion("⚙️ Extraction Configuration", open=True):
            components.update(self._create_configuration_panel())
        
        # Progress Tracking Panel
        with gr.Accordion("📊 Progress Tracking", open=True):
            components.update(self._create_progress_panel())
        
        # Control Panel
        with gr.Row():
            components.update(self._create_control_panel())
        
        # History and Logging Panel
        with gr.Accordion("📋 Extraction History & Logs", open=False):
            components.update(self._create_history_panel())
        
        # Scheduling Panel
        with gr.Accordion("⏰ Scheduling & Automation", open=False):
            components.update(self._create_scheduling_panel())
        
        # Setup event handlers
        self._setup_event_handlers(components)
        
        return components
    
    def _create_configuration_panel(self) -> Dict[str, gr.Component]:
        """Create the extraction configuration panel."""
        components = {}
        
        # Player Selection
        with gr.Row():
            components['player_selection'] = gr.Dropdown(
                label="Select Player *",
                info="Choose a player to extract matches for",
                interactive=True
            )
            components['refresh_players'] = gr.Button("🔄 Refresh", size="sm")
        
        # Queue Type Selection
        components['queue_types'] = gr.CheckboxGroup(
            choices=[
                ("Ranked Solo/Duo", "420"),
                ("Ranked Flex", "440"),
                ("Normal Draft", "400"),
                ("Normal Blind", "430"),
                ("ARAM", "450")
            ],
            label="Queue Types",
            value=["420", "440"],
            info="Select which queue types to extract matches from"
        )
        
        # Extraction Parameters
        with gr.Row():
            components['max_matches'] = gr.Slider(
                minimum=50,
                maximum=1000,
                value=300,
                step=50,
                label="Max Matches per Player",
                info="Maximum number of matches to extract"
            )
            
            components['date_range_days'] = gr.Slider(
                minimum=30,
                maximum=730,
                value=365,
                step=30,
                label="Date Range (Days)",
                info="How far back to look for matches"
            )
        
        # Advanced Options
        with gr.Accordion("Advanced Options", open=False):
            with gr.Row():
                components['batch_size'] = gr.Slider(
                    minimum=10,
                    maximum=100,
                    value=20,
                    step=10,
                    label="Batch Size",
                    info="Number of matches to fetch per API call"
                )
                
                components['rate_limit_delay'] = gr.Slider(
                    minimum=0.5,
                    maximum=5.0,
                    value=1.0,
                    step=0.1,
                    label="Rate Limit Delay (seconds)",
                    info="Delay between API calls to avoid rate limiting"
                )
            
            with gr.Row():
                components['enable_validation'] = gr.Checkbox(
                    label="Enable Data Validation",
                    value=True,
                    info="Validate extracted match data for consistency"
                )
                
                components['auto_retry'] = gr.Checkbox(
                    label="Auto Retry on Failure",
                    value=True,
                    info="Automatically retry failed API calls"
                )
                
                components['max_retries'] = gr.Slider(
                    minimum=1,
                    maximum=10,
                    value=3,
                    step=1,
                    label="Max Retries",
                    info="Maximum number of retry attempts"
                )
        
        # Configuration Validation
        components['config_validation'] = gr.HTML("")
        
        return components
    
    def _create_progress_panel(self) -> Dict[str, gr.Component]:
        """Create the progress tracking panel."""
        components = {}
        
        # Overall Progress
        with gr.Row():
            components['progress_bar'] = gr.Progress()
            components['progress_percentage'] = gr.Textbox(
                label="Progress",
                value="0%",
                interactive=False,
                scale=1
            )
        
        # Current Status
        components['current_status'] = gr.Textbox(
            label="Current Status",
            value="Ready to start extraction",
            interactive=False
        )
        
        # Detailed Progress Information
        with gr.Row():
            with gr.Column():
                components['matches_extracted'] = gr.Number(
                    label="Matches Extracted",
                    value=0,
                    interactive=False
                )
                
                components['total_available'] = gr.Number(
                    label="Total Available",
                    value=0,
                    interactive=False
                )
            
            with gr.Column():
                components['extraction_rate'] = gr.Textbox(
                    label="Extraction Rate",
                    value="0 matches/min",
                    interactive=False
                )
                
                components['estimated_completion'] = gr.Textbox(
                    label="Estimated Completion",
                    value="Unknown",
                    interactive=False
                )
        
        # Progress Timeline
        components['progress_timeline'] = gr.Markdown("""
        **Extraction Timeline:**
        - ⏳ Waiting to start...
        """)
        
        return components
    
    def _create_control_panel(self) -> Dict[str, gr.Component]:
        """Create the extraction control panel."""
        components = {}
        
        # Main Control Buttons
        components['start_extraction'] = gr.Button(
            "🚀 Start Extraction",
            variant="primary",
            size="lg"
        )
        
        components['pause_extraction'] = gr.Button(
            "⏸️ Pause",
            variant="secondary",
            interactive=False
        )
        
        components['resume_extraction'] = gr.Button(
            "▶️ Resume",
            variant="secondary",
            interactive=False
        )
        
        components['cancel_extraction'] = gr.Button(
            "🛑 Cancel",
            variant="stop",
            interactive=False
        )
        
        # Quick Actions
        with gr.Row():
            components['validate_config'] = gr.Button(
                "✅ Validate Configuration",
                variant="secondary",
                size="sm"
            )
            
            components['save_config'] = gr.Button(
                "💾 Save Configuration",
                variant="secondary",
                size="sm"
            )
            
            components['load_config'] = gr.Button(
                "📁 Load Configuration",
                variant="secondary",
                size="sm"
            )
        
        return components
    
    def _create_history_panel(self) -> Dict[str, gr.Component]:
        """Create the history and logging panel."""
        components = {}
        
        # Extraction History Table
        components['history_table'] = gr.DataFrame(
            headers=["Operation ID", "Player", "Status", "Matches", "Duration", "Timestamp"],
            datatype=["str", "str", "str", "number", "str", "str"],
            label="Extraction History"
        )
        
        # History Controls
        with gr.Row():
            components['refresh_history'] = gr.Button("🔄 Refresh History")
            components['clear_history'] = gr.Button("🗑️ Clear History", variant="secondary")
            components['export_history'] = gr.Button("📤 Export History", variant="secondary")
        
        # Real-time Log Display
        components['log_display'] = gr.Textbox(
            label="Real-time Extraction Log",
            lines=10,
            max_lines=20,
            interactive=False,
            placeholder="Extraction logs will appear here..."
        )
        
        # Log Controls
        with gr.Row():
            components['auto_scroll_logs'] = gr.Checkbox(
                label="Auto-scroll logs",
                value=True
            )
            components['clear_logs'] = gr.Button("Clear Logs", size="sm")
            components['export_logs'] = gr.Button("Export Logs", size="sm")
        
        return components
    
    def _create_scheduling_panel(self) -> Dict[str, gr.Component]:
        """Create the scheduling and automation panel."""
        components = {}
        
        # Schedule One-time Extraction
        with gr.Accordion("Schedule One-time Extraction", open=False):
            with gr.Row():
                components['schedule_date'] = gr.Textbox(
                    label="Schedule Date",
                    placeholder="YYYY-MM-DD",
                    info="Date to run the extraction"
                )
                
                components['schedule_time'] = gr.Textbox(
                    label="Schedule Time",
                    placeholder="HH:MM",
                    info="Time to run the extraction (24-hour format)"
                )
            
            components['schedule_extraction'] = gr.Button(
                "📅 Schedule Extraction",
                variant="secondary"
            )
        
        # Recurring Schedule
        with gr.Accordion("Recurring Extraction Schedule", open=False):
            components['recurring_interval'] = gr.Dropdown(
                label="Interval",
                choices=[
                    ("Daily", "24"),
                    ("Weekly", "168"),
                    ("Bi-weekly", "336"),
                    ("Monthly", "720")
                ],
                value="168",
                info="How often to run the extraction"
            )
            
            with gr.Row():
                components['create_recurring'] = gr.Button(
                    "🔄 Create Recurring Schedule",
                    variant="secondary"
                )
                
                components['view_schedules'] = gr.Button(
                    "📋 View Schedules",
                    variant="secondary"
                )
        
        # Scheduled Operations Display
        components['scheduled_operations'] = gr.DataFrame(
            headers=["Schedule ID", "Player", "Type", "Next Run", "Status"],
            datatype=["str", "str", "str", "str", "str"],
            label="Scheduled Operations"
        )
        
        return components
    
    def _setup_event_handlers(self, components: Dict[str, gr.Component]) -> None:
        """Setup event handlers for all components."""
        
        # Configuration validation
        def validate_configuration(*args) -> str:
            """Validate the extraction configuration."""
            try:
                config = self._get_config_from_inputs(*args)
                validation_result = self._validate_extraction_config(config)
                
                if validation_result['valid']:
                    return ValidationComponents.create_validation_message(
                        "✅ Configuration is valid", "success", self.config
                    ).value
                else:
                    return ValidationComponents.create_validation_message(
                        f"❌ {validation_result['message']}", "error", self.config
                    ).value
            
            except Exception as e:
                return ValidationComponents.create_validation_message(
                    f"❌ Validation error: {str(e)}", "error", self.config
                ).value
        
        # Start extraction handler
        def start_extraction(*args) -> Tuple[str, str, bool, bool, bool, bool]:
            """Start the extraction process."""
            try:
                config = self._get_config_from_inputs(*args)
                validation_result = self._validate_extraction_config(config)
                
                if not validation_result['valid']:
                    return (
                        f"❌ Cannot start: {validation_result['message']}",
                        "0%",
                        False,  # pause button
                        False,  # resume button
                        False,  # cancel button
                        True    # start button
                    )
                
                # Start extraction in background thread
                operation_id = self._start_extraction_operation(config)
                
                return (
                    f"🚀 Starting extraction (Operation: {operation_id[:8]}...)",
                    "0%",
                    True,   # pause button
                    False,  # resume button
                    True,   # cancel button
                    False   # start button
                )
            
            except Exception as e:
                self.logger.error(f"Error starting extraction: {e}")
                return (
                    f"❌ Failed to start extraction: {str(e)}",
                    "0%",
                    False, False, False, True
                )
        
        # Pause extraction handler
        def pause_extraction() -> Tuple[str, bool, bool, bool]:
            """Pause the current extraction."""
            try:
                # Find active operation
                active_ops = [op for op in self.active_operations.values() if op.status == "running"]
                if not active_ops:
                    return "❌ No active extraction to pause", False, False, False
                
                operation = active_ops[0]
                if operation.operation_id in self.pause_events:
                    self.pause_events[operation.operation_id].set()
                    operation.status = "paused"
                    operation.can_pause = False
                    operation.can_resume = True
                    
                    return (
                        "⏸️ Extraction paused",
                        False,  # pause button
                        True,   # resume button
                        True    # cancel button
                    )
                else:
                    return "❌ Cannot pause extraction", False, False, True
            
            except Exception as e:
                self.logger.error(f"Error pausing extraction: {e}")
                return f"❌ Error pausing: {str(e)}", False, False, True
        
        # Resume extraction handler
        def resume_extraction() -> Tuple[str, bool, bool, bool]:
            """Resume the paused extraction."""
            try:
                # Find paused operation
                paused_ops = [op for op in self.active_operations.values() if op.status == "paused"]
                if not paused_ops:
                    return "❌ No paused extraction to resume", False, False, False
                
                operation = paused_ops[0]
                if operation.operation_id in self.pause_events:
                    self.pause_events[operation.operation_id].clear()
                    operation.status = "running"
                    operation.can_pause = True
                    operation.can_resume = False
                    
                    return (
                        "▶️ Extraction resumed",
                        True,   # pause button
                        False,  # resume button
                        True    # cancel button
                    )
                else:
                    return "❌ Cannot resume extraction", False, False, True
            
            except Exception as e:
                self.logger.error(f"Error resuming extraction: {e}")
                return f"❌ Error resuming: {str(e)}", False, False, True
        
        # Cancel extraction handler
        def cancel_extraction() -> Tuple[str, str, bool, bool, bool, bool]:
            """Cancel the current extraction."""
            try:
                # Find active operation
                active_ops = [op for op in self.active_operations.values() 
                             if op.status in ["running", "paused"]]
                if not active_ops:
                    return (
                        "❌ No active extraction to cancel",
                        "0%",
                        False, False, False, True
                    )
                
                operation = active_ops[0]
                if operation.operation_id in self.stop_events:
                    self.stop_events[operation.operation_id].set()
                    operation.status = "cancelled"
                    operation.end_time = datetime.now()
                    
                    return (
                        "🛑 Extraction cancelled",
                        f"{operation.progress_percentage:.1f}%",
                        False,  # pause button
                        False,  # resume button
                        False,  # cancel button
                        True    # start button
                    )
                else:
                    return (
                        "❌ Cannot cancel extraction",
                        "0%",
                        False, False, False, True
                    )
            
            except Exception as e:
                self.logger.error(f"Error cancelling extraction: {e}")
                return (
                    f"❌ Error cancelling: {str(e)}",
                    "0%",
                    False, False, False, True
                )
        
        # Refresh player list handler
        def refresh_player_list() -> gr.Dropdown:
            """Refresh the player dropdown list."""
            try:
                players = self.core_engine.data_manager.load_player_data()
                choices = [f"{p.name} ({p.summoner_name})" for p in players]
                return gr.Dropdown.update(choices=choices)
            except Exception as e:
                self.logger.error(f"Error refreshing player list: {e}")
                return gr.Dropdown.update(choices=[])
        
        # Connect event handlers
        validation_inputs = [
            components['player_selection'],
            components['queue_types'],
            components['max_matches'],
            components['date_range_days'],
            components['batch_size'],
            components['rate_limit_delay'],
            components['enable_validation'],
            components['auto_retry'],
            components['max_retries']
        ]
        
        components['validate_config'].click(
            fn=validate_configuration,
            inputs=validation_inputs,
            outputs=components['config_validation']
        )
        
        components['start_extraction'].click(
            fn=start_extraction,
            inputs=validation_inputs,
            outputs=[
                components['current_status'],
                components['progress_percentage'],
                components['pause_extraction'],
                components['resume_extraction'],
                components['cancel_extraction'],
                components['start_extraction']
            ]
        )
        
        components['pause_extraction'].click(
            fn=pause_extraction,
            outputs=[
                components['current_status'],
                components['pause_extraction'],
                components['resume_extraction'],
                components['cancel_extraction']
            ]
        )
        
        components['resume_extraction'].click(
            fn=resume_extraction,
            outputs=[
                components['current_status'],
                components['pause_extraction'],
                components['resume_extraction'],
                components['cancel_extraction']
            ]
        )
        
        components['cancel_extraction'].click(
            fn=cancel_extraction,
            outputs=[
                components['current_status'],
                components['progress_percentage'],
                components['pause_extraction'],
                components['resume_extraction'],
                components['cancel_extraction'],
                components['start_extraction']
            ]
        )
        
        components['refresh_players'].click(
            fn=refresh_player_list,
            outputs=components['player_selection']
        )
    
    def _get_config_from_inputs(self, *args) -> ExtractionConfig:
        """Extract configuration from input components."""
        return ExtractionConfig(
            player_selection=args[0] or "",
            queue_types=args[1] or ["420", "440"],
            max_matches_per_player=int(args[2]) if args[2] else 300,
            date_range_days=int(args[3]) if args[3] else 365,
            batch_size=int(args[4]) if args[4] else 20,
            rate_limit_delay=float(args[5]) if args[5] else 1.0,
            enable_validation=bool(args[6]) if args[6] is not None else True,
            auto_retry=bool(args[7]) if args[7] is not None else True,
            max_retries=int(args[8]) if args[8] else 3
        )
    
    def _validate_extraction_config(self, config: ExtractionConfig) -> Dict[str, Any]:
        """Validate extraction configuration."""
        if not config.player_selection:
            return {'valid': False, 'message': 'Player selection is required'}
        
        if not config.queue_types:
            return {'valid': False, 'message': 'At least one queue type must be selected'}
        
        if config.max_matches_per_player < 1:
            return {'valid': False, 'message': 'Max matches must be at least 1'}
        
        if config.date_range_days < 1:
            return {'valid': False, 'message': 'Date range must be at least 1 day'}
        
        if config.batch_size < 1 or config.batch_size > 100:
            return {'valid': False, 'message': 'Batch size must be between 1 and 100'}
        
        if config.rate_limit_delay < 0.1:
            return {'valid': False, 'message': 'Rate limit delay must be at least 0.1 seconds'}
        
        # Check if player exists
        try:
            players = self.core_engine.data_manager.load_player_data()
            player_choices = [f"{p.name} ({p.summoner_name})" for p in players]
            
            if config.player_selection not in player_choices:
                return {'valid': False, 'message': 'Selected player not found'}
        
        except Exception as e:
            return {'valid': False, 'message': f'Error validating player: {str(e)}'}
        
        return {'valid': True, 'message': 'Configuration is valid'}
    
    def _start_extraction_operation(self, config: ExtractionConfig) -> str:
        """Start an extraction operation in a background thread."""
        operation_id = str(uuid.uuid4())
        
        # Find the selected player
        players = self.core_engine.data_manager.load_player_data()
        player_choices = [f"{p.name} ({p.summoner_name})" for p in players]
        player_idx = player_choices.index(config.player_selection)
        player = players[player_idx]
        
        # Create progress tracker
        progress = ExtractionProgress(
            operation_id=operation_id,
            player_name=player.name,
            status="running",
            start_time=datetime.now()
        )
        
        self.active_operations[operation_id] = progress
        
        # Create threading events
        self.stop_events[operation_id] = threading.Event()
        self.pause_events[operation_id] = threading.Event()
        
        # Start extraction thread
        thread = threading.Thread(
            target=self._run_extraction,
            args=(operation_id, config, player),
            daemon=True
        )
        
        self.operation_threads[operation_id] = thread
        thread.start()
        
        self.logger.info(f"Started extraction operation {operation_id} for player {player.name}")
        return operation_id
    
    def _run_extraction(self, operation_id: str, config: ExtractionConfig, player: Player) -> None:
        """Run the extraction operation in a background thread."""
        progress = self.active_operations[operation_id]
        stop_event = self.stop_events[operation_id]
        pause_event = self.pause_events[operation_id]
        
        try:
            progress.detailed_log.append(f"Starting extraction for {player.name}")
            progress.current_step = "Initializing extraction"
            
            # Use the core engine's historical match scraping
            result = self.core_engine.historical_match_scraping(
                player_names=[player.name],
                max_matches_per_player=config.max_matches_per_player,
                force_restart=False
            )
            
            if 'error' in result:
                progress.status = "failed"
                progress.error_message = result['error']
                progress.detailed_log.append(f"Extraction failed: {result['error']}")
            else:
                # Extract results
                player_results = result.get('player_results', {}).get(player.name, {})
                progress.matches_extracted = player_results.get('new_matches_stored', 0)
                progress.status = "completed"
                progress.progress_percentage = 100.0
                progress.detailed_log.append(f"Extraction completed: {progress.matches_extracted} matches extracted")
            
            progress.end_time = datetime.now()
            
            # Save to history
            duration = (progress.end_time - progress.start_time).total_seconds()
            history_entry = ExtractionHistory(
                operation_id=operation_id,
                player_name=player.name,
                config=config,
                progress=progress,
                timestamp=progress.start_time,
                duration_seconds=duration,
                success=(progress.status == "completed")
            )
            
            self.extraction_history.append(history_entry)
            self._save_extraction_history()
            
        except Exception as e:
            self.logger.error(f"Extraction operation {operation_id} failed: {e}")
            progress.status = "failed"
            progress.error_message = str(e)
            progress.end_time = datetime.now()
            progress.detailed_log.append(f"Extraction failed with error: {str(e)}")
        
        finally:
            # Cleanup
            if operation_id in self.stop_events:
                del self.stop_events[operation_id]
            if operation_id in self.pause_events:
                del self.pause_events[operation_id]
            if operation_id in self.operation_threads:
                del self.operation_threads[operation_id]
    
    def get_active_operations(self) -> List[ExtractionProgress]:
        """Get list of currently active operations."""
        return list(self.active_operations.values())
    
    def get_extraction_history(self) -> List[ExtractionHistory]:
        """Get extraction history."""
        return self.extraction_history.copy()
    
    def cleanup_completed_operations(self) -> None:
        """Clean up completed operations from active list."""
        completed_ops = [
            op_id for op_id, progress in self.active_operations.items()
            if progress.status in ["completed", "failed", "cancelled"]
        ]
        
        for op_id in completed_ops:
            del self.active_operations[op_id]
        
        self.logger.info(f"Cleaned up {len(completed_ops)} completed operations")