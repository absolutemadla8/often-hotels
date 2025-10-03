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
    PaginationMeta, SearchFilters, CountryInfo, DestinationInfo,
    CountryWithDestinations, DestinationWithAreas, AreaInDestination
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
        country_iso: Optional[str] = None,
        tracking_only: bool = False
    ) -> Tuple[List[CountryWithDestinations], PaginationMeta, SearchFilters]:
        """
        Search locations across destinations and areas with pagination
        
        Args:
            search_keyword: Search term
            page: Page number (1-based)
            per_page: Results per page
            location_type: Filter by type ("destination" or "area")
            country_iso: Filter by country ISO code (2 or 3 letter)
            tracking_only: Only show tracking-enabled locations
            
        Returns:
            Tuple of (hierarchical_results, pagination_meta, filters_applied)
        """
        # Validate and sanitize parameters
        per_page = min(max(per_page, 1), self.max_per_page)
        page = max(page, 1)
        search_keyword = search_keyword.strip()
        
        logger.info(f"Searching locations: '{search_keyword}', page={page}, per_page={per_page}, type={location_type}")
        
        # Build hierarchical results from database
        hierarchical_results, total_count = await self._build_hierarchical_results(
            search_keyword, page, per_page, location_type, country_iso, tracking_only
        )
        
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
            country_iso=country_iso,
            tracking_only=tracking_only
        )
        
        logger.info(f"Found {total_count} total results for '{search_keyword}' in hierarchical structure")
        
        return hierarchical_results, pagination, filters
    
    async def _build_hierarchical_results(
        self,
        keyword: str,
        page: int,
        per_page: int,
        location_type: Optional[str],
        country_iso: Optional[str],
        tracking_only: bool
    ) -> Tuple[List[CountryWithDestinations], int]:
        """Build hierarchical results grouped by country -> destination -> areas"""
        
        # Build search queries
        dest_query = self._build_destination_query(keyword, country_iso, tracking_only)
        area_query = self._build_area_query(keyword, country_iso, tracking_only)
        
        # Apply type filters
        if location_type == "destination":
            area_query = Area.filter(id__isnull=True)  # No areas
        elif location_type == "area":
            dest_query = Destination.filter(id__isnull=True)  # No destinations
        
        # Get data with proper relations
        destinations = await dest_query.prefetch_related('country').order_by('name')
        areas = await area_query.prefetch_related('country', 'destination').order_by('name')
        
        # Group data by country
        country_data = {}
        
        # Process destinations
        for dest in destinations:
            country_id = dest.country.id
            if country_id not in country_data:
                country_data[country_id] = {
                    'country': CountryInfo(
                        id=dest.country.id,
                        name=dest.country.name,
                        iso_code_2=dest.country.iso_code_2,
                        iso_code_3=dest.country.iso_code_3
                    ),
                    'destinations': {}
                }
            
            # Create destination
            dest_obj = DestinationWithAreas(
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
                areas=[]
            )
            country_data[country_id]['destinations'][dest.id] = dest_obj
        
        # Process areas
        for area in areas:
            country_id = area.country.id
            dest_id = area.destination.id
            
            # Ensure country exists
            if country_id not in country_data:
                country_data[country_id] = {
                    'country': CountryInfo(
                        id=area.country.id,
                        name=area.country.name,
                        iso_code_2=area.country.iso_code_2,
                        iso_code_3=area.country.iso_code_3
                    ),
                    'destinations': {}
                }
            
            # Ensure destination exists (for areas found without their destination in results)
            if dest_id not in country_data[country_id]['destinations']:
                country_data[country_id]['destinations'][dest_id] = DestinationWithAreas(
                    id=area.destination.id,
                    name=area.destination.name,
                    display_name=area.destination.display_name,
                    local_name=area.destination.local_name,
                    description=area.destination.description,
                    latitude=area.destination.latitude,
                    longitude=area.destination.longitude,
                    is_active=area.destination.is_active,
                    is_popular=area.destination.is_popular,
                    tracking=area.destination.tracking,
                    destination_type=area.destination.destination_type,
                    tourist_rating=area.destination.tourist_rating,
                    population=area.destination.population,
                    area_km2=area.destination.area_km2,
                    timezone=area.destination.timezone,
                    numberofdaystotrack=area.destination.numberofdaystotrack,
                    areas=[]
                )
            
            # Add area to destination
            area_obj = AreaInDestination(
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
                hotel_density=area.hotel_density
            )
            country_data[country_id]['destinations'][dest_id].areas.append(area_obj)
        
        # Convert to final structure
        results = []
        total_items = 0
        
        for country_info in country_data.values():
            country_result = CountryWithDestinations(
                country=country_info['country'],
                destinations=list(country_info['destinations'].values())
            )
            results.append(country_result)
            
            # Count total items for pagination
            for dest in country_result.destinations:
                total_items += 1  # destination
                total_items += len(dest.areas)  # areas
        
        # Sort results by relevance
        results = self._sort_countries_by_relevance(results, keyword)
        
        return results, total_items
    
    def _build_destination_query(self, keyword: str, country_iso: Optional[str], tracking_only: bool):
        """Build destination search query"""
        query = Destination.filter(is_active=True)
        
        # Add search conditions
        search_conditions = Q(name__icontains=keyword) | Q(display_name__icontains=keyword)
        if len(keyword) >= 3:
            search_conditions |= Q(description__icontains=keyword)
        query = query.filter(search_conditions)
        
        # Apply filters
        if country_iso:
            if len(country_iso) == 2:
                query = query.filter(country__iso_code_2__iexact=country_iso)
            elif len(country_iso) == 3:
                query = query.filter(country__iso_code_3__iexact=country_iso)
        
        if tracking_only:
            query = query.filter(tracking=True)
        
        return query
    
    def _build_area_query(self, keyword: str, country_iso: Optional[str], tracking_only: bool):
        """Build area search query"""
        query = Area.filter(is_active=True)
        
        # Add search conditions
        search_conditions = Q(name__icontains=keyword) | Q(display_name__icontains=keyword)
        if len(keyword) >= 3:
            search_conditions |= Q(description__icontains=keyword)
        query = query.filter(search_conditions)
        
        # Apply filters
        if country_iso:
            if len(country_iso) == 2:
                query = query.filter(country__iso_code_2__iexact=country_iso)
            elif len(country_iso) == 3:
                query = query.filter(country__iso_code_3__iexact=country_iso)
        
        if tracking_only:
            query = query.filter(tracking=True)
        
        return query
    
    def _sort_countries_by_relevance(self, results: List[CountryWithDestinations], keyword: str) -> List[CountryWithDestinations]:
        """Sort countries by search relevance"""
        keyword_lower = keyword.lower()
        
        def country_relevance_score(country_result: CountryWithDestinations) -> int:
            """Calculate relevance score for a country (lower is better)"""
            min_score = 10
            
            # Check country name
            if keyword_lower in country_result.country.name.lower():
                min_score = min(min_score, 1)
            
            # Check destinations and areas
            for dest in country_result.destinations:
                dest_score = self._location_relevance_score(dest.name, dest.display_name, dest.description, keyword_lower)
                min_score = min(min_score, dest_score)
                
                for area in dest.areas:
                    area_score = self._location_relevance_score(area.name, area.display_name, area.description, keyword_lower)
                    min_score = min(min_score, area_score)
            
            return min_score
        
        # Sort countries by relevance
        return sorted(results, key=country_relevance_score)
    
    def _location_relevance_score(self, name: str, display_name: Optional[str], description: Optional[str], keyword: str) -> int:
        """Calculate relevance score for a location"""
        name = name.lower()
        display_name = (display_name or "").lower()
        description = (description or "").lower()
        
        # Exact match
        if name == keyword or display_name == keyword:
            return 0
        
        # Starts with
        if name.startswith(keyword) or display_name.startswith(keyword):
            return 1
        
        # Contains in name
        if keyword in name or keyword in display_name:
            return 2
        
        # Contains in description
        if keyword in description:
            return 3
        
        return 4
    
    async def _search_destinations(
        self,
        keyword: str,
        page: int,
        per_page: int,
        country_iso: Optional[str],
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
        if country_iso:
            if len(country_iso) == 2:
                query = query.filter(country__iso_code_2__iexact=country_iso)
            elif len(country_iso) == 3:
                query = query.filter(country__iso_code_3__iexact=country_iso)
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
        country_iso: Optional[str],
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
        if country_iso:
            if len(country_iso) == 2:
                query = query.filter(country__iso_code_2__iexact=country_iso)
            elif len(country_iso) == 3:
                query = query.filter(country__iso_code_3__iexact=country_iso)
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
        country_iso: Optional[str],
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
        if country_iso:
            if len(country_iso) == 2:
                query = query.filter(country__iso_code_2__iexact=country_iso)
            elif len(country_iso) == 3:
                query = query.filter(country__iso_code_3__iexact=country_iso)
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