from datetime import datetime, date
from typing import Dict, List, Optional, Any
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field, field_validator

from app.models.booking import BookingStatus, NotificationStatus


# Booking Schemas
class BookingBase(BaseModel):
    check_in_date: date = Field(..., description="Check-in date")
    check_out_date: date = Field(..., description="Check-out date")
    guests: int = Field(default=1, ge=1, le=10)
    room_preferences: Optional[Dict[str, Any]] = None
    special_requests: Optional[str] = None
    target_price: Optional[Decimal] = Field(None, ge=0, description="Target price for alerts")
    currency: str = Field(default="USD", max_length=3)
    booking_name: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None
    price_drop_threshold_percent: Optional[float] = Field(default=5.0, ge=0, le=50)
    price_drop_threshold_amount: Optional[Decimal] = Field(None, ge=0)
    notification_frequency_hours: int = Field(default=24, ge=1, le=168)  # Max 1 week

    @field_validator('check_out_date', mode='after')
    @classmethod
    def validate_dates(cls, v, info):
        if v and info.data.get('check_in_date'):
            if v <= info.data['check_in_date']:
                raise ValueError('Check-out date must be after check-in date')
            
            # Check if booking is within 2 months of check-in date
            from datetime import date, timedelta
            max_advance_days = 60  # 2 months
            if (info.data['check_in_date'] - date.today()).days > max_advance_days:
                raise ValueError(f'Bookings can only be created up to {max_advance_days} days in advance')
        return v

    @field_validator('check_in_date', mode='after')
    @classmethod
    def validate_check_in_future(cls, v):
        from datetime import date
        if v and v <= date.today():
            raise ValueError('Check-in date must be in the future')
        return v


class BookingCreate(BookingBase):
    hotel_id: int = Field(..., description="Hotel ID")
    room_id: int = Field(..., description="Room ID")
    initial_price: Optional[Decimal] = Field(None, ge=0)

    @field_validator('hotel_id', 'room_id')
    @classmethod
    def validate_ids(cls, v):
        if v <= 0:
            raise ValueError('IDs must be positive integers')
        return v


class BookingUpdate(BaseModel):
    check_in_date: Optional[date] = None
    check_out_date: Optional[date] = None
    guests: Optional[int] = Field(None, ge=1, le=10)
    room_preferences: Optional[Dict[str, Any]] = None
    special_requests: Optional[str] = None
    target_price: Optional[Decimal] = Field(None, ge=0)
    booking_name: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None
    status: Optional[BookingStatus] = None
    notification_status: Optional[NotificationStatus] = None
    price_drop_threshold_percent: Optional[float] = Field(None, ge=0, le=50)
    price_drop_threshold_amount: Optional[Decimal] = Field(None, ge=0)
    notification_frequency_hours: Optional[int] = Field(None, ge=1, le=168)
    external_booking_reference: Optional[str] = None
    booking_platform: Optional[str] = None
    actual_booking_price: Optional[Decimal] = Field(None, ge=0)

    @field_validator('check_out_date', mode='after')
    @classmethod
    def validate_dates(cls, v, info):
        if v and info.data.get('check_in_date') and v <= info.data['check_in_date']:
            raise ValueError('Check-out date must be after check-in date')
        return v


class BookingResponse(BookingBase):
    id: int
    user_id: int
    hotel_id: int
    room_id: int
    nights: int
    initial_price: Optional[Decimal] = None
    status: BookingStatus
    notification_status: NotificationStatus
    last_notification_sent: Optional[datetime] = None
    external_booking_reference: Optional[str] = None
    booking_platform: Optional[str] = None
    actual_booking_date: Optional[datetime] = None
    actual_booking_price: Optional[Decimal] = None
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BookingWithDetails(BookingResponse):
    hotel_name: str
    hotel_city: str
    hotel_country: str
    room_name: str
    room_type: str
    current_price: Optional[Decimal] = None
    lowest_price_seen: Optional[Decimal] = None
    highest_price_seen: Optional[Decimal] = None
    days_until_checkin: int
    price_alerts_count: int


class BookingListResponse(BaseModel):
    bookings: List[BookingWithDetails]
    total_count: int
    active_count: int
    expired_count: int


# Price Alert Schemas
class PriceAlertBase(BaseModel):
    alert_type: str = Field(..., max_length=50)
    old_price: Optional[Decimal] = None
    new_price: Optional[Decimal] = None
    price_difference: Optional[Decimal] = None
    percentage_change: Optional[float] = None
    message: str
    alert_data: Optional[Dict[str, Any]] = None


class PriceAlertCreate(PriceAlertBase):
    booking_id: int
    delivery_method: Optional[str] = Field(default="email", max_length=50)


class PriceAlertResponse(PriceAlertBase):
    id: int
    booking_id: int
    user_id: int
    is_sent: bool = False
    sent_at: Optional[datetime] = None
    delivery_method: Optional[str] = None
    delivery_status: Optional[str] = None
    created_at: datetime
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Bulk Operations
class BulkBookingUpdate(BaseModel):
    booking_ids: List[int] = Field(..., min_length=1)
    update_data: BookingUpdate


class BulkStatusUpdate(BaseModel):
    booking_ids: List[int] = Field(..., min_length=1)
    status: BookingStatus


class BookingStatsResponse(BaseModel):
    total_bookings: int
    active_bookings: int
    cancelled_bookings: int
    expired_bookings: int
    total_alerts_sent: int
    avg_price_drop_percent: Optional[float] = None
    most_tracked_hotel: Optional[str] = None
    upcoming_checkins: int  # Next 7 days


# Search and Filter
class BookingSearchRequest(BaseModel):
    status: Optional[BookingStatus] = None
    notification_status: Optional[NotificationStatus] = None
    hotel_name: Optional[str] = None
    city: Optional[str] = None
    check_in_after: Optional[date] = None
    check_in_before: Optional[date] = None
    min_nights: Optional[int] = Field(None, ge=1)
    max_nights: Optional[int] = Field(None, ge=1)
    has_alerts: Optional[bool] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    sort_by: Optional[str] = Field(default="created_at", pattern="^(created_at|check_in_date|updated_at|nights)$")
    sort_order: Optional[str] = Field(default="desc", pattern="^(asc|desc)$")
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


# Quick Actions
class BookingQuickActions(BaseModel):
    pause_notifications: bool = False
    resume_notifications: bool = False
    mark_as_booked: bool = False
    cancel_tracking: bool = False
    update_target_price: Optional[Decimal] = None