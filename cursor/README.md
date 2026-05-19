# Cursor — governed activity correlator

Design and implementation track for **live operational truth** in Cursor (hooks + optional proxy + IDE timeline). Aligns with the product-first [DEC-2026-04-25](file:///mnt/lightspeed-data/Lightspeed-Engine/LSE-StandAlone-Deployment/REALIGNMENT-2026-04-19/architecture/DEC-2026-04-25-governed-runtime-sdk-extension-ecosystem.md).

## Documents

| File | Description |
|------|-------------|
| [DESIGN-2026-05-18-governed-activity-correlator.md](./DESIGN-2026-05-18-governed-activity-correlator.md) | Architecture: observation positions, event schema, extension role |
| [PLAN-2026-05-18-governed-activity-correlator.md](./PLAN-2026-05-18-governed-activity-correlator.md) | Phases, goals, deliverables, status |
| [FEATURE-CHECKLIST-2026-05-18.md](./FEATURE-CHECKLIST-2026-05-18.md) | **Your** tick-box acceptance per feature |
| [../cursor-activity/README.md](../cursor-activity/README.md) | Phase 2 VSIX — F5 / install |

## Precision time (local)

| File | Description |
|------|-------------|
| [precision_timekeeper.py](./precision_timekeeper.py) | NTP anchor + monotonic extrapolation for JSONL `ts` fields (no Redis/elections) |

Canonical upstream copy lives in LSE:

`LSE-Core-2.0-2.1/core/services/sigchain_adapter/precision_timekeeper.py`

Hook scripts can stamp events:

```bash
pip install ntplib   # once per environment
python3 -c "import asyncio; from precision_timekeeper import initialize_default, now_ms; asyncio.run(initialize_default()); print(now_ms())"
```

Run from this directory or set `PYTHONPATH` to `sai-extensions/cursor`.

## Hook kit (Phase 1)

```
cursor/
  hooks.json.example              # copy → .cursor/hooks.json
  scripts/hooks/
    append-activity.js            # normalize + append JSONL
    append-activity.sh            # wrapper (sets ACTIVITY_PROJECT_ROOT)
    redact.js                     # strip tokens / secrets
    log-spike.sh                  # optional raw spike logger
  scripts/install-project-hooks.sh
.cursor/                          # installed in sai-extensions (this repo)
  hooks.json
  hooks/append-activity.sh
```

**Activity log:** `.cursor/activity/activity.jsonl` (gitignored)

**Install into another repo:**

```bash
cd /path/to/your-repo
bash /path/to/sai-extensions/cursor/scripts/install-project-hooks.sh .
chmod +x .cursor/hooks/append-activity.sh
```

**Automated phase tests (regression — runs Phase 0 through N):**

```bash
cd /home/legion/sai-extensions
bash cursor/scripts/run-phase-tests.sh      # through Phase 2
bash cursor/scripts/run-phase-tests.sh 1    # phases 0 + 1 only

# Strict: fail if no live Agent log yet
ACTIVITY_REQUIRE_LIVE=1 bash cursor/scripts/run-phase-tests.sh 1
```

**CI:** GitHub Actions (`.github/workflows/activity-correlator.yml`) or GitLab (`.gitlab-ci.yml` at repo root). Both run the same `run-phase-tests.sh 2` on push/PR. Use one host; delete or ignore the other file if unused.

**Live log report only:**

```bash
bash cursor/scripts/validate-live.sh
```

## Phase 2 — `cursor-activity` VSIX

Sibling package: [`../cursor-activity/`](../cursor-activity/)

- Tails `.cursor/activity/activity.jsonl` (file watch + poll)
- **Activity** sidebar: Timeline webview + Instruction Context tree
- Status bar: session, event count, log path
- Commands: *Governance: Sample Git Status/Diff*, refresh, open log

```bash
cd cursor-activity && npm install && npm run compile
# F5 in cursor-activity folder for Extension Development Host
```

## Planned (later phases)

```
cursor/scripts/proxy/             # Phase 3 optional per-agent port proxy
```

## Activity log (per project)

When hooks are installed, events append to:

`.cursor/activity/activity.jsonl`

Add that path to the project `.gitignore` (sensitive audit data).

## Other material in this folder

- `cursor_pi_mono_profiles_and_agent_integ.md` — earlier notes on Cursor / Pi profiles (reference only)

## Quick start

1. Ensure `.cursor/hooks.json` exists (this repo already has it, or run `install-project-hooks.sh`).
2. `chmod +x .cursor/hooks/append-activity.sh`
3. Reload the workspace in Cursor (hooks reload on config change).
4. Run an Agent session; inspect `.cursor/activity/activity.jsonl`.
5. Run `bash cursor/scripts/validate-live.sh` to confirm live data (see report JSON).

Debug only: `ACTIVITY_SPIKE_ENABLED=1` writes duplicate raw lines to `/tmp/cursor-hook-spike.jsonl`.

See [SPIKE-2026-05-18-hooks.md](./SPIKE-2026-05-18-hooks.md) and [PLAN-2026-05-18-governed-activity-correlator.md](./PLAN-2026-05-18-governed-activity-correlator.md).
