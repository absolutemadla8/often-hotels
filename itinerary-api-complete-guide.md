# Itinerary Optimization API - Complete Guide

## 📋 Overview

The Itinerary Optimization API provides intelligent multi-destination trip planning with cost optimization and hotel assignment. It supports multiple search modes, single hotel preferences, and flexible date ranges.

## 🔧 API Request

### Basic Request Structure

```bash
curl -X POST "http://localhost:8000/api/v1/itineraries/optimize" \
  -H "Content-Type: application/json" \
  -d '{
    "destinations": [
      {
        "destination_id": 1,
        "area_id": 1,
        "nights": 4
      },
      {
        "destination_id": 2,
        "nights": 6
      }
    ],
    "global_date_range": {
      "start": "2025-10-25",
      "end": "2025-11-25"
    },
    "currency": "INR",
    "search_types": ["all"],
    "custom": true
  }'
```

### Request Parameters Explained

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `destinations` | Array | List of destinations in order | See below |
| `global_date_range` | Object | Overall date constraints | `{"start": "2025-10-25", "end": "2025-11-25"}` |
| `currency` | String | Preferred currency (3-letter code) | `"INR"`, `"USD"` |
| `search_types` | Array | Types of search to perform | `["all"]`, `["normal"]`, `["ranges"]` |
| `custom` | Boolean | Enable advanced search modes | `true`, `false` |

#### Destination Object Structure

```json
{
  "destination_id": 1,      // Required: Database destination ID
  "area_id": 1,             // Optional: Specific area within destination
  "nights": 4               // Required: Number of nights to stay (1-30)
}
```

#### Search Types

- **`"normal"`**: Fixed date patterns (start_month, mid_month, end_month)
- **`"ranges"`**: Flexible date ranges within the global range  
- **`"fixed_dates"`**: Specific exact dates (requires `fixed_dates` array)
- **`"all"`**: Executes all applicable search types

## 📊 API Response Structure

### High-Level Response Format

```json
{
  "success": true,
  "request_hash": "unique_request_identifier",
  "normal": { ... },          // Normal search results
  "ranges": { ... },          // Ranges search results  
  "fixed_dates": null,        // Fixed dates results (if requested)
  "best_itinerary": { ... },  // Overall best option
  "metadata": { ... },        // Performance metrics
  "filters_applied": { ... }, // Request summary
  "message": "Found X total itinerary options across Y search types"
}
```

## 🎯 Search Results Breakdown

### 1. Normal Search Results

Contains three time-based options within the global date range:

```json
"normal": {
  "start_month": { ... },    // Early dates in the range
  "mid_month": { ... },      // Middle dates in the range  
  "end_month": { ... }       // Later dates in the range
}
```

### 2. Ranges Search Results

Auto-generated overlapping date ranges for flexibility:

```json
"ranges": {
  "results": [
    { ... },  // Range 1: Early overlap (40% of period)
    { ... },  // Range 2: Mid overlap (40% of period)
    { ... }   // Range 3: Late overlap (40% of period)
  ]
}
```

## 🏨 Itinerary Object Structure

Each itinerary option contains:

```json
{
  "search_type": "normal",           // Which search produced this result
  "label": "mid_month",              // Specific label within search type
  "destinations": [...],             // Destination details (see below)
  "total_cost": "27183.00",          // Total trip cost
  "currency": "INR",                 // Currency of prices
  "total_nights": 10,                // Total nights across all destinations
  "start_date": "2025-11-05",        // Trip start date
  "end_date": "2025-11-14",          // Trip end date
  "optimization_score": null,        // Quality score (future use)
  "alternatives_generated": 1,       // Number of alternatives considered
  "single_hotel_destinations": 2,    // How many destinations use single hotels
  "date_context": null               // Additional date context (future use)
}
```

## 🏢 Destination Object in Results

Each destination in an itinerary contains:

```json
{
  "destination_id": 1,               // Database destination ID
  "destination_name": "Destination 1", // Display name
  "area_id": 1,                      // Area ID (if specified)
  "area_name": null,                 // Area display name
  "order": 0,                        // Position in itinerary (0-based)
  "nights": 4,                       // Nights at this destination
  "start_date": "2025-11-05",        // Check-in date
  "end_date": "2025-11-08",          // Check-out date
  "total_cost": "10233.00",          // Cost for this destination
  "currency": "INR",                 // Currency
  "hotels_count": 1,                 // Number of different hotels used
  "single_hotel": true,              // Whether same hotel all nights
  "hotel_assignments": [...]         // Daily hotel assignments (see below)
}
```

## 🏨 Hotel Assignment Structure

Each night's hotel assignment:

```json
{
  "hotel_id": 256,                   // Database hotel ID
  "hotel_name": "Jani's Place Cottage", // Hotel display name
  "assignment_date": "2025-11-05",   // Night date
  "price": "2701.00",                // Price for this night
  "currency": "INR",                 // Currency
  "room_type": null,                 // Room type (future use)
  "selection_reason": "single_hotel" // Why this hotel was chosen
}
```

