# Reporte rápido: duplicados de eventos y atributos Braze

Resumen de eventos y atributos que significan lo mismo en el codebase (excl. docs, porting analysis, events.md). Incluye dónde se usan, diferencia (si la hay) y recomendación de consolidación.

---

## Criterio: valor de verdad y dónde consolidar (front vs backend)

Al consolidar duplicados no debe asumirse que **todo** se unifica en frontend. Para cada par hay que decidir:

- **Nombre canónico** en Braze (un solo nombre de evento/atributo).
- **Dónde vive la “verdad” de negocio**: si el hecho lo confirma mejor el **backend** (BD, transacción real) o el **frontend** (acción del usuario en UI). Eso define qué origen es **fuente de verdad** para métricas, dedup y reportes.
- **Consolidar en front vs backend** según ese análisis: a veces conviene que el evento “oficial” lo emita solo el backend (más fiable); otras veces el frontend es el único que tiene el dato o lo tiene antes; en otros casos ambos emiten con el mismo nombre pero se documenta cuál se usa para conteos.

En cada sección de eventos duplicados se indica explícitamente **si consolidar en front, en backend o ambos (con dueño claro)** y el **por qué** desde valor de verdad y negocio.

---

## 1. Eventos duplicados / equivalentes

### 1.1 `started_checkout` vs `checkout_started`

| Variante             | Dónde se usa                                                                                                                                                  | Notas                                                                       |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| **started_checkout** | enhance.md-version1 (UserCheckout.vue, Payment.vue), kwilthealth.com (CheckoutView, CartView, CartView.vue, `useBrazeTracking.js`), microservices (events.go) | Evento enviado desde **frontend** (Vue/microservicios) al iniciar checkout. |
| **checkout_started** | magento-kwt, magento-emd: `ShippingInformationManagementPlugin.php` (al guardar dirección de envío en checkout)                                               | Evento enviado desde **backend Magento** (plugin).                          |

**Parámetros actuales:**

- **started_checkout (frontend, Braze JS / composables):**
  - Variantes de payload:
  - `email`, `SMS`/`sms`, `product_name` (string o array), `product_sku` (a veces), `product_plan`, `product_image`, `product_price`, `product_url`, `currency`, `timestamp`.
  - En algunos flujos solo se envía `email`, `sms`, `product_name`, `product_plan`.
- **checkout_started (Magento plugin):**
  - `quote_id`, `store_id`, `grand_total`, `items_count` (propiedades de carrito/quote Magento).

**Código actual (ejemplos simplificados):**

```js
// Frontend (actual) – enhance.md-version1 / kwilthealth.com
window.braze.logCustomEvent('started_checkout', {
  email: user.email,
  SMS: user.sms,
  product_name: productNames,
  product_plan: productPlans,
  currency: 'USD',
  timestamp: new Date().toISOString()
});
```

```php
// Magento (actual) – ShippingInformationManagementPlugin.php
$event = [
    'external_id' => $externalId,
    'name'        => 'checkout_started',
    'time'        => date('c'),
    'properties'  => [
        'quote_id'    => $quote->getId(),
        'store_id'    => $quote->getStoreId(),
        'grand_total' => $quote->getGrandTotal(),
        'items_count' => $quote->getItemsCount(),
    ],
];
```

**Código sugerido (unificación en `checkout_started`):**

```js
// Frontend (sugerido) – usar el mismo nombre que Magento
window.braze.logCustomEvent('checkout_started', {
  email: user.email,
  SMS: user.sms,
  product_name: productNames,
  product_plan: productPlans,
  currency: 'USD',
  timestamp: new Date().toISOString()
});
```

```go
// Microservices (sugerido) – nombre canónico
const EventCheckoutStarted = "checkout_started"
```

**¿Dónde consolidar (front vs backend) y por qué?**

| Criterio | Frontend | Backend (Magento) |
|----------|----------|-------------------|
| **Valor de verdad** | Dispara al **entrar** a la página de checkout (intención temprana). | Dispara al **guardar dirección de envío** en checkout (paso confirmado, carrito persistido). |
| **Conteo / negocio** | Puede inflar si el usuario abandona sin guardar. | Refleja un paso real completado (más fiable para funnel). |
| **Payload** | Rico en producto/contacto (marketing). | Rico en quote/carrito (IDs, totales desde BD). |

**Recomendación:** Nombre canónico **`checkout_started`**. **Consolidar la fuente de verdad en backend (Magento)**: el evento que cuenta para métricas de “inicio de checkout” debería ser el del plugin (usuario guardó dirección). El frontend puede seguir enviando un evento con el **mismo nombre** `checkout_started` en el paso anterior (landing a checkout) para contexto temprano, pero documentar que para reportes y segmentos estrictos se use el origen backend, o bien desactivar el envío frontend en rutas donde Magento ya dispara para evitar duplicados. No asumir “todo en front”: aquí el backend tiene mayor valor de verdad.

