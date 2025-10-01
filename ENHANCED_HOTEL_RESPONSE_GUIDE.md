# Enhanced Hotel Response API Guide

**Last Updated**: October 1, 2025  
**API Version**: v1  
**Status**: ✅ Production Ready

---

## 📋 Overview

The hotel search API has been enhanced to include comprehensive location and rating information in responses. Each hotel now returns detailed context including star rating, country, destination, and area information.

## 🆕 Enhanced Response Fields

### Core Hotel Information
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `hotel_name` | string | Hotel name | "AnandaDara Ubud Resort & Spa" |
| `star_rating` | float/null | Hotel star rating (1-5) | 5.0 |
| `guest_rating` | float/null | Guest review rating | 4.5 |

### ✨ New Location Context Fields
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `country_name` | string | Country where hotel is located | "Indonesia" |
| `destination_name` | string | Primary destination/city | "Bali" |
| `area_name` | string/null | Specific area within destination | "Ubud" |

### Pricing & Availability
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `available_dates` | array | Dates with pricing available | ["2025-10-01", "2025-10-02"] |
| `price_range` | object | Min/max prices for date range | {"min": 4500, "max": 6200} |
| `avg_price` | decimal | Average price per night | 5350.00 |
| `currency` | string | Price currency | "INR" |

### Search Metadata
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `relevance_score` | float/null | Search relevance (0-1) | 0.95 |
| `match_type` | string/null | Match type: exact/partial/fuzzy | "exact" |

---

## 🔍 API Usage Examples

### Basic Hotel Search with Enhanced Response

```bash
GET /api/v1/hotels/search?destination_ids=1&start_date=2025-10-01&end_date=2025-10-02&currency=INR&star_rating=4,5&per_page=3
```

**Response:**
```json
{
  "data": {
    "hotels": [
      {
        "hotel_id": 264,
        "hotel_name": "AnandaDara Ubud Resort & Spa",
        "star_rating": 5.0,
        "guest_rating": 4.5,
        "country_name": "Indonesia",
        "destination_name": "Bali",
        "area_name": null,
        "available_dates": ["2025-10-01", "2025-10-02"],
        "price_range": {"min": 4799, "max": 4799},
        "avg_price": 4799.00,
        "currency": "INR",
        "relevance_score": null,
        "match_type": null,
        "total_nights_available": 2,
        "covers_full_range": true
      }
    ],
    "search_metadata": {
      "star_rating_filter": "4,5",
      "total_before_search": 665
    }
  }
}
```

### Search with Area Filtering

```bash
GET /api/v1/hotels/search?destination_ids=1&area_ids=1&start_date=2025-10-01&end_date=2025-10-02&currency=INR&per_page=2
```

**Response with Area Information:**
```json
{
  "data": {
    "hotels": [
      {
        "hotel_name": "Murni's Houses & Spa",
        "star_rating": 4.0,
        "country_name": "Indonesia",
        "destination_name": "Bali",
        "area_name": "Ubud",
        "price_range": {"min": 3200, "max": 3500},
        "currency": "INR"
      }
    ]
  }
}
```

### Text Search with Relevance Scoring

```bash
GET /api/v1/hotels/search?destination_ids=1&search=luxury&start_date=2025-10-01&end_date=2025-10-02&currency=INR&sort_by=relevance
```

**Response with Search Metadata:**
```json
{
  "data": {
    "hotels": [
      {
        "hotel_name": "Luxury Villa Resort",
        "star_rating": 5.0,
        "country_name": "Indonesia",
        "destination_name": "Bali", 
        "area_name": "Seminyak",
        "relevance_score": 0.95,
        "match_type": "partial",
        "price_range": {"min": 8500, "max": 12000},
        "currency": "INR"
      }
    ],
    "search_metadata": {
      "query": "luxury",
      "query_type": "partial",
      "star_rating_filter": "4,5"
    }
  }
}
```

---

## 📊 Location Context Examples

### Hotels by Location Type

**1. Country-Level Context**
- All hotels show `country_name` for geographic context
- Example: "Indonesia", "Thailand", "India"

**2. Destination-Level Context**  
- Primary city/destination where hotel is located
- Example: "Bali", "Bangkok", "Mumbai"

**3. Area-Level Context (When Applicable)**
- Specific neighborhood or area within destination
- Shows `null` when hotel is not in a defined area
- Example: "Ubud", "Seminyak", "Kuta"

### Location Hierarchy Examples

```json
// Hotel in general Bali (no specific area)
{
  "country_name": "Indonesia",
  "destination_name": "Bali", 
  "area_name": null
}

// Hotel in specific Ubud area
{
  "country_name": "Indonesia",
  "destination_name": "Bali",
  "area_name": "Ubud"
}

// Hotel in Mumbai
{
  "country_name": "India",
  "destination_name": "Mumbai",
  "area_name": null
}
```

---

## ⭐ Star Rating Filter Usage

### Available Star Rating Options

| Parameter Value | Description | Hotels Returned |
|-----------------|-------------|-----------------|
| `star_rating=4,5` | 4-5 star hotels (default) | High-quality hotels only |
| `star_rating=5` | 5-star hotels only | Luxury hotels |
| `star_rating=4` | 4-star hotels only | Premium hotels |
| `star_rating=3,4,5` | 3+ star hotels | Mid-range and above |
| `star_rating=all` | All hotels | No star filter applied |

### Star Rating Examples

