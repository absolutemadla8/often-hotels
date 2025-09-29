# Location Search API Guide

A comprehensive guide for using the unified location search API that searches across both destinations and areas.

## 🌟 Overview

The Location Search API provides a unified interface to search across both **Destinations** (cities, provinces) and **Areas** (districts, neighborhoods) with proper pagination, filtering, and type indication.

### Key Features
- 🔍 **Unified Search**: Search both destinations and areas in one API call
- 🏷️ **Type Indication**: Clear marking of "destination" vs "area" 
- 📄 **Pagination**: Proper pagination with metadata
- 🎯 **Filtering**: By type, country, tracking status
- ⚡ **Performance**: Optimized with database indexes
- 🔗 **Relationships**: Areas show their parent destination

---

## 🚀 Quick Start

### Basic Search
```bash
curl -X GET "http://localhost:8000/api/v1/locations/search?q=bali" \
  -H "accept: application/json"
```

### Search with Pagination
```bash
curl -X GET "http://localhost:8000/api/v1/locations/search?q=bali&page=1&per_page=5" \
  -H "accept: application/json"
```

### Search Destinations Only
```bash
curl -X GET "http://localhost:8000/api/v1/locations/destinations?q=mumbai" \
  -H "accept: application/json"
```

---

## 📚 API Endpoints

### 1. Unified Search
**`GET /api/v1/locations/search`**

Search across both destinations and areas with full filtering capabilities.

#### Parameters:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `q` | string | ✅ | Search keyword (min 2 chars, max 100) |
| `page` | integer | ❌ | Page number (default: 1, max: 1000) |
| `per_page` | integer | ❌ | Results per page (default: 20, max: 100) |
| `type` | string | ❌ | Filter by type: "destination" or "area" |
| `country_id` | integer | ❌ | Filter by country ID |
| `tracking_only` | boolean | ❌ | Show only tracking-enabled locations |

#### Example:
```bash
curl -X GET "http://localhost:8000/api/v1/locations/search?q=ubud&type=area&tracking_only=true" \
  -H "accept: application/json"
```

### 2. Destinations Only
**`GET /api/v1/locations/destinations`**

Search only destinations (cities, provinces, countries).

#### Parameters:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `q` | string | ✅ | Search keyword |
| `page` | integer | ❌ | Page number |
| `per_page` | integer | ❌ | Results per page |
| `country_id` | integer | ❌ | Filter by country ID |
| `tracking_only` | boolean | ❌ | Show only tracking-enabled destinations |

#### Example:
```bash
curl -X GET "http://localhost:8000/api/v1/locations/destinations?q=mumbai&tracking_only=true" \
  -H "accept: application/json"
```

### 3. Areas Only
**`GET /api/v1/locations/areas`**

Search only areas (districts, neighborhoods, zones).

#### Parameters:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `q` | string | ✅ | Search keyword |
| `page` | integer | ❌ | Page number |
| `per_page` | integer | ❌ | Results per page |
| `country_id` | integer | ❌ | Filter by country ID |
| `tracking_only` | boolean | ❌ | Show only tracking-enabled areas |

#### Example:
```bash
curl -X GET "http://localhost:8000/api/v1/locations/areas?q=ubud" \
  -H "accept: application/json"
```

### 4. Tracking Locations Only
**`GET /api/v1/locations/tracking`**

Search only locations that have tracking enabled.

#### Parameters:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `q` | string | ✅ | Search keyword |
| `page` | integer | ❌ | Page number |
| `per_page` | integer | ❌ | Results per page |
| `type` | string | ❌ | Filter by type: "destination" or "area" |
| `country_id` | integer | ❌ | Filter by country ID |

#### Example:
```bash
curl -X GET "http://localhost:8000/api/v1/locations/tracking?q=bali&type=destination" \
  -H "accept: application/json"
```

---

## 📋 Response Format

### Success Response Structure
```json
{
  "success": true,
  "results": [
    {
      "id": 5,
      "name": "Bali",
      "type": "destination",
      "display_name": "Bali",
      "description": "Indonesian island and province...",
      "latitude": -8.3405,
      "longitude": 115.0920,
      "is_active": true,
      "is_popular": true,
      "tracking": true,
      "destination_type": "province",
      "tourist_rating": 4.8,
      "areas_count": 1,
      "country": {
        "id": 1119,
        "name": "Indonesia",
        "iso_code_2": "ID",
        "iso_code_3": "IDN"
      }
    },
    {
      "id": 1,
      "name": "Ubud",
      "type": "area",
      "display_name": "Ubud",
      "description": "Cultural heart of Bali...",
      "latitude": -8.5069,
      "longitude": 115.2625,
      "is_active": true,
      "is_popular": true,
      "tracking": true,
      "area_type": "town",
      "area_level": 1,
      "country": {
        "id": 1119,
        "name": "Indonesia",
        "iso_code_2": "ID",
        "iso_code_3": "IDN"
      },
      "destination": {
        "id": 5,
        "name": "Bali",
        "display_name": "Bali"
      }
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 2,
    "pages": 1,
    "has_next": false,
    "has_prev": false
  },
  "filters_applied": {
    "search_keyword": "bali",
    "type": null,
    "country_id": null,
    "tracking_only": false
  },
  "message": "Found 2 locations matching 'bali'"
}
```

### Error Response Structure
```json
{
  "success": false,
  "message": "Validation failed",
  "errors": [
    {
      "type": "validation_error",
      "field": "query -> q",
      "message": "String should have at least 2 characters",
      "input": "a"
    }
  ]
}
```

---

## 🎯 Result Types

