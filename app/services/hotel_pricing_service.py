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
        
        # Build query for hotels
        hotel_query = Hotel.filter(destination_id=destination_id, is_active=True)
        if area_id:
            hotel_query = hotel_query.filter(area_id=area_id)
        
        # Get hotels in the destination/area
        hotels = await hotel_query.limit(100)  # Reasonable limit for optimization
        
        if not hotels:
            self.logger.warning(f"No hotels found for destination {destination_id}, area {area_id}")
            return []
        
        hotel_ids = [hotel.id for hotel in hotels]
        
        # Fetch price data from UniversalPriceHistory
        price_data = await self._fetch_price_data(
            hotel_ids, start_date, end_date, currency
        )
        
        # Convert to HotelPriceData objects
        hotel_price_objects = []
        for hotel in hotels:
            hotel_prices = price_data.get(hotel.id, {})
            if hotel_prices:  # Only include hotels with price data
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
        
        self.logger.info(f"Found {len(hotel_price_objects)} hotels with pricing for destination {destination_id}")
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
        # Query price history for hotels in date range
        price_query = UniversalPriceHistory.filter(
            trackable_type=TrackableType.HOTEL_ROOM,
            trackable_id__in=hotel_ids,
            price_date__gte=start_date,
            price_date__lte=end_date,
            currency=currency,
            is_available=True
        ).order_by('trackable_id', 'price_date', '-recorded_at')
        
        price_records = await price_query.all()
        
        # Group by hotel_id and date, using most recent record for each date
        hotel_prices = defaultdict(dict)
        recorded_times = defaultdict(dict)  # Track when each price was recorded
        
        for record in price_records:
            hotel_id = record.trackable_id
            date_str = record.price_date.isoformat()
            
            # Use the most recent (latest recorded_at) price if multiple records exist for same date
            if (date_str not in hotel_prices[hotel_id] or 
                record.recorded_at > recorded_times[hotel_id][date_str]):
                hotel_prices[hotel_id][date_str] = record.price
                recorded_times[hotel_id][date_str] = record.recorded_at
        
        return dict(hotel_prices)
    
    def optimize_destination_hotels(
        self,
        destination_id: int,
        area_id: Optional[int],
        date_assignments: List[date],
        hotel_price_data: List[HotelPriceData]
    ) -> Optional[DestinationHotelSolution]:
        """
        Optimize hotel selection for a destination's date assignments.
        
        Priority:
        1. Single hotel covering all dates (if available and competitive)
        2. Cheapest combination of hotels per day
        
        Args:
            destination_id: Destination ID
            area_id: Optional area ID
            date_assignments: List of dates to assign hotels for
            hotel_price_data: Available hotel pricing
            
        Returns:
            Optimal hotel solution or None if no solution found
        """
        if not date_assignments or not hotel_price_data:
            self.logger.warning(f"No dates or hotel data for destination {destination_id}")
            return None
        
        start_date = min(date_assignments)
        end_date = max(date_assignments)
        
        # Try single hotel solution first
        single_hotel_solution = self._find_single_hotel_solution(
            destination_id, area_id, date_assignments, hotel_price_data
        )
        
        # Always calculate cheapest daily solution for comparison
        daily_solution = self._find_cheapest_daily_solution(
            destination_id, area_id, date_assignments, hotel_price_data
        )
        
        # Choose the better solution with strong preference for single hotel
        if single_hotel_solution and daily_solution:
            # Prefer single hotel if cost is within 20% of daily solution (increased tolerance)
            # This prioritizes convenience and consistency over pure cost optimization
            tolerance = Decimal('1.20')
            if single_hotel_solution.total_cost <= daily_solution.total_cost * tolerance:
                premium = single_hotel_solution.total_cost - daily_solution.total_cost
                self.logger.info(f"Selected single hotel solution (convenience premium: ₹{premium:.2f})")
                return single_hotel_solution
            else:
                savings = single_hotel_solution.total_cost - daily_solution.total_cost
                self.logger.info(f"Selected daily solution (significant savings: ₹{savings:.2f} > 20% threshold)")
                return daily_solution
        
        # Return whichever solution exists
        solution = single_hotel_solution or daily_solution
        if solution:
            self.logger.info(f"Hotel solution for destination {destination_id}: {solution.total_cost} {solution.currency}")
        
        return solution
    
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
    
    async def optimize_complete_itinerary(
        self,
        assignment: ConsecutiveAssignment,
        destinations: List[Dict],  # From DestinationRequest
        guest_config: GuestConfig,
        currency: str = "USD"
    ) -> Dict[int, DestinationHotelSolution]:
        """
        Optimize hotel selections for an entire itinerary.
        
        Args:
            assignment: Complete date assignment for destinations
            destinations: Destination configuration (with IDs and area IDs)
            guest_config: Guest configuration
            currency: Target currency
            
        Returns:
            Dict mapping destination_id -> hotel solution
        """
        solutions = {}
        
        for dest_id, start_date, end_date in assignment.destinations:
            # Find destination config
            dest_config = next((d for d in destinations if d['destination_id'] == dest_id), None)
            if not dest_config:
                self.logger.error(f"No config found for destination {dest_id}")
                continue
            
            area_id = dest_config.get('area_id')
            
            # Generate list of dates for this destination
            date_assignments = []
            current_date = start_date
            while current_date <= end_date:
                date_assignments.append(current_date)
                current_date += timedelta(days=1)
            
            # Get hotel price data
            hotel_price_data = await self.get_hotel_prices_for_destination(
                dest_id, area_id, (start_date, end_date), guest_config, currency
            )
            
            # Optimize hotel selection
            solution = self.optimize_destination_hotels(
                dest_id, area_id, date_assignments, hotel_price_data
            )
            
            if solution:
                solutions[dest_id] = solution
            else:
                self.logger.error(f"No hotel solution found for destination {dest_id}")
        
        return solutions
    
    def calculate_total_itinerary_cost(
        self,
        solutions: Dict[int, DestinationHotelSolution]
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