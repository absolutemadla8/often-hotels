"""
Hotel tracking service using SerpAPI
Integrated with Celery for async job processing
"""
import asyncio
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Any

from app.core.logging import get_logger
from app.models.models import (
    Tracker, TrackerResult, UniversalPriceHistory,
    Hotel, Area, Destination, TrackableType
)
from app.services.serp_service import get_serp_service, SearchCriteria, SortBy, HotelClass
from app.services.hotel_matching_service import get_hotel_matching_service
from app.services.data_validation_service import get_validation_service
from app.workers.scraping_tasks import scrape_hotel_prices_task, scrape_multiple_trackers_task

logger = get_logger(__name__)


class TrackingError(Exception):
    """Custom exception for tracking errors"""
    pass


class SerpApiTrackingService:
    """
    Service for tracking hotel prices using SerpAPI + Celery

    Features:
    - Async job processing with Celery
    - Sequential execution to avoid rate limiting
    - Hotel matching and deduplication
    - Data validation and quality checks
    - Comprehensive error handling
    """

    def __init__(self):
        self.matching_service = get_hotel_matching_service()
        self.validation_service = get_validation_service()

    async def submit_tracker_job(
        self,
        tracker: Tracker,
        priority: int = 5
    ) -> str:
        """
        Submit tracker to Celery job queue

        Args:
            tracker: Tracker to execute
            priority: Job priority (0-10, higher = more important)

        Returns:
            Celery task ID
        """
        try:
            # Parse tracker parameters
            params = self._parse_tracker_parameters(tracker)

            # Generate date ranges
            date_ranges = self._generate_date_ranges(
                params["start_date"],
                params["end_date"],
                params.get("interval_days", 1),
                params.get("stay_duration_days", 1)
            )

            # Submit job for first date range (or all if needed)
            check_in, check_out = date_ranges[0]

            task_result = scrape_hotel_prices_task.apply_async(
                args=[
                    tracker.id,
                    check_in.isoformat(),
                    check_out.isoformat(),
                    params["query"]
                ],
                kwargs={
                    "adults": params.get("adults", 2),
                    "children": params.get("children", 0),
                    "currency": params.get("currency", "USD"),
                    "country": params.get("country_code", "us"),
                    "gl": params.get("country_code", "us"),
                    "hl": params.get("language", "en"),
                    "hotel_class": [4, 5],  # Only 4 and 5 star
                    "zone": "residential"
                },
                priority=priority,
                queue="scraping"
            )

            logger.info(
                f"Submitted tracker {tracker.id} to job queue: {task_result.id}"
            )

            return task_result.id

        except Exception as e:
            logger.error(f"Failed to submit tracker {tracker.id}: {e}")
            raise TrackingError(f"Failed to submit tracker: {e}")

    async def submit_multiple_trackers(
        self,
        tracker_ids: List[int],
        priority: int = 5
    ) -> str:
        """
        Submit multiple trackers to job queue (processed sequentially)

        Args:
            tracker_ids: List of tracker IDs
            priority: Job priority

        Returns:
            Batch task ID
        """
        try:
            task_result = scrape_multiple_trackers_task.apply_async(
                args=[tracker_ids],
                priority=priority,
                queue="scraping"
            )

            logger.info(
                f"Submitted batch of {len(tracker_ids)} trackers: {task_result.id}"
            )

            return task_result.id

        except Exception as e:
            logger.error(f"Failed to submit batch: {e}")
            raise TrackingError(f"Failed to submit batch: {e}")

    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get status of Celery task

        Args:
            task_id: Celery task ID

        Returns:
            Task status information
        """
        from celery.result import AsyncResult
        from app.workers.celery_app import celery_app

        result = AsyncResult(task_id, app=celery_app)

        return {
            "task_id": task_id,
            "state": result.state,
            "info": result.info if result.info else {},
            "ready": result.ready(),
            "successful": result.successful() if result.ready() else None,
            "failed": result.failed() if result.ready() else None
        }

    async def run_tracker_sync(self, tracker: Tracker) -> TrackerResult:
        """
        Run tracker synchronously (without Celery) for immediate execution
        Use this for testing or manual runs

        Args:
            tracker: Tracker to execute

        Returns:
            TrackerResult
        """
        start_time = datetime.utcnow()
        run_id = f"{tracker.id}_{int(start_time.timestamp())}"

        try:
            logger.info(f"Starting sync tracker run: {tracker.name} (ID: {tracker.id})")

            # Parse parameters
            params = self._parse_tracker_parameters(tracker)

            # Generate date ranges
            date_ranges = self._generate_date_ranges(
                params["start_date"],
                params["end_date"],
                params.get("interval_days", 1),
                params.get("stay_duration_days", 1)
            )

            total_items_found = 0
            successful_searches = 0

            # Use SerpAPI service
            serp_service = get_serp_service()

            async with serp_service:

                # Process each date range sequentially
                for check_in, check_out in date_ranges:
                    try:
                        # Create search criteria
                        criteria = SearchCriteria(
                            query=params["query"],
                            check_in_date=check_in,
                            check_out_date=check_out,
                            adults=params.get("adults", 2),
                            children=params.get("children", 0),
                            currency=params.get("currency", "USD"),
                            gl=params.get("country_code", "us"),
                            hl=params.get("language", "en"),
                            hotel_class=[HotelClass.FOUR_STAR, HotelClass.FIVE_STAR],
                            sort_by=SortBy.LOWEST_PRICE,
                            is_tracker_search=True  # Enable property_types filter for tracker
                        )

                        # Scrape hotels
                        result = await serp_service.search_hotels(criteria)

                        # Process and save results
                        items_saved = await self._process_and_save_results(
                            tracker, result, params["query"],
                            check_in, check_out, params, run_id
                        )

                        total_items_found += items_saved
                        successful_searches += 1

                        logger.info(
                            f"Processed {items_saved} hotels for "
                            f"{check_in} to {check_out}"
                        )

                        # Delay between requests (SerpAPI has rate limits)
                        await asyncio.sleep(2)

                    except Exception as e:
                        logger.error(
                            f"Error processing date range "
                            f"{check_in} to {check_out}: {e}"
                        )
                        continue

            # Calculate execution time
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds()

            # Create tracker result
            result = await TrackerResult.create(
                tracker=tracker,
                run_id=run_id,
                execution_start=start_time,
                execution_end=end_time,
                success=successful_searches > 0,
                items_found=total_items_found,
                execution_time_seconds=execution_time,
                error_message=None if successful_searches > 0 else "No successful searches"
            )

            # Update tracker stats
            await self._update_tracker_stats(tracker, result.success)

            logger.info(
                f"Completed tracker run: {tracker.name}, "
                f"found {total_items_found} items in {execution_time:.2f}s"
            )

            return result

        except Exception as e:
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds()

            logger.error(f"Tracker run failed: {tracker.name} - {e}")

            # Create failed result
            result = await TrackerResult.create(
                tracker=tracker,
                run_id=run_id,
                execution_start=start_time,
                execution_end=end_time,
                success=False,
                items_found=0,
                execution_time_seconds=execution_time,
                error_message=str(e)
            )

            await self._update_tracker_stats(tracker, False)

            return result

    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two points using Haversine formula.
        Returns distance in kilometers.
        """
        from math import radians, sin, cos, sqrt, atan2

        R = 6371  # Earth's radius in kilometers

        # Convert to radians
        lat1_rad = radians(lat1)
        lon1_rad = radians(lon1)
        lat2_rad = radians(lat2)
        lon2_rad = radians(lon2)

        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        a = sin(dlat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        distance = R * c
        return distance

    async def _match_hotel_to_area(
        self,
        hotel_name: str,
        coordinates: Optional[tuple],
        all_areas: List,
        default_area
    ):
        """
        Match hotel to specific area using priority logic:
        1. Priority: Check if hotel name contains area name (e.g., "Radisson Kuta")
        2. Fallback: Use geo-location distance if coordinates available
        3. Default: Return the default area from query
        """
        hotel_name_lower = hotel_name.lower()

        # Priority 1: Check if hotel name contains any area name
        for area in all_areas:
            area_name_lower = area.name.lower()
            if area_name_lower in hotel_name_lower:
                logger.info(f"Matched hotel '{hotel_name}' to area '{area.name}' by name")
                return area

        # Priority 2: Use geo-location if available
        if coordinates and coordinates[0] is not None and coordinates[1] is not None:
            hotel_lat, hotel_lon = coordinates

            # Find closest area by distance
            closest_area = None
            min_distance = float('inf')

            for area in all_areas:
                if area.latitude is not None and area.longitude is not None:
                    # Use Haversine formula for accurate distance calculation
                    distance = self._haversine_distance(
                        hotel_lat, hotel_lon,
                        area.latitude, area.longitude
                    )

                    if distance < min_distance:
                        min_distance = distance
                        closest_area = area

            # Always use closest area (no distance threshold - assign all hotels to nearest area)
            if closest_area:
                logger.info(f"Matched hotel '{hotel_name}' to area '{closest_area.name}' by geo-location (distance: {min_distance:.4f})")
                return closest_area

        # Priority 3: Default to query-matched area
        logger.info(f"Hotel '{hotel_name}' defaulting to area '{default_area.name}'")
        return default_area

    async def _process_and_save_results(
        self,
        tracker: Tracker,
        scrape_result,  # SerpApiResponse
        query: str,
        check_in: date,
        check_out: date,
        params: Dict[str, Any],
        run_id: str
    ) -> int:
        """Process and save scraping results from SerpAPI"""

        hotels_saved = 0

        # Match query to Area/Destination
        query_lower = query.lower().strip()
        destination = None
        all_destination_areas = []
        default_area = None  # Will be used as fallback for hotel matching

        # Strategy 1: Try destination matching first (for queries like "Bangkok, Thailand hotels")
        query_words = query_lower.replace(",", " ").split()
        for word in query_words:
            if len(word) > 3:  # Skip short words
                dest = await Destination.filter(name__icontains=word).first()
                if dest:
                    destination = dest
                    logger.info(f"Matched destination '{destination.name}' using word '{word}' from query '{query}'")
                    break

        # Strategy 2: Try exact area match if no destination found
        if not destination:
            area = await Area.filter(name__icontains=query_lower).first()
            if area:
                await area.fetch_related('destination')
                destination = area.destination
                default_area = area  # Use this area as default for unmatched hotels
                logger.info(f"Matched area '{area.name}' -> destination '{destination.name}'")
            else:
                # Strategy 3: Try matching individual words to areas
                for word in query_words:
                    if len(word) > 3:
                        area = await Area.filter(name__icontains=word).first()
                        if area:
                            await area.fetch_related('destination')
                            destination = area.destination
                            default_area = area  # Use this area as default for unmatched hotels
                            logger.info(f"Matched area '{area.name}' using word '{word}' from query '{query}'")
                            break

        if not destination:
            logger.warning(f"No destination found for query: {query}")
            logger.info(f"Tried matching: full query='{query_lower}', words={query_words}")
            return 0

        # Fetch all areas for this destination
        all_destination_areas = await Area.filter(destination=destination).all()
        print(f"✓ Found {len(all_destination_areas)} areas for destination '{destination.name}'")
        logger.info(f"Found {len(all_destination_areas)} areas for destination '{destination.name}'")

        # Process hotels from SerpAPI response
        hotels = scrape_result.properties  # PropertyResult objects
        seen_hotels = set()

        for hotel_property in hotels:
            try:
                hotel_name = hotel_property.name
                logger.info(f"Processing hotel: {hotel_name}")

                # Skip duplicates
                if hotel_name in seen_hotels:
                    logger.debug(f"Skipping duplicate hotel: {hotel_name}")
                    continue
                seen_hotels.add(hotel_name)

                # Extract coordinates
                coordinates = None
                if hotel_property.gps_coordinates:
                    coordinates = (
                        hotel_property.gps_coordinates.latitude,
                        hotel_property.gps_coordinates.longitude
                    )
                    logger.info(f"Hotel '{hotel_name}' coordinates: {coordinates}")
                else:
                    logger.warning(f"Hotel '{hotel_name}' has no GPS coordinates")

                # Match hotel to specific area using priority logic
                logger.info(f"Matching hotel '{hotel_name}' to area...")
                matched_area = await self._match_hotel_to_area(
                    hotel_name, coordinates, all_destination_areas, default_area
                )

                if matched_area:
                    logger.info(f"✓ Hotel '{hotel_name}' matched to area: {matched_area.name} (ID: {matched_area.id})")
                else:
                    logger.error(f"✗ Hotel '{hotel_name}' could not be matched to any area!")

                # Extract first image as thumbnail
                thumbnail = None
                images_list = []
                if hotel_property.images and len(hotel_property.images) > 0:
                    # Get first image as thumbnail
                    thumbnail = hotel_property.images[0].thumbnail if hasattr(hotel_property.images[0], 'thumbnail') else None
                    # Store all images as JSON array
                    images_list = [
                        {
                            "thumbnail": img.thumbnail if hasattr(img, 'thumbnail') else None,
                            "original": img.original_image if hasattr(img, 'original_image') else None
                        }
                        for img in hotel_property.images[:5]  # Store first 5 images
                    ]

                # Find or create hotel with matched area
                logger.info(f"Finding or creating hotel '{hotel_name}' in area '{matched_area.name}'")
                hotel, is_new = await self.matching_service.find_or_create_hotel(
                    name=hotel_name,
                    area=matched_area,
                    coordinates=coordinates,
                    star_rating=hotel_property.extracted_hotel_class,
                    thumbnail=thumbnail,
                    images=images_list
                )

                if is_new:
                    logger.info(f"✓ Created new hotel: {hotel_name} (ID: {hotel.id}, Area: {matched_area.name})")
                else:
                    logger.info(f"✓ Found existing hotel: {hotel_name} (ID: {hotel.id})")

                # Save prices from all booking sources
                currency = params.get("currency", "USD")

                # Check if we have prices from multiple sources
                if hotel_property.prices and len(hotel_property.prices) > 0:
                    logger.info(f"Saving {len(hotel_property.prices)} price sources for '{hotel_name}'")
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
                            price_date=check_in,
                            search_date=date.today(),
                            data_source="serpapi",
                            booking_source=price_source.source,  # Booking.com, Hotels.com, etc.
                            search_criteria={
                                "property_name": hotel_name,
                                "query": query,
                                "check_in_date": check_in.isoformat(),
                                "check_out_date": check_out.isoformat(),
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
                                "area_id": matched_area.id,
                                "destination_id": destination.id,
                                "tracker_id": tracker.id,
                                "run_id": run_id
                            }
                        )

                    hotels_saved += 1
                    logger.info(f"✓ Successfully saved hotel '{hotel_name}' with {len(hotel_property.prices)} price sources (Total: {hotels_saved})")
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
                        price_date=check_in,
                        search_date=date.today(),
                        data_source="serpapi",
                        booking_source=None,  # No specific source
                        search_criteria={
                            "property_name": hotel_name,
                            "query": query,
                            "check_in_date": check_in.isoformat(),
                            "check_out_date": check_out.isoformat(),
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
                            "area_id": matched_area.id,
                            "destination_id": destination.id,
                            "tracker_id": tracker.id,
                            "run_id": run_id
                        }
                    )

                    hotels_saved += 1

            except Exception as e:
                logger.error(f"Failed to process hotel {hotel_property.name}: {e}")
                continue

        logger.info(f"Saved {hotels_saved} hotels from SerpAPI scrape")
        return hotels_saved

    def _parse_tracker_parameters(self, tracker: Tracker) -> Dict[str, Any]:
        """Parse tracker parameters"""
        try:
            params = tracker.search_criteria or {}

            # Required parameters
            query = params.get("query") or tracker.name
            start_date = datetime.fromisoformat(params["start_date"]).date()
            end_date = datetime.fromisoformat(params["end_date"]).date()

            # Optional parameters
            return {
                "query": query,
                "start_date": start_date,
                "end_date": end_date,
                "interval_days": params.get("interval_days", 1),
                "stay_duration_days": params.get("stay_duration_days", 1),
                "adults": params.get("adults", 2),
                "children": params.get("children", 0),
                "currency": params.get("currency", "USD"),
                "country_code": params.get("country_code", "us"),
                "language": params.get("language", "en"),
            }

        except (KeyError, ValueError, TypeError) as e:
            raise TrackingError(f"Invalid tracker parameters: {e}")

    def _generate_date_ranges(
        self,
        start_date: date,
        end_date: date,
        interval_days: int = 1,
        stay_duration_days: int = 1
    ) -> List[tuple[date, date]]:
        """Generate date ranges for tracking"""
        date_ranges = []
        current_date = start_date

        while current_date <= end_date:
            check_out_date = current_date + timedelta(days=stay_duration_days)

            if check_out_date > end_date + timedelta(days=stay_duration_days):
                break

            date_ranges.append((current_date, check_out_date))
            current_date += timedelta(days=interval_days)

        return date_ranges

    async def _update_tracker_stats(self, tracker: Tracker, success: bool):
        """Update tracker statistics"""
        tracker.total_runs += 1
        tracker.last_run_at = datetime.utcnow()

        if success:
            tracker.successful_runs += 1

        await tracker.save()

    async def get_service_metrics(self) -> Dict[str, Any]:
        """Get comprehensive service metrics"""
        return {
            "matching_service": self.matching_service.get_metrics(),
            "validation_service": self.validation_service.get_metrics()
        }


async def get_serpapi_tracking_service() -> SerpApiTrackingService:
    """Get SerpAPI tracking service instance"""
    return SerpApiTrackingService()
