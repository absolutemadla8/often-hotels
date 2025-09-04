#!/usr/bin/env python3
"""
Test TravClan API integration with real credentials
"""

import asyncio
import sys
import os
from datetime import date, timedelta

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from services.travclan_api_service import TravClanHotelApiService


async def test_location_search():
    """Test location search functionality"""
    print("🧪 Testing TravClan location search...")
    
    try:
        service = TravClanHotelApiService()
        async with service:
            response = await service.search_locations("Dubai")
            
            if response and 'results' in response:
                results = response['results']
                print(f"✅ Location search successful: {len(results)} results found")
                
                # Show first few results
                if results:
                    print("📍 Sample results:")
                    for i, location in enumerate(results[:3]):
                        print(f"   {i+1}. {location.get('name', 'N/A')} - {location.get('type', 'N/A')}")
                
                return True, results
            else:
                print("❌ Location search returned empty results")
                return False, []
                
    except Exception as e:
        print(f"❌ Location search failed: {e}")
        return False, []


async def test_hotel_search_with_location():
    """Test hotel search functionality with a real location"""
    print("🧪 Testing TravClan hotel search...")
    
    # First get a location ID
    print("  Getting location ID for Dubai...")
    location_success, locations = await test_location_search()
    
    if not location_success or not locations:
        print("  ❌ Cannot test hotel search without valid location")
        return False
    
    # Find a suitable location
    location_id = None
    for location in locations:
        if location.get('type') in ['CITY', 'DESTINATION', 'City', 'State'] and location.get('id'):
            location_id = location.get('id')
            location_name = location.get('name', 'Unknown')
            location_type = location.get('type', 'Unknown')
            print(f"  📍 Using location: {location_name} ({location_type}, ID: {location_id})")
            break
    
    if not location_id:
        print("  ❌ No suitable location found for hotel search")
        return False
    
    try:
        service = TravClanHotelApiService()
        
        # Sample search parameters
        search_data = {
            "checkIn": (date.today() + timedelta(days=30)).isoformat(),
            "checkOut": (date.today() + timedelta(days=33)).isoformat(),
            "nationality": "IN",
            "locationId": location_id,
            "occupancies": [
                {
                    "numOfAdults": 2,
                    "childAges": []
                }
            ]
        }
        
        print(f"  🔍 Searching hotels from {search_data['checkIn']} to {search_data['checkOut']}")
        
        async with service:
            response = await service.search_hotels(search_data)
            
            if response and 'results' in response:
                results = response['results']
                if results and len(results) > 0:
                    hotels_data = results[0].get('data', [])
                    print(f"✅ Hotel search successful: {len(hotels_data)} hotels found")
                    
                    # Show sample hotels
                    available_hotels = [h for h in hotels_data if h.get('isAvailable')]
                    print(f"🏨 Available hotels: {len(available_hotels)}")
                    
                    if available_hotels:
                        print("🏨 Sample hotels:")
                        for i, hotel in enumerate(available_hotels[:3]):
                            name = hotel.get('name', 'N/A')
                            star_rating = hotel.get('starRating', 'N/A')
                            rate = hotel.get('availability', {}).get('rate', {}).get('finalRate', 'N/A')
                            currency = hotel.get('availability', {}).get('rate', {}).get('currency', 'N/A')
                            print(f"   {i+1}. {name} ({star_rating}⭐) - {rate} {currency}")
                    
                    return True
                else:
                    print("✅ Hotel search successful but no hotels returned")
                    return True
            else:
                print("❌ Hotel search returned invalid response")
                return False
                
    except Exception as e:
        print(f"❌ Hotel search failed: {e}")
        return False


async def test_hotel_static_content():
    """Test hotel static content with a sample hotel ID"""
    print("🧪 Testing TravClan hotel static content...")
    
    # Use a sample hotel ID - this might need to be adjusted based on actual hotel IDs
    test_hotel_ids = ["H123", "test-hotel", "sample-hotel-id"]
    
    for hotel_id in test_hotel_ids:
        try:
            service = TravClanHotelApiService()
            
            async with service:
                response = await service.get_hotel_static_content(hotel_id)
                print(f"✅ Hotel static content retrieved successfully for {hotel_id}")
                print(f"   Response keys: {list(response.keys()) if response else 'None'}")
                return True
                
        except Exception as e:
            print(f"   ⚠️ Hotel static content failed for {hotel_id}: {e}")
            continue
    
    print("❌ Hotel static content failed for all test hotel IDs")
    return False


async def test_api_authentication():
    """Test if API authentication is working"""
    print("🧪 Testing TravClan API authentication...")
    
    try:
        service = TravClanHotelApiService()
        async with service:
            token = await service.get_access_token()
            if token:
                print(f"✅ API authentication successful")
                print(f"   Token: {token[:20]}...")
                return True
            else:
                print("❌ No access token received")
                return False
    except Exception as e:
        print(f"❌ API authentication failed: {e}")
        return False


async def main():
    """Run all TravClan API integration tests"""
    print("🚀 Starting TravClan API Integration Tests")
    print("=" * 60)
    
    async def location_search_wrapper():
        result, _ = await test_location_search()
        return result
    
    tests = [
        ("API Authentication", test_api_authentication),
        ("Location Search", location_search_wrapper),
        ("Hotel Search", test_hotel_search_with_location),
        ("Hotel Static Content", test_hotel_static_content),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*10} {test_name} {'='*10}")
        try:
            result = await test_func()
            results.append((test_name, result))
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"\n{status}: {test_name}")
        except Exception as e:
            results.append((test_name, False))
            print(f"❌ ERROR in {test_name}: {e}")
    
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    total_tests = len(results)
    passed_tests = sum(1 for _, result in results if result)
    print(f"\n📈 Results: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed! TravClan API integration is working correctly.")
        return 0
    elif passed_tests > 0:
        print("⚠️  Some tests passed. Check failed tests for issues.")
        return 1
    else:
        print("❌ All tests failed. Check API credentials and configuration.")
        return 1


if __name__ == "__main__":
    print("TravClan API Integration Test")
    print("Testing with real TravClan API credentials\n")
    
    exit_code = asyncio.run(main())
    sys.exit(exit_code)