# Shufti + AI-Spy: Phased Slices (pass/fail)

**Track:** SAI Cursor Validation  
**Date:** 2026-05-21 (rev 2 — concrete verification)  
**Companion:** `SHUFTI-AISPY-IMPLEMENTATION-STRATEGY.md`  
**Tests:** `tests/shufti/`, `scripts/run-shufti-slice-tests.sh`, `.github/workflows/shufti-aispy-slices.yml`

---

## SELDER error codes + centralized test log (no silent failures)

**Standard:** Every failure emits a **stable code** from `core/shared/selder-error-codes.json`. Every test emits a **JSONL line** to `reports/shufti-slice-latest.jsonl`. If the runner exits 0 but the log contains `FAIL`/`ERROR`, the harness exits **1** (`SAIV-TEST-0006`).

| Artifact | Path |
|----------|------|
| Code catalog | `core/shared/selder-error-codes.json` |
| JS helper | `core/shared/selder-error-codes.js` |
| Python helper | `tests/lib/selder_error_codes.py` (`CodedError`) |
| Python log | `tests/lib/test_log.py` |
| TypeScript log | `tests/lib/test-log.ts` |
| Pytest hooks | `tests/shufti/conftest.py` (START/PASS/FAIL/SKIP per test) |

**Slice → code prefix**

| Slice | Codes (examples) |
|-------|------------------|
| S0 | `SHUFTI-0100` … `SHUFTI-0103` |
| S2 | `SHUFTI-0200`, `SHUFTI-0201` |
| S5 | `SHUFTI-0300` |
| S1 live | `SAIV-SPY-0100` … `SAIV-SPY-0102` |
| S3/S8 contract | `SAIV-BRAID-*`, `SAIV-STACK-*` |
| Harness | `SAIV-TEST-0001` … `SAIV-TEST-0006`, `SYS003` |

**Rules**

1. Do not use bare `assert` for slice contract checks — raise `CodedError("SHUFTI-….")` (Python) or `recordFail(...)` (TypeScript).
2. Do not `pytest.mark.skip` without a non-empty `reason=`.
3. Pre-commit / CI: inspect `reports/shufti-slice-latest.jsonl` on failure; each line has `error_code`, `recovery`, `slice`, `test_id`.
4. Adding a new failure mode → add a row to `selder-error-codes.json` first, then use it in tests.

---

## TDD workflow (checkout → pre-commit → PR → merge)

### What “done” means

| Layer | Command | Merge? |
|-------|---------|--------|
| **Pre-commit (local)** | `npm run precommit:shufti` | Run before every commit touching topology/tests |
| **PR CI (required)** | GitHub job `S0 S2 S5 (merge gate)` | **Must be green** to merge |
| **Live CI (optional)** | workflow_dispatch `run_live=true` | Not required for merge |
| **Future slices** | `npm run test:shufti:contract` | xfail until slice lands; does not block merge |

A slice is **done in code** when its tests exist and pass (or are `xfail` with a ticket until implementation). A slice is **done in ops** when live checks pass on your machine (PLAN § per slice).

### What to check out

```bash
git clone <SAI-Cursor-Validation-url>
cd SAI-Cursor-Validation
# Optional: Lightspeed Engine sibling for live S0/S6 and vendor sync
export LIGHTSPEED_ENGINE_ROOT=/path/to/Lightspeed-Engine
```

**S0 PR scope (typical):** changes under `tests/shufti/`, `tests/fixtures/`, `core/topology/`, `scripts/run-shufti-slice-tests.sh`, workflow, PLAN doc. Upstream mapper lives in Lightspeed; CI uses **vendor copy** `tests/shufti/vendor/shufti_compose_mapper.py` (sync with `SYNC_VENDOR_MAPPER=1` locally when you change upstream).

### Pre-commit (local gate)

```bash
npm run precommit:shufti
# same as:
bash scripts/run-shufti-slice-tests.sh offline
```

**Offline gate runs (no network):**