**Conclusión de parámetros:** No son equivalentes: **frontend** envía contexto de producto/usuario, el **backend** envía contexto de quote/carrito. Si se unifica el nombre en Braze, hay que decidir un **superset de propiedades** o normalizar a un esquema común (por ejemplo, siempre enviar `product_*` + `quote_id` cuando exista).  
**Diferencia conceptual:** Mismo concepto (usuario inició checkout). Origen distinto: frontend vs backend y distinto shape de payload.  
**Recomendación:** Unificar **nombre** en **`checkout_started`** en todos los orígenes. **Fuente de verdad para negocio:** backend (Magento). Actualizar frontend y microservices al mismo nombre; decidir si frontend sigue enviando (con mismo nombre) o se deja solo backend según necesidad de “checkout iniciado temprano” vs evitar duplicados.

---

### 1.2 `subscription_renewal` / `upcoming_subscription_renewal` / `subscription_renewed`

| Variante                          | Dónde se usa                                                                                                                   | Significado                                                                 |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------- |
| **subscription_renewal**          | magento-kwt/emd: `SubscriptionGenerateSaveAfter.php` (cuando se genera un renewal/orden de renovación)                         | Evento: **renovación ejecutada** (orden creada).                            |
| **upcoming_subscription_renewal** | magento-kwt/emd: cron `CheckUpcomingRenewals.php`, custom scripts (braze_events_cron, BrazeEventBuilder, BrazeEventProcessors) | Evento: **recordatorio** de que la renovación se acerca (días hasta renew). |
| **subscription_renewed**          | No encontrado como nombre de evento en el codebase                                                                             | —                                                                           |

**Diferencia:**

- `subscription_renewal` = renovación ya ocurrida (order/renewal generado).  
- `upcoming_subscription_renewal` = aviso previo (ej. “renewal en X días”).

**Código actual (ejemplos simplificados):**

```php
// subscription_renewal – Magento observer SubscriptionGenerateSaveAfter
$event = [
    'external_id' => $externalId,
    'name'        => 'subscription_renewal',
    'time'        => date('c', strtotime($renewalDate)),
    'properties'  => [
        'subscription_id' => $subscription->getId(),
        'date_of_renewal' => $dateOfRenewal,
    ],
];
```

```php
// upcoming_subscription_renewal – cron CheckUpcomingRenewals.php
$event = [
    'external_id' => $externalId,
    'name'        => 'upcoming_subscription_renewal',
    'time'        => date('c'),
    'properties'  => [
        'subscription_id'                 => $subscriptionId,
        'renewal_date'                    => $nextRunDate,
        'days_until_subscription_renewal' => $daysUntilRenewal,
    ],
];
```

**Código sugerido:**

- Mantener **dos eventos distintos** con sus payloads tal como arriba.  
- Si en Braze existe un alias `subscription_renewed`, mapearlo lógicamente a `subscription_renewal` (no crear un tercer nombre en código).

**¿Dónde consolidar (front vs backend)?** No aplica: ambos eventos son **solo backend** (observers Magento y crons). No hay duplicado front/back; son dos momentos de negocio distintos (renovación ejecutada vs próximo renewal). Mantener ambos nombres.

---

### 1.3 `customer_registered` vs `account_registered`

| Variante                | Dónde se usa                                                                                                                                                                                                                                                              | Notas                                                          |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| **customer_registered** | magento-kwt, magento-emd: `Enhance/Braze/Observer/Customer/RegisterSuccess.php`                                                                                                                                                                                           | Backend Magento: registro exitoso de cliente.                  |
| **account_registered**  | enhance.md-version1 (Auth.vue, `useBrazeTracking.js`), kwilthealth.com (RegisterView, LiveFormPreview, `useBrazeTracking.js`), magento-kwt (braze_events_cron.php), magento-emd (BrazeEventBuilder, BrazeEventProcessors, braze_sync_by_email), microservices (events.go) | Frontend + scripts/cron emd: mismo hecho (registro de cuenta). |

**Parámetros actuales:**

- **customer_registered (Magento observer):**
  - `properties` típicas: `source`, `store_id`, `website_id`, `email`, `first_name`, `last_name`, `dob`, `gender`, `sms`, etc.
- **account_registered (frontend enhance.md-version1 / kwilthealth.com):**
  - `customer_id`, `first_name`, `last_name`, `email`, `SMS`/`sms`, `link_to_account_login`.
- **account_registered (scripts/crons Magento):**
  - Mínimo: `email`, `sms` y a veces `registration_source`, `link_to_account_login`.

**Conclusión de parámetros:** Todos representan la **misma acción de registro**, pero el conjunto de propiedades no es idéntico: el observer Magento tiene payload más rico; algunos flujos de frontend solo envían `email/sms/login_link`.  
**Diferencia conceptual:** Mismo evento de negocio, con distintos orígenes y nivel de detalle.  
**Código actual (ejemplos simplificados):**

