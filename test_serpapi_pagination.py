#!/usr/bin/env python3
"""
Test script to debug SerpAPI hotel_class filtering with pagination
"""
import asyncio
import json
from datetime import date

from app.core.hotel_tracking_config import get_search_criteria_defaults
from app.services.serp_service import SearchCriteria, get_serp_service

async def test_serpapi_pagination():
    """Test SerpAPI hotel_class filtering with pagination"""
    
    # Build search criteria exactly like the hotel tracking service
    search_defaults = get_search_criteria_defaults()
    criteria = SearchCriteria(
        query="Ubud, Bali, Indonesia",
        check_in_date=date(2025, 10, 20),
        check_out_date=date(2025, 10, 21),
        **search_defaults
    )
    
    # Get SerpAPI service
    serp_service = get_serp_service()
    
    try:
        print("🔍 Testing SerpAPI hotel_class filtering with pagination...")
        print(f"Query: {criteria.query}")
        print(f"Hotel class filter: {[hc.value for hc in criteria.hotel_class]}")
        print(f"Rating filter: {criteria.rating.value}")
        print()
        
        # Make the search request with pagination (like the tracking service)
        async with serp_service:
            responses = await serp_service.search_with_pagination(criteria, max_pages=5)
        
        print(f"📊 Pagination Results:")
        print(f"Total pages fetched: {len(responses)}")
        
        # Analyze each page
        all_star_ratings = {}
        all_hotels_without_rating = []
        
        for page_num, response in enumerate(responses, 1):
            print(f"\nPage {page_num}:")
            print(f"  Properties: {len(response.properties)}")
            print(f"  Ads: {len(response.ads)}")
            
            page_star_ratings = {}
            page_hotels_without_rating = []
            
            # Analyze properties on this page
            for prop in response.properties:
                if prop.extracted_hotel_class is not None:
                    rating = prop.extracted_hotel_class
                    page_star_ratings[rating] = page_star_ratings.get(rating, 0) + 1
                    all_star_ratings[rating] = all_star_ratings.get(rating, 0) + 1
                else:
                    hotel_info = {
                        "name": prop.name,
                        "hotel_class": prop.hotel_class,
                        "type": prop.type,
                        "page": page_num
                    }
                    page_hotels_without_rating.append(hotel_info)
                    all_hotels_without_rating.append(hotel_info)
            
            # Show page-specific star distribution
            if page_star_ratings:
                print(f"  Star ratings: {dict(sorted(page_star_ratings.items()))}")
            
            if page_hotels_without_rating:
                print(f"  Hotels without rating: {len(page_hotels_without_rating)}")
                # Show first few examples
                for hotel in page_hotels_without_rating[:3]:
                    print(f"    - {hotel['name']} (type: {hotel['type']})")
        
        print(f"\n⭐ Overall star rating distribution:")
        for rating in sorted(all_star_ratings.keys()):
            print(f"  {rating}-star: {all_star_ratings[rating]} hotels")
        
        print(f"\n❓ Total hotels without extracted_hotel_class: {len(all_hotels_without_rating)}")
        
        # Check if we got any 1-3 star hotels (which shouldn't happen)
        low_star_count = sum(count for rating, count in all_star_ratings.items() if rating in [1, 2, 3])
        if low_star_count > 0:
            print(f"\n🚨 ERROR: Got {low_star_count} hotels with 1-3 star ratings across all pages!")
            print("This indicates the SerpAPI filter is not working correctly on some pages.")
            
            # Show which pages had the problem
            for page_num, response in enumerate(responses, 1):
                page_low_star = sum(1 for prop in response.properties 
                                   if prop.extracted_hotel_class in [1, 2, 3])
                if page_low_star > 0:
                    print(f"  Page {page_num}: {page_low_star} low-star hotels")
        else:
            print(f"\n✅ SUCCESS: No 1-3 star hotels found across all pages. Filter is working correctly.")
            
        if all_hotels_without_rating:
            print(f"\n⚠️  Hotels without rating may need special handling:")
            for hotel in all_hotels_without_rating[:5]:
                print(f"  Page {hotel['page']}: {hotel['name']} (type: {hotel['type']}, class: {hotel['hotel_class']})")
        
        return responses
        
    except Exception as e:
        print(f"❌ Error testing SerpAPI pagination: {e}")
        return None

if __name__ == "__main__":
    asyncio.run(test_serpapi_pagination())