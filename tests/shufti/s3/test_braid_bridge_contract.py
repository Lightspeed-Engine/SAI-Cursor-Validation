"""S3 contract — braid bridge must subscribe to Spy system_areas (PLAN § S3)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.offline, pytest.mark.slice("S3")]

BRIDGE = Path(__file__).resolve().parents[3] / "cursor-activity" / "src" / "aispy" / "braidBridge.ts"


@pytest.mark.xfail(reason="S3 not implemented: bridge still uses single cursor.agent key")
def test_s3_bridge_subscribes_system_areas():
    text = BRIDGE.read_text(encoding="utf-8")
    assert "system_areas" in text, "braidBridge must handle system_areas"
    assert "area_update" in text, "braidBridge must handle area_update"


@pytest.mark.xfail(reason="S3 not implemented: per-entity agentKey")
def test_s3_bridge_uses_per_entity_agent_key():
    text = BRIDGE.read_text(encoding="utf-8")
    assert "entity_id" in text or "agent_id" in text
    assert "spy:" in text or "agentKey" in text
