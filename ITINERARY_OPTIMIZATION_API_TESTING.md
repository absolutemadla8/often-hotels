# Itinerary Optimization API Testing Guide

This document contains comprehensive testing examples for the Often Hotels Itinerary Optimization API, including all search types and their full responses.

## Authentication

First, obtain a JWT token by logging in:

```bash
curl -X POST "http://localhost:8006/api/v1/auth/login" \
-H "Content-Type: application/json" \
-d '{"email": "trippy@oftenhotels.com", "password": "admin123"}'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIzIiwiZXhwIjoxNzkxMDE3MTMzLCJ0eXBlIjoiYWNjZXNzIn0.XAL7-FbTvS82sQVk18iyCfBXFbTkpr1m7C7BVnNwtgk",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIzIiwiZXhwIjoxNzYyMDczMTMzLCJ0eXBlIjoicmVmcmVzaCJ9.zOQ6TbDUKVdS_vhimApAkxjkLt19a9FaBi3qsH8ywvk",
  "token_type": "bearer",
  "expires_in": 31536000
}
```

**Note:** Admin users automatically receive 1-year tokens (31,536,000 seconds = 365 days).

---

## 1. Normal Search (Default)

Standard monthly optimization with start, mid, and end-month options.

```bash
curl -X POST "http://localhost:8006/api/v1/itineraries/optimize" \
-H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIzIiwiZXhwIjoxNzkxMDE3MTMzLCJ0eXBlIjoiYWNjZXNzIn0.XAL7-FbTvS82sQVk18iyCfBXFbTkpr1m7C7BVnNwtgk" \
-H "Content-Type: application/json" \
-d '{
  "destinations": [
    {"destination_id": 1, "nights": 3}
  ],
  "global_date_range": {
    "start": "2025-10-01",
    "end": "2025-10-31"
  },
  "currency": "INR"
}'
```

**Response:**
```json
{
  "data": {
    "success": true,
    "request_hash": "30ec9cf276681a58c427b1a35dba955f4436e945139accbf9520450cdc409480",
    "normal": {
      "monthly_options": [
        {
          "month": "October 2025",
          "start_month": {
            "search_type": "fixed_dates",
            "label": "October 2025_start",
            "destinations": [
              {
                "destination_id": 1,
                "destination_name": "Destination 1",
                "area_id": null,
                "area_name": null,
                "order": 0,
                "nights": 3,
                "start_date": "2025-10-05",
                "end_date": "2025-10-07",
                "total_cost": 6537.0,
                "currency": "INR",
                "hotels_count": 1,
                "single_hotel": true,
                "hotel_assignments": [
                  {
                    "hotel_id": 294,
                    "hotel_name": "Villa Reisya & guest house reisya",
                    "assignment_date": "2025-10-05",
                    "price": 2179.0,
                    "currency": "INR",
                    "room_type": null,
                    "selection_reason": "cheapest_day"
                  },
                  {
                    "hotel_id": 294,
                    "hotel_name": "Villa Reisya & guest house reisya",
                    "assignment_date": "2025-10-06",
                    "price": 2179.0,
                    "currency": "INR",
                    "room_type": null,
                    "selection_reason": "cheapest_day"
                  },
                  {
                    "hotel_id": 294,
                    "hotel_name": "Villa Reisya & guest house reisya",
                    "assignment_date": "2025-10-07",
                    "price": 2179.0,
                    "currency": "INR",
                    "room_type": null,
                    "selection_reason": "cheapest_day"
                  }
                ]
              }
            ],
            "total_cost": 6537.0,
            "currency": "INR",
            "total_nights": 3,
            "start_date": "2025-10-05",
            "end_date": "2025-10-07",
            "optimization_score": null,
            "alternatives_generated": 1,
            "single_hotel_destinations": 1,
            "date_context": null
          },
          "mid_month": {
            "search_type": "fixed_dates",
            "label": "October 2025_mid",
            "destinations": [
              {
                "destination_id": 1,
                "destination_name": "Destination 1",
                "area_id": null,
                "area_name": null,
                "order": 0,
                "nights": 3,
                "start_date": "2025-10-15",
                "end_date": "2025-10-17",
                "total_cost": 6537.0,
                "currency": "INR",
                "hotels_count": 1,
                "single_hotel": true,
                "hotel_assignments": [
                  {
                    "hotel_id": 294,
                    "hotel_name": "Villa Reisya & guest house reisya",
                    "assignment_date": "2025-10-15",
                    "price": 2179.0,
                    "currency": "INR",
                    "room_type": null,
                    "selection_reason": "cheapest_day"
                  },
                  {
                    "hotel_id": 294,
                    "hotel_name": "Villa Reisya & guest house reisya",
                    "assignment_date": "2025-10-16",
                    "price": 2179.0,
                    "currency": "INR",
                    "room_type": null,
                    "selection_reason": "cheapest_day"
                  },
                  {
                    "hotel_id": 294,
                    "hotel_name": "Villa Reisya & guest house reisya",
                    "assignment_date": "2025-10-17",
                    "price": 2179.0,
                    "currency": "INR",
                    "room_type": null,
                    "selection_reason": "cheapest_day"
                  }
                ]
              }
            ],
            "total_cost": 6537.0,
            "currency": "INR",
            "total_nights": 3,
            "start_date": "2025-10-15",
            "end_date": "2025-10-17",
            "optimization_score": null,
            "alternatives_generated": 1,
            "single_hotel_destinations": 1,
            "date_context": null
          },
          "end_month": {
            "search_type": "fixed_dates",
            "label": "October 2025_end",
            "destinations": [
              {
                "destination_id": 1,
                "destination_name": "Destination 1",
                "area_id": null,
                "area_name": null,
                "order": 0,
                "nights": 3,
                "start_date": "2025-10-25",
                "end_date": "2025-10-27",
                "total_cost": 6946.0,
                "currency": "INR",
                "hotels_count": 1,
                "single_hotel": true,
                "hotel_assignments": [
                  {
                    "hotel_id": 294,
                    "hotel_name": "Villa Reisya & guest house reisya",
                    "assignment_date": "2025-10-25",
                    "price": 2280.0,
                    "currency": "INR",
                    "room_type": null,
                    "selection_reason": "cheapest_day"
                  },
                  {
                    "hotel_id": 294,
                    "hotel_name": "Villa Reisya & guest house reisya",
                    "assignment_date": "2025-10-26",
                    "price": 2280.0,
                    "currency": "INR",
                    "room_type": null,
                    "selection_reason": "cheapest_day"
                  },
                  {
                    "hotel_id": 294,
                    "hotel_name": "Villa Reisya & guest house reisya",
                    "assignment_date": "2025-10-27",
                    "price": 2386.0,
                    "currency": "INR",
                    "room_type": null,
                    "selection_reason": "cheapest_day"
                  }
                ]
              }
            ],
            "total_cost": 6946.0,
            "currency": "INR",
            "total_nights": 3,
            "start_date": "2025-10-25",
            "end_date": "2025-10-27",
            "optimization_score": null,
            "alternatives_generated": 1,
            "single_hotel_destinations": 1,
            "date_context": null
          }
        }
      ]
    },
    "ranges": null,
    "fixed_dates": null,
    "best_itinerary": {
      "search_type": "fixed_dates",
      "label": "October 2025_start",
      "destinations": [
        {
          "destination_id": 1,
          "destination_name": "Destination 1",
          "area_id": null,
          "area_name": null,
          "order": 0,
          "nights": 3,
          "start_date": "2025-10-05",
          "end_date": "2025-10-07",
          "total_cost": 6537.0,
          "currency": "INR",
          "hotels_count": 1,
          "single_hotel": true,
          "hotel_assignments": [
            {
              "hotel_id": 294,
              "hotel_name": "Villa Reisya & guest house reisya",
              "assignment_date": "2025-10-05",
              "price": 2179.0,
              "currency": "INR",
              "room_type": null,
              "selection_reason": "cheapest_day"
            },
            {
              "hotel_id": 294,
              "hotel_name": "Villa Reisya & guest house reisya",
              "assignment_date": "2025-10-06",
              "price": 2179.0,
              "currency": "INR",
              "room_type": null,
              "selection_reason": "cheapest_day"
            },
            {
              "hotel_id": 294,
              "hotel_name": "Villa Reisya & guest house reisya",
              "assignment_date": "2025-10-07",
              "price": 2179.0,
              "currency": "INR",
              "room_type": null,
              "selection_reason": "cheapest_day"
            }
          ]
        }
      ],
      "total_cost": 6537.0,
      "currency": "INR",
      "total_nights": 3,
      "start_date": "2025-10-05",
      "end_date": "2025-10-07",
      "optimization_score": null,
      "alternatives_generated": 1,
      "single_hotel_destinations": 1,
      "date_context": null
    },
    "metadata": {
      "processing_time_ms": 228,
      "cache_hit": true,
      "hotels_searched": 0,
      "price_queries": 0,
      "alternatives_generated": 3,
      "best_cost_found": 6537.0,
      "user_authenticated": false,
      "clean_structure_used": true,
      "nearest_option_shown": null
    },
    "filters_applied": {
      "search_types": ["normal"],
      "custom": false,
      "currency": "INR",
      "guests": {
        "adults": 1,
        "children": 0,
        "child_ages": null
      }
    },
    "message": "Found 3 itinerary options across 1 months"
  },
  "user_tier": "admin"
}
```

