"""
Base task class for Celery tasks with database tracking
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from celery import Task
from tortoise import Tortoise

from app.models.models import Task as TaskModel, TaskStatus

logger = logging.getLogger(__name__)


class BaseTask(Task):
    """
    Custom base task class that provides database tracking functionality
    """

    async def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        progress_current: Optional[int] = None,
        progress_message: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        traceback: Optional[str] = None
    ):
        """Update task status in the database"""
        try:
            task = await TaskModel.get_or_none(task_id=task_id)
            if not task:
                logger.warning(f"Task {task_id} not found in database")
                return

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