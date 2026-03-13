# Reporte rápido: duplicados de eventos y atributos Braze

Resumen de eventos y atributos que significan lo mismo en el codebase (excl. docs, porting analysis, events.md). Incluye dónde se usan, diferencia (si la hay) y recomendación de consolidación.

---

## 1. Eventos duplicados / equivalentes

### 1.1 `started_checkout` vs `checkout_started`

| Variante | Dónde se usa | Notas |
|----------|--------------|--------|
| **started_checkout** | enhance.md-version1 (UserCheckout.vue, Payment.vue), kwilthealth.com (CheckoutView, CartView, CartView.vue, `useBrazeTracking.js`), microservices (events.go) | Evento enviado desde **frontend** (Vue/microservicios) al iniciar checkout. |
| **checkout_started** | magento-kwt, magento-emd: `ShippingInformationManagementPlugin.php` (al guardar dirección de envío en checkout) | Evento enviado desde **backend Magento** (plugin). |

**Parámetros actuales:**  
- **started_checkout (frontend, Braze JS / composables):**  
  - Variantes de payload:  
  - `email`, `SMS`/`sms`, `product_name` (string o array), `product_sku` (a veces), `product_plan`, `product_image`, `product_price`, `product_url`, `currency`, `timestamp`.  
  - En algunos flujos solo se envía `email`, `sms`, `product_name`, `product_plan`.  
- **checkout_started (Magento plugin):**  
  - `quote_id`, `store_id`, `grand_total`, `items_count` (propiedades de carrito/quote Magento).

**Conclusión de parámetros:** No son equivalentes: **frontend** envía contexto de producto/usuario, el **backend** envía contexto de quote/carrito. Si se unifica el nombre en Braze, hay que decidir un **superset de propiedades** o normalizar a un esquema común (por ejemplo, siempre enviar `product_*` + `quote_id` cuando exista).  
**Diferencia conceptual:** Mismo concepto (usuario inició checkout). Origen distinto: frontend vs backend y distinto shape de payload.  
**Recomendación:** Unificar en **`checkout_started`** (alineado con Magento y nomenclatura `*_started`). Actualizar frontend (enhance.md-version1, kwilthealth.com) y `microservices/shared/braze/events.go` a `checkout_started` y deprecar `started_checkout`.

---

### 1.2 `subscription_renewal` / `upcoming_subscription_renewal` / `subscription_renewed`

| Variante | Dónde se usa | Significado |
|----------|--------------|-------------|
| **subscription_renewal** | magento-kwt/emd: `SubscriptionGenerateSaveAfter.php` (cuando se genera un renewal/orden de renovación) | Evento: **renovación ejecutada** (orden creada). |
| **upcoming_subscription_renewal** | magento-kwt/emd: cron `CheckUpcomingRenewals.php`, custom scripts (braze_events_cron, BrazeEventBuilder, BrazeEventProcessors) | Evento: **recordatorio** de que la renovación se acerca (días hasta renew). |
| **subscription_renewed** | No encontrado como nombre de evento en el codebase | — |

**Diferencia:**  
- `subscription_renewal` = renovación ya ocurrida (order/renewal generado).  
- `upcoming_subscription_renewal` = aviso previo (ej. “renewal en X días”).  
No son duplicados; son dos eventos distintos.  
**Recomendación:** Mantener ambos. Si en Braze existe `subscription_renewed`, mapear a `subscription_renewal` o documentar equivalencia en un solo nombre (ej. `subscription_renewal` para “renewal ejecutado” y `upcoming_subscription_renewal` para “próximo renewal”).

---

### 1.3 `customer_registered` vs `account_registered`

