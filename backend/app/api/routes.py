from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.deps import banner_for, parse_simulate, simulated_now
from app.core.time import utcnow
from app.schemas.api import (
    CurrentResponse,
    HealthResponse,
    LaunchDetailResponse,
    LaunchListResponse,
    MetaOut,
    launch_out,
    state_out,
)
from app.services.events import sse_stream
from app.services.repository import LaunchRepository
from app.services.selection import annotate, live_launches, recent_launches, select_current, upcoming_launches

router = APIRouter()


def _apply_simulation(launch, offset: int | None):
    """Windows are not T0 in production; simulation treats window open as T0 for visual testing."""
    if offset is None:
        return launch
    return launch.model_copy(update={"is_window": False, "is_exact_time": True})


def _sessions(request: Request) -> async_sessionmaker[AsyncSession]:
    return request.app.state.session_maker


def _meta(request: Request, *, simulation: bool = False) -> MetaOut:
    ingestion = request.app.state.ingestion
    stale = None
    if ingestion.last_success_at:
        stale = int((utcnow() - ingestion.last_success_at).total_seconds())
    banner = banner_for(request)
    return MetaOut(
        server_time=utcnow(),
        data_updated_at=ingestion.last_success_at,
        stale_seconds=stale,
        used_cache=ingestion.last_used_cache,
        banner=banner,
        simulation=simulation,
    )


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    ingestion = request.app.state.ingestion
    return HealthResponse(
        status="ok",
        server_time=utcnow(),
        last_ingest_ok=ingestion.last_error is None if ingestion.last_success_at else None,
        last_ingest_at=ingestion.last_success_at,
        used_cache=ingestion.last_used_cache,
    )


@router.get("/launches", response_model=LaunchListResponse)
async def list_all(request: Request) -> LaunchListResponse:
    async with _sessions(request)() as session:
        launches = await LaunchRepository(session).list_launches()
    engine = request.app.state.engine
    now = utcnow()
    payload = []
    for launch in launches:
        launch, state = annotate(launch, now, engine)
        payload.append(launch_out(launch, state.live_status))
    return LaunchListResponse(launches=payload, meta=_meta(request))


@router.get("/launches/upcoming", response_model=LaunchListResponse)
async def list_upcoming(request: Request) -> LaunchListResponse:
    async with _sessions(request)() as session:
        launches = await LaunchRepository(session).list_launches()
    engine = request.app.state.engine
    now = utcnow()
    items = upcoming_launches(launches, now, engine)
    payload = []
    for launch in items:
        launch, state = annotate(launch, now, engine)
        payload.append(launch_out(launch, state.live_status))
    return LaunchListResponse(launches=payload, meta=_meta(request))


@router.get("/launches/recent", response_model=LaunchListResponse)
async def list_recent(request: Request) -> LaunchListResponse:
    async with _sessions(request)() as session:
        launches = await LaunchRepository(session).list_launches()
    engine = request.app.state.engine
    now = utcnow()
    items = recent_launches(launches, now, engine)
    payload = []
    for launch in items:
        launch, state = annotate(launch, now, engine)
        payload.append(launch_out(launch, state.live_status))
    return LaunchListResponse(launches=payload, meta=_meta(request))


@router.get("/launches/live", response_model=LaunchListResponse)
async def list_live(request: Request) -> LaunchListResponse:
    async with _sessions(request)() as session:
        launches = await LaunchRepository(session).list_launches()
    engine = request.app.state.engine
    now = utcnow()
    items = live_launches(launches, now, engine)
    payload = []
    for launch in items:
        launch, state = annotate(launch, now, engine)
        payload.append(launch_out(launch, state.live_status))
    return LaunchListResponse(launches=payload, meta=_meta(request))


@router.get("/current", response_model=CurrentResponse)
async def current(
    request: Request,
    simulate: str | None = Query(default=None),
) -> CurrentResponse:
    offset = parse_simulate(simulate, request.app.state.settings.is_development)
    async with _sessions(request)() as session:
        launches = await LaunchRepository(session).list_launches()
    engine = request.app.state.engine
    now = utcnow()
    selected = select_current(launches, now, engine)
    if selected is None:
        return CurrentResponse(launch=None, state=None, meta=_meta(request))
    selected = _apply_simulation(selected, offset)
    sim_now, is_sim = simulated_now(selected.launch_time_start, offset)
    launch, state = annotate(selected, sim_now, engine)
    if is_sim:
        state.notes = ["SIMULATION — development only. Not persisted.", *state.notes]
        state.is_estimated = True
    return CurrentResponse(
        launch=launch_out(launch, state.live_status),
        state=state_out(state),
        meta=_meta(request, simulation=is_sim),
    )


@router.get("/launches/{slug}", response_model=LaunchDetailResponse)
async def launch_detail(
    slug: str,
    request: Request,
    simulate: str | None = Query(default=None),
) -> LaunchDetailResponse:
    offset = parse_simulate(simulate, request.app.state.settings.is_development)
    async with _sessions(request)() as session:
        launch = await LaunchRepository(session).get(slug)
    if launch is None:
        raise HTTPException(status_code=404, detail="Launch not found")
    launch = _apply_simulation(launch, offset)
    sim_now, is_sim = simulated_now(launch.launch_time_start, offset)
    launch, state = annotate(launch, sim_now, request.app.state.engine)
    if is_sim:
        state.notes = ["SIMULATION — development only. Not persisted.", *state.notes]
        state.is_estimated = True
    return LaunchDetailResponse(
        launch=launch_out(launch, state.live_status),
        state=state_out(state),
        meta=_meta(request, simulation=is_sim),
    )


@router.get("/launches/{slug}/state")
async def launch_state(
    slug: str,
    request: Request,
    simulate: str | None = Query(default=None),
):
    detail = await launch_detail(slug, request, simulate)
    return {"launch_id": slug, "state": detail.state, "meta": detail.meta}


@router.get("/events/stream")
async def events(request: Request) -> StreamingResponse:
    broker = request.app.state.broker
    return StreamingResponse(sse_stream(broker), media_type="text/event-stream")