```php
// Magento (actual) – Customer/RegisterSuccess observer
$event = [
    'external_id' => $externalId,
    'name'        => 'customer_registered',
    'time'        => date('c'),
    'properties'  => [
        'source'     => 'magento',
        'store_id'   => $customer->getStoreId(),
        'email'      => $customer->getEmail(),
        'first_name' => $customer->getFirstname(),
        'last_name'  => $customer->getLastname(),
    ],
];
```

```js
// Frontend (actual) – enhance.md-version1 Auth.vue
window.braze.logCustomEvent('account_registered', {
  customer_id: res.data.customer_id,
  first_name: formData.fname,
  last_name: formData.lname,
  email: decodedEmailForEvent,
  SMS: eventPhone
});
```

**Código sugerido (unificar en `account_registered`):**

```php
// Magento (sugerido) – cambiar nombre del evento
$event = [
    'external_id' => $externalId,
    'name'        => 'account_registered',
    'time'        => date('c'),
    'properties'  => [
        'registration_source'  => 'magento',
        'customer_id'          => $customer->getId(),
        'email'                => $customer->getEmail(),
        'first_name'           => $customer->getFirstname(),
        'last_name'            => $customer->getLastname(),
        'link_to_account_login'=> ACCOUNT_LOGIN_LINK,
    ],
];
```

**¿Dónde consolidar (front vs backend) y por qué?**

| Criterio | Frontend | Backend (Magento) |
|----------|----------|-------------------|
| **Valor de verdad** | Dispara tras submit del formulario de registro (puede haber race con la creación en BD). | Dispara cuando el cliente **ya está creado** en BD (observer `customer_register_success`). |
| **Conteo / negocio** | Riesgo de contar intentos o dobles si hay retries. | Un registro = un cliente creado; **fuente de verdad** clara. |
| **Payload** | A menudo mínimo (email, nombre, link). | Perfil completo (store, website, dob, gender, etc.). |

**Recomendación:** Nombre canónico **`account_registered`**. **Consolidar la fuente de verdad en backend (Magento)**: el evento que cuenta para “registros” y cohortes debería ser el del observer de registro exitoso. El frontend puede seguir enviando `account_registered` para inmediatez en Canvas/trigger, pero para métricas y reportes usar el origen backend. Cambiar en Magento el **nombre** del evento de `customer_registered` a `account_registered` (manteniendo backend como dueño del hecho). No consolidar “en front”: el backend es quien confirma el registro real.

**Recomendación (resumen):** Consolidar **nombre** en **`account_registered`**. **Fuente de verdad:** backend (Magento). Cambiar observer RegisterSuccess a enviar `account_registered`; armonizar payload mínimo: `customer_id`, `email`, `sms`, `first_name`, `last_name`, `registration_source`, `link_to_account_login`.

---

### 1.4 `logged_in` / `logged_into_portal` / `login` / `customer_logged_in`

| Variante               | Dónde se usa                                                                                                                                                                                                                                          | Notas                                                          |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| **customer_logged_in** | magento-kwt: `Enhance/Braze/Observer/Customer/Login.php` (activo). magento-emd: mismo observer pero **comentado**                                                                                                                                     | Solo Magento; “login como cliente”.                            |
| **logged_into_portal** | enhance.md-version1 (LoginRegister.vue, Intake/Auth.vue, Customer/Auth.vue, `useBrazeTracking.js`), kwilthealth.com (LoginView, services/login.js, `useBrazeTracking.js`), magento-emd (BrazeEventBuilder, BrazeEventProcessors, braze_sync_by_email) | Frontend + cron/scripts: login en portal.                      |
| **logged_in**          | magento-emd: atributos de tracking (`logged_in_sent`) y claves internas                                                                                                                                                                               | Uso interno (dedup), no como nombre de evento enviado a Braze. |
| **login**              | Uso genérico (rutas, formularios, recaptcha action); no como evento Braze                                                                                                                                                                             | No es evento Braze.                                            |

**Parámetros actuales:**

- **customer_logged_in (Magento observer):**
  - `customer_id`, `email`, `store_id`, `website_id` (y potencialmente más metadatos de cliente).
- **logged_into_portal (frontend / composables / crons):**
  - Siempre incluyen al menos: `email`, `SMS`/`sms`, `date_logged_in`, `portal_url`.
  - En emd (buildLoggedInEvent) se usa el mismo esquema (`date_logged_in`, `portal_url`, `email`, `SMS`).

**Código actual (ejemplos simplificados):**

```php
// Magento (actual) – Customer/Login observer
$event = [
    'external_id' => $externalId,
    'name'        => 'customer_logged_in',
    'time'        => date('c'),
    'properties'  => [
        'customer_id' => $customer->getId(),
        'email'       => $customer->getEmail(),
    ],
];
```

```js
// Frontend (actual) – LoginRegister.vue
window.braze.logCustomEvent('logged_into_portal', {
  email: res.data.email || '',
  SMS: e164Sms,
  date_logged_in: new Date().toISOString(),
  portal_url: window.location.origin + '/customer/myaccount'
});
```

