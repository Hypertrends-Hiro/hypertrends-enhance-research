## Response to task: Fix duplicate events

This document responds to the **fix duplicate events** task you created, based on the list of event and attribute pairs you shared. It explains **what we will do with each one**: which ones we will **unify** (what the final name is, and whether the source of truth is backend or frontend), which ones we will **keep** because they are actually different concepts, and which names we will **stop using** so we end up with a single name per concept in Braze.

---

## Events from the task

From your list:  
`checkout_started` / `started_checkout` · `subscription_renewal` / `upcoming_subscription_renewal` / `subscription_renewed` · `customer_registered` / `account_registered` · `logged_in` / `logged_into_portal` / `login` · `product_added_to_cart` / `add_to_cart`

### 1. checkout_started and started_checkout

| Action | Final Braze name | Source of truth | What we do |
|--------|------------------|-----------------|------------|
| **Unify** | **checkout_started** | **Backend** (Magento, when the user saves the address in checkout) | Single event. The backend is the reference for metrics and counts. The frontend can keep sending an earlier step (user lands on checkout) for context, but for reports and segments we use the backend event. We stop using **started_checkout**. |

**Why:** The backend confirms a concrete completed step (address saved); the frontend only indicates “landed on the page”. To avoid inflating counts or double-counting, the business truth comes from the backend. Unifying under a single name avoids having to think about two events in segments and funnels.

---

### 2. subscription_renewal, upcoming_subscription_renewal, subscription_renewed

| Action | Braze name(s) | Source of truth | What we do |
|--------|----------------|-----------------|------------|
| **Keep both** | **subscription_renewal** and **upcoming_subscription_renewal** (two events) | Backend (observers/crons) | We do **not** unify: they represent two different moments. **subscription_renewal** = renewal already charged; **upcoming_subscription_renewal** = reminder that renewal is approaching. If **subscription_renewed** exists in Braze, we treat it as equivalent to **subscription_renewal** and do not keep a third name. |

**Why:** Unifying “renewal happened” and “upcoming renewal” into a single event would mix two business concepts and make segments harder (revenue vs reminders). We keep both events with clear names.

---

### 3. customer_registered and account_registered

| Action | Final Braze name | Source of truth | What we do |
|--------|------------------|-----------------|------------|
| **Unify** | **account_registered** | **Backend** (Magento, successful record in DB) | Single event. The backend is the reference for registration counts. In Magento we rename **customer_registered** to **account_registered** and stop using **customer_registered**. |

**Why:** This is the same business action (user created). The backend confirms the customer exists in the database; for cohorts and reporting the source of truth is the backend. Unifying into **account_registered** aligns with portals and scripts and leaves a single standard name.

---

### 4. logged_in, logged_into_portal, login

| Action | Final Braze name | Source of truth | What we do |
|--------|------------------|-----------------|------------|
| **Unify** | **logged_into_portal** | **Backend** (Magento when active, or crons reading last_login from DB) | Single event. **customer_logged_in** (Magento) will be renamed to **logged_into_portal**. **logged_in** in the list is an internal dedup attribute, not an event name; it is not exposed as a Braze event. **login** is a generic use (routes/forms), not a Braze event. We stop using **customer_logged_in** as the event name. |

**Why:** Same user behavior (user logged into their account). The backend/cron confirms login in the system. A single event name simplifies activity and re‑engagement segments.

---

### 5. product_added_to_cart and add_to_cart

| Action | Final Braze name | Source of truth | What we do |
|--------|------------------|-----------------|------------|
| **Unify** | **add_to_cart** | **Backend** in the Magento store; **Frontend** in portal-only flows (no Magento cart) | Single event. In Magento we rename **product_added_to_cart** to **add_to_cart**. Where Magento exists, the backend is the source of truth for “added to cart” (cart persisted in DB). In portal-only contexts (no Magento cart) the frontend is the source. We stop using **product_added_to_cart**. |

**Why:** Same business action (item added to cart). In the store, the backend confirms the cart was updated; in portal-only flows we only have the frontend. A single event name makes abandoned cart campaigns and per‑product reporting simpler.

