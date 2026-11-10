"""
Centralized, typed application configuration.

All runtime configuration is read from environment variables (with sane
defaults) so the service behaves the same way locally, in Docker, and in
production without code changes.
"""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Server ---
    host: str = "0.0.0.0"
    port: int = 8001
    allowed_origins: str = "http://localhost:5173,http://localhost:4000"

    # --- MongoDB ---
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db_name: str = "ai_interviewer"

    # --- Frame processing ---
    frame_process_every_n: int = 2
    max_frame_width: int = 640

    # --- Object detection ---
    enable_object_detection: bool = False
    yolo_model_path: str = "yolov8n.pt"
    object_detection_every_n: int = 15

    # --- Reporting ---
    reports_dir: str = "./reports"
    logs_dir: str = "./logs"

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (loaded once per process)."""
    return Settings()
