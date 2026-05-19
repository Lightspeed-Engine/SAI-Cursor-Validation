#!/usr/bin/env node
'use strict';

const { describe, it, before, after } = require('node:test');
const assert = require('node:assert/strict');
const http = require('http');
const path = require('path');
const fs = require('fs');
const os = require('os');
const { spawn } = require('child_process');

const ROOT = path.join(__dirname, '../../..');
let child;
let base;

function request(method, pathname, body) {
  return new Promise((resolve, reject) => {
    const url = new URL(pathname, base);
    const req = http.request(
      url,
      { method, headers: { 'content-type': 'application/json' } },
      (res) => {
        const chunks = [];
        res.on('data', (c) => chunks.push(c));
        res.on('end', () => {
          const text = Buffer.concat(chunks).toString('utf8');
          let json = null;
          if (text) {
            try {
              json = JSON.parse(text);
            } catch {
              json = text;
            }
          }
          resolve({ status: res.statusCode, json });
        });
      }
    );
    req.on('error', reject);
    if (body) req.write(JSON.stringify(body));
    req.end();
  });
}

before(async () => {
  const logFile = path.join(os.tmpdir(), `braid-test-${Date.now()}.jsonl`);
  const port = 4700 + Math.floor(Math.random() * 200);
  base = `http://127.0.0.1:${port}`;
  child = spawn('node', [path.join(ROOT, 'core/braid/bin/braid.js')], {
    env: {
      ...process.env,
      BRAID_PORT: String(port),
      BRAID_LOG_PATH: logFile,
    },
    stdio: 'ignore',
  });
  for (let i = 0; i < 30; i++) {
    try {
      const r = await request('GET', '/health');
      if (r.status === 200) return;
    } catch {
      /* retry */
    }
    await new Promise((r) => setTimeout(r, 100));
  }
  throw new Error('braid daemon did not start');
});

after(() => {
  if (child) child.kill('SIGTERM');
});

describe('braid recording gate', () => {
  it('drops ingest when not recording', async () => {
    const r = await request('POST', '/v1/ingest', {
      event: {
        v: 1,
        ts: new Date().toISOString(),
        source: 'test',
        sessionId: 's',
        agentKey: 'k',
        type: 't',
        payload: {},
      },
    });
    assert.equal(r.status, 204);
  });

  it('retains after start', async () => {
    const logPath = path.join(os.tmpdir(), `braid-retain-${Date.now()}.jsonl`);
    await request('POST', '/v1/recording/start', {
      logPath,
      sessionId: 'sess-1',
      agentKey: 'cursor.agent',
      verbosity: 'meta',
    });
    const r = await request('POST', '/v1/ingest', {
      event: {
        v: 1,
        ts: new Date().toISOString(),
        source: 'test',
        sessionId: 'sess-1',
        agentKey: 'cursor.agent',
        type: 'tool.result',
        payload: { ok: true },
      },
    });
    assert.equal(r.status, 200);
    assert.ok(fs.existsSync(logPath));
    const lines = fs.readFileSync(logPath, 'utf8').trim().split('\n');
    assert.ok(lines.length >= 1);
    await request('POST', '/v1/recording/stop', {});
  });
});
