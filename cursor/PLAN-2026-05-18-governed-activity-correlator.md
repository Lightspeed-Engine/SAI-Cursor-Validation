# IMPLEMENTATION PLAN: Governed Activity Correlator (Cursor-first)

**Date:** 2026-05-18  
**Updated:** 2026-05-19  
**Status:** Active — Phase 0–1 done; Phase 2 scaffolded (user sign-off pending)  
**Location:** `sai-extensions/cursor/`  
**Design:** [DESIGN-2026-05-18-governed-activity-correlator.md](./DESIGN-2026-05-18-governed-activity-correlator.md)  
**Your checklist:** [FEATURE-CHECKLIST-2026-05-18.md](./FEATURE-CHECKLIST-2026-05-18.md)

---

## North star

**Live operational truth** for agent sessions: independent observations on one timestamped timeline, surfaced in the IDE—**not** post-hoc narrative vs `git`.

**Product shape:** Hooks write → extension reads → human sees timeline. Policy/verdicts come later.

**Regression rule:** Each phase ends with an automated test suite. Shipping phase *N* requires `run-phase-tests.sh N` to pass (which runs phases `0…N`).

```bash
bash cursor/scripts/run-phase-tests.sh        # through Phase 2 (current)
ACTIVITY_REQUIRE_LIVE=1 bash cursor/scripts/run-phase-tests.sh 1  # fail if no live Agent log
```

**CI (use one host):**

| Stage | When | GitHub | GitLab |
|-------|------|--------|--------|
| **Test** | Every PR / push to `main` | `activity-correlator.yml` | `activity-correlator:phase-tests` |
| **Live gate** | Manual / optional | `workflow_dispatch` + require live log | `activity-correlator:live-gate` |
| **Release** | Tag `cursor-activity-v*` | `publish.yml` → GitHub Release + VSIX artifact | `activity-correlator:release-artifacts` |
| **OpenVSX** | Same tag + secret configured | `publish-openvsx` job (`OPEN_VSX_TOKEN`) | `activity-correlator:publish-openvsx` (manual until token set) |
| **npm** | When shared packages exist | `publish-npm` job (disabled until `@agent-governance/*`) | `activity-correlator:publish-npm` (manual) |

PR/push CI runs phases 0–2 structurally. `validate-live` skips without a log on the runner.

**Publishing in CI (planned — not blocking v0 coding):**

1. Tag `cursor-activity-v0.1.0` → build VSIX → attach to **GitHub Release** (active in `publish.yml`).
2. **OpenVSX** — same VSIX via `ovsx publish` when `OPEN_VSX_TOKEN` is in repo secrets.
3. **npm** — publish extracted SDK packages only (not the VSIX); enable when `@agent-governance/*` or hook SDK packages land in repo.

---

## Phase summary

| Phase | Goal (one line) | Primary deliverable | Status |
|-------|-----------------|---------------------|--------|
| **0** | Know what Cursor sends | `SPIKE-2026-05-18-hooks.md` | **Done** |
| **1** | Live append-only audit log | Hooks + `activity.jsonl` + `validate-live.sh` | **Done** |
| **2** | IDE correlator (proper VSIX) | `cursor-activity/` package | **Built — verify** |
| **3** | Optional API observation | Per-agent proxy + registry | **Not started** |
| **4** | Same log from CLI runtimes | Bridges in governor packages | **Not started** |
| **5** | Policy / verdicts | `verifyClaim`, rules engine | **Deferred** |

