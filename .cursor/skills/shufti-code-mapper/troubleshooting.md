# Shufti troubleshooting

## Server will not start

| Symptom | Check | Fix |
|---------|-------|-----|
| `Shufti server not found` | `SHUFTI_SERVER` / `LIGHTSPEED_ROOT` | Point at `shufti_ui_server.py` |
| `No such file` for python | `LSE-Shufti_venv` | Install or set `SHUFTI_PYTHON` |
| Address already in use | `ss -tlnp \| grep 3005` | Stop duplicate process or change `SHUFTI_UI_PORT` |
| Import errors on start | Run server in venv | Use `LSE-Shufti_venv/bin/python` only |

## UI loads but areas empty

1. Emit `areas:list` — if `ok: false`, read server log (UI exposes log links).
2. Run `discover:areas` with correct workspace `root` (must be absolute path operator can read).
3. Confirm mapper completed — check `data/shufti_ui_runs/` for new run dir.

## discover:areas hangs or fails

- Tree too large: wait for `discover:areas:queued` then response.
- Permission denied on `root`: fix path or permissions.
- Single-file parse errors: mapper should skip bad files; check server log for `discover:areas:error`.

## AI-Spy map shows only `daemon only` (no Shufti)

- Shufti not running on port client expects (`SHUFTI_URL` / Vite env).
- `feature_area` paths do not align with Shufti `path` — tune `APP_AREA_HINTS` in `core/topology/topology.ts`.
- Client never received `areas:list:response` — CORS/host mismatch (use same host as browser or Tailscale IP consistently).

## Remote access (Tailscale)

- Bind with `SHUFTI_UI_HOST=<tailscale-ip>` (upstream default in `run_shufti_ui.sh`).
- Firewall must allow **3005** on that interface.
- React/TS clients must use the same base URL, not `127.0.0.1`, when viewing from another machine.

## Async / threading issues

- Default `SHUFTI_UI_ASYNC_MODE=threading`. If event loop errors appear, try documented alternative in server comments (do not change without reading `shufti_ui_server.py` startup).
