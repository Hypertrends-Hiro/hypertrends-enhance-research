"""Public catalog list — from Postgres when DATABASE_URL is set, else stub."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.db import db_pool
from app.deps import require_telemetry_api_key
from app.schemas.ingest import CatalogEventEntry, CatalogResponse

router = APIRouter(
    prefix="/telemetry",
    tags=["telemetry"],
    dependencies=[Depends(require_telemetry_api_key)],
)


@router.get(
    "/catalog",
    response_model=CatalogResponse,
    summary="List catalog event names (from DB or stub)",
)
async def get_catalog() -> CatalogResponse:
    pool = db_pool()
    if pool is None:
        return CatalogResponse(
            events=[
                CatalogEventEntry(name="page_viewed", description="SPA route change"),
                CatalogEventEntry(name="health_ping", description="Connectivity check"),
            ],
            note="Stub: set DATABASE_URL and run sql seeds for full catalog.",
        )
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT canonical_name, description
            FROM catalog_events
            WHERE lifecycle_status = 'active'
            ORDER BY canonical_name
            """
        )
    return CatalogResponse(
        events=[
            CatalogEventEntry(
                name=r["canonical_name"],
                description=(r["description"] or "")[:500] or None,
            )
            for r in rows
        ],
        note=f"from Postgres catalog_events ({len(rows)} active).",
    )