**Código sugerido (unificar en `logged_into_portal`):**

```php
// Magento (sugerido) – usar mismo nombre que frontend
$event = [
    'external_id' => $externalId,
    'name'        => 'logged_into_portal',
    'time'        => date('c'),
    'properties'  => [
        'customer_id'    => $customer->getId(),
        'email'          => $customer->getEmail(),
        'date_logged_in' => date('c'),
        'portal_url'     => PORTAL_LINK,
    ],
];
```

**¿Dónde consolidar (front vs backend) y por qué?**

| Criterio | Frontend | Backend (Magento) / Crons |
|----------|----------|----------------------------|
| **Valor de verdad** | Dispara en el momento del login en UI (inmediato). | Magento: cuando la sesión de cliente se crea realmente. Crons: leen `last_login` de BD (histórico). |
| **Conteo / negocio** | Bueno para “acaba de entrar” (triggers). | Backend/cron confirman que el login existió en sistema; mejor para “última vez que entró” y reportes. |
| **Payload** | `date_logged_in`, `portal_url`, email, sms. | Magento: customer_id, email; crons: mismo esquema desde BD. |

**Recomendación:** Nombre canónico **`logged_into_portal`**. **Consolidar la fuente de verdad en backend**: cuando Magento dispare el evento (observer Login), que use el nombre `logged_into_portal` y sea la fuente de verdad para “login en tienda”; en portales/crons que ya envían `logged_into_portal`, el backend (crons que leen last_login) puede ser fuente de verdad para backfill. Frontend puede seguir enviando para inmediatez. No asumir “solo front”: el backend (Magento o crons) aporta la confirmación de que el login ocurrió en sistema.

**Conclusión de parámetros:** Ambos eventos describen el **mismo login**, pero el payload de `customer_logged_in` está orientado a IDs Magento y el de `logged_into_portal` a telemetría de portal (email/sms/fecha/url).  
**Recomendación (resumen):** Unificar **nombre** en **`logged_into_portal`**. **Fuente de verdad:** backend (Magento cuando activo, o crons desde BD). Cambiar observer Login a `logged_into_portal`; homogeneizar payload mínimo: `email`, `sms`, `date_logged_in`, `portal_url`.

---

### 1.5 `product_added_to_cart` vs `add_to_cart`

| Variante                  | Dónde se usa                                                                                                                                                                                                                                                                           | Notas                              |
| ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------- |
| **product_added_to_cart** | magento-kwt, magento-emd: `Enhance/Braze/Plugin/CartItemRepositoryPlugin.php` (al añadir/actualizar ítem en carrito)                                                                                                                                                                   | Backend Magento.                   |
| **add_to_cart**           | enhance.md-version1 (UserCartDetails, SelectMedication, MedicalInformation), kwilthealth.com (ProductDetails, `useBrazeTracking.js`, MembershipPayment.vue, LiveFormPreview.vue), magento-emd (BrazeEventProcessors comentado, BrazeEventBuilder comentado), microservices (events.go) | Frontend y referencias en scripts. |

**Parámetros actuales:**

- **product_added_to_cart (Magento plugin, cuando está habilitado):**
  - Payload típico de Magento: `product_id`/`sku`, `name`, `qty`, `price`, posiblemente `plan_length`/`product_plan`, `quote_id` y metadatos de carrito.
- **add_to_cart (frontend / composables):**
  - En enhance.md-version1: `email`, `SMS`/`sms`, `product_name`, `product_sku`, `product_image`, `product_price`, `plan_length`/`product_plan`, `currency`, `quantity`, `timestamp`.
  - En kwilthealth.com: al menos `email`, `sms`, `product_name`, `product_image`, `product_price`, `product_plan`, más flags como `add_to_cart_success`, `default_payment`, `address{...}` en algunos flujos.

**Código actual (ejemplos simplificados):**

```php
// Magento (actual) – CartItemRepositoryPlugin.php
$eventName = $isUpdate ? 'cart_updated' : 'product_added_to_cart';

$event = [
    'external_id' => $externalId,
    'name'        => $eventName,
    'time'        => date('c'),
    'properties'  => [
        'product_sku' => $item->getSku(),
        'qty'         => $item->getQty(),
        'price'       => $item->getPrice(),
    ],
];
```

```js
// Frontend (actual) – SelectMedication.vue
window.braze.logCustomEvent('add_to_cart', {
  email: userEmail || '',
  SMS: formattedSMS || '',
  product_name: medication.title || '',
  product_sku: medication.sku || '',
  product_price: formattedPrice,
  currency: 'USD',
  quantity: 1,
  timestamp: new Date().toISOString()
});
```

**Código sugerido (unificar en `add_to_cart`):**

```php
// Magento (sugerido) – cambiar nombre del evento
$eventName = $isUpdate ? 'cart_updated' : 'add_to_cart';
```

