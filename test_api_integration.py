#!/usr/bin/env python3
"""
Simple test script to validate TravClan API integration
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
    print("Testing location search...")
    
    try:
        service = TravClanHotelApiService()
        async with service:
            response = await service.search_locations("Dubai")
            print(f"Location search successful: {len(response.get('results', []))} results found")
            return True
    except Exception as e:
        print(f"Location search failed: {e}")
        return False


async def test_hotel_search():
    """Test hotel search functionality"""
    print("Testing hotel search...")
    
    try:
        service = TravClanHotelApiService()
        
        # Sample search parameters
        search_data = {
            "checkIn": (date.today() + timedelta(days=30)).isoformat(),
            "checkOut": (date.today() + timedelta(days=33)).isoformat(),
            "nationality": "IN",
            "locationId": 12345,  # This would need to be a real location ID
            "occupancies": [
                {
                    "numOfAdults": 2,
                    "childAges": []
                }
            ]
        }
        
        async with service:
            response = await service.search_hotels(search_data)
            print(f"Hotel search successful: Response received")
            return True
    except Exception as e:
        print(f"Hotel search failed: {e}")
        return False


async def test_hotel_static_content():
    """Test hotel static content functionality"""
    print("Testing hotel static content...")
    
    try:
        service = TravClanHotelApiService()
        
        async with service:
            response = await service.get_hotel_static_content("test-hotel-id")
            print("Hotel static content retrieved successfully")
            return True
    except Exception as e:
        print(f"Hotel static content failed: {e}")
        return False


async def main():
    """Run all tests"""
    print("Starting TravClan API Integration Tests")
    print("=" * 50)
    
    # Note: These tests will fail without proper API credentials
    # They are designed to test the structure and error handling
    
    tests = [
        ("Location Search", test_location_search),
        ("Hotel Search", test_hotel_search), 
        ("Hotel Static Content", test_hotel_static_content),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name}...")
        try:
            result = await test_func()
            results.append((test_name, result))
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status}: {test_name}")
        except Exception as e:
            results.append((test_name, False))
            print(f"❌ ERROR in {test_name}: {e}")
    
    print("\n" + "=" * 50)
    print("Test Summary:")
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {test_name}")
    
    total_tests = len(results)
    passed_tests = sum(1 for _, result in results if result)
    print(f"\nTotal: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed. Check configuration and API credentials.")
        return 1


if __name__ == "__main__":
    print("TravClan API Integration Test")
    print("Note: This test requires proper API credentials in .env file")
    print("Without credentials, the tests will show the error handling capabilities\n")
    
    exit_code = asyncio.run(main())
    sys.exit(exit_code)