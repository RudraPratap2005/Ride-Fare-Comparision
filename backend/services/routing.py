import logging
from math import asin, cos, radians, sin, sqrt

import requests

from backend.core.config import Settings

logger = logging.getLogger(__name__)


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius_km = 6371.0
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)

    a = (
        sin(d_lat / 2) ** 2
        + cos(lat1_rad) * cos(lat2_rad) * sin(d_lon / 2) ** 2
    )
    c = 2 * asin(sqrt(a))
    return earth_radius_km * c


def get_route_metrics(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    settings: Settings,
) -> dict:
    route_url = (
        f"{settings.route_api_url}/{lon1},{lat1};{lon2},{lat2}"
        "?overview=false&alternatives=false&steps=false"
    )

    try:
        response = requests.get(route_url, timeout=settings.request_timeout_seconds)
        response.raise_for_status()
        data = response.json()

        routes = data.get("routes", [])
        if routes:
            best_route = routes[0]
            return {
                "distance_km": round(best_route["distance"] / 1000, 2),
                "duration_min": round(best_route["duration"] / 60, 1),
                "route_source": "OSRM live route",
            }
    except requests.RequestException:
        logger.warning("OSRM route lookup failed; using fallback route estimate.", exc_info=True)

    fallback_distance_km = haversine_distance_km(lat1, lon1, lat2, lon2)

    return {
        "distance_km": round(fallback_distance_km * 1.25, 2),
        "duration_min": round((fallback_distance_km * 1.25 / 24) * 60, 1),
        "route_source": "Haversine fallback",
    }
