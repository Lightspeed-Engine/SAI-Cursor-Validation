# HANDOFF: Governed activity correlator + precision time

**Date:** 2026-05-18  
**Status:** Phase 0–1 done (live log); Phase 2 VSIX built—**your sign-off pending** via [FEATURE-CHECKLIST](./FEATURE-CHECKLIST-2026-05-18.md)  
**Owner context:** Product-first Cursor/CLI extensions (`sai-extensions`); avoid LSE gateway/MCP as v0 dependency

---

## Goal

**Live operational truth** for agent sessions: multiple observation sources on one timeline (hooks, optional proxy, terminal, sampled `git`/find)—not post-hoc “did the paragraph match git?”

---

## Artifacts (where things live)

| Path | Purpose |
|------|---------|
| `sai-extensions/cursor/DESIGN-2026-05-18-governed-activity-correlator.md` | Architecture |
| `sai-extensions/cursor/PLAN-2026-05-18-governed-activity-correlator.md` | Phased implementation |
| `sai-extensions/cursor/README.md` | Index |
| `sai-extensions/cursor/precision_timekeeper.py` | **Working copy** — NTP + monotonic `ts` for JSONL |
| `sai-extensions/cursor/HANDOFF-2026-05-18-activity-correlator.md` | This file |
| `sai-extensions/cursor/FEATURE-CHECKLIST-2026-05-18.md` | **Your** acceptance checklist per phase |
| `sai-extensions/cursor-activity/` | Phase 2 VSIX (timeline UI) |

**LSE canonical time code**

| Path | Purpose |
|------|---------|
| `LSE-Core-2.0-2.1/.../sigchain_adapter/precision_timekeeper.py` | Standalone clock (edit here first) |
| `LSE-Core-2.0-2.1/.../sigchain_adapter/time_authority.py` | Refactored cluster (~730 lines); composes keeper |
| `LSE-Core-2.0-2.1/.../sigchain_adapter/time_authority.py.backup-20260518-original` | Frozen pre-refactor (~1017 lines) |

**Related DEC (sequencing only):**  
`LSE-StandAlone-Deployment/REALIGNMENT-2026-04-19/architecture/DEC-2026-04-25-governed-runtime-sdk-extension-ecosystem.md`

---

## Architecture (one paragraph)

Cursor **hooks** append JSONL → `.cursor/activity/activity.jsonl`. Extension `cursor-activity/` tails log + shows timeline + workspace rules context. Optional **per-agent HTTP proxy** for API metadata. **No workspace file watchers.** Stamp events with `precision_timekeeper` (`ts` ISO-8601 / ms). Cluster elections stay in LSE `time_authority.py`; correlator uses **local keeper only**.

---

## Cursor data sources (v0)

| Source | Collects |
|--------|----------|
| Hooks (`postToolUse`, `afterShellExecution`, `sessionStart`, …) | Tools, shell, session boundaries |
| `precision_timekeeper` | Aligned timestamps |
| Integrated terminal | Non–tool-call shell |
| On-demand commands | `git diff`, time-window `find` |
| Optional proxy | API traffic if base URL routed |
| Display only | `CLAUDE.md`, `.cursor/rules`, etc. |

**Not available:** Composer/Agent internal API stream; model name until `sessionStart` spike confirms payload.

---

## Done this session

- [x] Design + implementation plan in `sai-extensions/cursor/`
- [x] `precision_timekeeper.py` extracted; deduped `time_authority.py` refactor + backup
- [x] `mark_out_of_sync_and_trigger_election()` added (adapter was calling missing API)
- [x] Working copy of keeper in `sai-extensions/cursor/`
- [x] Phase 1 hook kit: `append-activity.js`, `redact.js`, `hooks.json.example`, project `.cursor/hooks.json`
- [x] `SPIKE-2026-05-18-hooks.md` (schema from Cursor docs; live checklist pending)

---

## Next steps (in order)

1. **F5 / install VSIX** — `cd cursor-activity && npm run compile` then Extension Development Host or `npm run package`
2. **Phase 3** — per-agent proxy port registry
3. Re-copy `precision_timekeeper.py` from LSE after any upstream edits

---

## Maintenance rules (stop copy-paste regression)

- **Clock math only** in `precision_timekeeper.py`
- **Redis/elections only** in `time_authority.py` (must call `PrecisionTimeKeeper`)
- Bugfixes: **surgical patches**, not full-file regen
- IDE showing ~1018 lines on `time_authority.py` → likely **backup** tab; refactored file is ~730 lines

---

## Quick commands

```bash
# Precision time smoke (from cursor/)
cd /home/legion/sai-extensions/cursor
pip install ntplib
python3 precision_timekeeper.py

# LSE canonical
cd /mnt/lightspeed-data/Lightspeed-Engine/LSE-Core-2.0-2.1/core/services/sigchain_adapter
python3 precision_timekeeper.py
```

---

## Open questions

1. `sessionStart` payload: `model`, `agentId`, `sessionId`?
2. Multiple Agent tabs → distinct `sessionId`s?
3. JSONL rotation / retention policy?

---

## Out of scope (v0)

LSE Observation Plane / MCP `agent_activity`, `@agent-governance/*` monorepo, file watchers, automated governance verdicts.
