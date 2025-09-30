from datetime import datetime, date, time
from enum import Enum
from typing import List, Dict, Any, Optional

from tortoise import fields
from tortoise.models import Model


# Enums for all models
class ClusterType(str, Enum):
    GEOGRAPHIC = "geographic"
    THEMATIC = "thematic"
    SEASONAL = "seasonal"
    PRICE_TIER = "price_tier"
    TRAVEL_STYLE = "travel_style"
    CUSTOM = "custom"


class ClusterItemType(str, Enum):
    COUNTRY = "country"
    DESTINATION = "destination"
    AREA = "area"
    AIRPORT = "airport"
    HOTEL = "hotel"
    FLIGHT_ROUTE = "flight_route"


class AirportType(str, Enum):
    INTERNATIONAL = "international"
    DOMESTIC = "domestic"
    REGIONAL = "regional"
    PRIVATE = "private"
    CARGO = "cargo"
    MILITARY = "military"


class AirportSize(str, Enum):
    LARGE = "large"
    MEDIUM = "medium"
    SMALL = "small"
    REGIONAL = "regional"


class TaskStatus(str, Enum):
    PENDING = "pending"
    STARTED = "started"
    SUCCESS = "success"
    FAILURE = "failure"
    RETRY = "retry"
    REVOKED = "revoked"


class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class FlightType(str, Enum):
    SCHEDULED = "scheduled"
    CHARTER = "charter"
    CARGO = "cargo"
    PRIVATE = "private"


class FlightStatus(str, Enum):
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    CANCELLED = "cancelled"
    DELAYED = "delayed"
    COMPLETED = "completed"


class Aircraft(str, Enum):
    NARROW_BODY = "narrow_body"
    WIDE_BODY = "wide_body"
    REGIONAL = "regional"
    TURBOPROP = "turboprop"
    PRIVATE_JET = "private_jet"
    OTHER = "other"


class HotelType(str, Enum):
    HOTEL = "hotel"
    RESORT = "resort"
    APARTHOTEL = "aparthotel"
    HOSTEL = "hostel"
    GUESTHOUSE = "guesthouse"
    VILLA = "villa"
    APARTMENT = "apartment"
    MOTEL = "motel"
    BOUTIQUE = "boutique"
    LUXURY = "luxury"
    BUSINESS = "business"


class HotelChain(str, Enum):
    INDEPENDENT = "independent"
    MARRIOTT = "marriott"
    HILTON = "hilton"
    IHG = "ihg"
    HYATT = "hyatt"
    ACCOR = "accor"
    CHOICE = "choice"
    WYNDHAM = "wyndham"
    BEST_WESTERN = "best_western"
    OTHER = "other"


class RoomType(str, Enum):
    STANDARD = "standard"
    DELUXE = "deluxe"
    SUPERIOR = "superior"
    SUITE = "suite"
    JUNIOR_SUITE = "junior_suite"
    PRESIDENTIAL = "presidential"
    FAMILY = "family"
    CONNECTING = "connecting"
    ACCESSIBLE = "accessible"
    STUDIO = "studio"
    APARTMENT = "apartment"
    VILLA = "villa"


class BedType(str, Enum):
    SINGLE = "single"
    TWIN = "twin"
    DOUBLE = "double"
    QUEEN = "queen"
    KING = "king"
    SOFA_BED = "sofa_bed"
    BUNK_BED = "bunk_bed"
    MURPHY_BED = "murphy_bed"


class BookableType(str, Enum):
    HOTEL = "hotel"
    FLIGHT = "flight"
    PACKAGE = "package"
    ACTIVITY = "activity"
    TRANSFER = "transfer"
    INSURANCE = "insurance"


class TrackableType(str, Enum):
    HOTEL_ROOM = "hotel_room"
    FLIGHT = "flight"
    PACKAGE = "package"
    ACTIVITY = "activity"


class BookingStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    BOOKED = "booked"
    COMPLETED = "completed"


class NotificationStatus(str, Enum):
    ENABLED = "enabled"
    DISABLED = "disabled"
    PAUSED = "paused"
    FREQUENCY_LIMITED = "frequency_limited"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    PARTIALLY_PAID = "partially_paid"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class TrackerType(str, Enum):
    HOTEL_SEARCH = "hotel_search"
    FLIGHT_SEARCH = "flight_search"
    MIXED_SEARCH = "mixed_search"
    CUSTOM_LIST = "custom_list"


class TrackerStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    EXPIRED = "expired"
    ERROR = "error"
    COMPLETED = "completed"


class TrackerFrequency(str, Enum):
    REALTIME = "realtime"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    DAILY = "daily"
    CUSTOM = "custom"


class AlertTrigger(str, Enum):
    PRICE_DROP = "price_drop"
    PRICE_INCREASE = "price_increase"
    AVAILABILITY_CHANGE = "availability_change"
    NEW_OPTIONS = "new_options"
    BEST_DEAL = "best_deal"
    ALL_CHANGES = "all_changes"


