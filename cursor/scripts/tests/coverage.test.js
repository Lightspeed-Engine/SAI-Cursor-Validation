#!/usr/bin/env node
'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');

const { redact, redactString } = require('../hooks/redact');
const {
  deriveAgentKey,
  deriveSessionId,
  mapEventType,
  buildRecord,
  appendLine,
  hookOutputFor,
  resolveLogPath,
  resolveSpikePath,
  projectRoot,
  SCHEMA_VERSION,
} = require('../hooks/append-activity');

const typesPath = path.join(
  __dirname,
  '../../../cursor-activity/dist/activity/types.js'
);
const {
  parseActivityLine,
  isActivityEvent,
  shortSessionId,
} = require(typesPath);

describe('redact', () => {
  it('redacts secret keys and bearer tokens', () => {
    const out = redact({
      authorization: 'Bearer sk-live-secret',
      password: 'hunter2',
      tool_output: 'token Bearer abc.def.ghi in text',
      nested: { api_key: 'ghp_abcdefghijklmnopqrstuvwxyz1234567890' },
    });
    assert.equal(out.authorization, '[REDACTED]');
    assert.equal(out.password, '[REDACTED]');
    assert.match(out.tool_output, /\[REDACTED\]/);
    assert.equal(out.nested.api_key, '[REDACTED]');
  });

  it('redacts env block', () => {
    const out = redact({ env: { API_KEY: 'x' }, note: 'ok' });
    assert.equal(out.env, '[REDACTED_ENV]');
    assert.equal(out.note, 'ok');
  });

  it('redactString strips bearer patterns', () => {
    const s = redactString('Authorization: Bearer abc.def.ghi');
    assert.match(s, /Bearer \[REDACTED\]/);
  });

  it('redacts arrays and nullish values', () => {
    const out = redact({ items: ['Bearer abc', 'plain'], empty: null });
    assert.ok(Array.isArray(out.items));
    assert.equal(out.empty, null);
  });
});

