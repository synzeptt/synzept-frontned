from functools import lru_cache

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    local_cors_origins: tuple[str, ...] = ("http://localhost:3000", "http://127.0.0.1:3000")
    environment: str = "development"
    log_level: str = "INFO"
    log_json: bool = False
    cors_origins: str = "http://localhost:3000,https://app.synzept.com"
    frontend_url: str = "http://localhost:3000"

    database_url: str = "sqlite+aiosqlite:///./synzept.db"
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # Optional: Redis + Dramatiq for durable background jobs
    redis_url: str = ""

    jwt_secret_key: str = Field(
        default="dev-only-change-me",
        validation_alias=AliasChoices("JWT_SECRET_KEY", "JWT_SECRET"),
    )
    jwt_refresh_secret: str = "dev-only-refresh-change-me"

    google_client_id: str = ""
    google_client_secret: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    password_reset_expire_minutes: int = 60

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "support@synzept.com"
    smtp_use_tls: bool = True

    openai_api_key: str = ""
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    llm_provider: str = "gemini"
    llm_fallback_provider: str = ""
    openai_model: str = "gpt-4o-mini"
    anthropic_model: str = "claude-3-5-haiku-20241022"
    gemini_model: str = "gemini-2.5-flash"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    llm_max_retries: int = 3
    llm_timeout_seconds: float = 45.0
    llm_stream_start_timeout_seconds: float = 12.0
    rate_limit_per_minute: int = 120
    request_max_body_bytes: int = 1_000_000
    slow_request_ms: int = 1500
    slow_operation_ms: int = 1000
    early_access_enabled: bool = True
    invite_required: bool = False

    # Supabase Storage (optional — file attachments)
    supabase_url: str = ""
    supabase_service_key: str = ""
    supabase_storage_bucket: str = "synzept"

    @property
    def use_background_worker(self) -> bool:
        return bool(self.redis_url)

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [o.strip().rstrip("/") for o in self.cors_origins.split(",") if o.strip()]
        frontend_origin = self.frontend_url.strip().rstrip("/")
        if frontend_origin:
            origins.append(frontend_origin)
        if self.environment != "production":
            origins.extend(self.local_cors_origins)
        return list(dict.fromkeys(origins))

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.environment == "production" and self.jwt_secret_key == "dev-only-change-me":
            raise ValueError("JWT_SECRET_KEY must be set in production")
        if self.environment == "production" and not (self.gemini_api_key or self.openai_api_key or self.anthropic_api_key):
            raise ValueError("At least one AI provider key must be set in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
