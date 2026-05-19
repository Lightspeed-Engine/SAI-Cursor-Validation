#!/usr/bin/env node
'use strict';

/**
 * Cursor hook: normalize stdin JSON and append to .cursor/activity/activity.jsonl.
 * Fail-open on errors (exit 0) so agent work is not blocked.
 */

const fs = require('fs');
const path = require('path');
const { redact } = require('./redact');

const SCHEMA_VERSION = 1;

async function readStdin() {
  const chunks = [];
  for await (const chunk of process.stdin) {
    chunks.push(chunk);
  }
  const text = Buffer.concat(chunks).toString('utf8').trim();
  if (!text) return null;
  return JSON.parse(text);
}

function projectRoot() {
  return process.env.ACTIVITY_PROJECT_ROOT || process.cwd();
}

function resolveLogPath(root) {
  const rel = process.env.ACTIVITY_LOG_PATH || '.cursor/activity/activity.jsonl';
  return path.isAbsolute(rel) ? rel : path.join(root, rel);
}

function resolveSpikePath(root) {
  const rel =
    process.env.ACTIVITY_SPIKE_PATH || '/tmp/cursor-hook-spike.jsonl';
  return path.isAbsolute(rel) ? rel : path.join(root, rel);
}

function resolveTimestamp(root) {
  if (process.env.ACTIVITY_USE_PRECISION_TIME === '1') {
    try {
      const { execFileSync } = require('child_process');
      const cursorDir = path.join(root, 'cursor');
      const script = `
import asyncio, sys
sys.path.insert(0, ${JSON.stringify(cursorDir)})
from precision_timekeeper import initialize_default, now_ms
async def main():
    await initialize_default(sync_ntp=False)
    print(now_ms())
asyncio.run(main())
`;
      const out = execFileSync('python3', ['-c', script], {
        encoding: 'utf8',
        timeout: 8000,
      }).trim();
      const ms = Number(out);
      if (!Number.isNaN(ms)) {
        return new Date(ms).toISOString();
      }
    } catch {
      /* fall through to wall clock */
    }
  }
  return new Date().toISOString();
}

function deriveAgentKey(input) {
  const mode = input.composer_mode || input.composerMode;
  if (mode) return `cursor.${mode}`;
  if (input.is_background_agent === true) return 'cursor.background';
  return 'cursor.agent';
}

function deriveSessionId(input) {
  return (
    input.session_id ||
    input.conversation_id ||
    process.env.CURSOR_SESSION_ID ||
    'unknown'
  );
}

function mapEventType(hookName) {
  const table = {
    sessionStart: 'session.start',
    sessionEnd: 'session.end',
    postToolUse: 'tool.result',
    postToolUseFailure: 'tool.failure',
    preToolUse: 'tool.before',
    beforeShellExecution: 'shell.before',
    afterShellExecution: 'shell.after',
    beforeMCPExecution: 'mcp.before',
    afterMCPExecution: 'mcp.after',
    beforeReadFile: 'file.read.before',
    afterFileEdit: 'file.edit',
    beforeSubmitPrompt: 'prompt.before',
    afterAgentResponse: 'agent.response',
    afterAgentThought: 'agent.thought',
    subagentStart: 'subagent.start',
    subagentStop: 'subagent.stop',
    stop: 'session.stop',
    preCompact: 'context.compact',
    workspaceOpen: 'workspace.open',
  };
  if (table[hookName]) return table[hookName];
  return hookName ? `hook.${hookName}` : 'hook.unknown';
}

function buildRecord(input) {
  const hookName = input.hook_event_name || process.env.CURSOR_HOOK_EVENT || 'unknown';
  const safePayload = redact(input);

  return {
    v: SCHEMA_VERSION,
    ts: resolveTimestamp(projectRoot()),
    source: `cursor.hook.${hookName}`,
    sessionId: deriveSessionId(input),
    agentKey: deriveAgentKey(input),
    type: mapEventType(hookName),
    payload: safePayload,
  };
}

function appendLine(filePath, record) {
  const dir = path.dirname(filePath);
  fs.mkdirSync(dir, { recursive: true });
  fs.appendFileSync(filePath, `${JSON.stringify(record)}\n`, 'utf8');
}

function hookOutputFor(input) {
  const hookName = input.hook_event_name;
  if (hookName === 'sessionStart') {
    return JSON.stringify({});
  }
  return JSON.stringify({});
}

async function deliverRecord(root, record) {
  if (process.env.ACTIVITY_LEGACY_DIRECT === '1') {
    appendLine(resolveLogPath(root), record);
    return;
  }
  const braidUrl = process.env.BRAID_URL || 'http://127.0.0.1:4711';
  try {
    const res = await fetch(`${braidUrl}/v1/ingest`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ event: record }),
      signal: AbortSignal.timeout(Number(process.env.BRAID_TIMEOUT_MS || 500)),
    });
    if (res.status === 204 || res.ok) {
      return;
    }
  } catch {
    /* braid offline */
  }
  if (process.env.ACTIVITY_BRAID_FAIL_OPEN === '1') {
    appendLine(resolveLogPath(root), record);
  }
}

async function main() {
  const input = await readStdin();
  if (!input) {
    process.stdout.write('{}');
    return;
  }

  const root = projectRoot();
  const record = buildRecord(input);

  await deliverRecord(root, record);

  if (process.env.ACTIVITY_SPIKE_ENABLED === '1') {
    appendLine(resolveSpikePath(root), {
      capturedAt: new Date().toISOString(),
      raw: redact(input),
    });
  }

  process.stdout.write(hookOutputFor(input));
}

module.exports = {
  SCHEMA_VERSION,
  readStdin,
  deriveAgentKey,
  deriveSessionId,
  mapEventType,
  buildRecord,
  appendLine,
  hookOutputFor,
  projectRoot,
  resolveLogPath,
  resolveSpikePath,
  resolveTimestamp,
  deliverRecord,
  main,
};

if (require.main === module) {
  main().catch((err) => {
    console.error('[append-activity]', err.message);
    process.stdout.write('{}');
    process.exit(0);
  });
}
