# Telemetry API (ingesta abierta + reenvío Braze)

Base URL local: `http://127.0.0.1:8090`

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/health` | Liveness |
| POST | `/api/v1/telemetry/ingest` | Un mensaje con payload universal |
| POST | `/api/v1/telemetry/ingest/batch` | Hasta 100 mensajes |
| GET | `/api/v1/telemetry/catalog` | Lista eventos activos desde Postgres, o stub sin `DATABASE_URL` |
| POST | `/api/v1/catalog/events` | **Admin** — crear evento canónico (+ alias opcional) |
| GET | `/api/v1/catalog/events` | **Admin** — listar (filtro `lifecycle`, paginación) |
| GET | `/api/v1/catalog/events/{canonical_name}` | **Admin** — detalle |
| POST | `/api/v1/catalog/resolve` | **Admin** — resolver nombre + config (debug) |
| POST | `/api/v1/system-catalog-configs` | **Admin** — crear routing por sistema/tenant/evento |
| GET | `/api/v1/system-catalog-configs` | **Admin** — listar (filtros opcionales) |
| PATCH | `/api/v1/system-catalog-configs/{config_id}` | **Admin** — actualizar `enabled` / `destinations` |

Documentación interactiva: **`/docs`** (Swagger) y **`/openapi.json`**.

## Catálogo en Postgres (opcional)

Si la app arranca con **`DATABASE_URL`**, antes de llamar a Braze valida:

1. `event.name` resuelve a un `catalog_events` (nombre canónico o fila en `catalog_event_aliases`).
2. Existe `system_catalog_configs` para `(meta.source_system, coalesce(meta.tenant, ''), event_id)` con `enabled = true` y `destinations.braze.enabled = true`.

Si falla, la respuesta sigue siendo `accepted` pero la nota indica que Braze **no** se llamó (ej. `unknown event in catalog` o `no system_catalog_config…`).

Sin `DATABASE_URL`, el comportamiento sigue siendo el anterior (solo Braze + idempotencia en memoria). Con URL pero queriendo saltar la DB: `TELEMETRY_IGNORE_CATALOG=1`.

Ver `README.md` — sección Postgres + scripts `sql/001_catalog_and_config.sql`, `sql/002_telemetry_ingest_audit.sql`, `sql/003_telemetry_admin_audit.sql` y `sql/seed/*.sql`.

### Autenticación (toda la API HTTP)

- Variable **`TELEMETRY_API_KEYS`**: lista separada por comas. Sin claves: **503** en `/health` y todo `/api/v1/*`.
- Cabecera **`X-Telemetry-Api-Key: <clave>`** (recomendada), o legado **`X-Telemetry-Admin-Key`**, o **`Authorization: Bearer <clave>`**.
- Con claves configuradas pero sin cabecera o clave incorrecta: **401**.

Los endpoints bajo **`/api/v1/catalog/...`** y **`/system-catalog-configs/...`** además requieren **`DATABASE_URL`** con esquema; si no, **503**. Los `canonical_name` nuevos deben ser **PascalCase** (ej. `ButtonClicked`).

### Auditoría (Postgres)

Tras aplicar `002` / `003`, la app puede registrar filas en `telemetry_ingest_audit` y `telemetry_admin_audit`. Variable **`TELEMETRY_AUDIT_INGEST=0`** desactiva la escritura de auditoría de ingest (si está definida y distinta de `1`/`true`).

## Payload universal

Misma forma que `telemetry/.plan/api-plan.html` y `payload-usage.html`.

Campos mínimos típicos:

- `meta.message_id` — idempotencia (recomendado UUIDv7).
- `meta.occurred_at` — ISO-8601, hora de negocio en origen.
- `meta.source_system` — nombre del sistema emisor.
- `event.name` — nombre del evento.
- `event.time` — ISO-8601 (suele igualar `occurred_at`).
- `user.external_id` o `user.anonymous_id` (recomendado al menos uno).
- `purchase` — si no aplica, omitir o `{ "enabled": false }`.

## Ejemplo `curl` — ingest simple

```bash
curl -sS -X POST "http://127.0.0.1:8090/api/v1/telemetry/ingest" \
  -H "Content-Type: application/json" \
  -H "X-Telemetry-Api-Key: TU_CLAVE_TELEMETRY_API_KEYS" \
  -d '{
    "meta": {
      "message_id": "018f7aa0-4f2f-7e4a-a0dc-1e6d2d69b001",
      "occurred_at": "2026-03-23T15:10:00Z",
      "source_system": "kwilthealth.com",
      "source_channel": "frontend",
      "tenant": "kwt",
      "schema_version": "1.0.0"
    },
    "user": { "anonymous_id": "anon_demo" },
    "session": {
      "session_id": "sess_demo",
      "page_url": "https://app.example.com/cart",
      "route": "/cart"
    },
    "event": {
      "name": "page_viewed",
      "time": "2026-03-23T15:10:00Z",
      "properties": { "previous_route": "/products" }
    },
    "purchase": { "enabled": false }
  }'
```

Respuesta esperada (primera vez):

```json
{
  "status": "accepted",
  "message_id": "018f7aa0-4f2f-7e4a-a0dc-1e6d2d69b001",
  "duplicate": false,
  "received_at": "...",
  "note": "Accepted. braze ok HTTP 201"
}
```

Si `BRAZE_API_KEY` no está definida, la nota indica que el reenvío a Braze está desactivado. Si Braze responde error, la nota incluye el detalle (`braze error HTTP …`) y el mensaje sigue `accepted` (ingesta local OK).

Reenviar el mismo `message_id`: `status: "duplicate_ignored"`, `duplicate: true` (no se llama de nuevo a Braze).

## Reenvío a Braze (`/users/track`)

Variables de entorno:

| Variable | Descripción |
|----------|-------------|
| `BRAZE_API_KEY` | Clave **REST** del dashboard Braze (no la Web SDK key). Si falta, no hay llamada a Braze. |
| `BRAZE_REST_ENDPOINT` o `BRAZE_API_ENDPOINT` | Opcional; mismo patrón que Go (`BRAZE_API_ENDPOINT`). Por defecto `https://rest.iad-02.braze.com`. |

Mapeo resumido: `event` → `events[]`; `user` + `user.attributes` → `attributes[]` si hay campos de perfil; `purchase.enabled` → `purchases[]`. Requiere `user.external_id` o `user.anonymous_id` para poder enviar.

## Idempotencia (Fase 1)

En memoria del proceso (máx. ~50k IDs). **No persiste** entre reinicios ni entre réplicas.

En producción: sustituir por Redis/Postgres + outbox.

## Seguridad

- **Ingest, catálogo, health y admin** usan la misma **`TELEMETRY_API_KEYS`** (cabecera o Bearer).
- **`/docs`** y **`/openapi.json`** no exigen clave para leer el spec; en producción restringir en el proxy si hace falta.
- Pendiente en evolución: rate limiting, mTLS, WAF, etc.
