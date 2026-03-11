# Stage 2 — Braze strategy: best practices for the ecosystem

Documento de **estrategia** (no auditoría de implementación). Perspectiva: jefe de aplicación + developer ultra senior — qué haría para aplicar Braze de forma correcta en EnhanceMD, Kwilt Health, secure-consult, Magento y microservicios.

---

## 1. Principios rectores

| Principio | Descripción |
|-----------|-------------|
| **Single source of truth por evento** | Cada hecho de negocio se envía a Braze **una sola vez**, desde el sistema que es dueño de la verdad (ej. “order_placed” solo desde el servicio que confirma el pago). |
| **Identidad antes que eventos** | Sin identidad estable (external_id + alias), los eventos no se pueden unir a un perfil; la resolución de identidad es prioridad #1. |
| **Backend-first para hechos críticos** | Eventos que definen negocio (orden, pago, intake completo, cita confirmada) los emite el backend; el frontend solo complementa con contexto de sesión/UX. |
| **Schema explícito y gobernado** | Nombre y propiedades de cada evento están definidos en un contrato (doc o repo); cambios con versionado y deprecación. |
| **Multi-marca, un solo modelo mental** | Misma taxonomía de eventos y atributos para EMD y KWT; la marca es una dimensión (campo) o un segmento, no un esquema distinto. |

---

## 2. Identidad y resolución

### 2.1 External ID

- **Regla:** Un único `external_id` por usuario B2C: el ID de cliente del sistema de registro (ej. `customer_id` de emd-user-services / Magento). Mismo valor en todos los touchpoints (enhance.md, kwilthealth.com, Magento, microservicios).
- **Alias:** Mantener alias por email (y opcionalmente por `consult_id` / order_id donde aplique) para reconciliar usuarios que aún no tienen `customer_id` (ej. pre-login). Al hacer login/registro, hacer `braze.changeUser(external_id)` y dejar de usar el alias anónimo para ese dispositivo.
- **Proveedores (secure-consult):** Si Braze se usa para ellos, un `external_id` distinto (ej. `practitioner_id`) y un perfil separado por tipo de usuario (atributo `user_type: patient | practitioner`) para no mezclar en segmentos.

### 2.2 Dispositivo y sesión

- **Device ID:** Dejar que el SDK genere/gestione el device_id; no usarlo como identificador principal. Usar solo para push tokens y atributos de dispositivo.
- **Sesión anónima:** Eventos pre-login (ej. “intake_started”, “step_viewed”) enviarlos con alias (email si se capturó) o con un anonymous_id temporal; en el primer login/registro, identificar con `external_id` y, si existe política de merge, fusionar el perfil anónimo al perfil identificado.

### 2.3 Cross-app y cross-brand

- Mismo `external_id` en enhance.md (EMD) y kwilthealth.com (KWT) si es el mismo customer en la base de datos. Braze recibe eventos de ambas apps y los une por `external_id`; usar atributo `brand` o `source_app` en el evento para segmentar (ej. “solo EMD”, “solo KWT”, “ambos”).

---

## 3. Taxonomía de eventos

### 3.1 Convención de nombres

- **Formato:** `snake_case`, verbo en pasado o sustantivo que denote el hecho: `order_placed`, `intake_completed`, `appointment_booked`, `payment_method_added`.
- **Prefijos por dominio (opcional):** Si se quiere namespacing: `commerce.order_placed`, `intake.step_saved`, `scheduler.appointment_booked`. Decisión única y documentada.
- **Evitar:** Nombres genéricos (`click`, `submit`) sin contexto; mejor `checkout_submit` o `intake_step_submit`.

### 3.2 Propiedades estándar (en todos los eventos)

- `source` (string): app que emite: `enhance_md_web`, `kwilthealth_web`, `secure_consult`, `magento_emd`, `magento_kwt`, `kwilt_intake`, `kwilt_order`, etc.
- `brand` (string): `emd` | `kwilt`.
- `environment` (string): `production` | `staging` (nunca enviar staging a prod Braze salvo que exista app Braze dedicada).
- Timestamp: enviado por Braze si no se manda; si el backend envía con delay, incluir `event_time` para no sesgar analytics.

### 3.3 Eventos canónicos por dominio (qué existiría en el contrato)

