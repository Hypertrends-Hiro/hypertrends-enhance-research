"""Resolve catalog + system_catalog_configs for ingest (Postgres)."""

from __future__ import annotations

import json
import os
import uuid
from typing import Any

from app.schemas.ingest import IngestPayload


def _ignore_catalog() -> bool:
    return os.getenv("TELEMETRY_IGNORE_CATALOG", "").strip().lower() in ("1", "true", "yes")


async def resolve_event_id(conn: Any, raw_event_name: str) -> uuid.UUID | None:
    row = await conn.fetchrow(
        "SELECT id FROM catalog_events WHERE canonical_name = $1",
        raw_event_name,
    )
    if row:
        return row["id"]
    row = await conn.fetchrow(
        """
        SELECT ce.id
        FROM catalog_events ce
        JOIN catalog_event_aliases a ON a.event_id = ce.id
        WHERE lower(a.alias) = lower($1)
        LIMIT 1
        """,
        raw_event_name,
    )
    return row["id"] if row else None


async def braze_allowed_by_catalog(
    conn: Any,
    *,
    system_id: str,
    tenant: str,
    event_id: uuid.UUID,
) -> tuple[bool, str]:
    row = await conn.fetchrow(
        """
        SELECT enabled, destinations
        FROM system_catalog_configs
        WHERE system_id = $1 AND tenant = $2 AND event_id = $3
        """,
        system_id,
        tenant,
        event_id,
    )
    if row is None:
        return False, "no system_catalog_config for this system/tenant/event"
    if not row["enabled"]:
        return False, "system_catalog_config.enabled is false"
    dest = row["destinations"]
    if isinstance(dest, str):
        dest = json.loads(dest)
    braze = (dest or {}).get("braze") or {}
    if not braze.get("enabled", False):
        return False, "destinations.braze.enabled is false"
    return True, "catalog allows braze"


async def ingest_braze_decision(conn: Any | None, body: IngestPayload) -> tuple[bool, str]:
    """
    If conn is None or TELEMETRY_IGNORE_CATALOG: allow Braze (caller still checks braze_configured()).
    Else enforce catalog + system_catalog_configs for Braze forward.
    """
    if conn is None or _ignore_catalog():
        return True, "catalog check skipped"

    system_id = (body.meta.source_system or "").strip()
    tenant = (body.meta.tenant or "").strip()
    raw = body.event.name

    eid = await resolve_event_id(conn, raw)
    if eid is None:
        return False, f"unknown event in catalog (event.name={raw!r})"

    ok, reason = await braze_allowed_by_catalog(conn, system_id=system_id, tenant=tenant, event_id=eid)
    if not ok:
        return False, reason
    return True, reason
