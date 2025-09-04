from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, date
from decimal import Decimal
import logging
import re

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.hotel import Hotel, Room
from app.models.price_history import PriceHistory
from app.schemas.price_history import PriceHistoryCreate

logger = logging.getLogger(__name__)


def calculate_room_name_similarity(name1: str, name2: str) -> float:
    """
    Calculate similarity score between two room names (0.0 to 1.0)
    Higher score means more similar
    """
    if not name1 or not name2:
        return 0.0
    
    # Normalize names: lowercase, remove extra spaces, common words
    def normalize_name(name: str) -> str:
        # Convert to lowercase and remove extra spaces
        name = re.sub(r'\s+', ' ', name.lower().strip())
        # Remove common words that don't help with matching
        common_words = ['room', 'the', 'a', 'an', 'with', 'and', 'or']
        words = [word for word in name.split() if word not in common_words and len(word) > 1]
        return ' '.join(words)
    
    norm_name1 = normalize_name(name1)
    norm_name2 = normalize_name(name2)
    
    # Exact match after normalization
    if norm_name1 == norm_name2:
        return 1.0
    
    # Check if one name contains the other
    if norm_name1 in norm_name2 or norm_name2 in norm_name1:
        return 0.8
    
    # Count common keywords
    words1 = set(norm_name1.split())
    words2 = set(norm_name2.split())
    
    if not words1 or not words2:
        return 0.0
    
    common_words = words1.intersection(words2)
    total_words = words1.union(words2)
    
    # Jaccard similarity
    jaccard_score = len(common_words) / len(total_words) if total_words else 0.0
    
    # Bonus for important room type keywords
    important_keywords = ['deluxe', 'suite', 'standard', 'premium', 'executive', 'king', 'queen', 'twin', 'double', 'single']
    important_matches = sum(1 for word in common_words if word in important_keywords)
    
    # Final score with bonus for important keyword matches
    final_score = jaccard_score + (important_matches * 0.1)
    
    return min(final_score, 1.0)


def find_best_room_matches(existing_rooms: List[Room], target_name: str, min_score: float = 0.3) -> List[Tuple[Room, float]]:
    """
    Find best matching rooms with similarity scores
    """
    matches = []
    
    for room in existing_rooms:
        score = calculate_room_name_similarity(room.name, target_name)
        if score >= min_score:
            matches.append((room, score))
    
    # Sort by score descending
    matches.sort(key=lambda x: x[1], reverse=True)
    
    return matches


