# Respuesta a la tarea: Fix duplicate events

Este documento responde a la tarea de **fix duplicate events** que creaste, con la descripción que incluye los pares de eventos y atributos a revisar. Aquí se indica **qué hacemos con cada uno**: cuáles se **unifican** (y en qué nombre, y si la fuente de verdad queda en backend o en front), cuáles **se mantienen** tal cual porque no son duplicados sino conceptos distintos, y cuáles **se eliminan** (dejamos un solo nombre y el otro se deja de usar).

---

## Eventos de la tarea

De tu lista:  
`checkout_started` / `started_checkout` · `subscription_renewal` / `upcoming_subscription_renewal` / `subscription_renewed` · `customer_registered` / `account_registered` · `logged_in` / `logged_into_portal` / `login` · `product_added_to_cart` / `add_to_cart`

### 1. checkout_started y started_checkout

| Acción   | Nombre final en Braze | Fuente de verdad | Qué hacemos |
|----------|------------------------|------------------|-------------|
| **Unificar** | **checkout_started** | **Backend** (Magento, cuando el usuario guarda dirección en checkout) | Un solo evento. El backend es la referencia para métricas y conteos. Frontend puede seguir enviando el mismo nombre en el paso anterior (entrar a checkout) para contexto temprano, pero para reportes y segmentos se usa el del backend. Se deja de usar **started_checkout**. |

**Por qué:** El backend confirma un paso real completado (dirección guardada); el front solo indica “entró a la página”. Para no inflar ni duplicar, la verdad de negocio la tiene el backend. Unificar en un nombre evita tener que pensar en dos eventos en segmentos y funnels.

---

### 2. subscription_renewal, upcoming_subscription_renewal, subscription_renewed

| Acción    | Nombre(es) en Braze | Fuente de verdad | Qué hacemos |
|-----------|----------------------|------------------|-------------|
| **Mantener** | **subscription_renewal** y **upcoming_subscription_renewal** (dos eventos) | Backend (observers/crons) | No unificamos: son dos momentos distintos. **subscription_renewal** = renovación ya cobrada; **upcoming_subscription_renewal** = aviso de que la renovación se acerca. Si en Braze existe **subscription_renewed**, lo tratamos como equivalente a **subscription_renewal** y no creamos un tercer nombre. **login** de la lista es uso genérico (rutas/formularios), no un evento Braze; no se toca. |

**Por qué:** Unificar “renovación hecha” y “próxima renovación” en uno solo mezclaría dos conceptos y complicaría segmentos (revenue vs recordatorios). Se mantienen los dos eventos con sus nombres.

---

### 3. customer_registered y account_registered

| Acción   | Nombre final en Braze | Fuente de verdad | Qué hacemos |
|----------|------------------------|------------------|-------------|
| **Unificar** | **account_registered** | **Backend** (Magento, registro exitoso en BD) | Un solo evento. El backend es la referencia para conteo de registros. Se cambia en Magento el nombre de **customer_registered** a **account_registered** y se deja de usar **customer_registered**. |

**Por qué:** Es el mismo hecho (usuario creado). El backend confirma que el cliente existe en BD; para cohortes y reportes la fuente de verdad es el backend. Unificar en **account_registered** alinea con portales y scripts y deja un único estándar.

---

### 4. logged_in, logged_into_portal, login

| Acción   | Nombre final en Braze | Fuente de verdad | Qué hacemos |
|----------|------------------------|------------------|-------------|
| **Unificar** | **logged_into_portal** | **Backend** (Magento cuando activo, o crons que leen last_login de BD) | Un solo evento. **customer_logged_in** (Magento) pasa a llamarse **logged_into_portal**. **logged_in** en la lista es atributo interno de dedup, no nombre de evento; no se expone como evento. **login** es uso genérico (rutas/formularios); no es evento Braze. Se elimina el nombre **customer_logged_in** como evento. |

**Por qué:** Mismo comportamiento (usuario entró a su cuenta). El backend/cron confirma el login en sistema. Un solo nombre simplifica segmentos de actividad y re-engagement.

---

### 5. product_added_to_cart y add_to_cart

