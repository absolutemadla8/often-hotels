from typing import Any, List, Optional
from datetime import date
from decimal import Decimal
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse

from app import models, schemas
from app.models.models import User, Hotel, UniversalPriceHistory, Destination, Area
from app.api.tortoise_deps import get_optional_current_user, get_current_verified_user, get_current_superuser
from app.schemas.itinerary import HotelSearchRequest, HotelSearchResponse, HotelAvailabilityInfo, DateRange
from app.core.data_filter import filter_by_user_access, create_filtered_response

router = APIRouter()


@router.get("/search")
async def search_hotels(
    destination_ids: str = Query(..., description="Destination IDs (comma-separated for multiple)"),
    area_ids: Optional[str] = Query(None, description="Area IDs (comma-separated for multiple, optional)"),
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    currency: str = Query("USD", description="Currency code"),
    current_user: Optional[User] = Depends(get_optional_current_user),
) -> JSONResponse:
    """
    Search hotels by destination(s)/area(s) and date range.
    
    Returns hotels with availability and pricing information for the specified period.
    Supports searching across multiple destinations and areas simultaneously.
    Helps users select preferred hotels for itinerary optimization.
    
    Args:
        destination_ids: Comma-separated list of destination IDs (e.g., "1,2,3")
        area_ids: Optional comma-separated list of area IDs (e.g., "1,2")
        start_date: Check-in date
        end_date: Check-out date
        currency: Currency code for pricing
    """
    
    # Validate date range
    if end_date <= start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End date must be after start date"
        )
    
    # Parse destination IDs
    try:
        destination_id_list = [int(x.strip()) for x in destination_ids.split(",") if x.strip()]
        if not destination_id_list:
            raise ValueError("No destination IDs provided")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid destination IDs format: {str(e)}"
        )
    
    # Parse area IDs if provided
    area_id_list = []
    if area_ids:
        try:
            area_id_list = [int(x.strip()) for x in area_ids.split(",") if x.strip()]
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid area IDs format: {str(e)}"
            )
    
    # Verify destinations exist
    existing_destinations = await Destination.filter(id__in=destination_id_list).all()
    if len(existing_destinations) != len(destination_id_list):
        found_dest_ids = {dest.id for dest in existing_destinations}
        missing_dest_ids = set(destination_id_list) - found_dest_ids
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Destinations not found: {list(missing_dest_ids)}"
        )
    
    # Verify areas exist if provided
    existing_areas = []
    if area_id_list:
        existing_areas = await Area.filter(id__in=area_id_list).all()
        if len(existing_areas) != len(area_id_list):
            found_area_ids = {area.id for area in existing_areas}
            missing_area_ids = set(area_id_list) - found_area_ids
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Areas not found: {list(missing_area_ids)}"
            )
    
    # Build hotel query for multiple destinations
    hotel_query = Hotel.filter(destination_id__in=destination_id_list, is_active=True)
    if area_id_list:
        hotel_query = hotel_query.filter(area_id__in=area_id_list)
    
    hotels = await hotel_query.all()
    
    if not hotels:
        # Create a unified response for multiple destinations/areas
        destination_names = [dest.name for dest in existing_destinations]
        area_names = [area.name for area in existing_areas] if existing_areas else []
        
        response_data = {
            "destination_ids": destination_id_list,
            "destination_names": destination_names,
            "area_ids": area_id_list if area_id_list else None,
            "area_names": area_names if area_names else None,
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "currency": currency,
            "total_hotels_found": 0,
            "hotels_full_coverage": 0,
            "hotels": [],
            "search_summary": {
                "destinations_searched": len(destination_id_list),
                "areas_searched": len(area_id_list) if area_id_list else 0,
                "total_locations": len(destination_id_list) + len(area_id_list)
            }
        }
        return create_filtered_response(
            data=response_data,
            user=current_user,
            endpoint_path="/hotels/search"
        )
    
    # Get price data for all hotels in the date range
    hotel_ids = [hotel.id for hotel in hotels]
    
    price_query = UniversalPriceHistory.filter(
        trackable_id__in=hotel_ids,
        price_date__gte=start_date,
        price_date__lte=end_date,
        currency=currency,
        is_available=True
    ).order_by('trackable_id', 'price_date', '-recorded_at')
    
    price_records = await price_query.all()
    
    # Group prices by hotel and date (using latest recorded price for each date)
    hotel_prices = defaultdict(dict)
    for record in price_records:
        hotel_id = record.trackable_id
        date_str = record.price_date.isoformat()
        
        # Use most recent price for each date
        if (date_str not in hotel_prices[hotel_id] or 
            record.recorded_at > hotel_prices[hotel_id][date_str]['recorded_at']):
            hotel_prices[hotel_id][date_str] = {
                'price': record.price,
                'recorded_at': record.recorded_at
            }
    
    # Generate date range for checking coverage
    from datetime import timedelta
    date_range = []
    current_date = start_date
    while current_date <= end_date:
        date_range.append(current_date.isoformat())
        current_date = current_date + timedelta(days=1)
    
    total_nights = len(date_range)
    
    # Build response for each hotel
    hotel_availability_list = []
    hotels_with_full_coverage = 0
    
    for hotel in hotels:
        hotel_id = hotel.id
        hotel_date_prices = hotel_prices.get(hotel_id, {})
        
        if not hotel_date_prices:
            continue  # Skip hotels with no price data
        
        available_dates = []
        prices = []
        
        for date_str in date_range:
            if date_str in hotel_date_prices:
                available_dates.append(date.fromisoformat(date_str))
                prices.append(hotel_date_prices[date_str]['price'])
        
        if not prices:
            continue  # Skip if no prices available
        
        covers_full_range = len(available_dates) == total_nights
        if covers_full_range:
            hotels_with_full_coverage += 1
        
        min_price = min(prices)
        max_price = max(prices)
        avg_price = sum(prices) / len(prices)
        
        hotel_info = HotelAvailabilityInfo(
            hotel_id=hotel_id,
            hotel_name=hotel.name,
            star_rating=hotel.star_rating,
            guest_rating=hotel.guest_rating,
            available_dates=available_dates,
            price_range={"min": min_price, "max": max_price},
            avg_price=Decimal(str(round(avg_price, 2))),
            total_nights_available=len(available_dates),
            covers_full_range=covers_full_range,
            currency=currency
        )
        
        hotel_availability_list.append(hotel_info)
    
    # Sort hotels: full coverage first, then by average price
    hotel_availability_list.sort(
        key=lambda h: (not h.covers_full_range, h.avg_price)
    )
    
    # Create unified response for multiple destinations/areas
    destination_names = [dest.name for dest in existing_destinations]
    area_names = [area.name for area in existing_areas] if existing_areas else []
    
    response_data = {
        "destination_ids": destination_id_list,
        "destination_names": destination_names,
        "area_ids": area_id_list if area_id_list else None,
        "area_names": area_names if area_names else None,
        "date_range": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        },
        "currency": currency,
        "total_hotels_found": len(hotel_availability_list),
        "hotels_full_coverage": hotels_with_full_coverage,
        "hotels": [hotel.model_dump() for hotel in hotel_availability_list],
        "search_summary": {
            "destinations_searched": len(destination_id_list),
            "areas_searched": len(area_id_list) if area_id_list else 0,
            "total_locations": len(destination_id_list) + len(area_id_list),
            "hotels_per_destination": {
                dest.name: len([h for h in hotels if h.destination_id == dest.id])
                for dest in existing_destinations
            },
            "hotels_per_area": {
                area.name: len([h for h in hotels if h.area_id == area.id])
                for area in existing_areas
            } if existing_areas else {}
        }
    }
    
    # Apply user access filtering
    return create_filtered_response(
        data=response_data,
        user=current_user,
        endpoint_path="/hotels/search"
    )


