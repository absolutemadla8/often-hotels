from datetime import datetime, date, timedelta
from typing import List, Optional, Any, Dict
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
import random

from app.models.models import UniversalPriceHistory
from app.schemas.response import ResponseBase

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


class DestinationStay(BaseModel):
    destination_id: str = Field(..., description="Destination identifier")
    nights: int = Field(..., gt=0, description="Number of nights to stay")


class RecommendationRequest(BaseModel):
    country_code: str = Field(..., description="ISO country code (e.g., 'id' for Indonesia)")
    destinations: List[DestinationStay] = Field(..., min_items=1, description="Array of destinations with nights")
    variations: int = Field(3, ge=1, le=10, description="Number of price/date variations to show")
    start_date: date = Field(..., description="Trip start date")
    adults: int = Field(2, ge=1, description="Number of adults")
    children: int = Field(0, ge=0, description="Number of children")
    currency: str = Field("USD", description="Currency code")


class MetaPrice(BaseModel):
    source: str = Field(..., description="Booking website name (e.g., 'Booking.com')")
    price: float = Field(..., description="Price on this website")


class Hotel(BaseModel):
    name: str
    hotelId: Optional[int] = None
    image: str
    price: float
    currency: str
    status: str
    nights: int
    checkIn: str
    checkOut: str
    meta_prices: List[MetaPrice] = Field(default_factory=list, description="Prices across different booking websites")


class Destination(BaseModel):
    name: str
    destinationId: str
    areaId: Optional[int] = None
    hotels: List[Hotel] = Field(..., description="One entry per time segment, same hotel repeated with different dates/prices")


class Tier(BaseModel):
    id: str
    title: str
    timeSegments: List[str] = Field(..., description="Array of time segment labels (e.g., '2024-12-01 to 2024-12-10')")
    destinations: List[Destination]


class RecommendationResponse(BaseModel):
    tiers: List[Tier]


def calculate_date_ranges(destinations: List[DestinationStay], start_date: date) -> List[tuple[str, date, date]]:
    """Calculate check-in/check-out dates for each destination"""
    ranges = []
    current_date = start_date

    for dest in destinations:
        check_out = current_date + timedelta(days=dest.nights)
        ranges.append((dest.destination_id, current_date, check_out))
        current_date = check_out

    return ranges


def generate_time_segments(start_date: date, variations: int) -> List[str]:
    """Generate time segment labels for different start dates"""
    segments = []

    for i in range(variations):
        if i == 0:
            segment_date = start_date
            segments.append(f"Original Plan ({segment_date.strftime('%B %d')})")
        else:
            # Find optimal dates within next 30 days for better pricing
            segment_date = start_date + timedelta(days=i * 7)  # Weekly intervals
            segments.append(f"Alternative {i} ({segment_date.strftime('%B %d')})")

    return segments


def get_status_for_price(price: float, variation_index: int) -> tuple[str, str, bool, Optional[str]]:
    """Generate status, color, blur state based on price and variation"""
    if variation_index == 0:
        if price < 200:
            return "Available", "text-green-600", False, None
        elif price < 400:
            return "Limited", "text-orange-600", False, None
        else:
            return "Premium", "text-red-600", False, None
    elif variation_index == 1:
        return "Premium View", "text-orange-600", True, "Upgrade to Premium to see exclusive rates"
    else:
        return "Peak Season", "text-red-600", True, "Subscribe to unlock holiday pricing"


def get_status_for_price_simple(price: float, segment_index: int) -> str:
    """Generate simple status based on price and segment index"""
    if segment_index == 0:
        if price < 200:
            return "Available"
        elif price < 400:
            return "Limited"
        else:
            return "Premium"
    elif segment_index == 1:
        return "Limited"
    else:
        return "Peak Season"


