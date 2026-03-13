# Braze: eventos y atributos duplicados o sinónimos — ubicación y consolidación

Este documento ubica en el código todos los **eventos** y **atributos** que significan lo mismo pero tienen nombres distintos, y recomienda **un nombre estándar** y qué eliminar o unificar.

---

## 1. Eventos duplicados / sinónimos

### 1.1 checkout_started vs started_checkout

| Nombre | Dónde se usa | Fuente |
|--------|----------------|--------|
| **checkout_started** | Magento (ambos), enhance.md-version1 | **magento-kwt** `app/code/Enhance/Braze/Plugin/ShippingInformationManagementPlugin.php` L46 → `'name' => 'checkout_started'`. **magento-emd** mismo plugin L69. **enhance.md-version1** `resources/js/plugins/brazeEventTracker.js` L85 → `trackToBraze('checkout_started', ...)`. |
| **started_checkout** | kwilthealth.com, Go shared | **kwilthealth.com** `src/composables/useBrazeTracking.js` L207 `startedCheckout` → `trackEvent('started_checkout', ...)`; `CheckoutView.vue` L966, L1677; `CartView.vue` L140. **microservices/shared/braze/events.go** L28 `EventStartedCheckout = "started_checkout"`. |

**Diferencia:** Mismo significado (usuario inició checkout). Magento y enhance.md-version1 usan `checkout_started`; kwilthealth.com y Go usan `started_checkout`.

**Recomendación:** Consolidar en **`checkout_started`** (verbo en pasado + sustantivo, alineado con `order_placed`, `profile_updated`). Cambiar en kwilthealth.com y en `microservices/shared/braze/events.go` a `checkout_started` y dejar de emitir `started_checkout`. Actualizar segmentos/triggers en Braze que usen `started_checkout` para que usen `checkout_started`.

---

### 1.2 subscription_renewal vs upcoming_subscription_renewal vs subscription_renewed

| Nombre | Dónde se usa | Significado |
|--------|----------------|-------------|
| **subscription_renewal** | Magento (ambos) | Evento cuando **acaba de ocurrir** una renovación (cobro/orden generada). **magento-kwt** y **magento-emd** `Observer/Subscription/SubscriptionGenerateSaveAfter.php` L155 `'name' => 'subscription_renewal'`. |
| **upcoming_subscription_renewal** | Magento (ambos), custom scripts, Go | Evento de **recordatorio** (próxima renovación dentro de X días). **magento-kwt** y **magento-emd** `Cron/CheckUpcomingRenewals.php` L181. **magento-kwt** `custom-scripts/braze_events_cron.php`; **magento-emd** BrazeEventBuilder, BrazeEventProcessors, braze_cron_job. **microservices/shared/braze/events.go** `EventUpcomingRenewal = "upcoming_subscription_renewal"`. |
| **subscription_renewed** | Solo documentación / guías | Aparece en **magento-kwt** y **magento-emd** `README.md`, `INSTALLATION_INSTRUCTIONS.md`, `HEADLESS_VUEJS_INTEGRATION.md`, `BRAZE_MODULE_REVIEW_AND_FIXES.md`, `BRAZE_INTEGRATION_DEVELOPER_GUIDE.md` como nombre de evento, pero en código PHP el evento enviado es **`subscription_renewal`**. No hay `subscription_renewed` en payloads. |

**Diferencia:**  
- `subscription_renewal` = renovación **ya ejecutada**.  
- `upcoming_subscription_renewal` = aviso de **próxima** renovación.  
- `subscription_renewed` = nombre usado solo en docs; en código no se envía.

**Recomendación:**  
- Mantener **dos eventos**: `subscription_renewal` (renovación ocurrida) y `upcoming_subscription_renewal` (recordatorio).  
- Unificar documentación: en todos los MD usar `subscription_renewal` y dejar de mencionar `subscription_renewed` como evento enviado, o considerar un único nombre `subscription_renewed` para el evento “renovación ejecutada” y cambiar el código de `subscription_renewal` a `subscription_renewed` si se prefiere ese nombre (y actualizar Braze).

