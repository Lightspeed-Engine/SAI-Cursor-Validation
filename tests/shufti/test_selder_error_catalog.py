"""Catalog integrity — every code has category, message, recovery."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = [pytest.mark.offline, pytest.mark.slice("META")]

CATALOG = Path(__file__).resolve().parents[2] / "core" / "shared" / "selder-error-codes.json"


def _valid_code_shape(code: str) -> bool:
    """SHUFTI-#### / SAIV-* / LSE SYS### (no hyphen, matches selder_runtime)."""
    if code.startswith("SYS") and len(code) > 3 and code[3:].isdigit():
        return True
    return "-" in code


def test_selder_error_catalog_shape():
    raw = json.loads(CATALOG.read_text(encoding="utf-8"))
    assert len(raw) >= 10
    for code, row in raw.items():
        assert _valid_code_shape(code), code
        assert "category" in row and row["category"]
        assert "message" in row and row["message"]
        assert "recovery" in row
