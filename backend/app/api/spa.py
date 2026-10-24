from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse


def mount_frontend(app: FastAPI, static_dir: Path) -> None:
    """Serve the Vite production build on the same origin as /api."""
    static_dir = static_dir.resolve()
    index = static_dir / "index.html"
    if not index.is_file():
        return

    @app.get("/")
    async def spa_index() -> FileResponse:
        return FileResponse(index)

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str) -> FileResponse:
        if full_path.startswith("api/"):
            return FileResponse(index)
        candidate = (static_dir / full_path).resolve()
        try:
            candidate.relative_to(static_dir)
        except ValueError:
            return FileResponse(index)
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index)
