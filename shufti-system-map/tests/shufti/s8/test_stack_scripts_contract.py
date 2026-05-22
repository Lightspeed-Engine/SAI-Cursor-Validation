"""S8 contract — validation stack scripts exist (PLAN § S8)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.offline, pytest.mark.slice("S8")]

REPO = Path(__file__).resolve().parents[3]
START = REPO / "scripts" / "start-validation-stack.sh"
CHECK = REPO / "scripts" / "check-validation-stack.sh"


@pytest.mark.xfail(reason="S8 not implemented: start-validation-stack.sh missing")
def test_s8_start_script_exists():
    assert START.is_file()


def test_s8_check_script_exists():
    assert CHECK.is_file()
    text = CHECK.read_text(encoding="utf-8")
    assert "SHUFTI_PORT" in text or "3005" in text
