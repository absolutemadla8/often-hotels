#!/usr/bin/env python3
"""
Debug script to test hotel pricing service directly
"""
import asyncio
import sys
import os
from datetime import date

# Add the app directory to Python path
sys.path.insert(0, '/Users/sarveshdakhore/Desktop/Often/often-hotels')

async def test_hotel_pricing():
    # Import after adding to path
    from app.services.hotel_pricing_service import HotelPricingService
    from app.schemas.itinerary import GuestConfig
    from app.core.database import init_db
    
    print("🔧 Initializing database connection...")
    await init_db()
    
    print("🔧 Creating hotel pricing service...")
    service = HotelPricingService()
    
    print("🔧 Testing hotel pricing for destination_id=3 (Mumbai)...")
    
    guest_config = GuestConfig(adults=2, children=0)
    date_range = (date(2025, 10, 1), date(2025, 10, 3))
    
    print(f"🔧 Date range: {date_range}")
    print(f"🔧 Guest config: {guest_config}")
    
    try:
        hotel_data = await service.get_hotel_prices_for_destination(
            destination_id=3,
            area_id=None,
            date_range=date_range,
            guest_config=guest_config,
            currency="USD"
        )
        
        print(f"✅ SUCCESS: Found {len(hotel_data)} hotels with pricing")
        for i, hotel in enumerate(hotel_data[:3]):
            print(f"   Hotel {i+1}: {hotel.hotel_name} ({hotel.hotel_id}) - {len(hotel.prices)} price entries")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_hotel_pricing())