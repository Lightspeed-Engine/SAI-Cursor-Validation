# Topology module (Shufti + AI-Spy merge)

Portable copy of the **usable** Shufti/topology pieces from Lightspeed `ai-spy`, for the SAI Cursor Validation track.

## Files

| File | Role |
|------|------|
| `types.ts` | `SystemArea`, Shufti area types, `TopologySector` |
| `shuftiClient.ts` | Socket.IO client → Shufti `:3005` |
| `topology.ts` | `buildTopologySectors()` — merge Shufti paths with Spy live areas |
| `scripts/run-shufti-ui.sh` | Launcher wrapper (points at upstream Python server) |

## Upstream (do not fork blindly)

- Shufti server: `/mnt/lightspeed-data/Lightspeed-Engine/LSE-Core-2.0-2.1/scripts/shufti_ui_server.py`
- Shufti mapper: `shufti_code_mapper.py` (same folder)
- AI-Spy daemon: `/mnt/lightspeed-data/Lightspeed-Engine/MCP/mcp_server/agent_detection_daemon.py`
- Full React map UI: `LSE-Core-2.0-2.1/core/services/agent_enrollment/ai-spy/`

Strategy and gap analysis: [`../../docs/SHUFTI-AISPY-IMPLEMENTATION-STRATEGY.md`](../../docs/SHUFTI-AISPY-IMPLEMENTATION-STRATEGY.md).

## Shufti Socket contract

| Emit | Response |
|------|----------|
| `areas:list` | `areas:list:response` → `{ ok, areas[] }` |
| `discover:areas` `{ root }` | `discover:areas:response` → `{ ok, proposed_areas[] }` |

## AI-Spy Socket contract (daemon, port 8887)

| Emit | Response / push |
|------|-----------------|
| `get_system_areas` | `system_areas` |
| `subscribe_area` `{ area_name }` | `area_agents`, `area_stats`, `area_update` |
| `get_agent_detail` `{ agent_id }` | `agent_detail` |
| `get_agent_tool_calls` `{ agent_id }` | `agent_tool_calls` |

See strategy doc for full inventory.
