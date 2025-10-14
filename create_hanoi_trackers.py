"""
Script to create trackers for all Hanoi areas using the API
Configuration: Nov-Dec 2025, Daily tracking, 1-night stays, INR currency
"""
import requests
import json
from datetime import date

# API base URL
BASE_URL = "http://localhost:8000/api/v1/tracking"

# Hanoi areas from seed data
HANOI_AREAS = [
    "Old Quarter",
    "Hoan Kiem",
    "Ba Dinh",
    "Tay Ho",
    "Hai Ba Trung"
]

# Tracker configuration
TRACKER_CONFIG = {
    "start_date": "2025-11-01",
    "end_date": "2025-12-31",
    "interval_days": 1,  # Daily tracking
    "stay_duration_days": 1,  # Single night stays
    "adults": 2,
    "children": 0,
    "currency": "INR",
    "country_code": "vn",
    "language": "en",
    "is_scheduled": True
}


def create_tracker(area_name: str):
    """Create a tracker for a specific Hanoi area"""

    payload = {
        "name": f"Hanoi - {area_name} - Nov-Dec 2025",
        "description": f"Daily price tracking for hotels in {area_name}, Hanoi (Nov-Dec 2025)",
        "query": f"{area_name} hanoi",
        **TRACKER_CONFIG
    }

    print(f"\n📍 Creating tracker for: {area_name}")
    print(f"   Query: {payload['query']}")

    try:
        response = requests.post(
            f"{BASE_URL}/trackers",
            json=payload,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            data = response.json()
            tracker_id = data['data']['id']
            print(f"   ✅ Tracker created successfully! ID: {tracker_id}")
            return tracker_id
        else:
            print(f"   ❌ Failed to create tracker: {response.status_code}")
            print(f"   Response: {response.text}")
            return None

    except Exception as e:
        print(f"   ❌ Error creating tracker: {e}")
        return None


def run_trackers(tracker_ids: list):
    """Run all created trackers"""

    if not tracker_ids:
        print("\n⚠️  No trackers to run!")
        return

    print(f"\n🚀 Running {len(tracker_ids)} trackers...")

    payload = {
        "tracker_ids": tracker_ids
    }

    try:
        response = requests.post(
            f"{BASE_URL}/run",
            json=payload,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Trackers started successfully!")
            print(f"   Response: {json.dumps(data, indent=2)}")
        else:
            print(f"❌ Failed to run trackers: {response.status_code}")
            print(f"   Response: {response.text}")

    except Exception as e:
        print(f"❌ Error running trackers: {e}")


def main():
    """Main execution"""
    print("=" * 60)
    print("🏨 Hanoi Hotel Tracker Creation Script")
    print("=" * 60)
    print(f"\n📊 Configuration:")
    print(f"   Period: Nov 1 - Dec 31, 2025")
    print(f"   Tracking: Daily (interval_days=1)")
    print(f"   Stay Duration: 1 night")
    print(f"   Currency: INR")
    print(f"   Adults: 2, Children: 0")
    print(f"\n📍 Creating trackers for {len(HANOI_AREAS)} Hanoi areas...")

    tracker_ids = []

    for area in HANOI_AREAS:
        tracker_id = create_tracker(area)
        if tracker_id:
            tracker_ids.append(tracker_id)

    print("\n" + "=" * 60)
    print(f"✅ Created {len(tracker_ids)} trackers successfully!")
    print(f"   Tracker IDs: {tracker_ids}")
    print("=" * 60)

    # Ask if user wants to run the trackers
    if tracker_ids:
        print("\n❓ Do you want to run all trackers now? (y/n): ", end="")
        choice = input().strip().lower()

        if choice == 'y':
            run_trackers(tracker_ids)
        else:
            print("\n💡 Trackers created but not started.")
            print(f"   To run them later, use: POST {BASE_URL}/run")
            print(f"   With payload: {{'tracker_ids': {tracker_ids}}}")


if __name__ == "__main__":
    main()
