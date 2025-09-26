from typing import Dict, Any, List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel, Field, field_validator

from app.api.tortoise_deps import get_current_verified_user
from app.models.models import User
from app.services.travclan_api_service import travclan_api_service

router = APIRouter()


class OccupancyRequest(BaseModel):
    numOfAdults: int = Field(..., ge=1, le=10, description="Number of adults")
    childAges: Optional[List[int]] = Field(default=[], description="Ages of children")


class DirectItineraryRequest(BaseModel):
    hotelId: str = Field(..., description="Hotel ID from external provider")
    checkIn: date = Field(..., description="Check-in date")
    checkOut: date = Field(..., description="Check-out date")
    occupancies: List[OccupancyRequest] = Field(..., min_length=1, description="Room occupancies")
    nationality: Optional[str] = Field(None, min_length=2, max_length=2, description="Nationality code")
    
    @field_validator('checkOut')
    @classmethod
    def validate_dates(cls, v, info):
        if v and info.data.get('checkIn') and v <= info.data['checkIn']:
            raise ValueError('Check-out date must be after check-in date')
        return v


class ItineraryRequest(BaseModel):
    hotelId: str = Field(..., description="Hotel ID") 
    traceId: str = Field(..., description="Trace ID from search")


class RoomRateAllocation(BaseModel):
    rateId: str = Field(..., description="Rate ID")
    roomId: str = Field(..., description="Room ID")
    occupancy: Dict[str, int] = Field(..., description="Occupancy details")


class RoomRateSelectionRequest(BaseModel):
    roomsAndRateAllocations: List[RoomRateAllocation] = Field(..., min_length=1)
    recommendationId: str = Field(..., description="Recommendation ID")
    acceptPriceChange: Optional[bool] = Field(default=False, description="Accept price changes")


class GuestRequest(BaseModel):
    title: str = Field(..., pattern="^(Mr|Mrs|Miss|Ms)$")
    firstName: str = Field(..., max_length=50)
    lastName: str = Field(..., max_length=50)
    isLeadGuest: Optional[bool] = Field(default=False)
    type: str = Field(..., pattern="^(adult|child|infant)$")
    email: str = Field(..., description="Email address")
    isdCode: int = Field(..., description="ISD code")
    contactNumber: str = Field(..., max_length=20)
    panCardNumber: Optional[str] = Field(None, max_length=20)
    passportNumber: Optional[str] = Field(None, max_length=50)
    passportExpiry: Optional[date] = Field(None, description="Passport expiry date")
    roomIndex: int = Field(..., ge=0, description="Room index")


class GuestAllocationRequest(BaseModel):
    guests: List[GuestRequest] = Field(..., min_length=1)
    specialRequests: Optional[str] = Field(None, max_length=500)


class BookingRequest(BaseModel):
    guestDetails: Dict[str, Any] = Field(..., description="Guest details")
    paymentInfo: Dict[str, Any] = Field(..., description="Payment information")
    traceId: str = Field(..., description="Trace ID")


