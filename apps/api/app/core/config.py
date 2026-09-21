from pathlib import Path

from pydantic_settings import BaseSettings


def _find_env() -> str | None:
    # Search upward from this file and cwd for .env (supports running from apps/api)
    candidates = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parents[3] / ".env",  # apps/api/app/core -> repo root
        Path(__file__).resolve().parents[4] / ".env",
        Path(".env"),
        Path("../.env"),
        Path("../../.env"),
    ]
    for p in candidates:
        if p.is_file():
            return str(p)
    return ".env"


class Settings(BaseSettings):
    app_name: str = "JevTrace API"
    api_v1_prefix: str = "/api/v1"
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_minutes: int = 60 * 24 * 7

    database_url: str = "postgresql+asyncpg://jev:jev@localhost:5432/jevtrace"
    sync_database_url: str = "postgresql://jev:jev@localhost:5432/jevtrace"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    jev_api_key: str | None = None
    jev_base_url: str = "https://api.typesafe.ai"
    jev_systemone_path: str = "/v1/systemone"

    otel_exporter_otlp_endpoint: str | None = None

    class Config:
        env_file = _find_env()
        extra = "ignore"


settings = Settings()

# Fail fast if JEV_API_KEY is not set — no mocking allowed for Jev
if not settings.jev_api_key:
    import os as _os

    if not _os.getenv("JEV_API_KEY"):
        # Don't crash at import in tests that patch env, but warn loudly
        import warnings as _w

        _w.warn("JEV_API_KEY not set — Jev calls will fail (mocking disabled)", UserWarning)
