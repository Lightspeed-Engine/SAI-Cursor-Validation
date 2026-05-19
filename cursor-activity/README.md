# Cursor Activity Correlator (VSIX)

Phase 2 extension: tails `.cursor/activity/activity.jsonl`, shows a live timeline, workspace instruction context, and git sample commands.

## Prerequisites

- [Phase 1 hooks](../cursor/README.md) installed in the workspace (`.cursor/hooks.json`)
- Node.js 18+

## Develop / test (dogfooding)

1. Open **`sai-extensions`** in Cursor (hooks already installed).
2. Run an Agent session — events append automatically to `.cursor/activity/activity.jsonl`.
3. Validate the log:
   ```bash
   bash cursor/scripts/validate-live.sh
   ```
4. **Extension Development Host:** open `cursor-activity/`, press **F5** (or *Run Extension*).
5. In the new window, open the **Activity** sidebar → **Timeline** and **Instruction Context**.
6. Status bar shows session id, event count, and log path.

## Build & install locally

```bash
cd cursor-activity
npm install
npm run compile
npm run package
```

Install the generated `.vsix` via *Extensions → … → Install from VSIX…*.

## Commands

| Command | Description |
|---------|-------------|
| Governance: Sample Git Status | Append `sample.git_status` event |
| Governance: Sample Git Diff | Append `sample.git_diff` event |
| Activity: Refresh Timeline | Reload log from disk |
| Activity: Open activity.jsonl | Open raw log |

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `cursorActivity.logPath` | (empty) | Override log file path |
| `cursorActivity.maxEvents` | `5000` | In-memory ring buffer size |

## Related docs

- [DESIGN](../cursor/DESIGN-2026-05-18-governed-activity-correlator.md)
- [PLAN](../cursor/PLAN-2026-05-18-governed-activity-correlator.md)
