# Shufti system map viewer — changelog

Pin a release with `git tag shufti-map-<version>` after updating `VERSION` and syncing `viewer/` + `upstream/shufti_ui/topology-map-viewer.html` from Lightspeed deploy path.

## 2026.05.22-v3.2 (current)

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