---

### 1.3 customer_registered vs account_registered

| Nombre | Dónde se usa |
|--------|----------------|
| **customer_registered** | **Magento (ambos)** Observer `Customer/RegisterSuccess.php` → evento enviado a Braze. **magento-kwt** L89; **magento-emd** L88. |
| **account_registered** | **kwilthealth.com** `useBrazeTracking.js` L333 `accountRegistered` → `trackEvent('account_registered', ...)`; `LiveFormPreview.vue`, `RegisterView.vue`, `RegisterCheckoutView.vue`. **magento-kwt** `custom-scripts/braze_events_cron.php` L1076 (evento `account_registered`). **magento-emd** BrazeEventBuilder L152, BrazeEventProcessors (account_registered). **microservices/shared/braze/events.go** `EventAccountRegistered = "account_registered"`. |

**Diferencia:** Mismo hecho (registro de cuenta). Magento envía `customer_registered` en tiempo real; cron/scripts y frontend envían o usan `account_registered`.

**Recomendación:** Consolidar en **`account_registered`** (más genérico y ya usado en frontend/Go). En **magento-kwt** y **magento-emd** cambiar en `Observer/Customer/RegisterSuccess.php` el nombre del evento de `customer_registered` a `account_registered`. Actualizar segmentos/triggers en Braze que usen `customer_registered` para que usen `account_registered`. Opcional: mantener ambos durante una transición y deprecar `customer_registered`.

---

### 1.4 logged_in / logged_into_portal / login / customer_logged_in

| Nombre | Dónde se usa |
|--------|----------------|
| **customer_logged_in** | **Magento (ambos)** Observer `Customer/Login.php` → evento enviado (en magento-kwt activo; en magento-emd **comentado**). |
| **logged_into_portal** | **kwilthealth.com** `useBrazeTracking.js` L226 `loggedIntoPortal` → `trackEvent('logged_into_portal', ...)`. Usado en LoginView u otros al entrar al portal. |
| **login** | **enhance.md-version1** `resources/js/components/themes/Amaze/Customer/Auth.vue` y `Intake/Auth.vue` → `window.braze.logCustomEvent('login', ...)` tras login exitoso. |

**Diferencia:**  
- `customer_logged_in` = login en **Magento** (storefront/API).  
- `logged_into_portal` = login en **portal** (kwilthealth.com).  
- `login` = login en **enhance.md-version1** (Laravel/Vue).

**Recomendación:** Consolidar en **`logged_into_portal`** para todos los logins de usuario en portales/app (un solo evento “usuario entró a su cuenta”). Cambiar en Magento el nombre de `customer_logged_in` a `logged_into_portal` (o mantener `customer_logged_in` solo para Magento y mapear en Braze a un concepto único). Cambiar en enhance.md-version1 de `login` a `logged_into_portal`. Así en Braze hay un solo evento de “login” para segmentos. Si se quiere distinguir origen, usar propiedad `source: 'magento' | 'portal' | 'enhance_v1'` en el mismo evento.

---

### 1.5 product_added_to_cart vs add_to_cart

| Nombre | Dónde se usa |
|--------|----------------|
| **product_added_to_cart** | **Magento (ambos)** Plugin `CartItemRepositoryPlugin.php` (al añadir ítem nuevo). **enhance.md-version1** `brazeEventTracker.js` L40 `trackToBraze('product_added_to_cart', ...)`. |
| **add_to_cart** | **kwilthealth.com** `useBrazeTracking.js` L186 `addToCart` → `trackEvent('add_to_cart', ...)`. **microservices/shared/braze/events.go** `EventAddToCart`. |

**Diferencia:** Mismo hecho (producto añadido al carrito). Magento y enhance.md-version1 usan `product_added_to_cart`; kwilthealth.com y Go usan `add_to_cart`.

