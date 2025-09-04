from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import Boolean, Column, DateTime, Date, Float, Integer, String, JSON, ForeignKey, Numeric, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base_class import Base


class PriceHistory(Base):
    __tablename__ = "price_history"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Hotel and room identification (external data)
    external_hotel_id = Column(String(255), nullable=False, index=True)  # External provider's hotel ID
    hotel_name = Column(String(255), nullable=False, index=True)
    room_name = Column(String(255), nullable=False, index=True)
    hotel_city = Column(String(100), nullable=True, index=True)
    
    # Price tracking details
    price_date = Column(Date, nullable=False, index=True)  # Date for which price applies
    check_in_date = Column(Date, nullable=False, index=True)  # Check-in date for the price
    check_out_date = Column(Date, nullable=False, index=True)  # Check-out date for the price
    nights = Column(Integer, nullable=False)  # Number of nights
    
    # Price information
    price_per_night = Column(Numeric(10, 2), nullable=False)  # Price per night
    total_price = Column(Numeric(10, 2), nullable=False)      # Total price for all nights
    currency = Column(String(3), nullable=False, default="USD")
    
    # Price metadata
    is_available = Column(Boolean, nullable=False, default=True)
    occupancies = Column(JSON, nullable=False)  # TravClan occupancy format: [{"numOfAdults": 2, "childAges": [3]}]
    
    # External API information
    partner_name = Column(String(100), nullable=False)  # Which API provided this price
    external_rate_id = Column(String(255), nullable=True)  # Partner's rate/price plan ID
    rate_name = Column(String(255), nullable=True)  # "Standard Rate", "Advance Purchase", etc.
    trace_id = Column(String(255), nullable=True, index=True)  # TravClan traceId for room rates API
    
    # Booking conditions and restrictions
    cancellation_policy = Column(String(255), nullable=True)
    payment_policy = Column(String(255), nullable=True)
    booking_conditions = Column(JSON, nullable=True)  # Flexible storage for various conditions
    
    # Price change tracking
    price_changed = Column(Boolean, default=False)  # Did price change from previous day?
    previous_price = Column(Numeric(10, 2), nullable=True)  # Previous day's price for comparison
    price_change_amount = Column(Numeric(10, 2), nullable=True)  # Change amount
    price_change_percent = Column(Float, nullable=True)  # Change percentage
    
    # Data collection metadata
    collected_at = Column(DateTime(timezone=True), server_default=func.now())
    api_response_time_ms = Column(Integer, nullable=True)  # How long API took to respond
    api_raw_data = Column(JSON, nullable=True)  # Store raw API response for debugging
    
    # Data quality indicators
    is_valid = Column(Boolean, default=True)  # Is this price data considered valid?
    quality_score = Column(Float, nullable=True)  # 0-1 score of data quality
    validation_errors = Column(JSON, nullable=True)  # Any validation issues found
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # No relationships - all data is external
    
    # Constraints and indexes for optimal querying
    __table_args__ = (
        # Unique constraint to prevent duplicate price records
        UniqueConstraint(
            'external_hotel_id', 'room_name', 'price_date', 'check_in_date', 'check_out_date', 'occupancies',
            name='unique_price_record'
        ),
        # Composite indexes for efficient querying
        Index('idx_price_lookup', 'external_hotel_id', 'room_name', 'check_in_date', 'check_out_date'),
        Index('idx_price_date_range', 'price_date', 'check_in_date'),
        Index('idx_hotel_price_date', 'external_hotel_id', 'price_date'),
        Index('idx_price_collection_date', 'collected_at'),
    )
    
    def __repr__(self):
        return f"<PriceHistory(id={self.id}, hotel_name='{self.hotel_name}', room_name='{self.room_name}', price_date='{self.price_date}', price={self.total_price})>"

    @property
    def price_per_night_float(self) -> float:
        """Convert Decimal to float for API responses"""
        return float(self.price_per_night)
    
    @property
    def total_price_float(self) -> float:
        """Convert Decimal to float for API responses"""
        return float(self.total_price)
    
    @property
    def total_guests(self) -> int:
        """Calculate total number of guests from occupancies"""
        if not self.occupancies:
            return 2  # Default fallback
        
        total = 0
        for occupancy in self.occupancies:
            total += occupancy.get('numOfAdults', 0)
            total += len(occupancy.get('childAges', []))
        
        return max(total, 1)  # At least 1 guest
    
    @property
    def total_adults(self) -> int:
        """Calculate total number of adults from occupancies"""
        if not self.occupancies:
            return 2  # Default fallback
        
        return sum(occupancy.get('numOfAdults', 0) for occupancy in self.occupancies)
    
    @property
    def num_rooms(self) -> int:
        """Number of rooms in this price record"""
        return len(self.occupancies) if self.occupancies else 1


class PriceStatistics(Base):
    __tablename__ = "price_statistics"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # References
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False)
    
    # Statistics period
    check_in_date = Column(Date, nullable=False, index=True)
    check_out_date = Column(Date, nullable=False, index=True)
    
    # Price statistics (calculated daily from price_history)
    min_price = Column(Numeric(10, 2), nullable=True)
    max_price = Column(Numeric(10, 2), nullable=True)
    avg_price = Column(Numeric(10, 2), nullable=True)
    median_price = Column(Numeric(10, 2), nullable=True)
    
    # Price trend indicators
    price_trend = Column(String(20), nullable=True)  # "rising", "falling", "stable"
    trend_strength = Column(Float, nullable=True)    # 0-1 indicator of trend strength
    
    # Volatility metrics
    price_volatility = Column(Float, nullable=True)  # Standard deviation of prices
    price_range = Column(Numeric(10, 2), nullable=True)  # max - min price
    
    # Data collection metrics
    total_price_points = Column(Integer, nullable=False, default=0)
    first_seen = Column(Date, nullable=True)
    last_updated = Column(Date, nullable=True)
    
    # Update tracking
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    hotel = relationship("Hotel")
    room = relationship("Room")
    
    __table_args__ = (
        UniqueConstraint(
            'hotel_id', 'room_id', 'check_in_date', 'check_out_date',
            name='unique_price_stats'
        ),
        Index('idx_stats_lookup', 'hotel_id', 'room_id', 'check_in_date'),
    )
    
    def __repr__(self):
        return f"<PriceStatistics(hotel_id={self.hotel_id}, room_id={self.room_id}, check_in='{self.check_in_date}', avg_price={self.avg_price})>"