| Acción   | Nombre final en Braze | Fuente de verdad | Qué hacemos |
|----------|------------------------|------------------|-------------|
| **Unificar** | **add_to_cart** | **Backend** en tienda Magento; **Frontend** en flujos solo portal (sin carrito Magento) | Un solo evento. En Magento se cambia **product_added_to_cart** a **add_to_cart**. Donde hay Magento, el backend es la referencia para “añadido al carrito” real; en portales sin Magento la fuente es el frontend. Se deja de usar **product_added_to_cart**. |

**Por qué:** Mismo hecho (ítem añadido al carrito). En tienda, el backend confirma que el carrito se actualizó en BD; en portal puro solo hay frontend. Un nombre único facilita campañas de carrito abandonado y reportes por producto.

---

## Resumen eventos

| De tu lista | Acción   | Nombre final / qué hacemos |
|-------------|----------|----------------------------|
| checkout_started, started_checkout | Unificar | **checkout_started** (fuente: backend). Eliminar uso de started_checkout. |
| subscription_renewal, upcoming_subscription_renewal, subscription_renewed | Mantener | **Mantener** subscription_renewal y upcoming_subscription_renewal (dos eventos). subscription_renewed → tratar como subscription_renewal si existe. |
| customer_registered, account_registered | Unificar | **account_registered** (fuente: backend). Eliminar customer_registered. |
| logged_in, logged_into_portal, login | Unificar | **logged_into_portal** (fuente: backend). Eliminar customer_logged_in como evento. logged_in/login = internos o genéricos, no eventos Braze. |
| product_added_to_cart, add_to_cart | Unificar | **add_to_cart** (fuente: backend en Magento, front en solo portal). Eliminar product_added_to_cart. |

---

## Atributos de la tarea

De tu lista:  
billing_address_line2 / billing_address_line_2 · shipping_address_line2 / shipping_address_line_2 · cancel_date / subscription_cancel_date · customer_id / magento_customer_id · email / Email · SMS / sms · coupon / coupon_code / order_coupon · discount / order_discount · last_video_consult_date / last_video_consultation_date · date_of_renewal / renewal_date · days_until_renewal / days_until_subscription_renewal · order_id / order_number · portal_link / portal_url / link_to_account_login / account_login_link / manage_subscription_link · date_logged_in / magento_last_login / logged_into_portal_ids · last_intake_name / latest_intake_name · last_intake_link / latest_intake_link · latest_intake_complete / intake_complete · subscription_cancel_reason / cancellation_reason · plan_length / last_plan_length / product_plan / subscription_frequency

### Unificar y eliminar el otro (un solo nombre por concepto)

| Par / grupo | Nombre a usar | Qué se elimina / deja de usarse |
|-------------|----------------|----------------------------------|
| billing_address_line2, billing_address_line_2 | **billing_address_line_2** | Eliminar **billing_address_line2**. Todo el código pasa a billing_address_line_2. |
| shipping_address_line2, shipping_address_line_2 | **shipping_address_line_2** | Eliminar **shipping_address_line2**. |
| email, Email | **email** (minúscula) | No usar **Email** como clave de atributo en Braze (case-sensitive). |
| SMS, sms | **sms** (minúscula) | Eliminar uso de **SMS** como clave; unificar en **sms**. |
| last_video_consult_date, last_video_consultation_date | **last_video_consultation_date** | Eliminar **last_video_consult_date**. |
| date_of_renewal, renewal_date | **date_of_renewal** | En payloads a Braze usar solo **date_of_renewal**; eliminar **renewal_date** en esos contextos. |
| days_until_renewal, days_until_subscription_renewal | **days_until_subscription_renewal** | Eliminar **days_until_renewal** en propiedades de evento/atributo. |
| portal_link, portal_url, link_to_account_login, account_login_link, manage_subscription_link | **portal_link** (URL principal); **account_login_link** (URL login); **manage_subscription_link** (link gestión suscripción) | Eliminar **portal_url** y **link_to_account_login** como atributos; usar portal_link y account_login_link. Los tres conceptos (portal, login, manage subscription) se mantienen con esos tres nombres. |
| last_intake_name, latest_intake_name | **last_intake_name** | Si existe latest_intake_name, migrar a last_intake_name y eliminarlo. |
| last_intake_link, latest_intake_link | **last_intake_link** | Si existe latest_intake_link, migrar y eliminarlo. |
| latest_intake_complete, intake_complete | **intake_complete** | Usar **intake_complete**. No introducir latest_intake_complete. |

