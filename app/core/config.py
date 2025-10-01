import secrets
from typing import Any, Dict, List, Optional, Union

from pydantic import AnyHttpUrl, EmailStr, HttpUrl, field_validator, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30 days
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30  # 30 days
    
    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode='before')
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    PROJECT_NAME: str = "Often Hotels API"
    API_DESCRIPTION: str = """Robust and scalable hotel booking API with multi-destination itinerary optimization

🆕 **Recent Updates:**
- Clean month-grouped structure with unified `monthly_options` 
- Anonymous user support with smart data filtering
- Enhanced price tracking with proper date logic
- Multi-currency support (INR, USD, EUR, etc.)
- Optimized hotel search with comprehensive debug logging

**Key Features:**
- Multi-destination itinerary optimization
- Hotel cost minimization with single-hotel preference
- Flexible search modes (normal, ranges, fixed_dates)
- Redis caching for improved performance
- Real-time hotel price tracking with SerpAPI
- Background job processing with Celery"""
    API_VERSION: str = "1.0.0"
    
    # Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_DB: str = "often_hotels"
    POSTGRES_PORT: str = "5432"
    DATABASE_URL: Optional[str] = None

    @model_validator(mode='after')
    def assemble_db_connection(self) -> 'Settings':
        if self.DATABASE_URL is None:
            self.DATABASE_URL = f"postgres://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        return self

    # Redis for caching and rate limiting
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Security
    ALGORITHM: str = "HS256"
    PASSWORD_MIN_LENGTH: int = 8
    
    # Email
    SMTP_TLS: bool = True
    SMTP_PORT: Optional[int] = None
    SMTP_HOST: Optional[str] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM_EMAIL: Optional[EmailStr] = None
    EMAILS_FROM_NAME: Optional[str] = None

    @field_validator("EMAILS_FROM_NAME", mode='before')
    @classmethod
    def get_project_name(cls, v: Optional[str]) -> str:
        if not v:
            return "Often Hotels API"
        return v

    EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 48
    EMAIL_TEMPLATES_DIR: str = "/app/app/email-templates/build"
    EMAILS_ENABLED: bool = False

    @model_validator(mode='after')
    def get_emails_enabled(self) -> 'Settings':
        self.EMAILS_ENABLED = bool(
            self.SMTP_HOST
            and self.SMTP_PORT
            and self.EMAILS_FROM_EMAIL
        )
        return self

    # Superuser
    FIRST_SUPERUSER: EmailStr = "admin@oftenhotels.com"
    FIRST_SUPERUSER_PASSWORD: str = "changeme"

    # Rate limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 60  # seconds

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # Monitoring
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090

    # Testing
    TESTING: bool = False
    
    # TravClan API Configuration
    TRAVCLAN_BASE_URL: str = "https://hotel-api-sandbox.travclan.com"
    TRAVCLAN_SEARCH_API_URL: str = "https://hms-api-sandbox.travclan.com"
    TRAVCLAN_AUTH_LOGIN_URL: str = "https://trav-auth-sandbox.travclan.com/authentication/internal/service/login"
    TRAVCLAN_AUTH_REFRESH_URL: str = "https://trav-auth-sandbox.travclan.com/authentication/internal/service/refresh"
    TRAVCLAN_API_KEY: str = ""
    TRAVCLAN_MERCHANT_ID: str = ""
    TRAVCLAN_USER_ID: str = ""

    # Admin Panel Configuration
    ADMIN_EMAIL: str = "admin@oftenhotels.com"
    ADMIN_PASSWORD: str = "admin123"

    # SerpApi Configuration
    SERP_API_KEY: Optional[str] = None
    SERP_API_BASE_URL: str = "https://serpapi.com/search.json"

    # Upstash Redis Configuration
    UPSTASH_REDIS_REST_URL: Optional[str] = None
    UPSTASH_REDIS_REST_TOKEN: Optional[str] = None

    model_config = {"case_sensitive": True, "env_file": ".env"}


settings = Settings()