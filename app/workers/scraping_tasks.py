"""
Celery tasks for hotel price scraping with retry logic and error handling
"""
from celery import Task
from celery.exceptions import MaxRetriesExceededError, SoftTimeLimitExceeded
from typing import Dict, List, Any, Optional
from datetime import datetime, date
import logging
import asyncio

from app.workers.celery_app import celery_app
from app.models.models import Tracker, TrackerResult, UniversalPriceHistory, TrackableType
from app.services.serp_service import get_serp_service, SearchCriteria, SortBy, HotelClass
from app.services.hotel_matching_service import get_hotel_matching_service

logger = logging.getLogger(__name__)


async def init_db():
    """Initialize Tortoise ORM for Celery tasks"""
    from tortoise import Tortoise
    from app.core.config import settings

    # Handle different database URL formats
    db_url = settings.DATABASE_URL
    if db_url and db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgres://', 1)
        if 'sslmode=require' in db_url:
            db_url = db_url.replace('?sslmode=require', '').replace('&sslmode=require', '')

    await Tortoise.init(
        db_url=db_url,
        modules={'models': ['app.models.models']}
    )


class CallbackTask(Task):
    """Base task with lifecycle callbacks for monitoring"""

    def on_success(self, retval, task_id, args, kwargs):
        """Called when task succeeds"""
        logger.info(f"✅ Task {task_id} succeeded: {retval.get('status', 'unknown')}")

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when task fails"""
        logger.error(f"❌ Task {task_id} failed: {exc}")
        # TODO: Send alert (email, Slack, PagerDuty, etc.)

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Called when task is retried"""
        logger.warning(f"🔄 Task {task_id} retrying due to: {exc}")


@celery_app.task(
    bind=True,
    base=CallbackTask,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 60},
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    name="scrape_hotel_prices"
)
def scrape_hotel_prices_task(
    self,
    tracker_id: int,
    check_in: str,
    check_out: str,
    query: str,
    **kwargs
) -> Dict[str, Any]:
    """
    Celery task for scraping hotel prices with BrightData

    Args:
        tracker_id: Tracker ID
        check_in: Check-in date (ISO format)
        check_out: Check-out date (ISO format)
        query: Search query
        **kwargs: Additional parameters (adults, children, currency, etc.)

    Returns:
        Result dictionary with status and metrics
    """

    # Update task progress
    self.update_state(
        state='PROGRESS',
        meta={'current': 0, 'total': 100, 'status': 'Initializing scrape...'}
    )

    try:
        # Run async function in sync context
        result = asyncio.run(_scrape_hotel_prices_async(
            self,
            tracker_id,
            check_in,
            check_out,
            query,
            **kwargs
        ))

        return result

    except SoftTimeLimitExceeded:
        logger.error(f"Task {self.request.id} exceeded time limit")
        raise

    except MaxRetriesExceededError:
        logger.critical(f"Task {self.request.id} exceeded max retries for tracker {tracker_id}")
        # Mark tracker as failed
        asyncio.run(_mark_tracker_failed(tracker_id, "Max retries exceeded"))
        raise

    except Exception as exc:
        logger.error(f"Task {self.request.id} failed: {exc}")
        raise self.retry(exc=exc)


async def _scrape_hotel_prices_async(
    task,
    tracker_id: int,
    check_in: str,
    check_out: str,
    query: str,
    **kwargs
) -> Dict[str, Any]:
    """Async implementation of scraping task"""

    # Initialize database
    await init_db()

    start_time = datetime.utcnow()

    try:
        # Fetch tracker
        tracker = await Tracker.get_or_none(id=tracker_id)
        if not tracker:
            raise Exception(f"Tracker {tracker_id} not found")

        # Update progress
        task.update_state(
            state='PROGRESS',
            meta={'current': 20, 'total': 100, 'status': 'Scraping hotels...'}
        )

        # Configure SerpAPI service
        serp_service = get_serp_service()

        # Scrape hotels
        async with serp_service:
            # Create search criteria
            criteria = SearchCriteria(
                query=query,
                check_in_date=date.fromisoformat(check_in),
                check_out_date=date.fromisoformat(check_out),
                adults=kwargs.get("adults", 2),
                children=kwargs.get("children", 0),
                currency=kwargs.get("currency", "USD"),
                gl=kwargs.get("gl", "us"),
                hl=kwargs.get("hl", "en"),
                hotel_class=[HotelClass.FOUR_STAR, HotelClass.FIVE_STAR],
                sort_by=SortBy.LOWEST_PRICE
            )

            result = await serp_service.search_hotels(criteria)

            # Track metrics
            metrics = {
                "total_requests": 1,
                "successful_requests": 1,
                "total_cost_usd": 0.01,  # SerpAPI costs per request
                "search_time": result.search_metadata.time_taken
            }

        # Update progress
        task.update_state(
            state='PROGRESS',
            meta={'current': 60, 'total': 100, 'status': 'Processing results...'}
        )

        # Process and save results
        hotels_saved = await _process_and_save_results(
            tracker,
            result,
            query,
            check_in,
            check_out,
            kwargs
        )

        # Update progress
        task.update_state(
            state='PROGRESS',
            meta={'current': 90, 'total': 100, 'status': 'Finalizing...'}
        )

        # Calculate execution time
        end_time = datetime.utcnow()
        execution_time = (end_time - start_time).total_seconds()

        # Create tracker result
        await TrackerResult.create(
            tracker=tracker,
            run_id=f"{tracker_id}_{int(start_time.timestamp())}",
            execution_start=start_time,
            execution_end=end_time,
            success=True,
            items_found=hotels_saved,
            execution_time_seconds=execution_time,
            error_message=None
        )

        # Update tracker stats
        tracker.total_runs += 1
        tracker.successful_runs += 1
        tracker.last_run_at = datetime.utcnow()
        await tracker.save()

        return {
            "status": "success",
            "tracker_id": tracker_id,
            "hotels_found": hotels_saved,
            "execution_time": execution_time,
            "cost_usd": metrics.get("total_cost_usd", 0),
            "scrape_metrics": metrics
        }

    except Exception as e:
        logger.error(f"Scraping failed for tracker {tracker_id}: {e}")

        # Save failed result
        end_time = datetime.utcnow()
        execution_time = (end_time - start_time).total_seconds()

        tracker = await Tracker.get_or_none(id=tracker_id)
        if tracker:
            await TrackerResult.create(
                tracker=tracker,
                run_id=f"{tracker_id}_{int(start_time.timestamp())}",
                execution_start=start_time,
                execution_end=end_time,
                success=False,
                items_found=0,
                execution_time_seconds=execution_time,
                error_message=str(e)
            )

            tracker.total_runs += 1
            tracker.last_run_at = datetime.utcnow()
            await tracker.save()

        raise


