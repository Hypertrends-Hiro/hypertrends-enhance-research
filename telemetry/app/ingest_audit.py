"""Persist ingest outcomes to telemetry_ingest_audit (optional)."""

from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Any

logger = logging.getLogger(__name__)


def _audit_enabled() -> bool:
    return os.getenv("TELEMETRY_AUDIT_INGEST", "1").strip().lower() not in ("0", "false", "no")


async def record_ingest_audit(
    conn: Any,
    *,
    message_id: str,
    source_system: str,
    tenant: str,
    original_event_name: str,
    canonical_name: str | None,
    event_id: uuid.UUID | None,
    decision: str,
    forwarding: dict[str, str],
    note: str | None,
) -> None:
    await conn.execute(
        """
        INSERT INTO telemetry_ingest_audit (
            message_id, source_system, tenant, original_event_name,
            canonical_name, event_id, decision, forwarding, note
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9)
        """,
        message_id,
        source_system,
        tenant,
        original_event_name,
        canonical_name,
        event_id,
        decision,
        json.dumps(forwarding),
        note,
    )


async def try_record_ingest_audit(
    pool: Any,
    *,
    message_id: str,
    source_system: str,
    tenant: str,
    original_event_name: str,
    canonical_name: str | None,
    event_id: uuid.UUID | None,
    decision: str,
    forwarding: dict[str, str],
    note: str | None,
) -> None:
    if pool is None or not _audit_enabled():
        return
    try:
        async with pool.acquire() as conn:
            await record_ingest_audit(
                conn,
                message_id=message_id,
                source_system=source_system,
                tenant=tenant,
                original_event_name=original_event_name,
                canonical_name=canonical_name,
                event_id=event_id,
                decision=decision,
                forwarding=forwarding,
                note=note,
            )
    except Exception:
        logger.warning("telemetry_ingest_audit insert failed (run sql/002?)", exc_info=True)
