"""
Analytics Batch Processor for the League of Legends Team Optimizer.

This module provides batch processing capabilities for large-scale analytics
operations, including parallel processing, progress tracking, and cancellation
support for long-running operations.
"""

import asyncio
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed, Future
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple, Union, Set
from queue import Queue, Empty
from threading import Event, Lock
import multiprocessing as mp
from functools import partial

from .analytics_models import AnalyticsError, AnalyticsFilters, PlayerAnalytics
from .config import Config


logger = logging.getLogger(__name__)


class BatchProcessingError(AnalyticsError):
    """Base exception for batch processing operations."""
    pass


class ProcessingCancelledException(BatchProcessingError):
    """Raised when processing is cancelled."""
    pass


@dataclass
class BatchTask:
    """Represents a single task in a batch operation."""
    
    task_id: str
    function: Callable
    args: Tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0  # Higher priority tasks are processed first
    estimated_duration: Optional[float] = None  # Estimated duration in seconds
    dependencies: Set[str] = field(default_factory=set)  # Task IDs this task depends on
    
    def __post_init__(self):
        """Initialize batch task."""
        if not self.task_id:
            raise ValueError("Task ID cannot be empty")
        if not callable(self.function):
            raise ValueError("Function must be callable")


@dataclass
class BatchProgress:
    """Tracks progress of batch processing operations."""
    
    batch_id: str
    total_tasks: int
    completed_tasks: int = 0
    failed_tasks: int = 0
    cancelled_tasks: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    current_task: Optional[str] = None
    estimated_completion: Optional[datetime] = None
    error_messages: List[str] = field(default_factory=list)
    
    @property
    def progress_percentage(self) -> float:
        """Calculate progress percentage."""
        if self.total_tasks == 0:
            return 100.0
        return (self.completed_tasks / self.total_tasks) * 100.0
    
    @property
    def is_complete(self) -> bool:
        """Check if batch processing is complete."""
        return (self.completed_tasks + self.failed_tasks + self.cancelled_tasks) >= self.total_tasks
    
    @property
    def elapsed_time(self) -> Optional[timedelta]:
        """Get elapsed processing time."""
        if not self.start_time:
            return None
        
        end_time = self.end_time or datetime.now()
        return end_time - self.start_time
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        processed_tasks = self.completed_tasks + self.failed_tasks + self.cancelled_tasks
        if processed_tasks == 0:
            return 0.0
        return (self.completed_tasks / processed_tasks) * 100.0


@dataclass
class BatchResult:
    """Result of batch processing operation."""
    
    batch_id: str
    progress: BatchProgress
    results: Dict[str, Any] = field(default_factory=dict)  # task_id -> result
    errors: Dict[str, Exception] = field(default_factory=dict)  # task_id -> error
    
    @property
    def successful_results(self) -> Dict[str, Any]:
        """Get only successful results."""
        return {task_id: result for task_id, result in self.results.items() 
                if task_id not in self.errors}
    
    @property
    def failed_results(self) -> Dict[str, Exception]:
        """Get only failed results."""
        return self.errors


