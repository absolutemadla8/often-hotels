"""
Intelligent hotel matching and deduplication service using fuzzy matching
Prevents duplicate hotels with slightly different names or coordinates
"""
from typing import Optional, Tuple, Dict, Any
from rapidfuzz import fuzz, process
from app.models.models import Hotel, Area, Destination
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class HotelMatchingService:
    """
    Intelligent hotel matching using multiple strategies:
    1. Exact name match (case-insensitive)
    2. Fuzzy name matching (handles typos, variations)
    3. Coordinate-based matching (geographic proximity)
    4. Combined scoring (name + location)
    """

    def __init__(
        self,
        name_similarity_threshold: int = 85,
        coordinate_distance_km: float = 0.1,
        use_cache: bool = True
    ):
        """
        Args:
            name_similarity_threshold: Minimum similarity score (0-100) for fuzzy match
            coordinate_distance_km: Maximum distance in km for coordinate match
            use_cache: Whether to use in-memory cache for performance
        """
        self.name_similarity_threshold = name_similarity_threshold
        self.coordinate_distance_km = coordinate_distance_km
        self.use_cache = use_cache
        self._cache: Dict[str, Hotel] = {}

        # Metrics
        self.total_lookups = 0
        self.cache_hits = 0
        self.exact_matches = 0
        self.fuzzy_matches = 0
        self.coordinate_matches = 0
        self.new_hotels_created = 0

    async def find_or_create_hotel(
        self,
        name: str,
        area: Area,
        coordinates: Optional[Tuple[float, float]] = None,
        **metadata
    ) -> Tuple[Hotel, bool]:
        """
        Find existing hotel or create new one using intelligent matching

        Args:
            name: Hotel name from SERP results
            area: Area where hotel is located
            coordinates: (latitude, longitude) tuple
            **metadata: Additional hotel data (star_rating, amenities, etc.)

        Returns:
            (hotel, is_new) tuple
            - hotel: Hotel instance
            - is_new: True if newly created, False if matched to existing
        """
        self.total_lookups += 1
        name_normalized = name.strip()

        # 1. Check cache first (fastest)
        cache_key = self._get_cache_key(area.id, name_normalized)
        if self.use_cache and cache_key in self._cache:
            self.cache_hits += 1
            logger.debug(f"Cache hit for '{name_normalized}' in area {area.id}")
            return self._cache[cache_key], False

        # 2. Try exact name match (case-insensitive)
        hotel = await self._find_by_exact_name(name_normalized, area)
        if hotel:
            self.exact_matches += 1
            self._update_cache(cache_key, hotel)
            logger.info(f"Exact match found: '{name_normalized}' -> '{hotel.name}'")
            return hotel, False

        # 3. Get all hotels in this area for fuzzy matching
        existing_hotels = await Hotel.filter(area=area).all()

        if not existing_hotels:
            # No hotels in area, create new
            hotel = await self._create_hotel(name_normalized, area, coordinates, **metadata)
            self._update_cache(cache_key, hotel)
            return hotel, True

        # 4. Try fuzzy name matching
        matched_hotel = await self._find_by_fuzzy_name(
            name_normalized, existing_hotels
        )
        if matched_hotel:
            self.fuzzy_matches += 1
            self._update_cache(cache_key, matched_hotel)

            # Update coordinates if missing
            if coordinates and not matched_hotel.latitude:
                await self._update_hotel_coordinates(matched_hotel, coordinates)

            return matched_hotel, False

        # 5. Try coordinate-based matching (if coordinates provided)
        if coordinates:
            matched_hotel = await self._find_by_coordinates(
                coordinates, existing_hotels
            )
            if matched_hotel:
                self.coordinate_matches += 1
                self._update_cache(cache_key, matched_hotel)
                logger.info(
                    f"Coordinate match: '{name_normalized}' -> '{matched_hotel.name}'"
                )
                return matched_hotel, False

        # 6. No match found, create new hotel
        hotel = await self._create_hotel(name_normalized, area, coordinates, **metadata)
        self._update_cache(cache_key, hotel)
        return hotel, True

    async def _find_by_exact_name(
        self,
        name: str,
        area: Area
    ) -> Optional[Hotel]:
        """Find hotel by exact name match (case-insensitive)"""
        return await Hotel.filter(
            name__iexact=name,
            area=area
        ).first()

    async def _find_by_fuzzy_name(
        self,
        name: str,
        existing_hotels: list[Hotel]
    ) -> Optional[Hotel]:
        """
        Find hotel using fuzzy string matching
        Uses token_sort_ratio which handles word order and extra words
        """
        if not existing_hotels:
            return None

        hotel_names = [h.name for h in existing_hotels]

        # Use rapidfuzz for fuzzy matching
        best_match = process.extractOne(
            name,
            hotel_names,
            scorer=fuzz.token_sort_ratio  # Handles word order differences
        )

        if best_match and best_match[1] >= self.name_similarity_threshold:
            matched_hotel = existing_hotels[hotel_names.index(best_match[0])]
            logger.info(
                f"Fuzzy match: '{name}' -> '{matched_hotel.name}' "
                f"(similarity: {best_match[1]}%)"
            )
            return matched_hotel

        return None

    async def _find_by_coordinates(
        self,
        coordinates: Tuple[float, float],
        existing_hotels: list[Hotel]
    ) -> Optional[Hotel]:
        """Find hotel by geographic proximity"""
        lat, lon = coordinates

        for hotel in existing_hotels:
            if hotel.latitude and hotel.longitude:
                distance = self._haversine_distance(
                    lat, lon,
                    hotel.latitude, hotel.longitude
                )

                if distance <= self.coordinate_distance_km:
                    logger.info(
                        f"Coordinate match found: distance {distance:.3f}km "
                        f"(threshold: {self.coordinate_distance_km}km)"
                    )
                    return hotel

        return None

    async def _create_hotel(
        self,
        name: str,
        area: Area,
        coordinates: Optional[Tuple[float, float]],
        **metadata
    ) -> Hotel:
        """Create new hotel entity"""
        # Fetch destination and country relationships
        await area.fetch_related('destination', 'destination__country')

        # Generate external_id from name and area
        import hashlib
        external_id = hashlib.md5(f"{name}_{area.id}".encode()).hexdigest()[:20]

        hotel_data = {
            "name": name,
            "display_name": name,
            "area": area,
            "destination": area.destination,
            "country": area.destination.country,
            "external_id": external_id,
            "partner_name": "serpapi",  # Required field
            "address": metadata.get("address", f"{area.name}, {area.destination.name}"),
            "city": area.destination.name,
            "latitude": coordinates[0] if coordinates else None,
            "longitude": coordinates[1] if coordinates else None,
            "star_rating": metadata.get("star_rating"),
            "description": metadata.get("description"),
            "thumbnail": metadata.get("thumbnail"),  # First image thumbnail
            "images": metadata.get("images"),  # All images as JSON array
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        hotel = await Hotel.create(**hotel_data)
        self.new_hotels_created += 1

        logger.info(
            f"Created new hotel: '{name}' in {area.name}, {area.destination.name} "
            f"(ID: {hotel.id})"
        )

        return hotel

    async def _update_hotel_coordinates(
        self,
        hotel: Hotel,
        coordinates: Tuple[float, float]
    ):
        """Update hotel coordinates if missing"""
        hotel.latitude = coordinates[0]
        hotel.longitude = coordinates[1]
        hotel.updated_at = datetime.utcnow()
        await hotel.save()
        logger.info(f"Updated coordinates for hotel '{hotel.name}'")

    @staticmethod
    def _haversine_distance(
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
    ) -> float:
        """
        Calculate distance between two coordinates in kilometers
        Uses Haversine formula
        """
        from math import radians, cos, sin, asin, sqrt

        # Convert to radians
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

        # Haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))

        # Radius of earth in kilometers
        r = 6371

        return c * r

    def _get_cache_key(self, area_id: int, name: str) -> str:
        """Generate cache key for hotel lookup"""
        return f"{area_id}:{name.lower()}"

    def _update_cache(self, key: str, hotel: Hotel):
        """Update in-memory cache"""
        if self.use_cache:
            self._cache[key] = hotel

    def clear_cache(self):
        """Clear in-memory cache"""
        self._cache.clear()
        logger.info("Hotel matching cache cleared")

    def get_metrics(self) -> Dict[str, Any]:
        """Get matching metrics for monitoring"""
        return {
            "total_lookups": self.total_lookups,
            "cache_hits": self.cache_hits,
            "cache_hit_rate": self.cache_hits / max(self.total_lookups, 1),
            "exact_matches": self.exact_matches,
            "fuzzy_matches": self.fuzzy_matches,
            "coordinate_matches": self.coordinate_matches,
            "new_hotels_created": self.new_hotels_created,
            "match_rate": (
                self.exact_matches + self.fuzzy_matches + self.coordinate_matches
            ) / max(self.total_lookups, 1)
        }

    def reset_metrics(self):
        """Reset metrics counters"""
        self.total_lookups = 0
        self.cache_hits = 0
        self.exact_matches = 0
        self.fuzzy_matches = 0
        self.coordinate_matches = 0
        self.new_hotels_created = 0


# Singleton instance
_hotel_matching_service: Optional[HotelMatchingService] = None


def get_hotel_matching_service(
    name_similarity_threshold: int = 85,
    coordinate_distance_km: float = 0.1,
    use_cache: bool = True
) -> HotelMatchingService:
    """
    Get singleton hotel matching service instance

    Usage:
        service = get_hotel_matching_service()
        hotel, is_new = await service.find_or_create_hotel(...)
    """
    global _hotel_matching_service

    if _hotel_matching_service is None:
        _hotel_matching_service = HotelMatchingService(
            name_similarity_threshold=name_similarity_threshold,
            coordinate_distance_km=coordinate_distance_km,
            use_cache=use_cache
        )

    return _hotel_matching_service
