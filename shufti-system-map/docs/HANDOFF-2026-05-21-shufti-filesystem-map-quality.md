# Handoff: Shufti Filesystem Map Quality (2026-05-21)

**Audience:** Next agent or operator continuing this work  
**Session focus:** Stabilize Shufti runs, clarify product direction, define path to reference-quality filesystem mapping  
**Operator context:** Tailscale remote; Shufti must bind `100.126.175.99:3005` (not localhost-only)

**Active work log (goals, accomplishments, mistakes):** `docs/WORKLOG-2026-05-22-shufti-map-quality.md` — **all phased slices paused** until HQ map polish passes on `:3005`.

---

## 1. Product north star (binding)

The buy/don't-buy surface is **one primary map** that makes the codebase filesystem **obvious, beautiful, and navigable** — a “chessboard / battlefield” operators can trust with their careers on the line.

| Priority | Item |
|----------|------|
| **#1** | Visual + organizational quality of the **filesystem map** (match or exceed reference PNGs in `SAI-Cursor-Validation/docs/`) |
| **#2** | Build and prove quality in **Shufti standalone** first (design studio) |
| **#3** | **Harvest** only needed JS/components into **AI-Spy** + **Cursor webview** (same engine, two shells) |
| Later | Incremental “update agent” (no full redraw on every app open); freemium SKUs |

**Explicitly deprioritized for the main product UI:**

- Full `dependency_graph`, `class_map`, `pattern_map`, `interaction_map` as parallel “product views”
- Those may remain as advanced/export artifacts; **not** what operators stare at daily

**Reference visuals (design target):**

- `docs/Higth-Level-Overview.png` — L1 system map + heat + sidebar concept
- `docs/Coupleing-Summery.png` — grouped module / coupling summary
- `docs/Component-coupleing.png` — component-level coupling

Blue/serious dark theme is fine; purple in compose viewer is acceptable; **mint-green `mermaid-viewer.html` is NOT the product look.**

---

## 2. Architecture decision (do not revert without reason)

```
Shufti Python mapper
  → code_topology.json   (canonical sectors / folders / files / light edges)
  → filesystem_map.*     (ONE primary diagram OR JS-rendered equivalent)

Shufti standalone (JS)     ← establish quality HERE
  → topology-viewer / battlefield UI
  → Tailscale :3005

Harvest when ready:
  → AI-Spy React (Vite, :8887) — live agents, heat, outages overlay
  → SAI-Cursor-Validation VS Code webview — same bundle, Spy socket + cached topology
```

**Why not Mermaid-as-product for large `core` scans:**

- Layout is automatic; flat `flowchart LR` produces orphan columns and squashed class strips
- Compose path already uses `flowchart TB` + subgraphs + `shufti_diagram_theme.py` — **code maps never got that treatment in the main viewer**
- **JS/React sector grid** can do responsive heat, agent pins, outages — better match for “battlefield”

**Webview in Cursor:** Yes, same quality is achievable (Codex Governor pattern: bundled React in webview). See `SAI-Codex-Governor` — Explorer/sidebar webview, not a separate product renderer.

---

## 3. What this session completed

### 3.1 Stability & recovery (Lightspeed upstream)

| Change | Path |
|--------|------|
| Manifest envelope fix (`{"artifacts":[],"errors":[]}` vs legacy list) | `LSE-Core-2.0-2.1/scripts/shufti_run_artifacts.py` (new) |
| Server imports shared parser | `shufti_ui_server.py` |
| Per-diagram try/except; caps (classes, interaction size) | `shufti_code_mapper.py` |
| Recovery ladder on mapper failure/timeout | `shufti_ui_server.py` (`attempt_mapper_recovery`) |
| Dependency orphans → subgraph; theme wrap for mermaid | `shufti_code_mapper.py` + `shufti_diagram_theme.py` |
| Client recovery hints | `shufti_ui/app.js` |
| Offline tests | `SAI-Cursor-Validation/tests/shufti/s0/test_run_artifacts.py` |

**Tests:** `bash scripts/run-shufti-slice-tests.sh offline` — 13 passed (includes new manifest tests).

**Server:** Restarted on `100.126.175.99:3005` (venv: `LSE-Shufti_venv`). Old process exit 137 from `fuser -k` during restart is expected.

### 3.2 Operator verification

- User confirmed maps **work again** after restart; colors still **old** (mint/white viewer) — expected until quality slice ships.

### 3.3 NOT completed (still the #1 workstream)

