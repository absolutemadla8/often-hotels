"""
Email-related background tasks
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, Any

from tortoise import Tortoise

from app.core.celery_app import celery_app
from app.models.models import User, TaskStatus
from .base import BaseTask

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, base=BaseTask)
def send_welcome_email(self, user_id: int) -> Dict[str, Any]:
    """Send welcome email to new user"""
    return asyncio.run(_send_welcome_email_async(self, user_id))


async def _send_welcome_email_async(task_instance, user_id: int) -> Dict[str, Any]:
    """Async implementation of welcome email task"""
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
            progress_message="Preparing welcome email"
        )
        
        # Mock email sending
        await _send_email_to_user(
            user=user,
            template="welcome",
            subject="Welcome to Often Hotels!",
            data={
                "user_name": user.full_name or user.email,
                "welcome_bonus": 50
            }
        )
        
        result = {
            "success": True,
            "user_id": user_id,
            "email": user.email,
            "template": "welcome",
            "sent_at": datetime.utcnow().isoformat(),
            "message": "Welcome email sent successfully"
        }
        
        await task_instance.update_task_status(task_id, TaskStatus.SUCCESS, result=result)
        return result
        
    except Exception as e:
        error_msg = f"Failed to send welcome email: {str(e)}"
        logger.error(error_msg)
        await task_instance.update_task_status(task_id, TaskStatus.FAILURE, error_message=error_msg)
        raise


@celery_app.task(bind=True, base=BaseTask)
def send_price_alert_email(self, user_id: int, alert_data: Dict[str, Any]) -> Dict[str, Any]:
    """Send price alert email to user"""
    return asyncio.run(_send_price_alert_email_async(self, user_id, alert_data))


async def _send_price_alert_email_async(task_instance, user_id: int, alert_data: Dict[str, Any]) -> Dict[str, Any]:
    """Async implementation of price alert email task"""
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
            progress_current=40,
            progress_message="Preparing price alert email"
        )
        
        # Mock email sending
        await _send_email_to_user(
            user=user,
            template="price_alert",
            subject="Price Alert: Hotel Deal Found!",
            data=alert_data
        )
        
        result = {
            "success": True,
            "user_id": user_id,
            "email": user.email,
            "template": "price_alert",
            "alert_data": alert_data,
            "sent_at": datetime.utcnow().isoformat(),
            "message": "Price alert email sent successfully"
        }
        
        await task_instance.update_task_status(task_id, TaskStatus.SUCCESS, result=result)
        return result
        
    except Exception as e:
        error_msg = f"Failed to send price alert email: {str(e)}"
        logger.error(error_msg)
        await task_instance.update_task_status(task_id, TaskStatus.FAILURE, error_message=error_msg)
        raise


async def _send_email_to_user(user: User, template: str, subject: str, data: Dict[str, Any]) -> bool:
    """Send email to user (mock implementation)"""
    try:
        # Mock email sending - replace with actual email service
        logger.info(f"📧 MOCK EMAIL SENT:")
        logger.info(f"To: {user.email}")
        logger.info(f"Subject: {subject}")
        logger.info(f"Template: {template}")
        logger.info(f"Data: {data}")
        
        # Simulate email sending delay
        await asyncio.sleep(0.5)
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False