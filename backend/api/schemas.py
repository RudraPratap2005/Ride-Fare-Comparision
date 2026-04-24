from enum import StrEnum

from pydantic import BaseModel, Field


class BookingType(StrEnum):
    ride_now = "Ride Now"
    schedule_for_later = "Schedule for Later"


class TripMode(StrEnum):
    budget = "Budget Ride"
    standard = "Standard Ride"
    premium = "Premium Ride"


class RideRequest(BaseModel):
    pickup_lat: float = Field(..., ge=-90, le=90)
    pickup_lon: float = Field(..., ge=-180, le=180)
    drop_lat: float = Field(..., ge=-90, le=90)
    drop_lon: float = Field(..., ge=-180, le=180)
    trip_mode: TripMode = TripMode.standard
    booking_type: BookingType = BookingType.ride_now
    trip_hour: int | None = Field(default=None, ge=0, le=23)


class RouteSummary(BaseModel):
    distance_km: float
    duration_min: float
    route_source: str


class PriceComponents(BaseModel):
    base_fare: float
    distance_charge: float
    time_charge: float
    booking_fee: float
    surge_multiplier: float
    traffic_multiplier: float
    inferred_traffic_multiplier: float
    trip_mode_multiplier: float
    minimum_fare: float


class ProviderPrice(BaseModel):
    provider: str
    price: int
    distance_km: float
    duration_min: float
    eta_min: int
    estimate_type: str
    route_source: str
    vehicle_type: str
    comfort_score: float
    reliability_score: float
    availability_score: float
    traffic_level: str
    price_components: PriceComponents
    value_score: float
    price_rank: int
    recommendation_tags: list[str]


class Insights(BaseModel):
    best_value_provider: str
    fastest_eta_provider: str
    summary: str
    scenario: str
    distance_band: str


class TripContext(BaseModel):
    trip_hour: int
    booking_type: BookingType
    trip_mode: TripMode
    peak_pricing_applied: bool
    inferred_traffic: str


class RideResponse(BaseModel):
    status: str
    route_summary: RouteSummary
    provider_prices: list[ProviderPrice]
    cheapest: ProviderPrice
    insights: Insights
    trip_context: TripContext
    note: str
