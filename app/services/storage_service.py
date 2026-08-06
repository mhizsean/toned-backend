from app.config import get_settings


class StorageService:
    """Placeholder for R2 / Supabase Storage integration."""

    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def is_configured(self) -> bool:
        return bool(
            self.settings.storage_endpoint
            and self.settings.storage_bucket
            and self.settings.storage_access_key
            and self.settings.storage_secret_key
        )

    def get_public_url(self, key: str) -> str | None:
        if not self.is_configured:
            return None
        base = self.settings.storage_endpoint.rstrip("/")
        return f"{base}/{self.settings.storage_bucket}/{key}"

    def upload_bytes(self, key: str, data: bytes, content_type: str) -> str:
        if not self.is_configured:
            raise RuntimeError("Object storage is not configured")
        # Wire up boto3 / supabase client when credentials are available.
        raise NotImplementedError("Storage upload not implemented yet")