### Selection Reasons Explained

| Reason | Meaning | Strategy |
|--------|---------|----------|
| `"single_hotel"` | Same hotel for all nights at destination | Convenience prioritized |
| `"cheapest_day"` | Cheapest hotel for this specific date | Cost optimization |

## 💰 Cost Optimization Logic

### Single Hotel vs Daily Optimization

The system calculates two options for each destination:

1. **Single Hotel Solution**: Best hotel that covers all nights
   - Finds hotels available for all required dates
   - Selects the one with **lowest total cost** across all nights
   - Provides convenience and consistency

2. **Daily Cheapest Solution**: Best hotel for each individual night
   - For each date, finds the absolute cheapest available hotel
   - May result in different hotels each night
   - Provides maximum cost savings

### Decision Algorithm

```python
if single_hotel_cost <= daily_cheapest_cost * 1.20:
    choose_single_hotel()  # Within 20% tolerance
else:
    choose_daily_cheapest()  # Savings > 20%
```

**20% Tolerance**: System prioritizes convenience unless daily switching saves more than 20%

## 📈 Metadata Section

Performance and optimization metrics:

```json
"metadata": {
  "processing_time_ms": 618,        // Total processing time
  "cache_hit": false,               // Whether result was cached
  "hotels_searched": 0,             // Hotels evaluated
  "price_queries": 0,               // Database queries made
  "alternatives_generated": 6,      // Total options generated
  "best_cost_found": "27183.00"     // Lowest cost option found
}
```

## 🎛️ Filters Applied Summary

Shows what was actually processed:

```json
"filters_applied": {
  "search_types": ["all"],          // Search types executed
  "custom": true,                   // Custom mode enabled
  "currency": "INR",                // Currency used
  "guests": {                       // Guest configuration
    "adults": 1,
    "children": 0,
    "child_ages": null
  }
}
```

## 🏆 Best Itinerary Selection

The `best_itinerary` is chosen based on:

1. **Lowest total cost** across all search results
2. **Single hotel preference** when costs are similar
3. **Date availability** and constraints

## 📝 Complete Example Response

### Request
```bash
curl -X POST "http://localhost:8000/api/v1/itineraries/optimize" \
  -H "Content-Type: application/json" \
  -d '{
    "destinations": [
      {"destination_id": 1, "area_id": 1, "nights": 4},
      {"destination_id": 2, "nights": 6}
    ],
    "global_date_range": {"start": "2025-10-25", "end": "2025-11-25"},
    "currency": "INR",
    "search_types": ["all"],
    "custom": true
  }'
```

### Key Response Insights

From the actual response:

**🎯 Best Option Found:**
- **Cost**: ₹27,183 for 10 nights (₹2,718 per night average)
- **Dates**: Nov 5-14, 2025
- **Strategy**: Single hotels at both destinations
- **Convenience**: No hotel switching required

**🏨 Hotel Assignments:**
- **Ubud (4 nights)**: Jani's Place Cottage - ₹10,233
  - Consistent pricing around ₹2,500/night
  - `"single_hotel": true` - convenience prioritized
- **Gili Trawangan (6 nights)**: Gili Paddy Hotel - ₹16,950  
  - Consistent ₹2,825/night rate
  - `"single_hotel": true` - convenience prioritized

**📊 Options Comparison:**
- **6 total options** across normal and ranges searches
- **Best ranges option**: ₹27,656 (₹473 more expensive)
- **Processing time**: 618ms (very fast)

**🎪 Search Types Results:**
- **Normal search**: 3 options (start_month, mid_month, end_month)
- **Ranges search**: 3 options (auto-generated overlapping ranges)
- **Fixed dates**: Not used (null)

## 🔍 What to Look For

### Quality Indicators

1. **`"single_hotel": true`** = Better travel experience
2. **Low `"hotels_count"`** = Less hassle, more consistency  
3. **`"selection_reason": "single_hotel"`** = Convenience over cost
4. **High `"single_hotel_destinations"`** = More convenient trip

### Cost Analysis

1. Compare `total_cost` across different search results
2. Check `metadata.best_cost_found` for overall best price
3. Look at cost per night: `total_cost / total_nights`
4. Consider convenience premium for single hotels

### Date Flexibility

1. **Normal search** = Fixed patterns within global range
2. **Ranges search** = Sliding date windows for flexibility
3. Multiple options = More choice for the traveler

## 🚀 Usage Tips

1. **Use `"search_types": ["all"]`** for maximum options
2. **Set `"custom": true`** to enable ranges search
3. **Wide date ranges** give more optimization opportunities
4. **Match currency** to your price data for best results
5. **Consider `single_hotel_destinations`** for trip convenience

This API provides sophisticated trip optimization balancing cost, convenience, and flexibility! 🎯