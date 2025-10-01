# Itinerary Optimization API - Testing Guide

A comprehensive testing guide for the multi-destination itinerary optimization system with real examples, curl commands, and step-by-step testing procedures.

## 🎯 Overview

This guide helps you test the optimized itinerary API that finds the best hotel prices across multiple destinations with different search strategies. The system now uses a **clean month-grouped structure** with `monthly_options` and supports anonymous user access with intelligent data filtering.

### 🆕 Key Improvements
- **Clean Month-Grouped Structure**: Replaced legacy start_month/mid_month/end_month with unified `monthly_options`
- **Anonymous User Support**: Smart filtering shows single nearest option for unauthenticated users
- **Enhanced Price Tracking**: Fixed date logic with proper price_date vs search_date handling
- **Improved Hotel Search**: Better star rating extraction and comprehensive debug logging
- **Optimized Performance**: Fixed ORM queries and added intelligent caching

### Current Test Destinations
- **Bali (Province)** 🏝️
  - **Ubud (Area)** - Cultural heart of Bali
  - **Nusa Dua (Area)** - Upscale resort area
- **Gili Trawangan (Island)** 🏖️
- **Mumbai (City)** 🏙️

---

## 🚀 Quick Start Testing

### 1. Basic Normal Search (Monthly Options - Clean Structure)
```bash
# Authenticated user - gets all monthly options
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
    "currency": "INR"
  }'
```

### 1.1 Anonymous User Test (Single Nearest Option)
```bash
# Anonymous user - gets only single nearest option
curl -X POST "http://localhost:8000/api/v1/itineraries/optimize" \
  -H "Content-Type: application/json" \
  -d '{
    "custom": false,
    "destinations": [
      {
        "destination_id": 5,
        "area_id": 1,
        "nights": 3
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
    "currency": "INR"
  }'
```

**Expected Response (Authenticated User):**
```json
{
  "success": true,
  "request_hash": "a1b2c3d4e5f6...",
  "normal": {
    "monthly_options": [
      {
        "search_type": "normal",
        "label": "December 2025",
        "start_month": "2025-12-01",
        "destinations": [
          {
            "destination_id": 5,
            "destination_name": "Bali",
            "area_id": 1,
            "area_name": "Ubud",
            "nights": 3,
            "start_date": "2025-12-01",
            "end_date": "2025-12-03",
            "total_cost": 15750.00,
            "currency": "INR",
            "single_hotel": true,
            "hotel_assignments": [...]
          }
        ],
        "total_cost": 31500.00,
        "currency": "INR",
        "total_nights": 5
      },
      {
        "search_type": "normal", 
        "label": "December 2025 Mid",
        "start_month": "2025-12-15",
        "destinations": [...],
        "total_cost": 28800.00,
        "currency": "INR"
      },
      {
        "search_type": "normal",
        "label": "December 2025 End", 
        "start_month": "2025-12-25",
        "destinations": [...],
        "total_cost": 33200.00,
        "currency": "INR"
      }
    ]
  },
  "best_itinerary": {
    "search_type": "normal",
    "label": "December 2025 Mid",
    "total_cost": 28800.00,
    "currency": "INR"
  },
  "metadata": {
    "processing_time_ms": 1250,
    "cache_hit": false,
    "alternatives_generated": 12,
    "user_authenticated": true
  }
}
```

