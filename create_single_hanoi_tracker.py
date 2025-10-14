"""
Script to create a single tracker for testing - Old Quarter Hanoi
Configuration: Nov-Dec 2025, Daily tracking, 1-night stays, INR currency
"""
import requests
import json

# API base URL
BASE_URL = "http://localhost:8000/api/v1/tracking"

# Single area for testing
AREA_NAME = "Old Quarter"
QUERY = f"{AREA_NAME} hanoi"

# Tracker configuration
tracker_payload = {
    "name": f"Hanoi - {AREA_NAME} - Nov-Dec 2025",
    "description": f"Daily price tracking for hotels in {AREA_NAME}, Hanoi (Nov-Dec 2025)",
    "query": QUERY,
    "start_date": "2025-11-01",
    "end_date": "2025-12-31",
    "interval_days": 1,
    "stay_duration_days": 1,
    "adults": 2,
    "children": 0,
    "currency": "INR",
    "country_code": "vn",
    "language": "en",
    "is_scheduled": True
}

print("=" * 60)
print("🏨 Single Hanoi Tracker Creation Script (TEST)")
print("=" * 60)
print(f"\n📊 Configuration:")
print(f"   Area: {AREA_NAME}")
print(f"   Query: {QUERY}")
print(f"   Period: Nov 1 - Dec 31, 2025")
print(f"   Tracking: Daily (interval_days=1)")
print(f"   Stay Duration: 1 night")
print(f"   Currency: INR")
print(f"   Adults: 2, Children: 0")
print(f"\n📍 Creating tracker for: {AREA_NAME}")

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

        # Ask if user wants to run it
        print(f"\n❓ Do you want to run this tracker now? (y/n): ", end="")
        choice = input().strip().lower()

        if choice == 'y':
            print(f"\n🚀 Running tracker {tracker_id}...")

            run_response = requests.post(
                f"{BASE_URL}/run",
                json={"tracker_ids": [tracker_id]},
                headers={"Content-Type": "application/json"}
            )

            if run_response.status_code == 200:
                print(f"✅ Tracker started successfully!")
                print(f"   Response: {json.dumps(run_response.json(), indent=2)}")
            else:
                print(f"❌ Failed to run tracker: {run_response.status_code}")
                print(f"   Response: {run_response.text}")
        else:
            print(f"\n💡 Tracker created but not started.")
            print(f"   To run it later, use:")
            print(f"   curl -X POST {BASE_URL}/run \\")
            print(f"     -H 'Content-Type: application/json' \\")
            print(f"     -d '{{\"tracker_ids\": [{tracker_id}]}}'")
    else:
        print(f"❌ Failed to create tracker: {response.status_code}")
        print(f"   Response: {response.text}")

except Exception as e:
    print(f"❌ Error: {e}")

print("\n✨ Done!")
