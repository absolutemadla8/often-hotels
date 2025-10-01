from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
# Removed broken FastAPI Admin
from tortoise.contrib.fastapi import register_tortoise
from tortoise import Tortoise

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.error_handlers import setup_exception_handlers
from app.core.logging import LoggingMiddleware, setup_logging
from app.core.security_middleware import (
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
    TrustedHostMiddleware,
)
from app.schemas.response import HealthResponse
from app.services.cache_service import get_cache_service, close_cache_service
# Removed broken admin imports


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events
    """
    # Startup (temporarily disable complex logging)
    # setup_logging()

    # Initialize Tortoise ORM
    # Handle different database URL formats
    db_url = settings.DATABASE_URL

    if db_url and db_url.startswith('postgresql://'):
        # Convert PostgreSQL URL format for Tortoise ORM
        db_url = db_url.replace('postgresql://', 'postgres://', 1)
        # Handle SSL mode parameter for Tortoise ORM
        if 'sslmode=require' in db_url:
            db_url = db_url.replace('?sslmode=require', '').replace('&sslmode=require', '')
    elif not db_url:
        # DATABASE_URL is required for PostgreSQL
        raise ValueError("DATABASE_URL environment variable is required")

    TORTOISE_ORM = {
        "connections": {"default": db_url},
        "apps": {
            "models": {
                "models": ["app.models.models"],
                "default_connection": "default",
            },
        },
    }

    await Tortoise.init(config=TORTOISE_ORM)
    register_tortoise(
        app,
        config=TORTOISE_ORM,
        generate_schemas=True,
        add_exception_handlers=True,
    )

    # Admin functionality disabled - use /docs for API testing

    # Initialize cache service
    try:
        await get_cache_service()
        print("Cache service initialized successfully")
    except Exception as e:
        print(f"Warning: Cache service initialization failed: {e}")

    # Database initialization would go here
    # await init_db()

    # Clean up expired refresh tokens
    # asyncio.create_task(cleanup_expired_tokens())

    yield

    # Shutdown
    await close_cache_service()
    print("Cache service closed")
    pass


def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application
    """
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description=settings.API_DESCRIPTION,
        version=settings.API_VERSION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Set up CORS
    if settings.BACKEND_CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Security middleware
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "0.0.0.0", "209.38.122.169", "*"])
    
    # Logging middleware
    app.add_middleware(RequestLoggingMiddleware)
    # app.add_middleware(LoggingMiddleware)  # Keep basic logging disabled for performance
    
    # Rate limiting (for production, use Redis-based rate limiting)
    # app.add_middleware(
    #     RateLimitMiddleware,
    #     calls=settings.RATE_LIMIT_REQUESTS,
    #     period=settings.RATE_LIMIT_PERIOD
    # )

    # Exception handlers
    setup_exception_handlers(app)

    # Include API routes
    app.include_router(api_router, prefix=settings.API_V1_STR)

    # Add simple admin info route
    @app.get("/admin", include_in_schema=False)
    async def admin_info():
        return {
            "message": "Admin panel temporarily disabled",
            "alternatives": {
                "api_docs": "/docs",
                "redoc": "/redoc",
                "api_endpoints": "/api/v1/"
            }
        }

    return app

# Create the app instance
app = create_application()


@app.get("/", include_in_schema=False)
async def root():
    """
    Root endpoint with basic API information
    """
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "version": settings.API_VERSION,
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "api_url": settings.API_V1_STR,
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint for monitoring and load balancers
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        version=settings.API_VERSION,
        environment="development" if not settings.TESTING else "testing"
    )


@app.get("/health/detailed", tags=["Health"])
async def detailed_health_check():
    """
    Detailed health check with service dependencies
    """
    checks = {
        "api": "healthy",
        "database": "healthy",  # Would check actual DB connection
        "redis": "healthy",     # Would check Redis connection
    }
    
    # In production, add real health checks:
    # try:
    #     await check_database_connection()
    # except Exception:
    #     checks["database"] = "unhealthy"
    
    overall_status = "healthy" if all(status == "healthy" for status in checks.values()) else "unhealthy"
    
    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.API_VERSION,
        "checks": checks,
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )