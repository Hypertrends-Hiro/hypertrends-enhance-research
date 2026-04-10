"""Admin system_catalog_configs API."""

from __future__ import annotations

import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.admin_audit import log_admin_request
from app.catalog_policy import resolve_event_id
from app.db import db_pool
from app.deps import require_telemetry_api_key
from app.schemas.admin import (
    DEFAULT_DESTINATIONS,
    SystemCatalogConfigCreate,
    SystemCatalogConfigListResponse,
    SystemCatalogConfigOut,
    SystemCatalogConfigPatch,
)

router = APIRouter(prefix="/system-catalog-configs", tags=["admin-system-catalog-config"])
TelemetryApiKey = Annotated[str, Depends(require_telemetry_api_key)]


def _destinations_json(row_dest) -> dict:
    d = row_dest
    if isinstance(d, str):
        d = json.loads(d)
    return dict(d or {})


async def _config_row_to_out(conn, row) -> SystemCatalogConfigOut:
    cn = await conn.fetchval(
        "SELECT canonical_name FROM catalog_events WHERE id = $1",
        row["event_id"],
    )
    return SystemCatalogConfigOut(
        id=row["id"],
        system_id=row["system_id"],
        tenant=row["tenant"],
        event_id=row["event_id"],
        canonical_name=cn or "?",
        enabled=row["enabled"],
        destinations=_destinations_json(row["destinations"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.post(
    "",
    response_model=SystemCatalogConfigOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create routing config for system+tenant+event",
)
async def admin_create_config(
    request: Request,
    body: SystemCatalogConfigCreate,
    api_key: TelemetryApiKey,
) -> SystemCatalogConfigOut:
    pool = db_pool()
    if pool is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "DATABASE_URL not configured.")
    dest = body.destinations if body.destinations is not None else dict(DEFAULT_DESTINATIONS)
    async with pool.acquire() as conn:
        eid = await resolve_event_id(conn, body.canonical_event_name.strip())
        if eid is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown canonical_event_name: {body.canonical_event_name!r}",
            )
        try:
            row = await conn.fetchrow(
                """
                INSERT INTO system_catalog_configs (system_id, tenant, event_id, enabled, destinations)
                VALUES ($1, $2, $3, $4, $5::jsonb)
                RETURNING *
                """,
                body.system_id.strip(),
                (body.tenant or "").strip(),
                eid,
                body.enabled,
                json.dumps(dest),
            )
        except Exception as e:
            if "unique" in str(e).lower() or "duplicate" in str(e).lower():
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    detail="Config already exists for this system_id, tenant, event.",
                ) from e
            raise
        out = await _config_row_to_out(conn, row)
    await log_admin_request(
        pool,
        method="POST",
        path=str(request.url.path),
        actor_label=api_key[:12] + "…",
        request_summary={
            "system_id": body.system_id,
            "tenant": body.tenant,
            "canonical_event_name": body.canonical_event_name,
        },
    )
    return out


@router.get("", response_model=SystemCatalogConfigListResponse, summary="List configs (filters optional)")
async def admin_list_configs(
    _auth: TelemetryApiKey,
    system_id: str | None = Query(None),
    tenant: str | None = Query(None),
    canonical_name: str | None = Query(None),
) -> SystemCatalogConfigListResponse:
    pool = db_pool()
    if pool is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "DATABASE_URL not configured.")
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT s.*, ce.canonical_name AS ce_canonical
            FROM system_catalog_configs s
            JOIN catalog_events ce ON ce.id = s.event_id
            WHERE ($1::text IS NULL OR s.system_id = $1)
              AND ($2::text IS NULL OR s.tenant = $2)
              AND ($3::text IS NULL OR ce.canonical_name = $3)
            ORDER BY s.system_id, s.tenant, ce.canonical_name
            """,
            system_id,
            tenant,
            canonical_name,
        )
        configs: list[SystemCatalogConfigOut] = []
        for r in rows:
            configs.append(
                SystemCatalogConfigOut(
                    id=r["id"],
                    system_id=r["system_id"],
                    tenant=r["tenant"],
                    event_id=r["event_id"],
                    canonical_name=r["ce_canonical"],
                    enabled=r["enabled"],
                    destinations=_destinations_json(r["destinations"]),
                    created_at=r["created_at"],
                    updated_at=r["updated_at"],
                )
            )
    return SystemCatalogConfigListResponse(configs=configs)


@router.patch("/{config_id}", response_model=SystemCatalogConfigOut, summary="Update config")
async def admin_patch_config(
    request: Request,
    config_id: UUID,
    body: SystemCatalogConfigPatch,
    api_key: TelemetryApiKey,
) -> SystemCatalogConfigOut:
    pool = db_pool()
    if pool is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "DATABASE_URL not configured.")
    if body.enabled is None and body.destinations is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Provide enabled and/or destinations")
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM system_catalog_configs WHERE id = $1",
            config_id,
        )
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown config_id")
        enabled = row["enabled"] if body.enabled is None else body.enabled
        dest = _destinations_json(row["destinations"])
        if body.destinations is not None:
            dest = body.destinations
        await conn.execute(
            """
            UPDATE system_catalog_configs
            SET enabled = $2, destinations = $3::jsonb, updated_at = now()
            WHERE id = $1
            """,
            config_id,
            enabled,
            json.dumps(dest),
        )
        row2 = await conn.fetchrow(
            "SELECT * FROM system_catalog_configs WHERE id = $1",
            config_id,
        )
        out = await _config_row_to_out(conn, row2)
    await log_admin_request(
        pool,
        method="PATCH",
        path=str(request.url.path),
        actor_label=api_key[:12] + "…",
        request_summary={"config_id": str(config_id), "patch": body.model_dump(exclude_none=True)},
    )
    return out
