#!/usr/bin/env python3
"""
Parse telemetry/.plan/braze-sdk-playground.html for SDK_EVENT_NAMES and
TELEMETRY_EVENT_NAMES, normalize to PascalCase canonical names, classify for
Braze/GA4/domain tags, write .plan/playground-events-catalog.normalized.json.

Run from repo root: python telemetry/scripts/gen_playground_events_catalog.py
Or from telemetry/: python scripts/gen_playground_events_catalog.py
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

META_STANDARD = {
    "AddPaymentInfo",
    "AddToCart",
    "CompleteRegistration",
    "InitiateCheckout",
    "Lead",
    "PageView",
    "Purchase",
    "Search",
    "SubmitApplication",
    "Subscribe",
    "ViewContent",
}

SPELLING_CANONICAL = {
    "subscription_cancelled": "SubscriptionCanceled",
}


def _telemetry_root() -> Path:
    p = Path(__file__).resolve()
    if p.parent.name == "scripts" and (p.parent.parent / ".plan").is_dir():
        return p.parent.parent
    return Path.cwd()


def parse_string_array_from_js(html: str, const_name: str) -> list[str]:
    m = re.search(
        rf"const\s+{re.escape(const_name)}\s*=\s*(\[[\s\S]*?\])\s*;",
        html,
    )
    if not m:
        raise ValueError(f"Could not find {const_name} in HTML")
    raw = m.group(1)
    return re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', raw)


def normalize_to_pascal(raw: str) -> str:
    s = raw.strip()
    if s in SPELLING_CANONICAL:
        return SPELLING_CANONICAL[s]
    s = re.sub(r"\.+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    if not s:
        return ""
    parts = [p for p in s.split("_") if p]
    if not parts:
        return ""
    if len(parts) == 1 and parts[0][0].isupper():
        w = parts[0]
        if re.search(r"[a-z][A-Z]", w):
            return w[0].upper() + w[1:]
        return w[0].upper() + w[1:] if len(w) > 1 else w.upper()
    return "".join(p[:1].upper() + p[1:].lower() for p in parts)


def refine_pascal(raw: str, p: str) -> str:
    r = raw.lower()
    if r in ("purchase", "Purchase"):
        return "Purchase"
    if r in ("add_to_cart", "AddToCart"):
        return "AddToCart"
    if r in ("page_viewed", "PageView", "pageview"):
        return "PageView"
    return p


def classify(canonical: str, aliases: set[str]) -> dict:
    al = " ".join(a.lower() for a in aliases)
    tags: set[str] = set()

    if any(
        x in al
        for x in (
            "backend_",
            "._",
            "syncorder",
            "syncsubscription",
            "repositoryplugin",
            "managementplugin",
        )
    ):
        tags.add("business_system")
    if any(
        x in al
        for x in (
            "page_viewed",
            "button_clicked",
            "slide_viewed",
            "video_",
            "cart_viewed",
            "product_listing",
            "search_performed",
            "assessment_slide",
            "intake_slide",
        )
    ) or canonical in ("PageView", "ViewContent", "Search"):
        tags.add("ux_experience")
    if any(
        x in al
        for x in (
            "intake_",
            "appointment_",
            "missed_appointment",
            "photo_",
            "lab_",
            "eligibility",
        )
    ):
        tags.add("clinical_intake_care")
    if any(
        x in al
        for x in (
            "order_",
            "cart",
            "checkout",
            "payment",
            "purchase",
            "product",
            "coupon",
            "shipping",
            "subscription",
            "renewal",
            "credit_card",
            "storecredit",
            "account_credit",
        )
    ) or canonical in ("AddToCart", "InitiateCheckout", "AddPaymentInfo", "Purchase"):
        tags.add("commerce_monetization")
    if any(
        x in al
        for x in (
            "login",
            "registration",
            "password_reset",
            "logged_into",
            "account_registered",
            "complete_registration",
            "subscriber",
            "address_saved",
            "addresssave",
        )
    ) or canonical == "CompleteRegistration":
        tags.add("identity_account")
    if any(x in al for x in ("referral", "message_sent", "comprehensive_panel", "lead", "subscribe")):
        tags.add("growth_marketing")
    if any(x in al for x in ("submitapplication",)):
        tags.add("growth_marketing")
        tags.add("ux_experience")
    if any(x in al for x in ("cron", "checkexpiring", "checkupcoming", "reminder", "midpoint")):
        tags.add("lifecycle_ops")
    if "event_name" in al:
        tags.add("placeholder_meta")
    if canonical == "UserProfilePatch":
        tags.add("identity_account")

    if canonical == "UserProfilePatch":
        braze_primary = "user_attributes_patch"
        braze_rest = ["attributes", "events"]
        ga4_primary = "user_properties_or_custom"
    elif canonical in ("Purchase", "LabPurchased"):
        braze_primary = "purchase_revenue_signal"
        braze_rest = ["events", "purchases"]
        ga4_primary = "purchase_or_ecommerce"
    elif canonical in META_STANDARD:
        braze_primary = "custom_event_meta_standard_name"
        braze_rest = ["events"]
        ga4_primary = "recommended_or_custom_event"
    else:
        braze_primary = "custom_event_domain"
        braze_rest = ["events"]
        ga4_primary = "custom_event"

    meta_standard = canonical in META_STANDARD

    if "placeholder_meta" in tags:
        pass
    elif not tags:
        tags.add("requires_manual_domain_review")

    return {
        "domain_tags": sorted(tags),
        "braze": {
            "primary_surface": braze_primary,
            "rest_track_arrays_typically_used": braze_rest,
            "sdk_web_typical": (
                "setUserAttribute / setEmail / etc. + optional logCustomEvent"
                if braze_primary == "user_attributes_patch"
                else "logCustomEvent"
            ),
            "notes": (
                "In Braze, most names are custom events via REST events[] or Web SDK logCustomEvent. "
                "Revenue may additionally use purchases[]. User traits use attributes[]."
            ),
        },
        "ga4": {
            "measurement_protocol_shape_hint": ga4_primary,
            "notes": (
                "GA4 uses client_id/user_id + events[] with name + params; user properties are a separate surface. "
                "Map from universal envelope via versioned mappers."
            ),
        },
        "meta_standard_event_name": meta_standard,
    }


def main() -> int:
    root = _telemetry_root()
    html_path = root / ".plan" / "braze-sdk-playground.html"
    if not html_path.is_file():
        print(f"Missing {html_path}", file=sys.stderr)
        return 1

    html = html_path.read_text(encoding="utf-8")
    sdk = parse_string_array_from_js(html, "SDK_EVENT_NAMES")
    tel = parse_string_array_from_js(html, "TELEMETRY_EVENT_NAMES")

    buckets: dict[str, dict] = defaultdict(lambda: {"aliases": set(), "sources": set()})

    def add(orig: str, source: str, force_pascal: str | None = None) -> None:
        p = force_pascal or normalize_to_pascal(orig)
        p = refine_pascal(orig, p)
        buckets[p]["aliases"].add(orig)
        buckets[p]["sources"].add(source)

    for n in sdk:
        add(n, "sdk")
    for n in tel:
        add(n, "telemetry")
    add("user_profile_patch", "telemetry", "UserProfilePatch")

    entries = []
    for canon, data in sorted(buckets.items()):
        aliases = sorted(data["aliases"], key=lambda x: (len(x), x.lower()))
        sources = sorted(data["sources"])
        c = classify(canon, data["aliases"])
        entries.append(
            {
                "canonical_name": canon,
                "aliases": aliases,
                "observed_in_playground_columns": {
                    "web_sdk_custom_event_buttons": "sdk" in sources,
                    "telemetry_ingest_buttons": "telemetry" in sources,
                },
                **c,
            }
        )

    doc = {
        "schema_version": "1.2.0",
        "title": "Playground-derived event catalog (normalized + classified)",
        "generated_at": date.today().isoformat(),
        "source_of_truth": (
            "telemetry/.plan/braze-sdk-playground.html "
            "(SDK_EVENT_NAMES + TELEMETRY_EVENT_NAMES + user_profile_patch from playground JS)"
        ),
        "source_files": ["telemetry/.plan/braze-sdk-playground.html"],
        "generator": "telemetry/scripts/gen_playground_events_catalog.py",
        "machine_readable_contract": (
            "Seed for Catalog + alias rows; SystemCatalogConfig references canonical_name."
        ),
        "normalization": {
            "canonical_naming": "PascalCase",
            "rules": [
                "snake_case and dotted Magento hooks: normalize separators to _, split segments, PascalCase each, join.",
                "StudlyCaps tokens without underscores preserved (AddToCart, PageView).",
                "subscription_canceled + subscription_cancelled -> SubscriptionCanceled.",
                "purchase + Purchase -> Purchase; add_to_cart + AddToCart -> AddToCart.",
                "page_viewed -> PageView (single canonical for page-view signals in this catalog).",
            ],
            "ingest_resolution": (
                "Resolve incoming event.name to canonical_name (case-insensitive + alias map) "
                "before SystemCatalogConfig evaluation."
            ),
        },
        "taxonomy_reference": {
            "domain_tags": {
                "ux_experience": "Session, navigation, UI engagement, product discovery.",
                "business_system": "Magento/Go hooks, plugins, sync pipelines — server-side.",
                "clinical_intake_care": "Intake flows, appointments, labs, clinical uploads.",
                "commerce_monetization": "Cart, checkout, orders, payments, credits, subscriptions.",
                "identity_account": "Auth, registration, password, portal identity, profile/address traits.",
                "growth_marketing": "Referrals, leads, messaging, upsell panels, applications.",
                "lifecycle_ops": "Reminders, expirations, scheduled maintenance events.",
                "placeholder_meta": "Non-production placeholder — block or quarantine in strict mode.",
                "requires_manual_domain_review": "Heuristic did not confidently tag; human review in backoffice.",
            },
            "braze_primary_surface": {
                "custom_event_domain": "Domain-specific name; REST events[] / Web logCustomEvent.",
                "custom_event_meta_standard_name": "Marketing-standard label; same transport as custom event.",
                "purchase_revenue_signal": "Commerce outcome; mapper may populate purchases[] and/or revenue fields.",
                "user_attributes_patch": "Profile/traits; REST attributes[] primary; optional companion event.",
            },
            "ga4_measurement_protocol_shape_hint": {
                "custom_event": "Standard GA4 custom event + params.",
                "purchase_or_ecommerce": "Use GA4 purchase / ecommerce params where applicable.",
                "recommended_or_custom_event": "May map to GA4 recommended events when params align; else custom.",
                "user_properties_or_custom": "User properties updates vs event stream; versioned mapper decides.",
            },
        },
        "special_entries": {
            "UserProfilePatch": "From fireTelemetryProfile(); not in TELEMETRY_EVENT_NAMES array.",
            "EventName": "Alias event_name — placeholder; exclude from prod or replace.",
        },
        "stats": {
            "unique_canonical_events": len(entries),
            "playground_raw_sdk_strings": len(sdk),
            "playground_raw_telemetry_strings": len(tel),
            "merged_aliases_total": sum(len(e["aliases"]) for e in entries),
        },
        "events": entries,
    }

    out = root / ".plan" / "playground-events-catalog.normalized.json"
    out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out} ({len(entries)} canonical events)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
