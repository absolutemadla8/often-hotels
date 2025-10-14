"""
Create a test tracker for Hanoi Old Quarter using the API
"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1/tracking"

# Tracker configuration
tracker_payload = {
    "name": "TEST - Hanoi Old Quarter - Nov 2025",
    "description": "Test tracker for Hanoi Old Quarter using BrightData (3 days only)",
    "query": "Old Quarter hanoi",
    "start_date": "2025-11-01",
    "end_date": "2025-11-03",  # Only 3 days for testing
    "interval_days": 1,
    "stay_duration_days": 1,
    "adults": 2,
    "children": 0,
    "currency": "INR",
    "country_code": "vn",
    "language": "en",
    "is_scheduled": False
}

print("=" * 60)
print("🏨 Creating Test Tracker for Hanoi Old Quarter")
print("=" * 60)
print(f"\n📋 Configuration:")
print(f"   Query: {tracker_payload['query']}")
print(f"   Dates: {tracker_payload['start_date']} to {tracker_payload['end_date']}")
print(f"   Duration: 3 days (testing)")
print(f"   Currency: {tracker_payload['currency']}")
print(f"   Adults: {tracker_payload['adults']}, Children: {tracker_payload['children']}")

print(f"\n📍 Creating tracker...")

try:
    response = requests.post(
        f"{BASE_URL}/trackers",
        json=tracker_payload,
        headers={"Content-Type": "application/json"}
    )

    if response.status_code == 200:
        data = response.json()
        tracker_id = data['data']['id']
        print(f"✅ Tracker created successfully! ID: {tracker_id}")

        print("\n" + "=" * 60)
        print("📡 Next Steps - Test the BrightData System")
        print("=" * 60)

        print(f"\n1️⃣  Run tracker synchronously (testing - no Celery needed):")
        print(f"   curl -X POST http://localhost:8000/api/v1/jobs/run-sync/{tracker_id}")

        print(f"\n2️⃣  OR submit to Celery queue (requires worker running):")
        print(f"   curl -X POST http://localhost:8000/api/v1/jobs/submit \\")
        print(f"     -H 'Content-Type: application/json' \\")
        print(f"     -d '{{\"tracker_id\": {tracker_id}, \"priority\": 8}}'")

        print(f"\n3️⃣  Check tracker status:")
        print(f"   curl http://localhost:8000/api/v1/tracking/trackers/{tracker_id}")

        print(f"\n4️⃣  View results:")
        print(f"   curl http://localhost:8000/api/v1/tracking/trackers/{tracker_id}/results")

        print(f"\n5️⃣  System metrics:")
        print(f"   curl http://localhost:8000/api/v1/monitoring/metrics/system")

        print("\n" + "=" * 60)
        print("⚠️  Important:")
        print("=" * 60)
        print("   • Set BRIGHTDATA_API_KEY in .env file")
        print("   • For Celery jobs: celery -A app.workers.celery_app worker --loglevel=info")
        print("   • Ensure Redis is running: redis-server")
        print("   • Expected cost: ~$0.50-1.00 for 3 days")
        print("\n✨ Ready to test!\n")

    else:
        print(f"❌ Failed to create tracker: {response.status_code}")
        print(f"   Response: {response.text}")

except requests.exceptions.ConnectionError:
    print("❌ Error: Cannot connect to API server")
    print("   Make sure the server is running:")
    print("   uvicorn app.main:app --reload --port 8000")
except Exception as e:
    print(f"❌ Error: {e}")
