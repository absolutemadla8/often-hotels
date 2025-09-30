"""
Itinerary optimization request and response schemas

Pydantic models for the multi-destination itinerary optimization system
with flexible search modes and hotel cost minimization.
"""

from datetime import date
from typing import List, Dict, Any, Optional, Union, Literal
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator, ConfigDict

from app.models.models import SearchType, ItineraryStatus


# Request Schemas
class DestinationRequest(BaseModel):
    """Single destination in an itinerary request"""
    destination_id: int = Field(..., gt=0, description="Destination ID")
    area_id: Optional[int] = Field(None, gt=0, description="Optional area ID within destination")
    nights: int = Field(..., gt=0, le=30, description="Required nights at this destination")
    
    model_config = ConfigDict(from_attributes=True)


class DateRange(BaseModel):
    """Date range for ranges search"""
    start: date = Field(..., description="Range start date")
    end: date = Field(..., description="Range end date")
    
    @field_validator('end')
    @classmethod
    def validate_end_after_start(cls, v, info):
        if v and info.data.get('start') and v <= info.data['start']:
            raise ValueError('End date must be after start date')
        return v
    
    model_config = ConfigDict(from_attributes=True)


class GuestConfig(BaseModel):
    """Guest configuration for bookings"""
    adults: int = Field(1, ge=1, le=10, description="Number of adults")
    children: int = Field(0, ge=0, le=8, description="Number of children")
    child_ages: Optional[List[int]] = Field(None, description="Ages of children")
    
    model_config = ConfigDict(from_attributes=True)


class ItineraryOptimizationRequest(BaseModel):
    """Main request for itinerary optimization"""
    
    # Search mode configuration
    custom: bool = Field(False, description="Use custom search modes or normal only")
    search_types: List[Literal["normal", "ranges", "fixed_dates", "all"]] = Field(
        ["normal"], 
        description="Search types to execute"
    )
    
    # Destinations and ordering
    destinations: List[DestinationRequest] = Field(
        ..., 
        min_length=1, 
        max_length=10,
        description="Destinations in order with nights required"
    )
    suggest_best_order: bool = Field(True, description="Allow system to reorder destinations")
    
    # Date constraints
    global_date_range: DateRange = Field(..., description="Overall date range for the trip")
    ranges: Optional[List[DateRange]] = Field(None, description="Date ranges for ranges search")
    fixed_dates: Optional[List[date]] = Field(None, description="Fixed dates for exact search")
    
    # Guest configuration
    guests: GuestConfig = Field(default_factory=GuestConfig, description="Guest configuration")
    
    # Search parameters
    currency: str = Field("USD", min_length=3, max_length=3, description="Preferred currency")
    top_k: int = Field(3, ge=1, le=10, description="Top itineraries per search type")
    
    # Performance options
    use_cache: bool = Field(True, description="Use cached results if available")
    max_optimization_time_ms: Optional[int] = Field(30000, description="Max optimization time")
    
    @field_validator('search_types')
    @classmethod
    def validate_search_types(cls, v):
        valid_types = {"normal", "ranges", "fixed_dates", "all"}
        for search_type in v:
            if search_type not in valid_types:
                raise ValueError(f"Invalid search type: {search_type}")
        
        # If "all" is present, it should be the only type
        if "all" in v and len(v) > 1:
            raise ValueError("'all' search type cannot be combined with others")
        
        return v
    
    @field_validator('ranges')
    @classmethod
    def validate_ranges(cls, v, info):
        if info.data.get('custom') and 'ranges' in info.data.get('search_types', []):
            if not v:
                raise ValueError("Ranges must be provided for ranges search")
        return v
    
    @field_validator('fixed_dates')
    @classmethod
    def validate_fixed_dates(cls, v, info):
        if info.data.get('custom') and 'fixed_dates' in info.data.get('search_types', []):
            if not v:
                raise ValueError("Fixed dates must be provided for fixed_dates search")
        return v
    
    model_config = ConfigDict(from_attributes=True)


# Response Schemas
class HotelAssignmentResponse(BaseModel):
    """Hotel assignment for a specific date"""
    hotel_id: int = Field(..., description="Hotel ID")
    hotel_name: str = Field(..., description="Hotel name")
    assignment_date: date = Field(..., description="Date for this assignment")
    price: Decimal = Field(..., description="Price for this date")
    currency: str = Field(..., description="Price currency")
    room_type: Optional[str] = Field(None, description="Room type")
    selection_reason: Optional[str] = Field(None, description="Why this hotel was selected")
    
    model_config = ConfigDict(from_attributes=True)


class DestinationResponse(BaseModel):
    """Destination in an optimized itinerary"""
    destination_id: int = Field(..., description="Destination ID")
    destination_name: str = Field(..., description="Destination name")
    area_id: Optional[int] = Field(None, description="Area ID if specified")
    area_name: Optional[str] = Field(None, description="Area name if specified")
    order: int = Field(..., description="Position in itinerary (0-based)")
    nights: int = Field(..., description="Nights at this destination")
    start_date: date = Field(..., description="Start date at destination")
    end_date: date = Field(..., description="End date at destination")
    total_cost: Decimal = Field(..., description="Total cost for this destination")
    currency: str = Field(..., description="Cost currency")
    hotels_count: int = Field(..., description="Number of hotels used")
    single_hotel: bool = Field(..., description="True if single hotel covers all nights")
    hotel_assignments: List[HotelAssignmentResponse] = Field(
        ..., 
        description="Daily hotel assignments"
    )
    
    model_config = ConfigDict(from_attributes=True)


