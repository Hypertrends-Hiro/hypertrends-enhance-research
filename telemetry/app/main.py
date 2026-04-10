from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.deps import require_telemetry_api_key

# Carga telemetry/.env al importar (BRAZE_* para reenvío a Braze).
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from app.routers import admin_catalog, admin_config, catalog, ingest


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.db import close_db_pool, init_db_pool

    await init_db_pool()
    yield
    await close_db_pool()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Telemetry API",
        version="0.5.0",
        description="""
**API key required** — set `TELEMETRY_API_KEYS` and send `X-Telemetry-Api-Key` or `Authorization: Bearer`.

Universal ingest payload: `telemetry/.plan/`.

- Guía payload: `telemetry/.plan/payload-usage.html`
- Frontend: `telemetry/.plan/frontend-usage.html`
- Backend: `telemetry/.plan/backend-usage.html`
        """.strip(),
        docs_url="/docs",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # CORS: playground HTML / otros orígenes en dev (ajustar con env en producción)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(ingest.router, prefix="/api/v1")
    app.include_router(catalog.router, prefix="/api/v1")
    app.include_router(admin_catalog.router, prefix="/api/v1")
    app.include_router(admin_config.router, prefix="/api/v1")

    @app.get("/health", dependencies=[Depends(require_telemetry_api_key)])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