**Recomendación:** Consolidar en **`product_added_to_cart`** (más descriptivo y alineado con `product_removed_from_wishlist`). En kwilthealth.com y en `microservices/shared/braze/events.go` cambiar a `product_added_to_cart`. Actualizar segmentos/triggers en Braze.

---

## 2. Atributos duplicados / sinónimos

La siguiente tabla indica **dónde está cada variante** en el código y qué nombre **mantener** o **eliminar**. En **magento-emd** ya existe un resumen en `custom-scripts/BRAZE_ATTRIBUTE_DOCUMENTATION.md` (sección "Duplicate Attributes to Consolidate"); aquí se añaden paths concretos.

### 2.1 Dirección

| Mantener | Eliminar / no usar | Dónde está la variante a eliminar |
|----------|---------------------|------------------------------------|
| **billing_address_line_2** | billing_address_line2 | **magento-emd** `braze_fix_data_v2.php` L968 `$attributes['billing_address_line2']`. **magento-kwt** no envía `billing_address_line2`; **magento-emd** `Observer/Subscription/SubscriptionGenerateSaveAfter.php` L363, `Observer/Customer/AddressSaveAfter.php` L87, `Observer/Sales/OrderPlaceAfter.php` L308 L371, `Cron/OrderShipped.php` L215, `Cron/SyncOrdersToBraze.php` L270 L295 L345 L353. **magento-emd** `braze_cron_job.php` L1640 usa `billing_address_line_2` (correcto). |
| **shipping_address_line_2** | shipping_address_line2 | **magento-emd** `braze_fix_data_v2.php` L947 `shipping_address_line2`. **magento-emd** observers/crons usan `shipping_address_line2` en varios archivos (SubscriptionGenerateSaveAfter L334, AddressSaveAfter L70, OrderPlaceAfter L285 L359, OrderShipped L215, SyncOrdersToBraze L270 L345). **BrazeEventBuilder.php**, **BrazeDbQueries.php**, **BrazeEventProcessors.php** usan `shipping_address_line_2`. **magento-emd** `braze_cron_job.php` L1620 usa `shipping_address_line_2` (correcto). |

**Recomendación:** En todos los archivos que envían `billing_address_line2` o `shipping_address_line2`, cambiar a **`billing_address_line_2`** y **`shipping_address_line_2`**. Eliminar en Braze los atributos sin guion bajo si ya no se envían.

---

### 2.2 Cancelación / fechas

| Mantener | Eliminar / no usar | Dónde |
|----------|---------------------|--------|
| **subscription_cancel_date** | cancel_date | En el código revisado no aparece `cancel_date` como atributo Braze; sí `subscription_cancel_date` en documentación. Si existe `cancel_date` en Braze, dejar de enviarlo y usar solo `subscription_cancel_date`. |
| **date_of_renewal** | renewal_date | **CheckUpcomingRenewals.php** (ambos Magentos) envía tanto `renewal_date` (en propiedades del evento) como `days_until_renewal`; en attributes se usa `days_until_subscription_renewal`. Para el atributo de “fecha de próxima renovación” consolidar en **`date_of_renewal`** o **`subscription_next_billing`** (ya usado). En **magento-kwt** `braze_events_cron.php` L937 se envía `date_of_renewal` en evento. **CheckUpcomingRenewals** L185 envía `renewal_date` en event properties. Recomendación: atributo de perfil **`subscription_next_billing`** para “próxima fecha de cobro”; en eventos usar **`date_of_renewal`** en propiedades si se quiere. Eliminar duplicado `renewal_date` como atributo de perfil si existe. |
| **days_until_renewal** | days_until_subscription_renewal | **magento-kwt** y **magento-emd** `Cron/CheckUpcomingRenewals.php` envían **ambos**: L195 `days_until_renewal`, L207 `days_until_subscription_renewal`. Consolidar en **`days_until_renewal`** y dejar de enviar `days_until_subscription_renewal` en ese cron. |

