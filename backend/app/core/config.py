from pathlib import Path
from functools import lru_cache
from urllib.parse import urlparse

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _normalize_origin(value: str | None) -> str:
    if not value:
        return ""
    return value.strip().rstrip("/")


def _normalize_origin_list(raw_value: str | None) -> list[str]:
    values = [origin.strip().rstrip("/") for origin in (raw_value or "").split(",") if origin.strip()]
    return list(dict.fromkeys(values))


def _get_setting_value(settings_obj: object, name: str, default: str = "") -> str:
    value = getattr(settings_obj, name, None)
    if value is None:
        return default
    return str(value)


def _get_setting_value_any(settings_obj: object, *names: str, default: str = "") -> str:
    for name in names:
        value = _get_setting_value(settings_obj, name, default="")
        if value:
            return value
    return default


def _looks_like_origin(value: str) -> bool:
    if not value:
        return False
    parsed = urlparse(value)
    return bool(parsed.scheme in {"http", "https"} and parsed.netloc)


def _read_env_value(path: Path, key: str) -> str:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return ""

    for line in raw.splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        name, _, value = line.partition("=")
        if name.strip() == key:
            return value.strip().strip('"').strip("'")
    return ""


def _read_optional_frontend_google_auth_client_id() -> str:
    repo_root = Path(__file__).resolve().parents[3]
    for candidate in [repo_root / "frontend" / ".env.local", repo_root / ".env.local"]:
        if candidate.is_file():
            value = _read_env_value(candidate, "NEXT_PUBLIC_GOOGLE_AUTH_CLIENT_ID")
            if value:
                return value
            value = _read_env_value(candidate, "NEXT_PUBLIC_GOOGLE_CLIENT_ID")
            if value:
                return value
    return ""