---

## 2. Custom Ranges Search

Sliding window optimization across provided date ranges.

```bash
curl -X POST "http://localhost:8006/api/v1/itineraries/optimize" \
-H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIzIiwiZXhwIjoxNzkxMDE3MTMzLCJ0eXBlIjoiYWNjZXNzIn0.XAL7-FbTvS82sQVk18iyCfBXFbTkpr1m7C7BVnNwtgk" \
-H "Content-Type: application/json" \
-d '{
  "custom": true,
  "search_types": ["ranges"],
  "destinations": [
    {"destination_id": 1, "nights": 3}
  ],
  "global_date_range": {
    "start": "2025-10-01",
    "end": "2025-10-31"
  },
  "ranges": [
    {"start": "2025-10-05", "end": "2025-10-15"},
    {"start": "2025-10-20", "end": "2025-10-30"}
  ],
  "currency": "INR"
}'
```

**Response:**
```json
{
  "data": {
    "success": true,
    "request_hash": "70e0429cb4d73062aff0c46bace606b59705e856f927f3f038cf871861600628",
    "normal": null,
    "ranges": {
      "results": [
        {
          "search_type": "ranges",
          "label": "range_optimized",
          "destinations": [
            {
              "destination_id": 1,
              "destination_name": "Destination 1",
              "area_id": null,
              "area_name": null,
              "order": 0,
              "nights": 3,
              "start_date": "2025-10-05",
              "end_date": "2025-10-07",
              "total_cost": 6537.0,
              "currency": "INR",
              "hotels_count": 1,
              "single_hotel": true,
              "hotel_assignments": [
                {
                  "hotel_id": 294,
                  "hotel_name": "Villa Reisya & guest house reisya",
                  "assignment_date": "2025-10-05",
                  "price": 2179.0,
                  "currency": "INR",
                  "room_type": null,
                  "selection_reason": "cheapest_day"
                },
                {
                  "hotel_id": 294,
                  "hotel_name": "Villa Reisya & guest house reisya",
                  "assignment_date": "2025-10-06",
                  "price": 2179.0,
                  "currency": "INR",
                  "room_type": null,
                  "selection_reason": "cheapest_day"
                },
                {
                  "hotel_id": 294,
                  "hotel_name": "Villa Reisya & guest house reisya",
                  "assignment_date": "2025-10-07",
                  "price": 2179.0,
                  "currency": "INR",
                  "room_type": null,
                  "selection_reason": "cheapest_day"
                }
              ]
            }
          ],
          "total_cost": 6537.0,
          "currency": "INR",
          "total_nights": 3,
          "start_date": "2025-10-05",
          "end_date": "2025-10-07",
          "optimization_score": null,
          "alternatives_generated": 1,
          "single_hotel_destinations": 1,
          "date_context": null
        },
        {
          "search_type": "ranges",
          "label": "range_optimized",
          "destinations": [
            {
              "destination_id": 1,
              "destination_name": "Destination 1",
              "area_id": null,
              "area_name": null,
              "order": 0,
              "nights": 3,
              "start_date": "2025-10-06",
              "end_date": "2025-10-08",
              "total_cost": 6537.0,
              "currency": "INR",
              "hotels_count": 1,
              "single_hotel": true,
              "hotel_assignments": [
                {
                  "hotel_id": 294,
                  "hotel_name": "Villa Reisya & guest house reisya",
                  "assignment_date": "2025-10-06",
                  "price": 2179.0,
                  "currency": "INR",
                  "room_type": null,
                  "selection_reason": "cheapest_day"
                },
                {
                  "hotel_id": 294,
                  "hotel_name": "Villa Reisya & guest house reisya",
                  "assignment_date": "2025-10-07",
                  "price": 2179.0,
                  "currency": "INR",
                  "room_type": null,
                  "selection_reason": "cheapest_day"
                },
                {
                  "hotel_id": 294,
                  "hotel_name": "Villa Reisya & guest house reisya",
                  "assignment_date": "2025-10-08",
                  "price": 2179.0,
                  "currency": "INR",
                  "room_type": null,
                  "selection_reason": "cheapest_day"
                }
              ]
            }
          ],
          "total_cost": 6537.0,
          "currency": "INR",
          "total_nights": 3,
          "start_date": "2025-10-06",
          "end_date": "2025-10-08",
          "optimization_score": null,
          "alternatives_generated": 1,
          "single_hotel_destinations": 1,
          "date_context": null
        },
        {
          "search_type": "ranges",
          "label": "range_optimized",
          "destinations": [
            {
              "destination_id": 1,
              "destination_name": "Destination 1",
              "area_id": null,
              "area_name": null,
              "order": 0,
              "nights": 3,
              "start_date": "2025-10-07",
              "end_date": "2025-10-09",
              "total_cost": 7678.0,
              "currency": "INR",
              "hotels_count": 2,
              "single_hotel": false,
              "hotel_assignments": [
                {
                  "hotel_id": 294,
                  "hotel_name": "Villa Reisya & guest house reisya",
                  "assignment_date": "2025-10-07",
                  "price": 2179.0,
                  "currency": "INR",
                  "room_type": null,
                  "selection_reason": "cheapest_day"
                },
                {
                  "hotel_id": 294,
                  "hotel_name": "Villa Reisya & guest house reisya",
                  "assignment_date": "2025-10-08",
                  "price": 2179.0,
                  "currency": "INR",
                  "room_type": null,
                  "selection_reason": "cheapest_day"
                },
                {
                  "hotel_id": 284,
                  "hotel_name": "The Crystal Luxury Bay Resort Nusa Dua - Bali",
                  "assignment_date": "2025-10-09",
                  "price": 3320.0,
                  "currency": "INR",
                  "room_type": null,
                  "selection_reason": "cheapest_day"
                }
              ]
            }
          ],
          "total_cost": 7678.0,
          "currency": "INR",
          "total_nights": 3,
          "start_date": "2025-10-07",
          "end_date": "2025-10-09",
          "optimization_score": null,
          "alternatives_generated": 1,
          "single_hotel_destinations": 0,
          "date_context": null
        }
      ]
    },
    "fixed_dates": null,
    "best_itinerary": {
      "search_type": "ranges",
      "label": "range_optimized",
      "destinations": [
        {
          "destination_id": 1,
          "destination_name": "Destination 1",
          "area_id": null,
          "area_name": null,
          "order": 0,
          "nights": 3,
          "start_date": "2025-10-05",
          "end_date": "2025-10-07",
          "total_cost": 6537.0,
          "currency": "INR",
          "hotels_count": 1,
          "single_hotel": true,
          "hotel_assignments": [
            {
              "hotel_id": 294,
              "hotel_name": "Villa Reisya & guest house reisya",
              "assignment_date": "2025-10-05",
              "price": 2179.0,
              "currency": "INR",
              "room_type": null,
              "selection_reason": "cheapest_day"
            },
            {
              "hotel_id": 294,
              "hotel_name": "Villa Reisya & guest house reisya",
              "assignment_date": "2025-10-06",
              "price": 2179.0,
              "currency": "INR",
              "room_type": null,
              "selection_reason": "cheapest_day"
            },
            {
              "hotel_id": 294,
              "hotel_name": "Villa Reisya & guest house reisya",
              "assignment_date": "2025-10-07",
              "price": 2179.0,
              "currency": "INR",
              "room_type": null,
              "selection_reason": "cheapest_day"
            }
          ]
        }
      ],
      "total_cost": 6537.0,
      "currency": "INR",
      "total_nights": 3,
      "start_date": "2025-10-05",
      "end_date": "2025-10-07",
      "optimization_score": null,
      "alternatives_generated": 1,
      "single_hotel_destinations": 1,
      "date_context": null
    },
    "metadata": {
      "processing_time_ms": 289,
      "cache_hit": false,
      "hotels_searched": 0,
      "price_queries": 0,
      "alternatives_generated": 3,
      "best_cost_found": 6537.0,
      "user_authenticated": false,
      "clean_structure_used": true,
      "nearest_option_shown": null
    },
    "filters_applied": {
      "search_types": ["ranges"],
      "custom": true,
      "currency": "INR",
      "guests": {
        "adults": 1,
        "children": 0,
        "child_ages": null
      }
    },
    "message": "Found 3 total itinerary options across 1 search types"
  },
  "user_tier": "admin"
}
```

