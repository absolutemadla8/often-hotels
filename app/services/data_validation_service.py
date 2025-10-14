"""
Data validation and quality checks for scraped hotel data
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, validator
from datetime import date, datetime
import logging

logger = logging.getLogger(__name__)


class GPSCoordinates(BaseModel):
    """GPS coordinates validation"""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class PriceData(BaseModel):
    """Price data validation"""
    amount: float = Field(..., gt=0, description="Price must be positive")
    currency: str = Field(..., min_length=3, max_length=3, description="ISO 4217 currency code")

    @validator('currency')
    def currency_uppercase(cls, v):
        return v.upper()


class HotelData(BaseModel):
    """Validated hotel data from SERP"""
    name: str = Field(..., min_length=1, max_length=500)
    price: Optional[PriceData] = None
    rating: Optional[float] = Field(None, ge=0, le=5)
    reviews: Optional[int] = Field(None, ge=0)
    hotel_class: Optional[int] = Field(None, ge=1, le=5, description="Star rating")
    gps_coordinates: Optional[GPSCoordinates] = None
    amenities: List[str] = Field(default_factory=list)
    images: List[str] = Field(default_factory=list)

    @validator('name')
    def clean_name(cls, v):
        """Clean and normalize hotel name"""
        return v.strip()


class DataValidationService:
    """
    Service for validating and cleaning scraped data
    - Schema validation with Pydantic
    - Price anomaly detection
    - Data quality scoring
    """

    def __init__(
        self,
        min_price_threshold: float = 10.0,
        max_price_threshold: float = 10000.0,
        price_change_threshold: float = 0.5  # 50% change triggers alert
    ):
        self.min_price_threshold = min_price_threshold
        self.max_price_threshold = max_price_threshold
        self.price_change_threshold = price_change_threshold

        # Metrics
        self.total_validated = 0
        self.validation_errors = 0
        self.anomalies_detected = 0

    def validate_hotel_data(self, raw_data: Dict[str, Any]) -> Optional[HotelData]:
        """
        Validate raw hotel data from SERP

        Args:
            raw_data: Raw data from scraper

        Returns:
            Validated HotelData or None if invalid
        """
        self.total_validated += 1

        try:
            # Extract price data
            price_data = None
            if "rate_per_night" in raw_data:
                amount = raw_data["rate_per_night"].get("extracted_lowest")
                currency = raw_data.get("currency", "USD")
                if amount and amount > 0:
                    price_data = PriceData(amount=amount, currency=currency)
            elif "total_rate" in raw_data:
                amount = raw_data["total_rate"].get("extracted_lowest")
                currency = raw_data.get("currency", "USD")
                if amount and amount > 0:
                    price_data = PriceData(amount=amount, currency=currency)

            # Extract GPS coordinates
            gps = None
            if "gps_coordinates" in raw_data and raw_data["gps_coordinates"]:
                coords = raw_data["gps_coordinates"]
                if "latitude" in coords and "longitude" in coords:
                    gps = GPSCoordinates(
                        latitude=coords["latitude"],
                        longitude=coords["longitude"]
                    )

            # Build validated hotel data
            hotel_data = HotelData(
                name=raw_data.get("name", "Unknown Hotel"),
                price=price_data,
                rating=raw_data.get("overall_rating"),
                reviews=raw_data.get("reviews"),
                hotel_class=raw_data.get("hotel_class"),
                gps_coordinates=gps,
                amenities=raw_data.get("amenities", []),
                images=raw_data.get("images", [])
            )

            return hotel_data

        except Exception as e:
            self.validation_errors += 1
            logger.error(f"Validation error for hotel data: {e}")
            return None

    def detect_price_anomalies(
        self,
        current_price: float,
        historical_prices: List[float],
        currency: str = "USD"
    ) -> Dict[str, Any]:
        """
        Detect price anomalies using statistical methods

        Args:
            current_price: Current price to check
            historical_prices: List of historical prices
            currency: Currency code

        Returns:
            Anomaly detection result with flags and scores
        """
        anomalies = {
            "is_anomaly": False,
            "reasons": [],
            "score": 0.0,
            "recommendations": []
        }

        # Check absolute price range
        if current_price < self.min_price_threshold:
            anomalies["is_anomaly"] = True
            anomalies["reasons"].append(f"Price too low: {current_price} < {self.min_price_threshold}")
            anomalies["recommendations"].append("Verify data source accuracy")

        if current_price > self.max_price_threshold:
            anomalies["is_anomaly"] = True
            anomalies["reasons"].append(f"Price too high: {current_price} > {self.max_price_threshold}")
            anomalies["recommendations"].append("Check for luxury/premium properties")

        # Check against historical prices
        if historical_prices:
            import statistics

            avg_price = statistics.mean(historical_prices)

            # Calculate percentage change
            if avg_price > 0:
                change_pct = abs(current_price - avg_price) / avg_price

                if change_pct > self.price_change_threshold:
                    anomalies["is_anomaly"] = True
                    anomalies["reasons"].append(
                        f"Unusual price change: {change_pct*100:.1f}% from average"
                    )
                    anomalies["recommendations"].append("Investigate seasonal/event pricing")
                    anomalies["score"] = change_pct

            # Check for outliers using IQR method
            if len(historical_prices) >= 4:
                sorted_prices = sorted(historical_prices)
                q1_idx = len(sorted_prices) // 4
                q3_idx = 3 * len(sorted_prices) // 4

                q1 = sorted_prices[q1_idx]
                q3 = sorted_prices[q3_idx]
                iqr = q3 - q1

                lower_bound = q1 - (1.5 * iqr)
                upper_bound = q3 + (1.5 * iqr)

                if current_price < lower_bound or current_price > upper_bound:
                    anomalies["is_anomaly"] = True
                    anomalies["reasons"].append(
                        f"Statistical outlier (IQR method): {lower_bound:.2f} - {upper_bound:.2f}"
                    )

        if anomalies["is_anomaly"]:
            self.anomalies_detected += 1
            logger.warning(
                f"Price anomaly detected: {current_price} {currency} - "
                f"Reasons: {', '.join(anomalies['reasons'])}"
            )

        return anomalies

    def calculate_data_quality_score(
        self,
        hotel_data: HotelData
    ) -> float:
        """
        Calculate data quality score (0-100)

        Factors:
        - Has price: +30
        - Has rating: +15
        - Has reviews: +10
        - Has coordinates: +20
        - Has images: +15
        - Has amenities: +10

        Returns:
            Quality score between 0-100
        """
        score = 0.0

        if hotel_data.price:
            score += 30

        if hotel_data.rating is not None:
            score += 15

        if hotel_data.reviews and hotel_data.reviews > 0:
            score += 10

        if hotel_data.gps_coordinates:
            score += 20

        if hotel_data.images:
            score += 15

        if hotel_data.amenities:
            score += 10

        return score

    def get_metrics(self) -> Dict[str, Any]:
        """Get validation metrics"""
        return {
            "total_validated": self.total_validated,
            "validation_errors": self.validation_errors,
            "anomalies_detected": self.anomalies_detected,
            "validation_success_rate": (
                (self.total_validated - self.validation_errors) / max(self.total_validated, 1)
            )
        }


# Singleton instance
_validation_service: Optional[DataValidationService] = None


def get_validation_service(
    min_price_threshold: float = 10.0,
    max_price_threshold: float = 10000.0,
    price_change_threshold: float = 0.5
) -> DataValidationService:
    """Get singleton validation service instance"""
    global _validation_service

    if _validation_service is None:
        _validation_service = DataValidationService(
            min_price_threshold=min_price_threshold,
            max_price_threshold=max_price_threshold,
            price_change_threshold=price_change_threshold
        )

    return _validation_service
