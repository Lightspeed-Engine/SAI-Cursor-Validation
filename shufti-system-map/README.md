# Shufti System Map

Preservation bundle for the **Shufti filesystem / component map** milestone (May 2026). This directory is the canonical snapshot for version control while upstream runtime remains under Lightspeed Engine.

## What this is

- **Product surface:** HTML/SVG system map (`viewer/topology-map-viewer.html`), not Mermaid downloads.
- **Data:** `code_topology.json` + `system_map.json` per run under `data/shufti_ui_runs/`.
- **Runtime (deployed):** `upstream/shufti_ui_server.py` + `upstream/shufti_ui/` on port 3005.

## Milestone features (2026-05-22)

- Sector-aware topology (`shufti_code_topology.py`)
- Layered SVG renderer with **Map controls** panel (layers, orthogonal edges, stub metrics)
- Reference-aligned polish track (see `docs/HANDOFF-2026-05-21-shufti-filesystem-map-quality.md`)

## Upstream paths (Lightspeed Engine)

| Role | Path |
|------|------|
| Server | `/mnt/lightspeed-data/Lightspeed-Engine/LSE-Core-2.0-2.1/scripts/shufti_ui_server.py` |
| Topology | `/mnt/lightspeed-data/Lightspeed-Engine/LSE-Core-2.0-2.1/scripts/shufti_code_topology.py` |
| Viewer | `/mnt/lightspeed-data/Lightspeed-Engine/LSE-Core-2.0-2.1/scripts/shufti_ui/topology-map-viewer.html` |

After pulling this repo, sync `viewer/` and `upstream/` back to those paths before restarting Shufti.

## Run locally

```bash
cd upstream
/path/to/LSE-Shufti_venv/bin/python shufti_ui_server.py --host 127.0.0.1 --port 3005
```

Open: `http://127.0.0.1:3005/static/topology-map-viewer.html?run_id=<run_id>`

## Tests

From SAI-Cursor-Validation root:

```bash
pytest tests/shufti -m offline
```

## Version

See `VERSION` — tag releases from this bundle to avoid map regressions.
