from pydantic_settings import BaseSettings


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
    jev_base_url: str = "https://api.jev.com"
    jev_systemone_path: str = "/v1/systemone"

    otel_exporter_otlp_endpoint: str | None = None

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
