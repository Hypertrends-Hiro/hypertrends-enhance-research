"""Map universal ingest payloads to Braze /users/track and POST asynchronously."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

import httpx

from app.schemas.ingest import IngestPayload

logger = logging.getLogger(__name__)


def braze_configured() -> bool:
    return bool(os.getenv("BRAZE_API_KEY", "").strip())


def _dt_iso_z(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    s = dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return s


def _resolve_external_id(body: IngestPayload) -> str | None:
    if body.user is None:
        return None
    if body.user.external_id:
        return body.user.external_id.strip()
    if body.user.anonymous_id:
        return body.user.anonymous_id.strip()
    return None


def build_users_track_body(body: IngestPayload) -> dict[str, Any]:
    ext = _resolve_external_id(body)
    if not ext:
        raise ValueError("Braze forward requires user.external_id or user.anonymous_id")

    req: dict[str, Any] = {}

    ev: dict[str, Any] = {
        "external_id": ext,
        "name": body.event.name,
        "time": _dt_iso_z(body.event.time),
        "properties": dict(body.event.properties or {}),
    }
    req["events"] = [ev]

    attr: dict[str, Any] = {"external_id": ext}
    if body.user:
        if body.user.email:
            attr["email"] = body.user.email
        if body.user.phone:
            attr["phone"] = body.user.phone
        if body.user.attributes:
            a = body.user.attributes
            if a.first_name:
                attr["first_name"] = a.first_name
            if a.last_name:
                attr["last_name"] = a.last_name
            for k, v in (a.custom or {}).items():
                attr[k] = v
    if len(attr) > 1:
        req["attributes"] = [attr]

    p = body.purchase
    if p.enabled:
        req["purchases"] = [
            {
                "external_id": ext,
                "product_id": p.product_id or "unknown",
                "currency": p.currency or "USD",
                "price": float(p.price if p.price is not None else 0),
                "quantity": int(p.quantity if p.quantity is not None else 1),
                "time": _dt_iso_z(body.event.time),
                "properties": dict(p.properties or {}),
            }
        ]

    return req


async def forward_ingest_to_braze(body: IngestPayload) -> str:
    """
    POST to Braze /users/track. Returns short status for API note (never raises).
    """
    api_key = os.getenv("BRAZE_API_KEY", "").strip()
    endpoint = (
        os.getenv("BRAZE_REST_ENDPOINT") or os.getenv("BRAZE_API_ENDPOINT") or "https://rest.iad-02.braze.com"
    ).rstrip("/")
    if not api_key:
        return "braze skipped (BRAZE_API_KEY unset)"

    try:
        track_body = build_users_track_body(body)
    except ValueError as e:
        return f"braze skipped ({e})"

    url = f"{endpoint}/users/track"
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                url,
                json=track_body,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )
            text = (resp.text or "")[:400]
            if resp.status_code >= 400:
                logger.warning("Braze /users/track %s: %s", resp.status_code, text)
                return f"braze error HTTP {resp.status_code}: {text}"
            return f"braze ok HTTP {resp.status_code}"
    except httpx.RequestError as e:
        logger.warning("Braze request failed: %s", e)
        return f"braze network error: {e!s}"
