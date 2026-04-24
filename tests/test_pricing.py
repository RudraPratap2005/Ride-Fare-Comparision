from backend.api.schemas import TripMode
from backend.services.pricing import enrich_results, estimate_price_for_provider
from backend.services.traffic import get_dataset_hour_profile, infer_traffic_level


def test_infer_traffic_level_for_peak_hour():
    get_dataset_hour_profile.cache_clear()
    assert infer_traffic_level(9) == "High"
    assert infer_traffic_level(14) == "Low"
    assert infer_traffic_level(17) == "Medium"


def test_infer_traffic_level_uses_dataset_without_overriding_flow(monkeypatch):
    get_dataset_hour_profile.cache_clear()
    monkeypatch.setattr(
        "backend.services.traffic.get_dataset_hour_profile",
        lambda: {
            "hour_counts": {hour: 100 for hour in range(24)} | {12: 140, 2: 80},
            "average_count": 101.6666666667,
            "high_threshold": 110,
            "low_threshold": 95,
        },
    )

    assert infer_traffic_level(12) == "High"
    assert infer_traffic_level(2) == "Low"
    assert infer_traffic_level(9) == "High"


def test_estimate_price_contains_provider_context():
    route_metrics = {
        "distance_km": 10.0,
        "duration_min": 25.0,
        "route_source": "test route",
    }

    result = estimate_price_for_provider(
        "Uber",
        route_metrics,
        TripMode.standard,
        9,
    )

    assert result["provider"] == "Uber"
    assert result["price"] >= 68
    assert result["traffic_level"] == "High"
    assert result["vehicle_type"] == "Mini / small car"


def test_enrich_results_ranks_lowest_price_first():
    results = [
        {
            "provider": "A",
            "price": 100,
            "reliability_score": 8,
            "comfort_score": 8,
            "availability_score": 8,
        },
        {
            "provider": "B",
            "price": 80,
            "reliability_score": 8,
            "comfort_score": 8,
            "availability_score": 8,
        },
    ]

    enriched = enrich_results(results)
    by_provider = {item["provider"]: item for item in enriched}

    assert by_provider["B"]["price_rank"] == 1
    assert "Lowest fare" in by_provider["B"]["recommendation_tags"]
