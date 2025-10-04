"""
Hotel Pricing Service

Handles hotel price optimization and selection for itinerary destinations.
Implements algorithms to find minimum cost hotel assignments with preferences
for single hotels covering entire stays.
"""

import logging
from datetime import date, timedelta
from typing import List, Dict, Tuple, Optional, Set
from decimal import Decimal
from dataclasses import dataclass
from collections import defaultdict

from app.models.models import Hotel, UniversalPriceHistory, TrackableType
from app.schemas.itinerary import HotelPriceData, GuestConfig
from app.services.date_window_service import ConsecutiveAssignment

logger = logging.getLogger(__name__)


@dataclass
class HotelAssignment:
    """Single hotel assignment for a date"""
    hotel_id: int
    hotel_name: str
    assignment_date: date
    price: Decimal
    currency: str
    room_type: Optional[str] = None
    selection_reason: str = "cheapest_day"


@dataclass
class DestinationHotelSolution:
    """Complete hotel solution for a destination"""
    destination_id: int
    area_id: Optional[int]
    start_date: date
    end_date: date
    assignments: List[HotelAssignment]
    total_cost: Decimal
    currency: str
    single_hotel: bool
    hotels_count: int


class HotelPricingService:
    """Service for optimizing hotel selections and costs"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._price_cache: Dict[str, Dict[str, Decimal]] = {}
    
    async def get_hotel_prices_for_destination(
        self,
        destination_id: int,
        area_id: Optional[int],
        date_range: Tuple[date, date],
        guest_config: GuestConfig,
        currency: str = "USD"
    ) -> List[HotelPriceData]:
        """
        Fetch hotel price data for a destination and date range.
        
        Args:
            destination_id: Target destination ID
            area_id: Optional area ID for more specific search
            date_range: (start_date, end_date) for price search
            guest_config: Guest configuration for pricing
            currency: Preferred currency
            
        Returns:
            List of hotel price data objects
        """
        start_date, end_date = date_range
        print(f"🚨🚨🚨 HOTEL PRICING METHOD CALLED: dest={destination_id}, area={area_id}, dates={start_date}-{end_date}, currency={currency}")
        self.logger.info(f"🔍 HOTEL PRICING: Starting search for destination_id={destination_id}, area_id={area_id}, dates={start_date} to {end_date}, currency={currency}")
        
        # Build query for hotels
        hotel_query = Hotel.filter(destination_id=destination_id, is_active=True)
        print(f"🚨🚨🚨 HOTEL QUERY: Built base query for destination_id={destination_id}, is_active=True")
        self.logger.info(f"🔍 HOTEL PRICING: Built base query for destination_id={destination_id}, is_active=True")
        
        if area_id:
            hotel_query = hotel_query.filter(area_id=area_id)
            print(f"🚨🚨🚨 HOTEL QUERY: Added area_id filter: area_id={area_id}")
            self.logger.info(f"🔍 HOTEL PRICING: Added area_id filter: area_id={area_id}")
        
        # Get hotels in the destination/area
        print(f"🚨🚨🚨 HOTEL QUERY: About to execute hotel query with limit 100...")
        self.logger.info(f"🔍 HOTEL PRICING: Executing hotel query with limit 100...")
        hotels = await hotel_query.limit(100).all()  # Reasonable limit for optimization
        print(f"🚨🚨🚨 HOTEL QUERY: Found {len(hotels)} hotels from query")
        self.logger.info(f"🔍 HOTEL PRICING: Found {len(hotels)} hotels from query")
        
        if not hotels:
            print(f"🚨🚨🚨 EARLY RETURN: No hotels found, returning empty list")
            self.logger.warning(f"❌ HOTEL PRICING: No hotels found for destination {destination_id}, area {area_id}")
            return []
        
        print(f"🚨🚨🚨 AFTER HOTEL CHECK: Hotels found, continuing processing")
        # Log first few hotel details for debugging
        for i, hotel in enumerate(hotels[:3]):
            self.logger.info(f"🔍 HOTEL PRICING: Hotel {i+1}: id={hotel.id}, name='{hotel.name}', destination_id={hotel.destination_id}, area_id={getattr(hotel, 'area_id', 'None')}")
        
        hotel_ids = [hotel.id for hotel in hotels]
        print(f"🚨🚨🚨 HOTEL IDS: Created list of {len(hotel_ids)} hotel IDs")
        self.logger.info(f"🔍 HOTEL PRICING: Hotel IDs to fetch prices for: {hotel_ids[:10]}{'...' if len(hotel_ids) > 10 else ''}")
        
        # Fetch price data from UniversalPriceHistory
        print(f"🚨🚨🚨 BEFORE PRICE FETCH: About to start price fetching section")
        print(f"🚨🚨🚨 PRICE DATA: About to fetch price data for {len(hotel_ids)} hotels")
        self.logger.info(f"🔍 HOTEL PRICING: Fetching price data from UniversalPriceHistory...")
        try:
            price_data = await self._fetch_price_data(
                hotel_ids, start_date, end_date, currency
            )
            print(f"🚨🚨🚨 PRICE DATA: Fetched price data for {len(price_data)} hotels")
            self.logger.info(f"🔍 HOTEL PRICING: Price data fetched - found data for {len(price_data)} hotels")
        except Exception as e:
            print(f"🚨🚨🚨 PRICE DATA ERROR: Exception in _fetch_price_data: {e}")
            self.logger.error(f"Error fetching price data: {e}")
            return []
        
        # Convert to HotelPriceData objects
        hotel_price_objects = []
        hotels_with_prices = 0
        hotels_without_prices = 0
        
        for hotel in hotels:
            hotel_prices = price_data.get(hotel.id, {})
            if hotel_prices:  # Only include hotels with price data
                hotels_with_prices += 1
                available_dates = [
                    date.fromisoformat(date_str) 
                    for date_str in hotel_prices.keys()
                ]
                
                hotel_price_obj = HotelPriceData(
                    hotel_id=hotel.id,
                    hotel_name=hotel.name,
                    prices={date_str: price for date_str, price in hotel_prices.items()},
                    currency=currency,
                    availability_dates=sorted(available_dates)
                )
                hotel_price_objects.append(hotel_price_obj)
                self.logger.info(f"🔍 HOTEL PRICING: ✅ Hotel {hotel.id} ({hotel.name}) has {len(hotel_prices)} price entries")
            else:
                hotels_without_prices += 1
                self.logger.info(f"🔍 HOTEL PRICING: ❌ Hotel {hotel.id} ({hotel.name}) has no price data")
        
        self.logger.info(f"🔍 HOTEL PRICING: SUMMARY - {hotels_with_prices} hotels WITH prices, {hotels_without_prices} hotels WITHOUT prices")
        self.logger.info(f"🔍 HOTEL PRICING: Returning {len(hotel_price_objects)} hotels with pricing for destination {destination_id}")
        return hotel_price_objects
    
    async def _fetch_price_data(
        self,
        hotel_ids: List[int],
        start_date: date,
        end_date: date,
        currency: str
    ) -> Dict[int, Dict[str, Decimal]]:
        """
        Fetch price data from database for hotels and date range.
        
        Returns:
            Dict mapping hotel_id -> {date_string -> price}
        """
        self.logger.info(f"🔍 PRICE FETCH: Starting price data fetch for {len(hotel_ids)} hotels")
        self.logger.info(f"🔍 PRICE FETCH: Date range: {start_date} to {end_date}")
        self.logger.info(f"🔍 PRICE FETCH: Currency: {currency}")
        self.logger.info(f"🔍 PRICE FETCH: Hotel IDs: {hotel_ids[:10]}{'...' if len(hotel_ids) > 10 else ''}")
        
        # Query price history for hotels in date range
        self.logger.info(f"🔍 PRICE FETCH: Building query with filters:")
        self.logger.info(f"🔍 PRICE FETCH: - trackable_type={TrackableType.HOTEL_ROOM}")
        self.logger.info(f"🔍 PRICE FETCH: - trackable_id__in={hotel_ids[:5]}{'...' if len(hotel_ids) > 5 else ''}")
        self.logger.info(f"🔍 PRICE FETCH: - price_date__gte={start_date}")
        self.logger.info(f"🔍 PRICE FETCH: - price_date__lte={end_date}")
        self.logger.info(f"🔍 PRICE FETCH: - currency={currency}")
        self.logger.info(f"🔍 PRICE FETCH: - is_available=True")
        
        price_query = UniversalPriceHistory.filter(
            trackable_type=TrackableType.HOTEL_ROOM,
            trackable_id__in=hotel_ids,
            price_date__gte=start_date,
            price_date__lte=end_date,
            currency=currency,
            is_available=True
        ).order_by('trackable_id', 'price_date', '-recorded_at')
        
        print(f"🚨🚨🚨 PRICE QUERY: About to execute price query...")
        self.logger.info(f"🔍 PRICE FETCH: Executing price query...")
        price_records = await price_query.all()
        print(f"🚨🚨🚨 PRICE QUERY: Found {len(price_records)} price records")
        self.logger.info(f"🔍 PRICE FETCH: Found {len(price_records)} price records")
        
        if len(price_records) > 0:
            # Log first few records for debugging
            for i, record in enumerate(price_records[:3]):
                self.logger.info(f"🔍 PRICE FETCH: Record {i+1}: hotel_id={record.trackable_id}, date={record.price_date}, price={record.price}, currency={record.currency}")
        
        # Group by hotel_id and date, using most recent record for each date
        hotel_prices = defaultdict(dict)
        recorded_times = defaultdict(dict)  # Track when each price was recorded
        
        processed_records = 0
        for record in price_records:
            hotel_id = record.trackable_id
            date_str = record.price_date.isoformat()
            
            # Use the most recent (latest recorded_at) price if multiple records exist for same date
            if (date_str not in hotel_prices[hotel_id] or 
                record.recorded_at > recorded_times[hotel_id][date_str]):
                hotel_prices[hotel_id][date_str] = record.price
                recorded_times[hotel_id][date_str] = record.recorded_at
                processed_records += 1
        
        self.logger.info(f"🔍 PRICE FETCH: Processed {processed_records} records into {len(hotel_prices)} hotels")
        
        # Log summary of hotels with price data
        for hotel_id, dates in list(hotel_prices.items())[:3]:
            self.logger.info(f"🔍 PRICE FETCH: Hotel {hotel_id} has prices for {len(dates)} dates: {list(dates.keys())[:5]}{'...' if len(dates) > 5 else ''}")
        
        return dict(hotel_prices)
    
    def optimize_destination_hotels(
        self,
        destination_id: int,
        area_id: Optional[int],
        date_assignments: List[date],
        hotel_price_data: List[HotelPriceData],
        preferred_hotels: Optional[List[int]] = None,
        hotel_change: bool = False
    ) -> Optional[DestinationHotelSolution]:
        """
        Optimize hotel selection for a destination's date assignments.
        
        Strategy based on hotel_change setting:
        - hotel_change=False: Find cheapest preferred hotel covering all dates
        - hotel_change=True: Smart switching with preferred hotel inclusion
        
        Args:
            destination_id: Destination ID
            area_id: Optional area ID
            date_assignments: List of dates to assign hotels for
            hotel_price_data: Available hotel pricing
            preferred_hotels: List of preferred hotel IDs to prioritize
            hotel_change: Whether to allow hotel switching for optimization
            
        Returns:
            Optimal hotel solution or None if no solution found
        """
        print(f"🚨🚨🚨 OPTIMIZE_DESTINATION_HOTELS CALLED: dest={destination_id}, dates={date_assignments}, hotel_data_len={len(hotel_price_data) if hotel_price_data else 0}")
        self.logger.info(f"🔍 OPTIMIZATION: Starting hotel optimization for destination {destination_id}")
        self.logger.info(f"🔍 OPTIMIZATION: Date assignments: {date_assignments}")
        self.logger.info(f"🔍 OPTIMIZATION: Hotel price data count: {len(hotel_price_data) if hotel_price_data else 0}")
        
        if not date_assignments:
            self.logger.warning(f"❌ OPTIMIZATION: No date assignments provided for destination {destination_id}")
            return None
            
        if not hotel_price_data:
            self.logger.warning(f"❌ OPTIMIZATION: No hotel price data provided for destination {destination_id}")
            return None
            
        self.logger.info(f"🔍 OPTIMIZATION: ✅ Both date assignments and hotel price data available, proceeding...")
        
        start_date = min(date_assignments)
        end_date = max(date_assignments)
        
        # Filter hotel data for preferred hotels if specified
        preferred_hotel_data = []
        non_preferred_hotel_data = hotel_price_data
        
        if preferred_hotels:
            preferred_hotel_data = [h for h in hotel_price_data if h.hotel_id in preferred_hotels]
            non_preferred_hotel_data = [h for h in hotel_price_data if h.hotel_id not in preferred_hotels]
        
        if not hotel_change:
            # hotel_change=False: Single hotel preference mode
            return self._find_preferred_single_hotel_solution(
                destination_id, area_id, date_assignments, 
                preferred_hotel_data, non_preferred_hotel_data
            )
        else:
            # hotel_change=True: Smart switching mode with preferred hotel inclusion
            return self._find_smart_switching_solution(
                destination_id, area_id, date_assignments,
                preferred_hotel_data, non_preferred_hotel_data
            )
    
    def _find_single_hotel_solution(
        self,
        destination_id: int,
        area_id: Optional[int],
        date_assignments: List[date],
        hotel_price_data: List[HotelPriceData]
    ) -> Optional[DestinationHotelSolution]:
        """Find best single hotel that covers all required dates"""
        
        best_solution = None
        best_cost = None
        date_strings = {d.isoformat() for d in date_assignments}
        
        for hotel_data in hotel_price_data:
            # Check if hotel has prices for all required dates
            hotel_date_strings = set(hotel_data.prices.keys())
            if not date_strings.issubset(hotel_date_strings):
                continue  # Hotel doesn't cover all required dates
            
            # Calculate total cost for this hotel
            total_cost = Decimal('0')
            assignments = []
            
            for assignment_date in sorted(date_assignments):
                date_str = assignment_date.isoformat()
                price = hotel_data.prices[date_str]
                total_cost += price
                
                assignment = HotelAssignment(
                    hotel_id=hotel_data.hotel_id,
                    hotel_name=hotel_data.hotel_name,
                    assignment_date=assignment_date,
                    price=price,
                    currency=hotel_data.currency,
                    selection_reason="single_hotel"
                )
                assignments.append(assignment)
            
            # Check if this is the best single hotel solution
            if best_cost is None or total_cost < best_cost:
                best_cost = total_cost
                best_solution = DestinationHotelSolution(
                    destination_id=destination_id,
                    area_id=area_id,
                    start_date=min(date_assignments),
                    end_date=max(date_assignments),
                    assignments=assignments,
                    total_cost=total_cost,
                    currency=hotel_data.currency,
                    single_hotel=True,
                    hotels_count=1
                )
        
        return best_solution
    
    def _find_cheapest_daily_solution(
        self,
        destination_id: int,
        area_id: Optional[int],
        date_assignments: List[date],
        hotel_price_data: List[HotelPriceData]
    ) -> Optional[DestinationHotelSolution]:
        """Find cheapest hotel for each day independently"""
        
        assignments = []
        total_cost = Decimal('0')
        hotels_used = set()
        currency = None
        
        for assignment_date in sorted(date_assignments):
            date_str = assignment_date.isoformat()
            
            # Find cheapest hotel for this specific date
            cheapest_price = None
            cheapest_hotel = None
            
            for hotel_data in hotel_price_data:
                if date_str in hotel_data.prices:
                    price = hotel_data.prices[date_str]
                    if cheapest_price is None or price < cheapest_price:
                        cheapest_price = price
                        cheapest_hotel = hotel_data
            
            if not cheapest_hotel:
                self.logger.warning(f"No hotel available for date {assignment_date}")
                return None
            
            # Create assignment for this date
            assignment = HotelAssignment(
                hotel_id=cheapest_hotel.hotel_id,
                hotel_name=cheapest_hotel.hotel_name,
                assignment_date=assignment_date,
                price=cheapest_price,
                currency=cheapest_hotel.currency,
                selection_reason="cheapest_day"
            )
            
            assignments.append(assignment)
            total_cost += cheapest_price
            hotels_used.add(cheapest_hotel.hotel_id)
            currency = cheapest_hotel.currency  # Assume all same currency
        
        if not assignments:
            return None
        
        return DestinationHotelSolution(
            destination_id=destination_id,
            area_id=area_id,
            start_date=min(date_assignments),
            end_date=max(date_assignments),
            assignments=assignments,
            total_cost=total_cost,
            currency=currency,
            single_hotel=len(hotels_used) == 1,
            hotels_count=len(hotels_used)
        )
    
    def _find_preferred_single_hotel_solution(
        self,
        destination_id: int,
        area_id: Optional[int],
        date_assignments: List[date],
        preferred_hotel_data: List[HotelPriceData],
        non_preferred_hotel_data: List[HotelPriceData]
    ) -> Optional[DestinationHotelSolution]:
        """Find cheapest single hotel solution, preferring user's preferred hotels"""
        
        # First try preferred hotels for single hotel solution
        if preferred_hotel_data:
            preferred_solution = self._find_single_hotel_solution(
                destination_id, area_id, date_assignments, preferred_hotel_data
            )
            if preferred_solution:
                self.logger.info(f"Found preferred single hotel solution: {preferred_solution.total_cost}")
                return preferred_solution
        
        # If no preferred hotel covers all dates, fallback to hotel_change=true mode
        self.logger.info("No preferred hotel available for all days, falling back to smart switching mode")
        return self._find_smart_switching_solution(
            destination_id, area_id, date_assignments, preferred_hotel_data, 
            preferred_hotel_data + non_preferred_hotel_data
        )
    
    def _find_smart_switching_solution(
        self,
        destination_id: int,
        area_id: Optional[int],
        date_assignments: List[date],
        preferred_hotel_data: List[HotelPriceData],
        non_preferred_hotel_data: List[HotelPriceData]
    ) -> Optional[DestinationHotelSolution]:
        """Find smart switching solution that maximizes preferred hotel usage and minimizes switches"""
        
        # Strategy: Try to find solution that maximizes preferred hotel nights
        # while minimizing hotel switches and optimizing cost
        
        # First, try preferred single hotel solution
        if preferred_hotel_data:
            preferred_single = self._find_single_hotel_solution(
                destination_id, area_id, date_assignments, preferred_hotel_data
            )
            if preferred_single:
                self.logger.info(f"Found preferred single hotel solution in switching mode: {preferred_single.total_cost}")
                return preferred_single
        
        # If single hotel not possible, find optimal switching solution
        all_hotel_data = preferred_hotel_data + non_preferred_hotel_data
        
        # Try block-based switching (minimize switches)
        block_solution = self._find_block_switching_solution(
            destination_id, area_id, date_assignments, preferred_hotel_data, all_hotel_data
        )
        
        # Also calculate pure daily cheapest for comparison
        daily_solution = self._find_cheapest_daily_solution(
            destination_id, area_id, date_assignments, all_hotel_data
        )
        
        # Choose best solution based on: preferred inclusion > switch minimization > cost
        if block_solution and daily_solution:
            # Prefer block solution if it's not significantly more expensive
            if block_solution.total_cost <= daily_solution.total_cost * Decimal('1.15'):  # 15% tolerance for switching
                self.logger.info(f"Selected block switching solution: {block_solution.total_cost}")
                return block_solution
            else:
                self.logger.info(f"Selected daily cheapest solution: {daily_solution.total_cost}")
                return daily_solution
        
        return block_solution or daily_solution
    
    def _find_block_switching_solution(
        self,
        destination_id: int,
        area_id: Optional[int],
        date_assignments: List[date],
        preferred_hotel_data: List[HotelPriceData],
        all_hotel_data: List[HotelPriceData]
    ) -> Optional[DestinationHotelSolution]:
        """Find solution with consecutive blocks of hotels to minimize switches"""
        
        if not date_assignments:
            return None
        
        sorted_dates = sorted(date_assignments)
        date_strings = [d.isoformat() for d in sorted_dates]
        
        # For small date ranges, use simple logic
        if len(sorted_dates) <= 3:
            return self._find_cheapest_daily_solution(destination_id, area_id, date_assignments, all_hotel_data)
        
        # Create blocks: try to split into consecutive hotel stays
        # Strategy: Find best hotels for first half and second half, minimize total cost + switch penalty
        
        mid_point = len(sorted_dates) // 2
        first_half = sorted_dates[:mid_point]
        second_half = sorted_dates[mid_point:]
        
        best_solution = None
        best_cost = None
        
        # Try different combinations of hotels for each block
        for first_hotel_data in all_hotel_data:
            # Check if first hotel covers first half
            first_hotel_dates = [d for d in first_half if d.isoformat() in first_hotel_data.prices]
            if len(first_hotel_dates) != len(first_half):
                continue
            
            for second_hotel_data in all_hotel_data:
                # Check if second hotel covers second half
                second_hotel_dates = [d for d in second_half if d.isoformat() in second_hotel_data.prices]
                if len(second_hotel_dates) != len(second_half):
                    continue
                
                # Calculate total cost
                first_half_cost = sum(first_hotel_data.prices[d.isoformat()] for d in first_half)
                second_half_cost = sum(second_hotel_data.prices[d.isoformat()] for d in second_half)
                total_cost = first_half_cost + second_half_cost
                
                # Add small penalty if switching hotels (to prefer single hotel when close)
                if first_hotel_data.hotel_id != second_hotel_data.hotel_id:
                    switch_penalty = total_cost * Decimal('0.01')  # 1% penalty for switching
                    total_cost += switch_penalty
                
                # Bonus for using preferred hotels
                preferred_bonus = Decimal('0')
                if preferred_hotel_data:
                    if first_hotel_data.hotel_id in [h.hotel_id for h in preferred_hotel_data]:
                        preferred_bonus += first_half_cost * Decimal('0.05')  # 5% bonus
                    if second_hotel_data.hotel_id in [h.hotel_id for h in preferred_hotel_data]:
                        preferred_bonus += second_half_cost * Decimal('0.05')  # 5% bonus
                
                adjusted_cost = total_cost - preferred_bonus
                
                if best_cost is None or adjusted_cost < best_cost:
                    best_cost = adjusted_cost
                    
                    # Build assignments
                    assignments = []
                    for assignment_date in first_half:
                        assignments.append(HotelAssignment(
                            hotel_id=first_hotel_data.hotel_id,
                            hotel_name=first_hotel_data.hotel_name,
                            assignment_date=assignment_date,
                            price=first_hotel_data.prices[assignment_date.isoformat()],
                            currency=first_hotel_data.currency,
                            selection_reason="preferred_block" if first_hotel_data.hotel_id in [h.hotel_id for h in preferred_hotel_data] else "cost_block"
                        ))
                    
                    for assignment_date in second_half:
                        assignments.append(HotelAssignment(
                            hotel_id=second_hotel_data.hotel_id,
                            hotel_name=second_hotel_data.hotel_name,
                            assignment_date=assignment_date,
                            price=second_hotel_data.prices[assignment_date.isoformat()],
                            currency=second_hotel_data.currency,
                            selection_reason="preferred_block" if second_hotel_data.hotel_id in [h.hotel_id for h in preferred_hotel_data] else "cost_block"
                        ))
                    
                    hotels_used = {first_hotel_data.hotel_id, second_hotel_data.hotel_id}
                    
                    best_solution = DestinationHotelSolution(
                        destination_id=destination_id,
                        area_id=area_id,
                        start_date=min(date_assignments),
                        end_date=max(date_assignments),
                        assignments=assignments,
                        total_cost=total_cost,  # Use original cost without adjustments
                        currency=first_hotel_data.currency,
                        single_hotel=len(hotels_used) == 1,
                        hotels_count=len(hotels_used)
                    )
        
        return best_solution
    
    async def optimize_complete_itinerary(
        self,
        assignment: ConsecutiveAssignment,
        destinations: List[Dict],  # From DestinationRequest
        guest_config: GuestConfig,
        currency: str = "USD",
        preferred_hotels: Optional[List[int]] = None,
        hotel_change: bool = False
    ) -> Dict[Tuple[int, Optional[int]], DestinationHotelSolution]:
        print(f"🚨🚨🚨 OPTIMIZE_COMPLETE_ITINERARY CALLED: destinations={destinations}, currency={currency}")
        """
        Optimize hotel selections for an entire itinerary.
        
        Args:
            assignment: Complete date assignment for destinations
            destinations: Destination configuration (with IDs and area IDs)
            guest_config: Guest configuration
            currency: Target currency
            preferred_hotels: List of preferred hotel IDs to prioritize
            hotel_change: Whether to allow hotel switching for optimization
            
        Returns:
            Dict mapping (destination_id, area_id) -> hotel solution
        """
        solutions = {}

        for dest_id, area_id, start_date, end_date in assignment.destinations:
            # Find destination config
            dest_config = next((d for d in destinations if d['destination_id'] == dest_id and d.get('area_id') == area_id), None)
            if not dest_config:
                self.logger.error(f"No config found for destination {dest_id}, area {area_id}")
                continue
            
            # Generate list of dates for this destination
            date_assignments = []
            current_date = start_date
            while current_date <= end_date:
                date_assignments.append(current_date)
                current_date += timedelta(days=1)
            
            # Get hotel price data
            print(f"🚨🚨🚨 ABOUT TO CALL get_hotel_prices_for_destination: dest_id={dest_id}, area_id={area_id}, start={start_date}, end={end_date}, currency={currency}")
            hotel_price_data = await self.get_hotel_prices_for_destination(
                dest_id, area_id, (start_date, end_date), guest_config, currency
            )
            print(f"🚨🚨🚨 RETURNED FROM get_hotel_prices_for_destination: got {len(hotel_price_data)} hotels")
            
            # Optimize hotel selection
            solution = self.optimize_destination_hotels(
                dest_id, area_id, date_assignments, hotel_price_data,
                preferred_hotels, hotel_change
            )
            
            if solution:
                # Use tuple key (dest_id, area_id) to support same destination with different areas
                solutions[(dest_id, area_id)] = solution
            else:
                self.logger.error(f"No hotel solution found for destination {dest_id}, area {area_id}")

        return solutions
    
    def calculate_total_itinerary_cost(
        self,
        solutions: Dict[Tuple[int, Optional[int]], DestinationHotelSolution]
    ) -> Tuple[Decimal, str]:
        """
        Calculate total cost across all destination solutions.
        
        Args:
            solutions: Dict of destination solutions
            
        Returns:
            (total_cost, currency)
        """
        if not solutions:
            return Decimal('0'), "USD"
        
        total_cost = Decimal('0')
        currency = None
        
        for solution in solutions.values():
            total_cost += solution.total_cost
            if currency is None:
                currency = solution.currency
            elif currency != solution.currency:
                self.logger.warning(f"Mixed currencies detected: {currency} vs {solution.currency}")
        
        return total_cost, currency or "USD"
    
    def get_itinerary_statistics(
        self,
        solutions: Dict[int, DestinationHotelSolution]
    ) -> Dict[str, any]:
        """
        Calculate statistics about the itinerary hotel solutions.
        
        Args:
            solutions: Dict of destination solutions
            
        Returns:
            Statistics dictionary
        """
        if not solutions:
            return {}
        
        total_cost, currency = self.calculate_total_itinerary_cost(solutions)
        single_hotel_destinations = sum(1 for sol in solutions.values() if sol.single_hotel)
        total_hotels = sum(sol.hotels_count for sol in solutions.values())
        total_nights = sum(len(sol.assignments) for sol in solutions.values())
        
        return {
            "total_cost": total_cost,
            "currency": currency,
            "total_destinations": len(solutions),
            "single_hotel_destinations": single_hotel_destinations,
            "total_hotels_used": total_hotels,
            "total_nights": total_nights,
            "average_cost_per_night": total_cost / total_nights if total_nights > 0 else Decimal('0'),
            "single_hotel_percentage": (single_hotel_destinations / len(solutions) * 100) if solutions else 0
        }


# Factory function for dependency injection
async def get_hotel_pricing_service() -> HotelPricingService:
    """Get configured hotel pricing service instance"""
    return HotelPricingService()