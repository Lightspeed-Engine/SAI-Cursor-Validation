# Shufti + AI-Spy: Strategy & Implementation Guide

**Track:** SAI Cursor Validation (core product)  
**Date:** 2026-05-18  
**Status:** Recovery / reconnect — not greenfield

This document states **goals**, **what exists**, **what is missing**, and **how the pieces connect**. It is the single planning reference for resuming the live codebase map with agent activity overlay.

---

## 1. Product goal

Answer one question for operators and validators:

> **Where in our codebase is AI work happening right now, and is that work healthy?**

| Layer | Question |
|-------|----------|
| **Shufti** | What is the *shape* of the repo? (areas, paths, file/line budgets) |
| **AI-Spy** | Which *agents* are active, in which *feature areas*, with what *tokens/tools/failures*? |
| **Merged map** | Visual *heat* on code geography + drill-down to agents |
| **Braid** (SAI) | Durable *ACTUAL* evidence timeline per session/agent (WebSocket, not MCP polling) |
| **Cursor Activity** | Host UX: recording, timeline, future system-agent panel |

Optional add-ons (governors, hooks, MCP hub) plug in; they are **not** required for the map to work.

---

## 2. Architecture (target)


**Data rule:** Spy → **braid ingest** for evidence. Do **not** make the product depend on MCP unified monitor polling.

---

## 3. What we copied into this repo

Portable TypeScript (no Vite-only env; works in Node/extension):

| Path | Source (Lightspeed) |
|------|---------------------|
| `core/topology/types.ts` | `ai-spy/src/types.ts` (subset) |
| `core/topology/shuftiClient.ts` | `ai-spy/src/services/shuftiClient.ts` |
| `core/topology/topology.ts` | `ai-spy/src/topology.ts` |
| `core/topology/scripts/run-shufti-ui.sh` | wraps `scripts/run_shufti_ui.sh` |

**Not copied (stay upstream; reference by path):**

| Asset | Path | Why |
|-------|------|-----|
| Shufti Python server | `LSE-Core-2.0-2.1/scripts/shufti_ui_server.py` | Large, venv-bound; run via wrapper |
| Shufti mapper | `shufti_code_mapper.py` | Same |
| AI-Spy daemon | `MCP/mcp_server/agent_detection_daemon.py` | System service |
| React map UI | `agent_enrollment/ai-spy/` (`App.tsx`, `TopologyMap.tsx`) | Reuse or embed later |
| Enrollment `service.py` | `agent_enrollment/service.py` | Rewired Mar 2026; use `.bak-*` to diff |

Already in SAI-Cursor-Validation before this doc:

| Piece | Path |
|-------|------|
| Spy → braid bridge | `cursor-activity/src/aispy/braidBridge.ts` |
| Braid ingest | `cursor-activity/src/braid/ingest.ts` |
| Standalone bridge | `core/bridges/ai-spy-braid-bridge.js` |

---

## 4. Inventory: exists vs partial vs missing

### 4.1 Shufti (codebase map)

| Item | Status | Notes |
|------|--------|-------|
| Area scan / discover | **Exists** | `discover:areas` on `:3005` |
| Area budgets list | **Exists** | `areas:list` |
| Standalone Flask UI | **Exists** | `shufti_ui_server.py` |
| Socket client in SAI | **Copied** | `core/topology/shuftiClient.ts` |
| Persisted run artifacts | **Exists** | `data/shufti_ui_runs/` (upstream) |
| Auto-start in SAI daemons | **Missing** | Not in `start-core-daemons.sh` |

### 4.2 AI-Spy daemon (live agents)

| Item | Status | Notes |
|------|--------|-------|
| Process / entity detection | **Exists** | `agent_detection_daemon.py` |
| `feature_area` / path classification | **Exists** | `_classify_work_area`, profiles |
| Level 1 `get_system_areas` | **Exists** | token_rate, tool_rate, bands |
| Level 2 `subscribe_area` | **Exists** | area_agents, area_stats |
| Level 3 agent detail / tool calls | **Exists** | handlers ~4008+ |
| Shufti integration inside daemon | **Missing** | Daemon does not call Shufti; merge is UI-side |
| Per-agent braid tags | **Partial** | Bridge uses single `cursor.agent` key |
| Cost per family per area ($) | **Partial** | Token rates yes; dollar cost TBD |
| Auto-start in SAI daemons | **Missing** | |

