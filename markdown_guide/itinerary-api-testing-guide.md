# Itinerary Optimization API - Testing Guide

A comprehensive testing guide for the multi-destination itinerary optimization system with real examples, curl commands, and step-by-step testing procedures.

## 🎯 Overview

This guide helps you test the new itinerary optimization API that finds the best hotel prices across multiple destinations with different search strategies. The system optimizes consecutive destination visits while minimizing accommodation costs.

### Current Test Destinations
- **Bali (Province)** 🏝️
  - **Ubud (Area)** - Cultural heart of Bali
  - **Nusa Dua (Area)** - Upscale resort area
- **Gili Trawangan (Island)** 🏖️
- **Mumbai (City)** 🏙️

---

## 🚀 Quick Start Testing

### 1. Basic Normal Search (Start/Mid/End Month)
```bash
curl -X POST "http://localhost:8000/api/v1/itineraries/optimize" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "custom": false,
    "destinations": [
      {
        "destination_id": 5,
        "area_id": 1,
        "nights": 3
      },
      {
        "destination_id": 5,
        "area_id": 2,
        "nights": 2
      }
    ],
    "global_date_range": {
      "start": "2025-12-01",
      "end": "2025-12-31"
    },
    "guests": {
      "adults": 2,
      "children": 0
    },
    "currency": "USD"
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "request_hash": "a1b2c3d4e5f6...",
  "normal": {
    "start_month": {
      "search_type": "normal",
      "label": "start_month",
      "destinations": [
        {
          "destination_id": 5,
          "destination_name": "Bali",
          "area_id": 1,
          "area_name": "Ubud",
          "nights": 3,
          "start_date": "2025-12-01",
          "end_date": "2025-12-03",
          "total_cost": 225.00,
          "single_hotel": true,
          "hotel_assignments": [...]
        }
      ],
      "total_cost": 450.00,
      "currency": "USD",
      "total_nights": 5
    },
    "mid_month": {...},
    "end_month": {...}
  },
  "best_itinerary": {...},
  "metadata": {
    "processing_time_ms": 1250,
    "cache_hit": false,
    "alternatives_generated": 12
  }
}
```

### 2. Advanced Multi-Mode Search
```bash
curl -X POST "http://localhost:8000/api/v1/itineraries/optimize" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "custom": true,
    "search_types": ["normal", "ranges"],
    "destinations": [
      {
        "destination_id": 5,
        "area_id": 1,
        "nights": 2
      },
      {
        "destination_id": 5,
        "area_id": 2,
        "nights": 3
      }
    ],
    "global_date_range": {
      "start": "2025-12-01",
      "end": "2025-12-31"
    },
    "ranges": [
      {
        "start": "2025-12-01",
        "end": "2025-12-15"
      },
      {
        "start": "2025-12-15",
        "end": "2025-12-31"
      }
    ],
    "guests": {
      "adults": 2,
      "children": 1,
      "child_ages": [8]
    },
    "currency": "USD",
    "top_k": 3
  }'
```

---

## 📋 Comprehensive Test Scenarios

### Test Case 1: Bali Multi-Area Trip
**Scenario:** 7-day trip covering Ubud and Nusa Dua in Bali

```bash
curl -X POST "http://localhost:8000/api/v1/itineraries/optimize" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "custom": true,
    "search_types": ["all"],
    "destinations": [
      {
        "destination_id": 5,
        "area_id": 1,
        "nights": 4
      },
      {
        "destination_id": 5,
        "area_id": 2,
        "nights": 3
      }
    ],
    "global_date_range": {
      "start": "2025-12-01",
      "end": "2025-12-31"
    },
    "ranges": [
      {"start": "2025-12-01", "end": "2025-12-10"},
      {"start": "2025-12-15", "end": "2025-12-25"}
    ],
    "fixed_dates": ["2025-12-05", "2025-12-20"],
    "guests": {"adults": 2},
    "currency": "USD",
    "top_k": 2
  }'
```

### Test Case 2: Multi-Destination Island Hopping
**Scenario:** Bali to Gili Trawangan island hopping