### Destination Results
Properties specific to destinations:
- `type`: Always "destination"
- `destination_type`: "city", "province", "country", etc.
- `tourist_rating`: Rating for tourism appeal
- `population`: Population count
- `areas_count`: Number of areas in this destination
- `numberofdaystotrack`: Days configured for hotel tracking

### Area Results  
Properties specific to areas:
- `type`: Always "area"
- `area_type`: "district", "town", "neighborhood", etc.
- `area_level`: Hierarchical level (1, 2, 3...)
- `walkability_score`: Walkability rating
- `hotel_density`: Hotel density classification
- `destination`: Parent destination information

---

## 🔍 Search Behavior

### Matching Strategy
The search uses fuzzy matching with relevance scoring:

1. **Exact Match** (highest priority)
   - `name = "bali"` → Exact match for "Bali"

2. **Starts With** (high priority)
   - `name LIKE "bali%"` → "Bali Province"

3. **Contains** (medium priority)
   - `name LIKE "%bali%"` → "South Bali"

4. **Description Match** (lower priority)
   - `description LIKE "%bali%"` → Mentions Bali in description

### Result Ordering
1. Relevance score (exact → starts → contains → description)
2. Type priority (destinations before areas in mixed results)
3. Alphabetical by name

---

## 💡 Usage Examples

### Frontend Search Autocomplete
```javascript
// Search as user types
async function searchLocations(query) {
  const response = await fetch(
    `/api/v1/locations/search?q=${encodeURIComponent(query)}&per_page=10`
  );
  const data = await response.json();
  
  return data.results.map(location => ({
    id: location.id,
    name: location.name,
    type: location.type,
    displayName: location.type === 'area' 
      ? `${location.name}, ${location.destination.name}`
      : location.name,
    country: location.country.name
  }));
}
```

### Admin Panel - Tracking Locations
```javascript
// Get only locations with tracking enabled
async function getTrackingLocations(page = 1) {
  const response = await fetch(
    `/api/v1/locations/tracking?q=&page=${page}&per_page=20`
  );
  return await response.json();
}
```

### Filter by Country
```javascript
// Search locations in Indonesia (country_id = 1119)
async function searchInIndonesia(query) {
  const response = await fetch(
    `/api/v1/locations/search?q=${query}&country_id=1119`
  );
  return await response.json();
}
```

---

## ⚡ Performance Tips

### 1. Use Specific Searches
```bash
# Better: Specific type search
GET /api/v1/locations/destinations?q=mumbai

# Slower: Generic search with filter
GET /api/v1/locations/search?q=mumbai&type=destination
```

### 2. Limit Results
```bash
# Use appropriate per_page values
GET /api/v1/locations/search?q=bali&per_page=10  # Good for autocomplete
GET /api/v1/locations/search?q=bali&per_page=50  # Good for full listings
```

### 3. Use Tracking Filter for Admin
```bash
# Admin interfaces: only show trackable locations
GET /api/v1/locations/tracking?q=destination_name
```

---

## 🚨 Error Handling

### Common Error Codes

| Status | Error | Description |
|--------|-------|-------------|
| 400 | Bad Request | Invalid parameters (query too short, invalid filters) |
| 422 | Validation Error | Parameter validation failed |
| 500 | Server Error | Internal server error |

### Example Error Responses
```json
// Query too short
{
  "success": false,
  "message": "Validation failed",
  "errors": [{"message": "String should have at least 2 characters"}]
}

// Invalid page number
{
  "success": false, 
  "message": "Validation failed",
  "errors": [{"message": "Input should be greater than or equal to 1"}]
}
```

---

## 🔧 Integration Examples

### React Hook
```javascript
import { useState, useEffect } from 'react';

function useLocationSearch(query, filters = {}) {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState(null);

  useEffect(() => {
    if (query.length < 2) return;
    
    setLoading(true);
    const params = new URLSearchParams({
      q: query,
      page: filters.page || 1,
      per_page: filters.perPage || 20,
      ...(filters.type && { type: filters.type }),
      ...(filters.countryId && { country_id: filters.countryId }),
      ...(filters.trackingOnly && { tracking_only: true })
    });

    fetch(`/api/v1/locations/search?${params}`)
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          setResults(data.results);
          setPagination(data.pagination);
        }
      })
      .finally(() => setLoading(false));
  }, [query, filters]);

  return { results, loading, pagination };
}
```

### Vue.js Composition API
```javascript
import { ref, watch } from 'vue';

export function useLocationSearch() {
  const query = ref('');
  const results = ref([]);
  const loading = ref(false);
  
  const search = async (searchQuery, options = {}) => {
    if (searchQuery.length < 2) return;
    
    loading.value = true;
    try {
      const params = new URLSearchParams({
        q: searchQuery,
        ...options
      });
      
      const response = await fetch(`/api/v1/locations/search?${params}`);
      const data = await response.json();
      
      if (data.success) {
        results.value = data.results;
      }
    } finally {
      loading.value = false;
    }
  };

  watch(query, (newQuery) => {
    search(newQuery);
  });

  return { query, results, loading, search };
}
```

---

## 📖 Related Documentation

- [Hotel Tracking API Guide](./hotel-tracking-api.md)
- [Authentication Guide](./authentication.md)  
- [Database Schema](./database-schema.md)
- [API Rate Limiting](./rate-limiting.md)

---

## 🆘 Support

If you encounter issues:
1. Check the error response for validation details
2. Ensure query parameters meet requirements
3. Verify API endpoint URLs
4. Check server logs for detailed error information

For additional support, contact the development team or check the project repository.