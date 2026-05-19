# Feature checklist — by phase

**Purpose:** What you expect at the end of each phase.  
**Automated gate:** `bash cursor/scripts/run-phase-tests.sh` (must pass before calling a phase done). Same command runs in **GitHub Actions** or **GitLab CI** on push/PR.  
**Manual sign-off:** You still tick items you verified in Cursor.

**Not confusing:** Items are numbered **inside each phase** (Phase 1 → 1.1, 1.2, …). There is no separate “B1 = Phase 0” mapping.

---

## Product intent (all phases)

Same end goal as **Claude Governor**, adapted for **Cursor**:

- Live operational truth on a timeline (not post-hoc story vs `git`)
- Agent runs **inside Cursor** (no governed container for this track)
- Cursor owns the runtime; we add **hooks + log + extension + later policy**
- Parity with Governor checkpoints / `verifyClaim` → **Phase 5**, not v0

---

## Phase 0 — Spike

**Goal:** Know what Cursor sends; lock canonical log path.

| # | Deliverable / expectation | Auto test | You |
|---|---------------------------|-----------|-----|
| 0.1 | `SPIKE-2026-05-18-hooks.md` exists, documents live fields | `test-phase-0.sh` | [ ] |
| 0.2 | Canonical log path = `.cursor/activity/activity.jsonl` | `test-phase-0.sh` | [ ] |
| 0.3 | `hooks.json.example` valid | `test-phase-0.sh` | [ ] |

**Run:** `bash cursor/scripts/run-phase-tests.sh 0`

---

## Phase 1 — Live activity stream (hooks → JSONL)

**Goal:** Append-only audit log during Agent sessions; no VSIX required.

| # | Deliverable / expectation | Auto test | You |
|---|---------------------------|-----------|-----|
| 1.1 | `.cursor/hooks.json` fires on tool/shell/edit | `validate-live` (live log) | [ ] |
| 1.2 | Normalized schema on every line | `validate-live` | [ ] |
| 1.3 | Redaction (no raw secrets) | `test-redact.js` | [ ] |
| 1.4 | Log gitignored | `test-phase-1.sh` | [ ] |
| 1.5 | Events append **while** Agent runs | Manual Agent session | [ ] |
| 1.6 | `validate-live.sh` passes on **live** data only | `test-phase-1.sh` | [ ] |
| 1.7 | `conversation_id` stable per chat | Manual / log inspect | [ ] |
| 1.8 | `session.start` if Cursor fires `sessionStart` | Optional — known gap on some builds | [ ] |

**Run (regression includes Phase 0):** `bash cursor/scripts/run-phase-tests.sh 1`  
**Strict live gate:** `ACTIVITY_REQUIRE_LIVE=1 bash cursor/scripts/run-phase-tests.sh 1`

---

## Phase 2 — VSIX (`cursor-activity`)

**Goal:** Proper extension — timeline + context + git samples; tails log file only.

| # | Deliverable / expectation | Auto test | You |
|---|---------------------------|-----------|-----|
| 2.1 | Package `cursor-activity/` compiles | `test-phase-2.sh` | [ ] |
| 2.2 | Produces `.vsix` (`npm run package`) | Manual / CI | [ ] |
| 2.3 | **Activity** sidebar → **Timeline** webview | Manual F5 / VSIX | [ ] |
| 2.4 | Timeline updates live during Agent session | Manual | [ ] |
| 2.5 | Filter by session / type / source | Manual | [ ] |
| 2.6 | Status bar: session, count, log path | Manual | [ ] |
| 2.7 | Instruction Context panel | Manual | [ ] |
| 2.8 | Git sample commands append to same log | Manual | [ ] |
| 2.9 | Parses existing `activity.jsonl` lines | `test-schema-parse.js` | [ ] |
| 2.10 | No workspace tree `fs.watch` | Design review | [ ] |

**Run (regression includes Phases 0–1):** `bash cursor/scripts/run-phase-tests.sh 2`

---

## Phase 3 — Proxy (not started)

**Goal:** Optional per-agent API metadata on same timeline.

| # | Expectation | Auto test | You |
|---|-------------|-----------|-----|
| 3.1 | Port registry `agentKey` → port | TBD `test-phase-3.sh` | [ ] |
| 3.2 | Proxy events `source: proxy.*` | TBD | [ ] |
| 3.3 | Switch agent closes old port | TBD | [ ] |

**Run (when implemented):** `bash cursor/scripts/run-phase-tests.sh 3`

---

## Phase 4 — CLI bridges (not started)

**Goal:** One log for Cursor + Claude CLI (same schema).

| # | Expectation | Auto test | You |
|---|-------------|-----------|-----|
| 4.1 | CLI events in `activity.jsonl` | TBD `test-phase-4.sh` | [ ] |
| 4.2 | Timeline shows mixed sources | TBD | [ ] |

---

## Phase 5 — Policy / verdicts (later)

**Goal:** Governor-style `verifyClaim`, pass/fail — **after** timeline trusted.

| # | Expectation | You |
|---|-------------|-----|
| 5.1 | Claims checked against timeline slices | [ ] |
| 5.2 | Local policy rules | [ ] |

---

## Non-goals (should stay out of scope)

- LSE / container enrollment as requirement for Cursor v0  
- Composer private API interception  
- Workspace-wide file watchers  
- OpenVSX publish in v0  

---

## Sign-off

| Milestone | Phase | Auto `run-phase-tests` | Your sign-off |
|-----------|-------|------------------------|---------------|
| M0 Spike | 0 | `… 0` | [ ] |
| M1 Live stream | 1 | `… 1` | [ ] |
| M2 IDE timeline | 2 | `… 2` | [ ] |
| M3 Proxy | 3 | `… 3` | [ ] |
| M4 Multi-runtime | 4 | `… 4` | [ ] |

**Your corrections:**

```

```
