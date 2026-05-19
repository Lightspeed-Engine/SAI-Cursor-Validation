#!/usr/bin/env node
'use strict';

/**
 * Live foundation validator — reads ONLY .cursor/activity/activity.jsonl
 * produced by Cursor hooks. No fixtures, no mocks. Exits non-zero if the
 * log is missing or contains no real Cursor events.
 */

const fs = require('fs');
const path = require('path');

const PROJECT_ROOT = process.env.ACTIVITY_PROJECT_ROOT || process.cwd();
const LOG_PATH =
  process.env.ACTIVITY_LOG_PATH ||
  path.join(PROJECT_ROOT, '.cursor/activity/activity.jsonl');

const FIXTURE_SESSION = /^(test-|wrap-test|c2$|unknown$)/i;
const FIXTURE_MODEL = /^(claude-test|test-model)$/i;
const FIXTURE_CURSOR_VERSION = /^(1\.0\.0|9\.9\.9)$/;

function isFixtureEvent(event) {
  const p = event.payload || {};
  if (FIXTURE_SESSION.test(String(event.sessionId || ''))) return true;
  if (FIXTURE_MODEL.test(String(p.model || ''))) return true;
  if (FIXTURE_CURSOR_VERSION.test(String(p.cursor_version || ''))) return true;
  return false;
}

function isLiveCursorEvent(event) {
  if (isFixtureEvent(event)) return false;
  const p = event.payload || {};
  // Real Cursor agent hooks include app version and conversation metadata.
  return Boolean(
    p.hook_event_name &&
    p.conversation_id &&
    p.cursor_version &&
    !FIXTURE_CURSOR_VERSION.test(String(p.cursor_version))
  );
}

function loadEvents() {
  if (!fs.existsSync(LOG_PATH)) {
    return { error: 'missing_log', path: LOG_PATH };
  }
  const raw = fs.readFileSync(LOG_PATH, 'utf8').trim();
  if (!raw) {
    return { error: 'empty_log', path: LOG_PATH };
  }
  const lines = raw.split('\n');
  const parsed = [];
  const parseErrors = [];
  for (let i = 0; i < lines.length; i++) {
    try {
      parsed.push({ line: i + 1, event: JSON.parse(lines[i]) });
    } catch (err) {
      parseErrors.push({ line: i + 1, message: err.message });
    }
  }
  return { lines: lines.length, parsed, parseErrors };
}

function validateSchema(event) {
  const required = ['v', 'ts', 'source', 'sessionId', 'agentKey', 'type', 'payload'];
  const missing = required.filter((k) => !(k in event));
  if (missing.length) return { ok: false, missing };
  if (event.v !== 1) return { ok: false, reason: 'v !== 1' };
  if (!event.source.startsWith('cursor.hook.')) {
    return { ok: false, reason: 'source not cursor.hook.*' };
  }
  return { ok: true };
}

function samplePayloadKeys(event) {
  return Object.keys(event.payload || {}).sort();
}

function buildReport() {
  const loaded = loadEvents();
  if (loaded.error) {
    return {
      ok: false,
      error: loaded.error,
      logPath: loaded.path,
      hint:
        'Open sai-extensions in Cursor, reload workspace, start a NEW Agent chat, run one tool + shell command.',
    };
  }

  const all = loaded.parsed.map((x) => x.event);
  const fixtures = all.filter(isFixtureEvent);
  const live = all.filter(isLiveCursorEvent);
  const schemaFailures = [];
  for (const { line, event } of loaded.parsed) {
    const s = validateSchema(event);
    if (!s.ok) schemaFailures.push({ line, ...s });
  }

  const byType = {};
  const bySource = {};
  const sessions = new Map();
  for (const e of live) {
    byType[e.type] = (byType[e.type] || 0) + 1;
    bySource[e.source] = (bySource[e.source] || 0) + 1;
    if (!sessions.has(e.sessionId)) {
      sessions.set(e.sessionId, {
        sessionId: e.sessionId,
        firstTs: e.ts,
        lastTs: e.ts,
        model: e.payload?.model,
        cursor_version: e.payload?.cursor_version,
        composer_mode: e.payload?.composer_mode,
        transcript_path: e.payload?.transcript_path,
        eventCount: 0,
      });
    }
    const s = sessions.get(e.sessionId);
    s.eventCount++;
    if (e.ts < s.firstTs) s.firstTs = e.ts;
    if (e.ts > s.lastTs) s.lastTs = e.ts;
  }

  const sessionStart = live.find((e) => e.type === 'session.start');
  const postToolUse = live.find((e) => e.type === 'tool.result');
  const shellAfter = live.find((e) => e.type === 'shell.after');

  const checks = {
    log_exists: true,
    parse_errors: loaded.parseErrors.length === 0,
    schema_valid: schemaFailures.length === 0,
    has_live_events: live.length > 0,
    no_fixture_pollution:
      fixtures.length === 0 ||
      `warning: ${fixtures.length} fixture line(s) in log — run scrub or start fresh log`,
    has_tool_result: Boolean(postToolUse),
    has_shell_after: Boolean(shellAfter),
    has_session_start: Boolean(sessionStart),
  };

  const ok =
    checks.parse_errors &&
    checks.schema_valid &&
    checks.has_live_events &&
    checks.has_tool_result;

  return {
    ok,
    logPath: LOG_PATH,
    totalLines: loaded.lines,
    liveEventCount: live.length,
    fixtureEventCount: fixtures.length,
    parseErrors: loaded.parseErrors,
    schemaFailures,
    checks,
    sessions: [...sessions.values()],
    byType,
    bySource,
    liveSamples: {
      sessionStart: sessionStart
        ? {
            ts: sessionStart.ts,
            sessionId: sessionStart.sessionId,
            agentKey: sessionStart.agentKey,
            payloadKeys: samplePayloadKeys(sessionStart),
            model: sessionStart.payload.model,
            composer_mode: sessionStart.payload.composer_mode,
            session_id: sessionStart.payload.session_id,
          }
        : null,
      postToolUse: postToolUse
        ? {
            ts: postToolUse.ts,
            tool_name: postToolUse.payload.tool_name,
            model: postToolUse.payload.model,
            cursor_version: postToolUse.payload.cursor_version,
            payloadKeys: samplePayloadKeys(postToolUse),
          }
        : null,
      shellAfter: shellAfter
        ? {
            ts: shellAfter.ts,
            commandPreview: String(shellAfter.payload.command || '').slice(0, 80),
            cursor_version: shellAfter.payload.cursor_version,
          }
        : null,
    },
    newestLiveEvents: live.slice(-5).map((e) => ({
      ts: e.ts,
      source: e.source,
      type: e.type,
      sessionId: e.sessionId,
    })),
    hint: !sessionStart
      ? 'Live hooks work but no session.start yet — start a NEW Agent chat (sessionStart only fires at conversation creation).'
      : undefined,
  };
}

const report = buildReport();
const json = JSON.stringify(report, null, 2);
if (process.argv.includes('--json-only')) {
  process.stdout.write(json + '\n');
} else {
  console.log(json);
}
process.exit(report.ok ? 0 : 1);
