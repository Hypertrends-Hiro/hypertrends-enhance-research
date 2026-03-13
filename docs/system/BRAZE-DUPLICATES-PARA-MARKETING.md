# Duplicados en Braze: guía para Marketing

Este documento explica, en lenguaje claro, qué eventos y atributos están duplicados en Braze, **si conviene cambiarlos** y **por qué**. Está pensado para equipos de marketing que usan Braze para segmentos, campañas y reportes.

---

## ¿Qué significa “duplicado”?

En algunos casos el **mismo comportamiento del usuario** (por ejemplo: “empezó el checkout”) se registra en Braze con **dos nombres distintos** según desde dónde se envíe el dato (web, app, backend). Eso puede:

- **Complicar segmentos y reportes**: hay que recordar los dos nombres y usarlos bien.
- **Inflar o confundir métricas**: si no se unifica, los números pueden verse raros o duplicados.
- **Simplificar la vida**: si se unifica en un solo nombre, todo el mundo trabaja con el mismo evento.

En cada sección verás: **qué es**, **si hay que cambiarlo** y **por qué**.

---

## 1. Inicio de checkout

### ¿Qué pasa hoy?

Cuando un usuario **empieza el proceso de pago** (llega al checkout), en Braze pueden aparecer dos eventos:

| Nombre en Braze        | Origen aproximado | Qué representa                    |
|------------------------|-------------------|------------------------------------|
| **started_checkout**   | Web / portal      | “El usuario abrió la página de checkout” |
| **checkout_started**   | Tienda Magento    | “El usuario guardó dirección en checkout” |

En la práctica es **el mismo momento de negocio**: el cliente decidió comprar y entró al flujo de pago.

### ¿Hay que cambiarlo?

**Sí.** Se recomienda usar **un solo nombre**: **checkout_started**.

### ¿Por qué?

- **Segmentos y funnels**: Hoy podrías estar filtrando por “started_checkout” en unos sitios y por “checkout_started” en otros. Un solo nombre evita errores y hace que “inicio de checkout” sea una métrica clara.
- **Reportes**: Un único evento permite comparar mejor entre canales y no duplicar conteos por el mismo comportamiento.
- **Campañas**: Triggers y segmentos como “Hizo checkout pero no compró” serán más simples de configurar y mantener.

---

## 2. Renovación de suscripción (dos eventos distintos)

### ¿Qué pasa hoy?

Hay dos eventos relacionados con la **renovación de suscripción**:

| Nombre en Braze                   | Significado en negocio                          |
|-----------------------------------|--------------------------------------------------|
| **subscription_renewal**          | La renovación **ya se cobró** (orden generada). |
| **upcoming_subscription_renewal** | **Aviso**: la renovación se acerca (ej. en X días). |

No son lo mismo: uno es “renovación hecha”, el otro es “próxima renovación”.

### ¿Hay que cambiarlo?

**No.** Conviene **mantener los dos** con sus nombres actuales.

### ¿Por qué?

- **subscription_renewal** sirve para medir renovaciones efectivas y revenue.
- **upcoming_subscription_renewal** sirve para campañas de recordatorio (“tu renovación es en 7 días”) o para segmentar “próximos a renovar”.
- Unificarlos en uno solo mezclaría dos conceptos y haría más difícil segmentar y reportar. Si en Braze ves algo llamado **subscription_renewed**, puedes tratarlo como equivalente a **subscription_renewal** (mismo concepto: renovación ejecutada).

---

## 3. Registro de cuenta

### ¿Qué pasa hoy?

Cuando un usuario **se registra** (crea cuenta), pueden llegar a Braze dos nombres de evento:

| Nombre en Braze         | Origen aproximado | Qué representa     |
|-------------------------|-------------------|---------------------|
| **customer_registered** | Tienda Magento    | Registro en la tienda |
| **account_registered**  | Web, portal, crons | Registro en el portal/cuenta |

Es **el mismo hecho**: “el usuario creó su cuenta”.

### ¿Hay que cambiarlo?

**Sí.** Se recomienda usar **un solo nombre**: **account_registered**.

### ¿Por qué?

- **Cohortes y atribución**: Para medir “usuarios nuevos” o “registros por campaña” necesitas un solo evento. Con dos nombres es fácil olvidar uno y subestimar o duplicar registros.
- **Flujos de bienvenida**: Si tu trigger o Canvas de bienvenida se basa en “se registró”, es más claro y seguro que todo llegue como **account_registered**.
- **Consistencia**: En portales y scripts ya se usa más **account_registered**; alinear la tienda a ese nombre deja un único estándar para todo el equipo.

---

