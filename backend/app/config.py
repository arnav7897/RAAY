from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://postgres:postgres@localhost:5432/raay"
    raw_cache_dir: Path = Path("data/raw")
    rbi_user_agent: str = "RAAY/0.1 (+https://example.invalid/contact)"
    rbi_request_interval_seconds: float = Field(default=1.0, ge=1.0)


def get_settings() -> Settings:
    return Settings()