async def get_hotels_from_database(
    destination_id: str,
    check_in: date,
    check_out: date,
    adults: int,
    children: int,
    currency: str,
    country_code: str
) -> List[Dict[str, Any]]:
    """Get hotels from internal price history database using structured queries"""
    from app.models.models import Area, Destination

    try:
        # Try to parse destination_id as integer (proper ID)
        try:
            dest_id_int = int(destination_id)
            # Query using trackable_id (hotel_id) and search_criteria destination_id
            price_records = await UniversalPriceHistory.filter(
                trackable_type="hotel_room",
                price_date=check_in,
                search_criteria__destination_id=dest_id_int
            ).order_by("price").limit(8)
        except ValueError:
            # If not an integer, try text matching (fallback for legacy data)
            # Map destination IDs to query patterns
            destination_patterns = {
                "ubud": "ubud",
                "canggu": "canggu",
                "seminyak": "seminyak",
                "kuta": "kuta",
                "sanur": "sanur",
                "goa": "goa",
                "mumbai": "mumbai",
                "delhi": "delhi"
            }

            location_pattern = destination_patterns.get(destination_id.lower(), destination_id.lower())

            # Fallback to text search for backward compatibility
            price_records = await UniversalPriceHistory.filter(
                trackable_type="hotel_room",
                price_date=check_in,
                search_criteria__icontains=location_pattern
            ).order_by("price").limit(8)

        hotels = []
        seen_hotels = set()  # Track unique hotels by name

        for record in price_records:
            search_criteria = record.search_criteria or {}
            hotel_name = search_criteria.get("property_name", f"Hotel in {destination_id.title()}")

            # Skip duplicates
            if hotel_name in seen_hotels:
                continue
            seen_hotels.add(hotel_name)

            hotels.append({
                "name": hotel_name,
                "image": search_criteria.get("main_image") or "https://images.unsplash.com/photo-1571896349842-33c89424de2d?q=80&w=200&h=100&fit=crop",
                "price": float(record.price),
                "rating": search_criteria.get("overall_rating", 4.5),
                "reviews": search_criteria.get("reviews", 1234),
                "currency": record.currency,
                "prices": search_criteria.get("prices", [])  # Include prices array from SERP
            })

        # If we don't have enough data, fill with mock data
        while len(hotels) < 3:
            hotels.append({
                "name": f"Premium Hotel {destination_id.title()} {len(hotels) + 1}",
                "image": "https://images.unsplash.com/photo-1571896349842-33c89424de2d?q=80&w=200&h=100&fit=crop",
                "price": random.randint(150, 500),
                "rating": 4.5,
                "reviews": 1234,
                "currency": currency,
                "prices": []  # No meta prices for mock data
            })

        return hotels[:6]  # Return top 6

    except Exception as e:
        # Return mock data if database query fails
        return [
            {
                "name": f"Premium Hotel {destination_id.title()}",
                "image": "https://images.unsplash.com/photo-1571896349842-33c89424de2d?q=80&w=200&h=100&fit=crop",
                "price": random.randint(150, 500),
                "rating": 4.5,
                "reviews": 1234,
                "currency": currency,
                "prices": []
            }
        ]


