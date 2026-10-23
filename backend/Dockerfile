FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATABASE_URL=sqlite+aiosqlite:////data/mission_control.db \
    APP_ENV=production \
    SEED_FROM_FIXTURES_ON_FAILURE=false

COPY pyproject.toml /app/pyproject.toml
COPY app /app/app
COPY tests/fixtures /app/tests/fixtures

RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir . \
    && mkdir -p /data

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
