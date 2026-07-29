from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_secret_key: str = "development-only-secret-change-me"
    credential_encryption_key: str | None = None
    database_url: str = "sqlite+aiosqlite:///./weaverun.db"
    redis_url: str = "redis://localhost:6379/0"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = ""
    minio_secret_key: str = ""
    minio_bucket: str = "weaverun"
    minio_secure: bool = False
    access_token_minutes: int = 720
    cors_origins: str = "http://localhost:5173"
    sandbox_url: str = "http://localhost:8081"
    sandbox_shared_secret: str = ""
    document_worker_url: str = "http://localhost:8082"
    max_upload_bytes: int = Field(default=50 * 1024 * 1024, ge=1024)
    max_request_body_bytes: int = Field(default=50 * 1024 * 1024, ge=1024)
    log_level: str = "INFO"
    otel_exporter_otlp_endpoint: str = ""
    alert_webhook_url: str = ""
    task_always_eager: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [value.strip() for value in self.cors_origins.split(",") if value.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
