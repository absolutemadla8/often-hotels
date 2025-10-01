from typing import Any, List, Optional
from datetime import date
from decimal import Decimal
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse

from app import models, schemas
from app.models.models import User, Hotel, UniversalPriceHistory, Destination, Area
from app.api.tortoise_deps import get_optional_current_user, get_current_verified_user, get_current_superuser
from app.schemas.itinerary import (
    HotelSearchRequest, HotelSearchResponse, HotelAvailabilityInfo, DateRange,
    PaginatedHotelSearchResponse, HotelAvailabilityInfoEnhanced, PaginationMeta,
    SearchMetadata, SortingInfo, HotelSearchSummary
)
from app.core.data_filter import filter_by_user_access, create_filtered_response

router = APIRouter()


@router.get("/search")
async def search_hotels(
    destination_ids: str = Query(..., description="Destination IDs (comma-separated for multiple)"),
    area_ids: Optional[str] = Query(None, description="Area IDs (comma-separated for multiple, optional)"),
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    currency: str = Query("USD", description="Currency code"),
    # New search and pagination parameters
    search: Optional[str] = Query(None, description="Hotel name search query (empty for all hotels)"),
    page: int = Query(1, ge=1, le=1000, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Results per page"),
    sort_by: str = Query("relevance", description="Sort by: relevance, price_asc, price_desc, rating, name"),
    current_user: Optional[User] = Depends(get_optional_current_user),
) -> JSONResponse:
    """
    Enhanced hotel search with pagination, fuzzy matching, and sorting.
    
    Returns hotels with availability and pricing information for the specified period.
    Supports searching across multiple destinations and areas with text search capabilities.
    
    Features:
    - Text search with fuzzy matching on hotel names
    - Pagination for large hotel datasets
    - Multiple sorting options (relevance, price, rating, name)
    - Empty search loads all hotels with pagination
    - Search relevance scoring for better results
    
    Args:
        destination_ids: Comma-separated destination IDs (e.g., "1,2,3")
        area_ids: Optional comma-separated area IDs (e.g., "1,2")
        start_date: Check-in date
        end_date: Check-out date
        currency: Currency code for pricing
        search: Hotel name search query (None/empty for all hotels)
        page: Page number (1-based)
        per_page: Results per page (1-100)
        sort_by: Sort order (relevance/price_asc/price_desc/rating/name)
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
    
    # Build base hotel query for multiple destinations
    hotel_query = Hotel.filter(destination_id__in=destination_id_list, is_active=True)
    if area_id_list:
        hotel_query = hotel_query.filter(area_id__in=area_id_list)
    
    # Implement search and fuzzy matching
    import time
    search_start_time = time.time()
    
    # Store original query for counting
    base_hotels_count = await hotel_query.count()
    search_query_normalized = search.strip() if search else None
    query_type = "empty"
    
    # Apply text search if provided
    if search_query_normalized:
        if len(search_query_normalized) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Search query must be at least 2 characters long"
            )
        
        # Try exact match first
        exact_match_query = hotel_query.filter(name__iexact=search_query_normalized)
        exact_count = await exact_match_query.count()
        
        if exact_count > 0:
            hotel_query = exact_match_query
            query_type = "exact"
        else:
            # Try partial match (case-insensitive LIKE)
            partial_match_query = hotel_query.filter(name__icontains=search_query_normalized)
            partial_count = await partial_match_query.count()
            
            if partial_count > 0:
                hotel_query = partial_match_query
                query_type = "partial"
            else:
                # Use fuzzy matching with PostgreSQL similarity
                # Note: This requires pg_trgm extension in PostgreSQL
                from tortoise.expressions import RawSQL
                
                # Calculate similarity score and filter by minimum threshold
                similarity_threshold = 0.3
                hotel_query = hotel_query.annotate(
                    similarity_score=RawSQL(f"similarity(name, '{search_query_normalized}')")
                ).filter(
                    similarity_score__gte=similarity_threshold
                ).order_by('-similarity_score')
                
                query_type = "fuzzy"
    
    # Get total count after search filtering
    total_filtered_hotels = await hotel_query.count()
    
    # Apply pagination
    offset = (page - 1) * per_page
    paginated_query = hotel_query.offset(offset).limit(per_page)
    
    # Apply sorting (before executing query)
    available_sorts = ["relevance", "price_asc", "price_desc", "rating", "name"]
    if sort_by not in available_sorts:
        sort_by = "relevance"
    
    if sort_by == "name":
        paginated_query = paginated_query.order_by('name')
    elif sort_by == "rating":
        paginated_query = paginated_query.order_by('-guest_rating', '-star_rating')
    # Note: price sorting will be applied after price data is loaded
    # relevance sorting is handled in fuzzy search above
    
    hotels = await paginated_query.all()
    
    search_time_ms = (time.time() - search_start_time) * 1000
    
    # Calculate pagination metadata
    total_pages = (total_filtered_hotels + per_page - 1) // per_page
    has_next = page < total_pages
    has_prev = page > 1
    
    pagination_meta = PaginationMeta(
        page=page,
        per_page=per_page,
        total=total_filtered_hotels,
        pages=total_pages,
        has_next=has_next,
        has_prev=has_prev
    )
    
    if not hotels:
        # Create empty response with pagination
        destination_names = [dest.name for dest in existing_destinations]
        area_names = [area.name for area in existing_areas] if existing_areas else []
        
        search_metadata = SearchMetadata(
            query=search_query_normalized,
            query_type=query_type,
            total_before_search=base_hotels_count,
            search_time_ms=search_time_ms
        )
        
        sorting_info = SortingInfo(
            sort_by=sort_by,
            sort_order="asc" if sort_by in ["name", "price_asc"] else "desc",
            available_sorts=available_sorts
        )
        
        search_summary = HotelSearchSummary(
            destinations_searched=len(destination_id_list),
            areas_searched=len(area_id_list) if area_id_list else 0,
            total_locations=len(destination_id_list) + len(area_id_list),
            hotels_per_destination={dest.name: 0 for dest in existing_destinations},
            hotels_per_area={area.name: 0 for area in existing_areas} if existing_areas else {},
            price_range_summary={"min": None, "max": None, "currency": currency}
        )
        
        response_data = PaginatedHotelSearchResponse(
            destination_ids=destination_id_list,
            destination_names=destination_names,
            area_ids=area_id_list if area_id_list else None,
            area_names=area_names if area_names else None,
            date_range={
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            currency=currency,
            search_metadata=search_metadata,
            pagination=pagination_meta,
            sorting=sorting_info,
            hotels=[],
            hotels_full_coverage=0,
            search_summary=search_summary
        )
        
        return create_filtered_response(
            data=response_data.model_dump(),
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
        
        # Calculate search relevance score
        relevance_score = None
        match_type = None
        
        if search_query_normalized:
            if query_type == "exact":
                relevance_score = 1.0
                match_type = "exact"
            elif query_type == "partial":
                # Calculate partial match score based on position and length
                name_lower = hotel.name.lower()
                query_lower = search_query_normalized.lower()
                if name_lower.startswith(query_lower):
                    relevance_score = 0.9
                elif query_lower in name_lower:
                    relevance_score = 0.7
                else:
                    relevance_score = 0.5
                match_type = "partial"
            elif query_type == "fuzzy":
                # Fuzzy match score is already calculated in the query
                relevance_score = 0.3  # Minimum threshold
                match_type = "fuzzy"
        
        # Get destination and area names for this hotel
        hotel_destination = next((dest for dest in existing_destinations if dest.id == hotel.destination_id), None)
        hotel_area = next((area for area in existing_areas if area.id == hotel.area_id), None) if hotel.area_id else None
        
        hotel_info = HotelAvailabilityInfoEnhanced(
            hotel_id=hotel_id,
            hotel_name=hotel.name,
            star_rating=hotel.star_rating,
            guest_rating=hotel.guest_rating,
            available_dates=available_dates,
            price_range={"min": min_price, "max": max_price},
            avg_price=Decimal(str(round(avg_price, 2))),
            total_nights_available=len(available_dates),
            covers_full_range=covers_full_range,
            currency=currency,
            relevance_score=relevance_score,
            match_type=match_type,
            destination_name=hotel_destination.name if hotel_destination else "Unknown",
            area_name=hotel_area.name if hotel_area else None
        )
        
        hotel_availability_list.append(hotel_info)
    
    # Apply sorting based on user preference
    if sort_by == "price_asc":
        hotel_availability_list.sort(key=lambda h: (not h.covers_full_range, h.avg_price))
    elif sort_by == "price_desc":
        hotel_availability_list.sort(key=lambda h: (not h.covers_full_range, -h.avg_price))
    elif sort_by == "rating":
        hotel_availability_list.sort(key=lambda h: (not h.covers_full_range, -(h.guest_rating or 0), -(h.star_rating or 0)))
    elif sort_by == "name":
        hotel_availability_list.sort(key=lambda h: (not h.covers_full_range, h.hotel_name.lower()))
    elif sort_by == "relevance":
        if search_query_normalized:
            # Sort by relevance score descending, then full coverage, then price
            hotel_availability_list.sort(key=lambda h: (-(h.relevance_score or 0), not h.covers_full_range, h.avg_price))
        else:
            # Default sort when no search: full coverage first, then price
            hotel_availability_list.sort(key=lambda h: (not h.covers_full_range, h.avg_price))
    
    # Calculate price range summary
    all_prices = [float(h.avg_price) for h in hotel_availability_list]
    price_range_summary = {
        "min": min(all_prices) if all_prices else None,
        "max": max(all_prices) if all_prices else None,
        "currency": currency,
        "count": len(all_prices)
    }
    
    # Calculate relevance score range for search metadata
    relevance_scores = [h.relevance_score for h in hotel_availability_list if h.relevance_score is not None]
    min_relevance = min(relevance_scores) if relevance_scores else None
    max_relevance = max(relevance_scores) if relevance_scores else None
    
    # Create response components
    destination_names = [dest.name for dest in existing_destinations]
    area_names = [area.name for area in existing_areas] if existing_areas else []
    
    search_metadata = SearchMetadata(
        query=search_query_normalized,
        query_type=query_type,
        min_relevance_score=min_relevance,
        max_relevance_score=max_relevance,
        total_before_search=base_hotels_count,
        search_time_ms=search_time_ms
    )
    
    sorting_info = SortingInfo(
        sort_by=sort_by,
        sort_order="asc" if sort_by in ["name", "price_asc"] else "desc",
        available_sorts=available_sorts
    )
    
    search_summary = HotelSearchSummary(
        destinations_searched=len(destination_id_list),
        areas_searched=len(area_id_list) if area_id_list else 0,
        total_locations=len(destination_id_list) + len(area_id_list),
        hotels_per_destination={
            dest.name: len([h for h in hotel_availability_list if h.destination_name == dest.name])
            for dest in existing_destinations
        },
        hotels_per_area={
            area.name: len([h for h in hotel_availability_list if h.area_name == area.name])
            for area in existing_areas
        } if existing_areas else {},
        price_range_summary=price_range_summary
    )
    
    response_data = PaginatedHotelSearchResponse(
        destination_ids=destination_id_list,
        destination_names=destination_names,
        area_ids=area_id_list if area_id_list else None,
        area_names=area_names if area_names else None,
        date_range={
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        },
        currency=currency,
        search_metadata=search_metadata,
        pagination=pagination_meta,
        sorting=sorting_info,
        hotels=hotel_availability_list,
        hotels_full_coverage=hotels_with_full_coverage,
        search_summary=search_summary
    )
    
    # Apply user access filtering
    return create_filtered_response(
        data=response_data.model_dump(),
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