---

## 3. Custom Fixed Dates Search

Optimization for exact start dates.

```bash
curl -X POST "http://localhost:8006/api/v1/itineraries/optimize" \
-H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIzIiwiZXhwIjoxNzkxMDE3MTMzLCJ0eXBlIjoiYWNjZXNzIn0.XAL7-FbTvS82sQVk18iyCfBXFbTkpr1m7C7BVnNwtgk" \
-H "Content-Type: application/json" \
-d '{
  "custom": true,
  "search_types": ["fixed_dates"],
  "destinations": [
    {"destination_id": 1, "nights": 3}
  ],
  "global_date_range": {
    "start": "2025-10-01",
    "end": "2025-10-31"
  },
  "fixed_dates": ["2025-10-10", "2025-10-15", "2025-10-20"],
  "currency": "INR"
}'
```

**Response:**
```json
{
  "data": {
    "success": true,
    "request_hash": "272e8c146f51dd60f2cebdec8f8c5c4c2d73720938c4a7ee579238155cf1cdc8",
    "normal": null,
    "ranges": null,
    "fixed_dates": {
      "results": [
        {
          "search_type": "fixed_dates",
          "label": "fixed_date",
          "destinations": [
            {
              "destination_id": 1,
              "destination_name": "Destination 1",
              "area_id": null,
              "area_name": null,
              "order": 0,
              "nights": 3,
              "start_date": "2025-10-10",
              "end_date": "2025-10-12",
              "total_cost": 7678.0,
              "currency": "INR",
              "hotels_count": 2,
              "single_hotel": false,
              "hotel_assignments": [
                {
                  "hotel_id": 284,
                  "hotel_name": "The Crystal Luxury Bay Resort Nusa Dua - Bali",
                  "assignment_date": "2025-10-10",
                  "price": 3320.0,
                  "currency": "INR",
                  "room_type": null,
                  "selection_reason": "cheapest_day"
                },
                {
                  "hotel_id": 294,
                  "hotel_name": "Villa Reisya & guest house reisya",
                  "assignment_date": "2025-10-11",
                  "price": 2179.0,
                  "currency": "INR",
                  "room_type": null,
                  "selection_reason": "cheapest_day"
                },
                {
                  "hotel_id": 294,
                  "hotel_name": "Villa Reisya & guest house reisya",
                  "assignment_date": "2025-10-12",
                  "price": 2179.0,
                  "currency": "INR",
                  "room_type": null,
                  "selection_reason": "cheapest_day"
                }
              ]
            }
          ],
          "total_cost": 7678.0,
          "currency": "INR",
          "total_nights": 3,
          "start_date": "2025-10-10",
          "end_date": "2025-10-12",
          "optimization_score": null,
          "alternatives_generated": 1,
          "single_hotel_destinations": 0,
          "date_context": null
        },
        {
          "search_type": "fixed_dates",
          "label": "fixed_date",
          "destinations": [
            {
              "destination_id": 1,
              "destination_name": "Destination 1",
              "area_id": null,
              "area_name": null,
              "order": 0,
              "nights": 3,
              "start_date": "2025-10-15",
              "end_date": "2025-10-17",
              "total_cost": 6537.0,
              "currency": "INR",
              "hotels_count": 1,
              "single_hotel": true,
              "hotel_assignments": [
                {
                  "hotel_id": 294,
                  "hotel_name": "Villa Reisya & guest house reisya",
                  "assignment_date": "2025-10-15",
                  "price": 2179.0,
                  "currency": "INR",
                  "room_type": null,
                  "selection_reason": "cheapest_day"
                },
                {
                  "hotel_id": 294,
                  "hotel_name": "Villa Reisya & guest house reisya",
                  "assignment_date": "2025-10-16",
                  "price": 2179.0,
                  "currency": "INR",
                  "room_type": null,
                  "selection_reason": "cheapest_day"
                },
                {
                  "hotel_id": 294,
                  "hotel_name": "Villa Reisya & guest house reisya",
                  "assignment_date": "2025-10-17",
                  "price": 2179.0,
                  "currency": "INR",
                  "room_type": null,
                  "selection_reason": "cheapest_day"
                }
              ]
            }
          ],
          "total_cost": 6537.0,
          "currency": "INR",
          "total_nights": 3,
          "start_date": "2025-10-15",
          "end_date": "2025-10-17",
          "optimization_score": null,
          "alternatives_generated": 1,
          "single_hotel_destinations": 1,
          "date_context": null
        },
        {
          "search_type": "fixed_dates",
          "label": "fixed_date",
          "destinations": [
            {
              "destination_id": 1,
              "destination_name": "Destination 1",
              "area_id": null,
              "area_name": null,
              "order": 0,
              "nights": 3,
              "start_date": "2025-10-20",
              "end_date": "2025-10-22",
              "total_cost": 6384.0,
              "currency": "INR",
              "hotels_count": 2,
              "single_hotel": false,
              "hotel_assignments": [
                {
                  "hotel_id": 294,
                  "hotel_name": "Villa Reisya & guest house reisya",
                  "assignment_date": "2025-10-20",
                  "price": 2184.0,
                  "currency": "INR",
                  "room_type": null,
                  "selection_reason": "cheapest_day"
                },
                {
                  "hotel_id": 294,
                  "hotel_name": "Villa Reisya & guest house reisya",
                  "assignment_date": "2025-10-21",
                  "price": 2280.0,
                  "currency": "INR",
                  "room_type": null,
                  "selection_reason": "cheapest_day"
                },
                {
                  "hotel_id": 277,
                  "hotel_name": "Villa Metimpal",
                  "assignment_date": "2025-10-22",
                  "price": 1920.0,
                  "currency": "INR",
                  "room_type": null,
                  "selection_reason": "cheapest_day"
                }
              ]
            }
          ],
          "total_cost": 6384.0,
          "currency": "INR",
          "total_nights": 3,
          "start_date": "2025-10-20",
          "end_date": "2025-10-22",
          "optimization_score": null,
          "alternatives_generated": 1,
          "single_hotel_destinations": 0,
          "date_context": null
        }
      ]
    },
    "best_itinerary": {
      "search_type": "fixed_dates",
      "label": "fixed_date",
      "destinations": [
        {
          "destination_id": 1,
          "destination_name": "Destination 1",
          "area_id": null,
          "area_name": null,
          "order": 0,
          "nights": 3,
          "start_date": "2025-10-20",
          "end_date": "2025-10-22",
          "total_cost": 6384.0,
          "currency": "INR",
          "hotels_count": 2,
          "single_hotel": false,
          "hotel_assignments": [
            {
              "hotel_id": 294,
              "hotel_name": "Villa Reisya & guest house reisya",
              "assignment_date": "2025-10-20",
              "price": 2184.0,
              "currency": "INR",
              "room_type": null,
              "selection_reason": "cheapest_day"
            },
            {
              "hotel_id": 294,
              "hotel_name": "Villa Reisya & guest house reisya",
              "assignment_date": "2025-10-21",
              "price": 2280.0,
              "currency": "INR",
              "room_type": null,
              "selection_reason": "cheapest_day"
            },
            {
              "hotel_id": 277,
              "hotel_name": "Villa Metimpal",
              "assignment_date": "2025-10-22",
              "price": 1920.0,
              "currency": "INR",
              "room_type": null,
              "selection_reason": "cheapest_day"
            }
          ]
        }
      ],
      "total_cost": 6384.0,
      "currency": "INR",
      "total_nights": 3,
      "start_date": "2025-10-20",
      "end_date": "2025-10-22",
      "optimization_score": null,
      "alternatives_generated": 1,
      "single_hotel_destinations": 0,
      "date_context": null
    },
    "metadata": {
      "processing_time_ms": 155,
      "cache_hit": false,
      "hotels_searched": 0,
      "price_queries": 0,
      "alternatives_generated": 3,
      "best_cost_found": 6384.0,
      "user_authenticated": false,
      "clean_structure_used": true,
      "nearest_option_shown": null
    },
    "filters_applied": {
      "search_types": ["fixed_dates"],
      "custom": true,
      "currency": "INR",
      "guests": {
        "adults": 1,
        "children": 0,
        "child_ages": null
      }
    },
    "message": "Found 3 total itinerary options across 1 search types"
  },
  "user_tier": "admin"
}
```

