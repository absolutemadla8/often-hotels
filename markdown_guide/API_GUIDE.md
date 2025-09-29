# API Usage Guide

This guide provides detailed examples of how to use the Often Hotels API endpoints.

## Base URL

- Development: `http://localhost:8000`
- Production: `https://your-domain.com`

All API endpoints are prefixed with `/api/v1`.

## Authentication Flow

### 1. Register a New User

```bash
curl -X POST "${BASE_URL}/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john.doe@example.com",
    "username": "johndoe",
    "password": "SecurePass123!",
    "confirm_password": "SecurePass123!",
    "first_name": "John",
    "last_name": "Doe",
    "phone_number": "+1234567890"
  }'
```

**Response:**
```json
{
  "id": 1,
  "email": "john.doe@example.com",
  "username": "johndoe",
  "first_name": "John",
  "last_name": "Doe",
  "phone_number": "+1234567890",
  "is_active": true,
  "is_verified": false,
  "is_superuser": false,
  "created_at": "2024-01-20T10:30:00Z",
  "updated_at": "2024-01-20T10:30:00Z",
  "last_login": null
}
```

### 2. Login and Get Tokens

```bash
curl -X POST "${BASE_URL}/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john.doe@example.com",
    "password": "SecurePass123!"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 691200
}
```

### 3. Use Access Token

Include the access token in the Authorization header for protected endpoints:

```bash
curl -X GET "${BASE_URL}/api/v1/auth/me" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### 4. Refresh Access Token

```bash
curl -X POST "${BASE_URL}/api/v1/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'
```

## User Management

### Get Current User Profile

```bash
curl -X GET "${BASE_URL}/api/v1/auth/me" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}"
```

### Update User Profile

```bash
curl -X PUT "${BASE_URL}/api/v1/auth/me" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Johnny",
    "bio": "Travel enthusiast and hotel reviewer",
    "timezone": "America/New_York"
  }'
```

### Change Password

```bash
curl -X POST "${BASE_URL}/api/v1/auth/change-password" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "current_password": "SecurePass123!",
    "new_password": "NewSecurePass456!",
    "confirm_new_password": "NewSecurePass456!"
  }'
```

## Hotel Operations

### Get Hotels List (Public)

```bash
# Without authentication (limited information)
curl -X GET "${BASE_URL}/api/v1/hotels/"

# With authentication (full information)
curl -X GET "${BASE_URL}/api/v1/hotels/" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}"

# With filters
curl -X GET "${BASE_URL}/api/v1/hotels/?location=bali&skip=0&limit=10"
```

**Response (authenticated):**
```json
{
  "hotels": [
    {
      "id": 1,
      "name": "Luxury Resort & Spa",
      "location": "Bali, Indonesia",
      "description": "A beautiful beachfront resort with world-class amenities",
      "price_per_night": 350.00,
      "rating": 4.8,
      "amenities": ["Pool", "Spa", "Beach Access", "Restaurant", "WiFi"],
      "available": true
    }
  ],
  "total": 3,
  "authenticated": true
}
```

### Get Hotel Details

```bash
curl -X GET "${BASE_URL}/api/v1/hotels/1" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}"
```

**Response:**
```json
{
  "hotel": {
    "id": 1,
    "name": "Luxury Resort & Spa",
    "location": "Bali, Indonesia",
    "description": "A beautiful beachfront resort with world-class amenities",
    "price_per_night": 350.00,
    "rating": 4.8,
    "amenities": ["Pool", "Spa", "Beach Access", "Restaurant", "WiFi"],
    "available": true
  },
  "user_authenticated": true,
  "special_offers": ["10% discount for verified users", "Free breakfast"]
}
```

### Book a Hotel (Requires verified user)

```bash
curl -X POST "${BASE_URL}/api/v1/hotels/1/book" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "check_in": "2024-03-15",
    "check_out": "2024-03-18",
    "nights": 3,
    "guests": 2,
    "room_type": "deluxe",
    "special_requests": "Ocean view room preferred"
  }'
```

**Response:**
```json
{
  "message": "Booking confirmed successfully",
  "booking": {
    "booking_id": "BK11001",
    "hotel_name": "Luxury Resort & Spa",
    "user_email": "john.doe@example.com",
    "user_name": "John Doe",
    "booking_data": {
      "check_in": "2024-03-15",
      "check_out": "2024-03-18",
      "nights": 3,
      "guests": 2,
      "room_type": "deluxe",
      "special_requests": "Ocean view room preferred"
    },
    "total_price": 1050.00,
    "status": "confirmed"
  }
}
```

### Get My Bookings

```bash
curl -X GET "${BASE_URL}/api/v1/hotels/bookings/my" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}"
```

### Hotel Reviews

#### Get Hotel Reviews

```bash
curl -X GET "${BASE_URL}/api/v1/hotels/1/reviews" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}"
```

#### Create Hotel Review

```bash
curl -X POST "${BASE_URL}/api/v1/hotels/1/reviews" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "rating": 5,
    "comment": "Absolutely amazing stay! The staff was incredibly friendly and the facilities were top-notch. Will definitely come back!"
  }'
