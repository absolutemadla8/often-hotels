"""
User Access API Endpoints

Provides endpoints to understand and test the user access system,
including user tier information and access permissions.
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.tortoise_deps import get_optional_current_user
from app.models.models import User
from app.core.data_filter import get_user_access_summary, get_result_limit_for_user
from app.core.user_access_config import (
    get_user_tier_from_user, DATA_EXPOSURE_RULES, PROMOTIONAL_MESSAGES,
    ENDPOINT_CONFIGS
)

router = APIRouter()


@router.get("/me")
async def get_my_access_info(
    current_user: Optional[User] = Depends(get_optional_current_user)
) -> JSONResponse:
    """
    Get current user's access tier and permissions
    
    Returns comprehensive information about what data and features
    are available to the current user based on their authentication status.
    """
    user_tier = get_user_tier_from_user(current_user)
    permissions = DATA_EXPOSURE_RULES.get(user_tier, {})
    
    # Get result limits for each endpoint
    endpoint_limits = {}
    for endpoint_path in ENDPOINT_CONFIGS.keys():
        limit = get_result_limit_for_user(current_user, endpoint_path)
        endpoint_limits[endpoint_path] = limit
    
    # Get promotional messages if applicable
    promo_messages = {}
    if permissions.get("show_promotional_messages", False):
        for msg_key, msg_data in PROMOTIONAL_MESSAGES.items():
            if (user_tier.value == "anonymous" and "anonymous" in msg_key) or \
               (user_tier.value == "authenticated" and "authenticated" in msg_key):
                promo_messages[msg_key] = msg_data
    
    return JSONResponse(content={
        "user_tier": user_tier.value,
        "permissions": permissions,
        "endpoint_limits": endpoint_limits,
        "promotional_messages": promo_messages,
        "user_info": {
            "is_authenticated": current_user is not None,
            "user_id": current_user.id if current_user else None,
            "is_superuser": getattr(current_user, 'is_superuser', False) if current_user else False,
            "is_premium": getattr(current_user, 'is_premium', False) if current_user else False
        }
    })


@router.get("/tiers")
async def get_access_tiers() -> JSONResponse:
    """
    Get information about all available access tiers
    
    Returns complete documentation of the access tier system,
    including what features are available at each tier.
    """
    tier_info = {}
    
    for tier, rules in DATA_EXPOSURE_RULES.items():
        # Get limits for this tier across all endpoints
        tier_limits = {}
        for endpoint_path, config in ENDPOINT_CONFIGS.items():
            limit = config.max_results.get(tier)
            tier_limits[endpoint_path] = limit
        
        tier_info[tier.value] = {
            "permissions": rules,
            "endpoint_limits": tier_limits,
            "description": _get_tier_description(tier.value)
        }
    
    return JSONResponse(content={
        "access_tiers": tier_info,
        "upgrade_path": {
            "anonymous": "Register for free to unlock authenticated features",
            "authenticated": "Upgrade to Premium for unlimited access",
            "premium": "You have full feature access",
            "admin": "You have complete system access"
        }
    })


@router.get("/field-access/{endpoint_path}")
async def check_field_access(
    endpoint_path: str,
    current_user: Optional[User] = Depends(get_optional_current_user)
) -> JSONResponse:
    """
    Check field-level access for a specific endpoint
    
    Shows which fields are visible, hidden, or masked for the current user
    on the specified endpoint.
    """
    # Normalize endpoint path
    if not endpoint_path.startswith('/'):
        endpoint_path = '/' + endpoint_path
    
    user_tier = get_user_tier_from_user(current_user)
    endpoint_config = ENDPOINT_CONFIGS.get(endpoint_path)
    
    if not endpoint_config:
        return JSONResponse(content={
            "error": f"No access configuration found for endpoint: {endpoint_path}",
            "available_endpoints": list(ENDPOINT_CONFIGS.keys())
        }, status_code=404)
    
    field_access = {}
    for field in endpoint_config.fields:
        is_visible = user_tier in field.visible_to
        field_access[field.field_name] = {
            "visible": is_visible,
            "masked_value": field.masked_value if not is_visible else None,
            "description": field.description,
            "visible_to_tiers": [tier.value for tier in field.visible_to]
        }
    
    return JSONResponse(content={
        "endpoint": endpoint_path,
        "user_tier": user_tier.value,
        "field_access": field_access,
        "result_limit": endpoint_config.max_results.get(user_tier),
        "rate_limit": endpoint_config.rate_limits.get(user_tier, {})
    })


@router.get("/demo/{tier}")
async def demo_tier_access(tier: str) -> JSONResponse:
    """
    Demonstrate what data would be visible for a specific tier
    
    Useful for testing and understanding the access system.
    Shows sample data filtered as it would appear to different user tiers.
    """
    from app.core.user_access_config import UserTier
    from app.core.data_filter import DataFilteringService
    
    # Validate tier
    try:
        demo_tier = UserTier(tier.lower())
    except ValueError:
        return JSONResponse(content={
            "error": f"Invalid tier: {tier}",
            "valid_tiers": [t.value for t in UserTier]
        }, status_code=400)
    
    # Create sample data for demonstration
    sample_hotel_data = {
        "hotel_id": 123,
        "hotel_name": "Sample Luxury Resort",
        "star_rating": 5,
        "guest_rating": 4.8,
        "available_dates": ["2025-11-01", "2025-11-02", "2025-11-03"],
        "price_range": {"min": 150.00, "max": 300.00},
        "avg_price": 225.00,
        "total_nights_available": 3,
        "covers_full_range": True
    }
    
    sample_itinerary_data = {
        "hotel_id": 123,
        "hotel_name": "Sample Luxury Resort",
        "price": 225.00,
        "selection_reason": "cheapest_available",
        "alternatives_generated": 5,
        "processing_time_ms": 150,
        "request_hash": "abc123def456"
    }
    
    # Create mock user for tier
    mock_user = None
    if demo_tier != UserTier.ANONYMOUS:
        class MockUser:
            def __init__(self, tier: UserTier):
                self.id = 999
                self.is_superuser = tier == UserTier.ADMIN
                self.is_premium = tier in [UserTier.PREMIUM, UserTier.ADMIN]
        
        mock_user = MockUser(demo_tier)
    
    # Apply filtering
    filtering_service = DataFilteringService()
    
    hotel_filtered = filtering_service.filter_response_data(
        sample_hotel_data, mock_user, "/hotels/search"
    )
    
    itinerary_filtered = filtering_service.filter_response_data(
        sample_itinerary_data, mock_user, "/itineraries/optimize"
    )
    
    return JSONResponse(content={
        "demonstration_tier": demo_tier.value,
        "sample_data": {
            "hotel_search": hotel_filtered,
            "itinerary_optimization": itinerary_filtered
        },
        "explanation": f"This shows how data would appear to a {demo_tier.value} user"
    })


def _get_tier_description(tier: str) -> str:
    """Get human-readable description of access tier"""
    descriptions = {
        "anonymous": "Unregistered users with limited access to encourage signup",
        "authenticated": "Registered users with core functionality access",
        "premium": "Paid subscribers with advanced features and unlimited access",
        "admin": "System administrators with complete access and debug information"
    }
    return descriptions.get(tier, "Unknown tier")