"""Pytest fixtures — isolate env and DB pool for the FastAPI app."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _telemetry_test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """No real DB or admin keys unless a test sets them explicitly."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("TELEMETRY_API_KEYS", raising=False)
    monkeypatch.delenv("TELEMETRY_IGNORE_CATALOG", raising=False)
    monkeypatch.delenv("TELEMETRY_AUDIT_INGEST", raising=False)
    monkeypatch.delenv("BRAZE_API_KEY", raising=False)
    monkeypatch.delenv("BRAZE_REST_ENDPOINT", raising=False)
    monkeypatch.delenv("BRAZE_API_ENDPOINT", raising=False)
