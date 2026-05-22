---
name: shufti-code-mapper
description: Operates and troubleshoots the Shufti codebase mapper and UI server (Socket.IO on port 3005, Python mapper, persisted runs). Use when the user mentions Shufti, codebase map, topology areas, shufti_ui_server, shufti_code_mapper, or static repo overlay for AI-Spy.
---

# Shufti Code Mapper

Shufti answers **where code lives**: application areas, paths, file/line budgets, maps and diagrams. It does **not** track live agents, tokens, or licensing.

## Canonical paths (Lightspeed upstream)

| Asset | Path |
|-------|------|
| UI server | `LSE-Core-2.0-2.1/scripts/shufti_ui_server.py` |
| Mapper CLI | `LSE-Core-2.0-2.1/scripts/shufti_code_mapper.py` |
| Venv | `LSE-Shufti_venv/bin/python` |
| README | `LSE-Core-2.0-2.1/scripts/SHUFTI_CODE_MAPPER_README.md` |
| Run artifacts | `LSE-Core-2.0-2.1/scripts/data/shufti_ui_runs/` (typical) |

SAI wrapper (does not fork Python):

- `SAI-Cursor-Validation/core/topology/scripts/run-shufti-ui.sh`
- TypeScript client: `SAI-Cursor-Validation/core/topology/shuftiClient.ts`

Merged overlay strategy: `SAI-Cursor-Validation/docs/SHUFTI-AISPY-IMPLEMENTATION-STRATEGY.md`

## Default runtime

| Setting | Default | Env override |
|---------|---------|----------------|
| Host | `127.0.0.1` (SAI script) / `100.126.175.99` (upstream `run_shufti_ui.sh`) | `SHUFTI_UI_HOST` |
| Port | **3005** | `SHUFTI_UI_PORT` |
| Async mode | `threading` | `SHUFTI_UI_ASYNC_MODE` |
| Repo root | `LIGHTSPEED_ROOT` | points at Lightspeed tree |

## Start

From SAI repo:

```bash
SHUFTI_UI_HOST=127.0.0.1 SHUFTI_UI_PORT=3005 \
  /home/legion/SAI-Cursor-Validation/core/topology/scripts/run-shufti-ui.sh
```

From upstream:

```bash
/mnt/lightspeed-data/Lightspeed-Engine/LSE-Core-2.0-2.1/scripts/run_shufti_ui.sh
```

Smoke: open `http://<host>:3005/` or connect Socket.IO client to same origin.

## Socket.IO contract (clients)

| Emit | Response event | Payload shape |
|------|----------------|---------------|
| `areas:list` | `areas:list:response` | `{ ok, areas: ShuftiAreaInfo[] }` |
| `discover:areas` | `discover:areas:response` | `{ ok, proposed_areas[] }` with `{ root }` |

`discover:areas` may emit `discover:areas:queued` before completion on large trees.

TypeScript types: `SAI-Cursor-Validation/core/topology/types.ts`

## How it fits AI-Spy overlay

1. Shufti supplies **static** area paths and size estimates.
2. AI-Spy daemon supplies **live** `system_areas` (agents per `feature_area`).
3. `buildTopologySectors()` in `core/topology/topology.ts` merges both → `TopologySector` for `TopologyMap`.

Overlay labels: `shufti budget`, `shufti discovered`, `daemon only`, `daemon + shufti` (hybrid).

## Operator workflows

**List configured areas**

- UI: Shufti browser at `:3005`
- API: emit `areas:list` on Socket.IO

**Discover areas for a workspace**

```javascript
socket.emit('discover:areas', { root: '/path/to/workspace' });
```

**Run mapper CLI (no UI)**

```bash
LSE-Shufti_venv/bin/python shufti_code_mapper.py --help
```

See `SHUFTI_CODE_MAPPER_README.md` for `--scope`, `--format`, diagrams, baselines.

## Maintenance

- Prefer **upstream** fixes in `shufti_ui_server.py` / `shufti_code_mapper.py`; copy deltas into `core/topology/` only when SAI needs offline types or merge logic.
- Do not delete `data/shufti_ui_runs/` without operator approval (persisted history).
- After mapper schema changes, verify `shuftiClient.ts` still matches response shapes.
- Large monorepos: tune excludes in mapper README defaults; pass explicit `root` on discover.

## Quick health checks

```bash
ss -tlnp | grep ':3005'
curl -s -o /dev/null -w '%{http_code}\n' "http://127.0.0.1:3005/"
```

## SELDER error codes

Verified 2026-05-21: **`SHUFTI-####` codes are not in upstream Shufti Python** (`shufti_ui_server.py`, `shufti_code_mapper.py`) or `core/common/error_codes.py`. Responses use informal strings (`mapper_failed`, `mapper_timeout`, etc.). Pattern tags (`FAC`, `ADP`, …) are map annotations, not fault codes.

Full table and informal→symptom mapping: [error-codes.md](error-codes.md).  
Compare AI-Spy: `AISPY_CODES` in `MCP/mcp_server/agent_detection_daemon.py`.

If you have `SHUFTI_CODES` elsewhere, add that path to the skill; do not guess code numbers.

## When things break

Follow [troubleshooting.md](troubleshooting.md). Common cases: wrong host for Tailscale, missing venv, empty `areas:list`, discover timeout on huge trees. Cross-check [error-codes.md](error-codes.md) for response `error` keys.

## Do not confuse with

| System | Role |
|--------|------|
| **AI-Spy daemon** | Live agents, :8887 |
| **Grafana :3002** | Prometheus metrics, not repo map |
| **Shufti standalone UI** | Source for topology data; product overlay is merged map in ai-spy React or SAI webview |
