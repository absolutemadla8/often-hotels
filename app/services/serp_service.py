import asyncio
import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum

import httpx
from pydantic import BaseModel, Field

from app.core.config import settings


logger = logging.getLogger(__name__)


class SortBy(Enum):
    """Hotel search sort options"""
    RELEVANCE = None
    LOWEST_PRICE = 3
    HIGHEST_RATING = 8
    MOST_REVIEWED = 13


class Rating(Enum):
    """Hotel rating filter options"""
    THREE_FIVE_PLUS = 7
    FOUR_PLUS = 8
    FOUR_FIVE_PLUS = 9


class HotelClass(Enum):
    """Hotel class filter options"""
    TWO_STAR = 2
    THREE_STAR = 3
    FOUR_STAR = 4
    FIVE_STAR = 5


@dataclass
class SearchCriteria:
    """Hotel search criteria"""
    query: str
    check_in_date: date
    check_out_date: date
    adults: int = 2
    children: int = 0
    children_ages: Optional[List[int]] = None
    gl: str = "us"  # country
    hl: str = "en"  # language
    currency: str = "USD"
    sort_by: Optional[SortBy] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    rating: Optional[Rating] = None
    hotel_class: Optional[List[HotelClass]] = None
    free_cancellation: Optional[bool] = None
    vacation_rentals: bool = False


class GPSCoordinates(BaseModel):
    latitude: float
    longitude: float


class RateInfo(BaseModel):
    lowest: Optional[str] = None
    extracted_lowest: Optional[float] = None
    before_taxes_fees: Optional[str] = None
    extracted_before_taxes_fees: Optional[float] = None


class PriceSource(BaseModel):
    source: str
    logo: Optional[str] = None
    rate_per_night: RateInfo


class Transportation(BaseModel):
    type: str
    duration: str


class NearbyPlace(BaseModel):
    name: str
    transportations: List[Transportation] = []


class ImageInfo(BaseModel):
    thumbnail: str
    original_image: Optional[str] = None


class ReviewBreakdown(BaseModel):
    name: str
    description: Optional[str] = None
    total_mentioned: Optional[int] = None
    positive: Optional[int] = None
    negative: Optional[int] = None
    neutral: Optional[int] = None


class RatingBreakdown(BaseModel):
    stars: int
    count: int


class PropertyResult(BaseModel):
    """Structured property result from SerpApi"""
    type: str  # "hotel" or "vacation rental"
    name: str
    description: Optional[str] = None
    link: Optional[str] = None
    logo: Optional[str] = None
    sponsored: Optional[bool] = None
    eco_certified: Optional[bool] = None
    gps_coordinates: Optional[GPSCoordinates] = None
    check_in_time: Optional[str] = None
    check_out_time: Optional[str] = None
    rate_per_night: Optional[RateInfo] = None
    total_rate: Optional[RateInfo] = None
    prices: List[PriceSource] = []
    nearby_places: List[NearbyPlace] = []
    hotel_class: Optional[str] = None
    extracted_hotel_class: Optional[int] = None
    images: List[ImageInfo] = []
    overall_rating: Optional[float] = None
    reviews: Optional[int] = None
    ratings: List[RatingBreakdown] = []
    location_rating: Optional[float] = None
    reviews_breakdown: List[ReviewBreakdown] = []
    amenities: List[str] = []
    excluded_amenities: List[str] = []
    essential_info: List[str] = []
    property_token: Optional[str] = None
    serpapi_property_details_link: Optional[str] = None

    # Additional fields for tracking
    search_query: Optional[str] = None
    search_date: Optional[datetime] = None


class AdResult(BaseModel):
    """Structured ad result from SerpApi"""
    name: str
    source: str
    source_icon: Optional[str] = None
    link: Optional[str] = None
    property_token: Optional[str] = None
    serpapi_property_details_link: Optional[str] = None
    gps_coordinates: Optional[GPSCoordinates] = None
    hotel_class: Optional[int] = None
    thumbnail: Optional[str] = None
    overall_rating: Optional[float] = None
    reviews: Optional[int] = None
    price: Optional[str] = None
    extracted_price: Optional[float] = None
    amenities: List[str] = []
    free_cancellation: Optional[bool] = None


class BrandInfo(BaseModel):
    id: int
    name: str
    children: Optional[List['BrandInfo']] = None


class SearchMetadata(BaseModel):
    id: str
    status: str
    json_endpoint: str
    created_at: str
    processed_at: str
    total_time_taken: Union[float, Dict[str, float]]

    @property
    def time_taken(self) -> float:
        if isinstance(self.total_time_taken, dict):
            return self.total_time_taken.get('float', 0.0)
        return self.total_time_taken


class SearchParameters(BaseModel):
    engine: str
    q: str
    gl: str
    hl: str
    currency: str
    check_in_date: str
    check_out_date: str
    adults: int
    children: int


class SearchInformation(BaseModel):
    total_results: Optional[int] = None
    hotels_results_state: Optional[str] = None


class Pagination(BaseModel):
    current_from: Optional[int] = None
    current_to: Optional[int] = None
    next_page_token: Optional[str] = None
    next: Optional[str] = None


