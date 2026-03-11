# Stage 1 — System overview and flows

Documento global del sistema: **tipo de sistema**, **qué hace**, **repositorios activos** y **todos los flujos**, con **amarre frontend ↔ backend** (rutas y APIs).  
Excluidos del alcance: carpeta `porting analysis` y archivo `events.md`.

---

## 1. Tipo de sistema

- **Arquitectura:** Multi-repo, multi-marca. Varias aplicaciones frontend (SPAs) + capa e-commerce (Magento) + microservicios backend (Go/Java) en Google Cloud Run.
- **Patrón:** Frontends Vue 3 (enhance.md, kwilthealth.com, secure-consult) consumen APIs HTTP (REST) de servicios Go/Java; parte del catálogo y órdenes puede pasar por Magento. No hay SSR en los frontends revisados.
- **Marcas:**  
  - **EnhanceMD:** telemedicina, intake médico, recetas (Rx), pedidos, membresías.  
  - **Kwilt Health:** bienestar, dashboard, labs, planes, citas, tracking.
- **Usuarios:** Pacientes (B2C) en portales; proveedores/clínicos en consola (secure-consult).

---

## 2. Qué hace el sistema (negocio)

| Área | Descripción |
|------|-------------|
| **Adquisición / landing** | Entrada de usuarios (origen puede ser Webflow, Magento o raíz del SPA; no unificado en código). |
| **Intake (cuestionario médico)** | Cuestionarios por pasos/slides según producto o prescripción; respuestas se guardan por pregunta o por slide; se marca intake completo al final. |
| **Autenticación** | Login, registro, verificación de email; token (atkn) y consult_id (cid) en frontend; identidad en backend (emd-user-services / auth en kwilt-intake). |
| **Catálogo y carrito** | Productos B2C, medicación, suscripciones; carrito no-Rx y mega-member cart; cupones, store credit. |
| **Checkout y pago** | Direcciones, tarjetas guardadas, place-order; integración con pasarela/Magento según flujo. |
| **Post-compra** | Thank-you, order info; fotos, labs, visitas virtuales, tratamientos, notas. |
| **Dashboard (Kwilt)** | Config por customer (kwilt-dashboard-config), escenarios de journey, resultados de labs (kwilt-lab-ai), planes, acciones. |
| **Citas y videoconsulta** | kwilt-scheduler (disponibilidad, reservas); secure-consult + Daily.co para video. |
| **Consola proveedor** | Colas de órdenes, intakes, labs, farmacia, encuentros, builder de formularios (kwilt-intake-builder). |
| **Marketing / analytics** | Braze (eventos y atributos desde frontends y backend); GA4/GTM en algunos frontends. |

---

## 3. Repositorios y ramas activas

Repos considerados activos (con trabajo reciente o rama de feature activa). Excluido: `porting analysis`.

| Repositorio | Rama actual típica | Uso principal |
|-------------|--------------------|----------------|
| **enhance.md** | feat/phase1-braze-sdk-stabilization / master | SPA paciente EMD: intake, carrito, checkout, cuenta. |
| **enhance.md-version1** | feat/phase1-braze-sdk-stabilization / main | Variante legacy EMD (Laravel + Vue), mismo flujo intake/checkout. |
| **kwilthealth.com** | feat/phase1-braze-sdk-stabilization / main | SPA paciente Kwilt: dashboard, labs, planes, checkout, intake (LiveFormPreview). |
| **secure-consult** | master | SPA consola proveedor: colas, videoconsulta, intakes, farmacia. |
| **microservices** | master / develop / customer_journey | Monorepo Go/Java: kwilt-intake, kwilt-order, kwilt-scheduler, kwilt-myaccount, emd-*, kwilt-braze, kwilt-dashboard-config, kwilt-lab-ai, etc. |
| **magento-kwt** | main / develop | E-commerce Kwilt (NAD+, weight loss, membresías). |
| **magento-emd** | main / develop | E-commerce EnhanceMD (productos Rx, suscripciones). |
| **system** | main | Documentación de arquitectura (README, diagramas). |
| **kt-feedback-service** | main | Servicio de feedback. |
| **old-secure-consult** | master | Legacy; ramas feature (feat/change-refill-date, feature/lab-waiver-practitioner-ack). |

Los tres frontends con cambios Phase 1 Braze están en la rama `feat/phase1-braze-sdk-stabilization`; el resto de repos suele estar en main/master/develop.

---

## 4. Amarre frontend ↔ backend (rutas y APIs)

### 4.1 enhance.md

**Clientes HTTP:** `apiISV`, `apiORD`, `apiPhotos`, `apiMyAccount` (definidos en `src/api/httpClient.js`).  
**Bases (hardcodeadas en `src/api/endPoints.js`):**

