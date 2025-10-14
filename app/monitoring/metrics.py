"""
Prometheus metrics for monitoring hotel scraping system
"""
from prometheus_client import Counter, Histogram, Gauge, Info
import time
from functools import wraps
from typing import Callable
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# Scraping Metrics
# ============================================================================

scrape_requests_total = Counter(
    'scrape_requests_total',
    'Total number of scraping requests',
    ['source', 'status', 'country']
)

scrape_duration_seconds = Histogram(
    'scrape_duration_seconds',
    'Duration of scraping requests in seconds',
    ['source', 'country'],
    buckets=(1, 5, 10, 30, 60, 120, 300, 600)
)

scrape_cost_total = Counter(
    'scrape_cost_total_usd',
    'Total scraping cost in USD',
    ['source', 'country']
)

scrape_hotels_found = Histogram(
    'scrape_hotels_found',
    'Number of hotels found per scrape',
    ['source', 'country'],
    buckets=(0, 10, 25, 50, 100, 200, 500)
)

circuit_breaker_state = Gauge(
    'circuit_breaker_state',
    'Circuit breaker state (0=closed, 1=half_open, 2=open)',
    ['service']
)

# ============================================================================
# Hotel Matching Metrics
# ============================================================================

hotel_matching_lookups_total = Counter(
    'hotel_matching_lookups_total',
    'Total hotel matching lookups',
    ['result_type']  # exact, fuzzy, coordinate, new
)

hotel_matching_cache_hits = Counter(
    'hotel_matching_cache_hits_total',
    'Total cache hits in hotel matching'
)

hotel_matching_duration_seconds = Histogram(
    'hotel_matching_duration_seconds',
    'Duration of hotel matching operations',
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1)
)

hotels_created_total = Counter(
    'hotels_created_total',
    'Total new hotels created',
    ['area', 'destination']
)

# ============================================================================
# Data Validation Metrics
# ============================================================================

data_validation_total = Counter(
    'data_validation_total',
    'Total data validation attempts',
    ['status']  # success, error
)

price_anomalies_detected = Counter(
    'price_anomalies_detected_total',
    'Total price anomalies detected',
    ['severity']  # low, medium, high
)

data_quality_score = Histogram(
    'data_quality_score',
    'Data quality scores (0-100)',
    buckets=(0, 20, 40, 60, 80, 90, 95, 100)
)

# ============================================================================
# Celery Task Metrics
# ============================================================================

celery_task_submitted = Counter(
    'celery_task_submitted_total',
    'Total Celery tasks submitted',
    ['task_name', 'queue']
)

celery_task_completed = Counter(
    'celery_task_completed_total',
    'Total Celery tasks completed',
    ['task_name', 'status']  # success, failure, retry
)

celery_task_duration_seconds = Histogram(
    'celery_task_duration_seconds',
    'Celery task execution duration',
    ['task_name'],
    buckets=(1, 10, 30, 60, 120, 300, 600, 1800)
)

celery_queue_size = Gauge(
    'celery_queue_size',
    'Number of tasks in Celery queue',
    ['queue']
)

# ============================================================================
# Tracker Metrics
# ============================================================================

trackers_active = Gauge(
    'trackers_active_total',
    'Number of active trackers'
)

tracker_runs_total = Counter(
    'tracker_runs_total',
    'Total tracker runs',
    ['tracker_id', 'status']
)

tracker_execution_seconds = Histogram(
    'tracker_execution_seconds',
    'Tracker execution duration',
    ['tracker_id'],
    buckets=(10, 30, 60, 120, 300, 600, 1800, 3600)
)

# ============================================================================
# Database Metrics
# ============================================================================

price_history_records_created = Counter(
    'price_history_records_created_total',
    'Total price history records created',
    ['data_source', 'destination']
)

database_query_duration_seconds = Histogram(
    'database_query_duration_seconds',
    'Database query execution time',
    ['operation'],
    buckets=(0.001, 0.01, 0.05, 0.1, 0.5, 1, 5)
)

# ============================================================================
# System Info
# ============================================================================

system_info = Info(
    'hotel_scraper_system',
    'Hotel scraping system information'
)

# Set system info
system_info.info({
    'version': '2.0.0',
    'service': 'serpapi_scraper',
    'environment': 'production'
})

