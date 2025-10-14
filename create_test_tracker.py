"""
Create a test tracker for Hanoi Old Quarter using BrightData system
"""
import asyncio
from datetime import date, timedelta
from tortoise import Tortoise
import os


async def init():
    """Initialize database connection"""
    # Get database URL from environment
    db_url = os.getenv('DATABASE_URL', 'postgres://postgres:password@localhost:5432/often_hotels')

    # Handle URL format
    if db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgres://', 1)

    await Tortoise.init(
        db_url=db_url,
        modules={'models': ['app.models.models']}
    )


async def create_hanoi_test_tracker():
    """Create a test tracker for Hanoi Old Quarter"""
    from app.models.models import Tracker

    print("=" * 60)
    print("🏨 Creating Test Tracker for Hanoi Old Quarter")
    print("=" * 60)

    # Define tracker configuration
    tracker_config = {
        "name": "TEST - Hanoi Old Quarter - Nov 2025",
        "description": "Test tracker for Hanoi Old Quarter using BrightData (3 days only)",
        "status": "active",
        "is_scheduled": False,
        "search_criteria": {
            "query": "Old Quarter hanoi",
            "start_date": "2025-11-01",
            "end_date": "2025-11-03",  # Only 3 days for testing
            "interval_days": 1,
            "stay_duration_days": 1,
            "adults": 2,
            "children": 0,
            "currency": "INR",
            "country_code": "vn",
            "language": "en"
        }
    }

    print(f"\n📋 Configuration:")
    print(f"   Name: {tracker_config['name']}")
    print(f"   Query: {tracker_config['search_criteria']['query']}")
    print(f"   Dates: {tracker_config['search_criteria']['start_date']} to {tracker_config['search_criteria']['end_date']}")
    print(f"   Duration: 3 days (testing)")
    print(f"   Currency: {tracker_config['search_criteria']['currency']}")

    # Check if tracker already exists
    existing = await Tracker.filter(name=tracker_config["name"]).first()

    if existing:
        print(f"\n⚠️  Tracker already exists (ID: {existing.id})")
        print(f"   Status: {existing.status}")
        print(f"   Total runs: {existing.total_runs}")
        return existing.id

    # Create new tracker
    tracker = await Tracker.create(**tracker_config)

    print(f"\n✅ Tracker created successfully!")
    print(f"   ID: {tracker.id}")
    print(f"   Status: {tracker.status}")

    return tracker.id


async def show_usage(tracker_id: int):
    """Show usage instructions"""
    print("\n" + "=" * 60)
    print("📡 Next Steps - Test the System")
    print("=" * 60)

    print(f"\n1️⃣  Submit scraping job (async with Celery):")
    print(f"   curl -X POST http://localhost:8000/api/v1/jobs/submit \\")
    print(f"     -H 'Content-Type: application/json' \\")
    print(f"     -d '{{\"tracker_id\": {tracker_id}, \"priority\": 8}}'")

    print(f"\n2️⃣  OR run synchronously (for testing - no Celery needed):")
    print(f"   curl -X POST http://localhost:8000/api/v1/jobs/run-sync/{tracker_id}")

    print(f"\n3️⃣  Check tracker status:")
    print(f"   curl http://localhost:8000/api/v1/tracking/trackers/{tracker_id}")

    print(f"\n4️⃣  View system metrics:")
    print(f"   curl http://localhost:8000/api/v1/monitoring/metrics/system")

    print(f"\n5️⃣  Get tracker statistics:")
    print(f"   curl http://localhost:8000/api/v1/jobs/trackers/stats")

    print("\n" + "=" * 60)
    print("⚠️  Important Notes:")
    print("=" * 60)
    print("   • Make sure you have BRIGHTDATA_API_KEY set in .env")
    print("   • For async jobs, start Celery worker:")
    print("     celery -A app.workers.celery_app worker --loglevel=info")
    print("   • Start Redis if not running:")
    print("     redis-server")
    print("   • This is a 3-day test (Nov 1-3, 2025)")
    print("   • Expected cost: ~$0.50-1.00 with BrightData")
    print("\n✨ Ready to scrape!\n")


async def main():
    """Main execution"""
    try:
        print("\n🚀 Initializing database connection...")
        await init()

        print("✅ Database connected\n")

        tracker_id = await create_hanoi_test_tracker()
        await show_usage(tracker_id)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(main())
