#!/usr/bin/env node
'use strict';

/**
 * Remove fixture/smoke-test lines from activity.jsonl (in-place).
 * Only run when you polluted the live log with manual pipe tests.
 */

const fs = require('fs');
const path = require('path');

const root = process.env.ACTIVITY_PROJECT_ROOT || process.cwd();
const rel =
  process.env.ACTIVITY_LOG_PATH || '.cursor/activity/activity.jsonl';
const LOG = path.isAbsolute(rel) ? rel : path.join(root, rel);

const FIXTURE_SESSION = /^(test-|wrap-test|c2$|unknown$)/i;
const FIXTURE_MODEL = /^(claude-test|test-model)$/i;
const FIXTURE_CURSOR_VERSION = /^(1\.0\.0|9\.9\.9)$/;

function isFixture(event) {
  const p = event.payload || {};
  if (FIXTURE_SESSION.test(String(event.sessionId || ''))) return true;
  if (FIXTURE_MODEL.test(String(p.model || ''))) return true;
  if (FIXTURE_CURSOR_VERSION.test(String(p.cursor_version || ''))) return true;
  return false;
}

if (!fs.existsSync(LOG)) {
  console.error('No log at', LOG);
  process.exit(1);
}

const lines = fs.readFileSync(LOG, 'utf8').trim().split('\n').filter(Boolean);
const kept = [];
let removed = 0;
for (const line of lines) {
  try {
    if (isFixture(JSON.parse(line))) {
      removed++;
    } else {
      kept.push(line);
    }
  } catch {
    kept.push(line);
  }
}

fs.writeFileSync(LOG, kept.length ? `${kept.join('\n')}\n` : '', 'utf8');
console.log(JSON.stringify({ logPath: LOG, removed, remaining: kept.length }));
