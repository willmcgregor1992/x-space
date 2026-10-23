from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.core.config import Settings
from app.core.time import utcnow
from app.providers.http import SpaceXHttpClient
from app.providers.spacex import SpaceXProvider

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def settings() -> Settings:
    return Settings(
        app_env="test",
        database_url="sqlite+aiosqlite:///:memory:",
        seed_from_fixtures_on_failure=False,
    )


@pytest.fixture
def fixtures() -> dict:
    payload = {
        "upcoming": json.loads((FIXTURES / "upcoming_tiles.json").read_text()),
        "tiles": json.loads((FIXTURES / "launch_tiles_sample.json").read_text()),
        "timings": json.loads((FIXTURES / "future_missions.json").read_text()),
        "details": {},
    }
    for path in FIXTURES.glob("mission_*.json"):
        raw = json.loads(path.read_text())
        slug = raw.get("missionId")
        if slug:
            payload["details"][slug] = raw
    return payload


@pytest.fixture
def provider(settings: Settings) -> SpaceXProvider:
    return SpaceXProvider(settings, SpaceXHttpClient(settings))


@pytest.fixture
def sample_launches(provider: SpaceXProvider, fixtures: dict):
    launches, meta = provider.build_launches(
        upcoming_raw=fixtures["upcoming"],
        tiles_raw=fixtures["tiles"],
        timings_raw=fixtures["timings"],
        details_raw=fixtures["details"],
        fetched_at=utcnow(),
    )
    return launches, meta
