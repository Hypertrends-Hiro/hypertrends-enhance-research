# Telemetry Service

Python telemetry API: accepts a **universal JSON envelope**, optional **Postgres-backed catalog and routing**, optional **Braze** forwarding, and an **admin API** for catalog and system config.

**Stack:** FastAPI, asyncpg, SQLAlchemy, Pydantic / pydantic-settings, httpx.

---

## How it works

### Purpose

Clients send events to **`POST /api/v1/telemetry/ingest`** (or batch). The service:

1. **Dedupes** by `meta.message_id` in process memory (not durable across restarts or replicas).
2. Optionally **checks Postgres** so Braze is only called when the event and routing config allow it.
3. Optionally **calls Braze** `/users/track` when credentials are set.
4. Returns **`accepted`** (or **`accepted_not_forwarded`** / **`duplicate_ignored`**) with a human **`note`** and a **`forwarding`** map per destination (e.g. `braze`: `ok` | `skipped` | `error` | `skipped_no_credentials`).

**All API routes require an API key:** set **`TELEMETRY_API_KEYS`** (comma-separated). Send **`X-Telemetry-Api-Key`**, legacy **`X-Telemetry-Admin-Key`**, or **`Authorization: Bearer <key>`**. If the variable is empty, every protected route returns **503**. If keys are set but the request has no/invalid key, **401**. **`/docs`** and **`/openapi.json`** stay open for browsing the spec (lock them at the edge in production if needed).

### Ingest flow (step by step)

1. **Idempotency** — If `message_id` was already seen in this process, respond with `duplicate_ignored` and skip forwarding (no Braze call).
2. **Database** — If `DATABASE_URL` is set and the app connects, an asyncpg pool is used. Otherwise the service runs without catalog DB checks.
3. **Catalog gate for Braze** (only when the pool exists **and** `TELEMETRY_IGNORE_CATALOG` is not truthy):
   - Resolve `event.name` to `catalog_events.id` via canonical name or **`catalog_event_aliases`**.
   - If unknown → **do not** call Braze; note includes `unknown event in catalog`.
   - If known, load **`system_catalog_configs`** for `(meta.source_system, meta.tenant or "", event_id)`. There must be a row with `enabled = true` and `destinations.braze.enabled = true`. Otherwise Braze is skipped and the note explains why.
4. **If Braze is allowed** (or catalog checks are skipped): if `BRAZE_API_KEY` and endpoint are configured, forward to Braze; otherwise note that forwarding is off.
5. **Optional audit** — If `telemetry_ingest_audit` exists and ingest audit is enabled, a row may be written (see SQL `002`).

### Catalog (read) vs admin (write)

- **`GET /api/v1/telemetry/catalog`** — Same API key as ingest. Lists **active** `catalog_events` when Postgres is available; otherwise a small **stub**.
- **`/api/v1/catalog/...`** and **`/api/v1/system-catalog-configs/...`** — Same API key. Without Postgres, admin handlers return **503**. New canonical names must be **PascalCase** (e.g. `ButtonClicked`). Mutations may be logged to **`telemetry_admin_audit`** (SQL `003`).

### Postgres objects (summary)

| Object | Role |
|--------|------|
| `catalog_events` | Canonical event name, lifecycle, metadata. |
| `catalog_event_aliases` | Alternate names clients may send in `event.name`. |
| `system_catalog_configs` | Per `system_id`, `tenant`, `event_id`: enabled flag and `destinations` (Braze, GA4, etc.). |
| `telemetry_ingest_audit` | Optional ingest decision log. |
| `telemetry_admin_audit` | Optional admin mutation log. |

### Environment variables

| Variable | Effect |
|----------|--------|
| `DATABASE_URL` | Enables asyncpg pool, catalog enforcement on ingest, real public catalog, admin API. |
| `TELEMETRY_IGNORE_CATALOG` | With DB set, skips catalog checks for the Braze decision (debug). |
| `TELEMETRY_API_KEYS` | Comma-separated API keys; empty disables the HTTP API (503 on `/health` and `/api/v1/*`). |
| `TELEMETRY_AUDIT_INGEST` | `0` / `false` disables writes to `telemetry_ingest_audit` (default on if table exists). |
| `BRAZE_API_KEY`, `BRAZE_REST_ENDPOINT` / `BRAZE_API_ENDPOINT` | Braze REST forward; without key, no outbound call. |

On startup, the app loads **`telemetry/.env`** if present (gitignored) for local secrets.

More request/response detail: **`docs/API.md`**. Payload contract: **`../.plan/api-plan.html`**, **`../.plan/payload-usage.html`**.

---

## How to run

**Requirements:** Python **≥ 3.12** (see `pyproject.toml`).

From the **`telemetry/`** directory:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -U pip
pip install -e ".[dev]"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8090
```

Without activating the venv (same directory):

```bash
.venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8090
```

- **OpenAPI / Swagger:** http://127.0.0.1:8090/docs (no key required to view; calls from “Try it” need your key in the request)  
- **Health:** http://127.0.0.1:8090/health — **requires** `X-Telemetry-Api-Key` (or Bearer)

Add to `telemetry/.env`, for example:

```env
TELEMETRY_API_KEYS=your-secret-key-here
```

---

## API overview

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness |
| POST | `/api/v1/telemetry/ingest` | Single universal payload |
| POST | `/api/v1/telemetry/ingest/batch` | Up to 100 payloads |
| GET | `/api/v1/telemetry/catalog` | Active catalog from Postgres, or stub |
| POST/GET | `/api/v1/catalog/events` | Admin: create / list catalog events |
| GET | `/api/v1/catalog/events/{canonical_name}` | Admin: get one event |
| POST | `/api/v1/catalog/resolve` | Admin: resolve name + config (debug) |
| POST/GET | `/api/v1/system-catalog-configs` | Admin: create / list routing configs |
| PATCH | `/api/v1/system-catalog-configs/{config_id}` | Admin: patch config |

---

## Postgres setup (optional)

Apply schema (order matters):

```bash
psql "$DATABASE_URL" -f sql/001_catalog_and_config.sql
psql "$DATABASE_URL" -f sql/002_telemetry_ingest_audit.sql
psql "$DATABASE_URL" -f sql/003_telemetry_admin_audit.sql
```

Regenerate seed SQL from normalized JSON:

```bash
python scripts/generate_postgres_seed_sql.py \
  --json .plan/playground-events-catalog.normalized.json \
  --out-dir sql/seed \
  --system-id braze-sdk-playground \
  --tenant kwt
```

Load seed data:

```bash
psql "$DATABASE_URL" -f sql/seed/010_catalog_inserts.sql
psql "$DATABASE_URL" -f sql/seed/020_system_config_inserts.sql
```

Default seed config typically has **Braze enabled** and **GA4 disabled** in `destinations`.

---

## Braze (optional)

Set REST API key and endpoint (same idea as other services in this org):

```bash
export BRAZE_API_KEY="your-rest-api-key"
export BRAZE_API_ENDPOINT="https://rest.iad-02.braze.com"
```

Or put them in `telemetry/.env`.

---

## Tests

```bash
pip install -e ".[dev]"
pytest -q
```

---

## Playground and repo docs

- **`.plan/braze-sdk-playground.html`** — SDK + telemetry column demo  
- Regenerate playground catalog names:

```bash
python scripts/gen_playground_events_catalog.py
python scripts/generate_postgres_seed_sql.py --out-dir sql/seed
```

- **`telemetry-plan.md`** — project plan  
- **`../.plan/api-plan.html`**, **`../.plan/frontend-usage.html`**, **`../.plan/backend-usage.html`**