async def _process_and_save_results(
    tracker: Tracker,
    scrape_result,  # SerpApiResponse
    query: str,
    check_in: str,
    check_out: str,
    params: Dict[str, Any]
) -> int:
    """Process scraping results from SerpAPI and save to database"""

    from app.models.models import Area, Destination

    hotels_saved = 0
    matching_service = get_hotel_matching_service()

    # Extract hotels from SerpAPI result
    hotels = scrape_result.properties  # PropertyResult objects

    # Match query to Area/Destination
    query_lower = query.lower().strip()
    area = await Area.filter(name__icontains=query_lower).first()

    if not area:
        # Try destination matching
        destination = await Destination.filter(name__icontains=query_lower).first()
        if destination:
            area = await Area.filter(destination=destination).first()

    if not area:
        logger.warning(f"No area found for query: {query}")
        # TODO: Create area dynamically or skip
        return 0

    await area.fetch_related('destination')
    destination = area.destination

    # Process each hotel from SerpAPI
    seen_hotels = set()

    for hotel_property in hotels:
        try:
            hotel_name = hotel_property.name

            # Skip duplicates
            if hotel_name in seen_hotels:
                continue
            seen_hotels.add(hotel_name)

            # Extract coordinates
            coordinates = None
            if hotel_property.gps_coordinates:
                coordinates = (
                    hotel_property.gps_coordinates.latitude,
                    hotel_property.gps_coordinates.longitude
                )

            # Find or create hotel using matching service
            hotel, is_new = await matching_service.find_or_create_hotel(
                name=hotel_name,
                area=area,
                coordinates=coordinates,
                star_rating=hotel_property.extracted_hotel_class
            )

            # Save prices from all booking sources
            currency = params.get("currency", "USD")

            # Check if we have prices from multiple sources
            if hotel_property.prices and len(hotel_property.prices) > 0:
                # Save price from each booking source
                for price_source in hotel_property.prices:
                    if not price_source.rate_per_night or not price_source.rate_per_night.extracted_lowest:
                        continue

                    await UniversalPriceHistory.create(
                        trackable_type=TrackableType.HOTEL_ROOM,
                        trackable_id=hotel.id,
                        price=price_source.rate_per_night.extracted_lowest,
                        base_price=price_source.rate_per_night.extracted_before_taxes_fees,
                        currency=currency,
                        is_available=True,
                        price_date=date.fromisoformat(check_in),
                        search_date=date.today(),
                        data_source="serpapi",
                        booking_source=price_source.source,  # Booking.com, Hotels.com, etc.
                        search_criteria={
                            "property_name": hotel_name,
                            "query": query,
                            "check_in_date": check_in,
                            "check_out_date": check_out,
                            "adults": params.get("adults", 2),
                            "children": params.get("children", 0),
                            "overall_rating": hotel_property.overall_rating,
                            "reviews": hotel_property.reviews,
                            "hotel_class": hotel_property.extracted_hotel_class,
                            "amenities": hotel_property.amenities,
                            "gps_coordinates": hotel_property.gps_coordinates.dict() if hotel_property.gps_coordinates else None,
                            "images": [img.dict() for img in hotel_property.images] if hotel_property.images else [],
                            "property_token": hotel_property.property_token,
                            "booking_source_logo": price_source.logo,
                            "hotel_id": hotel.id,
                            "area_id": area.id,
                            "destination_id": destination.id,
                            "tracker_id": tracker.id
                        }
                    )

                hotels_saved += 1
            else:
                # Fallback: save single price if no multiple sources available
                if not hotel_property.rate_per_night or not hotel_property.rate_per_night.extracted_lowest:
                    logger.warning(f"No valid price for hotel: {hotel_name}")
                    continue

                await UniversalPriceHistory.create(
                    trackable_type=TrackableType.HOTEL_ROOM,
                    trackable_id=hotel.id,
                    price=hotel_property.rate_per_night.extracted_lowest,
                    base_price=hotel_property.rate_per_night.extracted_before_taxes_fees,
                    currency=currency,
                    is_available=True,
                    price_date=date.fromisoformat(check_in),
                    search_date=date.today(),
                    data_source="serpapi",
                    booking_source=None,  # No specific source
                    search_criteria={
                        "property_name": hotel_name,
                        "query": query,
                        "check_in_date": check_in,
                        "check_out_date": check_out,
                        "adults": params.get("adults", 2),
                        "children": params.get("children", 0),
                        "overall_rating": hotel_property.overall_rating,
                        "reviews": hotel_property.reviews,
                        "hotel_class": hotel_property.extracted_hotel_class,
                        "amenities": hotel_property.amenities,
                        "gps_coordinates": hotel_property.gps_coordinates.dict() if hotel_property.gps_coordinates else None,
                        "images": [img.dict() for img in hotel_property.images] if hotel_property.images else [],
                        "property_token": hotel_property.property_token,
                        "hotel_id": hotel.id,
                        "area_id": area.id,
                        "destination_id": destination.id,
                        "tracker_id": tracker.id
                    }
                )

                hotels_saved += 1

        except Exception as e:
            logger.error(f"Failed to process hotel {hotel_property.name}: {e}")
            continue

    logger.info(f"Saved {hotels_saved} hotels for tracker {tracker.id}")
    return hotels_saved


