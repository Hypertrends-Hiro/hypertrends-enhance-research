"""Admin catalog API — requires TELEMETRY_API_KEYS + DATABASE_URL."""

from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.admin_audit import log_admin_request
from app.catalog_policy import resolve_catalog_for_admin
from app.catalog_validate import is_valid_canonical_event_name
from app.db import db_pool
from app.deps import require_telemetry_api_key
from app.schemas.admin import (
    CatalogEventCreate,
    CatalogEventListResponse,
    CatalogEventOut,
    CatalogResolveRequest,
)

router = APIRouter(prefix="/catalog", tags=["admin-catalog"])
TelemetryApiKey = Annotated[str, Depends(require_telemetry_api_key)]


async def _row_to_event_out(conn, row) -> CatalogEventOut:
    aliases = [
        r["alias"]
        for r in await conn.fetch(
            "SELECT alias FROM catalog_event_aliases WHERE event_id = $1 ORDER BY alias",
            row["id"],
        )
    ]
    meta = row["catalog_metadata"]
    if isinstance(meta, str):
        meta = json.loads(meta)
    return CatalogEventOut(
        id=row["id"],
        canonical_name=row["canonical_name"],
        display_name=row["display_name"],
        description=row["description"],
        lifecycle_status=row["lifecycle_status"],
        catalog_metadata=dict(meta or {}),
        aliases=aliases,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.post(
    "/events",
    response_model=CatalogEventOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create catalog event + optional aliases",
)
async def admin_create_catalog_event(
    request: Request,
    body: CatalogEventCreate,
    api_key: TelemetryApiKey,
) -> CatalogEventOut:
    if not is_valid_canonical_event_name(body.canonical_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="canonical_name must be PascalCase (e.g. ButtonClicked).",
        )
    pool = db_pool()
    if pool is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DATABASE_URL not configured.",
        )
    display = body.display_name or body.canonical_name
    async with pool.acquire() as conn:
        try:
            row = await conn.fetchrow(
                """
                INSERT INTO catalog_events (
                    canonical_name, display_name, description, lifecycle_status, catalog_metadata
                )
                VALUES ($1, $2, $3, $4, $5::jsonb)
                RETURNING *
                """,
                body.canonical_name,
                display,
                body.description,
                body.lifecycle_status,
                json.dumps(body.catalog_metadata or {}),
            )
        except Exception as e:
            if "unique" in str(e).lower() or "duplicate" in str(e).lower():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"canonical_name already exists: {body.canonical_name}",
                ) from e
            raise
        for alias in body.aliases:
            a = (alias or "").strip()
            if not a or a == body.canonical_name:
                continue
            try:
                await conn.execute(
                    """
                    INSERT INTO catalog_event_aliases (event_id, alias)
                    VALUES ($1, $2)
                    """,
                    row["id"],
                    a,
                )
            except Exception as e:
                if "unique" in str(e).lower():
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"alias already registered: {a}",
                    ) from e
                raise
        out = await _row_to_event_out(conn, row)
    await log_admin_request(
        pool,
        method="POST",
        path=str(request.url.path),
        actor_label=api_key[:12] + "…",
        request_summary={"canonical_name": body.canonical_name, "aliases": body.aliases},
    )
    return out


@router.get("/events", response_model=CatalogEventListResponse, summary="List catalog events")
async def admin_list_catalog_events(
    _auth: TelemetryApiKey,
    lifecycle: str | None = Query(None, description="active|deprecated|retired"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> CatalogEventListResponse:
    pool = db_pool()
    if pool is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "DATABASE_URL not configured.")
    async with pool.acquire() as conn:
        if lifecycle:
            total = await conn.fetchval(
                "SELECT count(*) FROM catalog_events WHERE lifecycle_status = $1",
                lifecycle,
            )
            rows = await conn.fetch(
                """
                SELECT * FROM catalog_events
                WHERE lifecycle_status = $1
                ORDER BY canonical_name
                LIMIT $2 OFFSET $3
                """,
                lifecycle,
                limit,
                offset,
            )
        else:
            total = await conn.fetchval("SELECT count(*) FROM catalog_events")
            rows = await conn.fetch(
                """
                SELECT * FROM catalog_events
                ORDER BY canonical_name
                LIMIT $1 OFFSET $2
                """,
                limit,
                offset,
            )
        events = [await _row_to_event_out(conn, r) for r in rows]
    return CatalogEventListResponse(events=events, total=int(total or 0))


@router.get("/events/{canonical_name:path}", response_model=CatalogEventOut, summary="Get one event")
async def admin_get_catalog_event(
    _auth: TelemetryApiKey,
    canonical_name: str,
) -> CatalogEventOut:
    pool = db_pool()
    if pool is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "DATABASE_URL not configured.")
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM catalog_events WHERE canonical_name = $1",
            canonical_name,
        )
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown canonical_name")
        return await _row_to_event_out(conn, row)


@router.post("/resolve", summary="Resolve event name + config (debug)")
async def admin_resolve_catalog(
    _auth: TelemetryApiKey,
    body: CatalogResolveRequest,
) -> dict:
    pool = db_pool()
    if pool is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "DATABASE_URL not configured.")
    async with pool.acquire() as conn:
        return await resolve_catalog_for_admin(
            conn,
            raw_event_name=body.event_name,
            system_id=body.system_id,
            tenant=body.tenant or "",
        )