| Variante | Dónde se usa | Notas |
|----------|--------------|--------|
| **customer_registered** | magento-kwt, magento-emd: `Enhance/Braze/Observer/Customer/RegisterSuccess.php` | Backend Magento: registro exitoso de cliente. |
| **account_registered** | enhance.md-version1 (Auth.vue, `useBrazeTracking.js`), kwilthealth.com (RegisterView, LiveFormPreview, `useBrazeTracking.js`), magento-kwt (braze_events_cron.php), magento-emd (BrazeEventBuilder, BrazeEventProcessors, braze_sync_by_email), microservices (events.go) | Frontend + scripts/cron emd: mismo hecho (registro de cuenta). |

**Parámetros actuales:**  
- **customer_registered (Magento observer):**  
  - `properties` típicas: `source`, `store_id`, `website_id`, `email`, `first_name`, `last_name`, `dob`, `gender`, `sms`, etc.  
- **account_registered (frontend enhance.md-version1 / kwilthealth.com):**  
  - `customer_id`, `first_name`, `last_name`, `email`, `SMS`/`sms`, `link_to_account_login`.  
- **account_registered (scripts/crons Magento):**  
  - Mínimo: `email`, `sms` y a veces `registration_source`, `link_to_account_login`.

**Conclusión de parámetros:** Todos representan la **misma acción de registro**, pero el conjunto de propiedades no es idéntico: el observer Magento tiene payload más rico; algunos flujos de frontend solo envían `email/sms/login_link`.  
**Diferencia conceptual:** Mismo evento de negocio, con distintos orígenes y nivel de detalle.  
**Recomendación:** Consolidar en **`account_registered`** (más usado en frontend y scripts). Cambiar en magento-kwt y magento-emd el observer `RegisterSuccess.php` para enviar `account_registered` en lugar de `customer_registered`, y deprecar `customer_registered` en Braze/documentación. Idealmente, armonizar un payload mínimo esperado: `customer_id`, `email`, `sms`, `first_name`, `last_name`, `registration_source`, `link_to_account_login`.

---

### 1.4 `logged_in` / `logged_into_portal` / `login` / `customer_logged_in`

| Variante | Dónde se usa | Notas |
|----------|--------------|--------|
| **customer_logged_in** | magento-kwt: `Enhance/Braze/Observer/Customer/Login.php` (activo). magento-emd: mismo observer pero **comentado** | Solo Magento; “login como cliente”. |
| **logged_into_portal** | enhance.md-version1 (LoginRegister.vue, Intake/Auth.vue, Customer/Auth.vue, `useBrazeTracking.js`), kwilthealth.com (LoginView, services/login.js, `useBrazeTracking.js`), magento-emd (BrazeEventBuilder, BrazeEventProcessors, braze_sync_by_email) | Frontend + cron/scripts: login en portal. |
| **logged_in** | magento-emd: atributos de tracking (`logged_in_sent`) y claves internas | Uso interno (dedup), no como nombre de evento enviado a Braze. |
| **login** | Uso genérico (rutas, formularios, recaptcha action); no como evento Braze | No es evento Braze. |

**Parámetros actuales:**  
- **customer_logged_in (Magento observer):**  
  - `customer_id`, `email`, `store_id`, `website_id` (y potencialmente más metadatos de cliente).  
- **logged_into_portal (frontend / composables / crons):**  
  - Siempre incluyen al menos: `email`, `SMS`/`sms`, `date_logged_in`, `portal_url`.  
  - En emd (buildLoggedInEvent) se usa el mismo esquema (`date_logged_in`, `portal_url`, `email`, `SMS`).  

**Conclusión de parámetros:** Ambos eventos describen el **mismo login**, pero el payload de `customer_logged_in` está orientado a IDs Magento y el de `logged_into_portal` a telemetría de portal (email/sms/fecha/url).  
**Diferencia conceptual:** Mismo acto de login; diferente naming y shape de propiedades según la capa.  
**Recomendación:** Unificar en **`logged_into_portal`** (ya estándar en frontend y emd). En magento-kwt (y magento-emd si se reactiva el observer) cambiar el evento a `logged_into_portal` para alinear con el resto. Mantener `logged_in_sent` solo como atributo interno si se sigue usando, y homogeneizar el payload mínimo esperado: `email`, `sms`, `date_logged_in`, `portal_url`.

