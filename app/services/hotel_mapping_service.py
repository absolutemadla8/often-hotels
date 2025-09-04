from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, date
from decimal import Decimal
import logging
import re

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.booking import Booking
from app.models.price_history import PriceHistory
from app.schemas.price_history import PriceHistoryCreate
from app.services.travclan_api_service import travclan_api_service

logger = logging.getLogger(__name__)


def calculate_hotel_name_similarity(user_hotel_name: str, api_hotel_name: str) -> float:
    """
    Calculate similarity score between user's hotel name and API hotel name (0.0 to 1.0)
    """
    if not user_hotel_name or not api_hotel_name:
        return 0.0
    
    # Normalize names: lowercase, remove extra spaces, common words
    def normalize_hotel_name(name: str) -> str:
        name = re.sub(r'\s+', ' ', name.lower().strip())
        # Remove common hotel words that don't help with matching
        common_words = ['hotel', 'resort', 'inn', 'suites', 'by', 'the', 'and', 'at', 'in', 'of']
        words = [word for word in name.split() if word not in common_words and len(word) > 2]
        return ' '.join(words)
    
    norm_user = normalize_hotel_name(user_hotel_name)
    norm_api = normalize_hotel_name(api_hotel_name)
    
    # Exact match after normalization
    if norm_user == norm_api:
        return 1.0
    
    # Check if one name contains the other
    if norm_user in norm_api or norm_api in norm_user:
        return 0.9
    
    # Count common keywords
    words_user = set(norm_user.split())
    words_api = set(norm_api.split())
    
    if not words_user or not words_api:
        return 0.0
    
    common_words = words_user.intersection(words_api)
    total_words = words_user.union(words_api)
    
    # Jaccard similarity
    jaccard_score = len(common_words) / len(total_words) if total_words else 0.0
    
    return jaccard_score


def calculate_room_name_similarity(user_room_name: str, api_room_name: str) -> float:
    """
    Calculate similarity score between user's room name and API room name (0.0 to 1.0)
    """
    if not user_room_name or not api_room_name:
        return 0.0
    
    # Normalize names
    def normalize_room_name(name: str) -> str:
        name = re.sub(r'\s+', ' ', name.lower().strip())
        common_words = ['room', 'the', 'a', 'an', 'with', 'and', 'or']
        words = [word for word in name.split() if word not in common_words and len(word) > 1]
        return ' '.join(words)
    
    norm_user = normalize_room_name(user_room_name)
    norm_api = normalize_room_name(api_room_name)
    
    # Exact match after normalization
    if norm_user == norm_api:
        return 1.0
    
    # Check if one name contains the other
    if norm_user in norm_api or norm_api in norm_user:
        return 0.8
    
    # Count common keywords
    words_user = set(norm_user.split())
    words_api = set(norm_api.split())
    
    if not words_user or not words_api:
        return 0.0
    
    common_words = words_user.intersection(words_api)
    total_words = words_user.union(words_api)
    
    # Jaccard similarity
    jaccard_score = len(common_words) / len(total_words) if total_words else 0.0
    
    # Bonus for important room type keywords
    important_keywords = ['deluxe', 'suite', 'standard', 'premium', 'executive', 'king', 'queen', 'twin', 'double', 'single']
    important_matches = sum(1 for word in common_words if word in important_keywords)
    
    # Final score with bonus for important keyword matches
    final_score = jaccard_score + (important_matches * 0.1)
    
    return min(final_score, 1.0)


