from typing import Dict, Any, List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import User
from app.services.travclan_api_service import travclan_api_service
from app.services.hotel_service import HotelService

router = APIRouter()


class OccupancyRequest(BaseModel):
    numOfAdults: int = Field(..., ge=1, le=10, description="Number of adults")
    childAges: Optional[List[int]] = Field(default=[], description="Ages of children")


class HotelSearchRequest(BaseModel):
    checkIn: date = Field(..., description="Check-in date")
    checkOut: date = Field(..., description="Check-out date")
    nationality: str = Field(..., min_length=2, max_length=2, description="Nationality code (2 letters)")
    locationId: Optional[int] = Field(None, description="Location ID for search")
    occupancies: List[OccupancyRequest] = Field(..., min_length=1, description="Room occupancy details")
    page: Optional[int] = Field(default=1, ge=1, description="Page number")
    hotelIds: Optional[List[str]] = Field(None, description="Specific hotel IDs to search")
    sortBy: Optional[List[str]] = Field(None, description="Sort criteria")
    
    @field_validator('checkOut')
    @classmethod
    def validate_dates(cls, v, info):
        if v and info.data.get('checkIn') and v <= info.data['checkIn']:
            raise ValueError('Check-out date must be after check-in date')
        return v
    
    @field_validator('checkIn')
    @classmethod
    def validate_check_in_future(cls, v):
        from datetime import date
        if v and v <= date.today():
            raise ValueError('Check-in date must be in the future')
        return v


class FilterByRequest(BaseModel):
    priceRange: Optional[Dict[str, int]] = None
    starRatings: Optional[List[int]] = None
    facilities: Optional[List[str]] = None
    rateOptions: Optional[Dict[str, bool]] = None