- `topology-viewer.html` / JS battlefield map
- `code_topology.json` export from mapper
- Package-grouped `filesystem_overview` as **the** default diagram
- Dark overhaul of `mermaid-viewer.html` (secondary)
- `topology_viewer_url` / auto-open from main UI
- AI-Spy component harvest
- Cursor webview panel
- Incremental update agent (user said: **after** quality)

---

## 4. Runtime & paths

| Item | Value |
|------|--------|
| Shufti UI | `http://100.126.175.99:3005/` |
| Shufti server | `/mnt/lightspeed-data/Lightspeed-Engine/LSE-Core-2.0-2.1/scripts/shufti_ui_server.py` |
| Venv | `/mnt/lightspeed-data/Lightspeed-Engine/LSE-Shufti_venv` |
| Runs archive | `/mnt/lightspeed-data/Lightspeed-Engine/data/shufti_ui_runs/<run_id>/` |
| AI-Spy daemon | `:8887` (Socket.IO); React UI `npm run dev` in `core/services/agent_enrollment/ai-spy/` |
| Strategy / plan | `SAI-Cursor-Validation/docs/SHUFTI-AISPY-IMPLEMENTATION-STRATEGY.md`, `PLAN-2026-05-21-shufti-aispy-phased-slices.md` |

**Restart Shufti:**

```bash
fuser -k 3005/tcp 2>/dev/null; sleep 1
cd /mnt/lightspeed-data/Lightspeed-Engine/LSE-Core-2.0-2.1/scripts
/mnt/lightspeed-data/Lightspeed-Engine/LSE-Shufti_venv/bin/python shufti_ui_server.py --host 100.126.175.99 --port 3005
```

**Run tests (validation repo):**

```bash
cd /home/legion/SAI-Cursor-Validation
bash scripts/run-shufti-slice-tests.sh offline
```

---

## 5. Current UI map (avoid confusing operator)

| Surface | Role | Product? |
|---------|------|----------|
| `shufti_ui/index.html` | Browse targets, generate map | Control panel |
| `mermaid-viewer.html` | Opens per-diagram `.mmd` from code mapper | Legacy diagram viewer (green/white) |
| `architecture-viewer.html` | Compose topology tabs | Compose only; **closest** to target look |
| AI-Spy `TopologyMap.tsx` | Sector cards + Spy/Shufti merge | **Harvest target** for L1 grid |
| AI-Spy `ArchitectureCouplingMap.tsx` | iframe/embed compose from Shufti API | Deployment topology |

**“Open generated diagrams”** in main UI still targets mermaid-viewer — **not** the future filesystem product view.

---

## 6. Recommended next implementation slice (quality)

### Step A — Canonical data (`shufti_code_topology.py` or extend mapper)

Emit per run under `diagrams/` or run root:

- `code_topology.json`
  - `sectors[]`: id, label, path, file_count, line_count, stub_count
  - `nodes[]`: files with path, module, metrics
  - `edges[]`: light edges (import/coupling), package-level aggregates optional
  - `views.filesystem_overview.mermaid` OR skip mermaid entirely for product

**Grouping rule:** Top-level package or directory segment (e.g. `core.services`, `core.common`, `scripts`) — mirror `render_coupling_summary` pattern in `shufti_compose_mapper.py`.

### Step B — Standalone JS viewer (`shufti_ui/filesystem-map.html` + module)

- Dark ops theme (reuse CSS tokens from `architecture-viewer.html`)
- Tabs: **Filesystem overview** (only required tab initially)
- Sidebar: file path, lines, stubs, patterns summary on click
- Optional: fetch `/api/topology/latest?run_id=` (endpoint **not yet implemented**)

### Step C — Server API

- `GET /api/topology/latest?run_id=`
- Add `topology_viewer_url` and `filesystem_map_url` to `execute_map_request` success payload
- `app.js`: auto-open topology viewer instead of mint mermaid tabs for code maps

### Step D — Mapper defaults

- `generate_diagrams`: default **one** diagram spec: `filesystem_overview` only (or `diagram_profile: filesystem`)
- Skip or gate `interaction_map` / `class_map` behind flag `advanced_diagrams=false`
- Prefer `diagram_format: dot` + SVG for export; product UI is JS

### Step E — AI-Spy harvest (after B is loved)

- Shared `topology.json` loader in `ai-spy/src/`
- Replace or augment flat sector cards with data from latest Shufti run
- Keep `buildTopologySectors` overlay logic in `ai-spy/src/topology.ts`

