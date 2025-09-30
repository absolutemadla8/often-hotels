# All models are now consolidated in models.py using Tortoise ORM
from .models import (
    # Core models
    User,
    RefreshToken,

    # Geography models
    Country,
    Destination,
    Area,

    # Cluster system
    Cluster,
    ClusterItem,
    ClusterType,
    ClusterItemType,

    # Aviation models
    Airport,
    Flight,
    AirportType,
    AirportSize,
    FlightType,
    FlightStatus,
    Aircraft,

    # Hotel models
    Hotel,
    Room,
    HotelType,
    HotelChain,
    RoomType,
    BedType,

    # Polymorphic models (new architecture)
    UniversalBooking,
    UniversalPriceHistory,
    UniversalPriceAlert,
    BookableType,
    TrackableType,
    BookingStatus,
    NotificationStatus,
    PaymentStatus,

    # Tracker system
    Tracker,
    TrackerResult,
    TrackerAlert,
    TrackerType,
    TrackerStatus,
    TrackerFrequency,
    AlertTrigger,
    
    # Task system
    Task,
    TaskLog,
    TaskStatus,
    LogLevel,
    
    # Itinerary system
    Itinerary,
    ItineraryDestination,
    ItineraryHotelAssignment,
    ItinerarySearchRequest,
    SearchType,
    ItineraryStatus,
)

__all__ = [
    # Core models
    "User",
    "RefreshToken",

    # Geography models
    "Country",
    "Destination",
    "Area",

    # Cluster system
    "Cluster",
    "ClusterItem",
    "ClusterType",
    "ClusterItemType",

    # Aviation models
    "Airport",
    "Flight",
    "AirportType",
    "AirportSize",
    "FlightType",
    "FlightStatus",
    "Aircraft",

    # Hotel models
    "Hotel",
    "Room",
    "HotelType",
    "HotelChain",
    "RoomType",
    "BedType",

    # Polymorphic models (new architecture)
    "UniversalBooking",
    "UniversalPriceHistory",
    "UniversalPriceAlert",
    "BookableType",
    "TrackableType",
    "BookingStatus",
    "NotificationStatus",
    "PaymentStatus",

    # Tracker system
    "Tracker",
    "TrackerResult",
    "TrackerAlert",
    "TrackerType",
    "TrackerStatus",
    "TrackerFrequency",
    "AlertTrigger",
    
    # Task system
    "Task",
    "TaskLog",
    "TaskStatus",
    "LogLevel",
    
    # Itinerary system
    "Itinerary",
    "ItineraryDestination",
    "ItineraryHotelAssignment",
    "ItinerarySearchRequest",
    "SearchType",
    "ItineraryStatus",
]