@router.post("/multi-destination", response_model=ResponseBase[RecommendationResponse])
async def get_multi_destination_recommendations(
    request: RecommendationRequest
):
    """Get hotel recommendations for multi-destination trip with price variations

    New Structure:
    - Returns tiers (e.g., December 2024 tier)
    - Each tier has timeSegments labels array
    - Each destination has hotels array with one entry per time segment
    - Same hotel repeated across time segments with different prices/dates
    """

    try:
        # Calculate total trip duration
        total_nights = sum(dest.nights for dest in request.destinations)
        trip_month = request.start_date.strftime("%B %Y")

        # Generate time segments (date ranges for each variation)
        time_segment_data = []
        for variation_idx in range(request.variations):
            variation_start_date = request.start_date + timedelta(days=variation_idx * 7)
            date_ranges = calculate_date_ranges(request.destinations, variation_start_date)

            # Create label for this time segment
            first_check_in = date_ranges[0][1]
            last_check_out = date_ranges[-1][2]
            label = f"{first_check_in.strftime('%Y-%m-%d')} to {last_check_out.strftime('%Y-%m-%d')}"

            time_segment_data.append({
                "label": label,
                "date_ranges": date_ranges,
                "start_date": first_check_in
            })

        # Build destinations structure
        # Key: destination_id, Value: list of hotels (one per time segment)
        destinations_map: Dict[str, Dict[str, Any]] = {}

        # For each destination in the request
        for dest_config in request.destinations:
            dest_id = dest_config.destination_id

            if dest_id not in destinations_map:
                destinations_map[dest_id] = {
                    "name": dest_id.title(),
                    "destinationId": dest_id,
                    "areaId": None,
                    "hotels_by_time_segment": []  # Will have entries for each time segment
                }

        # Process each time segment
        for segment_idx, segment_info in enumerate(time_segment_data):
            date_ranges = segment_info["date_ranges"]

            # For each destination's date range in this time segment
            for dest_config, (dest_id, check_in, check_out) in zip(request.destinations, date_ranges):
                # Get best hotel for this destination in this time segment
                hotels_data = await get_hotels_from_database(
                    dest_id, check_in, check_out,
                    request.adults, request.children,
                    request.currency, request.country_code
                )

                if hotels_data:
                    # Take the best hotel (lowest price)
                    hotel_data = hotels_data[0]
                    price = hotel_data["price"]
                    nights = (check_out - check_in).days

                    # Get status for this price
                    status = get_status_for_price_simple(price, segment_idx)

                    # Extract meta_prices from the hotel data
                    meta_prices = []
                    if "prices" in hotel_data and hotel_data["prices"]:
                        for price_source in hotel_data["prices"]:
                            meta_prices.append(MetaPrice(
                                source=price_source.get("source", "Unknown"),
                                price=price_source.get("rate_per_night", {}).get("extracted_lowest", price)
                            ))

                    hotel = Hotel(
                        name=hotel_data["name"],
                        hotelId=hotel_data.get("hotel_id"),
                        image=hotel_data["image"],
                        price=price,
                        currency=request.currency,
                        status=status,
                        nights=nights,
                        checkIn=check_in.isoformat(),
                        checkOut=check_out.isoformat(),
                        meta_prices=meta_prices
                    )

                    destinations_map[dest_id]["hotels_by_time_segment"].append(hotel)

        # Build final destinations list
        destinations = []
        for dest_id, dest_data in destinations_map.items():
            destinations.append(Destination(
                name=dest_data["name"],
                destinationId=dest_data["destinationId"],
                areaId=dest_data["areaId"],
                hotels=dest_data["hotels_by_time_segment"]
            ))

        # Create tier
        tier = Tier(
            id=f"{trip_month.lower().replace(' ', '-')}",
            title=f"{trip_month} ({total_nights} nights)",
            timeSegments=[seg["label"] for seg in time_segment_data],
            destinations=destinations
        )

        response_data = RecommendationResponse(tiers=[tier])

        return ResponseBase(
            success=True,
            message="Multi-destination recommendations generated successfully",
            data=response_data
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate recommendations: {str(e)}")


@router.get("/destinations", response_model=ResponseBase[List[Dict[str, str]]])
async def get_available_destinations():
    """Get list of available destinations"""
    destinations = [
        {"id": "ubud", "name": "Ubud, Bali", "country": "Indonesia"},
        {"id": "canggu", "name": "Canggu, Bali", "country": "Indonesia"},
        {"id": "seminyak", "name": "Seminyak, Bali", "country": "Indonesia"},
        {"id": "kuta", "name": "Kuta, Bali", "country": "Indonesia"},
        {"id": "sanur", "name": "Sanur, Bali", "country": "Indonesia"},
        {"id": "goa", "name": "Goa", "country": "India"},
        {"id": "mumbai", "name": "Mumbai", "country": "India"},
        {"id": "delhi", "name": "Delhi", "country": "India"}
    ]

    return ResponseBase(
        success=True,
        message="Available destinations retrieved",
        data=destinations
    )