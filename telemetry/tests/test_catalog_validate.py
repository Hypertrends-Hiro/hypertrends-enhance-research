"""Unit tests for canonical event name validation."""

from __future__ import annotations

import pytest

from app.catalog_validate import is_valid_canonical_event_name


@pytest.mark.parametrize(
    ("name", "ok"),
    [
        ("PageViewed", True),
        ("Add2Cart", True),
        ("A", True),
        ("", False),
        ("   ", False),
        ("page_viewed", False),
        ("Page_viewed", False),
        ("pageViewed", False),
        ("123Start", False),
        ("Page-View", False),
    ],
)
def test_is_valid_canonical_event_name(name: str, ok: bool) -> None:
    assert is_valid_canonical_event_name(name) is ok
