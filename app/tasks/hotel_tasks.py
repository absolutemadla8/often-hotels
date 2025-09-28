"""
Hotel-related background tasks
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, Any

from tortoise import Tortoise

from app.core.celery_app import celery_app
from app.models.models import Hotel, TaskStatus, User
from .base import BaseTask

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, base=BaseTask)
def sync_hotel_data(self) -> Dict[str, Any]:
    """Sync hotel data from external APIs"""
    return asyncio.run(_sync_hotel_data_async(self))


async def _sync_hotel_data_async(task_instance) -> Dict[str, Any]:
    """Async implementation of hotel data sync"""
    task_id = task_instance.request.id
    tortoise_initialized = False
    
    try:
        # Initialize Tortoise if not already initialized
        from app.core.config import settings
        from app.models.models import Hotel
        
        try:
            # Check if Tortoise is properly initialized by trying to access the model's db connection
            _ = Hotel._meta.db
            logger.info(f"Using existing Tortoise connection for hotel sync task {task_id}")
        except:
            # If we can't access the db, we need to initialize
            await Tortoise.init(
                db_url=settings.DATABASE_URL,
                modules={"models": ["app.models.models"]}
            )
            tortoise_initialized = True
            logger.info(f"Tortoise initialized for hotel sync task {task_id}")
        
        await task_instance.update_task_status(task_id, TaskStatus.STARTED)
        
        # Get all active hotels to update
        hotels = await Hotel.filter(is_active=True).all()
        total_hotels = len(hotels)
        
        await task_instance.update_task_status(
            task_id,
            TaskStatus.STARTED,
            progress_current=20,
            progress_message=f"Found {total_hotels} hotels to sync"
        )
        
        # Process hotels in batches for demo
        processed = 0
        for i, hotel in enumerate(hotels[:5]):  # Process first 5 for demo
            # Simulate hotel data update
            await asyncio.sleep(0.1)
            processed += 1
            
            progress = 20 + (processed / min(5, total_hotels)) * 60
            await task_instance.update_task_status(
                task_id,
                TaskStatus.STARTED,
                progress_current=int(progress),
                progress_message=f"Processed {processed}/{min(5, total_hotels)} hotels"
            )
        
        result = {
            "success": True,
            "total_hotels": total_hotels,
            "hotels_processed": processed,
            "hotels_updated": processed,
            "errors": 0,
            "sync_completed_at": datetime.utcnow().isoformat()
        }
        
        await task_instance.update_task_status(task_id, TaskStatus.SUCCESS, result=result)
        return result
        
    except Exception as e:
        error_msg = f"Hotel data sync failed: {str(e)}"
        logger.error(error_msg)
        await task_instance.update_task_status(task_id, TaskStatus.FAILURE, error_message=error_msg)
        raise
    finally:
        # Clean up Tortoise connection if we initialized it
        if tortoise_initialized:
            await Tortoise.close_connections()
            logger.info(f"Closed Tortoise connections for hotel sync task {task_id}")


@celery_app.task(bind=True, base=BaseTask)
def process_hotel_search(self, user_id: int, search_criteria: Dict[str, Any]) -> Dict[str, Any]:
    """Process hotel search in background"""
    return asyncio.run(_process_hotel_search_async(self, user_id, search_criteria))


async def _process_hotel_search_async(task_instance, user_id: int, search_criteria: Dict[str, Any]) -> Dict[str, Any]:
    """Async implementation of hotel search processing"""
    task_id = task_instance.request.id
    tortoise_initialized = False
    
    try:
        # Initialize Tortoise if not already initialized
        from app.core.config import settings
        from app.models.models import User
        
        try:
            # Check if Tortoise is properly initialized by trying to access the model's db connection
            _ = User._meta.db
            logger.info(f"Using existing Tortoise connection for hotel search task {task_id}")
        except:
            # If we can't access the db, we need to initialize
            await Tortoise.init(
                db_url=settings.DATABASE_URL,
                modules={"models": ["app.models.models"]}
            )
            tortoise_initialized = True
            logger.info(f"Tortoise initialized for hotel search task {task_id}")
        
        await task_instance.update_task_status(task_id, TaskStatus.STARTED)
        
        # Get user
        user = await User.get_or_none(id=user_id)
        if not user:
            raise ValueError(f"User with ID {user_id} not found")
        
        destination = search_criteria.get("destination", "Unknown")
        
        await task_instance.update_task_status(
            task_id,
            TaskStatus.STARTED,
            progress_current=30,
            progress_message=f"Searching hotels in {destination}"
        )
        
        # Mock search process
        await asyncio.sleep(2)  # Simulate API call delay
        
        # Mock search results
        mock_hotels = [
            {
                "id": i,
                "name": f"Hotel {i}",
                "destination": destination,
                "star_rating": 3 + (i % 3),
                "price": 100 + (i * 25),
                "currency": "USD",
                "availability": True
            }
            for i in range(1, 11)  # Return 10 mock results
        ]
        
        result = {
            "success": True,
            "user_id": user_id,
            "search_criteria": search_criteria,
            "hotels_found": len(mock_hotels),
            "hotels": mock_hotels,
            "search_completed_at": datetime.utcnow().isoformat()
        }
        
        await task_instance.update_task_status(task_id, TaskStatus.SUCCESS, result=result)
        return result
        
    except Exception as e:
        error_msg = f"Hotel search failed: {str(e)}"
        logger.error(error_msg)
        await task_instance.update_task_status(task_id, TaskStatus.FAILURE, error_message=error_msg)
        raise
    finally:
        # Clean up Tortoise connection if we initialized it
        if tortoise_initialized:
            await Tortoise.close_connections()
            logger.info(f"Closed Tortoise connections for hotel search task {task_id}")