# ============================================================================
# Helper Functions and Decorators
# ============================================================================

def track_scrape_request(source: str, country: str):
    """Decorator to track scraping requests"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status = 'success'

            try:
                result = await func(*args, **kwargs)

                # Track hotels found
                if isinstance(result, dict) and 'hotels' in result:
                    scrape_hotels_found.labels(
                        source=source,
                        country=country
                    ).observe(len(result['hotels']))

                # Track cost if available
                if isinstance(result, dict) and 'cost' in result:
                    scrape_cost_total.labels(
                        source=source,
                        country=country
                    ).inc(result['cost'])

                return result

            except Exception as e:
                status = 'error'
                raise

            finally:
                # Track request
                scrape_requests_total.labels(
                    source=source,
                    status=status,
                    country=country
                ).inc()

                # Track duration
                duration = time.time() - start_time
                scrape_duration_seconds.labels(
                    source=source,
                    country=country
                ).observe(duration)

        return wrapper
    return decorator


def track_celery_task(task_name: str, queue: str = 'default'):
    """Decorator to track Celery tasks"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Track submission
            celery_task_submitted.labels(
                task_name=task_name,
                queue=queue
            ).inc()

            start_time = time.time()
            status = 'success'

            try:
                result = func(*args, **kwargs)
                return result

            except Exception as e:
                status = 'failure'
                raise

            finally:
                # Track completion
                celery_task_completed.labels(
                    task_name=task_name,
                    status=status
                ).inc()

                # Track duration
                duration = time.time() - start_time
                celery_task_duration_seconds.labels(
                    task_name=task_name
                ).observe(duration)

        return wrapper
    return decorator


def track_hotel_matching(result_type: str):
    """Track hotel matching result"""
    hotel_matching_lookups_total.labels(
        result_type=result_type
    ).inc()


def track_database_operation(operation: str):
    """Decorator to track database operations"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)
                return result

            finally:
                duration = time.time() - start_time
                database_query_duration_seconds.labels(
                    operation=operation
                ).observe(duration)

        return wrapper
    return decorator


class MetricsCollector:
    """
    Centralized metrics collector for easy access
    """

    @staticmethod
    def record_scrape_success(source: str, country: str, duration: float, hotels_found: int, cost: float = 0):
        """Record successful scrape"""
        scrape_requests_total.labels(source=source, status='success', country=country).inc()
        scrape_duration_seconds.labels(source=source, country=country).observe(duration)
        scrape_hotels_found.labels(source=source, country=country).observe(hotels_found)
        if cost > 0:
            scrape_cost_total.labels(source=source, country=country).inc(cost)

    @staticmethod
    def record_scrape_failure(source: str, country: str, duration: float):
        """Record failed scrape"""
        scrape_requests_total.labels(source=source, status='error', country=country).inc()
        scrape_duration_seconds.labels(source=source, country=country).observe(duration)

    @staticmethod
    def record_hotel_match(result_type: str, duration: float):
        """Record hotel matching"""
        hotel_matching_lookups_total.labels(result_type=result_type).inc()
        hotel_matching_duration_seconds.observe(duration)

    @staticmethod
    def record_hotel_created(area: str, destination: str):
        """Record new hotel creation"""
        hotels_created_total.labels(area=area, destination=destination).inc()

    @staticmethod
    def record_validation(success: bool):
        """Record data validation"""
        status = 'success' if success else 'error'
        data_validation_total.labels(status=status).inc()

    @staticmethod
    def record_anomaly(severity: str):
        """Record price anomaly"""
        price_anomalies_detected.labels(severity=severity).inc()

    @staticmethod
    def record_quality_score(score: float):
        """Record data quality score"""
        data_quality_score.observe(score)

    @staticmethod
    def update_circuit_breaker(service: str, state: str):
        """Update circuit breaker state"""
        state_map = {'closed': 0, 'half_open': 1, 'open': 2}
        circuit_breaker_state.labels(service=service).set(state_map.get(state, 0))

    @staticmethod
    def update_active_trackers(count: int):
        """Update active tracker count"""
        trackers_active.set(count)

    @staticmethod
    def update_queue_size(queue: str, size: int):
        """Update Celery queue size"""
        celery_queue_size.labels(queue=queue).set(size)


# Export singleton
metrics = MetricsCollector()