class HotelService:
    """Service for managing hotels, rooms, and price history"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_or_create_hotel(
        self, 
        external_id: str, 
        partner_name: str, 
        hotel_data: Dict[str, Any]
    ) -> Hotel:
        """Get existing hotel or create new one from TravClan data"""
        
        # Check if hotel already exists
        result = await self.db.execute(
            select(Hotel).where(
                Hotel.external_id == external_id,
                Hotel.partner_name == partner_name
            )
        )
        existing_hotel = result.scalar_one_or_none()
        
        if existing_hotel:
            # Update existing hotel with latest data
            existing_hotel.name = hotel_data.get('name', existing_hotel.name)
            existing_hotel.star_rating = hotel_data.get('starRating', existing_hotel.star_rating)
            existing_hotel.api_last_updated = datetime.utcnow()
            existing_hotel.api_data = hotel_data
            
            # Update address if available
            address_data = hotel_data.get('contact', {}).get('address', {})
            if address_data:
                existing_hotel.address = address_data.get('line1', existing_hotel.address)
                existing_hotel.city = address_data.get('city', {}).get('name', existing_hotel.city)
                existing_hotel.country = address_data.get('country', {}).get('name', existing_hotel.country)
                existing_hotel.postal_code = address_data.get('postalCode', existing_hotel.postal_code)
            
            # Update coordinates
            geo_code = hotel_data.get('geoCode', {})
            if geo_code:
                existing_hotel.latitude = geo_code.get('lat', existing_hotel.latitude)
                existing_hotel.longitude = geo_code.get('long', existing_hotel.longitude)
            
            await self.db.commit()
            await self.db.refresh(existing_hotel)
            return existing_hotel
        
        # Create new hotel
        address_data = hotel_data.get('contact', {}).get('address', {})
        geo_code = hotel_data.get('geoCode', {})
        
        new_hotel = Hotel(
            external_id=external_id,
            partner_name=partner_name,
            name=hotel_data.get('name', ''),
            description=hotel_data.get('description', ''),
            address=address_data.get('line1', ''),
            city=address_data.get('city', {}).get('name', ''),
            country=address_data.get('country', {}).get('name', ''),
            postal_code=address_data.get('postalCode'),
            latitude=geo_code.get('lat'),
            longitude=geo_code.get('long'),
            star_rating=hotel_data.get('starRating'),
            phone_number=hotel_data.get('contact', {}).get('phoneNumber'),
            email=hotel_data.get('contact', {}).get('email'),
            amenities=[f.get('name') for f in hotel_data.get('facilities', [])],
            images=[hotel_data.get('heroImage')] if hotel_data.get('heroImage') else None,
            currency=hotel_data.get('availability', {}).get('rate', {}).get('currency', 'USD'),
            api_last_updated=datetime.utcnow(),
            api_data=hotel_data
        )
        
        self.db.add(new_hotel)
        await self.db.commit()
        await self.db.refresh(new_hotel)
        
        logger.info(f"Created new hotel: {new_hotel.name} (ID: {new_hotel.external_id})")
        return new_hotel
    
    async def get_or_create_room(
        self, 
        hotel: Hotel, 
        room_external_id: str, 
        room_data: Dict[str, Any]
    ) -> Room:
        """Get existing room or create new one with fuzzy name matching"""
        
        # First check if room already exists by external_id
        result = await self.db.execute(
            select(Room).where(
                Room.hotel_id == hotel.id,
                Room.external_id == room_external_id
            )
        )
        existing_room = result.scalar_one_or_none()
        
        if existing_room:
            # Update existing room
            existing_room.name = room_data.get('name', existing_room.name)
            existing_room.room_type = room_data.get('type', existing_room.room_type)
            existing_room.api_last_updated = datetime.utcnow()
            existing_room.api_data = room_data
            
            await self.db.commit()
            await self.db.refresh(existing_room)
            return existing_room
        
        # If not found by external_id, try fuzzy matching by room name
        room_name = room_data.get('name', '').strip()
        if room_name:
            # Try exact name match first
            result = await self.db.execute(
                select(Room).where(
                    Room.hotel_id == hotel.id,
                    Room.name == room_name
                )
            )
            name_match_room = result.scalar_one_or_none()
            
            if name_match_room:
                # Update external_id to link with API data
                name_match_room.external_id = room_external_id
                name_match_room.room_type = room_data.get('type', name_match_room.room_type)
                name_match_room.api_last_updated = datetime.utcnow()
                name_match_room.api_data = room_data
                
                await self.db.commit()
                await self.db.refresh(name_match_room)
                logger.info(f"Found room by exact name match: {room_name}")
                return name_match_room
            
            # Try advanced fuzzy matching using similarity scoring
            # Get all existing rooms for this hotel
            all_rooms_result = await self.db.execute(
                select(Room).where(Room.hotel_id == hotel.id)
            )
            all_rooms = all_rooms_result.scalars().all()
            
            if all_rooms:
                # Find best matches using similarity scoring
                room_matches = find_best_room_matches(all_rooms, room_name, min_score=0.4)
                
                if room_matches:
                    # Use the best match (highest similarity score)
                    best_match_room, similarity_score = room_matches[0]
                    
                    # Update the matched room with new external_id and data
                    best_match_room.external_id = room_external_id
                    best_match_room.name = room_name  # Update with the API name
                    best_match_room.room_type = room_data.get('type', best_match_room.room_type)
                    best_match_room.api_last_updated = datetime.utcnow()
                    best_match_room.api_data = room_data
                    
                    await self.db.commit()
                    await self.db.refresh(best_match_room)
                    logger.info(f"Found room by similarity match (score: {similarity_score:.2f}): '{best_match_room.name}' -> '{room_name}'")
                    return best_match_room
        
        # Create new room - for TravClan, we might not have detailed room data
        # So we'll create a generic room entry
        new_room = Room(
            hotel_id=hotel.id,
            external_id=room_external_id,
            name=room_data.get('name', f"Room {room_external_id}"),
            room_type=room_data.get('type', 'standard'),
            max_occupancy=room_data.get('maxOccupancy', 2),
            bed_type=room_data.get('bedType'),
            api_last_updated=datetime.utcnow(),
            api_data=room_data
        )
        
        self.db.add(new_room)
        await self.db.commit()
        await self.db.refresh(new_room)
        
        logger.info(f"Created new room: {new_room.name} for hotel {hotel.name}")
        return new_room
    
    async def store_price_history(
        self,
        hotel: Hotel,
        room: Room,
        search_request: Dict[str, Any],
        hotel_data: Dict[str, Any],
        trace_id: Optional[str] = None
    ) -> PriceHistory:
        """Store price history entry for hotel search result"""
        
        check_in_date = datetime.fromisoformat(search_request['checkIn']).date()
        check_out_date = datetime.fromisoformat(search_request['checkOut']).date()
        nights = (check_out_date - check_in_date).days
        
        # Extract rate information from hotel data
        availability = hotel_data.get('availability', {})
        rate = availability.get('rate', {})
        options = availability.get('options', {})
        
        final_rate = rate.get('finalRate', 0)
        currency = rate.get('currency', 'USD')
        
        # Calculate price per night
        price_per_night = Decimal(str(final_rate)) / nights if nights > 0 else Decimal(str(final_rate))
        total_price = Decimal(str(final_rate))
        
        # Get occupancy info
        occupancy = sum(occ.get('numOfAdults', 0) for occ in search_request.get('occupancies', []))
        
        price_history_data = PriceHistoryCreate(
            hotel_id=hotel.id,
            room_id=room.id,
            price_date=date.today(),  # Date when price was collected
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            price_per_night=price_per_night,
            total_price=total_price,
            currency=currency,
            is_available=hotel_data.get('isAvailable', True),
            occupancy=occupancy,
            partner_name="TravClan",
            external_rate_id=rate.get('rateId'),
            rate_name=rate.get('rateName'),
            trace_id=trace_id,
            cancellation_policy="Free Cancellation" if options.get('freeCancellation') else None,
            payment_policy="Pay at Hotel" if options.get('payAtHotel') else None,
            booking_conditions={
                'freeBreakfast': options.get('freeBreakfast', False),
                'freeCancellation': options.get('freeCancellation', False),
                'payAtHotel': options.get('payAtHotel', False),
                'instantConfirmation': options.get('instantConfirmation', False)
            },
            api_raw_data=hotel_data
        )
        
        # Check if price history already exists for this combination
        existing_result = await self.db.execute(
            select(PriceHistory).where(
                PriceHistory.hotel_id == hotel.id,
                PriceHistory.room_id == room.id,
                PriceHistory.price_date == price_history_data.price_date,
                PriceHistory.check_in_date == price_history_data.check_in_date,
                PriceHistory.check_out_date == price_history_data.check_out_date,
                PriceHistory.occupancy == price_history_data.occupancy
            )
        )
        existing_price_history = existing_result.scalar_one_or_none()
        
        if existing_price_history:
            # Update existing price history with new data
            existing_price_history.price_per_night = price_history_data.price_per_night
            existing_price_history.total_price = price_history_data.total_price
            existing_price_history.is_available = price_history_data.is_available
            existing_price_history.trace_id = price_history_data.trace_id
            existing_price_history.api_raw_data = price_history_data.api_raw_data
            existing_price_history.updated_at = datetime.utcnow()
            
            await self.db.commit()
            await self.db.refresh(existing_price_history)
            
            logger.info(f"Updated price history for hotel {hotel.name} - {check_in_date} to {check_out_date}")
            return existing_price_history
        
        # Create new price history entry
        new_price_history = PriceHistory(**price_history_data.model_dump())
        
        self.db.add(new_price_history)
        await self.db.commit()
        await self.db.refresh(new_price_history)
        
        logger.info(f"Created new price history for hotel {hotel.name} - {check_in_date} to {check_out_date}, trace_id: {trace_id}")
        return new_price_history
    
    async def process_hotel_search_results(
        self,
        search_request: Dict[str, Any],
        search_response: Dict[str, Any]
    ) -> List[PriceHistory]:
        """Process hotel search results and store price history"""
        
        results = search_response.get('results', [])
        if not results:
            return []
        
        first_result = results[0]
        trace_id = first_result.get('traceId')
        hotels_data = first_result.get('data', [])
        
        price_histories = []
        
        for hotel_data in hotels_data:
            if not hotel_data.get('isAvailable', False):
                continue
                
            try:
                # Get or create hotel
                hotel = await self.get_or_create_hotel(
                    external_id=str(hotel_data.get('id')),
                    partner_name="TravClan",
                    hotel_data=hotel_data
                )
                
                # For TravClan, create a generic room since detailed room data isn't provided in search
                room = await self.get_or_create_room(
                    hotel=hotel,
                    room_external_id=f"{hotel_data.get('id')}_default_room",
                    room_data={'name': 'Default Room', 'type': 'standard'}
                )
                
                # Store price history
                price_history = await self.store_price_history(
                    hotel=hotel,
                    room=room,
                    search_request=search_request,
                    hotel_data=hotel_data,
                    trace_id=trace_id
                )
                
                price_histories.append(price_history)
                
            except Exception as e:
                logger.error(f"Error processing hotel {hotel_data.get('id')}: {e}")
                continue
        
        logger.info(f"Processed {len(price_histories)} hotel price histories with trace_id: {trace_id}")
        return price_histories