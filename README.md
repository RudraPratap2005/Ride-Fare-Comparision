# RideScope AI

RideScope AI is a route-aware ride fare estimation dashboard with a FastAPI backend and a lightweight web frontend. It compares provider-style fare estimates using live route distance, automatic time-based traffic inference, vehicle-class pricing, and historical analytics.

## Features

- FastAPI backend with typed request and response models
- Static HTML, CSS, and JavaScript frontend for trip input and provider comparison
- OSRM route lookup with Haversine fallback
- Configurable provider fare model
- Time-aware traffic inference
- SQLite ride-history storage
- Unit tests for pricing and API validation
- Docker Compose setup for local production-style runs

## Project Structure

```text
backend/
  api/          FastAPI routes and Pydantic schemas
  core/         configuration and logging
  services/     routing, pricing, traffic, and history storage
frontend/
  index.html
  script.js
  style.css
tests/
data/
mains.py        FastAPI compatibility launcher
```

## Local Setup

Create and activate a virtual environment, then install dependencies:

```bash
pip install -r requirements.txt
```

Copy `.env.example` to `.env` if you want to override defaults.

Start the API:

```bash
uvicorn backend.main:app --reload
```

Open the web frontend in another terminal:

```bash
python -m http.server 5500 --directory frontend
```

Then open `http://localhost:5500`.

You can also use the frontend mounted by FastAPI at `http://localhost:8000/web`.

## Docker Setup

```bash
docker compose up --build
```

Frontend: `http://localhost:8501`

Backend docs: `http://localhost:8000/docs`

## API

Health check:

```http
GET /health
```

Estimate ride prices:

```http
POST /get-price
```

Example body:

```json
{
  "pickup_lat": 12.9716,
  "pickup_lon": 77.5946,
  "drop_lat": 12.9352,
  "drop_lon": 77.6245,
  "trip_mode": "Standard Ride",
  "booking_type": "Schedule for Later",
  "trip_hour": 9
}
```

Project analytics summary:

```http
GET /history-summary
```

Ola-focused analytics for Power BI:

```http
GET /analytics/ola
GET /analytics/ola/export.csv
```

`/analytics/ola` returns Ola-only KPIs plus the detailed records as JSON. `/analytics/ola/export.csv`
returns a flat table that Power BI can import directly from the web.

Suggested Power BI visuals for the Ola dashboard:

- KPI cards for `total_trips`, `avg_price`, `avg_price_per_km`, and `peak_hour_trip_share`
- Line chart of `avg_price` by `trip_hour`
- Clustered column chart of trips by `trip_mode`
- Donut chart of trips by `inferred_traffic`
- Table of recent Ola rides using `timestamp`, `price`, `distance_km`, and `booking_type`

## Testing

```bash
pytest
```

## Note

Prices are academic estimates based on configurable rules. They are not official fares from Uber, Ola, Rapido, or any ride platform.
