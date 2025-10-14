#!/bin/bash

# Script to create trackers for all Hanoi areas using curl
# Configuration: Nov-Dec 2025, Daily tracking, 1-night stays, INR currency

BASE_URL="http://localhost:8000/api/v1/tracking"

echo "============================================================"
echo "🏨 Hanoi Hotel Tracker Creation Script"
echo "============================================================"
echo ""
echo "📊 Configuration:"
echo "   Period: Nov 1 - Dec 31, 2025"
echo "   Tracking: Daily (interval_days=1)"
echo "   Stay Duration: 1 night"
echo "   Currency: INR"
echo "   Adults: 2, Children: 0"
echo ""

# Array to store tracker IDs
TRACKER_IDS=()

# Function to create a tracker
create_tracker() {
    local AREA_NAME=$1
    local QUERY="${AREA_NAME} hanoi"

    echo "📍 Creating tracker for: $AREA_NAME"
    echo "   Query: $QUERY"

    RESPONSE=$(curl -s -X POST "$BASE_URL/trackers" \
        -H "Content-Type: application/json" \
        -d "{
            \"name\": \"Hanoi - $AREA_NAME - Nov-Dec 2025\",
            \"description\": \"Daily price tracking for hotels in $AREA_NAME, Hanoi (Nov-Dec 2025)\",
            \"query\": \"$QUERY\",
            \"start_date\": \"2025-11-01\",
            \"end_date\": \"2025-12-31\",
            \"interval_days\": 1,
            \"stay_duration_days\": 1,
            \"adults\": 2,
            \"children\": 0,
            \"currency\": \"INR\",
            \"country_code\": \"vn\",
            \"language\": \"en\",
            \"is_scheduled\": true
        }")

    # Extract tracker ID from response
    TRACKER_ID=$(echo $RESPONSE | grep -o '"id":[0-9]*' | head -1 | grep -o '[0-9]*')

    if [ -n "$TRACKER_ID" ]; then
        echo "   ✅ Tracker created successfully! ID: $TRACKER_ID"
        TRACKER_IDS+=($TRACKER_ID)
    else
        echo "   ❌ Failed to create tracker"
        echo "   Response: $RESPONSE"
    fi
    echo ""
}

# Create trackers for all Hanoi areas
echo "📍 Creating trackers for 5 Hanoi areas..."
echo ""

create_tracker "Old Quarter"
create_tracker "Hoan Kiem"
create_tracker "Ba Dinh"
create_tracker "Tay Ho"
create_tracker "Hai Ba Trung"

echo "============================================================"
echo "✅ Created ${#TRACKER_IDS[@]} trackers successfully!"
echo "   Tracker IDs: ${TRACKER_IDS[@]}"
echo "============================================================"
echo ""

# Ask if user wants to run the trackers
if [ ${#TRACKER_IDS[@]} -gt 0 ]; then
    echo "❓ Do you want to run all trackers now? (y/n): "
    read -r CHOICE

    if [ "$CHOICE" = "y" ] || [ "$CHOICE" = "Y" ]; then
        echo ""
        echo "🚀 Running ${#TRACKER_IDS[@]} trackers..."

        # Build JSON array of tracker IDs
        IDS_JSON=$(printf '%s\n' "${TRACKER_IDS[@]}" | jq -R . | jq -s .)

        RESPONSE=$(curl -s -X POST "$BASE_URL/run" \
            -H "Content-Type: application/json" \
            -d "{\"tracker_ids\": $IDS_JSON}")

        echo "✅ Trackers started!"
        echo "   Response: $RESPONSE"
    else
        echo ""
        echo "💡 Trackers created but not started."
        echo "   To run them later, use:"
        echo "   curl -X POST $BASE_URL/run \\"
        echo "     -H 'Content-Type: application/json' \\"
        echo "     -d '{\"tracker_ids\": [${TRACKER_IDS[@]}]}'"
    fi
fi

echo ""
echo "✨ Done!"