---

## Event summary

| From your list | Action | Final name / what we do |
|----------------|--------|-------------------------|
| checkout_started, started_checkout | Unify | **checkout_started** (source: backend). Stop using started_checkout. |
| subscription_renewal, upcoming_subscription_renewal, subscription_renewed | Keep both | **Keep** subscription_renewal and upcoming_subscription_renewal (two events). subscription_renewed → treat as subscription_renewal if it exists. |
| customer_registered, account_registered | Unify | **account_registered** (source: backend). Stop using customer_registered. |
| logged_in, logged_into_portal, login | Unify | **logged_into_portal** (source: backend). Stop using customer_logged_in as event name. logged_in/login = internal or generic, not Braze events. |
| product_added_to_cart, add_to_cart | Unify | **add_to_cart** (source: backend in Magento, frontend in portal-only). Stop using product_added_to_cart. |

---

## Attributes from the task

From your list:  
billing_address_line2 / billing_address_line_2 · shipping_address_line2 / shipping_address_line_2 · cancel_date / subscription_cancel_date · customer_id / magento_customer_id · email / Email · SMS / sms · coupon / coupon_code / order_coupon · discount / order_discount · last_video_consult_date / last_video_consultation_date · date_of_renewal / renewal_date · days_until_renewal / days_until_subscription_renewal · order_id / order_number · portal_link / portal_url / link_to_account_login / account_login_link / manage_subscription_link · date_logged_in / magento_last_login / logged_into_portal_ids · last_intake_name / latest_intake_name · last_intake_link / latest_intake_link · latest_intake_complete / intake_complete · subscription_cancel_reason / cancellation_reason · plan_length / last_plan_length / product_plan / subscription_frequency

### Unify and remove the other name (one name per concept)

| Pair / group | Name to use | What is removed / no longer used |
|--------------|-------------|-----------------------------------|
| billing_address_line2, billing_address_line_2 | **billing_address_line_2** | Remove **billing_address_line2**. All code uses billing_address_line_2. |
| shipping_address_line2, shipping_address_line_2 | **shipping_address_line_2** | Remove **shipping_address_line2**. |
| email, Email | **email** (lowercase) | Do not use **Email** as an attribute key in Braze (case‑sensitive). |
| SMS, sms | **sms** (lowercase) | Stop using **SMS** as a key; unify on **sms**. |
| last_video_consult_date, last_video_consultation_date | **last_video_consultation_date** | Remove **last_video_consult_date**. |
| date_of_renewal, renewal_date | **date_of_renewal** | In Braze payloads use only **date_of_renewal**; stop sending renewal_date in those contexts. |
| days_until_renewal, days_until_subscription_renewal | **days_until_subscription_renewal** | Stop using **days_until_renewal** in event/property payloads. |
| portal_link, portal_url, link_to_account_login, account_login_link, manage_subscription_link | **portal_link** (main URL); **account_login_link** (login URL); **manage_subscription_link** (subscription management URL) | Remove **portal_url** and **link_to_account_login** as attributes; use portal_link and account_login_link. We keep three concepts (portal, login, manage subscription) with those three names. |
| last_intake_name, latest_intake_name | **last_intake_name** | If latest_intake_name exists, migrate to last_intake_name and remove it. |
| last_intake_link, latest_intake_link | **last_intake_link** | If latest_intake_link exists, migrate and remove it. |
| latest_intake_complete, intake_complete | **intake_complete** | Use **intake_complete**. Do not introduce latest_intake_complete. |

**Differences for each pair and why we remove one name:**

- **billing_address_line2 vs billing_address_line_2**: Same meaning (“billing address line 2”). The only difference is formatting: one without an underscore between “line” and “2”, the other with it. We keep **billing_address_line_2** because it matches the convention for **shipping_address_line_2** and the rest of the code. We remove **billing_address_line2** so Braze does not have two attributes with the same meaning.

- **shipping_address_line2 vs shipping_address_line_2**: Same as above but for shipping address. Same data, two names. We unify on **shipping_address_line_2** and remove **shipping_address_line2**.