```bash
curl -X POST "http://localhost:8000/api/v1/itineraries/optimize" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "custom": false,
    "destinations": [
      {
        "destination_id": 5,
        "area_id": 1,
        "nights": 3
      },
      {
        "destination_id": 4,
        "nights": 4
      }
    ],
    "global_date_range": {
      "start": "2025-12-10",
      "end": "2025-12-25"
    },
    "guests": {
      "adults": 4,
      "children": 2,
      "child_ages": [10, 12]
    },
    "currency": "USD"
  }'
```

### Test Case 3: Business Trip with Fixed Dates
**Scenario:** Mumbai business trip with specific conference dates

```bash
curl -X POST "http://localhost:8000/api/v1/itineraries/optimize" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "custom": true,
    "search_types": ["fixed_dates"],
    "destinations": [
      {
        "destination_id": 6,
        "nights": 3
      }
    ],
    "global_date_range": {
      "start": "2025-12-15",
      "end": "2025-12-25"
    },
    "fixed_dates": ["2025-12-16", "2025-12-20"],
    "guests": {"adults": 1},
    "currency": "USD"
  }'
```

### Test Case 4: Date Range Optimization
**Scenario:** Flexible dates with specific preferred periods

```bash
curl -X POST "http://localhost:8000/api/v1/itineraries/optimize" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "custom": true,
    "search_types": ["ranges"],
    "destinations": [
      {
        "destination_id": 5,
        "area_id": 2,
        "nights": 5
      }
    ],
    "global_date_range": {
      "start": "2025-12-01",
      "end": "2025-12-31"
    },
    "ranges": [
      {"start": "2025-12-01", "end": "2025-12-07"},
      {"start": "2025-12-08", "end": "2025-12-14"},
      {"start": "2025-12-15", "end": "2025-12-21"},
      {"start": "2025-12-22", "end": "2025-12-28"}
    ],
    "guests": {"adults": 2},
    "currency": "USD",
    "top_k": 5
  }'
```

---

## 🔄 Additional API Testing

### Compare All Search Types
```bash
curl -X POST "http://localhost:8000/api/v1/itineraries/compare" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "destinations": [
      {"destination_id": 5, "area_id": 1, "nights": 2},
      {"destination_id": 5, "area_id": 2, "nights": 2}
    ],
    "global_date_range": {
      "start": "2025-12-01",
      "end": "2025-12-20"
    },
    "ranges": [
      {"start": "2025-12-01", "end": "2025-12-10"},
      {"start": "2025-12-11", "end": "2025-12-20"}
    ],
    "fixed_dates": ["2025-12-05", "2025-12-15"],
    "guests": {"adults": 2},
    "currency": "USD"
  }'
```

