"""
Notification-related background tasks
"""

import logging
import asyncio
from typing import Dict, Any, Optional

from tortoise import Tortoise

from app.core.celery_app import celery_app
from app.models.models import User, TaskStatus
from .base import BaseTask

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, base=BaseTask)
def send_push_notification(self, user_id: int, title: str, message: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Send push notification to user"""
    return asyncio.run(_send_push_notification_async(self, user_id, title, message, data))


async def _send_push_notification_async(task_instance, user_id: int, title: str, message: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Async implementation of push notification task"""
    task_id = task_instance.request.id
    
    try:
        # Initialize Tortoise if not already initialized
        if not Tortoise._get_db(None):
            from tortoise_config import TORTOISE_ORM
            await Tortoise.init(config=TORTOISE_ORM)
        
        await task_instance.update_task_status(task_id, TaskStatus.STARTED)
        
        # Get user
        user = await User.get_or_none(id=user_id)
        if not user:
            raise ValueError(f"User with ID {user_id} not found")
        
        await task_instance.update_task_status(
            task_id,
            TaskStatus.STARTED,
            progress_current=30,
            progress_message="Preparing push notification"
        )
        
        # Mock push notification sending
        success = await _send_push_notification_to_device(
            user=user,
            title=title,
            message=message,
            data=data
        )
        
        if success:
            result = {
                "success": True,
                "user_id": user_id,
                "title": title,
                "message": message,
                "data": data,
                "sent_to": user.email,
                "message_status": "Push notification sent successfully"
            }
            await task_instance.update_task_status(task_id, TaskStatus.SUCCESS, result=result)
            return result
        else:
            raise Exception("Failed to send push notification")
            
    except Exception as e:
        error_msg = f"Failed to send push notification: {str(e)}"
        logger.error(error_msg)
        await task_instance.update_task_status(task_id, TaskStatus.FAILURE, error_message=error_msg)
        raise


async def _send_push_notification_to_device(user: User, title: str, message: str, data: Optional[Dict[str, Any]] = None) -> bool:
    """Send push notification to user's device (mock implementation)"""
    try:
        # Mock push notification - replace with actual implementation
        logger.info(f"📱 MOCK PUSH NOTIFICATION SENT:")
        logger.info(f"To: {user.email}")
        logger.info(f"Title: {title}")
        logger.info(f"Message: {message}")
        logger.info(f"Data: {data}")
        
        # Simulate notification sending delay
        await asyncio.sleep(0.5)
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to send push notification: {e}")
        return False