| Slice | Test file | Runner |
|-------|-----------|--------|
| S0 | `tests/shufti/s0/test_compose_mapper_offline.py` | pytest |
| S2 | `tests/shufti/s2/test_topology_merge_offline.ts` | `npx tsx --test` |
| S5 | `tests/shufti/s5/test_sectional_stitch_offline.ts` | `npx tsx --test` |

Python deps install into `tests/.venv` automatically (gitignored).

**Optional before commit (Lightspeed checkout present):**

```bash
SYNC_VENDOR_MAPPER=1 LIGHTSPEED_ENGINE_ROOT=$LIGHTSPEED_ENGINE_ROOT \
  tests/.venv/bin/python -m pytest tests/shufti/s0 -k sync -v
```

### PR → GitHub CI → merge

1. Open PR (e.g. branch `slice/s0-compose-ci`).
2. Workflow **Shufti AI-Spy Slices** runs on path filter (see `.github/workflows/shufti-aispy-slices.yml`).
3. Job **`S0 S2 S5 (merge gate)`** must pass:
   - `bash scripts/run-shufti-slice-tests.sh offline`
4. **Merge allowed** when that job is green (and your repo’s other required checks, e.g. Activity Correlator if those paths changed).
5. **S0-only PR:** if you only touch S0 files, only this workflow + relevant paths need to pass; you do not need live agent tests for merge.

**Not required for merge:**

- `RUN_LIVE=1` / job `S1 S8 live`
- `npm run test:shufti:contract` (S3/S8 xfail contracts)
- Manual `curl` block in § S0 below (use for ops proof on full LSE compose)

**After merge:** tag evidence optional: `docs/verification-log/YYYY-MM-DD-s0-pass.txt` with CI run URL.

### Live verification (operator, post-merge or nightly)

```bash
# Start stack manually, then:
RUN_LIVE=1 npm run test:shufti:live
# or GitHub: workflow_dispatch → run_live=true
```

Uses PLAN § S1 socket script and `scripts/check-validation-stack.sh` (ports 3005, 8887, 4711).

### Test map (all slices)

| Slice | Automated test | In merge gate? |
|-------|----------------|----------------|
| S0 | `tests/shufti/s0/test_compose_mapper_offline.py` | **Yes** |
| S1 | `tests/shufti/s1/test_daemon_live.py` | No (`RUN_LIVE=1`) |
| S2 | `tests/shufti/s2/test_topology_merge_offline.ts` | **Yes** |
| S3 | `tests/shufti/s3/test_braid_bridge_contract.py` | No (xfail) |
| S4 | — | Not yet |
| S5 | `tests/shufti/s5/test_sectional_stitch_offline.ts` | **Yes** |
| S6 | — | Not yet (live mapper) |
| S7 | — | Not yet |
| S8 | `tests/shufti/s8/test_stack_scripts_contract.py` | No (xfail start script) |

When you implement S3/S4/S6/S7/S8, move tests from xfail/skip into `offline` or `live` and add them to `run-shufti-slice-tests.sh` + workflow if they should block merge.

---

## Pass/fail rules (manual / live ops)

- A slice is **PASS** only if **every** item under **PASS** is true.
- A slice is **FAIL** if **any** item under **FAIL** is true.
- No subjective wording (“looks good”, “impressive”, “prove”). Numbers, HTTP codes, JSON keys, file paths only.
- Record evidence in `docs/verification-log/` (create as needed): paste command output + `run_id`.

**Constants (adjust host if not local)**

```bash
SHUFTI=http://127.0.0.1:3005
SPY=http://127.0.0.1:8887
COMPOSE_TARGET=LSE-StandAlone-Deployment/standalone-deployment-docker-compose.yml
REPO_ROOT=/mnt/lightspeed-data/Lightspeed-Engine
SAI_ROOT=/home/legion/SAI-Cursor-Validation
```

---

## Slice overview

