"""
Location search API endpoints

Provides unified search across destinations and areas with pagination,
filtering, and detailed location information.
"""

from typing import Optional, Literal
from fastapi import APIRouter, Query, Depends, HTTPException, status
import logging

from app.services.location_search_service import get_location_search_service, LocationSearchService
from app.schemas.location import LocationSearchResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/search", response_model=LocationSearchResponse)
async def search_locations(
    q: str = Query(..., min_length=2, max_length=100, description="Search keyword for locations"),
    page: int = Query(1, ge=1, le=1000, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Results per page"),
    type: Optional[Literal["destination", "area"]] = Query(None, description="Filter by location type"),
    country_id: Optional[int] = Query(None, ge=1, description="Filter by country ID"),
    tracking_only: bool = Query(False, description="Show only tracking-enabled locations"),
    search_service: LocationSearchService = Depends(get_location_search_service)
) -> LocationSearchResponse:
    """
    Search for locations (destinations and areas) with pagination
    
    **Search Features:**
    - Searches across both destinations and areas
    - Fuzzy matching on name, display_name, and description
    - Relevance-based sorting (exact match → starts with → contains)
    - Proper pagination with metadata
    - Type filtering (destination/area)
    - Country and tracking status filtering
    
    **Response includes:**
    - Clear type indication ("destination" or "area")
    - Complete location details with coordinates
    - Parent destination info for areas
    - Country information
    - Areas count for destinations
    - Pagination metadata
    """
    try:
        # Validate parameters
        search_keyword = q.strip()
        if len(search_keyword) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Search keyword must be at least 2 characters"
            )
        
        logger.info(f"Location search request: '{search_keyword}', page={page}, per_page={per_page}, type={type}")
        
        # Perform search
        results, pagination, filters = await search_service.search_locations(
            search_keyword=search_keyword,
            page=page,
            per_page=per_page,
            location_type=type,
            country_id=country_id,
            tracking_only=tracking_only
        )
        
        # Build response
        response = LocationSearchResponse(
            success=True,
            results=results,
            pagination=pagination,
            filters_applied=filters,
            message=f"Found {pagination.total} locations matching '{search_keyword}'"
        )
        
        logger.info(f"Location search completed: {len(results)} results returned")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Location search failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Location search failed: {str(e)}"
        )


@router.get("/destinations", response_model=LocationSearchResponse)
async def search_destinations_only(
    q: str = Query(..., min_length=2, max_length=100, description="Search keyword for destinations"),
    page: int = Query(1, ge=1, le=1000, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Results per page"),
    country_id: Optional[int] = Query(None, ge=1, description="Filter by country ID"),
    tracking_only: bool = Query(False, description="Show only tracking-enabled destinations"),
    search_service: LocationSearchService = Depends(get_location_search_service)
) -> LocationSearchResponse:
    """
    Search destinations only
    
    Convenience endpoint for searching only destinations (not areas).
    Same functionality as the main search endpoint but with type="destination" pre-applied.
    """
    return await search_locations(
        q=q,
        page=page,
        per_page=per_page,
        type="destination",
        country_id=country_id,
        tracking_only=tracking_only,
        search_service=search_service
    )


@router.get("/areas", response_model=LocationSearchResponse)
async def search_areas_only(
    q: str = Query(..., min_length=2, max_length=100, description="Search keyword for areas"),
    page: int = Query(1, ge=1, le=1000, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Results per page"),
    country_id: Optional[int] = Query(None, ge=1, description="Filter by country ID"),
    tracking_only: bool = Query(False, description="Show only tracking-enabled areas"),
    search_service: LocationSearchService = Depends(get_location_search_service)
) -> LocationSearchResponse:
    """
    Search areas only
    
    Convenience endpoint for searching only areas (not destinations).
    Same functionality as the main search endpoint but with type="area" pre-applied.
    """
    return await search_locations(
        q=q,
        page=page,
        per_page=per_page,
        type="area",
        country_id=country_id,
        tracking_only=tracking_only,
        search_service=search_service
    )


@router.get("/tracking", response_model=LocationSearchResponse)
async def search_tracking_locations(
    q: str = Query(..., min_length=2, max_length=100, description="Search keyword for tracking locations"),
    page: int = Query(1, ge=1, le=1000, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Results per page"),
    type: Optional[Literal["destination", "area"]] = Query(None, description="Filter by location type"),
    country_id: Optional[int] = Query(None, ge=1, description="Filter by country ID"),
    search_service: LocationSearchService = Depends(get_location_search_service)
) -> LocationSearchResponse:
    """
    Search tracking-enabled locations only
    
    Convenience endpoint for searching only locations that have tracking enabled.
    Useful for admin interfaces that need to show only trackable locations.
    """
    return await search_locations(
        q=q,
        page=page,
        per_page=per_page,
        type=type,
        country_id=country_id,
        tracking_only=True,
        search_service=search_service
    )