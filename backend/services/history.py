import sqlite3
from pathlib import Path

from backend.core.config import Settings


def initialize_database(settings: Settings) -> None:
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(settings.database_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS ride_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                provider TEXT NOT NULL,
                price INTEGER NOT NULL,
                distance_km REAL NOT NULL,
                duration_min REAL NOT NULL,
                route_source TEXT NOT NULL,
                booking_type TEXT NOT NULL,
                trip_mode TEXT NOT NULL,
                trip_hour INTEGER NOT NULL,
                inferred_traffic TEXT NOT NULL
            )
            """
        )


def save_ride_history(rows: list[dict], settings: Settings) -> None:
    initialize_database(settings)
    with sqlite3.connect(settings.database_path) as connection:
        connection.executemany(
            """
            INSERT INTO ride_history (
                timestamp,
                provider,
                price,
                distance_km,
                duration_min,
                route_source,
                booking_type,
                trip_mode,
                trip_hour,
                inferred_traffic
            )
            VALUES (
                :timestamp,
                :provider,
                :price,
                :distance_km,
                :duration_min,
                :route_source,
                :booking_type,
                :trip_mode,
                :trip_hour,
                :inferred_traffic
            )
            """,
            rows,
        )


def get_database_path(settings: Settings) -> Path:
    initialize_database(settings)
    return settings.database_path


def fetch_history_summary(settings: Settings) -> dict:
    initialize_database(settings)
    with sqlite3.connect(settings.database_path) as connection:
        connection.row_factory = sqlite3.Row

        total_rows = connection.execute(
            "SELECT COUNT(*) AS count FROM ride_history"
        ).fetchone()["count"]

        provider_stats = [
            dict(row)
            for row in connection.execute(
                """
                SELECT
                    provider,
                    COUNT(*) AS trip_count,
                    ROUND(AVG(price), 1) AS avg_price,
                    MIN(price) AS min_price,
                    MAX(price) AS max_price,
                    ROUND(AVG(value_score), 1) AS avg_value_score
                FROM (
                    SELECT
                        provider,
                        price,
                        CASE
                            WHEN provider = 'Uber' THEN 8.8
                            WHEN provider = 'Ola' THEN 8.2
                            ELSE 7.9
                        END AS value_score
                    FROM ride_history
                )
                GROUP BY provider
                ORDER BY avg_price ASC, provider ASC
                """
            )
        ]

        hourly_stats = [
            dict(row)
            for row in connection.execute(
                """
                SELECT
                    trip_hour AS hour,
                    COUNT(*) AS trip_count,
                    ROUND(AVG(price), 1) AS avg_price
                FROM ride_history
                GROUP BY trip_hour
                ORDER BY trip_hour ASC
                """
            )
        ]

        traffic_stats = [
            dict(row)
            for row in connection.execute(
                """
                SELECT
                    inferred_traffic AS traffic_level,
                    COUNT(*) AS trip_count,
                    ROUND(AVG(price), 1) AS avg_price
                FROM ride_history
                GROUP BY inferred_traffic
                ORDER BY avg_price DESC
                """
            )
        ]

        trip_mode_stats = [
            dict(row)
            for row in connection.execute(
                """
                SELECT
                    trip_mode,
                    COUNT(*) AS trip_count,
                    ROUND(AVG(price), 1) AS avg_price
                FROM ride_history
                GROUP BY trip_mode
                ORDER BY avg_price ASC
                """
            )
        ]

        recent_trips = [
            dict(row)
            for row in connection.execute(
                """
                SELECT
                    timestamp,
                    provider,
                    price,
                    distance_km,
                    duration_min,
                    booking_type,
                    trip_mode,
                    trip_hour,
                    inferred_traffic
                FROM ride_history
                ORDER BY datetime(timestamp) DESC, id DESC
                LIMIT 12
                """
            )
        ]

    return {
        "total_records": total_rows,
        "provider_stats": provider_stats,
        "hourly_stats": hourly_stats,
        "traffic_stats": traffic_stats,
        "trip_mode_stats": trip_mode_stats,
        "recent_trips": recent_trips,
    }


def fetch_provider_history_rows(provider: str, settings: Settings) -> list[dict]:
    initialize_database(settings)
    with sqlite3.connect(settings.database_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT
                id,
                timestamp,
                provider,
                price,
                distance_km,
                duration_min,
                route_source,
                booking_type,
                trip_mode,
                trip_hour,
                inferred_traffic
            FROM ride_history
            WHERE provider = ?
            ORDER BY datetime(timestamp) DESC, id DESC
            """,
            (provider,),
        ).fetchall()

    return [dict(row) for row in rows]


