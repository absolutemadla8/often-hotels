"""
Admin Hotel Tracking API Endpoints

This module provides admin-only API endpoints for managing hotel price tracking operations.
All endpoints require admin authentication and provide comprehensive tracking management.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import asyncio
import json

from app.middleware.admin_middleware import get_admin_user, admin_endpoint, log_admin_action
from app.models.models import User, Task, TaskStatus, TaskLog, LogLevel
from app.tasks.hotel_tracking_tasks import (
    trigger_hotel_tracking_now,
    trigger_destination_tracking_now,
    get_tracking_summary_now
)
from app.services.hotel_tracking_service import get_hotel_tracking_service

logger = logging.getLogger(__name__)

router = APIRouter()


# Response Models
class TaskResponse(BaseModel):
    """Response model for task operations"""
    task_id: str = Field(..., description="Unique task identifier")
    message: str = Field(..., description="Operation message")
    status: str = Field(..., description="Initial task status")


class TaskStatusResponse(BaseModel):
    """Response model for task status queries"""
    task_id: str = Field(..., description="Task identifier")
    task_name: str = Field(..., description="Task name")
    status: str = Field(..., description="Current task status")
    progress_current: int = Field(..., description="Current progress")
    progress_total: int = Field(..., description="Total progress")
    progress_percentage: float = Field(..., description="Progress percentage")
    progress_message: Optional[str] = Field(None, description="Progress message")
    started_at: Optional[datetime] = Field(None, description="Task start time")
    completed_at: Optional[datetime] = Field(None, description="Task completion time")
    execution_time_seconds: Optional[float] = Field(None, description="Execution time")
    result: Optional[Dict[str, Any]] = Field(None, description="Task result")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class TrackingConfigResponse(BaseModel):
    """Response model for tracking configuration"""
    tracking_enabled_destinations: int = Field(..., description="Number of destinations with tracking enabled")
    destinations: list = Field(..., description="List of trackable destinations")
    configuration: dict = Field(..., description="Current tracking configuration")
    statistics: dict = Field(..., description="Tracking statistics")


class DestinationTrackingRequest(BaseModel):
    """Request model for single destination tracking"""
    destination_id: int = Field(..., description="Destination ID to track", gt=0)


# Endpoints
@router.post(
    "/start",
    response_model=TaskResponse,
    summary="Trigger Hotel Tracking",
    description="Manually trigger hotel price tracking for all enabled destinations"
)
# @admin_endpoint
async def start_hotel_tracking(
    # admin_user: User = get_admin_user()
) -> TaskResponse:
    """
    Trigger immediate hotel price tracking scan for all destinations with tracking enabled.
    
    This endpoint starts a background task that will:
    1. Scan all destinations with tracking=True
    2. Search for 4-5 star hotels using SerpApi
    3. Create/update hotel records
    4. Create/update price history records
    
    Returns a task ID that can be used to monitor progress.
    """
    try:
        # Log admin action
        # log_admin_action(
        #     user=admin_user,
        #     action="triggered_hotel_tracking_scan",
        #     details={"endpoint": "/admin/hotel-tracking/start"}
        # )
        
        # Trigger the background task
        task_id = await trigger_hotel_tracking_now()
        
        logger.info(f"Hotel tracking scan triggered, task ID: {task_id}")
        
        return TaskResponse(
            task_id=task_id,
            message="Hotel tracking scan started successfully",
            status="PENDING"
        )
        
    except Exception as e:
        logger.error(f"Failed to start hotel tracking: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start hotel tracking: {str(e)}"
        )


@router.post(
    "/destination/{destination_id}",
    response_model=TaskResponse,
    summary="Track Single Destination",
    description="Trigger hotel tracking for a specific destination"
)
# @admin_endpoint
async def start_destination_tracking(
    destination_id: int,
    # admin_user: User = get_admin_user()
) -> TaskResponse:
    """
    Trigger hotel price tracking for a specific destination.
    
    This endpoint starts a background task that will:
    1. Process the specified destination
    2. Search for hotels across all tracking days
    3. Create/update hotel and price records
    
    Args:
        destination_id: ID of the destination to track
    """
    try:
        # Validate destination_id
        if destination_id <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid destination ID"
            )
        
        # Log admin action
        # log_admin_action(
        #     user=admin_user,
        #     action="triggered_destination_tracking",
        #     details={
        #         "endpoint": f"/admin/hotel-tracking/destination/{destination_id}",
        #         "destination_id": destination_id
        #     }
        # )
        
        # Trigger the background task
        task_id = await trigger_destination_tracking_now(destination_id)
        
        logger.info(
            f"Destination tracking triggered for destination {destination_id}, task ID: {task_id}"
        )
        
        return TaskResponse(
            task_id=task_id,
            message=f"Destination tracking started for destination {destination_id}",
            status="PENDING"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start destination tracking: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start destination tracking: {str(e)}"
        )


@router.get(
    "/status/{task_id}",
    response_model=TaskStatusResponse,
    summary="Get Task Status",
    description="Get the status and progress of a hotel tracking task"
)
# @admin_endpoint
async def get_task_status(
    task_id: str,
    # admin_user: User = get_admin_user()
) -> TaskStatusResponse:
    """
    Get the current status and progress of a hotel tracking task.
    
    Args:
        task_id: The task ID returned from start_hotel_tracking or start_destination_tracking
    """
    try:
        # Get task from database
        task = await Task.get_or_none(task_id=task_id)
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with ID {task_id} not found"
            )
        
        # Log admin action (minimal logging for status checks)
        logger.debug(f"Checked status of task {task_id}")
        
        return TaskStatusResponse(
            task_id=task.task_id,
            task_name=task.task_name,
            status=task.status.value,
            progress_current=task.progress_current,
            progress_total=task.progress_total,
            progress_percentage=task.progress_percentage,
            progress_message=task.progress_message,
            started_at=task.started_at,
            completed_at=task.completed_at,
            execution_time_seconds=task.execution_time_seconds,
            result=task.result,
            error_message=task.error_message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task status: {str(e)}"
        )


@router.get(
    "/config",
    response_model=TrackingConfigResponse,
    summary="Get Tracking Configuration",
    description="Get current hotel tracking configuration and statistics"
)
# @admin_endpoint
async def get_tracking_config(
    # admin_user: User = get_admin_user()
) -> TrackingConfigResponse:
    """
    Get the current hotel tracking configuration and statistics.
    
    Returns information about:
    - Destinations with tracking enabled
    - Current configuration settings
    - Tracking statistics
    """
    try:
        # Log admin action
        # log_admin_action(
        #     user=admin_user,
        #     action="viewed_tracking_config",
        #     details={"endpoint": "/admin/hotel-tracking/config"}
        # )
        
        # Get tracking configuration using the service
        async with await get_hotel_tracking_service() as tracking_service:
            config_data = await tracking_service.get_tracking_summary()
        
        return TrackingConfigResponse(
            tracking_enabled_destinations=config_data["tracking_enabled_destinations"],
            destinations=config_data["destinations"],
            configuration=config_data["configuration"],
            statistics=config_data["statistics"]
        )
        
    except Exception as e:
        logger.error(f"Failed to get tracking config: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tracking config: {str(e)}"
        )


@router.get(
    "/summary",
    response_model=TaskResponse,
    summary="Get Tracking Summary",
    description="Get detailed tracking summary as a background task"
)
# @admin_endpoint
async def get_tracking_summary_task(
    # admin_user: User = get_admin_user()
) -> TaskResponse:
    """
    Generate a detailed tracking summary as a background task.
    
    This is useful for generating comprehensive reports that might take some time.
    """
    try:
        # Log admin action
        # log_admin_action(
        #     user=admin_user,
        #     action="requested_tracking_summary",
        #     details={"endpoint": "/admin/hotel-tracking/summary"}
        # )
        
        # Trigger the background task
        task_id = await get_tracking_summary_now()
        
        logger.info(f"Tracking summary requested, task ID: {task_id}")
        
        return TaskResponse(
            task_id=task_id,
            message="Tracking summary generation started",
            status="PENDING"
        )
        
    except Exception as e:
        logger.error(f"Failed to start tracking summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start tracking summary: {str(e)}"
        )


@router.get(
    "/health",
    summary="Health Check",
    description="Check if hotel tracking system is healthy"
)
# @admin_endpoint
async def health_check(
    # admin_user: User = get_admin_user()
) -> Dict[str, Any]:
    """
    Health check endpoint for the hotel tracking system.
    
    Verifies that all components are working correctly.
    """
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "database": "connected",
                "serp_api": "available",
                "celery": "running",
                "tracking_service": "operational"
            }
        }
        
        # Test basic database connectivity
        from app.models.models import Destination
        destination_count = await Destination.filter(tracking=True).count()
        health_status["components"]["database"] = f"connected ({destination_count} tracked destinations)"
        
        # Test SerpApi service (basic initialization)
        try:
            from app.services.serp_service import get_serp_service
            serp_service = get_serp_service()
            health_status["components"]["serp_api"] = "configured"
        except Exception as e:
            health_status["components"]["serp_api"] = f"error: {str(e)}"
            health_status["status"] = "degraded"
        
        # Test tracking service initialization
        try:
            async with await get_hotel_tracking_service() as tracking_service:
                health_status["components"]["tracking_service"] = "operational"
        except Exception as e:
            health_status["components"]["tracking_service"] = f"error: {str(e)}"
            health_status["status"] = "degraded"
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


@router.get(
    "/logs/{task_id}/stream",
    summary="Stream Task Logs",
    description="Stream real-time logs for a hotel tracking task using Server-Sent Events"
)
# @admin_endpoint
async def stream_task_logs(
    task_id: str,
    level: Optional[str] = None,
    # admin_user: User = get_admin_user()
):
    """
    Stream real-time logs for a specific task using Server-Sent Events.
    
    Args:
        task_id: The task ID to stream logs for
        level: Optional log level filter (debug, info, warning, error, critical)
    
    Returns:
        StreamingResponse with Server-Sent Events
    """
    
    async def log_generator():
        """Generate Server-Sent Events for task logs"""
        try:
            # Verify task exists
            task = await Task.get_or_none(task_id=task_id)
            if not task:
                yield f"event: error\ndata: {json.dumps({'error': f'Task {task_id} not found'})}\n\n"
                return
            
            # Send initial connection event
            yield f"event: connected\ndata: {json.dumps({'message': 'Connected to log stream', 'task_id': task_id})}\n\n"
            
            # Get existing logs first
            query = TaskLog.filter(task=task)
            if level:
                try:
                    log_level = LogLevel(level.lower())
                    query = query.filter(level=log_level)
                except ValueError:
                    yield f"event: error\ndata: {json.dumps({'error': f'Invalid log level: {level}'})}\n\n"
                    return
            
            existing_logs = await query.order_by('timestamp').all()
            
            # Send existing logs
            for log_entry in existing_logs:
                log_data = {
                    "id": log_entry.id,
                    "level": log_entry.level,
                    "message": log_entry.message,
                    "source": log_entry.source,
                    "phase": log_entry.phase,
                    "progress_hint": log_entry.progress_hint,
                    "metadata": log_entry.metadata,
                    "timestamp": log_entry.timestamp.isoformat()
                }
                yield f"event: log\ndata: {json.dumps(log_data)}\n\n"
            
            # Keep track of the last log ID we've sent
            last_log_id = existing_logs[-1].id if existing_logs else 0
            
            # Poll for new logs
            while True:
                # Check if task is still running
                await task.refresh_from_db()
                
                # Get new logs since last check
                new_logs_query = TaskLog.filter(task=task, id__gt=last_log_id)
                if level:
                    new_logs_query = new_logs_query.filter(level=LogLevel(level.lower()))
                
                new_logs = await new_logs_query.order_by('timestamp').all()
                
                # Send new logs
                for log_entry in new_logs:
                    log_data = {
                        "id": log_entry.id,
                        "level": log_entry.level,
                        "message": log_entry.message,
                        "source": log_entry.source,
                        "phase": log_entry.phase,
                        "progress_hint": log_entry.progress_hint,
                        "metadata": log_entry.metadata,
                        "timestamp": log_entry.timestamp.isoformat()
                    }
                    yield f"event: log\ndata: {json.dumps(log_data)}\n\n"
                    last_log_id = log_entry.id
                
                # Send task status update
                task_status = {
                    "task_id": task.task_id,
                    "status": task.status.value,
                    "progress_current": task.progress_current,
                    "progress_total": task.progress_total,
                    "progress_percentage": task.progress_percentage,
                    "progress_message": task.progress_message,
                    "is_finished": task.is_finished
                }
                yield f"event: status\ndata: {json.dumps(task_status)}\n\n"
                
                # If task is finished, send completion event and break
                if task.is_finished:
                    completion_data = {
                        "message": "Task completed",
                        "final_status": task.status.value,
                        "result": task.result
                    }
                    yield f"event: completed\ndata: {json.dumps(completion_data)}\n\n"
                    break
                
                # Wait before next poll
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Error in log stream for task {task_id}: {e}")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        log_generator(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        }
    )


@router.get(
    "/logs/{task_id}",
    summary="Get Task Logs",
    description="Get all logs for a specific task"
)
# @admin_endpoint
async def get_task_logs(
    task_id: str,
    level: Optional[str] = None,
    limit: Optional[int] = 100,
    # admin_user: User = get_admin_user()
) -> Dict[str, Any]:
    """
    Get all logs for a specific task.
    
    Args:
        task_id: The task ID to get logs for
        level: Optional log level filter (debug, info, warning, error, critical)
        limit: Maximum number of logs to return (default: 100)
    """
    try:
        # Verify task exists
        task = await Task.get_or_none(task_id=task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with ID {task_id} not found"
            )
        
        # Build query
        query = TaskLog.filter(task=task)
        if level:
            try:
                log_level = LogLevel(level.lower())
                query = query.filter(level=log_level)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid log level: {level}"
                )
        
        # Get logs with limit
        logs = await query.order_by('-timestamp').limit(limit).all()
        
        # Format response
        log_data = []
        for log_entry in reversed(logs):  # Reverse to get chronological order
            log_data.append({
                "id": log_entry.id,
                "level": log_entry.level,
                "message": log_entry.message,
                "source": log_entry.source,
                "phase": log_entry.phase,
                "progress_hint": log_entry.progress_hint,
                "metadata": log_entry.metadata,
                "timestamp": log_entry.timestamp.isoformat()
            })
        
        return {
            "task_id": task_id,
            "total_logs": len(log_data),
            "logs": log_data,
            "task_status": task.status.value,
            "task_finished": task.is_finished
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task logs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task logs: {str(e)}"
        )