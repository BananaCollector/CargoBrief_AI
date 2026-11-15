from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CargoBrief AI"
    app_version: str = "0.1.0"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./cargobrief.db"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.5-flash-lite"
    gmail_address: str | None = None
    gmail_app_password: str | None = None
    gmail_imap_host: str = "imap.gmail.com"
    gmail_imap_port: int = 993
    gmail_smtp_host: str = "smtp.gmail.com"
    gmail_smtp_port: int = 465
    email_poll_interval_seconds: int = Field(default=60, ge=10, le=3600)
    dev_tools_enabled: bool = False

    @property
    def gmail_configured(self) -> bool:
        return bool((self.gmail_address or "").strip() and (self.gmail_app_password or "").strip())

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