class ProgressTracker:
    """Thread-safe progress tracking for batch operations."""
    
    def __init__(self):
        """Initialize progress tracker."""
        self._progresses: Dict[str, BatchProgress] = {}
        self._lock = Lock()
        self._callbacks: Dict[str, List[Callable[[BatchProgress], None]]] = {}
    
    def create_progress(self, batch_id: str, total_tasks: int) -> BatchProgress:
        """Create a new progress tracker for a batch."""
        with self._lock:
            progress = BatchProgress(
                batch_id=batch_id,
                total_tasks=total_tasks,
                start_time=datetime.now()
            )
            self._progresses[batch_id] = progress
            self._callbacks[batch_id] = []
            return progress
    
    def update_progress(self, batch_id: str, completed: int = 0, failed: int = 0, 
                       cancelled: int = 0, current_task: Optional[str] = None,
                       error_message: Optional[str] = None) -> Optional[BatchProgress]:
        """Update progress for a batch."""
        with self._lock:
            if batch_id not in self._progresses:
                return None
            
            progress = self._progresses[batch_id]
            progress.completed_tasks += completed
            progress.failed_tasks += failed
            progress.cancelled_tasks += cancelled
            
            if current_task:
                progress.current_task = current_task
            
            if error_message:
                progress.error_messages.append(error_message)
            
            # Update estimated completion
            if progress.completed_tasks > 0 and progress.elapsed_time:
                avg_time_per_task = progress.elapsed_time.total_seconds() / progress.completed_tasks
                remaining_tasks = progress.total_tasks - progress.completed_tasks - progress.failed_tasks - progress.cancelled_tasks
                if remaining_tasks > 0:
                    estimated_seconds = remaining_tasks * avg_time_per_task
                    progress.estimated_completion = datetime.now() + timedelta(seconds=estimated_seconds)
            
            # Mark as complete if all tasks are done
            if progress.is_complete and not progress.end_time:
                progress.end_time = datetime.now()
            
            # Notify callbacks
            for callback in self._callbacks.get(batch_id, []):
                try:
                    callback(progress)
                except Exception as e:
                    logger.warning(f"Progress callback failed: {e}")
            
            return progress
    
    def get_progress(self, batch_id: str) -> Optional[BatchProgress]:
        """Get current progress for a batch."""
        with self._lock:
            return self._progresses.get(batch_id)
    
    def add_progress_callback(self, batch_id: str, callback: Callable[[BatchProgress], None]):
        """Add a progress callback for a batch."""
        with self._lock:
            if batch_id in self._callbacks:
                self._callbacks[batch_id].append(callback)
    
    def remove_progress(self, batch_id: str):
        """Remove progress tracking for a batch."""
        with self._lock:
            self._progresses.pop(batch_id, None)
            self._callbacks.pop(batch_id, None)


class CancellationToken:
    """Thread-safe cancellation token for batch operations."""
    
    def __init__(self):
        """Initialize cancellation token."""
        self._cancelled = Event()
        self._reason: Optional[str] = None
        self._lock = Lock()
    
    def cancel(self, reason: Optional[str] = None):
        """Cancel the operation."""
        with self._lock:
            self._reason = reason or "Operation cancelled by user"
            self._cancelled.set()
    
    @property
    def is_cancelled(self) -> bool:
        """Check if operation is cancelled."""
        return self._cancelled.is_set()
    
    @property
    def cancellation_reason(self) -> Optional[str]:
        """Get cancellation reason."""
        with self._lock:
            return self._reason
    
    def check_cancelled(self):
        """Check if cancelled and raise exception if so."""
        if self.is_cancelled:
            raise ProcessingCancelledException(self.cancellation_reason or "Operation cancelled")


