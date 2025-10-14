"""
Celery application configuration for distributed task queue
"""
from celery import Celery
from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "hotel_scraper",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.scraping_tasks"]
)

# Configure Celery
celery_app.conf.update(
    # Task execution settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Task acknowledgment
    task_acks_late=True,  # Acknowledge after task completes (safer)
    task_reject_on_worker_lost=True,  # Requeue if worker crashes

    # Task time limits
    task_time_limit=600,  # 10 minutes hard limit
    task_soft_time_limit=540,  # 9 minutes soft limit (raises exception)

    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    result_persistent=True,  # Persist results across restarts

    # Worker settings
    worker_prefetch_multiplier=1,  # Don't prefetch tasks (better for long tasks)
    worker_max_tasks_per_child=100,  # Restart worker after 100 tasks (prevent memory leaks)

    # Retry settings
    task_autoretry_for=(Exception,),  # Auto-retry on any exception
    task_retry_kwargs={"max_retries": 3, "countdown": 60},  # Wait 60s before retry
    task_retry_backoff=True,  # Exponential backoff
    task_retry_backoff_max=600,  # Max backoff of 10 minutes
    task_retry_jitter=True,  # Add randomness to backoff

    # Rate limiting
    task_default_rate_limit="10/m",  # 10 tasks per minute default

    # Queue routing
    task_routes={
        "app.workers.scraping_tasks.scrape_hotel_prices_task": {"queue": "scraping"},
        "app.workers.scraping_tasks.scrape_multiple_trackers_task": {"queue": "scraping"},
        "app.workers.scraping_tasks.process_scraping_results_task": {"queue": "processing"},
    },

    # Priority queues
    task_queue_max_priority=10,
    task_default_priority=5,
)

if __name__ == "__main__":
    celery_app.start()
