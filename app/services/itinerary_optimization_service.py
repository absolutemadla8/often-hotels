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
# from app.services.cache_service import get_cache_service  # Temporarily disabled

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
        # if not self._cache_service:
        #     self._cache_service = await get_cache_service()  # Temporarily disabled
    
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
            } if request.global_date_range else None,
            "single_start_date": request.single_start_date.isoformat() if request.single_start_date else None,
            "trip_start_dates": [d.isoformat() for d in request.trip_start_dates] if request.trip_start_dates else None,
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
            
            # Validate request constraints (only for Mode 1 - global_date_range)
            if request.global_date_range:
                validation_result = self._date_service.validate_date_constraints(
                    request.global_date_range, request.destinations
                )

                if not validation_result["valid"]:
                    return self._create_error_response(
                        request_hash, validation_result["errors"]
                    )
            # For Mode 2 and 3, validation happens in the mode-specific functions
            
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
        """Execute normal search - finds 3 cheapest trip start dates

        Supports 3 modes:
        1. global_date_range: Find 3 cheapest dates in range
        2. single_start_date: Find 2 more cheapest dates within ±30 days
        3. trip_start_dates: Use exactly these dates
        """

        self.logger.info(f"🔍 NORMAL SEARCH: Starting normal search execution")
        self.logger.info(f"🔍 NORMAL SEARCH: Request destinations: {[d.model_dump() for d in request.destinations]}")

        # Import the schema here to avoid circular imports
        from app.schemas.itinerary import MonthlyOptions, DateRange

        # Determine which mode is being used
        if request.trip_start_dates:
            # Mode 3: Use exact start dates provided
            self.logger.info(f"🔍 NORMAL SEARCH: Mode 3 - Using exact start dates: {request.trip_start_dates}")
            return await self._execute_exact_dates_mode(request)

        elif request.single_start_date:
            # Mode 2: Find 2 more dates within ±30 days
            self.logger.info(f"🔍 NORMAL SEARCH: Mode 2 - Finding 2 more dates around {request.single_start_date}")
            return await self._execute_single_date_mode(request)

        elif request.global_date_range:
            # Mode 1: Find 3 cheapest in range
            self.logger.info(f"🔍 NORMAL SEARCH: Mode 1 - Finding 3 cheapest in range {request.global_date_range.start} to {request.global_date_range.end}")
            return await self._execute_range_mode(request)

        else:
            raise ValueError("No date mode specified")

    async def _execute_range_mode(
        self,
        request: ItineraryOptimizationRequest
    ) -> NormalSearchResults:
        """Mode 1: Find 3 cheapest trip start dates within global_date_range"""
        from app.schemas.itinerary import MonthlyOptions

        # Generate ALL possible trip start dates
        self.logger.info(f"🔍 RANGE MODE: Generating all possible trip assignments...")
        month_groups = self._date_service.generate_monthly_slices(
            request.global_date_range, request.destinations, top_k=request.top_k
        )

        if not month_groups:
            self.logger.warning("No valid trip assignments found")
            return NormalSearchResults(monthly_options=[])

        month_group = month_groups[0]  # Single month group with all assignments
        month_name = month_group["month"]
        all_assignments = month_group.get("all_assignments", [])

        self.logger.info(f"🔍 NORMAL SEARCH: Evaluating trip costs for {len(all_assignments)} possible start dates...")

        # Collect all assignments with their costs
        assignment_costs = []

        # Evaluate EVERY assignment to find the cheapest
        skipped = 0
        for idx, assignment in enumerate(all_assignments):
            # Optimize this assignment to get total cost
            itinerary = await self._optimize_single_assignment(
                assignment, request, assignment.label or f"{month_name}_option_{idx}"
            )

            if itinerary:
                assignment_costs.append({
                    "itinerary": itinerary,
                    "cost": float(itinerary.total_cost),
                    "start_date": itinerary.start_date
                })
                self.logger.info(f"  ✓ Trip starting {itinerary.start_date}: ${itinerary.total_cost:.2f}")
            else:
                skipped += 1

        if skipped > 0:
            self.logger.info(f"  ⊘ Skipped {skipped} dates with no price data")

        # Sort by cost to get cheapest
        assignment_costs.sort(key=lambda x: x["cost"])

        self.logger.info(f"🔍 NORMAL SEARCH: Evaluated {len(assignment_costs)} valid trips, selecting cheapest {min(3, len(assignment_costs))}")

        if assignment_costs:
            self.logger.info(f"  → Cheapest: {assignment_costs[0]['start_date']} (${assignment_costs[0]['cost']:.2f})")
            if len(assignment_costs) > 1:
                self.logger.info(f"  → 2nd cheapest: {assignment_costs[1]['start_date']} (${assignment_costs[1]['cost']:.2f})")
            if len(assignment_costs) > 2:
                self.logger.info(f"  → 3rd cheapest: {assignment_costs[2]['start_date']} (${assignment_costs[2]['cost']:.2f})")

        # Take top 3 cheapest (or fewer if less available)
        top_3 = assignment_costs[:3]

        # Build monthly options with the 3 cheapest
        optimized_month = {
            "month": month_name,
            "start_month": top_3[0]["itinerary"] if len(top_3) > 0 else None,
            "mid_month": top_3[1]["itinerary"] if len(top_3) > 1 else None,
            "end_month": top_3[2]["itinerary"] if len(top_3) > 2 else None
        }

        if any([optimized_month["start_month"], optimized_month["mid_month"], optimized_month["end_month"]]):
            monthly_options = [MonthlyOptions(**optimized_month)]
        else:
            monthly_options = []

        self.logger.info(f"🔍 NORMAL SEARCH: Returning {len(monthly_options)} month options with 3 cheapest trips")

        return NormalSearchResults(
            monthly_options=monthly_options
        )

    async def _execute_single_date_mode(
        self,
        request: ItineraryOptimizationRequest
    ) -> NormalSearchResults:
        """Mode 2: Given single start date, find 2 more cheapest dates within ±30 days"""
        from app.schemas.itinerary import MonthlyOptions, DateRange
        from datetime import timedelta

        single_date = request.single_start_date
        total_nights = sum(dest.nights for dest in request.destinations)

        # Create date range: ±30 days from single_start_date
        range_start = single_date - timedelta(days=30)
        range_end = single_date + timedelta(days=30)

        self.logger.info(f"🔍 SINGLE DATE MODE: Searching {range_start} to {range_end} (±30 days from {single_date})")

        # Generate all possible dates in this range
        temp_range = DateRange(start=range_start, end=range_end)
        month_groups = self._date_service.generate_monthly_slices(
            temp_range, request.destinations, top_k=request.top_k
        )

        if not month_groups:
            self.logger.warning("No valid trip assignments found")
            return NormalSearchResults(monthly_options=[])

        # Rest is same as range mode - evaluate all and pick cheapest 3
        month_group = month_groups[0]
        month_name = f"{single_date.strftime('%B %Y')}"
        all_assignments = month_group.get("all_assignments", [])

        self.logger.info(f"🔍 SINGLE DATE MODE: Evaluating {len(all_assignments)} possible dates...")

        assignment_costs = []
        for idx, assignment in enumerate(all_assignments):
            itinerary = await self._optimize_single_assignment(
                assignment, request, assignment.label or f"option_{idx}"
            )
            if itinerary:
                assignment_costs.append({
                    "itinerary": itinerary,
                    "cost": float(itinerary.total_cost),
                    "start_date": itinerary.start_date
                })

        assignment_costs.sort(key=lambda x: x["cost"])
        self.logger.info(f"🔍 SINGLE DATE MODE: Found {len(assignment_costs)} valid trips, selecting cheapest 3")

        top_3 = assignment_costs[:3]
        optimized_month = {
            "month": month_name,
            "start_month": top_3[0]["itinerary"] if len(top_3) > 0 else None,
            "mid_month": top_3[1]["itinerary"] if len(top_3) > 1 else None,
            "end_month": top_3[2]["itinerary"] if len(top_3) > 2 else None
        }

        monthly_options = [MonthlyOptions(**optimized_month)] if any(optimized_month.values()) else []
        return NormalSearchResults(monthly_options=monthly_options)

    async def _execute_exact_dates_mode(
        self,
        request: ItineraryOptimizationRequest
    ) -> NormalSearchResults:
        """Mode 3: Use exactly the trip_start_dates provided"""
        from app.schemas.itinerary import MonthlyOptions

        exact_dates = request.trip_start_dates
        self.logger.info(f"🔍 EXACT DATES MODE: Using exact dates: {exact_dates}")

        # Build assignments for each exact date
        assignment_costs = []

        for idx, start_date in enumerate(exact_dates):
            # Build consecutive assignment for this start date
            assignment = self._date_service._build_consecutive_assignment(
                request.destinations, start_date
            )

            if assignment:
                assignment.label = f"exact_date_{idx + 1}"

                # Optimize this assignment
                itinerary = await self._optimize_single_assignment(
                    assignment, request, assignment.label
                )

                if itinerary:
                    assignment_costs.append({
                        "itinerary": itinerary,
                        "cost": float(itinerary.total_cost),
                        "start_date": itinerary.start_date
                    })
                    self.logger.info(f"  ✓ Trip starting {itinerary.start_date}: ${itinerary.total_cost:.2f}")

        # Sort by cost (still useful even with exact dates)
        assignment_costs.sort(key=lambda x: x["cost"])
        self.logger.info(f"🔍 EXACT DATES MODE: Evaluated {len(assignment_costs)} trips")

        # Use the dates as provided (sorted by cost)
        month_name = exact_dates[0].strftime("%B %Y") if exact_dates else "Trip"
        optimized_month = {
            "month": month_name,
            "start_month": assignment_costs[0]["itinerary"] if len(assignment_costs) > 0 else None,
            "mid_month": assignment_costs[1]["itinerary"] if len(assignment_costs) > 1 else None,
            "end_month": assignment_costs[2]["itinerary"] if len(assignment_costs) > 2 else None
        }

        monthly_options = [MonthlyOptions(**optimized_month)] if any(optimized_month.values()) else []
        return NormalSearchResults(monthly_options=monthly_options)

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
        print(f"🚨🚨🚨 _OPTIMIZE_SINGLE_ASSIGNMENT CALLED: label={label}, assignment={assignment}, currency={request.currency}")
        
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
            # Need to match destinations by both dest_id and area_id
            required_dest_keys = {(dest_id, area_id) for dest_id, area_id, _, _ in assignment.destinations}
            found_dest_keys = set(hotel_solutions.keys())

            if not required_dest_keys.issubset(found_dest_keys):
                missing = required_dest_keys - found_dest_keys
                self.logger.warning(f"Missing hotel solutions for destinations: {missing}")
                return None

            # Convert to response format
            destination_responses = []

            for dest_id, area_id, start_date, end_date in assignment.destinations:
                # Find destination config for metadata
                dest_config = next(
                    (d for d in request.destinations if d.destination_id == dest_id and d.area_id == area_id),
                    None
                )

                if not dest_config:
                    self.logger.warning(f"No config found for dest_id={dest_id}, area_id={area_id}")
                    continue

                # Get solution using tuple key (dest_id, area_id)
                solution = hotel_solutions.get((dest_id, area_id))

                if not solution:
                    self.logger.warning(f"No solution found for dest_id={dest_id}, area_id={area_id}")
                    continue

                # Convert hotel assignments
                hotel_assignments = []
                for hotel_assign in solution.assignments:
                    # Convert meta_prices from internal format to response format
                    from app.schemas.itinerary import MetaPrice
                    meta_prices = []
                    if hotel_assign.meta_prices:
                        meta_prices = [
                            MetaPrice(source=mp["source"], price=mp["price"])
                            for mp in hotel_assign.meta_prices
                        ]

                    hotel_assignments.append(
                        HotelAssignmentResponse(
                            hotel_id=hotel_assign.hotel_id,
                            hotel_name=hotel_assign.hotel_name,
                            assignment_date=hotel_assign.assignment_date,
                            price=hotel_assign.price,
                            currency=hotel_assign.currency,
                            room_type=hotel_assign.room_type,
                            selection_reason=hotel_assign.selection_reason,
                            meta_prices=meta_prices
                        )
                    )
                
                # Load actual destination and area names
                from app.models.models import Destination, Area
                destination = await Destination.get_or_none(id=dest_id)
                destination_name = destination.name if destination else f"Destination {dest_id}"

                area_name = None
                if solution.area_id:
                    area = await Area.get_or_none(id=solution.area_id)
                    area_name = area.name if area else None

                destination_response = DestinationResponse(
                    destination_id=dest_id,
                    destination_name=destination_name,
                    area_id=solution.area_id,
                    area_name=area_name,
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
        # Redis temporarily disabled
        return None
        # try:
        #     cache_key = f"itinerary_optimization:{request_hash}"
        #     cached_data = await self._cache_service.get(cache_key)
        #
        #     if cached_data:
        #         # Convert cached data back to response object
        #         cached_data["metadata"]["cache_hit"] = True
        #         return ItineraryOptimizationResponse(**cached_data)
        #
        # except Exception as e:
        #     self.logger.warning(f"Cache retrieval failed: {e}")
        #
        # return None
    
    async def _cache_result(
        self,
        request_hash: str,
        result: ItineraryOptimizationResponse
    ):
        """Cache optimization result"""
        # Redis temporarily disabled
        return
        # try:
        #     cache_key = f"itinerary_optimization:{request_hash}"
        #     cache_data = result.model_dump()
        #
        #     # Cache for 1 hour (3600 seconds)
        #     await self._cache_service.set(cache_key, cache_data, ttl=3600)
        #
        # except Exception as e:
        #     self.logger.warning(f"Cache storage failed: {e}")
    
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


async def convert_to_tier_based_response(
    optimization_response: ItineraryOptimizationResponse,
    request: ItineraryOptimizationRequest
) -> Dict[str, Any]:
    """
    Convert legacy ItineraryOptimizationResponse to new tier-based format

    This function transforms the old response structure (normal/ranges/fixed_dates)
    into the new tier structure (tiers with time segments and destinations)
    """
    from app.schemas.itinerary import (
        TierBasedItineraryResponse, ItineraryTier, TierDestination,
        HotelInTimeSegment, MetaPrice, TimeSegmentWithHotels
    )

    tiers = []

    # Process normal search results (monthly options)
    if optimization_response.normal and optimization_response.normal.monthly_options:
        for monthly_option in optimization_response.normal.monthly_options:
            # Collect all itineraries from this month (start/mid/end)
            month_itineraries = []
            if monthly_option.start_month:
                month_itineraries.append(monthly_option.start_month)
            if monthly_option.mid_month:
                month_itineraries.append(monthly_option.mid_month)
            if monthly_option.end_month:
                month_itineraries.append(monthly_option.end_month)

            if not month_itineraries:
                continue

            # Build destinations map with areas and star rating groups
            # Structure: {dest_id: {name, destinationId, areas: {area_id: {name, areaId, time_segments: [{label, 4star: [], 5star: []}]}}}}
            destinations_map: Dict[int, Dict[str, Any]] = {}

            # Import Hotel model to get star ratings
            from app.models.models import Hotel

            # Process each itinerary (time segment)
            for segment_idx, itin in enumerate(month_itineraries):
                segment_label = f"{itin.start_date} to {itin.end_date}"

                for dest_response in itin.destinations:
                    dest_id = dest_response.destination_id
                    area_id = dest_response.area_id

                    if dest_id not in destinations_map:
                        destinations_map[dest_id] = {
                            "name": dest_response.destination_name,
                            "destinationId": dest_id,
                            "areas": {}
                        }

                    if area_id and area_id not in destinations_map[dest_id]["areas"]:
                        destinations_map[dest_id]["areas"][area_id] = {
                            "name": dest_response.area_name,
                            "areaId": area_id,
                            "time_segments": []
                        }

                    # Ensure we have a time segment entry for this index
                    area_data = destinations_map[dest_id]["areas"][area_id]
                    while len(area_data["time_segments"]) <= segment_idx:
                        area_data["time_segments"].append({
                            "label": segment_label,
                            "hotels_4star": [],
                            "hotels_5star": []
                        })

                    # For this destination in this time segment, fetch top 5 hotels by star rating directly from DB
                    if dest_id and area_id:
                        # Fetch all hotels in this area with price data for this date range
                        from app.models.models import UniversalPriceHistory, TrackableType
                        from decimal import Decimal

                        # Get all hotels for this area
                        hotels_in_area = await Hotel.filter(
                            destination_id=dest_id,
                            area_id=area_id,
                            is_active=True
                        ).all()

                        if not hotels_in_area:
                            continue

                        hotel_ids = [h.id for h in hotels_in_area]

                        # Fetch price data for these hotels in this date range
                        price_records = await UniversalPriceHistory.filter(
                            trackable_type=TrackableType.HOTEL_ROOM,
                            trackable_id__in=hotel_ids,
                            price_date__gte=dest_response.start_date,
                            price_date__lte=dest_response.end_date,
                            currency=dest_response.currency,
                            is_available=True
                        ).all()

                        # Group prices by hotel
                        hotel_price_totals = {}
                        for record in price_records:
                            if record.trackable_id not in hotel_price_totals:
                                hotel_price_totals[record.trackable_id] = {
                                    "total": Decimal(0),
                                    "count": 0,
                                    "meta_prices": []
                                }
                            hotel_price_totals[record.trackable_id]["total"] += record.price
                            hotel_price_totals[record.trackable_id]["count"] += 1

                            # Add booking source info for meta_prices
                            if record.booking_source:
                                hotel_price_totals[record.trackable_id]["meta_prices"].append({
                                    "source": record.booking_source,
                                    "price": float(record.price)
                                })

                        # Calculate average prices and match with hotel data
                        hotel_totals = {}
                        hotels_data = hotels_in_area

                        # Build hotel star ratings and totals
                        hotel_star_ratings = {}
                        for hotel in hotels_data:
                            hotel_star_ratings[hotel.id] = {
                                "star_rating": hotel.star_rating,
                                "images": hotel.images
                            }

                            # Only include hotels that have price data
                            if hotel.id in hotel_price_totals:
                                price_info = hotel_price_totals[hotel.id]
                                avg_price = price_info["total"] / price_info["count"] if price_info["count"] > 0 else Decimal(0)

                                hotel_totals[hotel.id] = {
                                    "name": hotel.name,
                                    "id": hotel.id,
                                    "total": float(avg_price),
                                    "nights": (dest_response.end_date - dest_response.start_date).days,
                                    "meta_prices": price_info.get("meta_prices", [])
                                }

                        # Separate hotels by star rating (4 and 5 stars)
                        four_star_hotels = []
                        five_star_hotels = []

                        for hotel_id, hotel_data in hotel_totals.items():
                            star_info = hotel_star_ratings.get(hotel_id, {"star_rating": None})
                            star_rating = star_info.get("star_rating")
                            images = star_info.get("images", [])

                            # Get thumbnail
                            thumbnail = None
                            if images and isinstance(images, list) and len(images) > 0:
                                thumbnail = images[0].get('thumbnail') if isinstance(images[0], dict) else None

                            hotel_obj = {
                                "hotel_data": hotel_data,
                                "star_info": star_info,
                                "thumbnail": thumbnail,
                                "avg_price": hotel_data["total"] / hotel_data["nights"]
                            }

                            if star_rating == 4:
                                four_star_hotels.append(hotel_obj)
                            elif star_rating == 5:
                                five_star_hotels.append(hotel_obj)

                        # Sort by price and get top 1-5 hotels for each star rating
                        four_star_hotels.sort(key=lambda x: x["avg_price"])
                        five_star_hotels.sort(key=lambda x: x["avg_price"])

                        # Get up to 5 hotels for 4-star (prefer at least 3, but accept 1+)
                        top_4star = four_star_hotels[:5]
                        for hotel_obj in top_4star:
                            hotel_data = hotel_obj["hotel_data"]
                            hotel_segment = HotelInTimeSegment(
                                name=hotel_data["name"],
                                hotelId=hotel_data["id"],
                                image=hotel_obj["thumbnail"],
                                price=float(hotel_obj["avg_price"]),
                                currency=str(dest_response.currency),
                                status="Available",
                                nights=hotel_data["nights"],
                                checkIn=str(dest_response.start_date),
                                checkOut=str(dest_response.end_date),
                                meta_prices=hotel_data["meta_prices"]
                            )
                            area_data["time_segments"][segment_idx]["hotels_4star"].append(hotel_segment)

                        # Get up to 5 hotels for 5-star (prefer at least 3, but accept 1+)
                        top_5star = five_star_hotels[:5]
                        for hotel_obj in top_5star:
                            hotel_data = hotel_obj["hotel_data"]
                            hotel_segment = HotelInTimeSegment(
                                name=hotel_data["name"],
                                hotelId=hotel_data["id"],
                                image=hotel_obj["thumbnail"],
                                price=float(hotel_obj["avg_price"]),
                                currency=str(dest_response.currency),
                                status="Available",
                                nights=hotel_data["nights"],
                                checkIn=str(dest_response.start_date),
                                checkOut=str(dest_response.end_date),
                                meta_prices=hotel_data["meta_prices"]
                            )
                            area_data["time_segments"][segment_idx]["hotels_5star"].append(hotel_segment)

            # Build tier destinations with areas and star rating groups
            from app.schemas.itinerary import StarRatingGroup, TierArea
            tier_destinations = []

            for dest_id, dest_data in destinations_map.items():
                tier_areas = []

                # Build each area with its star rating groups and time segments
                for area_id, area_data in dest_data["areas"].items():
                    star_rating_groups = []

                    # Build time segments for 4-star hotels
                    time_segments_4star = []
                    for segment_data in area_data["time_segments"]:
                        if segment_data["hotels_4star"]:
                            # Include segment if it has at least 1 hotel (up to 5)
                            time_segments_4star.append(TimeSegmentWithHotels(
                                label=segment_data["label"],
                                hotels=segment_data["hotels_4star"]
                            ))

                    # Build time segments for 5-star hotels
                    time_segments_5star = []
                    for segment_data in area_data["time_segments"]:
                        if segment_data["hotels_5star"]:
                            # Include segment if it has at least 1 hotel (up to 5)
                            time_segments_5star.append(TimeSegmentWithHotels(
                                label=segment_data["label"],
                                hotels=segment_data["hotels_5star"]
                            ))

                    # Add 4-star group if we have time segments with hotels
                    if time_segments_4star:
                        star_rating_groups.append(StarRatingGroup(
                            star_rating=4,
                            time_segments=time_segments_4star
                        ))

                    # Add 5-star group if we have time segments with hotels
                    if time_segments_5star:
                        star_rating_groups.append(StarRatingGroup(
                            star_rating=5,
                            time_segments=time_segments_5star
                        ))

                    # Only add area if it has at least one star rating group
                    if star_rating_groups:
                        tier_areas.append(TierArea(
                            name=area_data["name"],
                            areaId=area_data["areaId"],
                            star_ratings=star_rating_groups
                        ))

                # Only add destination if it has areas
                if tier_areas:
                    tier_destinations.append(TierDestination(
                        name=dest_data["name"],
                        destinationId=dest_data["destinationId"],
                        areas=tier_areas
                    ))

            # Create tier
            total_nights = sum(dest.nights for dest in request.destinations)
            tier = ItineraryTier(
                id=monthly_option.month.lower().replace(" ", "-"),
                title=f"{monthly_option.month} ({total_nights} nights)",
                destinations=tier_destinations
            )
            tiers.append(tier)

    # Create tier-based response
    tier_response = TierBasedItineraryResponse(tiers=tiers)

    return {
        "success": True,
        "message": "Itinerary optimization completed successfully",
        "data": tier_response.model_dump(),
        "errors": None
    }


# Factory function for dependency injection
async def get_itinerary_optimization_service() -> ItineraryOptimizationService:
    """Get configured itinerary optimization service instance"""
    return ItineraryOptimizationService()