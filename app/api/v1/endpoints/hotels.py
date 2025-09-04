from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app import models, schemas
from app.api import deps

router = APIRouter()


# Example hotel data (in production, this would come from a database)
SAMPLE_HOTELS = [
    {
        "id": 1,
        "name": "Luxury Resort & Spa",
        "location": "Bali, Indonesia",
        "description": "A beautiful beachfront resort with world-class amenities",
        "price_per_night": 350.00,
        "rating": 4.8,
        "amenities": ["Pool", "Spa", "Beach Access", "Restaurant", "WiFi"],
        "available": True
    },
    {
        "id": 2,
        "name": "City Center Business Hotel",
        "location": "New York, USA",
        "description": "Modern business hotel in the heart of Manhattan",
        "price_per_night": 275.00,
        "rating": 4.3,
        "amenities": ["Business Center", "Gym", "Restaurant", "WiFi", "Parking"],
        "available": True
    },
    {
        "id": 3,
        "name": "Mountain Lodge",
        "location": "Swiss Alps, Switzerland",
        "description": "Cozy lodge with stunning mountain views",
        "price_per_night": 180.00,
        "rating": 4.6,
        "amenities": ["Mountain View", "Fireplace", "Restaurant", "Hiking Trails"],
        "available": False
    }
]


@router.get("/")
async def get_hotels(
    skip: int = 0,
    limit: int = 10,
    location: Optional[str] = None,
    current_user: Optional[models.User] = Depends(deps.get_optional_current_user),
) -> Any:
    """
    Get list of hotels. (Public endpoint with optional authentication)
    
    - Authenticated users get additional details
    - Public users get basic information only
    """
    hotels = SAMPLE_HOTELS[skip : skip + limit]
    
    if location:
        hotels = [h for h in hotels if location.lower() in h["location"].lower()]
    
    # If user is not authenticated, remove sensitive information
    if not current_user:
        for hotel in hotels:
            hotel.pop("available", None)  # Remove availability for non-authenticated users
            
    return {
        "hotels": hotels,
        "total": len(SAMPLE_HOTELS),
        "authenticated": current_user is not None
    }


@router.get("/{hotel_id}")
async def get_hotel(
    hotel_id: int,
    current_user: Optional[models.User] = Depends(deps.get_optional_current_user),
) -> Any:
    """
    Get hotel details by ID. (Public endpoint with optional authentication)
    """
    hotel = next((h for h in SAMPLE_HOTELS if h["id"] == hotel_id), None)
    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel not found")
    
    # Authenticated users get full details
    if current_user:
        return {
            "hotel": hotel,
            "user_authenticated": True,
            "special_offers": ["10% discount for verified users", "Free breakfast"]
        }
    else:
        # Remove sensitive information for non-authenticated users
        public_hotel = hotel.copy()
        public_hotel.pop("available", None)
        return {
            "hotel": public_hotel,
            "user_authenticated": False,
            "message": "Login for exclusive offers and availability"
        }


@router.post("/{hotel_id}/book")
async def book_hotel(
    hotel_id: int,
    booking_data: dict,  # In production, use proper Pydantic model
    current_user: models.User = Depends(deps.get_current_verified_user),
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    """
    Book a hotel. (Requires verified user authentication)
    """
    hotel = next((h for h in SAMPLE_HOTELS if h["id"] == hotel_id), None)
    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel not found")
    
    if not hotel.get("available", True):
        raise HTTPException(status_code=400, detail="Hotel is not available")
    
    # In production, this would create a booking record in the database
    booking = {
        "booking_id": f"BK{hotel_id}{current_user.id}001",
        "hotel_name": hotel["name"],
        "user_email": current_user.email,
        "user_name": f"{current_user.first_name} {current_user.last_name}",
        "booking_data": booking_data,
        "total_price": hotel["price_per_night"] * booking_data.get("nights", 1),
        "status": "confirmed"
    }
    
    return {
        "message": "Booking confirmed successfully",
        "booking": booking
    }


@router.get("/{hotel_id}/reviews")
async def get_hotel_reviews(
    hotel_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get hotel reviews. (Requires authentication)
    """
    hotel = next((h for h in SAMPLE_HOTELS if h["id"] == hotel_id), None)
    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel not found")
    
    # Sample reviews (in production, fetch from database)
    reviews = [
        {
            "id": 1,
            "user": "John D.",
            "rating": 5,
            "comment": "Absolutely fantastic stay! Will definitely come back.",
            "date": "2024-01-15"
        },
        {
            "id": 2,
            "user": "Sarah M.",
            "rating": 4,
            "comment": "Great location and service. Room could be bigger.",
            "date": "2024-01-10"
        }
    ]
    
    return {
        "hotel_name": hotel["name"],
        "reviews": reviews,
        "average_rating": hotel["rating"]
    }


@router.post("/{hotel_id}/reviews")
async def create_hotel_review(
    hotel_id: int,
    review_data: dict,  # In production, use proper Pydantic model
    current_user: models.User = Depends(deps.get_current_verified_user),
) -> Any:
    """
    Create a hotel review. (Requires verified user authentication)
    """
    hotel = next((h for h in SAMPLE_HOTELS if h["id"] == hotel_id), None)
    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel not found")
    
    # In production, save review to database
    review = {
        "id": len(SAMPLE_HOTELS) + 1,
        "hotel_id": hotel_id,
        "user_id": current_user.id,
        "user_name": f"{current_user.first_name} {current_user.last_name}",
        "rating": review_data.get("rating"),
        "comment": review_data.get("comment"),
        "date": "2024-01-20"
    }
    
    return {
        "message": "Review created successfully",
        "review": review
    }


@router.get("/bookings/my")
async def get_my_bookings(
    current_user: models.User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    """
    Get current user's bookings. (Requires authentication)
    """
    # Sample user bookings (in production, fetch from database)
    bookings = [
        {
            "booking_id": f"BK{current_user.id}001",
            "hotel_name": "Luxury Resort & Spa",
            "check_in": "2024-02-15",
            "check_out": "2024-02-18",
            "total_price": 1050.00,
            "status": "confirmed"
        }
    ]
    
    return {
        "bookings": bookings,
        "total_bookings": len(bookings)
    }


@router.get("/admin/statistics")
async def get_admin_statistics(
    current_user: models.User = Depends(deps.get_current_superuser),
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    """
    Get booking statistics. (Admin only)
    """
    # Sample statistics (in production, calculate from database)
    stats = {
        "total_hotels": len(SAMPLE_HOTELS),
        "total_bookings": 1247,
        "revenue_this_month": 156750.50,
        "active_users": await crud.user.get_multi(db, limit=1000),  # Count active users
        "popular_destinations": [
            {"location": "Bali, Indonesia", "bookings": 342},
            {"location": "New York, USA", "bookings": 289},
            {"location": "Swiss Alps, Switzerland", "bookings": 156}
        ]
    }
    
    return stats