```js
// Frontend (sugerido) – sin cambios de nombre, solo documentar esquema mínimo
window.braze.logCustomEvent('add_to_cart', {
  email: user.email,
  SMS: user.sms,
  product_name: product.name,
  product_sku: product.sku,
  product_plan: product.plan,
  product_price: product.price,
  quantity: product.qty,
});
```

**¿Dónde consolidar (front vs backend) y por qué?**

| Criterio | Frontend | Backend (Magento) |
|----------|----------|-------------------|
| **Valor de verdad** | Dispara al añadir ítem en UI (portal/Vue). En flujos solo-portal puede ser la **única** fuente. | Dispara cuando el ítem **ya está en el quote/carrito** en BD (CartItemRepository::save). |
| **Conteo / negocio** | En Magento: puede adelantarse o duplicar si backend también envía. En portal puro: es la verdad. | En Magento: refleja carrito real (fuente de verdad para “añadido al carrito” en tienda). |
| **Payload** | Rico en producto/imagen/plan (marketing). | Rico en sku, qty, price, quote_id (sistema). |

**Recomendación:** Nombre canónico **`add_to_cart`**. **Dónde consolidar depende del flujo:**
- **Donde exista Magento (tienda):** **Fuente de verdad = backend (Magento)**. El plugin confirma que el carrito se actualizó. Cambiar el nombre del evento en el plugin a `add_to_cart`; el frontend puede dejar de enviar el mismo evento en esa ruta para evitar duplicados, o enviar con el mismo nombre pero documentar que para métricas se usa el backend.
- **Flujos solo portal (sin carrito Magento):** la **fuente de verdad es el frontend** (no hay backend de carrito). Mantener envío frontend con nombre `add_to_cart`.

No consolidar “todo en front”: en tienda Magento el backend debe ser la referencia para “añadido al carrito” real.

**Conclusión de parámetros:** Representan el mismo hecho (“se añadió un producto al carrito”), pero con payloads distintos.  
**Recomendación (resumen):** Consolidar **nombre** en **`add_to_cart`**. **Fuente de verdad:** backend (Magento) en flujos con carrito Magento; frontend en flujos solo portal. Cambiar CartItemRepositoryPlugin a `add_to_cart`; documentar esquema mínimo (`product_name`, `product_sku`, `product_plan`, `product_price`, `email`, `sms`, `quantity`).

---

## 2. Atributos duplicados / equivalentes

### 2.1 `billing_address_line2` vs `billing_address_line_2`

| Variante                                    | Dónde se usa                                                                                                                            |
| ------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| **billing_address_line_2** (con guión bajo) | enhance.md-version1 (OrderConfirmation.vue), magento-emd: BrazeEventBuilder, braze_cron_job.php                                         |
| **billing_address_line2** (sin guión bajo)  | magento-emd: braze_fix_data_v2.php, OrderPlaceAfter.php, AddressSaveAfter.php, SubscriptionGenerateSaveAfter.php, SyncOrdersToBraze.php |

**Recomendación:** Unificar en **`billing_address_line_2`** (consistente con `shipping_address_line_2` y convención “line_2”). Reemplazar todas las ocurrencias de `billing_address_line2` por `billing_address_line_2` en Magento y scripts.

---

### 2.2 `shipping_address_line2` vs `shipping_address_line_2`

| Variante                    | Dónde se usa                                                                                                                          |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| **shipping_address_line_2** | enhance.md-version1 (OrderConfirmation.vue), magento-emd: BrazeDbQueries, BrazeEventBuilder, BrazeEventProcessors, braze_cron_job.php |
| **shipping_address_line2**  | magento-emd: braze_fix_data_v2.php, OrderPlaceAfter, AddressSaveAfter, SubscriptionGenerateSaveAfter, OrderShipped, SyncOrdersToBraze |

**Recomendación:** Unificar en **`shipping_address_line_2`**. Reemplazar `shipping_address_line2` por `shipping_address_line_2` en todos los archivos listados.

---

### 2.3 `cancel_date` vs `subscription_cancel_date`

| Variante                     | Dónde se usa                                                                                                                                                                                         | Notas                                                 |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| **cancel_date**              | magento-kwt/emd: observers (SubscriptionSaveAfter, SubscriptionStatusChange), eventos (subscription_canceled); magento-emd BrazeEventBuilder, BrazeEventProcessors; microservices (props en eventos) | En **eventos** (propiedad del evento de cancelación). |
| **subscription_cancel_date** | magento-emd: atributos de usuario (braze_sync_by_email, braze_fix_data_v2, braze_cron_job, BrazeEventProcessors); microservices (attributes.go, kwilt-order, kwilt-myaccount)                        | Como **atributo de perfil** de usuario en Braze.      |

**Diferencia:** `cancel_date` suele ser propiedad de evento; `subscription_cancel_date` es atributo de usuario (fecha de cancelación de la suscripción).  
**Recomendación:** Mantener **`subscription_cancel_date`** solo para el **atributo de perfil**. En payloads de eventos se puede seguir usando `cancel_date` para la fecha de ese evento. Si se quiere un solo nombre en Braze para el perfil, usar solo `subscription_cancel_date` y no duplicar con otro nombre.

