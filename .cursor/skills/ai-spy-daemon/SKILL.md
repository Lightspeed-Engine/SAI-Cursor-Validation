---
name: ai-spy-daemon
description: Operates and troubleshoots the AI-Spy enterprise agent detection daemon (Socket.IO and HTTP on 8887, optional proxy 8888, React TopologyMap UI). Use when the user mentions AI-Spy, agent_detection_daemon, system_areas, agent monitoring overlay, topology map, or live agent drill-down for validation.
---

# AI-Spy Daemon

AI-Spy answers **who is running**: agents per feature area, tokens/tools, health bands, drill-down to agent detail. It is **not** the Shufti repo browser and **not** Grafana.

## Canonical vs legacy

| Component | Path | Use |
|-----------|------|-----|
| **Daemon (canonical)** | `MCP/mcp_server/agent_detection_daemon.py` | Socket.IO UI, Prometheus, proxy |
| Legacy monolith | `MCP/mcp_server/agent_detection.py` | Older HTTP `/api/agents`; avoid for new overlay work |
| Deprecated stub | `MCP/mcp_server/broken-Grafana-Agent-Monitor.py` | Forwards to daemon `main()` |
| React map UI | `LSE-Core-2.0-2.1/core/services/agent_enrollment/ai-spy/` | `TopologyMap`, 3-level drill-down |
| Handoff (legacy HTTP) | `MCP/mcp_server/AGENT_DETECTION_HANDOFF.md` | Reference only |

## Default runtime

| Setting | Default | Notes |
|---------|---------|--------|
| Dashboard / Socket.IO | **8887** | `--port` |
| HTTP proxy (optional) | **8888** | `--proxy-port` |
| WebSocket (legacy doc) | 8888 | Some docs say port+1; daemon uses Socket.IO on same service |
| License env | `MCP_ENTERPRISE_LICENSE` | Optional; `--license` |

**Not in LSE standalone compose** — start as host process.

## Dependencies

```bash
pip install python-socketio[aiohttp] aiohttp prometheus-client
```

Optional: `rocketchat_API`, `clickhouse_driver` (see daemon `--help` epilog).

## Start daemon

```bash
cd /mnt/lightspeed-data/Lightspeed-Engine/MCP
python3 mcp_server/agent_detection_daemon.py --port 8887 --proxy-port 8888
```

With venv if your environment uses one for MCP.

## Start React UI (harvest / Phase A)

```bash
cd /mnt/lightspeed-data/Lightspeed-Engine/LSE-Core-2.0-2.1/core/services/agent_enrollment/ai-spy
npm install
# Point Vite env at Shufti :3005 and daemon :8887 (see .env.example or vite config in tree)
npm run dev
npm run health:socketio   # optional socket probe
```

Exit criteria: non-empty `TopologyMap`, hybrid overlay `daemon + shufti`, sector → agents → tool/metrics.

## Socket.IO contract (topology / overlay)

| Emit | Response / push |
|------|-----------------|
| `get_system_areas` | `system_areas` `{ areas: SystemArea[] }` |
| `subscribe_area` `{ area_name }` | `area_agents`, `area_stats`, `area_update` |
| `get_agent_detail` `{ agent_id }` | `agent_detail` |
| `get_agent_tool_calls` `{ agent_id }` | `agent_tool_calls` |

On connect, server may push `system_areas` automatically.

Merge logic (SAI): `SAI-Cursor-Validation/core/topology/topology.ts` → `buildTopologySectors()`.

## HTTP smoke (daemon up)

```bash
curl -s "http://127.0.0.1:8887/metrics" | head
python3 -c "import socketio; s=socketio.Client(); s.connect('http://127.0.0.1:8887'); s.emit('get_system_areas'); s.disconnect()"
```

Legacy HTTP API (`agent_detection.py` only): `/api/agents`, `/api/statistics` — do not assume on daemon without verifying routes.

## SAI integration points

| Piece | Path |
|-------|------|
| Braid bridge | `cursor-activity/src/aispy/braidBridge.ts` |
| Standalone bridge | `core/bridges/ai-spy-braid-bridge.js` |
| Strategy | `docs/SHUFTI-AISPY-IMPLEMENTATION-STRATEGY.md` |

Bridge today listens to **legacy** event names. For overlay + validation, extend bridge to `get_system_areas` / `area_update` and ingest to braid (`evidence.agent` planned).

Config: `cursorActivity.aiSpyBridge.url` → `http://127.0.0.1:8887`

## Validation / ROI use

- **Group**: `system_areas` → sectors in `TopologyMap` (rates, bands, counts).
- **Individual**: `subscribe_area` → `get_agent_detail` / `get_agent_tool_calls`.
- **Proof**: braid ACTUAL timeline (hooks + Spy events), not Grafana alone.

## Maintenance

- Do not “simplify” by rewiring only `agent_enrollment/service.py` — keep daemon + React + Shufti as three legs (see strategy doc §9).
- Before UI deletes, grep for `buildTopologySectors`, `TopologyMap`, `test_ai_spy_ui_levels.py`.
- Compare `.bak-20260330-*` under `agent_enrollment/` when behavior regressed after swarm edits.
- Prometheus scrape: `localhost:8887` job `ai-spy` in `LSE-StandAlone-Deployment/monitoring/prometheus.yml` (requires host-network Prometheus).

## Quick health checks

```bash
ss -tlnp | grep ':8887'
curl -s -o /dev/null -w '%{http_code}\n' "http://127.0.0.1:8887/"
```

## When things break

See [troubleshooting.md](troubleshooting.md).

## Do not confuse with

| System | Role |
|--------|------|
| **Shufti :3005** | Static codebase map |
| **MCP gateway agent detection** | Ingress registration / licensing-shaped counting, not full-host Spy |
| **Grafana** | Metrics dashboards, not topology drill-down |