class SerpApiResponse(BaseModel):
    """Complete SerpApi Google Hotels response"""
    search_metadata: SearchMetadata
    search_parameters: SearchParameters
    search_information: Optional[SearchInformation] = None
    brands: List[BrandInfo] = []
    ads: List[AdResult] = []
    properties: List[PropertyResult] = []
    serpapi_pagination: Optional[Pagination] = None

    # Property details fields (when showing single property)
    type: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    link: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    phone_link: Optional[str] = None
    property_token: Optional[str] = None
    serpapi_property_details_link: Optional[str] = None


class SerpApiService:
    """Service for interacting with SerpApi Google Hotels API"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://serpapi.com/search.json"
        self.client = httpx.AsyncClient(timeout=30.0)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    def _build_search_params(self, criteria: SearchCriteria) -> Dict[str, Any]:
        """Build search parameters for SerpApi request"""
        params = {
            "engine": "google_hotels",
            "q": criteria.query,
            "check_in_date": criteria.check_in_date.strftime("%Y-%m-%d"),
            "check_out_date": criteria.check_out_date.strftime("%Y-%m-%d"),
            "adults": criteria.adults,
            "children": criteria.children,
            "gl": criteria.gl,
            "hl": criteria.hl,
            "currency": criteria.currency,
            "api_key": self.api_key,
        }

        # Add optional parameters
        if criteria.children_ages:
            params["children_ages"] = ",".join(map(str, criteria.children_ages))

        if criteria.sort_by and criteria.sort_by.value is not None:
            params["sort_by"] = criteria.sort_by.value

        if criteria.min_price:
            params["min_price"] = criteria.min_price

        if criteria.max_price:
            params["max_price"] = criteria.max_price

        if criteria.rating:
            params["rating"] = criteria.rating.value

        if criteria.hotel_class:
            params["hotel_class"] = ",".join([hc.value for hc in criteria.hotel_class])

        if criteria.free_cancellation is not None:
            params["free_cancellation"] = criteria.free_cancellation

        if criteria.vacation_rentals:
            params["vacation_rentals"] = True

        return params

    async def search_hotels(self, criteria: SearchCriteria) -> SerpApiResponse:
        """Search for hotels using SerpApi"""
        params = self._build_search_params(criteria)

        try:
            logger.info(f"Searching hotels with query: {criteria.query}")
            response = await self.client.get(self.base_url, params=params)
            response.raise_for_status()

            data = response.json()

            # Add search metadata to properties for tracking
            search_date = datetime.utcnow()
            for prop in data.get("properties", []):
                prop["search_query"] = criteria.query
                prop["search_date"] = search_date.isoformat()

            return SerpApiResponse(**data)

        except httpx.HTTPError as e:
            logger.error(f"HTTP error during hotel search: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during hotel search: {e}")
            raise

    async def get_property_details(self, property_token: str, criteria: SearchCriteria) -> SerpApiResponse:
        """Get detailed property information"""
        params = self._build_search_params(criteria)
        params["property_token"] = property_token

        try:
            logger.info(f"Getting property details for token: {property_token}")
            response = await self.client.get(self.base_url, params=params)
            response.raise_for_status()

            data = response.json()
            return SerpApiResponse(**data)

        except httpx.HTTPError as e:
            logger.error(f"HTTP error getting property details: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting property details: {e}")
            raise

    async def search_with_pagination(
        self,
        criteria: SearchCriteria,
        max_pages: int = 5
    ) -> List[SerpApiResponse]:
        """Search hotels with automatic pagination"""
        results = []
        next_page_token = None

        for page in range(max_pages):
            params = self._build_search_params(criteria)
            if next_page_token:
                params["next_page_token"] = next_page_token

            try:
                response = await self.client.get(self.base_url, params=params)
                response.raise_for_status()

                data = response.json()

                # Add search metadata to properties
                search_date = datetime.utcnow()
                for prop in data.get("properties", []):
                    prop["search_query"] = criteria.query
                    prop["search_date"] = search_date.isoformat()

                serp_response = SerpApiResponse(**data)
                results.append(serp_response)

                # Check if there's a next page
                if (serp_response.serpapi_pagination and
                    serp_response.serpapi_pagination.next_page_token):
                    next_page_token = serp_response.serpapi_pagination.next_page_token
                    logger.info(f"Found next page token, continuing to page {page + 2}")
                else:
                    logger.info(f"No more pages available, stopping at page {page + 1}")
                    break

            except httpx.HTTPError as e:
                logger.error(f"HTTP error during paginated search page {page + 1}: {e}")
                break
            except Exception as e:
                logger.error(f"Unexpected error during paginated search page {page + 1}: {e}")
                break

        return results

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


def get_serp_service() -> SerpApiService:
    """Get configured SerpApi service instance"""
    api_key = getattr(settings, 'SERP_API_KEY', None)
    if not api_key:
        raise ValueError("SERP_API_KEY not configured in settings")

    return SerpApiService(api_key=api_key)


# Fix forward reference
BrandInfo.model_rebuild()