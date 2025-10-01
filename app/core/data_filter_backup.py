"""
Data Filtering Middleware and Decorators - BACKUP COPY

Implements authentication-based data filtering using the user access configuration.
Provides decorators and middleware to automatically filter API responses based on user tiers.

*** THIS IS A BACKUP OF THE ORIGINAL FILTERING LOGIC ***
*** TO RESTORE: cp data_filter_backup.py data_filter.py ***
"""

import logging
import json
from datetime import date, datetime
from decimal import Decimal
from functools import wraps
from typing import Any, Dict, List, Optional, Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse

from app.core.user_access_config import (
    UserTier, EndpointConfig, get_user_tier_from_user, 
    is_field_visible, get_masked_value, get_max_results,
    ENDPOINT_CONFIGS, DATA_EXPOSURE_RULES, PROMOTIONAL_MESSAGES
)
from app.models.models import User

logger = logging.getLogger(__name__)


class DataFilteringService:
    """Service for filtering response data based on user access levels"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def _serialize_data(self, data: Any) -> Any:
        """Convert non-JSON serializable objects to serializable format"""
        if isinstance(data, dict):
            return {key: self._serialize_data(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._serialize_data(item) for item in data]
        elif isinstance(data, date):
            return data.isoformat()
        elif isinstance(data, datetime):
            return data.isoformat()
        elif isinstance(data, Decimal):
            return float(data)
        else:
            return data
    
    def filter_response_data(
        self,
        data: Any,
        user: Optional[User],
        endpoint_path: str
    ) -> Dict[str, Any]:
        """
        Filter response data based on user tier and endpoint configuration
        
        Args:
            data: The response data to filter
            user: The authenticated user (or None for anonymous)
            endpoint_path: The API endpoint path for configuration lookup
            
        Returns:
            Filtered response data with access controls applied
        """
        user_tier = get_user_tier_from_user(user)
        endpoint_config = ENDPOINT_CONFIGS.get(endpoint_path)
        
        if not endpoint_config:
            # No filtering configuration found, return data as-is
            self.logger.warning(f"No filtering config found for endpoint: {endpoint_path}")
            return {"data": data, "user_tier": user_tier.value}
        
        # Serialize data first to handle non-JSON serializable objects
        serialized_data = self._serialize_data(data)
        
        # Apply field-level filtering
        filtered_data = self._filter_fields(serialized_data, user_tier, endpoint_config)
        
        # Apply result limiting
        filtered_data = self._apply_result_limits(filtered_data, user_tier, endpoint_config)
        
        # Add promotional messages if applicable
        response = {
            "data": filtered_data,
            "user_tier": user_tier.value
        }
        
        promo_message = self._get_promotional_message(user_tier, endpoint_path)
        if promo_message:
            response["promotion"] = promo_message
        
        return response
    
    def _filter_fields(
        self,
        data: Any,
        user_tier: UserTier,
        endpoint_config: EndpointConfig
    ) -> Any:
        """Apply field-level filtering to data"""
        
        if isinstance(data, dict):
            return self._filter_dict_fields(data, user_tier, endpoint_config)
        elif isinstance(data, list):
            return [self._filter_fields(item, user_tier, endpoint_config) for item in data]
        else:
            return data
    
    def _filter_dict_fields(
        self,
        data: Dict[str, Any],
        user_tier: UserTier,
        endpoint_config: EndpointConfig
    ) -> Dict[str, Any]:
        """Filter fields in a dictionary based on visibility rules"""
        
        filtered_data = {}
        
        for field_name, value in data.items():
            if is_field_visible(field_name, user_tier, endpoint_config):
                # Field is visible to this user tier
                if isinstance(value, (dict, list)):
                    # Recursively filter nested structures
                    filtered_data[field_name] = self._filter_fields(value, user_tier, endpoint_config)
                else:
                    filtered_data[field_name] = value
            else:
                # Field is not visible, check if we should show a masked value
                masked_value = get_masked_value(field_name, endpoint_config)
                if masked_value is not None:
                    filtered_data[field_name] = masked_value
                # If masked_value is None, field is completely hidden (not included)
        
        return filtered_data
    
    def _apply_result_limits(
        self,
        data: Any,
        user_tier: UserTier,
        endpoint_config: EndpointConfig
    ) -> Any:
        """Apply result count limits based on user tier"""
        
        max_results = get_max_results(user_tier, endpoint_config)
        
        if max_results is None:
            return data  # No limit
        
        # Special handling for itinerary optimization normal search results
        if (endpoint_config.endpoint_path == "/itineraries/optimize" and 
            isinstance(data, dict) and "normal" in data and data.get("normal")):
            
            return self._limit_month_grouped_results(data, user_tier, max_results)
        
        if isinstance(data, list):
            limited_data = data[:max_results]
            if len(data) > max_results:
                self.logger.info(f"Limited results from {len(data)} to {max_results} for tier {user_tier}")
            return limited_data
        elif isinstance(data, dict) and "results" in data:
            # Handle paginated response format
            results = data.get("results", [])
            if isinstance(results, list) and len(results) > max_results:
                data["results"] = results[:max_results]
                data["total_available"] = len(results)
                data["showing"] = max_results
                data["limited_by_tier"] = True
        
        return data
    
    def _limit_month_grouped_results(
        self,
        data: Dict[str, Any],
        user_tier: UserTier,
        max_results: int
    ) -> Dict[str, Any]:
        """Special handling for month-grouped normal search results (clean version without legacy)"""
        
        if user_tier != UserTier.ANONYMOUS or max_results != 1:
            return data  # No special handling needed
        
        # For anonymous users, find the nearest (chronologically first) option
        normal_results = data.get("normal", {})
        if not normal_results:
            return data
        
        # Work with monthly_options structure only
        monthly_options = normal_results.get("monthly_options", [])
        if not monthly_options:
            return data  # No options to filter
        
        # Find the first available option across all months
        nearest_option = None
        nearest_month = ""
        option_type = ""
        total_option_count = 0
        
        for month_data in monthly_options:
            # Count all available options
            month_options = [
                month_data.get("start_month"),
                month_data.get("mid_month"), 
                month_data.get("end_month")
            ]
            valid_month_options = [opt for opt in month_options if opt and opt.get("total_cost")]
            total_option_count += len(valid_month_options)
            
            # Find the nearest (first chronologically)
            if not nearest_option and valid_month_options:
                # Sort by start date to get the nearest
                valid_month_options.sort(key=lambda x: x.get("start_date", ""))
                nearest_option = valid_month_options[0]
                nearest_month = month_data.get("month", "")
                
                # Determine which option type it was
                option_type = "start"
                if nearest_option == month_data.get("mid_month"):
                    option_type = "mid"
                elif nearest_option == month_data.get("end_month"):
                    option_type = "end"
        
        if nearest_option:
            # Create a response that shows all months but only the single nearest option overall
            limited_data = data.copy()
            limited_monthly_options = []
            
            # Process each month and show structure, but only populate the month with the nearest option
            for month_data in monthly_options:
                month_name = month_data.get("month", "")
                
                # Create month structure with all options as null by default
                limited_month = {
                    "month": month_name,
                    "start_month": None,
                    "mid_month": None,
                    "end_month": None
                }
                
                # Only populate the option if this month contains the nearest overall option
                if month_name == nearest_month:
                    if option_type == "start":
                        limited_month["start_month"] = nearest_option
                    elif option_type == "mid":
                        limited_month["mid_month"] = nearest_option
                    elif option_type == "end":
                        limited_month["end_month"] = nearest_option
                
                limited_monthly_options.append(limited_month)
            
            limited_data["normal"] = {
                "monthly_options": limited_monthly_options
            }
            
            # Update best_itinerary to be the overall nearest option
            limited_data["best_itinerary"] = nearest_option
            
            # Add helpful message showing what they're missing
            option_label = nearest_option.get("label", f"{nearest_month} {option_type}")
            limited_data["access_message"] = f"Showing nearest option ({option_label}). Login to see all {total_option_count} timing options across available months."
            
            self.logger.info(f"Limited normal search to single nearest option ({option_label}) from {total_option_count} total options for anonymous user")
            return limited_data
        
        return data
    
    def _get_promotional_message(
        self,
        user_tier: UserTier,
        endpoint_path: str
    ) -> Optional[Dict[str, Any]]:
        """Get appropriate promotional message for user tier and endpoint"""
        
        exposure_rules = DATA_EXPOSURE_RULES.get(user_tier, {})
        if not exposure_rules.get("show_promotional_messages", False):
            return None
        
        # Determine message key based on endpoint and user tier
        if "/hotels/search" in endpoint_path:
            if user_tier == UserTier.ANONYMOUS:
                message_key = "hotel_search_anonymous"
            elif user_tier == UserTier.AUTHENTICATED:
                message_key = "hotel_search_authenticated"
            else:
                return None
        elif "/itineraries/optimize" in endpoint_path:
            if user_tier == UserTier.ANONYMOUS:
                message_key = "itinerary_anonymous"
            elif user_tier == UserTier.AUTHENTICATED:
                message_key = "itinerary_authenticated"
            else:
                return None
        else:
            return None
        
        return PROMOTIONAL_MESSAGES.get(message_key)


def filter_by_user_access(endpoint_path: str):
    """
    Decorator to automatically filter endpoint responses based on user access tier
    
    Args:
        endpoint_path: The endpoint path for configuration lookup
        
    Usage:
        @filter_by_user_access("/hotels/search")
        async def search_hotels(...):
            return data
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user from kwargs if present
            user = kwargs.get('current_user') or kwargs.get('user')
            
            # Call the original function
            result = await func(*args, **kwargs)
            
            # Apply data filtering
            filtering_service = DataFilteringService()
            filtered_result = filtering_service.filter_response_data(
                result, user, endpoint_path
            )
            
            return filtered_result
        
        return wrapper
    return decorator


