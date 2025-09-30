"""
Date Window Service

Handles date range calculations and window generation for itinerary optimization.
Calculates valid date windows for consecutive destination visits.
"""

import logging
from datetime import date, timedelta
from typing import List, Dict, Tuple, Optional, Iterator
from dataclasses import dataclass

from app.schemas.itinerary import DateRange, DestinationRequest, DateWindow

logger = logging.getLogger(__name__)


@dataclass
class DestinationWindow:
    """Date window for a single destination"""
    destination_id: int
    area_id: Optional[int]
    nights: int
    order: int
    earliest_start: date
    latest_start: date
    
    @property
    def window_days(self) -> int:
        """Number of possible start days"""
        return (self.latest_start - self.earliest_start).days + 1


@dataclass
class ConsecutiveAssignment:
    """A complete assignment of dates to all destinations"""
    destinations: List[Tuple[int, date, date]]  # (destination_id, start_date, end_date)
    total_nights: int
    start_date: date
    end_date: date
    
    def get_dates_for_destination(self, destination_id: int) -> Optional[Tuple[date, date]]:
        """Get start and end dates for a specific destination"""
        for dest_id, start, end in self.destinations:
            if dest_id == destination_id:
                return start, end
        return None


class DateWindowService:
    """Service for calculating valid date windows for itinerary optimization"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def calculate_destination_windows(
        self,
        global_date_range: DateRange,
        destinations: List[DestinationRequest]
    ) -> List[DestinationWindow]:
        """
        Calculate valid date windows for each destination in order.
        
        Each destination must fit within the global date range, and subsequent
        destinations must have room after previous ones complete.
        
        Args:
            global_date_range: Overall trip date constraints
            destinations: Ordered list of destinations with nights required
            
        Returns:
            List of destination windows with earliest/latest start dates
        """
        if not destinations:
            return []
        
        total_nights = sum(dest.nights for dest in destinations)
        global_span = (global_date_range.end - global_date_range.start).days + 1
        
        if total_nights > global_span:
            self.logger.warning(f"Total nights ({total_nights}) exceeds global span ({global_span})")
            return []
        
        windows = []
        
        for i, dest in enumerate(destinations):
            # Calculate how many nights are needed after this destination
            remaining_nights = sum(d.nights for d in destinations[i+1:])
            
            # Earliest start: global start (or after previous destination ends)
            if i == 0:
                earliest_start = global_date_range.start
            else:
                # This will be calculated when we generate consecutive assignments
                earliest_start = global_date_range.start
            
            # Latest start: must leave room for this destination and all following ones
            latest_end = global_date_range.end
            latest_start = latest_end - timedelta(days=dest.nights + remaining_nights - 1)
            
            # Ensure latest start is not before earliest start
            if latest_start < earliest_start:
                self.logger.error(f"No valid window for destination {dest.destination_id}")
                return []
            
            window = DestinationWindow(
                destination_id=dest.destination_id,
                area_id=dest.area_id,
                nights=dest.nights,
                order=i,
                earliest_start=earliest_start,
                latest_start=latest_start
            )
            
            windows.append(window)
            self.logger.debug(f"Window {i}: {earliest_start} to {latest_start} ({window.window_days} days)")
        
        return windows
    
    def generate_consecutive_assignments(
        self,
        global_date_range: DateRange,
        destinations: List[DestinationRequest],
        max_combinations: int = 1000
    ) -> Iterator[ConsecutiveAssignment]:
        """
        Generate all valid consecutive date assignments for destinations.
        
        Args:
            global_date_range: Overall trip date constraints
            destinations: Ordered list of destinations
            max_combinations: Maximum assignments to generate
            
        Yields:
            ConsecutiveAssignment objects with specific dates for each destination
        """
        if not destinations:
            return
        
        total_nights = sum(dest.nights for dest in destinations)
        global_span = (global_date_range.end - global_date_range.start).days + 1
        
        if total_nights > global_span:
            self.logger.warning(f"Cannot fit {total_nights} nights in {global_span} days")
            return
        
        # Calculate latest possible start date for first destination
        latest_first_start = global_date_range.end - timedelta(days=total_nights - 1)
        
        combinations_generated = 0
        current_start = global_date_range.start
        
        while current_start <= latest_first_start and combinations_generated < max_combinations:
            assignment = self._build_consecutive_assignment(destinations, current_start)
            
            if assignment and assignment.end_date <= global_date_range.end:
                yield assignment
                combinations_generated += 1
            
            current_start += timedelta(days=1)
        
        self.logger.info(f"Generated {combinations_generated} consecutive assignments")
    
    def _build_consecutive_assignment(
        self,
        destinations: List[DestinationRequest],
        start_date: date
    ) -> Optional[ConsecutiveAssignment]:
        """
        Build a consecutive assignment starting from a specific date.
        
        Args:
            destinations: Ordered destinations
            start_date: Start date for first destination
            
        Returns:
            ConsecutiveAssignment or None if invalid
        """
        assignments = []
        current_date = start_date
        
        for dest in destinations:
            dest_start = current_date
            dest_end = current_date + timedelta(days=dest.nights - 1)
            
            assignments.append((dest.destination_id, dest_start, dest_end))
            
            # Next destination starts the day after this one ends
            current_date = dest_end + timedelta(days=1)
        
        # Calculate total trip span
        trip_start = assignments[0][1]
        trip_end = assignments[-1][2]
        total_nights = sum(dest.nights for dest in destinations)
        
        return ConsecutiveAssignment(
            destinations=assignments,
            total_nights=total_nights,
            start_date=trip_start,
            end_date=trip_end
        )
    
    def generate_monthly_slices(
        self,
        global_date_range: DateRange,
        destinations: List[DestinationRequest]
    ) -> List[ConsecutiveAssignment]:
        """
        Generate normal search assignments: start, middle, end of date range.
        
        Args:
            global_date_range: Overall trip date constraints
            destinations: Ordered destinations
            
        Returns:
            List of up to 3 assignments (start, mid, end)
        """
        assignments = []
        total_nights = sum(dest.nights for dest in destinations)
        range_days = (global_date_range.end - global_date_range.start).days + 1
        
        if total_nights > range_days:
            self.logger.warning("Trip too long for date range")
            return []
        
        # Start of range
        start_assignment = self._build_consecutive_assignment(destinations, global_date_range.start)
        if start_assignment and start_assignment.end_date <= global_date_range.end:
            assignments.append(start_assignment)
        
        # Middle of range (if there's room)
        if range_days >= total_nights + 2:  # Need at least 2 days buffer
            mid_start = global_date_range.start + timedelta(days=(range_days - total_nights) // 2)
            mid_assignment = self._build_consecutive_assignment(destinations, mid_start)
            if mid_assignment and mid_assignment.end_date <= global_date_range.end:
                assignments.append(mid_assignment)
        
        # End of range
        end_start = global_date_range.end - timedelta(days=total_nights - 1)
        if end_start != global_date_range.start:  # Don't duplicate start assignment
            end_assignment = self._build_consecutive_assignment(destinations, end_start)
            if end_assignment and end_assignment.end_date <= global_date_range.end:
                assignments.append(end_assignment)
        
        self.logger.info(f"Generated {len(assignments)} monthly slice assignments")
        return assignments
    
    def generate_range_assignments(
        self,
        date_ranges: List[DateRange],
        destinations: List[DestinationRequest],
        top_k: int = 3
    ) -> List[ConsecutiveAssignment]:
        """
        Generate assignments for specific date ranges (sliding window approach).
        
        Args:
            date_ranges: List of date ranges to search within
            destinations: Ordered destinations
            top_k: Maximum assignments per range
            
        Returns:
            List of assignments across all ranges
        """
        all_assignments = []
        
        for date_range in date_ranges:
            range_assignments = list(
                self.generate_consecutive_assignments(
                    date_range, 
                    destinations, 
                    max_combinations=top_k
                )
            )
            
            # Take top_k from this range
            all_assignments.extend(range_assignments[:top_k])
            
            self.logger.debug(f"Range {date_range.start} to {date_range.end}: {len(range_assignments)} assignments")
        
        # Sort all assignments by start date
        all_assignments.sort(key=lambda a: a.start_date)
        
        self.logger.info(f"Generated {len(all_assignments)} range assignments")
        return all_assignments
    
    def generate_fixed_date_assignments(
        self,
        fixed_dates: List[date],
        destinations: List[DestinationRequest]
    ) -> List[ConsecutiveAssignment]:
        """
        Generate assignments starting on specific fixed dates.
        
        Args:
            fixed_dates: List of exact start dates
            destinations: Ordered destinations
            
        Returns:
            List of assignments, one per fixed date (if valid)
        """
        assignments = []
        
        for fixed_date in fixed_dates:
            assignment = self._build_consecutive_assignment(destinations, fixed_date)
            if assignment:
                assignments.append(assignment)
                self.logger.debug(f"Fixed date {fixed_date}: valid assignment created")
            else:
                self.logger.debug(f"Fixed date {fixed_date}: no valid assignment")
        
        self.logger.info(f"Generated {len(assignments)} fixed date assignments")
        return assignments
    
    def validate_date_constraints(
        self,
        global_date_range: DateRange,
        destinations: List[DestinationRequest]
    ) -> Dict[str, any]:
        """
        Validate that destinations can fit within global date constraints.
        
        Args:
            global_date_range: Overall trip constraints
            destinations: Ordered destinations
            
        Returns:
            Validation result with details
        """
        total_nights = sum(dest.nights for dest in destinations)
        range_days = (global_date_range.end - global_date_range.start).days + 1
        
        result = {
            "valid": True,
            "total_nights": total_nights,
            "range_days": range_days,
            "buffer_days": range_days - total_nights,
            "warnings": [],
            "errors": []
        }
        
        if total_nights > range_days:
            result["valid"] = False
            result["errors"].append(
                f"Total nights ({total_nights}) exceeds date range ({range_days} days)"
            )
        
        if range_days - total_nights < 2:
            result["warnings"].append("Very tight date constraints - limited flexibility")
        
        # Check individual destination constraints
        for i, dest in enumerate(destinations):
            if dest.nights > 14:
                result["warnings"].append(f"Destination {dest.destination_id} has long stay ({dest.nights} nights)")
        
        return result


# Factory function for dependency injection
async def get_date_window_service() -> DateWindowService:
    """Get configured date window service instance"""
    return DateWindowService()