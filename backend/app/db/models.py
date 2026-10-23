from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class LaunchRow(Base):
    __tablename__ = "launches"

    slug: Mapped[str] = mapped_column(String(128), primary_key=True)
    mission_name: Mapped[str] = mapped_column(String(256))
    vehicle: Mapped[str | None] = mapped_column(String(64), nullable=True)
    launch_site: Mapped[str | None] = mapped_column(String(128), nullable=True)
    landing_site: Mapped[str | None] = mapped_column(String(128), nullable=True)
    landing_method: Mapped[str | None] = mapped_column(String(128), nullable=True)
    launch_time_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    launch_time_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    launch_timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    is_exact_time: Mapped[bool] = mapped_column(Boolean, default=False)
    is_window: Mapped[bool] = mapped_column(Boolean, default=False)
    tzero_paused: Mapped[bool] = mapped_column(Boolean, default=False)
    tzero_hold_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    official_url: Mapped[str] = mapped_column(String(512))
    webcast_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="unknown")
    mission_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cms_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    cms_is_live: Mapped[bool] = mapped_column(Boolean, default=False)
    call_to_action: Mapped[str | None] = mapped_column(String(64), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    iss_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    iss_tense: Mapped[str | None] = mapped_column(String(32), nullable=True)
    return_datetime_text: Mapped[str | None] = mapped_column(String(128), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    profile_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    booster_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    webcasts_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    provenance_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    extra_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    milestones: Mapped[list[MilestoneRow]] = relationship(
        back_populates="launch", cascade="all, delete-orphan"
    )


class MilestoneRow(Base):
    __tablename__ = "mission_milestones"
    __table_args__ = (UniqueConstraint("launch_slug", "key", name="uq_milestone_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    launch_slug: Mapped[str] = mapped_column(ForeignKey("launches.slug"), index=True)
    key: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(128))
    t_plus_seconds: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(Text, default="")
    phase: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_estimated: Mapped[bool] = mapped_column(Boolean, default=True)
    source: Mapped[str] = mapped_column(String(32), default="mission_profile")
    visual_role: Mapped[str | None] = mapped_column(String(32), nullable=True)

    launch: Mapped[LaunchRow] = relationship(back_populates="milestones")


class SourceSnapshotRow(Base):
    __tablename__ = "source_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    endpoint: Mapped[str] = mapped_column(String(64), index=True)
    payload_hash: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class IngestionRunRow(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ok: Mapped[bool] = mapped_column(Boolean, default=False)
    used_cache: Mapped[bool] = mapped_column(Boolean, default=False)
    launches_upserted: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
