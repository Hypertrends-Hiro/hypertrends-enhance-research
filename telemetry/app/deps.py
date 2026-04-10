"""FastAPI dependencies — API key for all telemetry HTTP routes."""

from __future__ import annotations

import os

from fastapi import Header, HTTPException, status


def _telemetry_api_key_set() -> set[str]:
    raw = os.getenv("TELEMETRY_API_KEYS", "").strip()
    return {k.strip() for k in raw.split(",") if k.strip()}


async def require_telemetry_api_key(
    x_telemetry_api_key: str | None = Header(None, alias="X-Telemetry-Api-Key"),
    x_telemetry_admin_key: str | None = Header(
        None,
        alias="X-Telemetry-Admin-Key",
        description="Deprecated alias; same validation as X-Telemetry-Api-Key.",
    ),
    authorization: str | None = Header(None),
) -> str:
    """Require a key from TELEMETRY_API_KEYS via X-Telemetry-Api-Key, X-Telemetry-Admin-Key, or Bearer."""
    keys = _telemetry_api_key_set()
    if not keys:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telemetry API disabled: set TELEMETRY_API_KEYS (comma-separated).",
        )
    token: str | None = None
    if x_telemetry_api_key:
        token = x_telemetry_api_key.strip()
    elif x_telemetry_admin_key:
        token = x_telemetry_admin_key.strip()
    elif authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    if not token or token not in keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key (X-Telemetry-Api-Key or Authorization: Bearer).",
        )
    return token
