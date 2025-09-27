# Often Hotels API - Deep Technical Architecture

## Overview
The Often Hotels API is a sophisticated FastAPI application designed for comprehensive hotel price monitoring and booking management. It integrates multiple external APIs (TravClan, SerpAPI), implements advanced tracking systems, and provides a complete hotel search and booking pipeline.

## 1. Application Architecture & Startup Process

### FastAPI Application Lifecycle (`app/main.py`)

The application follows a sophisticated startup process:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Database Initialization
    await Tortoise.init(config=TORTOISE_ORM)  # Async ORM setup
    
    # 2. Schema Generation & Migration
    register_tortoise(app, config=TORTOISE_ORM, generate_schemas=True)
    
    # 3. Background Tasks (commented out for stability)
    # - Token cleanup
    # - Price monitoring jobs
    
    yield  # Application runs here
    
    # 4. Graceful Shutdown
    # Close database connections, cleanup resources
```

**Key Technical Details:**
- **Tortoise ORM**: Async database abstraction layer
- **PostgreSQL Database**: Production-ready database with full ACID compliance
- **SSL Mode Handling**: Automatically adjusts connection strings for production
- **Lifespan Management**: Proper resource initialization and cleanup

### Middleware Stack (Execution Order)

1. **CORS Middleware**: Cross-origin request handling
2. **SecurityHeadersMiddleware**: Sets security headers (HSTS, CSP, etc.)
3. **TrustedHostMiddleware**: Validates request hosts
4. **RequestLoggingMiddleware** (disabled): Request/response logging
5. **Exception Handlers**: Global error processing

## 2. Authentication System Deep Dive

### JWT Token Architecture (`app/core/security.py`)

The system implements a dual-token approach:

```python
# Access Token (8 days)
{
  "exp": 1234567890,      # Expiration timestamp
  "sub": "user_id",       # User identifier
  "type": "access"        # Token type for validation
}

# Refresh Token (30 days)
{
  "exp": 1234567890,
  "sub": "user_id", 
  "type": "refresh"       # Different type for security
}
```

### Authentication Flow

1. **User Registration** (`/api/v1/auth/register`):
   ```
   User Input → Password Hashing (bcrypt) → Database Storage → User Response
   ```

2. **Login Process** (`/api/v1/auth/login`):
   ```
   Credentials → Password Verification → Token Generation → Database Storage → Token Response
   ```

3. **Token Validation** (`app/api/tortoise_deps.py`):
   ```
   Request → Extract Bearer Token → JWT Decode → Database Lookup → User Object
   ```

### Dependency Injection Hierarchy

```python
get_current_user()           # Base authentication
    ↓
get_current_active_user()    # + Active status check
    ↓
get_current_verified_user()  # + Email verification
    ↓
get_current_superuser()      # + Admin privileges
```

### Security Features

- **Password Hashing**: bcrypt with automatic salt generation
- **Token Expiration**: Automatic cleanup of expired refresh tokens
- **Device Tracking**: IP address and user-agent logging
- **Multi-device Logout**: Ability to revoke all user sessions

## 3. Database Architecture & Models

### Core Entity Relationships

```
User (1) ──────→ (N) RefreshToken
  │
  ├─→ (N) UniversalBooking
  ├─→ (N) Tracker
  └─→ (N) UniversalPriceAlert

Country (1) ──→ (N) Destination ──→ (N) Area ──→ (N) Hotel
   │                │                 │
   ├─→ (N) Airport   └─→ (N) Cluster   └─→ (N) Room
   └─→ (N) Flight

UniversalBooking ──→ UniversalPriceHistory
Tracker ──→ TrackerResult ──→ TrackerAlert
```

### Advanced Model Features

#### Polymorphic Design
```python
class UniversalBooking(Model):
    bookable_type = fields.CharEnumField(BookableType)  # "hotel", "flight", "package"
    bookable_id = fields.IntField()                      # ID of the bookable entity
    # This allows booking any type of travel product
```

#### Flexible Tracking System
```python
class UniversalPriceHistory(Model):
    trackable_type = fields.CharEnumField(TrackableType)
    trackable_id = fields.IntField()
    # Tracks price changes for any travel product
```

#### Geographic Hierarchy
```python
Country → Destination → Area → Hotel
# Enables location-based search and filtering
# Supports clustering and geographic analysis
```

### Database Performance Optimizations

- **Composite Indexes**: Multi-column indexes for common queries
- **Foreign Key Constraints**: Referential integrity with cascading deletes
- **JSON Fields**: Flexible schema for API responses and configuration
- **Async Queries**: Non-blocking database operations

## 4. External API Integration Architecture

### TravClan API Service (`app/services/travclan_api_service.py`)

#### Singleton Pattern with Token Management
```python
class TravClanHotelApiService(BaseApiClient):
    _instance = None  # Singleton instance
    _lock = asyncio.Lock()  # Thread-safe initialization
```

#### Advanced Token Management
```python
class TokenManager:
    def __init__(self):
        self._access_token = None
        self._token_expires_at = None  # Automatic expiry tracking
        self._refresh_token = None
        self._lock = asyncio.Lock()    # Async-safe token refresh
