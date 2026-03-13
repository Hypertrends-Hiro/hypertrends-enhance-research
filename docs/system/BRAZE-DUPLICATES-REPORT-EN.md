# Quick Report: Duplicate Braze Events and Attributes

Summary of events and attributes that mean the same thing in the codebase (excluding docs, porting analysis, events.md). Includes where they are used, the difference (if any), and a consolidation recommendation.

---

## 1. Duplicate / equivalent events

### 1.1 `started_checkout` vs `checkout_started`

| Variant | Where it is used | Notes |
|----------|--------------|--------|
| **started_checkout** | enhance.md-version1 (UserCheckout.vue, Payment.vue), kwilthealth.com (CheckoutView, CartView, CartView.vue, `useBrazeTracking.js`), microservices (events.go) | Event sent from the **frontend** (Vue/microservices) when checkout starts. |
| **checkout_started** | magento-kwt, magento-emd: `ShippingInformationManagementPlugin.php` (when saving shipping address during checkout) | Event sent from the **Magento backend** (plugin). |

**Current parameters:**  
- **started_checkout (frontend, Braze JS / composables):**  
  - Payload variants:  
  - `email`, `SMS`/`sms`, `product_name` (string or array), `product_sku` (sometimes), `product_plan`, `product_image`, `product_price`, `product_url`, `currency`, `timestamp`.  
  - In some flows only `email`, `sms`, `product_name`, `product_plan` are sent.  
- **checkout_started (Magento plugin):**  
  - `quote_id`, `store_id`, `grand_total`, `items_count` (Magento cart/quote properties).

**Parameter conclusion:** They are not equivalent: the **frontend** sends product/user context, while the **backend** sends quote/cart context. If the name is unified in Braze, a **superset of properties** must be decided or normalized into a shared schema (for example, always send `product_*` + `quote_id` when available).  
**Conceptual difference:** Same concept (user started checkout). Different source: frontend vs backend, and different payload shape.  
**Recommendation:** Standardize on **`checkout_started`** (aligned with Magento and `*_started` naming). Update frontend (enhance.md-version1, kwilthealth.com) and `microservices/shared/braze/events.go` to `checkout_started` and deprecate `started_checkout`.

---

### 1.2 `subscription_renewal` / `upcoming_subscription_renewal` / `subscription_renewed`

| Variant | Where it is used | Meaning |
|----------|--------------|-------------|
| **subscription_renewal** | magento-kwt/emd: `SubscriptionGenerateSaveAfter.php` (when a renewal/renewal order is generated) | Event: **renewal executed** (order created). |
| **upcoming_subscription_renewal** | magento-kwt/emd: cron `CheckUpcomingRenewals.php`, custom scripts (braze_events_cron, BrazeEventBuilder, BrazeEventProcessors) | Event: **reminder** that the renewal is approaching (days until renew). |
| **subscription_renewed** | Not found as an event name in the codebase | — |

**Difference:**  
- `subscription_renewal` = renewal already happened (order/renewal generated).  
- `upcoming_subscription_renewal` = advance notice (e.g. “renewal in X days”).  
They are not duplicates; they are two different events.  
**Recommendation:** Keep both. If `subscription_renewed` exists in Braze, map it to `subscription_renewal` or document the equivalence under a single name (e.g. `subscription_renewal` for “renewal executed” and `upcoming_subscription_renewal` for “upcoming renewal”).

---

### 1.3 `customer_registered` vs `account_registered`

| Variant | Where it is used | Notes |
|----------|--------------|--------|
| **customer_registered** | magento-kwt, magento-emd: `Enhance/Braze/Observer/Customer/RegisterSuccess.php` | Magento backend: successful customer registration. |
| **account_registered** | enhance.md-version1 (Auth.vue, `useBrazeTracking.js`), kwilthealth.com (RegisterView, LiveFormPreview, `useBrazeTracking.js`), magento-kwt (braze_events_cron.php), magento-emd (BrazeEventBuilder, BrazeEventProcessors, braze_sync_by_email), microservices (events.go) | Frontend + emd scripts/cron: same action (account registration). |

**Current parameters:**  
- **customer_registered (Magento observer):**  
  - Typical `properties`: `source`, `store_id`, `website_id`, `email`, `first_name`, `last_name`, `dob`, `gender`, `sms`, etc.  