```bash
# Luxury hotels only
GET /api/v1/hotels/search?destination_ids=1&star_rating=5&currency=INR

# Premium and luxury
GET /api/v1/hotels/search?destination_ids=1&star_rating=4,5&currency=INR

# All hotels (no filter)
GET /api/v1/hotels/search?destination_ids=1&star_rating=all&currency=INR
```

---

## 💱 Currency Support

### Important Currency Note
Current price data is stored in **INR (Indian Rupees)**. Always specify `currency=INR` for accurate results.

```bash
# Correct - will return hotels with pricing
GET /api/v1/hotels/search?destination_ids=1&currency=INR

# Incorrect - will return empty results
GET /api/v1/hotels/search?destination_ids=1&currency=USD
```

### Available Currencies
- ✅ **INR** - Indian Rupees (current data)
- 🔄 USD, EUR - Future expansion planned

---

## 🔍 Search and Filtering

### Text Search with Enhanced Context

```bash
# Search with fuzzy matching
GET /api/v1/hotels/search?destination_ids=1&search=resort&currency=INR

# Response includes match relevance
{
  "hotel_name": "Ubud Resort & Spa",
  "relevance_score": 0.87,
  "match_type": "partial",
  "country_name": "Indonesia",
  "destination_name": "Bali",
  "area_name": "Ubud"
}
```

### Combined Filters

```bash
# 5-star resorts in Ubud area
GET /api/v1/hotels/search?destination_ids=1&area_ids=1&search=resort&star_rating=5&currency=INR&sort_by=rating

# Response provides full context
{
  "hotels": [
    {
      "hotel_name": "Luxury Ubud Resort",
      "star_rating": 5.0,
      "guest_rating": 4.8,
      "country_name": "Indonesia", 
      "destination_name": "Bali",
      "area_name": "Ubud",
      "relevance_score": 0.92,
      "match_type": "partial"
    }
  ]
}
```

---

## 📈 Performance Optimizations

### Database Efficiency
- ✅ Prefetched relationships prevent N+1 queries
- ✅ Optimized joins for country/destination/area data
- ✅ Indexed queries for fast filtering

### Response Structure
```json
{
  "data": {
    "hotels": [...],           // Enhanced hotel objects
    "search_metadata": {
      "star_rating_filter": "4,5",
      "query": "search_term",
      "total_before_search": 665,
      "search_time_ms": 45.2
    },
    "pagination": {...}
  },
  "user_tier": "admin"
}
```

---

## 🚀 Integration Examples

### Frontend Display

```javascript
// Display hotel with full context
function displayHotel(hotel) {
  return `
    <div class="hotel-card">
      <h3>${hotel.hotel_name}</h3>
      <div class="rating">
        ⭐ ${hotel.star_rating}/5 stars
        👥 ${hotel.guest_rating}/5 guest rating
      </div>
      <div class="location">
        📍 ${hotel.area_name || hotel.destination_name}, ${hotel.country_name}
      </div>
      <div class="pricing">
        💰 ${hotel.avg_price} ${hotel.currency}/night
      </div>
    </div>
  `;
}
```

### Search Result Grouping

```javascript
// Group hotels by location hierarchy
function groupHotelsByLocation(hotels) {
  return hotels.reduce((groups, hotel) => {
    const key = hotel.area_name || hotel.destination_name;
    if (!groups[key]) groups[key] = [];
    groups[key].push(hotel);
    return groups;
  }, {});
}

// Example output:
{
  "Ubud": [/* hotels in Ubud area */],
  "Bali": [/* hotels in general Bali */]
}
```

---

## 🔧 Error Handling

### Common Issues and Solutions

**1. Empty Results with USD Currency**
```bash
# Problem: No results with USD
GET /api/v1/hotels/search?currency=USD

# Solution: Use INR currency
GET /api/v1/hotels/search?currency=INR
```

**2. Invalid Star Rating**
```bash
# Problem: Invalid star rating
GET /api/v1/hotels/search?star_rating=invalid

# Solution: Falls back to default 4,5 star filter
# Response includes applied filter in metadata
{
  "search_metadata": {
    "star_rating_filter": "4,5"  // Applied default
  }
}
```

**3. Location Context Missing**
- `country_name` will show "Unknown" if country data is missing
- `area_name` will be `null` for hotels not in specific areas
- `destination_name` will show "Unknown" if destination data is missing

---

## 📚 Related Documentation

- [Enhanced Hotel Search API Guide](./ENHANCED_HOTEL_SEARCH_API_GUIDE.md) - Complete search documentation
- [Admin Credentials](./ADMIN_CREDENTIALS.md) - Authentication setup
- [Itinerary Optimization Test Report](./ITINERARY_OPTIMIZATION_TEST_REPORT.md) - System testing results

---

## 📞 API Reference

**Base URL**: `http://localhost:8000/api/v1`  
**Authentication**: JWT Bearer token (optional for basic access)  
**Content-Type**: `application/json`  

**Endpoint**: `GET /hotels/search`

**Enhanced Response Schema**:
```typescript
interface HotelAvailabilityInfoEnhanced {
  hotel_id: number;
  hotel_name: string;
  star_rating: number | null;
  guest_rating: number | null;
  country_name: string;        // ✨ New
  destination_name: string;
  area_name: string | null;
  available_dates: string[];
  price_range: {min: number, max: number};
  avg_price: number;
  currency: string;
  relevance_score?: number;
  match_type?: string;
  total_nights_available: number;
  covers_full_range: boolean;
}
```

---

**Status**: ✅ **Production Ready**  
**Last Updated**: October 1, 2025  
**API Version**: v1.0

*This guide documents the enhanced hotel response fields providing comprehensive location context and star rating information for better user experience and frontend integration.*