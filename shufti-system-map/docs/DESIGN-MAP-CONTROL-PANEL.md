# Map control panel — UX design note

## Problem

The map accumulates orthogonal layers (grid, lanes, edges, labels, heat, stubs, live overlays). A single legend cannot hold toggles and debug knobs without cluttering the canvas.

## Recommendation: right-rail **Map controls** (shipped v1)

- **Placement:** Third column on wide screens; collapses below canvas on narrow viewports. Component drill-down stays in the middle column.
- **Persistence:** `localStorage` key `shufti-map-viewer-prefs-v1` (browser-local; fine for debug, not for team defaults).
- **Sections:**
  1. **Layers** — visibility only (grid, lanes, edges, edge labels, components).
  2. **Display** — heat fill, stubs on boxes, glow, edges-on-top, edge style (orthogonal / bezier), edge thickness S/M/L.
  3. **Debug** — anchor ports (more to come: layout grid coords, bounding boxes).

Release builds can hide section 3 and trim section 2 to heat + dependencies + stubs.

## Future: settings **drawer** + **URL hash**

For shareable views (reviews, CI artifacts):

- Encode minimal state in hash: `#layers=edges,components&edge=orthogonal&focus=common`
- Optional server-side `viewer_prefs.json` per run for team defaults.

## Stub / anatomy stats (next data phases)

| Stat | Source | UI |
|------|--------|-----|
| Stub count | mapper AST | box + sidebar + sector grid |
| Stub density | stubs/lines×1k | sidebar pill |
| Classes / interfaces | indexer (new) | drill-down tab “Symbols” |
| Public APIs | import/export graph | layer toggle “API surface” |

Toggles should map 1:1 to layers or overlay channels, not duplicate metrics in legend only.

## Line budget (server)

Adaptive scan: try requested budget → on OOM/timeout bisect → return `ok: false` with `max_lines_observed` and `recovery_attempts[]` (pattern already used for mapper recovery). Client shows in map run banner.

## Drill-down without full rescan

Reuse archived `code_topology.json` when `topology_fingerprint` unchanged; client filters subgraph and re-layouts (focus root). Server remap only when fingerprint or mtime set changes.