**Authority:** Aligns with [DEC-2026-04-25](file:///mnt/lightspeed-data/Lightspeed-Engine/LSE-StandAlone-Deployment/REALIGNMENT-2026-04-19/architecture/DEC-2026-04-25-governed-runtime-sdk-extension-ecosystem.md) product-first amendment. No SDK monorepo before **M2** sign-off.

---

## Phase 0 — Spike

### Goal

Confirm Cursor hook payloads and choose the canonical log path—using **live** captures, not assumed docs alone.

### Deliverables

| Deliverable | Path / artifact | Acceptance criteria |
|-------------|-----------------|---------------------|
| Spike notes | `cursor/SPIKE-2026-05-18-hooks.md` | Documents real fields from live log |
| Canonical log path | `.cursor/activity/activity.jsonl` | Decided and gitignored |
| Hook feasibility | `.cursor/hooks.json` | At least `postToolUse` fires in Agent session |

### Exit criteria

- [x] One real Agent session produced hook lines in the log  
- [x] Spike doc updated from live data (not docs-only)  
- [ ] `sessionStart` observed on your Cursor build (optional—may not fire on all versions)

### Automated test suite (Phase 0)

| Script | Verifies |
|--------|----------|
| `cursor/scripts/tests/test-phase-0.sh` | SPIKE doc, log path documented, `hooks.json.example` valid |

### Status: **Done**

---

## Phase 1 — Activity log + hook kit

### Goal

A **repeatable, project-local, live activity stream** without any extension—any repo can copy the kit and get a trustworthy JSONL audit trail.

### Deliverables

| Deliverable | Path | Acceptance criteria |
|-------------|------|---------------------|
| Append + normalize hook | `cursor/scripts/hooks/append-activity.js` | One JSON line per hook; v0 schema |
| Redaction | `cursor/scripts/hooks/redact.js` | No raw secrets in log |
| Project wrapper | `.cursor/hooks/append-activity.sh` | Cursor invokes from repo root |
| Hook template | `cursor/hooks.json.example` | Copy → `.cursor/hooks.json` |
| Install script | `cursor/scripts/install-project-hooks.sh` | Installs into another repo |
| Live validator | `cursor/scripts/validate-live.sh` | Exit 0 only on real Cursor events |
| Precision time (optional) | `cursor/precision_timekeeper.py` | Optional `ACTIVITY_USE_PRECISION_TIME=1` |
| Docs | `cursor/README.md` | Quick start + live validation |

### Exit criteria

- [x] `validate-live.sh` → `ok: true`, `fixtureEventCount: 0`  
- [x] Log grows during Agent session (tool, shell, edit events)  
- [x] `.cursor/activity/` in `.gitignore`  
- [ ] You sign off **M1** on [FEATURE-CHECKLIST](./FEATURE-CHECKLIST-2026-05-18.md)

### Automated test suite (Phase 1)

Runs **Phase 0 tests first** (regression), then:

| Script | Verifies |
|--------|----------|
| `test-phase-1.sh` | Hook files, gitignore, `hooks.json` paths, `test-redact.js` |
| `validate-live.sh` | Live log schema + real Cursor events (skipped if no log; required with `ACTIVITY_REQUIRE_LIVE=1`) |

### Status: **Done** (implementation) — **your sign-off pending**

---

## Phase 2 — `cursor-activity` extension (VSIX)

### Goal

**Proper VS Code / Cursor extension** that tails the live log and shows operational truth in the IDE—timeline, context, samples—not a hooks-only workaround.

### Deliverables

| Deliverable | Path | Acceptance criteria |
|-------------|------|---------------------|
| Extension package | `sai-extensions/cursor-activity/` | `package.json`, `engines.vscode`, compiles |
| Log tailer (file only) | `src/activity/tailer.ts` | Watches **activity.jsonl** only—not workspace tree |
| Event store | `src/activity/store.ts` | Ring buffer; v0 schema parse |
| Timeline UI | `src/ui/timelinePanel.ts` | Webview; filter session/type/source |
| Instruction context | `src/ui/contextPanel.ts` | Lists rules / agent md paths |
| Status bar | `src/ui/statusBar.ts` | session id, count, log path |
| Git sample commands | `src/activity/sampleWriter.ts` | Appends `sample.git_*` events |
| Build / package | `npm run compile`, `npm run package` | Produces installable `.vsix` |
| Extension README | `cursor-activity/README.md` | F5 + Install from VSIX steps |

### Exit criteria

- [ ] F5 or VSIX install in Cursor  
- [ ] Timeline updates during live Agent session  
- [ ] Git sample commands append to same log  
- [ ] You sign off **M2** on [FEATURE-CHECKLIST](./FEATURE-CHECKLIST-2026-05-18.md)

### Automated test suite (Phase 2)

Runs **Phases 0–1 tests first** (regression), then:

| Script | Verifies |
|--------|----------|
| `test-phase-2.sh` | `npm run compile`, dist modules, `package.json` contributes |
| `test-schema-parse.js` | Every line in live `activity.jsonl` parses as `ActivityEvent` |

Manual only (not automatable headless): F5 timeline refresh, git sample commands in UI.

### Status: **Built** — verify in Cursor (F5 / Install from VSIX)

```bash
cd cursor-activity && npm install && npm run compile && npm run package
```

---

## Phase 3 — Proxy port registry

### Goal

Optional **per-agent HTTP proxy** so API traffic metadata appears on the same timeline when the user routes model calls through local ports.

### Deliverables

| Deliverable | Path | Acceptance criteria |
|-------------|------|---------------------|
| Port registry | `cursor-activity/src/proxy/registry.ts` | `agentKey` → port in extension state |
| Minimal HTTP proxy | `cursor/scripts/proxy/` or extension | Forward + log metadata |
| Lifecycle | Extension + hooks | Switch agent → close old port, open new |
| Proxy events | Same JSONL | `source: proxy.*` |
| Docs | `cursor/README.md` | Base URL override instructions |

### Exit criteria

- [ ] Two agent profiles → two ports in UI  
- [ ] `curl` through proxy → line on timeline  
- [ ] You sign off **M3** on checklist  

### Automated test suite (Phase 3)

**TBD:** `test-phase-3.sh` — must run `run-phase-tests.sh 2` first (no regressions).

### Status: **Not started**

**Defer:** TLS MITM, full body capture, upstream auth.

---

## Phase 4 — Bridge CLI extensions

### Goal

**One workspace log** for Cursor Agent + CLI runtimes (Claude Code, Codex, etc.) using the same v0 event schema.

### Deliverables

| Deliverable | Package | Acceptance criteria |
|-------------|---------|---------------------|
| Terminal → JSONL | `claude-governor` | CLI events in `activity.jsonl` |
| Thin adapter | `claude-code` (optional) | Same schema |
| Timeline alignment | `codex-governor` | Uses timeline vs regex-only |
| Shared library (if needed) | `governor-core` | Only after second duplicate |

### Exit criteria

- [ ] Single `activity.jsonl` contains Cursor + CLI events  
- [ ] Optional UI links `sessionId` across runtimes  
- [ ] You sign off **M4** on checklist  

### Status: **Not started**

---

## Phase 5 — Validation / policy (later)

### Goal

Consume timeline slices for **governance verdicts**—without blocking Phases 1–3.

### Deliverables

- `verifyClaim` over timeline windows  
- Pluggable policy provider (local JSON → pass/fail)  
- Golden JSONL conformance tests (for policy, not for replacing live validation)

### Status: **Deferred** — track in `claude-governor` backlog

---

## Milestones (user-visible)

| Milestone | Phases | You should be able to say |
|-----------|--------|---------------------------|
| **M0** | 0 | “We know what Cursor actually sends.” |
| **M1** | 1 | “I have a live, trustworthy activity stream in my repo.” |
| **M2** | 2 | “I see the timeline in the IDE while the Agent runs.” |
| **M3** | 3 | “Per-agent proxy ports show API traffic on the timeline.” |
| **M4** | 4 | “Cursor and CLI share one correlated log.” |

---

## Repository layout

```
sai-extensions/
  cursor/                              # design, plan, checklist, hooks
    PLAN-2026-05-18-governed-activity-correlator.md
    FEATURE-CHECKLIST-2026-05-18.md
    scripts/hooks/
    scripts/validate-live.sh
  cursor-activity/                       # Phase 2 VSIX
    package.json
    src/
  .cursor/
    hooks.json
    activity/activity.jsonl            # live log (gitignored)
```

---

## Testing strategy

| When | Command | What it runs |
|------|---------|--------------|
| After any phase | `bash cursor/scripts/run-phase-tests.sh [N]` | Phases `0…N` cumulatively |
| Strict live gate | `ACTIVITY_REQUIRE_LIVE=1 … run-phase-tests.sh 1` | Fails if no real Agent log |
| Single phase | `bash cursor/scripts/tests/test-phase-1.sh` | That phase only (no regression) |

| Level | What | Fixture OK? |
|-------|------|-------------|
| Phase 0–2 structural | `test-phase-*.sh`, `test-redact.js` | N/A (structural) |
| Live log | `validate-live.sh` | **No** — real `activity.jsonl` only |
| Extension UI | F5 / VSIX + Agent session | Manual sign-off on checklist |
| Policy (Phase 5) | Golden JSONL | Yes (later) |

---

## Risks

| Risk | Mitigation |
|------|------------|
| `sessionStart` not firing | Use `conversation_id` from other hooks; document in SPIKE |
| Hook schema changes | Opaque `payload`; pin Cursor version |
| Large log | Rotation command (Phase 2+); gitignore |
| Phase 2 assumed done when only coded | **FEATURE-CHECKLIST** requires your sign-off |

---

## Immediate next actions

1. **You:** Walk [FEATURE-CHECKLIST-2026-05-18.md](./FEATURE-CHECKLIST-2026-05-18.md) — tick what matches expectations.  
2. **You:** F5 / Install VSIX for `cursor-activity`; confirm live timeline (M2).  
3. **Implement:** Phase 3 only after M2 sign-off.  
4. **Optional:** Debug why `sessionStart` never appears on Cursor 3.3.30 (not blocking M2).

---

## Out of scope (v0 implementation)

- LSE Observation Plane / MCP `agent_activity`  
- Workspace tree file watchers  
- Automated governance verdict UI  

**Deferred to CI publish stage (configured, not required for M2 sign-off):**

- OpenVSX marketplace publish (`publish.yml` / GitLab `publish-openvsx`)  
- npm registry publish for shared SDK packages (`publish-npm` when packages exist)  

`@agent-governance/*` monorepo first remains deferred per DEC; npm CI job enables when packages are extracted.