- **account_registered (frontend enhance.md-version1 / kwilthealth.com):**  
  - `customer_id`, `first_name`, `last_name`, `email`, `SMS`/`sms`, `link_to_account_login`.  
- **account_registered (Magento scripts/crons):**  
  - Minimum: `email`, `sms` and sometimes `registration_source`, `link_to_account_login`.

**Parameter conclusion:** All of them represent the **same registration action**, but the set of properties is not identical: the Magento observer has a richer payload; some frontend flows only send `email/sms/login_link`.  
**Conceptual difference:** Same business event, with different sources and level of detail.  
**Recommendation:** Consolidate into **`account_registered`** (more widely used in frontend and scripts). Change the `RegisterSuccess.php` observer in magento-kwt and magento-emd to send `account_registered` instead of `customer_registered`, and deprecate `customer_registered` in Braze/documentation. Ideally, harmonize a minimum expected payload: `customer_id`, `email`, `sms`, `first_name`, `last_name`, `registration_source`, `link_to_account_login`.

---

### 1.4 `logged_in` / `logged_into_portal` / `login` / `customer_logged_in`

| Variant | Where it is used | Notes |
|----------|--------------|--------|
| **customer_logged_in** | magento-kwt: `Enhance/Braze/Observer/Customer/Login.php` (active). magento-emd: same observer but **commented out** | Magento only; “logged in as customer”. |
| **logged_into_portal** | enhance.md-version1 (LoginRegister.vue, Intake/Auth.vue, Customer/Auth.vue, `useBrazeTracking.js`), kwilthealth.com (LoginView, services/login.js, `useBrazeTracking.js`), magento-emd (BrazeEventBuilder, BrazeEventProcessors, braze_sync_by_email) | Frontend + cron/scripts: portal login. |
| **logged_in** | magento-emd: tracking attributes (`logged_in_sent`) and internal keys | Internal use (dedup), not as an event name sent to Braze. |
| **login** | Generic use (routes, forms, recaptcha action); not as a Braze event | Not a Braze event. |

**Current parameters:**  
- **customer_logged_in (Magento observer):**  
  - `customer_id`, `email`, `store_id`, `website_id` (and potentially more customer metadata).  
- **logged_into_portal (frontend / composables / crons):**  
  - Always include at least: `email`, `SMS`/`sms`, `date_logged_in`, `portal_url`.  
  - In emd (`buildLoggedInEvent`) the same schema is used (`date_logged_in`, `portal_url`, `email`, `SMS`).  

**Parameter conclusion:** Both events describe the **same login**, but the `customer_logged_in` payload is oriented to Magento IDs and the `logged_into_portal` payload to portal telemetry (email/sms/date/url).  
**Conceptual difference:** Same login action; different naming and property shape depending on the layer.  
**Recommendation:** Standardize on **`logged_into_portal`** (already standard in frontend and emd). In magento-kwt (and magento-emd if the observer is re-enabled), change the event to `logged_into_portal` to align with the rest. Keep `logged_in_sent` only as an internal attribute if it is still used, and standardize the minimum expected payload: `email`, `sms`, `date_logged_in`, `portal_url`.

---

### 1.5 `product_added_to_cart` vs `add_to_cart`

| Variant | Where it is used | Notes |
|----------|--------------|--------|
| **product_added_to_cart** | magento-kwt, magento-emd: `Enhance/Braze/Plugin/CartItemRepositoryPlugin.php` (when adding/updating item in cart) | Magento backend. |
| **add_to_cart** | enhance.md-version1 (UserCartDetails, SelectMedication, MedicalInformation), kwilthealth.com (ProductDetails, `useBrazeTracking.js`, MembershipPayment.vue, LiveFormPreview.vue), magento-emd (BrazeEventProcessors commented out, BrazeEventBuilder commented out), microservices (events.go) | Frontend and references in scripts. |

**Current parameters:**  
- **product_added_to_cart (Magento plugin, when enabled):**  
  - Typical Magento payload: `product_id`/`sku`, `name`, `qty`, `price`, possibly `plan_length`/`product_plan`, `quote_id`, and cart metadata.  
