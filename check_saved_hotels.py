"""
Check hotels and price data saved from BrightData scraping
"""
import asyncio
from tortoise import Tortoise
import os


async def init():
    """Initialize database connection"""
    db_url = os.getenv('DATABASE_URL', 'postgres://postgres:password@localhost:5432/often_hotels')
    if db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgres://', 1)

    await Tortoise.init(
        db_url=db_url,
        modules={'models': ['app.models.models']}
    )


async def check_saved_data():
    """Check saved hotels and prices"""
    from app.models.models import Hotel, UniversalPriceHistory, Area

    print("=" * 80)
    print("🏨 BrightData Scraping Results - Saved Data")
    print("=" * 80)

    # Get Old Quarter area
    old_quarter = await Area.filter(name__icontains="old quarter").first()
    if old_quarter:
        await old_quarter.fetch_related('destination', 'destination__country')
        print(f"\n📍 Area: {old_quarter.name}")
        print(f"   Destination: {old_quarter.destination.name}")
        print(f"   Country: {old_quarter.destination.country.name}")
        print(f"   Area ID: {old_quarter.id}")

        # Get hotels in Old Quarter
        hotels = await Hotel.filter(area=old_quarter).all()
        print(f"\n🏨 Hotels in Old Quarter: {len(hotels)}")
        print("-" * 80)

        for hotel in hotels:
            print(f"\n   Hotel: {hotel.name}")
            print(f"   ID: {hotel.id}")
            print(f"   External ID: {hotel.external_id}")
            print(f"   Star Rating: {hotel.star_rating}")
            print(f"   Partner: {hotel.partner_name}")
            print(f"   Address: {hotel.address}")
            print(f"   Coordinates: ({hotel.latitude}, {hotel.longitude})")

            # Get price history for this hotel
            prices = await UniversalPriceHistory.filter(
                trackable_id=hotel.id,
                data_source="brightdata"
            ).order_by('-created_at').limit(5)

            if prices:
                print(f"   Recent Prices:")
                for price in prices:
                    print(f"      • {price.price} {price.currency} on {price.price_date} (Available: {price.is_available})")
            else:
                print(f"   No price history found")

    # Get all BrightData price records
    print("\n" + "=" * 80)
    print("💰 All BrightData Price Records")
    print("=" * 80)

    all_prices = await UniversalPriceHistory.filter(
        data_source="brightdata"
    ).order_by('-created_at').all()

    print(f"\nTotal BrightData Records: {len(all_prices)}\n")

    for i, price in enumerate(all_prices, 1):
        search_criteria = price.search_criteria or {}
        hotel_name = search_criteria.get('property_name', 'Unknown')
        query = search_criteria.get('query', 'Unknown')

        print(f"{i}. {hotel_name}")
        print(f"   Query: {query}")
        print(f"   Price: {price.price} {price.currency}")
        print(f"   Date: {price.price_date}")
        print(f"   Hotel ID: {price.trackable_id}")
        print(f"   Area ID: {search_criteria.get('area_id')}")
        print(f"   Destination ID: {search_criteria.get('destination_id')}")
        print(f"   Available: {price.is_available}")
        print()

    print("=" * 80)
    print("✅ Summary")
    print("=" * 80)
    print(f"   Hotels created: {len(hotels) if old_quarter else 0}")
    print(f"   Price records saved: {len(all_prices)}")
    print(f"   Data source: BrightData (mock)")
    print()


async def main():
    try:
        await init()
        await check_saved_data()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(main())
