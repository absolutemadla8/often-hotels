"""
API endpoints for managing Celery jobs and monitoring scraping tasks
"""
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel, Field
from celery.result import AsyncResult

from app.models.models import Tracker, TrackerResult
from app.schemas.response import ResponseBase
from app.services.tracking_service import get_serpapi_tracking_service
from app.workers.celery_app import celery_app

router = APIRouter(prefix="/jobs", tags=["Jobs & Monitoring"])


# ============================================================================
# Request/Response Models
# ============================================================================

class JobSubmitRequest(BaseModel):
    """Request to submit a scraping job"""
    tracker_id: int = Field(..., description="Tracker ID to execute")
    priority: int = Field(5, ge=0, le=10, description="Job priority (0-10, higher = more important)")


class BatchJobSubmitRequest(BaseModel):
    """Request to submit multiple scraping jobs"""
    tracker_ids: List[int] = Field(..., min_items=1, description="List of tracker IDs")
    priority: int = Field(5, ge=0, le=10, description="Job priority")


class JobStatusResponse(BaseModel):
    """Job status response"""
    task_id: str
    state: str  # PENDING, STARTED, SUCCESS, FAILURE, RETRY
    info: Dict[str, Any] = Field(default_factory=dict)
    ready: bool
    successful: Optional[bool] = None
    failed: Optional[bool] = None
    result: Optional[Dict[str, Any]] = None


class JobSubmitResponse(BaseModel):
    """Job submission response"""
    task_id: str
    tracker_id: Optional[int] = None
    tracker_ids: Optional[List[int]] = None
    status: str
    message: str


class TrackerStatsResponse(BaseModel):
    """Tracker statistics"""
    tracker_id: int
    name: str
    status: str
    total_runs: int
    successful_runs: int
    failed_runs: int
    success_rate: float
    last_run_at: Optional[datetime] = None
    avg_execution_time: Optional[float] = None
    total_hotels_found: int


