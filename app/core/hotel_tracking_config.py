"""
Hotel Price Tracking Configuration

This module contains configuration settings for the hotel price tracking system.
All timing and search parameters are centralized here for easy maintenance.
"""

from typing import List
from app.services.serp_service import HotelClass, Rating


class HotelTrackingConfig:
    """Configuration settings for hotel price tracking system"""
    
    # Date and Duration Settings
    START_FROM_TODAY: bool = True
    """Always start tracking from today (day 0)"""
    
    DEFAULT_STAY_DURATION_DAYS: int = 1
    """Default stay duration in days (1 night)"""
    
    USE_DESTINATION_TRACKING_DAYS: bool = True
    """Whether to use destination.numberOfDaysToTrack or global fallback"""
    
    GLOBAL_FALLBACK_TRACKING_DAYS: int = 30
    """Global fallback if destination tracking days not set"""
    
    # Search Parameters
    HOTEL_CLASS_FILTER: List[HotelClass] = [HotelClass.FOUR_STAR, HotelClass.FIVE_STAR]
    """Hotel star rating filter (4-5 stars only)"""
    
    RATING_FILTER: Rating = Rating.FOUR_PLUS
    """Minimum guest rating filter (4+ out of 5 stars, equivalent to 8+ out of 10)"""
    
    DEFAULT_ADULTS: int = 1
    """Default number of adults for pricing (single person)"""
    
    DEFAULT_CHILDREN: int = 0
    """Default number of children"""
    
    DEFAULT_CURRENCY: str = "INR"
    """Default currency for price tracking (Indian Rupees)"""
    
    DEFAULT_COUNTRY: str = "us"
    """Default country code for search localization"""
    
    DEFAULT_LANGUAGE: str = "en"
    """Default language for search results"""
    
    # Processing Settings
    MAX_HOTELS_PER_DESTINATION: int = 1000
    """Maximum number of hotels to process per destination (no practical limit - let pagination determine)"""
    
    MAX_PAGES_PER_SEARCH: int = 20
    """Maximum number of pages to fetch per search (typically ~20 hotels per page)"""
    
    API_CALL_DELAY_SECONDS: float = 1.0
    """Delay between API calls to respect rate limits"""
    
    MAX_RETRIES: int = 3
    """Maximum number of retries for failed API calls"""
    
    BATCH_SIZE: int = 10
    """Number of destinations to process in each batch"""
    
    # Data Source Settings
    DATA_SOURCE_NAME: str = "serpapi"
    """Name of the data source for price history records"""
    
    PARTNER_NAME: str = "serpapi"
    """Partner name for hotel records"""
    
    # Price History Settings
    UPDATE_SAME_DAY_PRICES: bool = True
    """Whether to update existing price records for the same day"""
    
    PRICE_CHANGE_THRESHOLD: float = 0.01
    """Minimum price change to consider significant (in currency units)"""
    
    # Logging and Monitoring
    LOG_PROGRESS_EVERY: int = 5
    """Log progress every N processed items"""
    
    TRACK_API_RESPONSE_TIME: bool = True
    """Whether to track and store API response times"""
    
    ENABLE_DETAILED_LOGGING: bool = True
    """Enable detailed logging for debugging"""


# Create a global configuration instance
tracking_config = HotelTrackingConfig()


def get_tracking_days(destination_days: int = None) -> int:
    """
    Get the number of days to track for a destination
    
    Args:
        destination_days: Number of days set on the destination
        
    Returns:
        Number of days to track
    """
    if tracking_config.USE_DESTINATION_TRACKING_DAYS and destination_days:
        return destination_days
    return tracking_config.GLOBAL_FALLBACK_TRACKING_DAYS


def get_search_criteria_defaults() -> dict:
    """
    Get default search criteria for hotel searches
    
    Returns:
        Dictionary of default search parameters
    """
    defaults = {
        "adults": tracking_config.DEFAULT_ADULTS,
        "children": tracking_config.DEFAULT_CHILDREN,
        "currency": tracking_config.DEFAULT_CURRENCY,
        "gl": tracking_config.DEFAULT_COUNTRY,
        "hl": tracking_config.DEFAULT_LANGUAGE,
    }
    
    # Only add filters if they're configured
    if tracking_config.HOTEL_CLASS_FILTER:
        defaults["hotel_class"] = tracking_config.HOTEL_CLASS_FILTER
    if tracking_config.RATING_FILTER:
        defaults["rating"] = tracking_config.RATING_FILTER
        
    return defaults