| Slice | What gets built (literal) | Verified by |
|-------|---------------------------|-------------|
| S0 | Compose → 3 `.mmd` files + HTTP API + AI-Spy tab | Shell `curl` + `wc`/`jq` on artifacts |
| S1 | Daemon `system_areas` + UI drill-down events | Socket.IO client or `curl` + UI event names |
| S2 | `topology.ts` hints + one Jest/Vitest test file | `npm test` / `pytest` exit 0 |
| S3 | Braid ingest records with distinct `agentKey` per Spy entity | `grep` on braid store or ingest log |
| S4 | Documented cost formula + band changes when failure fixture injected | Test + sample JSON fixture |
| S5 | `sectionalTypes.ts` + `sectional-stitch.test.ts` | `npm test` exit 0, no network |
| S6 | TS/JS files in mapper output for SAI repo | `jq` on run snapshot + diagram line counts |
| S7 | Stitch manifest on disk + viewer URL returns 200 | Files exist + `curl -f` |
| S8 | `start-validation-stack.sh` exits 0 when ports up | Script exit code |

| Slice | Status |
|-------|--------|
| S0 | **CI offline test PASS**; live § S0 `curl` optional on full LSE compose |
| S2, S5 | **CI offline test PASS** |
| S1 | Test file ready; **live only** |
| S3, S8 | Contract tests **xfail** until implementation |
| S4, S6, S7 | Not automated yet |

---

## S0 — Compose architecture map (deployment graph)

### What was actually built (not “demo wow”)

| # | Deliverable | Location |
|---|-------------|----------|
| 1 | Python: read `docker-compose*.yml`, emit graph JSON + 3 Mermaid files | `LSE-Core-2.0-2.1/scripts/shufti_compose_mapper.py` |
| 2 | HTTP: `POST /api/map` with `"mode":"compose"` runs mapper, writes run dir | `shufti_ui_server.py` |
| 3 | HTTP: `GET /api/compose/latest` returns diagram **text** + URLs | `shufti_ui_server.py` |
| 4 | Static HTML viewer (tabs, Mermaid render) | `shufti_ui/architecture-viewer.html` |
| 5 | AI-Spy: tab **Architecture (demo)** fetches latest compose + renders Mermaid | `ai-spy/src/components/ArchitectureCouplingMap.tsx` |

**Input file (fixed for LSE):**  
`$REPO_ROOT/LSE-StandAlone-Deployment/standalone-deployment-docker-compose.yml`

**Output files (per run):**  
`$REPO_ROOT/data/shufti_ui_runs/<run_id>/diagrams/high_level_overview.mmd`  
`.../component_coupling.mmd`  
`.../coupling_summary.mmd`  
`.../compose-graph.json`  
`.../snapshot.json` with `"mode": "compose"`

### Prerequisites

- Shufti UI server listening on `127.0.0.1:3005` (process running, not “maybe”).
- `python3` can import `yaml` in the Shufti venv used to start the server.
- Compose file exists: test with `test -f "$REPO_ROOT/$COMPOSE_TARGET"`.

### Verification procedure (run in order)

```bash
# 0) Prerequisite
test -f "$REPO_ROOT/$COMPOSE_TARGET" || echo "FAIL: compose file missing"

# 1) Generate map
curl -sS -X POST "$SHUFTI/api/map" \
  -H 'Content-Type: application/json' \
  -d "{\"targets\":[\"$COMPOSE_TARGET\"],\"mode\":\"compose\",\"format\":\"markdown\",\"generate_diagrams\":true,\"diagram_format\":\"mermaid\"}" \
  | tee /tmp/s0-map.json | jq -e '.ok == true and .run_id != null'

RUN_ID=$(jq -r .run_id /tmp/s0-map.json)
RUN_DIR="$REPO_ROOT/data/shufti_ui_runs/$RUN_ID"

# 2) Files on disk
test -f "$RUN_DIR/diagrams/component_coupling.mmd"
test -f "$RUN_DIR/diagrams/high_level_overview.mmd"
test -f "$RUN_DIR/diagrams/coupling_summary.mmd"
test -f "$RUN_DIR/snapshot.json"
jq -e '.mode == "compose"' "$RUN_DIR/snapshot.json"

# 3) Size / content thresholds (not “many nodes”)
wc -l < "$RUN_DIR/diagrams/component_coupling.mmd" | awk '{ if ($1 < 80) exit 1 }'
grep -c '-->|\["' "$RUN_DIR/diagrams/component_coupling.mmd" | awk '{ if ($1 < 15) exit 1 }'
jq -e '.edges | length >= 20' "$RUN_DIR/diagrams/compose-graph.json"
jq -e '.nodes | map(select(.kind == "service")) | length >= 10' "$RUN_DIR/diagrams/compose-graph.json"

# 4) Latest API
curl -sS "$SHUFTI/api/compose/latest" | jq -e '
  .ok == true
  and .diagrams.component_coupling.text != null
  and (.diagrams.component_coupling.text | length) > 500
'

# 5) Viewer static (HTTP 200)
curl -sS -o /dev/null -w '%{http_code}\n' "$SHUFTI/static/architecture-viewer.html" | grep -q '^200$'
```

