"""Application settings, loaded from environment / .env."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "AIVOA Customer Complaint Management API"
    api_prefix: str = "/api/v1"

    database_url: str = "postgresql+psycopg://aivoa:aivoa@localhost:5432/aivoa"

    # Groq. Two models on purpose -- see docs/ARCHITECTURE.md "Model routing".
    groq_api_key: str | None = None
    fast_model: str = "gemma2-9b-it"
    reasoning_model: str = "llama-3.3-70b-versatile"
    llm_temperature: float = 0.1
    llm_timeout_s: int = 45
    llm_max_retries: int = 2

    max_upload_mb: int = 10
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def llm_enabled(self) -> bool:
        return bool(self.groq_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