---

### 1.5 `product_added_to_cart` vs `add_to_cart`

| Variante | Dónde se usa | Notas |
|----------|--------------|--------|
| **product_added_to_cart** | magento-kwt, magento-emd: `Enhance/Braze/Plugin/CartItemRepositoryPlugin.php` (al añadir/actualizar ítem en carrito) | Backend Magento. |
| **add_to_cart** | enhance.md-version1 (UserCartDetails, SelectMedication, MedicalInformation), kwilthealth.com (ProductDetails, `useBrazeTracking.js`, MembershipPayment.vue, LiveFormPreview.vue), magento-emd (BrazeEventProcessors comentado, BrazeEventBuilder comentado), microservices (events.go) | Frontend y referencias en scripts. |

**Parámetros actuales:**  
- **product_added_to_cart (Magento plugin, cuando está habilitado):**  
  - Payload típico de Magento: `product_id`/`sku`, `name`, `qty`, `price`, posiblemente `plan_length`/`product_plan`, `quote_id` y metadatos de carrito.  
- **add_to_cart (frontend / composables):**  
  - En enhance.md-version1: `email`, `SMS`/`sms`, `product_name`, `product_sku`, `product_image`, `product_price`, `plan_length`/`product_plan`, `currency`, `quantity`, `timestamp`.  
  - En kwilthealth.com: al menos `email`, `sms`, `product_name`, `product_image`, `product_price`, `product_plan`, más flags como `add_to_cart_success`, `default_payment`, `address{...}` en algunos flujos.  

**Conclusión de parámetros:** Representan el mismo hecho (“se añadió un producto al carrito”), pero con payloads distintos: backend enfocado en IDs/qty/precio técnico; frontend en datos de marketing/analytics. Hay overlap (`product_name`, `product_plan`/`plan_length`, `product_price`, contacto), pero no son idénticos.  
**Diferencia conceptual:** Mismo evento de negocio, distintos orígenes y distinto detalle de payload.  
**Recomendación:** Consolidar en **`add_to_cart`** (más corto y usado en frontend/microservices). Cambiar en magento-kwt y magento-emd el `CartItemRepositoryPlugin` para enviar `add_to_cart` en lugar de `product_added_to_cart`, y documentar un esquema mínimo recomendado (`product_name`, `product_sku`, `product_plan`, `product_price`, `email`, `sms`, `quantity`).

---

## 2. Atributos duplicados / equivalentes

### 2.1 `billing_address_line2` vs `billing_address_line_2`

| Variante | Dónde se usa |
|----------|--------------|
| **billing_address_line_2** (con guión bajo) | enhance.md-version1 (OrderConfirmation.vue), magento-emd: BrazeEventBuilder, braze_cron_job.php |
| **billing_address_line2** (sin guión bajo) | magento-emd: braze_fix_data_v2.php, OrderPlaceAfter.php, AddressSaveAfter.php, SubscriptionGenerateSaveAfter.php, SyncOrdersToBraze.php |

**Recomendación:** Unificar en **`billing_address_line_2`** (consistente con `shipping_address_line_2` y convención “line_2”). Reemplazar todas las ocurrencias de `billing_address_line2` por `billing_address_line_2` en Magento y scripts.

---

### 2.2 `shipping_address_line2` vs `shipping_address_line_2`

| Variante | Dónde se usa |
|----------|--------------|
| **shipping_address_line_2** | enhance.md-version1 (OrderConfirmation.vue), magento-emd: BrazeDbQueries, BrazeEventBuilder, BrazeEventProcessors, braze_cron_job.php |
| **shipping_address_line2** | magento-emd: braze_fix_data_v2.php, OrderPlaceAfter, AddressSaveAfter, SubscriptionGenerateSaveAfter, OrderShipped, SyncOrdersToBraze |

**Recomendación:** Unificar en **`shipping_address_line_2`**. Reemplazar `shipping_address_line2` por `shipping_address_line_2` en todos los archivos listados.

