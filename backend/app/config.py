from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CargoBrief AI"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./cargobrief.db"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.5-flash-lite"

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