---

### 2.4 `customer_id` vs `magento_customer_id`

| Variante                | Dónde se usa                                                                                                                                                                                 |
| ----------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **customer_id**         | Uso masivo: respuesta de APIs, BD, modelos, payloads internos (no siempre como atributo Braze). En Braze: enhance.md-version1 (Auth.vue) en payload de eventos (customer_id en propiedades). |
| **magento_customer_id** | No encontrado como atributo Braze en el codebase.                                                                                                                                            |

**Recomendación:** Para **atributo de usuario en Braze**, definir uno solo: p. ej. **`magento_customer_id`** (o `customer_id` si Braze ya lo usa así) y documentarlo. El `external_id` ya es `magento_{customerId}`; si se necesita el ID como atributo, usar un único nombre en todos los envíos.

---

### 2.5 `email` vs `Email` (case)

En Braze los atributos son case-sensitive. En el codebase:

- **Minúscula `email`:** mayoritario (Magento observers, microservices models JSON `"email"`, frontend).
- **Mayúscula `Email`:** solo en mensajes de validación/labels (ej. `'email': 'Email'` en VeeValidate), no como clave de atributo Braze.

**Recomendación:** Usar siempre **`email`** (minúscula) como atributo Braze. No usar `Email` como clave en `/users/track`.

---

### 2.6 `SMS` vs `sms`

| Variante            | Dónde se usa                                                                                                                                  |
| ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| **sms** (minúscula) | magento-kwt (todos los observers y crons), microservices (models.go y eventos: `"sms"` en JSON)                                               |
| **SMS** (mayúscula) | magento-emd: BrazeEventBuilder.php, BrazeEventProcessors.php, braze_sync_all.php, braze_cron_job.php, ShippingInformationManagementPlugin.php |

**Recomendación:** Unificar en **`sms`** (minúscula) para coincidir con Magento KWT y microservices. Cambiar en magento-emd (BrazeEventBuilder, BrazeEventProcessors, braze_sync_all, braze_cron_job, plugin) de `'SMS'` a `'sms'`.

---

### 2.7 `coupon` / `coupon_code` / `order_coupon`

| Variante         | Dónde se usa (como atributo/event property Braze)                                                                                                                                |
| ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **coupon**       | magento-kwt/emd: OrderPlaceAfter (event properties), SubscriptionGenerateSaveAfter; magento-emd: braze_fix_data_v2, braze_cron_job (atributo usuario).                           |
| **coupon_code**  | magento-kwt/emd: CouponManagementPlugin (event properties), SyncOrdersToBraze (lee BD); enhance.md-version1, kwilthealth.com (payloads). Frontend y plugin envían `coupon_code`. |
| **order_coupon** | magento-kwt/emd: OrderPlaceAfter y SyncOrdersToBraze como **atributo** de usuario (último cupón de orden).                                                                       |

**Diferencia:** En eventos (apply/remove coupon, order) se usa `coupon_code` o `coupon`; como atributo de “último cupón usado” en Magento a veces `order_coupon` y en otros sitios `coupon`.  
**Recomendación:**

- En **eventos**: usar **`coupon_code`** (claro y ya usado en frontend/plugin).
- En **atributos de perfil** (último cupón/orden): usar **`order_coupon`** o **`coupon`** de forma única; elegir uno (ej. **`order_coupon`**) y reemplazar el otro en magento-emd (braze_fix_data_v2, braze_cron_job) y en Magento observers si envían atributo de cupón.

---

### 2.8 `discount` vs `order_discount`

| Variante           | Dónde se usa                                                                                                                                                                          |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **discount**       | magento-kwt/emd: OrderPlaceAfter (event properties y atributos), SubscriptionGenerateSaveAfter; magento-emd: BrazeEventBuilder, braze_fix_data_v2, braze_cron_job (atributo usuario). |
| **order_discount** | magento-kwt/emd: OrderPlaceAfter y SyncOrdersToBraze como **atributo** de usuario (discount amount en orden).                                                                         |

**Recomendación:** Unificar en **`order_discount`** para el atributo de perfil (monto de descuento de la orden), para no confundir con descuento en evento. En propiedades de evento `order_placed` se puede mantener `discount`; para atributo de usuario usar solo **`order_discount`** y eliminar `discount` de atributos en braze_fix_data_v2 y braze_cron_job si hoy se envían ambos.

---

### 2.9 `last_video_consult_date` vs `last_video_consultation_date`

| Variante                         | Dónde se usa                                              |
| -------------------------------- | --------------------------------------------------------- |
| **last_video_consult_date**      | magento-emd: BrazeEventProcessors.php (atributo usuario). |
| **last_video_consultation_date** | magento-emd: braze_fix_data_v2.php, braze_cron_job.php.   |

