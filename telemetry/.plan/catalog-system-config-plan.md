# Telemetry Robust Plan: Catalog + System Catalog Config

Plan maestro para evolucionar `telemetry` a una plataforma robusta con gobierno de eventos, control operativo por sistema y enrutamiento multidestino (Braze, GA4, futuros destinos).

## 1) Objetivo

Diseñar e implementar dos módulos separados:

1. `Catalog` (diccionario global de eventos): solo registra nombres canónicos y metadatos de definición.
2. `SystemCatalogConfig` (configuración operativa por sistema): define si un evento se procesa, a qué destinos se envía y con qué transformación.

Esta separación evita mezclar semántica del evento con reglas de operación por aplicación/tenant.

## 2) Principios de diseño

1. **Separación de responsabilidades**
   - `Catalog`: qué evento existe.
   - `SystemCatalogConfig`: cómo se comporta ese evento en cada sistema.
2. **Nombre canónico único**
   - Convención oficial: `PascalCase`.
   - Ejemplo: `AddPaymentInfo`, `IntakeIncomplete`, `OrderPlaced`.
3. **Ingest gobernado por datos**
   - La API de ingest no decide por hardcode.
   - Toda decisión se toma contra `Catalog` + `SystemCatalogConfig`.
4. **Trazabilidad total**
   - Toda solicitud de ingest queda auditada con decisión final.
5. **Compatibilidad evolutiva**
   - Se aceptan aliases legacy durante migración (snake/camel/variantes), pero el canónico oficial es PascalCase.

## 3) Alcance funcional

### Incluye

- API de gestión de `Catalog`.
- API de gestión de `SystemCatalogConfig`.
- Integración de validación en `POST /api/v1/telemetry/ingest` y `/ingest/batch`.
- Motor de resolución de nombres (canónico + aliases).
- Enrutamiento por destino (Braze/GA4) según configuración.
- Auditoría y observabilidad de decisiones.
- Backoffice para activar/desactivar eventos por sistema.

### No incluye (fase futura)

- UI avanzada de analytics.
- Motor de aprobación de cambios con workflow complejo.
- Multi-región y active-active.

## 4) Modelo conceptual

### 4.1 Catalog (global)

Registra el evento como entidad de negocio, sin reglas por sistema.

- `event_key` (UUID)
- `canonical_name` (string, único, PascalCase)
- `display_name` (string)
- `description` (string)
- `domain` (string, opcional)
- `lifecycle_status` (`active | deprecated | retired`)
- `aliases` (array de strings; opcional para transición)
- `created_at`, `updated_at`
- `created_by`, `updated_by`

### 4.2 SystemCatalogConfig (por sistema)

Configura el comportamiento operativo de cada evento por emisor o aplicación.

- `config_id` (UUID)
- `system_id` (string; ej. `kwilthealth-web`, `magento-kwt`, `intake-builder`)
- `tenant` (string opcional)
- `event_key` (FK -> Catalog)
- `enabled` (bool)
- `mode` (`allow | deny | shadow`)
- `destinations` (objeto):
  - `braze.enabled` (bool)
  - `ga4.enabled` (bool)
  - `warehouse.enabled` (bool, futuro)
- `mappers` (objeto):
  - `braze.mapper_version`
  - `ga4.mapper_version`
- `validation_policy`:
  - `strict_payload` (bool)
  - `reject_on_unknown_fields` (bool)
- `rate_limit_profile` (string opcional)
- `effective_from`, `effective_to` (opcionales)
- `created_at`, `updated_at`
- `created_by`, `updated_by`

### 4.3 Ingest audit trail

Persistencia de cada ingest para diagnóstico y cumplimiento:

- `message_id`
- `original_event_name`
- `canonical_event_name` (resuelto)
- `system_id`, `tenant`, `source_channel`
- `decision` (`forwarded | accepted_not_forwarded | rejected`)
- `decision_reason`
- `destinations_attempted` (json)
- `destinations_result` (json)
- `received_at`, `processed_at`

## 5) Contratos API propuestos

## 5.1 Catalog API

- `GET /api/v1/catalog/events`
  - Lista eventos canónicos.
- `POST /api/v1/catalog/events`
  - Crea evento canónico (valida PascalCase y unicidad).
- `GET /api/v1/catalog/events/{canonical_name}`
  - Obtiene detalle.
- `PATCH /api/v1/catalog/events/{canonical_name}`
  - Actualiza descripción, lifecycle, aliases.
- `POST /api/v1/catalog/events/{canonical_name}/aliases`
  - Agrega alias controlado.
- `DELETE /api/v1/catalog/events/{canonical_name}/aliases/{alias}`
  - Elimina alias.

## 5.2 SystemCatalogConfig API

- `GET /api/v1/system-catalog-configs`
  - Filtros por `system_id`, `tenant`, `canonical_name`, `enabled`.
- `POST /api/v1/system-catalog-configs`
  - Crea configuración por sistema+evento.
- `GET /api/v1/system-catalog-configs/{config_id}`
  - Detalle de regla operativa.
- `PATCH /api/v1/system-catalog-configs/{config_id}`
  - Cambia enable/disable, destinos, mappers, policy.
- `POST /api/v1/system-catalog-configs/{config_id}/activate`
  - Activación explícita.
- `POST /api/v1/system-catalog-configs/{config_id}/deactivate`
  - Desactivación explícita.

## 5.3 Endpoint de resolución (support)

