"""HTTP-level tests for catalog and ingest (API key + mocked Braze)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from starlette.testclient import TestClient

from app.main import create_app
from app.schemas.ingest import IngestPayload


def _headers(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    monkeypatch.setenv("TELEMETRY_API_KEYS", "test-key")
    return {"X-Telemetry-Api-Key": "test-key"}


def _ingest_json(message_id: str | None = None) -> dict:
    mid = message_id or str(uuid.uuid4())
    t = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "meta": {
            "message_id": mid,
            "occurred_at": t,
            "source_system": "pytest",
            "tenant": "t1",
        },
        "event": {"name": "PageViewed", "time": t, "properties": {}},
        "purchase": {"enabled": False},
    }


def test_get_public_catalog_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _headers(monkeypatch)
    with TestClient(create_app()) as client:
        r = client.get("/api/v1/telemetry/catalog", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert "events" in data
    assert any(e["name"] == "page_viewed" for e in data["events"])
    assert "Stub" in (data.get("note") or "")


def test_ingest_503_when_api_keys_unset() -> None:
    with TestClient(create_app()) as client:
        r = client.post("/api/v1/telemetry/ingest", json=_ingest_json())
    assert r.status_code == 503
    assert "TELEMETRY_API_KEYS" in r.json()["detail"]


def test_health_503_when_api_keys_unset() -> None:
    with TestClient(create_app()) as client:
        r = client.get("/health")
    assert r.status_code == 503


def test_ingest_401_wrong_or_missing_key_when_keys_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEMETRY_API_KEYS", "secret")
    with TestClient(create_app()) as client:
        r = client.post("/api/v1/telemetry/ingest", json=_ingest_json())
        assert r.status_code == 401
        r2 = client.post(
            "/api/v1/telemetry/ingest",
            json=_ingest_json(),
            headers={"X-Telemetry-Api-Key": "nope"},
        )
        assert r2.status_code == 401


def test_ingest_no_db_skips_braze_when_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _headers(monkeypatch)
    with TestClient(create_app()) as client:
        r = client.post("/api/v1/telemetry/ingest", json=_ingest_json(), headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "accepted"
    assert body["duplicate"] is False
    assert body.get("forwarding", {}).get("braze") == "skipped_no_credentials"


def test_ingest_no_db_forwards_when_braze_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_forward(_body: IngestPayload) -> str:
        return "braze ok HTTP 201"

    monkeypatch.setattr(
        "app.routers.ingest.forward_ingest_to_braze",
        fake_forward,
    )
    monkeypatch.setattr("app.routers.ingest.braze_configured", lambda: True)
    h = _headers(monkeypatch)

    with TestClient(create_app()) as client:
        r = client.post("/api/v1/telemetry/ingest", json=_ingest_json(), headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "accepted"
    assert body.get("forwarding", {}).get("braze") == "ok"


def test_ingest_duplicate_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _headers(monkeypatch)
    payload = _ingest_json("018f7aa0-4f2f-7e4a-a0dc-1e6d2d69b099")
    with TestClient(create_app()) as client:
        r1 = client.post("/api/v1/telemetry/ingest", json=payload, headers=h)
        r2 = client.post("/api/v1/telemetry/ingest", json=payload, headers=h)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["duplicate"] is False
    assert r2.json()["status"] == "duplicate_ignored"
    assert r2.json()["duplicate"] is True
