from fastapi import APIRouter

from app.api.v1.endpoints import auth, hotels, users, locations, hotel_search, hotel_booking

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(hotels.router, prefix="/hotels", tags=["hotels"])
api_router.include_router(locations.router, prefix="/locations", tags=["locations"])
api_router.include_router(hotel_search.router, prefix="/hotel-search", tags=["hotel-search"])
api_router.include_router(hotel_booking.router, prefix="/hotel-booking", tags=["hotel-booking"])