- **add_to_cart (frontend / composables):**  
  - In enhance.md-version1: `email`, `SMS`/`sms`, `product_name`, `product_sku`, `product_image`, `product_price`, `plan_length`/`product_plan`, `currency`, `quantity`, `timestamp`.  
  - In kwilthealth.com: at least `email`, `sms`, `product_name`, `product_image`, `product_price`, `product_plan`, plus flags like `add_to_cart_success`, `default_payment`, `address{...}` in some flows.  

**Parameter conclusion:** They represent the same fact (“a product was added to the cart”), but with different payloads: backend focused on IDs/qty/technical price; frontend focused on marketing/analytics data. There is overlap (`product_name`, `product_plan`/`plan_length`, `product_price`, contact info), but they are not identical.  
**Conceptual difference:** Same business event, different sources and different payload detail.  
**Recommendation:** Consolidate into **`add_to_cart`** (shorter and already used in frontend/microservices). Change the `CartItemRepositoryPlugin` in magento-kwt and magento-emd to send `add_to_cart` instead of `product_added_to_cart`, and document a recommended minimum schema (`product_name`, `product_sku`, `product_plan`, `product_price`, `email`, `sms`, `quantity`).

---

## 2. Duplicate / equivalent attributes

### 2.1 `billing_address_line2` vs `billing_address_line_2`

| Variant | Where it is used |
|----------|--------------|
| **billing_address_line_2** (with underscore) | enhance.md-version1 (OrderConfirmation.vue), magento-emd: BrazeEventBuilder, braze_cron_job.php |
| **billing_address_line2** (without underscore) | magento-emd: braze_fix_data_v2.php, OrderPlaceAfter.php, AddressSaveAfter.php, SubscriptionGenerateSaveAfter.php, SyncOrdersToBraze.php |

**Recommendation:** Standardize on **`billing_address_line_2`** (consistent with `shipping_address_line_2` and the “line_2” convention). Replace all occurrences of `billing_address_line2` with `billing_address_line_2` in Magento and scripts.

---

### 2.2 `shipping_address_line2` vs `shipping_address_line_2`

| Variant | Where it is used |
|----------|--------------|
| **shipping_address_line_2** | enhance.md-version1 (OrderConfirmation.vue), magento-emd: BrazeDbQueries, BrazeEventBuilder, BrazeEventProcessors, braze_cron_job.php |
| **shipping_address_line2** | magento-emd: braze_fix_data_v2.php, OrderPlaceAfter, AddressSaveAfter, SubscriptionGenerateSaveAfter, OrderShipped, SyncOrdersToBraze |

**Recommendation:** Standardize on **`shipping_address_line_2`**. Replace `shipping_address_line2` with `shipping_address_line_2` in all listed files.

---

### 2.3 `cancel_date` vs `subscription_cancel_date`

| Variant | Where it is used | Notes |
|----------|--------------|--------|
| **cancel_date** | magento-kwt/emd: observers (SubscriptionSaveAfter, SubscriptionStatusChange), events (`subscription_canceled`); magento-emd BrazeEventBuilder, BrazeEventProcessors; microservices (props in events) | In **events** (property of the cancellation event). |
| **subscription_cancel_date** | magento-emd: user attributes (braze_sync_by_email, braze_fix_data_v2, braze_cron_job, BrazeEventProcessors); microservices (attributes.go, kwilt-order, kwilt-myaccount) | As a Braze user **profile attribute**. |

**Difference:** `cancel_date` is usually an event property; `subscription_cancel_date` is a user attribute (subscription cancellation date).  
**Recommendation:** Keep **`subscription_cancel_date`** only for the **profile attribute**. Event payloads can continue using `cancel_date` for the date of that specific event. If only one profile name is desired in Braze, use only `subscription_cancel_date` and do not duplicate it under another name.

---

### 2.4 `customer_id` vs `magento_customer_id`

| Variant | Where it is used |
|----------|--------------|
| **customer_id** | Massive usage: API responses, DB, models, internal payloads (not always as a Braze attribute). In Braze: enhance.md-version1 (Auth.vue) in event payloads (`customer_id` in properties). |
| **magento_customer_id** | Not found as a Braze attribute in the codebase. |

**Recommendation:** For the **Braze user attribute**, define only one: e.g. **`magento_customer_id`** (or `customer_id` if Braze already uses it that way) and document it. `external_id` is already `magento_{customerId}`; if the ID is also needed as an attribute, use a single name in all payloads.

---

### 2.5 `email` vs `Email` (case)

