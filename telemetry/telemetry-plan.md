# Telemetry Plan (Robusto)

Plan de evolucion para convertir `telemetry` en la capa central de gobierno de eventos,
atributos y compras, con control de catalogo, observabilidad y despacho confiable.

## Vision

Centralizar la telemetria de todos los sistemas en un solo contrato:

- Los sistemas emisores publican al API de telemetria.
- El catalogo decide que se acepta, que se bloquea y que se envia a Braze.
- Los eventos no habilitados quedan auditados con razon de descarte.
- El envio a Braze es confiable, idempotente y observable.

## Principios

1. **Catalogo como fuente de verdad**: sin registro en catalogo, no hay envio.
2. **Contrato unico**: payload universal para frontend, backend, cron y workers.
3. **Idempotencia fuerte**: `meta.message_id` obligatorio y persistente.
4. **Separacion de responsabilidades**: ingesta, validacion, encolado, despacho.
5. **Trazabilidad total**: cada mensaje tiene estado final verificable.

## Estado actual (resumen)

- FastAPI con endpoints:
  - `POST /api/v1/telemetry/ingest`
  - `POST /api/v1/telemetry/ingest/batch`
  - `GET /api/v1/telemetry/catalog` (stub)
- Reenvio directo a Braze `users/track` cuando hay `BRAZE_API_KEY`.
- Idempotencia en memoria (util para dev, insuficiente para prod).
- Sin autenticacion, sin outbox persistente y sin worker dedicado.

## Brechas criticas

1. Idempotencia no persistente.
2. Catalogo no gobernado (stub).
3. Reenvio sin cola/outbox (riesgo de perdida ante fallos).
4. Sin politicas de seguridad por cliente emisor.
5. Logs y metricas aun sin estandar operativo.

## Arquitectura objetivo

### Capa 1: Ingesta

- Validar esquema universal.
- Rechazar mensajes sin `message_id`, `event.name`, `source_system`.
- Resolver estado de catalogo: `enabled`, `disabled`, `unknown`.
- Guardar registro de entrada (audit trail) siempre.

### Capa 2: Gobierno de catalogo

Catalogo por evento con metadatos:

- `module`, `namespace`, `event_name`
- `enabled`
- `allowed_sources`
- `schema_version`
- `routing`: `{ braze: on/off, warehouse: on/off }`
- `pii_policy`

### Capa 3: Outbox y worker

- Persistir en `telemetry_outbox`.
- Worker asincrono con reintentos y backoff exponencial.
- Dedupe por `message_id` y por destino.
- Dead-letter queue para errores permanentes.

### Capa 4: Destinos

- Braze (`users/track`) como primer destino.
- Extensible a warehouse / lake / alerting sin cambiar emisores.

### Capa 5: Observabilidad

- Logs estructurados JSON.
- Metricas: aceptados, bloqueados, enviados, errores, latencia p95.
- Trazas por `trace_id` y `message_id`.
- Dashboard operativo y alertas.

## Estados de procesamiento recomendados

- `accepted_forwarded`
- `accepted_queued`
- `accepted_not_enabled`
- `rejected_unknown_event`
- `rejected_invalid_payload`
- `delivery_failed_retrying`
- `delivery_failed_dead_letter`

## Modelo de datos minimo

### `telemetry_events`

- `id`
- `message_id` (unique)
- `source_system`
- `event_name`
- `catalog_status` (`enabled|disabled|unknown`)
- `payload_json`
- `received_at`

### `telemetry_outbox`

- `id`
- `message_id`
- `destination` (`braze`)
- `status` (`pending|sent|failed|dead`)
- `attempts`
- `next_retry_at`
- `last_error`
- `updated_at`

### `telemetry_rejections` (opcional pero recomendado)

- `message_id`
- `event_name`
- `reason`
- `source_system`
- `received_at`

## Plan por fases

### Fase 1 (1-2 semanas): Control y catalogo

- Implementar catalogo real (JSON inicial + endpoint admin simple).
- Validar `event.name` contra catalogo.
- Registrar descartes por `disabled/unknown`.
- Estandarizar respuestas por estado.

### Fase 2 (2-3 semanas): Persistencia e idempotencia

- Agregar PostgreSQL.
- Crear tablas `telemetry_events` y `telemetry_outbox`.
- Mover idempotencia de memoria a DB.
- Garantizar `message_id` unico por ventana definida.

### Fase 3 (2-3 semanas): Worker y entrega robusta

- Implementar worker para Braze.
- Reintentos + dead-letter.
- Trazabilidad por destino.
- Pruebas de resiliencia (timeouts, 429, 5xx).

### Fase 4 (1-2 semanas): Seguridad y operacion

- API keys por emisor.
- Rate limits por cliente.
- Restriccion CORS por entorno.
- Dashboards y alertas operativas.

## Reglas de gobernanza

1. Ningun evento nuevo entra a prod sin alta en catalogo.
2. Todo cambio de schema requiere version.
3. PII solo en `user`, no en `event.properties`.
4. Todo descarte debe quedar auditable.
5. Toda incidencia debe poder rastrearse por `message_id`.

## Criterios de exito

- 0 perdida silenciosa de eventos.
- 100% de eventos con estado final trazable.
- <1% de reintentos fallidos despues de 3 intentos (meta inicial).
- Tiempo medio de recuperacion ante fallo de destino < 30 min.
- Proceso de alta de evento documentado y repetible.
