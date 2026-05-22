# Shufti system map viewer — changelog

Pin a release with `git tag shufti-map-<version>` after updating `VERSION` and syncing `viewer/` + `upstream/shufti_ui/topology-map-viewer.html` from Lightspeed deploy path.

## 2026.05.22-v3.7-drilldown (current)

- **Viewer:** `viewer 2026.05.22-v3.7-drilldown` in subtitle before API load; click component → **file drill-down** on canvas (grid of files + internal file edges); click empty canvas → system map
- **Topology:** `edges.inheritance` / `dependency_layers.inheritance` from class `bases`; `module_to_sector_map` fixes basename-only sector bug (restores coupling on archived `core/` layouts)
- **Mapper:** path-suffix import index + `direct_dependency_paths` in `collect_dependency_edges`
- Tests: `tests/shufti/s0/test_module_to_sector.py`, `test_inheritance_edges.py`

## 2026.05.22-v3.6-focus (tag `shufti-map-2026.05.22-v3.6-focus`)

- **Parallel strands:** import weight → up to 12 lines per coupling (reference image semantics)
- **Relation layers:** Coupling (violet) / External hub (dashed) / Inheritance (green, when topology emits)
- **Focus:** dim off-path boxes and edges; accent via Focus color; click sidebar coupling row → single-path highlight
- **Sidebar half-drill-down:** Coupling + Imports by file + AI agent slots; map boxes title-only by default
- **Line legend** in controls; `dimOnFocus` on by default
- External edges collapsed to hub (performance); orthogonal backward routes retained

## 2026.05.22-v3.3-deps

- Topology **1.2.0**: `edges.external`, `edges.unresolved`, `dependency_layers`, per-file `imports` in drill-downs (`shufti_code_topology.py`)
- Viewer: toggles **Internal coupling** vs **External/stdlib** (hub node on right); unresolved imports in sidebar (not map lines)
- Research doc: `docs/RESEARCH-2026-05-21-shufti-api-route-detection.md` (API/OpenAPI feasibility — out of scope until next phase)

## 2026.05.22-v3.2 (tag `shufti-map-2026.05.22-v3.2`)

- **Edges visible:** draw above boxes by default; brighter SVG strokes; backward imports use curved routes
- **Dim non-neighbors** off by default (was confusing on open); only dims when selection has connected edges
- **Zero-edge runs:** banner shows `run_id` and hints to pick a run with coupling data
- `systemMapFromPayload` falls back to `topology.edges.packages` when `system_map.edges` empty
- Map badge: `N coupling edges drawn`; click empty canvas clears selection
- `VIEWER_BUILD` stamp in subtitle for rollback checks

## 2026.05.22-v3 (tag `shufti-map-2026.05.22-v3`)

- Grid A* routing with obstacle avoidance (no paths through box borders)
- Edge crossing hop arcs (inverted-U style)
- Fan-out lane ordering from shared sources
- **Color & focus** panel: heat / role / neutral fills, focus color, highlight neighbors + connected edges, dim others, selection glow
- Map controls persist in `localStorage` (`shufti-map-viewer-prefs-v2`)
- `scripts/restart-shufti-ui.sh` for operator restarts

## 2026.05.22-milestone (tag `shufti-map-2026.05.22-milestone`)

- Initial preservation bundle in `SAI-Cursor-Validation`
- Sector-aware topology (`shufti_code_topology.py`)
- Layered SVG viewer v1, orthogonal edges, stub metrics on boxes
- Commit `ce80b56`

## Rollback

```bash
# Git (validation repo) — one step back
git checkout shufti-map-2026.05.22-v3 -- shufti-system-map/viewer/topology-map-viewer.html
cp shufti-system-map/viewer/topology-map-viewer.html \
  /mnt/lightspeed-data/Lightspeed-Engine/LSE-Core-2.0-2.1/scripts/shufti_ui/topology-map-viewer.html
./scripts/restart-shufti-ui.sh

# Milestone (layered viewer v1)
git checkout shufti-map-2026.05.22-milestone -- shufti-system-map/viewer/topology-map-viewer.html
cp shufti-system-map/viewer/topology-map-viewer.html \
  /mnt/lightspeed-data/Lightspeed-Engine/LSE-Core-2.0-2.1/scripts/shufti_ui/topology-map-viewer.html
./scripts/restart-shufti-ui.sh
```
