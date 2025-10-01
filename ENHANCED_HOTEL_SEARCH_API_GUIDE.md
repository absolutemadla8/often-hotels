# Enhanced Hotel Search API Guide

A comprehensive guide to the enhanced hotel search API with pagination, fuzzy matching, and advanced sorting capabilities.

## 🚀 Overview

The enhanced hotel search API provides powerful search capabilities for finding hotels across multiple destinations with:

- **Text Search**: Exact, partial, and fuzzy matching on hotel names
- **Pagination**: Efficient browsing of large hotel datasets
- **Multiple Sorting**: Sort by relevance, price, rating, or name
- **Multi-Destination**: Search across multiple destinations and areas
- **Real-time Pricing**: Current availability and pricing data

## 📍 API Endpoint

```
GET /api/v1/hotels/search
```

## 🔧 Request Parameters

### Required Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `destination_ids` | string | Comma-separated destination IDs | `"1,2,3"` |
| `start_date` | date | Check-in date (YYYY-MM-DD) | `"2025-11-01"` |
| `end_date` | date | Check-out date (YYYY-MM-DD) | `"2025-11-05"` |

### Optional Parameters

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `area_ids` | string | null | - | Comma-separated area IDs |
| `currency` | string | "USD" | 3 chars | Currency code (USD, INR, EUR, etc.) |
| `search` | string | null | 2-100 chars | Hotel name search query |
| `page` | integer | 1 | 1-1000 | Page number |
| `per_page` | integer | 20 | 1-100 | Results per page |
| `sort_by` | string | "relevance" | - | Sort order (see options below) |

### Sort Options

| Sort Value | Description | Order |
|------------|-------------|-------|
| `relevance` | Best matches first (when searching) | Desc |
| `price_asc` | Price low to high | Asc |
| `price_desc` | Price high to low | Desc |
| `rating` | Guest rating high to low | Desc |
| `name` | Alphabetical order | Asc |

## 🔍 Search Features

### 1. Empty Search (Browse All Hotels)

Load all hotels with pagination:

```bash
GET /api/v1/hotels/search?destination_ids=1&start_date=2025-11-01&end_date=2025-11-05&page=1&per_page=20
```

### 2. Exact Hotel Name Search

Find hotels with exact name matches:

```bash
GET /api/v1/hotels/search?destination_ids=1&start_date=2025-11-01&end_date=2025-11-05&search=Hilton&page=1
```

### 3. Partial Hotel Name Search

Find hotels containing search terms:

```bash
GET /api/v1/hotels/search?destination_ids=1&start_date=2025-11-01&end_date=2025-11-05&search=resort&page=1
```

### 4. Fuzzy Search with Typos

Handle spelling mistakes and variations:

```bash
GET /api/v1/hotels/search?destination_ids=1&start_date=2025-11-01&end_date=2025-11-05&search=hilten&page=1
```

## 📊 Response Structure

### Success Response (200 OK)

```json
{
  "destination_ids": [1, 2],
  "destination_names": ["Bali", "Mumbai"],
  "area_ids": [1, 2],
  "area_names": ["Ubud", "Nusa Dua"],
  "date_range": {
    "start": "2025-11-01",
    "end": "2025-11-05"
  },
  "currency": "INR",
  "search_metadata": {
    "query": "hilton",
    "query_type": "partial",
    "min_relevance_score": 0.7,
    "max_relevance_score": 0.9,
    "total_before_search": 150,
    "search_time_ms": 45.2
  },
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 15,
    "pages": 1,
    "has_next": false,
    "has_prev": false
  },
  "sorting": {
    "sort_by": "relevance",
    "sort_order": "desc",
    "available_sorts": ["relevance", "price_asc", "price_desc", "rating", "name"]
  },
  "hotels": [
    {
      "hotel_id": 123,
      "hotel_name": "Hilton Garden Inn",
      "star_rating": 4.0,
      "guest_rating": 4.2,
      "available_dates": ["2025-11-01", "2025-11-02", "2025-11-03", "2025-11-04"],
      "price_range": {
        "min": 8500.00,
        "max": 12000.00
      },
      "avg_price": 10250.00,
      "total_nights_available": 4,
      "covers_full_range": true,
      "currency": "INR",
      "relevance_score": 0.9,
      "match_type": "partial",
      "destination_name": "Bali",
      "area_name": "Ubud"
    }
  ],
  "hotels_full_coverage": 12,
  "search_summary": {
    "destinations_searched": 2,
    "areas_searched": 2,
    "total_locations": 4,
    "hotels_per_destination": {
      "Bali": 10,
      "Mumbai": 5
    },
    "hotels_per_area": {
      "Ubud": 8,
      "Nusa Dua": 2
    },
    "price_range_summary": {
      "min": 5000.00,
      "max": 25000.00,
      "currency": "INR",
      "count": 15
    }
  }
}
```

