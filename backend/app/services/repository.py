from __future__ import annotations

import hashlib
import json
from datetime import datetime

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.time import assume_utc, utcnow
from app.db.models import IngestionRunRow, LaunchRow, MilestoneRow, SourceSnapshotRow
from app.models.domain import (
    BoosterInformation,
    Launch,
    Milestone,
    PayloadInformation,
    Provenance,
    Webcast,
)
from app.models.enums import DataSource, LaunchStatus


def _fingerprint(launch: Launch) -> str:
    payload = {
        "name": launch.mission_name,
        "start": launch.launch_time_start.isoformat() if launch.launch_time_start else None,
        "end": launch.launch_time_end.isoformat() if launch.launch_time_end else None,
        "status": launch.cms_status,
        "is_live": launch.cms_is_live,
        "webcast": launch.webcast_url,
        "window": launch.is_window,
        "paused": launch.tzero_paused,
    }
    blob = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()


class LaunchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_launches(self, launches: list[Launch]) -> list[str]:
        changed: list[str] = []
        now = utcnow()
        for launch in launches:
            fingerprint = _fingerprint(launch)
            existing = await self.session.get(LaunchRow, launch.slug)
            if existing and existing.fingerprint == fingerprint:
                existing.fetched_at = launch.fetched_at
                continue
            if existing:
                self._apply(existing, launch, fingerprint, now)
                existing.milestones.clear()
                existing.milestones.extend(_milestone_rows(launch))
                changed.append(launch.slug)
            else:
                row = LaunchRow(slug=launch.slug, created_at=now, updated_at=now)
                self._apply(row, launch, fingerprint, now)
                row.milestones = _milestone_rows(launch)
                self.session.add(row)
                changed.append(launch.slug)
        await self.session.commit()
        return changed

    def _apply(self, row: LaunchRow, launch: Launch, fingerprint: str, now: datetime) -> None:
        row.mission_name = launch.mission_name
        row.vehicle = launch.vehicle
        row.launch_site = launch.launch_site
        row.landing_site = launch.landing_site
        row.landing_method = launch.landing_method
        row.launch_time_start = launch.launch_time_start
        row.launch_time_end = launch.launch_time_end
        row.launch_timezone = launch.launch_timezone
        row.is_exact_time = launch.is_exact_time
        row.is_window = launch.is_window
        row.tzero_paused = launch.tzero_paused
        row.tzero_hold_seconds = launch.tzero_hold_seconds
        row.official_url = launch.official_url
        row.webcast_url = launch.webcast_url
        row.description = launch.description
        row.status = str(launch.status)
        row.mission_type = launch.mission_type
        row.cms_status = launch.cms_status
        row.cms_is_live = launch.cms_is_live
        row.call_to_action = launch.call_to_action
        row.correlation_id = launch.correlation_id
        row.iss_enabled = launch.iss_enabled
        row.iss_tense = launch.iss_tense
        row.return_datetime_text = launch.return_datetime_text
        row.image_url = launch.image_url
        row.profile_id = launch.profile_id
        row.booster_json = launch.booster_information.model_dump(mode="json") if launch.booster_information else None
        row.payload_json = launch.payload_information.model_dump(mode="json") if launch.payload_information else None
        row.webcasts_json = [item.model_dump(mode="json") for item in launch.webcasts]
        row.provenance_json = {k: v.model_dump(mode="json") for k, v in launch.field_provenance.items()}
        row.extra_json = launch.extra
        row.fingerprint = fingerprint
        row.source_updated_at = launch.source_updated_at
        row.fetched_at = launch.fetched_at
        row.updated_at = now

    async def list_launches(self) -> list[Launch]:
        stmt: Select[tuple[LaunchRow]] = (
            select(LaunchRow).options(selectinload(LaunchRow.milestones)).order_by(LaunchRow.slug)
        )
        rows = (await self.session.execute(stmt)).scalars().unique().all()
        return [row_to_launch(row) for row in rows]

    async def get(self, slug: str) -> Launch | None:
        stmt = (
            select(LaunchRow)
            .options(selectinload(LaunchRow.milestones))
            .where(LaunchRow.slug == slug)
        )
        row = (await self.session.execute(stmt)).scalar_one_or_none()
        return row_to_launch(row) if row else None

    async def save_snapshot(self, endpoint: str, payload: dict) -> None:
        blob = json.dumps(payload, sort_keys=True, default=str)
        digest = hashlib.sha256(blob.encode()).hexdigest()
        self.session.add(
            SourceSnapshotRow(
                endpoint=endpoint,
                payload_hash=digest,
                payload=payload,
                fetched_at=utcnow(),
            )
        )
        # Keep the last three snapshots per endpoint.
        stmt = (
            select(SourceSnapshotRow)
            .where(SourceSnapshotRow.endpoint == endpoint)
            .order_by(SourceSnapshotRow.fetched_at.desc())
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        for stale in rows[2:]:
            await self.session.delete(stale)
        await self.session.commit()

    async def record_run(self, **kwargs) -> None:
        self.session.add(IngestionRunRow(**kwargs))
        await self.session.commit()

    async def latest_run(self) -> IngestionRunRow | None:
        stmt = select(IngestionRunRow).order_by(IngestionRunRow.started_at.desc()).limit(1)
        return (await self.session.execute(stmt)).scalar_one_or_none()


def _milestone_rows(launch: Launch) -> list[MilestoneRow]:
    return [
        MilestoneRow(
            launch_slug=launch.slug,
            key=item.key,
            name=item.name,
            t_plus_seconds=item.t_plus_seconds,
            description=item.description,
            phase=item.phase,
            is_estimated=item.is_estimated,
            source=str(item.source),
            visual_role=item.visual_role,
        )
        for item in launch.milestones
    ]


def row_to_launch(row: LaunchRow) -> Launch:
    booster = BoosterInformation.model_validate(row.booster_json) if row.booster_json else None
    payload = PayloadInformation.model_validate(row.payload_json) if row.payload_json else None
    webcasts = [Webcast.model_validate(item) for item in (row.webcasts_json or [])]
    provenance = {
        key: Provenance.model_validate(value) for key, value in (row.provenance_json or {}).items()
    }
    milestones = [
        Milestone(
            key=item.key,
            name=item.name,
            t_plus_seconds=item.t_plus_seconds,
            description=item.description,
            phase=item.phase,
            is_estimated=item.is_estimated,
            source=DataSource(item.source) if item.source in DataSource._value2member_map_ else DataSource.MISSION_PROFILE,
            visual_role=item.visual_role,
        )
        for item in sorted(row.milestones, key=lambda m: m.t_plus_seconds)
    ]
    return Launch(
        id=row.slug,
        slug=row.slug,
        mission_name=row.mission_name,
        vehicle=row.vehicle,
        launch_site=row.launch_site,
        landing_site=row.landing_site,
        landing_method=row.landing_method,
        launch_time_start=assume_utc(row.launch_time_start),
        launch_time_end=assume_utc(row.launch_time_end),
        launch_timezone=row.launch_timezone,
        is_exact_time=row.is_exact_time,
        is_window=row.is_window,
        tzero_paused=row.tzero_paused,
        tzero_hold_seconds=row.tzero_hold_seconds,
        official_url=row.official_url,
        webcast_url=row.webcast_url,
        webcasts=webcasts,
        description=row.description,
        status=LaunchStatus(row.status) if row.status in LaunchStatus._value2member_map_ else LaunchStatus.UNKNOWN,
        mission_type=row.mission_type,
        booster_information=booster,
        payload_information=payload,
        source_updated_at=assume_utc(row.source_updated_at),
        fetched_at=assume_utc(row.fetched_at) or utcnow(),
        cms_status=row.cms_status,
        cms_is_live=row.cms_is_live,
        call_to_action=row.call_to_action,
        correlation_id=row.correlation_id,
        iss_enabled=row.iss_enabled,
        iss_tense=row.iss_tense,
        return_datetime_text=row.return_datetime_text,
        image_url=row.image_url,
        profile_id=row.profile_id,
        milestones=milestones,
        field_provenance=provenance,
        extra=row.extra_json or {},
    )
