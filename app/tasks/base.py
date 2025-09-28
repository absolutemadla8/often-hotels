"""
Base task class for Celery tasks with database tracking
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from celery import Task
from tortoise import Tortoise

from app.models.models import Task as TaskModel, TaskLog, TaskStatus, LogLevel

logger = logging.getLogger(__name__)


class BaseTask(Task):
    """
    Custom base task class that provides database tracking functionality
    """
    
    def _get_task_type_from_name(self, task_name: Optional[str]) -> str:
        """Extract task type from task name"""
        if not task_name:
            return "unknown"
        
        # Map task names to types
        task_type_mapping = {
            "hotel_tracking_tasks.track_hotels_for_destinations": "hotel_tracking",
            "cleanup_tasks.cleanup_expired_refresh_tokens": "cleanup",
            "serp_service": "hotel_search",
        }
        
        # Check for exact matches first
        if task_name in task_type_mapping:
            return task_type_mapping[task_name]
        
        # Check for partial matches
        for pattern, task_type in task_type_mapping.items():
            if pattern in task_name:
                return task_type
        
        # Extract from task name structure (e.g., "app.tasks.hotel_tracking_tasks.track_hotels")
        if "hotel_tracking" in task_name:
            return "hotel_tracking"
        elif "cleanup" in task_name:
            return "cleanup"
        elif "email" in task_name:
            return "email"
        elif "notification" in task_name:
            return "notification"
        
        return "general"

    async def log_task_message(
        self,
        task_id: str,
        message: str,
        level: LogLevel = LogLevel.INFO,
        source: str = None,
        phase: str = None,
        progress_hint: int = None,
        metadata: Dict[str, Any] = None
    ):
        """Log a structured message for the task"""
        try:
            # Get or create the task record
            task = await TaskModel.get_or_none(task_id=task_id)
            if not task:
                logger.warning(f"Task {task_id} not found for logging, skipping log entry")
                return
            
            # Create the log entry
            await TaskLog.create(
                task=task,
                level=level,
                message=message,
                source=source or f"{self.name}",
                phase=phase,
                progress_hint=progress_hint,
                metadata=metadata
            )
            
            # Also log to standard logger with task context
            log_method = getattr(logger, level.lower(), logger.info)
            log_method(f"[Task {task_id}] {message}")
            
        except Exception as e:
            logger.error(f"Failed to log task message for {task_id}: {e}")

    async def log_info(self, task_id: str, message: str, **kwargs):
        """Log an info message"""
        await self.log_task_message(task_id, message, LogLevel.INFO, **kwargs)

    async def log_warning(self, task_id: str, message: str, **kwargs):
        """Log a warning message"""
        await self.log_task_message(task_id, message, LogLevel.WARNING, **kwargs)

    async def log_error(self, task_id: str, message: str, **kwargs):
        """Log an error message"""
        await self.log_task_message(task_id, message, LogLevel.ERROR, **kwargs)

    async def log_debug(self, task_id: str, message: str, **kwargs):
        """Log a debug message"""
        await self.log_task_message(task_id, message, LogLevel.DEBUG, **kwargs)

    async def log_critical(self, task_id: str, message: str, **kwargs):
        """Log a critical message"""
        await self.log_task_message(task_id, message, LogLevel.CRITICAL, **kwargs)

    async def log_phase_start(self, task_id: str, phase: str, message: str = None):
        """Log the start of a task phase"""
        msg = message or f"Starting {phase} phase"
        await self.log_task_message(
            task_id, 
            msg, 
            LogLevel.INFO, 
            phase=phase,
            metadata={"phase_event": "start"}
        )

    async def log_phase_end(self, task_id: str, phase: str, message: str = None):
        """Log the end of a task phase"""
        msg = message or f"Completed {phase} phase"
        await self.log_task_message(
            task_id, 
            msg, 
            LogLevel.INFO, 
            phase=phase,
            metadata={"phase_event": "end"}
        )

    async def log_progress(self, task_id: str, message: str, progress: int, phase: str = None):
        """Log progress with a hint"""
        await self.log_task_message(
            task_id,
            message,
            LogLevel.INFO,
            phase=phase,
            progress_hint=progress,
            metadata={"progress": progress}
        )

    async def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        task_type: Optional[str] = None,
        progress_current: Optional[int] = None,
        progress_message: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        traceback: Optional[str] = None
    ):
        """Update task status in the database"""
        try:
            task = await TaskModel.get_or_none(task_id=task_id)
            
            # Create task record if it doesn't exist
            if not task:
                # Determine task_type from task name or provided parameter
                resolved_task_type = task_type or self._get_task_type_from_name(self.name)
                
                task = await TaskModel.create(
                    task_id=task_id,
                    task_name=self.name or "unknown_task",
                    task_type=resolved_task_type,
                    status=TaskStatus.PENDING,
                    progress_current=0,
                    progress_total=100,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                logger.info(f"Created new task record for {task_id} with type {resolved_task_type}")

            # Update basic status
            task.status = status
            task.updated_at = datetime.utcnow()

            # Update progress if provided
            if progress_current is not None:
                task.progress_current = progress_current
            if progress_message is not None:
                task.progress_message = progress_message

            # Update timestamps based on status
            if status == TaskStatus.STARTED and task.started_at is None:
                task.started_at = datetime.utcnow()
            elif status in [TaskStatus.SUCCESS, TaskStatus.FAILURE, TaskStatus.REVOKED]:
                if task.completed_at is None:
                    task.completed_at = datetime.utcnow()
                
                # Calculate execution time
                if task.started_at:
                    execution_time = (task.completed_at - task.started_at).total_seconds()
                    task.execution_time_seconds = execution_time

            # Update result and errors
            if result is not None:
                task.result = result
            if error_message is not None:
                task.error_message = error_message
            if traceback is not None:
                task.traceback = traceback

            await task.save()
            logger.debug(f"Updated task {task_id} status to {status}")

        except Exception as e:
            logger.error(f"Failed to update task {task_id} status: {e}")

    def on_success(self, retval, task_id, args, kwargs):
        """Called when task executes successfully"""
        logger.info(f"Task {task_id} completed successfully")

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when task fails"""
        logger.error(f"Task {task_id} failed: {exc}")

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Called when task is retried"""
        logger.warning(f"Task {task_id} retrying: {exc}")