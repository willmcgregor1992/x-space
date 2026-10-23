from __future__ import annotations

from app.core.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient


def _client() -> TestClient:
    settings = Settings(
        app_env="test",
        database_url="sqlite+aiosqlite:///:memory:",
        cors_origins="http://test",
    )
    return TestClient(create_app(settings))


def test_health():
    with _client() as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


def test_current_and_upcoming():
    with _client() as client:
        current = client.get("/api/current")
        assert current.status_code == 200
        body = current.json()
        assert body["launch"]["id"]
        assert body["state"]["state"]
        assert "server_time" in body["meta"]

        upcoming = client.get("/api/launches/upcoming")
        assert upcoming.status_code == 200
        slugs = [item["id"] for item in upcoming.json()["launches"]]
        assert "sl-15-15" in slugs


def test_launch_state_endpoint():
    with _client() as client:
        response = client.get("/api/launches/sl-15-15/state")
        assert response.status_code == 200
        assert response.json()["state"]["is_estimated"] in {True, False}


def test_simulate_rejected_outside_development():
    with _client() as client:
        response = client.get("/api/current", params={"simulate": "tplus-180"})
        assert response.status_code == 400