def fetch_ola_power_bi_dataset(settings: Settings) -> list[dict]:
    rows = fetch_provider_history_rows("Ola", settings)
    dataset = []
    for row in rows:
        trip_hour = row["trip_hour"]
        distance_km = row["distance_km"]
        duration_min = row["duration_min"]
        avg_speed_kmph = round(distance_km / (duration_min / 60), 2) if duration_min else 0.0

        dataset.append(
            {
                **row,
                "trip_date": row["timestamp"][:10],
                "trip_month": row["timestamp"][:7],
                "is_peak_hour": trip_hour in {8, 9, 10, 11, 18, 19, 20, 21},
                "price_per_km": round(row["price"] / distance_km, 2) if distance_km else 0.0,
                "price_per_min": round(row["price"] / duration_min, 2) if duration_min else 0.0,
                "avg_speed_kmph": avg_speed_kmph,
            }
        )

    return dataset


def fetch_ola_dashboard_summary(settings: Settings) -> dict:
    initialize_database(settings)
    dataset = fetch_ola_power_bi_dataset(settings)

    with sqlite3.connect(settings.database_path) as connection:
        connection.row_factory = sqlite3.Row

        overview = connection.execute(
            """
            SELECT
                COUNT(*) AS total_trips,
                ROUND(AVG(price), 1) AS avg_price,
                MIN(price) AS min_price,
                MAX(price) AS max_price,
                ROUND(AVG(distance_km), 2) AS avg_distance_km,
                ROUND(AVG(duration_min), 2) AS avg_duration_min
            FROM ride_history
            WHERE provider = 'Ola'
            """
        ).fetchone()

        hourly_distribution = [
            dict(row)
            for row in connection.execute(
                """
                SELECT
                    trip_hour AS hour,
                    COUNT(*) AS trip_count,
                    ROUND(AVG(price), 1) AS avg_price
                FROM ride_history
                WHERE provider = 'Ola'
                GROUP BY trip_hour
                ORDER BY trip_hour ASC
                """
            )
        ]

        trip_mode_distribution = [
            dict(row)
            for row in connection.execute(
                """
                SELECT
                    trip_mode,
                    COUNT(*) AS trip_count,
                    ROUND(AVG(price), 1) AS avg_price
                FROM ride_history
                WHERE provider = 'Ola'
                GROUP BY trip_mode
                ORDER BY trip_count DESC, trip_mode ASC
                """
            )
        ]

        traffic_distribution = [
            dict(row)
            for row in connection.execute(
                """
                SELECT
                    inferred_traffic AS traffic_level,
                    COUNT(*) AS trip_count,
                    ROUND(AVG(price), 1) AS avg_price
                FROM ride_history
                WHERE provider = 'Ola'
                GROUP BY inferred_traffic
                ORDER BY trip_count DESC, traffic_level ASC
                """
            )
        ]

        booking_distribution = [
            dict(row)
            for row in connection.execute(
                """
                SELECT
                    booking_type,
                    COUNT(*) AS trip_count,
                    ROUND(AVG(price), 1) AS avg_price
                FROM ride_history
                WHERE provider = 'Ola'
                GROUP BY booking_type
                ORDER BY trip_count DESC, booking_type ASC
                """
            )
        ]

    summary = dict(overview)
    summary["total_trips"] = summary["total_trips"] or 0
    summary["avg_price"] = summary["avg_price"] or 0
    summary["min_price"] = summary["min_price"] or 0
    summary["max_price"] = summary["max_price"] or 0
    summary["avg_distance_km"] = summary["avg_distance_km"] or 0
    summary["avg_duration_min"] = summary["avg_duration_min"] or 0

    if dataset:
        peak_rows = [row for row in dataset if row["is_peak_hour"]]
        summary["avg_price_per_km"] = round(
            sum(row["price_per_km"] for row in dataset) / len(dataset),
            2,
        )
        summary["avg_price_per_min"] = round(
            sum(row["price_per_min"] for row in dataset) / len(dataset),
            2,
        )
        summary["peak_hour_trip_share"] = round((len(peak_rows) / len(dataset)) * 100, 1)
    else:
        summary["avg_price_per_km"] = 0
        summary["avg_price_per_min"] = 0
        summary["peak_hour_trip_share"] = 0

    return {
        "provider": "Ola",
        "summary": summary,
        "hourly_distribution": hourly_distribution,
        "trip_mode_distribution": trip_mode_distribution,
        "traffic_distribution": traffic_distribution,
        "booking_distribution": booking_distribution,
        "records": dataset,
    }


def clear_ride_history(settings: Settings) -> int:
    initialize_database(settings)
    with sqlite3.connect(settings.database_path) as connection:
        cursor = connection.execute("SELECT COUNT(*) FROM ride_history")
        deleted_rows = cursor.fetchone()[0]
        connection.execute("DELETE FROM ride_history")
        connection.execute("DELETE FROM sqlite_sequence WHERE name = 'ride_history'")
    return deleted_rows
