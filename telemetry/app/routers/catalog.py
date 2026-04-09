"""Event catalog stub — will be backed by event_catalog.json later."""

from fastapi import APIRouter

from app.schemas.ingest import CatalogEventEntry, CatalogResponse

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


@router.get(
    "/catalog",
    response_model=CatalogResponse,
    summary="List allowed telemetry event names (stub)",
)
async def get_catalog() -> CatalogResponse:
    # Minimal seed so clients can smoke-test; replace with file/DB.
    return CatalogResponse(
        events=[
            CatalogEventEntry(name="page_viewed", description="SPA route change"),
            CatalogEventEntry(name="health_ping", description="Connectivity check"),
        ],
        note="Stub catalog. Extend with workspace event_catalog.json.",
    )