- `POST /api/v1/catalog/resolve`
  - Entrada: `system_id`, `tenant`, `event_name`.
  - Salida: `canonical_name`, `matched_by`, `is_enabled`, `routing_plan`.
  - Uso: debugging, QA y backoffice.

## 6) Reglas de decisión en ingest

Flujo para `POST /ingest`:

1. Validar envelope base (`meta`, `event`, `message_id`, `source_system`).
2. Resolver `event.name`:
   - exact match canónico,
   - match por alias,
   - no match -> `unknown_event`.
3. Buscar `SystemCatalogConfig` por `(system_id, tenant, event_key)`.
4. Evaluar política:
   - Si config no existe: `rejected` o `accepted_not_forwarded` (feature flag).
   - Si `enabled=false`: `accepted_not_forwarded`.
   - Si `enabled=true`: continuar.
5. Construir plan de destinos (`braze`, `ga4`) según config.
6. Transformar payload por destino:
   - `canonical -> braze_payload`
   - `canonical -> ga4_payload`
7. Enviar (sincrónico en fase inicial; outbox/worker en fase robusta).
8. Registrar `decision` y resultados por destino.
9. Responder al emisor con estado claro y trazable.

## 7) Política de nombres (oficial)

- Todos los eventos nuevos: **PascalCase**.
- No usar prefijos técnicos como `backend_` en canónico.
- El origen técnico viaja en metadata (`source_system`, `source_channel`), no en nombre.
- Alias legacy permitidos solo para transición y con fecha de retiro.

Ejemplos:

- `intake_incomplete` -> canónico `IntakeIncomplete`
- `AddPaymentInfo` -> canónico `AddPaymentInfo` (ya cumple)
- `subscription_canceled` + `subscription_cancelled` -> canónico `SubscriptionCanceled` (definir estándar de spelling)

## 8) Backoffice (MVP)

Pantallas mínimas:

1. **Catalog**
   - Alta/edición de eventos canónicos.
   - Gestión de aliases.
   - Estado de lifecycle.
2. **System Config**
   - Matriz `sistema x evento`.
   - Toggle `enabled`.
   - Toggles por destino (`Braze`, `GA4`).
   - Selección de `mapper_version`.
3. **Operations**
   - Eventos desconocidos detectados.
   - Config faltante por sistema.
   - Top eventos desactivados recibidos.

Seguridad:

- RBAC mínimo:
  - `catalog_admin`
  - `system_config_admin`
  - `viewer`
- Auditoría de cambios (quién, qué, cuándo, antes/después).

## 9) Payload por destino

Correcto y requerido: Braze y GA4 usan payloads finales distintos.

- Entrada única: envelope canónico.
- Salidas:
  - `braze_payload` (Braze `/users/track`)
  - `ga4_payload` (GA4 Measurement Protocol)

No duplicar semántica de negocio: el significado vive en el canónico; los payloads de destino son transformación.

## 10) Roadmap de implementación

## Fase 0 (2-3 días): Foundation

- Crear tablas `catalog_events`, `catalog_event_aliases`, `system_catalog_configs`.
- Implementar validadores de naming PascalCase.
- Seed inicial desde `braze-sdk-playground.html` y `event-inventory.json`.

Entregable: base persistente + bootstrap de catálogo.

## Fase 1 (4-6 días): APIs de gobierno

- Implementar Catalog API + SystemCatalogConfig API.
- Agregar auditoría de cambios.
- Endpoints protegidos por auth de backoffice.

Entregable: administración de eventos y reglas por sistema.

## Fase 2 (4-6 días): Ingest gobernado

- Integrar motor de resolución en `/ingest` y `/ingest/batch`.
- Aplicar decisiones según config.
- Respuestas estándar (`forwarded`, `accepted_not_forwarded`, `rejected`).

Entregable: ingest totalmente controlado por catálogo/config.

## Fase 3 (5-8 días): Destinos robustos

- Añadir mappers versionados para Braze y GA4.
- Persistir resultados de entrega por destino.
- Retries y outbox worker (si aplica en esta fase).

Entregable: fan-out confiable y trazable.

## Fase 4 (3-5 días): Backoffice MVP

- UI de catálogo + system config + operaciones.
- Toggles y filtros operativos.
- Log de auditoría consultable.

Entregable: operación self-service por negocio/tech ops.

## 11) Criterios de aceptación

1. Un evento solo se envía a destino si existe en `Catalog` y está habilitado en `SystemCatalogConfig`.
2. El sistema soporta naming canónico PascalCase y resolución por alias legacy.
3. Cada ingest deja rastro auditable con decisión y razón.
4. El backoffice puede activar/desactivar eventos por sistema sin despliegue.
5. Braze y GA4 reciben payload transformado según configuración vigente.

## 12) Riesgos y mitigaciones

- **Riesgo:** explosión de aliases legacy.
  - **Mitigación:** expiración programada y métricas de uso por alias.
- **Riesgo:** cambios en naming rompen dashboards.
  - **Mitigación:** canonical estable + tabla de equivalencias histórica.
- **Riesgo:** reglas por sistema inconsistentes.
  - **Mitigación:** validadores de conflicto y pruebas de configuración antes de activar.
- **Riesgo:** errores silenciosos en routing.
  - **Mitigación:** auditoría obligatoria + alertas por ratio de rechazo/fallo.

## 13) Siguiente paso inmediato recomendado

1. Aprobar este diseño.
2. Congelar lista inicial de canónicos PascalCase.
3. Crear seed inicial (`Catalog` + `SystemCatalogConfig` por sistema crítico).
4. Implementar Fase 0 y Fase 1 en el siguiente sprint.