**Recomendación:** Unificar en **`last_video_consultation_date`** (más explícito). Cambiar BrazeEventProcessors para escribir `last_video_consultation_date` en lugar de `last_video_consult_date`.

---

### 2.10 `date_of_renewal` vs `renewal_date`

| Variante            | Dónde se usa                                                                                                                                                                  |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **date_of_renewal** | magento-kwt/emd: SubscriptionGenerateSaveAfter, CheckUpcomingRenewals, BrazeEventBuilder, BrazeEventProcessors, braze_fix_data_v2, braze_cron_job; microservices (models.go). |
| **renewal_date**    | magento-kwt: braze_events_cron (query y propiedades de evento); magento-emd: CheckUpcomingRenewals (propiedades de evento upcoming).                                          |

**Recomendación:** Para **atributo de usuario** y **propiedad de evento** de renovación usar un solo nombre: **`date_of_renewal`**. Donde se use `renewal_date` en payloads a Braze (braze_events_cron, CheckUpcomingRenewals), cambiar a `date_of_renewal` para consistencia.

---

### 2.11 `days_until_renewal` vs `days_until_subscription_renewal`

| Variante                            | Dónde se usa                                                                    |
| ----------------------------------- | ------------------------------------------------------------------------------- |
| **days_until_renewal**              | magento-kwt/emd: CheckUpcomingRenewals (propiedades de evento).                 |
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

| Variante                     | Uso típico                                                                                                 |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------- |
| **portal_link**              | URL al portal/dashboard (fotos, sync, eventos, microservices).                                             |
| **portal_url**               | URL al portal/dashboard (enhance.md-version1, kwilthealth.com en logged_into_portal / account_registered). |
| **link_to_account_login**    | URL a login (enhance.md-version1, kwilthealth.com, magento-kwt braze_events_cron).                         |
| **account_login_link**       | magento-emd: braze_fix_data_v2, braze_cron_job (atributo usuario).                                         |
| **manage_subscription_link** | magento-kwt/emd: CheckUpcomingRenewals (link a gestionar suscripción).                                     |

**Recomendación:**

- **`portal_link`** = URL principal del portal/dashboard (un solo nombre; deprecar `portal_url` como atributo Braze y mapear a `portal_link`).
- **`account_login_link`** = URL de login (unificar con `link_to_account_login` en **`account_login_link`**).
- **`manage_subscription_link`** = mantener para link específico de suscripción.  
  Acción: en frontend y scripts reemplazar `portal_url` por `portal_link` y `link_to_account_login` por `account_login_link` en atributos Braze.

---

### 2.14 `date_logged_in` / `magento_last_login` / `logged_into_portal_ids`

| Variante                   | Uso                                                                                                                         |
| -------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| **date_logged_in**         | Propiedad en evento `logged_into_portal` (frontend, BrazeEventBuilder).                                                     |
| **magento_last_login**     | Atributo de usuario (magento-emd: braze_sync_by_email, braze_sync_all, braze_sync_user, braze_fix_data_v2, braze_cron_job). |
| **logged_into_portal_ids** | Atributo interno de dedup (lista de IDs ya enviados) en magento-emd; no es el “last login”.                                 |

**Recomendación:**

- **Atributo de perfil “última fecha de login”:** unificar en **`magento_last_login`** (o `last_login_at` si se prefiere nombre genérico).
- **Propiedad de evento:** mantener **`date_logged_in`** en el evento `logged_into_portal`.
- **`logged_into_portal_ids`** es solo control interno; no cambiar nombre salvo por claridad interna.

---

### 2.15 `last_intake_name` vs `latest_intake_name` / `last_intake_link` vs `latest_intake_link`

| Variante               | Dónde se usa                                                          |
| ---------------------- | --------------------------------------------------------------------- |
| **last_intake_name**   | enhance.md-version1: MedicalInformation.vue (setCustomUserAttribute). |
| **latest_intake_name** | No encontrado en código.                                              |
| **last_intake_link**   | enhance.md-version1: MedicalInformation.vue.                          |
| **latest_intake_link** | No encontrado en código.                                              |

**Recomendación:** Mantener **`last_intake_name`** y **`last_intake_link`**. Si en Braze existen `latest_*`, migrar a `last_*` o documentar alias.

---

### 2.16 `latest_intake_complete` vs `intake_complete`

| Variante                   | Dónde se usa                                                                                                                                   |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| **intake_complete**        | magento-emd: braze_sync_by_email, braze_get_user, BrazeEventProcessors (atributo usuario); microservices kwilt-lab-ai, kwilt-dashboard-config. |
| **latest_intake_complete** | No encontrado.                                                                                                                                 |

**Recomendación:** Usar **`intake_complete`** como atributo de perfil. No introducir `latest_intake_complete` salvo que ya exista en Braze; en ese caso mapear a `intake_complete`.

---

### 2.17 `subscription_cancel_reason` vs `cancellation_reason`