### Get Optimization History
```bash
curl -X GET "http://localhost:8000/api/v1/itineraries/history?limit=5&offset=0" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Retrieve Cached Result
```bash
curl -X GET "http://localhost:8000/api/v1/itineraries/cached/a1b2c3d4e5f6..." \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Clear Specific Cache
```bash
curl -X DELETE "http://localhost:8000/api/v1/itineraries/cache/a1b2c3d4e5f6..." \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 🎯 Expected Response Patterns

### Successful Normal Search Response
```json
{
  "success": true,
  "request_hash": "sha256_hash_here",
  "normal": {
    "start_month": {
      "search_type": "normal",
      "label": "start_month",
      "destinations": [
        {
          "destination_id": 5,
          "destination_name": "Bali", 
          "area_id": 1,
          "area_name": "Ubud",
          "order": 0,
          "nights": 3,
          "start_date": "2025-12-01",
          "end_date": "2025-12-03",
          "total_cost": 225.00,
          "currency": "USD",
          "hotels_count": 1,
          "single_hotel": true,
          "hotel_assignments": [
            {
              "hotel_id": 15,
              "hotel_name": "Ubud Luxury Resort",
              "assignment_date": "2025-12-01",
              "price": 75.00,
              "currency": "USD",
              "selection_reason": "single_hotel"
            },
            {
              "hotel_id": 15,
              "hotel_name": "Ubud Luxury Resort", 
              "assignment_date": "2025-12-02",
              "price": 75.00,
              "currency": "USD",
              "selection_reason": "single_hotel"
            },
            {
              "hotel_id": 15,
              "hotel_name": "Ubud Luxury Resort",
              "assignment_date": "2025-12-03", 
              "price": 75.00,
              "currency": "USD",
              "selection_reason": "single_hotel"
            }
          ]
        }
      ],
      "total_cost": 450.00,
      "currency": "USD",
      "total_nights": 5,
      "start_date": "2025-12-01",
      "end_date": "2025-12-05",
      "single_hotel_destinations": 2
    },
    "mid_month": { /* Similar structure */ },
    "end_month": { /* Similar structure */ }
  },
  "best_itinerary": {
    "search_type": "normal",
    "label": "start_month",
    "total_cost": 450.00,
    "currency": "USD"
  },
  "metadata": {
    "processing_time_ms": 1250,
    "cache_hit": false,
    "hotels_searched": 104,
    "alternatives_generated": 15,
    "best_cost_found": 450.00
  },
  "filters_applied": {
    "search_types": ["normal"],
    "custom": false,
    "currency": "USD",
    "guests": {"adults": 2, "children": 0}
  },
  "message": "Found 3 itinerary options"
}
```

### Multi-Search Type Response
```json
{
  "success": true,
  "request_hash": "sha256_hash_here",
  "normal": { /* Normal search results */ },
  "ranges": {
    "results": [
      {
        "search_type": "ranges",
        "label": "range_optimized",
        "total_cost": 420.00,
        "currency": "USD",
        "date_context": {
          "range_start": "2025-12-01",
          "range_end": "2025-12-15"
        }
      }
    ]
  },
  "fixed_dates": {
    "results": [
      {
        "search_type": "fixed_dates", 
        "label": "fixed_date",
        "total_cost": 480.00,
        "currency": "USD",
        "date_context": {
          "fixed_start_date": "2025-12-05"
        }
      }
    ]
  },
  "best_itinerary": {
    "search_type": "ranges",
    "total_cost": 420.00
  },
  "metadata": {
    "processing_time_ms": 2750,
    "alternatives_generated": 45
  },
  "message": "Found 8 total itinerary options across 3 search types"
}
```

### Comparison Analysis Response
```json
{
  "success": true,
  "optimization_result": { /* Full optimization result */ },
  "comparison_analysis": {
    "search_types_executed": ["normal", "ranges", "fixed_dates"],
    "cost_comparison": {
      "normal": {
        "count": 3,
        "min_cost": 450.00,
        "max_cost": 520.00,
        "avg_cost": 485.00
      },
      "ranges": {
        "count": 6,
        "min_cost": 420.00,
        "max_cost": 550.00,
        "avg_cost": 465.00
      },
      "fixed_dates": {
        "count": 2,
        "min_cost": 480.00,
        "max_cost": 500.00,
        "avg_cost": 490.00
      }
    },
    "best_overall": {
      "search_type": "ranges",
      "label": "range_optimized",
      "total_cost": 420.00,
      "currency": "USD",
      "start_date": "2025-12-03",
      "end_date": "2025-12-07"
    },
    "recommendations": [
      "'ranges' search offers the lowest cost option",
      "Consider flexible dates for better pricing"
    ]
  },
  "message": "Search type comparison completed successfully"
}
```

---

## ❌ Error Response Examples

### Validation Errors
```json
{
  "success": false,
  "errors": [
    {
      "type": "validation_error",
      "message": "Total nights (10) exceeds date range (7 days)",
      "details": {
        "total_nights": 10,
        "available_days": 7
      }
    }
  ],
  "request_hash": null
}
```

### Missing Parameters
```json
{
  "success": false,
  "errors": [
    {
      "type": "parameter_error",
      "message": "ranges parameter required for ranges search",
      "details": {
        "search_types": ["ranges"],
        "missing_parameter": "ranges"
      }
    }
  ]
}
```

### No Hotel Solutions Found
```json
{
  "success": false,
  "errors": [
    {
      "type": "optimization_error", 
      "message": "No hotel solutions found for destination 999",
      "details": {
        "destination_id": 999,
        "date_range": "2025-12-01 to 2025-12-05"
      }
    }
  ]
}
```

---

## 🧪 Testing Checklist

### Basic Functionality Tests
- [ ] Normal search (custom=false)
- [ ] Single destination optimization
- [ ] Multi-destination consecutive visits
- [ ] Date constraint validation
- [ ] Guest configuration validation

### Advanced Search Mode Tests  
- [ ] Ranges search with multiple ranges
- [ ] Fixed dates search with exact dates
- [ ] Combined search types
- [ ] "All" search type execution

### Hotel Optimization Tests
- [ ] Single hotel preference (when cost effective)
- [ ] Multi-hotel cheapest daily selection
- [ ] Cost comparison and selection logic
- [ ] Different destination area combinations

### Performance & Caching Tests
- [ ] Response times under 3 seconds
- [ ] Cache hit/miss functionality  
- [ ] Repeated request caching
- [ ] Cache invalidation

### API Integration Tests
- [ ] Authentication requirements
- [ ] Error handling and validation
- [ ] Response format consistency
- [ ] History and cache management endpoints

### Edge Cases Tests
- [ ] Single night stays
- [ ] Long duration stays (20+ nights)
- [ ] Peak season date ranges
- [ ] Large guest groups (8+ people)
- [ ] Different currencies

---

## 📊 Performance Benchmarks

### Expected Response Times
| Search Type | Hotels Available | Expected Time | With Cache |
|-------------|------------------|---------------|------------|
| Normal (3 options) | 100+ | < 1.5s | < 100ms |
| Ranges (5 ranges) | 100+ | < 2.5s | < 150ms |
| Fixed Dates (3 dates) | 100+ | < 1.2s | < 80ms |
| All Types Combined | 100+ | < 3.5s | < 200ms |

### Success Rate Targets
- **Hotel Solutions Found**: > 95% for tracked destinations
- **Single Hotel Coverage**: > 60% for 2-4 night stays  
- **Cost Optimization**: < 5% variance from true optimal
- **Cache Hit Rate**: > 80% for repeated requests

---

## 🐛 Common Issues & Solutions

### Issue: "No hotel solutions found"
**Cause:** No price data for requested dates/destinations
**Solution:** 
1. Verify destination has tracking enabled
2. Check if background hotel search jobs are running
3. Ensure dates are within data collection range (next 60 days)

### Issue: "Total nights exceeds date range"
**Cause:** Mathematical constraint violation
**Solution:**
```json
// Ensure: sum(nights) <= (end_date - start_date + 1)
{
  "destinations": [
    {"nights": 3},  // Total: 5 nights
    {"nights": 2}   
  ],
  "global_date_range": {
    "start": "2025-12-01",
    "end": "2025-12-06"  // 6 days available ✓
  }
}
```

### Issue: High response times
**Cause:** Large search space or cold cache
**Solutions:**
- Reduce `top_k` parameter to 1-3
- Use more specific search types instead of "all"
- Enable caching (default: true)
- Limit date ranges to < 30 days

### Issue: Cache misses for similar requests
**Cause:** Parameter ordering or formatting differences
**Solution:** Use identical parameter structure:
```json
// These are different requests due to parameter ordering
{"destinations": [{"destination_id": 5, "nights": 3}]}
{"destinations": [{"nights": 3, "destination_id": 5}]}
```

---

## 🔄 Next Steps

After setting up hotel data with background jobs:

1. **Test Basic Functionality**
   - Start with simple normal searches
   - Verify hotel assignments and pricing
   - Check cache behavior

2. **Test Advanced Features**
   - Multi-mode searches
   - Complex date range scenarios  
   - Performance under load

3. **Integration Testing**
   - Frontend integration
   - Mobile app integration
   - Third-party booking systems

4. **Performance Optimization**
   - Monitor response times
   - Optimize database queries
   - Tune cache settings

Ready to start testing the optimized itinerary system! 🚀