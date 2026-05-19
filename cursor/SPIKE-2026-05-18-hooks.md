# SPIKE: Cursor hooks — live validation (2026-05-18)

**Status:** Validated against **live** `.cursor/activity/activity.jsonl` from Cursor 3.3.30 (no fixtures).

Re-run anytime:

```bash
bash cursor/scripts/validate-live.sh
```

## Canonical log (live only)

| Path | Role |
|------|------|
| `.cursor/activity/activity.jsonl` | Single append-only audit log (gitignored) |

Spike `/tmp` duplicate logging is **off** by default (`ACTIVITY_SPIKE_ENABLED=0`).

---

## Live session observed

| Field | Value (real) |
|-------|----------------|
| `sessionId` / `conversation_id` | `208ef4e1-4660-4637-a37f-62dc0d6ea1cb` |
| `model` | `default` |
| `cursor_version` | `3.3.30` |
| `transcript_path` | `~/.cursor/projects/home-legion-sai-extensions/agent-transcripts/.../208ef4e1-....jsonl` |
| `user_email` | present (authenticated) |
| `workspace_roots` | multi-root: `sai-extensions`, LSE paths |

## Live event counts (one session)

| type | count | source |
|------|------:|--------|
| `tool.result` | 26 | `cursor.hook.postToolUse` |
| `shell.after` | 9 | `cursor.hook.afterShellExecution` |
| `file.edit` | 11 | `cursor.hook.afterFileEdit` |
| `prompt.before` | 3 | `cursor.hook.beforeSubmitPrompt` |
| `tool.failure` | 3 | `cursor.hook.postToolUseFailure` |
| `agent.response` | 1 | `cursor.hook.afterAgentResponse` |

## Open questions — live answers

### 1. `sessionStart` fields?

**Confirmed on other hooks:** `model`, `conversation_id`, `session_id`, `cursor_version`, `workspace_roots`, `transcript_path`, `generation_id`, `hook_event_name`.

**`sessionStart`:** Not yet captured in this log — hooks were installed mid-conversation. `sessionStart` only fires when a **new** composer chat is created. Start a fresh Agent tab to capture `session.start` with `composer_mode`, `is_background_agent`.

### 2. Multiple Agent tabs?

Use distinct `conversation_id` per tab. Validate by opening two Agent chats and running `validate-live.sh` — expect two entries under `sessions` in the report.

### 3. JSONL retention

Deferred; log was ~125KB after one extended session. Rotation can be Phase 2.

---

## `postToolUse` live payload keys

`conversation_id`, `generation_id`, `model`, `tool_name`, `tool_input`, `tool_output`, `tool_use_id`, `cwd`, `duration`, `session_id`, `hook_event_name`, `cursor_version`, `workspace_roots`, `user_email`, `transcript_path`

## Normalized record (live example)

```json
{
  "v": 1,
  "ts": "2026-05-19T02:11:34.839Z",
  "source": "cursor.hook.afterFileEdit",
  "sessionId": "208ef4e1-4660-4637-a37f-62dc0d6ea1cb",
  "agentKey": "cursor.agent",
  "type": "file.edit",
  "payload": { "...": "redacted live hook stdin" }
}
```

## Checklist

- [x] Hooks fire during Agent session (53+ live events)
- [x] `postToolUse` → `tool.result`
- [x] `afterShellExecution` → `shell.after`
- [x] `afterFileEdit` → `file.edit`
- [x] Schema v1 valid on all lines
- [ ] `sessionStart` on **new** chat (pending — start new conversation)
- [ ] Two tabs → two `conversation_id`s (pending manual test)