| Variante                       | Uso                                                                                                                                                                                             |
| ------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **cancellation_reason**        | Propiedad en eventos (subscription_canceled, etc.); enhance.md-version1, enhance.md, kwilthealth.com (useBrazeTracking); magento-emd braze_fix_data_v2, braze_cron_job (también como atributo). |
| **subscription_cancel_reason** | Atributo de usuario en magento-emd (braze_sync_by_email, braze_fix_data_v2, braze_cron_job, BrazeEventProcessors); microservices (attributes).                                                  |

**Recomendación:** Para **atributo de perfil** usar **`subscription_cancel_reason`**. En **propiedades de evento** usar **`cancellation_reason`**. Dejar de enviar ambos nombres al mismo perfil; en braze_fix_data_v2 y braze_cron_job enviar solo `subscription_cancel_reason` como atributo y no duplicar con `cancellation_reason`.

---

### 2.18 `plan_length` / `last_plan_length` / `product_plan` / `subscription_frequency`

| Variante                   | Uso                                                                                                                                                                    |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **plan_length**            | Event properties y atributos (orden, suscripción, renewal, payment failed, etc.) en Magento y scripts.                                                                 |
| **last_plan_length**       | magento-kwt/emd: SubscriptionGenerateSaveAfter; magento-emd: braze_fix_data_v2, braze_cron_job (atributo usuario).                                                     |
| **product_plan**           | magento-kwt/emd: observers de suscripción, SyncOrdersToBraze; kwilthealth.com (checkout, cart); magento-emd scripts. A veces mismo valor que plan_length (frecuencia). |
| **subscription_frequency** | magento-kwt/emd: SubscriptionSaveAfter, SubscriptionGenerateSaveAfter, SyncSubscriptionsToBraze; magento-emd scripts y crons (atributo usuario).                       |

**Recomendación:**

- **Frecuencia de suscripción (ej. “4 week”):** unificar en **`subscription_frequency`** para atributo de perfil y en eventos donde se quiera un solo nombre.
- **Plan/producto (nombre o descripción):** usar **`product_plan`** en eventos y atributos cuando el valor sea “nombre del plan” o similar.
- **`plan_length`** y **`last_plan_length`:** a menudo el mismo valor; usar **`plan_length`** en eventos y **`subscription_frequency`** (o `plan_length`) para “último plan” en perfil, y eliminar **`last_plan_length`** si no aporta (o documentar que es alias de `plan_length` para el último periodo).

---

## 3. Resumen de acciones sugeridas

| Tema                 | Nombre canónico        | Fuente de verdad (front vs backend) | Acción                                                                                   |
| -------------------- | ---------------------- | ------------------------------------- | ----------------------------------------------------------------------------------------- |
| Checkout event       | `checkout_started`     | **Backend** (Magento, al guardar dirección) | Unificar nombre en todos; métricas/conteo basados en backend. Actualizar front y microservices al mismo nombre. |
| Registro             | `account_registered`   | **Backend** (Magento, registro exitoso)    | Cambiar observer RegisterSuccess a `account_registered`; backend = fuente para conteos.  |
| Login event          | `logged_into_portal`   | **Backend** (Magento o crons desde BD)      | Cambiar observer Login a `logged_into_portal`; backend/cron = fuente de verdad.         |
| Cart event           | `add_to_cart`          | **Backend** en Magento; **Frontend** en flujos solo portal | Cambiar plugin a `add_to_cart`; en tienda Magento usar backend para métricas.             |
| Direcciones          | —                      | —                                    | Usar `billing_address_line_2` y `shipping_address_line_2` en todos los envíos.             |
| SMS                  | —                      | —                                    | Usar `sms` (minúscula) en magento-emd.                                                     |
| Email                | —                      | —                                    | Usar `email` (minúscula) como atributo Braze.                                              |
| Cupón (atributo)     | —                      | —                                    | Unificar en `order_coupon` o `coupon`; evento `coupon_code`.                               |
| Descuento (atributo) | —                      | —                                    | Usar `order_discount` para perfil.                                                         |
| Video consult        | —                      | —                                    | Unificar en `last_video_consultation_date`.                                                |
| Renewal (días)       | —                      | —                                    | Unificar en `days_until_subscription_renewal`.                                             |
| Renewal (fecha)      | —                      | —                                    | Unificar en `date_of_renewal` en payloads Braze.                                           |
| Portal URLs          | —                      | —                                    | `portal_link`, `account_login_link`; deprecar `portal_url` y `link_to_account_login` en Braze. |
| Cancel reason        | —                      | —                                    | Atributo: `subscription_cancel_reason`; evento: `cancellation_reason`.                     |
| Plan/frequency       | —                      | —                                    | Atributo perfil: `subscription_frequency` (y opcionalmente `product_plan`); reducir uso de `last_plan_length`. |

---

_Generado a partir de búsquedas en repos: magento-kwt, magento-emd, system, microservices, secure-consult, old-secure-consult, kwilthealth.com, kt-feedback-service, enhance.md, enhance.md-version1. Excluidos: docs, porting analysis, events.md._
