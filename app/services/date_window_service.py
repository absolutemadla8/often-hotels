"""
Date Window Service

Handles date range calculations and window generation for itinerary optimization.
Calculates valid date windows for consecutive destination visits.
"""

import logging
from datetime import date, timedelta
from typing import List, Dict, Tuple, Optional, Iterator, Any
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
    destinations: List[Tuple[int, Optional[int], date, date]]  # (destination_id, area_id, start_date, end_date)
    total_nights: int
    start_date: date
    end_date: date

    def get_dates_for_destination(self, destination_id: int, area_id: Optional[int] = None) -> Optional[Tuple[date, date]]:
        """Get start and end dates for a specific destination and area"""
        for dest_id, dest_area_id, start, end in self.destinations:
            if dest_id == destination_id and (area_id is None or dest_area_id == area_id):
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

            assignments.append((dest.destination_id, dest.area_id, dest_start, dest_end))

            # Next destination starts the day after this one ends
            current_date = dest_end + timedelta(days=1)

        # Calculate total trip span
        trip_start = assignments[0][2]  # Index 2 is now start_date (after adding area_id)
        trip_end = assignments[-1][3]   # Index 3 is now end_date
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
    ) -> List[Dict[str, Any]]:
        """
        Generate month-grouped assignments with future-only options.
        
        Returns list of month objects with start/mid/end options.
        Past options are set to None.
        
        Args:
            global_date_range: Overall trip date constraints
            destinations: Ordered destinations
            
        Returns:
            List of month dictionaries with assignments grouped by month
        """
        from calendar import monthrange
        
        total_nights = sum(dest.nights for dest in destinations)
        range_days = (global_date_range.end - global_date_range.start).days + 1
        
        if total_nights > range_days:
            self.logger.warning("Trip too long for date range")
            return []
        
        start_date = global_date_range.start
        end_date = global_date_range.end
        
        self.logger.info(f"Generating month-grouped slices from {start_date} to {end_date}")
        
        # Generate month-grouped options
        month_groups = self._generate_month_grouped_options(
            start_date, end_date, total_nights, destinations
        )
        
        self.logger.info(f"Generated {len(month_groups)} month groups")
        return month_groups
    
    def _generate_month_grouped_options(
        self,
        start_date: date,
        end_date: date,
        total_nights: int,
        destinations: List[DestinationRequest]
    ) -> List[Dict[str, Any]]:
        """Generate options grouped by month with future-only logic"""
        from calendar import monthrange
        
        month_groups = []
        current_date = start_date
        
        # Generate options for current month and next 1-2 months
        months_to_process = 0
        while current_date <= end_date and months_to_process < 3:
            month_name = current_date.strftime("%B %Y")
            
            # Get month boundaries
            month_start = current_date.replace(day=1)
            days_in_month = monthrange(current_date.year, current_date.month)[1]
            month_end = current_date.replace(day=days_in_month)
            
            # Generate start/mid/end options for this month
            month_options = self._generate_options_for_month(
                current_date, month_start, month_end, start_date, end_date, 
                total_nights, destinations
            )
            
            # Only add month if it has at least one option
            if any(month_options.values()):
                month_group = {
                    "month": month_name,
                    "start_month": month_options["start"],
                    "mid_month": month_options["mid"], 
                    "end_month": month_options["end"]
                }
                month_groups.append(month_group)
                self.logger.debug(f"Added month group: {month_name}")
            
            # Move to next month
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1, day=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1, day=1)
            
            months_to_process += 1
        
        return month_groups
    
    def _generate_options_for_month(
        self,
        current_month_date: date,
        month_start: date,
        month_end: date,
        search_start: date,
        search_end: date,
        total_nights: int,
        destinations: List[DestinationRequest]
    ) -> Dict[str, Optional[Any]]:
        """Generate start/mid/end options for a specific month"""
        
        options = {"start": None, "mid": None, "end": None}
        
        # Early month option (1st-10th)
        early_start = max(month_start, search_start)
        early_target = month_start.replace(day=min(5, month_start.day + 4))  # Around 5th
        early_start = max(early_start, early_target)
        
        if early_start >= search_start and early_start + timedelta(days=total_nights - 1) <= search_end:
            assignment = self._build_consecutive_assignment(destinations, early_start)
            if assignment and assignment.end_date <= search_end:
                assignment.label = f"{current_month_date.strftime('%B').lower()}_start"
                options["start"] = assignment
        
        # Mid month option (11th-20th)  
        mid_target = month_start.replace(day=15)
        mid_start = max(mid_target, search_start)
        
        if mid_start >= search_start and mid_start + timedelta(days=total_nights - 1) <= search_end:
            assignment = self._build_consecutive_assignment(destinations, mid_start)
            if assignment and assignment.end_date <= search_end:
                assignment.label = f"{current_month_date.strftime('%B').lower()}_mid"
                options["mid"] = assignment
        
        # Late month option (21st-end)
        late_target = month_start.replace(day=min(25, month_end.day))
        late_start = max(late_target, search_start)
        
        if late_start >= search_start and late_start + timedelta(days=total_nights - 1) <= search_end:
            assignment = self._build_consecutive_assignment(destinations, late_start)
            if assignment and assignment.end_date <= search_end:
                assignment.label = f"{current_month_date.strftime('%B').lower()}_end"
                options["end"] = assignment
        
        return options
    
    def _calculate_comprehensive_travel_options(
        self, 
        start_date: date, 
        end_date: date, 
        total_nights: int,
        search_day: int,
        days_in_month: int
    ) -> List[Tuple[str, date]]:
        """
        Calculate comprehensive travel timing options covering current and next month.
        
        Strategy: Generate ALL viable weekly and monthly options rather than limiting to 3.
        This provides better coverage of both current and next month opportunities.
        
        Returns list of (option_name, start_date) tuples
        """
        from calendar import monthrange
        
        options = []
        
        # Get key month boundaries
        current_month_start = start_date.replace(day=1)
        next_month_start = self._get_next_month_start(start_date)
        
        # Generate current month options (if there's still time)
        current_month_options = self._generate_current_month_options(
            start_date, end_date, total_nights, search_day, days_in_month
        )
        options.extend(current_month_options)
        
        # Generate next month options (comprehensive coverage)
        next_month_options = self._generate_next_month_options(
            start_date, end_date, total_nights, next_month_start
        )
        options.extend(next_month_options)
        
        # Generate additional weekly options within valid periods
        weekly_options = self._generate_weekly_options(
            start_date, end_date, total_nights, search_day
        )
        options.extend(weekly_options)
        
        # Remove duplicates and ensure all options are viable
        unique_options = []
        seen_dates = set()
        
        for option_name, option_start in options:
            if (option_start not in seen_dates and 
                option_start >= start_date and 
                option_start <= end_date - timedelta(days=total_nights - 1)):
                unique_options.append((option_name, option_start))
                seen_dates.add(option_start)
        
        # Sort by start date
        unique_options.sort(key=lambda x: x[1])
        
        # Ensure we have at least one option
        if not unique_options:
            self.logger.warning("No comprehensive options found, adding fallback")
            unique_options.append(("fallback_start", start_date))
        
        self.logger.info(f"Generated {len(unique_options)} comprehensive travel options")
        return unique_options
    
    def _generate_current_month_options(
        self, 
        start_date: date, 
        end_date: date, 
        total_nights: int, 
        search_day: int, 
        days_in_month: int
    ) -> List[Tuple[str, date]]:
        """Generate all viable options within the current month"""
        options = []
        
        # Immediate start (next few days)
        if search_day <= 25:  # Only if not too late in month
            immediate_start = start_date + timedelta(days=2)
            if immediate_start.day + total_nights <= days_in_month + 3:  # Can finish in current month or early next
                options.append(("current_immediate", immediate_start))
        
        # This weekend (if searching early/mid week)
        if search_day <= 20:
            # Find next weekend (Saturday)
            days_until_saturday = (5 - start_date.weekday()) % 7
            if days_until_saturday == 0:  # If today is Saturday
                days_until_saturday = 7
            weekend_start = start_date + timedelta(days=days_until_saturday)
            if weekend_start.month == start_date.month:
                options.append(("current_weekend", weekend_start))
        
        # Mid-month if not already past it
        if search_day <= 12:
            mid_month = start_date.replace(day=15)
            options.append(("current_mid", mid_month))
        
        # End of current month
        if search_day <= 22:
            month_end_start = self._get_month_end_start(start_date, total_nights)
            if month_end_start and month_end_start >= start_date:
                options.append(("current_end", month_end_start))
        
        return options
    
    def _generate_next_month_options(
        self, 
        start_date: date, 
        end_date: date, 
        total_nights: int, 
        next_month_start: date
    ) -> List[Tuple[str, date]]:
        """Generate comprehensive options for next month"""
        options = []
        
        if next_month_start > end_date - timedelta(days=total_nights - 1):
            return options  # Next month doesn't fit in date range
        
        # Start of next month
        options.append(("next_start", next_month_start))
        
        # First weekend of next month
        first_saturday = next_month_start + timedelta(days=(5 - next_month_start.weekday()) % 7)
        if first_saturday == next_month_start:  # If 1st is Saturday
            first_saturday += timedelta(days=7)
        options.append(("next_first_weekend", first_saturday))
        
        # Mid next month
        try:
            next_mid = next_month_start.replace(day=15)
            options.append(("next_mid", next_mid))
        except:
            pass
        
        # Third weekend of next month
        third_saturday = next_month_start + timedelta(days=14 + (5 - next_month_start.weekday()) % 7)
        options.append(("next_third_weekend", third_saturday))
        
        # End of next month
        next_month_end_start = self._get_next_month_end_start(start_date, total_nights)
        if next_month_end_start:
            options.append(("next_end", next_month_end_start))
        
        return options
    
    def _generate_weekly_options(
        self, 
        start_date: date, 
        end_date: date, 
        total_nights: int, 
        search_day: int
    ) -> List[Tuple[str, date]]:
        """Generate weekly interval options for better coverage"""
        options = []
        
        # Generate options every 7 days starting from a logical point
        current = start_date + timedelta(days=7 - (start_date.weekday() + 1) % 7)  # Next Monday
        week_count = 1
        
        while current <= end_date - timedelta(days=total_nights - 1) and week_count <= 6:
            options.append((f"week_{week_count}", current))
            current += timedelta(days=7)
            week_count += 1
        
        return options
    
    def _get_next_month_start(self, current_date: date) -> date:
        """Get the 1st of next month"""
        if current_date.month == 12:
            return date(current_date.year + 1, 1, 1)
        else:
            return date(current_date.year, current_date.month + 1, 1)
    
    def _get_next_month_mid(self, current_date: date) -> Optional[date]:
        """Get mid-point of next month (around 15th)"""
        try:
            next_month_start = self._get_next_month_start(current_date)
            return next_month_start.replace(day=15)
        except:
            return None
    
    def _get_month_end_start(self, current_date: date, trip_nights: int) -> Optional[date]:
        """Get start date for trip that ends at month end"""
        from calendar import monthrange
        try:
            days_in_month = monthrange(current_date.year, current_date.month)[1]
            # Start trip so it ends around last few days of month
            end_of_month = current_date.replace(day=days_in_month)
            trip_start = end_of_month - timedelta(days=trip_nights - 1)
            return trip_start if trip_start >= current_date else None
        except:
            return None
    
    def _get_next_month_end_start(self, current_date: date, trip_nights: int) -> Optional[date]:
        """Get start date for trip that ends at next month end"""
        from calendar import monthrange
        try:
            next_month_start = self._get_next_month_start(current_date)
            days_in_next_month = monthrange(next_month_start.year, next_month_start.month)[1]
            end_of_next_month = next_month_start.replace(day=days_in_next_month)
            trip_start = end_of_next_month - timedelta(days=trip_nights - 1)
            return trip_start
        except:
            return None
    
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