def create_filtered_response(
    data: Any,
    user: Optional[User],
    endpoint_path: str,
    status_code: int = 200
) -> JSONResponse:
    """
    Create a filtered JSON response for an endpoint
    
    Args:
        data: Response data to filter
        user: Authenticated user (or None)
        endpoint_path: Endpoint path for filtering rules
        status_code: HTTP status code
        
    Returns:
        JSONResponse with filtered data
    """
    filtering_service = DataFilteringService()
    filtered_data = filtering_service.filter_response_data(data, user, endpoint_path)
    
    return JSONResponse(
        content=filtered_data,
        status_code=status_code
    )


class UserAccessMiddleware:
    """
    FastAPI middleware for automatic user access filtering
    
    This middleware can be applied globally to automatically filter
    responses based on configured endpoints.
    """
    
    def __init__(self, app):
        self.app = app
        self.filtering_service = DataFilteringService()
    
    async def __call__(self, request: Request, call_next):
        # Get the response from the endpoint
        response = await call_next(request)
        
        # Check if this endpoint has filtering configuration
        endpoint_path = self._normalize_path(request.url.path)
        if endpoint_path not in ENDPOINT_CONFIGS:
            return response
        
        # Extract user from request state if available
        user = getattr(request.state, 'user', None)
        
        # Only filter JSON responses
        if response.headers.get('content-type', '').startswith('application/json'):
            try:
                # Get response body
                body = b""
                async for chunk in response.body_iterator:
                    body += chunk
                
                # Parse and filter the response
                import json
                data = json.loads(body.decode())
                filtered_data = self.filtering_service.filter_response_data(
                    data, user, endpoint_path
                )
                
                # Create new response with filtered data
                return JSONResponse(
                    content=filtered_data,
                    status_code=response.status_code,
                    headers=dict(response.headers)
                )
            
            except Exception as e:
                logger.error(f"Error filtering response: {e}")
                return response
        
        return response
    
    def _normalize_path(self, path: str) -> str:
        """Normalize API path for configuration lookup"""
        # Remove /api/v1 prefix if present
        if path.startswith('/api/v1'):
            path = path[7:]
        return path


# Utility functions for direct use in endpoints

def get_user_access_summary(user: Optional[User]) -> Dict[str, Any]:
    """Get summary of user's access permissions"""
    user_tier = get_user_tier_from_user(user)
    rules = DATA_EXPOSURE_RULES.get(user_tier, {})
    
    return {
        "user_tier": user_tier.value,
        "permissions": rules,
        "available_endpoints": list(ENDPOINT_CONFIGS.keys())
    }


def check_field_access(
    field_name: str,
    user: Optional[User],
    endpoint_path: str
) -> bool:
    """Check if user has access to a specific field"""
    user_tier = get_user_tier_from_user(user)
    endpoint_config = ENDPOINT_CONFIGS.get(endpoint_path)
    
    if not endpoint_config:
        return True  # Default to visible if no config
    
    return is_field_visible(field_name, user_tier, endpoint_config)


def get_result_limit_for_user(
    user: Optional[User],
    endpoint_path: str
) -> Optional[int]:
    """Get result limit for user tier and endpoint"""
    user_tier = get_user_tier_from_user(user)
    endpoint_config = ENDPOINT_CONFIGS.get(endpoint_path)
    
    if not endpoint_config:
        return None
    
    return get_max_results(user_tier, endpoint_config)