### Step F — Cursor webview (after E)

- Package shared UI into `SAI-Cursor-Validation/cursor-activity` or new extension view
- Load same JS; connect Spy socket for live layer

---

## 7. AI-Spy integration contract (for harvest)

**Existing merge:** `buildTopologySectors(systemAreas, shuftiAreas, shuftiDiscoveredAreas)` in `ai-spy/src/topology.ts`.

**Shufti client:** `ShuftiTopologyClient` — `areas:list`, `discover:areas` via socket; HTTP `getShuftiStandaloneUrl()` default port 3005.

**To add:**

- HTTP `GET {shufti}/api/topology/latest?run_id=` returning `code_topology.json` + diagram URLs
- Align sector `id` / `path` with Spy `feature_area` / `APP_AREA_HINTS` in `topology.ts`

**ArchitectureCouplingMap** already calls `{shufti}/api/compose/latest` and `{shufti}/api/map` — pattern for new endpoint.

---

## 8. Incremental updates (deferred)

User intent: after full render exists, only an **update agent** checks drift — **do not redraw entire map on every app open**.

Not implemented. Suggested approach for future doc:

- Persist `content_hash` per file in snapshot
- `GET /api/topology/status?run_id=` → `{changed: bool, delta_summary}`
- Background job or on-demand diff → patch sectors / re-render affected subgraph only

---

## 9. Known issues / regressions to avoid

| Issue | Cause | Fix state |
|-------|--------|-----------|
| `string indices must be integers, not 'str'` | Iterating manifest dict keys | Fixed via `shufti_run_artifacts.py` + tests |
| Empty run dirs | Mapper failed before recovery | Recovery + `mapper_failure.json` |
| `interaction_map` Mermaid size error | Too large | Skip in recovery; cap/truncate in mapper |
| Tailscale unreachable | Server on 127.0.0.1 only | Bind `100.126.175.99` |
| Ugly code diagrams | `mermaid-viewer` theme + flat LR layout | Quality slice |

---

## 10. Files touched this session (Lightspeed)

- `LSE-Core-2.0-2.1/scripts/shufti_run_artifacts.py` (**new**)
- `LSE-Core-2.0-2.1/scripts/shufti_ui_server.py`
- `LSE-Core-2.0-2.1/scripts/shufti_code_mapper.py`
- `LSE-Core-2.0-2.1/scripts/shufti_diagram_theme.py` (partial — `wrap_mermaid_diagram`, `code_map_class_defs`)
- `LSE-Core-2.0-2.1/scripts/shufti_ui/app.js`

**SAI-Cursor-Validation:**

- `tests/shufti/s0/test_run_artifacts.py` (**new**)

**Not created yet (highest value):**

- `shufti_code_topology.py`
- `shufti_ui/filesystem-map.html` (or `topology-viewer.html` rename/expand)
- `GET /api/topology/latest`

---

## 11. Compose mapper as layout reference

Copy patterns from:

- `shufti_compose_mapper.py` → `render_coupling_summary`, `render_high_level_overview` (`flowchart TB`, subgraphs, `_style_prelude`, classDefs)
- `shufti_ui/architecture-viewer.html` → dark chrome, mermaid init, edge pill CSS

Do **not** copy mint `mermaid-viewer.html` theme for product work.

---

## 12. Operator quotes (intent)

- “Most beautiful, well organized professional file system mapping imaginable”
- “Quality and polish = love or hate / buy or don't buy”
- “Standalone first, then harvest for AI-Spy; JS for heat/outages/responsive battlefield”
- “One map that makes sense — not all dependency/class views”
- “Don't redraw every time app opens — update agent later”
- “Freemium later; marketing SKUs later”

---

## 13. Suggested first message to next agent

> Read `SAI-Cursor-Validation/docs/HANDOFF-2026-05-21-shufti-filesystem-map-quality.md`. Implement Step A+B+C: `code_topology.json`, package-grouped filesystem overview, standalone JS viewer on :3005, `/api/topology/latest`. Do not expand dependency/class diagrams. Match reference PNGs. Confirm with user on Tailscale before claiming done.

---

## 14. Transcript

Parent session: `ca95b8ae-3ec4-45e2-a424-09e23ba7cd08` (Cursor agent transcripts).

---

*End of handoff — thank you to the operator for clear product direction; stability work is done, quality work is explicitly scoped and unblocked.*