---

### 2.3 Identidad y contacto

| Mantener | Eliminar / no usar | Dónde |
|----------|---------------------|--------|
| **magento_customer_id** | customer_id (como atributo de perfil Braze) | En Magento Braze los payloads usan `external_id` (magento_{id}); a veces se envían atributos con `customer_id` en **OrderPlaceAfter.php** L388 (en event properties). Para **atributo de perfil** usar **`magento_customer_id`** y no duplicar con `customer_id`. Revisar que ningún flujo envíe `customer_id` como atributo de perfil; si solo va en event properties, puede quedarse como está. |
| **email** | Email | Braze recomienda lowercase. Buscar en el código cualquier asignación a `Email` (mayúscula) y cambiar a **`email`**. |
| **sms** | SMS | Igual: usar **`sms`** en minúsculas. En Magento Braze ya se usa `sms` y `phone` en atributos. |

---

### 2.4 Cupón y descuento

| Mantener | Eliminar / no usar | Dónde |
|----------|---------------------|--------|
| **order_coupon** o **coupon** | No duplicar | **magento-kwt** OrderPlaceAfter envía `coupon` en event (L269) y `order_coupon` en attributes (L314). SyncOrdersToBraze envía `coupon` y `order_coupon`. **CouponManagementPlugin** envía `coupon_code` en propiedades del evento. Recomendación: **un solo nombre de atributo de perfil**: **`order_coupon`** (o **`coupon`**). En código: usar solo uno; p. ej. **`order_coupon`** para “cupón de la última orden” y en eventos usar `coupon_code` en properties. Eliminar envío de `coupon` como atributo si se usa `order_coupon`. |
| **order_discount** o **discount** | No duplicar | **magento-kwt** OrderPlaceAfter envía `discount` en event (L268) y `order_discount` en attributes (L313). SyncOrdersToBraze igual. Recomendación: **un solo atributo**: **`order_discount`** (o **`discount`**). Documentación emd sugiere mantener `discount`. Unificar en **`order_discount`** para claridad o **`discount`** para brevedad; dejar de enviar el otro. |

---

### 2.5 Video / consulta

| Mantener | Eliminar / no usar | Dónde |
|----------|---------------------|--------|
| **last_video_consultation_date** | last_video_consult_date | Buscar en el código cualquier `last_video_consult_date` y reemplazar por **`last_video_consultation_date`**. Si no se usa en el repo, solo existe en Braze, deprecar el antiguo. |

---

### 2.6 Orden

| Mantener | Eliminar / no usar | Dónde |
|----------|---------------------|--------|
| **order_id** y **order_number** | — | En Magento ambos se envían y a menudo tienen el **mismo valor** (increment_id). **order_id** = identificador de orden en eventos/atributos; **order_number** = número mostrado al usuario. Si en tu negocio son iguales, consolidar en **`order_id`** y dejar de enviar `order_number` como atributo duplicado. Si order_number puede ser distinto (ej. otro formato), mantener ambos con nombres claros. |

---

### 2.7 Links de portal / cuenta

| Mantener | Eliminar / no usar | Dónde |
|----------|---------------------|--------|
| **portal_link** | portal_url | **kwilthealth.com** usa `portal_url` en composable (L230) y `portal_link` en photoDetails (L318). **magento-kwt** braze_events_cron L938 `portal_link`; results_ready_to_braze `portal_link`. **magento-emd** BrazeEventBuilder usa `portal_link` y `portal_url` (L173). Recomendación: **un solo atributo** **`portal_link`** (URL al dashboard/portal). Dejar de enviar `portal_url`. |
| **account_login_link** | link_to_account_login | **kwilthealth.com** LiveFormPreview L902 `link_to_account_login`; useBrazeTracking L336 `link_to_account_login`. **magento-kwt** braze_events_cron L1115 `link_to_account_login`. **magento-emd** braze_fix_data_v2 L903 `account_login_link`; BrazeEventBuilder L155 `link_to_account_login`. Recomendación: consolidar en **`account_login_link`** y en todos los archivos cambiar `link_to_account_login` a `account_login_link`. |
| **manage_subscription_link** | — | Se usa en **CheckUpcomingRenewals.php** (magento-kwt L198) como atributo/link. No duplicar con `portal_link`; mantener **`manage_subscription_link`** para la URL específica de gestionar suscripción. |