@router.post("/search")
async def search_hotels(
    request: HotelSearchRequest,
    filterBy: Optional[FilterByRequest] = None,
    onlyFilter: Optional[bool] = Query(False, description="Only apply filters to existing results"),
    store_price_history: Optional[bool] = Query(True, description="Store price history data"),
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(deps.get_db)
) -> Dict[str, Any]:
    """
    Search for hotels
    
    Search for available hotels based on location, dates, and occupancy.
    Also stores price history data for tracking price changes over time.
    """
    try:
        # Convert request to dict for API service
        search_data = request.model_dump()
        
        # Add filter data if provided
        if filterBy:
            search_data['filterBy'] = filterBy.model_dump(exclude_none=True)
        
        # Use async context manager for the API service
        async with travclan_api_service:
            response = await travclan_api_service.search_hotels(search_data)
        
        # Store price history data if enabled
        stored_price_histories = []
        if store_price_history:
            try:
                hotel_service = HotelService(db)
                stored_price_histories = await hotel_service.process_hotel_search_results(
                    search_request=search_data,
                    search_response=response
                )
            except Exception as e:
                # Log error but don't fail the search
                import logging
                logging.getLogger(__name__).error(f"Failed to store price history: {e}")
        
        # Process the results for API response
        processed_data = process_hotel_results(response, current_user)
        
        # Apply filters if needed
        if filterBy:
            processed_data = apply_filters(processed_data, filterBy)
        
        # Add metadata about stored price histories
        processed_data['price_histories_stored'] = len(stored_price_histories)
        
        return {
            "status": "success",
            "data": processed_data
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hotel search failed: {str(e)}")


@router.get("/static-content/{hotel_id}")
async def get_hotel_static_content(
    hotel_id: str,
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(deps.get_db)
) -> Dict[str, Any]:
    """
    Get hotel static content
    
    Retrieve detailed static information about a specific hotel
    """
    try:
        async with travclan_api_service:
            response = await travclan_api_service.get_hotel_static_content(hotel_id)
        
        return {
            "status": "success",
            "data": response
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get hotel static content: {str(e)}")


def process_hotel_results(response: Dict[str, Any], user: User = None) -> Dict[str, Any]:
    """
    Process hotel search results and format them
    """
    useful_facilities = [
        'Free WiFi',
        'Swimming Pool', 
        'Free Breakfast',
        'Free Parking',
        'Airport Shuttle',
        'Fitness Facility',
        'Spa',
        'Restaurant',
        'Laundry Services'
    ]
    
    # Get initial filtered and processed results
    raw_hotels = response.get('results', [{}])[0].get('data', [])
    
    # Filter available hotels with images
    filtered_hotels = [
        hotel for hotel in raw_hotels 
        if hotel.get('isAvailable', False) and hotel.get('heroImage')
    ]
    
    # Remove duplicates based on ID
    unique_hotels = {}
    for hotel in filtered_hotels:
        hotel_id = hotel.get('id')
        if hotel_id and hotel_id not in unique_hotels:
            unique_hotels[hotel_id] = hotel
    
    processed_results = []
    for hotel in unique_hotels.values():
        original_rate = hotel.get('availability', {}).get('rate', {}).get('finalRate', 0)
        currency = hotel.get('availability', {}).get('rate', {}).get('currency', 'INR')
        
        # Basic processing without external dependencies
        final_rate = original_rate
        
        processed_hotel = {
            'id': hotel.get('id'),
            'name': hotel.get('name'),
            'star_rating': hotel.get('starRating'),
            'geoCode': {
                'latitude': hotel.get('geoCode', {}).get('lat'),
                'longitude': hotel.get('geoCode', {}).get('long')
            },
            'address': {
                'line1': hotel.get('contact', {}).get('address', {}).get('line1'),
                'line2': hotel.get('contact', {}).get('address', {}).get('line2'),
                'city': hotel.get('contact', {}).get('address', {}).get('city', {}).get('name'),
                'state': hotel.get('contact', {}).get('address', {}).get('state', {}).get('name'),
                'country': hotel.get('contact', {}).get('address', {}).get('country', {}).get('name'),
                'postal_code': hotel.get('contact', {}).get('address', {}).get('postalCode')
            },
            'facilities': [
                facility.get('name') for facility in hotel.get('facilities', [])
                if facility.get('name') in useful_facilities
            ],
            'reviews': {
                'count': hotel.get('reviews', [{}])[0].get('count'),
                'rating': hotel.get('reviews', [{}])[0].get('rating'),
                'categories': {
                    category.get('category'): category.get('rating')
                    for category in hotel.get('reviews', [{}])[0].get('categoryratings', [])
                }
            },
            'hero_image': hotel.get('heroImage'),
            'distance': hotel.get('distance'),
            'rates': {
                'original_rate': original_rate,
                'final_rate': final_rate,
                'currency': currency,
                'breakdown': {
                    'base_price': original_rate,
                    'fees': [],
                    'taxes': []
                }
            },
            'options': {
                'free_breakfast': hotel.get('availability', {}).get('options', {}).get('freeBreakfast', False),
                'free_cancellation': hotel.get('availability', {}).get('options', {}).get('freeCancellation', False)
            }
        }
        
        processed_results.append(processed_hotel)
    
    return {
        'message': response.get('message'),
        'error': response.get('error'),
        'code': response.get('code'),
        'traceId': response.get('results', [{}])[0].get('traceId'),
        'availableTypes': response.get('results', [{}])[0].get('availableTypes'),
        'availableFacilities': response.get('results', [{}])[0].get('availableFacilities'),
        'currentPage': response.get('results', [{}])[0].get('currentPage', 1),
        'perPage': response.get('results', [{}])[0].get('perPage', 25),
        'previousPage': response.get('results', [{}])[0].get('previousPage'),
        'nextPage': response.get('results', [{}])[0].get('nextPage'),
        'totalCount': response.get('results', [{}])[0].get('totalCount', 0),
        'availableCount': response.get('results', [{}])[0].get('availableCount', 0),
        'totalPages': response.get('results', [{}])[0].get('totalPages', 1),
        'originalCount': len(filtered_hotels),
        'filteredCount': len(processed_results),
        'results': processed_results
    }


def apply_filters(data: Dict[str, Any], filter_by: FilterByRequest) -> Dict[str, Any]:
    """
    Apply filters to hotel search results
    """
    hotels = data.get('results', [])
    
    # Filter by price range
    if filter_by.priceRange:
        min_price = filter_by.priceRange.get('min', 0)
        max_price = filter_by.priceRange.get('max', float('inf'))
        
        hotels = [
            hotel for hotel in hotels
            if min_price <= hotel.get('rates', {}).get('final_rate', 0) <= max_price
        ]
    
    # Filter by star rating
    if filter_by.starRatings:
        hotels = [
            hotel for hotel in hotels
            if hotel.get('star_rating') in filter_by.starRatings
        ]
    
    # Filter by facilities
    if filter_by.facilities:
        hotels = [
            hotel for hotel in hotels
            if all(facility in hotel.get('facilities', []) for facility in filter_by.facilities)
        ]
    
    # Filter by rate options
    if filter_by.rateOptions:
        if filter_by.rateOptions.get('freeBreakfast'):
            hotels = [
                hotel for hotel in hotels
                if hotel.get('options', {}).get('free_breakfast', False)
            ]
        
        if filter_by.rateOptions.get('freeCancellation'):
            hotels = [
                hotel for hotel in hotels
                if hotel.get('options', {}).get('free_cancellation', False)
            ]
    
    # Update data with filtered results
    data['results'] = hotels
    data['filteredCount'] = len(hotels)
    
    return data