from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Toned API"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/toned"

    supabase_url: str = ""
    supabase_jwt_secret: str = ""
    supabase_anon_key: str = ""
    # Required for hard account delete (Admin API). Never ship this to the mobile app.
    supabase_service_role_key: str = ""

    # Local/dev only: fixed 6-digit OTP for forgot-password + email verify without SMTP.
    # Requires SUPABASE_SERVICE_ROLE_KEY. Leave empty in production / Railway.
    auth_dev_otp: str = ""

    cors_origins: list[str] = ["http://localhost:8081", "exp://localhost:8081"]

    # Extra emails (comma-separated) that see the full uncurated catalogue.
    # seanseun.ss@gmail.com always has access.
    catalogue_full_access_emails: str = ""

    # Optional object storage (Cloudflare R2 / Supabase Storage)
    storage_endpoint: str = ""
    storage_bucket: str = ""
    storage_access_key: str = ""
    storage_secret_key: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
