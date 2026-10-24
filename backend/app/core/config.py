from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "production", "test"] = "development"
    database_url: str = "sqlite+aiosqlite:///./data/mission_control.db"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080"
    frontend_dist: str = ""

    spacex_cms_base_url: str = "https://content.spacex.com"
    spacex_site_base_url: str = "https://www.spacex.com"
    spacex_user_agent: str = (
        "SpaceXMissionControl/1.0 (+https://github.com; mission-status dashboard)"
    )
    spacex_http_timeout_seconds: float = 15.0
    spacex_http_retries: int = 3
    spacex_playwright_fallback: bool = False

    ingest_interval_normal_seconds: int = 600
    ingest_interval_within_6h_seconds: int = 120
    ingest_interval_within_30m_seconds: int = 45
    ingest_interval_active_seconds: int = 20
    ingest_full_catalog_seconds: int = 600
    ingest_recent_limit: int = 18
    ingest_upcoming_detail_limit: int = 12
    seed_from_fixtures_on_failure: bool = True

    api_rate_limit: str = "60/minute"
    log_level: str = "INFO"

    allowed_url_hosts: tuple[str, ...] = Field(
        default=(
            "www.spacex.com",
            "spacex.com",
            "content.spacex.com",
            "sxcontent9668.azureedge.us",
            "x.com",
            "twitter.com",
            "www.starlink.com",
            "starlink.com",
        )
    )

    @field_validator("database_url")
    @classmethod
    def normalize_sqlite(cls, value: str) -> str:
        if value.startswith("sqlite:///") and "+aiosqlite" not in value:
            return value.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
        if value.startswith("postgresql://") and "+asyncpg" not in value:
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [part.strip() for part in self.cors_origins.split(",") if part.strip()]

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def frontend_dist_path(self) -> Path | None:
        candidates: list[Path] = []
        if self.frontend_dist.strip():
            candidates.append(Path(self.frontend_dist))
        candidates.append(Path("/app/static"))
        for path in candidates:
            if (path / "index.html").is_file():
                return path
        return None


@lru_cache
def get_settings() -> Settings:
    return Settings()