class HotelMappingService:
    """Service for mapping user hotel/room names to external provider IDs"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def find_hotel_by_name(
        self, 
        hotel_name: str, 
        city: Optional[str] = None,
        min_similarity: float = 0.6
    ) -> Optional[Tuple[str, str, float]]:
        """
        Find external hotel ID by searching with hotel name
        Returns: (external_hotel_id, matched_hotel_name, similarity_score) or None
        """
        try:
            # Use location search to find hotels
            search_query = f"{hotel_name}"
            if city:
                search_query += f" {city}"
            
            async with travclan_api_service:
                location_response = await travclan_api_service.search_locations(search_query)
            
            locations = location_response.get('results', [])
            
            # Filter for hotels and calculate similarity scores
            hotel_matches = []
            for location in locations:
                if location.get('type') in ['HOTEL', 'Hotel']:
                    api_hotel_name = location.get('name', '')
                    similarity = calculate_hotel_name_similarity(hotel_name, api_hotel_name)
                    
                    if similarity >= min_similarity:
                        hotel_matches.append((
                            str(location.get('id')),
                            api_hotel_name,
                            similarity
                        ))
            
            # Sort by similarity and return best match
            if hotel_matches:
                hotel_matches.sort(key=lambda x: x[2], reverse=True)
                best_match = hotel_matches[0]
                logger.info(f"Found hotel match: '{hotel_name}' -> '{best_match[1]}' (score: {best_match[2]:.2f})")
                return best_match
            
            logger.warning(f"No hotel matches found for: {hotel_name}")
            return None
            
        except Exception as e:
            logger.error(f"Error finding hotel by name '{hotel_name}': {e}")
            return None
    
    async def find_matching_room_in_itinerary(
        self,
        external_hotel_id: str,
        user_room_name: str,
        check_in_date: date,
        check_out_date: date,
        occupancies: List[Dict[str, Any]],
        min_similarity: float = 0.4
    ) -> Optional[Tuple[str, str, float, Dict[str, Any]]]:
        """
        Find matching room in hotel itinerary response
        Returns: (room_id, matched_room_name, similarity_score, room_data) or None
        """
        try:
            # Get room rates from direct itinerary API
            request_data = {
                "hotelId": external_hotel_id,
                "checkIn": check_in_date.isoformat(),
                "checkOut": check_out_date.isoformat(),
                "occupancies": occupancies
            }
            
            async with travclan_api_service:
                itinerary_response = await travclan_api_service.create_direct_hotel_itinerary(request_data)
            
            # Extract room data from response
            rooms_data = itinerary_response.get('results', [{}])[0].get('items', [])
            
            # Find best room match
            room_matches = []
            for room_item in rooms_data:
                room_info = room_item.get('roomTypeInfo', {})
                api_room_name = room_info.get('name', '')
                room_id = room_info.get('id', '')
                
                if api_room_name:
                    similarity = calculate_room_name_similarity(user_room_name, api_room_name)
                    
                    if similarity >= min_similarity:
                        room_matches.append((
                            room_id,
                            api_room_name,
                            similarity,
                            room_item
                        ))
            
            # Sort by similarity and return best match
            if room_matches:
                room_matches.sort(key=lambda x: x[2], reverse=True)
                best_match = room_matches[0]
                logger.info(f"Found room match: '{user_room_name}' -> '{best_match[1]}' (score: {best_match[2]:.2f})")
                return best_match
            
            # If no good matches, return first available room with low score
            if rooms_data:
                first_room = rooms_data[0]
                room_info = first_room.get('roomTypeInfo', {})
                logger.warning(f"No good room matches for '{user_room_name}', using first available: '{room_info.get('name', 'Unknown')}'")
                return (
                    room_info.get('id', ''),
                    room_info.get('name', 'Unknown Room'),
                    0.0,
                    first_room
                )
            
            logger.warning(f"No rooms found for hotel {external_hotel_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error finding room in itinerary for hotel {external_hotel_id}: {e}")
            return None
    
    async def map_booking_to_external_provider(self, booking: Booking) -> bool:
        """
        Map a booking's hotel/room to external provider IDs
        Updates the booking record with external_hotel_id
        """
        try:
            # Find hotel mapping
            hotel_match = await self.find_hotel_by_name(
                booking.hotel_name,
                booking.hotel_city
            )
            
            if not hotel_match:
                logger.error(f"Could not map hotel '{booking.hotel_name}' to external provider")
                return False
            
            external_hotel_id, matched_hotel_name, hotel_similarity = hotel_match
            
            # Update booking with external mapping
            booking.external_hotel_id = external_hotel_id
            booking.partner_name = "TravClan"
            
            await self.db.commit()
            await self.db.refresh(booking)
            
            logger.info(f"Mapped booking {booking.id}: '{booking.hotel_name}' -> external ID {external_hotel_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error mapping booking {booking.id} to external provider: {e}")
            return False
    
    async def store_price_history_for_booking(
        self,
        booking: Booking,
        room_data: Dict[str, Any],
        trace_id: Optional[str] = None
    ) -> Optional[PriceHistory]:
        """
        Store price history for a mapped booking
        """
        try:
            if not booking.external_hotel_id:
                logger.error(f"Booking {booking.id} not mapped to external provider")
                return None
            
            # Extract price information from room data
            rate_info = room_data.get('rateInfo', {})
            total_price = rate_info.get('totalRate', 0)
            currency = rate_info.get('currency', 'USD')
            
            nights = (booking.check_out_date - booking.check_in_date).days
            price_per_night = Decimal(str(total_price)) / nights if nights > 0 else Decimal(str(total_price))
            
            # Check if price history already exists
            existing_result = await self.db.execute(
                select(PriceHistory).where(
                    PriceHistory.external_hotel_id == booking.external_hotel_id,
                    PriceHistory.room_name == booking.room_name,
                    PriceHistory.price_date == date.today(),
                    PriceHistory.check_in_date == booking.check_in_date,
                    PriceHistory.check_out_date == booking.check_out_date,
                    PriceHistory.occupancies == booking.occupancies
                )
            )
            existing_price_history = existing_result.scalar_one_or_none()
            
            if existing_price_history:
                # Update existing
                existing_price_history.total_price = Decimal(str(total_price))
                existing_price_history.price_per_night = price_per_night
                existing_price_history.trace_id = trace_id
                existing_price_history.api_raw_data = room_data
                existing_price_history.updated_at = datetime.utcnow()
                
                await self.db.commit()
                await self.db.refresh(existing_price_history)
                return existing_price_history
            
            # Create new price history
            new_price_history = PriceHistory(
                external_hotel_id=booking.external_hotel_id,
                hotel_name=booking.hotel_name,
                room_name=booking.room_name,
                hotel_city=booking.hotel_city,
                price_date=date.today(),
                check_in_date=booking.check_in_date,
                check_out_date=booking.check_out_date,
                nights=nights,
                price_per_night=price_per_night,
                total_price=Decimal(str(total_price)),
                currency=currency,
                is_available=True,
                occupancies=booking.occupancies,
                partner_name="TravClan",
                trace_id=trace_id,
                api_raw_data=room_data
            )
            
            self.db.add(new_price_history)
            await self.db.commit()
            await self.db.refresh(new_price_history)
            
            logger.info(f"Created price history for booking {booking.id}: {total_price} {currency}")
            return new_price_history
            
        except Exception as e:
            logger.error(f"Error storing price history for booking {booking.id}: {e}")
            return None
    
    async def get_current_room_rates_for_booking(self, booking: Booking) -> Optional[Dict[str, Any]]:
        """
        Get current room rates for a mapped booking
        """
        if not booking.external_hotel_id:
            logger.error(f"Booking {booking.id} not mapped to external provider")
            return None
        
        # Use the booking's occupancy structure directly
        occupancies = booking.occupancies
        
        room_match = await self.find_matching_room_in_itinerary(
            booking.external_hotel_id,
            booking.room_name,
            booking.check_in_date,
            booking.check_out_date,
            occupancies
        )
        
        if room_match:
            room_id, matched_room_name, similarity, room_data = room_match
            
            # Store price history
            await self.store_price_history_for_booking(booking, room_data)
            
            return {
                "booking_id": booking.id,
                "external_hotel_id": booking.external_hotel_id,
                "room_id": room_id,
                "matched_room_name": matched_room_name,
                "similarity_score": similarity,
                "room_data": room_data
            }
        
        return None