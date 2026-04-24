from backend.api.schemas import TripMode
from backend.services.traffic import (
    TRAFFIC_PROFILE_MULTIPLIERS,
    get_route_traffic_multiplier,
    infer_traffic_level,
)

PROVIDER_RULES = {
    "Uber": {
        "base_fare": 30,
        "per_km": 7.9,
        "per_min": 0.78,
        "booking_fee": 11,
        "minimum_fare": 68,
        "surge_multiplier": 1.02,
        "comfort_score": 9.1,
        "availability_score": 8.9,
        "reliability_score": 9.0,
    },
    "Ola": {
        "base_fare": 28,
        "per_km": 7.4,
        "per_min": 0.72,
        "booking_fee": 10,
        "minimum_fare": 64,
        "surge_multiplier": 1.0,
        "comfort_score": 8.4,
        "availability_score": 8.2,
        "reliability_score": 8.3,
    },
    "Rapido": {
        "base_fare": 25,
        "per_km": 6.5,
        "per_min": 0.58,
        "booking_fee": 8,
        "minimum_fare": 52,
        "surge_multiplier": 0.98,
        "comfort_score": 7.8,
        "availability_score": 8.0,
        "reliability_score": 7.9,
    },
}

TRIP_MODE_MULTIPLIERS = {
    TripMode.budget: {
        "fare": 0.85,
        "comfort": 0.84,
        "reliability": 0.92,
        "vehicle_type": "Economy ride",
    },
    TripMode.standard: {
        "fare": 1.0,
        "comfort": 1.0,
        "reliability": 1.0,
        "vehicle_type": "Mini / small car",
    },
    TripMode.premium: {
        "fare": 1.28,
        "comfort": 1.14,
        "reliability": 1.07,
        "vehicle_type": "Sedan / SUV",
    },
}


def clamp_score(value: float, minimum: float = 0.0, maximum: float = 10.0) -> float:
    return round(max(minimum, min(maximum, value)), 1)


def build_recommendation_tags(
    price_rank: int,
    value_score: float,
    comfort_score: float,
) -> list[str]:
    tags = []
    if price_rank == 1:
        tags.append("Lowest fare")
    if value_score >= 8.5:
        tags.append("High value")
    if comfort_score >= 8.8:
        tags.append("Comfort pick")
    if not tags:
        tags.append("Balanced option")
    return tags


def estimate_price_for_provider(
    provider_name: str,
    route_metrics: dict,
    trip_mode: TripMode,
    trip_hour: int,
) -> dict:
    rules = PROVIDER_RULES[provider_name]
    distance_km = route_metrics["distance_km"]
    duration_min = route_metrics["duration_min"]
    traffic_level = infer_traffic_level(trip_hour)
    route_traffic_multiplier = get_route_traffic_multiplier(distance_km, duration_min)
    inferred_traffic_multiplier = TRAFFIC_PROFILE_MULTIPLIERS[traffic_level]
    trip_profile = TRIP_MODE_MULTIPLIERS[trip_mode]

    raw_price = (
        rules["base_fare"]
        + distance_km * rules["per_km"]
        + duration_min * rules["per_min"]
        + rules["booking_fee"]
    )

    adjusted_price = (
        raw_price
        * rules["surge_multiplier"]
        * route_traffic_multiplier
        * inferred_traffic_multiplier
        * trip_profile["fare"]
    )
    final_price = max(rules["minimum_fare"], round(adjusted_price))

    comfort_score = clamp_score(rules["comfort_score"] * trip_profile["comfort"])
    reliability_score = clamp_score(
        rules["reliability_score"] * trip_profile["reliability"]
    )
    availability_boost = 1.03 if traffic_level == "High" else 1.0
    availability_score = clamp_score(rules["availability_score"] * availability_boost)

    return {
        "provider": provider_name,
        "price": final_price,
        "distance_km": distance_km,
        "duration_min": duration_min,
        "eta_min": max(2, round(duration_min * 0.28 + 4)),
        "estimate_type": "route-based estimate",
        "route_source": route_metrics["route_source"],
        "vehicle_type": trip_profile["vehicle_type"],
        "comfort_score": comfort_score,
        "reliability_score": reliability_score,
        "availability_score": availability_score,
        "traffic_level": traffic_level,
        "price_components": {
            "base_fare": rules["base_fare"],
            "distance_charge": round(distance_km * rules["per_km"], 2),
            "time_charge": round(duration_min * rules["per_min"], 2),
            "booking_fee": rules["booking_fee"],
            "surge_multiplier": rules["surge_multiplier"],
            "traffic_multiplier": route_traffic_multiplier,
            "inferred_traffic_multiplier": inferred_traffic_multiplier,
            "trip_mode_multiplier": trip_profile["fare"],
            "minimum_fare": rules["minimum_fare"],
        },
    }


def enrich_results(results: list[dict]) -> list[dict]:
    sorted_prices = sorted(item["price"] for item in results)
    min_price = sorted_prices[0]
    max_price = sorted_prices[-1]
    price_range = max(max_price - min_price, 1)

    price_rank_lookup = {
        provider["provider"]: index + 1
        for index, provider in enumerate(sorted(results, key=lambda item: item["price"]))
    }

    for item in results:
        price_efficiency = 10 - (((item["price"] - min_price) / price_range) * 4.5)
        value_score = clamp_score(
            (price_efficiency * 0.45)
            + (item["reliability_score"] * 0.25)
            + (item["comfort_score"] * 0.20)
            + (item["availability_score"] * 0.10)
        )
        item["value_score"] = value_score
        item["price_rank"] = price_rank_lookup[item["provider"]]
        item["recommendation_tags"] = build_recommendation_tags(
            item["price_rank"],
            value_score,
            item["comfort_score"],
        )

    return results


def build_project_insight(
    results: list[dict],
    route_metrics: dict,
    trip_mode: TripMode,
    traffic_level: str,
) -> dict:
    best_value = max(results, key=lambda item: item["value_score"])
    cheapest = min(results, key=lambda item: item["price"])
    fastest = min(results, key=lambda item: item["eta_min"])

    if best_value["provider"] == cheapest["provider"]:
        summary = (
            f"{best_value['provider']} leads this trip because it is both the cheapest "
            "and the strongest overall value option."
        )
    else:
        summary = (
            f"{cheapest['provider']} is the cheapest, but {best_value['provider']} offers "
            "a better balance of comfort, reliability, and value."
        )

    return {
        "best_value_provider": best_value["provider"],
        "fastest_eta_provider": fastest["provider"],
        "summary": summary,
        "scenario": f"{trip_mode.value} during {traffic_level.lower()} traffic",
        "distance_band": (
            "short urban ride"
            if route_metrics["distance_km"] < 8
            else "mid-distance commute"
            if route_metrics["distance_km"] < 18
            else "long ride"
        ),
    }