### PASS (all required)

1. `POST /api/map` returns HTTP 200, JSON `ok: true`, non-empty `run_id`.
2. Three `.mmd` files exist under `$RUN_DIR/diagrams/`.
3. `snapshot.json` contains `"mode": "compose"`.
4. `component_coupling.mmd` ≥ **80** lines.
5. `compose-graph.json` has **≥ 20** edges and **≥ 10** nodes with `kind == "service"`.
6. `GET /api/compose/latest` returns HTTP 200, `ok: true`, `diagrams.component_coupling.text` length **> 500** characters.
7. `GET /static/architecture-viewer.html` returns HTTP **200**.

### FAIL (any one)

1. `POST /api/map` returns `ok: false` or HTTP ≠ 200.
2. Any of the three `.mmd` paths missing.
3. `component_coupling.mmd` < 80 lines (empty or trivial graph).
4. `compose-graph.json` missing or `edges | length < 20`.
5. `GET /api/compose/latest` 404 or `ok: false`.
6. Mapper never ran (no new directory under `data/shufti_ui_runs/` after POST).

### AI-Spy UI check (optional second terminal; still S0)

Only if AI-Spy UI is built and served (e.g. port **8887** `/ui/ai-spy/`):

1. Open Level 1 → click **Architecture (demo)** (not Live agents).
2. Browser devtools → Network: request to `http://<host>:3005/api/compose/latest` returns 200.
3. Page contains an SVG produced by Mermaid (element with class `mermaid` or `svg` under architecture canvas).

**PASS UI:** steps 1–3 true. **FAIL UI:** tab missing, API 404, or canvas shows only error text from component.

### Evidence to save

- `/tmp/s0-map.json`
- `echo $RUN_ID` → log file
- `wc -l` on three `.mmd` files
- `jq '.edges | length, (.nodes | length)' compose-graph.json`

---

## S1 — Live agent map (daemon + optional Shufti overlay)

### What must work (literal behavior)

| # | Behavior | Mechanism |
|---|----------|-----------|
| 1 | Daemon exposes aggregated areas | Socket.IO event `system_areas` after `emit('get_system_areas')` |
| 2 | At least one area has counts | JSON `areas[0].active_count >= 1` **or** `verified_count >= 1` |
| 3 | Area drill-down returns agents | After `subscribe_area`, event `area_agents` with `agents.length >= 1` |
| 4 | Agent drill-down returns detail | After `get_agent_detail`, event `agent_detail` with `identity.agent_id` |
| 5 | React merge function runs | `buildTopologySectors()` returns array `length >= 1` when daemon payload non-empty |

**Shufti overlay is not required for S1 PASS** — only daemon + drill-down. Overlay is checked in S2.

### Prerequisites

- AI-Spy daemon on **8887** (Socket.IO).
- At least one detectable agent process (Cursor, opencode, etc.) for **15+ seconds** before step 2.
- Shufti **not required** for S1 PASS.

### Verification procedure

**A — Daemon (machine-readable)**

Use Python or `scripts/socketio-health-check.mjs` if present; minimal check:

