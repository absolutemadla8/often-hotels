"""
Task management endpoints
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.api.tortoise_deps import get_current_active_user
from app.core.celery_app import celery_app
from app.models.models import User, Task, TaskStatus
from app.tasks import (
    send_welcome_email,
    send_price_alert_email,
    sync_hotel_data,
    process_hotel_search,
    send_push_notification,
    cleanup_expired_refresh_tokens,
    cleanup_old_tasks
)

logger = logging.getLogger(__name__)
router = APIRouter()


# Pydantic models for request/response
class TaskResponse(BaseModel):
    id: int
    task_id: str
    task_name: str
    task_type: str
    status: TaskStatus
    progress_percentage: float
    progress_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_time_seconds: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class EmailTaskRequest(BaseModel):
    user_id: int
    email_type: str  # "welcome" or "price_alert"
    data: Optional[Dict[str, Any]] = None


class HotelSearchRequest(BaseModel):
    destination: str
    check_in: str
    check_out: str
    guests: int = 2
    filters: Optional[Dict[str, Any]] = None


class NotificationRequest(BaseModel):
    user_id: int
    title: str
    message: str
    notification_type: str  # "push" or "sms"
    data: Optional[Dict[str, Any]] = None


@router.get("/", response_model=List[TaskResponse])
async def get_tasks(
    status: Optional[TaskStatus] = Query(None, description="Filter by task status"),
    task_type: Optional[str] = Query(None, description="Filter by task type"),
    limit: int = Query(50, ge=1, le=100, description="Number of tasks to return"),
    offset: int = Query(0, ge=0, description="Number of tasks to skip"),
    current_user: User = Depends(get_current_active_user)
):
    """Get list of tasks for the current user"""
    try:
        query = Task.filter(user=current_user)
        
        if status:
            query = query.filter(status=status)
        if task_type:
            query = query.filter(task_type=task_type)
            
        tasks = await query.order_by("-created_at").offset(offset).limit(limit).all()
        
        # Convert to response format
        task_responses = []
        for task in tasks:
            task_responses.append(TaskResponse(
                id=task.id,
                task_id=task.task_id,
                task_name=task.task_name,
                task_type=task.task_type,
                status=task.status,
                progress_percentage=task.progress_percentage,
                progress_message=task.progress_message,
                started_at=task.started_at,
                completed_at=task.completed_at,
                execution_time_seconds=task.execution_time_seconds,
                result=task.result,
                error_message=task.error_message,
                created_at=task.created_at
            ))
            
        return task_responses
        
    except Exception as e:
        logger.error(f"Error getting tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get specific task by ID"""
    try:
        task = await Task.get_or_none(task_id=task_id, user=current_user)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
            
        return TaskResponse(
            id=task.id,
            task_id=task.task_id,
            task_name=task.task_name,
            task_type=task.task_type,
            status=task.status,
            progress_percentage=task.progress_percentage,
            progress_message=task.progress_message,
            started_at=task.started_at,
            completed_at=task.completed_at,
            execution_time_seconds=task.execution_time_seconds,
            result=task.result,
            error_message=task.error_message,
            created_at=task.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/email", response_model=Dict[str, str])
async def create_email_task(
    request: EmailTaskRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Create email task (welcome email or price alert)"""
    try:
        if request.email_type == "welcome":
            celery_task = send_welcome_email.delay(request.user_id)
        elif request.email_type == "price_alert":
            celery_task = send_price_alert_email.delay(
                request.user_id, 
                request.data or {}
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid email type")
        
        # Create task record
        await Task.create(
            task_id=celery_task.id,
            task_name=f"send_{request.email_type}_email",
            task_type="email",
            user=current_user,
            task_args=[request.user_id],
            task_kwargs={"data": request.data} if request.data else None,
            queue_name="email"
        )
        
        return {
            "task_id": celery_task.id,
            "status": "queued",
            "message": f"{request.email_type.title()} email task created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating email task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/hotel-search", response_model=Dict[str, str])
async def create_hotel_search_task(
    request: HotelSearchRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Create background hotel search task"""
    try:
        search_criteria = {
            "destination": request.destination,
            "check_in": request.check_in,
            "check_out": request.check_out,
            "guests": request.guests,
            "filters": request.filters or {}
        }
        
        celery_task = process_hotel_search.delay(current_user.id, search_criteria)
        
        # Create task record
        await Task.create(
            task_id=celery_task.id,
            task_name="process_hotel_search",
            task_type="hotel_processing",
            user=current_user,
            task_args=[current_user.id],
            task_kwargs={"search_criteria": search_criteria},
            queue_name="hotel_processing"
        )
        
        return {
            "task_id": celery_task.id,
            "status": "queued",
            "message": "Hotel search task created successfully"
        }
        
    except Exception as e:
        logger.error(f"Error creating hotel search task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notification", response_model=Dict[str, str])
async def create_notification_task(
    request: NotificationRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Create notification task (push or SMS)"""
    try:
        if request.notification_type == "push":
            celery_task = send_push_notification.delay(
                request.user_id,
                request.title,
                request.message,
                request.data
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid notification type")
        
        # Create task record
        await Task.create(
            task_id=celery_task.id,
            task_name=f"send_{request.notification_type}_notification",
            task_type="notifications",
            user=current_user,
            task_args=[request.user_id, request.title, request.message],
            task_kwargs={"data": request.data} if request.data else None,
            queue_name="notifications"
        )
        
        return {
            "task_id": celery_task.id,
            "status": "queued",
            "message": f"{request.notification_type.upper()} notification task created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating notification task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-hotels", response_model=Dict[str, str])
async def create_hotel_sync_task(
    current_user: User = Depends(get_current_active_user)
):
    """Create hotel data sync task (admin only)"""
    try:
        # Check if user is admin
        if not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        celery_task = sync_hotel_data.delay()
        
        # Create task record
        await Task.create(
            task_id=celery_task.id,
            task_name="sync_hotel_data",
            task_type="hotel_sync",
            user=current_user,
            queue_name="hotel_processing"
        )
        
        return {
            "task_id": celery_task.id,
            "status": "queued",
            "message": "Hotel sync task created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating hotel sync task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{task_id}")
async def cancel_task(
    task_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Cancel a running task"""
    try:
        # Check if task belongs to user
        task = await Task.get_or_none(task_id=task_id, user=current_user)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Check if task can be cancelled
        if task.is_finished:
            raise HTTPException(status_code=400, detail="Task is already finished")
        
        # Revoke the Celery task
        celery_app.control.revoke(task_id, terminate=True)
        
        # Update task status
        task.status = TaskStatus.REVOKED
        task.completed_at = datetime.utcnow()
        await task.save()
        
        return {"message": "Task cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/summary", response_model=Dict[str, Any])
async def get_task_stats(
    current_user: User = Depends(get_current_active_user)
):
    """Get task statistics for the current user"""
    try:
        # Get task counts by status
        total_tasks = await Task.filter(user=current_user).count()
        pending_tasks = await Task.filter(user=current_user, status=TaskStatus.PENDING).count()
        running_tasks = await Task.filter(user=current_user, status=TaskStatus.STARTED).count()
        completed_tasks = await Task.filter(user=current_user, status=TaskStatus.SUCCESS).count()
        failed_tasks = await Task.filter(user=current_user, status=TaskStatus.FAILURE).count()
        
        # Get recent tasks
        recent_tasks = await Task.filter(user=current_user).order_by("-created_at").limit(5).all()
        
        return {
            "total_tasks": total_tasks,
            "pending_tasks": pending_tasks,
            "running_tasks": running_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "success_rate": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
            "recent_tasks": [
                {
                    "task_id": task.task_id,
                    "task_name": task.task_name,
                    "status": task.status,
                    "created_at": task.created_at
                }
                for task in recent_tasks
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting task stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))