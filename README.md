# SpaceX Mission Control

A production-style mission-control dashboard for upcoming and live SpaceX launches.

The app answers three questions as soon as it opens:

1. What is the next SpaceX launch?
2. Is a SpaceX launch currently live?
3. Where is the mission in its journey (schematic / estimated unless SpaceX reports otherwise)?

It is **not** a clone of any concept frame. The visual language is a dark aerospace console: technical type, thin rules, restrained orange accents, and an SVG journey display.

## Prerequisites

- Python 3.12+
- Node.js 20+
- Optional: Docker and Docker Compose

## Architecture

```
frontend (React + Vite)  →  GET /api/* + SSE /api/events/stream
backend  (FastAPI)       →  SpaceX CMS JSON  + SQLite/Postgres
                              MissionStateEngine + mission profiles
```

- **Source of truth:** SpaceX's public CMS JSON behind [spacex.com/launches](https://www.spacex.com/launches), not HTML scraping. See [docs/DATA_SOURCE.md](docs/DATA_SOURCE.md).
- **Normalized model:** the rest of the stack never depends on SpaceX HTML.
- **Mission profiles:** Falcon 9 orbital, Falcon Heavy, Dragon/ISS, and Starship sequences live in `backend/app/data/profiles/`.
- **Estimated vs official:** interpolated vehicle position is always labelled estimated. Official CMS fields carry `spacex.com` provenance.

## Installation

```bash
cp .env.example .env
```

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Frontend

```bash
cd frontend
npm install
```

## Environment variables

See `.env.example`. Important keys:

| Variable | Purpose |
| --- | --- |
| `APP_ENV` | `development` / `production` / `test` |
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/mission_control.db` or `postgresql+asyncpg://…` |
| `SPACEX_CMS_BASE_URL` | default `https://content.spacex.com` |
| `INGEST_INTERVAL_*` | refresh cadence (normal / 6h / 30m / active) |
| `SEED_FROM_FIXTURES_ON_FAILURE` | development only: seed from parser fixtures if SpaceX is unreachable |
| `CORS_ORIGINS` | comma-separated frontend origins |

## Running locally

Terminal 1:

```bash
cd backend
source .venv/bin/activate
python -m app
```

API: http://127.0.0.1:8000  
OpenAPI: http://127.0.0.1:8000/docs

Terminal 2:

```bash
cd frontend
npm run dev
```

UI: http://127.0.0.1:5173 (Vite proxies `/api` to the backend).

### Docker

```bash
cp .env.example .env
docker compose up --build
```

- UI: http://localhost:8080
- API: http://localhost:8000

Postgres (optional):

```bash
DATABASE_URL=postgresql+asyncpg://spacex:spacex@postgres:5432/spacex
docker compose --profile postgres up --build
```

## Tests

Backend (never hits spacex.com; uses frozen fixtures):

```bash
cd backend
source .venv/bin/activate
pytest
ruff check app tests
```

Frontend:

```bash
cd frontend
npm test
```

## Production build

```bash
cd frontend && npm run build
cd ../backend && pip install .
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Or `docker compose up --build` with `APP_ENV=production`.

Single-service image (what Railway / Render / Fly should build):

```bash
docker compose --profile single up --build
```

UI and API share http://localhost:8000.

## Deploy online

Hosts that look for a root `Dockerfile` (Railway, Render, Fly) should use the repo-root image. It builds the Vite UI and serves it from FastAPI so the browser can keep calling `/api` on the same origin.

**Railway**

1. New project → Deploy from GitHub → this repo (`main`).
2. Railway reads `railway.toml` and the root `Dockerfile`.
3. Set `APP_ENV=production`. Optional: attach a volume at `/data` so SQLite survives restarts.
4. The public URL is the FastAPI process (`$PORT`). Open `/` for the dashboard and `/api/health` for a liveness check.

Do **not** point the builder at `backend/Dockerfile` or `frontend/Dockerfile` alone. Those are for the local two-container Compose setup. Vercel still needs extra work (hosted Postgres + cron ingest) because this backend is a long-lived process.

## Data source

SpaceX.com/launches is an Angular SPA. Launch rows come from:

- `https://content.spacex.com/api/spacex-website/launches-page-tiles/upcoming`
- `https://content.spacex.com/cms-assets/future_missions.json`
- `https://content.spacex.com/api/spacex-website/launches-page-tiles`
- `https://content.spacex.com/api/spacex-website/missions/{slug}`

The backend isolates this behind `app/providers/spacex.py`. Failures keep the last valid database snapshot and the UI shows **DATA DELAYED** rather than crashing.

## Estimated vs authoritative data

| Kind | Source | UI |
| --- | --- | --- |
| Mission name, site, vehicle, window, webcast | spacex.com | “Official SpaceX data” |
| Post-launch timeline from the mission page | spacex.com, still marked approximate | Estimated T+ |
| Vehicle position along the path | mission profile interpolation | **Estimated position — not real telemetry** |
| ISS “docked” when `toTheIssTense=present` | spacex.com | Reported status |

The dashboard never invents fuel, velocity, altitude, temperature, pressure, or engine state.

## Development simulator

Only in `APP_ENV=development`:

```
http://localhost:5173/?simulate=tplus-180
```

Accepted values: `tminus-600`, `tminus-30`, `t0`, `tplus-60`, `tplus-180`, `tplus-480`, `tplus-3600`.

The UI banners **SIMULATION**. Simulated clocks are not written to the database.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Liveness + ingest freshness |
| GET | `/api/current` | Live launch if one exists, else next |
| GET | `/api/launches` | Tracked launches |
| GET | `/api/launches/upcoming` | Upcoming |
| GET | `/api/launches/recent` | Recent completed |
| GET | `/api/launches/live` | Live / on-orbit |
| GET | `/api/launches/{id}` | Detail + mission state |
| GET | `/api/launches/{id}/state` | MissionStateEngine output |
| GET | `/api/events/stream` | SSE launch-change events |

Interactive docs: `/docs`.
