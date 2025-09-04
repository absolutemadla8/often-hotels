from datetime import datetime, date
from typing import Dict, List, Optional, Any
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


# Hotel Schemas
class HotelBase(BaseModel):
    external_id: str = Field(..., description="Partner's hotel ID")
    partner_name: str = Field(..., description="API partner name")
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    address: str
    city: str = Field(..., max_length=100)
    country: str = Field(..., max_length=100)
    postal_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    star_rating: Optional[int] = Field(None, ge=1, le=5)
    phone_number: Optional[str] = None
    email: Optional[str] = None
    website_url: Optional[str] = None
    amenities: Optional[List[str]] = None
    images: Optional[List[Dict[str, Any]]] = None
    is_active: bool = True
    is_bookable: bool = True
    currency: str = Field(default="USD", max_length=3)


class HotelCreate(HotelBase):
    api_data: Optional[Dict[str, Any]] = None  # Raw API response data


class HotelUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    star_rating: Optional[int] = Field(None, ge=1, le=5)
    phone_number: Optional[str] = None
    email: Optional[str] = None
    website_url: Optional[str] = None
    amenities: Optional[List[str]] = None
    images: Optional[List[Dict[str, Any]]] = None
    is_active: Optional[bool] = None
    is_bookable: Optional[bool] = None
    currency: Optional[str] = None
    api_data: Optional[Dict[str, Any]] = None


class HotelResponse(HotelBase):
    id: int
    api_last_updated: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class HotelWithRooms(HotelResponse):
    rooms: List["RoomResponse"] = []


# Room Schemas
class RoomBase(BaseModel):
    external_id: str = Field(..., description="Partner's room ID")
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    room_type: str = Field(..., max_length=100)
    max_occupancy: int = Field(default=2, ge=1)
    bed_type: Optional[str] = None
    room_size_sqm: Optional[float] = Field(None, ge=0)
    amenities: Optional[List[str]] = None
    images: Optional[List[Dict[str, Any]]] = None
    is_active: bool = True
    is_bookable: bool = True
    base_price: Optional[Decimal] = None


class RoomCreate(RoomBase):
    hotel_id: int
    api_data: Optional[Dict[str, Any]] = None


class RoomUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    room_type: Optional[str] = None
    max_occupancy: Optional[int] = Field(None, ge=1)
    bed_type: Optional[str] = None
    room_size_sqm: Optional[float] = Field(None, ge=0)
    amenities: Optional[List[str]] = None
    images: Optional[List[Dict[str, Any]]] = None
    is_active: Optional[bool] = None
    is_bookable: Optional[bool] = None
    base_price: Optional[Decimal] = None
    api_data: Optional[Dict[str, Any]] = None


class RoomResponse(RoomBase):
    id: int
    hotel_id: int
    api_last_updated: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RoomWithHotel(RoomResponse):
    hotel: HotelResponse


# Hotel Search and Filter Schemas
class HotelSearchRequest(BaseModel):
    city: Optional[str] = None
    country: Optional[str] = None
    check_in_date: Optional[date] = None
    check_out_date: Optional[date] = None
    guests: Optional[int] = Field(default=2, ge=1, le=10)
    min_star_rating: Optional[int] = Field(None, ge=1, le=5)
    max_star_rating: Optional[int] = Field(None, ge=1, le=5)
    amenities: Optional[List[str]] = None
    partner_name: Optional[str] = None
    max_price: Optional[Decimal] = None
    min_price: Optional[Decimal] = None
    currency: str = Field(default="USD", max_length=3)
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)

    @field_validator('check_out_date', mode='after')
    @classmethod
    def validate_dates(cls, v, info):
        if v and info.data.get('check_in_date') and v <= info.data['check_in_date']:
            raise ValueError('Check-out date must be after check-in date')
        return v


class HotelSearchResponse(BaseModel):
    hotels: List[HotelWithRooms]
    total_count: int
    has_more: bool
    search_params: HotelSearchRequest


# Price Information Schema (for API responses)
class RoomPriceInfo(BaseModel):
    room_id: int
    room_name: str
    price_per_night: Decimal
    total_price: Decimal
    currency: str
    is_available: bool
    rate_name: Optional[str] = None
    cancellation_policy: Optional[str] = None
    booking_conditions: Optional[Dict[str, Any]] = None


class HotelPriceInfo(BaseModel):
    hotel_id: int
    hotel_name: str
    check_in_date: date
    check_out_date: date
    nights: int
    rooms: List[RoomPriceInfo]
    last_updated: datetime


# Forward reference fix
HotelWithRooms.model_rebuild()