**Expected Response (Anonymous User):**
```json
{
  "success": true,
  "request_hash": "a1b2c3d4e5f6...",
  "normal": {
    "monthly_options": [
      {
        "search_type": "normal",
        "label": "December 2025 Mid",
        "start_month": "2025-12-15",
        "destinations": [
          {
            "destination_id": 5,
            "destination_name": "Bali",
            "area_id": 1,
            "area_name": "Ubud",
            "nights": 3,
            "start_date": "2025-12-15",
            "end_date": "2025-12-17",
            "total_cost": 14400.00,
            "currency": "INR",
            "single_hotel": true,
            "hotel_assignments": [...]
          }
        ],
        "total_cost": 14400.00,
        "currency": "INR",
        "total_nights": 3,
        "message": "Sign in to see all available options"
      }
    ]
  },
  "best_itinerary": {
    "search_type": "normal",
    "label": "December 2025 Mid", 
    "total_cost": 14400.00,
    "currency": "INR"
  },
  "metadata": {
    "processing_time_ms": 850,
    "cache_hit": false,
    "alternatives_generated": 1,
    "user_authenticated": false,
    "nearest_option_shown": true
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
    "currency": "INR",
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
    "currency": "INR",
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
    "currency": "INR"
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
    "currency": "INR"
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
    "currency": "INR",
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
    "currency": "INR"
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

### Successful Normal Search Response (New Clean Structure)
```json
{
  "success": true,
  "request_hash": "sha256_hash_here",
  "normal": {
    "monthly_options": [
      {
        "search_type": "normal",
        "label": "December 2025",
        "start_month": "2025-12-01",
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
          "total_cost": 15750.00,
          "currency": "INR",
          "hotels_count": 1,
          "single_hotel": true,
          "hotel_assignments": [
            {
              "hotel_id": 15,
              "hotel_name": "Ubud Luxury Resort",
              "assignment_date": "2025-12-01",
              "price": 5250.00,
              "currency": "INR",
              "selection_reason": "single_hotel"
            },
            {
              "hotel_id": 15,
              "hotel_name": "Ubud Luxury Resort", 
              "assignment_date": "2025-12-02",
              "price": 5250.00,
              "currency": "INR",
              "selection_reason": "single_hotel"
            },
            {
              "hotel_id": 15,
              "hotel_name": "Ubud Luxury Resort",
              "assignment_date": "2025-12-03", 
              "price": 5250.00,
              "currency": "INR",
              "selection_reason": "single_hotel"
            }
          ]
        }
      ],
        "total_cost": 15750.00,
        "currency": "INR",
        "total_nights": 3,
        "start_date": "2025-12-01",
        "end_date": "2025-12-03",
        "single_hotel_destinations": 1
      },
      {
        "search_type": "normal",
        "label": "December 2025 Mid",
        "start_month": "2025-12-15",
        "destinations": [...],
        "total_cost": 14400.00,
        "currency": "INR"
      },
      {
        "search_type": "normal",
        "label": "December 2025 End",
        "start_month": "2025-12-25",
        "destinations": [...],
        "total_cost": 16800.00,
        "currency": "INR"
      }
    ]
  },
  "best_itinerary": {
    "search_type": "normal",
    "label": "December 2025 Mid",
    "total_cost": 14400.00,
    "currency": "INR"
  },
  "metadata": {
    "processing_time_ms": 1250,
    "cache_hit": false,
    "hotels_searched": 104,
    "alternatives_generated": 15,
    "best_cost_found": 14400.00,
    "user_authenticated": true,
    "clean_structure_used": true
  },
  "filters_applied": {
    "search_types": ["normal"],
    "custom": false,
    "currency": "INR",
    "guests": {"adults": 2, "children": 0}
  },
  "message": "Found 3 monthly itinerary options"
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
        "currency": "INR",
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
        "currency": "INR",
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
      "currency": "INR",
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
- [ ] Normal search (custom=false) with monthly_options structure
- [ ] Single destination optimization
- [ ] Multi-destination consecutive visits
- [ ] Date constraint validation
- [ ] Guest configuration validation

### New Structure & Authentication Tests
- [ ] Clean monthly_options structure (no legacy fields)
- [ ] Authenticated user gets all monthly options
- [ ] Anonymous user gets single nearest option only
- [ ] Anonymous user sees "Sign in to see all options" message
- [ ] INR currency support and proper pricing display
- [ ] User authentication state in metadata

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
4. Check hotel tracking logs with 🔍 emoji markers for detailed debugging

### Issue: "Anonymous user not getting single nearest option"
**Cause:** Data filtering logic not working correctly
**Solution:**
1. Check `user_authenticated: false` in metadata
2. Verify `nearest_option_shown: true` in metadata
3. Ensure only one option in `monthly_options` array
4. Look for "Sign in to see all options" message

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

### Issue: "Old legacy structure in response"
**Cause:** Using outdated API or legacy code path
**Solution:**
1. Check for `clean_structure_used: true` in metadata
2. Verify response has `monthly_options` array instead of `start_month`, `mid_month`, `end_month`
3. Update API client to handle new structure
4. Look for deprecation warnings in response

### Issue: "Price tracking dates are wrong"
**Cause:** Date logic confusion between price_date and search_date
**Solution:**
1. `price_date` = today (when we searched)
2. `search_date` = travel check-in date
3. `search_end_date` = travel check-out date
4. Check hotel tracking service logs for date assignment verification

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

---

## 🆕 Recent Updates & New Features

### Clean Month-Grouped Structure ✅
- **Old**: Separate `start_month`, `mid_month`, `end_month` fields 
- **New**: Unified `monthly_options` array with consistent structure
- **Benefit**: Cleaner API, easier frontend integration, no data duplication

### Anonymous User Support ✅  
- **Feature**: Smart data filtering for unauthenticated users
- **Behavior**: Shows single nearest option instead of all options
- **Message**: "Sign in to see all available options"
- **Metadata**: `user_authenticated: false`, `nearest_option_shown: true`

### Enhanced Price Tracking ✅
- **Fixed**: Date logic confusion between price_date and search_date
- **Improved**: Hotel star rating extraction with fallback parsing  
- **Added**: Comprehensive debug logging with 🔍 emoji markers
- **Optimized**: Fixed Tortoise ORM queries with proper `.all()` calls

### Currency & Pricing Updates ✅
- **Default**: INR currency support (replaces USD in examples)
- **Realistic**: Updated pricing examples to match Indian market
- **Flexible**: Maintains multi-currency support

### Performance Improvements ✅
- **Caching**: Enhanced request caching with proper hash generation
- **Queries**: Optimized database queries for better response times
- **Logging**: Improved debugging with structured log messages

---

Ready to start testing the optimized itinerary system with clean structure and enhanced features! 🚀