class BatchProcessor:
    """High-performance batch processor for analytics operations."""
    
    def __init__(self, config: Config, max_workers: Optional[int] = None):
        """Initialize batch processor.
        
        Args:
            config: Application configuration
            max_workers: Maximum number of worker threads/processes
        """
        self.config = config
        self.max_workers = max_workers or min(32, (mp.cpu_count() or 1) + 4)
        self.progress_tracker = ProgressTracker()
        self.logger = logging.getLogger(__name__)
        
        # Active batch operations
        self._active_batches: Dict[str, CancellationToken] = {}
        self._batch_lock = Lock()
        
        # Performance metrics
        self._metrics = {
            'total_batches_processed': 0,
            'total_tasks_processed': 0,
            'total_processing_time': 0.0,
            'average_batch_size': 0.0,
            'average_processing_time_per_task': 0.0
        }
        self._metrics_lock = Lock()
    
    def process_batch_threaded(
        self,
        batch_id: str,
        tasks: List[BatchTask],
        max_workers: Optional[int] = None,
        progress_callback: Optional[Callable[[BatchProgress], None]] = None
    ) -> BatchResult:
        """Process batch of tasks using thread pool.
        
        Args:
            batch_id: Unique identifier for the batch
            tasks: List of tasks to process
            max_workers: Maximum number of worker threads
            progress_callback: Optional progress callback function
            
        Returns:
            BatchResult with processing results
            
        Raises:
            BatchProcessingError: If batch processing fails
            ProcessingCancelledException: If processing is cancelled
        """
        if not tasks:
            raise BatchProcessingError("No tasks provided for batch processing")
        
        # Create cancellation token and progress tracker
        cancellation_token = CancellationToken()
        with self._batch_lock:
            self._active_batches[batch_id] = cancellation_token
        
        progress = self.progress_tracker.create_progress(batch_id, len(tasks))
        if progress_callback:
            self.progress_tracker.add_progress_callback(batch_id, progress_callback)
        
        try:
            # Sort tasks by priority and resolve dependencies
            sorted_tasks = self._resolve_task_dependencies(tasks)
            
            # Process tasks in thread pool
            workers = max_workers or self.max_workers
            results = {}
            errors = {}
            
            with ThreadPoolExecutor(max_workers=workers) as executor:
                # Submit all tasks
                future_to_task = {}
                for task in sorted_tasks:
                    if cancellation_token.is_cancelled:
                        break
                    
                    # Wrap task function with cancellation check
                    wrapped_func = self._wrap_function_with_cancellation(
                        task.function, cancellation_token
                    )
                    
                    future = executor.submit(wrapped_func, *task.args, **task.kwargs)
                    future_to_task[future] = task
                
                # Process completed tasks
                for future in as_completed(future_to_task):
                    task = future_to_task[future]
                    
                    try:
                        # Check for cancellation
                        cancellation_token.check_cancelled()
                        
                        # Get result
                        result = future.result()
                        results[task.task_id] = result
                        
                        # Update progress
                        self.progress_tracker.update_progress(
                            batch_id, completed=1, current_task=task.task_id
                        )
                        
                    except ProcessingCancelledException:
                        # Task was cancelled
                        self.progress_tracker.update_progress(
                            batch_id, cancelled=1, current_task=task.task_id
                        )
                        
                    except Exception as e:
                        # Task failed
                        errors[task.task_id] = e
                        error_msg = f"Task {task.task_id} failed: {str(e)}"
                        self.progress_tracker.update_progress(
                            batch_id, failed=1, current_task=task.task_id,
                            error_message=error_msg
                        )
                        self.logger.error(error_msg)
            
            # Create final result
            final_progress = self.progress_tracker.get_progress(batch_id)
            batch_result = BatchResult(
                batch_id=batch_id,
                progress=final_progress,
                results=results,
                errors=errors
            )
            
            # Update metrics
            self._update_metrics(len(tasks), final_progress.elapsed_time.total_seconds() if final_progress.elapsed_time else 0)
            
            self.logger.info(f"Batch {batch_id} completed: {len(results)} successful, {len(errors)} failed")
            return batch_result
            
        except Exception as e:
            error_msg = f"Batch processing failed: {str(e)}"
            self.progress_tracker.update_progress(batch_id, error_message=error_msg)
            raise BatchProcessingError(error_msg) from e
            
        finally:
            # Cleanup
            with self._batch_lock:
                self._active_batches.pop(batch_id, None)
            self.progress_tracker.remove_progress(batch_id)
    
    def process_batch_multiprocess(
        self,
        batch_id: str,
        tasks: List[BatchTask],
        max_workers: Optional[int] = None,
        progress_callback: Optional[Callable[[BatchProgress], None]] = None
    ) -> BatchResult:
        """Process batch of tasks using process pool.
        
        Args:
            batch_id: Unique identifier for the batch
            tasks: List of tasks to process
            max_workers: Maximum number of worker processes
            progress_callback: Optional progress callback function
            
        Returns:
            BatchResult with processing results
            
        Raises:
            BatchProcessingError: If batch processing fails
            ProcessingCancelledException: If processing is cancelled
        """
        if not tasks:
            raise BatchProcessingError("No tasks provided for batch processing")
        
        # Create cancellation token and progress tracker
        cancellation_token = CancellationToken()
        with self._batch_lock:
            self._active_batches[batch_id] = cancellation_token
        
        progress = self.progress_tracker.create_progress(batch_id, len(tasks))
        if progress_callback:
            self.progress_tracker.add_progress_callback(batch_id, progress_callback)
        
        try:
            # Sort tasks by priority and resolve dependencies
            sorted_tasks = self._resolve_task_dependencies(tasks)
            
            # Process tasks in process pool
            workers = max_workers or min(self.max_workers, mp.cpu_count())
            results = {}
            errors = {}
            
            with ProcessPoolExecutor(max_workers=workers) as executor:
                # Submit all tasks
                future_to_task = {}
                for task in sorted_tasks:
                    if cancellation_token.is_cancelled:
                        break
                    
                    # For multiprocessing, we can't wrap functions easily
                    # So we'll check cancellation in the main loop
                    future = executor.submit(task.function, *task.args, **task.kwargs)
                    future_to_task[future] = task
                
                # Process completed tasks
                for future in as_completed(future_to_task):
                    task = future_to_task[future]
                    
                    try:
                        # Check for cancellation
                        cancellation_token.check_cancelled()
                        
                        # Get result with timeout to allow cancellation checks
                        result = future.result(timeout=1.0)
                        results[task.task_id] = result
                        
                        # Update progress
                        self.progress_tracker.update_progress(
                            batch_id, completed=1, current_task=task.task_id
                        )
                        
                    except ProcessingCancelledException:
                        # Task was cancelled
                        future.cancel()
                        self.progress_tracker.update_progress(
                            batch_id, cancelled=1, current_task=task.task_id
                        )
                        
                    except Exception as e:
                        # Task failed
                        errors[task.task_id] = e
                        error_msg = f"Task {task.task_id} failed: {str(e)}"
                        self.progress_tracker.update_progress(
                            batch_id, failed=1, current_task=task.task_id,
                            error_message=error_msg
                        )
                        self.logger.error(error_msg)
            
            # Create final result
            final_progress = self.progress_tracker.get_progress(batch_id)
            batch_result = BatchResult(
                batch_id=batch_id,
                progress=final_progress,
                results=results,
                errors=errors
            )
            
            # Update metrics
            self._update_metrics(len(tasks), final_progress.elapsed_time.total_seconds() if final_progress.elapsed_time else 0)
            
            self.logger.info(f"Batch {batch_id} completed: {len(results)} successful, {len(errors)} failed")
            return batch_result
            
        except Exception as e:
            error_msg = f"Batch processing failed: {str(e)}"
            self.progress_tracker.update_progress(batch_id, error_message=error_msg)
            raise BatchProcessingError(error_msg) from e
            
        finally:
            # Cleanup
            with self._batch_lock:
                self._active_batches.pop(batch_id, None)
            self.progress_tracker.remove_progress(batch_id)
    
    def cancel_batch(self, batch_id: str, reason: Optional[str] = None) -> bool:
        """Cancel a running batch operation.
        
        Args:
            batch_id: Batch ID to cancel
            reason: Optional cancellation reason
            
        Returns:
            True if batch was cancelled, False if not found
        """
        with self._batch_lock:
            if batch_id in self._active_batches:
                self._active_batches[batch_id].cancel(reason)
                self.logger.info(f"Cancelled batch {batch_id}: {reason or 'No reason provided'}")
                return True
            return False
    
    def get_active_batches(self) -> List[str]:
        """Get list of active batch IDs."""
        with self._batch_lock:
            return list(self._active_batches.keys())
    
    def get_batch_progress(self, batch_id: str) -> Optional[BatchProgress]:
        """Get progress for a specific batch."""
        return self.progress_tracker.get_progress(batch_id)
    
    def _resolve_task_dependencies(self, tasks: List[BatchTask]) -> List[BatchTask]:
        """Resolve task dependencies and return sorted task list.
        
        Args:
            tasks: List of tasks to sort
            
        Returns:
            List of tasks sorted by dependencies and priority
            
        Raises:
            BatchProcessingError: If circular dependencies are detected
        """
        # Create task lookup
        task_lookup = {task.task_id: task for task in tasks}
        
        # Check for missing dependencies
        for task in tasks:
            for dep_id in task.dependencies:
                if dep_id not in task_lookup:
                    raise BatchProcessingError(f"Task {task.task_id} depends on missing task {dep_id}")
        
        # Topological sort with priority
        sorted_tasks = []
        visited = set()
        temp_visited = set()
        
        def visit(task: BatchTask):
            if task.task_id in temp_visited:
                raise BatchProcessingError(f"Circular dependency detected involving task {task.task_id}")
            
            if task.task_id not in visited:
                temp_visited.add(task.task_id)
                
                # Visit dependencies first
                for dep_id in task.dependencies:
                    dep_task = task_lookup[dep_id]
                    visit(dep_task)
                
                temp_visited.remove(task.task_id)
                visited.add(task.task_id)
                sorted_tasks.append(task)
        
        # Visit all tasks
        for task in tasks:
            if task.task_id not in visited:
                visit(task)
        
        # Sort by priority within dependency constraints
        # Tasks with higher priority should be processed first when possible
        return sorted(sorted_tasks, key=lambda t: -t.priority)
    
    def _wrap_function_with_cancellation(self, func: Callable, token: CancellationToken) -> Callable:
        """Wrap a function to check for cancellation.
        
        Args:
            func: Function to wrap
            token: Cancellation token
            
        Returns:
            Wrapped function that checks for cancellation
        """
        def wrapped(*args, **kwargs):
            token.check_cancelled()
            result = func(*args, **kwargs)
            token.check_cancelled()
            return result
        
        return wrapped
    
    def _update_metrics(self, task_count: int, processing_time: float):
        """Update performance metrics.
        
        Args:
            task_count: Number of tasks processed
            processing_time: Total processing time in seconds
        """
        with self._metrics_lock:
            self._metrics['total_batches_processed'] += 1
            self._metrics['total_tasks_processed'] += task_count
            self._metrics['total_processing_time'] += processing_time
            
            # Calculate averages
            if self._metrics['total_batches_processed'] > 0:
                self._metrics['average_batch_size'] = (
                    self._metrics['total_tasks_processed'] / self._metrics['total_batches_processed']
                )
            
            if self._metrics['total_tasks_processed'] > 0:
                self._metrics['average_processing_time_per_task'] = (
                    self._metrics['total_processing_time'] / self._metrics['total_tasks_processed']
                )
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for batch processing.
        
        Returns:
            Dictionary containing performance metrics
        """
        with self._metrics_lock:
            return self._metrics.copy()
    
    def reset_metrics(self):
        """Reset performance metrics."""
        with self._metrics_lock:
            self._metrics = {
                'total_batches_processed': 0,
                'total_tasks_processed': 0,
                'total_processing_time': 0.0,
                'average_batch_size': 0.0,
                'average_processing_time_per_task': 0.0
            }


class AnalyticsBatchProcessor:
    """Specialized batch processor for analytics operations."""
    
    def __init__(self, config: Config, analytics_engine, match_manager):
        """Initialize analytics batch processor.
        
        Args:
            config: Application configuration
            analytics_engine: HistoricalAnalyticsEngine instance
            match_manager: MatchManager instance
        """
        self.config = config
        self.analytics_engine = analytics_engine
        self.match_manager = match_manager
        self.batch_processor = BatchProcessor(config)
        self.logger = logging.getLogger(__name__)
    
    def batch_analyze_players(
        self,
        puuids: List[str],
        filters: Optional[AnalyticsFilters] = None,
        progress_callback: Optional[Callable[[BatchProgress], None]] = None
    ) -> BatchResult:
        """Batch analyze multiple players.
        
        Args:
            puuids: List of player PUUIDs to analyze
            filters: Optional filters to apply
            progress_callback: Optional progress callback
            
        Returns:
            BatchResult with player analytics
        """
        batch_id = f"player_analysis_{int(time.time())}"
        
        # Create tasks for each player
        tasks = []
        for i, puuid in enumerate(puuids):
            task = BatchTask(
                task_id=f"analyze_player_{puuid}",
                function=self.analytics_engine.analyze_player_performance,
                args=(puuid,),
                kwargs={'filters': filters},
                priority=len(puuids) - i  # Process in order
            )
            tasks.append(task)
        
        self.logger.info(f"Starting batch analysis for {len(puuids)} players")
        return self.batch_processor.process_batch_threaded(
            batch_id, tasks, progress_callback=progress_callback
        )
    
    def batch_analyze_champions(
        self,
        champion_analyses: List[Tuple[str, int, str]],  # (puuid, champion_id, role)
        filters: Optional[AnalyticsFilters] = None,
        progress_callback: Optional[Callable[[BatchProgress], None]] = None
    ) -> BatchResult:
        """Batch analyze champion performance for multiple combinations.
        
        Args:
            champion_analyses: List of (puuid, champion_id, role) tuples
            filters: Optional filters to apply
            progress_callback: Optional progress callback
            
        Returns:
            BatchResult with champion analytics
        """
        batch_id = f"champion_analysis_{int(time.time())}"
        
        # Create tasks for each champion analysis
        tasks = []
        for i, (puuid, champion_id, role) in enumerate(champion_analyses):
            task = BatchTask(
                task_id=f"analyze_champion_{puuid}_{champion_id}_{role}",
                function=self.analytics_engine.analyze_champion_performance,
                args=(puuid, champion_id, role),
                kwargs={'filters': filters},
                priority=len(champion_analyses) - i
            )
            tasks.append(task)
        
        self.logger.info(f"Starting batch champion analysis for {len(champion_analyses)} combinations")
        return self.batch_processor.process_batch_threaded(
            batch_id, tasks, progress_callback=progress_callback
        )
    
    def batch_calculate_trends(
        self,
        trend_analyses: List[Tuple[str, int, str]],  # (puuid, time_window_days, metric)
        progress_callback: Optional[Callable[[BatchProgress], None]] = None
    ) -> BatchResult:
        """Batch calculate performance trends for multiple players/metrics.
        
        Args:
            trend_analyses: List of (puuid, time_window_days, metric) tuples
            progress_callback: Optional progress callback
            
        Returns:
            BatchResult with trend analytics
        """
        batch_id = f"trend_analysis_{int(time.time())}"
        
        # Create tasks for each trend analysis
        tasks = []
        for i, (puuid, time_window_days, metric) in enumerate(trend_analyses):
            task = BatchTask(
                task_id=f"calculate_trends_{puuid}_{metric}_{time_window_days}",
                function=self.analytics_engine.calculate_performance_trends,
                args=(puuid, time_window_days, metric),
                priority=len(trend_analyses) - i
            )
            tasks.append(task)
        
        self.logger.info(f"Starting batch trend analysis for {len(trend_analyses)} combinations")
        return self.batch_processor.process_batch_threaded(
            batch_id, tasks, progress_callback=progress_callback
        )
    
    def cancel_batch_operation(self, batch_id: str, reason: Optional[str] = None) -> bool:
        """Cancel a batch operation.
        
        Args:
            batch_id: Batch ID to cancel
            reason: Optional cancellation reason
            
        Returns:
            True if cancelled successfully
        """
        return self.batch_processor.cancel_batch(batch_id, reason)
    
    def get_active_operations(self) -> List[str]:
        """Get list of active batch operation IDs."""
        return self.batch_processor.get_active_batches()
    
    def get_operation_progress(self, batch_id: str) -> Optional[BatchProgress]:
        """Get progress for a batch operation."""
        return self.batch_processor.get_batch_progress(batch_id)