"""
Location search response schemas
"""
from typing import Optional, List, Dict, Any, Literal, Union
from pydantic import BaseModel, Field


class CountryInfo(BaseModel):
    """Country information for location results"""
    id: int
    name: str
    iso_code_2: str
    iso_code_3: str


class DestinationInfo(BaseModel):
    """Parent destination information for area results"""
    id: int
    name: str
    display_name: Optional[str] = None


class BaseLocationResult(BaseModel):
    """Base location result with common fields"""
    id: int
    name: str
    display_name: Optional[str] = None
    local_name: Optional[str] = None
    description: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_active: bool = True
    is_popular: bool = False
    tracking: bool = False
    country: CountryInfo


class DestinationResult(BaseLocationResult):
    """Destination search result"""
    type: Literal["destination"] = "destination"
    destination_type: str = "city"
    tourist_rating: Optional[float] = None
    population: Optional[int] = None
    area_km2: Optional[float] = None
    timezone: Optional[str] = None
    numberofdaystotrack: Optional[int] = None
    # Areas count for this destination
    areas_count: int = 0


class AreaResult(BaseLocationResult):
    """Area search result"""
    type: Literal["area"] = "area"
    area_type: str = "district"
    area_level: int = 1
    walkability_score: Optional[float] = None
    hotel_density: Optional[str] = None
    # Parent destination information
    destination: DestinationInfo


# Union type for search results (flat structure - for backward compatibility)
LocationSearchResult = Union[DestinationResult, AreaResult]


# New hierarchical schemas for tree structure
class AreaInDestination(BaseModel):
    """Area within a destination for hierarchical response"""
    id: int
    name: str
    display_name: Optional[str] = None
    local_name: Optional[str] = None
    description: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_active: bool = True
    is_popular: bool = False
    tracking: bool = False
    area_type: str = "district"
    area_level: int = 1
    walkability_score: Optional[float] = None
    hotel_density: Optional[str] = None


class DestinationWithAreas(BaseModel):
    """Destination with its areas for hierarchical response"""
    id: int
    name: str
    display_name: Optional[str] = None
    local_name: Optional[str] = None
    description: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_active: bool = True
    is_popular: bool = False
    tracking: bool = False
    destination_type: str = "city"
    tourist_rating: Optional[float] = None
    population: Optional[int] = None
    area_km2: Optional[float] = None
    timezone: Optional[str] = None
    numberofdaystotrack: Optional[int] = None
    areas: List[AreaInDestination] = []


class CountryWithDestinations(BaseModel):
    """Country with its destinations and areas for hierarchical response"""
    country: CountryInfo
    destinations: List[DestinationWithAreas] = []


class PaginationMeta(BaseModel):
    """Pagination metadata"""
    page: int = Field(..., ge=1, description="Current page number")
    per_page: int = Field(..., ge=1, le=100, description="Results per page")
    total: int = Field(..., ge=0, description="Total number of results")
    pages: int = Field(..., ge=0, description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")


class SearchFilters(BaseModel):
    """Applied search filters"""
    search_keyword: str
    type: Optional[Literal["destination", "area"]] = None
    country_iso: Optional[str] = None
    tracking_only: bool = False


class LocationSearchResponse(BaseModel):
    """Paginated location search response with hierarchical structure"""
    success: bool = True
    results: List[CountryWithDestinations]  # New hierarchical structure
    # Keep flat results for backward compatibility if needed
    flat_results: Optional[List[LocationSearchResult]] = None
    pagination: PaginationMeta
    filters_applied: SearchFilters
    message: Optional[str] = None


class LocationSearchParams(BaseModel):
    """Search parameters validation"""
    q: str = Field(..., min_length=2, max_length=100, description="Search keyword")
    page: int = Field(1, ge=1, le=1000, description="Page number")
    per_page: int = Field(20, ge=1, le=100, description="Results per page")
    type: Optional[Literal["destination", "area"]] = Field(None, description="Filter by location type")
    country_iso: Optional[str] = Field(None, min_length=2, max_length=3, description="Filter by country ISO code")
    tracking_only: bool = Field(False, description="Show only tracking-enabled locations")