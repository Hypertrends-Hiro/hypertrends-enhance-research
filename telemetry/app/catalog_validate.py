"""Canonical event name validation (PascalCase)."""

from __future__ import annotations

import re

# StudlyCaps segments: PageView, Add2Cart, UserProfilePatch
_PASCAL = re.compile(r"^[A-Z][a-zA-Z0-9]*(?:[A-Z][a-zA-Z0-9]*)*$")


def is_valid_canonical_event_name(name: str) -> bool:
    s = (name or "").strip()
    return bool(s) and bool(_PASCAL.fullmatch(s))
