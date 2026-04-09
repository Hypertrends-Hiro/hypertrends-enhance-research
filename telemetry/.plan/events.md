# Events and Attributes Split

Base: `telemetry/.plan/all-events.html` (eventos detectados)

## Eventos - Backend puros
Estos deben procesarse en backend (API + outbox + Braze).
- `AddPaymentInfo`
- `InitiateCheckout`
- `Purchase`
- `account_registered`
- `add_to_cart`
- `add_to_cart_failed`
- `add_to_cart_success`
- `appointment_booked`
- `appointment_cancelled`
- `appointment_rescheduled`
- `appointment_scheduled`
- `coupon_applied`
- `intake_abandoned`
- `intake_completed`
- `intake_incomplete`
- `intake_received`
- `intake_started`
- `intake_step_complete`
- `intake_step_completed`
- `login_attempted`
- `login_failed`
- `login_success`
- `membership_payment_attempted`
- `membership_payment_completed`
- `membership_payment_failed`
- `missed_appointment`
- `password_reset_failed`
- `password_reset_request`
- `password_reset_requested`
- `payment_failed`
- `payment_method_updated`
- `payment_successful`
- `purchase`
- `referral_redeemed`
- `referral_started`
- `registration_failed`
- `registration_success`
- `started_checkout`

## Eventos - Frontend UX puros
Estos se originan y permanecen en frontend por ser UX/interaccion local.
- `address_saved`
- `button_clicked`
- `cart_viewed`

## Eventos - Frontend requeridos explicitamente (sesion/tiempo en plataforma)
Estos deben emitirse en frontend porque dependen de presencia/actividad real del cliente.
- `assessment_slide_submitted`
- `intake_slide_viewed`
- `page_viewed`
- `registration_started`

### Recomendados para agregar (frontend requerido)
- `session_started`
- `session_heartbeat`
- `session_idle`
- `session_resumed`
- `session_ended`
- `active_time_reported`

## Atributos - Backend puros
Estos deben actualizarse desde backend para consistencia de perfil Braze.
- `setEmail`
- `setPhoneNumber`
- `setFirstName`
- `setLastName`
- `setDateOfBirth`
- `setGender`
- `setCustomUserAttribute`

## Atributos - Frontend UX puros
- Ninguno (UX puro normalmente se mide en propiedades de evento, no como atributo de usuario)

## Atributos - Frontend requeridos explicitamente
Solo para identidad de sesion mientras exista SDK web; idealmente migrar a backend en fase final.
- `changeUser`

## Notas de implementacion
- `session_*` y tiempos (`active_seconds`, `idle_seconds`) deben ir como **event properties**, no como atributos permanentes de usuario.
- Cuando el evento sea de negocio pero disparado en UI, frontend solo debe enviar a `/api/v1/telemetry/events`; Braze se publica en backend.
