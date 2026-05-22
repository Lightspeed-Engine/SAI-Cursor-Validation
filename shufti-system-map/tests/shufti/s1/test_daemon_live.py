"""S1 PASS/FAIL — AI-Spy daemon Socket.IO (PLAN § S1, requires live :8887)."""

from __future__ import annotations

import os
import time

import pytest

pytestmark = [pytest.mark.live, pytest.mark.slice("S1")]

SPY_URL = os.environ.get("AI_SPY_URL", "http://127.0.0.1:8887")
TIMEOUT_S = float(os.environ.get("AISPY_SOCKET_TIMEOUT", "5"))


@pytest.fixture
def socket_client():
    socketio = pytest.importorskip("socketio")
    client = socketio.Client()
    yield client
    if client.connected:
        client.disconnect()


def test_s1_system_areas_and_drill_down(socket_client):
    if not os.environ.get("RUN_LIVE"):
        pytest.skip("Set RUN_LIVE=1 with AI-Spy daemon on :8887")

    out: dict = {}

    @socket_client.on("system_areas")
    def on_areas(data):
        out["areas"] = (data or {}).get("areas") or []

    @socket_client.on("area_agents")
    def on_agents(data):
        out["agents"] = (data or {}).get("agents") or []

    @socket_client.on("agent_detail")
    def on_detail(data):
        out["detail"] = data

    socket_client.connect(SPY_URL, wait_timeout=TIMEOUT_S)
    socket_client.emit("get_system_areas")
    time.sleep(TIMEOUT_S)

    areas = out.get("areas") or []
    assert len(areas) >= 1, "system_areas.areas empty"
    first = areas[0]
    name = first.get("name") or first.get("area_name")
    assert (first.get("active_count") or 0) + (first.get("verified_count") or 0) >= 1

    socket_client.emit("subscribe_area", {"area_name": name})
    time.sleep(TIMEOUT_S)
    agents = out.get("agents") or []
    assert len(agents) >= 1, "area_agents.agents empty"
    agent_id = agents[0].get("agent_id") or agents[0].get("id")
    assert agent_id

    socket_client.emit("get_agent_detail", {"agent_id": agent_id})
    time.sleep(TIMEOUT_S)
    assert out.get("detail"), "agent_detail not received"