---

## 4. Custom "All" Search Types

Combines normal, ranges, and fixed_dates searches.

```bash
curl -X POST "http://localhost:8006/api/v1/itineraries/optimize" \
-H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIzIiwiZXhwIjoxNzkxMDE3MTMzLCJ0eXBlIjoiYWNjZXNzIn0.XAL7-FbTvS82sQVk18iyCfBXFbTkpr1m7C7BVnNwtgk" \
-H "Content-Type: application/json" \
-d '{
  "custom": true,
  "search_types": ["all"],
  "destinations": [
    {"destination_id": 1, "nights": 2}
  ],
  "global_date_range": {
    "start": "2025-10-01",
    "end": "2025-10-15"
  },
  "ranges": [
    {"start": "2025-10-05", "end": "2025-10-10"}
  ],
  "fixed_dates": ["2025-10-08", "2025-10-12"],
  "currency": "INR"
}'
```

**Response:**
```json
{
  "data": {
    "success": true,
    "request_hash": "8708478d67b6c39b58615b6c0ff05f577b5be63042cfd3c93f936ea0257dd3c0",
    "normal": {
      "monthly_options": [
        {
          "month": "October 2025",
          "start_month": {
            "search_type": "fixed_dates",
            "label": "October 2025_start",
            "destinations": [
              {
                "destination_id": 1,
                "destination_name": "Destination 1",
                "area_id": null,
                "area_name": null,
                "order": 0,
                "nights": 2,
                "start_date": "2025-10-05",
                "end_date": "2025-10-06",
                "total_cost": 4358.0,
                "currency": "INR",
                "hotels_count": 1,
                "single_hotel": true,
                "hotel_assignments": [
                  {
                    "hotel_id": 294,
                    "hotel_name": "Villa Reisya & guest house reisya",
                    "assignment_date": "2025-10-05",
                    "price": 2179.0,
                    "currency": "INR",
                    "room_type": null,
                    "selection_reason": "cheapest_day"
                  },
                  {
                    "hotel_id": 294,
                    "hotel_name": "Villa Reisya & guest house reisya",
                    "assignment_date": "2025-10-06",
                    "price": 2179.0,
                    "currency": "INR",
                    "room_type": null,
                    "selection_reason": "cheapest_day"
                  }
                ]
              }
            ],
            "total_cost": 4358.0,
            "currency": "INR",
            "total_nights": 2,
            "start_date": "2025-10-05",
            "end_date": "2025-10-06",
            "optimization_score": null,
            "alternatives_generated": 1,
            "single_hotel_destinations": 1,
            "date_context": null
          },
          "mid_month": null,
          "end_month": null
        }
      ]
    },
    "ranges": {
      "results": [
        {
          "search_type": "ranges",
          "label": "range_optimized",
          "destinations": [
            {
              "destination_id": 1,
              "destination_name": "Destination 1",
              "area_id": null,
              "area_name": null,
              "order": 0,
              "nights": 2,
              "start_date": "2025-10-05",
              "end_date": "2025-10-06",
              "total_cost": 4358.0,
              "currency": "INR",
              "hotels_count": 1,
              "single_hotel": true,
              "hotel_assignments": [
                {
                  "hotel_id": 294,
                  "hotel_name": "Villa Reisya & guest house reisya",
                  "assignment_date": "2025-10-05",
                  "price": 2179.0,
                  "currency": "INR",
                  "room_type": null,
                  "selection_reason": "cheapest_day"
                },
                {
                  "hotel_id": 294,
                  "hotel_name": "Villa Reisya & guest house reisya",
                  "assignment_date": "2025-10-06",
                  "price": 2179.0,
                  "currency": "INR",
                  "room_type": null,
                  "selection_reason": "cheapest_day"
                }
              ]
            }
          ],
          "total_cost": 4358.0,
          "currency": "INR",
          "total_nights": 2,
          "start_date": "2025-10-05",
          "end_date": "2025-10-06",
          "optimization_score": null,
          "alternatives_generated": 1,
          "single_hotel_destinations": 1,
          "date_context": null
        },
        {
          "search_type": "ranges",
          "label": "range_optimized",
          "destinations": [
            {
              "destination_id": 1,
              "destination_name": "Destination 1",
              "area_id": null,
              "area_name": null,
              "order": 0,
              "nights": 2,
              "start_date": "2025-10-06",
              "end_date": "2025-10-07",
              "total_cost": 4358.0,
              "currency": "INR",
              "hotels_count": 1,
              "single_hotel": true,
              "hotel_assignments": [
                {
                  "hotel_id": 294,
                  "hotel_name": "Villa Reisya & guest house reisya",
                  "assignment_date": "2025-10-06",
                  "price": 2179.0,
                  "currency": "INR",
                  "room_type": null,
                  "selection_reason": "cheapest_day"
                },
                {
                  "hotel_id": 294,
                  "hotel_name": "Villa Reisya & guest house reisya",
                  "assignment_date": "2025-10-07",
                  "price": 2179.0,
                  "currency": "INR",
                  "room_type": null,
                  "selection_reason": "cheapest_day"
                }
              ]
            }
          ],
          "total_cost": 4358.0,
          "currency": "INR",
          "total_nights": 2,
          "start_date": "2025-10-06",
          "end_date": "2025-10-07",
          "optimization_score": null,
          "alternatives_generated": 1,
          "single_hotel_destinations": 1,
          "date_context": null
        },
        {
          "search_type": "ranges",
          "label": "range_optimized",
          "destinations": [
            {
              "destination_id": 1,
              "destination_name": "Destination 1",
              "area_id": null,
              "area_name": null,
              "order": 0,
              "nights": 2,
              "start_date": "2025-10-07",
              "end_date": "2025-10-08",
              "total_cost": 4358.0,
              "currency": "INR",
              "hotels_count": 1,
              "single_hotel": true,
              "hotel_assignments": [
                {
                  "hotel_id": 294,
                  "hotel_name": "Villa Reisya & guest house reisya",
                  "assignment_date": "2025-10-07",
                  "price": 2179.0,
                  "currency": "INR",
                  "room_type": null,
                  "selection_reason": "cheapest_day"
                },
                {
                  "hotel_id": 294,
                  "hotel_name": "Villa Reisya & guest house reisya",
                  "assignment_date": "2025-10-08",
                  "price": 2179.0,
                  "currency": "INR",
                  "room_type": null,
                  "selection_reason": "cheapest_day"
                }
              ]
            }
          ],
          "total_cost": 4358.0,
          "currency": "INR",
          "total_nights": 2,
          "start_date": "2025-10-07",
          "end_date": "2025-10-08",
          "optimization_score": null,
          "alternatives_generated": 1,
          "single_hotel_destinations": 1,
          "date_context": null
        }
      ]
    },
    "fixed_dates": {
      "results": [
        {
          "search_type": "fixed_dates",
          "label": "fixed_date",
          "destinations": [
            {
              "destination_id": 1,
              "destination_name": "Destination 1",
              "area_id": null,
              "area_name": null,
              "order": 0,
              "nights": 2,
              "start_date": "2025-10-08",
              "end_date": "2025-10-09",
              "total_cost": 5499.0,
              "currency": "INR",
              "hotels_count": 2,
              "single_hotel": false,
              "hotel_assignments": [
                {
                  "hotel_id": 294,
                  "hotel_name": "Villa Reisya & guest house reisya",
                  "assignment_date": "2025-10-08",
                  "price": 2179.0,
                  "currency": "INR",
                  "room_type": null,
                  "selection_reason": "cheapest_day"
                },
                {
                  "hotel_id": 284,
                  "hotel_name": "The Crystal Luxury Bay Resort Nusa Dua - Bali",
                  "assignment_date": "2025-10-09",
                  "price": 3320.0,
                  "currency": "INR",
                  "room_type": null,
                  "selection_reason": "cheapest_day"
                }
              ]
            }
          ],
          "total_cost": 5499.0,
          "currency": "INR",
          "total_nights": 2,
          "start_date": "2025-10-08",
          "end_date": "2025-10-09",
          "optimization_score": null,
          "alternatives_generated": 1,
          "single_hotel_destinations": 0,
          "date_context": null
        },
        {
          "search_type": "fixed_dates",
          "label": "fixed_date",
          "destinations": [
            {
              "destination_id": 1,
              "destination_name": "Destination 1",
              "area_id": null,
              "area_name": null,
              "order": 0,
              "nights": 2,
              "start_date": "2025-10-12",
              "end_date": "2025-10-13",
              "total_cost": 4358.0,
              "currency": "INR",
              "hotels_count": 1,
              "single_hotel": true,
              "hotel_assignments": [
                {
                  "hotel_id": 294,
                  "hotel_name": "Villa Reisya & guest house reisya",
                  "assignment_date": "2025-10-12",
                  "price": 2179.0,
                  "currency": "INR",
                  "room_type": null,
                  "selection_reason": "cheapest_day"
                },
                {
                  "hotel_id": 294,
                  "hotel_name": "Villa Reisya & guest house reisya",
                  "assignment_date": "2025-10-13",
                  "price": 2179.0,
                  "currency": "INR",
                  "room_type": null,
                  "selection_reason": "cheapest_day"
                }
              ]
            }
          ],
          "total_cost": 4358.0,
          "currency": "INR",
          "total_nights": 2,
          "start_date": "2025-10-12",
          "end_date": "2025-10-13",
          "optimization_score": null,
          "alternatives_generated": 1,
          "single_hotel_destinations": 1,
          "date_context": null
        }
      ]
    },
    "best_itinerary": {
      "search_type": "fixed_dates",
      "label": "October 2025_start",
      "destinations": [
        {
          "destination_id": 1,
          "destination_name": "Destination 1",
          "area_id": null,
          "area_name": null,
          "order": 0,
          "nights": 2,
          "start_date": "2025-10-05",
          "end_date": "2025-10-06",
          "total_cost": 4358.0,
          "currency": "INR",
          "hotels_count": 1,
          "single_hotel": true,
          "hotel_assignments": [
            {
              "hotel_id": 294,
              "hotel_name": "Villa Reisya & guest house reisya",
              "assignment_date": "2025-10-05",
              "price": 2179.0,
              "currency": "INR",
              "room_type": null,
              "selection_reason": "cheapest_day"
            },
            {
              "hotel_id": 294,
              "hotel_name": "Villa Reisya & guest house reisya",
              "assignment_date": "2025-10-06",
              "price": 2179.0,
              "currency": "INR",
              "room_type": null,
              "selection_reason": "cheapest_day"
            }
          ]
        }
      ],
      "total_cost": 4358.0,
      "currency": "INR",
      "total_nights": 2,
      "start_date": "2025-10-05",
      "end_date": "2025-10-06",
      "optimization_score": null,
      "alternatives_generated": 1,
      "single_hotel_destinations": 1,
      "date_context": null
    },
    "metadata": {
      "processing_time_ms": 177,
      "cache_hit": false,
      "hotels_searched": 0,
      "price_queries": 0,
      "alternatives_generated": 6,
      "best_cost_found": 4358.0,
      "user_authenticated": false,
      "clean_structure_used": true,
      "nearest_option_shown": null
    },
    "filters_applied": {
      "search_types": ["all"],
      "custom": true,
      "currency": "INR",
      "guests": {
        "adults": 1,
        "children": 0,
        "child_ages": null
      }
    },
    "message": "Found 6 total itinerary options across 1 search types"
  },
  "user_tier": "admin"
}
```

