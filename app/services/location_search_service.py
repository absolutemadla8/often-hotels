"""
Location Search Service

Unified search service for Destinations and Areas with pagination,
filtering, and relevance scoring.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple, Literal
from math import ceil

from tortoise.expressions import Q
from tortoise.functions import Count

from app.models.models import Destination, Area, Country
from app.schemas.location import (
    LocationSearchResult, DestinationResult, AreaResult,
    PaginationMeta, SearchFilters, CountryInfo, DestinationInfo
)
from app.services.cache_service import get_cache_service

logger = logging.getLogger(__name__)


class LocationSearchService:
    """Service for searching across destinations and areas"""
    
    def __init__(self):
        self.max_per_page = 100
        self.default_per_page = 20
    
    async def search_locations(
        self,
        search_keyword: str,
        page: int = 1,
        per_page: int = 20,
        location_type: Optional[Literal["destination", "area"]] = None,
        country_id: Optional[int] = None,
        tracking_only: bool = False
    ) -> Tuple[List[LocationSearchResult], PaginationMeta, SearchFilters]:
        """
        Search locations across destinations and areas with pagination
        
        Args:
            search_keyword: Search term
            page: Page number (1-based)
            per_page: Results per page
            location_type: Filter by type ("destination" or "area")
            country_id: Filter by country ID
            tracking_only: Only show tracking-enabled locations
            
        Returns:
            Tuple of (results, pagination_meta, filters_applied)
        """
        # Validate and sanitize parameters
        per_page = min(max(per_page, 1), self.max_per_page)
        page = max(page, 1)
        search_keyword = search_keyword.strip()
        
        logger.info(f"Searching locations: '{search_keyword}', page={page}, per_page={per_page}, type={location_type}")
        
        # Try to get cached results first
        cache_service = await get_cache_service()
        cached_result = await cache_service.get_cached_search_results(
            search_keyword=search_keyword,
            page=page,
            per_page=per_page,
            location_type=location_type,
            country_id=country_id,
            tracking_only=tracking_only
        )
        
        if cached_result:
            logger.info(f"Cache HIT for location search: '{search_keyword}'")
            # Convert cached data back to proper types
            results = [
                DestinationResult(**item) if item['type'] == 'destination' 
                else AreaResult(**item) for item in cached_result['results']
            ]
            pagination = PaginationMeta(**cached_result['pagination'])
            filters = SearchFilters(**cached_result['filters'])
            return results, pagination, filters
        
        logger.info(f"Cache MISS for location search: '{search_keyword}' - querying database")
        
        # Build search results from database
        results = []
        total_count = 0
        
        if location_type != "area":
            # Search destinations
            destinations, dest_count = await self._search_destinations(
                search_keyword, page, per_page, country_id, tracking_only, location_type
            )
            results.extend(destinations)
            total_count += dest_count
        
        if location_type != "destination":
            # Search areas
            # Adjust pagination for areas if we already have destination results
            area_page = page
            area_per_page = per_page
            
            if location_type is None and len(results) > 0:
                # Mixed search: adjust area pagination based on destination results
                remaining_slots = per_page - len(results)
                if remaining_slots <= 0:
                    areas = []
                    area_count = await self._count_areas(search_keyword, country_id, tracking_only)
                else:
                    areas, area_count = await self._search_areas(
                        search_keyword, 1, remaining_slots, country_id, tracking_only
                    )
            else:
                areas, area_count = await self._search_areas(
                    search_keyword, area_page, area_per_page, country_id, tracking_only
                )
            
            results.extend(areas)
            total_count += area_count
        
        # Sort results by relevance if mixed search
        if location_type is None:
            results = self._sort_by_relevance(results, search_keyword)
        
        # Apply final pagination limit if mixed search returned too many results
        if len(results) > per_page:
            results = results[:per_page]
        
        # Create pagination metadata
        total_pages = ceil(total_count / per_page) if total_count > 0 else 1
        pagination = PaginationMeta(
            page=page,
            per_page=per_page,
            total=total_count,
            pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )
        
        # Create filters metadata
        filters = SearchFilters(
            search_keyword=search_keyword,
            type=location_type,
            country_id=country_id,
            tracking_only=tracking_only
        )
        
        logger.info(f"Found {len(results)} results (total: {total_count}) for '{search_keyword}'")
        
        # Cache the results for future requests (10 minutes TTL)
        await cache_service.cache_search_results(
            search_keyword=search_keyword,
            page=page,
            per_page=per_page,
            results={
                'results': [result.dict() for result in results],
                'pagination': pagination.dict(),
                'filters': filters.dict()
            },
            location_type=location_type,
            country_id=country_id,
            tracking_only=tracking_only
        )
        
        return results, pagination, filters
    
    async def _search_destinations(
        self,
        keyword: str,
        page: int,
        per_page: int,
        country_id: Optional[int],
        tracking_only: bool,
        location_type: Optional[str]
    ) -> Tuple[List[DestinationResult], int]:
        """Search destinations with filters"""
        
        # Build query
        query = Destination.filter(is_active=True)
        
        # Add search conditions
        search_conditions = Q(name__icontains=keyword) | Q(display_name__icontains=keyword)
        if len(keyword) >= 3:  # Include description for longer keywords
            search_conditions |= Q(description__icontains=keyword)
        query = query.filter(search_conditions)
        
        # Apply filters
        if country_id:
            query = query.filter(country_id=country_id)
        if tracking_only:
            query = query.filter(tracking=True)
        
        # Get total count
        total_count = await query.count()
        
        # Apply pagination only for destination-only searches
        if location_type == "destination":
            offset = (page - 1) * per_page
            query = query.offset(offset).limit(per_page)
        else:
            # For mixed searches, get more results and sort later
            query = query.limit(per_page * 2)
        
        # Execute query with relations
        destinations = await query.prefetch_related('country').order_by('name')
        
        # Get areas count for each destination
        destination_ids = [d.id for d in destinations]
        areas_counts = {}
        if destination_ids:
            areas_counts_raw = await Area.filter(
                destination_id__in=destination_ids,
                is_active=True
            ).group_by('destination_id').annotate(count=Count('id')).values('destination_id', 'count')
            areas_counts = {item['destination_id']: item['count'] for item in areas_counts_raw}
        
        # Convert to response models
        results = []
        for dest in destinations:
            result = DestinationResult(
                id=dest.id,
                name=dest.name,
                display_name=dest.display_name,
                local_name=dest.local_name,
                description=dest.description,
                latitude=dest.latitude,
                longitude=dest.longitude,
                is_active=dest.is_active,
                is_popular=dest.is_popular,
                tracking=dest.tracking,
                destination_type=dest.destination_type,
                tourist_rating=dest.tourist_rating,
                population=dest.population,
                area_km2=dest.area_km2,
                timezone=dest.timezone,
                numberofdaystotrack=dest.numberofdaystotrack,
                areas_count=areas_counts.get(dest.id, 0),
                country=CountryInfo(
                    id=dest.country.id,
                    name=dest.country.name,
                    iso_code_2=dest.country.iso_code_2,
                    iso_code_3=dest.country.iso_code_3
                )
            )
            results.append(result)
        
        return results, total_count
    
    async def _search_areas(
        self,
        keyword: str,
        page: int,
        per_page: int,
        country_id: Optional[int],
        tracking_only: bool
    ) -> Tuple[List[AreaResult], int]:
        """Search areas with filters"""
        
        # Build query
        query = Area.filter(is_active=True)
        
        # Add search conditions
        search_conditions = Q(name__icontains=keyword) | Q(display_name__icontains=keyword)
        if len(keyword) >= 3:  # Include description for longer keywords
            search_conditions |= Q(description__icontains=keyword)
        query = query.filter(search_conditions)
        
        # Apply filters
        if country_id:
            query = query.filter(country_id=country_id)
        if tracking_only:
            query = query.filter(tracking=True)
        
        # Get total count
        total_count = await query.count()
        
        # Apply pagination
        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)
        
        # Execute query with relations
        areas = await query.prefetch_related('country', 'destination').order_by('name')
        
        # Convert to response models
        results = []
        for area in areas:
            result = AreaResult(
                id=area.id,
                name=area.name,
                display_name=area.display_name,
                local_name=area.local_name,
                description=area.description,
                latitude=area.latitude,
                longitude=area.longitude,
                is_active=area.is_active,
                is_popular=area.is_popular,
                tracking=area.tracking,
                area_type=area.area_type,
                area_level=area.area_level,
                walkability_score=area.walkability_score,
                hotel_density=area.hotel_density,
                country=CountryInfo(
                    id=area.country.id,
                    name=area.country.name,
                    iso_code_2=area.country.iso_code_2,
                    iso_code_3=area.country.iso_code_3
                ),
                destination=DestinationInfo(
                    id=area.destination.id,
                    name=area.destination.name,
                    display_name=area.destination.display_name
                )
            )
            results.append(result)
        
        return results, total_count
    
    async def _count_areas(
        self,
        keyword: str,
        country_id: Optional[int],
        tracking_only: bool
    ) -> int:
        """Get count of areas matching search criteria"""
        query = Area.filter(is_active=True)
        
        # Add search conditions
        search_conditions = Q(name__icontains=keyword) | Q(display_name__icontains=keyword)
        if len(keyword) >= 3:
            search_conditions |= Q(description__icontains=keyword)
        query = query.filter(search_conditions)
        
        # Apply filters
        if country_id:
            query = query.filter(country_id=country_id)
        if tracking_only:
            query = query.filter(tracking=True)
        
        return await query.count()
    
    def _sort_by_relevance(self, results: List[LocationSearchResult], keyword: str) -> List[LocationSearchResult]:
        """Sort mixed results by relevance score"""
        keyword_lower = keyword.lower()
        
        def relevance_score(result: LocationSearchResult) -> int:
            """Calculate relevance score (lower is better)"""
            name = result.name.lower()
            display_name = (result.display_name or "").lower()
            
            # Exact match gets highest priority (score 0)
            if name == keyword_lower or display_name == keyword_lower:
                return 0
            
            # Starts with keyword (score 1)
            if name.startswith(keyword_lower) or display_name.startswith(keyword_lower):
                return 1
            
            # Contains keyword (score 2)
            if keyword_lower in name or keyword_lower in display_name:
                return 2
            
            # Description match (score 3)
            if result.description and keyword_lower in result.description.lower():
                return 3
            
            # Default (score 4)
            return 4
        
        # Sort by relevance, then by type (destinations first), then by name
        return sorted(results, key=lambda r: (
            relevance_score(r),
            r.type != "destination",  # destinations first
            r.name.lower()
        ))


# Factory function for dependency injection
async def get_location_search_service() -> LocationSearchService:
    """Get configured location search service instance"""
    return LocationSearchService()