@router.get("/{hotel_id}")
async def get_hotel_details(
    hotel_id: int,
    current_user: Optional[User] = Depends(get_optional_current_user),
) -> Any:
    """
    Get detailed information about a specific hotel.
    """
    hotel = await Hotel.get_or_none(id=hotel_id)
    if not hotel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hotel not found"
        )
    
    # Get destination and area info
    destination = await Destination.get_or_none(id=hotel.destination_id)
    area = await Area.get_or_none(id=hotel.area_id) if hotel.area_id else None
    
    return {
        "hotel": {
            "id": hotel.id,
            "name": hotel.name,
            "destination_id": hotel.destination_id,
            "destination_name": destination.name if destination else None,
            "area_id": hotel.area_id,
            "area_name": area.name if area else None,
            "star_rating": hotel.star_rating,
            "guest_rating": hotel.guest_rating,
            "description": hotel.short_description,
            "amenities": hotel.amenities,
            "is_active": hotel.is_active,
            "partner_name": hotel.partner_name,
            "external_id": hotel.external_id
        }
    }


@router.get("/")
async def list_hotels(
    destination_id: Optional[int] = Query(None, description="Filter by destination ID"),
    area_id: Optional[int] = Query(None, description="Filter by area ID"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    current_user: Optional[User] = Depends(get_optional_current_user),
) -> Any:
    """
    List hotels with optional filtering by destination/area.
    """
    query = Hotel.filter(is_active=True)
    
    if destination_id:
        query = query.filter(destination_id=destination_id)
    
    if area_id:
        query = query.filter(area_id=area_id)
    
    total = await query.count()
    hotels = await query.offset(skip).limit(limit).all()
    
    return {
        "hotels": [
            {
                "id": hotel.id,
                "name": hotel.name,
                "destination_id": hotel.destination_id,
                "area_id": hotel.area_id,
                "star_rating": hotel.star_rating,
                "guest_rating": hotel.guest_rating,
                "partner_name": hotel.partner_name
            }
            for hotel in hotels
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }