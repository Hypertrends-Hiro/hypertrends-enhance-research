"""
Telemetry ingest — requires TELEMETRY_API_KEYS (X-Telemetry-Api-Key or Bearer).

When DATABASE_URL is set, catalog + system_catalog_configs gate Braze.
"""

from __future__ import annotations

import asyncio
import uuid
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Final

from fastapi import APIRouter, Depends

from app.braze_forward import braze_configured, forward_ingest_to_braze
from app.deps import require_telemetry_api_key
from app.catalog_policy import fetch_canonical_name, ingest_braze_decision, resolve_event_id
from app.db import db_pool
from app.ingest_audit import try_record_ingest_audit
from app.schemas.ingest import (
    BatchIngestRequest,
    BatchIngestResponse,
    BatchItemResult,
    IngestPayload,
    IngestResponse,
)

router = APIRouter(
    prefix="/telemetry",
    tags=["telemetry"],
    dependencies=[Depends(require_telemetry_api_key)],
)

_MAX_IDS: Final[int] = 50_000
_seen_message_ids: OrderedDict[str, None] = OrderedDict()
_lock = asyncio.Lock()


async def _register_id(message_id: str) -> bool:
    async with _lock:
        if message_id in _seen_message_ids:
            _seen_message_ids.move_to_end(message_id)
            return False
        _seen_message_ids[message_id] = None
        while len(_seen_message_ids) > _MAX_IDS:
            _seen_message_ids.popitem(last=False)
        return True


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _ingest_forwarding(
    body: IngestPayload,
) -> tuple[str, dict[str, str], str | None, uuid.UUID | None]:
    """Human note fragment (after 'Accepted. '), forwarding map, canonical, event_id."""
    pool = db_pool()
    forwarding: dict[str, str] = {}
    canonical_name: str | None = None
    event_id: uuid.UUID | None = None
    if pool:
        async with pool.acquire() as conn:
            allow, cat_reason = await ingest_braze_decision(conn, body)
            eid = await resolve_event_id(conn, body.event.name)
            if eid:
                event_id = eid
                canonical_name = await fetch_canonical_name(conn, eid)
        if not allow:
            forwarding["braze"] = "skipped"
            return f"catalog: {cat_reason}; Braze not called.", forwarding, canonical_name, event_id
        if braze_configured():
            b = await forward_ingest_to_braze(body)
            if "ok" in b.lower():
                forwarding["braze"] = "ok"
            elif "skipped" in b.lower():
                forwarding["braze"] = "skipped"
            else:
                forwarding["braze"] = "error"
            return f"{b} (catalog ok)", forwarding, canonical_name, event_id
        forwarding["braze"] = "skipped_no_credentials"
        return (
            "catalog ok; Braze forward off (set BRAZE_API_KEY + BRAZE_REST_ENDPOINT).",
            forwarding,
            canonical_name,
            event_id,
        )
    if braze_configured():
        b = await forward_ingest_to_braze(body)
        forwarding["braze"] = "ok" if "ok" in b.lower() else ("skipped" if "skipped" in b.lower() else "error")
        return b, forwarding, None, None
    forwarding["braze"] = "skipped_no_credentials"
    return "Braze forward off (set BRAZE_API_KEY + BRAZE_REST_ENDPOINT).", forwarding, None, None


@router.post(
    "/ingest",
    response_model=IngestResponse,
    summary="Ingest single universal telemetry message",
)
async def ingest_one(body: IngestPayload) -> IngestResponse:
    mid = body.meta.message_id
    is_new = await _register_id(mid)
    received = _now()

    if not is_new:
        return IngestResponse(
            status="duplicate_ignored",
            message_id=mid,
            duplicate=True,
            received_at=received,
            note="Same message_id was already accepted in this process.",
            forwarding=None,
        )

    suffix, forwarding, canonical_name, event_id = await _ingest_forwarding(body)
    note_full = f"Accepted. {suffix}"
    status_out = "accepted"
    if forwarding.get("braze") == "skipped" and "catalog:" in suffix:
        status_out = "accepted_not_forwarded"

    pool = db_pool()
    await try_record_ingest_audit(
        pool,
        message_id=mid,
        source_system=(body.meta.source_system or "").strip(),
        tenant=(body.meta.tenant or "").strip(),
        original_event_name=body.event.name,
        canonical_name=canonical_name,
        event_id=event_id,
        decision=status_out,
        forwarding=forwarding,
        note=note_full,
    )

    return IngestResponse(
        status=status_out,
        message_id=mid,
        duplicate=False,
        received_at=received,
        note=note_full,
        forwarding=forwarding or None,
    )


@router.post(
    "/ingest/batch",
    response_model=BatchIngestResponse,
    summary="Ingest up to 100 universal messages",
)
async def ingest_batch(body: BatchIngestRequest) -> BatchIngestResponse:
    received = _now()
    results: list[BatchItemResult] = []

    for i, item in enumerate(body.items):
        mid = item.meta.message_id
        is_new = await _register_id(mid)
        if not is_new:
            results.append(
                BatchItemResult(
                    index=i,
                    message_id=mid,
                    status="duplicate_ignored",
                    duplicate=True,
                    note="Duplicate message_id in this process.",
                    forwarding=None,
                )
            )
        else:
            suffix, forwarding, canonical_name, event_id = await _ingest_forwarding(item)
            note_full = f"Accepted. {suffix}"
            st = "accepted"
            if forwarding.get("braze") == "skipped" and "catalog:" in suffix:
                st = "accepted_not_forwarded"
            pool = db_pool()
            await try_record_ingest_audit(
                pool,
                message_id=mid,
                source_system=(item.meta.source_system or "").strip(),
                tenant=(item.meta.tenant or "").strip(),
                original_event_name=item.event.name,
                canonical_name=canonical_name,
                event_id=event_id,
                decision=st,
                forwarding=forwarding,
                note=note_full,
            )
            results.append(
                BatchItemResult(
                    index=i,
                    message_id=mid,
                    status=st,
                    duplicate=False,
                    note=note_full,
                    forwarding=forwarding or None,
                )
            )

    return BatchIngestResponse(results=results, received_at=received)
