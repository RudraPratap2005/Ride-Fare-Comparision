from datetime import datetime
from io import StringIO
import csv

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from backend.api.schemas import BookingType, RideRequest, RideResponse
from backend.core.config import Settings, get_settings
from backend.services.history import (
    clear_ride_history,
    fetch_ola_dashboard_summary,
    fetch_ola_power_bi_dataset,
    fetch_history_summary,
    save_ride_history,
)
from backend.services.pricing import (
    PROVIDER_RULES,
    build_project_insight,
    enrich_results,
    estimate_price_for_provider,
)
from backend.services.routing import get_route_metrics
from backend.services.traffic import infer_traffic_level, is_peak_hour

router = APIRouter()


@router.get("/")
@router.get("/health")
def health_check() -> dict:
    return {"status": "ok", "message": "RideScope AI API is running."}


@router.post("/get-price", response_model=RideResponse)
def get_price(
    req: RideRequest,
    settings: Settings = Depends(get_settings),
) -> dict:
    trip_hour = datetime.now().hour if req.booking_type == BookingType.ride_now else req.trip_hour
    if trip_hour is None:
        trip_hour = datetime.now().hour

    route_metrics = get_route_metrics(
        req.pickup_lat,
        req.pickup_lon,
        req.drop_lat,
        req.drop_lon,
        settings,
    )

    results = [
        estimate_price_for_provider(
            provider_name,
            route_metrics,
            req.trip_mode,
            trip_hour,
        )
        for provider_name in PROVIDER_RULES
    ]
    results = enrich_results(results)
    inferred_traffic = infer_traffic_level(trip_hour)

    timestamp = datetime.now().isoformat(timespec="seconds")
    save_ride_history(
        [
            {
                "timestamp": timestamp,
                "provider": ride["provider"],
                "price": ride["price"],
                "distance_km": ride["distance_km"],
                "duration_min": ride["duration_min"],
                "route_source": ride["route_source"],
                "booking_type": req.booking_type.value,
                "trip_mode": req.trip_mode.value,
                "trip_hour": trip_hour,
                "inferred_traffic": inferred_traffic,
            }
            for ride in results
        ],
        settings,
    )

    sorted_results = sorted(results, key=lambda item: item["price"])
    cheapest = min(results, key=lambda item: item["price"])
    insights = build_project_insight(
        results,
        route_metrics,
        req.trip_mode,
        inferred_traffic,
    )

    return {
        "status": "success",
        "route_summary": route_metrics,
        "provider_prices": sorted_results,
        "cheapest": cheapest,
        "insights": insights,
        "trip_context": {
            "trip_hour": trip_hour,
            "booking_type": req.booking_type,
            "trip_mode": req.trip_mode,
            "peak_pricing_applied": is_peak_hour(trip_hour),
            "inferred_traffic": inferred_traffic,
        },
        "note": (
            "This dashboard uses live geocoding and route data with an automatic "
            "time-based traffic model and vehicle-class ride estimation. Prices are "
            "academic estimates, not official platform API fares."
        ),
    }


@router.get("/history-summary")
def history_summary(settings: Settings = Depends(get_settings)) -> dict:
    return {
        "status": "success",
        "analytics": fetch_history_summary(settings),
    }


@router.get("/analytics/ola")
def ola_analytics(settings: Settings = Depends(get_settings)) -> dict:
    return {
        "status": "success",
        "analytics": fetch_ola_dashboard_summary(settings),
    }


@router.get("/analytics/ola/export.csv")
def ola_analytics_export(settings: Settings = Depends(get_settings)) -> StreamingResponse:
    rows = fetch_ola_power_bi_dataset(settings)
    headers = [
        "id",
        "timestamp",
        "trip_date",
        "trip_month",
        "provider",
        "price",
        "distance_km",
        "duration_min",
        "avg_speed_kmph",
        "price_per_km",
        "price_per_min",
        "route_source",
        "booking_type",
        "trip_mode",
        "trip_hour",
        "is_peak_hour",
        "inferred_traffic",
    ]

    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=headers)
    writer.writeheader()
    for row in rows:
        writer.writerow({key: row.get(key) for key in headers})

    response = StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=ola_power_bi_export.csv"
    return response


@router.delete("/history")
def clear_history(settings: Settings = Depends(get_settings)) -> dict:
    deleted_rows = clear_ride_history(settings)
    return {
        "status": "success",
        "message": "Ride history cleared.",
        "deleted_rows": deleted_rows,
    }