```bash
# Replace with your project's health script if it exists:
# cd $REPO_ROOT/LSE-Core-2.0-2.1/core/services/agent_enrollment/ai-spy && npm run health:socketio

python3 <<'PY'
import json, socketio
c = socketio.Client()
out = {}
@c.on("system_areas")
def on_areas(data):
    out["areas"] = data.get("areas") or []
@c.on("area_agents")
def on_agents(data):
    out["agents"] = data.get("agents") or []
c.connect("http://127.0.0.1:8887", socketio_path="/socket.io")
c.emit("get_system_areas")
c.sleep(2)
if not out.get("areas"):
    raise SystemExit("FAIL: no system_areas")
a0 = out["areas"][0]
name = a0.get("name") or a0.get("area_name")
if (a0.get("active_count") or 0) + (a0.get("verified_count") or 0) < 1:
    raise SystemExit("FAIL: first area has zero active/verified")
c.emit("subscribe_area", {"area_name": name})
c.sleep(2)
if len(out.get("agents") or []) < 1:
    raise SystemExit("FAIL: area_agents empty")
c.emit("get_agent_detail", {"agent_id": out["agents"][0]["agent_id"]})
c.sleep(2)
print("PASS: daemon areas + agents + detail emit path OK")
c.disconnect()
PY
```

**B — Merge function (no network)**

```bash
cd "$SAI_ROOT"
# After test file exists (S2 may add); for S1 minimal:
# npx vitest run core/topology/topology.test.ts -t "buildTopologySectors returns sectors when areas non-empty"
```

If no test file yet, S1 PASS relies on **A** only; add test in S2.

### PASS (all required)

1. `get_system_areas` → `system_areas` received within **5 s**.
2. `areas.length >= 1`.
3. First area: `active_count + verified_count >= 1`.
4. `subscribe_area` → `area_agents.agents.length >= 1` within **5 s**.
5. `get_agent_detail` → `agent_detail` received within **5 s** with same `agent_id`.

### FAIL (any one)

1. Cannot connect to `127.0.0.1:8887`.
2. `system_areas` missing or `areas` empty array.
3. All areas have `active_count == 0` and `verified_count == 0`.
4. `area_agents` missing or `agents` empty.
5. No agent process running and counts still zero after **60 s** wait (environment not ready — fix env, re-run).

### Evidence to save

- JSON snippet: first `system_areas` payload (redact secrets).
- JSON snippet: `area_agents` for one area.
- Process list command used to show agent running (`ps` / `pgrep`).

---

## S2 — Merge quality (Shufti path ↔ Spy `feature_area`)

### What gets built

| File | Change |
|------|--------|
| `core/topology/topology.ts` | `APP_AREA_HINTS` entries for this monorepo |
| `core/topology/topology.test.ts` | Fixture-driven `buildTopologySectors` expectations |

### Verification

```bash
cd "$SAI_ROOT"
npm test -- --run core/topology/topology.test.ts
```

### PASS

1. Test file exists and **exit code 0**.
2. Test asserts: given fixture `system_areas` (2 areas) + fixture `shuftiAreas` (2 paths), `buildTopologySectors(...).length === 2`.
3. Test asserts: at least **1** sector has `overlaySource === 'hybrid'` or equivalent field your types use (update test to match `topology.ts` export).

### FAIL

1. Tests skipped or not written.
2. `buildTopologySectors` returns `[]` on non-empty fixture.
3. Hints table empty in `topology.ts`.

---

## S3 — Braid wiring

### What gets built

- `braidBridge.ts` subscribes to `system_areas` / `area_update`.
- Each ingest uses `agentKey` = `spy:<entity_id>` (not one global key).

### PASS

1. With bridge running, **≥ 3** ingest lines in log or store within **30 s** with **distinct** `agentKey` values (when **≥ 3** Spy entities active).
2. Each line includes `feature_area` in payload (grep).

### FAIL

1. All ingests use same `agentKey` while multiple entities active.
2. No ingest when daemon emits `system_areas`.

---

## S4 — Assessment metrics

### What gets built

- Markdown table: formula `cost_usd = (input_tokens * price_in + output_tokens * price_out) / 1e6` with model table path.
- Test fixture: inject `tool_call_failed` → band becomes `red` or `orange` (assert enum).

### PASS

1. Doc path listed in repo `docs/` or `core/topology/README.md`.
2. `npm test` / `pytest` for band fixture **exit 0**.