class SystemMetricsResponse(BaseModel):
    """System-wide metrics"""
    scraping_service: Dict[str, Any]
    active_trackers: int
    total_jobs_pending: int
    total_jobs_running: int
    total_jobs_completed: int


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/submit", response_model=ResponseBase[JobSubmitResponse])
async def submit_scraping_job(
    request: JobSubmitRequest
):
    """
    Submit a single scraping job to Celery queue

    The job will be processed asynchronously by workers.
    Use /jobs/status/{task_id} to check progress.
    """
    try:
        # Get tracker
        tracker = await Tracker.get_or_none(id=request.tracker_id)
        if not tracker:
            raise HTTPException(status_code=404, detail=f"Tracker {request.tracker_id} not found")

        if tracker.status != "active":
            raise HTTPException(
                status_code=400,
                detail=f"Tracker {request.tracker_id} is not active (status: {tracker.status})"
            )

        # Submit job
        service = await get_serpapi_tracking_service()
        task_id = await service.submit_tracker_job(tracker, priority=request.priority)

        return ResponseBase(
            success=True,
            message=f"Scraping job submitted for tracker {request.tracker_id}",
            data=JobSubmitResponse(
                task_id=task_id,
                tracker_id=request.tracker_id,
                status="submitted",
                message=f"Job queued with priority {request.priority}"
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit job: {str(e)}")


@router.post("/submit/batch", response_model=ResponseBase[JobSubmitResponse])
async def submit_batch_scraping_jobs(
    request: BatchJobSubmitRequest
):
    """
    Submit multiple scraping jobs (processed sequentially)

    All trackers will be processed one after another to avoid rate limiting.
    """
    try:
        # Validate all trackers exist and are active
        trackers = []
        for tracker_id in request.tracker_ids:
            tracker = await Tracker.get_or_none(id=tracker_id)
            if not tracker:
                raise HTTPException(status_code=404, detail=f"Tracker {tracker_id} not found")
            if tracker.status != "active":
                raise HTTPException(
                    status_code=400,
                    detail=f"Tracker {tracker_id} is not active"
                )
            trackers.append(tracker)

        # Submit batch job
        service = await get_serpapi_tracking_service()
        task_id = await service.submit_multiple_trackers(request.tracker_ids, priority=request.priority)

        return ResponseBase(
            success=True,
            message=f"Batch job submitted for {len(request.tracker_ids)} trackers",
            data=JobSubmitResponse(
                task_id=task_id,
                tracker_ids=request.tracker_ids,
                status="submitted",
                message=f"Batch job queued with {len(request.tracker_ids)} trackers"
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit batch job: {str(e)}")


@router.get("/status/{task_id}", response_model=ResponseBase[JobStatusResponse])
async def get_job_status(task_id: str):
    """
    Get status of a Celery task

    States:
    - PENDING: Task is waiting to be executed
    - STARTED: Task has been started
    - SUCCESS: Task completed successfully
    - FAILURE: Task failed
    - RETRY: Task is being retried
    """
    try:
        result = AsyncResult(task_id, app=celery_app)

        # Build response
        status_data = JobStatusResponse(
            task_id=task_id,
            state=result.state,
            info=result.info if result.info else {},
            ready=result.ready(),
            successful=result.successful() if result.ready() else None,
            failed=result.failed() if result.ready() else None,
            result=result.result if result.successful() else None
        )

        return ResponseBase(
            success=True,
            message=f"Task status: {result.state}",
            data=status_data
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get task status: {str(e)}")


@router.post("/cancel/{task_id}", response_model=ResponseBase[Dict[str, str]])
async def cancel_job(task_id: str):
    """
    Cancel a pending or running job

    Note: May not work if task is already executing
    """
    try:
        celery_app.control.revoke(task_id, terminate=True)

        return ResponseBase(
            success=True,
            message=f"Task {task_id} cancelled",
            data={"task_id": task_id, "status": "cancelled"}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel task: {str(e)}")


@router.get("/trackers/stats", response_model=ResponseBase[List[TrackerStatsResponse]])
async def get_tracker_statistics(
    status: Optional[str] = Query(None, description="Filter by tracker status"),
    limit: int = Query(20, ge=1, le=100)
):
    """
    Get statistics for all trackers

    Returns run counts, success rates, and performance metrics.
    """
    try:
        # Build query
        query = Tracker.all()
        if status:
            query = query.filter(status=status)

        trackers = await query.limit(limit).prefetch_related("results")

        stats = []
        for tracker in trackers:
            results = await TrackerResult.filter(tracker=tracker).all()

            total_runs = len(results)
            successful_runs = sum(1 for r in results if r.success)
            failed_runs = total_runs - successful_runs
            success_rate = successful_runs / total_runs if total_runs > 0 else 0.0

            # Calculate average execution time
            execution_times = [r.execution_time_seconds for r in results if r.execution_time_seconds]
            avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else None

            # Total hotels found
            total_hotels = sum(r.items_found for r in results if r.items_found)

            stats.append(TrackerStatsResponse(
                tracker_id=tracker.id,
                name=tracker.name,
                status=tracker.status,
                total_runs=total_runs,
                successful_runs=successful_runs,
                failed_runs=failed_runs,
                success_rate=success_rate,
                last_run_at=tracker.last_run_at,
                avg_execution_time=avg_execution_time,
                total_hotels_found=total_hotels
            ))

        return ResponseBase(
            success=True,
            message=f"Retrieved statistics for {len(stats)} trackers",
            data=stats
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get tracker stats: {str(e)}")


@router.get("/metrics/system", response_model=ResponseBase[SystemMetricsResponse])
async def get_system_metrics():
    """
    Get system-wide metrics

    Includes scraping service stats, active trackers, job queue status.
    """
    try:
        # Get service metrics
        service = await get_serpapi_tracking_service()
        service_metrics = await service.get_service_metrics()

        # Get active trackers count
        active_trackers = await Tracker.filter(status="active").count()

        # Get Celery queue stats
        inspect = celery_app.control.inspect()
        active_tasks = inspect.active() or {}
        scheduled_tasks = inspect.scheduled() or {}

        total_running = sum(len(tasks) for tasks in active_tasks.values())
        total_pending = sum(len(tasks) for tasks in scheduled_tasks.values())

        # Get completed tasks count (from TrackerResult)
        total_completed = await TrackerResult.all().count()

        metrics = SystemMetricsResponse(
            scraping_service=service_metrics,
            active_trackers=active_trackers,
            total_jobs_pending=total_pending,
            total_jobs_running=total_running,
            total_jobs_completed=total_completed
        )

        return ResponseBase(
            success=True,
            message="System metrics retrieved",
            data=metrics
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system metrics: {str(e)}")


@router.get("/queue/size", response_model=ResponseBase[Dict[str, int]])
async def get_queue_sizes():
    """Get current size of Celery queues"""
    try:
        inspect = celery_app.control.inspect()

        # Get reserved (active) tasks
        active = inspect.active() or {}
        scheduled = inspect.scheduled() or {}
        reserved = inspect.reserved() or {}

        queue_sizes = {
            "active": sum(len(tasks) for tasks in active.values()),
            "scheduled": sum(len(tasks) for tasks in scheduled.values()),
            "reserved": sum(len(tasks) for tasks in reserved.values())
        }

        return ResponseBase(
            success=True,
            message="Queue sizes retrieved",
            data=queue_sizes
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get queue sizes: {str(e)}")


@router.post("/run-sync/{tracker_id}", response_model=ResponseBase[Dict[str, Any]])
async def run_tracker_sync(
    tracker_id: int,
    background_tasks: BackgroundTasks
):
    """
    Run tracker synchronously (without Celery) for testing

    Use this for manual testing or immediate execution.
    For production, use /jobs/submit instead.
    """
    try:
        tracker = await Tracker.get_or_none(id=tracker_id)
        if not tracker:
            raise HTTPException(status_code=404, detail=f"Tracker {tracker_id} not found")

        service = await get_serpapi_tracking_service()
        result = await service.run_tracker_sync(tracker)

        return ResponseBase(
            success=True,
            message=f"Tracker {tracker_id} executed synchronously",
            data={
                "tracker_id": tracker_id,
                "run_id": result.run_id,
                "success": result.success,
                "items_found": result.items_found,
                "execution_time": result.execution_time_seconds,
                "error_message": result.error_message
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run tracker: {str(e)}")
