"""
Hotel Price Tracking Background Tasks

This module contains Celery background tasks for hotel price tracking operations.
These tasks can be scheduled as cron jobs or triggered manually via API.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

from tortoise import Tortoise

from app.core.celery_app import celery_app
from app.models.models import TaskStatus
from app.services.hotel_tracking_service import HotelTrackingService
from .base import BaseTask

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, base=BaseTask)
def scan_destinations_for_tracking(self) -> Dict[str, Any]:
    """
    Main cron job task to scan all destinations with tracking enabled
    and update hotel prices.
    
    This task should be scheduled to run daily or at desired intervals.
    """
    try:
        logger.info(f"Starting hotel tracking task with ID: {self.request.id}")
        result = asyncio.run(_scan_destinations_for_tracking_async(self))
        logger.info(f"Hotel tracking task completed: {result}")
        return result
    except Exception as e:
        logger.error(f"Hotel tracking task failed: {e}", exc_info=True)
        raise


async def _scan_destinations_for_tracking_async(task_instance) -> Dict[str, Any]:
    """Async implementation of destination scanning for hotel tracking"""
    task_id = task_instance.request.id
    logger.info(f"Async function started for task {task_id}")
    tortoise_initialized = False
    
    try:
        # Initialize Tortoise for this task if not already initialized
        from app.core.config import settings
        from tortoise import connections
        
        try:
            # Check if Tortoise is properly initialized by trying to get a connection
            from app.models.models import Destination
            try:
                # Try to access the model's db connection to see if it's properly initialized
                _ = Destination._meta.db
                logger.info(f"Using existing Tortoise connection for main scan task {task_id}")
            except:
                # If we can't access the db, we need to initialize
                await Tortoise.init(
                    db_url=settings.DATABASE_URL,
                    modules={"models": ["app.models.models"]}
                )
                tortoise_initialized = True
                logger.info(f"Tortoise initialized for main scan task {task_id}")
        except Exception as e:
            # Fallback: always try to initialize
            try:
                await Tortoise.init(
                    db_url=settings.DATABASE_URL,
                    modules={"models": ["app.models.models"]}
                )
                tortoise_initialized = True
                logger.info(f"Tortoise initialized (fallback) for main scan task {task_id}")
            except Exception as init_error:
                logger.error(f"Failed to initialize Tortoise: {init_error}")
                raise
        
        await task_instance.update_task_status(task_id, TaskStatus.STARTED, task_type="hotel_tracking")
        await task_instance.log_phase_start(task_id, "initialization", "Starting hotel tracking scan")
        
        # Update progress: Starting hotel tracking scan
        await task_instance.update_task_status(
            task_id,
            TaskStatus.STARTED,
            task_type="hotel_tracking",
            progress_current=10,
            progress_message="Initializing hotel tracking service"
        )
        await task_instance.log_progress(task_id, "Initializing hotel tracking service", 10, "initialization")
        
        # Initialize hotel tracking service
        async with HotelTrackingService() as tracking_service:
            await task_instance.log_phase_end(task_id, "initialization", "Hotel tracking service initialized")
            await task_instance.log_phase_start(task_id, "destinations", "Scanning destinations with tracking enabled")
            
            # Update progress: Service initialized
            await task_instance.update_task_status(
                task_id,
                TaskStatus.STARTED,
                progress_current=20,
                progress_message="Scanning destinations with tracking enabled"
            )
            await task_instance.log_progress(task_id, "Scanning destinations with tracking enabled", 20, "destinations")
            
            # Perform the main tracking operation with enhanced progress tracking
            tracking_result = await tracking_service.scan_all_tracking_destinations_with_progress(
                task_instance, task_id
            )
            
            # Update progress based on results
            if tracking_result['success']:
                await task_instance.log_phase_end(task_id, "destinations", f"Successfully processed {tracking_result['destinations_processed']} destinations")
                await task_instance.update_task_status(
                    task_id,
                    TaskStatus.STARTED,
                    progress_current=90,
                    progress_message=f"Processed {tracking_result['destinations_processed']} destinations"
                )
                await task_instance.log_info(
                    task_id, 
                    f"Discovered {tracking_result['hotels_discovered']} hotels, created {tracking_result['price_records_created']} price records",
                    phase="summary",
                    metadata={
                        "hotels_discovered": tracking_result['hotels_discovered'],
                        "price_records_created": tracking_result['price_records_created']
                    }
                )
            else:
                await task_instance.log_phase_end(task_id, "destinations", f"Completed with {len(tracking_result.get('errors', []))} errors")
                await task_instance.update_task_status(
                    task_id,
                    TaskStatus.STARTED,
                    progress_current=70,
                    progress_message=f"Completed with {len(tracking_result.get('errors', []))} errors"
                )
                for error in tracking_result.get('errors', []):
                    await task_instance.log_error(task_id, f"Error during processing: {error}", phase="destinations")
        
        # Prepare final result
        result = {
            "success": tracking_result['success'],
            "task_type": "hotel_tracking_scan",
            "destinations_found": tracking_result['destinations_found'],
            "destinations_processed": tracking_result['destinations_processed'],
            "hotels_discovered": tracking_result['hotels_discovered'],
            "price_records_created": tracking_result['price_records_created'],
            "processing_time_seconds": tracking_result['processing_time_seconds'],
            "errors": tracking_result['errors'],
            "completed_at": tracking_result.get('completed_at', datetime.utcnow().isoformat())
        }
        
        # Update final task status
        final_status = TaskStatus.SUCCESS if tracking_result['success'] else TaskStatus.FAILURE
        await task_instance.log_phase_start(task_id, "completion", "Finalizing hotel tracking scan")
        await task_instance.update_task_status(task_id, final_status, task_type="hotel_tracking", result=result)
        await task_instance.log_info(
            task_id,
            f"Hotel tracking scan completed with status: {final_status}",
            phase="completion",
            metadata={"final_status": final_status, "execution_time": tracking_result.get('processing_time_seconds')}
        )
        
        logger.info(
            f"Hotel tracking scan completed: "
            f"{result['destinations_processed']} destinations, "
            f"{result['hotels_discovered']} hotels, "
            f"{result['price_records_created']} price records"
        )
        
        return result
        
    except Exception as e:
        error_msg = f"Hotel tracking scan failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        await task_instance.update_task_status(
            task_id, 
            TaskStatus.FAILURE, 
            task_type="hotel_tracking",
            error_message=error_msg
        )
        raise
    finally:
        # Only close connections if this task initialized them
        if tortoise_initialized:
            try:
                await Tortoise.close_connections()
                logger.info(f"Closed Tortoise connections for main scan task {task_id}")
            except Exception as cleanup_error:
                logger.warning(f"Error closing Tortoise connections for main scan task {task_id}: {cleanup_error}")


@celery_app.task(bind=True, base=BaseTask)
def process_destination_hotels(self, destination_id: int) -> Dict[str, Any]:
    """
    Process hotel tracking for a specific destination
    
    Args:
        destination_id: ID of the destination to process
    """
    return asyncio.run(_process_destination_hotels_async(self, destination_id))


async def _process_destination_hotels_async(task_instance, destination_id: int) -> Dict[str, Any]:
    """Async implementation of single destination hotel tracking"""
    task_id = task_instance.request.id
    tortoise_initialized = False
    
    try:
        # Initialize Tortoise for this task if not already initialized
        from app.core.config import settings
        from tortoise import connections
        try:
            # Check if Tortoise is properly initialized by trying to get a connection
            from app.models.models import Destination
            try:
                # Try to access the model's db connection to see if it's properly initialized
                _ = Destination._meta.db
                logger.info(f"Using existing Tortoise connection for task {task_id}")
            except:
                # If we can't access the db, we need to initialize
                await Tortoise.init(
                    db_url=settings.DATABASE_URL,
                    modules={"models": ["app.models.models"]}
                )
                tortoise_initialized = True
                logger.info(f"Tortoise initialized for task {task_id}")
        except Exception as e:
            # Fallback: always try to initialize
            try:
                await Tortoise.init(
                    db_url=settings.DATABASE_URL,
                    modules={"models": ["app.models.models"]}
                )
                tortoise_initialized = True
                logger.info(f"Tortoise initialized (fallback) for task {task_id}")
            except Exception as init_error:
                logger.error(f"Failed to initialize Tortoise: {init_error}")
                raise
        
        await task_instance.update_task_status(task_id, TaskStatus.STARTED, task_type="hotel_tracking")
        
        # Import here to avoid circular imports
        from app.models.models import Destination
        
        # Get destination
        destination = await Destination.get_or_none(
            id=destination_id,
            tracking=True,
            is_active=True
        ).prefetch_related('country')
        
        if not destination:
            raise ValueError(f"Destination with ID {destination_id} not found or not trackable")
        
        await task_instance.update_task_status(
            task_id,
            TaskStatus.STARTED,
            task_type="hotel_tracking",
            progress_current=20,
            progress_message=f"Processing destination: {destination.name}"
        )
        
        # Initialize hotel tracking service
        async with HotelTrackingService() as tracking_service:
            # Process the destination
            tracking_result = await tracking_service.process_destination_tracking(destination)
            
            await task_instance.update_task_status(
                task_id,
                TaskStatus.STARTED,
                progress_current=80,
                progress_message=f"Completed {destination.name}: {tracking_result['hotels_discovered']} hotels"
            )
        
        # Prepare result
        result = {
            "success": tracking_result['success'],
            "task_type": "single_destination_tracking",
            "destination_id": destination_id,
            "destination_name": tracking_result['destination_name'],
            "tracking_days": tracking_result['tracking_days'],
            "hotels_discovered": tracking_result['hotels_discovered'],
            "price_records_created": tracking_result['price_records_created'],
            "completed_at": datetime.utcnow().isoformat()
        }
        
        await task_instance.update_task_status(task_id, TaskStatus.SUCCESS, task_type="hotel_tracking", result=result)
        
        logger.info(
            f"Destination tracking completed for {destination.name}: "
            f"{result['hotels_discovered']} hotels, "
            f"{result['price_records_created']} price records"
        )
        
        return result
        
    except Exception as e:
        error_msg = f"Destination tracking failed for ID {destination_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        await task_instance.update_task_status(
            task_id, 
            TaskStatus.FAILURE, 
            task_type="hotel_tracking",
            error_message=error_msg
        )
        raise
    finally:
        # Only close connections if this task initialized them
        if tortoise_initialized:
            try:
                await Tortoise.close_connections()
                logger.info(f"Closed Tortoise connections for task {task_id}")
            except Exception as cleanup_error:
                logger.warning(f"Error closing Tortoise connections for task {task_id}: {cleanup_error}")


@celery_app.task(bind=True, base=BaseTask)
def get_tracking_summary(self) -> Dict[str, Any]:
    """
    Get current tracking configuration and statistics
    """
    return asyncio.run(_get_tracking_summary_async(self))


async def _get_tracking_summary_async(task_instance) -> Dict[str, Any]:
    """Async implementation of tracking summary retrieval"""
    task_id = task_instance.request.id
    tortoise_initialized = False
    
    try:
        # Initialize Tortoise for this task if not already initialized
        from app.core.config import settings
        from tortoise import connections
        
        try:
            # Check if Tortoise is properly initialized by trying to get a connection
            from app.models.models import Destination
            try:
                # Try to access the model's db connection to see if it's properly initialized
                _ = Destination._meta.db
                logger.info(f"Using existing Tortoise connection for summary task {task_id}")
            except:
                # If we can't access the db, we need to initialize
                await Tortoise.init(
                    db_url=settings.DATABASE_URL,
                    modules={"models": ["app.models.models"]}
                )
                tortoise_initialized = True
                logger.info(f"Tortoise initialized for summary task {task_id}")
        except Exception as e:
            # Fallback: always try to initialize
            try:
                await Tortoise.init(
                    db_url=settings.DATABASE_URL,
                    modules={"models": ["app.models.models"]}
                )
                tortoise_initialized = True
                logger.info(f"Tortoise initialized (fallback) for summary task {task_id}")
            except Exception as init_error:
                logger.error(f"Failed to initialize Tortoise: {init_error}")
                raise
        
        await task_instance.update_task_status(task_id, TaskStatus.STARTED, task_type="hotel_tracking")
        
        # Initialize hotel tracking service
        async with HotelTrackingService() as tracking_service:
            # Get tracking summary
            summary = await tracking_service.get_tracking_summary()
        
        result = {
            "success": True,
            "task_type": "tracking_summary",
            "summary": summary,
            "retrieved_at": datetime.utcnow().isoformat()
        }
        
        await task_instance.update_task_status(task_id, TaskStatus.SUCCESS, task_type="hotel_tracking", result=result)
        
        return result
        
    except Exception as e:
        error_msg = f"Failed to get tracking summary: {str(e)}"
        logger.error(error_msg, exc_info=True)
        await task_instance.update_task_status(
            task_id, 
            TaskStatus.FAILURE, 
            task_type="hotel_tracking",
            error_message=error_msg
        )
        raise
    finally:
        # Only close connections if this task initialized them
        if tortoise_initialized:
            try:
                await Tortoise.close_connections()
                logger.info(f"Closed Tortoise connections for summary task {task_id}")
            except Exception as cleanup_error:
                logger.warning(f"Error closing Tortoise connections for summary task {task_id}: {cleanup_error}")


# Convenience function to trigger hotel tracking manually
async def trigger_hotel_tracking_now() -> str:
    """
    Trigger hotel tracking scan immediately
    
    Returns:
        Task ID for monitoring progress
    """
    task = scan_destinations_for_tracking.delay()
    logger.info(f"Triggered hotel tracking scan with task ID: {task.id}")
    return task.id


# Convenience function to trigger single destination tracking
async def trigger_destination_tracking_now(destination_id: int) -> str:
    """
    Trigger hotel tracking for a specific destination immediately
    
    Args:
        destination_id: ID of destination to track
        
    Returns:
        Task ID for monitoring progress
    """
    task = process_destination_hotels.delay(destination_id)
    logger.info(f"Triggered destination tracking for ID {destination_id} with task ID: {task.id}")
    return task.id


# Convenience function to get tracking summary
async def get_tracking_summary_now() -> str:
    """
    Get tracking configuration and statistics
    
    Returns:
        Task ID for monitoring progress
    """
    task = get_tracking_summary.delay()
    logger.info(f"Triggered tracking summary with task ID: {task.id}")
    return task.id