def _resolve_sqlite_database_url(url: str) -> str:
    """Resolve relative SQLite URLs against the repository root.

    SQLite URLs like sqlite+aiosqlite:///./synzept.db or sqlite+aiosqlite:///synzept.db
    are relative to the repository root, not the current working directory.
    """
    for prefix in ("sqlite+aiosqlite:///", "sqlite:///"):
        if not url.startswith(prefix):
            continue

        relative_path = url[len(prefix) :]
        if not relative_path or relative_path == ":memory:":
            return url

        # Four slashes indicate an absolute filesystem path.
        if url.startswith(prefix + "/"):
            return url

        normalized_path = relative_path.lstrip("/")
        repo_root = Path(__file__).resolve().parents[3]
        resolved_path = (repo_root / normalized_path).resolve()
        return f"{prefix}{resolved_path.as_posix()}"

    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[
            str(Path(__file__).resolve().parents[2] / ".env"),
            str(Path(__file__).resolve().parents[2] / ".env.local"),
            str(Path(__file__).resolve().parents[2] / "backend" / ".env"),
            str(Path(__file__).resolve().parents[2] / "backend" / ".env.local"),
        ],
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    local_cors_origins: tuple[str, ...] = (
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://0.0.0.0:3000",
        "http://0.0.0.0:3001",
    )
    environment: str = "development"
    log_level: str = "INFO"
    log_json: bool = False
    cors_origins: str = Field(
        default="https://app.synzept.com,https://synzept.com,https://www.synzept.com",
        validation_alias=AliasChoices("CORS_ORIGINS"),
    )
    frontend_url: str = Field(
        default="http://localhost:3000",
        validation_alias=AliasChoices("FRONTEND_URL"),
    )

    database_url: str = "sqlite+aiosqlite:///./synzept.db"
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # Optional: Redis + Dramatiq for durable background jobs
    redis_url: str = ""

    jwt_secret_key: str = Field(
        default="",
        validation_alias=AliasChoices("JWT_SECRET_KEY", "JWT_SECRET"),
    )
    jwt_refresh_secret: str = ""

    google_auth_client_id: str = Field(
        default="",
        validation_alias=AliasChoices("GOOGLE_AUTH_CLIENT_ID", "GOOGLE_CLIENT_ID"),
    )
    google_auth_client_secret: str = Field(
        default="",
        validation_alias=AliasChoices("GOOGLE_AUTH_CLIENT_SECRET", "GOOGLE_CLIENT_SECRET"),
    )
    google_auth_redirect_uri: str = Field(
        default="",
        validation_alias=AliasChoices("GOOGLE_AUTH_REDIRECT_URI", "GOOGLE_REDIRECT_URI", "GOOGLE_CALENDAR_REDIRECT_URI"),
    )
    google_connected_apps_client_id: str = Field(
        default="",
        validation_alias=AliasChoices("GOOGLE_CONNECTED_APPS_CLIENT_ID"),
    )
    google_connected_apps_client_secret: str = Field(
        default="",
        validation_alias=AliasChoices("GOOGLE_CONNECTED_APPS_CLIENT_SECRET"),
    )
    google_connected_apps_redirect_uri: str = Field(
        default="",
        validation_alias=AliasChoices("GOOGLE_CONNECTED_APPS_REDIRECT_URI"),
    )
    microsoft_client_id: str = ""
    microsoft_client_secret: str = ""
    microsoft_tenant_id: str = "common"
    microsoft_redirect_uri: str = ""
    github_client_id: str = ""
    github_client_secret: str = ""
    github_redirect_uri: str = ""
    slack_client_id: str = ""
    slack_client_secret: str = ""
    slack_redirect_uri: str = ""
    notion_client_id: str = ""
    notion_client_secret: str = ""
    notion_redirect_uri: str = ""
    connected_app_token_secret: str = ""
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
    groq_api_key: str = ""
    cerebras_api_key: str = ""
    llm_provider: str = "gemini"
    llm_fallback_provider: str = "groq"
    openai_model: str = "gpt-4o-mini"
    anthropic_model: str = "claude-3-5-haiku-20241022"
    gemini_model: str = "gemini-2.5-flash"
    groq_model: str = "llama-3.3-70b-versatile"
    cerebras_model: str = "llama3.1-8b"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    llm_max_retries: int = 2
    ai_usage_limit_enabled: bool = True
    ai_usage_limit_free_per_day: int = 25
    ai_usage_limit_pro_per_day: int = 200
    ai_usage_limit_window_hours: int = 24
    llm_timeout_seconds: float = 45.0
    llm_stream_start_timeout_seconds: float = 12.0
    rate_limit_per_minute: int = 120
    rate_limit_window_seconds: int = 60
    request_max_body_bytes: int = 1_000_000
    slow_request_ms: int = 1500
    slow_operation_ms: int = 1000
    early_access_enabled: bool = True
    invite_required: bool = False

    # Supabase Storage (optional — file attachments)
    supabase_url: str = ""
    supabase_service_key: str = ""
    supabase_storage_bucket: str = "synzept"

    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""
    razorpay_pro_plan_id: str = ""
    pro_monthly_price_inr: int = 499
    founder_analytics_emails: str = ""

    @property
    def google_client_id(self) -> str:
        return self.google_connected_apps_client_id

    @google_client_id.setter
    def google_client_id(self, value: str) -> None:
        self.google_connected_apps_client_id = value

    @property
    def google_client_secret(self) -> str:
        return self.google_connected_apps_client_secret

    @google_client_secret.setter
    def google_client_secret(self, value: str) -> None:
        self.google_connected_apps_client_secret = value

    @property
    def google_calendar_redirect_uri(self) -> str:
        return self.google_connected_apps_redirect_uri

    @google_calendar_redirect_uri.setter
    def google_calendar_redirect_uri(self, value: str) -> None:
        self.google_connected_apps_redirect_uri = value

    @property
    def use_background_worker(self) -> bool:
        return bool(self.redis_url)

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def cors_origin_list(self) -> list[str]:
        origins = _normalize_origin_list(self.cors_origins)
        frontend_origin = _normalize_origin(self.frontend_url)
        local_prefixes = ("http://localhost:", "http://127.0.0.1:", "http://0.0.0.0:")
        if self.environment == "production":
            origins = [origin for origin in origins if not origin.startswith(local_prefixes)]
        if frontend_origin and (self.environment != "production" or not frontend_origin.startswith(local_prefixes)):
            origins.append(frontend_origin)
        if self.environment != "production":
            origins.extend(_normalize_origin(origin) for origin in self.local_cors_origins)
        return list(dict.fromkeys([origin for origin in origins if origin]))

    @property
    def founder_analytics_email_list(self) -> list[str]:
        return [email.strip().lower() for email in self.founder_analytics_emails.split(",") if email.strip()]

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        self.environment = self.environment.strip().lower()
        if self.pro_monthly_price_inr != 499:
            raise ValueError("PRO_MONTHLY_PRICE_INR must remain 499")
        if self.environment == "production" and not self.jwt_secret_key:
            raise ValueError("JWT_SECRET_KEY must be set in production")
        if self.environment == "production" and not self.jwt_refresh_secret:
            raise ValueError("JWT_REFRESH_SECRET must be set in production")
        if self.environment == "production" and not self.connected_app_token_secret:
            raise ValueError("CONNECTED_APP_TOKEN_SECRET must be set in production")
        if self.environment == "production" and not self.redis_url:
            raise ValueError("REDIS_URL must be set in production for durable background jobs")
        if self.environment == "production" and "*" in _normalize_origin_list(self.cors_origins):
            raise ValueError("CORS_ORIGINS cannot contain * when credentials are enabled")
        if self.environment == "production":
            production_origins = _normalize_origin_list(self.cors_origins)
            if self.frontend_url:
                production_origins.append(_normalize_origin(self.frontend_url))
            invalid_origins = [origin for origin in production_origins if urlparse(origin).scheme != "https"]
            if invalid_origins:
                raise ValueError("Production CORS origins and FRONTEND_URL must use https")
        if self.environment == "production" and self.is_sqlite:
            raise ValueError("DATABASE_URL must point to PostgreSQL in production")
        if self.environment == "production" and self.razorpay_key_id:
            missing_billing = [
                name for name, value in (
                    ("RAZORPAY_KEY_SECRET", self.razorpay_key_secret),
                    ("RAZORPAY_WEBHOOK_SECRET", self.razorpay_webhook_secret),
                    ("RAZORPAY_PRO_PLAN_ID", self.razorpay_pro_plan_id),
                ) if not value
            ]
            if missing_billing:
                raise ValueError("Razorpay configuration is incomplete. Missing: " + ", ".join(missing_billing))
        if self.environment == "production" and not (
            self.gemini_api_key or self.groq_api_key or self.cerebras_api_key or self.openai_api_key or self.anthropic_api_key
        ):
            raise ValueError("At least one AI provider key must be set in production")
        if self.database_url:
            self.database_url = _resolve_sqlite_database_url(self.database_url)
        return self