| Cliente | Base URL (ejemplo) | Servicio backend inferido |
|---------|--------------------|----------------------------|
| apiISV | https://ufe-isv1-396730550724.us-central1.run.app | kwilt-intake (intake, auth, config, medication, thankyou, verify) |
| apiORD | https://ufe-ordv1-396730550724.us-central1.run.app | kwilt-order (customer, cart, payment, order, coupon, storeCredit, nonrxcart) |
| apiPhotos | https://eus-kx1z4q-396730550724.us-central1.run.app | emd-upload-service (photos) |
| apiMyAccount | https://ufe-myacv1-396730550724.us-central1.run.app | kwilt-myaccount (myInfo, recentOrders, medication, notes, referral, etc.) |

**Rutas frontend → API (resumen):**

| Flujo | Ruta Vue / pantalla | Método + endpoint | Backend |
|-------|----------------------|-------------------|---------|
| Intake: fetch questions | QuestionStep / created | POST /intake | kwilt-intake |
| Intake: save response | emdStore.saveResponse | POST /save-intake | kwilt-intake |
| Intake: complete | emdStore.handleFinalStep | POST /intake-complete | kwilt-intake |
| Auth login | Auth.vue / CustomerAuth | POST /login (ISV) o /auth/signin | kwilt-intake |
| Auth register | Auth.vue / CustomerAuth | POST /signup o /auth/signup | kwilt-intake |
| Config | QuestionStep | GET /sysconfig, /virtualhub-config | kwilt-intake |
| B2C medication | SelectMedication, Payment, intakeOrderreview | GET /b2cmedication | kwilt-intake |
| Thank-you content | ThankYou, MyLabs, intakeOrderreview | GET /cmpnt/:slug | kwilt-intake |
| Customer addresses | Varios checkout/myaccount | GET /customer/getaddress, POST /customer/saveaddress | kwilt-order |
| Cart / nonrx | UserCheckout, UserCartDetails, intakeOrderreview | GET/POST /nonrx-cart/*, /place-order | kwilt-order |
| Payment | Payment, EditPaymentDetails, etc. | POST /payment/savecreditcard, GET /stored-cards | kwilt-order |
| Order info | OrderConfirmation | POST /ordrinfo | kwilt-intake |
| Photos | PhotoUpload, ManageMembership | POST /photos/upload, GET /photos/all-photos | emd-upload-service |
| My account | MyAccount, MyLabs, MyMedications, etc. | GET/POST /customer/my-info, /medication, /treatmentplan, etc. | kwilt-myaccount |

---

### 4.2 kwilthealth.com

**Bases:** Definidas por env (VITE_BASE_ISV, VITE_BASE_ORD, VITE_BASE_KWT_MY_ACCOUNT, VITE_BASE_KWT_SCHEDULER, VITE_BASE_INTAKE, VITE_BASE_LAB_AI, VITE_BASE_PAYMENT, VITE_BASE_DASHBOARD_CONFIG, VITE_BASE_CUSTOMER_PHOTO, VITE_BASE_INT_BUILDER).  
**Clientes:** apiISV, apiORD, apikwtMyAccount, apikwtOrd, apikwtScheduler, apiIntake, apiLabAi, apiPayment, apiCustomerPhoto, apiDashboardConfig (`src/api/httpClient.js`).

| Flujo | Ruta Vue / pantalla | Método + endpoint | Backend inferido |
|-------|----------------------|-------------------|------------------|
| Customer info | userStore | GET /customer/info | kwilt-myaccount (KWT) |
| Dashboard config | MyProfile | GET /api/v1/customer/:id/config | kwilt-dashboard-config |
| Intake: save slide | LiveFormPreview | POST /save-intake-slide | kwilt-intake |
| Intake: complete | LiveFormPreview | POST /save-to-multi-tables (ENDPOINTS.intake.completeIntake) | kwilt-lab-ai (o intake) |
| Cart | CheckoutView | GET /nonrx-cart/getcart/:cartId | kwilt-order |
| Checkout / place order | CheckoutView | POST /megamember-cart/payment-placeorder, placeOrder | kwilt-order / payment |
| Payment / referral | CheckoutView, RegisterCheckoutView, ReferralModal | getSavedCard, saveReferral, redeemReferral, getReferral | kwilt-myaccount / payment |
| Scheduler | userStore (getAllBookings, bookAppointment, etc.) | GET/POST /bookings, /appointment-availability, /appointment-booking | kwilt-scheduler |
| Labs / customer photo | MyProfile, LabRequisitions, ProfilePhoto | GET /labs/all, /photos/* | emd-upload-service / customer-photo |
| Plans / lab AI | Plan.vue, LabResultLatest, NewLabResults, etc. | VITE_API_BASE_URL + /api/... (planes, test-results) | kwilt-ai-data / kwilt-lab-ai |
| Product listing / detail | ProductListing, ProductDetails | POST /products, GET /product-info/:sku | kwilt-intake (productinfo) |
| Add to cart (Kwilt) | ProductDetails, LiveFormPreview | POST /nonrx-cart/addItemToCart, /megamember-cart/addItemToCart | kwilt-order |

---

### 4.3 secure-consult

**Base:** `VITE_SECURE_BASE_URL`; otros servicios vía `VITE_PHARMA_SERVICE_URL`, `VITE_UPCOMING_ORDER_URL`, `VITE_QUEUE_ORDER_URL`, `VITE_EC_URL`, `VITE_USER_DASHBOARD_SERVICE_URL`, `VITE_INTAKE_BUILDER_URL`, `VITE_SCHEDULER_URL`, `VITE_USER_SERVICE_URL`, `VITE_KWILT_USER_SERVICE_URL`, `VITE_KWILT_SCHEDULER_URL`, etc. (`src/api/repository.js`).  
**Uso:** Un solo `repository` que delega en axios por servicio (baseAxios, userAxios, pharmaAxios, upcomingAxios, orderAxios, ecAxios, schedulerAxios, intakeAIAxios, etc.). Org (KWT vs EMD) cambia baseURL de user y scheduler por interceptor.

| Área | APIs (ejemplos) | Backend inferido |
|------|------------------|------------------|
| Intake builder | api/v1/forms/, api/v2/questions, api/v2/intake-types | kwilt-intake-builder |
| Colas / órdenes | repository (orderAxios, upcomingAxios) | emd-consultation / emd-upcoming-orders |
| Farmacia | pharmaAxios, emd-ph-od-396730550724 (direct) | emd-pharmacy-orders |
| Citas / disponibilidad | schedulerAxios (KWT o EMD por org) | kwilt-scheduler |
| Usuarios | userAxios (KWT o EMD por org) | emd-user-services |
| Dashboard / config | dashboardConfigAxios, checkoutConfigAxios | kwilt-dashboard-config |

---

## 5. Flujos del sistema (lista global)

### 5.1 Flujo paciente — EnhanceMD (enhance.md)

1. **Entrada:** `/` → redirect a `/customer/myaccount` (logado) o `/start` (anónimo).
2. **Intake:** `/:firstSegment` (start, weightloss-consult, …) → redirect a `/:firstSegment/step-1`. Navegación `/:firstSegment/step-:stepId`. QuestionStep carga preguntas (POST /intake), guarda respuestas (POST /save-intake), completa (POST /intake-complete).
3. **Login/registro:** Durante intake o en CustomerAuth: POST /login o /signup (apiISV → kwilt-intake).
4. **Carrito / checkout:** `/cart`, `/customer/checkout` (UserCartDetails, UserCheckout, Payment, intakeOrderreview). apiORD: getcart, addItemToCart, place-order, savecreditcard, getaddress, coupon, storecredit.
5. **Thank-you / order info:** OrderConfirmation (dentro de intake) o post-pago: POST /ordrinfo (apiISV). Contenido thank-you: GET /cmpnt/:slug.
6. **Cuenta:** `/customer/myaccount`, mylabs, mymedications, myintakes, myphotos, treatmentplan, notes, referral, etc. apiMyAccount → kwilt-myaccount.
7. **Fotos:** PhotoUpload, ManageMembership → apiPhotos (emd-upload-service).

### 5.2 Flujo paciente — Kwilt Health (kwilthealth.com)

1. **Entrada:** `/`, `/login`, `/register` → dashboard o auth.
2. **Dashboard:** `/dashboard`, `/dashboard/myprofile`. GET /api/v1/customer/:id/config (kwilt-dashboard-config); customer info (apikwtMyAccount).
3. **Intake:** `/intake/:id`. LiveFormPreview: POST /save-intake-slide (apiIntake), POST /save-to-multi-tables (apiLabAi) para complete.
4. **Labs:** `/dashboard/lab-results`, `/dashboard/new-lab-results`, `/dashboard/lab-upload`, `/dashboard/lab-requisitions`. apiLabAi, apiCustomerPhoto.
5. **Planes:** `/dashboard/plans`, `/dashboard/plan/:id`. VITE_API_BASE_URL + /api (kwilt-ai-data o similar).
6. **Carrito / checkout:** `/checkout`. apiORD, apikwtMyAccount: getCart, placeOrder, getSavedCard, updateCustomer, coupon, storeCredit, redeemReferral.
7. **Citas:** userStore: getAllBookings, bookAppointment, appointmentAvailability → apikwtScheduler (kwilt-scheduler).
8. **Productos:** ProductListing, ProductDetails: productListing, productDetail, addToCart → apiISV / apikwtOrd.
9. **Configuración / perfil:** MyProfile, Settings, PaymentMethod, AddressForm, ProfilePhoto, ReferralModal → apikwtMyAccount, apiORD, apiCustomerPhoto.

### 5.3 Flujo proveedor (secure-consult)

1. **Login:** Auth contra VITE_USER_SERVICE_URL o VITE_KWILT_USER_SERVICE_URL (org).
2. **Colas:** Órdenes, intakes pendientes, labs, farmacia (orderAxios, upcomingAxios, pharmaAxios).
3. **Intake builder:** CRUD formularios, preguntas, intake-types (intakeAIAxios → kwilt-intake-builder).
4. **Citas y disponibilidad:** schedulerAxios (KWT o EMD según org).
5. **Videoconsulta:** Integración Daily.co (no mapeada a un solo backend en este doc).
6. **Paciente (vista proveedor):** Portal paciente, detalle por customer_id (consultations, etc.).

### 5.4 Flujos e-commerce (Magento)

- **magento-kwt:** Catálogo Kwilt, carrito, checkout, suscripciones; observers Braze, CustomerJourney; cron sync intake to Braze.
- **magento-emd:** Catálogo EnhanceMD, pedidos Rx, suscripciones; Braze, Gorgias, Shipstation, etc.  
Los frontends Vue pueden orquestar pedidos vía kwilt-order que a su vez puede integrar con Magento/VirtualHub; el detalle de qué llama a Magento directamente no está completo en los frontends revisados.

### 5.5 Flujos de journey (backend)

- **customer_journey_events / customer_journey_current_state:** Actualizados por kwilt-intake (intake_started, intake_saved, intake_completed), kwilt-order, emd-upcoming-orders, kwilt-scheduler, kwilt-lab-ai, etc.  
- **kwilt-dashboard-config:** Lee journey y devuelve scenario_id + banner + action_cards para el dashboard (GET /api/v1/customer/:id/config).

---

## 6. Resumen de servicios backend por nombre

| Servicio | Responsabilidad principal | Consumido por (frontend) |
|----------|---------------------------|---------------------------|
| kwilt-intake | Intake (fetch, save, complete), auth (signin/signup/verify), config, b2cmedication, product info, ordrinfo, component content | enhance.md (apiISV), kwilthealth.com (apiISV, apiIntake) |
| kwilt-order | Customer addresses, cart, nonrx-cart, megamember-cart, payment (save card, stored-cards), place-order, coupon, store credit | enhance.md (apiORD), kwilthealth.com (apiORD, apikwtOrd) |
| kwilt-myaccount | my-info, recent orders, medication, treatmentplan, notes, referral, progress tracker, virtual visits, program switch | enhance.md (apiMyAccount), kwilthealth.com (apikwtMyAccount) |
| kwilt-scheduler | Bookings, appointment-availability, appointment-booking, visit-summary, check-providers-availability | kwilthealth.com (apikwtScheduler), secure-consult (schedulerAxios) |
| kwilt-dashboard-config | GET /api/v1/customer/:id/config (scenarios, banner, action_cards) | kwilthealth.com (apiDashboardConfig) |
| kwilt-lab-ai | save-to-multi-tables (complete intake), lab results, planes (según uso) | kwilthealth.com (apiLabAi) |
| kwilt-intake-builder | api/v1/forms, api/v2/questions, intake-types, content-blocks, slides | secure-consult (intakeAIAxios) |
| emd-upload-service | photos/upload, photos/all-photos | enhance.md (apiPhotos) |
| emd-user-services | Auth y perfil usuario (secure-consult userAxios) | secure-consult |
| emd-pharmacy-orders | Farmacia (pharmaAxios) | secure-consult |
| emd-upcoming-orders | Órdenes próximas, colas (upcomingAxios) | secure-consult |
| emd-consultation | Colas consulta (orderAxios / ecService) | secure-consult |

---

## 7. Próximos stages (referencia)

- **Stage 2 — Braze:** Eventos, ownership, composables, flush (ya documentado en war-plan/phase1-*).
- **Stage 3 — Documentation:** Ubicación de docs, convenciones, gaps.
- **Stage 4 — Env vars:** Inventario VITE_*, por repo y servicio.
- **Stage 5 — Issues:** Bugs conocidos, deuda técnica, riesgos de atribución (ver ENHANCE_MD_GA4_ATTRIBUTION_RISKS.md).

---

**Referencias:**  
- `system/README.md` (arquitectura y diagrama).  
- `enhance.md/src/api/endPoints.js`, `enhance.md/src/api/httpClient.js`.  
- `kwilthealth.com/src/api/endPoints.js`, `kwilthealth.com/src/api/httpClient.js`.  
- `secure-consult/src/api/repository.js`, `secure-consult/src/config/api`.  
- `microservices/kwilt-intake/request/*.go`, `microservices/kwilt-order/request/*.go`.
