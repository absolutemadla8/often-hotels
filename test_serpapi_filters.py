#!/usr/bin/env python3
"""
Test script to debug SerpAPI hotel_class filtering
"""
import asyncio
import json
from datetime import date

from app.services.serp_service import SearchCriteria, HotelClass, Rating, get_serp_service

async def test_serpapi_filtering():
    """Test SerpAPI hotel_class filtering directly"""
    
    # Create search criteria with 4-5 star filter
    criteria = SearchCriteria(
        query="Ubud, Bali, Indonesia",
        check_in_date=date(2025, 10, 20),
        check_out_date=date(2025, 10, 21),
        adults=1,
        children=0,
        currency="INR",
        gl="us",
        hl="en",
        hotel_class=[HotelClass.FOUR_STAR, HotelClass.FIVE_STAR],
        rating=Rating.FOUR_PLUS,
        vacation_rentals=False
    )
    
    # Get SerpAPI service
    serp_service = get_serp_service()
    
    try:
        print("🔍 Testing SerpAPI hotel_class filtering...")
        print(f"Query: {criteria.query}")
        print(f"Hotel class filter: {[hc.value for hc in criteria.hotel_class]}")
        print(f"Rating filter: {criteria.rating.value}")
        print()
        
        # Make the search request
        async with serp_service:
            response = await serp_service.search_hotels(criteria)
        
        print(f"📊 Results Summary:")
        print(f"Total properties: {len(response.properties)}")
        print(f"Total ads: {len(response.ads)}")
        print()
        
        # Analyze the star ratings in the response
        star_ratings = {}
        hotels_without_rating = []
        
        for prop in response.properties:
            if prop.extracted_hotel_class is not None:
                rating = prop.extracted_hotel_class
                star_ratings[rating] = star_ratings.get(rating, 0) + 1
            else:
                hotels_without_rating.append({
                    "name": prop.name,
                    "hotel_class": prop.hotel_class,
                    "type": prop.type
                })
        
        print("⭐ Star rating distribution:")
        for rating in sorted(star_ratings.keys()):
            print(f"  {rating}-star: {star_ratings[rating]} hotels")
        
        print(f"\n❓ Hotels without extracted_hotel_class: {len(hotels_without_rating)}")
        
        if hotels_without_rating:
            print("\nExamples of hotels without star rating:")
            for hotel in hotels_without_rating[:5]:
                print(f"  - {hotel['name']} (type: {hotel['type']}, hotel_class: {hotel['hotel_class']})")
        
        # Check if we got any 1-3 star hotels (which shouldn't happen)
        low_star_count = sum(count for rating, count in star_ratings.items() if rating in [1, 2, 3])
        if low_star_count > 0:
            print(f"\n🚨 ERROR: Got {low_star_count} hotels with 1-3 star ratings!")
            print("This indicates the SerpAPI filter is not working correctly.")
        else:
            print(f"\n✅ SUCCESS: No 1-3 star hotels found. Filter appears to be working.")
            
        return response
        
    except Exception as e:
        print(f"❌ Error testing SerpAPI: {e}")
        return None

if __name__ == "__main__":
    asyncio.run(test_serpapi_filtering())