### Mantener ambos con roles distintos (no son redundantes)

| Par / grupo | Uso |
|-------------|-----|
| cancel_date, subscription_cancel_date | **cancel_date** en propiedades de *eventos* (ej. evento subscription_canceled). **subscription_cancel_date** como *atributo de perfil* del usuario. No eliminar ninguno; cada uno en su contexto. |
| coupon, coupon_code, order_coupon | En *eventos* usar **coupon_code**. En *atributos de perfil* (último cupón) usar **order_coupon** (o **coupon** de forma consistente). Unificar en un solo nombre por contexto, no mezclar. |
| discount, order_discount | En *eventos* (order_placed) se puede mantener **discount**. En *atributo de perfil* usar solo **order_discount** y eliminar **discount** de atributos para no duplicar. |
| subscription_cancel_reason, cancellation_reason | **cancellation_reason** en propiedades de *eventos*. **subscription_cancel_reason** como *atributo de perfil*. No enviar ambos nombres al mismo perfil; en atributos solo subscription_cancel_reason. |
| plan_length, last_plan_length, product_plan, subscription_frequency | **subscription_frequency** para atributo de perfil (frecuencia). **product_plan** cuando el valor es nombre del plan. Reducir o eliminar **last_plan_length** si no aporta (documentar como alias de plan_length si se mantiene). |

### Definir convención (no duplicados sino uso distinto)

| Par / grupo | Decisión |
|-------------|----------|
| customer_id, magento_customer_id | Definir un solo nombre para *atributo* en Braze (ej. **magento_customer_id** o **customer_id**) y usarlo en todos los envíos. external_id ya es magento_{id}. |
| order_id, order_number | **order_id** = ID interno; **order_number** = número visible. Para atributos de “última orden” usar **last_order_number** (o order_number). No mezclar en el mismo contexto. |
| date_logged_in, magento_last_login, logged_into_portal_ids | **date_logged_in** = propiedad del *evento* logged_into_portal. **magento_last_login** = *atributo de perfil* (última fecha de login). **logged_into_portal_ids** = control interno de dedup; no es “last login”. Unificar atributo de perfil en **magento_last_login** (o last_login_at). |

---

## Resumen atributos

| Tipo | Ejemplos | Qué hacemos |
|------|----------|-------------|
| **Unificar y eliminar una variante** | billing_address_line2 → billing_address_line_2; shipping_address_line2 → shipping_address_line_2; SMS → sms; Email → email; last_video_consult_date → last_video_consultation_date; renewal_date → date_of_renewal; days_until_renewal → days_until_subscription_renewal; portal_url / link_to_account_login → portal_link y account_login_link | Un solo nombre por concepto; el otro se deja de usar en código y en Braze. |
| **Mantener con roles distintos** | cancel_date (evento) vs subscription_cancel_date (perfil); coupon_code (evento) vs order_coupon (perfil); discount (evento) vs order_discount (perfil); cancellation_reason (evento) vs subscription_cancel_reason (perfil); plan_length / product_plan / subscription_frequency | No eliminar; cada uno en su contexto. Reducir last_plan_length si no aporta. |
| **Definir convención** | customer_id / magento_customer_id; order_id / order_number; date_logged_in / magento_last_login / logged_into_portal_ids | Un nombre por uso (atributo vs evento vs interno) y documentarlo. |

---

## Próximos pasos

- Desarrollo aplicará las unificaciones y eliminaciones anteriores (eventos y atributos) según este documento y el reporte técnico.
- En Braze, hasta que el cambio esté desplegado: en segmentos y reportes que usen los nombres antiguos, podéis incluir **tanto el nombre nuevo como el antiguo** donde corresponda para no perder usuarios. Cuando el cambio esté hecho, actualizar a solo el nombre final.
- Si algún evento o atributo de la tarea requiere una decisión distinta (por ejemplo mantener ambos nombres en algún caso concreto), se puede revisar con el equipo técnico y actualizar este documento.
