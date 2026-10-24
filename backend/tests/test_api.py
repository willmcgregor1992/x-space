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


def test_spa_served_from_frontend_dist(tmp_path):
    (tmp_path / "index.html").write_text("<!doctype html><title>Mission Control</title>", encoding="utf-8")
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "app.js").write_text("console.log('ok')", encoding="utf-8")
    settings = Settings(
        app_env="test",
        database_url="sqlite+aiosqlite:///:memory:",
        cors_origins="http://test",
        frontend_dist=str(tmp_path),
    )
    with TestClient(create_app(settings)) as client:
        home = client.get("/")
        assert home.status_code == 200
        assert "Mission Control" in home.text
        asset = client.get("/assets/app.js")
        assert asset.status_code == 200
        assert "console.log" in asset.text
        deep = client.get("/anything/deep")
        assert deep.status_code == 200
        assert "Mission Control" in deep.text
        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"