- **email vs Email**: Same value (user email). In Braze, attribute keys are case‑sensitive, so `email` and `Email` would become two separate attributes. We use only **email** (lowercase) since that is the standard in code and APIs; **Email** as a key is removed to avoid duplicating the same data.

- **SMS vs sms**: Both represent the same thing (phone for SMS). We standardize on **sms** (lowercase) because that is what Magento KWT and microservices already use. **SMS** as a key is removed so Braze has a single attribute.

- **last_video_consult_date vs last_video_consultation_date**: Both mean “last video‑consult date”. The second name is more explicit (“consultation”) and is already used in newer scripts. We keep **last_video_consultation_date** and remove **last_video_consult_date**.

- **date_of_renewal vs renewal_date**: Both mean “renewal date”. We choose **date_of_renewal** because it is already used more widely (Magento, crons, microservices). **renewal_date** stops being sent to Braze as an event/property so we do not have two names for the same concept.

- **days_until_renewal vs days_until_subscription_renewal**: Both represent “days until the next renewal”. **days_until_subscription_renewal** is clearer (explicitly says “subscription”). We keep that one and remove **days_until_renewal**.

- **portal_link, portal_url, link_to_account_login, account_login_link, manage_subscription_link**: Here we actually have three different concepts: (1) link to the portal/dashboard, (2) link to the login screen, (3) link to manage subscription. We therefore keep three names: **portal_link**, **account_login_link**, **manage_subscription_link**. **portal_url** and **link_to_account_login** are just naming variants of the same things, so we remove them as attribute keys to avoid five attributes where there are only three business concepts.

- **last_intake_name vs latest_intake_name**: Same meaning (“name of the last intake”). We use **last_intake_name** for consistency with other “last_*” attributes. If **latest_intake_name** exists in Braze or code, we migrate that data into **last_intake_name** and stop using the “latest” variant.

- **last_intake_link vs latest_intake_link**: Same as above, for the intake link. We keep **last_intake_link** and remove **latest_intake_link** after migration where needed.

- **latest_intake_complete vs intake_complete**: Both express “the intake is complete”. A single flag is enough; we use **intake_complete**. We do not introduce or keep **latest_intake_complete** to avoid duplicating the same concept.

### Keep both, with different roles (not redundant)

| Pair / group | How we use them |
|--------------|-----------------|
| cancel_date, subscription_cancel_date | **cancel_date** in *event* properties (e.g. event subscription_canceled). **subscription_cancel_date** as a *profile attribute* on the user. Do not remove either; each has its own context. |
| coupon, coupon_code, order_coupon | In *events* use **coupon_code**. In *profile attributes* (last coupon used) use **order_coupon** (or **coupon**, consistently). We unify names within each context so we do not mix event vs profile. |
| discount, order_discount | In *events* (order_placed) we can keep **discount**. In *profile attributes* we use only **order_discount** and stop sending **discount** as a profile attribute. |
| subscription_cancel_reason, cancellation_reason | **cancellation_reason** in *event* properties. **subscription_cancel_reason** as a *profile attribute*. Do not send both names into the profile; only subscription_cancel_reason there. |
| plan_length, last_plan_length, product_plan, subscription_frequency | **subscription_frequency** for profile attribute (frequency). **product_plan** when the value is the plan name. Reduce or remove **last_plan_length** if it does not add value (or document it clearly as an alias of plan_length if we keep it). |

**Differences and why we keep both (with different roles):**

- **cancel_date vs subscription_cancel_date**: Not duplicates. **cancel_date** is a property *inside an event* (for example when “subscription_canceled” fires). **subscription_cancel_date** is a *profile attribute* (the date the user canceled, stored on the profile). We keep both: one lives on events, the other on the profile.

- **coupon, coupon_code, order_coupon**: In *events* (apply/remove coupon, orders) we use **coupon_code**. In *profile attributes* (last coupon used) we use **order_coupon** (or a single consistent name). We do not remove the concepts, we just standardize one name per context so we do not blur event vs profile data.

