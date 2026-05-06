from pathlib import Path

from fastapi.testclient import TestClient

from backend.api.routes import get_settings
from backend.core.config import Settings
from backend.main import app


def build_test_settings(database_name: str):
    database_path = Path("data") / database_name
    if database_path.exists():
        database_path.unlink()

    def test_settings():
        return Settings(database_path=database_path)

    return test_settings


def test_get_price_returns_valid_response(monkeypatch):
    def fake_route_metrics(*args, **kwargs):
        return {
            "distance_km": 8.5,
            "duration_min": 20.0,
            "route_source": "test route",
        }

    monkeypatch.setattr("backend.api.routes.get_route_metrics", fake_route_metrics)
    app.dependency_overrides[get_settings] = build_test_settings("test_ride_fare_comparision.db")

    client = TestClient(app)
    response = client.post(
        "/get-price",
        json={
            "pickup_lat": 12.9716,
            "pickup_lon": 77.5946,
            "drop_lat": 12.9352,
            "drop_lon": 77.6245,
            "trip_mode": "Standard Ride",
            "booking_type": "Schedule for Later",
            "trip_hour": 9,
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert len(payload["provider_prices"]) == 3
    assert payload["trip_context"]["inferred_traffic"] == "High"


def test_get_price_rejects_invalid_coordinates():
    client = TestClient(app)
    response = client.post(
        "/get-price",
        json={
            "pickup_lat": 120,
            "pickup_lon": 77.5946,
            "drop_lat": 12.9352,
            "drop_lon": 77.6245,
        },
    )

    assert response.status_code == 422


def test_history_summary_returns_success(monkeypatch):
    app.dependency_overrides[get_settings] = build_test_settings("test_ride_fare_comparision_summary.db")

    client = TestClient(app)
    response = client.get("/history-summary")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert "analytics" in payload


def test_clear_history_returns_deleted_rows(monkeypatch):
    app.dependency_overrides[get_settings] = build_test_settings("test_ride_fare_comparision_clear.db")

    client = TestClient(app)
    client.post(
        "/get-price",
        json={
            "pickup_lat": 12.9716,
            "pickup_lon": 77.5946,
            "drop_lat": 12.9352,
            "drop_lon": 77.6245,
        },
    )
    response = client.delete("/history")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["deleted_rows"] >= 1


def test_ola_analytics_returns_provider_focused_dataset(monkeypatch):
    def fake_route_metrics(*args, **kwargs):
        return {
            "distance_km": 10.0,
            "duration_min": 25.0,
            "route_source": "test route",
        }

    monkeypatch.setattr("backend.api.routes.get_route_metrics", fake_route_metrics)
    app.dependency_overrides[get_settings] = build_test_settings("test_ride_fare_comparision_ola.db")

    client = TestClient(app)
    client.post(
        "/get-price",
        json={
            "pickup_lat": 12.9716,
            "pickup_lon": 77.5946,
            "drop_lat": 12.9352,
            "drop_lon": 77.6245,
            "trip_mode": "Standard Ride",
            "booking_type": "Schedule for Later",
            "trip_hour": 9,
        },
    )
    response = client.get("/analytics/ola")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["analytics"]["provider"] == "Ola"
    assert payload["analytics"]["summary"]["total_trips"] >= 1
    assert all(record["provider"] == "Ola" for record in payload["analytics"]["records"])


def test_ola_analytics_csv_export_returns_csv(monkeypatch):
    def fake_route_metrics(*args, **kwargs):
        return {
            "distance_km": 10.0,
            "duration_min": 25.0,
            "route_source": "test route",
        }

    monkeypatch.setattr("backend.api.routes.get_route_metrics", fake_route_metrics)
    app.dependency_overrides[get_settings] = build_test_settings(
        "test_ride_fare_comparision_ola_export.db"
    )

    client = TestClient(app)
    client.post(
        "/get-price",
        json={
            "pickup_lat": 12.9716,
            "pickup_lon": 77.5946,
            "drop_lat": 12.9352,
            "drop_lon": 77.6245,
            "trip_mode": "Premium Ride",
            "booking_type": "Schedule for Later",
            "trip_hour": 19,
        },
    )
    response = client.get("/analytics/ola/export.csv")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "trip_date" in response.text
    assert "Ola" in response.text