class ItineraryResponse(BaseModel):
    """Single optimized itinerary result"""
    search_type: str = Field(..., description="Search type that generated this itinerary")
    label: Optional[str] = Field(None, description="Label for this itinerary (e.g., 'start_month')")
    
    # Itinerary details
    destinations: List[DestinationResponse] = Field(..., description="Ordered destinations")
    total_cost: Decimal = Field(..., description="Total trip cost")
    currency: str = Field(..., description="Cost currency")
    total_nights: int = Field(..., description="Total nights in itinerary")
    
    # Date information
    start_date: date = Field(..., description="Trip start date")
    end_date: date = Field(..., description="Trip end date")
    
    # Optimization metadata
    optimization_score: Optional[float] = Field(None, description="Quality score")
    alternatives_generated: int = Field(0, description="Number of alternatives considered")
    single_hotel_destinations: int = Field(0, description="Destinations with single hotel")
    
    # Additional context for ranges/fixed_dates searches
    date_context: Optional[Dict[str, Any]] = Field(None, description="Additional date context")
    
    model_config = ConfigDict(from_attributes=True)


class NormalSearchResults(BaseModel):
    """Results from normal search (start/mid/end month)"""
    start_month: Optional[ItineraryResponse] = Field(None, description="Start of month itinerary")
    mid_month: Optional[ItineraryResponse] = Field(None, description="Mid-month itinerary")
    end_month: Optional[ItineraryResponse] = Field(None, description="End of month itinerary")
    
    model_config = ConfigDict(from_attributes=True)


class RangesSearchResults(BaseModel):
    """Results from ranges search"""
    results: List[ItineraryResponse] = Field(..., description="Itineraries for each range")
    
    model_config = ConfigDict(from_attributes=True)


class FixedDatesSearchResults(BaseModel):
    """Results from fixed dates search"""
    results: List[ItineraryResponse] = Field(..., description="Itineraries for each fixed date")
    
    model_config = ConfigDict(from_attributes=True)


class OptimizationMetadata(BaseModel):
    """Metadata about the optimization process"""
    processing_time_ms: int = Field(..., description="Total processing time")
    cache_hit: bool = Field(False, description="Whether results came from cache")
    hotels_searched: int = Field(0, description="Total hotels searched")
    price_queries: int = Field(0, description="Total price queries made")
    alternatives_generated: int = Field(0, description="Total alternatives generated")
    best_cost_found: Optional[Decimal] = Field(None, description="Best total cost found")
    
    model_config = ConfigDict(from_attributes=True)


class ItineraryOptimizationResponse(BaseModel):
    """Main response for itinerary optimization"""
    success: bool = Field(True, description="Operation success status")
    request_hash: str = Field(..., description="Request hash for caching")
    
    # Results by search type
    normal: Optional[NormalSearchResults] = Field(None, description="Normal search results")
    ranges: Optional[RangesSearchResults] = Field(None, description="Ranges search results")
    fixed_dates: Optional[FixedDatesSearchResults] = Field(None, description="Fixed dates results")
    
    # Best overall result
    best_itinerary: Optional[ItineraryResponse] = Field(None, description="Best overall itinerary")
    
    # Metadata
    metadata: OptimizationMetadata = Field(..., description="Processing metadata")
    filters_applied: Dict[str, Any] = Field(..., description="Applied search filters")
    
    # User context
    message: str = Field(..., description="Human-readable result message")
    
    model_config = ConfigDict(from_attributes=True)


# Error response schemas
class ItineraryError(BaseModel):
    """Error in itinerary optimization"""
    type: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    
    model_config = ConfigDict(from_attributes=True)


class ItineraryErrorResponse(BaseModel):
    """Error response for itinerary optimization"""
    success: bool = Field(False, description="Operation success status")
    errors: List[ItineraryError] = Field(..., description="List of errors")
    request_hash: Optional[str] = Field(None, description="Request hash if generated")
    
    model_config = ConfigDict(from_attributes=True)


# Utility schemas for internal use
class HotelPriceData(BaseModel):
    """Hotel price data for optimization algorithms"""
    hotel_id: int = Field(..., description="Hotel ID")
    hotel_name: str = Field(..., description="Hotel name")
    prices: Dict[str, Decimal] = Field(..., description="Date -> Price mapping")
    currency: str = Field(..., description="Price currency")
    availability_dates: List[date] = Field(..., description="Available dates")
    
    model_config = ConfigDict(from_attributes=True)


class DateWindow(BaseModel):
    """Date window for optimization calculations"""
    destination_order: int = Field(..., description="Destination position")
    earliest_start: date = Field(..., description="Earliest possible start date")
    latest_start: date = Field(..., description="Latest possible start date")
    nights: int = Field(..., description="Required nights")
    
    model_config = ConfigDict(from_attributes=True)


class OptimizationCandidate(BaseModel):
    """Single optimization candidate during processing"""
    destinations: List[Dict[str, Any]] = Field(..., description="Destination assignments")
    total_cost: Decimal = Field(..., description="Total cost")
    currency: str = Field(..., description="Currency")
    feasible: bool = Field(..., description="Whether assignment is feasible")
    score: Optional[float] = Field(None, description="Optimization score")
    
    model_config = ConfigDict(from_attributes=True)