"""
Celery application configuration for background tasks
"""

from celery import Celery
from app.core.config import settings

# Create Celery instance
celery_app = Celery(
    "often-hotels",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.email_tasks",
        "app.tasks.hotel_tasks", 
        "app.tasks.hotel_tracking_tasks",
        "app.tasks.notification_tasks",
        "app.tasks.cleanup_tasks"
    ]
)

# Celery Configuration
celery_app.conf.update(
    # Task Settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Result Backend Settings
    result_expires=3600,  # 1 hour
    result_backend_transport_options={
        "master_name": "mymaster"
    },
    
    # Task Execution Settings
    task_always_eager=False,  # Set to True for testing
    task_eager_propagates=True,
    task_ignore_result=False,
    task_store_eager_result=True,
    
    # Worker Settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    
    # Task Routing - temporarily disabled to use default queue
    # task_routes={
    #     "app.tasks.email_tasks.*": {"queue": "email"},
    #     "app.tasks.hotel_tasks.*": {"queue": "hotel_processing"},
    #     "app.tasks.hotel_tracking_tasks.*": {"queue": "hotel_tracking"},
    #     "app.tasks.notification_tasks.*": {"queue": "notifications"},
    #     "app.tasks.cleanup_tasks.*": {"queue": "maintenance"},
    # },
    
    # Beat Schedule (for periodic tasks)
    beat_schedule={
        "cleanup-expired-tokens": {
            "task": "app.tasks.cleanup_tasks.cleanup_expired_refresh_tokens",
            "schedule": 60.0 * 60.0,  # Every hour
        },
        "daily-hotel-sync": {
            "task": "app.tasks.hotel_tasks.sync_hotel_data",
            "schedule": 60.0 * 60.0 * 24.0,  # Every 24 hours
        },
    },
)

# Health check task
@celery_app.task(bind=True)
def health_check(self):
    """Simple health check task"""
    return {"status": "healthy", "task_id": self.request.id}