### 4.3 AI-Spy React UI (upstream)

| Item | Status | Notes |
|------|--------|-------|
| `TopologyMap` sector view | **Exists** | `ai-spy/src/components/TopologyMap.tsx` |
| Shufti + Spy merge | **Exists** | `buildTopologySectors` in App |
| 3-level drill-down | **Exists** | map → area → agent |
| Packaged / served on 8887 | **Partial** | `ai-spy-control.sh` needs env |
| Tests vs reality | **Stale** | `test_ai_spy_ui_levels.py` says "not implemented" but daemon has handlers |

### 4.4 SAI Cursor Validation

| Item | Status | Notes |
|------|--------|-------|
| Braid ACTUAL stream | **Exists** | `evidence.session` |
| `evidence.agent` stream | **Missing** | Spec'd, not in `store.js` |
| Spy → braid bridge | **Exists** | MVP event forward |
| Topology module | **Copied** | `core/topology/` |
| Map in VS Code | **Missing** | No webview yet |
| Unified startup script | **Missing** | Shufti + Spy + braid + UI |

### 4.5 Lost / damaged (Mar 2026 overwrite)

| Item | Recovery |
|------|----------|
| Enrollment backend rewire | `service.py.bak-20260330-*` in `agent_enrollment/` |
| Operator trust ("UI empty") | Usually **services down**, not deleted React |
| Git history | Check Lightspeed repo log around 2026-03-30 |

---

## 5. Connection plan (phases)

### Phase A — Prove the map (upstream stack)

**Goal:** See live sectors with Shufti overlay again.

1. Start Shufti: `core/topology/scripts/run-shufti-ui.sh` (or upstream `run_shufti_ui.sh`)
2. Start daemon: `python agent_detection_daemon.py` (dashboard **8887**)
3. Run agents (Cursor, OpenCode, etc.) so Spy has entities
4. Build/serve ai-spy UI (`npm run dev` in upstream `ai-spy/`) with `VITE_*` pointing at `:3005` and `:8887`
5. Confirm: non-empty `TopologyMap`, overlay label `daemon + shufti` on at least one sector

**Exit criteria:** Click sector → see agents; click agent → tool calls / performance.

### Phase B — Harden merge quality

**Goal:** Fewer `daemon_only` overlays; areas match real folders.

1. Tune `APP_AREA_HINTS` in `core/topology/topology.ts` for your monorepo layout
2. Optionally: pass Shufti `root` = workspace root on `requestTopology(root)`
3. Align Spy `feature_area` names with Shufti `path` segments (convention doc for agents)
4. Add integration test: mock `system_areas` + Shufti JSON → assert `buildTopologySectors` hybrid count

### Phase C — SAI product wiring

**Goal:** Same semantics inside Cursor Validation repo.

1. Import `core/topology` from `cursor-activity` (or shared package)
2. Extend `AiSpyBraidBridge` to subscribe `system_areas` / `area_update` and ingest structured events
3. Mint **ephemeral `agentId`** per Spy `entity_id` (tagged braid streams)
4. Implement `evidence.agent` in braid + timeline filter
5. Optional: VS Code webview hosting `TopologyMap` or simplified sector list

### Phase D — Assessment layer

**Goal:** "How good/bad" per area/family.

1. Roll up token + tool metrics per `feature_area` (daemon already aggregates)
2. Add cost model (provider × model table) → **cost per agent family per area**
3. Surface tool evaluator failures (`TOOL_CALL_EVALUATED`, April 2026 telemetry handoff) as **mistake rate**
4. Push summary events to braid: `topology.area.summary`, `agent.performance.band`

---

## 6. Runtime ports & env

| Service | Default port | Env overrides |
|---------|--------------|---------------|
| Shufti | 3005 | `SHUFTI_UI_PORT`, `SHUFTI_URL` |
| AI-Spy Socket.IO | 8887 | `AI_SPY_UI_PORT` |
| AI-Spy proxy | 8888 | (optional) |
| Braid | 4711 | `BRAID_URL` |
| Cursor Activity | — | `cursorActivity.aiSpyBridge.url` |

