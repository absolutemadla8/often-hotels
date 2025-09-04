import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime

import httpx
from fastapi import HTTPException
import logging

from app.core.config import settings
from .base_api_client import BaseApiClient

logger = logging.getLogger(__name__)


class TravClanTokenManager:
    """Singleton token manager for TravClan API"""
    _instance = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.base_api_client = None
            self.initialized = True
    
    async def get_valid_access_token(self) -> str:
        """Get a valid access token, refreshing if necessary"""
        if not self.base_api_client:
            raise HTTPException(status_code=500, detail="Token manager not initialized")
        
        if self.base_api_client.token_manager.is_token_expired():
            await self.base_api_client.refresh_access_token()
        
        token = self.base_api_client.token_manager.get_access_token()
        if not token:
            raise HTTPException(status_code=401, detail="No valid access token available")
        
        return token
    
    async def handle_unauthorized_response(self) -> str:
        """Handle 401 response by refreshing token"""
        if not self.base_api_client:
            raise HTTPException(status_code=500, detail="Token manager not initialized")
        
        await self.base_api_client.refresh_access_token()
        return await self.get_valid_access_token()


class TravClanHotelApiService(BaseApiClient):
    """TravClan Hotel API Service"""
    
    _instance = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            super().__init__(
                base_url=settings.TRAVCLAN_BASE_URL,
                search_api_url=settings.TRAVCLAN_SEARCH_API_URL
            )
            self.token_manager_singleton = TravClanTokenManager()
            self.token_manager_singleton.base_api_client = self
            self.initialized = True
    
    async def refresh_access_token(self):
        """Refresh TravClan access token using internal service login"""
        async with self._lock:
            if not self._client:
                raise HTTPException(status_code=500, detail="HTTP client not initialized")
            
            # Use refresh token if available, otherwise use login
            refresh_token = self.token_manager.get_refresh_token()
            
            if refresh_token:
                await self._refresh_with_refresh_token(refresh_token)
            else:
                await self._login_and_get_token()
    
    async def _login_and_get_token(self):
        """Login to TravClan authentication service"""
        try:
            login_payload = {
                "api_key": settings.TRAVCLAN_API_KEY,
                "merchant_id": settings.TRAVCLAN_MERCHANT_ID,
                "user_id": settings.TRAVCLAN_USER_ID
            }
            
            response = await self._client.post(
                settings.TRAVCLAN_AUTH_LOGIN_URL,
                headers={'Content-Type': 'application/json'},
                json=login_payload
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=401, 
                    detail=f"Failed to login to TravClan: {response.text}"
                )
            
            token_data = response.json()
            
            # Extract token information - TravClan uses different field names
            access_token = token_data.get('AccessToken') or token_data.get('accessToken')
            refresh_token = token_data.get('RefreshToken') or token_data.get('refreshToken')
            expires_in = token_data.get('ExpiresIn', token_data.get('expiresIn', 3600))  # Default to 1 hour
            
            if not access_token:
                raise HTTPException(
                    status_code=401,
                    detail="No access token received from TravClan login"
                )
            
            self.token_manager.set_tokens(
                access_token=access_token,
                expires_in=expires_in,
                refresh_token=refresh_token
            )
            
            logger.info("TravClan login successful, token refreshed")
            
        except httpx.RequestError as e:
            logger.error(f"Network error during TravClan login: {e}")
            raise HTTPException(status_code=500, detail="Network error during authentication")
        except Exception as e:
            logger.error(f"Unexpected error during TravClan login: {e}")
            raise HTTPException(status_code=500, detail="Failed to authenticate with TravClan")
    
    async def _refresh_with_refresh_token(self, refresh_token: str):
        """Refresh token using refresh token"""
        try:
            refresh_payload = {
                "refreshToken": refresh_token
            }
            
            response = await self._client.post(
                settings.TRAVCLAN_AUTH_REFRESH_URL,
                headers={'Content-Type': 'application/json'},
                json=refresh_payload
            )
            
            if response.status_code != 200:
                logger.warning("Refresh token failed, falling back to login")
                await self._login_and_get_token()
                return
            
            token_data = response.json()
            
            # Extract new token information - TravClan uses different field names
            access_token = token_data.get('AccessToken') or token_data.get('accessToken')
            new_refresh_token = token_data.get('RefreshToken') or token_data.get('refreshToken', refresh_token)
            expires_in = token_data.get('ExpiresIn', token_data.get('expiresIn', 3600))
            
            if not access_token:
                logger.warning("No access token in refresh response, falling back to login")
                await self._login_and_get_token()
                return
            
            self.token_manager.set_tokens(
                access_token=access_token,
                expires_in=expires_in,
                refresh_token=new_refresh_token
            )
            
            logger.info("TravClan token refreshed successfully")
            
        except Exception as e:
            logger.error(f"Refresh token failed: {e}, falling back to login")
            await self._login_and_get_token()
    
    async def get_access_token(self) -> str:
        """Get the current access token"""
        return await self.token_manager_singleton.get_valid_access_token()
    
    # Location Search
    async def search_locations(self, search_keyword: str) -> Dict[str, Any]:
        """Search for locations"""
        try:
            response = await self.make_request(
                'GET',
                '/api/v1/locations/search',
                params={'searchString': search_keyword}
            )
            return response
            
        except Exception as e:
            logger.error(f"TravClan search locations failed: {e}")
            raise HTTPException(status_code=500, detail=f"Location search failed: {str(e)}")
    
    # Hotel Search
    async def search_hotels(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Search for hotels"""
        default_payload = {
            'filterBy': {
                'subLocationIds': None,
                'ratings': [4, 5],
                'facilities': None,
                'type': None,
                'tags': None,
                'reviewRatings': None
            }
        }
        
        payload = {**default_payload, **request_data}
        
        logger.info(f"TravClan searchHotels payload: {payload}")
        
        try:
            response = await self.make_request(
                'POST',
                '/hms/external/api/v1/hotels/search',
                data=payload,
                use_search_api=True
            )
            return response
            
        except Exception as e:
            logger.error(f"TravClan hotel search failed: {e}")
            raise HTTPException(status_code=500, detail=f"Hotel search failed: {str(e)}")
    
    # Hotel Static Content
    async def get_hotel_static_content(self, hotel_id: str) -> Dict[str, Any]:
        """Get hotel static content"""
        try:
            response = await self.make_request(
                'GET',
                f'/api/v1/hotels/{hotel_id}/static-content'
            )
            return response
            
        except Exception as e:
            logger.error(f"TravClan hotel static content failed: {e}")
            raise HTTPException(status_code=500, detail=f"Hotel static content failed: {str(e)}")
    
    # Hotel Itinerary Creation
    async def create_hotel_itinerary(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create hotel itinerary"""
        try:
            response = await self.make_request(
                'POST',
                '/api/v2/hotels/itineraries',
                data=request_data
            )
            return response
            
        except Exception as e:
            logger.error(f"TravClan create hotel itinerary failed: {e}")
            raise HTTPException(status_code=500, detail=f"Create itinerary failed: {str(e)}")
    
    async def create_direct_hotel_itinerary(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create direct hotel itinerary"""
        try:
            response = await self.make_request(
                'POST',
                '/api/v1/hotels/itineraries',
                data=request_data
            )
            return response
            
        except Exception as e:
            logger.error(f"TravClan create direct hotel itinerary failed: {e}")
            raise HTTPException(status_code=500, detail=f"Create direct itinerary failed: {str(e)}")
    
    # Room Rate Selection
    async def select_room_rates(self, itinerary_id: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Select room rates for an itinerary"""
        try:
            response = await self.make_request(
                'POST',
                f'/api/v1/hotels/itineraries/{itinerary_id}/select-roomrates',
                data=request_data
            )
            return response
            
        except Exception as e:
            logger.error(f"TravClan select room rates failed: {e}")
            raise HTTPException(status_code=500, detail=f"Select room rates failed: {str(e)}")
    
    # Guest Allocation
    async def allocate_guests_to_rooms(self, itinerary_code: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Allocate guests to rooms"""
        try:
            response = await self.make_request(
                'POST',
                f'/api/v1/hotels/itineraries/{itinerary_code}/rooms-allocations',
                data=request_data
            )
            return response
            
        except Exception as e:
            logger.error(f"TravClan allocate guests to rooms failed: {e}")
            raise HTTPException(status_code=500, detail=f"Guest allocation failed: {str(e)}")
    
    # Itinerary Details
    async def get_itinerary_details(self, itinerary_code: str, query_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get itinerary details"""
        try:
            response = await self.make_request(
                'GET',
                f'/api/v1/hotels/itineraries/{itinerary_code}',
                params=query_params or {}
            )
            return response
            
        except Exception as e:
            logger.error(f"TravClan get itinerary details failed: {e}")
            raise HTTPException(status_code=500, detail=f"Get itinerary details failed: {str(e)}")
    
    # Price Check
    async def check_itinerary_price(self, itinerary_code: str, trace_id: Optional[str] = None) -> Dict[str, Any]:
        """Check itinerary price"""
        query_params = {}
        if trace_id:
            query_params['traceId'] = trace_id
        
        try:
            response = await self.make_request(
                'GET',
                f'/api/v1/hotels/itineraries/{itinerary_code}/check-price',
                params=query_params
            )
            return response
            
        except Exception as e:
            logger.error(f"TravClan check itinerary price failed: {e}")
            raise HTTPException(status_code=500, detail=f"Price check failed: {str(e)}")
    
    # Booking
    async def book_itinerary(self, itinerary_code: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Book an itinerary"""
        try:
            response = await self.make_request(
                'POST',
                f'/api/v1/hotels/itineraries/{itinerary_code}/book',
                data=request_data
            )
            return response
            
        except Exception as e:
            logger.error(f"TravClan book itinerary failed: {e}")
            raise HTTPException(status_code=500, detail=f"Booking failed: {str(e)}")
    
    # Booking Details
    async def get_booking_details(self, booking_code: str, query_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get booking details"""
        try:
            response = await self.make_request(
                'GET',
                f'/api/v1/hotels/itineraries/bookings/{booking_code}',
                params=query_params or {}
            )
            return response
            
        except Exception as e:
            logger.error(f"TravClan get booking details failed: {e}")
            raise HTTPException(status_code=500, detail=f"Get booking details failed: {str(e)}")
    
    # Cancel Booking
    async def cancel_booking(self, booking_code: str, trace_id: str) -> Dict[str, Any]:
        """Cancel a booking"""
        request_data = {'traceId': trace_id}
        
        try:
            response = await self.make_request(
                'POST',
                f'/api/v1/hotels/itineraries/bookings/{booking_code}/cancel',
                data=request_data
            )
            return response
            
        except Exception as e:
            logger.error(f"TravClan cancel booking failed: {e}")
            raise HTTPException(status_code=500, detail=f"Booking cancellation failed: {str(e)}")


# Singleton instance
travclan_api_service = TravClanHotelApiService()