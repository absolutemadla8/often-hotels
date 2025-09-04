from datetime import datetime, date
from typing import Dict, List, Optional, Any
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


# Price History Schemas
class PriceHistoryBase(BaseModel):
    price_date: date = Field(..., description="Date for which price applies")
    check_in_date: date = Field(..., description="Check-in date for the booking")
    check_out_date: date = Field(..., description="Check-out date for the booking")
    price_per_night: Decimal = Field(..., ge=0, description="Price per night")
    total_price: Decimal = Field(..., ge=0, description="Total price for stay")
    currency: str = Field(default="USD", max_length=3)
    is_available: bool = True
    occupancies: List[Dict[str, Any]] = Field(..., description="TravClan occupancy format: [{'numOfAdults': 2, 'childAges': [3]}]")
    partner_name: str = Field(..., max_length=100, description="API partner providing this price")
    external_rate_id: Optional[str] = None
    rate_name: Optional[str] = None
    trace_id: Optional[str] = Field(None, description="TravClan traceId for room rates API")
    cancellation_policy: Optional[str] = None
    payment_policy: Optional[str] = None
    booking_conditions: Optional[Dict[str, Any]] = None

    @field_validator('check_out_date', mode='after')
    @classmethod
    def validate_dates(cls, v, info):
        if v and info.data.get('check_in_date') and v <= info.data['check_in_date']:
            raise ValueError('Check-out date must be after check-in date')
        return v

    @field_validator('total_price', mode='after')
    @classmethod
    def validate_total_price(cls, v, info):
        if v and info.data.get('price_per_night') and info.data.get('check_in_date') and info.data.get('check_out_date'):
            nights = (info.data['check_out_date'] - info.data['check_in_date']).days
            expected_total = info.data['price_per_night'] * nights
            if abs(float(v) - float(expected_total)) > 0.01:  # Allow small rounding differences
                raise ValueError(f'Total price should be {expected_total} for {nights} nights')
        return v


class PriceHistoryCreate(PriceHistoryBase):
    hotel_id: int
    room_id: int
    api_response_time_ms: Optional[int] = Field(None, ge=0)
    api_raw_data: Optional[Dict[str, Any]] = None
    quality_score: Optional[float] = Field(None, ge=0, le=1)
    validation_errors: Optional[List[str]] = None


class PriceHistoryUpdate(BaseModel):
    is_available: Optional[bool] = None
    is_valid: Optional[bool] = None
    quality_score: Optional[float] = Field(None, ge=0, le=1)
    validation_errors: Optional[List[str]] = None


class PriceHistoryResponse(PriceHistoryBase):
    id: int
    hotel_id: int
    room_id: int
    nights: int
    price_changed: bool = False
    previous_price: Optional[Decimal] = None
    price_change_amount: Optional[Decimal] = None
    price_change_percent: Optional[float] = None
    trace_id: Optional[str] = None
    collected_at: datetime
    api_response_time_ms: Optional[int] = None
    is_valid: bool = True
    quality_score: Optional[float] = None
    validation_errors: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PriceHistoryWithHotelRoom(PriceHistoryResponse):
    hotel_name: str
    hotel_city: str
    room_name: str
    room_type: str


# Price Statistics Schemas
class PriceStatisticsBase(BaseModel):
    check_in_date: date
    check_out_date: date
    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None
    avg_price: Optional[Decimal] = None
    median_price: Optional[Decimal] = None
    price_trend: Optional[str] = Field(None, pattern="^(rising|falling|stable)$")
    trend_strength: Optional[float] = Field(None, ge=0, le=1)
    price_volatility: Optional[float] = Field(None, ge=0)
    price_range: Optional[Decimal] = Field(None, ge=0)


class PriceStatisticsCreate(PriceStatisticsBase):
    hotel_id: int
    room_id: int
    total_price_points: int = 0
    first_seen: Optional[date] = None


class PriceStatisticsResponse(PriceStatisticsBase):
    id: int
    hotel_id: int
    room_id: int
    total_price_points: int
    first_seen: Optional[date] = None
    last_updated: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PriceStatisticsWithDetails(PriceStatisticsResponse):
    hotel_name: str
    hotel_city: str
    room_name: str
    room_type: str
    nights: int


# Price Analysis Schemas
class PriceAnalysisRequest(BaseModel):
    hotel_id: int
    room_id: int
    check_in_date: date
    check_out_date: date
    days_back: int = Field(default=30, ge=1, le=365)
    include_predictions: bool = False

    @field_validator('check_out_date', mode='after')
    @classmethod
    def validate_dates(cls, v, info):
        if v and info.data.get('check_in_date') and v <= info.data['check_in_date']:
            raise ValueError('Check-out date must be after check-in date')
        return v


class PriceAnalysisResponse(BaseModel):
    hotel_id: int
    room_id: int
    hotel_name: str
    room_name: str
    check_in_date: date
    check_out_date: date
    nights: int
    analysis_period_days: int
    current_price: Optional[Decimal] = None
    historical_stats: PriceStatisticsBase
    price_history: List[PriceHistoryResponse]
    price_predictions: Optional[List[Dict[str, Any]]] = None  # Future feature
    recommendations: List[str] = []


# Price Comparison Schemas
class PriceComparisonRequest(BaseModel):
    hotel_ids: List[int] = Field(..., min_length=2, max_length=10)
    check_in_date: date
    check_out_date: date
    occupancies: List[Dict[str, Any]] = Field(..., description="TravClan occupancy format: [{'numOfAdults': 2, 'childAges': [3]}]")

    @field_validator('check_out_date', mode='after')
    @classmethod
    def validate_dates(cls, v, info):
        if v and info.data.get('check_in_date') and v <= info.data['check_in_date']:
            raise ValueError('Check-out date must be after check-in date')
        return v


class HotelPriceComparison(BaseModel):
    hotel_id: int
    hotel_name: str
    city: str
    star_rating: Optional[int] = None
    cheapest_room_price: Optional[Decimal] = None
    most_expensive_room_price: Optional[Decimal] = None
    avg_room_price: Optional[Decimal] = None
    available_rooms: int = 0
    last_updated: Optional[datetime] = None


class PriceComparisonResponse(BaseModel):
    check_in_date: date
    check_out_date: date
    nights: int
    occupancy: int
    hotels: List[HotelPriceComparison]
    cheapest_overall: Optional[HotelPriceComparison] = None
    most_expensive_overall: Optional[HotelPriceComparison] = None


# Bulk Price Operations
class BulkPriceHistoryCreate(BaseModel):
    price_records: List[PriceHistoryCreate] = Field(..., min_length=1, max_length=1000)


class BulkPriceHistoryResponse(BaseModel):
    created_count: int
    updated_count: int
    errors_count: int
    errors: List[Dict[str, Any]] = []


# Price Alerts and Notifications
class PriceDropAlert(BaseModel):
    hotel_name: str
    room_name: str
    check_in_date: date
    check_out_date: date
    old_price: Decimal
    new_price: Decimal
    price_drop_amount: Decimal
    price_drop_percent: float
    currency: str = "USD"


class PriceDropNotification(BaseModel):
    user_email: str
    alerts: List[PriceDropAlert]
    notification_type: str = "price_drop"
    created_at: datetime