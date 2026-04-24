from functools import lru_cache
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()


class Settings(BaseModel):
    app_name: str = "RideScope AI API"
    route_api_url: str = "https://router.project-osrm.org/route/v1/driving"
    request_timeout_seconds: int = Field(default=12, ge=1, le=60)
    database_path: Path = Path("data/ridescope.db")
    cors_origins: list[str] = [
        "http://localhost:8501",
        "http://127.0.0.1:8501",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ]


@lru_cache
def get_settings() -> Settings:
    cors_origins = os.getenv("RIDESCOPE_CORS_ORIGINS")
    return Settings(
        app_name=os.getenv("RIDESCOPE_APP_NAME", "RideScope AI API"),
        route_api_url=os.getenv(
            "RIDESCOPE_ROUTE_API_URL",
            "https://router.project-osrm.org/route/v1/driving",
        ),
        request_timeout_seconds=int(os.getenv("RIDESCOPE_REQUEST_TIMEOUT_SECONDS", "12")),
        database_path=Path(os.getenv("RIDESCOPE_DATABASE_PATH", "data/ridescope.db")),
        cors_origins=(
            [origin.strip() for origin in cors_origins.split(",") if origin.strip()]
            if cors_origins
            else [
                "http://localhost:8501",
                "http://127.0.0.1:8501",
                "http://localhost:5500",
                "http://127.0.0.1:5500",
            ]
        ),
    )