```

#### Automatic Token Refresh Flow
```
API Request → Token Expired? → Yes → Refresh Token → Retry Request
                    ↓ No
                Make Request → 401 Response? → Yes → Refresh → Retry
                    ↓ No
                Return Response
```

### Base API Client Features (`app/services/base_api_client.py`)

- **Automatic Retry Logic**: Handles token expiration transparently
- **Request/Response Logging**: Comprehensive API call tracking
- **Error Handling**: Converts HTTP errors to FastAPI exceptions
- **Timeout Management**: Configurable request timeouts
- **Context Manager Support**: Proper resource cleanup

## 5. Request/Response Flow Architecture

### Complete Request Processing Pipeline

```
1. HTTP Request → Nginx Reverse Proxy
    ↓
2. FastAPI App → Middleware Stack
    ↓
3. Route Matching → Endpoint Function
    ↓
4. Dependency Injection → Authentication Check
    ↓
5. Request Validation → Pydantic Schemas
    ↓
6. Business Logic → Service Layer
    ↓
7. Database Operations → Tortoise ORM
    ↓
8. Response Serialization → Pydantic Models
    ↓
9. HTTP Response → Client
```

### Example: Hotel Search Flow

```python
# 1. Request arrives at endpoint
@router.post("/search", response_model=List[HotelResponse])
async def search_hotels(
    search_request: HotelSearchRequest,
    current_user: User = Depends(get_current_active_user)
):
    # 2. Service layer coordination
    async with travclan_api_service as api:
        # 3. External API call
        response = await api.search_hotels(search_request.dict())
        
        # 4. Data transformation
        hotels = HotelMappingService.transform_api_response(response)
        
        # 5. Database storage (optional)
        await store_search_results(hotels, current_user.id)
        
        # 6. Response formatting
        return [HotelResponse.from_orm(hotel) for hotel in hotels]
```

## 6. Advanced Features

### Price Tracking System

The system implements sophisticated price monitoring:

```python
class Tracker(Model):
    tracking_frequency = fields.CharEnumField(TrackerFrequency)
    alert_triggers = fields.JSONField(default=list)
    price_drop_threshold_percent = fields.FloatField()
    
    # Automated tracking execution
    async def execute_tracking_run(self):
        # 1. Fetch current prices
        # 2. Compare with historical data
        # 3. Trigger alerts if thresholds met
        # 4. Store results for analysis
```

### Cluster-Based Organization

Hotels and destinations are organized into intelligent clusters:

```python
class Cluster(Model):
    cluster_type = fields.CharEnumField(ClusterType)  # geographic, thematic, etc.
    is_dynamic = fields.BooleanField()                # Auto-updating clusters
    update_rules = fields.JSONField()                 # Rules for dynamic updates
```

### Universal Booking System

Supports booking any type of travel product:

```python
class UniversalBooking(Model):
    bookable_type = fields.CharEnumField(BookableType)
    secondary_bookable_type = fields.CharField()  # For package deals
    travel_start_date = fields.DateField()
    travel_end_date = fields.DateField()
    # Flexible traveler information
    travelers = fields.JSONField()
```

## 7. Configuration & Environment Management

### Settings Architecture (`app/core/config.py`)

```python
class Settings(BaseSettings):
    # Automatic environment variable loading
    # Type validation with Pydantic
    # Default value management
    # Complex validation with @model_validator
    
    @model_validator(mode='after')
    def assemble_db_connection(self) -> 'Settings':
        # Dynamic database URL construction
        if self.DATABASE_URL is None:
            self.DATABASE_URL = f"postgres://{self.POSTGRES_USER}:..."
        return self
```

### Environment-Specific Configuration

- **Development**: PostgreSQL database (Docker), verbose logging
- **Production**: PostgreSQL database (hosted), optimized logging, SSL
- **Testing**: PostgreSQL database (in-memory or test database), fast execution

## 8. Error Handling & Logging

### Exception Hierarchy

```python
# Custom exceptions with specific handling
class AuthenticationException(HTTPException)
class ValidationException(HTTPException)  
class InvalidTokenException(HTTPException)

# Global error handlers
@app.exception_handler(AuthenticationException)
async def auth_exception_handler(request, exc):
    # Standardized error responses
```

### Comprehensive Logging

- **Request/Response Logging**: All API calls tracked
- **Performance Monitoring**: Execution time tracking
- **Error Tracking**: Detailed error context
- **Business Metrics**: User actions and system health

## 9. Performance & Scalability

### Async Architecture

- **Non-blocking I/O**: All database and API calls are async
- **Connection Pooling**: Efficient resource utilization
- **Background Tasks**: Price monitoring without blocking requests

### Caching Strategy

- **Redis Integration**: Session and temporary data caching
- **API Response Caching**: Reduce external API calls
- **Database Query Optimization**: Efficient data retrieval

### Monitoring & Observability

- **Health Checks**: `/health` and `/health/detailed` endpoints
- **Metrics Export**: Prometheus-compatible metrics
- **Performance Tracking**: Request timing and throughput
- **Error Rate Monitoring**: System reliability metrics

This architecture provides a robust, scalable foundation for hotel price monitoring and booking management, with sophisticated features for tracking, alerting, and user management.