## 4. Login / “entró al portal”

### ¿Qué pasa hoy?

Cuando un usuario **inicia sesión**, pueden aparecer en Braze:

| Nombre en Braze          | Origen aproximado | Qué representa        |
|--------------------------|-------------------|------------------------|
| **customer_logged_in**   | Tienda Magento    | Login en la tienda     |
| **logged_into_portal**   | Web, portal, crons | Login en el portal/cuenta |

Es **el mismo comportamiento**: “el usuario entró a su cuenta”.

### ¿Hay que cambiarlo?

**Sí.** Se recomienda usar **un solo nombre**: **logged_into_portal**.

### ¿Por qué?

- **Segmentos de actividad**: “Usuarios que han entrado en los últimos 30 días” debe basarse en un solo evento; si usas dos nombres, hay que incluirlos ambos en el filtro y el concepto se vuelve confuso.
- **Re-engagement**: Campañas del tipo “no has entrado hace tiempo” son más fiables con un único evento de login.
- **Claridad**: **logged_into_portal** ya es el estándar en web y portales; unificar la tienda en ese nombre evita tener que pensar “¿este proyecto usa logged_in o logged_into_portal?”.

---

## 5. Añadir al carrito

### ¿Qué pasa hoy?

Cuando un usuario **añade un producto al carrito**, pueden registrarse dos eventos:

| Nombre en Braze             | Origen aproximado | Qué representa              |
|-----------------------------|-------------------|------------------------------|
| **product_added_to_cart**   | Tienda Magento    | Ítem añadido (desde la tienda) |
| **add_to_cart**             | Web, portal       | Ítem añadido (desde web/portal) |

Es **el mismo comportamiento**: “añadió un producto al carrito”.

### ¿Hay que cambiarlo?

**Sí.** Se recomienda usar **un solo nombre**: **add_to_cart**.

### ¿Por qué?

- **Carritos abandonados**: Las campañas de recuperación de carrito suelen filtrar por “hizo add_to_cart y no compró”. Con un solo nombre el segmento es más simple y no se pierde parte del comportamiento (por ejemplo, solo el de la web o solo el de la tienda).
- **Productos más añadidos**: Reportes y segmentos por producto/SKU son más limpios si todo cae en **add_to_cart**.
- **Menos confusión**: **add_to_cart** es corto, claro y ya se usa en web y microservicios; unificar la tienda en ese nombre facilita la vida a todo el que configure segmentos o dashboards.

---

## Resumen rápido: ¿qué cambiar y qué no?

| Tema                    | Nombre actual (duplicados)     | ¿Cambiar? | Nombre a usar           |
|-------------------------|---------------------------------|-----------|--------------------------|
| Inicio de checkout      | started_checkout, checkout_started | **Sí**    | **checkout_started**     |
| Renovación suscripción  | subscription_renewal, upcoming_subscription_renewal | **No**    | Mantener ambos          |
| Registro de cuenta       | customer_registered, account_registered | **Sí**    | **account_registered**  |
| Login                   | customer_logged_in, logged_into_portal   | **Sí**    | **logged_into_portal**   |
| Añadir al carrito        | product_added_to_cart, add_to_cart       | **Sí**    | **add_to_cart**          |

---

## Atributos duplicados (resumen para marketing)

Además de eventos, hay **atributos de perfil** que a veces se envían con dos nombres para lo mismo (por ejemplo dirección línea 2, teléfono, cupón, etc.). Esos se están documentando y unificando en el reporte técnico para que en Braze quede **un solo nombre por concepto** (por ejemplo siempre **sms** en minúscula, siempre **billing_address_line_2** con guión bajo).  
Cuando esos cambios se apliquen, los segmentos y filtros que usen esos atributos seguirán funcionando mejor si se basan en el nombre que se elija como estándar; el equipo técnico os indicará el nombre final de cada uno.

---

## Próximos pasos

- **Si se aprueba unificar** los eventos indicados (checkout, registro, login, add_to_cart), desarrollo irá cambiando los nombres en frontend/backend para que todo llegue con el nombre recomendado.
- **Mientras tanto**, en Braze podéis:
  - En segmentos y reportes que midan “inicio de checkout”, “registro”, “login” o “add to cart”, **incluir los dos nombres** donde existan (así no se pierde ningún usuario).
  - Cuando el cambio esté hecho, **actualizar esos segmentos/reportes** para usar solo el nombre nuevo y, si se desea, deprecar el antiguo.

Si tenéis dudas sobre cómo afecta un evento o atributo concreto a vuestras campañas o dashboards, se puede revisar caso por caso con el equipo técnico usando este documento como referencia.