### Error Responses

#### 400 Bad Request - Invalid Parameters

```json
{
  "detail": "Invalid destination IDs format: invalid literal for int()"
}
```

#### 404 Not Found - Invalid Destinations

```json
{
  "detail": "Destinations not found: [999]"
}
```

## 📈 Performance Optimizations

The API includes several performance optimizations:

### Database Indexes

- **GIN Trigram Index**: Fast fuzzy search using PostgreSQL pg_trgm
- **B-tree Indexes**: Efficient exact and prefix matching
- **Composite Indexes**: Optimized filtering and sorting
- **Price History Indexes**: Fast price data joins

### Expected Performance

| Operation | Response Time | Optimization |
|-----------|---------------|---------------|
| Empty search (paginated) | < 100ms | Composite indexes |
| Text search | < 200ms | B-tree + GIN indexes |
| Fuzzy search | < 500ms | Trigram similarity |
| Large datasets (1000+ hotels) | < 1s | Pagination + indexes |
| Concurrent searches | Linear scaling | Index efficiency |

## 🎯 Usage Examples

### 1. Browse Hotels in Multiple Destinations

```bash
curl -X GET "https://your-api.com/api/v1/hotels/search?destination_ids=1,2,3&start_date=2025-12-01&end_date=2025-12-05&currency=USD&page=1&per_page=25"
```

### 2. Search for Luxury Resorts

```bash
curl -X GET "https://your-api.com/api/v1/hotels/search?destination_ids=1&area_ids=1,2&start_date=2025-12-01&end_date=2025-12-05&search=luxury%20resort&sort_by=rating&page=1"
```

### 3. Find Budget Hotels

```bash
curl -X GET "https://your-api.com/api/v1/hotels/search?destination_ids=1&start_date=2025-12-01&end_date=2025-12-05&sort_by=price_asc&page=1&per_page=10"
```

### 4. Search with Spelling Mistakes

```bash
curl -X GET "https://your-api.com/api/v1/hotels/search?destination_ids=1&start_date=2025-12-01&end_date=2025-12-05&search=mariot&page=1"
```

### 5. Pagination Through Results

```bash
# First page
curl -X GET "https://your-api.com/api/v1/hotels/search?destination_ids=1&start_date=2025-12-01&end_date=2025-12-05&page=1&per_page=20"

# Second page
curl -X GET "https://your-api.com/api/v1/hotels/search?destination_ids=1&start_date=2025-12-01&end_date=2025-12-05&page=2&per_page=20"
```

## 🔍 Search Relevance Scoring

The API uses a sophisticated relevance scoring system:

### Score Ranges

| Match Type | Score Range | Description |
|------------|-------------|-------------|
| **Exact** | 1.0 | Perfect name match |
| **Partial (Prefix)** | 0.9 | Name starts with search term |
| **Partial (Contains)** | 0.7 | Name contains search term |
| **Partial (Other)** | 0.5 | Other partial matches |
| **Fuzzy** | 0.3-0.99 | Similarity-based matching |

### Query Types

- **`empty`**: No search query provided (browse all)
- **`exact`**: Exact name match found
- **`partial`**: Substring match found
- **`fuzzy`**: Similarity-based match using trigrams

## 🛡️ Authentication & Security

### Authentication

The API supports optional authentication:

