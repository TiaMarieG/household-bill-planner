from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    """Application settings read from environment variables or the repo-root .env file."""

    model_config = SettingsConfigDict(env_file=REPO_ROOT_ENV, extra="ignore")

    app_env: str = "development"
    database_url: str
    test_database_url: str | None = None
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        """Split the comma-separated CORS_ORIGINS value into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a single cached Settings instance for the whole app."""
    return Settings()