describe('append-activity helpers', () => {
  it('deriveAgentKey from composer mode', () => {
    assert.equal(deriveAgentKey({ composer_mode: 'agent' }), 'cursor.agent');
    assert.equal(deriveAgentKey({ is_background_agent: true }), 'cursor.background');
  });

  it('deriveSessionId prefers session_id', () => {
    assert.equal(
      deriveSessionId({ session_id: 's1', conversation_id: 'c1' }),
      's1'
    );
    const prev = process.env.CURSOR_SESSION_ID;
    process.env.CURSOR_SESSION_ID = 'from-env';
    assert.equal(deriveSessionId({}), 'from-env');
    process.env.CURSOR_SESSION_ID = prev;
  });

  it('mapEventType maps known hooks', () => {
    assert.equal(mapEventType('sessionStart'), 'session.start');
    assert.equal(mapEventType('afterFileEdit'), 'file.edit');
    assert.equal(mapEventType('customHook'), 'hook.customHook');
    assert.equal(mapEventType(''), 'hook.unknown');
    assert.equal(mapEventType(undefined), 'hook.unknown');
  });

  it('buildRecord produces schema v1 shape', () => {
    const record = buildRecord({
      hook_event_name: 'postToolUse',
      conversation_id: 'conv-abc',
      tool_name: 'shell',
    });
    assert.equal(record.v, SCHEMA_VERSION);
    assert.equal(record.type, 'tool.result');
    assert.equal(record.sessionId, 'conv-abc');
    assert.match(record.ts, /^\d{4}-\d{2}-\d{2}T/);
    assert.equal(record.source, 'cursor.hook.postToolUse');
    assert.equal(record.payload.tool_name, 'shell');
  });

  it('appendLine creates directories and writes jsonl', () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'activity-'));
    const file = path.join(dir, 'nested', 'activity.jsonl');
    appendLine(file, {
      v: 1,
      ts: '2026-05-19T00:00:00.000Z',
      source: 'test',
      sessionId: 's',
      agentKey: 'k',
      type: 't',
      payload: {},
    });
    assert.equal(fs.readFileSync(file, 'utf8').trim().split('\n').length, 1);
  });

  it('hookOutputFor returns json object string', () => {
    assert.equal(hookOutputFor({ hook_event_name: 'sessionStart' }), '{}');
    assert.equal(hookOutputFor({ hook_event_name: 'postToolUse' }), '{}');
  });

  it('resolveLogPath and resolveSpikePath honor env', () => {
    const logPrev = process.env.ACTIVITY_LOG_PATH;
    const spikePrev = process.env.ACTIVITY_SPIKE_PATH;
    process.env.ACTIVITY_LOG_PATH = 'custom/activity.jsonl';
    process.env.ACTIVITY_SPIKE_PATH = '/tmp/spike-test.jsonl';
    assert.match(resolveLogPath('/repo'), /custom[/\\]activity\.jsonl$/);
    assert.equal(resolveSpikePath('/repo'), '/tmp/spike-test.jsonl');
    process.env.ACTIVITY_LOG_PATH = logPrev;
    process.env.ACTIVITY_SPIKE_PATH = spikePrev;
  });

  it('projectRoot uses ACTIVITY_PROJECT_ROOT', () => {
    const prev = process.env.ACTIVITY_PROJECT_ROOT;
    process.env.ACTIVITY_PROJECT_ROOT = '/tmp/activity-root';
    assert.equal(projectRoot(), '/tmp/activity-root');
    process.env.ACTIVITY_PROJECT_ROOT = prev;
  });

  it('CLI appends hook payload to activity.jsonl', () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'activity-cli-'));
    const script = path.join(__dirname, '../hooks/append-activity.js');
    const payload = JSON.stringify({
      hook_event_name: 'afterFileEdit',
      conversation_id: 'conv-cli',
      file: 'README.md',
    });
    const env = { ...process.env, ACTIVITY_PROJECT_ROOT: dir };
    delete env.ACTIVITY_LOG_PATH;
    const result = spawnSync('node', [script], {
      input: payload,
      encoding: 'utf8',
      env,
      cwd: dir,
    });
    assert.equal(result.status, 0, result.stderr);
    assert.equal(result.stdout.trim(), '{}');
    const logFile = path.join(dir, '.cursor/activity/activity.jsonl');
    assert.ok(fs.existsSync(logFile), `missing log at ${logFile}`);
    const line = JSON.parse(fs.readFileSync(logFile, 'utf8').trim());
    assert.equal(line.type, 'file.edit');
    assert.equal(line.sessionId, 'conv-cli');
  });

  it('CLI writes empty object when stdin is empty', () => {
    const script = path.join(__dirname, '../hooks/append-activity.js');
    const result = spawnSync('node', [script], {
      input: '',
      encoding: 'utf8',
    });
    assert.equal(result.status, 0);
    assert.equal(result.stdout.trim(), '{}');
  });

  it('CLI records spike log when enabled', () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'activity-spike-'));
    const script = path.join(__dirname, '../hooks/append-activity.js');
    const spikeFile = path.join(dir, 'spike.jsonl');
    const payload = JSON.stringify({
      hook_event_name: 'postToolUse',
      conversation_id: 'c-spike',
    });
    const result = spawnSync('node', [script], {
      input: payload,
      encoding: 'utf8',
      env: {
        ...process.env,
        ACTIVITY_PROJECT_ROOT: dir,
        ACTIVITY_SPIKE_ENABLED: '1',
        ACTIVITY_SPIKE_PATH: spikeFile,
      },
    });
    assert.equal(result.status, 0);
    assert.ok(fs.existsSync(spikeFile));
  });
});

describe('activity types', () => {
  const sample = JSON.stringify({
    v: 1,
    ts: '2026-05-19T00:00:00.000Z',
    source: 'cursor.hook.postToolUse',
    sessionId: 'sess-1',
    agentKey: 'cursor.agent',
    type: 'tool.result',
    payload: { ok: true },
  });

  it('parseActivityLine accepts valid events', () => {
    const event = parseActivityLine(sample);
    assert.ok(event);
    assert.ok(isActivityEvent(event));
    assert.equal(event.sessionId, 'sess-1');
  });

  it('parseActivityLine rejects invalid lines', () => {
    assert.equal(parseActivityLine('not json'), null);
    assert.equal(parseActivityLine('{"v":2}'), null);
    assert.equal(parseActivityLine(''), null);
    assert.equal(isActivityEvent(null), false);
    assert.equal(isActivityEvent({ v: 1 }), false);
  });

  it('shortSessionId truncates long ids', () => {
    assert.match(shortSessionId('abcdefghijklmnop'), /…$/);
    assert.equal(shortSessionId('unknown'), '—');
  });
});
