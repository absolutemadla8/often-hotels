#!/usr/bin/env python3
"""
Test script to verify star rating extraction logic
"""
from app.services.hotel_tracking_service import HotelTrackingService
from app.services.serp_service import PropertyResult, GPSCoordinates

def test_star_rating_extraction():
    """Test the _extract_hotel_star_rating method"""
    
    # Create a tracking service instance
    tracking_service = HotelTrackingService()
    
    print("🧪 Testing star rating extraction logic")
    print()
    
    # Test cases
    test_cases = [
        {
            "name": "Hotel with extracted_hotel_class",
            "extracted_hotel_class": 5,
            "hotel_class": "5-star hotel",
            "expected": 5
        },
        {
            "name": "Hotel with only hotel_class string",
            "extracted_hotel_class": None,
            "hotel_class": "4-star hotel",
            "expected": 4
        },
        {
            "name": "Hotel with '5 star' format",
            "extracted_hotel_class": None,
            "hotel_class": "5 star luxury resort",
            "expected": 5
        },
        {
            "name": "Hotel with missing data (should default to 4)",
            "extracted_hotel_class": None,
            "hotel_class": None,
            "expected": 4
        },
        {
            "name": "Hotel with non-matching string",
            "extracted_hotel_class": None,
            "hotel_class": "luxury resort",
            "expected": 4
        }
    ]
    
    for test_case in test_cases:
        print(f"Test: {test_case['name']}")
        
        # Create a mock PropertyResult
        prop = PropertyResult(
            type="hotel",
            name=f"Test {test_case['name']}",
            extracted_hotel_class=test_case["extracted_hotel_class"],
            hotel_class=test_case["hotel_class"]
        )
        
        # Test the extraction
        result = tracking_service._extract_hotel_star_rating(prop)
        
        print(f"  Input: extracted_hotel_class={test_case['extracted_hotel_class']}, hotel_class='{test_case['hotel_class']}'")
        print(f"  Result: {result}")
        print(f"  Expected: {test_case['expected']}")
        
        if result == test_case["expected"]:
            print("  ✅ PASS")
        else:
            print("  ❌ FAIL")
        print()

if __name__ == "__main__":
    test_star_rating_extraction()