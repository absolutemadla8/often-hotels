from datetime import datetime
from typing import List

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base_class import Base


class Hotel(Base):
    __tablename__ = "hotels"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # External partner data
    external_id = Column(String(255), unique=True, index=True, nullable=False)  # Partner's hotel ID
    partner_name = Column(String(100), nullable=False)  # Which partner API (e.g., "booking.com", "expedia")
    
    # Basic hotel information
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    address = Column(Text, nullable=False)
    city = Column(String(100), nullable=False, index=True)
    country = Column(String(100), nullable=False, index=True)
    postal_code = Column(String(20), nullable=True)
    
    # Geographic coordinates
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # Hotel details
    star_rating = Column(Integer, nullable=True)  # 1-5 stars
    phone_number = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    website_url = Column(String(500), nullable=True)
    
    # Amenities and features (stored as JSON)
    amenities = Column(JSON, nullable=True)  # ["wifi", "pool", "spa", "parking"]
    images = Column(JSON, nullable=True)  # [{"url": "", "caption": "", "type": ""}]
    
    # Operational status
    is_active = Column(Boolean, default=True)
    is_bookable = Column(Boolean, default=True)
    
    # Pricing info
    currency = Column(String(3), nullable=False, default="USD")  # ISO currency code
    
    # External API metadata
    api_last_updated = Column(DateTime(timezone=True), nullable=True)
    api_data = Column(JSON, nullable=True)  # Store raw API response for debugging
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    
    # Relationships
    rooms = relationship("Room", back_populates="hotel", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="hotel")
    price_histories = relationship("PriceHistory", back_populates="hotel")
    
    def __repr__(self):
        return f"<Hotel(id={self.id}, name='{self.name}', external_id='{self.external_id}')>"


class Room(Base):
    __tablename__ = "rooms"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    
    # External partner data
    external_id = Column(String(255), nullable=False, index=True)  # Partner's room ID
    
    # Room information
    name = Column(String(255), nullable=False)  # "Deluxe King Room", "Standard Double"
    description = Column(Text, nullable=True)
    room_type = Column(String(100), nullable=False)  # "king", "double", "suite"
    
    # Room capacity and features
    max_occupancy = Column(Integer, nullable=False, default=2)
    bed_type = Column(String(100), nullable=True)  # "King", "Queen", "Twin"
    room_size_sqm = Column(Float, nullable=True)  # Room size in square meters
    
    # Room amenities
    amenities = Column(JSON, nullable=True)  # ["wifi", "tv", "minibar", "balcony"]
    images = Column(JSON, nullable=True)  # Room images
    
    # Availability and pricing
    is_active = Column(Boolean, default=True)
    is_bookable = Column(Boolean, default=True)
    base_price = Column(Float, nullable=True)  # Base nightly rate
    
    # External API metadata
    api_last_updated = Column(DateTime(timezone=True), nullable=True)
    api_data = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    
    # Relationships
    hotel = relationship("Hotel", back_populates="rooms")
    bookings = relationship("Booking", back_populates="room")
    price_histories = relationship("PriceHistory", back_populates="room")
    
    def __repr__(self):
        return f"<Room(id={self.id}, name='{self.name}', hotel_id={self.hotel_id})>"