- **Intake:** `intake_started`, `intake_step_viewed`, `intake_step_saved`, `intake_completed` (propiedades: intake_type, product/sku, step_id donde aplique).
- **Commerce:** `cart_updated`, `checkout_started`, `order_placed`, `payment_method_added`, `subscription_renewed` (order_id, amount, currency, skus).
- **Scheduler:** `appointment_scheduled`, `appointment_cancelled`, `appointment_completed`.
- **Labs:** `lab_result_available`, `lab_uploaded`.
- **Auth:** `signed_up`, `signed_in`, `signed_out`, `email_verified`.
- **Engagement (frontend):** `screen_viewed` (screen_name, flow), `cta_clicked` (cta_name, location) — solo si se usan para journeys; no duplicar con GA4 sin criterio.

Cada uno con **owner** (qué sistema lo emite) y **único emisor** para ese evento en producción.

---

## 4. Quién envía qué (ownership)

### 4.1 Backend como dueño de la verdad

- **order_placed:** Solo el servicio que confirma el pago (kwilt-order o Magento). Los frontends no emiten “order_placed”; pueden emitir “checkout_submitted” como intención.
- **intake_completed:** Solo el servicio que persiste el estado final (kwilt-intake o kwilt-lab-ai). El frontend puede emitir “intake_final_step_submitted”.
- **appointment_booked:** Solo kwilt-scheduler (o el backend que confirma la cita).
- **payment_method_added:** Backend que guarda la tarjeta (kwilt-order / pasarela).

Ventajas: consistencia, no duplicados, no dependencia de que el usuario tenga la pestaña abierta; el evento llega aunque el usuario cierre el navegador tras pagar.

### 4.2 Frontend como complemento

- Eventos de **sesión/UX:** `screen_viewed`, `intake_step_viewed`, `checkout_started`, `cta_clicked`. Útiles para abandonos, tiempo en paso, A/B tests.
- **Atributos de sesión:** última URL, referrer, device type — como atributos de usuario o propiedades de evento, según política.
- No reenviar desde frontend el mismo hecho que ya emite el backend (ej. no “order_placed” desde Vue si kwilt-order ya lo envía).

### 4.3 Magento

- Observers/cron que emitan eventos canónicos con el mismo nombre y propiedades que el backend (ej. `order_placed` con order_id, amount, skus). `source: magento_emd` o `magento_kwt` para distinguir.
- Sincronización de atributos de usuario (email, nombre, última compra) vía API Braze o eventos; un solo flujo de “customer updated” para no bombardear con updates redundantes.

### 4.4 Tabla resumen (recomendación)

| Evento | Emisor único | Fuente típica |
|--------|--------------|----------------|
| order_placed | Backend | kwilt-order / Magento |
| intake_completed | Backend | kwilt-intake / kwilt-lab-ai |
| appointment_booked | Backend | kwilt-scheduler |
| payment_method_added | Backend | kwilt-order |
| signed_up / signed_in | Backend o frontend (uno solo) | Auth service o SPA tras login exitoso |
| intake_started / step_saved | Backend o frontend (uno solo) | kwilt-intake (save-intake) o SPA |
| screen_viewed, checkout_started | Frontend | enhance.md, kwilthealth.com |

---

## 5. Canales y consentimiento

- **Push:** Solo si hay app nativa; en web, solo Web Push con consentimiento explícito y almacenamiento de suscripción en backend/Braze.
- **Email:** Respetar preferencias (opt-in por tipo: marketing, transaccional). Atributos en Braze: `email_subscribe`, `email_marketing_consent`, etc.; actualizarlos desde backend cuando el usuario cambie preferencias.
- **In-app / Content Cards:** Útiles en SPAs; definir lugares canónicos (ej. banner en dashboard, post-checkout) y no abusar para no cansar.
- **SMS:** Consentimiento explícito; cumplir normativa por país (TCPA, GDPR, etc.). Guardar en Braze y en sistema de origen.
- **Provider (secure-consult):** Si se envían mensajes a proveedores, segmentar por `user_type` y canal apropiado (email operativo vs marketing).

---

## 6. Multi-marca y multi-app

- **Un workspace Braze** (o agrupación clara por entorno) con **un solo esquema de eventos y atributos**. Marca y app como dimensión:
  - Atributo de usuario: `brand` (emd | kwilt), `primary_app` (opcional).
  - En cada evento: `brand`, `source` (app/servicio).