In Braze, attributes are case-sensitive. In the codebase:
- **Lowercase `email`:** dominant usage (Magento observers, microservices models JSON `"email"`, frontend).
- **Uppercase `Email`:** only in validation messages/labels (e.g. `'email': 'Email'` in VeeValidate), not as a Braze attribute key.

**Recommendation:** Always use **`email`** (lowercase) as the Braze attribute. Do not use `Email` as a key in `/users/track`.

---

### 2.6 `SMS` vs `sms`

| Variant | Where it is used |
|----------|--------------|
| **sms** (lowercase) | magento-kwt (all observers and crons), microservices (models.go and events: `"sms"` in JSON) |
| **SMS** (uppercase) | magento-emd: BrazeEventBuilder.php, BrazeEventProcessors.php, braze_sync_all.php, braze_cron_job.php, ShippingInformationManagementPlugin.php |

**Recommendation:** Standardize on **`sms`** (lowercase) to match Magento KWT and microservices. Change `'SMS'` to `'sms'` in magento-emd (BrazeEventBuilder, BrazeEventProcessors, braze_sync_all, braze_cron_job, plugin).

---

### 2.7 `coupon` / `coupon_code` / `order_coupon`

| Variant | Where it is used (as Braze attribute/event property) |
|----------|----------------------------------------------------|
| **coupon** | magento-kwt/emd: OrderPlaceAfter (event properties), SubscriptionGenerateSaveAfter; magento-emd: braze_fix_data_v2, braze_cron_job (user attribute). |
| **coupon_code** | magento-kwt/emd: CouponManagementPlugin (event properties), SyncOrdersToBraze (reads DB); enhance.md-version1, kwilthealth.com (payloads). Frontend and plugin send `coupon_code`. |
| **order_coupon** | magento-kwt/emd: OrderPlaceAfter and SyncOrdersToBraze as a user **attribute** (last order coupon). |

**Difference:** In events (apply/remove coupon, order) `coupon_code` or `coupon` is used; as an attribute for “last coupon used” Magento sometimes uses `order_coupon` and elsewhere `coupon`.  
**Recommendation:**  
- In **events**: use **`coupon_code`** (clearer and already used in frontend/plugin).  
- In **profile attributes** (last coupon/order): use **`order_coupon`** or **`coupon`** consistently; choose one (e.g. **`order_coupon`**) and replace the other in magento-emd (braze_fix_data_v2, braze_cron_job) and in Magento observers if they send a coupon attribute.

---

### 2.8 `discount` vs `order_discount`

| Variant | Where it is used |
|----------|--------------|
| **discount** | magento-kwt/emd: OrderPlaceAfter (event properties and attributes), SubscriptionGenerateSaveAfter; magento-emd: BrazeEventBuilder, braze_fix_data_v2, braze_cron_job (user attribute). |
| **order_discount** | magento-kwt/emd: OrderPlaceAfter and SyncOrdersToBraze as a user **attribute** (discount amount on the order). |

**Recommendation:** Standardize on **`order_discount`** for the profile attribute (order discount amount), to avoid confusion with discount at the event level. In `order_placed` event properties, `discount` can remain; for the user attribute, use only **`order_discount`** and remove `discount` from attributes in braze_fix_data_v2 and braze_cron_job if both are currently sent.

---

### 2.9 `last_video_consult_date` vs `last_video_consultation_date`

| Variant | Where it is used |
|----------|--------------|
| **last_video_consult_date** | magento-emd: BrazeEventProcessors.php (user attribute). |
| **last_video_consultation_date** | magento-emd: braze_fix_data_v2.php, braze_cron_job.php. |

**Recommendation:** Standardize on **`last_video_consultation_date`** (more explicit). Change BrazeEventProcessors to write `last_video_consultation_date` instead of `last_video_consult_date`.

---

### 2.10 `date_of_renewal` vs `renewal_date`

| Variant | Where it is used |
|----------|--------------|
| **date_of_renewal** | magento-kwt/emd: SubscriptionGenerateSaveAfter, CheckUpcomingRenewals, BrazeEventBuilder, BrazeEventProcessors, braze_fix_data_v2, braze_cron_job; microservices (models.go). |
| **renewal_date** | magento-kwt: braze_events_cron (query and event properties); magento-emd: CheckUpcomingRenewals (upcoming event properties). |