```

## Admin Operations (Superuser only)

### List All Users

```bash
curl -X GET "${BASE_URL}/api/v1/users/?skip=0&limit=10" \
  -H "Authorization: Bearer ${ADMIN_ACCESS_TOKEN}"
```

### Create User (Admin)

```bash
curl -X POST "${BASE_URL}/api/v1/users/" \
  -H "Authorization: Bearer ${ADMIN_ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "username": "newuser",
    "password": "SecurePass123!",
    "confirm_password": "SecurePass123!",
    "first_name": "New",
    "last_name": "User",
    "is_active": true,
    "is_verified": true
  }'
```

### Update User (Admin)

```bash
curl -X PUT "${BASE_URL}/api/v1/users/2" \
  -H "Authorization: Bearer ${ADMIN_ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "is_active": false
  }'
```

### Deactivate User

```bash
curl -X POST "${BASE_URL}/api/v1/users/2/deactivate" \
  -H "Authorization: Bearer ${ADMIN_ACCESS_TOKEN}"
```

### Get Admin Statistics

```bash
curl -X GET "${BASE_URL}/api/v1/hotels/admin/statistics" \
  -H "Authorization: Bearer ${ADMIN_ACCESS_TOKEN}"
```

## Error Handling

The API returns consistent error responses:

### Validation Error (422)

```json
{
  "success": false,
  "message": "Validation failed",
  "errors": [
    {
      "type": "validation_error",
      "field": "password",
      "message": "ensure this value has at least 8 characters",
      "input": "short"
    }
  ]
}
```

### Authentication Error (401)

```json
{
  "success": false,
  "message": "Could not validate credentials",
  "errors": [
    {
      "type": "HTTPException",
      "code": 401,
      "message": "Could not validate credentials"
    }
  ]
}
```

### Authorization Error (403)

```json
{
  "success": false,
  "message": "Not enough permissions",
  "errors": [
    {
      "type": "HTTPException",
      "code": 403,
      "message": "The user doesn't have enough privileges"
    }
  ]
}
```

### Rate Limit Error (429)

```json
{
  "success": false,
  "message": "Rate limit exceeded. Please try again later.",
  "errors": [
    {
      "type": "rate_limit_error",
      "message": "Too many requests"
    }
  ]
}
```

## Response Format

All API responses follow a consistent format:

### Success Response

```json
{
  "success": true,
  "message": "Operation completed successfully",
  "data": {
    // Response data here
  }
}
```

### Error Response

```json
{
  "success": false,
  "message": "Error message",
  "errors": [
    {
      "type": "error_type",
      "message": "Detailed error message"
    }
  ]
}
```

## Status Codes

- `200 OK` - Successful GET, PUT requests
- `201 Created` - Successful POST requests
- `204 No Content` - Successful DELETE requests
- `400 Bad Request` - Invalid request data
- `401 Unauthorized` - Authentication required or failed
- `403 Forbidden` - Access denied
- `404 Not Found` - Resource not found
- `409 Conflict` - Resource already exists
- `422 Unprocessable Entity` - Validation errors
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server error

## Testing with Postman

You can import the API into Postman:

1. Start the API server
2. Navigate to `http://localhost:8000/api/v1/openapi.json`
3. Copy the JSON content
4. In Postman: Import → Paste Raw Text → Continue

## Testing with curl Scripts

Save these environment variables for easier testing:

```bash
export BASE_URL="http://localhost:8000"
export ACCESS_TOKEN=""  # Set after login
export REFRESH_TOKEN=""  # Set after login
```

Login and set tokens:

```bash
# Login and extract tokens
RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john.doe@example.com",
    "password": "SecurePass123!"
  }')

export ACCESS_TOKEN=$(echo $RESPONSE | jq -r '.access_token')
export REFRESH_TOKEN=$(echo $RESPONSE | jq -r '.refresh_token')

echo "Access token set: ${ACCESS_TOKEN:0:50}..."
```

## WebSocket Support (Future Enhancement)

The API is designed to support WebSocket connections for real-time features:

- Real-time booking notifications
- Live chat support
- Real-time availability updates
- User activity notifications

## GraphQL Support (Future Enhancement)

Consider adding GraphQL endpoints for more flexible data querying:

- Single endpoint for complex queries
- Reduce over-fetching of data
- Better frontend integration
- Real-time subscriptions

## SDK and Client Libraries

Consider creating client SDKs for popular languages:

- JavaScript/TypeScript SDK
- Python SDK  
- Mobile SDKs (iOS/Android)
- PHP SDK

This would simplify integration for developers using the API.