def validate_google_auth_runtime_settings(settings: Settings | None = None) -> None:
    resolved = settings or get_settings()

    google_auth_client_id = _get_setting_value_any(resolved, "google_auth_client_id", "google_client_id")
    google_auth_client_secret = _get_setting_value_any(resolved, "google_auth_client_secret", "google_client_secret")
    redirect_uri = _get_setting_value_any(
        resolved,
        "google_auth_redirect_uri",
        "google_redirect_uri",
    )

    missing = []
    if not google_auth_client_id:
        missing.append("GOOGLE_AUTH_CLIENT_ID")
    if not google_auth_client_secret:
        missing.append("GOOGLE_AUTH_CLIENT_SECRET")
    if not redirect_uri:
        missing.append("GOOGLE_AUTH_REDIRECT_URI")

    if missing:
        raise ValueError("Google authentication configuration is incomplete. Missing: " + ", ".join(missing))

    if not _looks_like_origin(redirect_uri):
        raise ValueError("GOOGLE_AUTH_REDIRECT_URI must be an absolute http(s) URL")
    if getattr(resolved, "environment", "development") == "production":
        parsed = urlparse(redirect_uri)
        if parsed.scheme != "https" or parsed.netloc != "api.synzept.com" or parsed.path != "/api/v1/auth/google":
            raise ValueError("Production GOOGLE_AUTH_REDIRECT_URI must be https://api.synzept.com/api/v1/auth/google")


def validate_connected_apps_runtime_settings(settings: Settings | None = None) -> None:
    resolved = settings or get_settings()
    missing = [
        name
        for name, value in (
            ("GOOGLE_CONNECTED_APPS_CLIENT_ID", resolved.google_connected_apps_client_id),
            ("GOOGLE_CONNECTED_APPS_CLIENT_SECRET", resolved.google_connected_apps_client_secret),
            ("GOOGLE_CONNECTED_APPS_REDIRECT_URI", resolved.google_connected_apps_redirect_uri),
            ("CONNECTED_APP_TOKEN_SECRET", getattr(resolved, "connected_app_token_secret", "")),
        )
        if not value
    ]
    if missing:
        raise ValueError("Google Connected Apps configuration is incomplete. Missing: " + ", ".join(missing))
    parsed = urlparse(resolved.google_connected_apps_redirect_uri)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("GOOGLE_CONNECTED_APPS_REDIRECT_URI must be an absolute http(s) URL")
    expected_path = "/api/connected-apps/google-calendar/callback"
    if parsed.path != expected_path:
        raise ValueError(f"GOOGLE_CONNECTED_APPS_REDIRECT_URI must end with {expected_path}")
    if resolved.environment == "production" and (parsed.scheme != "https" or parsed.netloc != "api.synzept.com"):
        raise ValueError("Production GOOGLE_CONNECTED_APPS_REDIRECT_URI must be https://api.synzept.com/api/connected-apps/google-calendar/callback")