- **discount vs order_discount**: In events (order_placed) we can keep **discount** as a property. As a *profile attribute* (discount of the last order) we only use **order_discount** and stop sending **discount** as a profile field, to avoid duplicating the same information.

- **subscription_cancel_reason vs cancellation_reason**: **cancellation_reason** is used in *event* properties (subscription_canceled). **subscription_cancel_reason** is the *profile attribute*. We do not send both keys onto the profile; there we only keep **subscription_cancel_reason**.

- **plan_length, last_plan_length, product_plan, subscription_frequency**: Related but not identical. **subscription_frequency** = billing frequency (e.g. “4 week”). **product_plan** = plan name. **plan_length** is used at event level. **last_plan_length** may be redundant; we either reduce it or document it clearly as an alias. We keep the names that carry clear meaning and avoid having two keys for the same thing.

### Define a convention (not duplicates, but we must pick a standard)

| Pair / group | Decision |
|--------------|----------|
| customer_id, magento_customer_id | Define a single *profile attribute* name in Braze (for example **magento_customer_id** or **customer_id**) and use it in all payloads. external_id is already magento_{id}. |
| order_id, order_number | **order_id** = internal ID; **order_number** = user‑visible number. For “last order” attributes we use **last_order_number** (or order_number). We do not mix them in the same context. |
| date_logged_in, magento_last_login, logged_into_portal_ids | **date_logged_in** = property on the *logged_into_portal* event. **magento_last_login** = *profile attribute* (last login date). **logged_into_portal_ids** = internal list for dedup, not a “last login” field. We standardize the profile attribute as **magento_last_login** (or last_login_at). |

**Differences and why we define a convention (instead of just deleting one name):**

- **customer_id vs magento_customer_id**: Both carry the same customer ID. It is not two data points, just two names. We define a single attribute name in Braze (for example **magento_customer_id** or **customer_id**) and use it everywhere. external_id is already `magento_{id}`; if we also store it as a profile attribute, there should be only one key.

- **order_id vs order_number**: Not the same. **order_id** = internal identifier (numeric or UUID). **order_number** = the order number the customer sees (increment_id, etc.). For “last order” attributes we use **last_order_number** (or **order_number**). The convention is: do not mix both in the same context; choose the one that matches the business meaning.

- **date_logged_in, magento_last_login, logged_into_portal_ids**: Three different uses. **date_logged_in** = property on the *logged_into_portal* event (date/time of that specific login). **magento_last_login** = *profile attribute* (the last time the user logged in). **logged_into_portal_ids** = internal list used for dedup, not something we use for segmentation as “last login”. We standardize the profile attribute as **magento_last_login** and keep **date_logged_in** only on the event.

---

## Attribute summary

| Type | Examples | What we do |
|------|----------|------------|
| **Unify and remove one variant** | billing_address_line2 → billing_address_line_2; shipping_address_line2 → shipping_address_line_2; SMS → sms; Email → email; last_video_consult_date → last_video_consultation_date; renewal_date → date_of_renewal; days_until_renewal → days_until_subscription_renewal; portal_url / link_to_account_login → portal_link and account_login_link | One name per concept; the other name stops being used in code and in Braze. |
| **Keep, with different roles** | cancel_date (event) vs subscription_cancel_date (profile); coupon_code (event) vs order_coupon (profile); discount (event) vs order_discount (profile); cancellation_reason (event) vs subscription_cancel_reason (profile); plan_length / product_plan / subscription_frequency | Do not delete the concepts; keep one clear name per context. Reduce last_plan_length if it does not add value. |
| **Define convention** | customer_id / magento_customer_id; order_id / order_number; date_logged_in / magento_last_login / logged_into_portal_ids | One standard name per use (profile attribute vs event vs internal) and document it. |

---

## Next steps

- Engineering will apply the unifications and removals above (events and attributes) according to this document and the technical report.
- In Braze, until the code changes are fully deployed: in segments and reports that still rely on old names, you can include **both the new and old names** where needed so we do not lose users. Once the rollout is complete, we switch to using only the final names.
- If any event or attribute from the task needs a different decision (for example, keeping both names in a very specific use case), we can review it with the technical team and update this document.