---

## 5. Multi-Destination Custom Search

Optimization with multiple destinations and hotel switching enabled.

```bash
curl -X POST "http://localhost:8006/api/v1/itineraries/optimize" \
-H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIzIiwiZXhwIjoxNzkxMDE3MTMzLCJ0eXBlIjoiYWNjZXNzIn0.XAL7-FbTvS82sQVk18iyCfBXFbTkpr1m7C7BVnNwtgk" \
-H "Content-Type: application/json" \
-d '{
  "custom": true,
  "search_types": ["normal"],
  "destinations": [
    {"destination_id": 1, "nights": 2},
    {"destination_id": 3, "nights": 2}
  ],
  "global_date_range": {
    "start": "2025-10-01",
    "end": "2025-10-20"
  },
  "currency": "INR",
  "hotel_change": true
}'
```

**Response:**
```json
{
  "data": {
    "success": true,
    "request_hash": "f1cde16177f729ccab6530ab89a7a6581ce2e53cb2a9efb8675d673ea0acb9d7",
    "normal": {
      "monthly_options": [
        {
          "month": "October 2025",
          "start_month": {
            "search_type": "fixed_dates",
            "label": "October 2025_start",
            "destinations": [
              {
                "destination_id": 1,
                "destination_name": "Destination 1",
                "area_id": null,
                "area_name": null,
                "order": 0,
                "nights": 2,
                "start_date": "2025-10-05",
                "end_date": "2025-10-06",
                "total_cost": 4358.0,
                "currency": "INR",
                "hotels_count": 1,
                "single_hotel": true,
                "hotel_assignments": [
                  {
                    "hotel_id": 294,
                    "hotel_name": "Villa Reisya & guest house reisya",
                    "assignment_date": "2025-10-05",
                    "price": 2179.0,
                    "currency": "INR",
                    "room_type": null,
                    "selection_reason": "cheapest_day"
                  },
                  {
                    "hotel_id": 294,
                    "hotel_name": "Villa Reisya & guest house reisya",
                    "assignment_date": "2025-10-06",
                    "price": 2179.0,
                    "currency": "INR",
                    "room_type": null,
                    "selection_reason": "cheapest_day"
                  }
                ]
              },
              {
                "destination_id": 3,
                "destination_name": "Destination 3",
                "area_id": null,
                "area_name": null,
                "order": 1,
                "nights": 2,
                "start_date": "2025-10-07",
                "end_date": "2025-10-08",
                "total_cost": 1050.0,
                "currency": "INR",
                "hotels_count": 1,
                "single_hotel": true,
                "hotel_assignments": [
                  {
                    "hotel_id": 397,
                    "hotel_name": "Sun-n-Sand Hotel",
                    "assignment_date": "2025-10-07",
                    "price": 525.0,
                    "currency": "INR",
                    "room_type": null,
                    "selection_reason": "cheapest_day"
                  },
                  {
                    "hotel_id": 397,
                    "hotel_name": "Sun-n-Sand Hotel",
                    "assignment_date": "2025-10-08",
                    "price": 525.0,
                    "currency": "INR",
                    "room_type": null,
                    "selection_reason": "cheapest_day"
                  }
                ]
              }
            ],
            "total_cost": 5408.0,
            "currency": "INR",
            "total_nights": 4,
            "start_date": "2025-10-05",
            "end_date": "2025-10-08",
            "optimization_score": null,
            "alternatives_generated": 1,
            "single_hotel_destinations": 2,
            "date_context": null
          },
          "mid_month": {
            "search_type": "fixed_dates",
            "label": "October 2025_mid",
            "destinations": [
              {
                "destination_id": 1,
                "destination_name": "Destination 1",
                "area_id": null,
                "area_name": null,
                "order": 0,
                "nights": 2,
                "start_date": "2025-10-15",
                "end_date": "2025-10-16",
                "total_cost": 4358.0,
                "currency": "INR",
                "hotels_count": 1,
                "single_hotel": true,
                "hotel_assignments": [
                  {
                    "hotel_id": 294,
                    "hotel_name": "Villa Reisya & guest house reisya",
                    "assignment_date": "2025-10-15",
                    "price": 2179.0,
                    "currency": "INR",
                    "room_type": null,
                    "selection_reason": "cheapest_day"
                  },
                  {
                    "hotel_id": 294,
                    "hotel_name": "Villa Reisya & guest house reisya",
                    "assignment_date": "2025-10-16",
                    "price": 2179.0,
                    "currency": "INR",
                    "room_type": null,
                    "selection_reason": "cheapest_day"
                  }
                ]
              },
              {
                "destination_id": 3,
                "destination_name": "Destination 3",
                "area_id": null,
                "area_name": null,
                "order": 1,
                "nights": 2,
                "start_date": "2025-10-17",
                "end_date": "2025-10-18",
                "total_cost": 842.0,
                "currency": "INR",
                "hotels_count": 1,
                "single_hotel": true,
                "hotel_assignments": [
                  {
                    "hotel_id": 397,
                    "hotel_name": "Sun-n-Sand Hotel",
                    "assignment_date": "2025-10-17",
                    "price": 421.0,
                    "currency": "INR",
                    "room_type": null,
                    "selection_reason": "cheapest_day"
                  },
                  {
                    "hotel_id": 397,
                    "hotel_name": "Sun-n-Sand Hotel",
                    "assignment_date": "2025-10-18",
                    "price": 421.0,
                    "currency": "INR",
                    "room_type": null,
                    "selection_reason": "cheapest_day"
                  }
                ]
              }
            ],
            "total_cost": 5200.0,
            "currency": "INR",
            "total_nights": 4,
            "start_date": "2025-10-15",
            "end_date": "2025-10-18",
            "optimization_score": null,
            "alternatives_generated": 1,
            "single_hotel_destinations": 2,
            "date_context": null
          },
          "end_month": null
        }
      ]
    },
    "ranges": null,
    "fixed_dates": null,
    "best_itinerary": {
      "search_type": "fixed_dates",
      "label": "October 2025_mid",
      "destinations": [
        {
          "destination_id": 1,
          "destination_name": "Destination 1",
          "area_id": null,
          "area_name": null,
          "order": 0,
          "nights": 2,
          "start_date": "2025-10-15",
          "end_date": "2025-10-16",
          "total_cost": 4358.0,
          "currency": "INR",
          "hotels_count": 1,
          "single_hotel": true,
          "hotel_assignments": [
            {
              "hotel_id": 294,
              "hotel_name": "Villa Reisya & guest house reisya",
              "assignment_date": "2025-10-15",
              "price": 2179.0,
              "currency": "INR",
              "room_type": null,
              "selection_reason": "cheapest_day"
            },
            {
              "hotel_id": 294,
              "hotel_name": "Villa Reisya & guest house reisya",
              "assignment_date": "2025-10-16",
              "price": 2179.0,
              "currency": "INR",
              "room_type": null,
              "selection_reason": "cheapest_day"
            }
          ]
        },
        {
          "destination_id": 3,
          "destination_name": "Destination 3",
          "area_id": null,
          "area_name": null,
          "order": 1,
          "nights": 2,
          "start_date": "2025-10-17",
          "end_date": "2025-10-18",
          "total_cost": 842.0,
          "currency": "INR",
          "hotels_count": 1,
          "single_hotel": true,
          "hotel_assignments": [
            {
              "hotel_id": 397,
              "hotel_name": "Sun-n-Sand Hotel",
              "assignment_date": "2025-10-17",
              "price": 421.0,
              "currency": "INR",
              "room_type": null,
              "selection_reason": "cheapest_day"
            },
            {
              "hotel_id": 397,
              "hotel_name": "Sun-n-Sand Hotel",
              "assignment_date": "2025-10-18",
              "price": 421.0,
              "currency": "INR",
              "room_type": null,
              "selection_reason": "cheapest_day"
            }
          ]
        }
      ],
      "total_cost": 5200.0,
      "currency": "INR",
      "total_nights": 4,
      "start_date": "2025-10-15",
      "end_date": "2025-10-18",
      "optimization_score": null,
      "alternatives_generated": 1,
      "single_hotel_destinations": 2,
      "date_context": null
    },
    "metadata": {
      "processing_time_ms": 211,
      "cache_hit": false,
      "hotels_searched": 0,
      "price_queries": 0,
      "alternatives_generated": 2,
      "best_cost_found": 5200.0,
      "user_authenticated": false,
      "clean_structure_used": true,
      "nearest_option_shown": null
    },
    "filters_applied": {
      "search_types": ["normal"],
      "custom": true,
      "currency": "INR",
      "guests": {
        "adults": 1,
        "children": 0,
        "child_ages": null
      }
    },
    "message": "Found 2 total itinerary options across 1 search types"
  },
  "user_tier": "admin"
}
```

