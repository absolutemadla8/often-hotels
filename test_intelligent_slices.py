#!/usr/bin/env python3

"""
Test script to demonstrate the new intelligent monthly slices logic
"""

import requests
import json
from datetime import date, timedelta

API_BASE = "http://localhost:8000/api/v1"

def test_intelligent_slices():
    """Test different search scenarios to show intelligent timing"""
    
    # Scenario 1: Searching on 20th of October (late month)
    print("🗓️  SCENARIO 1: Searching on Oct 20th (Late Month)")
    print("Expected: Next month options (Nov start, Nov mid, Nov end)\n")
    
    test_request = {
        "custom": False,  # Normal search
        "destinations": [
            {"destination_id": 1, "area_id": 1, "nights": 3},  # Bali - Ubud area
            {"destination_id": 3, "nights": 2}   # Mumbai
        ],
        "global_date_range": {
            "start": "2025-10-20",  # Oct 20th - late month  
            "end": "2025-11-20"     # 30-day window with valid data
        },
        "guests": {"adults": 2, "children": 0},
        "currency": "INR"
    }
    
    response = requests.post(f"{API_BASE}/itineraries/optimize", json=test_request)
    if response.status_code == 200:
        result = response.json()
        print("DEBUG - Full response:", json.dumps(result, indent=2, default=str))
        show_timing_results(result, "Late Month Search (Oct 20)")
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
    
    print("\n" + "="*80 + "\n")
    
    # Scenario 2: Searching on 5th of November (early month)  
    print("🗓️  SCENARIO 2: Searching on Nov 5th (Early Month)")
    print("Expected: Current month start/mid + next month start\n")
    
    test_request["global_date_range"] = {
        "start": "2025-11-05",  # Nov 5th - early month
        "end": "2025-11-25"     # 20-day window with valid data
    }
    
    response = requests.post(f"{API_BASE}/itineraries/optimize", json=test_request)
    if response.status_code == 200:
        result = response.json()
        show_timing_results(result, "Early Month Search (Nov 5)")
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
    
    print("\n" + "="*80 + "\n")
    
    # Scenario 3: Searching on 15th of November (mid month)
    print("🗓️  SCENARIO 3: Searching on Nov 15th (Mid Month)")  
    print("Expected: End of current month + next month start/mid\n")
    
    test_request["global_date_range"] = {
        "start": "2025-11-15",  # Nov 15th - mid month
        "end": "2025-11-27"     # Until end of our data
    }
    
    response = requests.post(f"{API_BASE}/itineraries/optimize", json=test_request)
    if response.status_code == 200:
        result = response.json()
        show_timing_results(result, "Mid Month Search (Nov 15)")
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)

def show_timing_results(result, scenario_name):
    """Display the timing results in a readable format"""
    
    print(f"📊 Results for: {scenario_name}")
    
    data = result.get("data", result)  # Handle filtered response
    
    if "normal" in data and data["normal"]:
        normal = data["normal"]
        
        # Handle new month-grouped structure
        monthly_options = normal.get("monthly_options", [])
        if monthly_options:
            print(f"📅 Month-Grouped Options ({len(monthly_options)} months):")
            
            for month_data in monthly_options:
                month_name = month_data.get("month", "Unknown Month")
                print(f"\n  🗓️  {month_name}:")
                
                # Check each timing option in the month
                timing_options = [
                    ("Early", month_data.get("start_month")),
                    ("Mid", month_data.get("mid_month")), 
                    ("Late", month_data.get("end_month"))
                ]
                
                for timing_name, option_data in timing_options:
                    if option_data:
                        start_date = option_data.get("start_date", "Unknown")
                        end_date = option_data.get("end_date", "Unknown") 
                        label = option_data.get("label", "Unknown")
                        cost = option_data.get("total_cost", "Unknown")
                        
                        print(f"    ✅ {timing_name}: {start_date} to {end_date}")
                        print(f"       Strategy: {label}")
                        print(f"       Cost: ₹{cost}")
                    else:
                        print(f"    ❌ {timing_name}: Not available")
        else:
            print("❌ No monthly options found")
    
    # Show access message if present (for anonymous users)
    if "access_message" in data:
        print(f"💡 {data['access_message']}")
    
    user_tier = result.get("user_tier", "unknown")
    print(f"👤 User Tier: {user_tier}")

if __name__ == "__main__":
    test_intelligent_slices()