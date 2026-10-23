from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.time import ensure_utc, utcnow
from app.models.domain import IngestionResult, Launch
from app.providers.spacex import SpaceXProvider
from app.services.events import EventBroker
from app.services.mission_state import MissionStateEngine
from app.services.profiles import select_profile
from app.services.repository import LaunchRepository

logger = logging.getLogger(__name__)
FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures"


class IngestionService:
    def __init__(
        self,
        settings: Settings,
        provider: SpaceXProvider,
        session_maker: async_sessionmaker[AsyncSession],
        broker: EventBroker,
        engine: MissionStateEngine,
    ) -> None:
        self.settings = settings
        self.provider = provider
        self.session_maker = session_maker
        self.broker = broker
        self.engine = engine
        self.last_success_at: datetime | None = None
        self.last_error: str | None = None
        self.last_used_cache = False
        self._last_full_catalog_at: datetime | None = None

    def next_interval(self, launches: list[Launch], now: datetime | None = None) -> int:
        now = now or utcnow()
        settings = self.settings
        interval = settings.ingest_interval_normal_seconds
        for launch in launches:
            profile = select_profile(launch.vehicle, launch.mission_type, launch.iss_enabled)
            t0 = launch.launch_time_start
            if t0 is None:
                continue
            delta = (ensure_utc(t0) - now).total_seconds()
            state = self.engine.compute(launch, now, profile)
            if state.live_status.value in {"webcast_live", "launch_window", "mission_active"}:
                interval = min(interval, settings.ingest_interval_active_seconds)
            elif 0 <= abs(delta) <= 30 * 60:
                interval = min(interval, settings.ingest_interval_within_30m_seconds)
            elif 0 <= abs(delta) <= 6 * 3600:
                interval = min(interval, settings.ingest_interval_within_6h_seconds)
        return max(15, interval)

    async def run(self, *, bust_cache: bool = False) -> IngestionResult:
        started = utcnow()
        async with self.session_maker() as session:
            repo = LaunchRepository(session)
            try:
                if self.settings.app_env == "test":
                    launches = load_fixture_launches(self.settings)
                    tracked = launches
                    await repo.upsert_launches(tracked)
                    await repo.record_run(
                        started_at=started,
                        finished_at=utcnow(),
                        ok=True,
                        used_cache=True,
                        launches_upserted=len(tracked),
                        error=None,
                        source_updated_at=utcnow(),
                    )
                    self.last_success_at = utcnow()
                    self.last_error = None
                    self.last_used_cache = True
                    return IngestionResult(
                        ok=True,
                        used_cache=True,
                        launches_upserted=len(tracked),
                        fetched_at=self.last_success_at,
                        source_updated_at=self.last_success_at,
                        stale_seconds=0,
                    )
                detail_slugs = await self._detail_slugs(repo)
                launches, meta = await self.provider.fetch_catalog(
                    bust_cache=bust_cache,
                    include_details_for=detail_slugs or None,
                )
                tracked = self._select_tracked(launches)
                for launch in tracked:
                    launch.profile_id = select_profile(
                        launch.vehicle, launch.mission_type, launch.iss_enabled
                    ).id
                    profile = select_profile(launch.vehicle, launch.mission_type, launch.iss_enabled)
                    from app.services.profiles import merge_milestones

                    launch.milestones = merge_milestones(profile, launch.milestones)
                changed = await repo.upsert_launches(tracked)
                raw = meta.get("raw") or {}
                await repo.save_snapshot("spacex_catalog", _summarize_raw(raw))
                await repo.record_run(
                    started_at=started,
                    finished_at=utcnow(),
                    ok=True,
                    used_cache=False,
                    launches_upserted=len(tracked),
                    error=None,
                    source_updated_at=utcnow(),
                )
                self.last_success_at = utcnow()
                self.last_error = None
                self.last_used_cache = False
                if changed:
                    await self.broker.publish(
                        "launches_updated",
                        {"changed": changed, "count": len(tracked)},
                    )
                return IngestionResult(
                    ok=True,
                    used_cache=False,
                    launches_upserted=len(tracked),
                    fetched_at=self.last_success_at,
                    source_updated_at=self.last_success_at,
                    stale_seconds=0,
                )
            except Exception as exc:
                logger.exception("ingestion failed; preserving cached launches")
                self.last_error = str(exc)
                self.last_used_cache = True
                if self.settings.is_development and self.settings.seed_from_fixtures_on_failure:
                    existing = await repo.list_launches()
                    if not existing:
                        seeded = load_fixture_launches(self.settings)
                        if seeded:
                            await repo.upsert_launches(seeded)
                            logger.warning("seeded database from fixtures after live fetch failure")
                await repo.record_run(
                    started_at=started,
                    finished_at=utcnow(),
                    ok=False,
                    used_cache=True,
                    launches_upserted=0,
                    error=str(exc)[:2000],
                    source_updated_at=self.last_success_at,
                )
                stale = None
                if self.last_success_at:
                    stale = int((utcnow() - self.last_success_at).total_seconds())
                return IngestionResult(
                    ok=False,
                    used_cache=True,
                    error="spacex_unreachable",
                    fetched_at=self.last_success_at or started,
                    source_updated_at=self.last_success_at,
                    stale_seconds=stale,
                )

    async def _detail_slugs(self, repo: LaunchRepository) -> set[str]:
        existing = await repo.list_launches()
        upcoming = [
            item
            for item in existing
            if item.cms_status == "upcoming" or item.status.value in {"scheduled", "countdown", "window_open"}
        ]
        in_progress = [item for item in existing if item.cms_status == "in-progress"]
        recent = sorted(
            [item for item in existing if item.cms_status == "final"],
            key=lambda item: item.launch_time_start or datetime.min.replace(tzinfo=item.fetched_at.tzinfo),
            reverse=True,
        )[: self.settings.ingest_recent_limit]
        chosen = upcoming[: self.settings.ingest_upcoming_detail_limit] + in_progress + recent
        return {item.slug for item in chosen}

    def _select_tracked(self, launches: list[Launch]) -> list[Launch]:
        upcoming = [item for item in launches if item.cms_status == "upcoming"]
        in_progress = [item for item in launches if item.cms_status == "in-progress"]
        recent = sorted(
            [item for item in launches if item.cms_status == "final" and item.launch_time_start],
            key=lambda item: item.launch_time_start or utcnow(),
            reverse=True,
        )[: self.settings.ingest_recent_limit]
        by_slug = {item.slug: item for item in upcoming + in_progress + recent}
        return list(by_slug.values())