- **Segmentos:** Construidos sobre ese esquema: “Usuarios EMD que completaron intake y no compraron”, “Usuarios KWT con lab result en últimos 7 días”. No duplicar segmentos por marca con lógica distinta; usar filtros por `brand`/`source`.
- **Campañas y journeys:** Plantillas por marca (copy, creative) pero misma lógica de trigger (mismo evento, mismas propiedades). Liquid o segmentos para variar mensaje por marca.

---

## 7. Gobierno y contrato de datos

- **Registro de eventos:** Doc (Markdown/Confluence) o repo `docs/braze/` con tabla: evento, propiedades, tipo, emisor, deprecación. En cada PR que añada o cambie eventos, actualizar el registro.
- **Versionado:** Si se cambia el nombre o propiedades de un evento, mantener el antiguo durante un periodo (ej. 6 meses) con deprecation y migrar consumidores (journeys, reportes) al nuevo; luego dejar de enviar el viejo.
- **Validación:** En staging, un validador (script o pipeline) que compruebe que los payloads enviados cumplen el contrato (nombres, tipos). En prod, muestreo o alertas si llegan eventos “unknown”.
- **PII:** No enviar datos sensibles (número de tarjeta, resultados de labs completos) en propiedades de evento; usar identificadores (order_id, lab_result_id). Atributos de usuario: solo los necesarios para personalización (nombre, email, preferencias); el resto en sistema de origen.

---

## 8. Implementación técnica recomendada

- **SDK:** Una versión acordada del SDK Braze (Web, Android, iOS) por app; actualizar en ciclos controlados. En web, cargar desde CDN o bundle; no mezclar versión antigua y nueva en la misma app.
- **Inicialización:** Config (API key, endpoint) por entorno (env vars); no hardcodear keys en frontend. En backend, usar REST API o SDK del lenguaje con credenciales en secret manager.
- **Flush y batching:** Configurar flush (envío en lote) para no generar una petición por evento; respetar límites de Braze. En backend, cola + batch para alta carga.
- **Kill switch:** Feature flag o config que deshabilite el envío de eventos a Braze sin desplegar (útil en incidentes o si Braze cae). En frontend: no llamar a `logEvent` si flag desactivado; en backend: mismo criterio.
- **Errores:** No bloquear flujo de negocio si Braze falla; en backend, fire-and-forget o cola asíncrona; en frontend, try/catch y log local, no mostrar error al usuario.

---

## 9. Testing y QA

- **Staging:** App Braze separada para staging (o cluster); todos los entornos no-prod envían ahí. Misma identidad que prod (external_id) en tests E2E si hace falta, pero con datos de prueba.
- **Replay/seed:** Herramienta o script que reenvíe eventos de ejemplo contra staging para validar journeys y segmentos.
- **Validación de segmentos:** Antes de lanzar campaña, comprobar en staging que el segmento devuelve los usuarios esperados (muestra conocida).
- **No enviar tráfico real a staging:** Evitar que producción apunte por error a la app Braze de staging (revisar env vars en pipelines y config de prod).

---

## 10. Documentación y operación

- **Runbook:** Qué hacer si Braze deja de recibir eventos (comprobar keys, red, límites, status.braze.com); a quién escalar; cómo activar kill switch.
- **Ownership por dominio:** Una persona o equipo dueño de “intake”, “commerce”, “scheduler” en Braze (segmentos, campañas, eventos); coordinación con los equipos que emiten esos eventos.
- **Onboarding de devs:** Doc corta: “Cómo emitir un evento”, “Registro de eventos”, “Dónde está la config”. Link en README de cada repo que toque Braze.

---

## 11. Resumen ejecutivo

- **Identidad:** Un `external_id` por usuario; alias para anónimos; mismo ID en todas las apps/marcas.
- **Eventos:** Taxonomía única, snake_case, propiedades estándar (`source`, `brand`, `environment`); cada hecho de negocio con un solo emisor (backend preferido para críticos).
- **Ownership:** Backend para order_placed, intake_completed, appointment_booked, payment_method_added; frontend para sesión/UX; Magento alineado al mismo esquema.
- **Gobierno:** Registro de eventos, versionado con deprecación, validación en staging, cuidado con PII.
- **Multi-marca:** Un esquema; marca y app como dimensión; segmentos y campañas reutilizables.
- **Operación:** Kill switch, no bloquear negocio por fallos de Braze, staging separado, runbook y ownership por dominio.

Este documento sirve como **estrategia de referencia** para Stage 2 Braze; la fase siguiente puede ser auditar la implementación actual frente a estos criterios y definir un plan de convergencia.