def build_auth_health_report(settings: Settings | None = None) -> dict[str, object]:
    resolved = settings or get_settings()
    warnings: list[str] = []

    auth_client_id = _get_setting_value_any(resolved, "google_auth_client_id", "google_client_id")
    auth_client_secret = _get_setting_value_any(resolved, "google_auth_client_secret", "google_client_secret")
    auth_redirect_uri = _get_setting_value_any(
        resolved,
        "google_auth_redirect_uri",
        "google_redirect_uri",
    )
    connected_apps_client_id = resolved.google_connected_apps_client_id
    connected_apps_client_secret = resolved.google_connected_apps_client_secret
    connected_apps_redirect_uri = resolved.google_connected_apps_redirect_uri
    frontend_url = _get_setting_value(resolved, "frontend_url")
    cors_origins = _get_setting_value(resolved, "cors_origins")
    frontend_google_auth_client_id = _read_optional_frontend_google_auth_client_id()
    environment = _get_setting_value(resolved, "environment")

    try:
        validate_google_auth_runtime_settings(resolved)
        auth_oauth_status = "configured"
    except ValueError as exc:
        auth_oauth_status = "misconfigured"
        warnings.append(str(exc))

    try:
        validate_connected_apps_runtime_settings(resolved)
        connected_apps_status = "configured"
    except ValueError as exc:
        connected_apps_status = "misconfigured"
        warnings.append(str(exc))

    connected_apps_ready = bool(
        connected_apps_client_id
        and connected_apps_client_secret
        and connected_apps_redirect_uri
        and getattr(resolved, "connected_app_token_secret", "")
    )
    auth_ready = auth_oauth_status == "configured"
    client_ids_match = bool(frontend_google_auth_client_id and auth_client_id and frontend_google_auth_client_id == auth_client_id)
    if frontend_google_auth_client_id and auth_client_id and not client_ids_match:
        warnings.append("NEXT_PUBLIC_GOOGLE_AUTH_CLIENT_ID does not match GOOGLE_AUTH_CLIENT_ID")

    if frontend_google_auth_client_id and not auth_client_id:
        warnings.append("Frontend NEXT_PUBLIC_GOOGLE_AUTH_CLIENT_ID is present, but backend GOOGLE_AUTH_CLIENT_ID is missing.")

    allowed_origins = _normalize_origin_list(cors_origins)
    if frontend_url:
        allowed_origins.append(_normalize_origin(frontend_url))
    if environment != "production":
        allowed_origins.extend(_normalize_origin(origin) for origin in getattr(resolved, "local_cors_origins", ()) if _normalize_origin(origin))

    normalized_allowed_origins = list(dict.fromkeys([origin for origin in allowed_origins if origin]))
    frontend_url_in_allowed_origins = bool(frontend_url and _normalize_origin(frontend_url) in {_normalize_origin(origin) for origin in normalized_allowed_origins})
    if frontend_url and not frontend_url_in_allowed_origins:
        warnings.append("FRONTEND_URL is not present in the allowed CORS origins")

    return {
        "authentication": {
            "client_loaded": auth_client_id,
            "frontend_client_loaded": frontend_google_auth_client_id,
            "redirect_uri": auth_redirect_uri,
            "oauth_ready": auth_ready,
            "oauth_status": auth_oauth_status,
            "client_ids_match": client_ids_match,
        },
        "connected_apps": {
            "client_loaded": connected_apps_client_id,
            "connector_oauth_ready": connected_apps_ready,
            "oauth_status": connected_apps_status,
            "redirect_uri": connected_apps_redirect_uri,
            "scopes": [
                "https://www.googleapis.com/auth/calendar.readonly",
                "https://www.googleapis.com/auth/gmail.readonly",
                "https://www.googleapis.com/auth/drive.metadata.readonly",
                "https://www.googleapis.com/auth/documents",
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/presentations",
            ],
        },
        "google_client_id_loaded": auth_client_id,
        "frontend_google_client_id_loaded": frontend_google_auth_client_id,
        "google_client_ids_match": client_ids_match,
        "frontend_url": frontend_url,
        "frontend_url_in_allowed_origins": frontend_url_in_allowed_origins,
        "redirect_uri": auth_redirect_uri,
        "allowed_origins": normalized_allowed_origins,
        "oauth_status": auth_oauth_status,
        "oauth_ready": auth_ready,
        "environment_status": "ready" if not warnings else "warning",
        "warnings": warnings,
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
