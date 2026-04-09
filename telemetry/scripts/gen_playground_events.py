#!/usr/bin/env python3
"""
Regenerate SDK_EVENT_NAMES / TELEMETRY_EVENT_NAMES in braze-sdk-playground.html from:
- telemetry/.plan/event-inventory.json (paths → front vs Magento backend)
- microservices/shared/braze/events.go (canonical Go / server event names)

Run from repo root or telemetry/:
  python scripts/gen_playground_events.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INV_PATH = ROOT / ".plan" / "event-inventory.json"
GO_PATH = ROOT.parent / "microservices" / "shared" / "braze" / "events.go"
HTML_PATH = ROOT / ".plan" / "braze-sdk-playground.html"


def go_event_names() -> set[str]:
    if not GO_PATH.is_file():
        return set()
    text = GO_PATH.read_text(encoding="utf-8")
    return set(re.findall(r'Event\w+\s*=\s*"([^"]+)"', text))


def classify_inventory(inv: dict) -> tuple[set[str], set[str]]:
    fe: set[str] = set()
    be_only: set[str] = set()
    for name, files in inv.items():
        has_fe = any(
            ("enhance.md" in f or "kwilthealth.com" in f) and f.endswith((".js", ".vue"))
            for f in files
        )
        has_be = any(
            f.startswith("microservices/")
            or f.startswith("magento-emd/")
            or f.startswith("magento-kwt/")
            or f.endswith(".go")
            or (f.endswith(".php") and "braze" in f.lower())
            for f in files
        )
        if has_fe:
            fe.add(name)
        if has_be and not has_fe:
            be_only.add(name)
    return fe, be_only


def main() -> None:
    inv = json.loads(INV_PATH.read_text(encoding="utf-8"))["events"]
    fe, be_only = classify_inventory(inv)
    go_names = go_event_names()
    telemetry = sorted(be_only | go_names)
    sdk = sorted(fe)

    html = HTML_PATH.read_text(encoding="utf-8")
    html = re.sub(
        r"const SDK_EVENT_NAMES = \[.*?\];",
        "const SDK_EVENT_NAMES = " + json.dumps(sdk, ensure_ascii=False) + ";",
        html,
        count=1,
        flags=re.DOTALL,
    )
    html = re.sub(
        r"const TELEMETRY_EVENT_NAMES = \[.*?\];",
        "const TELEMETRY_EVENT_NAMES = " + json.dumps(telemetry, ensure_ascii=False) + ";",
        html,
        count=1,
        flags=re.DOTALL,
    )
    html = re.sub(
        r"<p class=\"small text-muted mt-2\">Eventos telemetry: \d+ · Eventos SDK: \d+</p>",
        f'<p class="small text-muted mt-2">Eventos telemetry (Magento+Go): {len(telemetry)} · '
        f"Eventos SDK (front): {len(sdk)} · Total nombres únicos: {len(set(sdk) | set(telemetry))}</p>",
        html,
        count=1,
    )
    HTML_PATH.write_text(html, encoding="utf-8")
    print(f"Wrote {HTML_PATH}")
    print(f"  SDK (front): {len(sdk)}")
    print(f"  Telemetry (Magento-only ∪ Go): {len(telemetry)}")


if __name__ == "__main__":
    main()
