#!/usr/bin/env python3
"""
Test script to check what get_search_criteria_defaults() returns
"""
from app.core.hotel_tracking_config import get_search_criteria_defaults, tracking_config
from app.services.serp_service import SearchCriteria
from datetime import date

def test_search_defaults():
    """Test what search defaults are being used"""
    
    print("🔍 Testing get_search_criteria_defaults()")
    print()
    
    # Get the defaults
    defaults = get_search_criteria_defaults()
    
    print("📋 Search defaults returned:")
    for key, value in defaults.items():
        print(f"  {key}: {value} ({type(value).__name__})")
    
    print()
    print("🔧 Tracking config values:")
    print(f"  HOTEL_CLASS_FILTER: {tracking_config.HOTEL_CLASS_FILTER}")
    print(f"  RATING_FILTER: {tracking_config.RATING_FILTER}")
    
    print()
    print("🏗️ Building SearchCriteria with defaults:")
    
    try:
        criteria = SearchCriteria(
            query="Ubud, Bali, Indonesia",
            check_in_date=date(2025, 10, 20),
            check_out_date=date(2025, 10, 21),
            **defaults
        )
        
        print("✅ SearchCriteria created successfully")
        print(f"  hotel_class: {criteria.hotel_class}")
        print(f"  rating: {criteria.rating}")
        print(f"  adults: {criteria.adults}")
        print(f"  currency: {criteria.currency}")
        
    except Exception as e:
        print(f"❌ Error creating SearchCriteria: {e}")

if __name__ == "__main__":
    test_search_defaults()