# Core Models
class User(Model):
    id = fields.IntField(pk=True)
    email = fields.CharField(max_length=255, unique=True)
    hashed_password = fields.CharField(max_length=255)
    full_name = fields.CharField(max_length=100, null=True)
    is_active = fields.BooleanField(default=True)
    is_superuser = fields.BooleanField(default=False)
    password_reset_token = fields.CharField(max_length=500, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "users"


class RefreshToken(Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="refresh_tokens", on_delete=fields.CASCADE)
    token = fields.CharField(max_length=255, unique=True)
    expires_at = fields.DatetimeField()
    is_revoked = fields.BooleanField(default=False)
    is_active = fields.BooleanField(default=True)
    user_agent = fields.CharField(max_length=500, null=True)
    ip_address = fields.CharField(max_length=45, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "refresh_tokens"


# Geography Models
class Country(Model):
    id = fields.IntField(pk=True)
    iso_code_2 = fields.CharField(max_length=2, unique=True)
    iso_code_3 = fields.CharField(max_length=3, unique=True)
    numeric_code = fields.CharField(max_length=3, null=True)
    name = fields.CharField(max_length=100)
    official_name = fields.CharField(max_length=255, null=True)
    common_name = fields.CharField(max_length=100, null=True)
    continent = fields.CharField(max_length=50, null=True)
    region = fields.CharField(max_length=100, null=True)
    sub_region = fields.CharField(max_length=100, null=True)
    currency_code = fields.CharField(max_length=3, null=True)
    currency_name = fields.CharField(max_length=50, null=True)
    languages = fields.JSONField(null=True)
    capital_city = fields.CharField(max_length=100, null=True)
    latitude = fields.FloatField(null=True)
    longitude = fields.FloatField(null=True)
    calling_code = fields.CharField(max_length=10, null=True)
    timezone_info = fields.JSONField(null=True)
    popular_destinations = fields.JSONField(null=True)
    is_active = fields.BooleanField(default=True)
    is_popular = fields.BooleanField(default=False)
    travel_restrictions = fields.JSONField(null=True)
    external_ids = fields.JSONField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    destinations: fields.ReverseRelation["Destination"]
    areas: fields.ReverseRelation["Area"]
    airports: fields.ReverseRelation["Airport"]
    hotels: fields.ReverseRelation["Hotel"]

    class Meta:
        table = "countries"

    def __str__(self):
        return self.name


class Destination(Model):
    id = fields.IntField(pk=True)
    country = fields.ForeignKeyField("models.Country", related_name="destinations", on_delete=fields.CASCADE)
    name = fields.CharField(max_length=100)
    display_name = fields.CharField(max_length=150, null=True)
    local_name = fields.CharField(max_length=100, null=True)
    destination_type = fields.CharField(max_length=50, default="city")
    state_province = fields.CharField(max_length=100, null=True)
    administrative_area = fields.CharField(max_length=100, null=True)
    latitude = fields.FloatField()
    longitude = fields.FloatField()
    description = fields.TextField(null=True)
    population = fields.IntField(null=True)
    area_km2 = fields.FloatField(null=True)
    elevation_m = fields.IntField(null=True)
    tourist_rating = fields.FloatField(null=True)
    best_visit_months = fields.JSONField(null=True)
    climate_type = fields.CharField(max_length=50, null=True)
    famous_attractions = fields.JSONField(null=True)
    timezone = fields.CharField(max_length=50, null=True)
    airport_codes = fields.JSONField(null=True)
    common_languages = fields.JSONField(null=True)
    external_ids = fields.JSONField(null=True)
    google_place_id = fields.CharField(max_length=255, null=True)
    is_active = fields.BooleanField(default=True)
    is_popular = fields.BooleanField(default=False)
    is_capital = fields.BooleanField(default=False)
    priority_score = fields.IntField(default=0)
    slug = fields.CharField(max_length=100, null=True, unique=True)
    meta_description = fields.TextField(null=True)
    keywords = fields.JSONField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    tracking   = fields.BooleanField(default=False)
    numberofdaystotrack = fields.IntField(default=3)

    areas: fields.ReverseRelation["Area"]
    airports: fields.ReverseRelation["Airport"]
    hotels: fields.ReverseRelation["Hotel"]

    class Meta:
        table = "destinations"

    def __str__(self):
        return f"{self.name}, {self.country.name}"


class Area(Model):
    id = fields.IntField(pk=True)
    destination = fields.ForeignKeyField("models.Destination", related_name="areas", on_delete=fields.CASCADE)
    country = fields.ForeignKeyField("models.Country", related_name="areas", on_delete=fields.CASCADE)
    parent_area = fields.ForeignKeyField("models.Area", related_name="sub_areas", on_delete=fields.SET_NULL, null=True)
    name = fields.CharField(max_length=100)
    display_name = fields.CharField(max_length=150, null=True)
    local_name = fields.CharField(max_length=100, null=True)
    area_type = fields.CharField(max_length=50, default="district")
    area_level = fields.IntField(default=1)
    latitude = fields.FloatField(null=True)
    longitude = fields.FloatField(null=True)
    boundary_coordinates = fields.JSONField(null=True)
    description = fields.TextField(null=True)
    characteristics = fields.JSONField(null=True)
    popular_for = fields.JSONField(null=True)
    transport_hubs = fields.JSONField(null=True)
    walkability_score = fields.FloatField(null=True)
    hotel_density = fields.CharField(max_length=20, null=True)
    attraction_count = fields.IntField(default=0)
    restaurant_count = fields.IntField(default=0)
    avg_hotel_price_range = fields.CharField(max_length=20, null=True)
    external_ids = fields.JSONField(null=True)
    google_place_id = fields.CharField(max_length=255, null=True)
    is_active = fields.BooleanField(default=True)
    is_popular = fields.BooleanField(default=False)
    tracking = fields.BooleanField(default=False)
    priority_score = fields.IntField(default=0)
    slug = fields.CharField(max_length=100, null=True)
    meta_description = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    hotels: fields.ReverseRelation["Hotel"]
    sub_areas: fields.ReverseRelation["Area"]

    class Meta:
        table = "areas"

    def __str__(self):
        return f"{self.name}, {self.destination.name}"


# Cluster System
class Cluster(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=200)
    display_name = fields.CharField(max_length=255, null=True)
    description = fields.TextField(null=True)
    cluster_type = fields.CharEnumField(ClusterType, default=ClusterType.GEOGRAPHIC)
    category = fields.CharField(max_length=100, null=True)
    subcategory = fields.CharField(max_length=100, null=True)
    is_system_cluster = fields.BooleanField(default=False)
    is_dynamic = fields.BooleanField(default=False)
    update_rules = fields.JSONField(null=True)
    icon_name = fields.CharField(max_length=50, null=True)
    color_code = fields.CharField(max_length=7, null=True)
    sort_order = fields.IntField(default=0)
    bounding_box = fields.JSONField(null=True)
    center_latitude = fields.CharField(max_length=20, null=True)
    center_longitude = fields.CharField(max_length=20, null=True)
    total_items = fields.IntField(default=0)
    item_type_counts = fields.JSONField(null=True)
    popularity_score = fields.IntField(default=0)
    external_ids = fields.JSONField(null=True)
    tags = fields.JSONField(null=True)
    is_active = fields.BooleanField(default=True)
    is_public = fields.BooleanField(default=True)
    is_featured = fields.BooleanField(default=False)
    slug = fields.CharField(max_length=100, null=True, unique=True)
    meta_title = fields.CharField(max_length=200, null=True)
    meta_description = fields.TextField(null=True)
    keywords = fields.JSONField(null=True)
    created_by_user = fields.ForeignKeyField("models.User", related_name="created_clusters", on_delete=fields.SET_NULL, null=True)
    is_shared = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    last_recalculated = fields.DatetimeField(null=True)

    items: fields.ReverseRelation["ClusterItem"]
    trackers: fields.ReverseRelation["Tracker"]

    class Meta:
        table = "clusters"

    def __str__(self):
        return self.name


class ClusterItem(Model):
    id = fields.IntField(pk=True)
    cluster = fields.ForeignKeyField("models.Cluster", related_name="items", on_delete=fields.CASCADE)
    item_type = fields.CharEnumField(ClusterItemType)
    item_id = fields.IntField()
    item_name = fields.CharField(max_length=255, null=True)
    item_display_name = fields.CharField(max_length=255, null=True)
    item_description = fields.TextField(null=True)
    latitude = fields.CharField(max_length=20, null=True)
    longitude = fields.CharField(max_length=20, null=True)
    country = fields.ForeignKeyField("models.Country", related_name="cluster_items", on_delete=fields.CASCADE, null=True)
    destination = fields.ForeignKeyField("models.Destination", related_name="cluster_items", on_delete=fields.CASCADE, null=True)
    weight = fields.IntField(default=1)
    sort_order = fields.IntField(default=0)
    is_primary = fields.BooleanField(default=False)
    custom_attributes = fields.JSONField(null=True)
    inclusion_reason = fields.CharField(max_length=200, null=True)
    auto_added = fields.BooleanField(default=False)
    rule_criteria = fields.JSONField(null=True)
    is_active = fields.BooleanField(default=True)
    is_validated = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    last_validated = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "cluster_items"
        unique_together = (("cluster", "item_type", "item_id"),)

    def __str__(self):
        return f"{self.item_name} ({self.item_type})"


# Aviation Models
class Airport(Model):
    id = fields.IntField(pk=True)
    country = fields.ForeignKeyField("models.Country", related_name="airports", on_delete=fields.CASCADE)
    destination = fields.ForeignKeyField("models.Destination", related_name="airports", on_delete=fields.SET_NULL, null=True)
    iata_code = fields.CharField(max_length=3, unique=True)
    icao_code = fields.CharField(max_length=4, unique=True, null=True)
    faa_code = fields.CharField(max_length=4, null=True)
    name = fields.CharField(max_length=255)
    official_name = fields.CharField(max_length=300, null=True)
    common_name = fields.CharField(max_length=200, null=True)
    local_name = fields.CharField(max_length=255, null=True)
    city = fields.CharField(max_length=100)
    state_province = fields.CharField(max_length=100, null=True)
    latitude = fields.FloatField()
    longitude = fields.FloatField()
    elevation_ft = fields.IntField(null=True)
    elevation_m = fields.IntField(null=True)
    airport_type = fields.CharEnumField(AirportType, default=AirportType.INTERNATIONAL)
    airport_size = fields.CharEnumField(AirportSize, default=AirportSize.MEDIUM)
    timezone = fields.CharField(max_length=50)
    utc_offset = fields.CharField(max_length=10, null=True)
    runway_count = fields.IntField(null=True)
    terminal_count = fields.IntField(null=True)
    annual_passengers = fields.IntField(null=True)
    cargo_capacity_tons = fields.IntField(null=True)
    facilities = fields.JSONField(null=True)
    airlines = fields.JSONField(null=True)
    car_rental_companies = fields.JSONField(null=True)
    ground_transport = fields.JSONField(null=True)
    distance_to_city_km = fields.FloatField(null=True)
    drive_time_minutes = fields.IntField(null=True)
    external_ids = fields.JSONField(null=True)
    google_place_id = fields.CharField(max_length=255, null=True)
    is_hub = fields.BooleanField(default=False)
    is_international = fields.BooleanField(default=True)
    passenger_rating = fields.FloatField(null=True)
    on_time_performance = fields.FloatField(null=True)
    is_active = fields.BooleanField(default=True)
    is_operational = fields.BooleanField(default=True)
    operational_notes = fields.TextField(null=True)
    slug = fields.CharField(max_length=100, null=True, unique=True)
    description = fields.TextField(null=True)
    meta_description = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    last_verified = fields.DatetimeField(null=True)

    departure_flights: fields.ReverseRelation["Flight"]
    arrival_flights: fields.ReverseRelation["Flight"]

    class Meta:
        table = "airports"

    def __str__(self):
        return f"{self.iata_code} - {self.name}"


class Flight(Model):
    id = fields.IntField(pk=True)
    departure_airport = fields.ForeignKeyField("models.Airport", related_name="departure_flights", on_delete=fields.CASCADE)
    arrival_airport = fields.ForeignKeyField("models.Airport", related_name="arrival_flights", on_delete=fields.CASCADE)
    flight_number = fields.CharField(max_length=20)
    airline_code = fields.CharField(max_length=3)
    airline_name = fields.CharField(max_length=100)
    aircraft_type = fields.CharEnumField(Aircraft, null=True)
    aircraft_code = fields.CharField(max_length=10, null=True)
    flight_type = fields.CharEnumField(FlightType, default=FlightType.SCHEDULED)
    departure_time_utc = fields.DatetimeField()
    arrival_time_utc = fields.DatetimeField()
    departure_time_local = fields.DatetimeField()
    arrival_time_local = fields.DatetimeField()
    duration_minutes = fields.IntField()
    distance_km = fields.IntField(null=True)
    distance_miles = fields.IntField(null=True)
    operates_on = fields.JSONField(null=True)
    valid_from = fields.DateField(null=True)
    valid_to = fields.DateField(null=True)
    seasonal_info = fields.JSONField(null=True)
    cabin_classes = fields.JSONField()
    total_seats = fields.IntField(null=True)
    seat_configuration = fields.JSONField(null=True)
    services = fields.JSONField(null=True)
    baggage_policy = fields.JSONField(null=True)
    meal_service = fields.JSONField(null=True)
    external_ids = fields.JSONField(null=True)
    external_flight_data = fields.JSONField(null=True)
    typical_price_ranges = fields.JSONField(null=True)
    price_currency = fields.CharField(max_length=3, default="USD")
    status = fields.CharEnumField(FlightStatus, default=FlightStatus.ACTIVE)
    is_bookable = fields.BooleanField(default=True)
    is_codeshare = fields.BooleanField(default=False)
    operating_airline = fields.CharField(max_length=100, null=True)
    is_popular_route = fields.BooleanField(default=False)
    route_popularity_score = fields.IntField(default=0)
    on_time_performance = fields.FloatField(null=True)
    last_price_update = fields.DatetimeField(null=True)
    data_source = fields.CharField(max_length=100, null=True)
    api_last_updated = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "flights"
        unique_together = (("flight_number", "airline_code", "departure_time_utc"),)

    def __str__(self):
        return f"{self.airline_code}{self.flight_number} ({self.departure_airport.iata_code}-{self.arrival_airport.iata_code})"


# Hotel Models
class Hotel(Model):
    id = fields.IntField(pk=True)
    country = fields.ForeignKeyField("models.Country", related_name="hotels", on_delete=fields.CASCADE)
    destination = fields.ForeignKeyField("models.Destination", related_name="hotels", on_delete=fields.CASCADE)
    area = fields.ForeignKeyField("models.Area", related_name="hotels", on_delete=fields.SET_NULL, null=True)
    external_id = fields.CharField(max_length=255, unique=True)
    partner_name = fields.CharField(max_length=100)
    name = fields.CharField(max_length=255)
    display_name = fields.CharField(max_length=300, null=True)
    brand_name = fields.CharField(max_length=100, null=True)
    description = fields.TextField(null=True)
    short_description = fields.CharField(max_length=500, null=True)
    address = fields.TextField()
    city = fields.CharField(max_length=100)
    postal_code = fields.CharField(max_length=20, null=True)
    latitude = fields.FloatField(null=True)
    longitude = fields.FloatField(null=True)
    hotel_type = fields.CharEnumField(HotelType, default=HotelType.HOTEL)
    hotel_chain = fields.CharEnumField(HotelChain, default=HotelChain.INDEPENDENT)
    star_rating = fields.IntField(null=True)
    official_rating = fields.CharField(max_length=20, null=True)
    guest_rating = fields.FloatField(null=True)
    guest_rating_count = fields.IntField(default=0)
    phone_number = fields.CharField(max_length=50, null=True)
    email = fields.CharField(max_length=255, null=True)
    website_url = fields.CharField(max_length=500, null=True)
    year_built = fields.IntField(null=True)
    year_renovated = fields.IntField(null=True)
    total_rooms = fields.IntField(null=True)
    total_floors = fields.IntField(null=True)
    check_in_time = fields.CharField(max_length=10, null=True)
    check_out_time = fields.CharField(max_length=10, null=True)
    amenities = fields.JSONField(null=True)
    images = fields.JSONField(null=True)
    facilities = fields.JSONField(null=True)
    accessibility_features = fields.JSONField(null=True)
    pet_policy = fields.JSONField(null=True)
    children_policy = fields.JSONField(null=True)
    is_active = fields.BooleanField(default=True)
    is_bookable = fields.BooleanField(default=True)
    is_featured = fields.BooleanField(default=False)
    is_popular = fields.BooleanField(default=False)
    business_center = fields.BooleanField(default=False)
    meeting_rooms = fields.IntField(default=0)
    conference_facilities = fields.JSONField(null=True)
    sustainability_certifications = fields.JSONField(null=True)
    sustainability_score = fields.FloatField(null=True)
    currency = fields.CharField(max_length=3, default="USD")
    typical_price_range = fields.CharField(max_length=20, null=True)
    price_level = fields.IntField(null=True)
    api_last_updated = fields.DatetimeField(null=True)
    api_data = fields.JSONField(null=True)
    external_ids = fields.JSONField(null=True)
    slug = fields.CharField(max_length=200, null=True, unique=True)
    meta_title = fields.CharField(max_length=200, null=True)
    meta_description = fields.TextField(null=True)
    keywords = fields.JSONField(null=True)
    view_count = fields.IntField(default=0)
    booking_count = fields.IntField(default=0)
    popularity_score = fields.FloatField(default=0.0)
    last_booked = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    last_verified = fields.DatetimeField(null=True)

    rooms: fields.ReverseRelation["Room"]

    class Meta:
        table = "hotels"
        unique_together = (("external_id", "partner_name"),)

    def __str__(self):
        return f"{self.name} ({self.destination.name})"


class Room(Model):
    id = fields.IntField(pk=True)
    hotel = fields.ForeignKeyField("models.Hotel", related_name="rooms", on_delete=fields.CASCADE)
    external_id = fields.CharField(max_length=255)
    external_ids = fields.JSONField(null=True)
    name = fields.CharField(max_length=255)
    display_name = fields.CharField(max_length=300, null=True)
    description = fields.TextField(null=True)
    short_description = fields.CharField(max_length=500, null=True)
    room_type = fields.CharEnumField(RoomType, default=RoomType.STANDARD)
    room_category = fields.CharField(max_length=100, null=True)
    room_code = fields.CharField(max_length=50, null=True)
    max_occupancy = fields.IntField(default=2)
    max_adults = fields.IntField(null=True)
    max_children = fields.IntField(null=True)
    bed_configuration = fields.JSONField(null=True)
    primary_bed_type = fields.CharEnumField(BedType, null=True)
    room_size_sqm = fields.FloatField(null=True)
    room_size_sqft = fields.FloatField(null=True)
    floor_number = fields.IntField(null=True)
    room_numbers = fields.JSONField(null=True)
    view_type = fields.CharField(max_length=100, null=True)
    balcony_terrace = fields.BooleanField(default=False)
    floor_level = fields.CharField(max_length=50, null=True)
    amenities = fields.JSONField(null=True)
    bathroom_features = fields.JSONField(null=True)
    technology_features = fields.JSONField(null=True)
    comfort_features = fields.JSONField(null=True)
    kitchen_facilities = fields.JSONField(null=True)
    dining_area = fields.BooleanField(default=False)
    accessibility_features = fields.JSONField(null=True)
    is_accessible = fields.BooleanField(default=False)
    images = fields.JSONField(null=True)
    virtual_tour_url = fields.CharField(max_length=500, null=True)
    is_active = fields.BooleanField(default=True)
    is_bookable = fields.BooleanField(default=True)
    is_featured = fields.BooleanField(default=False)
    base_price = fields.FloatField(null=True)
    currency = fields.CharField(max_length=3, default="USD")
    total_rooms = fields.IntField(null=True)
    room_inventory_code = fields.CharField(max_length=100, null=True)
    api_last_updated = fields.DatetimeField(null=True)
    api_data = fields.JSONField(null=True)
    booking_count = fields.IntField(default=0)
    popularity_score = fields.FloatField(default=0.0)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    last_verified = fields.DatetimeField(null=True)

    class Meta:
        table = "rooms"
        unique_together = (("hotel", "external_id"),)

    def __str__(self):
        return f"{self.name} - {self.hotel.name}"


# Polymorphic Models
class UniversalBooking(Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="universal_bookings", on_delete=fields.CASCADE)
    bookable_type = fields.CharEnumField(BookableType)
    bookable_id = fields.IntField()
    secondary_bookable_type = fields.CharField(max_length=50, null=True)
    secondary_bookable_id = fields.IntField(null=True)
    booking_reference = fields.CharField(max_length=100, unique=True)
    external_booking_reference = fields.CharField(max_length=255, null=True)
    partner_name = fields.CharField(max_length=100, null=True)
    travel_start_date = fields.DateField()
    travel_end_date = fields.DateField(null=True)
    travel_duration_days = fields.IntField(null=True)
    travelers = fields.JSONField()
    total_travelers = fields.IntField(default=1)
    origin_country = fields.ForeignKeyField("models.Country", related_name="origin_bookings", on_delete=fields.SET_NULL, null=True)
    origin_destination = fields.ForeignKeyField("models.Destination", related_name="origin_bookings", on_delete=fields.SET_NULL, null=True)
    destination_country = fields.ForeignKeyField("models.Country", related_name="destination_bookings", on_delete=fields.SET_NULL, null=True)
    destination_destination = fields.ForeignKeyField("models.Destination", related_name="destination_bookings", on_delete=fields.SET_NULL, null=True)
    preferences = fields.JSONField(null=True)
    special_requests = fields.TextField(null=True)
    booking_conditions = fields.JSONField(null=True)
    base_price = fields.DecimalField(max_digits=12, decimal_places=2, null=True)
    current_price = fields.DecimalField(max_digits=12, decimal_places=2, null=True)
    target_price = fields.DecimalField(max_digits=12, decimal_places=2, null=True)
    currency = fields.CharField(max_length=3, default="USD")
    price_drop_threshold_percent = fields.FloatField(null=True, default=5.0)
    price_drop_threshold_amount = fields.DecimalField(max_digits=10, decimal_places=2, null=True)
    price_increase_alert = fields.BooleanField(default=False)
    booking_name = fields.CharField(max_length=255, null=True)
    booking_notes = fields.TextField(null=True)
    tags = fields.JSONField(null=True)
    status = fields.CharEnumField(BookingStatus, default=BookingStatus.ACTIVE)
    notification_status = fields.CharEnumField(NotificationStatus, default=NotificationStatus.ENABLED)
    payment_status = fields.CharEnumField(PaymentStatus, null=True)
    last_notification_sent = fields.DatetimeField(null=True)
    notification_frequency_hours = fields.IntField(default=24)
    email_notifications = fields.BooleanField(default=True)
    push_notifications = fields.BooleanField(default=True)
    sms_notifications = fields.BooleanField(default=False)
    actual_booking_date = fields.DatetimeField(null=True)
    actual_booking_price = fields.DecimalField(max_digits=12, decimal_places=2, null=True)
    booking_platform = fields.CharField(max_length=100, null=True)
    confirmation_number = fields.CharField(max_length=255, null=True)
    external_data = fields.JSONField(null=True)
    last_price_check = fields.DatetimeField(null=True)
    price_check_frequency_minutes = fields.IntField(default=60)
    price_alerts_sent = fields.IntField(default=0)
    times_viewed = fields.IntField(default=0)
    last_viewed = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    expires_at = fields.DatetimeField(null=True)

    price_alerts: fields.ReverseRelation["UniversalPriceAlert"]

    class Meta:
        table = "universal_bookings"

    def __str__(self):
        return f"{self.booking_reference} - {self.bookable_type}"


class UniversalPriceHistory(Model):
    id = fields.IntField(pk=True)
    trackable_type = fields.CharEnumField(TrackableType)
    trackable_id = fields.IntField(null=True)
    secondary_trackable_type = fields.CharField(max_length=50, null=True)
    secondary_trackable_id = fields.IntField(null=True)
    price_date = fields.DateField()
    search_date = fields.DateField()
    search_end_date = fields.DateField(null=True)
    price = fields.DecimalField(max_digits=12, decimal_places=2)
    base_price = fields.DecimalField(max_digits=12, decimal_places=2, null=True)
    taxes_fees = fields.DecimalField(max_digits=12, decimal_places=2, null=True)
    currency = fields.CharField(max_length=3, default="USD")
    is_available = fields.BooleanField(default=True)
    availability_count = fields.IntField(null=True)
    booking_conditions = fields.JSONField(null=True)
    search_criteria = fields.JSONField()
    rate_plan_name = fields.CharField(max_length=200, null=True)
    rate_plan_code = fields.CharField(max_length=100, null=True)
    restrictions = fields.JSONField(null=True)
    cancellation_policy = fields.CharField(max_length=100, null=True)
    previous_price = fields.DecimalField(max_digits=12, decimal_places=2, null=True)
    price_change_amount = fields.DecimalField(max_digits=12, decimal_places=2, null=True)
    price_change_percent = fields.FloatField(null=True)
    is_price_drop = fields.BooleanField(null=True)
    is_price_increase = fields.BooleanField(null=True)
    data_source = fields.CharField(max_length=100)
    external_rate_id = fields.CharField(max_length=255, null=True)
    api_response_time_ms = fields.IntField(null=True)
    trace_id = fields.CharField(max_length=255, null=True)
    confidence_score = fields.FloatField(null=True)
    data_freshness_minutes = fields.IntField(null=True)
    validation_errors = fields.JSONField(null=True)
    origin_country = fields.ForeignKeyField("models.Country", related_name="origin_price_history", on_delete=fields.SET_NULL, null=True)
    origin_destination = fields.ForeignKeyField("models.Destination", related_name="origin_price_history", on_delete=fields.SET_NULL, null=True)
    destination_country = fields.ForeignKeyField("models.Country", related_name="destination_price_history", on_delete=fields.SET_NULL, null=True)
    destination_destination = fields.ForeignKeyField("models.Destination", related_name="destination_price_history", on_delete=fields.SET_NULL, null=True)
    raw_api_response = fields.JSONField(null=True)
    
    # Itinerary context fields
    itinerary_request_id = fields.CharField(max_length=64, null=True)  # Link to search request hash
    destination_order = fields.IntField(null=True)  # Position in itinerary (0-based)
    nights_context = fields.IntField(null=True)  # Duration context for this destination
    itinerary_total_nights = fields.IntField(null=True)  # Total trip duration
    
    recorded_at = fields.DatetimeField(auto_now_add=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "universal_price_history"
        unique_together = (("trackable_type", "trackable_id", "secondary_trackable_id", "price_date", "search_date", "search_end_date", "data_source"),)

    def __str__(self):
        return f"{self.trackable_type} - {self.price} {self.currency} ({self.search_date})"


class UniversalPriceAlert(Model):
    id = fields.IntField(pk=True)
    booking = fields.ForeignKeyField("models.UniversalBooking", related_name="price_alerts", on_delete=fields.CASCADE)
    user = fields.ForeignKeyField("models.User", related_name="universal_price_alerts", on_delete=fields.CASCADE)
    alert_type = fields.CharField(max_length=50)
    trigger_condition = fields.JSONField()
    old_price = fields.DecimalField(max_digits=12, decimal_places=2, null=True)
    new_price = fields.DecimalField(max_digits=12, decimal_places=2, null=True)
    price_difference = fields.DecimalField(max_digits=12, decimal_places=2, null=True)
    percentage_change = fields.FloatField(null=True)
    alert_title = fields.CharField(max_length=255)
    alert_message = fields.TextField()
    alert_data = fields.JSONField(null=True)
    delivery_channels = fields.JSONField()
    delivery_status = fields.JSONField(null=True)
    sent_at = fields.DatetimeField(null=True)
    delivered_at = fields.DatetimeField(null=True)
    is_read = fields.BooleanField(default=False)
    read_at = fields.DatetimeField(null=True)
    user_action = fields.CharField(max_length=50, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    expires_at = fields.DatetimeField(null=True)

    class Meta:
        table = "universal_price_alerts"

    def __str__(self):
        return f"{self.alert_type} - {self.booking.booking_reference}"


# Tracker System
class Tracker(Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="trackers", on_delete=fields.CASCADE)
    created_by_user = fields.ForeignKeyField("models.User", related_name="created_trackers", on_delete=fields.SET_NULL, null=True)
    name = fields.CharField(max_length=255)
    description = fields.TextField(null=True)
    tracker_type = fields.CharEnumField(TrackerType, default=TrackerType.HOTEL_SEARCH)
    country = fields.ForeignKeyField("models.Country", related_name="trackers", on_delete=fields.CASCADE, null=True)
    destination = fields.ForeignKeyField("models.Destination", related_name="trackers", on_delete=fields.CASCADE, null=True)
    area = fields.ForeignKeyField("models.Area", related_name="trackers", on_delete=fields.SET_NULL, null=True)
    cluster = fields.ForeignKeyField("models.Cluster", related_name="trackers", on_delete=fields.SET_NULL, null=True)
    origin_country = fields.ForeignKeyField("models.Country", related_name="origin_trackers", on_delete=fields.CASCADE, null=True)
    origin_destination = fields.ForeignKeyField("models.Destination", related_name="origin_trackers", on_delete=fields.CASCADE, null=True)
    start_date = fields.DateField()
    end_date = fields.DateField()
    flexible_dates = fields.BooleanField(default=False)
    date_flexibility_days = fields.IntField(null=True)
    trackable_items = fields.JSONField()
    search_criteria = fields.JSONField()
    filters = fields.JSONField(null=True)
    preferences = fields.JSONField(null=True)
    exclusions = fields.JSONField(null=True)
    price_range_min = fields.DecimalField(max_digits=10, decimal_places=2, null=True)
    price_range_max = fields.DecimalField(max_digits=10, decimal_places=2, null=True)
    currency = fields.CharField(max_length=3, default="USD")
    alert_triggers = fields.JSONField(default=list)
    price_drop_threshold_percent = fields.FloatField(null=True, default=10.0)
    price_drop_threshold_amount = fields.DecimalField(max_digits=10, decimal_places=2, null=True)
    price_increase_threshold_percent = fields.FloatField(null=True)
    tracking_frequency = fields.CharEnumField(TrackerFrequency, default=TrackerFrequency.MEDIUM)
    custom_interval_minutes = fields.IntField(null=True)
    tracking_schedule = fields.JSONField(null=True)
    timezone = fields.CharField(max_length=50, default="UTC")
    status = fields.CharEnumField(TrackerStatus, default=TrackerStatus.ACTIVE)
    is_shared = fields.BooleanField(default=False)
    is_template = fields.BooleanField(default=False)
    last_run_at = fields.DatetimeField(null=True)
    next_run_at = fields.DatetimeField(null=True)
    total_runs = fields.IntField(default=0)
    successful_runs = fields.IntField(default=0)
    failed_runs = fields.IntField(default=0)
    last_error = fields.TextField(null=True)
    total_items_tracked = fields.IntField(default=0)
    active_items_tracked = fields.IntField(default=0)
    price_alerts_sent = fields.IntField(default=0)
    best_price_found = fields.DecimalField(max_digits=10, decimal_places=2, null=True)
    average_price_found = fields.DecimalField(max_digits=10, decimal_places=2, null=True)
    last_results_summary = fields.JSONField(null=True)
    average_execution_time_seconds = fields.FloatField(null=True)
    api_calls_per_run = fields.IntField(null=True)
    data_quality_score = fields.FloatField(null=True)
    notification_settings = fields.JSONField(null=True)
    email_notifications = fields.BooleanField(default=True)
    push_notifications = fields.BooleanField(default=True)
    sms_notifications = fields.BooleanField(default=False)
    notification_frequency_limit_hours = fields.IntField(default=4)
    external_tracker_ids = fields.JSONField(null=True)
    webhook_url = fields.CharField(max_length=500, null=True)
    api_integrations = fields.JSONField(null=True)
    monthly_api_call_limit = fields.IntField(null=True)
    monthly_api_calls_used = fields.IntField(default=0)
    estimated_monthly_cost = fields.DecimalField(max_digits=8, decimal_places=2, null=True)
    auto_pause_on_no_results = fields.BooleanField(default=False)
    auto_stop_after_days = fields.IntField(null=True)
    auto_adjust_frequency = fields.BooleanField(default=False)
    tags = fields.JSONField(null=True)
    priority = fields.IntField(default=0)
    folder = fields.CharField(max_length=100, null=True)
    view_count = fields.IntField(default=0)
    last_viewed = fields.DatetimeField(null=True)
    insights = fields.JSONField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    starts_at = fields.DatetimeField(null=True)
    expires_at = fields.DatetimeField(null=True)

    tracker_results: fields.ReverseRelation["TrackerResult"]
    tracker_alerts: fields.ReverseRelation["TrackerAlert"]

    class Meta:
        table = "trackers"

    def __str__(self):
        return f"{self.name} ({self.tracker_type})"


class TrackerResult(Model):
    id = fields.IntField(pk=True)
    tracker = fields.ForeignKeyField("models.Tracker", related_name="tracker_results", on_delete=fields.CASCADE)
    run_id = fields.CharField(max_length=100)
    execution_start = fields.DatetimeField()
    execution_end = fields.DatetimeField()
    execution_time_seconds = fields.FloatField()
    success = fields.BooleanField(default=False)
    error_message = fields.TextField(null=True)
    items_found = fields.IntField(default=0)
    available_items = fields.IntField(default=0)
    price_changes_detected = fields.IntField(default=0)
    lowest_price = fields.DecimalField(max_digits=10, decimal_places=2, null=True)
    highest_price = fields.DecimalField(max_digits=10, decimal_places=2, null=True)
    average_price = fields.DecimalField(max_digits=10, decimal_places=2, null=True)
    median_price = fields.DecimalField(max_digits=10, decimal_places=2, null=True)
    api_calls_made = fields.IntField(default=0)
    api_errors = fields.IntField(default=0)
    data_sources_used = fields.JSONField(null=True)
    results_data = fields.JSONField(null=True)
    insights = fields.JSONField(null=True)
    recommendations = fields.JSONField(null=True)
    data_quality_score = fields.FloatField(null=True)
    data_completeness = fields.FloatField(null=True)
    validation_warnings = fields.JSONField(null=True)
    alerts_triggered = fields.IntField(default=0)
    alert_types = fields.JSONField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "tracker_results"

    def __str__(self):
        return f"{self.tracker.name} - {self.run_id}"


class TrackerAlert(Model):
    id = fields.IntField(pk=True)
    tracker = fields.ForeignKeyField("models.Tracker", related_name="tracker_alerts", on_delete=fields.CASCADE)
    user = fields.ForeignKeyField("models.User", related_name="tracker_alerts", on_delete=fields.CASCADE)
    alert_type = fields.CharField(max_length=50)
    alert_title = fields.CharField(max_length=255)
    alert_message = fields.TextField()
    alert_data = fields.JSONField(null=True)
    trigger_run_id = fields.CharField(max_length=100, null=True)
    trigger_data = fields.JSONField(null=True)
    affected_items = fields.JSONField(null=True)
    old_price = fields.DecimalField(max_digits=10, decimal_places=2, null=True)
    new_price = fields.DecimalField(max_digits=10, decimal_places=2, null=True)
    price_change_percent = fields.FloatField(null=True)
    delivery_channels = fields.JSONField()
    delivery_status = fields.JSONField(null=True)
    sent_at = fields.DatetimeField(null=True)
    delivered_at = fields.DatetimeField(null=True)
    is_read = fields.BooleanField(default=False)
    read_at = fields.DatetimeField(null=True)
    user_action = fields.CharField(max_length=50, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    expires_at = fields.DatetimeField(null=True)

    class Meta:
        table = "tracker_alerts"

    def __str__(self):
        return f"{self.alert_type} - {self.tracker.name}"


# Task System for Celery Background Jobs
class Task(Model):
    """Model to track Celery background tasks"""
    id = fields.IntField(pk=True)
    task_id = fields.CharField(max_length=255, unique=True)  # Celery task ID
    task_name = fields.CharField(max_length=255)  # Task function name
    task_type = fields.CharField(max_length=100)  # email, hotel_sync, cleanup, etc.
    status = fields.CharEnumField(TaskStatus, default=TaskStatus.PENDING)
    user = fields.ForeignKeyField("models.User", related_name="tasks", on_delete=fields.CASCADE, null=True)
    
    # Task execution details
    started_at = fields.DatetimeField(null=True)
    completed_at = fields.DatetimeField(null=True)
    execution_time_seconds = fields.FloatField(null=True)
    
    # Task data
    task_args = fields.JSONField(null=True)  # Task arguments
    task_kwargs = fields.JSONField(null=True)  # Task keyword arguments
    result = fields.JSONField(null=True)  # Task result
    error_message = fields.TextField(null=True)  # Error details if failed
    traceback = fields.TextField(null=True)  # Full traceback on error
    
    # Progress tracking
    progress_current = fields.IntField(default=0)
    progress_total = fields.IntField(default=100)
    progress_message = fields.CharField(max_length=500, null=True)
    
    # Retry information
    retry_count = fields.IntField(default=0)
    max_retries = fields.IntField(default=3)
    
    # Queue and priority
    queue_name = fields.CharField(max_length=100, null=True)
    priority = fields.IntField(default=0)
    
    # Timestamps
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    
    @property
    def progress_percentage(self) -> float:
        """Calculate progress as percentage"""
        if self.progress_total == 0:
            return 0.0
        return (self.progress_current / self.progress_total) * 100
    
    @property
    def is_finished(self) -> bool:
        """Check if task is in a finished state"""
        return self.status in [TaskStatus.SUCCESS, TaskStatus.FAILURE, TaskStatus.REVOKED]
    
    class Meta:
        table = "tasks"
    
    def __str__(self):
        return f"{self.task_name} ({self.status})"


class TaskLog(Model):
    """Model to store real-time log messages for tasks"""
    id = fields.IntField(pk=True)
    task = fields.ForeignKeyField("models.Task", related_name="logs", on_delete=fields.CASCADE)
    level = fields.CharEnumField(LogLevel, default=LogLevel.INFO)
    message = fields.TextField()
    source = fields.CharField(max_length=100, null=True)  # Function/module name
    timestamp = fields.DatetimeField(auto_now_add=True)
    
    # Optional structured data
    metadata = fields.JSONField(null=True)  # Additional context
    phase = fields.CharField(max_length=50, null=True)  # e.g., "destinations", "hotels", "prices"
    progress_hint = fields.IntField(null=True)  # Progress indicator for this log entry
    
    class Meta:
        table = "task_logs"
        ordering = ["timestamp"]
    
    def __str__(self):
        return f"{self.level} - {self.message[:50]}..."


# Itinerary Models
class SearchType(str, Enum):
    NORMAL = "normal"
    RANGES = "ranges"
    FIXED_DATES = "fixed_dates"
    ALL = "all"


class ItineraryStatus(str, Enum):
    PENDING = "pending"
    OPTIMIZING = "optimizing"
    COMPLETED = "completed"
    FAILED = "failed"


class Itinerary(Model):
    """Main itinerary container with optimization results"""
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="itineraries", on_delete=fields.CASCADE)
    
    # Search configuration
    custom_search = fields.BooleanField(default=False)
    search_types = fields.JSONField()  # List of SearchType values
    suggest_best_order = fields.BooleanField(default=True)
    
    # Date constraints
    global_start_date = fields.DateField()
    global_end_date = fields.DateField()
    date_ranges = fields.JSONField(null=True)  # For ranges search
    fixed_dates = fields.JSONField(null=True)  # For fixed_dates search
    
    # Guest configuration
    adults = fields.IntField(default=1)
    children = fields.IntField(default=0)
    child_ages = fields.JSONField(null=True)
    
    # Optimization results
    total_cost = fields.DecimalField(max_digits=12, decimal_places=2, null=True)
    currency = fields.CharField(max_length=3, default="USD")
    optimization_score = fields.FloatField(null=True)  # Quality metric
    
    # Processing metadata
    status = fields.CharEnumField(ItineraryStatus, default=ItineraryStatus.PENDING)
    optimization_time_ms = fields.IntField(null=True)
    alternatives_generated = fields.IntField(default=0)
    
    # Search context
    top_k = fields.IntField(default=3)  # Number of results per search type
    request_hash = fields.CharField(max_length=64, null=True)  # For caching
    
    # Timestamps
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    
    class Meta:
        table = "itineraries"
        
    def __str__(self):
        return f"Itinerary {self.id} - {self.status} - {self.total_cost} {self.currency}"


class ItineraryDestination(Model):
    """Destination stops within an itinerary with ordering and duration"""
    id = fields.IntField(pk=True)
    itinerary = fields.ForeignKeyField("models.Itinerary", related_name="destinations", on_delete=fields.CASCADE)
    destination = fields.ForeignKeyField("models.Destination", related_name="itinerary_stops", on_delete=fields.CASCADE)
    area = fields.ForeignKeyField("models.Area", related_name="itinerary_stops", on_delete=fields.SET_NULL, null=True)
    
    # Ordering and duration
    order = fields.IntField()  # 0-based position in itinerary
    nights = fields.IntField()  # Required nights at this destination
    
    # Actual assigned dates (after optimization)
    start_date = fields.DateField(null=True)
    end_date = fields.DateField(null=True)
    
    # Cost summary for this destination
    total_cost = fields.DecimalField(max_digits=12, decimal_places=2, null=True)
    currency = fields.CharField(max_length=3, default="USD")
    
    # Hotel assignment summary
    hotels_count = fields.IntField(default=0)
    single_hotel = fields.BooleanField(default=False)  # True if single hotel covers all nights
    
    # Metadata
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    
    class Meta:
        table = "itinerary_destinations"
        unique_together = (("itinerary", "order"),)
        ordering = ["order"]
        
    def __str__(self):
        return f"Destination {self.order}: {self.destination.name} - {self.nights} nights"


class ItineraryHotelAssignment(Model):
    """Hotel assignments for specific dates within a destination"""
    id = fields.IntField(pk=True)
    itinerary_destination = fields.ForeignKeyField(
        "models.ItineraryDestination", 
        related_name="hotel_assignments", 
        on_delete=fields.CASCADE
    )
    hotel = fields.ForeignKeyField("models.Hotel", related_name="itinerary_assignments", on_delete=fields.CASCADE)
    
    # Date and pricing
    assignment_date = fields.DateField()  # Specific date for this assignment
    price = fields.DecimalField(max_digits=12, decimal_places=2)
    base_price = fields.DecimalField(max_digits=12, decimal_places=2, null=True)
    currency = fields.CharField(max_length=3, default="USD")
    
    # Booking details
    room_type = fields.CharField(max_length=100, null=True)
    rate_plan = fields.CharField(max_length=100, null=True)
    guest_count = fields.IntField(default=1)
    
    # Optimization metadata
    selection_reason = fields.CharField(max_length=50, null=True)  # 'single_hotel', 'cheapest_day', etc.
    alternative_count = fields.IntField(default=0)  # Number of alternatives considered
    
    # External reference
    external_rate_id = fields.CharField(max_length=255, null=True)
    partner_name = fields.CharField(max_length=100, null=True)
    
    # Timestamps
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    
    class Meta:
        table = "itinerary_hotel_assignments"
        unique_together = (("itinerary_destination", "assignment_date"),)
        ordering = ["assignment_date"]
        
    def __str__(self):
        return f"{self.hotel.name} on {self.assignment_date} - {self.price} {self.currency}"


class ItinerarySearchRequest(Model):
    """Log of search requests for caching and analytics"""
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="itinerary_requests", on_delete=fields.CASCADE, null=True)
    
    # Request fingerprint
    request_hash = fields.CharField(max_length=64, unique=True)
    
    # Request parameters
    custom_search = fields.BooleanField(default=False)
    search_types = fields.JSONField()
    destinations = fields.JSONField()  # Destination IDs and nights
    global_date_range = fields.JSONField()
    date_ranges = fields.JSONField(null=True)
    fixed_dates = fields.JSONField(null=True)
    guest_config = fields.JSONField()  # Adults, children, ages
    
    # Results summary
    itineraries_generated = fields.IntField(default=0)
    best_cost = fields.DecimalField(max_digits=12, decimal_places=2, null=True)
    currency = fields.CharField(max_length=3, default="USD")
    
    # Performance metrics
    processing_time_ms = fields.IntField(null=True)
    cache_hit = fields.BooleanField(default=False)
    
    # Usage tracking
    access_count = fields.IntField(default=1)
    last_accessed = fields.DatetimeField(auto_now=True)
    
    # Timestamps
    created_at = fields.DatetimeField(auto_now_add=True)
    
    class Meta:
        table = "itinerary_search_requests"
        
    def __str__(self):
        return f"Search {self.request_hash[:8]} - {self.search_types}"