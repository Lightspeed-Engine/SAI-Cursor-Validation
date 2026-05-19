#!/usr/bin/env node
'use strict';

/**
 * Parse real lines from activity.jsonl (if present) using cursor-activity types.
 * Requires: cursor-activity built (npm run compile).
 */

const fs = require('fs');
const path = require('path');

const root = process.env.ACTIVITY_PROJECT_ROOT || path.join(__dirname, '../../..');
const logPath = path.join(root, '.cursor/activity/activity.jsonl');
const typesPath = path.join(root, 'cursor-activity/dist/activity/types.js');

if (!fs.existsSync(typesPath)) {
  console.error('SKIP schema-parse: run `cd cursor-activity && npm run compile` first');
  process.exit(0);
}

const { parseActivityLine, isActivityEvent } = require(typesPath);

if (!fs.existsSync(logPath)) {
  console.log('SKIP schema-parse: no live log at', logPath);
  process.exit(0);
}

const lines = fs.readFileSync(logPath, 'utf8').trim().split('\n').filter(Boolean);
if (lines.length === 0) {
  console.error('FAIL: activity.jsonl is empty');
  process.exit(1);
}

let parsed = 0;
let failed = 0;
for (const line of lines) {
  const event = parseActivityLine(line);
  if (!event || !isActivityEvent(event)) {
    failed++;
    continue;
  }
  parsed++;
}

console.log(`PASS: parsed ${parsed}/${lines.length} log lines with ActivityEvent schema`);

if (parsed === 0) {
  console.error('FAIL: no lines matched schema');
  process.exit(1);
}

if (failed > 0) {
  console.error(`FAIL: ${failed} lines failed schema parse`);
  process.exit(1);
}

process.exit(0);
