# Stage 2 — Braze strategy (nice to have)

Sugerencias **nice to have** desde la perspectiva de jefe de aplicación: qué priorizaría para identidad y Braze. Mismo título que el doc de estrategia principal; este es la variante “deseable”.

---

## 1. Cookie first — usuario anónimo

**Objetivo:** Un identificador estable en el browser antes de login, para unir todo el journey anónimo a un solo perfil y luego fusionarlo al usuario al registrarse.

- **Cookie first-party** con un **UUID** (ej. `crypto.randomUUID()`), nombre ej. `browser_uuid`, dominio según app (o dominio compartido si EMD/KWT comparten). Duración larga (ej. 1–2 años), `SameSite=Lax`, `Secure` en HTTPS.
- En **todas las llamadas a Braze** en sesión anónima, usar ese UUID como **alias** (ej. `browser_uuid:<uuid>` o `anon_<uuid>`). Así todos los eventos pre-login (intake_started, step_viewed, checkout_started, etc.) van al mismo perfil anónimo en Braze.
- Al **registrar**, el frontend envía el `browser_uuid` en el payload de signup; el backend guarda ese UUID en el registro del customer. En el frontend, `changeUser(customer_id)` y merge en Braze del alias con el `external_id`. El perfil anónimo queda unido al usuario.

**Nice to have:** Misma cookie en todas las rutas anónimas (SPA), sin depender de que Braze genere un device_id; el merge en registro es explícito y controlado.

---

## 2. Cookie first — después de login (reemplazar el id)

**Objetivo:** Tras el login, la cookie debe reflejar la identidad autenticada y **reemplazar** el uso del id anónimo; en visitas siguientes el app lee la cookie primero y ya sabe quién es el usuario sin esperar una llamada de auth.

- **Al hacer login/registro exitoso:** Además de lo que haga hoy el backend (token, sesión), el frontend **sobrescribe** la cookie first-party: en lugar de guardar solo el UUID anónimo, guardar un valor que represente al usuario logueado. Dos opciones típicas:
  - **Opción A:** Misma cookie, otro nombre o mismo: guardar un **token opaco** (session token o signed JWT) que el backend emite y que solo el backend puede validar. En cada carga, el frontend envía esa cookie; el backend resuelve token → `customer_id` y devuelve el usuario. El “id” que se reemplaza es el anónimo: ya no se usa `browser_uuid` como identificador activo para Braze; se usa `external_id = customer_id`.
  - **Opción B:** Misma cookie (ej. `browser_uuid`): después de login, el backend devuelve un **nuevo valor** para esa cookie (ej. `auth_id` o un hash de `customer_id` + salt) y el frontend la actualiza. Ese valor es el que se lee en las siguientes visitas; el frontend (o el backend en la primera request) resuelve a `customer_id`. Así la cookie “reemplaza” el UUID anónimo por un id post-login.

- **Comportamiento “cookie first after login”:** En cada carga de la app, **leer la cookie antes** de llamar a Braze o a la API de “who am I”. Si hay cookie de sesión/token válido → usuario logueado, usar `customer_id` como `external_id` en Braze y no usar el UUID anónimo. Si no hay cookie de sesión o está expirada → tratar como anónimo (y si existe `browser_uuid` antiguo, seguir usándolo como alias hasta el próximo login).

- **Reemplazo del id:** El id anónimo (UUID) deja de ser el identificador activo; el identificador activo pasa a ser el de la cookie post-login (token o auth_id que resuelve a `customer_id`). Opcional: guardar en backend la relación “este `customer_id` tuvo este `browser_uuid`” para trazabilidad; en Braze el perfil activo es el de `external_id = customer_id`.

**Nice to have:** Menos latencia en “who am I”, menos dependencia de llamadas de auth en cada carga, y Braze siempre recibe eventos con el `external_id` correcto desde el primer evento de la sesión logueada.

---

## 3. Otras sugerencias (nice to have)

- **Un solo lugar que defina “quién es el usuario”:** Un módulo o composable (ej. `useIdentity`) que lee primero la cookie (anon UUID vs session token/auth_id), resuelve a `customer_id` si hay sesión, y expone `externalId` y `isAnonymous` para Braze y para el resto de la app. Así toda la app usa la misma lógica cookie-first.
- **Backend guarda `browser_uuid` en el usuario:** En registro (y opcionalmente en login), persistir en BD el UUID de la cookie; permite soporte, antifraude y analítica de “dispositivo de registro” sin meter PII en Braze.
- **Mismo esquema de cookie entre EMD y KWT:** Si comparten dominio o subdominio padre, misma cookie name y formato para anon y post-login; si no, cada app con su cookie pero misma lógica (anon UUID → merge en registro; después de login, cookie reemplaza id).

---

Este documento es la variante **nice to have** del Stage 2 Braze; el doc canónico sigue en `docs/system/STAGE2-BRAZE-STRATEGY.md`.
