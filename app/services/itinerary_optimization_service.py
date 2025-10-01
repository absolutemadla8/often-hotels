"""
Itinerary Optimization Service

Main orchestration service for multi-destination itinerary optimization.
Handles different search modes (normal, ranges, fixed_dates, all) and
coordinates date window calculation with hotel cost optimization.
"""

import asyncio
import hashlib
import json
import logging
import time
from datetime import date
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal

from app.models.models import (
    Itinerary, ItineraryDestination, ItineraryHotelAssignment, 
    ItinerarySearchRequest, SearchType, ItineraryStatus, User
)
from app.schemas.itinerary import (
    ItineraryOptimizationRequest, ItineraryOptimizationResponse,
    ItineraryResponse, DestinationResponse, HotelAssignmentResponse,
    NormalSearchResults, RangesSearchResults, FixedDatesSearchResults,
    OptimizationMetadata, ItineraryErrorResponse, ItineraryError
)
from app.services.date_window_service import (
    DateWindowService, ConsecutiveAssignment, get_date_window_service
)
from app.services.hotel_pricing_service import (
    HotelPricingService, DestinationHotelSolution, get_hotel_pricing_service
)
from app.services.cache_service import get_cache_service

logger = logging.getLogger(__name__)


class ItineraryOptimizationService:
    """Main service for itinerary optimization across multiple search modes"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._date_service: Optional[DateWindowService] = None
        self._pricing_service: Optional[HotelPricingService] = None
        self._cache_service = None
    
    async def _get_services(self):
        """Initialize required services lazily"""
        if not self._date_service:
            self._date_service = await get_date_window_service()
        if not self._pricing_service:
            self._pricing_service = await get_hotel_pricing_service()
        if not self._cache_service:
            self._cache_service = await get_cache_service()
    
    def _generate_request_hash(self, request: ItineraryOptimizationRequest) -> str:
        """Generate a consistent hash for the optimization request"""
        # Create normalized request dict for hashing
        request_dict = {
            "custom": request.custom,
            "search_types": sorted(request.search_types),
            "destinations": [
                {
                    "destination_id": dest.destination_id,
                    "area_id": dest.area_id,
                    "nights": dest.nights
                }
                for dest in request.destinations
            ],
            "global_date_range": {
                "start": request.global_date_range.start.isoformat(),
                "end": request.global_date_range.end.isoformat()
            },
            "ranges": [
                {"start": r.start.isoformat(), "end": r.end.isoformat()}
                for r in (request.ranges or [])
            ],
            "fixed_dates": [d.isoformat() for d in (request.fixed_dates or [])],
            "guests": request.guests.model_dump(),
            "currency": request.currency,
            "top_k": request.top_k,
            "preferred_hotels": sorted(request.preferred_hotels or []),
            "hotel_change": request.hotel_change
        }
        
        request_json = json.dumps(request_dict, sort_keys=True)
        return hashlib.sha256(request_json.encode()).hexdigest()
    
    async def optimize_itinerary(
        self,
        request: ItineraryOptimizationRequest,
        user: Optional[User] = None
    ) -> ItineraryOptimizationResponse:
        """
        Main entry point for itinerary optimization.
        
        Args:
            request: Optimization request with all parameters
            user: Optional user for personalization and caching
            
        Returns:
            Complete optimization response with all requested search types
        """
        start_time = time.time()
        request_hash = self._generate_request_hash(request)
        
        await self._get_services()
        
        try:
            # Check cache first if enabled
            cached_result = None
            if request.use_cache:
                cached_result = await self._get_cached_result(request_hash)
                if cached_result:
                    self.logger.info(f"Cache hit for request {request_hash[:8]}")
                    return cached_result
            
            # Validate request constraints
            validation_result = self._date_service.validate_date_constraints(
                request.global_date_range, request.destinations
            )
            
            if not validation_result["valid"]:
                return self._create_error_response(
                    request_hash, validation_result["errors"]
                )
            
            # Route to appropriate optimization method
            if not request.custom:
                # Simple normal search only
                result = await self._optimize_normal_only(request, request_hash, user)
            else:
                # Multi-mode custom search
                result = await self._optimize_custom_search(request, request_hash, user)
            
            # Add processing time
            processing_time_ms = int((time.time() - start_time) * 1000)
            result.metadata.processing_time_ms = processing_time_ms
            
            # Cache result if enabled
            if request.use_cache and result.success:
                await self._cache_result(request_hash, result)
            
            # Log successful optimization
            total_itineraries = 0
            
            # Count normal search results
            if hasattr(result, 'normal') and result.normal and result.normal.monthly_options:
                for month_option in result.normal.monthly_options:
                    if month_option.start_month:
                        total_itineraries += 1
                    if month_option.mid_month:
                        total_itineraries += 1
                    if month_option.end_month:
                        total_itineraries += 1
            
            # Count ranges search results
            if hasattr(result, 'ranges') and result.ranges and result.ranges.results:
                total_itineraries += len(result.ranges.results)
            
            # Count fixed_dates search results
            if hasattr(result, 'fixed_dates') and result.fixed_dates and result.fixed_dates.results:
                total_itineraries += len(result.fixed_dates.results)
            
            self.logger.info(
                f"Optimization complete: {total_itineraries} itineraries in {processing_time_ms}ms"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Optimization failed: {str(e)}", exc_info=True)
            return self._create_error_response(
                request_hash, [f"Optimization failed: {str(e)}"]
            )
    
    async def _optimize_normal_only(
        self,
        request: ItineraryOptimizationRequest,
        request_hash: str,
        user: Optional[User] = None
    ) -> ItineraryOptimizationResponse:
        """Optimize using normal search mode only"""
        
        normal_results = await self._execute_normal_search(request)
        
        # Find best overall itinerary from monthly options
        all_options = []
        for month_option in normal_results.monthly_options:
            if month_option.start_month:
                all_options.append(month_option.start_month)
            if month_option.mid_month:
                all_options.append(month_option.mid_month)
            if month_option.end_month:
                all_options.append(month_option.end_month)
        
        best_itinerary = self._find_best_itinerary(all_options)
        
        metadata = OptimizationMetadata(
            processing_time_ms=0,  # Will be updated by caller
            cache_hit=False,
            hotels_searched=0,  # TODO: Track this
            price_queries=0,     # TODO: Track this
            alternatives_generated=sum([
                r.alternatives_generated for r in all_options if r
            ]),
            best_cost_found=best_itinerary.total_cost if best_itinerary else None
        )
        
        return ItineraryOptimizationResponse(
            success=True,
            request_hash=request_hash,
            normal=normal_results,
            best_itinerary=best_itinerary,
            metadata=metadata,
            filters_applied={
                "search_types": ["normal"],
                "custom": False,
                "currency": request.currency,
                "guests": request.guests.model_dump()
            },
            message=f"Found {len(all_options)} itinerary options across {len(normal_results.monthly_options)} months"
        )
    
    async def _optimize_custom_search(
        self,
        request: ItineraryOptimizationRequest,
        request_hash: str,
        user: Optional[User] = None
    ) -> ItineraryOptimizationResponse:
        """Optimize using custom search modes"""
        
        results = {}
        all_itineraries = []
        
        # Execute each requested search type
        for search_type in request.search_types:
            if search_type == "normal":
                results["normal"] = await self._execute_normal_search(request)
                # Add all options from monthly_options to all_itineraries
                for month_option in results["normal"].monthly_options:
                    if month_option.start_month:
                        all_itineraries.append(month_option.start_month)
                    if month_option.mid_month:
                        all_itineraries.append(month_option.mid_month)
                    if month_option.end_month:
                        all_itineraries.append(month_option.end_month)
            
            elif search_type == "ranges":
                if request.ranges:
                    results["ranges"] = await self._execute_ranges_search(request)
                    all_itineraries.extend(results["ranges"].results)
            
            elif search_type == "fixed_dates":
                if request.fixed_dates:
                    results["fixed_dates"] = await self._execute_fixed_dates_search(request)
                    all_itineraries.extend(results["fixed_dates"].results)
            
            elif search_type == "all":
                # Execute all search types
                results["normal"] = await self._execute_normal_search(request)
                # Add all options from monthly_options to all_itineraries
                for month_option in results["normal"].monthly_options:
                    if month_option.start_month:
                        all_itineraries.append(month_option.start_month)
                    if month_option.mid_month:
                        all_itineraries.append(month_option.mid_month)
                    if month_option.end_month:
                        all_itineraries.append(month_option.end_month)
                
                # Auto-generate ranges from global_date_range if not provided
                if request.ranges:
                    results["ranges"] = await self._execute_ranges_search(request)
                    all_itineraries.extend(results["ranges"].results)
                else:
                    # Generate default ranges from global date range
                    auto_ranges = self._generate_default_ranges(request.global_date_range)
                    if auto_ranges:
                        temp_request = request.model_copy()
                        temp_request.ranges = auto_ranges
                        results["ranges"] = await self._execute_ranges_search(temp_request)
                        all_itineraries.extend(results["ranges"].results)
                
                if request.fixed_dates:
                    results["fixed_dates"] = await self._execute_fixed_dates_search(request)
                    all_itineraries.extend(results["fixed_dates"].results)
        
        # Find best overall itinerary
        valid_itineraries = [i for i in all_itineraries if i is not None]
        best_itinerary = self._find_best_itinerary(valid_itineraries)
        
        # Calculate metadata
        total_alternatives = sum([
            r.alternatives_generated for r in valid_itineraries
        ])
        
        metadata = OptimizationMetadata(
            processing_time_ms=0,  # Will be updated by caller
            cache_hit=False,
            hotels_searched=0,  # TODO: Track this
            price_queries=0,     # TODO: Track this
            alternatives_generated=total_alternatives,
            best_cost_found=best_itinerary.total_cost if best_itinerary else None
        )
        
        return ItineraryOptimizationResponse(
            success=True,
            request_hash=request_hash,
            normal=results.get("normal"),
            ranges=results.get("ranges"),
            fixed_dates=results.get("fixed_dates"),
            best_itinerary=best_itinerary,
            metadata=metadata,
            filters_applied={
                "search_types": request.search_types,
                "custom": request.custom,
                "currency": request.currency,
                "guests": request.guests.model_dump()
            },
            message=f"Found {len(valid_itineraries)} total itinerary options across {len(request.search_types)} search types"
        )
    
    async def _execute_normal_search(
        self, 
        request: ItineraryOptimizationRequest
    ) -> NormalSearchResults:
        """Execute normal search with month-grouped future-only results"""
        
        self.logger.info(f"🔍 NORMAL SEARCH: Starting normal search execution")
        self.logger.info(f"🔍 NORMAL SEARCH: Request destinations: {[d.model_dump() for d in request.destinations]}")
        self.logger.info(f"🔍 NORMAL SEARCH: Global date range: {request.global_date_range.model_dump()}")
        self.logger.info(f"🔍 NORMAL SEARCH: Currency: {request.currency}")
        self.logger.info(f"🔍 NORMAL SEARCH: Guests: {request.guests.model_dump()}")
        
        # Import the schema here to avoid circular imports
        from app.schemas.itinerary import MonthlyOptions
        
        # Generate month-grouped assignments
        self.logger.info(f"🔍 NORMAL SEARCH: Generating monthly slices...")
        month_groups = self._date_service.generate_monthly_slices(
            request.global_date_range, request.destinations
        )
        self.logger.info(f"🔍 NORMAL SEARCH: Generated {len(month_groups)} month groups: {[mg.get('month', 'Unknown') for mg in month_groups]}")
        
        # Process each month group
        monthly_options = []
        all_available_options = []  # Track all options for debugging
        
        for month_group in month_groups:
            month_name = month_group["month"]
            
            # Optimize each assignment in the month
            optimized_month = {
                "month": month_name,
                "start_month": None,
                "mid_month": None,
                "end_month": None
            }
            
            # Process start_month option
            if month_group["start_month"]:
                itinerary = await self._optimize_single_assignment(
                    month_group["start_month"], request, f"{month_name}_start"
                )
                if itinerary:
                    optimized_month["start_month"] = itinerary
                    all_available_options.append(itinerary)
            
            # Process mid_month option
            if month_group["mid_month"]:
                itinerary = await self._optimize_single_assignment(
                    month_group["mid_month"], request, f"{month_name}_mid"
                )
                if itinerary:
                    optimized_month["mid_month"] = itinerary
                    all_available_options.append(itinerary)
            
            # Process end_month option
            if month_group["end_month"]:
                itinerary = await self._optimize_single_assignment(
                    month_group["end_month"], request, f"{month_name}_end"
                )
                if itinerary:
                    optimized_month["end_month"] = itinerary
                    all_available_options.append(itinerary)
            
            # Only add month if it has at least one successful optimization
            if any([optimized_month["start_month"], optimized_month["mid_month"], optimized_month["end_month"]]):
                monthly_options.append(MonthlyOptions(**optimized_month))
        
        return NormalSearchResults(
            monthly_options=monthly_options
        )
    
    async def _execute_ranges_search(
        self,
        request: ItineraryOptimizationRequest
    ) -> RangesSearchResults:
        """Execute ranges search (sliding window across date ranges)"""
        
        assignments = self._date_service.generate_range_assignments(
            request.ranges, request.destinations, request.top_k
        )
        
        # Optimize each assignment
        results = []
        for assignment in assignments[:request.top_k]:
            itinerary = await self._optimize_single_assignment(
                assignment, request, "range_optimized"
            )
            if itinerary:
                results.append(itinerary)
        
        return RangesSearchResults(results=results)
    
    async def _execute_fixed_dates_search(
        self,
        request: ItineraryOptimizationRequest
    ) -> FixedDatesSearchResults:
        """Execute fixed dates search (exact start dates)"""
        
        assignments = self._date_service.generate_fixed_date_assignments(
            request.fixed_dates, request.destinations
        )
        
        # Optimize each assignment
        results = []
        for assignment in assignments:
            itinerary = await self._optimize_single_assignment(
                assignment, request, "fixed_date"
            )
            if itinerary:
                results.append(itinerary)
        
        return FixedDatesSearchResults(results=results)
    
    async def _optimize_single_assignment(
        self,
        assignment: ConsecutiveAssignment,
        request: ItineraryOptimizationRequest,
        label: str
    ) -> Optional[ItineraryResponse]:
        """Optimize a single date assignment with hotel selection"""
        
        try:
            # Convert destinations to format expected by pricing service
            destination_configs = [
                {
                    "destination_id": dest.destination_id,
                    "area_id": dest.area_id
                }
                for dest in request.destinations
            ]
            
            # Get hotel solutions for all destinations
            hotel_solutions = await self._pricing_service.optimize_complete_itinerary(
                assignment, destination_configs, request.guests, request.currency,
                request.preferred_hotels, request.hotel_change
            )
            
            if not hotel_solutions:
                self.logger.warning(f"No hotel solutions found for assignment {label}")
                return None
            
            # Check if we have solutions for all destinations
            required_destination_ids = {dest_id for dest_id, _, _ in assignment.destinations}
            found_destination_ids = set(hotel_solutions.keys())
            
            if not required_destination_ids.issubset(found_destination_ids):
                missing = required_destination_ids - found_destination_ids
                self.logger.warning(f"Missing hotel solutions for destinations: {missing}")
                return None
            
            # Convert to response format
            destination_responses = []
            
            for dest_id, start_date, end_date in assignment.destinations:
                solution = hotel_solutions[dest_id]
                
                # Find destination config for metadata
                dest_config = next(
                    (d for d in request.destinations if d.destination_id == dest_id), 
                    None
                )
                
                if not dest_config:
                    continue
                
                # Convert hotel assignments
                hotel_assignments = [
                    HotelAssignmentResponse(
                        hotel_id=assignment.hotel_id,
                        hotel_name=assignment.hotel_name,
                        assignment_date=assignment.assignment_date,
                        price=assignment.price,
                        currency=assignment.currency,
                        room_type=assignment.room_type,
                        selection_reason=assignment.selection_reason
                    )
                    for assignment in solution.assignments
                ]
                
                destination_response = DestinationResponse(
                    destination_id=dest_id,
                    destination_name=f"Destination {dest_id}",  # TODO: Load actual name
                    area_id=solution.area_id,
                    area_name=None,  # TODO: Load actual name if area_id exists
                    order=len(destination_responses),
                    nights=dest_config.nights,
                    start_date=start_date,
                    end_date=end_date,
                    total_cost=solution.total_cost,
                    currency=solution.currency,
                    hotels_count=solution.hotels_count,
                    single_hotel=solution.single_hotel,
                    hotel_assignments=hotel_assignments
                )
                
                destination_responses.append(destination_response)
            
            # Calculate totals
            total_cost = sum(dest.total_cost for dest in destination_responses)
            single_hotel_destinations = sum(1 for dest in destination_responses if dest.single_hotel)
            
            return ItineraryResponse(
                search_type="normal" if label in ["start_month", "mid_month", "end_month"] else 
                          "ranges" if "range" in label else "fixed_dates",
                label=label,
                destinations=destination_responses,
                total_cost=total_cost,
                currency=request.currency,
                total_nights=assignment.total_nights,
                start_date=assignment.start_date,
                end_date=assignment.end_date,
                optimization_score=None,  # TODO: Implement scoring
                alternatives_generated=1,  # TODO: Track actual alternatives
                single_hotel_destinations=single_hotel_destinations,
                date_context=None
            )
            
        except Exception as e:
            self.logger.error(f"Failed to optimize assignment {label}: {str(e)}", exc_info=True)
            return None
    
    def _find_best_itinerary(
        self, 
        itineraries: List[Optional[ItineraryResponse]]
    ) -> Optional[ItineraryResponse]:
        """Find the best itinerary from a list based on cost"""
        
        valid_itineraries = [i for i in itineraries if i is not None]
        
        if not valid_itineraries:
            return None
        
        # Sort by total cost (ascending) and return the cheapest
        return min(valid_itineraries, key=lambda x: x.total_cost)
    
    async def _get_cached_result(
        self, 
        request_hash: str
    ) -> Optional[ItineraryOptimizationResponse]:
        """Retrieve cached optimization result"""
        try:
            cache_key = f"itinerary_optimization:{request_hash}"
            cached_data = await self._cache_service.get(cache_key)
            
            if cached_data:
                # Convert cached data back to response object
                cached_data["metadata"]["cache_hit"] = True
                return ItineraryOptimizationResponse(**cached_data)
        
        except Exception as e:
            self.logger.warning(f"Cache retrieval failed: {e}")
        
        return None
    
    async def _cache_result(
        self, 
        request_hash: str, 
        result: ItineraryOptimizationResponse
    ):
        """Cache optimization result"""
        try:
            cache_key = f"itinerary_optimization:{request_hash}"
            cache_data = result.model_dump()
            
            # Cache for 1 hour (3600 seconds)
            await self._cache_service.set(cache_key, cache_data, ttl=3600)
            
        except Exception as e:
            self.logger.warning(f"Cache storage failed: {e}")
    
    def _create_error_response(
        self, 
        request_hash: str, 
        error_messages: List[str]
    ) -> ItineraryErrorResponse:
        """Create standardized error response"""
        errors = [
            ItineraryError(
                type="optimization_error",
                message=msg,
                details=None
            )
            for msg in error_messages
        ]
        
        return ItineraryErrorResponse(
            success=False,
            errors=errors,
            request_hash=request_hash
        )
    
    def _generate_default_ranges(self, global_range) -> List:
        """Generate default date ranges for ranges search when not provided"""
        try:
            from datetime import timedelta
            from app.schemas.itinerary import DateRange
            
            # Calculate total days in global range
            total_days = (global_range.end - global_range.start).days + 1
            
            # If range is too small, return single range
            if total_days <= 7:
                return [global_range]
            
            # Generate 3 overlapping ranges: early, mid, late
            ranges = []
            
            # Early range: first 40% of the period
            early_end = global_range.start + timedelta(days=int(total_days * 0.4))
            ranges.append(DateRange(start=global_range.start, end=early_end))
            
            # Mid range: middle 40% of the period  
            mid_start = global_range.start + timedelta(days=int(total_days * 0.3))
            mid_end = global_range.start + timedelta(days=int(total_days * 0.7))
            ranges.append(DateRange(start=mid_start, end=mid_end))
            
            # Late range: last 40% of the period
            late_start = global_range.start + timedelta(days=int(total_days * 0.6))
            ranges.append(DateRange(start=late_start, end=global_range.end))
            
            return ranges
            
        except Exception as e:
            self.logger.warning(f"Failed to generate default ranges: {e}")
            return [global_range]  # Fallback to single range


# Factory function for dependency injection
async def get_itinerary_optimization_service() -> ItineraryOptimizationService:
    """Get configured itinerary optimization service instance"""
    return ItineraryOptimizationService()