```bash
# Without authentication (limited results)
curl -X GET "https://your-api.com/api/v1/hotels/search?destination_ids=1&start_date=2025-12-01&end_date=2025-12-05"

# With authentication (full access)
curl -X GET "https://your-api.com/api/v1/hotels/search?destination_ids=1&start_date=2025-12-01&end_date=2025-12-05" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Data Filtering

- **Anonymous Users**: Limited results and features
- **Authenticated Users**: Full access to all features
- **Admin Users**: Access to all data and admin features

## 🚨 Rate Limiting

The API includes rate limiting to ensure fair usage:

- **Anonymous Users**: 100 requests per hour
- **Authenticated Users**: 1000 requests per hour
- **Admin Users**: 10000 requests per hour

## 🐛 Error Handling

### Common Errors

| Status Code | Error | Solution |
|-------------|-------|----------|
| 400 | Invalid date range | Ensure end_date > start_date |
| 400 | Invalid destination IDs | Check destination IDs exist |
| 400 | Search query too short | Use at least 2 characters |
| 400 | Invalid page number | Use page between 1-1000 |
| 400 | Invalid per_page | Use per_page between 1-100 |
| 404 | Destinations not found | Verify destination IDs |
| 404 | Areas not found | Verify area IDs |

### Error Response Format

```json
{
  "detail": "Error description with helpful context"
}
```

## 📱 Frontend Integration

### React/JavaScript Example

```javascript
const searchHotels = async (params) => {
  const queryParams = new URLSearchParams({
    destination_ids: params.destinationIds.join(','),
    start_date: params.startDate,
    end_date: params.endDate,
    currency: params.currency || 'USD',
    search: params.search || '',
    page: params.page || 1,
    per_page: params.perPage || 20,
    sort_by: params.sortBy || 'relevance'
  });

  const response = await fetch(`/api/v1/hotels/search?${queryParams}`, {
    headers: {
      'Authorization': `Bearer ${userToken}`,
      'Content-Type': 'application/json'
    }
  });

  if (!response.ok) {
    throw new Error(`Search failed: ${response.statusText}`);
  }

  return await response.json();
};

// Usage
const results = await searchHotels({
  destinationIds: [1, 2],
  startDate: '2025-12-01',
  endDate: '2025-12-05',
  search: 'luxury resort',
  page: 1,
  perPage: 20,
  sortBy: 'rating'
});
```

### Python Example

```python
import requests
from datetime import date

def search_hotels(destination_ids, start_date, end_date, **kwargs):
    params = {
        'destination_ids': ','.join(map(str, destination_ids)),
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'currency': kwargs.get('currency', 'USD'),
        'search': kwargs.get('search', ''),
        'page': kwargs.get('page', 1),
        'per_page': kwargs.get('per_page', 20),
        'sort_by': kwargs.get('sort_by', 'relevance')
    }
    
    response = requests.get(
        'https://your-api.com/api/v1/hotels/search',
        params=params,
        headers={'Authorization': f'Bearer {user_token}'}
    )
    
    response.raise_for_status()
    return response.json()

# Usage
results = search_hotels(
    destination_ids=[1, 2],
    start_date=date(2025, 12, 1),
    end_date=date(2025, 12, 5),
    search='luxury resort',
    sort_by='rating'
)
```

## 💡 Best Practices

### 1. Optimize Search Queries

- Use specific search terms for better relevance
- Combine destination and area filters for precision
- Use appropriate page sizes (10-50 results)

### 2. Handle Pagination Efficiently

- Check `has_next` before requesting next page
- Use reasonable page sizes to balance performance
- Cache results when appropriate

### 3. Implement Smart Sorting

- Use `relevance` for search queries
- Use `price_asc` for budget-conscious users
- Use `rating` for quality-focused searches

### 4. Error Handling

- Always handle 404 errors for invalid destinations
- Validate date ranges before making requests
- Implement retry logic for temporary failures

### 5. Performance Optimization

- Use search filters to reduce dataset size
- Implement client-side caching for repeated searches
- Consider debouncing for real-time search

## 🔗 Related APIs

- **`GET /api/v1/hotels/{hotel_id}`**: Get detailed hotel information
- **`GET /api/v1/hotels/`**: List hotels with basic filtering
- **`GET /api/v1/destinations/search`**: Search destinations and areas
- **`POST /api/v1/itineraries/optimize`**: Optimize multi-destination itineraries

## 📞 Support

For API support and questions:

- Documentation: [API Docs](https://your-api.com/docs)
- GitHub Issues: [Report Issues](https://github.com/your-repo/issues)
- Email: api-support@your-domain.com

---

**Last Updated**: October 2025  
**API Version**: v1  
**Guide Version**: 1.0