---

### 2.8 Login / sesión

| Mantener | Eliminar / no usar | Dónde |
|----------|---------------------|--------|
| **magento_last_login** | date_logged_in, logged_into_portal_ids | **kwilthealth.com** useBrazeTracking L229 envía `date_logged_in` en propiedades del evento `logged_into_portal`. Para **atributo de perfil** “última vez que entró”, usar **`magento_last_login`** (o un nombre genérico `last_login_at`) y no duplicar con `date_logged_in`. Si `date_logged_in` solo va en event properties, puede quedarse. `logged_into_portal_ids` (si existe): evaluar si es necesario; si es solo para dedup, no exponer como atributo de perfil. |

---

### 2.9 Intake

| Mantener | Eliminar / no usar | Dónde |
|----------|---------------------|--------|
| **last_intake_name** | latest_intake_name | Buscar en el código `latest_intake_name`; reemplazar por **`last_intake_name`**. |
| **last_intake_link** | latest_intake_link | Igual: reemplazar **`latest_intake_link`** por **`last_intake_link`**. |
| **intake_complete** (boolean) | latest_intake_complete | Si existe `latest_intake_complete`, consolidar en **`intake_complete`**. En **emd-upcoming-orders** journey.go se usa el concepto `intake_complete` como etapa; para atributo Braze usar **`intake_complete`**. |

---

### 2.10 Cancelación suscripción

| Mantener | Eliminar / no usar | Dónde |
|----------|---------------------|--------|
| **subscription_cancel_reason** o **cancellation_reason** | — | **enhance.md** y **enhance.md-version1** composables envían **`cancellation_reason`** en eventos (subscriptionCancelled). **magento-emd** BRAZE_ATTRIBUTE_DOCUMENTATION indica que ambos son “Same as subscription_cancel_reason”. Recomendación: **un solo nombre** **`cancellation_reason`** (más corto). En Magento/scripts que envíen `subscription_cancel_reason` como atributo, mantener ese nombre o cambiar todo a **`cancellation_reason`** y dejar de usar `subscription_cancel_reason`. |

---

### 2.11 Plan / frecuencia suscripción

| Mantener | Eliminar / no usar | Dónde |
|----------|---------------------|--------|
| **plan_length** | last_plan_length (como duplicado) | **magento-kwt** SubscriptionGenerateSaveAfter envía `subscription_frequency` y `last_plan_length` (L175, L180) y `plan_length` (L339). SyncOrdersToBraze L251 L304 L340 L364 `plan_length` y `subscription_frequency`. Recomendación: **atributo de perfil** para “duración del plan actual” usar **`plan_length`** (string ej. "1 month") y dejar de enviar **`last_plan_length`**. |
| **product_plan** | — | Mantener para “nombre del plan” (ej. "1 Month Supply"). No eliminar. |
| **subscription_frequency** | — | Usado en SyncOrdersToBraze y otros como “frecuencia” (ej. "1 month"). Puede ser sinónimo de `plan_length` en muchos casos. Recomendación: **un solo atributo** **`plan_length`** para “1 month”, “3 month”, etc.; dejar de enviar **`subscription_frequency`** si siempre tiene el mismo valor que plan_length. Si en algún flujo tienen significados distintos, documentar y mantener ambos. |

---

## 3. Resumen de acciones recomendadas

### Eventos

