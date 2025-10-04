"""
Hotel Price Tracking Service

This service handles hotel discovery and price tracking operations.
It integrates with SerpApi for hotel searches and manages hotel and price history records.
"""

import asyncio
import json
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal

from tortoise.expressions import Q
from tortoise.transactions import in_transaction

from app.core.hotel_tracking_config import tracking_config, get_tracking_days, get_search_criteria_defaults
from app.models.models import (
    Destination, Area, Hotel, UniversalPriceHistory, Country,
    TrackableType, HotelType, HotelChain, TaskStatus
)
from app.services.serp_service import (
    SerpApiService, SearchCriteria, PropertyResult, SerpApiResponse,
    get_serp_service
)

logger = logging.getLogger(__name__)


class HotelTrackingService:
    """Service for hotel price tracking operations"""
    
    def __init__(self):
        self.serp_service: Optional[SerpApiService] = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.serp_service = get_serp_service()
        await self.serp_service.__aenter__()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.serp_service:
            await self.serp_service.__aexit__(exc_type, exc_val, exc_tb)
    
    async def scan_all_tracking_destinations(self) -> Dict[str, Any]:
        """
        Scan all destinations with tracking=True and process hotel tracking
        
        Returns:
            Summary of tracking operation
        """
        start_time = datetime.utcnow()
        
        # Get all destinations with tracking enabled
        logger.info("About to query destinations...")
        destinations = await Destination.filter(
            tracking=True,
            is_active=True
        ).prefetch_related('country').all()
        logger.info(f"Found {len(destinations)} destinations")
        
        if not destinations:
            logger.info("No destinations with tracking enabled found")
            return {
                "success": True,
                "destinations_found": 0,
                "destinations_processed": 0,
                "hotels_discovered": 0,
                "price_records_created": 0,
                "errors": [],
                "processing_time_seconds": 0
            }
        
        logger.info(f"Found {len(destinations)} destinations with tracking enabled")
        
        total_hotels_discovered = 0
        total_price_records = 0
        destinations_processed = 0
        errors = []
        
        # Process each destination
        for destination in destinations:
            try:
                logger.info(f"Processing destination: {destination.name}")
                
                result = await self.process_destination_tracking(destination)
                
                total_hotels_discovered += result['hotels_discovered']
                total_price_records += result['price_records_created']
                destinations_processed += 1
                
                if tracking_config.ENABLE_DETAILED_LOGGING:
                    logger.info(
                        f"Completed {destination.name}: "
                        f"{result['hotels_discovered']} hotels, "
                        f"{result['price_records_created']} price records"
                    )
                
                # Add delay between destinations to respect API limits
                if tracking_config.API_CALL_DELAY_SECONDS > 0:
                    await asyncio.sleep(tracking_config.API_CALL_DELAY_SECONDS)
                    
            except Exception as e:
                error_msg = f"Error processing {destination.name}: {str(e)}"
                logger.error(error_msg)
                errors.append({
                    "destination": destination.name,
                    "error": str(e)
                })
        
        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds()
        
        return {
            "success": len(errors) == 0,
            "destinations_found": len(destinations),
            "destinations_processed": destinations_processed,
            "hotels_discovered": total_hotels_discovered,
            "price_records_created": total_price_records,
            "errors": errors,
            "processing_time_seconds": processing_time,
            "completed_at": end_time.isoformat()
        }
    
    async def scan_all_tracking_destinations_with_progress(self, task_instance, task_id: str) -> Dict[str, Any]:
        """
        Scan all destinations with tracking=True and process hotel tracking with detailed progress updates
        
        Args:
            task_instance: BaseTask instance for logging progress
            task_id: Task ID for progress tracking
            
        Returns:
            Summary of tracking operation
        """
        start_time = datetime.utcnow()
        
        # Get all destinations with tracking enabled
        await task_instance.log_info(task_id, "Querying destinations with tracking enabled", phase="destinations")
        destinations = await Destination.filter(
            tracking=True,
            is_active=True
        ).prefetch_related('country').all()
        
        if not destinations:
            await task_instance.log_warning(task_id, "No destinations with tracking enabled found", phase="destinations")
            return {
                "success": True,
                "destinations_found": 0,
                "destinations_processed": 0,
                "hotels_discovered": 0,
                "price_records_created": 0,
                "errors": [],
                "processing_time_seconds": 0
            }
        
        await task_instance.log_info(
            task_id, 
            f"Found {len(destinations)} destinations with tracking enabled",
            phase="destinations",
            metadata={"destinations_count": len(destinations)}
        )
        
        total_hotels_discovered = 0
        total_price_records = 0
        destinations_processed = 0
        errors = []
        
        # Process each destination with detailed progress
        for i, destination in enumerate(destinations):
            try:
                # Calculate progress (20% to 85% for destination processing)
                progress = 20 + int((i / len(destinations)) * 65)
                
                await task_instance.log_phase_start(
                    task_id, 
                    "destination_processing", 
                    f"Processing destination: {destination.name} ({i+1}/{len(destinations)})"
                )
                
                await task_instance.update_task_status(
                    task_id,
                    TaskStatus.STARTED,
                    progress_current=progress,
                    progress_message=f"Processing {destination.name} ({i+1}/{len(destinations)})"
                )
                
                await task_instance.log_progress(
                    task_id,
                    f"Processing destination: {destination.name}",
                    progress,
                    "destination_processing"
                )
                
                result = await self.process_destination_tracking_with_progress(
                    destination, task_instance, task_id, i+1, len(destinations)
                )
                
                total_hotels_discovered += result['hotels_discovered']
                total_price_records += result['price_records_created']
                destinations_processed += 1
                
                await task_instance.log_phase_end(
                    task_id,
                    "destination_processing",
                    f"Completed {destination.name}: {result['hotels_discovered']} hotels, {result['price_records_created']} price records"
                )
                
                # Add delay between destinations to respect API limits
                if tracking_config.API_CALL_DELAY_SECONDS > 0:
                    await asyncio.sleep(tracking_config.API_CALL_DELAY_SECONDS)
                    
            except Exception as e:
                error_msg = f"Error processing {destination.name}: {str(e)}"
                await task_instance.log_error(
                    task_id, 
                    error_msg, 
                    phase="destination_processing",
                    metadata={"destination": destination.name}
                )
                errors.append({
                    "destination": destination.name,
                    "error": str(e)
                })
        
        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds()
        
        await task_instance.log_info(
            task_id,
            f"Tracking scan completed: {destinations_processed} destinations processed, {total_hotels_discovered} hotels discovered, {total_price_records} price records created",
            phase="summary",
            metadata={
                "destinations_processed": destinations_processed,
                "hotels_discovered": total_hotels_discovered,
                "price_records_created": total_price_records,
                "processing_time_seconds": processing_time,
                "errors_count": len(errors)
            }
        )
        
        return {
            "success": len(errors) == 0,
            "destinations_found": len(destinations),
            "destinations_processed": destinations_processed,
            "hotels_discovered": total_hotels_discovered,
            "price_records_created": total_price_records,
            "errors": errors,
            "processing_time_seconds": processing_time,
            "completed_at": end_time.isoformat()
        }
    
    async def process_destination_tracking(self, destination: Destination) -> Dict[str, Any]:
        """
        Process hotel tracking for a single destination
        
        Args:
            destination: Destination to process
            
        Returns:
            Summary of destination processing
        """
        tracking_days = get_tracking_days(destination.numberofdaystotrack)
        start_date = datetime.now().date()
        
        hotels_discovered = 0
        price_records_created = 0
        
        logger.info(
            f"Processing {destination.name} for {tracking_days} days "
            f"starting from {start_date}"
        )
        
        # Process each day in the tracking period
        for day_offset in range(tracking_days):
            checkin_date = start_date + timedelta(days=day_offset)
            checkout_date = checkin_date + timedelta(days=tracking_config.DEFAULT_STAY_DURATION_DAYS)
            
            try:
                # Search hotels for this date range
                day_result = await self.search_and_update_hotels(
                    destination, checkin_date, checkout_date, area=None
                )
                
                hotels_discovered += day_result['hotels_processed']
                price_records_created += day_result['price_records_created']
                
                if tracking_config.ENABLE_DETAILED_LOGGING and day_offset % tracking_config.LOG_PROGRESS_EVERY == 0:
                    logger.info(
                        f"{destination.name} - Day {day_offset + 1}/{tracking_days}: "
                        f"{day_result['hotels_processed']} hotels processed"
                    )
                
                # Small delay between searches
                if tracking_config.API_CALL_DELAY_SECONDS > 0:
                    await asyncio.sleep(tracking_config.API_CALL_DELAY_SECONDS / 2)
                    
            except Exception as e:
                logger.error(
                    f"Error processing {destination.name} for {checkin_date}: {str(e)}"
                )
                continue
        
        return {
            "destination_name": destination.name,
            "tracking_days": tracking_days,
            "hotels_discovered": hotels_discovered,
            "price_records_created": price_records_created,
            "success": True
        }
    
    async def process_destination_tracking_with_progress(
        self, 
        destination: Destination, 
        task_instance, 
        task_id: str,
        destination_index: int,
        total_destinations: int
    ) -> Dict[str, Any]:
        """
        Process hotel tracking for a single destination with detailed progress updates
        
        Args:
            destination: Destination to process
            task_instance: BaseTask instance for logging progress
            task_id: Task ID for progress tracking
            destination_index: Current destination index (1-based)
            total_destinations: Total number of destinations
            
        Returns:
            Summary of destination processing
        """
        # Check if destination has areas with tracking enabled
        areas_with_tracking = await Area.filter(
            destination_id=destination.id,
            tracking=True,
            is_active=True
        ).all()
        
        tracking_days = get_tracking_days(destination.numberofdaystotrack)
        start_date = datetime.now().date()
        
        hotels_discovered = 0
        price_records_created = 0
        
        # Determine search strategy
        if areas_with_tracking:
            await task_instance.log_info(
                task_id,
                f"Processing {destination.name} with {len(areas_with_tracking)} tracking areas for {tracking_days} days starting from {start_date}",
                phase="destination_processing",
                metadata={
                    "destination": destination.name,
                    "areas_count": len(areas_with_tracking),
                    "areas": [area.name for area in areas_with_tracking],
                    "tracking_days": tracking_days,
                    "start_date": start_date.isoformat(),
                    "destination_index": destination_index,
                    "total_destinations": total_destinations
                }
            )
        else:
            await task_instance.log_info(
                task_id,
                f"Processing {destination.name} (no areas) for {tracking_days} days starting from {start_date}",
                phase="destination_processing",
                metadata={
                    "destination": destination.name,
                    "tracking_days": tracking_days,
                    "start_date": start_date.isoformat(),
                    "destination_index": destination_index,
                    "total_destinations": total_destinations
                }
            )
        
        # Process each day in the tracking period
        for day_offset in range(tracking_days):
            checkin_date = start_date + timedelta(days=day_offset)
            checkout_date = checkin_date + timedelta(days=tracking_config.DEFAULT_STAY_DURATION_DAYS)
            
            try:
                if areas_with_tracking:
                    # Area-based search: Search each area separately
                    await task_instance.log_phase_start(
                        task_id,
                        "day_processing",
                        f"Processing {destination.name} areas - Day {day_offset + 1}/{tracking_days} ({checkin_date})"
                    )
                    
                    for area in areas_with_tracking:
                        await task_instance.log_info(
                            task_id,
                            f"Searching hotels in {area.name}, {destination.name}",
                            phase="area_processing",
                            metadata={"area": area.name, "destination": destination.name}
                        )
                        
                        # Search hotels for this area and date range
                        area_result = await self.search_and_update_hotels_with_progress(
                            destination, checkin_date, checkout_date, task_instance, task_id,
                            day_offset + 1, tracking_days, area=area
                        )
                        
                        hotels_discovered += area_result['hotels_processed']
                        price_records_created += area_result['price_records_created']
                        
                        await task_instance.log_info(
                            task_id,
                            f"{area.name} area - Day {day_offset + 1}: {area_result['hotels_processed']} hotels, {area_result['price_records_created']} price records",
                            phase="area_processing"
                        )
                        
                        # Small delay between area searches
                        if tracking_config.API_CALL_DELAY_SECONDS > 0:
                            await asyncio.sleep(tracking_config.API_CALL_DELAY_SECONDS / 4)
                else:
                    # Destination-based search: Search destination directly
                    await task_instance.log_phase_start(
                        task_id,
                        "day_processing",
                        f"Processing {destination.name} - Day {day_offset + 1}/{tracking_days} ({checkin_date})"
                    )
                    
                    # Search hotels for this destination and date range
                    day_result = await self.search_and_update_hotels_with_progress(
                        destination, checkin_date, checkout_date, task_instance, task_id,
                        day_offset + 1, tracking_days
                    )
                    
                    hotels_discovered += day_result['hotels_processed']
                    price_records_created += day_result['price_records_created']
                    
                    await task_instance.log_info(
                        task_id,
                        f"{destination.name} - Day {day_offset + 1}/{tracking_days}: {day_result['hotels_processed']} hotels processed, {day_result['price_records_created']} price records created",
                        phase="day_processing",
                        metadata={
                            "destination": destination.name,
                            "day": day_offset + 1,
                            "total_days": tracking_days,
                            "checkin_date": checkin_date.isoformat(),
                            "hotels_processed": day_result['hotels_processed'],
                            "price_records_created": day_result['price_records_created']
                        }
                    )
                
                await task_instance.log_phase_end(
                    task_id,
                    "day_processing",
                    f"Completed Day {day_offset + 1}/{tracking_days} for {destination.name}"
                )
                
                # Small delay between searches
                if tracking_config.API_CALL_DELAY_SECONDS > 0:
                    await asyncio.sleep(tracking_config.API_CALL_DELAY_SECONDS / 2)
                    
            except Exception as e:
                await task_instance.log_error(
                    task_id,
                    f"Error processing {destination.name} for {checkin_date}: {str(e)}",
                    phase="day_processing",
                    metadata={
                        "destination": destination.name,
                        "checkin_date": checkin_date.isoformat(),
                        "day": day_offset + 1
                    }
                )
                continue
        
        await task_instance.log_info(
            task_id,
            f"Destination {destination.name} completed: {hotels_discovered} hotels discovered, {price_records_created} price records created",
            phase="destination_processing",
            metadata={
                "destination": destination.name,
                "hotels_discovered": hotels_discovered,
                "price_records_created": price_records_created,
                "tracking_days": tracking_days
            }
        )
        
        return {
            "destination_name": destination.name,
            "tracking_days": tracking_days,
            "hotels_discovered": hotels_discovered,
            "price_records_created": price_records_created,
            "success": True
        }
    
    async def search_and_update_hotels(
        self, 
        destination: Destination, 
        checkin_date: date, 
        checkout_date: date,
        area: Area = None
    ) -> Dict[str, Any]:
        """
        Search hotels for a specific date range and update database
        
        Args:
            destination: Destination to search in
            checkin_date: Check-in date
            checkout_date: Check-out date
            area: Optional area for more specific search
            
        Returns:
            Summary of search and update operation
        """
        # Build search criteria
        search_defaults = get_search_criteria_defaults()
        criteria = SearchCriteria(
            query=f"{destination.name}, {destination.country.name}",
            check_in_date=checkin_date,
            check_out_date=checkout_date,
            **search_defaults
        )
        
        # Perform search with pagination to get more hotels
        search_responses = await self.serp_service.search_with_pagination(
            criteria, 
            max_pages=tracking_config.MAX_PAGES_PER_SEARCH
        )
        
        if not search_responses:
            logger.warning(f"No search results for {destination.name} on {checkin_date}")
            return {
                "hotels_processed": 0,
                "price_records_created": 0,
                "search_date": checkin_date,
                "total_results": 0
            }
        
        # Combine all properties from all pages
        all_properties = []
        for page_num, response in enumerate(search_responses, 1):
            page_properties = len(response.properties)
            all_properties.extend(response.properties)
            logger.info(f"📄 Page {page_num}: Found {page_properties} hotels for {destination.name}")
        
        logger.info(f"🏨 Total hotels found across {len(search_responses)} pages: {len(all_properties)} for {destination.name}")
        
        # Create a combined response object for compatibility
        search_response = search_responses[0]
        search_response.properties = all_properties
        
        hotels_processed = 0
        price_records_created = 0
        
        # Process each property result (all hotels from pagination)
        for property_result in search_response.properties:
            try:
                # Handle hotels with missing star rating data
                # Since SerpAPI hotel_class filter ensures only 4-5 star hotels are returned,
                # hotels with missing extracted_hotel_class are still valid
                star_rating = self._extract_hotel_star_rating(property_result)
                if star_rating is None:
                    logger.debug(f"Skipping {property_result.name} - unable to determine star rating")
                    continue
                
                # Create or update hotel
                hotel = await self.create_or_update_hotel(property_result, destination, area)
                hotels_processed += 1
                
                # Create price history record
                price_created = await self.create_price_history_record(
                    hotel, property_result, criteria, checkin_date
                )
                
                if price_created:
                    price_records_created += 1
                else:
                    logger.warning(f"⚠️ Price record NOT created for {hotel.name} on {checkin_date}")
                    
            except Exception as e:
                logger.error(f"❌ CRITICAL ERROR processing hotel {property_result.name} on {checkin_date}: {str(e)}")
                logger.error(f"Exception type: {type(e).__name__}")
                continue
        
        return {
            "hotels_processed": hotels_processed,
            "price_records_created": price_records_created,
            "search_date": checkin_date,
            "total_results": len(search_response.properties)
        }
    
    async def search_and_update_hotels_with_progress(
        self, 
        destination: Destination, 
        checkin_date: date, 
        checkout_date: date,
        task_instance,
        task_id: str,
        day_number: int,
        total_days: int,
        area: Area = None
    ) -> Dict[str, Any]:
        """
        Search hotels for a specific date range and update database with detailed progress updates
        
        Args:
            destination: Destination to search in
            checkin_date: Check-in date
            checkout_date: Check-out date
            task_instance: BaseTask instance for logging progress
            task_id: Task ID for progress tracking
            day_number: Current day number (1-based)
            total_days: Total number of days being processed
            area: Optional area for more specific search (if None, searches destination)
            
        Returns:
            Summary of search and update operation
        """
        # Build search criteria with area-aware query
        search_defaults = get_search_criteria_defaults()
        
        if area:
            # Area-based search: "Area, Destination, Country"
            search_query = f"{area.name}, {destination.name}, {destination.country.name}"
            search_location = f"{area.name} area"
        else:
            # Destination-based search: "Destination, Country"
            search_query = f"{destination.name}, {destination.country.name}"
            search_location = destination.name
        
        criteria = SearchCriteria(
            query=search_query,
            check_in_date=checkin_date,
            check_out_date=checkout_date,
            **search_defaults
        )
        
        await task_instance.log_info(
            task_id,
            f"Starting hotel search for {search_location} on {checkin_date} (query: {search_query})",
            phase="hotel_search",
            metadata={
                "destination": destination.name,
                "area": area.name if area else None,
                "search_query": search_query,
                "checkin_date": checkin_date.isoformat(),
                "checkout_date": checkout_date.isoformat(),
                "day_number": day_number,
                "total_days": total_days
            }
        )
        
        # Perform search with pagination to get more hotels
        search_responses = await self.serp_service.search_with_pagination(
            criteria, 
            max_pages=tracking_config.MAX_PAGES_PER_SEARCH
        )
        
        if not search_responses:
            await task_instance.log_warning(
                task_id,
                f"No search results for {search_location} on {checkin_date}",
                phase="hotel_search",
                metadata={
                    "destination": destination.name,
                    "area": area.name if area else None,
                    "search_query": search_query,
                    "checkin_date": checkin_date.isoformat()
                }
            )
            return {
                "hotels_processed": 0,
                "price_records_created": 0,
                "search_date": checkin_date,
                "total_results": 0
            }
        
        # Combine all properties from all pages
        all_properties = []
        for page_num, response in enumerate(search_responses, 1):
            page_properties = len(response.properties)
            all_properties.extend(response.properties)
            
            await task_instance.log_info(
                task_id,
                f"Page {page_num}: Found {page_properties} hotels for {destination.name}",
                phase="hotel_search",
                metadata={
                    "destination": destination.name,
                    "page_number": page_num,
                    "hotels_found": page_properties,
                    "checkin_date": checkin_date.isoformat()
                }
            )
        
        await task_instance.log_info(
            task_id,
            f"Total hotels found across {len(search_responses)} pages: {len(all_properties)} for {destination.name}",
            phase="hotel_search",
            metadata={
                "destination": destination.name,
                "total_pages": len(search_responses),
                "total_hotels": len(all_properties),
                "checkin_date": checkin_date.isoformat()
            }
        )
        
        # Create a combined response object for compatibility
        search_response = search_responses[0]
        search_response.properties = all_properties
        
        hotels_processed = 0
        price_records_created = 0
        
        await task_instance.log_phase_start(
            task_id,
            "hotel_processing",
            f"Processing {len(all_properties)} hotels for {destination.name}"
        )
        
        # Process each property result (all hotels from pagination)
        for i, property_result in enumerate(search_response.properties):
            try:
                # Handle hotels with missing star rating data
                # Since SerpAPI hotel_class filter ensures only 4-5 star hotels are returned,
                # hotels with missing extracted_hotel_class are still valid
                star_rating = self._extract_hotel_star_rating(property_result)
                if star_rating is None:
                    await task_instance.log_debug(
                        task_id,
                        f"Skipping {property_result.name} - unable to determine star rating",
                        phase="hotel_processing",
                        metadata={"hotel_name": property_result.name}
                    )
                    continue
                
                # Create or update hotel
                hotel = await self.create_or_update_hotel(property_result, destination, area)
                hotels_processed += 1
                
                # Create price history record
                price_created = await self.create_price_history_record(
                    hotel, property_result, criteria, checkin_date
                )
                
                if price_created:
                    price_records_created += 1
                    # Extract price info for logging
                    price_info = self._extract_price_info(property_result)
                    await task_instance.log_debug(
                        task_id,
                        f"✅ Updated price record for {hotel.name} on {checkin_date}: {price_info['price']} {price_info['currency']}",
                        phase="hotel_processing",
                        metadata={
                            "hotel_name": hotel.name,
                            "price": str(price_info['price']),
                            "currency": price_info['currency'],
                            "checkin_date": checkin_date.isoformat()
                        }
                    )
                else:
                    await task_instance.log_warning(
                        task_id,
                        f"⚠️ Price record NOT created for {hotel.name} on {checkin_date}",
                        phase="hotel_processing",
                        metadata={"hotel_name": hotel.name, "checkin_date": checkin_date.isoformat()}
                    )
                    
            except Exception as e:
                await task_instance.log_error(
                    task_id,
                    f"❌ CRITICAL ERROR processing hotel {property_result.name} on {checkin_date}: {str(e)}",
                    phase="hotel_processing",
                    metadata={
                        "hotel_name": property_result.name,
                        "checkin_date": checkin_date.isoformat(),
                        "error_type": type(e).__name__
                    }
                )
                continue
        
        await task_instance.log_phase_end(
            task_id,
            "hotel_processing",
            f"Completed processing hotels for {destination.name}: {hotels_processed} hotels, {price_records_created} price records"
        )
        
        return {
            "hotels_processed": hotels_processed,
            "price_records_created": price_records_created,
            "search_date": checkin_date,
            "total_results": len(search_response.properties)
        }
    
    async def create_or_update_hotel(
        self, 
        property_result: PropertyResult, 
        destination: Destination,
        area: Area = None
    ) -> Hotel:
        """
        Create or update hotel record from PropertyResult
        
        Args:
            property_result: Hotel data from SerpApi
            destination: Destination the hotel belongs to
            area: Optional area the hotel belongs to
            
        Returns:
            Hotel instance
        """
        # Generate external_id from property_token or name
        external_id = property_result.property_token or f"serp_{hash(property_result.name)}_{destination.id}"
        
        # Try to find existing hotel with relations prefetched
        hotel = await Hotel.get_or_none(external_id=external_id).prefetch_related('country', 'destination')
        
        # Prepare hotel data
        hotel_data = {
            "external_id": external_id,
            "partner_name": tracking_config.PARTNER_NAME,
            "name": property_result.name,
            "display_name": property_result.name,
            "brand_name": None,  # SerpAPI doesn't provide brand info
            "description": property_result.description,
            "short_description": property_result.description[:500] if property_result.description else None,
            "country": destination.country,
            "destination": destination,
            "area": area,
            "hotel_type": HotelType.HOTEL,
            "hotel_chain": HotelChain.INDEPENDENT,
            "star_rating": self._extract_hotel_star_rating(property_result),
            "official_rating": property_result.hotel_class,  # "5-star hotel", "4-star hotel", etc.
            "guest_rating": property_result.overall_rating,
            "guest_rating_count": property_result.reviews or 0,
            "latitude": property_result.gps_coordinates.latitude if property_result.gps_coordinates else None,
            "longitude": property_result.gps_coordinates.longitude if property_result.gps_coordinates else None,
            "postal_code": None,  # SerpAPI doesn't provide postal codes
            "check_in_time": property_result.check_in_time,
            "check_out_time": property_result.check_out_time,
            "amenities": property_result.amenities,
            "images": [{"thumbnail": img.thumbnail, "original": img.original_image} for img in property_result.images],
            "is_active": True,
            "is_bookable": True,
            "currency": tracking_config.DEFAULT_CURRENCY,
            "api_last_updated": datetime.utcnow(),
            "api_data": json.loads(property_result.model_dump_json()),
            "address": f"{destination.name}, {destination.country.name}",  # Basic address
            "city": destination.name,
        }
        
        async with in_transaction():
            if hotel:
                # Update existing hotel
                for key, value in hotel_data.items():
                    if key not in ['country', 'destination']:  # Skip relations for update
                        setattr(hotel, key, value)
                await hotel.save()
                
                logger.info(f"🔄 Updated existing hotel: {hotel.name}")
            else:
                # Create new hotel
                hotel = await Hotel.create(**hotel_data)
                
                logger.info(f"🏨 Created NEW hotel: {hotel.name}")
        
        return hotel
    
    async def create_price_history_record(
        self,
        hotel: Hotel,
        property_result: PropertyResult,
        criteria: SearchCriteria,
        checkin_date: date
    ) -> bool:
        """
        Create or update price history record
        
        Args:
            hotel: Hotel instance
            property_result: Property data from SerpApi
            criteria: Search criteria used
            checkin_date: Check-in date for the search
            
        Returns:
            True if record was created/updated, False otherwise
        """
        # Extract price information
        price = None
        price_source = None
        
        if property_result.rate_per_night and property_result.rate_per_night.extracted_lowest:
            price = Decimal(str(property_result.rate_per_night.extracted_lowest))
            price_source = "rate_per_night"
        elif property_result.total_rate and property_result.total_rate.extracted_lowest:
            price = Decimal(str(property_result.total_rate.extracted_lowest))
            price_source = "total_rate"
        elif property_result.prices and len(property_result.prices) > 0:
            # Try to get price from first price source
            first_price = property_result.prices[0]
            if first_price.rate_per_night and first_price.rate_per_night.extracted_lowest:
                price = Decimal(str(first_price.rate_per_night.extracted_lowest))
                price_source = f"price_source_{first_price.source}"
        
        if price is None:
            logger.warning(f"No price found for hotel {hotel.name} on {checkin_date}")
            if tracking_config.ENABLE_DETAILED_LOGGING:
                logger.debug(f"Price debug for {hotel.name}: rate_per_night={property_result.rate_per_night}, total_rate={property_result.total_rate}, prices_count={len(property_result.prices) if property_result.prices else 0}")
            return False
        
        logger.info(f"Found price for {hotel.name}: {price} {tracking_config.DEFAULT_CURRENCY} (source: {price_source})")
        
        # Check for existing record - each day should be a separate record
        # The key is: hotel + price_date (TODAY) + search criteria (travel dates)
        today = datetime.utcnow().date()
        existing_record = await UniversalPriceHistory.get_or_none(
            trackable_type=TrackableType.HOTEL_ROOM,
            trackable_id=hotel.id,
            price_date=today,  # When we searched (today)
            search_date=checkin_date,  # Travel check-in date
            search_end_date=criteria.check_out_date,  # Travel check-out date
            data_source=tracking_config.DATA_SOURCE_NAME
        )
        
        # Get the actual country and destination IDs safely
        # For existing hotels, we need to handle QuerySet relations properly
        country_id = None
        destination_id = None
        
        try:
            # Try to get the country ID
            if hasattr(hotel.country, 'id'):
                country_id = hotel.country.id
            else:
                # If it's a QuerySet, get the first item
                country = await hotel.country.first() if hasattr(hotel.country, 'first') else hotel.country
                country_id = country.id if country else None
        except Exception as e:
            logger.warning(f"Could not get country ID for hotel {hotel.name}: {e}")
            country_id = destination.country.id  # Fallback to destination's country
            
        try:
            # Try to get the destination ID
            if hasattr(hotel.destination, 'id'):
                destination_id = hotel.destination.id
            else:
                # If it's a QuerySet, get the first item
                dest = await hotel.destination.first() if hasattr(hotel.destination, 'first') else hotel.destination
                destination_id = dest.id if dest else None
        except Exception as e:
            logger.warning(f"Could not get destination ID for hotel {hotel.name}: {e}")
            destination_id = destination.id  # Fallback to current destination

        # Prepare price history data
        price_data = {
            "trackable_type": TrackableType.HOTEL_ROOM,
            "trackable_id": hotel.id,
            "price_date": today,  # When we searched (today)
            "search_date": checkin_date,  # Travel check-in date
            "search_end_date": criteria.check_out_date,  # Travel check-out date
            "price": price,
            "currency": tracking_config.DEFAULT_CURRENCY,
            "is_available": True,
            "search_criteria": {
                "query": criteria.query,
                "check_in_date": criteria.check_in_date.isoformat(),
                "check_out_date": criteria.check_out_date.isoformat(),
                "adults": criteria.adults,
                "children": criteria.children,
                "currency": criteria.currency,
                "gl": criteria.gl,
                "hl": criteria.hl,
            },
            "data_source": tracking_config.DATA_SOURCE_NAME,
            "destination_country_id": country_id,
            "destination_destination_id": destination_id,
            "raw_api_response": json.loads(property_result.model_dump_json()),
        }
        
        # Calculate price changes if updating
        if existing_record:
            old_price = existing_record.price
            price_change = price - old_price
            price_change_percent = float((price_change / old_price) * 100) if old_price > 0 else 0
            
            price_data.update({
                "previous_price": old_price,
                "price_change_amount": price_change,
                "price_change_percent": price_change_percent,
                "is_price_drop": price_change < 0,
                "is_price_increase": price_change > 0,
            })
        
        try:
            async with in_transaction():
                if existing_record and tracking_config.UPDATE_SAME_DAY_PRICES:
                    # Update existing record (same day, different time)
                    for key, value in price_data.items():
                        if key not in ['destination_country_id', 'destination_destination_id']:  # Skip relations
                            setattr(existing_record, key, value)
                    await existing_record.save()
                    
                    logger.info(f"✅ Updated price record for {hotel.name} on {checkin_date}: {price} INR")
                        
                elif not existing_record:
                    # Create new record - this should happen for each unique day
                    await UniversalPriceHistory.create(**price_data)
                    
                    logger.info(f"✅ Created NEW price record for {hotel.name} on {checkin_date}: {price} INR")
                else:
                    # Existing record found but UPDATE_SAME_DAY_PRICES is False
                    logger.info(f"⚠️ Skipped existing price record for {hotel.name} on {checkin_date} (update disabled)")
                    return False
            
            return True
            
        except Exception as db_error:
            logger.error(f"❌ CRITICAL: Failed to save price record for {hotel.name} on {checkin_date}: {str(db_error)}")
            logger.error(f"Price data: {price_data}")
            # Don't re-raise - continue processing other hotels
            return False
    
    def _extract_hotel_star_rating(self, property_result: PropertyResult) -> Optional[int]:
        """
        Extract hotel star rating from property result.
        
        Tries multiple sources:
        1. extracted_hotel_class (preferred)
        2. hotel_class string parsing (e.g., "4-star hotel" -> 4)
        3. STRICT: Return None if no clear 4-5 star rating found
        
        Args:
            property_result: SerpAPI property result
            
        Returns:
            Star rating (4 or 5) or None if unable to determine or not 4-5 star
        """
        # Try extracted_hotel_class first (most reliable)
        if property_result.extracted_hotel_class is not None:
            if property_result.extracted_hotel_class in [4, 5]:
                return property_result.extracted_hotel_class
            else:
                logger.debug(f"Rejecting {property_result.name} - extracted rating {property_result.extracted_hotel_class} is not 4-5 star")
                return None
        
        # Try to parse from hotel_class string
        if property_result.hotel_class:
            import re
            # Look for patterns like "4-star hotel", "5 star", etc.
            match = re.search(r'(\d+)[-\s]*star', property_result.hotel_class.lower())
            if match:
                rating = int(match.group(1))
                if rating in [4, 5]:  # Only accept 4-5 star
                    return rating
                else:
                    logger.debug(f"Rejecting {property_result.name} - parsed rating {rating} is not 4-5 star")
                    return None
        
        # STRICT FILTERING: Reject hotels without clear 4-5 star rating
        # Don't assume SerpAPI filters are working correctly
        logger.debug(f"Rejecting {property_result.name} - no clear 4-5 star rating found (hotel_class: {property_result.hotel_class})")
        return None

    async def get_tracking_summary(self) -> Dict[str, Any]:
        """
        Get summary of current tracking configuration and status
        
        Returns:
            Summary of tracking setup
        """
        # Get destinations with tracking enabled
        destinations = await Destination.filter(
            tracking=True,
            is_active=True
        ).prefetch_related('country').all()
        
        # Get recent price history stats
        recent_prices = await UniversalPriceHistory.filter(
            recorded_at__gte=datetime.utcnow() - timedelta(days=1),
            data_source=tracking_config.DATA_SOURCE_NAME
        ).count()
        
        # Get total hotels tracked
        hotels_tracked = await Hotel.filter(
            partner_name=tracking_config.PARTNER_NAME,
            is_active=True
        ).count()
        
        return {
            "tracking_enabled_destinations": len(destinations),
            "destinations": [
                {
                    "name": dest.name,
                    "country": dest.country.name,
                    "tracking_days": dest.numberofdaystotrack
                }
                for dest in destinations
            ],
            "configuration": {
                "start_from_today": tracking_config.START_FROM_TODAY,
                "stay_duration_days": tracking_config.DEFAULT_STAY_DURATION_DAYS,
                "hotel_class_filter": [hc.value for hc in tracking_config.HOTEL_CLASS_FILTER],
                "default_adults": tracking_config.DEFAULT_ADULTS,
                "max_hotels_per_destination": tracking_config.MAX_HOTELS_PER_DESTINATION,
            },
            "statistics": {
                "hotels_tracked": hotels_tracked,
                "price_records_last_24h": recent_prices,
            }
        }
    
    def _extract_price_info(self, property_result: PropertyResult) -> Dict[str, str]:
        """
        Extract price and currency information from PropertyResult for logging
        
        Args:
            property_result: Property data from SerpApi
            
        Returns:
            Dict with 'price' and 'currency' keys
        """
        if property_result.rate_per_night and property_result.rate_per_night.extracted_lowest:
            price = property_result.rate_per_night.extracted_lowest
            return {"price": str(price), "currency": tracking_config.DEFAULT_CURRENCY}
        elif property_result.total_rate and property_result.total_rate.extracted_lowest:
            price = property_result.total_rate.extracted_lowest
            return {"price": str(price), "currency": tracking_config.DEFAULT_CURRENCY}
        elif property_result.prices and len(property_result.prices) > 0:
            first_price = property_result.prices[0]
            if first_price.rate_per_night and first_price.rate_per_night.extracted_lowest:
                price = first_price.rate_per_night.extracted_lowest
                return {"price": str(price), "currency": tracking_config.DEFAULT_CURRENCY}
        
        # Fallback if no price found
        return {"price": "N/A", "currency": tracking_config.DEFAULT_CURRENCY}


# Factory function for dependency injection
async def get_hotel_tracking_service() -> HotelTrackingService:
    """Get configured hotel tracking service instance"""
    return HotelTrackingService()