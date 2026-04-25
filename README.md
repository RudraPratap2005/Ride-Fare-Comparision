# Ride Comparison

Ride Comparison is a route-aware ride fare estimation dashboard with a FastAPI backend and a static web frontend. It compares provider-style fare estimates using live route distance, automatic time-based traffic inference, vehicle-class pricing, and historical analytics.

## Features

- FastAPI backend with typed request and response models
- Web dashboard for trip input, provider comparison, and analytics
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
  analytics.html
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


Start the app:

```bash
uvicorn backend.main:app --reload
```

Open the frontend at `http://localhost:8000/web`.

Backend docs are available at `http://localhost:8000/docs`.

## Docker Setup

```bash
docker compose up --build
```

Frontend: `http://localhost:8000/web`

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

## Testing

```bash
pytest
```

## Note

Prices are academic estimates based on configurable rules. They are not official fares from Uber, Ola, Rapido, or any ride platform.
