# Work log: Shufti HQ map quality (2026-05-22)

## 2026-05-22 — Milestone preservation + layered viewer

- **Viewer:** explicit SVG layers + Map controls panel (orthogonal edges default, stub metrics on boxes/sidebar, `localStorage` prefs).
- **Git bundle:** `shufti-system-map/` with upstream snapshot — tag `shufti-map-2026.05.22-milestone`.
- **GitLab:** `shufti-system-map/docs/PUSH-GITLAB.md` (`gitlab.lightspeed.internal:2222` when DNS/VPN available).

**Operator gate (binding):** No further phased slices (Braid S3, ephemeral agent IDs, AI-Spy harvest, extension webview, assessment) until **filesystem/component map UI** meets reference polish on **Shufti standalone** (`http://100.126.175.99:3005`). Release bar: map quality first; infrastructure can work and still not ship.

**Related docs:** `HANDOFF-2026-05-21-shufti-filesystem-map-quality.md`, `SHUFTI-AISPY-IMPLEMENTATION-STRATEGY.md`, `PLAN-2026-05-21-shufti-aispy-phased-slices.md` (slices **paused**).

---

## Current goals

| # | Goal | Done when |
|---|------|-----------|
| G1 | **HQ system map render** — lane layout, component boxes, labeled coupling edges, dark ops theme (reference: `docs/Higth-Level-Overview.png`, `docs/Component-coupleing.png`) | Operator says standalone viewer matches reference bar |
| G2 | **Component drill-down** — sidebar: metrics, top files, patterns; not a bare file list under card grid | Same |
| G3 | **Sensible component granularity** — e.g. `core.services.agent_enrollment`, not two blobs `mnt.lightspeed-data` / `home.legion` | `sector_count` ≫ 2 on `core`-only map; package edges visible |
| G4 | **Shufti auto-opens product viewer** after map run (not mint-green mermaid as default) | One map on `core` → topology viewer is first surface |
| G5 | **Stable mapper runs** — no manifest/envelope regressions | `run-shufti-slice-tests.sh offline` green |

**Parked until G1–G4 pass:** Braid per-entity keys, `evidence.agent`, AI-Spy overlay, Cursor webview bundle, incremental update agent.

---

## Reference bar (visual)

- Dark navy / purple-accent theme (`architecture-viewer.html` style), **not** `mermaid-viewer.html` mint-green.
- Graph: components as cards in role lanes; edges with relation/weight pills.
- Sidebar on selection (coupling summary + file drill-down).

---

## Key paths

| Item | Path |
|------|------|
| Shufti server | `/mnt/lightspeed-data/Lightspeed-Engine/LSE-Core-2.0-2.1/scripts/shufti_ui_server.py` |
| Topology export | `shufti_code_topology.py` |
| Product viewer (today) | `shufti_ui/topology-map-viewer.html` |
| Prototype SVG renderer | `SAI-Cursor-Validation/core/topology/webview/validation-map.js` |
| Sample run | `data/shufti_ui_runs/20260522T005139Z-922b75fa/diagrams/` |

---

## Log (newest first)

### 2026-05-22 — Operator validation: “miles better” (screenshot)

**Accomplishments**

- Operator confirmed **topology-map-viewer** works after Shufti restart (`100.126.175.99:3005`).
- Example run on `LSE-Core-2.0-2.1/core`: **49 components**, **23 coupling edges**, lane layout (Gateway → Support), sidebar drill-down (e.g. `services · talons_hub` file list).
- Raw `.mmd` download confusion understood; **system map URL** is the correct path.

**Not perfect (operator + visual gap vs reference PNGs)**

- Layout density / overlap on large `core` scans; edge labels all `package_import` (not relation variety like compose reference).
- Visual polish vs `Higth-Level-Overview.png` / `Component-coupleing.png` still short of “career on the line” bar.
- **Gate unchanged:** no phased slices (Braid/Spy harvest) until operator signs off on next polish tranche.

**Screenshot:** `Screenshot_2026-05-22_at_4.57.54_AM` (workspace assets).

---

### 2026-05-22 — HQ viewer + sector grouping (Cursor)

**Accomplishments**

- Created this work log and linked it from `HANDOFF-2026-05-21-shufti-filesystem-map-quality.md`.
- **`shufti_code_topology.sector_key_for_module`:** path-aware grouping (`core.services.<name>`, `core.common`, `sai.*`) so maps are not mount-path blobs.
- **`topology-map-viewer.html`:** rebuilt as primary product surface — SVG lane system map (from `system_map` / `views.system_overview`), purple edge relation pills, heat-filled components, right sidebar drill-down; sector grid + mermaid export demoted to secondary tabs.
- **Tests:** `tests/shufti/s0/test_sector_key.py` (3 cases); offline slice suite **16/16** pass (was 13 before this file).