1. **checkout_started / started_checkout** → Unificar en **`checkout_started`**. Cambiar kwilthealth.com y `microservices/shared/braze/events.go`.
2. **subscription_renewal / upcoming_subscription_renewal** → Mantener ambos (significados distintos). Documentación: usar `subscription_renewal` y no `subscription_renewed` en código.
3. **customer_registered / account_registered** → Unificar en **`account_registered`**. Cambiar Magento RegisterSuccess.
4. **customer_logged_in / logged_into_portal / login** → Unificar en **`logged_into_portal`** (o mantener un solo nombre estándar y añadir property `source`). Cambiar Magento Login y enhance.md-version1.
5. **product_added_to_cart / add_to_cart** → Unificar en **`product_added_to_cart`**. Cambiar kwilthealth.com y Go.

### Atributos

1. **billing_address_line_2** / shipping_address_line_2 → Usar siempre con guion bajo; reemplazar `billing_address_line2` y `shipping_address_line2` en magento-emd (observers, crons, braze_fix_data_v2).
2. **subscription_cancel_date** → Usar solo este; no `cancel_date`.
3. **days_until_renewal** → Unificar; dejar de enviar `days_until_subscription_renewal` en CheckUpcomingRenewals.
4. **email**, **sms** → Siempre minúsculas; no `Email`, `SMS`.
5. **order_coupon** o **coupon** → Elegir uno para atributo de perfil (ej. `order_coupon`) y no duplicar.
6. **order_discount** o **discount** → Elegir uno (ej. `order_discount`) y no duplicar.
7. **portal_link** → Unificar; dejar de enviar `portal_url`.
8. **account_login_link** → Unificar; reemplazar `link_to_account_login` en todos los archivos.
9. **magento_last_login** → Para “último login”; no duplicar con `date_logged_in` como atributo de perfil.
10. **last_intake_name**, **last_intake_link**, **intake_complete** → Preferir estos; no `latest_*` ni `latest_intake_complete`.
11. **cancellation_reason** o **subscription_cancel_reason** → Elegir uno (ej. `cancellation_reason`) y usar en todos los flujos.
12. **plan_length** y **product_plan** → Mantener; dejar de enviar **last_plan_length**; evaluar si **subscription_frequency** puede sustituirse por **plan_length**.

---

## 4. Archivos a tocar (referencia rápida)

- **Eventos:**  
  - kwilthealth.com: `src/composables/useBrazeTracking.js`, `CheckoutView.vue`, `CartView.vue`.  
  - microservices: `shared/braze/events.go`.  
  - magento-kwt / magento-emd: `Enhance/Braze/Observer/Customer/Login.php`, `RegisterSuccess.php`; `Plugin/ShippingInformationManagementPlugin.php`; `Plugin/CartItemRepositoryPlugin.php` (no cambiar nombre, ya product_added_to_cart).  
  - enhance.md-version1: `brazeEventTracker.js`, `Auth.vue` (Customer e Intake).

- **Atributos:**  
  - magento-emd: `app/code/Enhance/Braze/Observer/*.php`, `Cron/*.php`; `custom-scripts/braze_fix_data_v2.php`, `braze_cron_job.php`, `braze_helpers/BrazeEventBuilder.php`, `BrazeEventProcessors.php`, `BrazeDbQueries.php`; `braze_sync_all.php`, `braze_sync_user.php`, `braze_sync_by_email.php`.  
  - magento-kwt: `Enhance/Braze/Observer/Sales/OrderPlaceAfter.php`, `Cron/SyncOrdersToBraze.php`, `Cron/CheckUpcomingRenewals.php`, `Observer/Subscription/SubscriptionGenerateSaveAfter.php`.  
  - kwilthealth.com: `useBrazeTracking.js`, `LiveFormPreview.vue`.

Documentación existente en **magento-emd**: `custom-scripts/BRAZE_ATTRIBUTE_DOCUMENTATION.md` (sección "Duplicate Attributes to Consolidate" y "Attributes NOT IN USE"). Conviene alinear este documento con esa guía tras aplicar los cambios de código.