---

## Key Features Demonstrated

### 🎯 **Optimization Results**
- **Single destination**: ₹6,384 - ₹6,946 for 3 nights
- **Multi-destination**: ₹5,200 for 4 nights total (2 destinations)
- **Hotel switching**: Automatic optimization between hotels for best prices
- **Single hotel preference**: When possible, use same hotel for entire stay

### 🏨 **Hotel Examples Found**
- **Villa Reisya & guest house reisya**: ₹2,179/night (most common, budget option)
- **The Crystal Luxury Bay Resort**: ₹3,320/night (luxury option)
- **Villa Metimpal**: ₹1,920/night (budget alternative)
- **Sun-n-Sand Hotel** (Mumbai): ₹421-525/night (very budget-friendly)

### 📊 **Search Type Capabilities**
- **Normal**: Monthly options (start/mid/end month)
- **Ranges**: Sliding window across date ranges
- **Fixed Dates**: Exact start date optimization
- **All**: Combines all search types for comprehensive results

### 🔧 **API Features**
- **Authentication**: 1-year JWT tokens for admin users
- **Currency Support**: INR pricing with local database
- **Caching**: Request hashing and cache hit detection
- **Multi-destination**: Consecutive destination visits
- **Hotel Optimization**: Single hotel vs. hotel switching strategies

---

## Environment Setup Notes

- **Database**: Local Docker PostgreSQL with 816 hotels and 17,842 price records
- **Currency**: Using INR for price data (local database)
- **Authentication**: Admin users get 365-day tokens automatically
- **Destinations Available**: 
  - Destination 1: Bali (667 hotels)
  - Destination 3: Mumbai (117 hotels)

---

*Generated on: 2025-10-03*  
*API Version**: v1.0.0*  
*Authentication**: JWT Bearer Token*