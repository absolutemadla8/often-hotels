"""
Monitoring endpoints for Prometheus metrics and health checks
"""
from fastapi import APIRouter, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from typing import Dict, Any
from datetime import datetime

from app.schemas.response import ResponseBase
from app.models.models import Tracker, TrackerResult, UniversalPriceHistory, Hotel
from app.monitoring.metrics import metrics

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])


@router.get("/metrics")
async def prometheus_metrics():
    """
    Prometheus metrics endpoint

    Exposes all application metrics in Prometheus format.
    Configure Prometheus to scrape this endpoint.

    Example prometheus.yml:
    ```yaml
    scrape_configs:
      - job_name: 'often-hotels'
        static_configs:
          - targets: ['localhost:8000']
        metrics_path: '/api/v1/monitoring/metrics'
    ```
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


@router.get("/health", response_model=ResponseBase[Dict[str, Any]])
async def health_check():
    """
    Health check endpoint

    Returns:
    - status: healthy/unhealthy
    - timestamp: current UTC time
    - database: connection status
    - redis: connection status (if configured)
    - celery: worker status
    """
    from app.core.database import database

    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0",
        "service": "brightdata_scraper"
    }

    # Check database connection
    try:
        # Simple query to test connection
        await Tracker.all().count()
        health_status["database"] = "connected"
    except Exception as e:
        health_status["database"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"

    # Check Celery workers
    try:
        from app.workers.celery_app import celery_app
        inspect = celery_app.control.inspect()
        stats = inspect.stats()

        if stats:
            health_status["celery"] = {
                "workers": len(stats),
                "status": "running"
            }
        else:
            health_status["celery"] = {
                "workers": 0,
                "status": "no workers available"
            }
            health_status["status"] = "degraded"

    except Exception as e:
        health_status["celery"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    # Check Redis (optional)
    try:
        from app.core.config import settings
        import aioredis

        redis = await aioredis.create_redis_pool(settings.REDIS_URL)
        await redis.ping()
        redis.close()
        await redis.wait_closed()
        health_status["redis"] = "connected"
    except:
        health_status["redis"] = "not configured"

    return ResponseBase(
        success=health_status["status"] in ["healthy", "degraded"],
        message=f"System status: {health_status['status']}",
        data=health_status
    )


@router.get("/stats/database", response_model=ResponseBase[Dict[str, Any]])
async def database_stats():
    """
    Database statistics

    Returns counts of key entities and data quality metrics.
    """
    try:
        stats = {
            "trackers": {
                "total": await Tracker.all().count(),
                "active": await Tracker.filter(status="active").count(),
                "paused": await Tracker.filter(status="paused").count(),
                "stopped": await Tracker.filter(status="stopped").count(),
                "error": await Tracker.filter(status="error").count(),
                "completed": await Tracker.filter(status="completed").count()
            },
            "tracker_results": {
                "total": await TrackerResult.all().count(),
                "successful": await TrackerResult.filter(success=True).count(),
                "failed": await TrackerResult.filter(success=False).count()
            },
            "price_history": {
                "total_records": await UniversalPriceHistory.all().count(),
                "brightdata_records": await UniversalPriceHistory.filter(data_source="brightdata").count(),
                "serpapi_records": await UniversalPriceHistory.filter(data_source="serpapi").count(),
                "available_prices": await UniversalPriceHistory.filter(is_available=True).count()
            },
            "hotels": {
                "total": await Hotel.all().count()
            }
        }

        return ResponseBase(
            success=True,
            message="Database statistics retrieved",
            data=stats
        )

    except Exception as e:
        return ResponseBase(
            success=False,
            message=f"Failed to retrieve database stats: {str(e)}",
            data={}
        )


@router.get("/stats/scraping", response_model=ResponseBase[Dict[str, Any]])
async def scraping_stats():
    """
    Scraping statistics

    Returns recent scraping activity and performance metrics.
    """
    try:
        from datetime import timedelta

        # Get recent tracker results (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_results = await TrackerResult.filter(
            execution_start__gte=yesterday
        ).all()

        total_runs = len(recent_results)
        successful_runs = sum(1 for r in recent_results if r.success)
        failed_runs = total_runs - successful_runs

        # Calculate averages
        execution_times = [r.execution_time_seconds for r in recent_results if r.execution_time_seconds]
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0

        total_hotels = sum(r.items_found for r in recent_results if r.items_found)

        stats = {
            "last_24_hours": {
                "total_runs": total_runs,
                "successful_runs": successful_runs,
                "failed_runs": failed_runs,
                "success_rate": successful_runs / total_runs if total_runs > 0 else 0,
                "avg_execution_time_seconds": round(avg_execution_time, 2),
                "total_hotels_found": total_hotels
            },
            "timestamp": datetime.utcnow().isoformat()
        }

        return ResponseBase(
            success=True,
            message="Scraping statistics retrieved",
            data=stats
        )

    except Exception as e:
        return ResponseBase(
            success=False,
            message=f"Failed to retrieve scraping stats: {str(e)}",
            data={}
        )


@router.get("/ready")
async def readiness_check():
    """
    Kubernetes readiness probe

    Returns 200 if service is ready to accept traffic.
    """
    try:
        # Check if database is accessible
        await Tracker.all().count()
        return {"ready": True}
    except:
        return Response(status_code=503, content={"ready": False})


@router.get("/live")
async def liveness_check():
    """
    Kubernetes liveness probe

    Returns 200 if service is alive.
    """
    return {"alive": True}