**Mistakes / risks**

- **Not re-run** full `core` map on server yet — operator must restart Shufti and generate a new run to see improved sectors/edges in the UI (old runs still show 2-blob topology).
- **Edge count** may still be low until a fresh mapper pass rebuilds `package_edges` with new sector ids; unverified on live run.
- **HQ bar** not operator-approved — closer to reference PNGs but not a sign-off.

**Next**

- Operator: restart Shufti on `:3005`, map `LSE-Core-2.0-2.1/core`, open `topology_map_viewer_url` from success payload.
- If component count still low, tune `derive_analysis_root` / import graph in mapper (separate log entry).

---

### 2026-05-22 — Session start: goals + audit (Cursor)

**Accomplishments**

- Captured operator **release gate** and paused slice plan in this work log.
- Audited current surfaces:
  - `topology-map-viewer.html` = sector **card grid only**; does not render `system_map` / `views.system_overview` from API.
  - `validation-map.js` already implements **lane SVG + edges + sidebar** (intended HQ pattern) but lives only in validation repo webview, not Shufti `:3005`.
  - `GET /api/topology/latest` returns `topology`, `system_map`, `webview_contract` (server wiring exists).
  - Latest sample run `20260522T005139Z-922b75fa`: **2 sectors**, **`package_edge_count`: 0**, `views.system_overview.edges`: `[]` — data too coarse for reference PNGs even with a perfect renderer.

**Mistakes / gaps**

- Prior Cursor turn **started** HQ viewer work but **did not ship** viewer changes before context handoff; operator correctly called out uncertainty on ephemeral-ID docs (answered separately; not in scope until map gate passes).
- Tool calls **interrupted** mid-audit once (grep/read timeout); re-ran selectively — no code harm, delayed picture.
- Initial wrong assumption: `views` empty in topology JSON — actually populated under `views.system_overview`; API also exposes `system_map.json`. Confusion came from checking top-level `topology` key vs nested `views`.

**Next actions (superseded by entry above)**

1. ~~Fix sector grouping~~ — done in code; needs **new map run** on server.
2. ~~Upgrade topology-map-viewer~~ — done in code; needs server restart + new run.
3. Operator verify on `:3005` (see checklist below).

---

## Operator FAQ — `.mmd.crdownload` in Downloads

**What happened:** Shufti created `filesystem_overview.mmd` correctly. Chrome treated a link to the **raw artifact URL** (`/artifacts/.../filesystem_overview.mmd`) as a **file download**, hence `filesystem_overview.mmd.crdownload` in Downloads. That is **not** the product map.

**What to open instead:** the **HTML viewer** (no special file extension on disk):

`http://100.126.175.99:3005/static/topology-map-viewer.html?run_id=20260522T114511Z-f0d4eb52`

(Replace `run_id` with your run from **Recent Runs** or the status line after **Generate Map**.)

**UI fix (in repo):** Auto-open and artifact links now prefer **system map** viewer; `.mmd` is labeled **export .mmd** only. Restart Shufti + hard-refresh after pulling UI changes.

---

## Operator FAQ — “Do I generate Mermaid?”

**No.** Mermaid/DOT are **export/diagnostic** formats only. The product map is **`code_topology.json`** rendered by **`topology-map-viewer.html`** (SVG system map).

| Control in Run Controls → **Diagram output** | What to set |
|---------------------------------------------|-------------|
| **Diagram scope** | `filesystem (recommended)` — emits `code_topology.json` + `system_map.json` |
| **Diagram source** | Mermaid or DOT — **either is fine**; only changes the optional `.mmd`/`.dot` export, not the HQ viewer |
| **Open with** | `Shufti filesystem map` or `Auto (smart)` — opens the JS battlefield viewer |
| **Open after run** | checked |

If you only see Mermaid/DOT and not **Diagram scope** / **Open with**, the server is serving **old static UI** — restart Shufti on `:3005` and hard-refresh the browser (`Ctrl+Shift+R`).

After a successful run, you can also open **`topology_map_viewer_url`** from the response or click artifact **`code_topology`** → API link, or artifact link that opens the filesystem map tab.

---

## PASS / FAIL checklist (operator)

- [x] Open `topology-map-viewer.html?run_id=…` after `core` map — **not** 2 giant cards / mint mermaid (2026-05-22 operator OK).
- [x] Click component — sidebar shows files, lines, coupling counts.
- [x] At least ~8–15 components for full `core` scan (**49** observed).
- [x] Visible package/import edges between components (**23** observed).
- [ ] Visual match to reference PNGs (layout, edge pill copy, heat, sidebar richness) — **partial**; operator: “not perfect but miles better.”