@router.post("/create-direct-itinerary")
async def create_direct_hotel_itinerary(
    request: DirectItineraryRequest,
    current_user: User = Depends(get_current_verified_user),
) -> Dict[str, Any]:
    """
    Get room rates directly using hotel external ID
    
    This is used when we already know the hotel's external provider ID and want
    to get current room rates and availability without needing a search traceId.
    Perfect for getting rates for user's existing bookings.
    """
    try:
        # Convert dates to strings
        request_data = request.model_dump()
        request_data['checkIn'] = request.checkIn.isoformat()
        request_data['checkOut'] = request.checkOut.isoformat()
        
        async with travclan_api_service:
            response = await travclan_api_service.create_direct_hotel_itinerary(request_data)
        
        # Process room data for potential room name matching and storage
        try:
            from app.services.hotel_service import HotelService
            hotel_service = HotelService()
            
            # Extract room data from response for fuzzy matching with existing rooms
            rooms_data = response.get('results', [{}])[0].get('items', [])
            if rooms_data:
                # Process each room type for potential matching
                for room_item in rooms_data:
                    room_info = room_item.get('roomTypeInfo', {})
                    room_name = room_info.get('name', '')
                    
                    # Log room name for tracking and debugging
                    import logging
                    logging.getLogger(__name__).info(f"Room found in direct API: {room_name} for hotel {request.hotelId}")
                    
                    # Here we can potentially match with existing rooms using fuzzy matching
                    # This is useful for updating room details with API-specific information
        
        except Exception as e:
            # Don't fail the API call if room processing fails
            import logging
            logging.getLogger(__name__).warning(f"Room processing failed for hotel {request.hotelId}: {e}")
        
        return {
            "status": "success",
            "message": "Room rates retrieved successfully",
            "data": response
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create direct itinerary: {str(e)}")


@router.post("/create-itinerary")
async def create_hotel_itinerary(
    request: ItineraryRequest,
    current_user: User = Depends(get_current_verified_user),
) -> Dict[str, Any]:
    """
    Create hotel itinerary from search results
    """
    try:
        request_data = request.model_dump()
        
        async with travclan_api_service:
            response = await travclan_api_service.create_hotel_itinerary(request_data)
        
        return {
            "status": "success",
            "message": "Hotel itinerary created successfully", 
            "data": response
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create itinerary: {str(e)}")


@router.post("/itinerary/{itinerary_id}/select-room-rates")
async def select_room_rates(
    itinerary_id: str = Path(..., description="Itinerary ID"),
    request: RoomRateSelectionRequest = ...,
    current_user: User = Depends(get_current_verified_user),
) -> Dict[str, Any]:
    """
    Select room rates for an itinerary
    """
    try:
        request_data = request.model_dump()
        
        async with travclan_api_service:
            response = await travclan_api_service.select_room_rates(itinerary_id, request_data)
        
        # Check for price changes
        price_changed = response.get('results', [{}])[0].get('items', [{}])[0].get('priceChangeData', {}).get('isPriceChanged', False)
        
        if price_changed and not request.acceptPriceChange:
            return {
                "status": "price_changed",
                "message": "The price for the selected room has changed. Please review the updated pricing details.",
                "data": response
            }
        
        return {
            "status": "success",
            "message": "Room rates selected successfully",
            "data": response
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to select room rates: {str(e)}")


@router.post("/itinerary/{itinerary_code}/allocate-guests")
async def allocate_guests_to_rooms(
    itinerary_code: str = Path(..., description="Itinerary code"),
    request: GuestAllocationRequest = ...,
    current_user: User = Depends(get_current_verified_user),
) -> Dict[str, Any]:
    """
    Allocate guests to rooms for an itinerary
    """
    try:
        request_data = request.model_dump()
        
        async with travclan_api_service:
            response = await travclan_api_service.allocate_guests_to_rooms(itinerary_code, request_data)
        
        return {
            "status": "success",
            "message": "Guests allocated successfully",
            "data": response
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to allocate guests: {str(e)}")


@router.get("/itinerary/{itinerary_code}")
async def get_itinerary_details(
    itinerary_code: str = Path(..., description="Itinerary code"),
    traceId: Optional[str] = None,
    current_user: User = Depends(get_current_verified_user),
) -> Dict[str, Any]:
    """
    Get detailed information about an itinerary
    """
    try:
        query_params = {}
        if traceId:
            query_params['traceId'] = traceId
        
        async with travclan_api_service:
            response = await travclan_api_service.get_itinerary_details(itinerary_code, query_params)
        
        return {
            "status": "success",
            "data": response
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get itinerary details: {str(e)}")


@router.get("/itinerary/{itinerary_code}/check-price")
async def check_itinerary_price(
    itinerary_code: str = Path(..., description="Itinerary code"),
    traceId: Optional[str] = None,
    current_user: User = Depends(get_current_verified_user),
) -> Dict[str, Any]:
    """
    Check current price for an itinerary
    """
    try:
        async with travclan_api_service:
            response = await travclan_api_service.check_itinerary_price(itinerary_code, traceId)
        
        return {
            "status": "success",
            "data": response
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check price: {str(e)}")


@router.post("/itinerary/{itinerary_code}/book")
async def book_itinerary(
    itinerary_code: str = Path(..., description="Itinerary code"),
    request: BookingRequest = ...,
    current_user: User = Depends(get_current_verified_user),
) -> Dict[str, Any]:
    """
    Book an itinerary
    """
    try:
        request_data = request.model_dump()
        
        async with travclan_api_service:
            response = await travclan_api_service.book_itinerary(itinerary_code, request_data)
        
        return {
            "status": "success",
            "message": "Booking confirmed successfully",
            "data": response
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Booking failed: {str(e)}")


@router.get("/booking/{booking_code}")
async def get_booking_details(
    booking_code: str = Path(..., description="Booking code"),
    traceId: Optional[str] = None,
    current_user: User = Depends(get_current_verified_user),
) -> Dict[str, Any]:
    """
    Get booking details
    """
    try:
        query_params = {}
        if traceId:
            query_params['traceId'] = traceId
        
        async with travclan_api_service:
            response = await travclan_api_service.get_booking_details(booking_code, query_params)
        
        return {
            "status": "success",
            "data": response
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get booking details: {str(e)}")


class CancelBookingRequest(BaseModel):
    traceId: str = Field(..., description="Trace ID")


@router.post("/booking/{booking_code}/cancel")
async def cancel_booking(
    booking_code: str = Path(..., description="Booking code"),
    request: CancelBookingRequest = ...,
    current_user: User = Depends(get_current_verified_user),
) -> Dict[str, Any]:
    """
    Cancel a booking
    """
    try:
        async with travclan_api_service:
            response = await travclan_api_service.cancel_booking(booking_code, request.traceId)
        
        return {
            "status": "success",
            "message": "Booking cancelled successfully",
            "data": response
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel booking: {str(e)}")