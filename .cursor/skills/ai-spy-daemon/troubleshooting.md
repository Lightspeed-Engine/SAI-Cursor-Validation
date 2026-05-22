# AI-Spy troubleshooting

## Daemon will not start

| Symptom | Check | Fix |
|---------|-------|-----|
| Missing dependencies | Import error on start | `pip install python-socketio[aiohttp] aiohttp prometheus-client` |
| Port in use | `ss -tlnp \| grep 8887` | Kill stale process or `--port` alternate |
| Startup exception in logs | stderr from daemon | See `AISPY-0900` style codes in daemon; fix env/RC/ClickHouse optional deps |
| Wrong file run | `agent_detection.py` vs `agent_detection_daemon.py` | Use **daemon** for Socket.IO overlay |

## TopologyMap empty (no sectors)

1. **Daemon down** — nothing listening on 8887.
2. **No live entities** — run at least one agent (Cursor, OpenCode, etc.); Spy only shows detected processes/clients.
3. **Shufti down** — map may render `daemon only` sectors or appear sparse; start Shufti :3005 for hybrid overlay.
4. **Vite wrong URL** — client must target reachable host (Tailscale IP vs 127.0.0.1).
5. **Socket event mismatch** — UI expects `get_system_areas`; custom clients using `get_agents` will see nothing.

## Hybrid overlay never appears (`daemon + shufti`)

- Shufti `areas:list` empty or paths do not match `feature_area` naming.
- Tune `APP_AREA_HINTS` in `core/topology/topology.ts`.
- Run `discover:areas` with workspace root before expecting discovered overlays.

## Drill-down broken (sector → agents)

- Emit `subscribe_area` with exact `area_name` from `system_areas`.
- Wait for `area_agents` before rendering level 2.
- If push stalls, reconnect Socket.IO; check daemon logs for handler errors on `get_agent_detail`.

## Braid bridge silent (SAI)

- `cursorActivity.aiSpyBridge.enabled` false or not recording.
- Bridge URL not `http://127.0.0.1:8887`.
- Bridge still on legacy events (`agents`, `stats`) — upgrade to `system_areas` / `area_update` per strategy doc Phase C.
- Braid not running on :4711 — ingest fails independently of Spy UI.

## Prometheus / Grafana empty for AI-Spy

- Scrape target `localhost:8887` requires **host-network** Prometheus (bridge network cannot reach host daemon).
- LSE `lse-prometheus` may fail if **9090** already bound (GitLab or other listener).
- Grafana shows ops metrics, not `TopologyMap` — empty Grafana ≠ empty Spy UI.

## enrollment / service.py regressions

- Diff against `service.py.bak-20260330-aispy-sync` before large rewires.
- Run upstream tests: `MCP/tests/test_ai_spy_ui_levels.py`, `test_ai_spy_backend_intake.py`.

## Remote (Tailscale)

- Bind/connect using same IP the browser uses.
- Open **8887** (and **3005** for Shufti) on tailnet; portal `/ai-spy/` routes useless if `portal-gateway` is down — use direct ports.
