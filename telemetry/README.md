# Telemetry Service

Proyecto base de telemetria con stack Python moderno:

- FastAPI
- SQLAlchemy
- asyncpg
- Pydantic / pydantic-settings

## Run local

Desde `telemetry/`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8090
```

## Endpoints

- `GET /health` — liveness
- `GET /` — hello world
- `POST /api/v1/telemetry/ingest` — payload universal (1 evento)
- `POST /api/v1/telemetry/ingest/batch` — hasta 100 eventos
- `GET /api/v1/telemetry/catalog` — catálogo stub

Swagger: **`http://127.0.0.1:8090/docs`**

Detalle de uso: **`docs/API.md`**

### Postgres + catálogo (opcional, prueba con playground)

Si definís `DATABASE_URL`, el ingest **exige** que el evento exista en `catalog_events` (o alias) y que `system_catalog_configs` permita Braze para `(meta.source_system, meta.tenant, evento)`.

1. Esquema:

```bash
psql "$DATABASE_URL" -f sql/001_catalog_and_config.sql
```

2. Regenerar SQL de seed desde el JSON normalizado (y escribir `sql/seed/*.sql`):

```bash
python scripts/generate_postgres_seed_sql.py \
  --json .plan/playground-events-catalog.normalized.json \
  --out-dir sql/seed \
  --system-id braze-sdk-playground \
  --tenant kwt
```

3. Cargar datos:

```bash
psql "$DATABASE_URL" -f sql/seed/010_catalog_inserts.sql
psql "$DATABASE_URL" -f sql/seed/020_system_config_inserts.sql
```

Por defecto el seed de config deja **Braze `enabled: true`** y **GA4 `enabled: false`** (`mapper_version` braze_track_v1 / ga4_mp_v1).

En `.env` también podés usar `DATABASE_URL=postgresql://...`. Para desactivar la verificación contra DB manteniendo la URL (debug): `TELEMETRY_IGNORE_CATALOG=1`.

### Braze (opcional)

Con `telemetry/.env` (gitignored) ya cargado al arrancar la app: `BRAZE_API_KEY` y `BRAZE_API_ENDPOINT` como en los microservicios Go. Si no hay `.env`, exportá en la shell:

```bash
export BRAZE_API_KEY="tu-rest-api-key"
export BRAZE_API_ENDPOINT="https://rest.iad-02.braze.com"
```

Playground HTML: **`.plan/braze-sdk-playground.html`** — columna SDK (front) + columna telemetry (Magento/Go). Regenerar nombres de eventos del playground:

```bash
python scripts/gen_playground_events_catalog.py
python scripts/generate_postgres_seed_sql.py --out-dir sql/seed
```

## Plan y documentación en repo

- `telemetry-plan.md` — plan del proyecto
- `../.plan/api-plan.html` — contrato payload + Braze
- `../.plan/payload-usage.html` — guía de campos e idempotencia
- `../.plan/frontend-usage.html` / `backend-usage.html` — por rol
