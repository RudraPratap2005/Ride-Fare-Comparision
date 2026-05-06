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

## Deploy on Render

This project can be deployed as a single FastAPI web service because the backend already serves the static frontend from `/web`.

1. Push the repository to GitHub.
2. Sign in to Render and choose `New +` -> `Blueprint`.
3. Select this GitHub repository.
4. Render will detect `render.yaml` and create the web service.
5. After deployment, open:
   - App UI: `https://<your-service-name>.onrender.com/web`
   - API docs: `https://<your-service-name>.onrender.com/docs`

Start command used by Render:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

Important note:

- The app currently uses SQLite. On Render's free web service, local filesystem data is ephemeral, so ride history may reset after restarts or redeploys. For persistent analytics history, attach a disk on Render or move to a managed database.

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