---

## 7. Socket event cheat sheet

### Shufti → client

```
emit areas:list {}
on  areas:list:response { ok, areas: ShuftiAreaInfo[] }

emit discover:areas { root: "/path/to/workspace" }
on  discover:areas:response { ok, proposed_areas: ShuftiDiscoveredArea[] }
```

### AI-Spy daemon → client

```
emit get_system_areas {}
on  system_areas { areas: SystemArea[] }

emit subscribe_area { area_name: "agent_enrollment" }
on  area_agents { area_name, agents: AgentSummary[] }
on  area_stats { ... }
on  area_update { ... }   # push

emit get_agent_detail { agent_id }
on  agent_detail { ... }

emit get_agent_tool_calls { agent_id }
on  agent_tool_calls { ... }
```

### SAI braid ingest (today)

```
POST /v1/ingest
{ stream: "evidence.session", agentKey, sessionId, kind, payload }
```

**Planned:** `stream: "evidence.agent"`, tags `entity_id`, `feature_area`, `app_area`.

---

## 8. Goals checklist (explicit)

- [ ] **G1** Live codebase sector map visible with ≥1 hybrid (Shufti + Spy) sector  
- [ ] **G2** Drill-down: area → agents → tool/metrics detail  
- [ ] **G3** Shufti + Spy + braid start from one documented command  
- [ ] **G4** Spy events on braid with per-entity agent keys  
- [ ] **G5** Token/cost rollup per feature area  
- [ ] **G6** Failure/mistake signal affects performance band  
- [ ] **G7** Cursor Activity shows system agents (not only local hooks)  

---

## 9. Principles (avoid repeat of overwrite)

1. **Do not rewire enrollment `service.py` to "simplify" the UI** — daemon + React + Shufti are three legs; keep contracts in `test_ai_spy_ui_levels.py` green.  
2. **Copy/adapt into `SAI-Cursor-Validation`**; treat Lightspeed tree as upstream unless explicitly patching.  
3. **Braid is the evidence bus** — MCP monitor is optional, not core.  
4. **Before deleting UI code** — search for `buildTopologySectors`, `ShuftiTopologyClient`, `TopologyMap`; if present, fix wiring don't replace.  
5. **Keep `.bak-*` and this doc** when touching agent_enrollment.  

---

## 10. Next actions (recommended order)

| # | Action | Owner |
|---|--------|-------|
| 1 | Run Phase A stack; screenshot map with agents running | Ops |
| 2 | Diff `service.py` vs `service.py.bak-20260330-aispy-sync` | Dev |
| 3 | Wire `core/topology` into cursor-activity dev dependency | Dev |
| 4 | Extend braid bridge for `system_areas` snapshots | Dev |
| 5 | Add `scripts/start-validation-stack.sh` (shufti + spy + braid) | Dev |

---

## 11. Related docs

| Doc | Location |
|-----|----------|
| **Phased slices + TDD/CI** | `docs/PLAN-2026-05-21-shufti-aispy-phased-slices.md` |
| **Slice test README** | `tests/shufti/README.md` |
| AI-Spy UI spec | `LSE-Core-2.0-2.1/.../ai-spy/AI-SPY-UI-TECHNICAL-SPECIFICATION.md` |
| Tool telemetry handoff | `agent_enrollment/AI-SPY-TOOL-TELEMETRY-HANDOFF-2026-04-01.md` |
| Braid spec | `SAI-Cursor-Validation/core/braid/BRAID-TECHNICAL-SPEC.md` |
| Topology module README | `SAI-Cursor-Validation/core/topology/README.md` |
| Reference map visuals | `docs/Component-coupleing.png`, `Higth-Level-Overview.png`, `Coupleing-Summery.png` |

---

*This guide is the canonical plan for Shufti + AI-Spy inside SAI Cursor Validation. **Slice-level execution order and exit criteria** live in `PLAN-2026-05-21-shufti-aispy-phased-slices.md`. Update the inventory tables when a row moves from Missing → Exists.*
