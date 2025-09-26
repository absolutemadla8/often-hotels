import asyncio
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum

from app.models.models import (
    Tracker, TrackerResult, UniversalPriceHistory,
    Hotel, Country, Destination, Area, TrackableType
)
from app.services.serp_service import (
    SerpApiService, SearchCriteria, SortBy, Rating, HotelClass,
    PropertyResult, SerpApiResponse, get_serp_service
)

logger = logging.getLogger(__name__)


class TrackingError(Exception):
    """Custom exception for tracking errors"""
    pass


@dataclass
class TrackingTask:
    """Represents a single tracking task"""
    tracker_id: int
    search_query: str
    check_in_date: date
    check_out_date: date
    adults: int = 2
    children: int = 0
    currency: str = "USD"
    country_code: str = "us"
    language: str = "en"


class HotelTrackingService:
    """Service for tracking hotel prices using SerpApi"""

    def __init__(self, serp_service: Optional[SerpApiService] = None):
        self.serp_service = serp_service or get_serp_service()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self.serp_service, 'close'):
            await self.serp_service.close()

    async def run_tracker(self, tracker: Tracker) -> TrackerResult:
        """Run a single tracker and save results"""
        start_time = datetime.utcnow()
        run_id = f"{tracker.id}_{int(start_time.timestamp())}"

        try:
            logger.info(f"Starting tracker run: {tracker.name} (ID: {tracker.id})")

            # Parse search parameters from tracker
            search_params = self._parse_tracker_parameters(tracker)

            # Generate date ranges if interval tracking is enabled
            date_ranges = self._generate_date_ranges(
                search_params["start_date"],
                search_params["end_date"],
                search_params.get("interval_days", 1),
                search_params.get("stay_duration_days", 1)
            )

            total_items_found = 0
            successful_searches = 0

            # Execute searches for each date range
            for check_in, check_out in date_ranges:
                try:
                    criteria = SearchCriteria(
                        query=search_params["query"],
                        check_in_date=check_in,
                        check_out_date=check_out,
                        adults=search_params.get("adults", 2),
                        children=search_params.get("children", 0),
                        currency=search_params.get("currency", "USD"),
                        gl=search_params.get("country_code", "us"),
                        hl=search_params.get("language", "en"),
                        sort_by=SortBy.LOWEST_PRICE,  # Default to lowest price
                        hotel_class=[HotelClass.FOUR_STAR, HotelClass.FIVE_STAR],  # Only 4 and 5 star hotels
                    )

                    # Search hotels
                    response = await self.serp_service.search_hotels(criteria)

                    # Process and save results
                    items_saved = await self._process_search_results(
                        response, tracker, run_id, criteria
                    )

                    total_items_found += items_saved
                    successful_searches += 1

                    logger.info(
                        f"Processed {items_saved} items for {check_in} to {check_out}"
                    )

                    # Add delay between requests to respect rate limits
                    await asyncio.sleep(1)

                except Exception as e:
                    logger.error(
                        f"Error processing date range {check_in} to {check_out}: {e}"
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

            # Update tracker statistics
            await self._update_tracker_stats(tracker, result.success)

            logger.info(
                f"Completed tracker run: {tracker.name}, "
                f"found {total_items_found} items in {execution_time:.2f}s"
            )

            return result

        except Exception as e:
            # Calculate execution time even on error
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

    def _parse_tracker_parameters(self, tracker: Tracker) -> Dict[str, Any]:
        """Parse tracker parameters from JSON config"""
        try:
            params = tracker.search_criteria or {}

            # Required parameters
            query = params.get("query") or tracker.name
            start_date = datetime.fromisoformat(params["start_date"]).date()
            end_date = datetime.fromisoformat(params["end_date"]).date()

            # Optional parameters
            interval_days = params.get("interval_days", 1)
            stay_duration_days = params.get("stay_duration_days", 1)
            adults = params.get("adults", 2)
            children = params.get("children", 0)
            currency = params.get("currency", "USD")
            country_code = params.get("country_code", "us")
            language = params.get("language", "en")

            return {
                "query": query,
                "start_date": start_date,
                "end_date": end_date,
                "interval_days": interval_days,
                "stay_duration_days": stay_duration_days,
                "adults": adults,
                "children": children,
                "currency": currency,
                "country_code": country_code,
                "language": language,
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
        """Generate date ranges for interval tracking"""
        date_ranges = []
        current_date = start_date

        while current_date <= end_date:
            check_out_date = current_date + timedelta(days=stay_duration_days)

            # Don't exceed the end date
            if check_out_date > end_date + timedelta(days=stay_duration_days):
                break

            date_ranges.append((current_date, check_out_date))
            current_date += timedelta(days=interval_days)

        return date_ranges

    async def _process_search_results(
        self,
        response: SerpApiResponse,
        tracker: Tracker,
        run_id: str,
        criteria: SearchCriteria
    ) -> int:
        """Process search results and save to price history"""
        items_saved = 0

        # Process main properties
        for property_result in response.properties:
            try:
                await self._save_price_history(
                    property_result, tracker, run_id, criteria
                )
                items_saved += 1
            except Exception as e:
                logger.warning(f"Failed to save property {property_result.name}: {e}")
                continue

        # Process ads if they contain pricing info
        for ad_result in response.ads:
            try:
                if ad_result.extracted_price:
                    # Convert ad to property-like structure for saving
                    await self._save_ad_price_history(
                        ad_result, tracker, run_id, criteria
                    )
                    items_saved += 1
            except Exception as e:
                logger.warning(f"Failed to save ad {ad_result.name}: {e}")
                continue

        return items_saved

    async def _save_price_history(
        self,
        property_result: PropertyResult,
        tracker: Tracker,
        run_id: str,
        criteria: SearchCriteria
    ) -> None:
        """Save property result to price history"""

        # Extract price information
        price = None
        currency = criteria.currency

        if property_result.rate_per_night and property_result.rate_per_night.extracted_lowest:
            price = property_result.rate_per_night.extracted_lowest
        elif property_result.total_rate and property_result.total_rate.extracted_lowest:
            price = property_result.total_rate.extracted_lowest

        if price is None:
            logger.warning(f"No price found for property: {property_result.name}")
            return

        # Determine availability
        is_available = price > 0

        # Create price history entry
        await UniversalPriceHistory.create(
            trackable_type=TrackableType.HOTEL_ROOM,
            trackable_id=None,  # We don't have hotel ID from SERP
            price=price,
            currency=currency,
            is_available=is_available,
            price_date=criteria.check_in_date,
            search_date=criteria.check_in_date,
            data_source="serpapi",
            search_criteria={
                "property_name": property_result.name,
                "property_type": property_result.type,
                "query": criteria.query,
                "check_in_date": criteria.check_in_date.isoformat(),
                "check_out_date": criteria.check_out_date.isoformat(),
                "adults": criteria.adults,
                "children": criteria.children,
                "overall_rating": property_result.overall_rating,
                "reviews": property_result.reviews,
                "hotel_class": property_result.extracted_hotel_class,
                "amenities": property_result.amenities,
                "gps_coordinates": property_result.gps_coordinates.dict() if property_result.gps_coordinates else None,
                "property_token": property_result.property_token,
                "images": [img.dict() for img in property_result.images] if property_result.images else [],
                "main_image": property_result.original_image,
                "run_id": run_id,
                "tracker_id": tracker.id,
            }
        )

    async def _save_ad_price_history(
        self,
        ad_result,
        tracker: Tracker,
        run_id: str,
        criteria: SearchCriteria
    ) -> None:
        """Save ad result to price history"""

        price = ad_result.extracted_price
        currency = criteria.currency
        is_available = price > 0

        await UniversalPriceHistory.create(
            trackable_type=TrackableType.HOTEL_ROOM,
            trackable_id=None,
            price=price,
            currency=currency,
            is_available=is_available,
            price_date=criteria.check_in_date,
            search_date=criteria.check_in_date,
            data_source="serpapi_ads",
            search_criteria={
                "property_name": ad_result.name,
                "source": ad_result.source,
                "query": criteria.query,
                "check_in_date": criteria.check_in_date.isoformat(),
                "check_out_date": criteria.check_out_date.isoformat(),
                "adults": criteria.adults,
                "children": criteria.children,
                "overall_rating": ad_result.overall_rating,
                "reviews": ad_result.reviews,
                "hotel_class": ad_result.hotel_class,
                "amenities": ad_result.amenities,
                "gps_coordinates": ad_result.gps_coordinates.dict() if ad_result.gps_coordinates else None,
                "property_token": ad_result.property_token,
                "run_id": run_id,
                "tracker_id": tracker.id,
                "is_ad": True,
            }
        )

    async def _update_tracker_stats(self, tracker: Tracker, success: bool) -> None:
        """Update tracker statistics"""
        tracker.total_runs += 1
        tracker.last_run_at = datetime.utcnow()

        if success:
            tracker.successful_runs += 1

        await tracker.save()

    async def run_multiple_trackers(self, tracker_ids: List[int]) -> List[TrackerResult]:
        """Run multiple trackers concurrently"""
        # Fetch trackers
        trackers = []
        for tracker_id in tracker_ids:
            tracker = await Tracker.get_or_none(id=tracker_id, status="active")
            if tracker:
                trackers.append(tracker)
            else:
                logger.warning(f"Tracker {tracker_id} not found or not active")

        if not trackers:
            logger.warning("No active trackers found to run")
            return []

        # Run trackers concurrently with limited concurrency
        semaphore = asyncio.Semaphore(3)  # Limit to 3 concurrent requests

        async def run_single_tracker(tracker):
            async with semaphore:
                return await self.run_tracker(tracker)

        tasks = [run_single_tracker(tracker) for tracker in trackers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions and return successful results
        successful_results = []
        for result in results:
            if isinstance(result, TrackerResult):
                successful_results.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Tracker execution failed: {result}")

        return successful_results

    async def run_scheduled_trackers(self) -> List[TrackerResult]:
        """Run all trackers that are due for execution"""
        # Find trackers that need to run
        # This is a simple implementation - in production you might want
        # more sophisticated scheduling logic
        trackers = await Tracker.filter(
            status="active",
            is_scheduled=True
        ).all()

        due_trackers = []
        for tracker in trackers:
            if self._is_tracker_due(tracker):
                due_trackers.append(tracker)

        if not due_trackers:
            logger.info("No trackers due for execution")
            return []

        logger.info(f"Running {len(due_trackers)} scheduled trackers")
        tracker_ids = [t.id for t in due_trackers]

        return await self.run_multiple_trackers(tracker_ids)

    def _is_tracker_due(self, tracker: Tracker) -> bool:
        """Check if a tracker is due for execution"""
        if not tracker.last_run_at:
            return True

        # Simple frequency check - run if hasn't run in the last hour
        # In production, you'd have more sophisticated scheduling
        time_since_last_run = datetime.utcnow() - tracker.last_run_at
        return time_since_last_run.total_seconds() > 3600  # 1 hour


async def get_tracking_service() -> HotelTrackingService:
    """Get configured tracking service instance"""
    return HotelTrackingService()