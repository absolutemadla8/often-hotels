"""
User Access Configuration

Defines what data is exposed to different user types:
- Unauthenticated users (anonymous)
- Authenticated users (logged in)
- Premium users (paid subscription)
- Admin users (full access)

This follows a freemium model where basic data is shown to encourage registration,
while detailed data requires authentication.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel


class UserTier(str, Enum):
    """User access tiers"""
    ANONYMOUS = "anonymous"
    AUTHENTICATED = "authenticated" 
    PREMIUM = "premium"
    ADMIN = "admin"


class DataField(BaseModel):
    """Configuration for a specific data field"""
    field_name: str
    visible_to: List[UserTier]
    masked_value: Optional[Any] = None  # Value to show instead when hidden
    description: Optional[str] = None


class EndpointConfig(BaseModel):
    """Configuration for an API endpoint"""
    endpoint_path: str
    fields: List[DataField]
    max_results: Dict[UserTier, Optional[int]]  # Result limits per user tier
    rate_limits: Dict[UserTier, Dict[str, int]]  # Rate limits per user tier


# Hotel Search Endpoint Configuration
HOTEL_SEARCH_CONFIG = EndpointConfig(
    endpoint_path="/hotels/search",
    fields=[
        DataField(
            field_name="hotel_id",
            visible_to=[UserTier.AUTHENTICATED, UserTier.PREMIUM, UserTier.ADMIN],
            masked_value=None,
            description="Hotel database ID - required for booking"
        ),
        DataField(
            field_name="hotel_name",
            visible_to=[UserTier.ANONYMOUS, UserTier.AUTHENTICATED, UserTier.PREMIUM, UserTier.ADMIN],
            description="Hotel name - always visible"
        ),
        DataField(
            field_name="star_rating",
            visible_to=[UserTier.ANONYMOUS, UserTier.AUTHENTICATED, UserTier.PREMIUM, UserTier.ADMIN],
            description="Hotel star rating - marketing data"
        ),
        DataField(
            field_name="guest_rating",
            visible_to=[UserTier.AUTHENTICATED, UserTier.PREMIUM, UserTier.ADMIN],
            masked_value="Login to see ratings",
            description="Guest reviews - premium feature"
        ),
        DataField(
            field_name="available_dates",
            visible_to=[UserTier.AUTHENTICATED, UserTier.PREMIUM, UserTier.ADMIN],
            masked_value=[],
            description="Exact availability - requires authentication"
        ),
        DataField(
            field_name="price_range",
            visible_to=[UserTier.ANONYMOUS, UserTier.AUTHENTICATED, UserTier.PREMIUM, UserTier.ADMIN],
            description="Price range - limited for anonymous users"
        ),
        DataField(
            field_name="avg_price", 
            visible_to=[UserTier.AUTHENTICATED, UserTier.PREMIUM, UserTier.ADMIN],
            masked_value="Login for pricing",
            description="Average price - requires login"
        ),
        DataField(
            field_name="total_nights_available",
            visible_to=[UserTier.AUTHENTICATED, UserTier.PREMIUM, UserTier.ADMIN],
            masked_value=None,
            description="Availability count - authenticated only"
        ),
        DataField(
            field_name="covers_full_range",
            visible_to=[UserTier.AUTHENTICATED, UserTier.PREMIUM, UserTier.ADMIN],
            masked_value=None,
            description="Full coverage indicator - authenticated only"
        )
    ],
    max_results={
        UserTier.ANONYMOUS: 5,       # Only show 5 hotels to encourage signup
        UserTier.AUTHENTICATED: 50,  # Show more hotels after login
        UserTier.PREMIUM: None,      # No limit for premium users
        UserTier.ADMIN: None         # No limit for admin
    },
    rate_limits={
        UserTier.ANONYMOUS: {"requests": 10, "per_minutes": 60},      # 10 requests per hour
        UserTier.AUTHENTICATED: {"requests": 100, "per_minutes": 60}, # 100 requests per hour  
        UserTier.PREMIUM: {"requests": 500, "per_minutes": 60},       # 500 requests per hour
        UserTier.ADMIN: {"requests": 1000, "per_minutes": 60}         # 1000 requests per hour
    }
)


# Itinerary Optimization Endpoint Configuration  
ITINERARY_OPTIMIZATION_CONFIG = EndpointConfig(
    endpoint_path="/itineraries/optimize",
    fields=[
        DataField(
            field_name="hotel_id",
            visible_to=[UserTier.AUTHENTICATED, UserTier.PREMIUM, UserTier.ADMIN],
            masked_value=None,
            description="Hotel IDs - required for booking"
        ),
        DataField(
            field_name="hotel_name",
            visible_to=[UserTier.ANONYMOUS, UserTier.AUTHENTICATED, UserTier.PREMIUM, UserTier.ADMIN],
            description="Hotel names - always visible"
        ),
        DataField(
            field_name="price",
            visible_to=[UserTier.AUTHENTICATED, UserTier.PREMIUM, UserTier.ADMIN],
            masked_value="Login for pricing",
            description="Exact prices - premium feature"
        ),
        DataField(
            field_name="selection_reason",
            visible_to=[UserTier.PREMIUM, UserTier.ADMIN],
            masked_value="Upgrade for insights",
            description="Algorithm insights - premium feature"
        ),
        DataField(
            field_name="alternatives_generated",
            visible_to=[UserTier.PREMIUM, UserTier.ADMIN],
            masked_value=None,
            description="Optimization details - premium feature"
        ),
        DataField(
            field_name="processing_time_ms",
            visible_to=[UserTier.PREMIUM, UserTier.ADMIN],
            masked_value=None,
            description="Performance metrics - premium feature"
        ),
        DataField(
            field_name="request_hash",
            visible_to=[UserTier.AUTHENTICATED, UserTier.PREMIUM, UserTier.ADMIN],
            masked_value=None,
            description="Cache key - authenticated feature"
        )
    ],
    max_results={
        UserTier.ANONYMOUS: 1,       # Only 1 basic itinerary option
        UserTier.AUTHENTICATED: 3,   # Standard 3 options  
        UserTier.PREMIUM: None,      # All available options
        UserTier.ADMIN: None         # All available options
    },
    rate_limits={
        UserTier.ANONYMOUS: {"requests": 3, "per_minutes": 60},       # 3 optimizations per hour
        UserTier.AUTHENTICATED: {"requests": 20, "per_minutes": 60},  # 20 optimizations per hour
        UserTier.PREMIUM: {"requests": 100, "per_minutes": 60},       # 100 optimizations per hour  
        UserTier.ADMIN: {"requests": 500, "per_minutes": 60}          # 500 optimizations per hour
    }
)


# General Data Exposure Rules
DATA_EXPOSURE_RULES = {
    # Anonymous users see basic info to encourage signup
    UserTier.ANONYMOUS: {
        "show_hotel_ids": False,
        "show_exact_prices": False,
        "show_availability_details": False,
        "show_optimization_insights": False,
        "max_search_results": 5,
        "max_itinerary_options": 1,
        "show_promotional_messages": True
    },
    
    # Authenticated users get core functionality
    UserTier.AUTHENTICATED: {
        "show_hotel_ids": True,
        "show_exact_prices": True,
        "show_availability_details": True,
        "show_optimization_insights": False,
        "max_search_results": 50,
        "max_itinerary_options": 3,
        "show_promotional_messages": True  # Promote premium features
    },
    
    # Premium users get advanced features and insights
    UserTier.PREMIUM: {
        "show_hotel_ids": True,
        "show_exact_prices": True,
        "show_availability_details": True,
        "show_optimization_insights": True,
        "max_search_results": None,  # No limit
        "max_itinerary_options": None,  # No limit
        "show_promotional_messages": False
    },
    
    # Admin users get everything
    UserTier.ADMIN: {
        "show_hotel_ids": True,
        "show_exact_prices": True,
        "show_availability_details": True,
        "show_optimization_insights": True,
        "max_search_results": None,
        "max_itinerary_options": None,
        "show_promotional_messages": False,
        "show_debug_info": True
    }
}


# Promotional Messages for Different Scenarios
PROMOTIONAL_MESSAGES = {
    "hotel_search_anonymous": {
        "message": "Login to see all available hotels and exact pricing",
        "cta": "Sign up for free",
        "benefits": ["View all hotels", "See exact prices", "Get availability details"]
    },
    "hotel_search_authenticated": {
        "message": "Upgrade to Premium for unlimited searches and advanced insights",
        "cta": "Upgrade to Premium", 
        "benefits": ["Unlimited searches", "Algorithm insights", "Priority support"]
    },
    "itinerary_anonymous": {
        "message": "Login to unlock multiple itinerary options and exact pricing",
        "cta": "Create free account",
        "benefits": ["3 itinerary options", "Exact pricing", "Hotel booking access"]
    },
    "itinerary_authenticated": {
        "message": "Upgrade to Premium for unlimited optimizations and insights",
        "cta": "Go Premium",
        "benefits": ["Unlimited optimizations", "Algorithm insights", "Advanced preferences"]
    }
}


def get_user_tier_from_user(user: Optional[Any]) -> UserTier:
    """Determine user tier from user object"""
    if not user:
        return UserTier.ANONYMOUS
    
    # Check if user is admin (superuser)
    if hasattr(user, 'is_superuser') and user.is_superuser:
        return UserTier.ADMIN
    
    # Check if user has premium subscription
    if hasattr(user, 'is_premium') and user.is_premium:
        return UserTier.PREMIUM
    
    # Authenticated user
    return UserTier.AUTHENTICATED


def is_field_visible(field_name: str, user_tier: UserTier, endpoint_config: EndpointConfig) -> bool:
    """Check if a field should be visible to the user tier"""
    for field in endpoint_config.fields:
        if field.field_name == field_name:
            return user_tier in field.visible_to
    return True  # Default to visible if not configured


def get_masked_value(field_name: str, endpoint_config: EndpointConfig) -> Any:
    """Get the masked value for a hidden field"""
    for field in endpoint_config.fields:
        if field.field_name == field_name:
            return field.masked_value
    return None


def get_max_results(user_tier: UserTier, endpoint_config: EndpointConfig) -> Optional[int]:
    """Get maximum results allowed for user tier"""
    return endpoint_config.max_results.get(user_tier)


def get_rate_limits(user_tier: UserTier, endpoint_config: EndpointConfig) -> Dict[str, int]:
    """Get rate limits for user tier"""
    return endpoint_config.rate_limits.get(user_tier, {"requests": 10, "per_minutes": 60})


# Export configurations
ENDPOINT_CONFIGS = {
    "/hotels/search": HOTEL_SEARCH_CONFIG,
    "/itineraries/optimize": ITINERARY_OPTIMIZATION_CONFIG
}