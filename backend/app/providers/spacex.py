from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from app.core.config import Settings
from app.core.time import utcnow
from app.models.domain import Launch
from app.providers.http import ProviderHttpError, SpaceXHttpClient
from app.providers.spacex_parse import (
    detect_suspicious_empty,
    merge_launch,
    parse_mission_detail,
    parse_tile,
    parse_timings_entry,
)

logger = logging.getLogger(__name__)


class SpaceXProvider:
    name = "spacex"

    def __init__(self, settings: Settings, http: SpaceXHttpClient) -> None:
        self._settings = settings
        self._http = http

    def _url(self, path: str) -> str:
        return f"{self._settings.spacex_cms_base_url.rstrip('/')}/{path.lstrip('/')}"

    async def fetch_catalog(
        self, *, bust_cache: bool = False, include_details_for: set[str] | None = None
    ) -> tuple[list[Launch], dict[str, Any]]:
        upcoming_raw = await self._http.get_json(
            self._url("api/spacex-website/launches-page-tiles/upcoming"),
            bust_cache=bust_cache,
        )
        timings_raw = await self._http.get_json(
            self._url("cms-assets/future_missions.json"),
            bust_cache=bust_cache,
        )
        tiles_raw = await self._http.get_json(self._url("api/spacex-website/launches-page-tiles"))
        suspicious = detect_suspicious_empty(upcoming_raw, tiles_raw, timings_raw)
        if suspicious:
            raise ValueError(f"suspicious SpaceX payload: {suspicious}")

        launches, meta = self.build_launches(
            upcoming_raw=upcoming_raw,
            tiles_raw=tiles_raw,
            timings_raw=timings_raw,
            details_raw={},
            fetched_at=utcnow(),
        )

        slugs = include_details_for if include_details_for else self.default_detail_slugs(launches)
        details: dict[str, Any] = {}
        for slug in slugs:
            try:
                details[slug] = await self._http.get_json(
                    self._url(f"api/spacex-website/missions/{slug}")
                )
            except ProviderHttpError as exc:
                logger.warning("mission detail fetch failed slug=%s error=%s", slug, exc)
            except Exception:
                logger.exception("mission detail fetch failed slug=%s", slug)

        if details:
            launches, meta = self.build_launches(
                upcoming_raw=upcoming_raw,
                tiles_raw=tiles_raw,
                timings_raw=timings_raw,
                details_raw=details,
                fetched_at=utcnow(),
            )
        meta["raw"] = {
            "upcoming": upcoming_raw,
            "tiles": tiles_raw,
            "timings": timings_raw,
            "details": {k: _strip_media(v) for k, v in details.items()},
        }
        return launches, meta

    def default_detail_slugs(self, launches: list[Launch]) -> set[str]:
        upcoming = [item for item in launches if item.cms_status == "upcoming"][
            : self._settings.ingest_upcoming_detail_limit
        ]
        in_progress = [item for item in launches if item.cms_status == "in-progress"]
        recent = sorted(
            [item for item in launches if item.cms_status == "final" and item.launch_time_start],
            key=lambda item: item.launch_time_start or item.fetched_at,
            reverse=True,
        )[: self._settings.ingest_recent_limit]
        return {item.slug for item in upcoming + in_progress + recent}

    def build_launches(
        self,
        *,
        upcoming_raw: list[dict[str, Any]],
        tiles_raw: list[dict[str, Any]],
        timings_raw: dict[str, Any],
        details_raw: dict[str, Any],
        fetched_at: datetime,
    ) -> tuple[list[Launch], dict[str, Any]]:
        timings_by_corr = {
            key: parse_timings_entry(value)
            for key, value in (timings_raw or {}).items()
            if isinstance(value, dict)
        }
        by_slug: dict[str, dict[str, Any]] = {}
        parse_errors = 0
        for tile in tiles_raw + list(upcoming_raw):
            try:
                parsed = parse_tile(tile, site_base=self._settings.spacex_site_base_url)
            except Exception:
                parse_errors += 1
                logger.exception("failed to parse launch tile")
                continue
            by_slug[parsed["slug"]] = parsed

        launches: list[Launch] = []
        for parsed in by_slug.values():
            corr = parsed.get("correlation_id")
            timings = timings_by_corr.get(corr) if corr else None
            detail = None
            raw_detail = details_raw.get(parsed["slug"])
            if isinstance(raw_detail, dict) and "error" not in raw_detail:
                try:
                    detail = parse_mission_detail(raw_detail)
                except Exception:
                    parse_errors += 1
                    logger.exception("failed to parse mission detail slug=%s", parsed["slug"])
            try:
                launches.append(
                    merge_launch(parsed, timings, detail, fetched_at=fetched_at)
                )
            except Exception:
                parse_errors += 1
                logger.exception("failed to merge launch slug=%s", parsed.get("slug"))

        meta = {
            "parse_errors": parse_errors,
            "upcoming_count": len(upcoming_raw),
            "tile_count": len(tiles_raw),
            "timing_count": len(timings_by_corr),
            "fetched_at": fetched_at,
        }
        if not launches:
            raise ValueError("parser produced zero launches from a non-empty payload")
        return launches, meta


def _strip_media(value: Any) -> Any:
    if isinstance(value, dict):
        skip = {
            "imageDesktop",
            "imageMobile",
            "videoDesktop",
            "videoMobile",
            "infographicDesktop",
            "infographicMobile",
            "carousel",
            "media",
            "formats",
        }
        return {k: _strip_media(v) for k, v in value.items() if k not in skip}
    if isinstance(value, list):
        return [_strip_media(v) for v in value]
    return value