### FAIL

1. Band unchanged when failure fixture applied.

---

## S5 — Sectional contract (types + tests only)

### What gets built

- `core/topology/sectionalTypes.ts`
- `tests/topology/sectional-stitch.test.ts` (or `core/topology/sectional-stitch.test.ts`)

### PASS

1. `npm test` exit **0**.
2. Test builds `StitchedMap` from **2** mock `SectionResult` without HTTP.
3. `StitchedMap.sections.length === 2` and `merged_diagrams.length >= 1`.

### FAIL

1. Types only, no test.
2. Test hits network.

---

## S6 — TypeScript mapper (Lightspeed)

### What gets built

- Mapper analyzes `.ts`, `.tsx`, `.js`, `.jsx` under scan target.

### Verification

```bash
curl -sS -X POST "$SHUFTI/api/map" \
  -H 'Content-Type: application/json' \
  -d "{\"targets\":[\"$SAI_ROOT\"],\"mode\":\"auto\",\"format\":\"json\",\"generate_diagrams\":true,\"diagram_format\":\"mermaid\"}" \
  | tee /tmp/s6-map.json | jq -e '.ok == true'
RUN_ID=$(jq -r .run_id /tmp/s6-map.json)
SNAP="$REPO_ROOT/data/shufti_ui_runs/$RUN_ID/snapshot.json"
jq -e '.file_count >= 5' "$SNAP"    # adjust key name to match actual snapshot schema
# dependency diagram must have edges:
test -f "$REPO_ROOT/data/shufti_ui_runs/$RUN_ID/diagrams/dependency_graph.mmd"
grep -c '-->' "$REPO_ROOT/data/shufti_ui_runs/$RUN_ID/diagrams/dependency_graph.mmd" | awk '{ if ($1 < 3) exit 1 }'
```

### PASS

1. `file_count >= 5` in snapshot (TS/JS files, not 1 Python file).
2. `dependency_graph.mmd` exists with **≥ 3** lines containing `-->`.

### FAIL

1. Only `cursor/precision_timekeeper.py` counted (Python-only scan).
2. `dependency_graph.mmd` has 0 edges.

---

## S7 — Stitch + viewer

### What gets built

- `stitched-map.json` at known path under `shufti_ui_runs/`.
- Viewer URL returns 200 and body includes mermaid from stitch.

### PASS

1. File exists: `.../stitched-map.json` with `sections.length >= 2`.
2. `curl -f` viewer URL succeeds.

### FAIL

1. Manual copy of mermaid required between runs.

---

## S8 — Start script

### What gets built

- `scripts/start-validation-stack.sh`
- `scripts/check-validation-stack.sh` (exit 0 / 1)

### PASS

1. `./scripts/check-validation-stack.sh` exit **0** when Shufti **3005**, Spy **8887**, braid **4711** respond.
2. Exit **1** when Shufti stopped (document in script header).

### FAIL

1. Script starts processes but no check script.

---

## Execution order

```text
S0 (verify) → S1 → S5 ∥ S6 → S7 → S2 → S3 → S4 → S8
```

Waiving a slice: add a line to **Update log** with date + reason; do not mark PASS without checks.

---

## Investigation backlog

| Item | Notes |
|------|--------|
| **Shroud integration** | Investigate Shroud integration with the Shufti / system-map pipeline and MCP stack (Shroud lives under `MCP/` in Lightspeed Engine). Clarify data hooks for map layers, governance or policy signals, and whether Shroud augments topology export vs. a separate overlay channel. **Status:** investigate — after map-polish gate unless operator reprioritizes. |

---

## Update log

| Date | Change |
|------|--------|
| 2026-05-22 | Added investigation backlog: Shroud integration |
| 2026-05-21 | Rev 1 — vague slices |
| 2026-05-21 | Rev 2 — PASS/FAIL commands, S0 build table, S1 daemon-only scope |
| 2026-05-21 | Rev 3 — TDD section, `tests/shufti/*`, GitHub workflow, pre-commit script |
| 2026-05-21 | Rev 4 — SELDER error catalog + JSONL test log; no silent failure gate |