async def _mark_tracker_failed(tracker_id: int, error_message: str):
    """Mark tracker as failed"""
    await init_db()

    tracker = await Tracker.get_or_none(id=tracker_id)
    if tracker:
        tracker.status = "failed"
        tracker.last_run_at = datetime.utcnow()
        await tracker.save()

        logger.error(f"Tracker {tracker_id} marked as failed: {error_message}")


@celery_app.task(
    bind=True,
    base=CallbackTask,
    name="scrape_multiple_trackers"
)
def scrape_multiple_trackers_task(self, tracker_ids: List[int]) -> Dict[str, Any]:
    """
    Batch scraping task - spawns individual scraping tasks sequentially

    Args:
        tracker_ids: List of tracker IDs to process

    Returns:
        Summary of batch execution
    """

    try:
        result = asyncio.run(_scrape_multiple_trackers_async(self, tracker_ids))
        return result
    except Exception as e:
        logger.error(f"Batch scraping failed: {e}")
        raise


async def _scrape_multiple_trackers_async(task, tracker_ids: List[int]) -> Dict[str, Any]:
    """Async implementation of batch scraping"""

    await init_db()

    total = len(tracker_ids)
    completed = 0
    failed = 0
    task_ids = []

    # Process trackers sequentially to avoid rate limiting
    for i, tracker_id in enumerate(tracker_ids):
        try:
            # Update progress
            task.update_state(
                state='PROGRESS',
                meta={
                    'current': i + 1,
                    'total': total,
                    'status': f'Processing tracker {tracker_id}...'
                }
            )

            # Fetch tracker to get search criteria
            tracker = await Tracker.get_or_none(id=tracker_id)
            if not tracker:
                logger.warning(f"Tracker {tracker_id} not found")
                failed += 1
                continue

            # Extract search parameters
            params = tracker.search_criteria or {}

            # Submit scraping task
            task_result = scrape_hotel_prices_task.apply_async(
                args=[
                    tracker_id,
                    params.get("start_date", date.today().isoformat()),
                    params.get("end_date", (date.today()).isoformat()),
                    params.get("query", tracker.name)
                ],
                kwargs=params
            )

            task_ids.append(task_result.id)
            completed += 1

            # Delay between submissions to avoid overwhelming the queue
            await asyncio.sleep(2)

        except Exception as e:
            logger.error(f"Failed to submit tracker {tracker_id}: {e}")
            failed += 1

    return {
        "status": "success",
        "total_trackers": total,
        "submitted": completed,
        "failed": failed,
        "task_ids": task_ids
    }


@celery_app.task(
    bind=True,
    base=CallbackTask,
    name="process_scraping_results"
)
def process_scraping_results_task(
    self,
    result_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Process scraping results (data validation, anomaly detection, etc.)

    Args:
        result_data: Raw scraping results

    Returns:
        Processed data
    """

    # TODO: Implement data validation, price anomaly detection, etc.
    return {"status": "success", "processed": True}
