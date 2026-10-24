from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.api.spa import mount_frontend
from app.core.config import Settings, get_settings
from app.db.session import create_engine, init_db, session_factory
from app.providers.http import SpaceXHttpClient
from app.providers.spacex import SpaceXProvider
from app.services.events import EventBroker
from app.services.ingestion import IngestionService
from app.services.mission_state import MissionStateEngine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings: Settings = app.state.settings
    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
    engine = create_engine(settings)
    await init_db(engine)
    session_maker = session_factory(engine)
    http = SpaceXHttpClient(settings)
    provider = SpaceXProvider(settings, http)
    broker = EventBroker()
    state_engine = MissionStateEngine()
    ingestion = IngestionService(settings, provider, session_maker, broker, state_engine)
    app.state.engine_db = engine
    app.state.session_maker = session_maker
    app.state.http = http
    app.state.broker = broker
    app.state.engine = state_engine
    app.state.ingestion = ingestion
    app.state.settings = settings

    first_ingest = asyncio.create_task(ingestion.run())
    if settings.app_env == "test":
        await first_ingest

    stop = asyncio.Event()

    async def loop() -> None:
        if not first_ingest.done():
            try:
                await first_ingest
            except Exception:
                logger.exception("initial ingest crashed")
                await asyncio.sleep(30)
        while not stop.is_set():
            try:
                async with session_maker() as session:
                    from app.services.repository import LaunchRepository

                    launches = await LaunchRepository(session).list_launches()
                delay = ingestion.next_interval(launches)
                try:
                    await asyncio.wait_for(stop.wait(), timeout=delay)
                    break
                except TimeoutError:
                    await ingestion.run()
            except Exception:
                logger.exception("ingest loop crashed")
                await asyncio.sleep(30)

    task = asyncio.create_task(loop())
    yield
    stop.set()
    first_ingest.cancel()
    task.cancel()
    await http.aclose()
    await engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(
        title="SpaceX Mission Control API",
        version="1.0.0",
        description="Normalized SpaceX launch status, mission state, and live event stream.",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list or ["*"],
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    app.include_router(router, prefix="/api")
    if settings.frontend_dist_path is not None:
        mount_frontend(app, settings.frontend_dist_path)

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception) -> JSONResponse:
        if isinstance(exc, HTTPException):
            return await http_exception_handler(request, exc)
        logger.exception("unhandled error")
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    return app


app = create_app()