---

### 2.3 `cancel_date` vs `subscription_cancel_date`

| Variante | Dónde se usa | Notas |
|----------|--------------|--------|
| **cancel_date** | magento-kwt/emd: observers (SubscriptionSaveAfter, SubscriptionStatusChange), eventos (subscription_canceled); magento-emd BrazeEventBuilder, BrazeEventProcessors; microservices (props en eventos) | En **eventos** (propiedad del evento de cancelación). |
| **subscription_cancel_date** | magento-emd: atributos de usuario (braze_sync_by_email, braze_fix_data_v2, braze_cron_job, BrazeEventProcessors); microservices (attributes.go, kwilt-order, kwilt-myaccount) | Como **atributo de perfil** de usuario en Braze. |

**Diferencia:** `cancel_date` suele ser propiedad de evento; `subscription_cancel_date` es atributo de usuario (fecha de cancelación de la suscripción).  
**Recomendación:** Mantener **`subscription_cancel_date`** solo para el **atributo de perfil**. En payloads de eventos se puede seguir usando `cancel_date` para la fecha de ese evento. Si se quiere un solo nombre en Braze para el perfil, usar solo `subscription_cancel_date` y no duplicar con otro nombre.

---

### 2.4 `customer_id` vs `magento_customer_id`

| Variante | Dónde se usa |
|----------|--------------|
| **customer_id** | Uso masivo: respuesta de APIs, BD, modelos, payloads internos (no siempre como atributo Braze). En Braze: enhance.md-version1 (Auth.vue) en payload de eventos (customer_id en propiedades). |
| **magento_customer_id** | No encontrado como atributo Braze en el codebase. |

**Recomendación:** Para **atributo de usuario en Braze**, definir uno solo: p. ej. **`magento_customer_id`** (o `customer_id` si Braze ya lo usa así) y documentarlo. El `external_id` ya es `magento_{customerId}`; si se necesita el ID como atributo, usar un único nombre en todos los envíos.

---

### 2.5 `email` vs `Email` (case)

En Braze los atributos son case-sensitive. En el codebase:
- **Minúscula `email`:** mayoritario (Magento observers, microservices models JSON `"email"`, frontend).
- **Mayúscula `Email`:** solo en mensajes de validación/labels (ej. `'email': 'Email'` en VeeValidate), no como clave de atributo Braze.

**Recomendación:** Usar siempre **`email`** (minúscula) como atributo Braze. No usar `Email` como clave en `/users/track`.

---

### 2.6 `SMS` vs `sms`

| Variante | Dónde se usa |
|----------|--------------|
| **sms** (minúscula) | magento-kwt (todos los observers y crons), microservices (models.go y eventos: `"sms"` en JSON) |
| **SMS** (mayúscula) | magento-emd: BrazeEventBuilder.php, BrazeEventProcessors.php, braze_sync_all.php, braze_cron_job.php, ShippingInformationManagementPlugin.php |

**Recomendación:** Unificar en **`sms`** (minúscula) para coincidir con Magento KWT y microservices. Cambiar en magento-emd (BrazeEventBuilder, BrazeEventProcessors, braze_sync_all, braze_cron_job, plugin) de `'SMS'` a `'sms'`.

---

### 2.7 `coupon` / `coupon_code` / `order_coupon`

| Variante | Dónde se usa (como atributo/event property Braze) |
|----------|----------------------------------------------------|
| **coupon** | magento-kwt/emd: OrderPlaceAfter (event properties), SubscriptionGenerateSaveAfter; magento-emd: braze_fix_data_v2, braze_cron_job (atributo usuario). |
| **coupon_code** | magento-kwt/emd: CouponManagementPlugin (event properties), SyncOrdersToBraze (lee BD); enhance.md-version1, kwilthealth.com (payloads). Frontend y plugin envían `coupon_code`. |
| **order_coupon** | magento-kwt/emd: OrderPlaceAfter y SyncOrdersToBraze como **atributo** de usuario (último cupón de orden). |

