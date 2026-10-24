# Single-service image for Render / Railway / Fly.
# Builds the Vite UI, then serves it from FastAPI on the same origin as /api.
FROM node:22-alpine AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    DATABASE_URL=sqlite+aiosqlite:////data/mission_control.db \
    SEED_FROM_FIXTURES_ON_FAILURE=false \
    FRONTEND_DIST=/app/static \
    CORS_ORIGINS=*

COPY backend/pyproject.toml /app/pyproject.toml
COPY backend/app /app/app
COPY backend/tests/fixtures /app/tests/fixtures
COPY --from=frontend /frontend/dist /app/static

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir . \
    && mkdir -p /data

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