def load_fixture_launches(settings: Settings) -> list[Launch]:
    try:
        upcoming = json.loads((FIXTURES / "upcoming_tiles.json").read_text())
        tiles = json.loads((FIXTURES / "launch_tiles_sample.json").read_text())
        timings = json.loads((FIXTURES / "future_missions.json").read_text())
        details = {}
        for path in FIXTURES.glob("mission_*.json"):
            raw = json.loads(path.read_text())
            slug = raw.get("missionId")
            if slug:
                details[slug] = raw
        from app.providers.http import SpaceXHttpClient
        from app.providers.spacex import SpaceXProvider

        provider = SpaceXProvider(settings, SpaceXHttpClient(settings))
        launches, _ = provider.build_launches(
            upcoming_raw=upcoming,
            tiles_raw=tiles,
            timings_raw=timings,
            details_raw=details,
            fetched_at=utcnow(),
        )
        tracked = []
        for launch in launches:
            profile = select_profile(launch.vehicle, launch.mission_type, launch.iss_enabled)
            launch.profile_id = profile.id
            from app.services.profiles import merge_milestones

            launch.milestones = merge_milestones(profile, launch.milestones)
            tracked.append(launch)
        return tracked
    except Exception:
        logger.exception("fixture seed failed")
        return []


def _summarize_raw(raw: dict[str, Any]) -> dict[str, Any]:
    def count(value: Any) -> int:
        if isinstance(value, list):
            return len(value)
        if isinstance(value, dict):
            return len(value)
        return 0

    return {
        "upcoming": count(raw.get("upcoming")),
        "tiles": count(raw.get("tiles")),
        "timings": count(raw.get("timings")),
        "details": list((raw.get("details") or {}).keys()),
        "fetched_at": utcnow().isoformat(),
    }


def stale_banner(last_success_at: datetime | None, last_error: str | None) -> dict[str, Any] | None:
    if last_success_at is None and last_error:
        return {
            "code": "parser_or_source_failed",
            "title": "DATA UNAVAILABLE",
            "message": "SpaceX could not be reached. Showing empty mission board until the first successful sync.",
        }
    if last_success_at is None:
        return None
    age = utcnow() - last_success_at
    if last_error or age > timedelta(minutes=12):
        minutes = max(1, int(age.total_seconds() // 60))
        return {
            "code": "stale",
            "title": "DATA DELAYED",
            "message": f"Last SpaceX update received {minutes} minute{'s' if minutes != 1 else ''} ago. Mission calculations are based on cached launch information.",
        }
    return None