**Recommendation:** Use a single name for the **user attribute** and **renewal event property**: **`date_of_renewal`**. Wherever `renewal_date` is used in Braze payloads (braze_events_cron, CheckUpcomingRenewals), change it to `date_of_renewal` for consistency.

---

### 2.11 `days_until_renewal` vs `days_until_subscription_renewal`

| Variant | Where it is used |
|----------|--------------|
| **days_until_renewal** | magento-kwt/emd: CheckUpcomingRenewals (event properties). |
| **days_until_subscription_renewal** | magento-kwt/emd: CheckUpcomingRenewals (user attributes in the same cron). |

**Recommendation:** Standardize on **`days_until_subscription_renewal`** (clearer). Replace `days_until_renewal` with `days_until_subscription_renewal` in event properties in CheckUpcomingRenewals.

---

### 2.12 `order_id` vs `order_number`

Very widely used: `order_id` is usually the internal ID; `order_number` is the number shown to the user (`increment_id`, etc.). In Braze:
- **order_id** is used in event payloads (`order_placed`, etc.) and sometimes as an attribute.
- **order_number** in views and attributes (e.g. `last_order_number`).

**Recommendation:** Define a convention: **`order_id`** = internal ID (integer/uuid); **`order_number`** = visible order number (string). For “last order” attributes use **`last_order_number`** (or `order_number` if it is a single value). Do not mix them: within the same context (event or attribute), use the correct name according to the meaning.

---

### 2.13 `portal_link` / `portal_url` / `link_to_account_login` / `account_login_link` / `manage_subscription_link`

| Variant | Typical use |
|----------|------------|
| **portal_link** | URL to the portal/dashboard (photos, sync, events, microservices). |
| **portal_url** | URL to the portal/dashboard (enhance.md-version1, kwilthealth.com in `logged_into_portal` / `account_registered`). |
| **link_to_account_login** | Login URL (enhance.md-version1, kwilthealth.com, magento-kwt braze_events_cron). |
| **account_login_link** | magento-emd: braze_fix_data_v2, braze_cron_job (user attribute). |
| **manage_subscription_link** | magento-kwt/emd: CheckUpcomingRenewals (link to manage subscription). |

**Recommendation:**  
- **`portal_link`** = main portal/dashboard URL (one single name; deprecate `portal_url` as a Braze attribute and map it to `portal_link`).  
- **`account_login_link`** = login URL (standardize `link_to_account_login` into **`account_login_link`**).  
- **`manage_subscription_link`** = keep for the specific subscription-management link.  
Action: in frontend and scripts replace `portal_url` with `portal_link` and `link_to_account_login` with `account_login_link` in Braze attributes.

---

### 2.14 `date_logged_in` / `magento_last_login` / `logged_into_portal_ids`

| Variant | Use |
|----------|-----|
| **date_logged_in** | Property in `logged_into_portal` event (frontend, BrazeEventBuilder). |
| **magento_last_login** | User attribute (magento-emd: braze_sync_by_email, braze_sync_all, braze_sync_user, braze_fix_data_v2, braze_cron_job). |
| **logged_into_portal_ids** | Internal dedup attribute (list of IDs already sent) in magento-emd; not the “last login”. |

**Recommendation:**  
- **Profile attribute for “last login date”:** standardize on **`magento_last_login`** (or `last_login_at` if a generic name is preferred).  
- **Event property:** keep **`date_logged_in`** in the `logged_into_portal` event.  
- **`logged_into_portal_ids`** is internal control only; do not rename unless for internal clarity.

---

### 2.15 `last_intake_name` vs `latest_intake_name` / `last_intake_link` vs `latest_intake_link`

| Variant | Where it is used |
|----------|--------------|
| **last_intake_name** | enhance.md-version1: MedicalInformation.vue (`setCustomUserAttribute`). |
| **latest_intake_name** | Not found in code. |
| **last_intake_link** | enhance.md-version1: MedicalInformation.vue. |
| **latest_intake_link** | Not found in code. |

**Recommendation:** Keep **`last_intake_name`** and **`last_intake_link`**. If `latest_*` exists in Braze, migrate to `last_*` or document it as an alias.

---

### 2.16 `latest_intake_complete` vs `intake_complete`