**Diferencia:** En eventos (apply/remove coupon, order) se usa `coupon_code` o `coupon`; como atributo de “último cupón usado” en Magento a veces `order_coupon` y en otros sitios `coupon`.  
**Recomendación:**  
- En **eventos**: usar **`coupon_code`** (claro y ya usado en frontend/plugin).  
- En **atributos de perfil** (último cupón/orden): usar **`order_coupon`** o **`coupon`** de forma única; elegir uno (ej. **`order_coupon`**) y reemplazar el otro en magento-emd (braze_fix_data_v2, braze_cron_job) y en Magento observers si envían atributo de cupón.

---

### 2.8 `discount` vs `order_discount`

| Variante | Dónde se usa |
|----------|--------------|
| **discount** | magento-kwt/emd: OrderPlaceAfter (event properties y atributos), SubscriptionGenerateSaveAfter; magento-emd: BrazeEventBuilder, braze_fix_data_v2, braze_cron_job (atributo usuario). |
| **order_discount** | magento-kwt/emd: OrderPlaceAfter y SyncOrdersToBraze como **atributo** de usuario (discount amount en orden). |

**Recomendación:** Unificar en **`order_discount`** para el atributo de perfil (monto de descuento de la orden), para no confundir con descuento en evento. En propiedades de evento `order_placed` se puede mantener `discount`; para atributo de usuario usar solo **`order_discount`** y eliminar `discount` de atributos en braze_fix_data_v2 y braze_cron_job si hoy se envían ambos.

---

### 2.9 `last_video_consult_date` vs `last_video_consultation_date`

| Variante | Dónde se usa |
|----------|--------------|
| **last_video_consult_date** | magento-emd: BrazeEventProcessors.php (atributo usuario). |
| **last_video_consultation_date** | magento-emd: braze_fix_data_v2.php, braze_cron_job.php. |

**Recomendación:** Unificar en **`last_video_consultation_date`** (más explícito). Cambiar BrazeEventProcessors para escribir `last_video_consultation_date` en lugar de `last_video_consult_date`.

---

### 2.10 `date_of_renewal` vs `renewal_date`

| Variante | Dónde se usa |
|----------|--------------|
| **date_of_renewal** | magento-kwt/emd: SubscriptionGenerateSaveAfter, CheckUpcomingRenewals, BrazeEventBuilder, BrazeEventProcessors, braze_fix_data_v2, braze_cron_job; microservices (models.go). |
| **renewal_date** | magento-kwt: braze_events_cron (query y propiedades de evento); magento-emd: CheckUpcomingRenewals (propiedades de evento upcoming). |

**Recomendación:** Para **atributo de usuario** y **propiedad de evento** de renovación usar un solo nombre: **`date_of_renewal`**. Donde se use `renewal_date` en payloads a Braze (braze_events_cron, CheckUpcomingRenewals), cambiar a `date_of_renewal` para consistencia.

---

### 2.11 `days_until_renewal` vs `days_until_subscription_renewal`

| Variante | Dónde se usa |
|----------|--------------|
| **days_until_renewal** | magento-kwt/emd: CheckUpcomingRenewals (propiedades de evento). |
| **days_until_subscription_renewal** | magento-kwt/emd: CheckUpcomingRenewals (atributos de usuario en el mismo cron). |

**Recomendación:** Unificar en **`days_until_subscription_renewal`** (más claro). Reemplazar `days_until_renewal` por `days_until_subscription_renewal` en propiedades de evento en CheckUpcomingRenewals.

---

### 2.12 `order_id` vs `order_number`

Uso muy extendido: `order_id` suele ser ID interno; `order_number` es el número mostrado al usuario (increment_id, etc.). En Braze:
- **order_id** se usa en payloads de eventos (order_placed, etc.) y a veces como atributo.
- **order_number** en vistas y atributos (ej. last_order_number).

**Recomendación:** Definir convención: **`order_id`** = ID interno (entero/uuid); **`order_number`** = número de orden visible (string). Para atributos de “última orden” usar **`last_order_number`** (o `order_number` si es un único valor). No mezclar: en un mismo contexto (evento o atributo) usar el mismo nombre según el significado.

---

### 2.13 `portal_link` / `portal_url` / `link_to_account_login` / `account_login_link` / `manage_subscription_link`

| Variante | Uso típico |
|----------|------------|
| **portal_link** | URL al portal/dashboard (fotos, sync, eventos, microservices). |
| **portal_url** | URL al portal/dashboard (enhance.md-version1, kwilthealth.com en logged_into_portal / account_registered). |
| **link_to_account_login** | URL a login (enhance.md-version1, kwilthealth.com, magento-kwt braze_events_cron). |
| **account_login_link** | magento-emd: braze_fix_data_v2, braze_cron_job (atributo usuario). |
| **manage_subscription_link** | magento-kwt/emd: CheckUpcomingRenewals (link a gestionar suscripción). |

**Recomendación:**  
- **`portal_link`** = URL principal del portal/dashboard (un solo nombre; deprecar `portal_url` como atributo Braze y mapear a `portal_link`).  
- **`account_login_link`** = URL de login (unificar con `link_to_account_login` en **`account_login_link`**).  
- **`manage_subscription_link`** = mantener para link específico de suscripción.  
Acción: en frontend y scripts reemplazar `portal_url` por `portal_link` y `link_to_account_login` por `account_login_link` en atributos Braze.

---

### 2.14 `date_logged_in` / `magento_last_login` / `logged_into_portal_ids`

| Variante | Uso |
|----------|-----|
| **date_logged_in** | Propiedad en evento `logged_into_portal` (frontend, BrazeEventBuilder). |
| **magento_last_login** | Atributo de usuario (magento-emd: braze_sync_by_email, braze_sync_all, braze_sync_user, braze_fix_data_v2, braze_cron_job). |
| **logged_into_portal_ids** | Atributo interno de dedup (lista de IDs ya enviados) en magento-emd; no es el “last login”. |

**Recomendación:**  
- **Atributo de perfil “última fecha de login”:** unificar en **`magento_last_login`** (o `last_login_at` si se prefiere nombre genérico).  
- **Propiedad de evento:** mantener **`date_logged_in`** en el evento `logged_into_portal`.  
- **`logged_into_portal_ids`** es solo control interno; no cambiar nombre salvo por claridad interna.

---

### 2.15 `last_intake_name` vs `latest_intake_name` / `last_intake_link` vs `latest_intake_link`

| Variante | Dónde se usa |
|----------|--------------|
| **last_intake_name** | enhance.md-version1: MedicalInformation.vue (setCustomUserAttribute). |
| **latest_intake_name** | No encontrado en código. |
| **last_intake_link** | enhance.md-version1: MedicalInformation.vue. |
| **latest_intake_link** | No encontrado en código. |

**Recomendación:** Mantener **`last_intake_name`** y **`last_intake_link`**. Si en Braze existen `latest_*`, migrar a `last_*` o documentar alias.

---

### 2.16 `latest_intake_complete` vs `intake_complete`

| Variante | Dónde se usa |
|----------|--------------|
| **intake_complete** | magento-emd: braze_sync_by_email, braze_get_user, BrazeEventProcessors (atributo usuario); microservices kwilt-lab-ai, kwilt-dashboard-config. |
| **latest_intake_complete** | No encontrado. |

**Recomendación:** Usar **`intake_complete`** como atributo de perfil. No introducir `latest_intake_complete` salvo que ya exista en Braze; en ese caso mapear a `intake_complete`.

---

### 2.17 `subscription_cancel_reason` vs `cancellation_reason`

| Variante | Uso |
|----------|-----|
| **cancellation_reason** | Propiedad en eventos (subscription_canceled, etc.); enhance.md-version1, enhance.md, kwilthealth.com (useBrazeTracking); magento-emd braze_fix_data_v2, braze_cron_job (también como atributo). |
| **subscription_cancel_reason** | Atributo de usuario en magento-emd (braze_sync_by_email, braze_fix_data_v2, braze_cron_job, BrazeEventProcessors); microservices (attributes). |

**Recomendación:** Para **atributo de perfil** usar **`subscription_cancel_reason`**. En **propiedades de evento** usar **`cancellation_reason`**. Dejar de enviar ambos nombres al mismo perfil; en braze_fix_data_v2 y braze_cron_job enviar solo `subscription_cancel_reason` como atributo y no duplicar con `cancellation_reason`.

---

### 2.18 `plan_length` / `last_plan_length` / `product_plan` / `subscription_frequency`

| Variante | Uso |
|----------|-----|
| **plan_length** | Event properties y atributos (orden, suscripción, renewal, payment failed, etc.) en Magento y scripts. |
| **last_plan_length** | magento-kwt/emd: SubscriptionGenerateSaveAfter; magento-emd: braze_fix_data_v2, braze_cron_job (atributo usuario). |
| **product_plan** | magento-kwt/emd: observers de suscripción, SyncOrdersToBraze; kwilthealth.com (checkout, cart); magento-emd scripts. A veces mismo valor que plan_length (frecuencia). |
| **subscription_frequency** | magento-kwt/emd: SubscriptionSaveAfter, SubscriptionGenerateSaveAfter, SyncSubscriptionsToBraze; magento-emd scripts y crons (atributo usuario). |

**Recomendación:**  
- **Frecuencia de suscripción (ej. “4 week”):** unificar en **`subscription_frequency`** para atributo de perfil y en eventos donde se quiera un solo nombre.  
- **Plan/producto (nombre o descripción):** usar **`product_plan`** en eventos y atributos cuando el valor sea “nombre del plan” o similar.  
- **`plan_length`** y **`last_plan_length`:** a menudo el mismo valor; usar **`plan_length`** en eventos y **`subscription_frequency`** (o `plan_length`) para “último plan” en perfil, y eliminar **`last_plan_length`** si no aporta (o documentar que es alias de `plan_length` para el último periodo).

---

## 3. Resumen de acciones sugeridas

| Tema | Acción |
|------|--------|
| Checkout event | Unificar en `checkout_started`; actualizar frontend y microservices. |
| Registro | Unificar en `account_registered`; cambiar observer RegisterSuccess en Magento. |
| Login event | Unificar en `logged_into_portal`; cambiar observer Login en Magento. |
| Cart event | Unificar en `add_to_cart`; cambiar CartItemRepositoryPlugin en Magento. |
| Direcciones | Usar `billing_address_line_2` y `shipping_address_line_2` en todos los envíos. |
| SMS | Usar `sms` (minúscula) en magento-emd. |
| Email | Usar `email` (minúscula) como atributo Braze. |
| Cupón (atributo) | Unificar en `order_coupon` o `coupon`; evento `coupon_code`. |
| Descuento (atributo) | Usar `order_discount` para perfil. |
| Video consult | Unificar en `last_video_consultation_date`. |
| Renewal (días) | Unificar en `days_until_subscription_renewal`. |
| Renewal (fecha) | Unificar en `date_of_renewal` en payloads Braze. |
| Portal URLs | `portal_link`, `account_login_link`; deprecar `portal_url` y `link_to_account_login` en Braze. |
| Cancel reason | Atributo: `subscription_cancel_reason`; evento: `cancellation_reason`. |
| Plan/frequency | Atributo perfil: `subscription_frequency` (y opcionalmente `product_plan`); reducir uso de `last_plan_length`. |

---

*Generado a partir de búsquedas en repos: magento-kwt, magento-emd, system, microservices, secure-consult, old-secure-consult, kwilthealth.com, kt-feedback-service, enhance.md, enhance.md-version1. Excluidos: docs, porting analysis, events.md.*
