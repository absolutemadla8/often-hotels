from datetime import datetime, date
from decimal import Decimal
from enum import Enum

from sqlalchemy import Boolean, Column, DateTime, Date, Float, Integer, String, Text, JSON, Enum as SQLEnum, ForeignKey, CheckConstraint, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base_class import Base


class BookingStatus(str, Enum):
    ACTIVE = "active"           # User is tracking this booking
    CANCELLED = "cancelled"     # User cancelled tracking
    EXPIRED = "expired"         # Check-in date has passed
    BOOKED = "booked"          # User actually booked (optional status)


class NotificationStatus(str, Enum):
    ENABLED = "enabled"         # User wants price drop notifications
    DISABLED = "disabled"       # User disabled notifications
    PAUSED = "paused"          # Temporarily paused


class Booking(Base):
    __tablename__ = "bookings"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # User reference
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Hotel and room information (user-provided, not foreign keys)
    hotel_name = Column(String(255), nullable=False, index=True)
    room_name = Column(String(255), nullable=False, index=True)
    hotel_city = Column(String(100), nullable=True, index=True)
    hotel_country = Column(String(100), nullable=True)
    
    # External provider mapping (populated after mapping)
    external_hotel_id = Column(String(255), nullable=True, index=True)  # TravClan hotel ID
    partner_name = Column(String(100), nullable=True)  # "TravClan", "Booking.com", etc.
    
    # Booking details - user provided data
    check_in_date = Column(Date, nullable=False, index=True)
    check_out_date = Column(Date, nullable=False, index=True)
    nights = Column(Integer, nullable=False)  # Calculated: check_out - check_in
    occupancies = Column(JSON, nullable=False)  # TravClan occupancy format: [{"numOfAdults": 2, "childAges": [3]}]
    
    # Room and booking preferences
    room_preferences = Column(JSON, nullable=True)  # User preferences like "ocean view", "high floor"
    special_requests = Column(Text, nullable=True)
    
    # Price tracking information
    initial_price = Column(Numeric(10, 2), nullable=True)  # Price when user first added booking
    target_price = Column(Numeric(10, 2), nullable=True)   # Price user wants to be notified below
    currency = Column(String(3), nullable=False, default="USD")
    
    # Booking metadata
    booking_name = Column(String(255), nullable=True)      # User can name their booking
    notes = Column(Text, nullable=True)                    # User's personal notes
    
    # Status and notifications
    status = Column(SQLEnum(BookingStatus), nullable=False, default=BookingStatus.ACTIVE)
    notification_status = Column(SQLEnum(NotificationStatus), nullable=False, default=NotificationStatus.ENABLED)
    
    # Price alert settings
    price_drop_threshold_percent = Column(Float, nullable=True, default=5.0)  # Notify if price drops by X%
    price_drop_threshold_amount = Column(Numeric(10, 2), nullable=True)       # Notify if price drops by $X
    last_notification_sent = Column(DateTime(timezone=True), nullable=True)
    notification_frequency_hours = Column(Integer, default=24)  # Max one notification per X hours
    
    # External booking reference (if user actually booked)
    external_booking_reference = Column(String(255), nullable=True)
    booking_platform = Column(String(100), nullable=True)  # "booking.com", "expedia", etc.
    actual_booking_date = Column(DateTime(timezone=True), nullable=True)
    actual_booking_price = Column(Numeric(10, 2), nullable=True)
    
    # Tracking metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Auto-calculated based on check_in_date
    
    # Relationships
    user = relationship("User", back_populates="bookings")
    price_alerts = relationship("PriceAlert", back_populates="booking", cascade="all, delete-orphan")
    
    # Table constraints
    __table_args__ = (
        CheckConstraint('check_out_date > check_in_date', name='valid_date_range'),
        CheckConstraint('nights > 0', name='positive_nights'),
        CheckConstraint('price_drop_threshold_percent >= 0', name='valid_threshold_percent'),
    )
    
    def __repr__(self):
        return f"<Booking(id={self.id}, user_id={self.user_id}, hotel_name='{self.hotel_name}', check_in='{self.check_in_date}')>"

    @property
    def is_valid_for_tracking(self) -> bool:
        """Check if booking is still valid for price tracking"""
        from datetime import date
        return (
            self.status == BookingStatus.ACTIVE and
            self.check_in_date > date.today() and
            self.notification_status == NotificationStatus.ENABLED
        )
    
    @property
    def days_until_checkin(self) -> int:
        """Days remaining until check-in"""
        from datetime import date
        return (self.check_in_date - date.today()).days
    
    @property
    def total_guests(self) -> int:
        """Calculate total number of guests from occupancies"""
        if not self.occupancies:
            return 1
        
        total = 0
        for occupancy in self.occupancies:
            total += occupancy.get('numOfAdults', 0)
            total += len(occupancy.get('childAges', []))
        
        return max(total, 1)  # At least 1 guest
    
    @property
    def total_adults(self) -> int:
        """Calculate total number of adults from occupancies"""
        if not self.occupancies:
            return 1
        
        return sum(occupancy.get('numOfAdults', 0) for occupancy in self.occupancies)
    
    @property
    def total_children(self) -> int:
        """Calculate total number of children from occupancies"""
        if not self.occupancies:
            return 0
        
        return sum(len(occupancy.get('childAges', [])) for occupancy in self.occupancies)
    
    @property
    def num_rooms(self) -> int:
        """Number of rooms in this booking"""
        return len(self.occupancies) if self.occupancies else 1


class PriceAlert(Base):
    __tablename__ = "price_alerts"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # References
    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Alert details
    alert_type = Column(String(50), nullable=False)  # "price_drop", "availability_change", "manual"
    old_price = Column(Numeric(10, 2), nullable=True)
    new_price = Column(Numeric(10, 2), nullable=True)
    price_difference = Column(Numeric(10, 2), nullable=True)
    percentage_change = Column(Float, nullable=True)
    
    # Alert message and metadata
    message = Column(Text, nullable=False)
    alert_data = Column(JSON, nullable=True)  # Additional structured data
    
    # Notification delivery
    is_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    delivery_method = Column(String(50), nullable=True)  # "email", "push", "sms"
    delivery_status = Column(String(50), nullable=True)  # "delivered", "failed", "pending"
    
    # Alert metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    booking = relationship("Booking", back_populates="price_alerts")
    user = relationship("User", back_populates="price_alerts")
    
    def __repr__(self):
        return f"<PriceAlert(id={self.id}, booking_id={self.booking_id}, alert_type='{self.alert_type}')>"