| Variant | Where it is used |
|----------|--------------|
| **intake_complete** | magento-emd: braze_sync_by_email, braze_get_user, BrazeEventProcessors (user attribute); microservices kwilt-lab-ai, kwilt-dashboard-config. |
| **latest_intake_complete** | Not found. |

**Recommendation:** Use **`intake_complete`** as the profile attribute. Do not introduce `latest_intake_complete` unless it already exists in Braze; in that case, map it to `intake_complete`.

---

### 2.17 `subscription_cancel_reason` vs `cancellation_reason`

| Variant | Use |
|----------|-----|
| **cancellation_reason** | Property in events (`subscription_canceled`, etc.); enhance.md-version1, enhance.md, kwilthealth.com (`useBrazeTracking`); magento-emd braze_fix_data_v2, braze_cron_job (also as attribute). |
| **subscription_cancel_reason** | User attribute in magento-emd (braze_sync_by_email, braze_fix_data_v2, braze_cron_job, BrazeEventProcessors); microservices (attributes). |

**Recommendation:** For the **profile attribute**, use **`subscription_cancel_reason`**. For **event properties**, use **`cancellation_reason`**. Stop sending both names to the same profile; in braze_fix_data_v2 and braze_cron_job send only `subscription_cancel_reason` as the attribute and do not duplicate it with `cancellation_reason`.

---

### 2.18 `plan_length` / `last_plan_length` / `product_plan` / `subscription_frequency`

| Variant | Use |
|----------|-----|
| **plan_length** | Event properties and attributes (order, subscription, renewal, payment failed, etc.) in Magento and scripts. |
| **last_plan_length** | magento-kwt/emd: SubscriptionGenerateSaveAfter; magento-emd: braze_fix_data_v2, braze_cron_job (user attribute). |
| **product_plan** | magento-kwt/emd: subscription observers, SyncOrdersToBraze; kwilthealth.com (checkout, cart); magento-emd scripts. Sometimes same value as `plan_length` (frequency). |
| **subscription_frequency** | magento-kwt/emd: SubscriptionSaveAfter, SubscriptionGenerateSaveAfter, SyncSubscriptionsToBraze; magento-emd scripts and crons (user attribute). |

**Recommendation:**  
- **Subscription frequency** (e.g. “4 week”): standardize on **`subscription_frequency`** for the profile attribute and in events where a single name is desired.  
- **Plan/product** (name or description): use **`product_plan`** in events and attributes when the value is the “plan name” or similar.  
- **`plan_length`** and **`last_plan_length`**: often the same value; use **`plan_length`** in events and **`subscription_frequency`** (or `plan_length`) for the “last plan” in the profile, and remove **`last_plan_length`** if it adds no value (or document it as an alias of `plan_length` for the latest period).

---

## 3. Summary of suggested actions

| Topic | Action |
|------|--------|
| Checkout event | Standardize on `checkout_started`; update frontend and microservices. |
| Registration | Standardize on `account_registered`; change RegisterSuccess observer in Magento. |
| Login event | Standardize on `logged_into_portal`; change Login observer in Magento. |
| Cart event | Standardize on `add_to_cart`; change CartItemRepositoryPlugin in Magento. |
| Addresses | Use `billing_address_line_2` and `shipping_address_line_2` in all payloads. |
| SMS | Use `sms` (lowercase) in magento-emd. |
| Email | Use `email` (lowercase) as the Braze attribute. |
| Coupon (attribute) | Standardize on `order_coupon` or `coupon`; event should use `coupon_code`. |
| Discount (attribute) | Use `order_discount` for profile. |
| Video consult | Standardize on `last_video_consultation_date`. |
| Renewal (days) | Standardize on `days_until_subscription_renewal`. |
| Renewal (date) | Standardize on `date_of_renewal` in Braze payloads. |
| Portal URLs | `portal_link`, `account_login_link`; deprecate `portal_url` and `link_to_account_login` in Braze. |
| Cancel reason | Attribute: `subscription_cancel_reason`; event: `cancellation_reason`. |
| Plan/frequency | Profile attribute: `subscription_frequency` (and optionally `product_plan`); reduce usage of `last_plan_length`. |

---

*Generated from searches across repos: magento-kwt, magento-emd, system, microservices, secure-consult, old-secure-consult, kwilthealth.com, kt-feedback-service, enhance.md, enhance.md-version1. Excluded: docs, porting analysis, events.md.*
