"""
Telemetry ingest — open endpoints for Phase 1 (no auth).

Security (API keys, mTLS, rate limits) will be added in a later phase.
"""

from __future__ import annotations

import asyncio
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Final

from fastapi import APIRouter

from app.braze_forward import braze_configured, forward_ingest_to_braze
from app.catalog_policy import ingest_braze_decision
from app.db import db_pool
from app.schemas.ingest import (
    BatchIngestRequest,
    BatchIngestResponse,
    BatchItemResult,
    IngestPayload,
    IngestResponse,
)

router = APIRouter(prefix="/telemetry", tags=["telemetry"])

# In-process idempotency (dev / single-worker). Replace with Redis/DB in production.
_MAX_IDS: Final[int] = 50_000
_seen_message_ids: OrderedDict[str, None] = OrderedDict()
_lock = asyncio.Lock()


async def _register_id(message_id: str) -> bool:
    """
    Returns True if new, False if duplicate.
    """
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


async def _braze_note_for_ingest(body: IngestPayload) -> str:
    """
    If DATABASE_URL is set, enforce catalog + system_catalog_configs before calling Braze.
    Set TELEMETRY_IGNORE_CATALOG=1 to skip DB checks while DATABASE_URL is set.
    """
    pool = db_pool()
    if pool:
        async with pool.acquire() as conn:
            allow, cat_reason = await ingest_braze_decision(conn, body)
        if not allow:
            return f"catalog: {cat_reason}; Braze not called."
        if braze_configured():
            b = await forward_ingest_to_braze(body)
            return f"{b} (catalog ok)"
        return "catalog ok; Braze forward off (set BRAZE_API_KEY + BRAZE_REST_ENDPOINT)."
    if braze_configured():
        return await forward_ingest_to_braze(body)
    return "Braze forward off (set BRAZE_API_KEY + BRAZE_REST_ENDPOINT)."


@router.post(
    "/ingest",
    response_model=IngestResponse,
    summary="Ingest single universal telemetry message",
    description="""
Accepts one payload matching `telemetry/.plan/api-plan.html`.

Validates shape, applies in-memory idempotency, and **forwards to Braze** `/users/track` when `BRAZE_API_KEY` is set.

See also: `payload-usage.html`, `frontend-usage.html`, `backend-usage.html`.
    """,
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
        )

    braze_note = await _braze_note_for_ingest(body)
    return IngestResponse(
        status="accepted",
        message_id=mid,
        duplicate=False,
        received_at=received,
        note=f"Accepted. {braze_note}",
    )


@router.post(
    "/ingest/batch",
    response_model=BatchIngestResponse,
    summary="Ingest up to 100 universal messages",
    description="Cada ítem nuevo se reenvía a Braze cuando BRAZE_API_KEY está configurada (igual que /ingest).",
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
                )
            )
        else:
            bnote = await _braze_note_for_ingest(item)
            results.append(
                BatchItemResult(
                    index=i,
                    message_id=mid,
                    status="accepted",
                    duplicate=False,
                    note=f"Accepted. {bnote}",
                )
            )

    return BatchIngestResponse(results=results, received_at=received)
