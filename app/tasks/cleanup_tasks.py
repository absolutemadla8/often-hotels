"""
Cleanup and maintenance background tasks
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any

from tortoise import Tortoise

from app.core.celery_app import celery_app
from app.models.models import User, Task, TaskStatus
from .base import BaseTask

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, base=BaseTask)
def cleanup_expired_refresh_tokens(self) -> Dict[str, Any]:
    """Clean up expired refresh tokens from the database"""
    return asyncio.run(_cleanup_expired_refresh_tokens_async(self))


async def _cleanup_expired_refresh_tokens_async(task_instance) -> Dict[str, Any]:
    """Async implementation of refresh token cleanup"""
    task_id = task_instance.request.id
    
    try:
        # Initialize Tortoise if not already initialized
        if not Tortoise._get_db(None):
            from tortoise_config import TORTOISE_ORM
            await Tortoise.init(config=TORTOISE_ORM)
        
        await task_instance.update_task_status(task_id, TaskStatus.STARTED)
        
        await task_instance.update_task_status(
            task_id,
            TaskStatus.STARTED,
            progress_current=20,
            progress_message="Identifying expired refresh tokens"
        )
        
        # Calculate cutoff date (30 days ago)
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        
        # Mock cleanup - in reality you'd clean from a refresh_tokens table
        tokens_cleaned = 0
        
        # Simulate cleanup process
        await asyncio.sleep(1)
        
        await task_instance.update_task_status(
            task_id,
            TaskStatus.STARTED,
            progress_current=80,
            progress_message=f"Cleaned {tokens_cleaned} expired tokens"
        )
        
        result = {
            "success": True,
            "tokens_cleaned": tokens_cleaned,
            "cutoff_date": cutoff_date.isoformat(),
            "cleanup_completed_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Refresh token cleanup completed: {result}")
        
        await task_instance.update_task_status(task_id, TaskStatus.SUCCESS, result=result)
        return result
        
    except Exception as e:
        error_msg = f"Refresh token cleanup failed: {str(e)}"
        logger.error(error_msg)
        await task_instance.update_task_status(task_id, TaskStatus.FAILURE, error_message=error_msg)
        raise


@celery_app.task(bind=True, base=BaseTask)
def cleanup_old_tasks(self, days_old: int = 30) -> Dict[str, Any]:
    """Clean up old completed tasks from the database"""
    return asyncio.run(_cleanup_old_tasks_async(self, days_old))


async def _cleanup_old_tasks_async(task_instance, days_old: int) -> Dict[str, Any]:
    """Async implementation of old tasks cleanup"""
    task_id = task_instance.request.id
    
    try:
        # Initialize Tortoise if not already initialized
        if not Tortoise._get_db(None):
            from tortoise_config import TORTOISE_ORM
            await Tortoise.init(config=TORTOISE_ORM)
        
        await task_instance.update_task_status(task_id, TaskStatus.STARTED)
        
        await task_instance.update_task_status(
            task_id,
            TaskStatus.STARTED,
            progress_current=20,
            progress_message=f"Finding tasks older than {days_old} days"
        )
        
        # Calculate cutoff date
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        # Find old completed tasks
        old_tasks = await Task.filter(
            created_at__lt=cutoff_date,
            status__in=[TaskStatus.SUCCESS, TaskStatus.FAILURE]
        ).all()
        
        total_tasks = len(old_tasks)
        
        await task_instance.update_task_status(
            task_id,
            TaskStatus.STARTED,
            progress_current=40,
            progress_message=f"Found {total_tasks} old tasks to clean up"
        )
        
        # Delete old tasks in batches
        batch_size = 100
        tasks_deleted = 0
        
        for i in range(0, total_tasks, batch_size):
            batch = old_tasks[i:i + batch_size]
            batch_ids = [task.id for task in batch]
            
            # Delete batch
            deleted_count = await Task.filter(id__in=batch_ids).delete()
            tasks_deleted += deleted_count
            
            # Update progress
            progress = 40 + (tasks_deleted / total_tasks) * 40 if total_tasks > 0 else 80
            await task_instance.update_task_status(
                task_id,
                TaskStatus.STARTED,
                progress_current=int(progress),
                progress_message=f"Deleted {tasks_deleted}/{total_tasks} old tasks"
            )
            
            # Small delay between batches
            await asyncio.sleep(0.1)
        
        result = {
            "success": True,
            "tasks_deleted": tasks_deleted,
            "total_tasks_found": total_tasks,
            "days_old": days_old,
            "cutoff_date": cutoff_date.isoformat(),
            "cleanup_completed_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Old tasks cleanup completed: {result}")
        
        await task_instance.update_task_status(task_id, TaskStatus.SUCCESS, result=result)
        return result
        
    except Exception as e:
        error_msg = f"Old tasks cleanup failed: {str(e)}"
        logger.error(error_msg)
        await task_instance.update_task_status(task_id, TaskStatus.FAILURE, error_message=error_msg)
        raise