"""Telemetry API key + admin routes (no real Postgres)."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from app.main import create_app

HDR = {"X-Telemetry-Api-Key": "k"}


def test_admin_list_503_when_keys_unset() -> None:
    with TestClient(create_app()) as client:
        r = client.get("/api/v1/catalog/events")
    assert r.status_code == 503
    assert "TELEMETRY_API_KEYS" in r.json()["detail"]


def test_admin_list_401_wrong_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEMETRY_API_KEYS", "correct-one")
    with TestClient(create_app()) as client:
        r = client.get(
            "/api/v1/catalog/events",
            headers={"X-Telemetry-Api-Key": "wrong"},
        )
    assert r.status_code == 401


def test_admin_list_503_no_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEMETRY_API_KEYS", "k")
    with TestClient(create_app()) as client:
        r = client.get("/api/v1/catalog/events", headers=HDR)
    assert r.status_code == 503
    assert "DATABASE_URL" in r.json()["detail"]


def test_admin_bearer_ok_header_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    """Valid key + no DB still yields 503 from handler (pool missing)."""
    monkeypatch.setenv("TELEMETRY_API_KEYS", "secret-token")
    with TestClient(create_app()) as client:
        r = client.get(
            "/api/v1/catalog/events",
            headers={"Authorization": "Bearer secret-token"},
        )
    assert r.status_code == 503


def test_legacy_admin_header_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    """X-Telemetry-Admin-Key still accepted (same key ring)."""
    monkeypatch.setenv("TELEMETRY_API_KEYS", "legacy")
    with TestClient(create_app()) as client:
        r = client.get(
            "/api/v1/catalog/events",
            headers={"X-Telemetry-Admin-Key": "legacy"},
        )
    assert r.status_code == 503


def test_admin_create_invalid_canonical_before_db(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEMETRY_API_KEYS", "k")
    with TestClient(create_app()) as client:
        r = client.post(
            "/api/v1/catalog/events",
            headers=HDR,
            json={
                "canonical_name": "not_PascalCase",
                "lifecycle_status": "active",
            },
        )
    assert r.status_code == 400
    assert "PascalCase" in r.json()["detail"]
